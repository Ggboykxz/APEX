use crate::formatter;
use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::sync::Mutex;

/// Build a shell invocation for the current platform.
///
/// The Python backend runs on POSIX `sh`; the Rust port keeps the same
/// behaviour on Unix and uses `cmd /C` on Windows so tools work everywhere.
pub(crate) fn shell_command(command: &str) -> Command {
    #[cfg(windows)]
    {
        let mut cmd = Command::new("cmd");
        cmd.args(["/C", command]);
        cmd
    }
    #[cfg(not(windows))]
    {
        let mut cmd = Command::new("sh");
        cmd.args(["-c", command]);
        cmd
    }
}

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
    // The literal is split into chunks: a single json! with this many
    // entries exceeds serde_json's macro expansion recursion limit.
    let mut base: Vec<Value> = Vec::new();
    base.extend(json!([
        {"type":"function","function":{"name":"read_file","description":"Read a file","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"write_file","description":"Write a file","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
        {"type":"function","function":{"name":"edit_file","description":"Replace a unique string in a file with new content.","parameters":{"type":"object","properties":{"path":{"type":"string","description":"Path to the file to edit"},"old_string":{"type":"string","description":"Unique string to find and replace"},"new_string":{"type":"string","description":"String to replace it with"}},"required":["path","old_string","new_string"]}}},
        {"type":"function","function":{"name":"apply_patch","description":"Apply a multi-file patch atomically. Supports Codex-style patches (***) and unified diffs (--- a/path, +++ b/path). All files are validated before any write; use dry_run to preview. Paths must be relative to the project root.","parameters":{"type":"object","properties":{"patch":{"type":"string","description":"Patch content to apply"},"dry_run":{"type":"boolean","description":"Validate and preview without writing files"}},"required":["patch"]}}},
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
    ]).as_array().cloned().unwrap_or_default());
    base.extend(json!([
        {"type":"function","function":{"name":"lsp_diagnostics","description":"Get LSP diagnostics for a file","parameters":{"type":"object","properties":{"path":{"type":"string"},"server":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"lsp_definition","description":"Go to definition using LSP","parameters":{"type":"object","properties":{"path":{"type":"string"},"line":{"type":"integer"},"column":{"type":"integer"},"server":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"lsp_references","description":"Find references using LSP","parameters":{"type":"object","properties":{"path":{"type":"string"},"line":{"type":"integer"},"column":{"type":"integer"},"server":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"lsp_hover","description":"Show hover information using LSP","parameters":{"type":"object","properties":{"path":{"type":"string"},"line":{"type":"integer"},"column":{"type":"integer"},"server":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"git_stage","description":"Stage files for commit.","parameters":{"type":"object","properties":{"files":{"type":"array","items":{"type":"string"},"description":"Files to stage"}},"required":["files"]}}},
        {"type":"function","function":{"name":"git_unstage","description":"Unstage files.","parameters":{"type":"object","properties":{"files":{"type":"array","items":{"type":"string"},"description":"Files to unstage"}}}}},
        {"type":"function","function":{"name":"git_commit","description":"Commit staged changes.","parameters":{"type":"object","properties":{"message":{"type":"string","description":"Commit message"}},"required":["message"]}}},
        {"type":"function","function":{"name":"git_create_branch","description":"Create a new git branch.","parameters":{"type":"object","properties":{"name":{"type":"string","description":"Branch name"},"checkout":{"type":"boolean","description":"Switch to new branch"}},"required":["name"]}}},
        {"type":"function","function":{"name":"git_switch_branch","description":"Switch to an existing git branch.","parameters":{"type":"object","properties":{"name":{"type":"string","description":"Branch name"}},"required":["name"]}}},
        {"type":"function","function":{"name":"git_delete_branch","description":"Delete a git branch.","parameters":{"type":"object","properties":{"name":{"type":"string","description":"Branch name"},"force":{"type":"boolean","description":"Force delete"}},"required":["name"]}}},
        {"type":"function","function":{"name":"git_list_branches","description":"List all git branches.","parameters":{"type":"object","properties":{}}}},
        {"type":"function","function":{"name":"git_pre_commit","description":"Run git pre-commit checks.","parameters":{"type":"object","properties":{}}}},
        {"type":"function","function":{"name":"git_create_pr","description":"Create a GitHub pull request.","parameters":{"type":"object","properties":{"title":{"type":"string","description":"PR title"},"body":{"type":"string","description":"PR description"},"base":{"type":"string","description":"Target branch"}},"required":["title"]}}},
    ]).as_array().cloned().unwrap_or_default());
    base.extend(json!([
        {"type":"function","function":{"name":"refactor_code","description":"Refactor code (add types, make async, extract method).","parameters":{"type":"object","properties":{"path":{"type":"string","description":"File to refactor"},"function":{"type":"string","description":"Function name"},"style":{"type":"string","description":"Style: async, type_hints, modern"}},"required":["path","function"]}}},
        {"type":"function","function":{"name":"generate_db_model","description":"Generate database model from table schema.","parameters":{"type":"object","properties":{"table":{"type":"string","description":"Table name"},"columns":{"type":"array","items":{"type":"object"},"description":"Column definitions"}},"required":["table","columns"]}}},
        {"type":"function","function":{"name":"generate_dockerfile","description":"Generate Dockerfile for language.","parameters":{"type":"object","properties":{"language":{"type":"string","description":"Language: python, node, go, rust, java"}},"required":["language"]}}},
        {"type":"function","function":{"name":"generate_docker_compose","description":"Generate docker-compose.yml.","parameters":{"type":"object","properties":{"services":{"type":"array","items":{"type":"object"},"description":"Service definitions"}},"required":["services"]}}},
        {"type":"function","function":{"name":"generate_api_client","description":"Generate API client from OpenAPI spec.","parameters":{"type":"object","properties":{"spec":{"type":"string","description":"Path to OpenAPI spec"}},"required":["spec"]}}},
        {"type":"function","function":{"name":"generate_docs","description":"Generate documentation.","parameters":{"type":"object","properties":{"type":{"type":"string","description":"Type: readme, api, markdoc"},"path":{"type":"string","description":"File path for api docs"}},"required":["type"]}}},
        {"type":"function","function":{"name":"profile_code","description":"Profile code complexity and performance.","parameters":{"type":"object","properties":{"path":{"type":"string","description":"File to profile"}},"required":["path"]}}},
        {"type":"function","function":{"name":"optimize_code","description":"Get optimization suggestions.","parameters":{"type":"object","properties":{"path":{"type":"string","description":"File to analyze"}},"required":["path"]}}},
        {"type":"function","function":{"name":"diff_files","description":"Show unified diff between two files.","parameters":{"type":"object","properties":{"path_a":{"type":"string","description":"Path to first file"},"path_b":{"type":"string","description":"Path to second file"}},"required":["path_a","path_b"]}}},
        {"type":"function","function":{"name":"list_skills","description":"List available skills.","parameters":{"type":"object","properties":{}}}},
        {"type":"function","function":{"name":"use_skill","description":"Use a skill with arguments.","parameters":{"type":"object","properties":{"name":{"type":"string","description":"Skill name"},"args":{"type":"object","description":"Skill arguments"}},"required":["name"]}}},
        {"type":"function","function":{"name":"replace_in_files","description":"Search and replace across multiple files.","parameters":{"type":"object","properties":{"pattern":{"type":"string","description":"Search pattern (regex)"},"replacement":{"type":"string","description":"Replacement string"},"files":{"type":"array","items":{"type":"string"},"description":"Glob patterns to match files"},"dry_run":{"type":"boolean","description":"Preview without applying"}},"required":["pattern","replacement"]}}},
        {"type":"function","function":{"name":"analyze_code","description":"Analyze code structure and complexity.","parameters":{"type":"object","properties":{"path":{"type":"string","description":"File to analyze"}},"required":["path"]}}},
        {"type":"function","function":{"name":"explain_code","description":"Explain what a code block does.","parameters":{"type":"object","properties":{"path":{"type":"string","description":"File to explain"},"start":{"type":"integer","description":"Start line"},"end":{"type":"integer","description":"End line"}},"required":["path"]}}}
    ]).as_array().cloned().unwrap_or_default());
    let mut arr = base;
    for t in crate::mcp_client::global_tools() {
        arr.push(t);
    }
    for t in crate::plugins::plugin_tools() {
        arr.push(t);
    }
    Value::Array(arr)
}

fn is_dangerous_command(cmd: &str) -> bool {
    let lower = cmd.to_lowercase();
    let blocked = [
        "rm -rf /",
        "rm -rf ~",
        ":(){:|:&};:",
        "mkfs",
        "dd if=",
        "> /dev/sd",
    ];
    blocked.iter().any(|b| lower.contains(b))
}

pub fn execute_tool(name: &str, args: &Value, cwd: &std::path::Path) -> String {
    if name.starts_with("mcp_") {
        if let Some(res) = crate::mcp_client::call_tool_blocking(name.to_string(), args.clone()) {
            return res;
        }
        return "ERROR: MCP tool unavailable".to_string();
    }
    if name.starts_with(crate::plugins::PLUGIN_TOOL_PREFIX) {
        let result = crate::plugins::execute_plugin_tool(name, args, cwd)
            .unwrap_or_else(|| format!("ERROR: Unknown plugin tool '{name}'"));
        crate::hooks::trigger_hooks(name, args);
        return result;
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
        "edit_file" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let old_string = args
                .get("old_string")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let new_string = args
                .get("new_string")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let full = resolve(path, cwd);
            if !full.exists() {
                format!("ERROR: File not found: {}", full.display())
            } else {
                match fs::read_to_string(&full) {
                    Ok(content) => {
                        if !content.contains(old_string) {
                            "ERROR: String not found in file. Use read_file to see content."
                                .to_string()
                        } else {
                            let new_content = content.replacen(old_string, new_string, 1);
                            match fs::write(&full, new_content) {
                                Ok(_) => format!("SUCCESS: Edited {}", full.display()),
                                Err(e) => format!("ERROR: Cannot edit file: {e}"),
                            }
                        }
                    }
                    Err(e) => format!("ERROR: Cannot edit file: {e}"),
                }
            }
        }
        "apply_patch" => {
            let patch = args.get("patch").and_then(|v| v.as_str()).unwrap_or("");
            let dry_run = args
                .get("dry_run")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            match crate::patch::apply_patch(patch, cwd, dry_run) {
                Ok(result) => {
                    let count = result.files.len();
                    let header = if result.dry_run { "PREVIEW" } else { "SUCCESS" };
                    let action = if result.dry_run {
                        "Patch would apply"
                    } else {
                        "Patch applied"
                    };
                    let mut lines = vec![format!(
                        "{header}: {action} ({count} files, +{}/-{})",
                        result.additions, result.deletions
                    )];
                    for w in &result.warnings {
                        lines.push(format!("warning: {w}"));
                    }
                    lines.join("\n")
                }
                Err(e) => {
                    let mut detail = format!("{}: {}", e.reason, e.message);
                    if let Some(p) = &e.path {
                        if !e.message.contains(p.as_str()) {
                            detail.push_str(&format!(" ({p})"));
                        }
                    }
                    format!("ERROR: {detail}")
                }
            }
        }
        "undo_last_edit" => undo_last_edit(),
        "redo_last_edit" => redo_last_edit(),
        "git_undo" => {
            let path = args.get("path").and_then(|v| v.as_str());
            let mut cmd = vec!["checkout", "--"];
            if let Some(p) = path {
                cmd.push(p);
            } else {
                cmd.push(".");
            }
            match Command::new("git").args(&cmd).current_dir(cwd).output() {
                Ok(o) if o.status.success() => "Reverted uncommitted changes".to_string(),
                Ok(o) => format!("ERROR: {}", String::from_utf8_lossy(&o.stderr)),
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "lsp_diagnostics" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let server = args.get("server").and_then(|v| v.as_str()).unwrap_or("");
            run_lsp_op("diagnostics", path, 0, 0, server, cwd)
        }
        "lsp_definition" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let server = args.get("server").and_then(|v| v.as_str()).unwrap_or("");
            let line = args.get("line").and_then(|v| v.as_i64()).unwrap_or(0);
            let column = args.get("column").and_then(|v| v.as_i64()).unwrap_or(0);
            run_lsp_op("definition", path, line, column, server, cwd)
        }
        "lsp_references" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let server = args.get("server").and_then(|v| v.as_str()).unwrap_or("");
            let line = args.get("line").and_then(|v| v.as_i64()).unwrap_or(0);
            let column = args.get("column").and_then(|v| v.as_i64()).unwrap_or(0);
            run_lsp_op("references", path, line, column, server, cwd)
        }
        "lsp_hover" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let server = args.get("server").and_then(|v| v.as_str()).unwrap_or("");
            let line = args.get("line").and_then(|v| v.as_i64()).unwrap_or(0);
            let column = args.get("column").and_then(|v| v.as_i64()).unwrap_or(0);
            run_lsp_op("hover", path, line, column, server, cwd)
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
            // The shell-security port catches a wider set of destructive
            // patterns than the legacy denylist above.
            let analysis = crate::shell_security::SHELL_ANALYZER.analyze(cmd);
            if !analysis.safe {
                return format!(
                    "ERROR: Command blocked by safety policy: {}",
                    analysis.warnings.join("; ")
                );
            }
            match shell_command(cmd).current_dir(cwd).output() {
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
        "git_stage" => {
            let files = string_array(args, "files");
            if files.is_empty() {
                "ERROR: No files specified".to_string()
            } else {
                let mut cmd = vec!["add"];
                cmd.extend(files.iter().map(|s| s.as_str()));
                match git_ok(cwd, &cmd, |_| {
                    format!("SUCCESS: Staged {} file(s)", files.len())
                }) {
                    Ok(out) => out,
                    Err(e) => format!("ERROR: {e}"),
                }
            }
        }
        "git_unstage" => {
            let files = string_array(args, "files");
            let mut cmd = vec!["reset"];
            if files.is_empty() {
                cmd.push("HEAD");
            } else {
                cmd.extend(files.iter().map(|s| s.as_str()));
            }
            match git_ok(cwd, &cmd, |_| "SUCCESS: Unstaged files".to_string()) {
                Ok(out) => out,
                // On an unborn branch (no commits yet) `git reset HEAD` fails:
                // drop everything from the index instead, like the Python tool
                // which reported success regardless of git's exit code.
                Err(e) => match git_ok(cwd, &["rm", "--cached", "-r", "--quiet", "."], |_| {
                    "SUCCESS: Unstaged files".to_string()
                }) {
                    Ok(out) => out,
                    Err(_) => format!("ERROR: {e}"),
                },
            }
        }
        "git_commit" => {
            let message = args.get("message").and_then(|v| v.as_str()).unwrap_or("");
            if message.is_empty() {
                "ERROR: No commit message".to_string()
            } else {
                match git_ok(cwd, &["commit", "-m", message], |stdout| {
                    format!("SUCCESS: Committed\n{stdout}")
                }) {
                    Ok(out) => out,
                    Err(e) => format!("ERROR: {e}"),
                }
            }
        }
        "git_create_branch" => {
            let name = args.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let checkout = args
                .get("checkout")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            let msg = if checkout {
                format!("SUCCESS: Created branch '{name}' and checked out")
            } else {
                format!("SUCCESS: Created branch '{name}'")
            };
            match git_ok(cwd, &["branch", name], |_| msg.clone()) {
                Ok(out) if checkout => match git_ok(cwd, &["checkout", name], |_| out.clone()) {
                    Ok(out) => out,
                    Err(e) => format!("ERROR: {e}"),
                },
                Ok(out) => out,
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "git_switch_branch" => {
            let name = args.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let cmd = ["checkout", name];
            match git_ok(cwd, &cmd, |_| {
                format!("SUCCESS: Switched to branch '{name}'")
            }) {
                Ok(out) => out,
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "git_delete_branch" => {
            let name = args.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let force = args.get("force").and_then(|v| v.as_bool()).unwrap_or(false);
            let flag = if force { "-D" } else { "-d" };
            match git_ok(cwd, &["branch", flag, name], |_| {
                format!("SUCCESS: Deleted branch '{name}'")
            }) {
                Ok(out) => out,
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "git_list_branches" => match Command::new("git")
            .args(["branch", "-a"])
            .current_dir(cwd)
            .output()
        {
            Ok(o) => format!("Branches:\n{}", String::from_utf8_lossy(&o.stdout)),
            Err(e) => format!("ERROR: {e}"),
        },
        "git_pre_commit" => {
            let status = Command::new("git")
                .args(["status", "--short"])
                .current_dir(cwd)
                .output();
            match status {
                Ok(o) if String::from_utf8_lossy(&o.stdout).trim().is_empty() => {
                    "Nothing to commit (working tree clean)".to_string()
                }
                Ok(o) => {
                    let staged = Command::new("git")
                        .args(["diff", "--cached", "--stat"])
                        .current_dir(cwd)
                        .output()
                        .map(|s| String::from_utf8_lossy(&s.stdout).to_string())
                        .unwrap_or_default();
                    let staged = if staged.trim().is_empty() {
                        "none".to_string()
                    } else {
                        staged
                    };
                    format!(
                        "Pre-commit checks:\nStaged: {staged}\nUnstaged: {}",
                        String::from_utf8_lossy(&o.stdout)
                    )
                }
                Err(e) => format!("ERROR: {e}"),
            }
        }
        "git_create_pr" => {
            let title = args.get("title").and_then(|v| v.as_str()).unwrap_or("");
            let body = args.get("body").and_then(|v| v.as_str()).unwrap_or("");
            let base = args.get("base").and_then(|v| v.as_str()).unwrap_or("main");
            let head = args.get("head").and_then(|v| v.as_str());
            crate::github::create_pr_tool(cwd, title, body, base, head)
        }
        "refactor_code" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let function = args.get("function").and_then(|v| v.as_str()).unwrap_or("");
            let style = args
                .get("style")
                .and_then(|v| v.as_str())
                .unwrap_or("modern");
            let cr = crate::codegen::CodeRefactorer::new(cwd);
            let result = cr.refactor_function(path, function, style);
            match result.get("error").and_then(|e| e.as_str()) {
                Some(err) => format!("ERROR: {err}"),
                None => format!("SUCCESS: Refactored {function} with {style} style"),
            }
        }
        "generate_db_model" => {
            let table = args.get("table").and_then(|v| v.as_str()).unwrap_or("");
            let columns = args
                .get("columns")
                .and_then(|v| v.as_array())
                .cloned()
                .unwrap_or_default();
            let code = crate::codegen::DatabaseManager::generate_model(table, &columns);
            format!("Generated model for {table}:\n\n{code}")
        }
        "generate_dockerfile" => {
            let language = args.get("language").and_then(|v| v.as_str()).unwrap_or("");
            crate::codegen::DockerManager::generate_dockerfile(language)
        }
        "generate_docker_compose" => {
            let services = args
                .get("services")
                .and_then(|v| v.as_array())
                .cloned()
                .unwrap_or_default();
            crate::codegen::DockerManager::generate_docker_compose(&services)
        }
        "generate_api_client" => {
            let spec = args.get("spec").and_then(|v| v.as_str()).unwrap_or("");
            crate::codegen::ApiClientGenerator::new(cwd).generate_from_openapi(spec)
        }
        "generate_docs" => {
            let dtype = args.get("type").and_then(|v| v.as_str()).unwrap_or("");
            let path = args.get("path").and_then(|v| v.as_str());
            let dg = crate::codegen::DocumentationGenerator::new(cwd);
            match (dtype, path) {
                ("readme", _) => dg.generate_readme(),
                ("api", Some(path)) => dg.generate_api_docs(path),
                ("markdoc", _) => dg.generate_markdoc(),
                _ => "ERROR: Invalid doc type or missing path".to_string(),
            }
        }
        "profile_code" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let profile = crate::codegen::PerformanceProfiler::new(cwd).profile_file(path);
            match profile.get("error").and_then(|e| e.as_str()) {
                Some(err) => err.to_string(),
                None => format!(
                    "Code Profile\n{}\nLines: {}\nFunctions: {}\nClasses: {}\nImports: {}\nComplexity: {}",
                    "=".repeat(40),
                    profile["lines"],
                    profile["functions"],
                    profile["classes"],
                    profile["imports"],
                    profile["complexity_score"],
                ),
            }
        }
        "optimize_code" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let suggestions =
                crate::codegen::PerformanceProfiler::new(cwd).suggest_optimizations(path);
            let mut out = format!("Optimization Suggestions\n{}", "=".repeat(40));
            for s in suggestions {
                out.push_str(&format!("\n- {s}"));
            }
            out
        }
        "diff_files" => {
            let path_a = args.get("path_a").and_then(|v| v.as_str()).unwrap_or("");
            let path_b = args.get("path_b").and_then(|v| v.as_str()).unwrap_or("");
            crate::skills::DiffTool::new(cwd).diff(path_a, path_b)
        }
        "list_skills" => {
            let skills = crate::skills::SkillManager::new(cwd).list_skills();
            if skills.is_empty() {
                "No skills available. Create .apex/skills/*.md files.".to_string()
            } else {
                let mut out = vec!["Available skills:".to_string()];
                for (name, description) in skills {
                    out.push(format!("  {name} - {description}"));
                }
                out.join("\n")
            }
        }
        "use_skill" => {
            let name = args.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let mut skill_args: std::collections::BTreeMap<String, String> = Default::default();
            if let Some(obj) = args.get("args").and_then(|v| v.as_object()) {
                for (k, v) in obj {
                    let value = match v {
                        Value::String(s) => s.clone(),
                        other => other.to_string(),
                    };
                    skill_args.insert(k.clone(), value);
                }
            }
            match crate::skills::SkillManager::new(cwd).render(name, &skill_args) {
                Some(rendered) => format!("[SKILL: {name}]\n{rendered}"),
                None => format!("ERROR: Skill '{name}' not found"),
            }
        }
        "replace_in_files" => {
            let pattern = args.get("pattern").and_then(|v| v.as_str()).unwrap_or("");
            let replacement = args
                .get("replacement")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let files = string_array(args, "files");
            let dry_run = args
                .get("dry_run")
                .and_then(|v| v.as_bool())
                .unwrap_or(true);
            let result = crate::skills::SearchReplace::new(cwd).replace_in_files(
                pattern,
                replacement,
                &files,
                dry_run,
            );
            if let Some(err) = result.get("error").and_then(|e| e.as_str()) {
                return err.to_string();
            }
            let replacements = result["replacements"].as_i64().unwrap_or(0);
            let files_modified = result["files_modified"]
                .as_array()
                .cloned()
                .unwrap_or_default();
            let mut out = format!(
                "Found {replacements} replacements in {} files",
                files_modified.len()
            );
            if dry_run {
                out += " (DRY RUN - use dry_run: false to apply)";
            }
            out += "\n\nFiles:\n";
            out += &files_modified
                .iter()
                .take(10)
                .map(|f| f.as_str().unwrap_or(""))
                .collect::<Vec<_>>()
                .join("\n");
            out
        }
        "analyze_code" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let a = crate::skills::CodeAnalyzer::new(cwd).analyze_file(path);
            if let Some(err) = a.get("error").and_then(|e| e.as_str()) {
                return err.to_string();
            }
            let mut lines = vec!["Code Analysis".to_string(), "=".repeat(40)];
            lines.push(format!("File: {}", a["path"].as_str().unwrap_or("")));
            lines.push(format!("Lines: {}", a["lines"]));
            lines.push(format!("Code lines: {}", a["code_lines"]));
            lines.push(format!("Comment lines: {}", a["comment_lines"]));
            lines.push(format!("Blank lines: {}", a["blank_lines"]));
            lines.push(String::new());
            let functions = a["functions"].as_array().cloned().unwrap_or_default();
            lines.push(format!("Functions ({}):", functions.len()));
            for f in functions.iter().take(5) {
                lines.push(format!(
                    "  - {} (line {})",
                    f["name"].as_str().unwrap_or(""),
                    f["line"]
                ));
            }
            lines.push(String::new());
            let classes = a["classes"].as_array().cloned().unwrap_or_default();
            lines.push(format!("Classes ({}):", classes.len()));
            for c in classes.iter().take(5) {
                lines.push(format!(
                    "  - {} (line {})",
                    c["name"].as_str().unwrap_or(""),
                    c["line"]
                ));
            }
            lines.push(String::new());
            let imports = a["imports"].as_array().cloned().unwrap_or_default();
            lines.push(format!("Imports ({}):", imports.len()));
            lines.push(
                imports
                    .iter()
                    .take(10)
                    .map(|i| i.as_str().unwrap_or(""))
                    .collect::<Vec<_>>()
                    .join(", "),
            );
            lines.join("\n")
        }
        "explain_code" => {
            let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
            let start = args.get("start").and_then(|v| v.as_i64()).unwrap_or(1);
            let end = args.get("end").and_then(|v| v.as_i64());
            crate::skills::CodeAnalyzer::new(cwd).explain_code(path, start, end)
        }
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
            match Command::new("grep")
                .args(["-rn", pattern, &full.to_string_lossy()])
                .output()
            {
                Ok(o) => {
                    let s = String::from_utf8_lossy(&o.stdout).to_string();
                    if s.trim().is_empty() {
                        "[no matches]".to_string()
                    } else {
                        s
                    }
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

/// LSP server command for a file, honouring an explicit `server` override.
fn lsp_server_for(path: &str, server: &str) -> (String, Vec<String>) {
    if !server.is_empty() {
        return (server.to_string(), vec![]);
    }
    let ext = std::path::Path::new(path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_lowercase();
    match ext.as_str() {
        "rs" => ("rust-analyzer".to_string(), vec![]),
        "py" => (
            "pyright-langserver".to_string(),
            vec!["--stdio".to_string()],
        ),
        "ts" | "js" | "tsx" | "jsx" => (
            "typescript-language-server".to_string(),
            vec!["--stdio".to_string()],
        ),
        "go" => ("gopls".to_string(), vec![]),
        _ => (String::new(), vec![]),
    }
}

/// Run one LSP operation (`diagnostics`, `definition`, `references`, `hover`).
///
/// Same nested-runtime concern as MCP: the client runs on a dedicated thread
/// with its own Tokio runtime.
fn run_lsp_op(
    op: &str,
    path: &str,
    line: i64,
    column: i64,
    server: &str,
    cwd: &std::path::Path,
) -> String {
    let (prog, sargs) = lsp_server_for(path, server);
    if prog.is_empty() {
        return "ERROR: No LSP server for this file type".to_string();
    }
    if which(&prog).is_none() {
        return format!("ERROR: LSP server '{prog}' not installed");
    }
    let full_path = if std::path::Path::new(path).is_absolute() {
        path.to_string()
    } else {
        cwd.join(path).to_string_lossy().to_string()
    };
    let root = cwd.to_string_lossy().to_string();
    let op = op.to_string();
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
            // Open the document: servers only answer queries for open files.
            let _ = lsp.did_open(&full_path).await;
            // …and wait for indexing to finish (rust-analyzer returns `null` while loading).
            lsp.wait_ready(15000).await;
            let mut res = run_op(&mut lsp, &op, &full_path, line, column).await;
            // The server may not be fully indexed yet: wait, then retry once.
            if matches!(&res, Ok(v) if v.is_null()) {
                lsp.wait_ready(15000).await;
                res = run_op(&mut lsp, &op, &full_path, line, column).await;
            }
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

/// Dispatch one LSP operation against a started manager.
async fn run_op(
    lsp: &mut crate::lsp::LspManager,
    op: &str,
    path: &str,
    line: i64,
    column: i64,
) -> anyhow::Result<Value> {
    match op {
        "definition" => lsp.definition(path, line, column).await,
        "references" => lsp.references(path, line, column).await,
        "hover" => lsp.hover(path, line, column).await,
        _ => lsp.diagnostics(path).await,
    }
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

/// Run git and map trimmed stdout on success, stderr on failure.
fn git_ok(
    cwd: &std::path::Path,
    args: &[&str],
    on_success: impl FnOnce(&str) -> String,
) -> Result<String, String> {
    match Command::new("git").args(args).current_dir(cwd).output() {
        Ok(o) if o.status.success() => Ok(on_success(String::from_utf8_lossy(&o.stdout).trim())),
        Ok(o) => Err(String::from_utf8_lossy(&o.stderr).trim().to_string()),
        Err(e) => Err(e.to_string()),
    }
}

fn string_array(args: &Value, key: &str) -> Vec<String> {
    args.get(key)
        .and_then(|v| v.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|x| x.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_default()
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
        assert!(execute_tool(
            "write_file",
            &serde_json::json!({"path": p.to_str().unwrap(), "content": "hi"}),
            dir.path()
        )
        .contains("Wrote"));
        assert_eq!(
            execute_tool(
                "read_file",
                &serde_json::json!({"path": p.to_str().unwrap()}),
                dir.path()
            ),
            "hi"
        );
        let listing = execute_tool(
            "list_files",
            &serde_json::json!({"path": dir.path().to_str().unwrap()}),
            dir.path(),
        );
        assert!(listing.contains("a.txt"));
    }

    #[test]
    fn run_command_echo() {
        let dir = tempdir().unwrap();
        let out = execute_tool(
            "run_command",
            &serde_json::json!({"command": "echo hello"}),
            dir.path(),
        );
        assert!(out.contains("hello"));
    }

    #[test]
    fn dangerous_command_blocked() {
        let dir = tempdir().unwrap();
        let out = execute_tool(
            "run_command",
            &serde_json::json!({"command": "rm -rf /"}),
            dir.path(),
        );
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
        execute_tool(
            "write_file",
            &serde_json::json!({"path": p.to_str().unwrap(), "content": "changed"}),
            dir.path(),
        );
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

    fn init_repo(dir: &std::path::Path) {
        for args in [
            vec!["init", "-q"],
            vec!["config", "user.email", "t@example.com"],
            vec!["config", "user.name", "Test"],
        ] {
            std::process::Command::new("git")
                .args(&args)
                .current_dir(dir)
                .output()
                .unwrap();
        }
    }

    #[test]
    fn git_workflow_tools() {
        let dir = tempdir().unwrap();
        init_repo(dir.path());
        fs::write(dir.path().join("a.txt"), "hello").unwrap();

        assert_eq!(
            execute_tool(
                "git_stage",
                &serde_json::json!({"files": ["a.txt"]}),
                dir.path()
            ),
            "SUCCESS: Staged 1 file(s)"
        );
        assert_eq!(
            execute_tool("git_stage", &serde_json::json!({"files": []}), dir.path()),
            "ERROR: No files specified"
        );
        assert_eq!(
            execute_tool("git_unstage", &serde_json::json!({}), dir.path()),
            "SUCCESS: Unstaged files"
        );

        // Pre-commit report shows the dirty file before committing.
        let pre = execute_tool("git_pre_commit", &serde_json::json!({}), dir.path());
        assert!(pre.starts_with("Pre-commit checks:"), "got {pre}");
        assert!(pre.contains("Unstaged:") && pre.contains("a.txt"));

        execute_tool(
            "git_stage",
            &serde_json::json!({"files": ["a.txt"]}),
            dir.path(),
        );
        let commit = execute_tool(
            "git_commit",
            &serde_json::json!({"message": "first"}),
            dir.path(),
        );
        assert!(commit.starts_with("SUCCESS: Committed"), "got {commit}");
        assert_eq!(
            execute_tool(
                "git_commit",
                &serde_json::json!({"message": ""}),
                dir.path()
            ),
            "ERROR: No commit message"
        );
        assert_eq!(
            execute_tool("git_pre_commit", &serde_json::json!({}), dir.path()),
            "Nothing to commit (working tree clean)"
        );

        // Branches
        let branches = execute_tool("git_list_branches", &serde_json::json!({}), dir.path());
        assert!(branches.starts_with("Branches:\n"), "got {branches}");
        assert_eq!(
            execute_tool(
                "git_create_branch",
                &serde_json::json!({"name": "feature"}),
                dir.path()
            ),
            "SUCCESS: Created branch 'feature'"
        );
        assert!(
            execute_tool("git_list_branches", &serde_json::json!({}), dir.path())
                .contains("feature")
        );
        assert_eq!(
            execute_tool(
                "git_switch_branch",
                &serde_json::json!({"name": "feature"}),
                dir.path()
            ),
            "SUCCESS: Switched to branch 'feature'"
        );
        // Deleting the current branch must fail (git protects it).
        let err = execute_tool(
            "git_delete_branch",
            &serde_json::json!({"name": "feature"}),
            dir.path(),
        );
        assert!(err.starts_with("ERROR"), "got {err}");
        execute_tool(
            "git_create_branch",
            &serde_json::json!({"name": "tmp"}),
            dir.path(),
        );
        assert_eq!(
            execute_tool(
                "git_delete_branch",
                &serde_json::json!({"name": "tmp", "force": true}),
                dir.path()
            ),
            "SUCCESS: Deleted branch 'tmp'"
        );
        assert!(execute_tool(
            "git_create_branch",
            &serde_json::json!({"name": "other", "checkout": true}),
            dir.path()
        )
        .starts_with("SUCCESS: Created branch 'other' and checked out"));
    }

    #[test]
    fn git_create_pr_without_gh_or_token() {
        if crate::github::which("gh").is_some() {
            return; // gh would try the network: covered by github.rs tests instead.
        }
        std::env::remove_var("GITHUB_TOKEN");
        std::env::remove_var("GH_TOKEN");
        let dir = tempdir().unwrap();
        let out = execute_tool(
            "git_create_pr",
            &serde_json::json!({"title": "t"}),
            dir.path(),
        );
        assert_eq!(
            out,
            "ERROR: gh CLI not found and no GITHUB_TOKEN/GH_TOKEN set."
        );
    }

    #[test]
    fn codegen_tools() {
        let dir = tempdir().unwrap();

        let dockerfile = execute_tool(
            "generate_dockerfile",
            &serde_json::json!({"language": "python"}),
            dir.path(),
        );
        assert!(dockerfile.starts_with("FROM python:3.11-slim"));
        assert_eq!(
            execute_tool(
                "generate_dockerfile",
                &serde_json::json!({"language": "lisp"}),
                dir.path()
            ),
            "# Unsupported language"
        );

        let model = execute_tool(
            "generate_db_model",
            &serde_json::json!({"table": "user", "columns": [{"name": "id", "type": "int"}]}),
            dir.path(),
        );
        assert!(model.starts_with("Generated model for user:\n\nclass User:"));
        assert!(model.contains("id: int = None"));

        let compose = execute_tool(
            "generate_docker_compose",
            &serde_json::json!({"services": [{"name": "web", "image": "nginx"}]}),
            dir.path(),
        );
        assert!(compose.contains("  web:\n    image: nginx"));

        // refactor_code
        fs::write(dir.path().join("m.py"), "def foo(a):\n    return a\n").unwrap();
        assert_eq!(
            execute_tool(
                "refactor_code",
                &serde_json::json!({"path": "m.py", "function": "foo", "style": "async"}),
                dir.path()
            ),
            "SUCCESS: Refactored foo with async style"
        );
        assert!(fs::read_to_string(dir.path().join("m.py"))
            .unwrap()
            .contains("async def foo"));
        assert!(execute_tool(
            "refactor_code",
            &serde_json::json!({"path": "m.py", "function": "missing"}),
            dir.path()
        )
        .starts_with("ERROR: Function not found"));

        // Docs
        let readme = execute_tool(
            "generate_docs",
            &serde_json::json!({"type": "readme"}),
            dir.path(),
        );
        assert!(readme.starts_with("# Project"), "got {readme}");
        let api = execute_tool(
            "generate_docs",
            &serde_json::json!({"type": "api", "path": "m.py"}),
            dir.path(),
        );
        assert!(api.contains("## foo"));
        assert_eq!(
            execute_tool(
                "generate_docs",
                &serde_json::json!({"type": "api"}),
                dir.path()
            ),
            "ERROR: Invalid doc type or missing path"
        );

        // Profiler
        let profile = execute_tool(
            "profile_code",
            &serde_json::json!({"path": "m.py"}),
            dir.path(),
        );
        assert!(profile.starts_with("Code Profile\n="), "got {profile}");
        assert!(profile.contains("Lines: 3"), "got {profile}");
        assert!(profile.contains("Functions: 1"));
        assert_eq!(
            execute_tool(
                "profile_code",
                &serde_json::json!({"path": "nope.py"}),
                dir.path()
            ),
            "File not found"
        );
        let suggestions = execute_tool(
            "optimize_code",
            &serde_json::json!({"path": "m.py"}),
            dir.path(),
        );
        assert!(suggestions.starts_with("Optimization Suggestions\n="));

        // API client
        fs::write(
            dir.path().join("spec.json"),
            r#"{"servers":[{"url":"https://api.example.com"}],"paths":{"/things":{"get":{}}}}"#,
        )
        .unwrap();
        let client = execute_tool(
            "generate_api_client",
            &serde_json::json!({"spec": "spec.json"}),
            dir.path(),
        );
        assert!(
            client.contains("def get_things(self, **kwargs):"),
            "got {client}"
        );
    }

    #[test]
    fn edit_file_replaces_first_occurrence() {
        let dir = tempdir().unwrap();
        let p = dir.path().join("doc.txt");
        fs::write(&p, "alpha beta alpha\n").unwrap();
        let out = execute_tool(
            "edit_file",
            &serde_json::json!({"path": "doc.txt", "old_string": "alpha", "new_string": "ALPHA"}),
            dir.path(),
        );
        assert!(out.starts_with("SUCCESS: Edited"), "got {out}");
        assert_eq!(fs::read_to_string(p).unwrap(), "ALPHA beta alpha\n");
    }

    #[test]
    fn edit_file_error_paths() {
        let dir = tempdir().unwrap();
        fs::write(dir.path().join("doc.txt"), "hello\n").unwrap();
        assert_eq!(
            execute_tool(
                "edit_file",
                &serde_json::json!({"path": "missing.txt", "old_string": "a", "new_string": "b"}),
                dir.path()
            ),
            format!(
                "ERROR: File not found: {}",
                dir.path().join("missing.txt").display()
            )
        );
        assert_eq!(
            execute_tool(
                "edit_file",
                &serde_json::json!({"path": "doc.txt", "old_string": "nope", "new_string": "b"}),
                dir.path()
            ),
            "ERROR: String not found in file. Use read_file to see content."
        );
    }

    #[test]
    fn apply_patch_tool_applies_and_previews() {
        let dir = tempdir().unwrap();
        fs::write(dir.path().join("a.txt"), "one\ntwo\n").unwrap();
        let patch = "--- a/a.txt\n+++ b/a.txt\n@@ -1,2 +1,2 @@\n one\n-two\n+TWO\n";

        let preview = execute_tool(
            "apply_patch",
            &serde_json::json!({"patch": patch, "dry_run": true}),
            dir.path(),
        );
        assert!(
            preview.starts_with("PREVIEW: Patch would apply (1 files, +1/-1)"),
            "got {preview}"
        );
        assert_eq!(
            fs::read_to_string(dir.path().join("a.txt")).unwrap(),
            "one\ntwo\n"
        );

        let applied = execute_tool(
            "apply_patch",
            &serde_json::json!({"patch": patch}),
            dir.path(),
        );
        assert!(
            applied.starts_with("SUCCESS: Patch applied (1 files, +1/-1)"),
            "got {applied}"
        );
        assert_eq!(
            fs::read_to_string(dir.path().join("a.txt")).unwrap(),
            "one\nTWO\n"
        );
    }

    #[test]
    fn apply_patch_tool_reports_engine_errors() {
        let dir = tempdir().unwrap();
        let out = execute_tool(
            "apply_patch",
            &serde_json::json!({"patch": "*** Begin Patch\n*** Add File: ../evil.txt\n+x\n*** End Patch\n"}),
            dir.path(),
        );
        assert!(
            out.starts_with("ERROR: path_traversal: '..' is not allowed"),
            "got {out}"
        );
        assert!(out.contains("evil.txt"), "got {out}");
    }
}
