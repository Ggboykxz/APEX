//! Custom command manager — port of `apex/commands_manager.py`.
//!
//! Markdown commands with YAML frontmatter from `~/.config/apex/commands/`
//! and `<cwd>/.apex/commands/`, plus the four built-ins (`/test`, `/review`,
//! `/commit`, `/docs`). Backs `GET /api/v1/commands` and
//! `POST /api/v1/commands/execute`.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::time::Duration;

use regex::Regex;

/// One custom command (Python's `CommandConfig`).
#[derive(Debug, Clone, Default)]
pub struct CommandConfig {
    pub name: String,
    pub template: String,
    pub description: String,
    pub agent: Option<String>,
    pub model: Option<String>,
    pub subtask: bool,
}

/// Python's `_BUILTIN_COMMANDS` (overridable by user commands).
fn builtin_commands() -> Vec<CommandConfig> {
    vec![
        CommandConfig {
            name: "test".into(),
            template: "Run the full test suite for this project. Show the results including any failures or errors. If there are failures, analyze them and suggest fixes. Fix any failing tests.".into(),
            description: "Run tests".into(),
            agent: Some("build".into()),
            model: None,
            subtask: false,
        },
        CommandConfig {
            name: "review".into(),
            template: "Review the current uncommitted changes in this project. Analyze the diff, provide feedback on code quality, potential bugs, security issues, and suggest improvements.".into(),
            description: "Review current changes".into(),
            agent: Some("reviewer".into()),
            model: None,
            subtask: false,
        },
        CommandConfig {
            name: "commit".into(),
            template: "Analyze the current changes in the repository. Create a concise, well-structured commit message summarizing the changes. Stage all modified files and commit with the generated message.".into(),
            description: "Commit with AI message".into(),
            agent: Some("build".into()),
            model: None,
            subtask: false,
        },
        CommandConfig {
            name: "docs".into(),
            template: "Generate documentation for the recent changes and the relevant parts of the codebase. Focus on APIs, public interfaces, and any new functionality.".into(),
            description: "Generate documentation".into(),
            agent: Some("plan".into()),
            model: None,
            subtask: false,
        },
    ]
}

/// YAML frontmatter parser (port of `_parse_yaml_frontmatter`, stdlib only).
/// Returns the scalar values and the body. Booleans are normalised to
/// `"true"`/`"false"`, empty and `"null"` values are dropped.
fn parse_frontmatter(text: &str) -> (HashMap<String, String>, String) {
    let mut result: HashMap<String, String> = HashMap::new();
    let lines: Vec<&str> = text.split('\n').collect();
    let Some(first) = lines.first() else {
        return (result, text.to_string());
    };
    if first.trim() != "---" {
        return (result, text.to_string());
    }
    let mut end: Option<usize> = None;
    for (i, line) in lines.iter().enumerate().skip(1) {
        if line.trim() == "---" {
            end = Some(i);
            break;
        }
    }
    let Some(end) = end else {
        return (result, text.to_string());
    };
    for line in &lines[1..end] {
        let stripped = line.trim();
        if stripped.is_empty() || stripped.starts_with('#') {
            continue;
        }
        let Some(colon) = stripped.find(':') else {
            continue;
        };
        let key = stripped[..colon].trim();
        let mut val = stripped[colon + 1..].trim().to_string();
        let lower = val.to_lowercase();
        if lower == "true" || lower == "false" {
            val = lower;
        } else if val.is_empty() || val == "null" {
            continue;
        }
        if !key.is_empty() {
            result.insert(key.to_string(), val);
        }
    }
    let body = lines[end + 1..].join("\n").trim().to_string();
    (result, body)
}

/// Run a template `!command` (port of `_exec_shell`): guarded by the shell
/// security analyzer, 30 s timeout, `stdout` else `stderr`, empty on
/// timeout or spawn failure.
fn exec_inline(cmd: &str, project_dir: &Path) -> String {
    use crate::shell_security::CommandCategory;
    let analysis = crate::shell_security::SHELL_ANALYZER.analyze(cmd);
    if analysis.category == CommandCategory::Dangerous {
        return format!("[blocked by security: {}]", analysis.warnings.join("; "));
    }
    if analysis.requires_confirmation
        && !matches!(
            analysis.category,
            CommandCategory::WorkingDir | CommandCategory::FileRead | CommandCategory::Build
        )
    {
        return format!(
            "[blocked by security: {} requires confirmation]",
            analysis.category.value()
        );
    }
    let dir = project_dir.to_path_buf();
    let cmd = cmd.to_string();
    let (tx, rx) = std::sync::mpsc::channel();
    let _ = std::thread::spawn(move || {
        let out = crate::tools::shell_command(&cmd).current_dir(&dir).output();
        let _ = tx.send(out);
    });
    match rx.recv_timeout(Duration::from_secs(30)) {
        Ok(Ok(o)) => {
            let stdout = String::from_utf8_lossy(&o.stdout).trim().to_string();
            if !stdout.is_empty() {
                stdout
            } else {
                String::from_utf8_lossy(&o.stderr).trim().to_string()
            }
        }
        // Python returns "" on TimeoutExpired / spawn errors.
        // Divergence: a timed-out child is not killed (Python's
        // subprocess.run(timeout=) kills it) — recorded in PARITY.md.
        _ => String::new(),
    }
}

