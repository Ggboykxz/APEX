//! Agent registry — port of `apex/agents.py`.
//!
//! Provides the 11 built-in agents, markdown agent loading from
//! `.apex/agents/*.md` (project) and `~/.config/apex/agents/*.md` (global),
//! per-agent permissions with glob patterns, and merge rules for global
//! config / agent / environment permission overrides.

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};
use std::fs;
use std::path::{Path, PathBuf};

// ────────────────────────────────────────────────────────────
// PermissionLevel
// ────────────────────────────────────────────────────────────

/// Port of the permission values used by agents (`allow`/`ask`/`deny`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum PermissionLevel {
    Allow,
    Ask,
    Deny,
}

impl PermissionLevel {
    pub fn as_str(&self) -> &'static str {
        match self {
            PermissionLevel::Allow => "allow",
            PermissionLevel::Ask => "ask",
            PermissionLevel::Deny => "deny",
        }
    }

    #[allow(dead_code)] // alias for `as_str`; kept for API compat with `permission` module — TODO(v2.6): wire into dispatch gate or remove
    pub fn value(&self) -> &'static str {
        self.as_str()
    }
}

impl std::fmt::Display for PermissionLevel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

impl std::str::FromStr for PermissionLevel {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.trim().to_lowercase().as_str() {
            "allow" => Ok(PermissionLevel::Allow),
            "ask" => Ok(PermissionLevel::Ask),
            "deny" => Ok(PermissionLevel::Deny),
            other => Err(format!("unknown permission level: {other}")),
        }
    }
}

/// Compatibility alias for callers that use the permission module's name.
#[allow(dead_code)] // kept for API parity with `permission::PermissionAction` — TODO(v2.6): wire into dispatch gate or remove
pub type PermissionAction = PermissionLevel;

// ────────────────────────────────────────────────────────────
// AgentMode
// ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AgentMode {
    Primary,
    Subagent,
    System,
    All,
}

impl AgentMode {
    pub fn as_str(&self) -> &'static str {
        match self {
            AgentMode::Primary => "primary",
            AgentMode::Subagent => "subagent",
            AgentMode::System => "system",
            AgentMode::All => "all",
        }
    }

    pub fn parse(s: &str) -> Self {
        match s.trim().to_lowercase().as_str() {
            "primary" => AgentMode::Primary,
            "subagent" => AgentMode::Subagent,
            "system" => AgentMode::System,
            "all" => AgentMode::All,
            _ => AgentMode::Subagent,
        }
    }

    #[allow(dead_code)] // used by permission dispatch gate — TODO(v2.6): wire into tool dispatch
    pub fn is_primary(&self) -> bool {
        matches!(self, AgentMode::Primary | AgentMode::All)
    }

    #[allow(dead_code)] // used by permission dispatch gate — TODO(v2.6): wire into tool dispatch
    pub fn is_subagent(&self) -> bool {
        matches!(self, AgentMode::Subagent | AgentMode::All)
    }
}

impl std::fmt::Display for AgentMode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

impl std::str::FromStr for AgentMode {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Ok(AgentMode::parse(s))
    }
}

/// Compatibility alias for callers that expect `Mode`.
#[allow(dead_code)] // kept for API parity — TODO(v2.6): wire into agent mode parsing or remove
pub type Mode = AgentMode;

// ────────────────────────────────────────────────────────────
// Agent
// ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Agent {
    pub name: String,
    pub description: String,
    pub mode: AgentMode,
    pub model: Option<String>,
    pub temperature: Option<f64>,
    pub max_steps: Option<u32>,
    pub permission: HashMap<String, PermissionLevel>,
    pub color: Option<String>,
    pub hidden: bool,
    pub disabled: bool,
    pub is_builtin: bool,
}

impl Agent {
    #[allow(dead_code)] // used by CLI listing/dispatch — TODO(v2.6): wire into tool dispatch
    pub fn is_hidden(&self) -> bool {
        self.hidden
    }

    #[allow(dead_code)] // used by CLI listing/dispatch — TODO(v2.6): wire into tool dispatch
    pub fn is_primary(&self) -> bool {
        self.mode.is_primary()
    }

