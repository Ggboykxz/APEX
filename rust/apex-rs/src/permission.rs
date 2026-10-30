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
    /// Python's `value()`; no CLI/API surface reads action strings yet.
    // TODO(v2.6): `apex-rs permission list` prints actions via this.
    #[allow(dead_code)]
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
    /// Parity field; consumed by the not-yet-wired request flow.
    // TODO(v2.6): read it when the approval flow ships.
    #[allow(dead_code)]
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

/// Port of `PermissionRequest`. The interactive request/approve/deny flow
/// is unwired: the headless backend has no prompt surface.
// TODO(v2.6): wire approval over a `serve` route or `/ws/events`.
#[allow(dead_code)]
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
    /// Backing store for the not-yet-wired request flow.
    // TODO(v2.6): used when approval requests are served.
    #[allow(dead_code)]
    requests: HashMap<String, PermissionRequest>,
    /// Backing store for the not-yet-wired request flow.
    // TODO(v2.6): used when approval requests are served.
    #[allow(dead_code)]
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

    /// Rule-management parity; only tests call it so far.
    // TODO(v2.6): expose via an `apex-rs permission rule remove` command.
    #[allow(dead_code)]
    pub fn remove_rule(&mut self, pattern: &str, action: PermissionAction) -> bool {
        let before = self.rules.len();
        self.rules
            .retain(|r| !(r.pattern == pattern && r.action == action));
        self.rules.len() < before
    }

    /// Rule-management parity; only tests call it so far.
    // TODO(v2.6): expose via an `apex-rs permission rule clear` command.
    #[allow(dead_code)]
    pub fn clear_rules(&mut self) {
        self.rules.clear();
        self.setup_default_rules();
    }

    /// Headless Rust backend variant of the manager.
    ///
    /// Same rules as `new()`, except the catch-all is ALLOW instead of ASK:
    /// Python's `*` → ASK default models an interactive user who can answer
    /// permission prompts, and the Rust backend has no prompt surface, so
    /// mirroring it would refuse every tool without an explicit allow rule
    /// (all writes, all commands). Explicit DENY/ASK rules and the
    /// `APEX_PERMISSION_DENY` / `APEX_PERMISSION_ASK` env rules still win.
    pub fn headless() -> Self {
        let mut m = Self::new();
        m.rules
            .retain(|r| !(r.pattern == "*" && r.action == PermissionAction::Ask));
        m.rules.push(PermissionRule {
            pattern: "*".into(),
            action: PermissionAction::Allow,
            reason: Some("Rust headless default: allow".into()),
            expires_at: None,
            remember: false,
        });
        m
    }

    /// The action of the first non-expired rule matching the tool, or `None`.
    pub fn matching_action(&self, tool_name: &str) -> Option<PermissionAction> {
        self.rules
            .iter()
            .find(|r| !r.is_expired() && fnmatch_regex(&r.pattern).is_match(tool_name))
            .map(|r| r.action)
    }

    /// Add rules from `APEX_PERMISSION_DENY` and `APEX_PERMISSION_ASK`
    /// (comma-separated fnmatch patterns). Intended to be called once per
    /// manager; inserted first so they win over the defaults.
    pub fn install_env_rules(&mut self) {
        for p in env_patterns("APEX_PERMISSION_DENY") {
            self.add_rule(
                &p,
                PermissionAction::Deny,
                Some(format!("Denied by APEX_PERMISSION_DENY ({p})")),
                None,
                false,
            );
        }
        for p in env_patterns("APEX_PERMISSION_ASK") {
            self.add_rule(
                &p,
                PermissionAction::Ask,
                Some(format!("Requires approval (APEX_PERMISSION_ASK {p})")),
                None,
                false,
            );
        }
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
                        rule.reason
                            .clone()
                            .unwrap_or_else(|| "Allowed by rule".into()),
                    ),
                    PermissionAction::Deny => (
                        false,
                        rule.reason
                            .clone()
                            .unwrap_or_else(|| "Denied by rule".into()),
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

    /// Part of the interactive request flow, unwired: the headless backend
    /// has no prompt surface (ASK refuses in `dispatch_gate` instead).
    // TODO(v2.6): wire approval over a `serve` route or `/ws/events`.
    #[allow(dead_code)]
    pub fn request_permission(
        &mut self,
        tool_name: &str,
        args: Value,
        permission: &str,
        workspace_id: Option<String>,
        user_id: Option<String>,
    ) -> String {
        self.request_id_counter += 1;
        let request_id = format!("req_{}_{:08x}", self.request_id_counter, now_secs() as u64);
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

    /// Part of the interactive request flow, unwired: the headless backend
    /// has no prompt surface.
    // TODO(v2.6): wire approval over a `serve` route or `/ws/events`.
    #[allow(dead_code)]
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
            self.add_rule(
                &request.tool_name,
                PermissionAction::Allow,
                Some(reason),
                expires_in,
                true,
            );
        }
        true
    }

    /// Part of the interactive request flow, unwired: the headless backend
    /// has no prompt surface.
    // TODO(v2.6): wire approval over a `serve` route or `/ws/events`.
    #[allow(dead_code)]
    pub fn deny_request(&mut self, request_id: &str, remember: bool) -> bool {
        let Some(request) = self.requests.remove(request_id) else {
            return false;
        };
        if remember {
            let reason = format!("Denied for {}", request.tool_name);
            self.add_rule(
                &request.tool_name,
                PermissionAction::Deny,
                Some(reason),
                None,
                true,
            );
        }
        true
    }

    /// Part of the interactive request flow, unwired: the headless backend
    /// has no prompt surface.
    // TODO(v2.6): wire approval over a `serve` route or `/ws/events`.
    #[allow(dead_code)]
    pub fn get_pending_requests(&self) -> Vec<PermissionRequest> {
        self.requests.values().cloned().collect()
    }

    /// Part of the interactive request flow, unwired: the headless backend
    /// has no prompt surface.
    // TODO(v2.6): wire approval over a `serve` route or `/ws/events`.
    #[allow(dead_code)]
    pub fn get_request(&self, request_id: &str) -> Option<PermissionRequest> {
        self.requests.get(request_id).cloned()
    }
}

