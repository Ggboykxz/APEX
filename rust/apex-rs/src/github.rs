//! GitHub integration — port of `apex/github_integration.py`.
//!
//! Same strategy as Python: prefer the `gh` CLI when it is installed, fall back
//! to the REST API with `GITHUB_TOKEN` / `GH_TOKEN`.
//!
//! Two deliberate fixes over the Python reference (see CHANGELOG):
//!
//! * `GitHubClient.create_branch` runs `git checkout -b <branch> origin/<base>`.
//!   Python invokes `gh git checkout …`, and `gh` has no `git` subcommand, so
//!   the Python method always returned `False`.
//! * Errors are propagated (`Result`) instead of being swallowed, so the
//!   `git_create_pr` tool can report why it failed.

use crate::cost::now_iso8601_micros;
use serde_json::{json, Value};
use std::path::Path;
use std::process::Command;

/// `https://api.github.com`, overridable with `APEX_GITHUB_API` (tests).
pub fn api_base_from_env() -> String {
    match std::env::var("APEX_GITHUB_API") {
        Ok(v) if !v.is_empty() => v.trim_end_matches('/').to_string(),
        _ => "https://api.github.com".to_string(),
    }
}

pub struct GitHubClient {
    pub token: String,
    pub owner: String,
    pub repo: String,
    pub api_base: String,
}

impl GitHubClient {
    pub fn new(token: Option<&str>, owner: &str, repo: &str) -> Self {
        let token = token
            .map(|t| t.to_string())
            .or_else(|| std::env::var("GITHUB_TOKEN").ok())
            .filter(|t| !t.is_empty())
            .unwrap_or_default();
        Self {
            token,
            owner: owner.to_string(),
            repo: repo.to_string(),
            api_base: api_base_from_env(),
        }
    }

    pub fn from_env() -> Self {
        let mut client = Self::new(None, "", "");
        if client.token.is_empty() {
            if let Ok(t) = std::env::var("GH_TOKEN") {
                client.token = t;
            }
        }
        client
    }

    /// Override the API root (tests point this at a local fake server).
    pub fn with_api_base(mut self, base: &str) -> Self {
        self.api_base = base.trim_end_matches('/').to_string();
        self
    }

    pub fn set_repo(&mut self, owner: &str, repo: &str) {
        self.owner = owner.to_string();
        self.repo = repo.to_string();
    }

    /// `gh repo view --json owner,name`, then the `origin` remote.
    pub fn detect_repo(&self, cwd: &Path) -> Option<(String, String)> {
        if which("gh").is_some() {
            let out = Command::new("gh")
                .args(["repo", "view", "--json", "owner,name"])
                .current_dir(cwd)
                .output();
            if let Ok(out) = out {
                if out.status.success() {
                    if let Ok(v) = serde_json::from_slice::<Value>(&out.stdout) {
                        let owner = v
                            .get("owner")
                            .and_then(|o| o.get("login"))
                            .and_then(|l| l.as_str());
                        let name = v.get("name").and_then(|n| n.as_str());
                        if let (Some(owner), Some(name)) = (owner, name) {
                            return Some((owner.to_string(), name.to_string()));
                        }
                    }
                }
            }
        }
        let remote = git_output(cwd, &["remote", "get-url", "origin"])?;
        parse_github_remote(&remote)
    }

    fn url(&self, path: &str) -> String {
        format!("{}{}", self.api_base, path)
    }

    pub fn list_issues(&self, state: &str, labels: &str) -> Vec<Value> {
        let mut path = format!("/repos/{}/{}/issues", self.owner, self.repo);
        if !state.is_empty() {
            path.push_str(&format!("?state={state}"));
        }
        if !labels.is_empty() {
            path.push_str(&format!("&labels={labels}"));
        }
        match self.request("GET", &path, None) {
            Ok(Value::Array(items)) => items,
            _ => Vec::new(),
        }
    }