    #[allow(dead_code)] // used by CLI listing/dispatch — TODO(v2.6): wire into tool dispatch
    pub fn is_subagent(&self) -> bool {
        self.mode.is_subagent()
    }
}

// ────────────────────────────────────────────────────────────
// AgentRegistry
// ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Default)]
pub struct AgentRegistry {
    pub agents: BTreeMap<String, Agent>,
}

impl AgentRegistry {
    pub fn new() -> Self {
        let mut registry = Self::default();
        for (name, agent) in builtin_agents() {
            registry.agents.insert(name, agent);
        }
        registry
    }

    pub fn get(&self, name: &str) -> Option<&Agent> {
        self.agents.get(name)
    }

    #[allow(dead_code)] // used by mutation API — TODO(v2.6): wire into CLI delete or remove
    pub fn get_mut(&mut self, name: &str) -> Option<&mut Agent> {
        self.agents.get_mut(name)
    }

    #[allow(dead_code)] // used to register custom agents — TODO(v2.6): wire into CLI create/load
    pub fn register(&mut self, agent: Agent) {
        self.agents.insert(agent.name.clone(), agent);
    }

    pub fn list(&self) -> Vec<&Agent> {
        self.agents.values().collect()
    }

    #[allow(dead_code)] // convenience alias for `list` — TODO(v2.6): wire into CLI or remove
    pub fn list_agents(&self) -> Vec<&Agent> {
        self.list()
    }

