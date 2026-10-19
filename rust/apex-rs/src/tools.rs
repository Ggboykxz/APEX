use crate::formatter;
use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::sync::Mutex;

static BACKUP_STACK: Mutex<Vec<(PathBuf, String)>> = Mutex::new(Vec::new());
static REDO_STACK: Mutex<Vec<(PathBuf, String, String)>> = Mutex::new(Vec::new());

/// Restore the last file overwritten by `write_file`.
pub fn undo_last_edit() -> String {
    let mut stack = match BACKUP_STACK.lock() {
        Ok(s) => s,
        Err(_) => return "ERROR: lock poisoned".to_string(),
    };
    let Some((path, old_content)) = stack.pop() else {
        return "Nothing to undo".to_string();
    };
    let current = fs::read_to_string(&path).unwrap_or_default();
    match fs::write(&path, &old_content) {
        Ok(_) => {
            if let Ok(mut redo) = REDO_STACK.lock() {
                redo.push((path.clone(), old_content, current));
            }
            format!("Restored {}", path.display())
        }
        Err(e) => format!("ERROR: {e}"),
    }
}

/// Re-apply the last undone edit.
pub fn redo_last_edit() -> String {
    let mut redo = match REDO_STACK.lock() {
        Ok(s) => s,
        Err(_) => return "ERROR: lock poisoned".to_string(),
    };
    let Some((path, old_content, new_content)) = redo.pop() else {
        return "Nothing to redo".to_string();
    };
    match fs::write(&path, &new_content) {
        Ok(_) => {
            if let Ok(mut stack) = BACKUP_STACK.lock() {
                stack.push((path.clone(), old_content));
            }
            format!("Re-applied {}", path.display())
        }
        Err(e) => format!("ERROR: {e}"),
    }
}

