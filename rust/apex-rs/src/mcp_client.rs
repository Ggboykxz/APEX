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

use std::sync::Mutex;

pub struct McpManager {
    pub servers: HashMap<String, McpClient>,
}

static GLOBAL_MCP: Mutex<Option<McpManager>> = Mutex::new(None);

pub fn set_global(manager: McpManager) {
    if let Ok(mut g) = GLOBAL_MCP.lock() {
        *g = Some(manager);
    }
}

/// Convert an MCP tool definition (`name`/`description`/`inputSchema`)
/// into the OpenAI function-calling schema expected by the model API.
pub fn to_openai_tool(server: &str, tool: &Value) -> Value {
    let name = tool.get("name").and_then(|n| n.as_str()).unwrap_or("tool");
    let desc = tool.get("description").and_then(|d| d.as_str()).unwrap_or("");
    let params = tool
        .get("inputSchema")
        .cloned()
        .unwrap_or_else(|| json!({"type": "object", "properties": {}}));
    json!({
        "type": "function",
        "function": {
            "name": format!("mcp_{}_{}", server, name),
            "description": desc,
            "parameters": params
        }
    })
}

pub fn global_tools() -> Vec<Value> {
    let mut out = Vec::new();
    if let Ok(g) = GLOBAL_MCP.lock() {
        if let Some(m) = g.as_ref() {
            for (sname, client) in &m.servers {
                for t in &client.tools {
                    out.push(to_openai_tool(sname, t));
                }
            }
        }
    }
    out
}

fn parse_mcp_name(name: &str) -> Option<(String, String)> {
    let stripped = name.strip_prefix("mcp_")?;
    let mut parts = stripped.splitn(2, '_');
    let server = parts.next()?.to_string();
    let tool = parts.next()?.to_string();
    Some((server, tool))
}

/// Execute an MCP tool from synchronous code.
///
/// The call runs on its own thread with a fresh runtime and a fresh server
/// process. This avoids both nested-runtime panics and reusing pipe handles
/// after the discovery runtime has been dropped.
pub fn call_tool_blocking(name: String, args: Value) -> Option<String> {
    let (server, tool) = parse_mcp_name(&name)?;
    let (command, server_args) = {
        let g = GLOBAL_MCP.lock().ok()?;
        let m = g.as_ref()?;
        let c = m.servers.get(&server)?;
        (c.config.command.clone(), c.config.args.clone())
    };
    std::thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().ok()?;
        rt.block_on(async move {
            let mut client = McpClient::new(McpServerConfig {
                name: server,
                command,
                args: server_args,
            });
            if client.connect().await.is_err() {
                return None;
            }
            let res = client.call_tool(&tool, args).await.ok();
            client.shutdown().await;
            res
        })
    })
    .join()
    .ok()
    .flatten()
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
                // Discovery is done: keep only the tool schemas. Calls spawn a
                // fresh process on demand (see `call_tool_blocking`), because
                // the discovery runtime is dropped when this function returns.
                s.shutdown().await;
            }
        }
    }

    pub fn all_tools(&self) -> Vec<(String, Value)> {
        let mut out = Vec::new();
        for (sname, client) in &self.servers {
            for t in &client.tools {
                out.push((sname.clone(), to_openai_tool(sname, t)));
            }
        }
        out
    }
}
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn openai_schema_conversion() {
        let t = json!({
            "name": "echo",
            "description": "Echo text",
            "inputSchema": {"type": "object", "properties": {"x": {"type": "string"}}}
        });
        let o = to_openai_tool("srv", &t);
        assert_eq!(o["type"], "function");
        assert_eq!(o["function"]["name"], "mcp_srv_echo");
        assert_eq!(o["function"]["description"], "Echo text");
        assert_eq!(o["function"]["parameters"]["properties"]["x"]["type"], "string");
    }

    #[tokio::test]
    async fn mcp_roundtrip_with_fake_server() {
        let dir = tempfile::tempdir().unwrap();
        let script = dir.path().join("fake_mcp.sh");
        let body = r#"#!/bin/sh
while IFS= read -r line; do
  case "$line" in
    *tools/list*) echo '{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"echo","description":"Echo","inputSchema":{"type":"object","properties":{"text":{"type":"string"}}}}]}}' ;;
    *tools/call*) echo '{"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"hello from mcp"}]}}' ;;
    *initialize*) echo '{"jsonrpc":"2.0","id":1,"result":{}}' ;;
  esac
done
"#;
        std::fs::write(&script, body).unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&script, std::fs::Permissions::from_mode(0o755)).unwrap();
        }
        let mut client = McpClient::new(McpServerConfig {
            name: "fake".into(),
            command: script.to_string_lossy().to_string(),
            args: vec![],
        });
        client.connect().await.unwrap();
        assert_eq!(client.tools.len(), 1);
        let out = client.call_tool("echo", json!({"text": "hi"})).await.unwrap();
        assert!(out.contains("hello from mcp"));
        client.shutdown().await;
    }
}
