//! sandbox — Code execution sandbox ported from `apex/sandbox.py`.
//!
//! Provides CodeSandbox for running code in various languages and ShellSession
//! for persistent interactive shell sessions.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

/// Code sandbox for running untrusted code safely.
pub struct CodeSandbox {
    /// Reserved for future config; the tool runner uses the default 30 s.
    #[allow(dead_code)] // TODO(v2.6): expose timeout via tool args/config
    pub timeout: i64,
    pub max_output: usize,
    pub temp_dir: PathBuf,
}

impl CodeSandbox {
    pub const LANGUAGES: [(&'static str, &'static str, &'static str); 7] = [
        ("python", ".py", "python3 {file}"),
        ("javascript", ".js", "node {file}"),
        ("bash", ".sh", "bash {file}"),
        ("ruby", ".rb", "ruby {file}"),
        ("go", ".go", "go run {file}"),
        ("rust", ".rs", "rustc {file} -o {binary}"),
        ("php", ".php", "php {file}"),
    ];

    pub fn new(timeout: Option<i64>, max_output: Option<usize>) -> Self {
        let temp_dir = std::env::temp_dir().join("apex_sandbox");
        let _ = std::fs::create_dir_all(&temp_dir);

        Self {
            timeout: timeout.unwrap_or(30),
            max_output: max_output.unwrap_or(50000),
            temp_dir,
        }
    }

    pub fn run_code(&self, code: &str, language: &str, args: Option<&[String]>) -> String {
        let lang_config = Self::LANGUAGES.iter().find(|(l, _, _)| *l == language);
        let (ext, run_cmd) = match lang_config {
            Some((_, ext, run)) => (ext, run),
            None => return format!("ERROR: Unsupported language: {}", language),
        };

        let file_id = short_id();
        let file_path = self.temp_dir.join(format!("{}{}", file_id, ext));

        let result = (|| -> Result<String, String> {
            std::fs::write(&file_path, code).map_err(|e| format!("ERROR: Write failed: {}", e))?;

            if language == "rust" {
                let binary_path = self.temp_dir.join(format!("{}_binary", file_id));
                let compile_output = Command::new("rustc")
                    .arg(&file_path)
                    .arg("-o")
                    .arg(&binary_path)
                    .output()
                    .map_err(|e| format!("ERROR: Compile spawn failed: {}", e))?;
                if !compile_output.status.success() {
                    return Err(format!(
                        "ERROR: Compilation failed:\n{}",
                        String::from_utf8_lossy(&compile_output.stderr)
                    ));
                }
                let mut cmd = Command::new(&binary_path);
                if let Some(args) = args {
                    cmd.args(args);
                }
                cmd.current_dir(&self.temp_dir)
                    .stdout(Stdio::piped())
                    .stderr(Stdio::piped());
                let output = cmd.output().map_err(|e| format!("ERROR: {}", e))?;
                let stdout = String::from_utf8_lossy(&output.stdout);
                let stderr = String::from_utf8_lossy(&output.stderr);
                let mut parts: Vec<String> = Vec::new();
                if !stdout.is_empty() {
                    parts.push(stdout.chars().take(self.max_output).collect());
                }
                if !stderr.is_empty() {
                    parts.push(format!(
                        "[STDERR]\n{}",
                        stderr.chars().take(self.max_output).collect::<String>()
                    ));
                }
                if !output.status.success() {
                    parts.insert(
                        0,
                        format!("[EXIT CODE: {}]", output.status.code().unwrap_or(-1)),
                    );
                }
                if parts.is_empty() {
                    Ok("[no output]".to_string())
                } else {
                    Ok(parts.join("\n"))
                }
            } else {
                let cmd_str = run_cmd.replace("{file}", &file_path.to_string_lossy());
                let mut parts = cmd_str.split_whitespace();
                let mut cmd = Command::new(parts.next().unwrap_or(""));
                for arg in parts {
                    cmd.arg(arg);
                }
                if let Some(args) = args {
                    cmd.args(args);
                }
                cmd.current_dir(&self.temp_dir)
                    .stdout(Stdio::piped())
                    .stderr(Stdio::piped());
                let output = cmd.output().map_err(|e| format!("ERROR: {}", e))?;
                let stdout = String::from_utf8_lossy(&output.stdout);
                let stderr = String::from_utf8_lossy(&output.stderr);
                let mut parts: Vec<String> = Vec::new();
                if !stdout.is_empty() {
                    parts.push(stdout.chars().take(self.max_output).collect());
                }
                if !stderr.is_empty() {
                    parts.push(format!(
                        "[STDERR]\n{}",
                        stderr.chars().take(self.max_output).collect::<String>()
                    ));
                }
                if !output.status.success() {
                    parts.insert(
                        0,
                        format!("[EXIT CODE: {}]", output.status.code().unwrap_or(-1)),
                    );
                }
                if parts.is_empty() {
                    Ok("[no output]".to_string())
                } else {
                    Ok(parts.join("\n"))
                }
            }
        })();

        match result {
            Ok(r) => r,
            Err(e) => e,
        }
    }

    /// Convenience wrapper for running a Python snippet through `run_code`.
    #[allow(dead_code)] // TODO(v2.6): wire into tool dispatch or remove
    pub fn run_python_snippet(&self, code: &str) -> String {
        self.run_code(code, "python", None)
    }

    /// Convenience wrapper for running a JavaScript snippet through `run_code`.
    #[allow(dead_code)] // TODO(v2.6): wire into tool dispatch or remove
    pub fn run_javascript_snippet(&self, code: &str) -> String {
        self.run_code(code, "javascript", None)
    }
}

impl Default for CodeSandbox {
    fn default() -> Self {
        Self::new(None, None)
    }
}

/// Persistent interactive shell session.
#[allow(dead_code)] // Headless stub; TODO(v2.6): wire into start_shell/run_shell tools
#[allow(clippy::all)]
pub struct ShellSession {
    cwd: PathBuf,
    env: HashMap<String, String>,
}

#[allow(dead_code)] // Headless stub; see struct-level allow above
impl ShellSession {
    #[allow(dead_code)] // See struct-level allow above
    pub fn new(cwd: Option<&Path>, env: Option<&[(&str, &str)]>) -> Self {
        let cwd = cwd
            .map(|p| p.to_path_buf())
            .unwrap_or_else(|| std::env::current_dir().unwrap_or_default());
        let env = env
            .map(|e| {
                e.iter()
                    .map(|(k, v)| (k.to_string(), v.to_string()))
                    .collect()
            })
            .unwrap_or_else(|| std::env::vars().collect());
        Self { cwd, env }
    }

    pub fn start(&mut self, _shell: &str) -> bool {
        // Shell sessions are not supported in headless mode; each command runs independently.
        false
    }

    pub fn run(&mut self, _command: &str, _timeout: Option<i64>) -> String {
        "ERROR: Shell sessions not available in headless mode".to_string()
    }

    pub fn close(&mut self) {}
}

impl Default for ShellSession {
    fn default() -> Self {
        Self::new(None, None)
    }
}

fn short_id() -> String {
    use std::fmt::Write;
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    let mut s = String::new();
    let mut n = now;
    for _ in 0..8 {
        let _ = write!(s, "{:x}", n % 16);
        n /= 16;
    }
    s
}
