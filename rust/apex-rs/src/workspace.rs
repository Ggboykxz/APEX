//! Workspace awareness — port of `apex/workspace.py`.
//!
//! `WorkspaceManager::analyze` snapshots the Git state (branch, commit, dirty
//! flag, remote, ahead/behind, first tags) and detects the language, package
//! manager and test framework from marker files. The resulting
//! `[WORKSPACE CONTEXT]` block is appended to the agent system prompt.
//!
//! Two deliberate divergences from Python, both recorded in `PARITY.md`:
//!
//! * Python runs `git fetch --dry-run` after finding a GitHub remote and
//!   discards the output; the Rust port skips that network round-trip.
//! * On a tagless repository Python returns `[""]` (`"".split('\n')`) while
//!   the Rust port returns an empty list.

use serde::Serialize;
use std::env;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

/// Python uses a 5-second timeout on every git invocation.
const GIT_TIMEOUT: Duration = Duration::from_secs(5);

/// Python: `GitContext` dataclass.
#[derive(Debug, Default, Clone, PartialEq, Eq, Serialize)]
pub struct GitContext {
    pub branch: String,
    pub remote: String,
    pub remote_url: String,
    pub is_dirty: bool,
    pub commit: String,
    pub commits_ahead: i64,
    pub commits_behind: i64,
    pub pr_number: Option<i64>,
    pub pr_title: String,
    pub pr_url: String,
    pub tags: Vec<String>,
}

/// Python: `WorkspaceContext` dataclass.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct WorkspaceContext {
    pub root: PathBuf,
    pub git: Option<GitContext>,
    pub language: String,
    pub package_manager: String,
    pub test_framework: String,
}

impl WorkspaceContext {
    fn new(root: PathBuf) -> Self {
        Self {
            root,
            git: None,
            language: String::new(),
            package_manager: String::new(),
            test_framework: String::new(),
        }
    }
}

/// Language markers in Python's dict order (first match wins).
const LANGUAGE_MARKERS: &[(&str, &str)] = &[
    ("pyproject.toml", "Python"),
    ("requirements.txt", "Python"),
    ("setup.py", "Python"),
    ("package.json", "JavaScript"),
    ("go.mod", "Go"),
    ("Cargo.toml", "Rust"),
    ("pom.xml", "Java"),
    ("build.gradle", "Kotlin"),
];

/// Package-manager markers in Python's dict order.
const PACKAGE_MANAGER_MARKERS: &[(&str, &str)] = &[
    ("package-lock.json", "npm"),
    ("yarn.lock", "yarn"),
    ("pnpm-lock.yaml", "pnpm"),
    ("requirements.txt", "pip"),
    ("pyproject.toml", "poetry"),
    ("go.mod", "go"),
    ("Cargo.lock", "cargo"),
    ("Gemfile", "bundler"),
];

/// Test-framework markers in Python's dict order.
const TEST_FRAMEWORK_MARKERS: &[(&str, &str)] = &[
    ("pytest.ini", "pytest"),
    ("pyproject.toml", "pytest"),
    ("jest.config.js", "jest"),
    ("vitest.config.ts", "vitest"),
    ("go.sum", "testing"),
    ("Cargo.toml", "cargo test"),
];

/// Result of one `git` invocation.
struct GitOutput {
    /// Exit code; `None` when the process was killed by a signal.
    status: Option<i32>,
    stdout: String,
}

impl GitOutput {
    fn succeeded(&self) -> bool {
        self.status == Some(0)
    }
}

