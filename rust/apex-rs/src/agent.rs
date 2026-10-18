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
        self.history.push(json!({"role":"user","content":user_input}));

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
}