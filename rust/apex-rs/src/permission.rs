//! Ruleset-based permission system — port of `apex/permission.py`.
//!
//! Mirrors the Python reference: `PermissionRule` list (first match wins),
//! wildcard matching via `fnmatch`-style patterns, ALLOW/DENY/ASK actions,
//! and a request/approve/deny flow that can remember decisions as rules.

use regex::Regex;
use serde_json::Value;
use std::collections::HashMap;
use std::sync::{LazyLock, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

// ────────────────────────────────────────────────────────────
// PermissionAction
// ────────────────────────────────────────────────────────────

/// Port of `PermissionAction`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PermissionAction {
    Allow,
    Deny,
    Ask,
}

impl PermissionAction {
    pub fn value(&self) -> &'static str {
        match self {
            PermissionAction::Allow => "allow",
            PermissionAction::Deny => "deny",
            PermissionAction::Ask => "ask",
        }
    }
}

// ────────────────────────────────────────────────────────────
// PermissionRule
// ────────────────────────────────────────────────────────────

/// Port of `PermissionRule`.
#[derive(Debug, Clone)]
pub struct PermissionRule {
    pub pattern: String,
    pub action: PermissionAction,
    pub reason: Option<String>,
    pub expires_at: Option<f64>,
    pub remember: bool,
}

impl PermissionRule {
    pub fn is_expired(&self) -> bool {
        match self.expires_at {
            Some(at) => now_secs() > at,
            None => false,
        }
    }
}

fn now_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

// ────────────────────────────────────────────────────────────
// PermissionRequest
// ────────────────────────────────────────────────────────────

/// Port of `PermissionRequest`.
#[derive(Debug, Clone)]
pub struct PermissionRequest {
    pub request_id: String,
    pub tool_name: String,
    pub permission: String,
    pub args: Value,
    pub timestamp: f64,
    pub status: String,
    pub workspace_id: Option<String>,
    pub user_id: Option<String>,
}

// ────────────────────────────────────────────────────────────
// fnmatch-style wildcards
// ────────────────────────────────────────────────────────────

/// Translate an `fnmatch`-style pattern into a `regex` pattern
/// (`*` → `.*`, `?` → `.`; everything else is escaped).
fn fnmatch_regex(pattern: &str) -> Regex {
    let mut re = String::from("^");
    for ch in pattern.chars() {
        match ch {
            '*' => re.push_str(".*"),
            '?' => re.push('.'),
            _ => {
                if ch.is_ascii_alphanumeric() || ch == '_' {
                    re.push(ch);
                } else {
                    re.push('\\');
                    re.push(ch);
                }
            }
        }
    }
    re.push('$');
    Regex::new(&re).expect("invalid fnmatch pattern")
}

// ────────────────────────────────────────────────────────────
// PermissionManager
// ────────────────────────────────────────────────────────────

/// Port of `PermissionManager`. Unlike the Python version, the manager is
/// initialized at construction (default rules are always present).
pub struct PermissionManager {
    rules: Vec<PermissionRule>,
    requests: HashMap<String, PermissionRequest>,
    request_id_counter: u64,
}

impl Default for PermissionManager {
    fn default() -> Self {
        Self::new()
    }
}

impl PermissionManager {
    pub fn new() -> Self {
        let mut m = Self {
            rules: Vec::new(),
            requests: HashMap::new(),
            request_id_counter: 0,
        };
        m.setup_default_rules();
        m
    }

    fn setup_default_rules(&mut self) {
        self.rules = vec![
            PermissionRule {
                pattern: "read_file".into(),
                action: PermissionAction::Allow,
                reason: Some("Reading files is safe".into()),
                expires_at: None,
                remember: false,
            },
            PermissionRule {
                pattern: "glob".into(),
                action: PermissionAction::Allow,
                reason: Some("File searching is safe".into()),
                expires_at: None,
                remember: false,
            },
            PermissionRule {
                pattern: "grep".into(),
                action: PermissionAction::Allow,
                reason: Some("Search is safe".into()),
                expires_at: None,
                remember: false,
            },
            PermissionRule {
                pattern: "lsp_*".into(),
                action: PermissionAction::Allow,
                reason: Some("LSP operations are safe".into()),
                expires_at: None,
                remember: false,
            },
            PermissionRule {
                pattern: "*".into(),
                action: PermissionAction::Ask,
                reason: Some("Default: ask for permission".into()),
                expires_at: None,
                remember: false,
            },
        ];
    }