pub fn tool_schemas() -> Value {
    let base = json!([
        {"type":"function","function":{"name":"read_file","description":"Read a file","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"write_file","description":"Write a file","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
        {"type":"function","function":{"name":"list_files","description":"List files in a directory","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"run_command","description":"Run a shell command","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}},
        {"type":"function","function":{"name":"git_status","description":"Show git working tree status","parameters":{"type":"object","properties":{}}}},
        {"type":"function","function":{"name":"git_diff","description":"Show git diff","parameters":{"type":"object","properties":{"ref":{"type":"string"}}}}},
        {"type":"function","function":{"name":"git_log","description":"Show recent git commits","parameters":{"type":"object","properties":{"n":{"type":"integer"}}}}},
        {"type":"function","function":{"name":"search_in_files","description":"Search a pattern in files","parameters":{"type":"object","properties":{"pattern":{"type":"string"},"path":{"type":"string"}},"required":["pattern"]}}},
        {"type":"function","function":{"name":"format_file","description":"Format a file with the appropriate formatter","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"undo_last_edit","description":"Undo the last file write","parameters":{"type":"object","properties":{}}}},
        {"type":"function","function":{"name":"redo_last_edit","description":"Re-apply the last undone file write","parameters":{"type":"object","properties":{}}}},
        {"type":"function","function":{"name":"git_undo","description":"Revert uncommitted changes (git checkout)","parameters":{"type":"object","properties":{"path":{"type":"string"}}}}},
        {"type":"function","function":{"name":"lsp_diagnostics","description":"Get LSP diagnostics for a file","parameters":{"type":"object","properties":{"path":{"type":"string"},"server":{"type":"string"}},"required":["path"]}}}
    ]);
    let mut arr = base.as_array().cloned().unwrap_or_default();
    for t in crate::mcp_client::global_tools() {
        arr.push(t);
    }
    Value::Array(arr)
}

fn is_dangerous_command(cmd: &str) -> bool {
    let lower = cmd.to_lowercase();
    let blocked = ["rm -rf /", "rm -rf ~", ":(){:|:&};:", "mkfs", "dd if=", "> /dev/sd"];
    blocked.iter().any(|b| lower.contains(b))
}

pub fn execute_tool(name: &str, args: &Value, cwd: &std::path::Path) -> String {
    if name.starts_with("mcp_") {
        if let Some(res) = crate::mcp_client::call_tool_blocking(name.to_string(), args.clone()) {
            return res;
        }
        return "ERROR: MCP tool unavailable".to_string();
    }
    let result = match name {
        "read_file" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let full = resolve(path, cwd);
            match fs::read_to_string(&full) {
                Ok(c) => c,
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "write_file" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let content = args.get("content").and_then(|v| v.as_str()).unwrap_or("");
            let full = resolve(path, cwd);
            // Snapshot before overwrite for undo support.
            if full.exists() {
                if let Ok(orig) = fs::read_to_string(&full) {
                    if let Ok(mut stack) = BACKUP_STACK.lock() {
                        stack.push((full.clone(), orig));
                    }
                }
            }
            if let Ok(mut redo) = REDO_STACK.lock() {
                redo.clear();
            }
            if let Some(parent) = full.parent() {
                let _ = fs::create_dir_all(parent);
            }
            match fs::write(&full, content) {
                Ok(_) => {
                    let fmt = formatter::format_file(&full);
                    format!("Wrote {} ({})", full.display(), fmt)
                }
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "undo_last_edit" => undo_last_edit(),
        "redo_last_edit" => redo_last_edit(),
        "git_undo" => {
            let path = args.get("path").and_then(|v| v.as_str());
            let mut cmd = vec!["checkout", "--"];
            if let Some(p) = path { cmd.push(p); } else { cmd.push("."); }
            match Command::new("git").args(&cmd).current_dir(cwd).output() {
                Ok(o) if o.status.success() => "Reverted uncommitted changes".to_string(),
                Ok(o) => format!("ERROR: {}", String::from_utf8_lossy(&o.stderr)),
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "lsp_diagnostics" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let server = args.get("server").and_then(|v| v.as_str()).unwrap_or("");
            // Determine server command from extension if not provided
            let (prog, sargs): (String, Vec<String>) = if !server.is_empty() {
                (server.to_string(), vec![])
            } else {
                let ext = std::path::Path::new(path).extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
                match ext.as_str() {
                    "rs" => ("rust-analyzer".to_string(), vec![]),
                    "py" => ("pyright-langserver".to_string(), vec!["--stdio".to_string()]),
                    "ts" | "js" | "tsx" | "jsx" => ("typescript-language-server".to_string(), vec!["--stdio".to_string()]),
                    "go" => ("gopls".to_string(), vec![]),
                    _ => (String::new(), vec![]),
                }
            };
            if prog.is_empty() {
                return "ERROR: No LSP server for this file type".to_string();
            }
            // Check if binary available
            if which(&prog).is_none() {
                return format!("ERROR: LSP server '{prog}' not installed");
            }
            let full_path = if std::path::Path::new(path).is_absolute() {
                path.to_string()
            } else {
                cwd.join(path).to_string_lossy().to_string()
            };
            let root = cwd.to_string_lossy().to_string();
            // Same nested-runtime concern as MCP: run on a dedicated thread.
            std::thread::spawn(move || {
                let rt = match tokio::runtime::Runtime::new() {
                    Ok(r) => r,
                    Err(e) => return format!("ERROR: {e}"),
                };
                rt.block_on(async {
                    let mut lsp = crate::lsp::LspManager::new();
                    let arg_refs: Vec<&str> = sargs.iter().map(|s| s.as_str()).collect();
                    if lsp.start(&prog, &arg_refs, &root).await.is_err() {
                        return format!("ERROR: failed to start {prog}");
                    }
                    let res = lsp.diagnostics(&full_path).await;
                    lsp.shutdown().await;
                    match res {
                        Ok(v) => serde_json::to_string_pretty(&v).unwrap_or_default(),
                        Err(e) => format!("ERROR: {e}"),
                    }
                })
            })
            .join()
            .unwrap_or_else(|_| "ERROR: LSP thread panicked".to_string())
        }
        "list_files" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or(".");
            let full = resolve(path, cwd);
            match fs::read_dir(&full) {
                Ok(entries) => {
                    let mut out = Vec::new();
                    for e in entries.flatten() {
                        out.push(e.file_name().to_string_lossy().to_string());
                    }
                    out.join("\n")
                }
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "run_command" => {
            let cmd = args.get("command").and_then(|v| v.as_str()).unwrap_or("");
            if is_dangerous_command(cmd) {
                return "ERROR: Command blocked by safety policy".to_string();
            }
            match Command::new("sh").arg("-c").arg(cmd).current_dir(cwd).output() {
                Ok(o) => {
                    let mut s = String::from_utf8_lossy(&o.stdout).to_string();
                    if !o.stderr.is_empty() {
                        s.push_str("\nSTDERR:\n");
                        s.push_str(&String::from_utf8_lossy(&o.stderr));
                    }
                    if !o.status.success() {
                        s.push_str(&format!("\n[exit {}]", o.status.code().unwrap_or(-1)));
                    }
                    s
                }
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "git_status" => run_git(cwd, &["status", "--porcelain"]),
        "git_diff" => {
            let r = args.get("ref").and_then(|v| v.as_str());
            if let Some(ref_) = r {
                run_git(cwd, &["diff", ref_])
            } else {
                run_git(cwd, &["diff"])
            }
        }
        "git_log" => {
            let n = args.get("n").and_then(|v| v.as_i64()).unwrap_or(10);
            run_git(cwd, &["log", &format!("-{n}"), "--oneline", "--decorate"])
        }
        "search_in_files" => {
            let pattern = args.get("pattern").and_then(|v| v.as_str()).unwrap_or("");
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or(".");
            let full = resolve(path, cwd);
            match Command::new("grep").args(["-rn", pattern, &full.to_string_lossy()]).output() {
                Ok(o) => {
                    let s = String::from_utf8_lossy(&o.stdout).to_string();
                    if s.trim().is_empty() { "[no matches]".to_string() } else { s }
                }
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "format_file" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let full = resolve(path, cwd);
            formatter::format_file(&full)
        }
        _ => format!("ERROR: Unknown tool '{name}'"),
    };
    crate::hooks::trigger_hooks(name, args);
    result
}

fn which(name: &str) -> Option<std::path::PathBuf> {
    let path = std::env::var("PATH").unwrap_or_default();
    for dir in path.split(':') {
        let p = std::path::Path::new(dir).join(name);
        if p.is_file() {
            return Some(p);
        }
    }
    None
}

fn resolve(path: &str, cwd: &std::path::Path) -> PathBuf {
    if std::path::Path::new(path).is_absolute() {
        PathBuf::from(path)
    } else {
        cwd.join(path)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn read_write_list() {
        let dir = tempdir().unwrap();
        let p = dir.path().join("a.txt");
        assert!(execute_tool("write_file", &serde_json::json!({"path": p.to_str().unwrap(), "content": "hi"}), dir.path()).contains("Wrote"));
        assert_eq!(execute_tool("read_file", &serde_json::json!({"path": p.to_str().unwrap()}), dir.path()), "hi");
        let listing = execute_tool("list_files", &serde_json::json!({"path": dir.path().to_str().unwrap()}), dir.path());
        assert!(listing.contains("a.txt"));
    }

    #[test]
    fn run_command_echo() {
        let dir = tempdir().unwrap();
        let out = execute_tool("run_command", &serde_json::json!({"command": "echo hello"}), dir.path());
        assert!(out.contains("hello"));
    }

    #[test]
    fn dangerous_command_blocked() {
        let dir = tempdir().unwrap();
        let out = execute_tool("run_command", &serde_json::json!({"command": "rm -rf /"}), dir.path());
        assert!(out.contains("blocked"));
    }

    #[test]
    fn unknown_tool() {
        let dir = tempdir().unwrap();
        let out = execute_tool("bogus", &serde_json::json!({}), dir.path());
        assert!(out.contains("Unknown tool"));
    }

    #[test]
    fn undo_last_edit() {
        let dir = tempdir().unwrap();
        let p = dir.path().join("b.txt");
        std::fs::write(&p, "original").unwrap();
        execute_tool("write_file", &serde_json::json!({"path": p.to_str().unwrap(), "content": "changed"}), dir.path());
        assert_eq!(std::fs::read_to_string(&p).unwrap(), "changed");
        let out = execute_tool("undo_last_edit", &serde_json::json!({}), dir.path());
        assert!(out.contains("Restored") || out.contains("Nothing"));
        assert_eq!(std::fs::read_to_string(&p).unwrap(), "original");
    }

    #[test]
    fn git_undo_no_repo() {
        let dir = tempdir().unwrap();
        let out = execute_tool("git_undo", &serde_json::json!({}), dir.path());
        assert!(out.contains("ERROR") || out.contains("Reverted"));
    }
}

fn run_git(cwd: &std::path::Path, args: &[&str]) -> String {
    match Command::new("git").args(args).current_dir(cwd).output() {
        Ok(o) => {
            let out = String::from_utf8_lossy(&o.stdout).to_string();
            if out.trim().is_empty() {
                String::from_utf8_lossy(&o.stderr).to_string()
            } else {
                out
            }
        }
        Err(e) => format!("ERROR: {e}"),
    }
}