    #[allow(dead_code)] // used by CLI/validation — TODO(v2.6): wire into agent name validation
    pub fn builtin_names() -> Vec<&'static str> {
        vec![
            "build",
            "plan",
            "planner",
            "reviewer",
            "shell",
            "general",
            "explore",
            "scout",
            "compaction",
            "title",
            "summary",
        ]
    }

    // ── Markdown loading ────────────────────────────────────

    #[allow(dead_code)] // convenience wrapper — TODO(v2.6): wire into CLI or remove in favor of `load_markdown_agents_from`
    pub fn load_markdown_agents(&mut self) {
        if let Ok(cwd) = std::env::current_dir() {
            self.load_markdown_agents_from(&cwd);
        }
    }

    pub fn load_markdown_agents_from(&mut self, cwd: &Path) {
        let mut dirs: Vec<PathBuf> = Vec::new();
        if let Some(home) = crate::config::home_dir() {
            dirs.push(home.join(".config").join("apex").join("agents"));
        }
        dirs.push(cwd.join(".apex").join("agents"));

        for dir in dirs {
            if !dir.is_dir() {
                continue;
            }
            let mut files: Vec<PathBuf> = fs::read_dir(&dir)
                .ok()
                .into_iter()
                .flatten()
                .flatten()
                .map(|e| e.path())
                .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("md"))
                .collect();
            files.sort();
            for path in files {
                if let Some(agent) = Self::parse_markdown_agent(&path) {
                    self.agents.insert(agent.name.clone(), agent);
                }
            }
        }
    }

    pub fn parse_markdown_agent(path: &Path) -> Option<Agent> {
        let text = fs::read_to_string(path).ok()?;
        let trimmed = text.trim_start();
        let after_open = trimmed.strip_prefix("---")?;
        let close_idx = after_open.find("\n---")?;
        let front = &after_open[..close_idx];
        let body = after_open[close_idx + 4..].trim().to_string();

        let name = path.file_stem()?.to_string_lossy().to_string();
        let mut description = format!("Custom agent: {name}");
        let mut mode = AgentMode::Subagent;
        let mut model: Option<String> = None;
        let mut temperature: Option<f64> = None;
        let mut max_steps: Option<u32> = None;
        let mut hidden = false;
        let mut disabled = false;
        let mut color: Option<String> = Some("cyan".to_string());
        let mut permission: HashMap<String, PermissionLevel> = HashMap::new();

        let lines: Vec<&str> = front.lines().collect();
        let mut i = 0usize;
        while i < lines.len() {
            let raw = lines[i];
            let t = raw.trim();
            if t.is_empty() {
                i += 1;
                continue;
            }
            // Top-level keys only (no leading whitespace).
            if raw.starts_with(' ') || raw.starts_with('\t') {
                i += 1;
                continue;
            }
            let Some((key, value)) = t.split_once(':') else {
                i += 1;
                continue;
            };
            let key = key.trim();
            let value = value.trim();
            match key {
                "description" => {
                    if !value.is_empty() {
                        description = value.to_string();
                    }
                }
                "mode" => {
                    if !value.is_empty() {
                        mode = AgentMode::parse(value);
                    }
                }
                "model" => {
                    if !value.is_empty() {
                        model = Some(value.to_string());
                    } else {
                        model = None;
                    }
                }
                "temperature" => {
                    temperature = value.parse::<f64>().ok();
                }
                "max_steps" => {
                    max_steps = value.parse::<u32>().ok();
                }
                "hidden" => {
                    hidden = parse_bool(value);
                }
                "disabled" => {
                    disabled = parse_bool(value);
                }
                "color" => {
                    if !value.is_empty() {
                        color = Some(value.to_string());
                    }
                }
                "permission" => {
                    i += 1;
                    while i < lines.len() {
                        let inner = lines[i];
                        if inner.trim().is_empty() {
                            i += 1;
                            continue;
                        }
                        // Stop at next top-level key.
                        if !(inner.starts_with(' ') || inner.starts_with('\t')) {
                            break;
                        }
                        if let Some((pk, pv)) = inner.trim().split_once(':') {
                            if let Ok(level) = pv.trim().parse::<PermissionLevel>() {
                                permission.insert(pk.trim().to_string(), level);
                            }
                        }
                        i += 1;
                    }
                    continue;
                }
                _ => {}
            }
            i += 1;
        }

        let _ = body; // Prompt body is not stored in the parity struct.

        Some(Agent {
            name,
            description,
            mode,
            model,
            temperature,
            max_steps,
            permission,
            color,
            hidden,
            disabled,
            is_builtin: false,
        })
    }

    // ── Permissions ─────────────────────────────────────────

    #[allow(dead_code)] // used by permission dispatch gate — TODO(v2.6): wire into tool dispatch
    pub fn can_execute_tool(&self, agent: &str, tool: &str) -> (bool, String) {
        let env_deny = std::env::var("APEX_PERMISSION_DENY").ok();
        let env_ask = std::env::var("APEX_PERMISSION_ASK").ok();
        self.can_execute_tool_with_env(agent, tool, env_deny.as_deref(), env_ask.as_deref())
    }

    #[allow(dead_code)] // used by permission dispatch gate — TODO(v2.6): wire into tool dispatch
    pub fn can_execute_tool_with_env(
        &self,
        agent: &str,
        tool: &str,
        env_deny: Option<&str>,
        env_ask: Option<&str>,
    ) -> (bool, String) {
        let level = resolve_permission_level(self, agent, tool, env_deny, env_ask);
        match level {
            PermissionLevel::Allow => (true, String::new()),
            PermissionLevel::Deny => (
                false,
                format!("Tool '{tool}' is denied for agent '{agent}'"),
            ),
            PermissionLevel::Ask => (
                false,
                format!("Tool '{tool}' requires confirmation for agent '{agent}'"),
            ),
        }
    }
}

// ────────────────────────────────────────────────────────────
// Standalone helpers (CLI + tests)
// ────────────────────────────────────────────────────────────

pub fn valid_agent_name(name: &str) -> bool {
    !name.is_empty()
        && !name.contains('/')
        && !name.contains('\\')
        && !name.contains("..")
        && !name.contains('\0')
}

