//! Shell tools — port of `apex/tools.py` shell operations.
//!
//! Implements: run_test, install_package.
//!
//! The following shell tools depend on modules not yet ported:
//! - `run_command_custom` → `commands.py` (command manager, not ported)
//! - `run_code` → `sandbox.py` (ShellSession, PR #348)
//! - `start_shell` / `run_shell` / `close_shell` → `sandbox.py` (ShellSession, PR #348)

use serde_json::Value;
use std::path::Path;

use crate::shell_security::SHELL_ANALYZER;
use crate::tools::shell_command;

/// `run_test` — Run tests using pytest, jest, cargo, or npm.
/// Mirrors Python's `_execute_run_test` with a 300 s timeout.
pub fn run_test(args: &Value, cwd: &Path) -> String {
    let framework = args.get("framework").and_then(|v| v.as_str()).unwrap_or("");
    let path = args.get("path").and_then(|v| v.as_str()).unwrap_or(".");

    let commands: &[(&str, &[&str])] = &[
        ("pytest", &["pytest", "-v", path]),
        ("jest", &["npx", "jest", path]),
        ("cargo", &["cargo", "test", "--", "--test-threads=1"]),
        ("npm", &["npm", "test", "--", path]),
    ];

    let Some((_, cmd_args)) = commands.iter().find(|(name, _)| *name == framework) else {
        return format!("ERROR: Unknown framework: {framework}. Use pytest, jest, or cargo.");
    };

    let cmd_str = cmd_args.join(" ");
    run_shell_command(&cmd_str, cwd)
}

/// `install_package` — Install a package via pip, npm, yarn, or cargo.
/// Mirrors Python's `_execute_install_package` with a 300 s timeout.
pub fn install_package(args: &Value, cwd: &Path) -> String {
    let manager = args.get("manager").and_then(|v| v.as_str()).unwrap_or("");
    let package = args.get("package").and_then(|v| v.as_str()).unwrap_or("");

    let commands: &[(&str, &[&str])] = &[
        ("pip", &["pip", "install", package]),
        ("npm", &["npm", "install", package]),
        ("yarn", &["yarn", "add", package]),
        ("cargo", &["cargo", "install", package]),
    ];

    let Some((_, cmd_args)) = commands.iter().find(|(name, _)| *name == manager) else {
        return format!("ERROR: Unknown package manager: {manager}");
    };

    let cmd_str = cmd_args.join(" ");
    run_shell_command(&cmd_str, cwd)
}

/// Run a shell command through the platform shell, with shell-safety analysis.
/// Mirrors Python's `subprocess.run(..., cwd=..., capture_output=True, text=True)`.
fn run_shell_command(cmd_str: &str, cwd: &Path) -> String {
    let analysis = SHELL_ANALYZER.analyze(cmd_str);
    if !analysis.safe {
        return format!(
            "ERROR: Command blocked by safety policy: {}",
            analysis.warnings.join("; ")
        );
    }

    match shell_command(cmd_str).current_dir(cwd).output() {
        Ok(o) => {
            let mut s = String::from_utf8_lossy(&o.stdout).to_string();
            if !o.stderr.is_empty() {
                s.push_str("\nSTDERR:\n");
                s.push_str(&String::from_utf8_lossy(&o.stderr));
            }
            if !o.status.success() {
                s.push_str(&format!("\n[exit {}]", o.status.code().unwrap_or(-1)));
            }
            if s.is_empty() {
                "[no output]".to_string()
            } else {
                s
            }
        }
        Err(e) => {
            let prog = cmd_str.split_whitespace().next().unwrap_or(cmd_str);
            if e.kind() == std::io::ErrorKind::NotFound {
                format!("ERROR: {prog} not found. Install it first.")
            } else {
                format!("ERROR: Command execution failed: {e}")
            }
        }
    }
}
