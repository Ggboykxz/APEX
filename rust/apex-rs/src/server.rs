use crate::agent::Agent;
use crate::config::Config;
use axum::response::sse::{Event, Sse};
use axum::{routing::{get, post}, Json, Router};
use futures::stream::StreamExt;
use serde::{Deserialize, Serialize};
use std::convert::Infallible;
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Deserialize)]
struct ChatReq { prompt: String }

#[derive(Serialize)]
struct ChatResp { response: String }

pub async fn serve(config: Config, port: u16) {
    let agent = Arc::new(Mutex::new(Agent::new(config)));
    let app = Router::new()
        .route("/health", get(|| async { "ok" }))
        .route("/api/v1/tools", get(|| async {
            Json(serde_json::to_value(crate::tools::tool_schemas()).unwrap())
        }))
        .route("/api/v1/models", get(|| async {
            Json(serde_json::json!({"models":[std::env::var("APEX_MODEL").unwrap_or_else(|_| "gpt-4o-mini".to_string())]}))
        }))
        .route("/api/v1/sessions", get(|| async {
            let base = dirs::home_dir().unwrap_or_default().join(".apex").join("sessions");
            let mut names = Vec::new();
            if let Ok(rd) = std::fs::read_dir(&base) {
                for e in rd.flatten() {
                    if let Some(n) = e.file_name().to_str() {
                        names.push(n.trim_end_matches(".json").to_string());
                    }
                }
            }
            Json(serde_json::json!({"sessions": names}))
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
        .route("/api/v1/agents/:id", get(|axum::extract::Path(id): axum::extract::Path<String>| async move {
            Json(serde_json::json!({"id": id, "name": id}))
        }))
        .route("/api/v1/plugins", get(|| async {
            let ps = crate::plugins::discover_plugins();
            let names: Vec<String> = ps.into_iter().map(|p| p.name).collect();
            Json(serde_json::json!({"plugins": names}))
        }))
        .route("/api/v1/agents", get(|| async {
            Json(serde_json::json!({"agents": [{"id":"build","name":"Build"},{"id":"plan","name":"Plan"}]}))
        }))
        .route("/api/v1/themes", get(|| async {
            Json(serde_json::json!({"themes": [{"id":"default","name":"Default"},{"id":"light","name":"Light"}]}))
        }))
        .route("/api/v1/files", get(|| async {
            Json(serde_json::json!({"files": []}))
        }))
        .route("/api/v1/tui-config", get(|| async {
            Json(serde_json::json!({"leader_timeout": 1000, "keybinds": {}}))
        }))
        .route("/api/v1/config", get(|| async {
            Json(serde_json::json!({"model": std::env::var("APEX_MODEL").unwrap_or_else(|_| "gpt-4o-mini".to_string())}))
        }))
        .route("/api/v1/undo", post(|| async { Json(serde_json::json!({"ok": true})) }))
        .route("/api/v1/redo", post(|| async { Json(serde_json::json!({"ok": true})) }))
        .route("/api/v1/chat", post({
            let agent = agent.clone();
            move |Json(req): Json<ChatReq>| async move {
                let mut a = agent.lock().await;
                let resp = a.chat(&req.prompt).await.unwrap_or_else(|e| format!("ERROR: {e}"));
                Json(ChatResp { response: resp })
            }
        }))
        .route("/api/v1/chat/stream", post({
            let agent = agent.clone();
            move |Json(req): Json<ChatReq>| async move {
                let (tx, rx) = tokio::sync::mpsc::channel::<String>(64);
                let agent = agent.clone();
                let prompt = req.prompt.clone();
                tokio::spawn(async move {
                    let mut a = agent.lock().await;
                    let _ = a.chat_stream(&prompt, tx).await;
                });
                let stream = tokio_stream::wrappers::ReceiverStream::new(rx)
                    .map(|msg| Ok::<_, Infallible>(Event::default().data(msg)));
                Sse::new(stream)
            }
        }));
    let addr = format!("127.0.0.1:{port}");
    println!("APEX (Rust) listening on {addr}");
    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}