/// Module-level manager, mirroring `permission_manager`. The Rust backend
/// is headless, so it runs the `headless()` policy (default-allow catch-all).
pub static PERMISSION_MANAGER: LazyLock<Mutex<PermissionManager>> =
    LazyLock::new(|| Mutex::new(PermissionManager::headless()));

static ENV_RULES_INSTALLED: std::sync::atomic::AtomicBool =
    std::sync::atomic::AtomicBool::new(false);

/// Comma-separated fnmatch patterns from env var `name` (empty segments
/// dropped, missing var → empty list).
fn env_patterns(name: &str) -> Vec<String> {
    std::env::var(name)
        .ok()
        .map(|v| {
            v.split(',')
                .map(|p| p.trim().to_string())
                .filter(|p| !p.is_empty())
                .collect()
        })
        .unwrap_or_default()
}

fn ensure_env_rules() {
    use std::sync::atomic::Ordering;
    if ENV_RULES_INSTALLED.swap(true, Ordering::SeqCst) {
        return;
    }
    let mut manager = PERMISSION_MANAGER.lock().unwrap();
    manager.install_env_rules();
}

/// Permission decision for tool dispatch in the headless Rust backend.
///
/// The global manager's rules decide (headless default-allow catch-all,
/// explicit DENY/ASK rules, `APEX_PERMISSION_DENY` / `APEX_PERMISSION_ASK`
/// installed on first use). ASK refuses: there is no prompt surface, so an
/// unanswered "ask" cannot become an allow.
pub fn dispatch_gate(tool_name: &str) -> (bool, String) {
    ensure_env_rules();
    let manager = PERMISSION_MANAGER.lock().unwrap();
    match manager.matching_action(tool_name) {
        Some(PermissionAction::Allow) => (true, String::new()),
        // DENY and ASK both refuse; `can_execute_tool` carries the rule reason.
        _ => manager.can_execute_tool(tool_name, None, None),
    }
}

// ────────────────────────────────────────────────────────────
// Tool → permission mapping
// ────────────────────────────────────────────────────────────

/// Port of `get_tool_permission`. Consumed by the request flow, which is
/// unwired in the headless backend.
// TODO(v2.6): used when approval requests ship (names the permission asked for).
#[allow(dead_code)]
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

/// Port of `PermissionRequestDenied`. Thrown by the request flow, which is
/// unwired in the headless backend.
// TODO(v2.6): surfaced when approval requests ship.
#[allow(dead_code)]
#[derive(Debug)]
pub struct PermissionRequestDenied {
    pub tool_name: String,
    pub permission: String,
    pub request_id: String,
}

