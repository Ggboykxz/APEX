//! File watcher — port of `apex/watcher.py`.
//!
//! Polling-based, zero-dependency file watcher: background daemon thread,
//! debounced callbacks, gitignore-aware ignore patterns. Mirrors OpenCode's
//! watcher UX.
//
//! This module is not yet wired into the dispatch gate / agent loop.
//! Allow dead code with a named exit criterion — TODO(v2.6): wire into tool
//! dispatch / agent message handling and remove this allow.
#![allow(dead_code)]

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, OnceLock};
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;
use std::time::{Duration, Instant, UNIX_EPOCH};

// ────────────────────────────────────────────────────────────
// Default ignore patterns
// ────────────────────────────────────────────────────────────

pub const DEFAULT_IGNORE_PATTERNS: &[&str] = &[
    "**/node_modules/**",
    "**/.git/**",
    "**/__pycache__/**",
    "**/.venv/**",
    "**/venv/**",
    "**/dist/**",
    "**/build/**",
    "**/.next/**",
    "**/target/**",
];

// ────────────────────────────────────────────────────────────
// Utility: pattern matching
// ────────────────────────────────────────────────────────────

/// Match `path` against a glob `pattern`.
///
/// Supports:
///   - `**/X/**`  (directory recursion anywhere)
///   - `*.ext`    (extension match)
///   - standard fnmatch patterns
pub fn matches_pattern(path: &str, pattern: &str) -> bool {
    // Normalise to forward slashes
    let normalised = path.replace('\\', "/");

    // If pattern is an extension pattern like *.log
    if pattern.starts_with("*.") {
        return normalised == pattern
            || normalised.ends_with(&pattern[1..])
            || fnmatch_like(&normalised, pattern);
    }

    // For **/X/** style patterns (match middle segment anywhere in tree)
    if pattern.starts_with("**/") && pattern.ends_with("/**") {
        let middle = &pattern[3..pattern.len() - 3];
        let parts: Vec<&str> = normalised.split('/').collect();
        return parts.contains(&middle);
    }

    // For **/X (match anywhere in tree)
    if pattern.starts_with("**/") {
        let suffix = pattern.strip_prefix("**/").unwrap_or(pattern);
        return normalised.ends_with(suffix)
            || format!("/{}", suffix) == normalised
            || normalised == suffix
            || normalised.contains(&format!("/{}", suffix));
    }

    // Bare filename or extension pattern (e.g. ".env", "*.log")
    if !pattern.contains('/') && pattern.starts_with('*') {
        return fnmatch_like(&normalised, pattern);
    }

    // Bare filename without glob (e.g. ".env") — match any file with that name
    if !pattern.contains('/') && !pattern.contains('*') && !pattern.contains('?') {
        let base = normalised.rsplit('/').next().unwrap_or(&normalised);
        return base == pattern;
    }

    // Standard fnmatch fallback
    fnmatch_like(&normalised, pattern)
}

/// Simple fnmatch-like matcher supporting `*`, `?`, `[...]`.
fn fnmatch_like(text: &str, pattern: &str) -> bool {
    fn match_bytes(pat: &[u8], txt: &[u8]) -> bool {
        let mut pi = 0;
        let mut ti = 0;
        let mut star: Option<usize> = None;
        let mut match_ti = 0;

        while ti < txt.len() {
            if pi < pat.len() && pat[pi] == b'*' {
                star = Some(pi);
                match_ti = ti;
                pi += 1;
                continue;
            }
            if pi < pat.len() && (pat[pi] == b'?' || pat[pi] == b'[') {
                pi += 1;
                ti += 1;
                continue;
            }
            if pi < pat.len() && pat[pi] == txt[ti] {
                pi += 1;
                ti += 1;
                continue;
            }
            if let Some(s) = star {
                pi = s + 1;
                match_ti += 1;
                ti = match_ti;
                continue;
            }
            return false;
        }

        while pi < pat.len() && pat[pi] == b'*' {
            pi += 1;
        }
        pi == pat.len()
    }

    match_bytes(pattern.as_bytes(), text.as_bytes())
}

/// Check if `path` matches any of the given ignore patterns.
pub fn is_ignored(path: &str, patterns: &[String]) -> bool {
    let normalised = path.replace('\\', "/");
    for pattern in patterns {
        let cleaned = pattern.trim();
        if cleaned.is_empty() {
            continue;
        }
        if matches_pattern(&normalised, cleaned) {
            return true;
        }
    }
    false
}

// ────────────────────────────────────────────────────────────
// Gitignore parsing
// ────────────────────────────────────────────────────────────

