use crate::formatter;
use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;
use std::process::Command;

pub fn tool_schemas() -> Value {
    json!([
        {"type":"function","function":{"name":"read_file","description":"Read a file","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"write_file","description":"Write a file","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
        {"type":"function","function":{"name":"list_files","description":"List files in a directory","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"run_command","description":"Run a shell command","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}},
        {"type":"function","function":{"name":"git_status","description":"Show git working tree status","parameters":{"type":"object","properties":{}}}},
        {"type":"function","function":{"name":"git_diff","description":"Show git diff","parameters":{"type":"object","properties":{"ref":{"type":"string"}}}}},
        {"type":"function","function":{"name":"git_log","description":"Show recent git commits","parameters":{"type":"object","properties":{"n":{"type":"integer"}}}}},
        {"type":"function","function":{"name":"search_in_files","description":"Search a pattern in files","parameters":{"type":"object","properties":{"pattern":{"type":"string"},"path":{"type":"string"}},"required":["pattern"]}}},
        {"type":"function","function":{"name":"format_file","description":"Format a file with the appropriate formatter","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}}
    ])
}

fn is_dangerous_command(cmd: &str) -> bool {
    let lower = cmd.to_lowercase();
    let blocked = ["rm -rf /", "rm -rf ~", ":(){:|:&};:", "mkfs", "dd if=", "> /dev/sd"];
    blocked.iter().any(|b| lower.contains(b))
}

pub fn execute_tool(name: &str, args: &Value, cwd: &std::path::Path) -> String {
    match name {
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
    }
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