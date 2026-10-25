//! Rust-native plugin support.
//!
//! Python plugins are `.py` files executed inside the interpreter; the Rust
//! port cannot embed CPython, so plugins are declared as data instead:
//!
//! ```text
//! ~/.apex/plugins/<name>/plugin.json
//! {
//!   "name": "git-extras",
//!   "version": "1.0.0",
//!   "description": "Extra git helpers",
//!   "enabled": true,
//!   "tools": [
//!     {
//!       "name": "changed_files",
//!       "description": "List files changed since a ref",
//!       "parameters": {"type": "object", "properties": {"ref": {"type": "string"}}, "required": ["ref"]},
//!       "command": "git diff --name-only {ref}"
//!     }
//!   ]
//! }
//! ```
//!
//! Each declared tool is exposed to the model as `plugin_<plugin>_<tool>` and
//! runs either through `sh -c` (`command`, with `{arg}` placeholders shell-escaped)
//! or without a shell (`args`, argv template). The environment gets
//! `APEX_PLUGIN_NAME`, `APEX_PLUGIN_DIR`, `APEX_TOOL_NAME` and `APEX_PLUGIN_ARGS`
//! (JSON). Directory override for tests/tools: `APEX_PLUGINS_DIR`.

use serde::Deserialize;
use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

pub const PLUGIN_TOOL_PREFIX: &str = "plugin_";

#[derive(Debug, Clone, Deserialize)]
pub struct PluginTool {
    pub name: String,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub parameters: Option<Value>,
    /// Shell command template; `{arg}` placeholders are substituted shell-escaped.
    #[serde(default)]
    pub command: Option<String>,
    /// Alternative to `command`: program + argv template, executed without a shell.
    #[serde(default)]
    pub args: Option<Vec<String>>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct PluginManifest {
    #[serde(default)]
    pub name: Option<String>,
    #[serde(default)]
    pub version: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default)]
    pub tools: Vec<PluginTool>,
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Clone)]
pub struct PluginInfo {
    pub name: String,
    pub path: PathBuf,
    pub manifest: Option<PluginManifest>,
}

impl PluginInfo {
    pub fn enabled(&self) -> bool {
        self.manifest.as_ref().map(|m| m.enabled).unwrap_or(true)
    }

    pub fn version(&self) -> String {
        self.manifest
            .as_ref()
            .and_then(|m| m.version.clone())
            .unwrap_or_default()
    }

    pub fn description(&self) -> String {
        self.manifest
            .as_ref()
            .and_then(|m| m.description.clone())
            .unwrap_or_default()
    }

    pub fn tools(&self) -> &[PluginTool] {
        self.manifest
            .as_ref()
            .map(|m| m.tools.as_slice())
            .unwrap_or(&[])
    }
}

fn plugins_dir() -> PathBuf {
    if let Ok(dir) = std::env::var("APEX_PLUGINS_DIR") {
        if !dir.is_empty() {
            return PathBuf::from(dir);
        }
    }
    crate::config::home_dir()
        .unwrap_or_default()
        .join(".apex")
        .join("plugins")
}

/// Discover plugins: every subdirectory holding a `plugin.json`, plus top-level
/// `*.json` manifest files. Legacy `.toml` files / bare directories are listed
/// without a manifest (so `apex-rs plugins` still reports them).
pub fn discover_plugins() -> Vec<PluginInfo> {
    load_manifests_from(&plugins_dir())
}

pub fn load_manifests_from(base: &Path) -> Vec<PluginInfo> {
    let mut out = Vec::new();
    let Ok(rd) = fs::read_dir(base) else {
        return out;
    };
    for e in rd.flatten() {
        let p = e.path();
        let dir_name = e.file_name().to_string_lossy().to_string();
        if p.is_dir() {
            let manifest_path = p.join("plugin.json");
            let manifest = fs::read_to_string(&manifest_path)
                .ok()
                .and_then(|data| serde_json::from_str::<PluginManifest>(&data).ok());
            out.push(PluginInfo {
                name: manifest
                    .as_ref()
                    .and_then(|m| m.name.clone())
                    .unwrap_or(dir_name),
                path: p,
                manifest,
            });
        } else if p.extension().and_then(|x| x.to_str()) == Some("json") {
            let manifest = fs::read_to_string(&p)
                .ok()
                .and_then(|data| serde_json::from_str::<PluginManifest>(&data).ok());
            let stem = p
                .file_stem()
                .map(|s| s.to_string_lossy().to_string())
                .unwrap_or_default();
            out.push(PluginInfo {
                name: manifest
                    .as_ref()
                    .and_then(|m| m.name.clone())
                    .unwrap_or(stem),
                path: p,
                manifest,
            });
        } else if p.extension().and_then(|x| x.to_str()) == Some("toml") {
            out.push(PluginInfo {
                name: dir_name,
                path: p,
                manifest: None,
            });
        }
    }
    out.sort_by(|a, b| a.name.cmp(&b.name));
    out
}

