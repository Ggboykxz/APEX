//! Formatter system — port of `apex/formatter.py`.
//!
//! OpenCode-style auto-formatters: built-in configs for ruff, prettier, biome,
//! rustfmt, gofmt, clang-format, etc., with availability discovery, config-driven
//! enable/disable, and per-file formatter selection.
//
//! This module is not yet wired into the dispatch gate / agent loop.
//! Allow dead code with a named exit criterion — TODO(v2.6): wire into tool
//! dispatch / agent message handling and remove this allow.
#![allow(dead_code)]

use std::collections::HashMap;
use std::path::Path;
use std::process::Command;

use serde::{Deserialize, Serialize};
use tempfile::Builder;

/// Configuration for a single formatter.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FormatterConfig {
    pub name: String,
    pub command: Vec<String>,
    pub extensions: Vec<String>,
    pub environment: HashMap<String, String>,
    pub disabled: bool,
    pub requirements: Option<Vec<String>>,
}

/// Built-in formatter definitions (mirrors `apex/formatter.py`).
pub fn builtin_formatters() -> Vec<FormatterConfig> {
    vec![
        FormatterConfig {
            name: "ruff".into(),
            command: vec!["ruff".into(), "format".into(), "$FILE".into()],
            extensions: vec![".py".into(), ".pyi".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "prettier".into(),
            command: vec![
                "npx".into(),
                "prettier".into(),
                "--write".into(),
                "$FILE".into(),
            ],
            extensions: vec![
                ".js".into(),
                ".ts".into(),
                ".jsx".into(),
                ".tsx".into(),
                ".json".into(),
                ".yaml".into(),
                ".md".into(),
                ".html".into(),
                ".css".into(),
            ],
            environment: HashMap::new(),
            disabled: false,
            requirements: Some(vec!["package.json:prettier".into()]),
        },
        FormatterConfig {
            name: "biome".into(),
            command: vec![
                "npx".into(),
                "@biomejs/biome".into(),
                "format".into(),
                "--write".into(),
                "$FILE".into(),
            ],
            extensions: vec![
                ".js".into(),
                ".jsx".into(),
                ".ts".into(),
                ".tsx".into(),
                ".json".into(),
                ".css".into(),
                ".html".into(),
                ".md".into(),
            ],
            environment: HashMap::new(),
            disabled: false,
            requirements: Some(vec!["biome.json".into(), "biome.jsonc".into()]),
        },
        FormatterConfig {
            name: "rustfmt".into(),
            command: vec!["rustfmt".into(), "$FILE".into()],
            extensions: vec![".rs".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "cargofmt".into(),
            command: vec!["cargo".into(), "fmt".into(), "--".into(), "$FILE".into()],
            extensions: vec![".rs".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "gofmt".into(),
            command: vec!["gofmt".into(), "-w".into(), "$FILE".into()],
            extensions: vec![".go".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "google-java-format".into(),
            command: vec!["google-java-format".into(), "$FILE".into()],
            extensions: vec![".java".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "clang-format".into(),
            command: vec!["clang-format".into(), "-i".into(), "$FILE".into()],
            extensions: vec![
                ".c".into(),
                ".h".into(),
                ".cpp".into(),
                ".hpp".into(),
                ".ino".into(),
            ],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "rubocop".into(),
            command: vec!["rubocop".into(), "-a".into(), "$FILE".into()],
            extensions: vec![
                ".rb".into(),
                ".rake".into(),
                ".gemspec".into(),
                ".ru".into(),
            ],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "scalafmt".into(),
            command: vec!["scalafmt".into(), "$FILE".into()],
            extensions: vec![".scala".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "ktlint".into(),
            command: vec!["ktlint".into(), "$FILE".into()],
            extensions: vec![".kt".into(), ".kts".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "swift-format".into(),
            command: vec!["swift-format".into(), "-i".into(), "$FILE".into()],
            extensions: vec![".swift".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "zig-fmt".into(),
            command: vec!["zig".into(), "fmt".into(), "$FILE".into()],
            extensions: vec![".zig".into(), ".zon".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "dart".into(),
            command: vec!["dart".into(), "format".into(), "$FILE".into()],
            extensions: vec![".dart".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "shfmt".into(),
            command: vec!["shfmt".into(), "-w".into(), "$FILE".into()],
            extensions: vec![".sh".into(), ".bash".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "terraform".into(),
            command: vec!["terraform".into(), "fmt".into(), "$FILE".into()],
            extensions: vec![".tf".into(), ".tfvars".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "mix".into(),
            command: vec!["mix".into(), "format".into(), "$FILE".into()],
            extensions: vec![".ex".into(), ".exs".into(), ".eex".into(), ".heex".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "nixfmt".into(),
            command: vec!["nixfmt".into(), "$FILE".into()],
            extensions: vec![".nix".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "standardrb".into(),
            command: vec!["standardrb".into(), "--fix".into(), "$FILE".into()],
            extensions: vec![
                ".rb".into(),
                ".rake".into(),
                ".gemspec".into(),
                ".ru".into(),
            ],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
        FormatterConfig {
            name: "uv".into(),
            command: vec![
                "uv".into(),
                "tool".into(),
                "run".into(),
                "ruff".into(),
                "format".into(),
                "$FILE".into(),
            ],
            extensions: vec![".py".into(), ".pyi".into()],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        },
    ]
}

/// Manager for formatters: tracks built-ins, config overrides, availability
/// discovery, and selection per file extension.
#[derive(Debug, Clone)]
pub struct FormatterManager {
    formatters: Vec<FormatterConfig>,
    available: HashMap<String, bool>,
    loaded: bool,
}

impl Default for FormatterManager {
    fn default() -> Self {
        Self::new()
    }
}

impl FormatterManager {
    /// Create a new manager with the built-in formatters (disabled until loaded).
    pub fn new() -> Self {
        Self {
            formatters: builtin_formatters(),
            available: HashMap::new(),
            loaded: false,
        }
    }

    /// Returns a clone of the configured formatters.
    pub fn formatters(&self) -> Vec<FormatterConfig> {
        self.formatters.clone()
    }

    /// Load formatter configuration from the apex config (formatter section).
    ///
    /// `cfg` mirrors Python's `config_v2.apex_config.formatter`:
    /// - `false` / `{"disabled": true}` → disable all
    /// - `true` → enable all, run availability discovery
    /// - `{"name": {...}}` → per-formatter overrides + custom additions
    pub fn load_from_config(&mut self, cfg: Option<&serde_json::Value>) {
        self.formatters = builtin_formatters();

        match cfg {
            None | Some(serde_json::Value::Bool(false)) => {
                for fmt in &mut self.formatters {
                    fmt.disabled = true;
                }
                self.available = self
                    .formatters
                    .iter()
                    .map(|f| (f.name.clone(), false))
                    .collect();
                self.loaded = true;
                return;
            }
            Some(serde_json::Value::Object(obj)) => {
                if obj.get("disabled").and_then(|v| v.as_bool()).unwrap_or(false) {
                    for fmt in &mut self.formatters {
                        fmt.disabled = true;
                    }
                    self.available = self
                        .formatters
                        .iter()
                        .map(|f| (f.name.clone(), false))
                        .collect();
                    self.loaded = true;
                    return;
                }

                for (name, opts) in obj {
                    if let serde_json::Value::Object(opts_obj) = opts {
                        let existing = self
                            .formatters
                            .iter_mut()
                            .find(|f| f.name == *name);
                        if let Some(existing) = existing {
                            if let Some(disabled) =
                                opts_obj.get("disabled").and_then(|v| v.as_bool())
                            {
                                existing.disabled = disabled;
                            }
                            if let Some(command) =
                                opts_obj.get("command").and_then(|v| v.as_array())
                            {
                                existing.command = command
                                    .iter()
                                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                                    .collect();
                            }
                            if let Some(extensions) =
                                opts_obj.get("extensions").and_then(|v| v.as_array())
                            {
                                existing.extensions = extensions
                                    .iter()
                                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                                    .collect();
                            }
                            if let Some(env) =
                                opts_obj.get("environment").and_then(|v| v.as_object())
                            {
                                existing.environment = env
                                    .iter()
                                    .map(|(k, v)| {
                                        (
                                            k.clone(),
                                            v.as_str()
                                                .unwrap_or(&v.to_string())
                                                .to_string(),
                                        )
                                    })
                                    .collect();
                            }
                        } else if let (Some(command), Some(extensions)) = (
                            opts_obj.get("command").and_then(|v| v.as_array()),
                            opts_obj.get("extensions").and_then(|v| v.as_array()),
                        ) {
                            self.formatters.push(FormatterConfig {
                                name: name.clone(),
                                command: command
                                    .iter()
                                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                                    .collect(),
                                extensions: extensions
                                    .iter()
                                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                                    .collect(),
                                environment: opts_obj
                                    .get("environment")
                                    .and_then(|v| v.as_object())
                                    .map(|env| {
                                        env.iter()
                                            .map(|(k, v)| {
                                                (
                                                    k.clone(),
                                                    v.as_str()
                                                        .unwrap_or(&v.to_string())
                                                        .to_string(),
                                                )
                                            })
                                            .collect()
                                    })
                                    .unwrap_or_default(),
                                disabled: opts_obj
                                    .get("disabled")
                                    .and_then(|v| v.as_bool())
                                    .unwrap_or(false),
                                requirements: opts_obj.get("requirements").and_then(|v| {
                                    v.as_array().map(|arr| {
                                        arr.iter()
                                            .filter_map(|r| r.as_str().map(|s| s.to_string()))
                                            .collect()
                                    })
                                }),
                            });
                        }
                    }
                }
            }
            _ => {}
        }

        self.loaded = true;
        self.discover_available();
    }

    /// Check a single requirement string against the environment.
    ///
    /// - `"package.json:prettier"` → file exists AND contains dep name
    /// - `"biome.json"` → file exists
    /// - `"ruff"` → binary on PATH
    pub fn check_requirement(&self, req: &str) -> bool {
        if let Some((file_part, dep)) = req.split_once(':') {
            let p = Path::new(file_part);
            if !p.is_file() {
                return false;
            }
            return std::fs::read_to_string(p)
                .map(|content| content.contains(dep))
                .unwrap_or(false);
        }
        let p = Path::new(req);
        if p.is_file() {
            return true;
        }
        Command::new(req.split_whitespace().next().unwrap_or(req))
            .output()
            .is_ok()
    }

    /// Run availability discovery for all formatters.
    pub fn discover_available(&mut self) {
        self.available.clear();
        for fmt in &self.formatters {
            if let Some(reqs) = &fmt.requirements {
                if !reqs.iter().all(|r| self.check_requirement(r)) {
                    self.available.insert(fmt.name.clone(), false);
                    continue;
                }
            }
            let binary = fmt.command[0].split_whitespace().next().unwrap_or("");
            let available = match binary {
                "npx" => Command::new("node").output().is_ok(),
                "cargo" => Command::new("cargo").output().is_ok(),
                _ => Command::new(binary).output().is_ok(),
            };
            self.available.insert(fmt.name.clone(), available);
        }
    }

    /// Return enabled and available formatters.
    pub fn list_available(&self) -> Vec<FormatterConfig> {
        self.formatters
            .iter()
            .filter(|f| !f.disabled && self.available.get(&f.name).copied().unwrap_or(false))
            .cloned()
            .collect()
    }

    /// Return the formatter configured for a file's extension, if enabled and available.
    pub fn get_formatter_for<P: AsRef<Path>>(&self, file_path: P) -> Option<FormatterConfig> {
        let file_path = file_path.as_ref();
        let ext = file_path
            .extension()
            .map(|e| e.to_string_lossy().to_string())
            .unwrap_or_default()
            .to_lowercase();
        for fmt in &self.formatters {
            if fmt.disabled {
                continue;
            }
            if fmt.extensions.iter().any(|e| e.as_str() == ext)
                && self.available.get(&fmt.name).copied().unwrap_or(false)
            {
                return Some(fmt.clone());
            }
        }
        None
    }

    /// Return true if a file can be formatted by an available enabled formatter.
    pub fn is_formattable<P: AsRef<Path>>(&self, file_path: P) -> bool {
        self.get_formatter_for(file_path).is_some()
    }

    /// Format a file in place. Returns true on success.
    pub fn format_file<P: AsRef<Path>>(&self, file_path: P) -> bool {
        let file_path = file_path.as_ref().to_str().unwrap_or("");
        let fmt = match self.get_formatter_for(file_path) {
            Some(f) => f,
            None => return false,
        };
        self.run_formatter(&fmt, file_path)
    }

    /// Format multiple files, returning a map of path → success.
    pub fn format_files(&self, file_paths: &[String]) -> HashMap<String, bool> {
        file_paths
            .iter()
            .map(|fp| (fp.clone(), self.format_file(fp)))
            .collect()
    }

    /// Format in-memory code for a given extension using a temp file.
    pub fn format_code(&self, code: &str, extension: &str) -> String {
        let ext = if extension.starts_with('.') {
            extension.to_string()
        } else {
            format!(".{extension}")
        };
        for fmt in &self.formatters {
            if fmt.disabled {
                continue;
            }
            if fmt.extensions.iter().any(|e| e.as_str() == ext.as_str())
                && self.available.get(&fmt.name).copied().unwrap_or(false)
            {
                return self.run_formatter_tempfile(fmt, code, ext.as_str());
            }
        }
        code.to_string()
    }

    /// Build the command for a formatter, replacing `$FILE` with the path.
    pub fn build_command(&self, fmt: &FormatterConfig, file_path: &str) -> Vec<String> {
        fmt.command
            .iter()
            .map(|part| part.replace("$FILE", file_path))
            .collect()
    }

    /// Run a formatter against a real file on disk.
    fn run_formatter(&self, fmt: &FormatterConfig, file_path: &str) -> bool {
        if !Path::new(file_path).is_file() {
            return false;
        }
        let cmd = self.build_command(fmt, file_path);
        let env: HashMap<String, String> = std::env::vars()
            .chain(fmt.environment.iter().map(|(k, v)| (k.clone(), v.clone())))
            .collect();
        match Command::new(&cmd[0]).args(&cmd[1..]).envs(&env).output() {
            Ok(output) => output.status.success(),
            Err(_) => false,
        }
    }

    /// Run a formatter against in-memory code via a temp file.
    fn run_formatter_tempfile(&self, fmt: &FormatterConfig, code: &str, extension: &str) -> String {
        let mut tmp = match Builder::new().suffix(extension).tempfile() {
            Ok(t) => t,
            Err(_) => return code.to_string(),
        };
        if std::io::Write::write_all(&mut tmp, code.as_bytes()).is_err() {
            return code.to_string();
        }
        let tmp_path = tmp.path().to_string_lossy().to_string();
        let cmd = self.build_command(fmt, &tmp_path);
        let env: HashMap<String, String> = std::env::vars()
            .chain(fmt.environment.iter().map(|(k, v)| (k.clone(), v.clone())))
            .collect();
        match Command::new(&cmd[0]).args(&cmd[1..]).envs(&env).output() {
            Ok(output) if output.status.success() => {
                std::fs::read_to_string(&tmp_path).unwrap_or_else(|_| code.to_string())
            }
            _ => code.to_string(),
        }
    }
}

/// Global formatter manager instance (created lazily per process).
static FORMATTER_MANAGER: std::sync::OnceLock<FormatterManager> =
    std::sync::OnceLock::new();

/// Returns the global formatter manager.
pub fn formatter_manager() -> &'static FormatterManager {
    FORMATTER_MANAGER.get_or_init(FormatterManager::new)
}

/// Format a file using the global manager. Returns true on success.
pub fn format_file<P: AsRef<Path>>(path: P) -> bool {
    formatter_manager().format_file(path)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builtin_formatters_are_present() {
        let formatters = builtin_formatters();
        let names: Vec<&str> = formatters.iter().map(|f| f.name.as_str()).collect();
        assert!(names.contains(&"ruff"));
        assert!(names.contains(&"prettier"));
        assert!(names.contains(&"rustfmt"));
        assert!(names.contains(&"gofmt"));
        assert!(names.contains(&"clang-format"));
    }

    #[test]
    fn new_manager_has_all_builtins() {
        let mgr = FormatterManager::new();
        assert_eq!(mgr.formatters().len(), builtin_formatters().len());
        assert!(!mgr.loaded);
    }

    #[test]
    fn disable_all_via_false() {
        let mut mgr = FormatterManager::new();
        mgr.load_from_config(Some(&serde_json::Value::Bool(false)));
        assert!(mgr.loaded);
        assert!(mgr.formatters().iter().all(|f| f.disabled));
        assert!(mgr.list_available().is_empty());
    }

    #[test]
    fn disable_all_via_object() {
        let mut mgr = FormatterManager::new();
        mgr.load_from_config(Some(&serde_json::json!({ "disabled": true })));
        assert!(mgr.formatters().iter().all(|f| f.disabled));
    }

    #[test]
    fn enable_all_via_true() {
        let mut mgr = FormatterManager::new();
        mgr.load_from_config(Some(&serde_json::Value::Bool(true)));
        assert!(mgr.loaded);
        assert!(!mgr.formatters().iter().any(|f| f.disabled));
    }

    #[test]
    fn custom_formatter_override() {
        let mut mgr = FormatterManager::new();
        mgr.load_from_config(Some(&serde_json::json!({
            "ruff": { "disabled": true },
            "custom-fmt": {
                "command": ["my-fmt", "--write", "$FILE"],
                "extensions": [".xyz"]
            }
        })));
        let formatters = mgr.formatters();
        let ruff = formatters.iter().find(|f| f.name == "ruff").unwrap();
        assert!(ruff.disabled);
        let custom = formatters.iter().find(|f| f.name == "custom-fmt").unwrap();
        assert_eq!(custom.extensions, vec![".xyz".to_string()]);
    }

    #[test]
    fn get_formatter_for_extension() {
        let mut mgr = FormatterManager::new();
        mgr.load_from_config(Some(&serde_json::Value::Bool(true)));
        // Unknown extension → no formatter available
        assert!(mgr.get_formatter_for("src/unknown.xyz").is_none());
    }

    #[test]
    fn is_formattable_matches_extension() {
        let mut mgr = FormatterManager::new();
        mgr.load_from_config(Some(&serde_json::Value::Bool(true)));
        // Unknown extension → never formattable
        assert!(!mgr.is_formattable("src/unknown.xyz"));
    }

    #[test]
    fn format_files_returns_map() {
        let mgr = FormatterManager::new();
        let result = mgr.format_files(&["a.rs".into(), "b.py".into()]);
        assert_eq!(result.len(), 2);
        // Not loaded → neither formattable
        assert!(!result.values().any(|v| *v));
    }

    #[test]
    fn check_requirement_file_exists() {
        let mgr = FormatterManager::new();
        assert!(!mgr.check_requirement("nonexistent-file-xyz"));
    }

    #[test]
    fn build_command_replaces_dollar_file() {
        let mgr = FormatterManager::new();
        let fmt = FormatterConfig {
            name: "test".into(),
            command: vec!["fmt".into(), "$FILE".into()],
            extensions: vec![],
            environment: HashMap::new(),
            disabled: false,
            requirements: None,
        };
        let cmd = mgr.build_command(&fmt, "src/main.rs");
        assert_eq!(cmd, vec!["fmt", "src/main.rs"]);
    }

    #[test]
    fn global_format_file_delegates() {
        // Just calls the global manager without panicking on a missing file.
        assert!(!format_file("nonexistent-file-xyz.rs"));
    }
}
