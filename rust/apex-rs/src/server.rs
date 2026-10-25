use crate::agent::Agent;
use crate::config::Config;
use crate::tools;
use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::State;
use axum::response::sse::{Event, Sse};
use axum::{
    routing::{get, post},
    Json, Router,
};
use futures::stream::StreamExt;
use serde::Serialize;
use std::convert::Infallible;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::sync::Mutex;

#[derive(Clone)]
struct AppState {
    agent: Arc<Mutex<Agent>>,
    config: Config,
    /// Broadcast bus for TUI events (`chat_complete`, …), parity with Python's `event_bus`.
    events: tokio::sync::broadcast::Sender<String>,
}

/// Chat request. The TUI sends `message`, the CLI/API docs use `prompt`.
#[derive(serde::Deserialize)]
struct ChatReq {
    #[serde(default)]
    prompt: Option<String>,
    #[serde(default)]
    message: Option<String>,
    #[serde(default)]
    model: Option<String>,
    // Accepted for API compatibility but not forwarded to the agent yet.
    // TODO(v2.6): select the requested agent in `/api/v1/chat`.
    #[serde(default)]
    #[allow(dead_code)]
    agent: Option<String>,
}

impl ChatReq {
    fn text(&self) -> String {
        self.prompt
            .clone()
            .or_else(|| self.message.clone())
            .unwrap_or_default()
    }
}

#[derive(Serialize)]
struct ChatResp {
    response: String,
    usage: serde_json::Value,
}

fn now_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0)
}

fn event(name: &str, data: serde_json::Value) -> String {
    serde_json::json!({
        "event": name,
        "data": data,
        "timestamp": now_ms(),
    })
    .to_string()
}

/// Recursively list files under `root`, relative paths, skipping VCS/build dirs.
fn list_files(root: &std::path::Path, max: usize) -> Vec<String> {
    const SKIP: [&str; 6] = [".git", "node_modules", "target", ".venv", "dist", "build"];
    let mut out = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(rd) = std::fs::read_dir(&dir) else {
            continue;
        };
        for entry in rd.flatten() {
            if out.len() >= max {
                return out;
            }
            let path = entry.path();
            let name = entry.file_name().to_string_lossy().to_string();
            if name.starts_with('.') && name != ".env" && name != ".gitignore" {
                continue;
            }
            if path.is_dir() {
                if !SKIP.contains(&name.as_str()) {
                    stack.push(path);
                }
            } else if let Ok(rel) = path.strip_prefix(root) {
                // The HTTP API exposes POSIX-style paths on every platform.
                out.push(rel.to_string_lossy().replace('\\', "/"));
            }
        }
    }
    out.sort();
    out
}

fn run_shell_capture(command: &str, cwd: &std::path::Path) -> serde_json::Value {
    // `/api/v1/bash` must not be a way around the same safety policy that
    // guards the `run_command` tool.
    let analysis = crate::shell_security::SHELL_ANALYZER.analyze(command);
    if !analysis.safe {
        return serde_json::json!({
            "error": "blocked by safety policy",
            "warnings": analysis.warnings,
        });
    }
    match crate::tools::shell_command(command)
        .current_dir(cwd)
        .output()
    {
        Ok(o) => serde_json::json!({
            "stdout": String::from_utf8_lossy(&o.stdout),
            "stderr": String::from_utf8_lossy(&o.stderr),
            "exit_code": o.status.code().unwrap_or(-1),
        }),
        Err(e) => serde_json::json!({"error": e.to_string()}),
    }
}

