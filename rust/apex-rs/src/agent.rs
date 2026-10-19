use crate::config::Config;
use crate::tools;
use anyhow::Result;
use serde_json::{json, Value};
use std::io::{self, Write};

pub struct Agent {
    pub config: Config,
    pub history: Vec<Value>,
}

/// Incremental output of [`Agent::chat_stream`].
#[derive(Debug, Clone, PartialEq)]
pub enum StreamEvent {
    /// A piece of assistant text.
    Chunk(String),
    /// The answer is complete.
    Done,
    /// The upstream API (or transport) failed.
    Error(String),
}

impl Agent {
    pub fn new(config: Config) -> Self {
        Self { config, history: Vec::new() }
    }

    /// Expand @file mentions in user input by appending file contents.
    pub fn expand_mentions(&self, input: &str) -> String {
        let mut out = input.to_string();
        for token in input.split_whitespace() {
            if !token.starts_with('@') { continue; }
            let path = token.trim_start_matches('@');
            if path.is_empty() { continue; }
            let full = if std::path::Path::new(path).is_absolute() {
                std::path::PathBuf::from(path)
            } else {
                self.config.cwd.join(path)
            };
            let ext = full.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
            let is_image = matches!(ext.as_str(), "png" | "jpg" | "jpeg" | "gif" | "webp" | "bmp");
            if is_image {
                if let Ok(bytes) = std::fs::read(&full) {
                    use base64::Engine;
                    let b64 = base64::engine::general_purpose::STANDARD.encode(&bytes);
                    out.push_str(&format!("\n\n[Image: {} (base64, {} bytes)]\n{}", full.display(), bytes.len(), b64));
                }
            } else if let Ok(content) = std::fs::read_to_string(&full) {
                out.push_str(&format!("\n\n[File: {}]\n{}", full.display(), content));
            }
        }
        out
    }

    /// Compact conversation history. Returns number of messages removed.
    /// strategies: "prune" (keep last N), "summarize" (placeholder summary), "merge" (merge consecutive same-role).
    pub fn compact_context(&mut self, strategy: &str) -> usize {
        if self.history.is_empty() {
            return 0;
        }
        let before = self.history.len();
        match strategy {
            "prune" => {
                let keep = 10usize;
                if self.history.len() > keep {
                    let start = self.history.len() - keep;
                    self.history = self.history[start..].to_vec();
                }
            }
            "summarize" => {
                let keep = 10usize;
                if self.history.len() > keep {
                    let start = self.history.len() - keep;
                    let summary: String = self.history[..start]
                        .iter()
                        .map(|m| {
                            let role = m.get("role").and_then(|r| r.as_str()).unwrap_or("?");
                            let content = m.get("content").and_then(|c| c.as_str()).unwrap_or("");
                            format!("{}: {}", role, &content[..content.len().min(80)])
                        })
                        .collect::<Vec<_>>()
                        .join("\n");
                    let mut new = vec![serde_json::json!({"role":"system","content": format!("[Previous conversation summary]\n{}", summary)})];
                    new.extend(self.history[start..].to_vec());
                    self.history = new;
                }
            }
            "merge" => {
                let mut merged: Vec<serde_json::Value> = Vec::new();
                for m in self.history.drain(..) {
                    if let Some(last) = merged.last_mut() {
                        let last_role = last.get("role").and_then(|r| r.as_str()).unwrap_or("");
                        let cur_role = m.get("role").and_then(|r| r.as_str()).unwrap_or("");
                        if last_role == cur_role {
                            let last_content = last.get("content").and_then(|c| c.as_str()).unwrap_or("").to_string();
                            let cur_content = m.get("content").and_then(|c| c.as_str()).unwrap_or("");
                            last["content"] = serde_json::json!(format!("{}\n{}", last_content, cur_content));
                            continue;
                        }
                    }
                    merged.push(m);
                }
                self.history = merged;
            }
            _ => {}
        }
        before - self.history.len()
    }