pub fn builtin_agents() -> BTreeMap<String, Agent> {
    let mut map = BTreeMap::new();

    macro_rules! add {
        ($name:expr, $desc:expr, $mode:expr, $color:expr, $hidden:expr, $perms:expr) => {
            let mut permission = HashMap::new();
            for (k, v) in $perms {
                permission.insert(k.to_string(), v);
            }
            map.insert(
                $name.to_string(),
                Agent {
                    name: $name.to_string(),
                    description: $desc.to_string(),
                    mode: $mode,
                    model: None,
                    temperature: Some(0.0),
                    max_steps: None,
                    permission,
                    color: Some($color.to_string()),
                    hidden: $hidden,
                    disabled: false,
                    is_builtin: true,
                },
            );
        };
    }

    add!(
        "build",
        "Default agent with full tool access for development work",
        AgentMode::Primary,
        "#00e5ff",
        false,
        [
            ("read", PermissionLevel::Allow),
            ("edit", PermissionLevel::Allow),
            ("glob", PermissionLevel::Allow),
            ("grep", PermissionLevel::Allow),
            ("list", PermissionLevel::Allow),
            ("bash", PermissionLevel::Allow),
            ("task", PermissionLevel::Allow),
            ("webfetch", PermissionLevel::Allow),
            ("websearch", PermissionLevel::Allow),
        ]
    );
    add!(
        "plan",
        "Read-only agent for planning and analysis — does not modify files",
        AgentMode::Primary,
        "#a855f7",
        false,
        [
            ("read", PermissionLevel::Allow),
            ("edit", PermissionLevel::Deny),
            ("glob", PermissionLevel::Allow),
            ("grep", PermissionLevel::Allow),
            ("list", PermissionLevel::Allow),
            ("bash", PermissionLevel::Deny),
            ("task", PermissionLevel::Allow),
            ("webfetch", PermissionLevel::Allow),
            ("websearch", PermissionLevel::Allow),
        ]
    );
    add!(
        "planner",
        "Read-only agent for detailed planning — does not modify files or delegate tasks",
        AgentMode::Primary,
        "#eab308",
        false,
        [
            ("read", PermissionLevel::Allow),
            ("edit", PermissionLevel::Deny),
            ("glob", PermissionLevel::Allow),
            ("grep", PermissionLevel::Allow),
            ("list", PermissionLevel::Allow),
            ("bash", PermissionLevel::Deny),
            ("task", PermissionLevel::Deny),
            ("webfetch", PermissionLevel::Allow),
            ("websearch", PermissionLevel::Allow),
        ]
    );
    add!(
        "reviewer",
        "Code review specialist — read-only, never modifies files",
        AgentMode::Subagent,
        "#00ff88",
        false,
        [
            ("read", PermissionLevel::Allow),
            ("edit", PermissionLevel::Deny),
            ("glob", PermissionLevel::Allow),
            ("grep", PermissionLevel::Allow),
            ("list", PermissionLevel::Allow),
            ("bash", PermissionLevel::Deny),
            ("task", PermissionLevel::Deny),
            ("webfetch", PermissionLevel::Allow),
            ("websearch", PermissionLevel::Allow),
        ]
    );
    add!(
        "shell",
        "Infrastructure and deployment specialist",
        AgentMode::Primary,
        "#ff6b35",
        false,
        [
            ("read", PermissionLevel::Allow),
            ("edit", PermissionLevel::Ask),
            ("glob", PermissionLevel::Allow),
            ("grep", PermissionLevel::Allow),
            ("list", PermissionLevel::Allow),
            ("bash", PermissionLevel::Ask),
            ("task", PermissionLevel::Allow),
            ("webfetch", PermissionLevel::Allow),
            ("websearch", PermissionLevel::Allow),
        ]
    );
    add!(
        "general",
        "General-purpose research and multi-step task agent with full tool access",
        AgentMode::Subagent,
        "#89b4fa",
        false,
        [
            ("read", PermissionLevel::Allow),
            ("edit", PermissionLevel::Allow),
            ("glob", PermissionLevel::Allow),
            ("grep", PermissionLevel::Allow),
            ("list", PermissionLevel::Allow),
            ("bash", PermissionLevel::Allow),
            ("task", PermissionLevel::Allow),
            ("webfetch", PermissionLevel::Allow),
            ("websearch", PermissionLevel::Allow),
        ]
    );
    add!(
        "explore",
        "Fast read-only codebase exploration agent",
        AgentMode::Subagent,
        "#f9e2af",
        false,
        [
            ("read", PermissionLevel::Allow),
            ("edit", PermissionLevel::Deny),
            ("glob", PermissionLevel::Allow),
            ("grep", PermissionLevel::Allow),
            ("list", PermissionLevel::Allow),
            ("bash", PermissionLevel::Deny),
            ("task", PermissionLevel::Deny),
            ("webfetch", PermissionLevel::Deny),
            ("websearch", PermissionLevel::Deny),
        ]
    );
    add!(
        "scout",
        "External documentation and dependency research agent",
        AgentMode::Subagent,
        "#a6e3a1",
        false,
        [
            ("read", PermissionLevel::Allow),
            ("edit", PermissionLevel::Deny),
            ("glob", PermissionLevel::Allow),
            ("grep", PermissionLevel::Allow),
            ("list", PermissionLevel::Allow),
            ("bash", PermissionLevel::Ask),
            ("bash:git clone *", PermissionLevel::Allow),
            ("bash:pip *", PermissionLevel::Allow),
            ("bash:npm *", PermissionLevel::Allow),
            ("task", PermissionLevel::Deny),
            ("webfetch", PermissionLevel::Allow),
            ("websearch", PermissionLevel::Allow),
        ]
    );
    add!(
        "compaction",
        "Hidden system agent for context window compaction",
        AgentMode::Subagent,
        "#6c7086",
        true,
        [
            ("read", PermissionLevel::Allow),
            ("edit", PermissionLevel::Deny),
            ("bash", PermissionLevel::Deny),
        ]
    );
    add!(
        "title",
        "Hidden system agent for session title generation",
        AgentMode::Subagent,
        "#6c7086",
        true,
        [
            ("read", PermissionLevel::Deny),
            ("edit", PermissionLevel::Deny),
            ("bash", PermissionLevel::Deny),
        ]
    );
    add!(
        "summary",
        "Hidden system agent for session summaries",
        AgentMode::Subagent,
        "#6c7086",
        true,
        [
            ("read", PermissionLevel::Allow),
            ("edit", PermissionLevel::Deny),
            ("bash", PermissionLevel::Deny),
        ]
    );

    map
}

