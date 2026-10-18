use crate::config::Config;
use crate::tools;
use anyhow::Result;
use serde_json::{json, Value};
use std::io::{self, Write};

pub struct Agent {
    pub config: Config,
    pub history: Vec<Value>,
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
            if let Ok(content) = std::fs::read_to_string(&full) {
                out.push_str(&format!("\n\n[File: {}]\n{}", full.display(), content));
            }
        }
        out
    }

    pub fn session_path(&self, id: &str) -> std::path::PathBuf {
        let base = dirs::home_dir().unwrap_or_else(|| std::path::PathBuf::from("."));
        base.join(".apex").join("sessions").join(format!("{id}.json"))
    }

    pub fn save_session(&self, id: &str) -> anyhow::Result<()> {
        let path = self.session_path(id);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let json = serde_json::to_string_pretty(&self.history)?;
        std::fs::write(&path, json)?;
        Ok(())
    }

    pub fn load_session(&mut self, id: &str) -> anyhow::Result<()> {
        let path = self.session_path(id);
        if path.exists() {
            let data = std::fs::read_to_string(&path)?;
            self.history = serde_json::from_str(&data).unwrap_or_default();
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

    pub async fn chat_stream(&mut self, user_input: &str, tx: tokio::sync::mpsc::Sender<String>) -> anyhow::Result<()> {
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
                let _ = tx.send(format!("ERROR: API {}: {}", "error", text)).await;
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
                        let _ = tx.send(c.to_string()).await;
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
            let _ = tx.send("[DONE]".to_string()).await;
            return Ok(());
        }
        let _ = tx.send("[DONE]".to_string()).await;
        Ok(())
    }
}