    pub fn add_rule(
        &mut self,
        pattern: &str,
        action: PermissionAction,
        reason: Option<String>,
        expires_in: Option<u64>,
        remember: bool,
    ) {
        let expires_at = expires_in.map(|s| now_secs() + s as f64);
        let mut rule = PermissionRule {
            pattern: pattern.to_string(),
            action,
            reason,
            expires_at,
            remember,
        };
        if remember && expires_in.is_none() {
            rule.expires_at = None;
        }
        self.rules.insert(0, rule);
    }

    pub fn remove_rule(&mut self, pattern: &str, action: PermissionAction) -> bool {
        let before = self.rules.len();
        self.rules
            .retain(|r| !(r.pattern == pattern && r.action == action));
        self.rules.len() < before
    }

    pub fn clear_rules(&mut self) {
        self.rules.clear();
        self.setup_default_rules();
    }

    /// Returns `(allowed, reason_or_message)` — port of `can_execute_tool`.
    pub fn can_execute_tool(
        &self,
        tool_name: &str,
        _workspace_id: Option<&str>,
        _user_id: Option<&str>,
    ) -> (bool, String) {
        for rule in &self.rules {
            if rule.is_expired() {
                continue;
            }
            if fnmatch_regex(&rule.pattern).is_match(tool_name) {
                return match rule.action {
                    PermissionAction::Allow => (
                        true,
                        rule.reason.clone().unwrap_or_else(|| "Allowed by rule".into()),
                    ),
                    PermissionAction::Deny => (
                        false,
                        rule.reason.clone().unwrap_or_else(|| "Denied by rule".into()),
                    ),
                    PermissionAction::Ask => (
                        false,
                        format!(
                            "Requires permission: {}",
                            rule.reason.clone().unwrap_or_else(|| tool_name.to_string())
                        ),
                    ),
                };
            }
        }
        (
            false,
            format!("No rule matched '{tool_name}', defaulting to ask"),
        )
    }

    pub fn request_permission(
        &mut self,
        tool_name: &str,
        args: Value,
        permission: &str,
        workspace_id: Option<String>,
        user_id: Option<String>,
    ) -> String {
        self.request_id_counter += 1;
        let request_id = format!(
            "req_{}_{:08x}",
            self.request_id_counter,
            now_secs() as u64
        );
        let request = PermissionRequest {
            request_id: request_id.clone(),
            tool_name: tool_name.to_string(),
            permission: permission.to_string(),
            args,
            timestamp: now_secs(),
            status: "pending".to_string(),
            workspace_id,
            user_id,
        };
        self.requests.insert(request_id.clone(), request);
        request_id
    }

    pub fn approve_request(
        &mut self,
        request_id: &str,
        remember: bool,
        expires_in: Option<u64>,
    ) -> bool {
        let Some(request) = self.requests.remove(request_id) else {
            return false;
        };
        if remember {
            let reason = format!("Approved for {}", request.tool_name);
            self.add_rule(&request.tool_name, PermissionAction::Allow, Some(reason), expires_in, true);
        }
        true
    }

    pub fn deny_request(&mut self, request_id: &str, remember: bool) -> bool {
        let Some(request) = self.requests.remove(request_id) else {
            return false;
        };
        if remember {
            let reason = format!("Denied for {}", request.tool_name);
            self.add_rule(&request.tool_name, PermissionAction::Deny, Some(reason), None, true);
        }
        true
    }

    pub fn get_pending_requests(&self) -> Vec<PermissionRequest> {
        self.requests.values().cloned().collect()
    }

    pub fn get_request(&self, request_id: &str) -> Option<PermissionRequest> {
        self.requests.get(request_id).cloned()
    }
}

/// Module-level manager, mirroring `permission_manager`.
pub static PERMISSION_MANAGER: LazyLock<Mutex<PermissionManager>> =
    LazyLock::new(|| Mutex::new(PermissionManager::new()));

// ────────────────────────────────────────────────────────────
// Tool → permission mapping
// ────────────────────────────────────────────────────────────