/// Run `git <args>` in `root` with Python's 5-second timeout.
///
/// Returns `None` when git cannot be spawned or the deadline expires; both
/// cases are exceptions in Python, which aborts `_get_git_context` and keeps
/// the context gathered so far. Non-zero exits are returned normally so the
/// caller can mirror Python's `returncode` checks.
fn run_git(root: &Path, args: &[&str]) -> Option<GitOutput> {
    let mut child = Command::new("git")
        .args(args)
        .current_dir(root)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .ok()?;

    // Drain both pipes on separate threads so a large `git status` cannot
    // fill the pipe buffer and block the child before it exits.
    let mut stdout = child.stdout.take()?;
    let mut stderr = child.stderr.take()?;
    let stdout_reader = thread::spawn(move || {
        let mut buf = Vec::new();
        let _ = stdout.read_to_end(&mut buf);
        buf
    });
    let stderr_reader = thread::spawn(move || {
        let mut buf = Vec::new();
        let _ = stderr.read_to_end(&mut buf);
        buf
    });

    let deadline = Instant::now() + GIT_TIMEOUT;
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break Some(status),
            Ok(None) if Instant::now() < deadline => thread::sleep(Duration::from_millis(10)),
            _ => {
                let _ = child.kill();
                let _ = child.wait();
                break None;
            }
        }
    };

    let stdout = stdout_reader.join().unwrap_or_default();
    let _ = stderr_reader.join();
    Some(GitOutput {
        status: status.and_then(|s| s.code()),
        stdout: String::from_utf8_lossy(&stdout).to_string(),
    })
}

/// Python: `len(stdout.strip().split("\n")) if stdout.strip() else 0`.
fn count_lines(output: &str) -> i64 {
    let trimmed = output.trim();
    if trimmed.is_empty() {
        0
    } else {
        trimmed.lines().count() as i64
    }
}

/// Python: `WorkspaceManager`.
#[derive(Debug, Clone)]
pub struct WorkspaceManager {
    root: PathBuf,
    context: Option<WorkspaceContext>,
}