fn sanitize(name: &str) -> String {
    name.chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '_' {
                c
            } else {
                '_'
            }
        })
        .collect()
}

/// Full model-facing tool name for a plugin tool.
pub fn tool_full_name(plugin: &str, tool: &str) -> String {
    format!(
        "{}{}_{}",
        PLUGIN_TOOL_PREFIX,
        sanitize(plugin),
        sanitize(tool)
    )
}

/// OpenAI `tools` array entries for every enabled plugin tool.
pub fn plugin_tools() -> Vec<Value> {
    let mut out = Vec::new();
    for plugin in discover_plugins() {
        if !plugin.enabled() {
            continue;
        }
        for tool in plugin.tools() {
            if tool.command.is_none() && tool.args.is_none() {
                continue;
            }
            let description = tool
                .description
                .clone()
                .unwrap_or_else(|| format!("Plugin tool {} from {}", tool.name, plugin.name));
            let parameters = tool
                .parameters
                .clone()
                .unwrap_or_else(|| json!({"type": "object", "properties": {}}));
            out.push(json!({
                "type": "function",
                "function": {
                    "name": tool_full_name(&plugin.name, &tool.name),
                    "description": description,
                    "parameters": parameters,
                }
            }));
        }
    }
    out
}

/// Value → template substitution text. Strings are taken verbatim, everything
/// else is compact JSON.
fn substitute_value(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        other => other.to_string(),
    }
}

/// POSIX shell quoting: wrap in single quotes, escaping embedded quotes.
fn shell_escape(s: &str) -> String {
    format!("'{}'", s.replace('\'', "'\\''"))
}

/// Replace `{key}` placeholders. `escape` controls shell escaping of values.
fn fill_template(template: &str, args: &Value, escape: bool) -> String {
    let mut out = String::new();
    let mut rest = template;
    while let Some(start) = rest.find('{') {
        let Some(end_rel) = rest[start + 1..].find('}') else {
            break;
        };
        let end = start + 1 + end_rel;
        let key = &rest[start + 1..end];
        // Only substitute simple identifiers; leave other braces untouched.
        if !key.is_empty() && key.chars().all(|c| c.is_ascii_alphanumeric() || c == '_') {
            out.push_str(&rest[..start]);
            let raw = args.get(key).map(substitute_value).unwrap_or_default();
            let value = if escape { shell_escape(&raw) } else { raw };
            out.push_str(&value);
            rest = &rest[end + 1..];
        } else {
            out.push_str(&rest[..start + 1]);
            rest = &rest[start + 1..];
        }
    }
    out.push_str(rest);
    out
}

/// Run a registered plugin tool. `plugin_dir` is exported to the command.
fn run_plugin_tool(
    plugin_name: &str,
    plugin_dir: &Path,
    tool: &PluginTool,
    args: &Value,
    cwd: &Path,
) -> String {
    let args_json = serde_json::to_string(args).unwrap_or_else(|_| "{}".to_string());
    let base_env = |cmd: &mut Command| {
        cmd.env("APEX_PLUGIN_NAME", plugin_name)
            .env("APEX_PLUGIN_DIR", plugin_dir)
            .env("APEX_TOOL_NAME", &tool.name)
            .env("APEX_PLUGIN_ARGS", &args_json);
    };

    let output = if let Some(template) = &tool.command {
        let cmdline = fill_template(template, args, true);
        let mut cmd = Command::new("sh");
        cmd.arg("-c").arg(cmdline).current_dir(cwd);
        base_env(&mut cmd);
        cmd.output()
    } else if let Some(argv) = &tool.args {
        if argv.is_empty() {
            return "ERROR: plugin tool has an empty 'args' array".to_string();
        }
        let expanded: Vec<String> = argv.iter().map(|a| fill_template(a, args, false)).collect();
        let mut cmd = Command::new(&expanded[0]);
        cmd.args(&expanded[1..]).current_dir(cwd);
        base_env(&mut cmd);
        cmd.output()
    } else {
        return "ERROR: plugin tool declares neither 'command' nor 'args'".to_string();
    };

    match output {
        Ok(o) => {
            let mut s = String::from_utf8_lossy(&o.stdout).to_string();
            if !o.stderr.is_empty() {
                if !s.is_empty() && !s.ends_with('\n') {
                    s.push('\n');
                }
                s.push_str("STDERR:\n");
                s.push_str(&String::from_utf8_lossy(&o.stderr));
            }
            if !o.status.success() {
                s.push_str(&format!("\n[exit {}]", o.status.code().unwrap_or(-1)));
            }
            if s.is_empty() {
                s = "[no output]".to_string();
            }
            s
        }
        Err(e) => format!("ERROR: {e}"),
    }
}