pub fn save_agent_file(cwd: &Path, agent: &Agent) -> std::io::Result<PathBuf> {
    let dir = cwd.join(".apex").join("agents");
    fs::create_dir_all(&dir)?;
    let path = dir.join(format!("{}.md", agent.name));
    fs::write(&path, agent_to_markdown(agent))?;
    Ok(path)
}

pub fn remove_agent_file(cwd: &Path, name: &str) -> bool {
    let path = cwd.join(".apex").join("agents").join(format!("{name}.md"));
    fs::remove_file(path).is_ok()
}

pub fn agent_to_markdown(agent: &Agent) -> String {
    let mut lines = Vec::new();
    lines.push("---".to_string());
    lines.push(format!("description: {}", agent.description));
    lines.push(format!("mode: {}", agent.mode.as_str()));
    if let Some(model) = &agent.model {
        lines.push(format!("model: {model}"));
    }
    if let Some(temp) = agent.temperature {
        lines.push(format!("temperature: {temp}"));
    }
    if let Some(max) = agent.max_steps {
        lines.push(format!("max_steps: {max}"));
    }
    if let Some(color) = &agent.color {
        lines.push(format!("color: {color}"));
    }
    if agent.hidden {
        lines.push("hidden: true".to_string());
    }
    if agent.disabled {
        lines.push("disabled: true".to_string());
    }
    if !agent.permission.is_empty() {
        lines.push("permission:".to_string());
        let mut keys: Vec<&String> = agent.permission.keys().collect();
        keys.sort();
        for key in keys {
            let level = agent.permission.get(key).unwrap();
            lines.push(format!("  {key}: {}", level.as_str()));
        }
    }
    lines.push("---".to_string());
    lines.push(String::new());
    lines.join("\n")
}

// ────────────────────────────────────────────────────────────
// Permission resolution helpers
// ────────────────────────────────────────────────────────────

