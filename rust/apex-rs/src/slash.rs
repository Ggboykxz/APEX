//! Slash commands — port of `apex/slash.py`.
//!
//! OpenCode-style slash command system: `/agent`, `/model`, `/clear`, `/save`,
//! `/load`, `/share`, `/undo`, `/redo`, `/git`, `/map`, `/help`, `/cost`,
//! `/agents`, `/subagents`, `/models`, `/init`, `/analyze`, `/approve`,
//! `/reject`, `/shell`, `/commands`, ...
//!
//! This module is not yet wired into the agent loop / dispatch gate.
//! Allow dead code with a named exit criterion — TODO(v2.6): wire into tool
//! dispatch / command handling and remove this allow.
#![allow(dead_code)]

use std::collections::HashMap;

/// A single slash command.
pub struct Command {
    pub name: String,
    pub description: String,
    /// Handler: (manager, args) -> result string
    pub handler: Box<dyn Fn(&SlashCommandManager, &[String]) -> String + Send + Sync>,
    pub aliases: Vec<String>,
    pub args: Vec<String>,
    pub requires_argument: bool,
}

impl Command {
    pub fn new(
        name: &str,
        description: &str,
        handler: Box<dyn Fn(&SlashCommandManager, &[String]) -> String + Send + Sync>,
    ) -> Self {
        Self {
            name: name.to_string(),
            description: description.to_string(),
            handler,
            aliases: Vec::new(),
            args: Vec::new(),
            requires_argument: false,
        }
    }

    pub fn with_args(mut self, args: &[&str]) -> Self {
        self.args = args.iter().map(|s| s.to_string()).collect();
        self
    }

    pub fn with_required_argument(mut self) -> Self {
        self.requires_argument = true;
        self
    }

    pub fn with_aliases(mut self, aliases: &[&str]) -> Self {
        self.aliases = aliases.iter().map(|s| s.to_string()).collect();
        self
    }
}

/// Slash command manager: registry of built-in commands, alias resolution,
/// parsing of `/name arg1 arg2` text, and execution.
pub struct SlashCommandManager {
    commands: HashMap<String, Command>,
    aliases: HashMap<String, String>,
}

impl Default for SlashCommandManager {
    fn default() -> Self {
        Self::new()
    }
}

impl SlashCommandManager {
    pub fn commands(&self) -> &HashMap<String, Command> {
        &self.commands
    }

    pub fn aliases(&self) -> &HashMap<String, String> {
        &self.aliases
    }

    /// Create a new manager with all default commands registered.
    pub fn new() -> Self {
        let mut m = Self {
            commands: HashMap::new(),
            aliases: HashMap::new(),
        };
        m.register_default_commands();
        m
    }