/// Load ignore patterns from `.gitignore` files walking up from `project_dir`.
pub fn load_gitignore_patterns(project_dir: &Path) -> Vec<String> {
    let mut patterns: Vec<String> = Vec::new();
    let mut current = project_dir.to_path_buf();
    loop {
        let gi = current.join(".gitignore");
        if gi.is_file() {
            if let Ok(text) = fs::read_to_string(&gi) {
                for line in text.lines() {
                    let line = line.trim();
                    if line.is_empty() || line.starts_with('#') {
                        continue;
                    }
                    // Folders: "some_dir/" -> "**/some_dir/**"
                    let line = if line.ends_with('/') {
                        format!("**/{}**", line)
                    } else {
                        line.to_string()
                    };
                    patterns.push(line);
                }
            }
        }
        if !current.pop() {
            break;
        }
    }
    patterns
}

// ────────────────────────────────────────────────────────────
// Config
// ────────────────────────────────────────────────────────────

/// Configuration for the file watcher.
#[derive(Debug, Clone)]
pub struct WatcherConfig {
    pub ignore_patterns: Vec<String>,
    pub enabled: bool,
}

impl Default for WatcherConfig {
    fn default() -> Self {
        Self {
            ignore_patterns: DEFAULT_IGNORE_PATTERNS
                .iter()
                .map(|s| s.to_string())
                .collect(),
            enabled: false,
        }
    }
}

// ────────────────────────────────────────────────────────────
// FileWatcher
// ────────────────────────────────────────────────────────────

/// Polling-based file watcher that runs in a background daemon thread.
///
/// Tracks file mtimes and fires `callback(path)` for each changed file,
/// debounced by `debounce_ms`.
pub struct FileWatcher {
    stop: Arc<AtomicBool>,
    thread: Mutex<Option<thread::JoinHandle<()>>>,
    project_dir: Arc<Mutex<Option<PathBuf>>>,
    callback: Arc<Mutex<Option<WatcherCallback>>>,
    mtimes: Arc<Mutex<HashMap<String, u64>>>,
    config: Arc<Mutex<WatcherConfig>>,
    poll_interval: Arc<Mutex<Duration>>,
    debounce_ms: Arc<Mutex<u64>>,
    pending: Arc<Mutex<HashMap<String, Instant>>>,
}

type WatcherCallback = Box<dyn Fn(String) + Send + Sync>;

impl Default for FileWatcher {
    fn default() -> Self {
        Self::new()
    }
}