pub async fn serve(config: Config, port: u16) {
    let (events, _) = tokio::sync::broadcast::channel::<String>(256);
    let state = AppState {
        agent: Arc::new(Mutex::new(Agent::new(config.clone()))),
        config,
        events,
    };

    let app = Router::new()
        .route("/health", get(|| async { "ok" }))
        .route("/api/v1/tools", get(|| async {
            Json(serde_json::to_value(tools::tool_schemas()).unwrap())
        }))
        .route("/api/v1/security/analyze", post({
            move |Json(req): Json<serde_json::Value>| async move {
                let command = req.get("command").and_then(|v| v.as_str()).unwrap_or("");
                let analysis = crate::shell_security::SHELL_ANALYZER.analyze(command);
                let mut verdict = analysis.to_json();
                verdict["allowed"] =
                    serde_json::json!(crate::shell_security::SHELL_ANALYZER.is_safe(command));
                Json(verdict)
            }
        }))
        .route("/api/v1/models", get(|State(st): State<AppState>| async move {
            let mut models = vec![st.config.model.clone()];
            for m in ["gpt-4o", "gpt-4o-mini", "claude-sonnet-4-5", "claude-opus-4-1"] {
                if !models.iter().any(|x| x == m) {
                    models.push(m.to_string());
                }
            }
            Json(serde_json::json!({"models": models}))
        }))
        .route("/api/v1/sessions", get(|_st: State<AppState>| async move {
            Json(serde_json::json!({"sessions": crate::share::list_sessions()}))
        }))
        .route("/api/v1/files/read", post({
            move |Json(req): Json<serde_json::Value>| async move {
                let path = req.get("path").and_then(|v| v.as_str()).unwrap_or("");
                match std::fs::read_to_string(path) {
                    Ok(c) => Json(serde_json::json!({"content": c})),
                    Err(e) => Json(serde_json::json!({"error": e.to_string()})),
                }
            }
        }))
        .route("/api/v1/files/write", post({
            move |Json(req): Json<serde_json::Value>| async move {
                let path = req.get("path").and_then(|v| v.as_str()).unwrap_or("");
                let content = req.get("content").and_then(|v| v.as_str()).unwrap_or("");
                match std::fs::write(path, content) {
                    Ok(_) => Json(serde_json::json!({"ok": true})),
                    Err(e) => Json(serde_json::json!({"error": e.to_string()})),
                }
            }
        }))
        .route(
            "/api/v1/agents/:id",
            get(|axum::extract::Path(id): axum::extract::Path<String>| async move {
                Json(serde_json::json!({"id": id, "name": id}))
            }),
        )
        .route("/api/v1/plugins", get(|| async {
            let ps = crate::plugins::discover_plugins();
            let list: Vec<serde_json::Value> = ps
                .iter()
                .map(|p| {
                    let tools: Vec<serde_json::Value> = p
                        .tools()
                        .iter()
                        .map(|t| {
                            serde_json::json!({
                                "name": t.name,
                                "full_name": crate::plugins::tool_full_name(&p.name, &t.name),
                                "description": t.description,
                            })
                        })
                        .collect();
                    serde_json::json!({
                        "name": p.name,
                        "version": p.version(),
                        "description": p.description(),
                        "enabled": p.enabled(),
                        "has_manifest": p.manifest.is_some(),
                        "tools": tools,
                    })
                })
                .collect();
            let names: Vec<String> = ps.into_iter().map(|p| p.name).collect();
            Json(serde_json::json!({"plugins": names, "details": list}))
        }))
        .route("/api/v1/agents", get(|| async {
            Json(serde_json::json!({"agents": [
                {"id":"build","name":"Build"},
                {"id":"plan","name":"Plan"}
            ]}))
        }))
        .route("/api/v1/themes", get(|State(st): State<AppState>| async move {
            let themes = [
                ("default", "Default"),
                ("light", "Light"),
                ("dark", "Dark"),
                ("forest", "Forest"),
                ("sunset", "Sunset"),
            ];
            let list: Vec<serde_json::Value> = themes
                .iter()
                .map(|(id, name)| serde_json::json!({"id": id, "name": name}))
                .collect();
            Json(serde_json::json!({"themes": list, "current": st.config.theme}))
        }))
        .route("/api/v1/files", get(|State(st): State<AppState>| async move {
            let files = list_files(&st.config.cwd, 500);
            Json(serde_json::json!({"files": files}))
        }))
        .route("/api/v1/tui-config", get(|State(st): State<AppState>| async move {
            Json(serde_json::json!({
                "leader_timeout": 2000,
                "keybinds": st.config.keybinds,
                "theme": st.config.theme,
                "model": st.config.model,
            }))
        }))
        .route("/api/v1/config", get(|State(st): State<AppState>| async move {
            let a = st.agent.lock().await;
            Json(serde_json::json!({
                "model": a.config.model,
                "base_url": a.config.base_url,
                "theme": a.config.theme,
                "cwd": a.config.cwd.to_string_lossy(),
                "auto_compact": a.config.auto_compact,
                "compact_threshold": a.config.compact_threshold,
                "denied_tools": a.config.denied_tools,
            }))
        }))
        .route("/api/v1/undo", post(|| async {
            let msg = tools::undo_last_edit();
            let ok = !msg.starts_with("ERROR") && !msg.starts_with("Nothing");
            Json(serde_json::json!({"ok": ok, "detail": msg, "error": if ok { serde_json::Value::Null } else { serde_json::Value::String(msg.clone()) }}))
        }))
        .route("/api/v1/redo", post(|| async {
            let msg = tools::redo_last_edit();
            let ok = !msg.starts_with("ERROR") && !msg.starts_with("Nothing");
            Json(serde_json::json!({"ok": ok, "detail": msg, "error": if ok { serde_json::Value::Null } else { serde_json::Value::String(msg.clone()) }}))
        }))
        .route("/api/v1/compact", post({
            let state = state.clone();
            move || async move {
                let mut a = state.agent.lock().await;
                let removed = a.compact_context("summarize");
                Json(serde_json::json!({"ok": true, "removed": removed}))
            }
        }))
        .route("/api/v1/bash", post({
            let state = state.clone();
            move |Json(req): Json<serde_json::Value>| async move {
                let command = req.get("command").and_then(|v| v.as_str()).unwrap_or("");
                Json(run_shell_capture(command, &state.config.cwd))
            }
        }))
        .route("/api/v1/sessions/:id", get(|axum::extract::Path(id): axum::extract::Path<String>| async move {
            match crate::share::load_session(&id) {
                Some(history) => Json(serde_json::json!({"id": id, "history": history})),
                None => Json(serde_json::json!({"id": id, "error": "session not found"})),
            }
        }))
        .route("/api/v1/sessions/:id/load", post({
            let state = state.clone();
            move |axum::extract::Path(id): axum::extract::Path<String>| async move {
                let mut a = state.agent.lock().await;
                match a.load_session(&id) {
                    Ok(_) => Json(serde_json::json!({"ok": true, "id": id, "messages": a.history.len()})),
                    Err(e) => Json(serde_json::json!({"ok": false, "error": e.to_string()})),
                }
            }
        }))
        .route("/api/v1/sessions/:id/save", post({
            let state = state.clone();
            move |axum::extract::Path(id): axum::extract::Path<String>| async move {
                let a = state.agent.lock().await;
                match a.save_session(&id) {
                    Ok(_) => Json(serde_json::json!({"ok": true, "id": id})),
                    Err(e) => Json(serde_json::json!({"ok": false, "error": e.to_string()})),
                }
            }
        }))
        .route("/api/v1/sessions/:id/history", get(|axum::extract::Path(id): axum::extract::Path<String>| async move {
            match crate::share::load_session(&id) {
                Some(data) => {
                    let history = crate::share::history_of(&data);
                    Json(serde_json::json!({
                        "id": id,
                        "model": data.get("model"),
                        "messages": history,
                    }))
                }
                None => Json(serde_json::json!({"id": id, "error": "session not found"})),
            }
        }))
        .route("/api/v1/share", post({
            let state = state.clone();
            move |Json(req): Json<serde_json::Value>| async move {
                let session_id = req.get("session_id").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let title = req.get("title").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let live = {
                    let a = state.agent.lock().await;
                    a.history.clone()
                };
                let (id, url) = crate::share::share_session(&session_id, &title, Some(live));
                Json(serde_json::json!({"ok": true, "id": id, "url": url}))
            }
        }))
        .route("/api/v1/share/:id", axum::routing::delete(|axum::extract::Path(id): axum::extract::Path<String>| async move {
            let ok = crate::share::unshare_session(&id);
            Json(serde_json::json!({"ok": ok, "id": id}))
        }))
        .route("/api/v1/shares", get(|| async {
            Json(serde_json::json!({"shares": crate::share::list_shares()}))
        }))
        .route("/api/v1/export", post({
            let state = state.clone();
            move |Json(req): Json<serde_json::Value>| async move {
                let session_id = req.get("session_id").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let live = {
                    let a = state.agent.lock().await;
                    a.history.clone()
                };
                match crate::share::export_session(&session_id, &state.config.cwd, Some(live)) {
                    Some(path) => Json(serde_json::json!({"ok": true, "path": path.to_string_lossy()})),
                    None => Json(serde_json::json!({"ok": false, "error": "nothing to export"})),
                }
            }
        }))
        .route("/api/v1/chat", post({
            let state = state.clone();
            move |Json(req): Json<ChatReq>| async move {
                let mut a = state.agent.lock().await;
                if let Some(model) = req.model.clone().filter(|m| !m.is_empty()) {
                    a.config.model = model;
                }
                let resp = a
                    .chat(&req.text())
                    .await
                    .unwrap_or_else(|e| format!("ERROR: {e}"));
                let usage = a.usage_json();
                Json(ChatResp { response: resp, usage })
            }
        }))
        .route("/api/v1/cost", get(|State(st): State<AppState>| async move {
            let a = st.agent.lock().await;
            let mut cost = a.cost.get_session_cost();
            if let Some(obj) = cost.as_object_mut() {
                obj.insert("usage".to_string(), a.usage_json());
                obj.insert("model".to_string(), serde_json::json!(a.config.model));
            }
            Json(cost)
        }))
        .route("/api/v1/cost/history", get(|State(st): State<AppState>| async move {
            let a = st.agent.lock().await;
            Json(serde_json::json!({"history": a.cost.get_history()}))
        }))
        .route("/api/v1/cost/reset", post(|State(st): State<AppState>| async move {
            let mut a = st.agent.lock().await;
            a.cost.reset_session();
            Json(serde_json::json!({"ok": true}))
        }))
        .route("/api/v1/chat/stream", post(chat_stream_handler))
        .route("/chat/stream", post(chat_stream_handler))
        .route("/ws", get(ws_handler))
        .route("/ws/events", get(ws_handler))
        .with_state(state);

    let addr = format!("127.0.0.1:{port}");
    println!("APEX (Rust) listening on {addr}");
    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn chat_stream_handler(
    State(state): State<AppState>,
    Json(req): Json<ChatReq>,
) -> Sse<impl futures::Stream<Item = Result<Event, Infallible>>> {
    let (tx, rx) = tokio::sync::mpsc::channel::<crate::agent::StreamEvent>(64);
    let agent = state.agent.clone();
    let events = state.events.clone();
    let prompt = req.text();
    let model_override = req.model.clone().filter(|m| !m.is_empty());
    tokio::spawn(async move {
        let mut a = agent.lock().await;
        if let Some(model) = model_override {
            a.config.model = model;
        }
        if let Err(e) = a.chat_stream(&prompt, tx.clone()).await {
            let _ = tx
                .send(crate::agent::StreamEvent::Error(e.to_string()))
                .await;
        }
        // Parity with Python's event_bus.publish("chat_complete", {...}).
        // Usage is per request here (the TUI accumulates its own session totals).
        let payload = event(
            "chat_complete",
            serde_json::json!({
                "model": a.config.model,
                "usage": a.last_usage_json(),
            }),
        );
        let _ = events.send(payload);
    });
    let stream = tokio_stream::wrappers::ReceiverStream::new(rx).map(|ev| {
        // The TUI parses each SSE data line as JSON: `chunk` for text,
        // `usage` before completion, `done` when finished, `error` on failure.
        let payload = match ev {
            crate::agent::StreamEvent::Chunk(text) => serde_json::json!({"chunk": text}),
            crate::agent::StreamEvent::Usage(usage) => serde_json::json!({"usage": usage}),
            crate::agent::StreamEvent::Done => serde_json::json!({"done": true}),
            crate::agent::StreamEvent::Error(message) => serde_json::json!({"error": message}),
        }
        .to_string();
        Ok::<_, Infallible>(Event::default().data(payload))
    });
    Sse::new(stream)
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
) -> impl axum::response::IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, state))
}