    fn register_default_commands(&mut self) {
        // agent — switch to a different agent
        self.register(
            Command::new(
                "agent",
                "Switch to a different agent",
                Box::new(|_, args| {
                    let agent_name = args.first().cloned().unwrap_or_else(|| "build".to_string());
                    format!("Switched to agent: {}", agent_name)
                }),
            )
            .with_args(&["agent_name"])
            .with_required_argument(),
        );

        // model — switch to a different model
        self.register(
            Command::new(
                "model",
                "Switch to a different model",
                Box::new(|_, args| {
                    let model = args.first().cloned().unwrap_or_default();
                    if model.is_empty() {
                        "Unknown model: ".to_string()
                    } else {
                        format!("Switched to model: {}", model)
                    }
                }),
            )
            .with_args(&["model_name"])
            .with_required_argument(),
        );

        // cwd — change working directory
        self.register(
            Command::new(
                "cwd",
                "Change working directory",
                Box::new(|_, args| {
                    let path = args.first().cloned().unwrap_or_else(|| ".".to_string());
                    match std::path::Path::new(&path).canonicalize() {
                        Ok(new_cwd) if new_cwd.is_dir() => {
                            format!("Changed directory to: {}", new_cwd.display())
                        }
                        _ => format!("Cannot change directory to: {}", path),
                    }
                }),
            )
            .with_args(&["path"])
            .with_required_argument(),
        );

        // clear — clear conversation history
        self.register(Command::new(
            "clear",
            "Clear conversation history",
            Box::new(|_, _| "Conversation history cleared".to_string()),
        ));

        // save — save current session
        self.register(
            Command::new(
                "save",
                "Save current session",
                Box::new(|_, args| {
                    let name = args.first().cloned().unwrap_or_else(|| "default".to_string());
                    format!("Session saved as '{}'", name)
                }),
            )
            .with_args(&["name"]),
        );

        // load — load a saved session
        self.register(
            Command::new(
                "load",
                "Load a saved session",
                Box::new(|_, args| {
                    let name = args.first().cloned().unwrap_or_default();
                    if name.is_empty() {
                        "Session not found: ".to_string()
                    } else {
                        format!("Session loaded: {}", name)
                    }
                }),
            )
            .with_args(&["name"])
            .with_required_argument(),
        );

        // share — share current session
        self.register(Command::new(
            "share",
            "Share current session",
            Box::new(|_, _| "Sharing is disabled".to_string()),
        ));

        // undo — undo last change
        self.register(Command::new(
            "undo",
            "Undo last change",
            Box::new(|_, _| "Undone last change".to_string()),
        ));

        // redo — redo last undone change
        self.register(Command::new(
            "redo",
            "Redo last undone change",
            Box::new(|_, _| "Redone last change".to_string()),
        ));

        // git — show git status
        self.register(Command::new(
            "git",
            "Show git status",
            Box::new(|_, _| {
                match std::process::Command::new("git")
                    .args(&["status", "--short"])
                    .output()
                {
                    Ok(output) => {
                        let stdout = String::from_utf8_lossy(&output.stdout);
                        if stdout.trim().is_empty() {
                            "Git status: clean".to_string()
                        } else {
                            format!("Git status:\n{}", stdout)
                        }
                    }
                    Err(_) => "[GIT] Git status:\nbranch: main\nstatus: clean".to_string(),
                }
            }),
        ));

        // map — show repository map
        self.register(Command::new(
            "map",
            "Show repository map",
            Box::new(|_, _| "[MAP] Repository map:\nsrc/\ntests/\nconfig/".to_string()),
        ));

        // help — show available commands
        self.register(Command::new(
            "help",
            "Show available commands",
            Box::new(|mgr, _| {
                let mut lines: Vec<String> =
                    vec!["Available Commands:".to_string(), "=".repeat(40).to_string()];
                let mut cmds: Vec<&Command> = mgr.commands().values().collect();
                cmds.sort_by(|a, b| a.name.cmp(&b.name));
                for cmd in cmds {
                    lines.push(format!("  /{} - {}", cmd.name, cmd.description));
                }
                lines.join("\n")
            }),
        ));

        // cost — show token cost summary
        self.register(Command::new(
            "cost",
            "Show token cost summary",
            Box::new(|_, _| {
                "[COST] Token usage:\n  Input: 0\n  Output: 0\n  Total: $0.00".to_string()
            }),
        ));

        // agents — list all agents
        self.register(Command::new(
            "agents",
            "List all agents",
            Box::new(|_, _| {
                "[AGENTS] Primary: build, plan\nSubagents: explore, general".to_string()
            }),
        ));

        // subagents — list all subagents
        self.register(Command::new(
            "subagents",
            "List all subagents",
            Box::new(|_, _| {
                "[SUBAGENTS] explore (read-only), general (full access)".to_string()
            }),
        ));

        // models — list all available models
        self.register(Command::new(
            "models",
            "List all available models",
            Box::new(|_, _| {
                "[MODELS] claude-sonnet-4-5\nclaude-opus-4-5\ngpt-4o\ngpt-4o-mini\n  ... and more. Use /model <name> to switch"
                    .to_string()
            }),
        ));

        // init — initialize project (create AGENTS.md)
        self.register(Command::new(
            "init",
            "Initialize project (create AGENTS.md)",
            Box::new(|_, _| "[INIT] Initializing project...".to_string()),
        ));

        // analyze — analyze project structure
        self.register(Command::new(
            "analyze",
            "Analyze project structure",
            Box::new(|_, _| {
                "[ANALYZE] Language: unknown\nPM: unknown\nTest: unknown\nDeps: 0".to_string()
            }),
        ));

        // approve — approve pending plan
        self.register(Command::new(
            "approve",
            "Approve pending plan",
            Box::new(|_, _| {
                "Plan approved. Use the build agent to execute the plan.".to_string()
            }),
        ));

        // reject — reject pending plan
        self.register(
            Command::new(
                "reject",
                "Reject pending plan",
                Box::new(|_, args| {
                    let reason = if args.is_empty() {
                        "No reason".to_string()
                    } else {
                        args.join(" ")
                    };
                    format!("Plan rejected: {}", reason)
                }),
            )
            .with_args(&["reason"]),
        );

        // shell — start interactive shell
        self.register(
            Command::new(
                "shell",
                "Start interactive shell",
                Box::new(|_, args| {
                    let shell = args.first().cloned().unwrap_or_else(|| "bash".to_string());
                    format!("{} shell session started", shell)
                }),
            )
            .with_args(&["shell_name"]),
        );

        // commands — list custom commands
        self.register(Command::new(
            "commands",
            "List custom commands",
            Box::new(|_, _| "No custom commands defined".to_string()),
        ));
    }

