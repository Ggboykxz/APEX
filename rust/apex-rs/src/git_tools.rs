//! Git tools — port of `apex/tools.py` git operations not yet wired.
//!
//! Implements: add_git_hook, git_status_enhanced, git_log_enhanced.
//!
//! Existing git tools (git_status, git_diff, git_log, git_stage, git_unstage,
//! git_commit, git_create_branch, git_switch_branch, git_delete_branch,
//! git_list_branches, git_pre_commit, git_create_pr, git_undo) live in
//! `tools.rs`. This module adds the hook-management surface from PR #343.

use serde_json::Value;
use std::fs;
use std::path::Path;

use crate::shell_security::SHELL_ANALYZER;

/// Valid git hook names, mirrored from `apex/tools.py`.
const VALID_HOOKS: &[&str] = &[
    "applypatch-msg",
    "pre-applypatch",
    "post-applypatch",
    "pre-commit",
    "pre-merge-commit",
    "prepare-commit-msg",
    "commit-msg",
    "post-commit",
    "pre-rebase",
    "post-checkout",
    "post-merge",
    "pre-push",
    "pre-receive",
    "update",
    "post-receive",
    "post-update",
    "push-to-checkout",
    "pre-auto-gc",
    "post-rewrite",
    "sendemail-validate",
    "fsmonitor-watchman",
];

/// `add_git_hook` — Install a git hook script under `.git/hooks/<hook>`.
/// Mirrors Python's `_execute_add_git_hook`.
pub fn add_git_hook(args: &Value, cwd: &Path) -> String {
    let hook = args.get("hook").and_then(|v| v.as_str()).unwrap_or("");
    let command = args.get("command").and_then(|v| v.as_str()).unwrap_or("");

    if hook.is_empty() {
        return "ERROR: No hook name provided".to_string();
    }

    if !VALID_HOOKS.contains(&hook) {
        let valid: Vec<String> = VALID_HOOKS.iter().map(|s| s.to_string()).collect();
        return format!(
            "ERROR: Invalid git hook name: {hook}. Valid hooks: {}",
            valid.join(", ")
        );
    }

    let git_dir = cwd.join(".git");
    if !git_dir.exists() {
        return "ERROR: Not a git repository".to_string();
    }

    let hooks_dir = git_dir.join("hooks");
    if let Err(e) = fs::create_dir_all(&hooks_dir) {
        return format!("ERROR: Cannot create hooks directory: {e}");
    }

    let analysis = SHELL_ANALYZER.analyze(command);
    if !analysis.safe {
        return format!(
            "ERROR: Command rejected by security analyzer: {}",
            analysis.category.value()
        );
    }

    let hook_path = hooks_dir.join(hook);
    let content = format!("#!/bin/sh\n{command}\n");
    match fs::write(&hook_path, content) {
        Ok(_) => {
            set_hook_executable(&hook_path);
            format!("SUCCESS: Added {hook} hook")
        }
        Err(e) => format!("ERROR: Cannot write hook: {e}"),
    }
}

/// Make a hook script executable on Unix; no-op on Windows.
#[cfg(unix)]
fn set_hook_executable(path: &Path) {
    use std::os::unix::fs::PermissionsExt;
    let _ = fs::set_permissions(path, fs::Permissions::from_mode(0o755));
}

#[cfg(not(unix))]
fn set_hook_executable(_path: &Path) {}

/// `git_status_enhanced` — Richer git status with staged/unstaged/untracked separation.
pub fn git_status_enhanced(cwd: &Path) -> String {
    let git_dir = cwd.join(".git");
    if !git_dir.exists() {
        return "ERROR: Not a git repository".to_string();
    }

    let porcelain = match std::process::Command::new("git")
        .args(["status", "--porcelain=v1"])
        .current_dir(cwd)
        .output()
    {
        Ok(o) => String::from_utf8_lossy(&o.stdout).to_string(),
        Err(e) => return format!("ERROR: Git status failed: {e}"),
    };

    if porcelain.trim().is_empty() {
        return "[working tree clean]".to_string();
    }

    let mut staged: Vec<String> = Vec::new();
    let mut unstaged: Vec<String> = Vec::new();
    let mut untracked: Vec<String> = Vec::new();

    for line in porcelain.lines() {
        if line.is_empty() {
            continue;
        }
        let (xy, path) = line.split_at(2);
        let path = path.trim();
        let x = xy.chars().next().unwrap_or(' ');
        let y = xy.chars().nth(1).unwrap_or(' ');

        match (x, y) {
            ('M' | 'A' | 'D' | 'R' | 'C', ' ') => staged.push(format!("  staged: {path}")),
            (' ', 'M' | 'D') => unstaged.push(format!("  unstaged: {path}")),
            ('?', '?') => untracked.push(format!("  untracked: {path}")),
            _ => staged.push(format!("  {xy} {path}")),
        }
    }

    let mut out = String::new();
    if !staged.is_empty() {
        out.push_str("Staged:\n");
        out.push_str(&staged.join("\n"));
        out.push('\n');
    }
    if !unstaged.is_empty() {
        out.push_str("Unstaged:\n");
        out.push_str(&unstaged.join("\n"));
        out.push('\n');
    }
    if !untracked.is_empty() {
        out.push_str("Untracked:\n");
        out.push_str(&untracked.join("\n"));
    }

    out.trim_end().to_string()
}

/// `git_log_enhanced` — Richer git log with hash, subject, author, date.
pub fn git_log_enhanced(args: &Value, cwd: &Path) -> String {
    let n = args.get("n").and_then(|v| v.as_i64()).unwrap_or(10).max(1);

    let git_dir = cwd.join(".git");
    if !git_dir.exists() {
        return "ERROR: Not a git repository".to_string();
    }

    let output = match std::process::Command::new("git")
        .args([
            "log",
            &format!("-{n}"),
            "--pretty=format:%h %s (%an, %ad)",
            "--date=short",
        ])
        .current_dir(cwd)
        .output()
    {
        Ok(o) => String::from_utf8_lossy(&o.stdout).to_string(),
        Err(e) => return format!("ERROR: Git log failed: {e}"),
    };

    if output.trim().is_empty() {
        "[no commits]".to_string()
    } else {
        output
    }
}