    pub fn get_issue(&self, issue_num: i64) -> Option<Value> {
        self.request("GET", &format!("/repos/{}/{}/issues/{issue_num}", self.owner, self.repo), None)
            .ok()
    }

    pub fn create_issue(&self, title: &str, body: &str, labels: Option<Vec<String>>) -> Option<Value> {
        let mut data = json!({"title": title, "body": body});
        if let Some(labels) = labels {
            data["labels"] = json!(labels);
        }
        self.request("POST", &format!("/repos/{}/{}/issues", self.owner, self.repo), Some(data))
            .ok()
    }

    pub fn close_issue(&self, issue_num: i64) -> bool {
        self.request(
            "PATCH",
            &format!("/repos/{}/{}/issues/{issue_num}", self.owner, self.repo),
            Some(json!({"state": "closed"})),
        )
        .is_ok()
    }

    pub fn list_prs(&self, state: &str) -> Vec<Value> {
        let path = format!("/repos/{}/{}/pulls?state={state}", self.owner, self.repo);
        match self.request("GET", &path, None) {
            Ok(Value::Array(items)) => items,
            _ => Vec::new(),
        }
    }

    pub fn get_pr(&self, pr_num: i64) -> Option<Value> {
        self.request("GET", &format!("/repos/{}/{}/pulls/{pr_num}", self.owner, self.repo), None)
            .ok()
    }

    pub fn create_pr(&self, title: &str, body: &str, head: &str, base: &str) -> Option<Value> {
        self.request(
            "POST",
            &format!("/repos/{}/{}/pulls", self.owner, self.repo),
            Some(json!({"title": title, "body": body, "head": head, "base": base})),
        )
        .ok()
    }

    pub fn merge_pr(&self, pr_num: i64, method: &str) -> bool {
        match self.request(
            "PUT",
            &format!("/repos/{}/{}/pulls/{pr_num}/merge", self.owner, self.repo),
            Some(json!({"merge_method": method})),
        ) {
            // Python: `result is not None and "merged" in str(result)`.
            Ok(v) => v.to_string().contains("merged"),
            Err(_) => false,
        }
    }

    /// `git checkout -b <branch> origin/<base>` (see module docs).
    pub fn create_branch(&self, cwd: &Path, branch_name: &str, base: &str) -> bool {
        Command::new("git")
            .args(["checkout", "-b", branch_name, &format!("origin/{base}")])
            .current_dir(cwd)
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    /// Authenticated JSON request; Python returned `None` on every error, this
    /// returns the reason and the callers decide.
    pub fn request(&self, method: &str, path: &str, data: Option<Value>) -> Result<Value, String> {
        let mut headers = vec![("Accept".to_string(), "application/vnd.github.v3+json".to_string())];
        if !self.token.is_empty() {
            headers.push(("Authorization".to_string(), format!("token {}", self.token)));
        }
        http_json(method, &self.url(path), &headers, data, 30)
    }
}

pub struct GitHubAutomation {
    pub client: GitHubClient,
    pub repo: Option<(String, String)>,
}

impl GitHubAutomation {
    pub fn new(token: &str, cwd: &Path) -> Self {
        let mut client = if token.is_empty() {
            GitHubClient::from_env()
        } else {
            GitHubClient::new(Some(token), "", "")
        };
        let repo = client.detect_repo(cwd);
        if let Some((owner, name)) = &repo {
            client.set_repo(owner, name);
        }
        Self { client, repo }
    }

    pub fn auto_create_pr(
        &self,
        cwd: &Path,
        title: &str,
        description: &str,
        branch: &str,
        base: &str,
    ) -> Option<Value> {
        self.repo.as_ref()?;
        self.client.create_branch(cwd, branch, base);
        self.client.create_pr(title, description, branch, base)
    }

