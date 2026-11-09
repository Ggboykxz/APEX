//! Port of `apex/config_tools.py` — custom tools defined from configuration.
//!
//! Two loading paths, exactly like Python:
//! - `ensure_tools_loaded()` (one-shot) scans the four tool directories:
//!   `~/.config/opencode/tools`, `./.opencode/tools`, `~/.config/apex/tools`
//!   and `./.apex/tools`.
//! - `load_custom_tools` reads a YAML `custom_tools:` mapping.
//!
//! Registered tools are exposed to the model as `custom_{name}` schemas
//! (`CustomToolManager::get_schemas`) and dispatched by name through
//! `CustomToolManager::execute` from the `tools::execute_tool` fallback,
//! mirroring Python's `ToolExecutor.execute`.
//!
//! Divergence: Python's `load_tools_from_dirs` imports `*.py` files exposing
//! a `TOOL_DEFINITION` with a callable handler. Rust cannot import Python,
//! so the directory scan loads `*.json` definitions instead with the shape
//! `{"name"?, "description"?, "parameters"?, "command", "cwd"?}` — the
//! command is executed through the same allowlist/pattern/timeout pipeline
//! as the YAML tools.

use serde_json::{json, Value};
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Mutex,
};

/// Python's `ALLOWED_COMMANDS` (34 entries).
const DEFAULT_ALLOWED: &[&str] = &[
    "git", "npm", "node", "python", "python3", "pip", "ruff", "pytest", "cargo", "go", "make",
    "ls", "cat", "head", "tail", "grep", "find", "curl", "wget", "touch", "mkdir", "rm", "cp",
    "mv", "chmod", "pwd", "echo", "env", "which", "whoami", "uname", "df", "du", "ps",
];

static DEFAULT_ALLOWED_SET: std::sync::OnceLock<HashSet<String>> = std::sync::OnceLock::new();
/// Test override mirroring the Python tests that patch `ALLOWED_COMMANDS`.
static ALLOWED_OVERRIDE: Mutex<Option<HashSet<String>>> = Mutex::new(None);

fn default_allowed() -> HashSet<String> {
    DEFAULT_ALLOWED.iter().map(|s| s.to_string()).collect()
}

/// Whether `cmd` is in the active allowlist (Python: `cmd in ALLOWED_COMMANDS`).
pub fn is_allowed(cmd: &str) -> bool {
    if let Some(set) = ALLOWED_OVERRIDE.lock().unwrap().as_ref() {
        return set.contains(cmd);
    }
    DEFAULT_ALLOWED_SET
        .get_or_init(default_allowed)
        .contains(cmd)
}

#[cfg(test)]
pub fn set_allowed_for_test(allowed: HashSet<String>) {
    *ALLOWED_OVERRIDE.lock().unwrap() = Some(allowed);
}

#[cfg(test)]
pub fn reset_allowed_for_test() {
    *ALLOWED_OVERRIDE.lock().unwrap() = None;
}

static DANGEROUS_PATTERNS: std::sync::OnceLock<Vec<regex::Regex>> = std::sync::OnceLock::new();

fn dangerous_patterns() -> &'static [regex::Regex] {
    DANGEROUS_PATTERNS.get_or_init(|| {
        // Python's `[r"\$\(", r"`", r"rm\s+-rf", r"chmod\s+777"]`.
        [r"\$\(", r"`", r"rm\s+-rf", r"chmod\s+777"]
            .iter()
            .map(|p| regex::Regex::new(p).unwrap())
            .collect()
    })
}

fn contains_dangerous(cmd: &str) -> bool {
    dangerous_patterns().iter().any(|p| p.is_match(cmd))
}

/// A registered custom tool (Python's `CustomTool` dataclass).
pub struct CustomTool {
    pub name: String,
    pub description: String,
    pub parameters: Value,
    handler: Box<dyn Fn(&Value) -> String + Send + Sync>,
}

impl CustomTool {
    pub fn new(
        name: &str,
        description: &str,
        parameters: Value,
        handler: Box<dyn Fn(&Value) -> String + Send + Sync>,
    ) -> Self {
        Self {
            name: name.to_string(),
            description: description.to_string(),
            parameters,
            handler,
        }
    }

    /// Python's `handler(args)` call.
    pub fn run(&self, args: &Value) -> String {
        (self.handler)(args)
    }
}

