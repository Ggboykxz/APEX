use crate::jsonrpc::JsonRpcClient;
use anyhow::Result;
use serde_json::{json, Value};
use std::path::Path;

pub struct LspManager {
    client: Option<JsonRpcClient>,
    root: String,
}

impl LspManager {
    pub fn new() -> Self { Self { client: None, root: String::new() } }

    pub async fn start(&mut self, program: &str, args: &[&str], root: &str) -> Result<()> {
        let mut c = JsonRpcClient::spawn(program, args).await?;
        let root_uri = format!("file://{}", root);
        let _ = c.request("initialize", json!({
            "processId": std::process::id(),
            "rootUri": root_uri,
            "capabilities": {}
        })).await;
        let _ = c.notify("initialized", json!({})).await;
        self.client = Some(c);
        self.root = root.to_string();
        Ok(())
    }

    pub async fn diagnostics(&mut self, path: &str) -> Result<Value> {
        let c = self.client.as_mut().ok_or_else(|| anyhow::anyhow!("no lsp server"))?;
        let uri = if path.starts_with("file://") { path.to_string() } else { format!("file://{}", path) };
        // pull diagnostics (LSP 3.17)
        c.request("textDocument/diagnostic", json!({"textDocument":{"uri":uri}})).await
    }

    pub async fn shutdown(&mut self) {
        if let Some(c) = self.client.as_mut() {
            let _ = c.request("shutdown", json!(null)).await;
            let _ = c.notify("exit", json!({})).await;
            c.shutdown().await;
        }
        self.client = None;
    }
}

pub fn get_lsp_manager(_cwd: &str) -> LspManager {
    LspManager::new()
}