    pub fn create_issue_from_error(&self, error_msg: &str, file_path: &str) -> Option<Value> {
        self.repo.as_ref()?;
        let head: String = error_msg.chars().take(50).collect();
        let title = format!("Bug: {head}...");
        let body = format!(
            "## Error\n```\n{error_msg}\n```\n\n## Location\n- File: `{file_path}`\n- Timestamp: {}\n\n## Steps to Reproduce\n1. (Add steps here)\n\n## Expected Behavior\n(Describe what should happen)\n",
            now_iso8601_micros()
        );
        self.client.create_issue(&title, &body, Some(vec!["bug".to_string()]))
    }

    pub fn create_pr_for_changes(&self, cwd: &Path, changes: &[String]) -> Option<Value> {
        self.repo.as_ref()?;
        let branch = format!("apex-changes-{}", compact_timestamp());
        let title = "APEX: Automated changes";
        let mut body = "## Changes\n".to_string();
        body.push_str(
            &changes
                .iter()
                .take(10)
                .map(|f| format!("- {f}"))
                .collect::<Vec<_>>()
                .join("\n"),
        );
        if changes.len() > 10 {
            body.push_str(&format!("\n\n... and {} more files", changes.len() - 10));
        }
        self.auto_create_pr(cwd, title, &body, &branch, "main")
    }

    pub fn list_issues_by_label(&self, label: &str) -> Vec<Value> {
        self.client.list_issues("open", label)
    }

    pub fn get_issue_todos(&self) -> Vec<Value> {
        self.list_issues_by_label("todo")
    }

    pub fn close_completed_prs(&self) -> usize {
        self.client
            .list_prs("merged")
            .iter()
            .filter(|pr| pr.get("merged_at").map(|v| !v.is_null()).unwrap_or(false))
            .count()
    }
}

/// `20261019071238` (Python: `strftime('%Y%m%d%H%M%S')`).
fn compact_timestamp() -> String {
    now_iso8601_micros()
        .chars()
        .filter(|c| c.is_ascii_digit())
        .take(14)
        .collect()
}

/// The `git_create_pr` tool: `gh` first, REST fallback (Python parity).
pub fn create_pr_tool(
    cwd: &Path,
    title: &str,
    body: &str,
    base: &str,
    head: Option<&str>,
) -> String {
    if which("gh").is_some() {
        let mut cmd = vec!["pr", "create", "--title", title, "--base", base];
        if !body.is_empty() {
            cmd.push("--body");
            cmd.push(body);
        }
        if let Some(head) = head {
            cmd.push("--head");
            cmd.push(head);
        }
        match output_with_timeout(Command::new("gh").args(&cmd).current_dir(cwd), std::time::Duration::from_secs(60)) {
            Ok(o) if o.status.success() => {
                let stdout = String::from_utf8_lossy(&o.stdout).trim().to_string();
                if stdout.is_empty() {
                    "PR created.".to_string()
                } else {
                    stdout
                }
            }
            Ok(o) => format!("ERROR: gh pr create failed: {}", String::from_utf8_lossy(&o.stderr).trim()),
            Err(e) => format!("ERROR: gh pr create failed: {e}"),
        }
    } else {
        rest_create_pr(cwd, title, body, base, head)
    }
}

/// Run a command with a deadline (Python: `subprocess.run(..., timeout=60)`).
fn output_with_timeout(
    cmd: &mut Command,
    timeout: std::time::Duration,
) -> Result<std::process::Output, String> {
    let mut child = cmd
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| e.to_string())?;
    let start = std::time::Instant::now();
    loop {
        match child.try_wait() {
            Ok(Some(_)) => break,
            Ok(None) => {
                if start.elapsed() > timeout {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Err(format!("timed out after {}s", timeout.as_secs()));
                }
                std::thread::sleep(std::time::Duration::from_millis(50));
            }
            Err(e) => return Err(e.to_string()),
        }
    }
    child.wait_with_output().map_err(|e| e.to_string())
}

