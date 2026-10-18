use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;
use std::process::Command;

pub struct ToolResult {
    pub output: String,
}

pub fn tool_schemas() -> Value {
    json!([
        {"type":"function","function":{"name":"read_file","description":"Read a file","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"write_file","description":"Write a file","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
        {"type":"function","function":{"name":"list_files","description":"List files in a directory","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"run_command","description":"Run a shell command","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}}
    ])
}

pub fn execute_tool(name: &str, args: &Value, cwd: &std::path::Path) -> String {
    match name {
        "read_file" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let full = if std::path::Path::new(path).is_absolute() {
                PathBuf::from(path)
            } else {
                cwd.join(path)
            };
            match fs::read_to_string(&full) {
                Ok(c) => c,
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "write_file" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let content = args.get("content").and_then(|v| v.as_str()).unwrap_or("");
            let full = if std::path::Path::new(path).is_absolute() {
                PathBuf::from(path)
            } else {
                cwd.join(path)
            };
            if let Some(parent) = full.parent() {
                let _ = fs::create_dir_all(parent);
            }
            match fs::write(&full, content) {
                Ok(_) => format!("Wrote {}", full.display()),
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "list_files" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or(".");
            let full = if std::path::Path::new(path).is_absolute() {
                PathBuf::from(path)
            } else {
                cwd.join(path)
            };
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
            match Command::new("sh").arg("-c").arg(cmd).current_dir(cwd).output() {
                Ok(o) => {
                    let mut s = String::new();
                    s.push_str(&String::from_utf8_lossy(&o.stdout));
                    if !o.stderr.is_empty() {
                        s.push_str("\nSTDERR:\n");
                        s.push_str(&String::from_utf8_lossy(&o.stderr));
                    }
                    s
                }
                Err(e) => format!("ERROR: {e}"),
            }
        }
        _ => format!("ERROR: Unknown tool '{name}'"),
    }
}