impl WorkspaceManager {
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self {
            root: root.into(),
            context: None,
        }
    }

    /// Python: `analyze()`. The context is cached for the manager's lifetime.
    pub fn analyze(&mut self) -> &WorkspaceContext {
        let mut context = WorkspaceContext::new(self.root.clone());

        if self.root.join(".git").exists() {
            context.git = Some(self.get_git_context());
        }

        context.language = self.detect_language();
        context.package_manager = self.detect_package_manager();
        context.test_framework = self.detect_test_framework();

        self.context = Some(context);
        self.context
            .as_ref()
            .expect("workspace context was just set")
    }

    /// Python: `_get_git_context()`. Any git failure degrades to defaults.
    fn get_git_context(&self) -> GitContext {
        let mut ctx = GitContext::default();
        let root = self.root.as_path();

        let out = match run_git(root, &["rev-parse", "--abbrev-ref", "HEAD"]) {
            Some(out) => out,
            None => return ctx,
        };
        if out.succeeded() {
            ctx.branch = out.stdout.trim().to_string();
        }

        let out = match run_git(root, &["rev-parse", "HEAD"]) {
            Some(out) => out,
            None => return ctx,
        };
        if out.succeeded() {
            ctx.commit = out.stdout.trim().chars().take(8).collect();
        }

        let out = match run_git(root, &["status", "--porcelain"]) {
            Some(out) => out,
            None => return ctx,
        };
        ctx.is_dirty = !out.stdout.trim().is_empty();

        let out = match run_git(root, &["remote", "get-url", "origin"]) {
            Some(out) => out,
            None => return ctx,
        };
        if out.succeeded() {
            ctx.remote_url = out.stdout.trim().to_string();
            if ctx.remote_url.contains("github.com") {
                let owner_repo = ctx.remote_url.replace(".git", "");
                ctx.remote = owner_repo
                    .split("github.com/")
                    .last()
                    .unwrap_or("")
                    .to_string();
                // Python runs `git fetch --dry-run` here and discards the
                // result; the Rust port skips the network round-trip.
            }
        }

        let out = match run_git(root, &["log", "@{u}..HEAD", "--oneline"]) {
            Some(out) => out,
            None => return ctx,
        };
        ctx.commits_ahead = count_lines(&out.stdout);

        let out = match run_git(root, &["log", "HEAD..@{u}", "--oneline"]) {
            Some(out) => out,
            None => return ctx,
        };
        ctx.commits_behind = count_lines(&out.stdout);

        if env::var_os("GITHUB_HEAD_REF").is_some() {
            let value = env::var("GITHUB_PR_NUMBER").unwrap_or_else(|_| "0".to_string());
            match value.trim().parse::<i64>() {
                Ok(number) => ctx.pr_number = Some(number),
                // Python's `int()` raises, the outer `except` aborts the
                // rest of the collector (so tags stay empty).
                Err(_) => return ctx,
            }
        }

        let out = match run_git(root, &["tag", "--list", "-l", "--sort=-creatordate"]) {
            Some(out) => out,
            None => return ctx,
        };
        if out.succeeded() {
            let trimmed = out.stdout.trim();
            if !trimmed.is_empty() {
                ctx.tags = trimmed.lines().take(5).map(String::from).collect();
            }
        }

        ctx
    }

    /// Python: `_detect_language()`. First marker wins; unknown is `Unknown`.
    fn detect_language(&self) -> String {
        detect_marker(&self.root, LANGUAGE_MARKERS, "Unknown")
    }

    /// Python: `_detect_package_manager()`. Unknown is lowercase `unknown`.
    fn detect_package_manager(&self) -> String {
        detect_marker(&self.root, PACKAGE_MANAGER_MARKERS, "unknown")
    }

    /// Python: `_detect_test_framework()`. Unknown is lowercase `unknown`.
    fn detect_test_framework(&self) -> String {
        detect_marker(&self.root, TEST_FRAMEWORK_MARKERS, "unknown")
    }

    /// Python: `get_system_prompt_context()`, lazily analyzing if needed.
    pub fn get_system_prompt_context(&mut self) -> String {
        if self.context.is_none() {
            self.analyze();
        }
        let context = self.context.as_ref().expect("workspace context is set");

        let mut parts = vec!["[WORKSPACE CONTEXT]".to_string()];

        if let Some(git) = &context.git {
            parts.push(format!("Git branch: {}", git.branch));
            if git.is_dirty {
                parts.push("Git status: dirty (uncommitted changes)".to_string());
            }
            if git.commits_ahead != 0 {
                parts.push(format!("Commits ahead of remote: {}", git.commits_ahead));
            }
            if git.commits_behind != 0 {
                parts.push(format!("Commits behind remote: {}", git.commits_behind));
            }
        }

        parts.push(format!("Language: {}", context.language));
        parts.push(format!("Package manager: {}", context.package_manager));
        parts.push(format!("Test framework: {}", context.test_framework));

        parts.join("\n")
    }
}

