use crate::jsonrpc::JsonRpcClient;
use anyhow::Result;
use serde_json::{json, Value};
use std::collections::HashMap;

pub struct McpServerConfig {
    pub name: String,
    pub command: String,
    pub args: Vec<String>,
}

pub struct McpClient {
    pub config: McpServerConfig,
    client: Option<JsonRpcClient>,
    pub tools: Vec<Value>,
}

impl McpClient {
    pub fn new(config: McpServerConfig) -> Self {
        Self { config, client: None, tools: Vec::new() }
    }

    pub async fn connect(&mut self) -> Result<()> {
        let args: Vec<&str> = self.config.args.iter().map(|s| s.as_str()).collect();
        let mut c = JsonRpcClient::spawn(&self.config.command, &args).await?;
        let _ = c.request("initialize", json!({
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name":"apex-rs","version":"0.1"}
        })).await;
        let _ = c.notify("notifications/initialized", json!({})).await;
        if let Ok(res) = c.request("tools/list", json!({})).await {
            if let Some(tools) = res.get("tools").and_then(|t| t.as_array()) {
                self.tools = tools.clone();
            }
        }
        self.client = Some(c);
        Ok(())
    }

    pub async fn call_tool(&mut self, name: &str, args: Value) -> Result<String> {
        let c = self.client.as_mut().ok_or_else(|| anyhow::anyhow!("not connected"))?;
        let res = c.request("tools/call", json!({"name": name, "arguments": args})).await?;
        // extract text content
        if let Some(content) = res.get("content").and_then(|c| c.as_array()) {
            let mut out = String::new();
            for item in content {
                if let Some(t) = item.get("text").and_then(|x| x.as_str()) {
                    out.push_str(t);
                    out.push('\n');
                }
            }
            if !out.is_empty() { return Ok(out); }
        }
        Ok(serde_json::to_string(&res).unwrap_or_default())
    }

    pub async fn shutdown(&mut self) {
        if let Some(c) = self.client.as_mut() {
            c.shutdown().await;
        }
        self.client = None;
    }
}

pub struct McpManager {
    pub servers: HashMap<String, McpClient>,
}

impl McpManager {
    pub fn new() -> Self { Self { servers: HashMap::new() } }

    pub fn add_server(&mut self, name: String, command: String, args: Vec<String>) {
        self.servers.insert(name.clone(), McpClient::new(McpServerConfig { name, command, args }));
    }

    pub async fn connect_all(&mut self) {
        let names: Vec<String> = self.servers.keys().cloned().collect();
        for name in names {
            if let Some(s) = self.servers.get_mut(&name) {
                let _ = s.connect().await;
            }
        }
    }

    pub fn all_tools(&self) -> Vec<(String, Value)> {
        let mut out = Vec::new();
        for (sname, client) in &self.servers {
            for t in &client.tools {
                let mut tool = t.clone();
                // prefix name with mcp_<server>_
                if let Some(name) = tool.get("name").and_then(|n| n.as_str()) {
                    let prefixed = format!("mcp_{}_{}", sname, name);
                    if let Some(obj) = tool.as_object_mut() {
                        obj.insert("name".to_string(), serde_json::Value::String(prefixed));
                    }
                }
                out.push((sname.clone(), tool));
            }
        }
        out
    }
}