#[allow(dead_code)] // used by permission dispatch gate — TODO(v2.6): wire into tool dispatch
fn resolve_permission_level(
    registry: &AgentRegistry,
    agent_name: &str,
    tool: &str,
    env_deny: Option<&str>,
    env_ask: Option<&str>,
) -> PermissionLevel {
    let category = tool_category(tool);

    let mut levels: Vec<PermissionLevel> = Vec::new();

    if let Some(agent) = registry.agents.get(agent_name) {
        for (pattern, level) in &agent.permission {
            if glob_matches(pattern, tool) || glob_matches(pattern, category) {
                levels.push(*level);
            }
        }
    }

    let mut level = if levels.is_empty() || levels.contains(&PermissionLevel::Deny) {
        PermissionLevel::Deny
    } else if levels.contains(&PermissionLevel::Ask) {
        PermissionLevel::Ask
    } else {
        PermissionLevel::Allow
    };

    // Environment overrides (deny wins over ask/allow).
    let deny_patterns = split_patterns(env_deny);
    if deny_patterns
        .iter()
        .any(|p| glob_matches(p, tool) || glob_matches(p, category))
    {
        level = PermissionLevel::Deny;
    }

    let ask_patterns = split_patterns(env_ask);
    if level != PermissionLevel::Deny
        && ask_patterns
            .iter()
            .any(|p| glob_matches(p, tool) || glob_matches(p, category))
    {
        level = PermissionLevel::Ask;
    }

    level
}

#[allow(dead_code)] // used by permission dispatch gate — TODO(v2.6): wire into tool dispatch
fn tool_category(tool: &str) -> &'static str {
    const READ_TOOLS: &[&str] = &[
        "read_file",
        "list_files",
        "search_in_files",
        "glob_search",
        "get_file_tree",
        "get_git_status",
        "get_git_log",
        "git_diff",
        "get_repo_map",
        "get_language_stats",
        "fetch_url",
        "read_image",
        "read",
        "list",
        "glob",
        "grep",
    ];
    const EDIT_TOOLS: &[&str] = &[
        "write_file",
        "edit_file",
        "delete_file",
        "create_directory",
        "run_test",
        "format_file",
        "install_package",
    ];
    const BASH_TOOLS: &[&str] = &["run_command", "bash"];
    const WEB_TOOLS: &[&str] = &["web_search"];

    if READ_TOOLS.contains(&tool) {
        "read"
    } else if EDIT_TOOLS.contains(&tool) {
        "edit"
    } else if BASH_TOOLS.contains(&tool) {
        "bash"
    } else if tool == "task" {
        "task"
    } else if WEB_TOOLS.contains(&tool) {
        "websearch"
    } else {
        "read"
    }
}

#[allow(dead_code)] // used by permission dispatch gate — TODO(v2.6): wire into tool dispatch
fn split_patterns(input: Option<&str>) -> Vec<String> {
    input
        .unwrap_or("")
        .split(',')
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect()
}

fn parse_bool(value: &str) -> bool {
    matches!(
        value.trim().to_lowercase().as_str(),
        "true" | "1" | "yes" | "on"
    )
}

#[allow(dead_code)] // used by permission dispatch gate — TODO(v2.6): wire into tool dispatch
fn glob_matches(pattern: &str, text: &str) -> bool {
    // Simple fnmatch-style matcher supporting `*` and `?`.
    fn match_bytes(pattern: &[u8], text: &[u8]) -> bool {
        if pattern.is_empty() {
            return text.is_empty();
        }
        if pattern[0] == b'*' {
            for i in 0..=text.len() {
                if match_bytes(&pattern[1..], &text[i..]) {
                    return true;
                }
            }
            return false;
        }
        if !text.is_empty() && (pattern[0] == b'?' || pattern[0] == text[0]) {
            return match_bytes(&pattern[1..], &text[1..]);
        }
        false
    }
    match_bytes(pattern.as_bytes(), text.as_bytes())
}