/// Render a command template (port of `_render_template`):
/// `$ARGUMENTS`, `$1..$N`, `!command`, `@file`.
pub fn render_template(template: &str, args: &[String], project_dir: &Path) -> String {
    let mut result = template.to_string();
    let joined = args.join(" ");
    result = result.replace("$ARGUMENTS", &joined);
    for (idx, arg) in args.iter().enumerate() {
        result = result.replace(&format!("${}", idx + 1), arg);
    }

    let shell_re = Regex::new(r"!([^\n]+)").expect("static regex");
    result = shell_re
        .replace_all(&result, |caps: &regex::Captures| {
            exec_inline(caps.get(1).unwrap().as_str().trim(), project_dir)
        })
        .to_string();

    let file_re = Regex::new(r"@(\S+)").expect("static regex");
    result = file_re
        .replace_all(&result, |caps: &regex::Captures| {
            let raw = caps.get(1).unwrap().as_str().trim();
            let p = Path::new(raw);
            let full = if p.is_absolute() {
                p.to_path_buf()
            } else {
                project_dir.join(p)
            };
            if !full.is_file() {
                return String::new();
            }
            // Python reads with `errors="replace"`; lossy UTF-8 matches.
            let bytes = std::fs::read(&full).unwrap_or_default();
            String::from_utf8_lossy(&bytes).into_owned()
        })
        .to_string();

    result
}

/// Python's `CustomCommandManager`.
#[derive(Debug, Default)]
pub struct CustomCommandManager {
    commands: HashMap<String, CommandConfig>,
}

impl CustomCommandManager {
    pub fn new() -> Self {
        let mut manager = Self::default();
        manager.load_builtins();
        manager
    }

    fn load_builtins(&mut self) {
        self.commands.clear();
        for cmd in builtin_commands() {
            self.commands.insert(cmd.name.clone(), cmd);
        }
    }

    /// Python's `load_all(project_dir)`: built-ins, then
    /// `~/.config/apex/commands/`, then `<project>/.apex/commands/`
    /// (sorted `*.md`), then the config `command` section — which Rust's
    /// flat `Config` has no equivalent of (recorded divergence).
    pub fn load_all(&mut self, project_dir: Option<&Path>) {
        self.load_builtins();

        if let Some(home) = crate::config::home_dir() {
            let global_dir = home.join(".config").join("apex").join("commands");
            if global_dir.is_dir() {
                self.load_from_dir(&global_dir);
            }
        }

        let resolved = match project_dir {
            Some(p) => p.to_path_buf(),
            None => std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
        };
        let project_cmds = resolved.join(".apex").join("commands");
        if project_cmds.is_dir() {
            self.load_from_dir(&project_cmds);
        }
    }

    fn load_from_dir(&mut self, directory: &Path) {
        let mut files: Vec<PathBuf> = std::fs::read_dir(directory)
            .into_iter()
            .flatten()
            .flatten()
            .map(|e| e.path())
            .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("md"))
            .collect();
        files.sort();
        for md_file in files {
            let Ok(content) = std::fs::read_to_string(&md_file) else {
                continue;
            };
            let (frontmatter, body) = parse_frontmatter(&content);
            let name = md_file
                .file_stem()
                .and_then(|s| s.to_str())
                .unwrap_or_default()
                .to_string();
            if name.is_empty() {
                continue;
            }
            self.commands.insert(
                name.clone(),
                CommandConfig {
                    name,
                    template: if body.is_empty() { content } else { body },
                    description: frontmatter.get("description").cloned().unwrap_or_default(),
                    agent: frontmatter.get("agent").cloned(),
                    model: frontmatter.get("model").cloned(),
                    subtask: frontmatter
                        .get("subtask")
                        .map(|v| v == "true")
                        .unwrap_or(false),
                },
            );
        }
    }

    pub fn get(&self, name: &str) -> Option<&CommandConfig> {
        self.commands.get(name)
    }

    /// Python's `list()` — insertion-free map order is not preserved here;
    /// callers that need a stable order sort by name (the HTTP route does).
    pub fn list(&self) -> Vec<&CommandConfig> {
        self.commands.values().collect()
    }

    /// Render the command's prompt (Python's `execute` minus the agent call,
    /// which the HTTP handler performs on the shared agent).
    pub fn render(&self, name: &str, args: &[String], project_dir: &Path) -> Option<String> {
        let cmd = self.get(name)?;
        Some(render_template(&cmd.template, args, project_dir))
    }
}

/// Python's module-level `commands_manager` singleton is recreated per
/// request (Python's `load_all` refreshes it on every call anyway), so the
/// Rust port builds a fresh manager instead of holding a global.
pub fn command_manager(cwd: &Path) -> CustomCommandManager {
    let mut manager = CustomCommandManager::new();
    manager.load_all(Some(cwd));
    manager
}