impl std::fmt::Display for PermissionRequestDenied {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "Permission required for {}: {}",
            self.tool_name, self.permission
        )
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
        assert_eq!(
            m.can_execute_tool("read_file", None, None),
            (true, "Reading files is safe".to_string())
        );
        assert!(m.can_execute_tool("grep", None, None).0);
        assert!(m.can_execute_tool("lsp_diagnostics", None, None).0);
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
        m.add_rule(
            "write_file",
            PermissionAction::Deny,
            Some("no writes".into()),
            None,
            false,
        );
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
        let id = m.request_permission(
            "bash",
            serde_json::json!({"cmd": "ls"}),
            "shell:execute",
            None,
            None,
        );
        assert!(id.starts_with("req_"));
        assert_eq!(m.get_request(&id).unwrap().status, "pending");
        assert!(m.approve_request(&id, true, None));
        assert!(m.get_request(&id).is_none());
        assert!(m.can_execute_tool("bash", None, None).0);
    }

    #[test]
    fn request_deny_remember_adds_deny_rule() {
        let mut m = PermissionManager::new();
        let id = m.request_permission(
            "write_file",
            serde_json::json!({}),
            "file:write",
            None,
            None,
        );
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

    // Tests that mutate process env vars must run sequentially.
    static ENV_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());

    #[test]
    fn headless_allows_unlisted_tools() {
        let m = PermissionManager::headless();
        // `new()` asks for `bash` (falls through to the `*` ASK catch-all);
        // the headless catch-all is ALLOW.
        assert_eq!(
            m.can_execute_tool("bash", None, None),
            (true, "Rust headless default: allow".to_string())
        );
        assert!(m.can_execute_tool("totally_custom_tool", None, None).0);
        // Explicit allow rules are preserved.
        assert_eq!(
            m.can_execute_tool("read_file", None, None),
            (true, "Reading files is safe".to_string())
        );
    }

    #[test]
    fn headless_still_honours_explicit_rules() {
        let mut m = PermissionManager::headless();
        m.add_rule(
            "write_file",
            PermissionAction::Deny,
            Some("No writes".into()),
            None,
            false,
        );
        m.add_rule(
            "bash",
            PermissionAction::Ask,
            Some("Watch the shell".into()),
            None,
            false,
        );
        let (ok, msg) = m.can_execute_tool("write_file", None, None);
        assert!(!ok);
        assert_eq!(msg, "No writes");
        // ASK refuses headlessly (no prompt surface).
        let (ok, msg) = m.can_execute_tool("bash", None, None);
        assert!(!ok);
        assert!(msg.contains("Requires permission"));
        // The catch-all still applies to everything else.
        assert!(m.can_execute_tool("other_tool", None, None).0);
    }

    #[test]
    fn matching_action_follows_first_rule() {
        let mut m = PermissionManager::headless();
        m.add_rule("demo_*", PermissionAction::Allow, None, None, false);
        m.add_rule("demo_*", PermissionAction::Deny, None, None, false);
        // `add_rule` inserts at position 0, so the later rule matches first.
        assert_eq!(m.matching_action("demo_tool"), Some(PermissionAction::Deny));
        // Unlisted tools fall through to the headless catch-all.
        assert_eq!(
            m.matching_action("unlisted_tool"),
            Some(PermissionAction::Allow)
        );
    }

    #[test]
    fn env_rules_take_precedence_over_headless_default() {
        let _guard = ENV_LOCK.lock().unwrap();
        std::env::set_var("APEX_PERMISSION_DENY", "env_deny_tool");
        std::env::set_var("APEX_PERMISSION_ASK", "env_ask_tool");
        let mut m = PermissionManager::headless();
        m.install_env_rules();
        // DENY wins over the headless allow catch-all.
        let (ok, msg) = m.can_execute_tool("env_deny_tool", None, None);
        assert!(!ok);
        assert!(msg.contains("APEX_PERMISSION_DENY"));
        // ASK wins too (and refuses headlessly).
        let (ok, msg) = m.can_execute_tool("env_ask_tool", None, None);
        assert!(!ok);
        assert!(msg.contains("Requires permission"));
        // Unmatched tools stay allowed.
        assert!(m.can_execute_tool("env_free_tool", None, None).0);
        std::env::remove_var("APEX_PERMISSION_DENY");
        std::env::remove_var("APEX_PERMISSION_ASK");
    }

    #[test]
    fn dispatch_gate_refuses_global_deny_rule() {
        // A made-up tool: the headless global manager allows it.
        assert!(dispatch_gate("rm_rf_tool").0);
        let mut manager = PERMISSION_MANAGER.lock().unwrap();
        manager.add_rule(
            "rm_rf_tool",
            PermissionAction::Deny,
            Some("Test deny rule".into()),
            None,
            false,
        );
        drop(manager);
        let (ok, msg) = dispatch_gate("rm_rf_tool");
        assert!(!ok);
        assert!(msg.contains("Test deny rule"));
        // Cleanup: restore the headless default for the other test threads.
        let mut manager = PERMISSION_MANAGER.lock().unwrap();
        assert!(manager.remove_rule("rm_rf_tool", PermissionAction::Deny));
        drop(manager);
        assert!(dispatch_gate("rm_rf_tool").0);
    }

    #[test]
    fn dispatch_gate_allows_headless_default() {
        // `new()` would ask for `bash`; the global headless manager allows it.
        let (ok, reason) = dispatch_gate("bash");
        assert!(ok);
        assert!(reason.is_empty());
    }
}