/// Port of `get_tool_permission`.
pub fn get_tool_permission(tool_name: &str) -> &'static str {
    const MAP: &[(&str, &str)] = &[
        ("read_file", "file:read"),
        ("write_file", "file:write"),
        ("edit_file", "file:edit"),
        ("delete_file", "file:delete"),
        ("run_command", "shell:execute"),
        ("bash", "shell:execute"),
        ("shell", "shell:execute"),
        ("search", "web:search"),
        ("fetch_url", "web:fetch"),
        ("mcp_*", "mcp:execute"),
    ];
    for (pattern, permission) in MAP {
        if fnmatch_regex(pattern).is_match(tool_name) {
            return permission;
        }
    }
    "tool:execute"
}

/// Port of `PermissionRequestDenied`.
#[derive(Debug)]
pub struct PermissionRequestDenied {
    pub tool_name: String,
    pub permission: String,
    pub request_id: String,
}

impl std::fmt::Display for PermissionRequestDenied {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Permission required for {}: {}", self.tool_name, self.permission)
    }
}

impl std::error::Error for PermissionRequestDenied {}

// ────────────────────────────────────────────────────────────
// Tests
// ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_allows_safe_tools() {
        let m = PermissionManager::new();
        assert_eq!(m.can_execute_tool("read_file", None, None), (true, "Reading files is safe".to_string()));
        assert_eq!(m.can_execute_tool("grep", None, None).0, true);
        assert_eq!(m.can_execute_tool("lsp_diagnostics", None, None).0, true);
    }

    #[test]
    fn default_asks_for_unknown() {
        let m = PermissionManager::new();
        let (ok, msg) = m.can_execute_tool("bash", None, None);
        assert!(!ok);
        assert!(msg.contains("Requires permission"));
    }

    #[test]
    fn deny_rule_wins_by_position() {
        let mut m = PermissionManager::new();
        m.add_rule("write_file", PermissionAction::Deny, Some("no writes".into()), None, false);
        let (ok, msg) = m.can_execute_tool("write_file", None, None);
        assert!(!ok);
        assert!(msg.contains("no writes"));
        assert!(m.remove_rule("write_file", PermissionAction::Deny));
    }

    #[test]
    fn wildcard_star_and_question() {
        let mut m = PermissionManager::new();
        m.add_rule("mcp_?", PermissionAction::Allow, None, None, false);
        assert!(m.can_execute_tool("mcp_a", None, None).0);
        assert!(!m.can_execute_tool("mcp_ab", None, None).0);
    }

    #[test]
    fn clear_resets_defaults() {
        let mut m = PermissionManager::new();
        m.add_rule("*", PermissionAction::Deny, None, None, false);
        m.clear_rules();
        assert!(m.can_execute_tool("read_file", None, None).0);
    }

    #[test]
    fn request_approve_remember_adds_allow_rule() {
        let mut m = PermissionManager::new();
        let id = m.request_permission("bash", serde_json::json!({"cmd": "ls"}), "shell:execute", None, None);
        assert!(id.starts_with("req_"));
        assert_eq!(m.get_request(&id).unwrap().status, "pending");
        assert!(m.approve_request(&id, true, None));
        assert!(m.get_request(&id).is_none());
        assert!(m.can_execute_tool("bash", None, None).0);
    }

    #[test]
    fn request_deny_remember_adds_deny_rule() {
        let mut m = PermissionManager::new();
        let id = m.request_permission("write_file", serde_json::json!({}), "file:write", None, None);
        assert!(m.deny_request(&id, true));
        assert!(!m.can_execute_tool("write_file", None, None).0);
    }

    #[test]
    fn unknown_request_rejected() {
        let mut m = PermissionManager::new();
        assert!(!m.approve_request("req_unknown", false, None));
        assert!(!m.deny_request("req_unknown", false));
    }

    #[test]
    fn tool_permission_map() {
        assert_eq!(get_tool_permission("read_file"), "file:read");
        assert_eq!(get_tool_permission("bash"), "shell:execute");
        assert_eq!(get_tool_permission("mcp_fetch"), "mcp:execute");
        assert_eq!(get_tool_permission("whatever"), "tool:execute");
    }
}