/// Look the fully-qualified tool name up in the manifests and run it.
/// Returns `None` when no plugin declares that tool.
pub fn execute_plugin_tool(name: &str, args: &Value, cwd: &Path) -> Option<String> {
    let registry = discover_plugins();
    execute_registered(&registry, name, args, cwd)
}

fn execute_registered(
    registry: &[PluginInfo],
    name: &str,
    args: &Value,
    cwd: &Path,
) -> Option<String> {
    for plugin in registry {
        if !plugin.enabled() {
            continue;
        }
        for tool in plugin.tools() {
            if tool_full_name(&plugin.name, &tool.name) == name {
                return Some(run_plugin_tool(&plugin.name, &plugin.path, tool, args, cwd));
            }
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn write_plugin(dir: &Path, name: &str, json_body: &str) {
        let pdir = dir.join(name);
        fs::create_dir_all(&pdir).unwrap();
        fs::write(pdir.join("plugin.json"), json_body).unwrap();
    }

    #[test]
    fn discovers_manifest_and_reports_tools() {
        let dir = tempdir().unwrap();
        write_plugin(
            dir.path(),
            "greeter",
            r#"{
                "name": "greeter",
                "version": "1.2.3",
                "description": "Says hello",
                "tools": [{"name": "hello", "command": "echo hi"}]
            }"#,
        );
        write_plugin(dir.path(), "broken", "{not json");
        fs::create_dir_all(dir.path().join("legacy")).unwrap();

        let plugins = load_manifests_from(dir.path());
        assert_eq!(plugins.len(), 3);

        let greeter = plugins.iter().find(|p| p.name == "greeter").unwrap();
        assert_eq!(greeter.version(), "1.2.3");
        assert_eq!(greeter.description(), "Says hello");
        assert_eq!(greeter.tools().len(), 1);
        assert!(greeter.enabled());

        let broken = plugins.iter().find(|p| p.name == "broken").unwrap();
        assert!(broken.manifest.is_none());

        let legacy = plugins.iter().find(|p| p.name == "legacy").unwrap();
        assert!(legacy.manifest.is_none());
    }

    #[test]
    fn tool_names_are_prefixed_and_sanitized() {
        assert_eq!(
            tool_full_name("git-extras", "changed.files"),
            "plugin_git_extras_changed_files"
        );
    }

    #[cfg(unix)]
    #[test]
    fn executes_shell_command_with_substitution() {
        let dir = tempdir().unwrap();
        write_plugin(
            dir.path(),
            "tpl",
            r#"{"tools": [{"name": "greet", "command": "printf 'hello %s' {who}"}]}"#,
        );
        let registry = load_manifests_from(dir.path());
        let out = execute_registered(
            &registry,
            "plugin_tpl_greet",
            &json!({"who": "world"}),
            dir.path(),
        )
        .unwrap();
        assert_eq!(out, "hello world");

        // Shell-escaped: a quote in the value must not break out of the argument.
        let out = execute_registered(
            &registry,
            "plugin_tpl_greet",
            &json!({"who": "a'; rm -rf /tmp/nope; echo 'b"}),
            dir.path(),
        )
        .unwrap();
        assert!(out.contains("a'; rm -rf /tmp/nope; echo 'b"), "got: {out}");
        assert!(
            !out.contains("hello b\n"),
            "injection should not execute twice: {out}"
        );
    }

    #[cfg(unix)]
    #[test]
    fn executes_argv_style_without_shell() {
        let dir = tempdir().unwrap();
        write_plugin(
            dir.path(),
            "argv",
            r#"{"tools": [{"name": "echoer", "args": ["printf", "%s-%s", "{a}", "{b}"]}]}"#,
        );
        let registry = load_manifests_from(dir.path());
        let out = execute_registered(
            &registry,
            "plugin_argv_echoer",
            &json!({"a": "one", "b": "two"}),
            dir.path(),
        )
        .unwrap();
        assert_eq!(out, "one-two");
    }

    #[test]
    fn disabled_plugins_are_skipped() {
        let dir = tempdir().unwrap();
        write_plugin(
            dir.path(),
            "off",
            r#"{"enabled": false, "tools": [{"name": "x", "command": "echo x"}]}"#,
        );
        let registry = load_manifests_from(dir.path());
        assert!(execute_registered(&registry, "plugin_off_x", &json!({}), dir.path()).is_none());
    }

    #[test]
    fn unknown_plugin_tool_returns_none() {
        let dir = tempdir().unwrap();
        let registry = load_manifests_from(dir.path());
        assert!(
            execute_registered(&registry, "plugin_missing_x", &json!({}), dir.path()).is_none()
        );
    }
}