/// Python's `CustomToolManager`.
pub struct CustomToolManager {
    tools: std::collections::HashMap<String, CustomTool>,
}

impl CustomToolManager {
    pub fn new() -> Self {
        Self {
            tools: std::collections::HashMap::new(),
        }
    }

    pub fn register(
        &mut self,
        name: &str,
        description: &str,
        parameters: Value,
        handler: Box<dyn Fn(&Value) -> String + Send + Sync>,
    ) {
        self.tools.insert(
            name.to_string(),
            CustomTool::new(name, description, parameters, handler),
        );
    }

    pub fn get(&self, name: &str) -> Option<&CustomTool> {
        self.tools.get(name)
    }

    /// Python's `list_tools()` — `[{"name", "description", "parameters"}]`.
    ///
    /// Dead in Python too: production only calls `get_schemas`/`execute`;
    /// `list_tools` is the module API exercised by the test suite.
    /// TODO(v2.6): expose it through the `tools` CLI or a route.
    #[allow(dead_code)]
    pub fn list_tools(&self) -> Vec<Value> {
        self.tools
            .values()
            .map(|t| {
                json!({
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                })
            })
            .collect()
    }

    /// Python's `execute(name, args)`. The unknown-tool answer keeps the
    /// exact `ERROR: Unknown custom tool: {name}` string the dispatcher
    /// checks before reporting `ERROR: Unknown tool`.
    pub fn execute(&self, name: &str, args: &Value) -> String {
        match self.get(name) {
            Some(tool) => tool.run(args),
            None => format!("ERROR: Unknown custom tool: {name}"),
        }
    }

    /// Python's `get_schemas()` — schemas exposed to the model as
    /// `custom_{name}`.
    pub fn get_schemas(&self) -> Vec<Value> {
        self.tools
            .values()
            .map(|t| {
                json!({
                    "type": "function",
                    "function": {
                        "name": format!("custom_{}", t.name),
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                })
            })
            .collect()
    }
}

impl Default for CustomToolManager {
    fn default() -> Self {
        Self::new()
    }
}

static MANAGER: std::sync::LazyLock<Mutex<CustomToolManager>> =
    std::sync::LazyLock::new(|| Mutex::new(CustomToolManager::new()));
static TOOLS_LOADED: AtomicBool = AtomicBool::new(false);

/// The process-wide manager (Python's module-level `custom_tool_manager`).
pub fn custom_tool_manager() -> std::sync::MutexGuard<'static, CustomToolManager> {
    Mutex::lock(&*MANAGER).unwrap()
}

/// Python's `ensure_tools_loaded()` — one-shot directory scan.
pub fn ensure_tools_loaded() {
    if TOOLS_LOADED
        .compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
        .is_ok()
    {
        load_tools_from_dirs();
    }
}

/// The four tool directories (Python's `_find_tool_dirs`), deduplicated by
/// resolved path like Python's `seen` set.
pub fn find_tool_dirs() -> Vec<PathBuf> {
    let cwd = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let home = crate::config::home_dir().unwrap_or_else(|| PathBuf::from("."));
    let candidates = [
        home.join(".config").join("opencode").join("tools"),
        cwd.join(".opencode").join("tools"),
        home.join(".config").join("apex").join("tools"),
        cwd.join(".apex").join("tools"),
    ];
    let mut seen: HashSet<PathBuf> = HashSet::new();
    let mut dirs = Vec::new();
    for d in candidates {
        // Python resolves for the dedup; canonicalize fails on missing paths.
        let key = d.canonicalize().unwrap_or(d.clone());
        if seen.insert(key) {
            dirs.push(d);
        }
    }
    dirs
}

/// Scan the four tool directories (Python's `load_tools_from_dirs`).
///
/// Divergence: Python imports `*.py` modules exposing a `TOOL_DEFINITION`
/// with a callable handler; Rust loads `*.json` definitions instead (see the
/// module docs).
pub fn load_tools_from_dirs() {
    for dir in find_tool_dirs() {
        load_tools_from_dir(&mut custom_tool_manager(), &dir);
    }
}

