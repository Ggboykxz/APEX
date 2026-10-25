use crate::jsonrpc::JsonRpcClient;
use anyhow::Result;
use serde_json::{json, Value};
use std::path::Path;

pub struct LspManager {
    client: Option<JsonRpcClient>,
    root: String,
}

/// LSP `languageId` for a file extension.
pub fn language_id(path: &str) -> &'static str {
    match Path::new(path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_lowercase()
        .as_str()
    {
        "rs" => "rust",
        "py" => "python",
        "ts" => "typescript",
        "tsx" => "typescriptreact",
        "js" => "javascript",
        "jsx" => "javascriptreact",
        "go" => "go",
        "dart" => "dart",
        "json" => "json",
        "md" => "markdown",
        _ => "plaintext",
    }
}

pub fn file_uri(path: &str) -> String {
    if path.starts_with("file://") {
        path.to_string()
    } else {
        format!("file://{path}")
    }
}

impl LspManager {
    pub fn new() -> Self {
        Self {
            client: None,
            root: String::new(),
        }
    }

    pub async fn start(&mut self, program: &str, args: &[&str], root: &str) -> Result<()> {
        // LSP requires `Content-Length` framing — unlike MCP's line-delimited JSON.
        let mut c = JsonRpcClient::spawn_framed(program, args).await?;
        let root_uri = file_uri(root);
        let _ = c
            .request(
                "initialize",
                json!({
                    "processId": std::process::id(),
                    "rootUri": root_uri,
                    "capabilities": {
                        "experimental": {"serverStatusNotification": true},
                        "textDocument": {
                            "hover": {"contentFormat": ["plaintext", "markdown"]},
                            "definition": {},
                            "references": {},
                            "publishDiagnostics": {}
                        }
                    },
                    "workspaceFolders": [{"uri": root_uri, "name": "workspace"}]
                }),
            )
            .await;
        let _ = c.notify("initialized", json!({})).await;
        self.client = Some(c);
        self.root = root.to_string();
        Ok(())
    }

    /// `textDocument/didOpen` — most servers only answer queries for open documents.
    pub async fn did_open(&mut self, path: &str) -> Result<()> {
        let c = self
            .client
            .as_mut()
            .ok_or_else(|| anyhow::anyhow!("no lsp server"))?;
        let text = std::fs::read_to_string(path).unwrap_or_default();
        c.notify(
            "textDocument/didOpen",
            json!({
                "textDocument": {
                    "uri": file_uri(path),
                    "languageId": language_id(path),
                    "version": 1,
                    "text": text,
                }
            }),
        )
        .await
    }

    /// Block until the server reports it is done indexing, or until it has been
    /// silent for a while (servers that never report readiness).
    ///
    /// rust-analyzer answers queries with `null` while it is still loading, so
    /// queries must wait for `experimental/serverStatus {quiescent: true}`.
    pub async fn wait_ready(&mut self, timeout_ms: u64) -> bool {
        let Some(c) = self.client.as_mut() else {
            return false;
        };
        let deadline = tokio::time::Instant::now() + std::time::Duration::from_millis(timeout_ms);
        let mut last_message = tokio::time::Instant::now();
        // Servers that report their status (rust-analyzer) must be waited for;
        // servers that stay silent are assumed ready after a quiet period.
        let mut saw_status = false;
        loop {
            let now = tokio::time::Instant::now();
            if now >= deadline {
                return false;
            }
            let step = std::time::Duration::from_millis(400).min(deadline - now);
            match tokio::time::timeout(step, c.read_message()).await {
                Ok(Ok(v)) => {
                    if let Some(q) = v.get("params").and_then(|p| p.get("quiescent")) {
                        saw_status = true;
                        if q.as_bool() == Some(true) {
                            return true;
                        }
                    }
                    last_message = tokio::time::Instant::now();
                }
                Ok(Err(_)) => return false,
                Err(_) => {
                    // Consecutive read timeouts = the server is idle.
                    if !saw_status
                        && last_message.elapsed() >= std::time::Duration::from_millis(800)
                    {
                        return true;
                    }
                }
            }
        }
    }

    fn position(line: i64, column: i64) -> Value {
        json!({"line": line.max(0), "character": column.max(0)})
    }

    pub async fn definition(&mut self, path: &str, line: i64, column: i64) -> Result<Value> {
        let uri = file_uri(path);
        let c = self
            .client
            .as_mut()
            .ok_or_else(|| anyhow::anyhow!("no lsp server"))?;
        c.request(
            "textDocument/definition",
            json!({
                "textDocument": {"uri": uri},
                "position": Self::position(line, column),
            }),
        )
        .await
    }

    pub async fn references(&mut self, path: &str, line: i64, column: i64) -> Result<Value> {
        let uri = file_uri(path);
        let c = self
            .client
            .as_mut()
            .ok_or_else(|| anyhow::anyhow!("no lsp server"))?;
        c.request(
            "textDocument/references",
            json!({
                "textDocument": {"uri": uri},
                "position": Self::position(line, column),
                "context": {"includeDeclaration": true},
            }),
        )
        .await
    }

    pub async fn hover(&mut self, path: &str, line: i64, column: i64) -> Result<Value> {
        let uri = file_uri(path);
        let c = self
            .client
            .as_mut()
            .ok_or_else(|| anyhow::anyhow!("no lsp server"))?;
        c.request(
            "textDocument/hover",
            json!({
                "textDocument": {"uri": uri},
                "position": Self::position(line, column),
            }),
        )
        .await
    }

    pub async fn diagnostics(&mut self, path: &str) -> Result<Value> {
        let c = self
            .client
            .as_mut()
            .ok_or_else(|| anyhow::anyhow!("no lsp server"))?;
        // pull diagnostics (LSP 3.17)
        c.request(
            "textDocument/diagnostic",
            json!({"textDocument":{"uri":file_uri(path)}}),
        )
        .await
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn language_ids_by_extension() {
        assert_eq!(language_id("/tmp/a.rs"), "rust");
        assert_eq!(language_id("/tmp/a.tsx"), "typescriptreact");
        assert_eq!(language_id("/tmp/a.py"), "python");
        assert_eq!(language_id("/tmp/a.unknown"), "plaintext");
    }

    #[test]
    fn uris_are_prefixed_once() {
        assert_eq!(file_uri("/tmp/a.rs"), "file:///tmp/a.rs");
        assert_eq!(file_uri("file:///tmp/a.rs"), "file:///tmp/a.rs");
    }
}