// ────────────────────────────────────────────────────────────
// Tests
// ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn eleven_builtins_with_modes_and_colors() {
        let reg = AgentRegistry::new();
        assert_eq!(reg.agents.len(), 11);
        let expected = [
            ("build", "primary", "#00e5ff"),
            ("plan", "primary", "#a855f7"),
            ("planner", "primary", "#eab308"),
            ("reviewer", "subagent", "#00ff88"),
            ("shell", "primary", "#ff6b35"),
            ("general", "subagent", "#89b4fa"),
            ("explore", "subagent", "#f9e2af"),
            ("scout", "subagent", "#a6e3a1"),
            ("compaction", "subagent", "#6c7086"),
            ("title", "subagent", "#6c7086"),
            ("summary", "subagent", "#6c7086"),
        ];
        for (name, mode, color) in expected {
            let agent = reg.get(name).expect(name);
            assert!(agent.is_builtin);
            assert_eq!(agent.mode.as_str(), mode);
            assert_eq!(agent.color.as_deref(), Some(color));
        }
        assert!(reg.get("compaction").unwrap().hidden);
        assert!(reg.get("title").unwrap().hidden);
        assert!(reg.get("summary").unwrap().hidden);
    }

    #[test]
    fn parse_markdown_frontmatter() {
        let dir = tempdir().unwrap();
        let agents = dir.path().join(".apex").join("agents");
        std::fs::create_dir_all(&agents).unwrap();
        std::fs::write(
            agents.join("reviewer-x.md"),
            "---\ndescription: Reviews code\nmode: subagent\nmodel: anthropic/claude-sonnet-4-5\ntemperature: 0.1\npermission:\n  edit: deny\n  bash: deny\n---\nYou are a reviewer.\n",
        )
        .unwrap();
        let mut reg = AgentRegistry::new();
        reg.load_markdown_agents_from(dir.path());
        let agent = reg.get("reviewer-x").expect("loaded");
        assert_eq!(agent.description, "Reviews code");
        assert_eq!(agent.mode, AgentMode::Subagent);
        assert_eq!(agent.model.as_deref(), Some("anthropic/claude-sonnet-4-5"));
        assert_eq!(agent.temperature, Some(0.1));
        assert_eq!(agent.permission.get("edit"), Some(&PermissionLevel::Deny));
        assert_eq!(agent.permission.get("bash"), Some(&PermissionLevel::Deny));
        assert!(!agent.is_builtin);
    }

    #[test]
    fn invalid_names_rejected() {
        for bad in ["", "..", "a/b", "a\\b", "../x"] {
            assert!(!valid_agent_name(bad), "{bad:?}");
        }
        assert!(valid_agent_name("good-agent"));
    }

    #[test]
    fn merge_permissions_deny_beats_allow() {
        let mut reg = AgentRegistry::new();
        let mut permission = HashMap::new();
        permission.insert("*".to_string(), PermissionLevel::Allow);
        permission.insert("danger*".to_string(), PermissionLevel::Deny);
        reg.register(Agent {
            name: "mixed".to_string(),
            description: "mixed".to_string(),
            mode: AgentMode::Primary,
            model: None,
            temperature: None,
            max_steps: None,
            permission,
            color: None,
            hidden: false,
            disabled: false,
            is_builtin: false,
        });
        let (ok, _) = reg.can_execute_tool("mixed", "danger_tool");
        assert!(!ok);
        let (ok, _) = reg.can_execute_tool("mixed", "safe_tool");
        assert!(ok);
    }

    #[test]
    fn env_rules() {
        let reg = AgentRegistry::new();
        let (ok, _) = reg.can_execute_tool_with_env("build", "bash", Some("bash"), None);
        assert!(!ok);
        let (ok, _) = reg.can_execute_tool_with_env("build", "bash", None, Some("bash"));
        assert!(!ok);
        let (ok, _) = reg.can_execute_tool_with_env("build", "bash", None, None);
        assert!(ok);
    }

    #[test]
    fn create_and_delete_agent_file() {
        let dir = tempdir().unwrap();
        let agent = Agent {
            name: "my-agent".to_string(),
            description: "Custom".to_string(),
            mode: AgentMode::Subagent,
            model: Some("gpt-4o".to_string()),
            temperature: None,
            max_steps: None,
            permission: HashMap::new(),
            color: Some("cyan".to_string()),
            hidden: false,
            disabled: false,
            is_builtin: false,
        };
        let path = save_agent_file(dir.path(), &agent).unwrap();
        assert!(path.exists());
        let mut reg = AgentRegistry::new();
        reg.load_markdown_agents_from(dir.path());
        assert!(reg.get("my-agent").is_some());

        assert!(remove_agent_file(dir.path(), "my-agent"));
        assert!(!dir
            .path()
            .join(".apex")
            .join("agents")
            .join("my-agent.md")
            .exists());
    }
}