/// Load `*.json` tool definitions from one directory.
fn load_tools_from_dir(manager: &mut CustomToolManager, dir: &Path) {
    if !dir.is_dir() {
        return;
    }
    let mut files: Vec<PathBuf> = std::fs::read_dir(dir)
        .into_iter()
        .flatten()
        .filter_map(|entry| entry.ok())
        .map(|entry| entry.path())
        .filter(|p| p.is_file() && p.extension().and_then(|s| s.to_str()) == Some("json"))
        .collect();
    files.sort(); // Python: sorted(glob("*.py"))
    for file in files {
        let stem = file
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or_default()
            .to_string();
        let Ok(text) = std::fs::read_to_string(&file) else {
            continue;
        };
        let Ok(def) = serde_json::from_str::<Value>(&text) else {
            continue;
        };
        let Some(object) = def.as_object() else {
            continue;
        };
        let name = object
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or(&stem)
            .to_string();
        if manager.get(&name).is_some() {
            continue;
        }
        let description = object
            .get("description")
            .and_then(|v| v.as_str())
            .unwrap_or(&format!("Custom tool: {name}"))
            .to_string();
        let parameters = object
            .get("parameters")
            .cloned()
            .unwrap_or_else(|| json!({"type": "object", "properties": {}}));
        let command = object
            .get("command")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let cwd = object
            .get("cwd")
            .and_then(|v| v.as_str())
            .unwrap_or(".")
            .to_string();
        if let Some(first) = shlex_split(&command).first() {
            if !is_allowed(first) {
                eprintln!("Custom tool '{name}' blocked: command '{first}' not in allowlist");
                continue;
            }
        }
        manager.register(
            &name,
            &description,
            parameters,
            command_handler(command, cwd),
        );
    }
}

/// Python's `load_custom_tools(config_path)` against the global manager.
///
/// Dead in Python too: only the test suite calls it.
/// TODO(v2.6): expose the YAML loader through a CLI/config surface.
#[allow(dead_code)]
pub fn load_custom_tools(config_path: &Path) {
    load_custom_tools_into(&mut custom_tool_manager(), config_path);
}

/// Read a YAML `custom_tools:` mapping (Python's `load_custom_tools` core).
fn load_custom_tools_into(manager: &mut CustomToolManager, config_path: &Path) {
    if !config_path.exists() {
        return;
    }
    let Ok(text) = std::fs::read_to_string(config_path) else {
        eprintln!("Failed to load custom tools: unreadable config");
        return;
    };
    let config: Value = match serde_yaml::from_str(&text) {
        Ok(config) => config,
        Err(e) => {
            eprintln!("Failed to load custom tools: {e}");
            return;
        }
    };
    let Some(custom_tools) = config.get("custom_tools").and_then(|v| v.as_object()) else {
        return;
    };
    for (tool_name, tool_config) in custom_tools {
        // Python: a non-mapping tool config raises inside the `try`, is
        // caught by the outer `except`, logged and aborts the load.
        let Some(cfg) = tool_config.as_object() else {
            eprintln!("Failed to load custom tools: tool '{tool_name}' is not a mapping");
            return;
        };
        if !is_truthy(cfg.get("enabled")) {
            continue;
        }
        let description = cfg
            .get("description")
            .and_then(|v| v.as_str())
            .unwrap_or("Custom tool")
            .to_string();
        let parameters = cfg
            .get("parameters")
            .cloned()
            .unwrap_or_else(|| json!({"type": "object", "properties": {}}));
        let command = cfg
            .get("command")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let cwd = cfg
            .get("cwd")
            .and_then(|v| v.as_str())
            .unwrap_or(".")
            .to_string();
        if let Some(first) = shlex_split(&command).first() {
            if !is_allowed(first) {
                eprintln!("Custom tool '{tool_name}' blocked: command '{first}' not in allowlist");
                continue;
            }
        }
        manager.register(
            tool_name,
            &description,
            parameters,
            command_handler(command, cwd),
        );
    }
}

/// Python truthiness for the `enabled` flag (`if not tool_config.get("enabled", True)`).
fn is_truthy(value: Option<&Value>) -> bool {
    match value {
        None => true,
        Some(Value::Null) => false,
        Some(Value::Bool(b)) => *b,
        Some(Value::Number(n)) => n.as_i64().unwrap_or(0) != 0,
        Some(Value::String(s)) => !s.is_empty(),
        Some(Value::Array(a)) => !a.is_empty(),
        Some(Value::Object(o)) => !o.is_empty(),
    }
}