fn rest_create_pr(cwd: &Path, title: &str, body: &str, base: &str, head: Option<&str>) -> String {
    let token = std::env::var("GITHUB_TOKEN")
        .ok()
        .or_else(|| std::env::var("GH_TOKEN").ok())
        .unwrap_or_default();
    if token.is_empty() {
        return "ERROR: gh CLI not found and no GITHUB_TOKEN/GH_TOKEN set.".to_string();
    }
    let Some(remote) = git_output(cwd, &["remote", "get-url", "origin"]) else {
        return "ERROR: Could not parse GitHub remote URL.".to_string();
    };
    let Some((owner, repo)) = parse_github_remote(&remote) else {
        return "ERROR: Could not parse GitHub remote URL.".to_string();
    };
    let head = match head {
        Some(h) if !h.is_empty() => h.to_string(),
        _ => git_output(cwd, &["branch", "--show-current"]).unwrap_or_default(),
    };
    let api_base = api_base_from_env();
    let headers = vec![
        ("Authorization".to_string(), format!("Bearer {token}")),
        ("Accept".to_string(), "application/vnd.github+json".to_string()),
        ("User-Agent".to_string(), "APEX".to_string()),
    ];
    let payload = json!({"title": title, "body": body, "base": base, "head": head});
    match http_json("POST", &format!("{api_base}/repos/{owner}/{repo}/pulls"), &headers, Some(payload), 30) {
        Ok(v) => v
            .get("html_url")
            .and_then(|u| u.as_str())
            .map(|s| s.to_string())
            .unwrap_or_else(|| "PR created.".to_string()),
        Err(e) => format!("ERROR: PR creation failed: {e}"),
    }
}

/// `git@github.com:user/repo.git` / `https://github.com/user/repo` → `(user, repo)`.
pub fn parse_github_remote(remote: &str) -> Option<(String, String)> {
    // Python: re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote)
    let remote = remote.trim();
    let idx = remote.find("github.com")?;
    let rest = &remote[idx + "github.com".len()..];
    let rest = rest.strip_prefix(':').or_else(|| rest.strip_prefix('/'))?;
    let rest = rest.trim();
    let repo_path = rest.strip_suffix(".git").unwrap_or(rest);
    let repo_path = repo_path.split_whitespace().next().unwrap_or("").trim_matches('/');
    let mut parts = repo_path.splitn(2, '/');
    let owner = parts.next().unwrap_or("");
    let repo = parts.next().unwrap_or("");
    if owner.is_empty() || repo.is_empty() {
        return None;
    }
    Some((owner.to_string(), repo.to_string()))
}

/// Run a git command in `cwd`, returning trimmed stdout on success.
fn git_output(cwd: &Path, args: &[&str]) -> Option<String> {
    let out = Command::new("git").args(args).current_dir(cwd).output().ok()?;
    if !out.status.success() {
        return None;
    }
    let text = String::from_utf8_lossy(&out.stdout).trim().to_string();
    if text.is_empty() {
        None
    } else {
        Some(text)
    }
}

pub fn which(prog: &str) -> Option<std::path::PathBuf> {
    let paths = std::env::var("PATH").unwrap_or_default();
    for dir in paths.split(':') {
        if dir.is_empty() {
            continue;
        }
        let candidate = Path::new(dir).join(prog);
        if candidate.is_file() {
            return Some(candidate);
        }
    }
    None
}

