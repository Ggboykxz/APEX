use anyhow::{anyhow, Result};
use serde_json::{json, Value};
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, Command};

/// Wire framing used by the server.
///
/// MCP servers speak line-delimited JSON, the Language Server Protocol uses
/// `Content-Length` headers — the client supports both.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Framing {
    Line,
    ContentLength,
}

pub struct JsonRpcClient {
    child: Child,
    stdin: tokio::process::ChildStdin,
    reader: BufReader<tokio::process::ChildStdout>,
    next_id: i64,
    framing: Framing,
}

impl JsonRpcClient {
    /// Line-delimited JSON-RPC (MCP).
    pub async fn spawn(program: &str, args: &[&str]) -> Result<Self> {
        Self::spawn_with(program, args, Framing::Line).await
    }

    /// `Content-Length` framed JSON-RPC (LSP).
    pub async fn spawn_framed(program: &str, args: &[&str]) -> Result<Self> {
        Self::spawn_with(program, args, Framing::ContentLength).await
    }

    pub async fn spawn_with(program: &str, args: &[&str], framing: Framing) -> Result<Self> {
        let mut child = Command::new(program)
            .args(args)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()?;
        let stdin = child.stdin.take().ok_or_else(|| anyhow!("no stdin"))?;
        let stdout = child.stdout.take().ok_or_else(|| anyhow!("no stdout"))?;
        let reader = BufReader::new(stdout);
        Ok(Self {
            child,
            stdin,
            reader,
            next_id: 1,
            framing,
        })
    }

    async fn write_message(&mut self, v: &Value) -> Result<()> {
        let body = serde_json::to_string(v)?;
        let payload = match self.framing {
            Framing::Line => format!("{body}\n"),
            Framing::ContentLength => {
                format!("Content-Length: {}\r\n\r\n{}", body.len(), body)
            }
        };
        self.stdin.write_all(payload.as_bytes()).await?;
        self.stdin.flush().await?;
        Ok(())
    }

    /// Read one JSON message, tolerating either framing on the wire.
    pub(crate) async fn read_message(&mut self) -> Result<Value> {
        // Try to read a `Content-Length` header block first; a line-delimited
        // server will instead send `{...}\n`, which we parse below.
        let mut first = String::new();
        let n = self.reader.read_line(&mut first).await?;
        if n == 0 {
            return Err(anyhow!("EOF from server"));
        }
        let trimmed = first.trim_end_matches(['\r', '\n']);
        if let Some(rest) = trimmed.strip_prefix("Content-Length:") {
            let len: usize = rest
                .trim()
                .parse()
                .map_err(|_| anyhow!("bad Content-Length"))?;
            // Consume the remaining headers up to the blank line.
            loop {
                let mut header = String::new();
                let hn = self.reader.read_line(&mut header).await?;
                if hn == 0 {
                    return Err(anyhow!("EOF in headers"));
                }
                if header == "\r\n" || header == "\n" {
                    break;
                }
            }
            let mut body = vec![0u8; len];
            self.reader.read_exact(&mut body).await?;
            return Ok(serde_json::from_slice(&body)?);
        }
        if trimmed.is_empty() || !trimmed.starts_with('{') {
            // Unknown preamble (e.g. server logging) — skip and retry.
            return Box::pin(self.read_message()).await;
        }
        Ok(serde_json::from_str(trimmed)?)
    }

    pub async fn request(&mut self, method: &str, params: Value) -> Result<Value> {
        let id = self.next_id;
        self.next_id += 1;
        let req = json!({"jsonrpc":"2.0","id":id,"method":method,"params":params});
        self.write_message(&req).await?;

        // read until we get a response with matching id
        loop {
            let v = self.read_message().await?;
            if v.get("id").and_then(|x| x.as_i64()) == Some(id) {
                if let Some(err) = v.get("error") {
                    return Err(anyhow!("rpc error: {}", err));
                }
                return Ok(v.get("result").cloned().unwrap_or(Value::Null));
            }
            // notification or other id -> ignore
        }
    }

    pub async fn notify(&mut self, method: &str, params: Value) -> Result<()> {
        let req = json!({"jsonrpc":"2.0","method":method,"params":params});
        self.write_message(&req).await
    }

    pub async fn shutdown(&mut self) {
        let _ = self.child.kill().await;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn frame(body: &str) -> String {
        format!("Content-Length: {}\r\n\r\n{}", body.len(), body)
    }

    #[test]
    fn content_length_frame_shape() {
        let f = frame(r#"{"jsonrpc":"2.0"}"#);
        assert!(f.starts_with("Content-Length: 17\r\n\r\n"));
        assert!(f.ends_with(r#"{"jsonrpc":"2.0"}"#));
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn reads_line_delimited_and_framed_messages() {
        // A fake "server" that writes one line-delimited message, one framed
        // message, then keeps reading stdin so the client does not hit EPIPE
        // when it sends the second request.
        let framed_body = r#"{"jsonrpc":"2.0","id":2,"result":"framed-mode"}"#;
        let script = format!(
            "printf '{{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":\"line-mode\"}}\\n'\nprintf 'Content-Length: {}\\r\\n\\r\\n{}'\ncat >/dev/null",
            framed_body.len(),
            framed_body
        );
        let mut c = JsonRpcClient::spawn("sh", &["-c", &script]).await.unwrap();
        let r1 = c.request("ping", json!({})).await.unwrap();
        assert_eq!(r1, json!("line-mode"));
        let r2 = c.request("ping", json!({})).await.unwrap();
        assert_eq!(r2, json!("framed-mode"));
    }

    #[tokio::test]
    async fn framed_client_writes_content_length_header() {
        // Minimal Content-Length framing server (Node); skipped when node is absent.
        let node = std::env::var_os("PATH").and_then(|paths| {
            std::env::split_paths(&paths)
                .map(|d| d.join(if cfg!(windows) { "node.exe" } else { "node" }))
                .find(|p| p.is_file())
        });
        let Some(node) = node else {
            eprintln!("skipping: node not installed");
            return;
        };
        let dir = tempfile::tempdir().unwrap();
        let script_path = dir.path().join("fake_lsp.js");
        std::fs::write(&script_path, r#"
let buf = Buffer.alloc(0);
process.stdin.on('data', (d) => {
  buf = Buffer.concat([buf, d]);
  for (;;) {
    const sep = buf.indexOf('\r\n\r\n');
    if (sep < 0) return;
    const head = buf.slice(0, sep).toString();
    const m = head.match(/Content-Length: (\d+)/);
    if (!m) return;
    const len = parseInt(m[1], 10);
    if (buf.length < sep + 4 + len) return;
    const body = buf.slice(sep + 4, sep + 4 + len).toString();
    buf = buf.slice(sep + 4 + len);
    const req = JSON.parse(body);
    const resp = JSON.stringify({ jsonrpc: '2.0', id: req.id, result: { echoed_method: req.method } });
    process.stdout.write('Content-Length: ' + Buffer.byteLength(resp) + '\r\n\r\n' + resp);
  }
});
"#).unwrap();

        let mut c =
            JsonRpcClient::spawn_framed(node.to_str().unwrap(), &[script_path.to_str().unwrap()])
                .await
                .unwrap();
        let res = c.request("initialize", json!({"x": 1})).await.unwrap();
        assert_eq!(res["echoed_method"], "initialize");
        let res = c.request("textDocument/hover", json!({})).await.unwrap();
        assert_eq!(res["echoed_method"], "textDocument/hover");
        c.shutdown().await;
    }
}