/// Python's `make_handler(cmd, wd)` — substitute the arguments, re-check the
/// allowlist, block dangerous patterns, then run with a 30 s timeout.
fn command_handler(command: String, cwd: String) -> Box<dyn Fn(&Value) -> String + Send + Sync> {
    Box::new(move |args: &Value| {
        let safe_cmd = match format_command(&command, args) {
            Ok(cmd) => cmd,
            Err(e) => return e,
        };
        if let Some(first) = shlex_split(&safe_cmd).first() {
            if !is_allowed(first) {
                return format!("ERROR: Command '{first}' not allowed");
            }
        }
        if contains_dangerous(&safe_cmd) {
            return "ERROR: Dangerous pattern blocked".to_string();
        }
        run_capped(&shlex_split(&safe_cmd), &cwd)
    })
}

/// Substitute `{key}` placeholders like Python's `cmd.format(**args)`.
///
/// Only bare identifiers are supported (no format specs or positional
/// fields); `{{`/`}}` stay literal, like Python. A missing key fails with
/// `ERROR: '{key}'` (Python raises `KeyError('key')`).
fn format_command(command: &str, args: &Value) -> Result<String, String> {
    let args = args.as_object();
    let mut out = String::new();
    let chars: Vec<char> = command.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        match chars[i] {
            '{' if i + 1 < chars.len() && chars[i + 1] == '{' => {
                out.push('{');
                i += 2;
            }
            '{' => {
                let mut j = i + 1;
                while j < chars.len() && chars[j] != '}' {
                    j += 1;
                }
                if j >= chars.len() {
                    return Err("ERROR: Single '{' encountered".to_string());
                }
                let key: String = chars[i + 1..j].iter().collect();
                let value = args.and_then(|o| o.get(&key)).map(|v| match v {
                    Value::String(s) => s.clone(),
                    other => other.to_string(),
                });
                match value {
                    Some(v) => out.push_str(&v),
                    None => return Err(format!("ERROR: '{key}'")),
                }
                i = j + 1;
            }
            '}' if i + 1 < chars.len() && chars[i + 1] == '}' => {
                out.push('}');
                i += 2;
            }
            '}' => return Err("ERROR: Single '}' encountered".to_string()),
            c => {
                out.push(c);
                i += 1;
            }
        }
    }
    Ok(out)
}

/// A minimal `shlex.split` parity (no shell): whitespace-separated words with
/// single/double-quote merging and backslash escapes outside quotes.
fn shlex_split(command: &str) -> Vec<String> {
    let chars: Vec<char> = command.chars().collect();
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut in_word = false;
    let mut i = 0;
    while i < chars.len() {
        match chars[i] {
            ' ' | '\t' | '\n' | '\r' => {
                if in_word {
                    out.push(std::mem::take(&mut cur));
                    in_word = false;
                }
                i += 1;
            }
            '\'' => {
                in_word = true;
                i += 1;
                while i < chars.len() && chars[i] != '\'' {
                    cur.push(chars[i]);
                    i += 1;
                }
                i += 1; // skip the closing quote (or run past EOF)
            }
            '"' => {
                in_word = true;
                i += 1;
                while i < chars.len() && chars[i] != '"' {
                    if chars[i] == '\\'
                        && i + 1 < chars.len()
                        && matches!(chars[i + 1], '"' | '\\' | '$' | '`' | '\'')
                    {
                        cur.push(chars[i + 1]);
                        i += 2;
                    } else {
                        cur.push(chars[i]);
                        i += 1;
                    }
                }
                i += 1; // skip the closing quote (or run past EOF)
            }
            '\\' if i + 1 < chars.len() => {
                in_word = true;
                cur.push(chars[i + 1]);
                i += 2;
            }
            c => {
                in_word = true;
                cur.push(c);
                i += 1;
            }
        }
    }
    if in_word || !cur.is_empty() {
        out.push(cur);
    }
    out
}