async fn handle_socket(socket: WebSocket, state: AppState) {
    use futures::{SinkExt, StreamExt};
    let (mut sender, mut receiver) = socket.split();
    let (out_tx, out_rx) = tokio::sync::mpsc::unbounded_channel::<String>();

    // Outbound traffic = broadcast bus (chat_complete, …) + direct replies to
    // this client's messages, merged into a single sink task.
    let bcast_rx = state.events.subscribe();
    let send_task = tokio::spawn(async move {
        let bcast = futures::stream::unfold(bcast_rx, |mut rx| async move {
            loop {
                match rx.recv().await {
                    Ok(payload) => return Some((payload, rx)),
                    Err(tokio::sync::broadcast::error::RecvError::Lagged(_)) => continue,
                    Err(_) => return None,
                }
            }
        });
        let outbound = tokio_stream::wrappers::UnboundedReceiverStream::new(out_rx);
        let merged = futures::stream::select(bcast, outbound);
        futures::pin_mut!(merged);
        while let Some(payload) = merged.next().await {
            if sender.send(Message::Text(payload)).await.is_err() {
                break;
            }
        }
    });

    let connected = event(
        "connected",
        serde_json::json!({
            "model": state.agent.lock().await.config.model,
            "agent": "build",
            "cwd": state.config.cwd.to_string_lossy(),
            "version": env!("CARGO_PKG_VERSION"),
        }),
    );
    if out_tx.send(connected).is_err() {
        send_task.abort();
        return;
    }

    while let Some(Ok(msg)) = receiver.next().await {
        let Message::Text(text) = msg else {
            if matches!(msg, Message::Close(_)) {
                break;
            }
            continue;
        };
        let v: serde_json::Value = match serde_json::from_str(&text) {
            Ok(v) => v,
            Err(_) => {
                let _ = out_tx.send(event(
                    "error",
                    serde_json::json!({"message": "invalid JSON"}),
                ));
                continue;
            }
        };
        let method = v.get("method").and_then(|m| m.as_str()).unwrap_or("");
        let out = match method {
            "ping" => Some(event("pong", serde_json::json!({}))),
            "state" => {
                let a = state.agent.lock().await;
                Some(event(
                    "state",
                    serde_json::json!({
                        "model": a.config.model,
                        "agent": "build",
                        "cwd": a.config.cwd.to_string_lossy(),
                        "historyLength": a.history.len(),
                        "usage": a.usage_json(),
                    }),
                ))
            }
            "cost" => {
                let a = state.agent.lock().await;
                Some(event(
                    "cost",
                    serde_json::json!({
                        "cost": a.cost.get_session_cost(),
                        "usage": a.usage_json(),
                    }),
                ))
            }
            "undo" => {
                let detail = tools::undo_last_edit();
                Some(event("undo", serde_json::json!({"detail": detail})))
            }
            "redo" => {
                let detail = tools::redo_last_edit();
                Some(event("redo", serde_json::json!({"detail": detail})))
            }
            "compact" => {
                let removed = state.agent.lock().await.compact_context("summarize");
                Some(event("compact", serde_json::json!({"removed": removed})))
            }
            "theme_changed" => {
                let theme = v
                    .get("params")
                    .and_then(|p| p.get("theme"))
                    .and_then(|t| t.as_str())
                    .unwrap_or("default");
                Some(event("theme_changed", serde_json::json!({"theme": theme})))
            }
            "" => None,
            other => Some(event(
                "error",
                serde_json::json!({"message": format!("unknown method: {other}")}),
            )),
        };
        if let Some(payload) = out {
            if out_tx.send(payload).is_err() {
                break;
            }
        }
    }
    drop(out_tx);
    send_task.abort();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn chat_req_accepts_message_and_prompt() {
        let a: ChatReq = serde_json::from_str(r#"{"message":"hi"}"#).unwrap();
        assert_eq!(a.text(), "hi");
        let b: ChatReq = serde_json::from_str(r#"{"prompt":"yo"}"#).unwrap();
        assert_eq!(b.text(), "yo");
        let c: ChatReq = serde_json::from_str(r#"{"prompt":"p","message":"m"}"#).unwrap();
        assert_eq!(c.text(), "p");
    }

    #[test]
    fn shell_capture_works() {
        let dir = tempfile::tempdir().unwrap();
        let v = run_shell_capture("echo hello", dir.path());
        assert_eq!(v["stdout"].as_str().unwrap().trim(), "hello");
        assert_eq!(v["exit_code"], 0);
    }

    #[test]
    fn shell_capture_blocks_dangerous_commands() {
        let dir = tempfile::tempdir().unwrap();
        let marker = dir.path().join("marker.txt");
        let command = format!("echo hi > {} && rm -rf /", marker.display());
        let v = run_shell_capture(&command, dir.path());
        assert_eq!(v["error"], "blocked by safety policy");
        assert!(!marker.exists(), "blocked command must not execute");
    }

    #[test]
    fn list_files_skips_vcs_and_hidden() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("a.txt"), "x").unwrap();
        std::fs::create_dir(dir.path().join(".git")).unwrap();
        std::fs::write(dir.path().join(".git").join("HEAD"), "x").unwrap();
        std::fs::create_dir(dir.path().join("src")).unwrap();
        std::fs::write(dir.path().join("src").join("main.rs"), "x").unwrap();
        let files = list_files(dir.path(), 100);
        assert!(files.contains(&"a.txt".to_string()));
        assert!(files.contains(&"src/main.rs".to_string()));
        assert!(!files.iter().any(|f| f.contains(".git")));
    }
}
