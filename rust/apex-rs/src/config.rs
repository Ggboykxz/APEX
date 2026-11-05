use anyhow::{anyhow, Result};
use serde_json::{Map, Value};
use std::env;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

// ─────────────────────────────────────────────────────────────────────
// home_dir — existing helper (unchanged)
// ─────────────────────────────────────────────────────────────────────

/// Resolve the user's home directory.
///
/// `HOME`/`USERPROFILE` take precedence over the platform lookup so hermetic
/// CLI tests can redirect `~/.apex` by setting the usual variables.
/// `dirs::home_dir()` remains the fallback (Windows known-folder API, etc.).
pub fn home_dir() -> Option<PathBuf> {
    for key in ["HOME", "USERPROFILE"] {
        if let Ok(value) = env::var(key) {
            if !value.trim().is_empty() {
                return Some(PathBuf::from(value));
            }
        }
    }
    dirs::home_dir()
}

/// Extra directories allowed for `{file:...}` interpolation (e.g. project dir).
static EXTRA_ALLOWED_DIRS: Mutex<Vec<PathBuf>> = Mutex::new(Vec::new());

/// Apply OpenCode→APEX env var aliases, matching Python's
/// `_apply_opencode_env_aliases` so an existing OpenCode setup works as-is.
/// Only sets an APEX var when the corresponding OPENCODE var is set and the
/// APEX var is not already set.
fn apply_opencode_aliases() {
    let map = [
        ("OPENCODE_CONFIG", "APEX_CONFIG"),
        ("OPENCODE_CONFIG_DIR", "APEX_CONFIG_DIR"),
        ("OPENCODE_CONFIG_CONTENT", "APEX_CONFIG_CONTENT"),
    ];
    for (opencode_var, apex_var) in map {
        if env::var_os(apex_var).is_none() {
            if let Some(v) = env::var_os(opencode_var) {
                // SAFETY: env is process-global and this only runs on config load.
                unsafe { env::set_var(apex_var, v) };
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────
// Legacy Config (still used by main.rs)
// ─────────────────────────────────────────────────────────────────────

#[derive(Clone, Default)]
pub struct Config {
    pub model: String,
    pub api_key: String,
    pub base_url: String,
    pub cwd: PathBuf,
    pub denied_tools: Vec<String>,
    pub theme: String,
}
}

impl Default for Config {
    fn default() -> Self {
        Config {
            model: String::new(),
            api_key: String::new(),
            base_url: String::new(),
            cwd: PathBuf::new(),
            denied_tools: Vec::new(),
            theme: String::new(),
        }
    }
}
    pub theme: String,
    pub auto_compact: bool,
    pub compact_threshold: usize,
    pub theme: String,
    pub keybinds: std::collections::HashMap<String, String>,
}

impl Config {
    pub fn from_env() -> Self {
        let model = env::var("APEX_MODEL").unwrap_or_else(|_| "gpt-4o-mini".to_string());
        let api_key = env::var("APEX_API_KEY")
            .or_else(|_| env::var("OPENAI_API_KEY"))
            .unwrap_or_default();
        let base_url =
            env::var("APEX_BASE_URL").unwrap_or_else(|_| "https://api.openai.com/v1".to_string());
        let cwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
        let denied_tools = env::var("APEX_DENIED_TOOLS")
            .map(|v| {
                v.split(',')
                    .map(|s| s.trim().to_string())
                    .filter(|s| !s.is_empty())
                    .collect()
            })
            .unwrap_or_default();
        let auto_compact = env::var("APEX_AUTO_COMPACT")
            .map(|v| v != "0" && v.to_lowercase() != "false")
            .unwrap_or(true);
        let compact_threshold = env::var("APEX_COMPACT_THRESHOLD")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(20);
        let theme = env::var("APEX_THEME").unwrap_or_else(|_| "default".to_string());
        let keybinds = std::collections::HashMap::new();
        Self {
            model,
            api_key,
            base_url,
            cwd,
            denied_tools,
            auto_compact,
            compact_threshold,
            theme,
            keybinds,
        }
    }
}

// ─────────────────────────────────────────────────────────────────────
// JSONC stripping
// ─────────────────────────────────────────────────────────────────────

/// Strip C-style comments from a JSONC string, preserving string contents.
///
/// Handles `//` line comments and `/* */` block comments. A `//` inside a
/// JSON string literal is preserved (e.g. URLs). Also strips trailing commas
/// before `}` or `]`.
pub fn strip_jsonc_comments(text: &str) -> String {
    let mut result = String::with_capacity(text.len());
    let mut chars = text.chars().peekable();
    let mut in_string = false;
    let mut escape_next = false;

    while let Some(ch) = chars.next() {
        if in_string {
            result.push(ch);
            if escape_next {
                escape_next = false;
            } else if ch == '\\' {
                escape_next = true;
            } else if ch == '"' {
                in_string = false;
            }
            continue;
        }

        // Not in a string
        if ch == '"' {
            in_string = true;
            result.push(ch);
            continue;
        }

        // Check for // line comment
        if ch == '/' && chars.peek() == Some(&'/') {
            // Consume until end of line
            for c in chars.by_ref() {
                if c == '\n' {
                    break;
                }
            }
            continue;
        }

        // Check for /* block comment */
        if ch == '/' && chars.peek() == Some(&'*') {
            // Consume until */
            chars.next(); // consume *
            while let Some(c) = chars.next() {
                if c == '*' && chars.peek() == Some(&'/') {
                    chars.next(); // consume /
                    break;
                }
            }
            continue;
        }

        result.push(ch);
    }

    // Now strip trailing commas (before } or ])
    strip_trailing_commas(&result)
}

/// Remove trailing commas that appear before `}` or `]`, preserving strings.
fn strip_trailing_commas(text: &str) -> String {
    let mut result = String::with_capacity(text.len());
    let mut chars = text.chars().peekable();
    let mut in_string = false;
    let mut escape_next = false;

    while let Some(ch) = chars.next() {
        if in_string {
            result.push(ch);
            if escape_next {
                escape_next = false;
            } else if ch == '\\' {
                escape_next = true;
            } else if ch == '"' {
                in_string = false;
            }
            continue;
        }

        if ch == '"' {
            in_string = true;
            result.push(ch);
            continue;
        }

        if ch == ',' {
            // Look ahead for } or ] (skipping whitespace)
            let mut lookahead = chars.clone();
            let mut found_brace = false;
            while let Some(&next) = lookahead.peek() {
                if next.is_whitespace() {
                    lookahead.next();
                } else if next == '}' || next == ']' {
                    found_brace = true;
                    break;
                } else {
                    break;
                }
            }

            if found_brace {
                // Skip this comma
                continue;
            }
        }

        result.push(ch);
    }

    result
}

/// Parse a JSONC string into a serde_json::Value.
pub fn parse_jsonc(text: &str) -> Result<Value> {
    let cleaned = strip_jsonc_comments(text);
    let value: Value = serde_json::from_str(&cleaned)?;
    Ok(value)
}

// ─────────────────────────────────────────────────────────────────────
// Variable substitution
// ─────────────────────────────────────────────────────────────────────

/// Recursively substitute {env:VAR} and {file:PATH} variables in a Value.
pub fn substitute_vars(value: &Value, seen: &mut Vec<PathBuf>) -> Value {
    match value {
        Value::String(s) => Value::String(substitute_string(s, seen)),
        Value::Array(arr) => Value::Array(arr.iter().map(|v| substitute_vars(v, seen)).collect()),
        Value::Object(obj) => {
            let mut new_obj = Map::new();
            for (k, v) in obj {
                new_obj.insert(k.clone(), substitute_vars(v, seen));
            }
            Value::Object(new_obj)
        }
        _ => value.clone(),
    }
}

/// Substitute variables in a single string.
fn substitute_string(s: &str, seen: &mut Vec<PathBuf>) -> String {
    // Process {env:VAR} first
    let mut result = substitute_env_in_string(s);
    // Then {file:PATH}
    result = substitute_file_in_string(&result, seen);
    result
}

/// Replace {env:VAR} patterns in a string.
/// If the env var is not found, returns empty string (mirrors Python).
fn substitute_env_in_string(s: &str) -> String {
    let mut result = String::new();
    let mut remaining = s;

    while let Some(start) = remaining.find("{env:") {
        // Copy everything before the match
        result.push_str(&remaining[..start]);
        remaining = &remaining[start + 5..]; // skip past "{env:"

        if let Some(end) = remaining.find('}') {
            let var_name = &remaining[..end].trim();
            let val = env::var(var_name).unwrap_or_default();
            result.push_str(&val);
            remaining = &remaining[end + 1..];
        } else {
            // No closing brace, keep the rest as-is
            result.push_str("{env:");
            result.push_str(remaining);
            break;
        }
    }
    result.push_str(remaining);
    result
}

/// Replace {file:PATH} patterns in a string.
/// Expands ~ to home directory. Returns empty string if file doesn't exist
/// or path is not allowed.
fn substitute_file_in_string(s: &str, seen: &mut Vec<PathBuf>) -> String {
    let mut result = String::new();
    let mut remaining = s;

    while let Some(start) = remaining.find("{file:") {
        // Copy everything before the match
        result.push_str(&remaining[..start]);
        remaining = &remaining[start + 6..]; // skip past "{file:"

        if let Some(end) = remaining.find('}') {
            let path_str = &remaining[..end].trim();
            let path = expand_path(path_str);
            if path.is_none() && seen.contains(&PathBuf::from(path_str)) {
                result.push_str("");
            } else if let Some(ref p) = path {
                if seen.contains(p) {
                    result.push_str("");
                } else if p.is_file() && is_path_allowed(p) {
                    if let Ok(content) = std::fs::read_to_string(p) {
                        seen.push(p.clone());
                        let substituted = substitute_string(&content, seen);
                        seen.pop();
                        result.push_str(&substituted);
                    } else {
                        result.push_str("");
                    }
                } else {
                    result.push_str("");
                }
            } else {
                result.push_str("");
            }
            remaining = &remaining[end + 1..];
        } else {
            result.push_str("{file:");
            result.push_str(remaining);
            break;
        }
    }
    result.push_str(remaining);
    result
}

/// Expand ~ and environment variables in a path string.
fn expand_path(path_str: &str) -> Option<PathBuf> {
    let s = path_str.trim();
    if let Some(rest) = s.strip_prefix("~") {
        let home = home_dir()?;
        let rest = rest.trim_start_matches(['/', '\\']);
        Some(home.join(rest))
    } else {
        Some(PathBuf::from(s))
    }
}

/// Check if a path is in an allowed directory.
fn is_path_allowed(p: &Path) -> bool {
    let resolved = p.canonicalize().unwrap_or_else(|_| p.to_path_buf());

    // Get allowed dirs
    let home = match home_dir() {
        Some(h) => h,
        None => return false,
    };

    let mut allowed_dirs: Vec<PathBuf> =
        vec![home.join(".config").join("apex"), home.join(".apex")];

    // Include any project-specific allowed dirs registered via load_config.
    if let Ok(extra) = EXTRA_ALLOWED_DIRS.lock() {
        allowed_dirs.extend(extra.clone());
    }

    for d in &allowed_dirs {
        let d_resolved = d.canonicalize().unwrap_or_else(|_| d.clone());
        if d_resolved == resolved || d_resolved.ancestors().any(|a| a == resolved) {
            return true;
        }
        if resolved.starts_with(&d_resolved) {
            return true;
        }
    }

    false
}

// ─────────────────────────────────────────────────────────────────────
// Deep merge
// ─────────────────────────────────────────────────────────────────────

/// Deep merge `source` into `target`. Objects are merged recursively.
/// Scalars and arrays replace.
pub fn deep_merge(target: &mut Value, source: &Value) {
    match (target.clone(), source) {
        (Value::Object(_), Value::Object(_)) => {
            if let (Value::Object(target_obj), Value::Object(source_obj)) = (target, source) {
                for (key, val) in source_obj {
                    if let Some(existing) = target_obj.get_mut(key) {
                        if existing.is_object() && val.is_object() {
                            deep_merge(existing, val);
                        } else {
                            target_obj.insert(key.clone(), val.clone());
                        }
                    } else {
                        target_obj.insert(key.clone(), val.clone());
                    }
                }
            }
        }
        _ => {
            *target = source.clone();
        }
    }
}

/// Merge defaults into target (target values take precedence).
pub fn deep_merge_defaults(target: &mut Value, defaults: &Value) {
    if let (Value::Object(target_obj), Value::Object(defaults_obj)) = (target, defaults) {
        for (key, val) in defaults_obj {
            if !target_obj.contains_key(key) {
                if let Value::Object(_) = val {
                    let mut new_val = val.clone();
                    // Recursively merge defaults for new sub-objects
                    deep_merge_defaults(&mut new_val, val);
                    target_obj.insert(key.clone(), new_val);
                } else {
                    target_obj.insert(key.clone(), val.clone());
                }
            } else if let Some(existing) = target_obj.get_mut(key) {
                if existing.is_object() && val.is_object() {
                    deep_merge_defaults(existing, val);
                }
                // For non-objects or mismatched types, keep existing
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────
// Defaults
// ─────────────────────────────────────────────────────────────────────

lazy_static::lazy_static! {
    static ref DEFAULTS: Value = {
        let shell = env::var("SHELL").unwrap_or_else(|_| "/bin/bash".to_string());
        serde_json::json!({
            "model": "or-gpt4o-mini",
            "small_model": null,
            "provider": {},
            "agent": {},
            "command": {},
            "server": {
                "port": 8080,
                "hostname": "127.0.0.1",
                "cors": {"origin": "*", "methods": "*", "headers": "*"},
            },
            "permission": {},
            "tools": {},
            "lsp": false,
            "mcp": {},
            "plugin": [],
            "formatter": false,
            "snapshot": true,
            "autoupdate": true,
            "share": "manual",
            "shell": shell,
            "compaction": {
                "auto": true,
                "prune": true,
                "reserved": 10000,
            },
            "context": {
                "max_repo_map_tokens": 2000,
                "prune_tool_outputs": true,
                "tool_output_max_chars": 4000,
                "keep_recent_tool_results": 3,
            },
            "watcher": {
                "ignore": [
                    "**/node_modules/**",
                    "**/.git/**",
                    "**/__pycache__/**",
                    "**/.venv/**",
                    "**/venv/**",
                    "**/dist/**",
                    "**/build/**",
                    "**/.next/**",
                    "**/target/**",
                ],
            },
            "theme": "apex",
            "keybinds": {},
            "instructions": [],
            "disabled_providers": [],
            "enabled_providers": [],
            "default_agent": "build",
        })
    };
}

// ─────────────────────────────────────────────────────────────────────
// Config paths
// ─────────────────────────────────────────────────────────────────────

/// Returns the config directory: ~/.config/apex
pub fn config_dir() -> Option<PathBuf> {
    home_dir().map(|h| h.join(".config").join("apex"))
}

/// Returns the global config file path (apex.jsonc or apex.json)
pub fn global_config_path() -> Option<PathBuf> {
    let dir = config_dir()?;
    if dir.join("apex.jsonc").exists() {
        Some(dir.join("apex.jsonc"))
    } else if dir.join("apex.json").exists() {
        Some(dir.join("apex.json"))
    } else {
        None
    }
}

/// Old v1 config location: ~/.apex/config.json
pub fn old_config_path() -> Option<PathBuf> {
    home_dir().map(|h| h.join(".apex").join("config.json"))
}

/// Find project config file (apex.jsonc, apex.json, or opencode variants)
pub fn find_project_config(start: Option<&Path>) -> Option<PathBuf> {
    let cwd = match start {
        Some(p) => p.to_path_buf(),
        None => env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
    };

    for name in ["apex.jsonc", "apex.json", "opencode.jsonc", "opencode.json"] {
        let candidate = cwd.join(name);
        if candidate.is_file() {
            return Some(candidate);
        }
    }
    None
}

// ─────────────────────────────────────────────────────────────────────
// Load single JSON/JSONC file
// ─────────────────────────────────────────────────────────────────────

/// Load a JSON or JSONC file into a Value. Returns empty object on error.
pub fn load_json_file(path: &Path) -> Value {
    match std::fs::read_to_string(path) {
        Ok(text) => {
            if path.extension().is_some_and(|ext| ext == "jsonc") {
                parse_jsonc(&text).unwrap_or(Value::Object(Map::new()))
            } else {
                serde_json::from_str(&text).unwrap_or(Value::Object(Map::new()))
            }
        }
        Err(_) => Value::Object(Map::new()),
    }
}

// ─────────────────────────────────────────────────────────────────────
// Migration v1→v2
// ─────────────────────────────────────────────────────────────────────

/// Migrate old config from ~/.apex/config.json to ~/.config/apex/apex.jsonc.
/// Returns true if migration was performed.
pub fn migrate_v1_to_v2() -> bool {
    if global_config_path().is_some() {
        return false;
    }

    if let Some(old_path) = old_config_path() {
        if old_path.is_file() {
            if let Ok(old_data) = std::fs::read_to_string(&old_path) {
                if let Ok(value) = serde_json::from_str::<Value>(&old_data) {
                    let config_dir = match config_dir() {
                        Some(d) => d,
                        None => return false,
                    };
                    if std::fs::create_dir_all(&config_dir).is_ok() {
                        let target = config_dir.join("apex.jsonc");
                        let text = serde_json::to_string_pretty(&value).unwrap_or_default();
                        if std::fs::write(&target, &text).is_ok() {
                            // Create backup
                            let backup = old_path.with_extension("json.bak");
                            if !backup.exists() {
                                let _ = std::fs::copy(&old_path, &backup);
                            }
                            return true;
                        }
                    }
                }
            }
        }
    }
    false
}

// ─────────────────────────────────────────────────────────────────────
// Config loading & merging (hierarchy)
// ─────────────────────────────────────────────────────────────────────

/// Load and merge config from all layers (global → custom → project → inline).
pub fn load_config(project_dir: Option<&Path>) -> Value {
    apply_opencode_aliases();

    // Register the project directory (plus the standard home dirs) as an
    // allowed source for `{file:...}` interpolation — parity with Python's
    // `_init_allowed_dirs`.
    if let Ok(mut extra) = EXTRA_ALLOWED_DIRS.lock() {
        extra.clear();
        if let Some(p) = project_dir {
            if let Ok(resolved) = p.canonicalize() {
                extra.push(resolved);
            } else {
                extra.push(p.to_path_buf());
            }
        }
    }

    let mut layers: Vec<Value> = Vec::new();

    // 1) Global
    if let Some(global_path) = global_config_path() {
        layers.push(load_json_file(&global_path));
    }

    // 2) Custom from env
    if let Ok(custom_env) = env::var("APEX_CONFIG") {
        let custom_path = expand_path(&custom_env);
        if let Some(ref p) = custom_path {
            if p.is_file() {
                layers.push(load_json_file(p));
            }
        }
    }

    // 3) Project
    if let Some(project) = project_dir {
        if let Some(project_path) = find_project_config(Some(project)) {
            layers.push(load_json_file(&project_path));
        }
    } else if let Some(project_path) = find_project_config(None) {
        layers.push(load_json_file(&project_path));
    }

    // 4) Inline from env
    if let Ok(inline_raw) = env::var("APEX_CONFIG_CONTENT") {
        if let Ok(inline) = parse_jsonc(&inline_raw) {
            if let Value::Object(_) = &inline {
                layers.push(inline);
            }
        }
    }

    // Merge layers (later overrides)
    let mut merged = Value::Object(Map::new());
    for layer in &layers {
        deep_merge(&mut merged, layer);
    }

    // Fill in defaults
    deep_merge_defaults(&mut merged, &DEFAULTS);

    // Normalize context config (parity with Python ApexConfig.context)
    if let Some(ctx) = merged.get("context").cloned() {
        merged["context"] = normalize_context_config(&ctx);
    }

    // Substitute variables
    let mut seen: Vec<PathBuf> = Vec::new();
    merged = substitute_vars(&merged, &mut seen);
    merged
}

// ─────────────────────────────────────────────────────────────────────
// Context config normalization
// ─────────────────────────────────────────────────────────────────────

/// Normalize the nested `context` config, validating and clamping integer keys,
/// and ensuring booleans are real booleans.
pub fn normalize_context_config(raw: &Value) -> Value {
    let mut context = DEFAULTS["context"].clone();

    if let Value::Object(raw_obj) = raw {
        let int_keys = [
            "max_repo_map_tokens",
            "tool_output_max_chars",
            "keep_recent_tool_results",
        ];

        for key in &int_keys {
            if let Some(val) = raw_obj.get(*key) {
                if let Some(n) = val.as_u64() {
                    context[key] = serde_json::json!(n);
                }
                // Non-integers are ignored, fall back to default
            }
        }

        if let Some(prune) = raw_obj.get("prune_tool_outputs") {
            if prune.is_boolean() {
                context["prune_tool_outputs"] = prune.clone();
            }
        }
    }

    context
}

// ─────────────────────────────────────────────────────────────────────
// Validation
// ─────────────────────────────────────────────────────────────────────

/// All valid top-level config keys.
const VALID_CONFIG_KEYS: &[&str] = &[
    "model",
    "small_model",
    "provider",
    "agent",
    "command",
    "server",
    "permission",
    "tools",
    "lsp",
    "mcp",
    "plugin",
    "formatter",
    "snapshot",
    "autoupdate",
    "share",
    "shell",
    "compaction",
    "context",
    "watcher",
    "theme",
    "keybinds",
    "instructions",
    "disabled_providers",
    "enabled_providers",
    "default_agent",
];

/// A validation error with location and message.
#[derive(Debug, Clone)]
pub struct ConfigError {
    pub key: String,
    pub path: String,
    pub message: String,
}

impl std::fmt::Display for ConfigError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "config[{}] ({}): {}", self.key, self.path, self.message)
    }
}

/// Validate a config Value against the schema.
/// Returns a list of errors (empty if valid).
pub fn validate_config(value: &Value) -> Vec<ConfigError> {
    let mut errors = Vec::new();

    if let Value::Object(obj) = value {
        for key in obj.keys() {
            if !VALID_CONFIG_KEYS.contains(&key.as_str()) {
                errors.push(ConfigError {
                    key: key.clone(),
                    path: format!("root.{}", key),
                    message: "unknown configuration key".to_string(),
                });
            }
        }

        // Validate share
        if let Some(share) = obj.get("share") {
            if let Value::String(s) = share {
                if !["manual", "auto", "disabled"].contains(&s.as_str()) {
                    errors.push(ConfigError {
                        key: "share".to_string(),
                        path: "root.share".to_string(),
                        message: format!("must be 'manual', 'auto', or 'disabled', got '{}'", s),
                    });
                }
            } else {
                errors.push(ConfigError {
                    key: "share".to_string(),
                    path: "root.share".to_string(),
                    message: "must be a string".to_string(),
                });
            }
        }

        // Validate server
        if let Some(Value::Object(server_obj)) = obj.get("server") {
            if let Some(port) = server_obj.get("port") {
                if !port.is_u64() {
                    errors.push(ConfigError {
                        key: "server.port".to_string(),
                        path: "server.port".to_string(),
                        message: "must be an integer".to_string(),
                    });
                }
            }
            if let Some(hostname) = server_obj.get("hostname") {
                if !hostname.is_string() {
                    errors.push(ConfigError {
                        key: "server.hostname".to_string(),
                        path: "server.hostname".to_string(),
                        message: "must be a string".to_string(),
                    });
                }
            }
        }

        // Validate compaction
        if let Some(Value::Object(comp_obj)) = obj.get("compaction") {
            for int_key in ["auto", "prune"] {
                if let Some(val) = comp_obj.get(int_key) {
                    if !val.is_boolean() {
                        errors.push(ConfigError {
                            key: format!("compaction.{}", int_key),
                            path: format!("compaction.{}", int_key),
                            message: "must be a boolean".to_string(),
                        });
                    }
                }
            }
            if let Some(val) = comp_obj.get("reserved") {
                if !val.is_u64() {
                    errors.push(ConfigError {
                        key: "compaction.reserved".to_string(),
                        path: "compaction.reserved".to_string(),
                        message: "must be an integer".to_string(),
                    });
                }
            }
        }

        // Validate context
        if let Some(Value::Object(ctx_obj)) = obj.get("context") {
            for int_key in [
                "max_repo_map_tokens",
                "tool_output_max_chars",
                "keep_recent_tool_results",
            ] {
                if let Some(val) = ctx_obj.get(int_key) {
                    if val.is_boolean() {
                        errors.push(ConfigError {
                            key: format!("context.{}", int_key),
                            path: format!("context.{}", int_key),
                            message: "must be an integer, not boolean".to_string(),
                        });
                    } else if !val.is_u64() {
                        errors.push(ConfigError {
                            key: format!("context.{}", int_key),
                            path: format!("context.{}", int_key),
                            message: "must be an integer".to_string(),
                        });
                    }
                }
            }
        }

        // Validate lsp
        if let Some(lsp) = obj.get("lsp") {
            if !lsp.is_boolean() && !lsp.is_object() {
                errors.push(ConfigError {
                    key: "lsp".to_string(),
                    path: "root.lsp".to_string(),
                    message: "must be a boolean or an object".to_string(),
                });
            }
        }

        // Validate formatter
        if let Some(formatter) = obj.get("formatter") {
            if !formatter.is_boolean() && !formatter.is_object() {
                errors.push(ConfigError {
                    key: "formatter".to_string(),
                    path: "root.formatter".to_string(),
                    message: "must be a boolean or an object".to_string(),
                });
            }
        }

        // Validate arrays
        for arr_key in [
            "plugin",
            "instructions",
            "disabled_providers",
            "enabled_providers",
        ] {
            if let Some(val) = obj.get(arr_key) {
                if !val.is_array() {
                    errors.push(ConfigError {
                        key: arr_key.to_string(),
                        path: format!("root.{}", arr_key),
                        message: "must be an array".to_string(),
                    });
                }
            }
        }

        // Validate provider/agent/command/permission/tools/mcp/keybinds are objects
        for obj_key in [
            "provider",
            "agent",
            "command",
            "permission",
            "tools",
            "mcp",
            "keybinds",
        ] {
            if let Some(val) = obj.get(obj_key) {
                if !val.is_object() {
                    errors.push(ConfigError {
                        key: obj_key.to_string(),
                        path: format!("root.{}", obj_key),
                        message: "must be an object".to_string(),
                    });
                }
            }
        }

        // Validate model and theme are strings
        for str_key in ["model", "theme", "shell", "default_agent"] {
            if let Some(val) = obj.get(str_key) {
                if !val.is_string() {
                    errors.push(ConfigError {
                        key: str_key.to_string(),
                        path: format!("root.{}", str_key),
                        message: "must be a string".to_string(),
                    });
                }
            }
        }

        // Validate booleans
        for bool_key in ["snapshot", "autoupdate"] {
            if let Some(val) = obj.get(bool_key) {
                if !val.is_boolean() {
                    errors.push(ConfigError {
                        key: bool_key.to_string(),
                        path: format!("root.{}", bool_key),
                        message: "must be a boolean".to_string(),
                    });
                }
            }
        }
    }

    errors
}

// ─────────────────────────────────────────────────────────────────────
// CLI helpers
// ─────────────────────────────────────────────────────────────────────

/// Show the merged config as pretty JSON.
pub fn cmd_config_show(json: bool) -> Result<()> {
    let config = load_config(None);

    if json {
        println!("{}", serde_json::to_string_pretty(&config)?);
    } else {
        // Pretty print
        println!("{}", serde_json::to_string_pretty(&config)?);
    }
    Ok(())
}

/// Validate the config and report errors.
pub fn cmd_config_validate(path: Option<&str>) -> Result<()> {
    let config = if let Some(p) = path {
        let p = expand_path(p).unwrap_or_else(|| PathBuf::from(p));
        load_json_file(&p)
    } else {
        load_config(None)
    };

    let errors = validate_config(&config);

    if errors.is_empty() {
        println!("Config is valid");
        Ok(())
    } else {
        for err in &errors {
            eprintln!("ERROR: {}", err);
        }
        Err(anyhow!(
            "Config validation failed with {} error(s)",
            errors.len()
        ))
    }
}

/// Migrate old config format to new.
pub fn cmd_config_migrate(path: Option<&str>) -> Result<()> {
    if let Some(p) = path {
        let p = expand_path(p).unwrap_or_else(|| PathBuf::from(p));
        if !p.is_file() {
            return Err(anyhow!("Config file not found: {}", p.display()));
        }
        let value = load_json_file(&p);
        let text = serde_json::to_string_pretty(&value)?;
        let target = p;
        std::fs::write(&target, &text)?;
        println!("Migrated config to: {}", target.display());
        Ok(())
    } else if migrate_v1_to_v2() {
        println!("Migrated v1 config (~/.apex/config.json) to ~/.config/apex/apex.jsonc");
        Ok(())
    } else {
        println!("No v1 config found to migrate");
        Ok(())
    }
}

// ─────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    // Helper to set env vars safely in tests
    fn set_env_var(key: &str, value: &str) -> (String, String) {
        let old = env::var(key).ok();
        // SAFETY: We're in a test with a mutex lock
        unsafe { env::set_var(key, value) };
        (key.to_string(), old.unwrap_or_default())
    }

    fn restore_env_var(key: &str, old: &str) {
        if old.is_empty() {
            // SAFETY: We're in a test with a mutex lock
            unsafe { env::remove_var(key) };
        } else {
            // SAFETY: We're in a test with a mutex lock
            unsafe { env::set_var(key, old) };
        }
    }

    // ── existing tests ──

    #[test]
    fn defaults() {
        let _g = ENV_LOCK.lock().unwrap();
        env::set_var("APEX_MODEL", "gpt-4o-mini");
        env::set_var("APEX_DENIED_TOOLS", "");
        env::set_var("APEX_AUTO_COMPACT", "true");
        env::set_var("APEX_COMPACT_THRESHOLD", "20");
        let c = Config::from_env();
        assert_eq!(c.model, "gpt-4o-mini");
        assert!(c.denied_tools.is_empty());
        assert!(c.auto_compact);
        assert_eq!(c.compact_threshold, 20);
        env::remove_var("APEX_MODEL");
        env::remove_var("APEX_DENIED_TOOLS");
        env::remove_var("APEX_AUTO_COMPACT");
        env::remove_var("APEX_COMPACT_THRESHOLD");
    }

    #[test]
    fn denied_tools_parsed() {
        let _g = ENV_LOCK.lock().unwrap();
        env::set_var("APEX_DENIED_TOOLS", "run_command, write_file");
        let c = Config::from_env();
        assert_eq!(c.denied_tools, vec!["run_command", "write_file"]);
        env::remove_var("APEX_DENIED_TOOLS");
    }

    static ENV_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());

    // ── JSONC tests ──

    #[test]
    fn jsonc_strips_line_comments() {
        let input = r#"{"key": "value" // comment"#;
        let result = strip_jsonc_comments(input);
        assert_eq!(result, r#"{"key": "value" "#);
    }

    #[test]
    fn jsonc_strips_block_comments() {
        let input = r#"{"key": /* comment */ "value"}"#;
        let result = strip_jsonc_comments(input);
        assert_eq!(result, r#"{"key":  "value"}"#);
    }

    #[test]
    fn jsonc_preserves_string_with_url() {
        let input = r#"{"url": "http://example.com//path"}"#;
        let result = strip_jsonc_comments(input);
        assert_eq!(result, input);
    }

    #[test]
    fn jsonc_trailing_comma() {
        let input = r#"{"key": "value",}"#;
        let value: Value = parse_jsonc(input).unwrap();
        assert_eq!(value["key"], "value");
    }

    #[test]
    fn jsonc_full_parse() {
        let input = r#"{
            // This is a comment
            "model": "gpt-4o", /* inline */
            "keybinds": {
                "ctrl+s": "save", // save shortcut
            },
        }"#;
        let value = parse_jsonc(input).unwrap();
        assert_eq!(value["model"], "gpt-4o");
        assert_eq!(value["keybinds"]["ctrl+s"], "save");
    }

    #[test]
    fn jsonc_string_with_comment_inside() {
        let input = r#"{"url": "http://example.com/path//not-a-comment"}"#;
        let result = strip_jsonc_comments(input);
        assert_eq!(result, input);
    }

    #[test]
    fn jsonc_escaped_quotes() {
        let input = r#"{"msg": "He said \"hello\" // not a comment"}"#;
        let result = strip_jsonc_comments(input);
        assert_eq!(result, input);
    }

    // ── Deep merge tests ──

    #[test]
    fn deep_merge_objects_recursive() {
        let mut target: Value = serde_json::json!({
            "a": {"x": 1, "y": 2},
            "b": 3
        });
        let source: Value = serde_json::json!({
            "a": {"x": 10, "z": 30},
            "c": 4
        });
        deep_merge(&mut target, &source);
        assert_eq!(target["a"]["x"], 10);
        assert_eq!(target["a"]["y"], 2);
        assert_eq!(target["a"]["z"], 30);
        assert_eq!(target["b"], 3);
        assert_eq!(target["c"], 4);
    }

    #[test]
    fn deep_merge_scalars_replace() {
        let mut target: Value = serde_json::json!({"a": 1, "b": [1, 2]});
        let source: Value = serde_json::json!({"a": 2, "b": [3, 4]});
        deep_merge(&mut target, &source);
        assert_eq!(target["a"], 2);
        assert_eq!(target["b"], serde_json::json!([3, 4]));
    }

    #[test]
    fn deep_merge_defaults_keeps_existing() {
        let mut target: Value = serde_json::json!({"a": 1, "b": {"x": 10}});
        let defaults: Value = serde_json::json!({"a": 99, "b": {"x": 1, "y": 2}, "c": 3});
        deep_merge_defaults(&mut target, &defaults);
        assert_eq!(target["a"], 1); // kept
        assert_eq!(target["b"]["x"], 10); // kept
        assert_eq!(target["b"]["y"], 2); // added from defaults
        assert_eq!(target["c"], 3); // added from defaults
    }

    // ── Hierarchy / precedence tests ──

    #[test]
    fn precedence_project_overrides_global() {
        let _g = ENV_LOCK.lock().unwrap();

        // Set up temp HOME
        let home = TempDir::new().unwrap();
        let config_dir = home.path().join(".config").join("apex");
        std::fs::create_dir_all(&config_dir).unwrap();

        // Global config
        let global_path = config_dir.join("apex.json");
        std::fs::write(
            &global_path,
            r#"{"model": "global-model", "theme": "global-theme"}"#,
        )
        .unwrap();

        // Project config in temp dir
        let proj = TempDir::new().unwrap();
        let proj_config = proj.path().join("apex.json");
        std::fs::write(&proj_config, r#"{"model": "proj-model"}"#).unwrap();

        // Set HOME
        set_env_var("HOME", home.path().to_str().unwrap());
        set_env_var("USERPROFILE", home.path().to_str().unwrap());

        let config = load_config(Some(proj.path()));
        assert_eq!(config["model"], "proj-model");
        assert_eq!(config["theme"], "global-theme"); // inherited from global

        restore_env_var("HOME", "");
        restore_env_var("USERPROFILE", "");
    }

    #[test]
    fn precedence_inline_overrides_all() {
        let _g = ENV_LOCK.lock().unwrap();

        let home = TempDir::new().unwrap();
        set_env_var("HOME", home.path().to_str().unwrap());
        set_env_var("USERPROFILE", home.path().to_str().unwrap());

        let global_path = home.path().join(".config").join("apex");
        std::fs::create_dir_all(&global_path).unwrap();
        std::fs::write(global_path.join("apex.json"), r#"{"model": "global"}"#).unwrap();

        // Inline config
        set_env_var("APEX_CONFIG_CONTENT", r#"{"model": "inline"}"#);

        let config = load_config(None);
        assert_eq!(config["model"], "inline");

        env::remove_var("APEX_CONFIG_CONTENT");
        restore_env_var("HOME", "");
        restore_env_var("USERPROFILE", "");
    }

    #[test]
    fn precedence_custom_env_overrides_global() {
        let _g = ENV_LOCK.lock().unwrap();

        let home = TempDir::new().unwrap();
        let config_dir = home.path().join(".config").join("apex");
        std::fs::create_dir_all(&config_dir).unwrap();

        // Global
        std::fs::write(config_dir.join("apex.json"), r#"{"model": "global"}"#).unwrap();

        // Custom
        let custom = TempDir::new().unwrap();
        let custom_path = custom.path().join("apex.json");
        std::fs::write(&custom_path, r#"{"model": "custom"}"#).unwrap();

        set_env_var("HOME", home.path().to_str().unwrap());
        set_env_var("USERPROFILE", home.path().to_str().unwrap());
        set_env_var("APEX_CONFIG", custom_path.to_str().unwrap());

        let config = load_config(None);
        assert_eq!(config["model"], "custom");

        env::remove_var("APEX_CONFIG");
        restore_env_var("HOME", "");
        restore_env_var("USERPROFILE", "");
    }

    // ── Interpolation tests ──

    #[test]
    fn interpolation_env_var() {
        let _g = ENV_LOCK.lock().unwrap();

        set_env_var("TEST_MODEL_VAR", "from-env");
        let input = serde_json::json!({"model": "{env:TEST_MODEL_VAR}"});
        let mut seen = Vec::new();
        let result = substitute_vars(&input, &mut seen);
        assert_eq!(result["model"], "from-env");

        env::remove_var("TEST_MODEL_VAR");
    }

    #[test]
    fn interpolation_env_var_missing() {
        let _g = ENV_LOCK.lock().unwrap();

        env::remove_var("NONEXISTENT_VAR_12345");
        let input = serde_json::json!({"model": "{env:NONEXISTENT_VAR_12345}"});
        let result = substitute_vars(&input, &mut Vec::new());
        assert_eq!(result["model"], "");
    }

    #[test]
    fn interpolation_file_var() {
        let _g = ENV_LOCK.lock().unwrap();

        let home = TempDir::new().unwrap();
        set_env_var("HOME", home.path().to_str().unwrap());
        set_env_var("USERPROFILE", home.path().to_str().unwrap());

        let config_dir = home.path().join(".config").join("apex");
        std::fs::create_dir_all(&config_dir).unwrap();

        let key_file = config_dir.join("api_key.txt");
        std::fs::write(&key_file, "my-secret-key").unwrap();

        let input = serde_json::json!({"key": "{file:~/.config/apex/api_key.txt}"});
        let mut seen = Vec::new();
        let result = substitute_vars(&input, &mut seen);
        assert_eq!(result["key"], "my-secret-key");

        restore_env_var("HOME", "");
        restore_env_var("USERPROFILE", "");
    }

    #[test]
    fn interpolation_nested() {
        let input = serde_json::json!({
            "models": ["{env:TEST_NESTED_VAR}", "static"],
            "nested": {"key": "{env:TEST_NESTED_VAR}"}
        });
        set_env_var("TEST_NESTED_VAR", "nested-value");
        let result = substitute_vars(&input, &mut Vec::new());
        assert_eq!(result["models"][0], "nested-value");
        assert_eq!(result["nested"]["key"], "nested-value");
        env::remove_var("TEST_NESTED_VAR");
    }

    // ── Validation tests ──

    #[test]
    fn validation_valid_config() {
        let config = serde_json::json!({
            "model": "gpt-4o",
            "theme": "apex",
            "share": "manual",
            "snapshot": true,
            "server": {"port": 8080, "hostname": "127.0.0.1"},
            "compaction": {"auto": true, "prune": false, "reserved": 10000},
            "context": {"max_repo_map_tokens": 2000, "prune_tool_outputs": true},
            "lsp": false,
            "formatter": true,
            "plugin": [],
            "instructions": [],
            "disabled_providers": [],
            "enabled_providers": [],
            "default_agent": "build",
            "shell": "/bin/bash",
            "autoupdate": true,
            "keybinds": {},
            "agent": {},
            "command": {},
            "permission": {},
            "tools": {},
            "mcp": {},
            "small_model": null,
            "provider": {},
            "watcher": {"ignore": ["**/node_modules/**"]},
        });
        let errors = validate_config(&config);
        assert!(errors.is_empty(), "Expected no errors, got: {:?}", errors);
    }

    #[test]
    fn validation_unknown_key() {
        let config = serde_json::json!({
            "unknown_key": "value"
        });
        let errors = validate_config(&config);
        assert!(!errors.is_empty());
        assert_eq!(errors[0].key, "unknown_key");
    }

    #[test]
    fn validation_bad_type() {
        let config = serde_json::json!({
            "model": 123
        });
        let errors = validate_config(&config);
        assert!(!errors.is_empty());
        assert_eq!(errors[0].key, "model");
    }

    #[test]
    fn validation_bad_share() {
        let config = serde_json::json!({
            "share": "invalid"
        });
        let errors = validate_config(&config);
        assert!(!errors.is_empty());
        assert_eq!(errors[0].key, "share");
    }

    #[test]
    fn validation_bad_lsp() {
        let config = serde_json::json!({
            "lsp": "not-a-bool-or-object"
        });
        let errors = validate_config(&config);
        assert!(!errors.is_empty());
        assert_eq!(errors[0].key, "lsp");
    }

    // ── Migration tests ──

    #[test]
    fn migration_v1_to_v2() {
        let _g = ENV_LOCK.lock().unwrap();

        let home = TempDir::new().unwrap();
        set_env_var("HOME", home.path().to_str().unwrap());
        set_env_var("USERPROFILE", home.path().to_str().unwrap());

        // Create old config
        let old_dir = home.path().join(".apex");
        std::fs::create_dir_all(&old_dir).unwrap();
        let old_config = old_dir.join("config.json");
        std::fs::write(&old_config, r#"{"model": "old-model"}"#).unwrap();

        // Migrate
        let migrated = migrate_v1_to_v2();
        assert!(migrated);

        // Verify new config exists
        let new_config = home.path().join(".config").join("apex").join("apex.jsonc");
        assert!(new_config.exists());

        let content = std::fs::read_to_string(&new_config).unwrap();
        let value: Value = serde_json::from_str(&content).unwrap();
        assert_eq!(value["model"], "old-model");

        restore_env_var("HOME", "");
        restore_env_var("USERPROFILE", "");
    }

    #[test]
    fn migration_skips_when_new_exists() {
        let _g = ENV_LOCK.lock().unwrap();

        let home = TempDir::new().unwrap();
        set_env_var("HOME", home.path().to_str().unwrap());
        set_env_var("USERPROFILE", home.path().to_str().unwrap());

        // Create new config
        let config_dir = home.path().join(".config").join("apex");
        std::fs::create_dir_all(&config_dir).unwrap();
        std::fs::write(config_dir.join("apex.json"), r#"{"model": "new"}"#).unwrap();

        // Create old config
        let old_dir = home.path().join(".apex");
        std::fs::create_dir_all(&old_dir).unwrap();
        std::fs::write(old_dir.join("config.json"), r#"{"model": "old"}"#).unwrap();

        let migrated = migrate_v1_to_v2();
        assert!(!migrated);

        restore_env_var("HOME", "");
        restore_env_var("USERPROFILE", "");
    }

    // ── Context normalization tests ──

    #[test]
    fn normalize_context_defaults() {
        let raw = serde_json::json!({});
        let result = normalize_context_config(&raw);
        assert_eq!(result["max_repo_map_tokens"], 2000);
        assert_eq!(result["prune_tool_outputs"], true);
    }

    #[test]
    fn normalize_context_clamps_negatives() {
        let raw = serde_json::json!({"max_repo_map_tokens": -5});
        let result = normalize_context_config(&raw);
        assert_eq!(result["max_repo_map_tokens"], 2000); // -5 is not u64, fallback to default
    }

    #[test]
    fn normalize_context_valid_int() {
        let raw = serde_json::json!({"max_repo_map_tokens": 5000});
        let result = normalize_context_config(&raw);
        assert_eq!(result["max_repo_map_tokens"], 5000);
    }

    #[test]
    fn normalize_context_ignores_boolean_for_int() {
        let raw = serde_json::json!({"max_repo_map_tokens": true});
        let result = normalize_context_config(&raw);
        assert_eq!(result["max_repo_map_tokens"], 2000); // boolean falls back to default
    }

    // ── Full hierarchy integration test ──

    #[test]
    fn full_hierarchy_merge() {
        let _g = ENV_LOCK.lock().unwrap();

        let home = TempDir::new().unwrap();
        set_env_var("HOME", home.path().to_str().unwrap());
        set_env_var("USERPROFILE", home.path().to_str().unwrap());

        // Global with base config
        let config_dir = home.path().join(".config").join("apex");
        std::fs::create_dir_all(&config_dir).unwrap();
        std::fs::write(
            config_dir.join("apex.json"),
            r#"{
            "model": "global-model",
            "compaction": {"auto": true, "reserved": 5000},
            "server": {"port": 8080}
        }"#,
        )
        .unwrap();

        // Inline override
        set_env_var(
            "APEX_CONFIG_CONTENT",
            r#"{
            "model": "inline-model",
            "compaction": {"reserved": 10000}
        }"#,
        );

        let config = load_config(None);

        // Inline overrides global
        assert_eq!(config["model"], "inline-model");
        // Nested deep merge
        assert_eq!(config["compaction"]["auto"], true); // inherited
        assert_eq!(config["compaction"]["reserved"], 10000); // overridden
                                                             // Global server preserved
        assert_eq!(config["server"]["port"], 8080);
        // Defaults applied
        assert_eq!(config["share"], "manual");
        assert_eq!(config["default_agent"], "build");

        env::remove_var("APEX_CONFIG_CONTENT");
        restore_env_var("HOME", "");
        restore_env_var("USERPROFILE", "");
    }

    // ── Path resolution tests ──

    #[test]
    fn expand_path_tilde() {
        let _g = ENV_LOCK.lock().unwrap();

        let home = TempDir::new().unwrap();
        set_env_var("HOME", home.path().to_str().unwrap());
        set_env_var("USERPROFILE", home.path().to_str().unwrap());

        let expanded = expand_path("~/.config/apex/test.json");
        assert!(expanded.is_some());
        let expanded = expanded.unwrap();
        assert!(expanded.starts_with(home.path()));

        restore_env_var("HOME", "");
        restore_env_var("USERPROFILE", "");
    }
}