fn detect_marker(root: &Path, markers: &[(&str, &str)], fallback: &str) -> String {
    for (file, value) in markers {
        if root.join(file).exists() {
            return (*value).to_string();
        }
    }
    fallback.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::process::Command;

    /// Run git with a fixed identity so tests do not depend on global config.
    fn git(dir: &Path, args: &[&str]) {
        let out = Command::new("git")
            .args(args)
            .current_dir(dir)
            .env("GIT_AUTHOR_NAME", "Test")
            .env("GIT_AUTHOR_EMAIL", "test@example.com")
            .env("GIT_COMMITTER_NAME", "Test")
            .env("GIT_COMMITTER_EMAIL", "test@example.com")
            .output()
            .expect("git must be installed for the workspace tests");
        assert!(
            out.status.success(),
            "git {:?} failed: {}",
            args,
            String::from_utf8_lossy(&out.stderr)
        );
    }

    fn init_repo() -> tempfile::TempDir {
        let dir = tempfile::tempdir().unwrap();
        git(dir.path(), &["init"]);
        git(dir.path(), &["symbolic-ref", "HEAD", "refs/heads/main"]);
        fs::write(dir.path().join("README.md"), "# test\n").unwrap();
        git(dir.path(), &["add", "-A"]);
        git(dir.path(), &["commit", "-m", "init"]);
        dir
    }

    #[test]
    fn git_context_defaults_match_python() {
        let ctx = GitContext::default();
        assert_eq!(ctx.branch, "");
        assert_eq!(ctx.remote, "");
        assert_eq!(ctx.remote_url, "");
        assert!(!ctx.is_dirty);
        assert_eq!(ctx.commit, "");
        assert_eq!(ctx.commits_ahead, 0);
        assert_eq!(ctx.commits_behind, 0);
        assert_eq!(ctx.pr_number, None);
        assert_eq!(ctx.pr_title, "");
        assert_eq!(ctx.pr_url, "");
        assert!(ctx.tags.is_empty());
    }

    #[test]
    fn workspace_context_defaults_match_python() {
        let ctx = WorkspaceContext::new(PathBuf::from("/tmp"));
        assert_eq!(ctx.root, PathBuf::from("/tmp"));
        assert!(ctx.git.is_none());
        assert_eq!(ctx.language, "");
        assert_eq!(ctx.package_manager, "");
        assert_eq!(ctx.test_framework, "");
    }

    #[test]
    fn analyze_non_git_directory() {
        let dir = tempfile::tempdir().unwrap();
        let mut wm = WorkspaceManager::new(dir.path());
        let ctx = wm.analyze();
        assert_eq!(ctx.root, dir.path());
        assert!(ctx.git.is_none());
        assert_eq!(ctx.language, "Unknown");
        assert_eq!(ctx.package_manager, "unknown");
        assert_eq!(ctx.test_framework, "unknown");
    }

    #[test]
    fn analyze_git_repository() {
        let repo = init_repo();
        let mut wm = WorkspaceManager::new(repo.path());
        let ctx = wm.analyze();
        let git = ctx.git.as_ref().expect("a .git directory must be detected");
        assert_eq!(git.branch, "main");
        assert_eq!(git.commit.len(), 8);
        assert!(!git.is_dirty);
        assert_eq!(git.commits_ahead, 0);
        assert_eq!(git.commits_behind, 0);
        assert!(git.tags.is_empty());
    }

    #[test]
    fn detects_every_language_marker_in_python_order() {
        for (file, expected) in LANGUAGE_MARKERS {
            let dir = tempfile::tempdir().unwrap();
            fs::write(dir.path().join(file), "").unwrap();
            let mut wm = WorkspaceManager::new(dir.path());
            assert_eq!(&wm.analyze().language, expected, "marker {file}");
        }
    }

    #[test]
    fn language_priority_is_first_match() {
        let dir = tempfile::tempdir().unwrap();
        fs::write(dir.path().join("package.json"), "{}").unwrap();
        fs::write(dir.path().join("pyproject.toml"), "[project]").unwrap();
        fs::write(dir.path().join("Cargo.toml"), "[package]").unwrap();
        let mut wm = WorkspaceManager::new(dir.path());
        assert_eq!(wm.analyze().language, "Python");
    }

    #[test]
    fn detects_every_package_manager_marker_in_python_order() {
        for (file, expected) in PACKAGE_MANAGER_MARKERS {
            let dir = tempfile::tempdir().unwrap();
            fs::write(dir.path().join(file), "").unwrap();
            let mut wm = WorkspaceManager::new(dir.path());
            assert_eq!(&wm.analyze().package_manager, expected, "marker {file}");
        }
    }

    #[test]
    fn package_manager_priority_is_first_match() {
        let dir = tempfile::tempdir().unwrap();
        fs::write(dir.path().join("yarn.lock"), "").unwrap();
        fs::write(dir.path().join("package-lock.json"), "{}").unwrap();
        let mut wm = WorkspaceManager::new(dir.path());
        assert_eq!(wm.analyze().package_manager, "npm");
    }

    #[test]
    fn detects_every_test_framework_marker_in_python_order() {
        for (file, expected) in TEST_FRAMEWORK_MARKERS {
            let dir = tempfile::tempdir().unwrap();
            fs::write(dir.path().join(file), "").unwrap();
            let mut wm = WorkspaceManager::new(dir.path());
            assert_eq!(&wm.analyze().test_framework, expected, "marker {file}");
        }
    }

    #[test]
    fn test_framework_priority_is_first_match() {
        let dir = tempfile::tempdir().unwrap();
        fs::write(dir.path().join("jest.config.js"), "").unwrap();
        fs::write(dir.path().join("pytest.ini"), "").unwrap();
        let mut wm = WorkspaceManager::new(dir.path());
        assert_eq!(wm.analyze().test_framework, "pytest");
    }

    #[test]
    fn prompt_context_for_non_git_directory_is_exact() {
        let dir = tempfile::tempdir().unwrap();
        let mut wm = WorkspaceManager::new(dir.path());
        assert_eq!(
            wm.get_system_prompt_context(),
            "[WORKSPACE CONTEXT]\nLanguage: Unknown\nPackage manager: unknown\nTest framework: unknown"
        );
    }

    #[test]
    fn prompt_context_is_cached_after_analysis() {
        let dir = tempfile::tempdir().unwrap();
        let mut wm = WorkspaceManager::new(dir.path());
        assert!(wm.get_system_prompt_context().contains("Language: Unknown"));
        fs::write(dir.path().join("Cargo.toml"), "[package]").unwrap();
        assert!(
            wm.get_system_prompt_context().contains("Language: Unknown"),
            "Python caches `self._context`, so later file changes are ignored"
        );
    }

    #[test]
    fn prompt_context_includes_dirty_and_ahead_behind_lines() {
        let remote = tempfile::tempdir().unwrap();
        git(remote.path(), &["init", "--bare"]);
        // The bare repo's default HEAD may still be `master`; point it at the
        // branch we push so the second clone checks out `main`.
        git(remote.path(), &["symbolic-ref", "HEAD", "refs/heads/main"]);

        let repo = init_repo();
        let remote_url = remote.path().to_string_lossy().to_string();
        git(repo.path(), &["remote", "add", "origin", &remote_url]);
        git(repo.path(), &["push", "-u", "origin", "HEAD"]);

        // Two local commits: ahead of the upstream.
        fs::write(repo.path().join("local.txt"), "a\n").unwrap();
        git(repo.path(), &["add", "-A"]);
        git(repo.path(), &["commit", "-m", "local one"]);
        fs::write(repo.path().join("local.txt"), "b\n").unwrap();
        git(repo.path(), &["add", "-A"]);
        git(repo.path(), &["commit", "-m", "local two"]);

        // One commit in a second clone, then fetch: behind the upstream.
        let other = tempfile::tempdir().unwrap();
        git(other.path(), &["clone", &remote_url, "."]);
        fs::write(other.path().join("remote.txt"), "c\n").unwrap();
        git(other.path(), &["add", "-A"]);
        git(other.path(), &["commit", "-m", "remote one"]);
        git(other.path(), &["push"]);
        git(repo.path(), &["fetch", "origin"]);

        // Uncommitted change: dirty.
        fs::write(repo.path().join("README.md"), "# changed\n").unwrap();

        let mut wm = WorkspaceManager::new(repo.path());
        let ctx = wm.get_system_prompt_context();
        let lines: Vec<&str> = ctx.lines().collect();
        assert_eq!(lines[0], "[WORKSPACE CONTEXT]");
        assert_eq!(lines[1], "Git branch: main");
        assert_eq!(lines[2], "Git status: dirty (uncommitted changes)");
        assert_eq!(lines[3], "Commits ahead of remote: 2");
        assert_eq!(lines[4], "Commits behind remote: 1");
        assert_eq!(lines[5], "Language: Unknown");
        assert_eq!(lines[6], "Package manager: unknown");
        assert_eq!(lines[7], "Test framework: unknown");
        assert_eq!(lines.len(), 8);

        let git_ctx = wm.analyze().git.as_ref().unwrap();
        assert!(git_ctx.is_dirty);
        assert_eq!(git_ctx.commits_ahead, 2);
        assert_eq!(git_ctx.commits_behind, 1);
    }

    #[test]
    fn broken_git_directory_degrades_to_defaults() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir(dir.path().join(".git")).unwrap();
        let mut wm = WorkspaceManager::new(dir.path());
        let ctx = wm.analyze();
        let git = ctx
            .git
            .as_ref()
            .expect("presence of `.git` sets a context even when git commands fail");
        assert_eq!(git.branch, "");
        assert_eq!(git.commit, "");
        assert!(!git.is_dirty);
        assert_eq!(git.remote_url, "");
        assert_eq!(git.commits_ahead, 0);
        assert_eq!(git.commits_behind, 0);
        assert!(git.tags.is_empty());
    }

    #[test]
    fn analyzes_with_github_remote() {
        let repo = init_repo();
        git(
            repo.path(),
            &[
                "remote",
                "add",
                "origin",
                "https://github.com/owner/repo.git",
            ],
        );
        let mut wm = WorkspaceManager::new(repo.path());
        let ctx = wm.get_system_prompt_context();
        assert!(ctx.contains("Git branch: main"), "got: {ctx}");
    }

    #[test]
    fn github_remote_sets_owner_repo() {
        let repo = init_repo();
        git(
            repo.path(),
            &[
                "remote",
                "add",
                "origin",
                "https://github.com/owner/repo.git",
            ],
        );
        let mut wm = WorkspaceManager::new(repo.path());
        let ctx = wm.analyze();
        let git_ctx = ctx.git.as_ref().unwrap();
        assert_eq!(git_ctx.remote_url, "https://github.com/owner/repo.git");
        assert_eq!(git_ctx.remote, "owner/repo");
    }

    #[test]
    fn non_github_remote_keeps_remote_empty() {
        let repo = init_repo();
        git(
            repo.path(),
            &[
                "remote",
                "add",
                "origin",
                "https://gitlab.com/owner/repo.git",
            ],
        );
        let mut wm = WorkspaceManager::new(repo.path());
        let ctx = wm.analyze();
        let git_ctx = ctx.git.as_ref().unwrap();
        assert_eq!(git_ctx.remote_url, "https://gitlab.com/owner/repo.git");
        assert_eq!(git_ctx.remote, "");
    }

    #[test]
    fn pr_number_comes_from_github_environment() {
        let previous_head = env::var_os("GITHUB_HEAD_REF");
        let previous_number = env::var_os("GITHUB_PR_NUMBER");

        let repo = init_repo();
        env::set_var("GITHUB_HEAD_REF", "feature/workspace");
        env::set_var("GITHUB_PR_NUMBER", "42");

        let mut wm = WorkspaceManager::new(repo.path());
        let ctx = wm.analyze();
        assert_eq!(ctx.git.as_ref().unwrap().pr_number, Some(42));

        match previous_head {
            Some(value) => env::set_var("GITHUB_HEAD_REF", value),
            None => env::remove_var("GITHUB_HEAD_REF"),
        }
        match previous_number {
            Some(value) => env::set_var("GITHUB_PR_NUMBER", value),
            None => env::remove_var("GITHUB_PR_NUMBER"),
        }
    }

    #[test]
    fn tags_are_capped_at_five() {
        let repo = init_repo();
        for i in 1..=6 {
            git(repo.path(), &["tag", "-a", &format!("v{i}"), "-m", "tag"]);
        }
        let mut wm = WorkspaceManager::new(repo.path());
        let ctx = wm.analyze();
        let tags = &ctx.git.as_ref().unwrap().tags;
        assert_eq!(tags.len(), 5, "got: {tags:?}");
        assert!(tags.iter().all(|tag| tag.starts_with('v')));
    }
}