    pub fn session_path(&self, id: &str) -> std::path::PathBuf {
        let base = dirs::home_dir().unwrap_or_else(|| std::path::PathBuf::from("."));
        base.join(".apex").join("sessions").join(format!("{id}.json"))
    }

    /// Persist the session in the Python-compatible encrypted format.
    pub fn save_session(&self, id: &str) -> anyhow::Result<()> {
        let cwd = self.config.cwd.to_string_lossy().to_string();
        crate::share::save_session(id, &self.config.model, &cwd, &self.history)
            .map(|_| ())
            .ok_or_else(|| anyhow::anyhow!("failed to save session {id}"))
    }

    /// Load a session (encrypted `.enc`, `latest_*` symlink, or plain JSON).
    pub fn load_session(&mut self, id: &str) -> anyhow::Result<()> {
        if let Some(data) = crate::share::load_session(id) {
            self.history = crate::share::history_of(&data);
        }
        Ok(())
    }

    pub async fn chat(&mut self, user_input: &str) -> Result<String> {
        let expanded = self.expand_mentions(user_input);
        self.history.push(json!({"role":"user","content":expanded}));

        // Auto-compaction
        if self.config.auto_compact && self.history.len() > self.config.compact_threshold {
            let keep = self.config.compact_threshold / 2;
            if self.history.len() > keep {
                let start = self.history.len().saturating_sub(keep);
                self.history = self.history[start..].to_vec();
            }
        }

        let client = reqwest::Client::new();
        for _ in 0..10 {
            let mut messages = vec![json!({"role":"system","content":"You are APEX, a helpful coding assistant."})];
            messages.extend(self.history.clone());

            let body = json!({
                "model": self.config.model,
                "messages": messages,
                "tools": tools::tool_schemas(),
                "tool_choice": "auto"
            });

            let url = format!("{}/chat/completions", self.config.base_url.trim_end_matches('/'));
            let mut req = client.post(&url).json(&body);
            if !self.config.api_key.is_empty() {
                req = req.bearer_auth(&self.config.api_key);
            }
            let resp = req.send().await?;
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            if !status.is_success() {
                return Err(anyhow::anyhow!("API error {}: {}", status, text));
            }
            let data: Value = serde_json::from_str(&text)?;
            let choice = &data["choices"][0]["message"];
            let assistant_text = choice.get("content").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let tool_calls = choice.get("tool_calls").cloned().unwrap_or(Value::Null);

            if tool_calls.is_null() || tool_calls.as_array().map(|a| a.is_empty()).unwrap_or(true) {
                self.history.push(json!({"role":"assistant","content":assistant_text}));
                return Ok(assistant_text);
            }

            // execute tools
            self.history.push(choice.clone());
            if let Some(arr) = tool_calls.as_array() {
                for tc in arr {
                    let name = tc["function"]["name"].as_str().unwrap_or("");
                    let args: Value = serde_json::from_str(tc["function"]["arguments"].as_str().unwrap_or("{}")).unwrap_or(json!({}));
                    if self.config.denied_tools.iter().any(|d| d == name) {
                        let tool_call_id = tc["id"].as_str().unwrap_or("");
                        self.history.push(json!({"role":"tool","tool_call_id":tool_call_id,"content":"ERROR: Permission denied"}));
                        continue;
                    }
                    let result = tools::execute_tool(name, &args, &self.config.cwd);
                    let tool_call_id = tc["id"].as_str().unwrap_or("");
                    self.history.push(json!({"role":"tool","tool_call_id":tool_call_id,"content":result}));
                }
            }
        }
        Ok("[max rounds reached]".to_string())
    }

    pub fn run_repl(&mut self) {
        let stdin = io::stdin();
        let mut line = String::new();
        loop {
            print!("apex> ");
            let _ = io::stdout().flush();
            line.clear();
            if stdin.read_line(&mut line).unwrap_or(0) == 0 {
                break;
            }
            let input = line.trim();
            if input.is_empty() {
                continue;
            }
            if input == "/quit" || input == "/exit" {
                break;
            }
            match tokio::runtime::Runtime::new().unwrap().block_on(self.chat(input)) {
                Ok(resp) => println!("{resp}"),
                Err(e) => println!("ERROR: {e}"),
            }
        }
    }