/// Blocking JSON request on a private runtime.
///
/// Tools run inside the server's Tokio runtime, so this must not create or drop
/// a runtime there — hence the dedicated thread.
fn http_json(
    method: &str,
    url: &str,
    headers: &[(String, String)],
    data: Option<Value>,
    timeout_secs: u64,
) -> Result<Value, String> {
    let method = method.to_string();
    let url = url.to_string();
    let headers = headers.to_vec();
    let handle = std::thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().map_err(|e| e.to_string())?;
        rt.block_on(async move {
            let client = reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(timeout_secs))
                .build()
                .map_err(|e| e.to_string())?;
            let m = reqwest::Method::from_bytes(method.as_bytes()).map_err(|e| e.to_string())?;
            let mut req = client.request(m, &url);
            for (k, v) in &headers {
                req = req.header(k, v);
            }
            if let Some(body) = &data {
                req = req.json(body);
            }
            let resp = req.send().await.map_err(|e| e.to_string())?;
            let status = resp.status();
            let text = resp.text().await.map_err(|e| e.to_string())?;
            if !status.is_success() {
                return Err(format!("HTTP {status}: {text}"));
            }
            serde_json::from_str::<Value>(&text).map_err(|e| format!("invalid JSON response: {e}"))
        })
    });
    handle.join().map_err(|_| "github request thread panicked".to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{extract::State, routing::any, Json, Router};
    use std::sync::{Arc, Mutex};

    /// Tests that mutate process-wide env vars must not run concurrently.
    static ENV_LOCK: Mutex<()> = Mutex::new(());

    fn lock_env() -> std::sync::MutexGuard<'static, ()> {
        ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner())
    }

    fn test_client(base: &str) -> GitHubClient {
        GitHubClient {
            token: "test-token".to_string(),
            owner: "octo".to_string(),
            repo: "demo".to_string(),
            api_base: base.to_string(),
        }
    }

    #[test]
    fn parse_remote_variants() {
        assert_eq!(parse_github_remote("git@github.com:user/repo.git"), Some(("user".into(), "repo".into())));
        assert_eq!(parse_github_remote("https://github.com/user/repo.git"), Some(("user".into(), "repo".into())));
        assert_eq!(parse_github_remote("https://github.com/user/repo"), Some(("user".into(), "repo".into())));
        assert_eq!(parse_github_remote("git@github.com:Ggboykxz/APEX.git\n"), Some(("Ggboykxz".into(), "APEX".into())));
        assert_eq!(parse_github_remote("git@gitlab.com:user/repo.git"), None);
        assert_eq!(parse_github_remote("https://github.com/onlyowner"), None);
    }

    #[test]
    fn compact_timestamp_shape() {
        let t = compact_timestamp();
        assert_eq!(t.len(), 14, "got {t}");
        assert!(t.chars().all(|c| c.is_ascii_digit()));
        assert!(t.starts_with("20"), "year first: {t}");
    }

    #[test]
    fn which_finds_sh() {
        assert!(which("sh").is_some());
        assert!(which("definitely-not-a-real-binary-xyz").is_none());
    }

    #[test]
    fn command_timeout_kills_the_child() {
        let start = std::time::Instant::now();
        let out = output_with_timeout(
            Command::new("sh").args(["-c", "sleep 5"]),
            std::time::Duration::from_millis(200),
        );
        assert!(out.is_err(), "expected a timeout error");
        assert!(start.elapsed() < std::time::Duration::from_secs(3), "killed early");

        let ok = output_with_timeout(
            Command::new("sh").args(["-c", "echo hi"]),
            std::time::Duration::from_secs(5),
        )
        .unwrap();
        assert_eq!(String::from_utf8_lossy(&ok.stdout).trim(), "hi");
    }

    /// Records every request so the assertions can check method/path/body.
    #[derive(Clone, Default)]
    struct Recorder {
        requests: Arc<Mutex<Vec<(String, String, String, Option<Value>)>>>,
    }

    async fn fake_github(State(rec): State<Recorder>, req: axum::extract::Request) -> Json<Value> {
        let method = req.method().to_string();
        let uri = req.uri().to_string();
        let auth = req
            .headers()
            .get("authorization")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("")
            .to_string();
        let body = axum::body::to_bytes(req.into_body(), 1 << 20).await.ok();
        let body = body.and_then(|b| serde_json::from_slice::<Value>(&b).ok());
        rec.requests.lock().unwrap().push((method.clone(), uri.clone(), auth, body));

        let path = uri.split('?').next().unwrap_or("").to_string();
        if path.ends_with("/pulls") && path.contains("/repos/octo/demo") {
            Json(json!({"html_url": "https://github.com/octo/demo/pull/7", "number": 7}))
        } else if path.ends_with("/issues") {
            if method == "GET" {
                Json(json!([{"number": 1, "title": "first"}, {"number": 2, "title": "second"}]))
            } else {
                Json(json!({"number": 9, "title": "first"}))
            }
        } else if path.ends_with("/merge") {
            Json(json!({"merged": true, "message": "Pull Request successfully merged"}))
        } else if path.contains("/issues/") || path.contains("/pulls/") {
            Json(json!({"number": 3, "state": "closed", "merged_at": "2026-10-19T00:00:00Z"}))
        } else {
            Json(json!({}))
        }
    }

    fn spawn_fake() -> (String, Recorder) {
        let rec = Recorder::default();
        let state = rec.clone();
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        listener.set_nonblocking(true).unwrap();
        std::thread::spawn(move || {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(async move {
                let app = Router::new().fallback(any(fake_github)).with_state(state);
                let listener = tokio::net::TcpListener::from_std(listener).unwrap();
                axum::serve(listener, app).await.unwrap();
            });
        });
        (format!("http://{addr}"), rec)
    }

    #[test]
    fn rest_methods_hit_the_expected_endpoints() {
        let (base, rec) = spawn_fake();
        let client = test_client(&base);

        // Issues
        let issues = client.list_issues("open", "bug");
        assert_eq!(issues.len(), 2);
        let created = client.create_issue("title", "body", Some(vec!["bug".to_string()])).unwrap();
        assert_eq!(created["title"], "first");
        assert!(client.get_issue(3).is_some());
        assert!(client.close_issue(3));

        // Pull requests
        let pr = client.create_pr("t", "b", "feature", "main").unwrap();
        assert_eq!(pr["html_url"], "https://github.com/octo/demo/pull/7");
        assert!(client.get_pr(3).is_some());
        assert!(client.merge_pr(7, "squash"));

        let requests = rec.requests.lock().unwrap().clone();
        let flat: Vec<String> = requests
            .iter()
            .map(|(m, u, _, _)| format!("{m} {u}"))
            .collect();

        assert!(flat.contains(&"GET /repos/octo/demo/issues?state=open&labels=bug".to_string()));
        assert!(flat.contains(&"POST /repos/octo/demo/issues".to_string()));
        assert!(flat.contains(&"PATCH /repos/octo/demo/issues/3".to_string()));
        assert!(flat.contains(&"POST /repos/octo/demo/pulls".to_string()));
        assert!(flat.contains(&"PUT /repos/octo/demo/pulls/7/merge".to_string()));

        // Tokens and payloads really travel.
        let (_, _, auth, _) = requests.iter().find(|(m, u, _, _)| m == "GET" && u.contains("issues?")).unwrap();
        assert_eq!(auth, "token test-token");
        let (_, _, _, body) = requests
            .iter()
            .find(|(m, u, _, _)| m == "POST" && u == "/repos/octo/demo/pulls")
            .unwrap();
        assert_eq!(
            body.as_ref().unwrap(),
            &json!({"title": "t", "body": "b", "head": "feature", "base": "main"})
        );
    }

    #[test]
    fn errors_are_reported_not_swallowed() {
        // Nothing listens on this port: connect refused.
        let client = test_client("http://127.0.0.1:9");
        let err = client.request("GET", "/repos/octo/demo/issues", None).unwrap_err();
        assert!(!err.is_empty());
        assert!(client.list_issues("open", "").is_empty(), "Python parity: empty on error");
        assert!(!client.merge_pr(1, "squash"));
    }

    #[test]
    fn rest_create_pr_reports_missing_token() {
        let _guard = lock_env();
        let dir = tempfile::tempdir().unwrap();
        // Ensure neither token variable leaks in from the environment.
        std::env::remove_var("GITHUB_TOKEN");
        std::env::remove_var("GH_TOKEN");
        let out = rest_create_pr(dir.path(), "t", "b", "main", None);
        assert_eq!(out, "ERROR: gh CLI not found and no GITHUB_TOKEN/GH_TOKEN set.");
    }

    #[test]
    fn rest_create_pr_reports_unparsable_remote() {
        let _guard = lock_env();
        let dir = tempfile::tempdir().unwrap();
        let repo = dir.path().join("repo");
        std::fs::create_dir(&repo).unwrap();
        std::process::Command::new("git").args(["init", "-q"]).current_dir(&repo).output().unwrap();
        std::process::Command::new("git")
            .args(["remote", "add", "origin", "git@gitlab.com:octo/demo.git"])
            .current_dir(&repo)
            .output()
            .unwrap();
        std::env::set_var("GITHUB_TOKEN", "token-from-test");
        let out = rest_create_pr(&repo, "t", "b", "main", None);
        std::env::remove_var("GITHUB_TOKEN");
        assert_eq!(out, "ERROR: Could not parse GitHub remote URL.");
    }

    #[test]
    fn rest_create_pr_posts_and_returns_url() {
        let _guard = lock_env();
        let (base, rec) = spawn_fake();
        std::env::set_var("APEX_GITHUB_API", &base);
        let dir = tempfile::tempdir().unwrap();
        let repo = dir.path().join("repo");
        std::fs::create_dir(&repo).unwrap();
        for args in [
            vec!["init", "-q"],
            vec!["remote", "add", "origin", "git@github.com:octo/demo.git"],
        ] {
            std::process::Command::new("git").args(&args).current_dir(&repo).output().unwrap();
        }
        std::env::set_var("GITHUB_TOKEN", "token-from-test");
        let out = rest_create_pr(&repo, "Title", "Body", "main", Some("feature"));
        std::env::remove_var("APEX_GITHUB_API");
        std::env::remove_var("GITHUB_TOKEN");

        assert_eq!(out, "https://github.com/octo/demo/pull/7");
        let requests = rec.requests.lock().unwrap().clone();
        let (_, uri, auth, body) = requests
            .iter()
            .find(|(m, _, _, _)| m == "POST")
            .expect("POST reached the fake API");
        assert_eq!(uri, "/repos/octo/demo/pulls");
        assert_eq!(auth, "Bearer token-from-test");
        assert_eq!(
            body.as_ref().unwrap(),
            &json!({"title": "Title", "body": "Body", "base": "main", "head": "feature"})
        );
    }

    #[test]
    fn close_completed_prs_counts_merged() {
        let (base, _rec) = spawn_fake();
        let mut client = test_client(&base);
        client.owner = "octo".to_string();
        let automation = GitHubAutomation {
            client,
            repo: Some(("octo".to_string(), "demo".to_string())),
        };
        // The fake answers /pulls?state=merged with the issue-shaped list.
        assert_eq!(automation.close_completed_prs(), 0);
    }

    #[test]
    fn detect_repo_from_origin_remote() {
        let dir = tempfile::tempdir().unwrap();
        let repo = dir.path().join("repo");
        std::fs::create_dir(&repo).unwrap();
        for args in [
            vec!["init", "-q"],
            vec!["remote", "add", "origin", "https://github.com/Ggboykxz/APEX.git"],
        ] {
            std::process::Command::new("git").args(&args).current_dir(&repo).output().unwrap();
        }
        // Only meaningful when `gh` is absent (otherwise it would hit the network).
        if which("gh").is_none() {
            let client = test_client("http://127.0.0.1:9");
            assert_eq!(
                client.detect_repo(&repo),
                Some(("Ggboykxz".to_string(), "APEX".to_string()))
            );
        }
    }
}