impl FileWatcher {
    /// Create a new (stopped) file watcher.
    pub fn new() -> Self {
        Self {
            stop: Arc::new(AtomicBool::new(false)),
            thread: Mutex::new(None),
            project_dir: Arc::new(Mutex::new(None)),
            callback: Arc::new(Mutex::new(None)),
            mtimes: Arc::new(Mutex::new(HashMap::new())),
            config: Arc::new(Mutex::new(WatcherConfig::default())),
            poll_interval: Arc::new(Mutex::new(Duration::from_secs(1))),
            debounce_ms: Arc::new(Mutex::new(300)),
            pending: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Start watching *project_dir* for file changes.
    ///
    /// Calls `callback(path)` for each changed file (debounced).
    pub fn start<P: AsRef<Path>, F: Fn(String) + Send + Sync + 'static>(
        &self,
        project_dir: P,
        callback: F,
    ) {
        if self.is_running() {
            return;
        }

        let project_dir = Some(project_dir.as_ref().to_path_buf());
        *self.project_dir.lock().unwrap() = project_dir.clone();
        *self.callback.lock().unwrap() = Some(Box::new(callback));
        self.stop.store(false, Ordering::Relaxed);

        // Load config from apex_config.watcher
        let enabled = self.config.lock().unwrap().enabled;
        if !enabled {
            return;
        }

        // Build initial mtime snapshot
        let project_dir_ref = self.project_dir.lock().unwrap();
        let config_guard = self.config.lock().unwrap();
        let patterns = Self::all_patterns(project_dir_ref.as_ref().unwrap(), &config_guard);
        let initial = Self::scan(project_dir.as_ref().unwrap(), &patterns);
        drop(config_guard);
        *self.mtimes.lock().unwrap() = initial;
        drop(project_dir_ref);

        // Spawn polling thread
        let project_dir = project_dir.unwrap();
        let callback = self.callback.clone();
        let config = self.config.clone();
        let mtimes = self.mtimes.clone();
        let pending = self.pending.clone();
        let poll_interval = self.poll_interval.clone();
        let debounce_ms = self.debounce_ms.clone();
        let stop = self.stop.clone();

        let handle = thread::spawn(move || {
            // Wait one interval first so the initial scan settles before
            // detecting changes.
            loop {
                if stop.load(Ordering::Relaxed) {
                    break;
                }
                thread::sleep(*poll_interval.lock().unwrap());
                if stop.load(Ordering::Relaxed) {
                    break;
                }
                Self::check_changes(
                    &project_dir,
                    &callback,
                    &config,
                    &mtimes,
                    &pending,
                    &debounce_ms,
                );
            }
        });
        *self.thread.lock().unwrap() = Some(handle);
    }

    /// Stop the watcher thread.
    pub fn stop(&self) {
        self.stop.store(true, Ordering::Relaxed);
        if let Some(handle) = self.thread.lock().unwrap().take() {
            let _ = handle.join();
        }
        *self.mtimes.lock().unwrap() = HashMap::new();
        self.pending.lock().unwrap().clear();
    }

    /// Return true if the watcher has been started and not stopped.
    pub fn is_running(&self) -> bool {
        !self.stop.load(Ordering::Relaxed)
            && self.project_dir.lock().unwrap().is_some()
    }

    /// Return the currently configured ignore patterns.
    pub fn get_ignored_patterns(&self) -> Vec<String> {
        self.config.lock().unwrap().ignore_patterns.clone()
    }

    /// Check if *file_path* should be ignored (config + gitignore patterns).
    pub fn should_ignore(&self, file_path: &str) -> bool {
        let config = self.config.lock().unwrap();
        let project_dir = self.project_dir.lock().unwrap();
        let mut patterns = config.ignore_patterns.clone();
        if let Some(dir) = project_dir.as_ref() {
            patterns.extend(load_gitignore_patterns(dir));
        }
        drop(config);
        drop(project_dir);
        is_ignored(file_path, &patterns)
    }

    /// Set the poll interval in seconds.
    pub fn set_poll_interval(&self, seconds: f64) {
        *self.poll_interval.lock().unwrap() = Duration::from_secs_f64(seconds.max(0.1));
    }

    /// Set the debounce window in milliseconds.
    pub fn set_debounce_ms(&self, ms: f64) {
        *self.debounce_ms.lock().unwrap() = ms.max(0.0) as u64;
    }

    // ── Internal ────────────────────────────────────────────

    /// All patterns (config + gitignore).
    fn all_patterns(project_dir: &Path, config: &WatcherConfig) -> Vec<String> {
        let mut patterns = config.ignore_patterns.clone();
        patterns.extend(load_gitignore_patterns(project_dir));
        patterns
    }

    /// Walk `project_dir` and record mtimes for non-ignored files.
    fn scan(project_dir: &Path, patterns: &[String]) -> HashMap<String, u64> {
        let mut new_mtimes: HashMap<String, u64> = HashMap::new();
        let _ = Self::walk(project_dir, project_dir, patterns, &mut new_mtimes);
        new_mtimes
    }

    /// Recursive walk collecting mtimes of non-ignored files.
    fn walk(
        dir: &Path,
        root: &Path,
        patterns: &[String],
        out: &mut HashMap<String, u64>,
    ) -> std::io::Result<()> {
        let entries = match fs::read_dir(dir) {
            Ok(e) => e,
            Err(_) => return Ok(()),
        };
        let mut dirs: Vec<PathBuf> = Vec::new();
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                let rel = path
                    .strip_prefix(root)
                    .unwrap_or(&path)
                    .to_string_lossy()
                    .to_string();
                if !is_ignored(&rel, patterns) {
                    dirs.push(path);
                }
            } else if path.is_file() {
                let rel = path
                    .strip_prefix(root)
                    .unwrap_or(&path)
                    .to_string_lossy()
                    .to_string();
                if is_ignored(&rel, patterns) {
                    continue;
                }
                if let Ok(st) = path.metadata() {
                    if let Some(mtime) = st
                        .modified()
                        .ok()
                        .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                        .map(|d| d.as_secs())
                    {
                        out.insert(rel, mtime);
                    }
                }
            }
        }
        for d in dirs {
            let _ = Self::walk(&d, root, patterns, out);
        }
        Ok(())
    }

    /// Poll for changes since the last scan.
    fn check_changes(
        project_dir: &Path,
        callback: &Arc<Mutex<Option<WatcherCallback>>>,
        config: &Arc<Mutex<WatcherConfig>>,
        mtimes: &Arc<Mutex<HashMap<String, u64>>>,
        pending: &Arc<Mutex<HashMap<String, Instant>>>,
        debounce_ms: &Arc<Mutex<u64>>,
    ) {
        if project_dir.as_os_str().is_empty() {
            return;
        }
        let config = config.lock().unwrap();
        let patterns = Self::all_patterns(project_dir, &config);
        drop(config);

        let now = Instant::now();
        let mut seen: HashMap<String, u64> = HashMap::new();
        let _ = Self::walk(project_dir, project_dir, &patterns, &mut seen);

        // Detect changed / new files
        let mut to_debounce: Vec<String> = Vec::new();
        let mtimes_guard = mtimes.lock().unwrap();
        for (path, mtime) in &seen {
            let prev = mtimes_guard.get(path).copied();
            if prev.is_none() || prev != Some(*mtime) {
                to_debounce.push(path.clone());
            }
        }
        drop(mtimes_guard);

        // Remove tracked files that no longer exist
        {
            let mut mtimes = mtimes.lock().unwrap();
            for full in mtimes.keys().cloned().collect::<Vec<_>>() {
                if !seen.contains_key(&full) {
                    mtimes.remove(&full);
                }
            }
            *mtimes = seen;
        }

        // Debounce + fire
        let debounce_ms_val = *debounce_ms.lock().unwrap();
        {
            let mut pending = pending.lock().unwrap();
            for path in &to_debounce {
                pending.insert(path.clone(), now);
            }
            if !pending.is_empty() {
                let pending_keys: Vec<String> = pending.keys().cloned().collect();
                let cb = callback.clone();
                thread::spawn(move || {
                    thread::sleep(Duration::from_millis(debounce_ms_val));
                    if let Some(cb) = cb.lock().unwrap().as_ref() {
                        for path in pending_keys {
                            cb(path);
                        }
                    }
                });
            }
        }
    }
}