    /// Events emitted while streaming an answer (see [`chat_stream`]).
    pub async fn chat_stream(
        &mut self,
        user_input: &str,
        tx: tokio::sync::mpsc::Sender<StreamEvent>,
    ) -> anyhow::Result<()> {
        let expanded = self.expand_mentions(user_input);
        self.history.push(json!({"role":"user","content":expanded}));

        if self.config.auto_compact && self.history.len() > self.config.compact_threshold {
            let keep = self.config.compact_threshold / 2;
            if self.history.len() > keep {
                let start = self.history.len().saturating_sub(keep);
                self.history = self.history[start..].to_vec();
            }
        }

        let client = reqwest::Client::new();
        for _ in 0..10 {
            let mut messages = vec![json!({"role":"system","content":"You are APEX, a helpful coding assistant."})];
            messages.extend(self.history.clone());

            let body = json!({
                "model": self.config.model,
                "messages": messages,
                "tools": tools::tool_schemas(),
                "tool_choice": "auto",
                "stream": true
            });

            let url = format!("{}/chat/completions", self.config.base_url.trim_end_matches('/'));
            let mut req = client.post(&url).json(&body);
            if !self.config.api_key.is_empty() {
                req = req.bearer_auth(&self.config.api_key);
            }
            let resp = req.send().await?;
            if !resp.status().is_success() {
                let text = resp.text().await.unwrap_or_default();
                let _ = tx.send(StreamEvent::Error(format!("API error: {text}"))).await;
                return Ok(());
            }

            use futures::StreamExt;
            let mut stream = resp.bytes_stream();
            let mut content_acc = String::new();
            // tool_calls accumulator: index -> (id, name, args)
            let mut tool_calls: std::collections::BTreeMap<usize, (String, String, String)> = std::collections::BTreeMap::new();
            let mut finish_reason: Option<String> = None;

            let mut buf = String::new();
            while let Some(chunk) = stream.next().await {
                let chunk = chunk?;
                buf.push_str(&String::from_utf8_lossy(&chunk));
                while let Some(pos) = buf.find('\n') {
                    let line = buf[..pos].trim().to_string();
                    buf = buf[pos + 1..].to_string();
                    if line.is_empty() || !line.starts_with("data:") {
                        continue;
                    }
                    let data = line.trim_start_matches("data:").trim();
                    if data == "[DONE]" {
                        finish_reason = Some("stop".to_string());
                        break;
                    }
                    let v: Value = match serde_json::from_str(data) {
                        Ok(v) => v,
                        Err(_) => continue,
                    };
                    if let Some(fr) = v["choices"][0]["finish_reason"].as_str() {
                        if !fr.is_empty() && fr != "null" {
                            finish_reason = Some(fr.to_string());
                        }
                    }
                    let delta = &v["choices"][0]["delta"];
                    if let Some(c) = delta.get("content").and_then(|x| x.as_str()) {
                        content_acc.push_str(c);
                        let _ = tx.send(StreamEvent::Chunk(c.to_string())).await;
                    }
                    if let Some(tcs) = delta.get("tool_calls").and_then(|x| x.as_array()) {
                        for tc in tcs {
                            let idx = tc.get("index").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
                            let entry = tool_calls.entry(idx).or_insert_with(|| (String::new(), String::new(), String::new()));
                            if let Some(id) = tc.get("id").and_then(|x| x.as_str()) {
                                if entry.0.is_empty() { entry.0 = id.to_string(); }
                            }
                            if let Some(f) = tc.get("function") {
                                if let Some(n) = f.get("name").and_then(|x| x.as_str()) {
                                    if entry.1.is_empty() { entry.1 = n.to_string(); }
                                }
                                if let Some(a) = f.get("arguments").and_then(|x| x.as_str()) {
                                    entry.2.push_str(a);
                                }
                            }
                        }
                    }
                }
                if finish_reason.as_deref() == Some("stop") {
                    break;
                }
            }

            let fr = finish_reason.unwrap_or_default();
            if fr == "tool_calls" || !tool_calls.is_empty() {
                // push assistant message with tool_calls
                let tcs_json: Vec<Value> = tool_calls.iter().map(|(idx, (id, name, args))| {
                    json!({"id": id, "type": "function", "function": {"name": name, "arguments": args}})
                }).collect();
                self.history.push(json!({"role":"assistant","content": if content_acc.is_empty() { Value::Null } else { Value::String(content_acc.clone()) }, "tool_calls": tcs_json}));
                for (_idx, (id, name, args)) in &tool_calls {
                    let parsed_args: Value = serde_json::from_str(args).unwrap_or(json!({}));
                    if self.config.denied_tools.iter().any(|d| d == name) {
                        self.history.push(json!({"role":"tool","tool_call_id": id, "content": "ERROR: Permission denied"}));
                        continue;
                    }
                    let result = tools::execute_tool(name, &parsed_args, &self.config.cwd);
                    self.history.push(json!({"role":"tool","tool_call_id": id, "content": result}));
                }
                continue;
            }

            // final
            self.history.push(json!({"role":"assistant","content": content_acc}));
            let _ = tx.send(StreamEvent::Done).await;
            return Ok(());
        }
        let _ = tx.send(StreamEvent::Done).await;
        Ok(())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::Config;

    #[test]
    fn expand_mentions_text() {
        let cfg = Config::from_env();
        let agent = Agent::new(cfg);
        let out = agent.expand_mentions("hello @README.md");
        assert!(out.contains("hello"));
    }

    #[test]
    fn compact_context_reduces() {
        let cfg = Config::from_env();
        let mut agent = Agent::new(cfg);
        for i in 0..10 {
            agent.history.push(serde_json::json!({"role":"user","content":format!("msg {}", i)}));
            agent.history.push(serde_json::json!({"role":"assistant","content":format!("reply {}", i)}));
        }
        let before = agent.history.len();
        agent.compact_context("prune");
        let after = agent.history.len();
        assert!(after < before);
    }

    #[test]
    fn compact_context_merge() {
        let cfg = Config::from_env();
        let mut agent = Agent::new(cfg);
        agent.history.push(serde_json::json!({"role":"user","content":"a"}));
        agent.history.push(serde_json::json!({"role":"user","content":"b"}));
        agent.history.push(serde_json::json!({"role":"assistant","content":"c"}));
        let before = agent.history.len();
        agent.compact_context("merge");
        assert_eq!(agent.history.len(), 2);
        assert!(before >= 2);
    }

    /// Fake OpenAI-compatible API: first call asks for a `read_file` tool call,
    /// second call answers with plain text.
    async fn fake_api(
        axum::extract::State(calls): axum::extract::State<std::sync::Arc<std::sync::atomic::AtomicUsize>>,
        axum::Json(_body): axum::Json<serde_json::Value>,
    ) -> axum::Json<serde_json::Value> {
        use std::sync::atomic::Ordering;
        let n = calls.fetch_add(1, Ordering::SeqCst);
        if n == 0 {
            axum::Json(serde_json::json!({
                "choices": [{
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": null,
                        "tool_calls": [{
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "read_file", "arguments": "{\"path\":\"note.txt\"}"}
                        }]
                    }
                }]
            }))
        } else {
            axum::Json(serde_json::json!({
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "done"}
                }]
            }))
        }
    }

    #[tokio::test]
    async fn agent_executes_tool_calls_against_api() {
        use axum::{routing::post, Router};
        use std::sync::atomic::AtomicUsize;
        use std::sync::Arc;

        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("note.txt"), "file body").unwrap();

        let calls = Arc::new(AtomicUsize::new(0));
        let app = Router::new()
            .route("/chat/completions", post(fake_api))
            .with_state(calls.clone());
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        tokio::spawn(async move {
            let _ = axum::serve(listener, app).await;
        });

        let mut cfg = Config::from_env();
        cfg.base_url = format!("http://{addr}");
        cfg.model = "fake-model".to_string();
        cfg.api_key = "test".to_string();
        cfg.cwd = dir.path().to_path_buf();

        let mut agent = Agent::new(cfg);
        let reply = agent.chat("please read note.txt").await.unwrap();
        assert_eq!(reply, "done");
        assert_eq!(calls.load(std::sync::atomic::Ordering::SeqCst), 2);

        // The tool result must be threaded back into the conversation.
        let tool_msg = agent
            .history
            .iter()
            .find(|m| m.get("role").and_then(|r| r.as_str()) == Some("tool"))
            .expect("tool message missing");
        assert!(tool_msg["content"].as_str().unwrap().contains("file body"));

        // The assistant tool_call message must be part of the history too.
        assert!(agent
            .history
            .iter()
            .any(|m| m.get("tool_calls").is_some()));
    }

    async fn fake_sse() -> axum::response::Response {
        let body = concat!(
            "data: {\"choices\":[{\"delta\":{\"content\":\"Hel\"},\"finish_reason\":null}]}\n\n",
            "data: {\"choices\":[{\"delta\":{\"content\":\"lo\"},\"finish_reason\":null}]}\n\n",
            "data: {\"choices\":[{\"delta\":{},\"finish_reason\":\"stop\"}]}\n\n",
            "data: [DONE]\n\n",
        );
        axum::response::Response::builder()
            .header("content-type", "text/event-stream")
            .body(axum::body::Body::from(body))
            .unwrap()
    }

    #[tokio::test]
    async fn chat_stream_emits_chunks() {
        use axum::{routing::post, Router};

        let app = Router::new().route("/chat/completions", post(fake_sse));
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        tokio::spawn(async move {
            let _ = axum::serve(listener, app).await;
        });

        let mut cfg = Config::from_env();
        cfg.base_url = format!("http://{addr}");
        cfg.model = "fake-model".to_string();
        cfg.api_key = "test".to_string();

        let mut agent = Agent::new(cfg);
        let (tx, mut rx) = tokio::sync::mpsc::channel::<StreamEvent>(8);
        agent.chat_stream("hi", tx).await.unwrap();
        let mut collected = String::new();
        let mut saw_done = false;
        while let Some(ev) = rx.recv().await {
            match ev {
                StreamEvent::Chunk(text) => collected.push_str(&text),
                StreamEvent::Done => {
                    saw_done = true;
                    break;
                }
                StreamEvent::Error(e) => panic!("unexpected stream error: {e}"),
            }
        }
        assert_eq!(collected, "Hello");
        assert!(saw_done, "stream must end with Done");
        // Streaming answers are recorded in history as well.
        assert!(agent
            .history
            .iter()
            .any(|m| m.get("content").and_then(|c| c.as_str()) == Some("Hello")));
    }

    #[tokio::test]
    async fn denied_tool_is_refused() {
        use axum::{routing::post, Router};
        use std::sync::atomic::AtomicUsize;
        use std::sync::Arc;

        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("note.txt"), "secret body").unwrap();

        let calls = Arc::new(AtomicUsize::new(0));
        let app = Router::new()
            .route("/chat/completions", post(fake_api))
            .with_state(calls.clone());
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        tokio::spawn(async move {
            let _ = axum::serve(listener, app).await;
        });

        let mut cfg = Config::from_env();
        cfg.base_url = format!("http://{addr}");
        cfg.model = "fake-model".to_string();
        cfg.api_key = "test".to_string();
        cfg.cwd = dir.path().to_path_buf();
        cfg.denied_tools = vec!["read_file".to_string()];

        let mut agent = Agent::new(cfg);
        let _ = agent.chat("read note.txt").await.unwrap();
        let tool_msg = agent
            .history
            .iter()
            .find(|m| m.get("role").and_then(|r| r.as_str()) == Some("tool"))
            .expect("tool message missing");
        // Content must not leak when the tool is denied.
        let content = tool_msg["content"].as_str().unwrap();
        assert!(content.contains("Permission denied"));
        assert!(!content.contains("secret body"));
    }
}