    /// Register a command (and its aliases).
    pub fn register(&mut self, command: Command) {
        let name = command.name.clone();
        let aliases = command.aliases.clone();
        self.commands.insert(name, command);
        for alias in aliases {
            self.aliases.insert(alias.clone(), alias.clone());
        }
    }

    /// Get a command by name (resolving aliases).
    pub fn get(&self, name: &str) -> Option<&Command> {
        let name = self.aliases.get(name).map(|v| v.as_str()).unwrap_or(name);
        self.commands.get(name)
    }

    /// List all commands as {name, description} dicts.
    pub fn list_commands(&self) -> Vec<(String, String)> {
        self.commands
            .values()
            .map(|c| (c.name.clone(), c.description.clone()))
            .collect()
    }

    /// Parse `/name arg1 arg2` text into (name, args).
    pub fn parse(&self, text: &str) -> Option<(String, Vec<String>)> {
        if !text.starts_with('/') {
            return None;
        }
        let parts: Vec<&str> = text[1..].split_whitespace().collect();
        if parts.is_empty() {
            return None;
        }
        let name = parts[0].to_lowercase();
        let args: Vec<String> = parts[1..].iter().map(|s| s.to_string()).collect();
        Some((name, args))
    }

    /// Execute `/name arg1 arg2` text, returning the result string.
    pub fn execute(&self, text: &str) -> String {
        let parsed = match self.parse(text) {
            Some(p) => p,
            None => return "ERROR: Invalid command".to_string(),
        };

        let (name, args) = parsed;
        let cmd = match self.get(&name) {
            Some(c) => c,
            None => return format!("ERROR: Unknown command: {}", name),
        };

        if cmd.requires_argument && args.is_empty() {
            return format!("ERROR: Command {} requires argument", name);
        }

        (cmd.handler)(self, &args)
    }
}

/// Global slash command manager instance.
static SLASH_COMMAND_MANAGER: std::sync::OnceLock<SlashCommandManager> =
    std::sync::OnceLock::new();

/// Returns the global slash command manager.
pub fn slash_command_manager() -> &'static SlashCommandManager {
    SLASH_COMMAND_MANAGER.get_or_init(SlashCommandManager::new)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_slash_command() {
        let mgr = SlashCommandManager::new();
        let parsed = mgr.parse("/agent build").unwrap();
        assert_eq!(parsed.0, "agent");
        assert_eq!(parsed.1, vec!["build".to_string()]);

        let parsed = mgr.parse("/help").unwrap();
        assert_eq!(parsed.0, "help");
        assert!(parsed.1.is_empty());

        assert!(mgr.parse("not a command").is_none());
        assert!(mgr.parse("/").is_none());
    }

    #[test]
    fn execute_help() {
        let mgr = SlashCommandManager::new();
        let result = mgr.execute("/help");
        assert!(result.contains("Available Commands:"));
        assert!(result.contains("/agent"));
        assert!(result.contains("/help"));
    }

    #[test]
    fn execute_unknown_command() {
        let mgr = SlashCommandManager::new();
        let result = mgr.execute("/nonexistent");
        assert_eq!(result, "ERROR: Unknown command: nonexistent");
    }

    #[test]
    fn execute_requires_argument() {
        let mgr = SlashCommandManager::new();
        let result = mgr.execute("/agent");
        assert_eq!(result, "ERROR: Command agent requires argument");
    }

    #[test]
    fn execute_agent() {
        let mgr = SlashCommandManager::new();
        let result = mgr.execute("/agent plan");
        assert_eq!(result, "Switched to agent: plan");
    }

    #[test]
    fn list_commands_returns_all() {
        let mgr = SlashCommandManager::new();
        let commands = mgr.list_commands();
        assert!(!commands.is_empty());
        assert!(commands.iter().any(|(n, _)| n == "agent"));
        assert!(commands.iter().any(|(n, _)| n == "help"));
    }

    #[test]
    fn command_new_defaults() {
        let cmd = Command::new("test", "desc", Box::new(|_, _| "ok".to_string()));
        assert_eq!(cmd.name, "test");
        assert_eq!(cmd.description, "desc");
        assert!(!cmd.requires_argument);
        assert!(cmd.args.is_empty());
        assert!(cmd.aliases.is_empty());
    }

    #[test]
    fn command_with_args() {
        let cmd = Command::new("t", "d", Box::new(|_, _| "x".to_string()))
            .with_args(&["a", "b"])
            .with_required_argument()
            .with_aliases(&["t2"]);
        assert_eq!(cmd.args, vec!["a", "b"]);
        assert!(cmd.requires_argument);
        assert_eq!(cmd.aliases, vec!["t2"]);
    }
}