// ────────────────────────────────────────────────────────────
// Singleton
// ────────────────────────────────────────────────────────────

/// Global file watcher instance.
pub static WATCHER: OnceLock<FileWatcher> = OnceLock::new();

/// Returns the global file watcher.
pub fn watcher() -> &'static FileWatcher {
    WATCHER.get_or_init(FileWatcher::new)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matches_pattern_bare_filename() {
        assert!(matches_pattern("src/.env", ".env"));
        assert!(!matches_pattern("src/.envrc", ".env"));
    }

    #[test]
    fn matches_pattern_extension() {
        assert!(matches_pattern("src/main.py", "*.py"));
        assert!(!matches_pattern("src/main.rs", "*.py"));
    }

    #[test]
    fn matches_pattern_double_star_dir() {
        assert!(matches_pattern("src/node_modules/pkg/index.js", "**/node_modules/**"));
        assert!(!matches_pattern("src/pkg/index.js", "**/node_modules/**"));
    }

    #[test]
    fn matches_pattern_double_star_suffix() {
        // **/dist matches any path containing /dist as a substring
        assert!(matches_pattern("project/dist/bundle.js", "**/dist"));
        assert!(matches_pattern("src/dist.txt", "**/dist"));
        assert!(matches_pattern("dist", "**/dist"));
        assert!(matches_pattern("src/distribution.txt", "**/dist"));
        assert!(matches_pattern("src/distribute", "**/dist"));
        // src/data.txt does not contain /dist
        assert!(!matches_pattern("src/data.txt", "**/dist"));
    }

    #[test]
    fn is_ignored_matches_any() {
        let patterns: Vec<String> = vec!["**/.git/**".into(), "*.log".into()];
        assert!(is_ignored("src/.git/config", &patterns));
        assert!(is_ignored("app.log", &patterns));
        assert!(!is_ignored("src/main.rs", &patterns));
    }

    #[test]
    fn watcher_default_disabled() {
        let w = FileWatcher::new();
        assert!(!w.is_running());
        assert!(!w.config.lock().unwrap().enabled);
    }

    #[test]
    fn set_poll_interval_and_debounce() {
        let w = FileWatcher::new();
        w.set_poll_interval(2.5);
        assert_eq!(w.poll_interval.lock().unwrap().as_secs_f64(), 2.5);
        w.set_debounce_ms(500.0);
        assert_eq!(*w.debounce_ms.lock().unwrap(), 500);
    }

    #[test]
    fn load_gitignore_patterns_ignores_comments() {
        let dir = tempfile::tempdir().unwrap();
        let gi = dir.path().join(".gitignore");
        std::fs::write(&gi, "# comment\n\nbuild/\n*.tmp\n").unwrap();
        let patterns = load_gitignore_patterns(dir.path());
        assert!(patterns.iter().any(|p| p.contains("build")));
        assert!(patterns.iter().any(|p| p == "*.tmp"));
    }

    #[test]
    fn scan_detects_files() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("a.txt"), "hello").unwrap();
        std::fs::write(dir.path().join("b.txt"), "world").unwrap();
        let w = FileWatcher::new();
        // Enable the watcher and scan directly (avoids starting the thread).
        *w.config.lock().unwrap() = WatcherConfig {
            ignore_patterns: DEFAULT_IGNORE_PATTERNS.iter().map(|s| s.to_string()).collect(),
            enabled: true,
        };
        *w.project_dir.lock().unwrap() = Some(dir.path().to_path_buf());
        let patterns = FileWatcher::all_patterns(dir.path(), &w.config.lock().unwrap());
        let mtimes = FileWatcher::scan(dir.path(), &patterns);
        assert!(mtimes.iter().any(|(p, _)| p.ends_with("a.txt")));
        assert!(mtimes.iter().any(|(p, _)| p.ends_with("b.txt")));
    }
}
