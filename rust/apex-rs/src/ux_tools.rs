//! UX tools — port of `apex/tools.py` user-interaction operations.
//!
//! Implements: ask_user, select_files, clipboard_read, clipboard_write,
//! retry_last, retry_tool.
//!
//! These are headless-port implementations: `ask_user` returns a waiting
//! message (no prompt surface in headless mode), clipboard tools return an
//! error (no clipboard on a headless backend), and retry tools return an
//! error (no persistent last-tool state / no `advanced.py` port yet).

use serde_json::Value;
use std::path::Path;

/// `ask_user` — Request user input (headless: returns a waiting message).
pub fn ask_user(args: &Value) -> String {
    let question = args.get("question").and_then(|v| v.as_str()).unwrap_or("");
    let options = args
        .get("options")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        })
        .unwrap_or_default();

    if options.is_empty() {
        format!(
            "[WAITING FOR USER INPUT]\nQuestion: {question}\nOptions: Free text answer\n\nUse /answer <response> to reply."
        )
    } else {
        format!(
            "[WAITING FOR USER INPUT]\nQuestion: {question}\nOptions: [{options}]\n\nUse /answer <response> to reply."
        )
    }
}

/// `select_files` — Find files by glob patterns relative to cwd.
pub fn select_files(args: &Value, cwd: &Path) -> String {
    let patterns = args
        .get("patterns")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect::<Vec<_>>())
        .unwrap_or_default();

    if patterns.is_empty() {
        return "ERROR: No patterns provided".to_string();
    }

    let mut files: Vec<String> = Vec::new();
    for pattern in &patterns {
        let glob_pattern = if Path::new(pattern).is_absolute() {
            pattern.to_string()
        } else {
            cwd.join(pattern).to_string_lossy().to_string()
        };
        if let Ok(entries) = glob::glob(&glob_pattern) {
            for entry in entries.flatten() {
                if entry.is_file() {
                    if let Ok(rel) = entry.strip_prefix(cwd) {
                        files.push(rel.to_string_lossy().to_string());
                    }
                }
            }
        }
    }

    if files.is_empty() {
        return format!("No files found matching: {:?}", patterns);
    }

    files.sort();
    files.dedup();
    format!("Selected {} files:\n{}", files.len(), files.join("\n"))
}

/// `clipboard_read` — Read clipboard (headless: not available).
pub fn clipboard_read() -> String {
    "ERROR: No clipboard tool available. Install pyperclip or xclip.".to_string()
}

/// `clipboard_write` — Write clipboard (headless: not available).
pub fn clipboard_write(args: &Value) -> String {
    let _text = args.get("text").and_then(|v| v.as_str()).unwrap_or("");
    "ERROR: No clipboard tool available. Install pyperclip or xclip.".to_string()
}

/// `retry_last` — Retry the last tool (headless: no state).
pub fn retry_last() -> String {
    "ERROR: No previous tool to retry".to_string()
}

/// `retry_tool` — Retry a specific tool (headless: `advanced.py` not ported).
pub fn retry_tool(args: &Value) -> String {
    let _tool = args.get("tool").and_then(|v| v.as_str()).unwrap_or("");
    let _retries = args.get("retries").and_then(|v| v.as_i64()).unwrap_or(3);
    "ERROR: Retry handler not available (advanced.py not ported)".to_string()
}