/// Python's `subprocess.run(..., capture_output=True, timeout=30)` — returns
/// `stdout or stderr or "[no output]"`.
fn run_capped(argv: &[String], cwd: &str) -> String {
    if argv.is_empty() {
        return "ERROR: empty command".to_string();
    }
    let mut child = match std::process::Command::new(&argv[0])
        .args(&argv[1..])
        .current_dir(cwd)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
    {
        Ok(child) => child,
        Err(e) => return format!("ERROR: {e}"),
    };
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(30);
    loop {
        match child.try_wait() {
            Ok(Some(_)) => break,
            Ok(None) => {
                if std::time::Instant::now() >= deadline {
                    let _ = child.kill();
                    let _ = child.wait();
                    return format!("ERROR: Command '{}' timed out after 30 seconds", argv[0]);
                }
                std::thread::sleep(std::time::Duration::from_millis(100));
            }
            Err(e) => return format!("ERROR: {e}"),
        }
    }
    match child.wait_with_output() {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let stderr = String::from_utf8_lossy(&output.stderr);
            if !stdout.is_empty() {
                stdout.into_owned()
            } else if !stderr.is_empty() {
                stderr.into_owned()
            } else {
                "[no output]".to_string()
            }
        }
        Err(e) => format!("ERROR: {e}"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn register_command(manager: &mut CustomToolManager, name: &str, command: &str, cwd: &str) {
        manager.register(
            name,
            "desc",
            json!({"type": "object"}),
            command_handler(command.to_string(), cwd.to_string()),
        );
    }

    #[test]
    fn allowed_commands_membership() {
        for cmd in [
            "git", "python", "python3", "npm", "pytest", "make", "ls", "echo",
        ] {
            assert!(is_allowed(cmd), "{cmd} must be allowed");
        }
        assert!(!is_allowed("sudo"));
    }

    #[test]
    fn custom_tool_fields_and_handler() {
        let tool = CustomTool::new(
            "test",
            "Test tool",
            json!({"type": "object"}),
            Box::new(|_| "ok".to_string()),
        );
        assert_eq!(tool.name, "test");
        assert_eq!(tool.description, "Test tool");
        assert_eq!(tool.parameters, json!({"type": "object"}));
        assert_eq!(tool.run(&json!({"key": "val"})), "ok");
    }

    #[test]
    fn manager_starts_empty() {
        let manager = CustomToolManager::new();
        assert!(manager.list_tools().is_empty());
        assert!(manager.get_schemas().is_empty());
    }

    #[test]
    fn register_and_get() {
        let mut manager = CustomToolManager::new();
        manager.register(
            "test",
            "Test tool",
            json!({"type": "object"}),
            Box::new(|_| "result".to_string()),
        );
        let tool = manager.get("test").unwrap();
        assert_eq!(tool.name, "test");
        assert_eq!(tool.description, "Test tool");
        assert_eq!(tool.parameters, json!({"type": "object"}));
        assert!(manager.get("nonexistent").is_none());
    }

    #[test]
    fn list_tools_structure() {
        let mut manager = CustomToolManager::new();
        manager.register("t1", "Tool 1", json!({}), Box::new(|_| "1".to_string()));
        manager.register("t2", "Tool 2", json!({}), Box::new(|_| "2".to_string()));
        let tools = manager.list_tools();
        assert_eq!(tools.len(), 2);
        let names: HashSet<String> = tools
            .iter()
            .map(|t| t["name"].as_str().unwrap().to_string())
            .collect();
        assert_eq!(names, HashSet::from(["t1".to_string(), "t2".to_string()]));
        manager.register(
            "t",
            "desc",
            json!({"type": "object"}),
            Box::new(|_| String::new()),
        );
        let one = manager
            .list_tools()
            .into_iter()
            .find(|t| t["name"] == "t")
            .unwrap();
        assert_eq!(
            one,
            json!({
                "name": "t",
                "description": "desc",
                "parameters": {"type": "object"},
            })
        );
    }

    #[test]
    fn execute_and_unknown() {
        let mut manager = CustomToolManager::new();
        manager.register(
            "test",
            "desc",
            json!({}),
            Box::new(|args| {
                format!(
                    "got {}",
                    args.get("x").and_then(|v| v.as_str()).unwrap_or("")
                )
            }),
        );
        assert_eq!(manager.execute("test", &json!({"x": "hello"})), "got hello");
        assert!(manager
            .execute("unknown", &json!({}))
            .contains("ERROR: Unknown custom tool"));
    }

    #[test]
    fn get_schemas_shapes() {
        let mut manager = CustomToolManager::new();
        assert!(manager.get_schemas().is_empty());
        manager.register(
            "test",
            "desc",
            json!({"type": "object"}),
            Box::new(|_| "ok".to_string()),
        );
        let schemas = manager.get_schemas();
        assert_eq!(schemas.len(), 1);
        assert_eq!(schemas[0]["type"], "function");
        assert_eq!(schemas[0]["function"]["name"], "custom_test");
        assert_eq!(schemas[0]["function"]["description"], "desc");
        assert_eq!(
            schemas[0]["function"]["parameters"],
            json!({"type": "object"})
        );
        manager.register("a", "Alpha", json!({"a": 1}), Box::new(|_| String::new()));
        manager.register("b", "Beta", json!({"b": 2}), Box::new(|_| String::new()));
        let names: HashSet<String> = manager
            .get_schemas()
            .iter()
            .map(|s| s["function"]["name"].as_str().unwrap().to_string())
            .collect();
        assert_eq!(
            names,
            HashSet::from([
                "custom_test".to_string(),
                "custom_a".to_string(),
                "custom_b".to_string()
            ])
        );
    }

    fn write_yaml(dir: &Path, name: &str, body: &str) -> PathBuf {
        let path = dir.join(name);
        std::fs::write(&path, body).unwrap();
        path
    }

    #[test]
    fn load_custom_tools_nonexistent_and_empty() {
        let mut manager = CustomToolManager::new();
        load_custom_tools_into(&mut manager, Path::new("/nonexistent/config.yaml"));
        assert!(manager.list_tools().is_empty());
        let dir = tempfile::tempdir().unwrap();
        let empty = write_yaml(dir.path(), "empty.yaml", "");
        load_custom_tools_into(&mut manager, &empty);
        assert!(manager.list_tools().is_empty());
        let no_key = write_yaml(dir.path(), "nokey.yaml", "other_key: value\n");
        load_custom_tools_into(&mut manager, &no_key);
        assert!(manager.list_tools().is_empty());
        let null = write_yaml(dir.path(), "null.yaml", "~");
        load_custom_tools_into(&mut manager, &null);
        assert!(manager.list_tools().is_empty());
    }

    #[test]
    fn load_custom_tools_disabled_and_blocked() {
        let dir = tempfile::tempdir().unwrap();
        let mut manager = CustomToolManager::new();
        let path = write_yaml(
            dir.path(),
            "config.yaml",
            "custom_tools:\n  off:\n    enabled: false\n    command: echo hi\n  bad:\n    command: sudo rm -rf /\n",
        );
        load_custom_tools_into(&mut manager, &path);
        assert!(manager.get("off").is_none());
        assert!(manager.get("bad").is_none());
        assert!(manager.list_tools().is_empty());
    }

    #[test]
    fn load_custom_tools_defaults() {
        let dir = tempfile::tempdir().unwrap();
        let mut manager = CustomToolManager::new();
        let path = write_yaml(
            dir.path(),
            "config.yaml",
            "custom_tools:\n  nodesc:\n    command: echo hi\n",
        );
        load_custom_tools_into(&mut manager, &path);
        let tool = manager.get("nodesc").unwrap();
        assert_eq!(tool.description, "Custom tool");
        assert_eq!(tool.parameters, json!({"type": "object", "properties": {}}));
    }

    #[test]
    fn load_custom_tools_explicit_parameters() {
        let dir = tempfile::tempdir().unwrap();
        let mut manager = CustomToolManager::new();
        let path = write_yaml(
            dir.path(),
            "config.yaml",
            "custom_tools:\n  explicit:\n    description: My Tool\n    command: echo hi\n    parameters:\n      type: object\n      properties:\n        name:\n          type: string\n",
        );
        load_custom_tools_into(&mut manager, &path);
        let tool = manager.get("explicit").unwrap();
        assert_eq!(tool.description, "My Tool");
        assert_eq!(
            tool.parameters,
            json!({
                "type": "object",
                "properties": {"name": {"type": "string"}},
            })
        );
    }

    #[test]
    fn load_custom_tools_bad_yaml() {
        let dir = tempfile::tempdir().unwrap();
        let mut manager = CustomToolManager::new();
        let path = write_yaml(
            dir.path(),
            "bad.yaml",
            "custom_tools:\n  broken: [unclosed\n",
        );
        load_custom_tools_into(&mut manager, &path);
        assert!(manager.list_tools().is_empty());
    }

    #[test]
    fn load_custom_tools_multiple_and_schema() {
        let dir = tempfile::tempdir().unwrap();
        let mut manager = CustomToolManager::new();
        let path = write_yaml(
            dir.path(),
            "config.yaml",
            "custom_tools:\n  fmt:\n    description: Formatter\n    command: ruff check {path}\n    parameters:\n      type: object\n      properties:\n        path:\n          type: string\n  tool_b:\n    command: echo B\n",
        );
        load_custom_tools_into(&mut manager, &path);
        assert!(manager.get("fmt").is_some());
        assert!(manager.get("tool_b").is_some());
        assert_eq!(manager.list_tools().len(), 2);
        let matching = manager
            .get_schemas()
            .into_iter()
            .filter(|s| s["function"]["name"] == "custom_fmt")
            .collect::<Vec<_>>();
        assert_eq!(matching.len(), 1);
        assert_eq!(matching[0]["function"]["description"], "Formatter");
        assert_eq!(
            matching[0]["function"]["parameters"]["properties"]["path"]["type"],
            "string"
        );
    }

    #[test]
    fn format_command_substitutes_and_escapes() {
        let args = json!({"name": "World"});
        assert_eq!(
            format_command("Hello {name}", &args).unwrap(),
            "Hello World"
        );
        assert_eq!(
            format_command("{{literal}} {name}", &args).unwrap(),
            "{literal} World"
        );
        assert!(format_command("echo {nonexistent}", &json!({})).is_err());
        assert_eq!(
            format_command("echo {nonexistent}", &json!({})).unwrap_err(),
            "ERROR: 'nonexistent'"
        );
    }

    #[test]
    fn shlex_split_quoting() {
        fn sv(items: &[&str]) -> Vec<String> {
            items.iter().map(|s| s.to_string()).collect()
        }
        assert_eq!(
            shlex_split("git -C . status"),
            sv(&["git", "-C", ".", "status"])
        );
        assert!(shlex_split("").is_empty());
        assert_eq!(shlex_split("'a b' c"), sv(&["a b", "c"]));
        assert_eq!(shlex_split("\"a b\" c"), sv(&["a b", "c"]));
        assert_eq!(shlex_split("a\\ b"), sv(&["a b"]));
        // Adjacent quotes concatenate, exactly like Python's shlex:
        // `'it''s'` is `it` + `s` (quotes stripped), i.e. `its`.
        assert_eq!(shlex_split("echo 'it''s'"), sv(&["echo", "its"]));
    }

    #[test]
    fn execute_blocks_dangerous_patterns() {
        let mut manager = CustomToolManager::new();
        register_command(&mut manager, "t", "echo {x}", ".");
        assert_eq!(
            manager.execute("t", &json!({"x": "$(whoami)"})),
            "ERROR: Dangerous pattern blocked"
        );
        assert_eq!(
            manager.execute("t", &json!({"x": "`whoami`"})),
            "ERROR: Dangerous pattern blocked"
        );
        assert_eq!(
            manager.execute("t", &json!({"x": "rm -rf /"})),
            "ERROR: Dangerous pattern blocked"
        );
        assert_eq!(
            manager.execute("t", &json!({"x": "chmod 777 file"})),
            "ERROR: Dangerous pattern blocked"
        );
    }

    #[test]
    fn execute_missing_format_key_is_error() {
        let mut manager = CustomToolManager::new();
        register_command(&mut manager, "missing_key", "echo {nonexistent}", ".");
        let result = manager.execute("missing_key", &json!({}));
        assert!(result.starts_with("ERROR"), "got: {result}");
    }

    #[test]
    fn execute_not_allowed_after_format() {
        let mut manager = CustomToolManager::new();
        register_command(&mut manager, "runner", "echo {cmd}", ".");
        let without_echo: HashSet<String> = DEFAULT_ALLOWED
            .iter()
            .filter(|c| **c != "echo")
            .map(|s| s.to_string())
            .collect();
        set_allowed_for_test(without_echo);
        let result = manager.execute("runner", &json!({"cmd": "test"}));
        assert!(result.contains("not allowed"), "got: {result}");
        reset_allowed_for_test();
    }

    #[test]
    fn execute_success_git_version() {
        // `git` is on every machine that runs this suite (the E2E suite
        // already requires it), and it is allowlisted.
        let mut manager = CustomToolManager::new();
        register_command(&mut manager, "version", "git --version", ".");
        let result = manager.execute("version", &json!({}));
        assert!(result.contains("git version"), "got: {result}");
    }

    #[cfg(unix)]
    #[test]
    fn execute_success_python() {
        let mut manager = CustomToolManager::new();
        register_command(
            &mut manager,
            "greeter",
            "python3 -c \"import sys;print('Hello '+sys.argv[1])\" {name}",
            ".",
        );
        let result = manager.execute("greeter", &json!({"name": "World"}));
        assert!(result.contains("Hello World"), "got: {result}");
    }

    #[cfg(unix)]
    #[test]
    fn execute_stderr_and_no_output() {
        let mut manager = CustomToolManager::new();
        register_command(
            &mut manager,
            "errwriter",
            "python3 -c \"import sys; sys.stderr.write('stderr msg')\"",
            ".",
        );
        let result = manager.execute("errwriter", &json!({}));
        assert!(result.contains("stderr msg"), "got: {result}");
        register_command(&mut manager, "silent", "python3 -c \"import sys\"", ".");
        assert_eq!(manager.execute("silent", &json!({})), "[no output]");
    }

    #[cfg(unix)]
    #[test]
    fn execute_custom_cwd() {
        let dir = tempfile::tempdir().unwrap();
        let subdir = dir.path().join("subdir");
        std::fs::create_dir_all(&subdir).unwrap();
        std::fs::write(subdir.join("marker.txt"), "present").unwrap();
        let mut manager = CustomToolManager::new();
        register_command(
            &mut manager,
            "lstool",
            "python3 -c \"import os;print(os.listdir('.'))\"",
            subdir.to_str().unwrap(),
        );
        let result = manager.execute("lstool", &json!({}));
        assert!(result.contains("marker.txt"), "got: {result}");
    }

    #[cfg(unix)]
    #[test]
    fn execute_preserves_quoted_args() {
        let mut manager = CustomToolManager::new();
        register_command(&mut manager, "quoted", "echo 'a b' \"c d\"", ".");
        assert_eq!(manager.execute("quoted", &json!({})).trim(), "a b c d");
    }

    #[test]
    fn find_tool_dirs_shape() {
        let dirs = find_tool_dirs();
        assert!((1..=4).contains(&dirs.len()));
        let cwd = std::env::current_dir().unwrap();
        assert!(dirs.contains(&cwd.join(".apex").join("tools")));
    }

    #[test]
    fn load_tools_from_dir_json() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("hello.json"),
            r#"{"name": "hello", "command": "git --version"}"#,
        )
        .unwrap();
        std::fs::write(dir.path().join("blocked.json"), r#"{"command": "sudo ls"}"#).unwrap();
        std::fs::write(dir.path().join("notjson.json"), "not json {").unwrap();
        let mut manager = CustomToolManager::new();
        load_tools_from_dir(&mut manager, dir.path());
        let tool = manager.get("hello").expect("hello must load");
        assert_eq!(tool.description, "Custom tool: hello");
        assert!(manager.get("blocked").is_none());
        assert!(manager.get("notjson").is_none());
        // Python: an already-registered name is skipped.
        manager.register(
            "hello",
            "explicit",
            json!({}),
            Box::new(|_| "explicit".to_string()),
        );
        load_tools_from_dir(&mut manager, dir.path());
        assert_eq!(manager.get("hello").unwrap().description, "explicit");
    }

    #[test]
    fn ensure_tools_loaded_is_one_shot() {
        ensure_tools_loaded();
        ensure_tools_loaded();
        assert!(TOOLS_LOADED.load(Ordering::SeqCst));
    }

    #[test]
    fn global_load_custom_tools_registers_in_global() {
        let dir = tempfile::tempdir().unwrap();
        let path = write_yaml(
            dir.path(),
            "config.yaml",
            "custom_tools:\n  globalprobe:\n    command: echo hi\n",
        );
        load_custom_tools(&path);
        let mut guard = custom_tool_manager();
        assert!(guard.get("globalprobe").is_some());
        guard.tools.remove("globalprobe");
        drop(guard);
    }
}
