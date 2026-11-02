//! Workspace rollback — port of `apex/workspace_rollback.py`.
//!
//! Snapshots live in `<cwd>/.apex/snapshots/<name>/`:
//!
//! ```text
//! metadata.json       # timestamp, label, created_at
//! changed_files.txt   # `git diff --name-only` output (tracked edits only)
//! git_status.txt      # `git status --porcelain` output
//! files/<relpath>     # backup copy of every changed tracked file
//! ```
//!
//! `TurnTracker` records one snapshot per turn in `.apex/turns.json` and can
//! restore the workspace to any recorded turn.
//!
//! Deliberate divergences from Python, all recorded in `PARITY.md`:
//!
//! * Snapshot names and `created_at` values use UTC (Python uses local time).
//!   The formats are identical and ordering is unaffected.
//! * Snapshot names from the CLI are validated as bare directory names, so
//!   `restore`/`delete` cannot escape `.apex/snapshots/` (Python joins the
//!   user value directly).
//! * A corrupt `.apex/turns.json` is reported as an error instead of a
//!   traceback, and IO failures surface as `ERROR: …` strings.

use crate::cost::now_iso8601_micros;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

/// One snapshot, as returned by `list_snapshots`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct SnapshotInfo {
    pub name: String,
    pub created_at: String,
    pub label: String,
}

/// One recorded turn in `.apex/turns.json`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TurnRecord {
    pub turn_number: usize,
    pub snapshot: String,
    pub timestamp: String,
    pub data: Value,
}

/// Snapshot timestamp pair: compact (`%Y%m%d_%H%M%S`) and ISO.
struct Timestamp {
    compact: String,
    iso: String,
}

impl Timestamp {
    fn now() -> Self {
        Self::from_iso(now_iso8601_micros())
    }

    /// Build from `YYYY-MM-DDTHH:MM:SS.ffffff` (the shape Python's
    /// `datetime.isoformat()` produces).
    fn from_iso(iso: String) -> Self {
        let digits: String = iso
            .chars()
            .filter(|c| c.is_ascii_digit())
            .take(14)
            .collect();
        let compact = format!("{}_{}", &digits[..8], &digits[8..]);
        Self { compact, iso }
    }
}

/// Python: `WorkspaceRollback`.
#[derive(Debug, Clone)]
pub struct WorkspaceRollback {
    pub cwd: PathBuf,
    pub snapshots_dir: PathBuf,
}

impl WorkspaceRollback {
    /// Python's constructor eagerly creates `.apex/snapshots`.
    pub fn new(cwd: impl Into<PathBuf>) -> Result<Self, String> {
        let cwd = cwd.into();
        let snapshots_dir = cwd.join(".apex").join("snapshots");
        fs::create_dir_all(&snapshots_dir)
            .map_err(|e| format!("ERROR: Cannot create {}: {e}", snapshots_dir.display()))?;
        Ok(Self { cwd, snapshots_dir })
    }

    /// Python: `_run_git` — returns `(-1, "", "git not found")` when git
    /// cannot be spawned, so callers can treat it like a failed command.
    fn run_git(&self, args: &[&str]) -> (i32, String, String) {
        self.run_git_with("git", args)
    }

    fn run_git_with(&self, program: &str, args: &[&str]) -> (i32, String, String) {
        match Command::new(program)
            .args(args)
            .current_dir(&self.cwd)
            .output()
        {
            Ok(out) => (
                out.status.code().unwrap_or(-1),
                String::from_utf8_lossy(&out.stdout).into_owned(),
                String::from_utf8_lossy(&out.stderr).into_owned(),
            ),
            Err(_) => (-1, String::new(), "git not found".to_string()),
        }
    }

    /// Python: `is_git_repo`.
    pub fn is_git_repo(&self) -> bool {
        self.run_git(&["rev-parse", "--git-dir"]).0 == 0
    }

    /// Python: `create_snapshot(label)`. Returns the snapshot name.
    pub fn create_snapshot(&self, label: &str) -> Result<String, String> {
        self.create_snapshot_at(label, &Timestamp::now())
    }

    /// Testable core of `create_snapshot`: the caller supplies the timestamp.
    fn create_snapshot_at(&self, label: &str, stamp: &Timestamp) -> Result<String, String> {
        if !label.is_empty() && !is_bare_name(label) {
            return Err(format!("ERROR: Invalid snapshot label: {label}"));
        }
        let suffix = if label.is_empty() { "auto" } else { label };
        let name = format!("snapshot_{}_{}", stamp.compact, suffix);
        let snapshot_path = self.snapshots_dir.join(&name);

        // Python uses `mkdir(parents=True, exist_ok=False)`: two snapshots
        // with the same second and label collide instead of merging.
        fs::create_dir(&snapshot_path)
            .map_err(|e| format!("ERROR: Cannot create snapshot {name} (already exists?): {e}"))?;

        let metadata = serde_json::json!({
            "timestamp": stamp.compact,
            "label": label,
            "created_at": stamp.iso,
        });
        write_file(
            &snapshot_path.join("metadata.json"),
            &serde_json::to_string(&metadata).map_err(|e| format!("ERROR: {e}"))?,
        )?;

        if self.is_git_repo() {
            self.save_changed_files(&snapshot_path)?;
            let (code, stdout, _) = self.run_git(&["status", "--porcelain"]);
            if code == 0 {
                write_file(&snapshot_path.join("git_status.txt"), &stdout)?;
            }
        }

        Ok(name)
    }

    /// Python: the `git diff --name-only` block of `create_snapshot`.
    ///
    /// Only tracked modifications are copied; untracked files appear in
    /// `git_status.txt` but not in `files/`, exactly like Python.
    fn save_changed_files(&self, snapshot_path: &Path) -> Result<(), String> {
        let (code, stdout, _) = self.run_git(&["diff", "--name-only"]);
        if code != 0 || stdout.trim().is_empty() {
            return Ok(());
        }
        write_file(&snapshot_path.join("changed_files.txt"), &stdout)?;
        for file in stdout.trim().split('\n') {
            if file.is_empty() {
                continue;
            }
            let src = self.cwd.join(file);
            if src.exists() {
                let dst = snapshot_path.join("files").join(file);
                if let Some(parent) = dst.parent() {
                    fs::create_dir_all(parent)
                        .map_err(|e| format!("ERROR: Cannot create {}: {e}", parent.display()))?;
                }
                fs::copy(&src, &dst).map_err(|e| {
                    format!(
                        "ERROR: Cannot copy {} to {}: {e}",
                        src.display(),
                        dst.display()
                    )
                })?;
            }
        }
        Ok(())
    }

    /// Python: `restore_snapshot(name)`.
    ///
    /// Returns `Ok(false)` when the snapshot does not exist, `Ok(true)` after
    /// copying every backed-up file back into the workspace.
    pub fn restore_snapshot(&self, snapshot_name: &str) -> Result<bool, String> {
        let Some(snapshot_path) = self.snapshot_path(snapshot_name)? else {
            return Ok(false);
        };
        let files_dir = snapshot_path.join("files");
        if files_dir.exists() {
            let mut files = Vec::new();
            collect_files(&files_dir, &mut files)?;
            for file in files {
                let rel_path = file
                    .strip_prefix(&files_dir)
                    .map_err(|e| format!("ERROR: Cannot resolve {}: {e}", file.display()))?;
                let dst = self.cwd.join(rel_path);
                if let Some(parent) = dst.parent() {
                    fs::create_dir_all(parent)
                        .map_err(|e| format!("ERROR: Cannot create {}: {e}", parent.display()))?;
                }
                fs::copy(&file, &dst).map_err(|e| {
                    format!(
                        "ERROR: Cannot restore {} to {}: {e}",
                        file.display(),
                        dst.display()
                    )
                })?;
            }
        }
        Ok(true)
    }

    /// Python: `list_snapshots` — sorted by name, non-directories skipped,
    /// missing metadata tolerated (`unknown` / empty label).
    pub fn list_snapshots(&self) -> Result<Vec<SnapshotInfo>, String> {
        if !self.snapshots_dir.exists() {
            return Ok(Vec::new());
        }
        let mut paths = Vec::new();
        let entries = fs::read_dir(&self.snapshots_dir)
            .map_err(|e| format!("ERROR: Cannot read {}: {e}", self.snapshots_dir.display()))?;
        for entry in entries {
            let entry = entry.map_err(|e| format!("ERROR: Cannot read snapshot entry: {e}"))?;
            paths.push(entry.path());
        }
        sort_snapshot_paths(&mut paths);

        let mut snapshots = Vec::new();
        for path in paths {
            if !path.is_dir() {
                continue;
            }
            let name = path
                .file_name()
                .map(|n| n.to_string_lossy().into_owned())
                .unwrap_or_default();
            let metadata_file = path.join("metadata.json");
            let (created_at, label) = if metadata_file.exists() {
                let data = fs::read_to_string(&metadata_file)
                    .map_err(|e| format!("ERROR: Cannot read {}: {e}", metadata_file.display()))?;
                let metadata: Value = serde_json::from_str(&data).map_err(|e| {
                    format!(
                        "ERROR: Invalid metadata in {}: {e}",
                        metadata_file.display()
                    )
                })?;
                (
                    metadata
                        .get("created_at")
                        .and_then(Value::as_str)
                        .unwrap_or("unknown")
                        .to_string(),
                    metadata
                        .get("label")
                        .and_then(Value::as_str)
                        .unwrap_or("")
                        .to_string(),
                )
            } else {
                ("unknown".to_string(), String::new())
            };
            snapshots.push(SnapshotInfo {
                name,
                created_at,
                label,
            });
        }
        Ok(snapshots)
    }

    /// Python: `delete_snapshot(name)`.
    pub fn delete_snapshot(&self, snapshot_name: &str) -> Result<bool, String> {
        let Some(snapshot_path) = self.snapshot_path(snapshot_name)? else {
            return Ok(false);
        };
        fs::remove_dir_all(&snapshot_path)
            .map_err(|e| format!("ERROR: Cannot delete {}: {e}", snapshot_path.display()))?;
        Ok(true)
    }

    /// Python: `rollback_turn(turns_ago)` — restore the snapshot `turns_ago`
    /// positions from the end, clamped to the oldest snapshot.
    pub fn rollback_turn(&self, turns_ago: usize) -> Result<bool, String> {
        if turns_ago == 0 {
            return Err("ERROR: turns must be at least 1".to_string());
        }
        let snapshots = self.list_snapshots()?;
        if snapshots.is_empty() {
            return Ok(false);
        }
        let target_idx = snapshots.len().saturating_sub(turns_ago);
        self.restore_snapshot(&snapshots[target_idx].name)
    }

    /// Resolve a caller-supplied snapshot name to a direct child of
    /// `.apex/snapshots`, rejecting traversal and separators.
    fn snapshot_path(&self, name: &str) -> Result<Option<PathBuf>, String> {
        if !is_bare_name(name) {
            return Err(format!("ERROR: Invalid snapshot name: {name}"));
        }
        let path = self.snapshots_dir.join(name);
        Ok(path.exists().then_some(path))
    }
}

/// Python: `TurnTracker`.
#[derive(Debug, Clone)]
pub struct TurnTracker {
    pub cwd: PathBuf,
    rollback: WorkspaceRollback,
    turns: Vec<TurnRecord>,
}

impl TurnTracker {
    pub fn new(cwd: impl Into<PathBuf>) -> Result<Self, String> {
        let cwd = cwd.into();
        let rollback = WorkspaceRollback::new(cwd.clone())?;
        let turn_file = cwd.join(".apex").join("turns.json");
        let turns = if turn_file.exists() {
            let data = fs::read_to_string(&turn_file)
                .map_err(|e| format!("ERROR: Cannot read {}: {e}", turn_file.display()))?;
            serde_json::from_str(&data)
                .map_err(|e| format!("ERROR: Invalid turn history {}: {e}", turn_file.display()))?
        } else {
            Vec::new()
        };
        Ok(Self {
            cwd,
            rollback,
            turns,
        })
    }

    /// Python: `self.turn_file = self.cwd / ".apex" / "turns.json"`.
    fn turn_file(&self) -> PathBuf {
        self.cwd.join(".apex").join("turns.json")
    }

    fn save_turns(&self) -> Result<(), String> {
        let turn_file = self.turn_file();
        if let Some(parent) = turn_file.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("ERROR: Cannot create {}: {e}", parent.display()))?;
        }
        let data = serde_json::to_string_pretty(&self.turns).map_err(|e| format!("ERROR: {e}"))?;
        write_file(&turn_file, &data)
    }

    /// Python: `record_turn(turn_data)` — snapshot, append, persist, return
    /// the snapshot name.
    pub fn record_turn(&mut self, data: Value) -> Result<String, String> {
        let turn_number = self.turns.len() + 1;
        let snapshot = self
            .rollback
            .create_snapshot(&format!("turn_{turn_number}"))?;
        self.turns.push(TurnRecord {
            turn_number,
            snapshot: snapshot.clone(),
            timestamp: now_iso8601_micros(),
            data,
        });
        self.save_turns()?;
        Ok(snapshot)
    }

    /// Python: `revert_turn(turns_ago)`.
    ///
    /// `turns_ago == 0` targets the first turn (Python's `turns[-0]` is
    /// `turns[0]`), and an over-large value is clamped to the first turn.
    pub fn revert_turn(&self, turns_ago: usize) -> Result<bool, String> {
        if self.turns.is_empty() {
            return Ok(false);
        }
        let index = if turns_ago == 0 || turns_ago > self.turns.len() {
            0
        } else {
            self.turns.len() - turns_ago
        };
        self.rollback.restore_snapshot(&self.turns[index].snapshot)
    }

    /// Python: `get_turn_history`.
    pub fn get_turn_history(&self) -> &[TurnRecord] {
        &self.turns
    }
}

/// A single path component that cannot traverse upwards: no separators, no
/// `.`/`..`, no drive prefix.
fn is_bare_name(name: &str) -> bool {
    !name.is_empty()
        && name != "."
        && name != ".."
        && Path::new(name).components().count() == 1
        && !name.contains('/')
        && !name.contains('\\')
}

fn write_file(path: &Path, contents: &str) -> Result<(), String> {
    fs::write(path, contents).map_err(|e| format!("ERROR: Cannot write {}: {e}", path.display()))
}

/// Collect regular files recursively; directory symlinks are not followed
/// (`Path.rglob` parity) while file symlinks are treated as files.
fn collect_files(dir: &Path, out: &mut Vec<PathBuf>) -> Result<(), String> {
    let entries =
        fs::read_dir(dir).map_err(|e| format!("ERROR: Cannot read {}: {e}", dir.display()))?;
    for entry in entries {
        let entry = entry.map_err(|e| format!("ERROR: Cannot read {}: {e}", dir.display()))?;
        let path = entry.path();
        let file_type = entry
            .file_type()
            .map_err(|e| format!("ERROR: Cannot stat {}: {e}", path.display()))?;
        if file_type.is_dir() {
            collect_files(&path, out)?;
        } else if file_type.is_file() || (file_type.is_symlink() && path.is_file()) {
            out.push(path);
        }
    }
    Ok(())
}

/// Python sorts `Path` objects; on Windows that comparison is
/// case-insensitive, so mirror it there and sort byte-wise elsewhere.
fn sort_snapshot_paths(paths: &mut [PathBuf]) {
    #[cfg(windows)]
    paths.sort_by_key(|p| p.to_string_lossy().to_lowercase());
    #[cfg(not(windows))]
    paths.sort();
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::process::Command;

    fn git(dir: &Path, args: &[&str]) {
        let out = Command::new("git")
            .args(args)
            .current_dir(dir)
            .env("GIT_AUTHOR_NAME", "Test")
            .env("GIT_AUTHOR_EMAIL", "test@example.com")
            .env("GIT_COMMITTER_NAME", "Test")
            .env("GIT_COMMITTER_EMAIL", "test@example.com")
            .output()
            .expect("git must be installed for the rollback tests");
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
        fs::write(dir.path().join("tracked.txt"), "original\n").unwrap();
        git(dir.path(), &["add", "-A"]);
        git(dir.path(), &["commit", "-m", "init"]);
        dir
    }

    fn stamp(compact: &str) -> Timestamp {
        Timestamp::from_iso(format!(
            "{}-{}-{}T{}:{}:{}.000000",
            &compact[0..4],
            &compact[4..6],
            &compact[6..8],
            &compact[9..11],
            &compact[11..13],
            &compact[13..15]
        ))
    }

    #[test]
    fn timestamp_conversion_matches_python_name_shape() {
        let ts = Timestamp::from_iso("2026-01-02T03:04:05.000006".to_string());
        assert_eq!(ts.compact, "20260102_030405");
        assert_eq!(ts.iso, "2026-01-02T03:04:05.000006");
    }

    #[test]
    fn new_creates_snapshots_directory_like_python() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        assert_eq!(rb.cwd, dir.path());
        assert_eq!(rb.snapshots_dir, dir.path().join(".apex").join("snapshots"));
        assert!(rb.snapshots_dir.is_dir());
    }

    #[test]
    fn is_git_repo_true_and_false() {
        let repo = init_repo();
        assert!(WorkspaceRollback::new(repo.path()).unwrap().is_git_repo());
        let plain = tempfile::tempdir().unwrap();
        assert!(!WorkspaceRollback::new(plain.path()).unwrap().is_git_repo());
    }

    #[test]
    fn missing_git_binary_reports_python_error() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        let (code, out, err) = rb.run_git_with("apex-rs-definitely-not-git", &["status"]);
        assert_eq!(code, -1);
        assert_eq!(out, "");
        assert_eq!(err, "git not found");
    }

    #[test]
    fn snapshot_names_and_metadata_match_python() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        let name = rb
            .create_snapshot_at("demo", &stamp("20260102_030405"))
            .unwrap();
        assert_eq!(name, "snapshot_20260102_030405_demo");
        let metadata: Value = serde_json::from_str(
            &fs::read_to_string(rb.snapshots_dir.join(&name).join("metadata.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(metadata["timestamp"], "20260102_030405");
        assert_eq!(metadata["label"], "demo");
        assert_eq!(metadata["created_at"], "2026-01-02T03:04:05.000000");
    }

    #[test]
    fn empty_label_becomes_auto() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        let name = rb
            .create_snapshot_at("", &stamp("20260102_030405"))
            .unwrap();
        assert_eq!(name, "snapshot_20260102_030405_auto");
    }

    #[test]
    fn snapshot_labels_cannot_escape_the_snapshots_directory() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        let ts = stamp("20260102_030405");
        for label in ["../escape", "..\\escape", "a/b", "..", "."] {
            let err = rb.create_snapshot_at(label, &ts).unwrap_err();
            assert!(err.contains("Invalid snapshot label"), "got: {err}");
        }
        assert!(!dir.path().join("escape").exists());
    }

    #[test]
    fn same_second_and_label_collides_without_overwriting() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        let ts = stamp("20260102_030405");
        let name = rb.create_snapshot_at("demo", &ts).unwrap();
        let err = rb.create_snapshot_at("demo", &ts).unwrap_err();
        assert!(err.contains(&name), "got: {err}");
        assert!(rb.snapshots_dir.join(&name).join("metadata.json").exists());
    }

    #[test]
    fn snapshot_copies_changed_tracked_files_and_status() {
        let repo = init_repo();
        let rb = WorkspaceRollback::new(repo.path()).unwrap();
        fs::write(repo.path().join("tracked.txt"), "modified\n").unwrap();
        fs::write(repo.path().join("untracked.txt"), "new\n").unwrap();

        let name = rb
            .create_snapshot_at("dirty", &stamp("20260102_030405"))
            .unwrap();
        let snapshot = rb.snapshots_dir.join(&name);
        assert_eq!(
            fs::read_to_string(snapshot.join("changed_files.txt")).unwrap(),
            "tracked.txt\n"
        );
        assert_eq!(
            fs::read_to_string(snapshot.join("files").join("tracked.txt")).unwrap(),
            "modified\n"
        );
        assert!(
            !snapshot.join("files").join("untracked.txt").exists(),
            "`git diff --name-only` ignores untracked files"
        );
        let status = fs::read_to_string(snapshot.join("git_status.txt")).unwrap();
        assert!(status.contains(" M tracked.txt"), "got: {status}");
        assert!(status.contains("?? untracked.txt"), "got: {status}");
    }

    #[test]
    fn snapshot_saves_nested_changed_files() {
        let repo = init_repo();
        fs::create_dir_all(repo.path().join("src")).unwrap();
        fs::write(repo.path().join("src").join("nested.txt"), "one\n").unwrap();
        git(repo.path(), &["add", "-A"]);
        git(repo.path(), &["commit", "-m", "nested"]);
        fs::write(repo.path().join("src").join("nested.txt"), "two\n").unwrap();

        let rb = WorkspaceRollback::new(repo.path()).unwrap();
        let name = rb
            .create_snapshot_at("nested", &stamp("20260102_030405"))
            .unwrap();
        assert_eq!(
            fs::read_to_string(
                rb.snapshots_dir
                    .join(name)
                    .join("files")
                    .join("src")
                    .join("nested.txt")
            )
            .unwrap(),
            "two\n"
        );
    }

    #[test]
    fn non_git_snapshot_has_only_metadata() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        let name = rb
            .create_snapshot_at("plain", &stamp("20260102_030405"))
            .unwrap();
        let snapshot = rb.snapshots_dir.join(name);
        assert!(snapshot.join("metadata.json").exists());
        assert!(!snapshot.join("changed_files.txt").exists());
        assert!(!snapshot.join("git_status.txt").exists());
    }

    #[test]
    fn restore_copies_files_back_and_creates_parents() {
        let repo = init_repo();
        let rb = WorkspaceRollback::new(repo.path()).unwrap();
        fs::write(repo.path().join("tracked.txt"), "snapshot\n").unwrap();
        let name = rb
            .create_snapshot_at("before", &stamp("20260102_030405"))
            .unwrap();

        fs::write(repo.path().join("tracked.txt"), "later\n").unwrap();
        assert!(rb.restore_snapshot(&name).unwrap());
        assert_eq!(
            fs::read_to_string(repo.path().join("tracked.txt")).unwrap(),
            "snapshot\n"
        );
    }

    #[test]
    fn restore_missing_snapshot_returns_false() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        assert!(!rb.restore_snapshot("nonexistent_snapshot").unwrap());
    }

    #[test]
    fn restore_and_delete_reject_traversal_names() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        for name in ["", "../outside", "..\\outside", "..", ".", "a/b"] {
            assert!(
                rb.restore_snapshot(name).is_err(),
                "restore must reject {name}"
            );
            assert!(
                rb.delete_snapshot(name).is_err(),
                "delete must reject {name}"
            );
        }
    }

    #[test]
    fn list_snapshots_sorts_skips_files_and_defaults_metadata() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        rb.create_snapshot_at("second", &stamp("20260102_030406"))
            .unwrap();
        rb.create_snapshot_at("first", &stamp("20260102_030405"))
            .unwrap();
        fs::write(rb.snapshots_dir.join("not_a_dir.txt"), "skip\n").unwrap();
        fs::create_dir(rb.snapshots_dir.join("snapshot_no_meta")).unwrap();

        let snapshots = rb.list_snapshots().unwrap();
        let names: Vec<&str> = snapshots.iter().map(|s| s.name.as_str()).collect();
        assert_eq!(
            names,
            vec![
                "snapshot_20260102_030405_first",
                "snapshot_20260102_030406_second",
                "snapshot_no_meta",
            ]
        );
        let no_meta = snapshots.last().unwrap();
        assert_eq!(no_meta.created_at, "unknown");
        assert_eq!(no_meta.label, "");
        assert_eq!(snapshots[0].label, "first");
    }

    #[test]
    fn corrupt_metadata_is_reported() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        let name = rb
            .create_snapshot_at("bad", &stamp("20260102_030405"))
            .unwrap();
        fs::write(rb.snapshots_dir.join(name).join("metadata.json"), "{{{").unwrap();
        assert!(rb.list_snapshots().is_err());
    }

    #[test]
    fn delete_snapshot_removes_directory_and_missing_returns_false() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        let name = rb
            .create_snapshot_at("gone", &stamp("20260102_030405"))
            .unwrap();
        assert!(rb.delete_snapshot(&name).unwrap());
        assert!(rb.list_snapshots().unwrap().is_empty());
        assert!(!rb.delete_snapshot(&name).unwrap());
    }

    #[test]
    fn rollback_turn_clamps_to_oldest_snapshot() {
        let repo = init_repo();
        let rb = WorkspaceRollback::new(repo.path()).unwrap();

        fs::write(repo.path().join("tracked.txt"), "v1\n").unwrap();
        rb.create_snapshot_at("v1", &stamp("20260102_030405"))
            .unwrap();
        fs::write(repo.path().join("tracked.txt"), "v2\n").unwrap();
        rb.create_snapshot_at("v2", &stamp("20260102_030406"))
            .unwrap();
        fs::write(repo.path().join("tracked.txt"), "v3\n").unwrap();

        assert!(rb.rollback_turn(1).unwrap());
        assert_eq!(
            fs::read_to_string(repo.path().join("tracked.txt")).unwrap(),
            "v2\n"
        );

        fs::write(repo.path().join("tracked.txt"), "v4\n").unwrap();
        assert!(rb.rollback_turn(99).unwrap());
        assert_eq!(
            fs::read_to_string(repo.path().join("tracked.txt")).unwrap(),
            "v1\n"
        );
    }

    #[test]
    fn rollback_turn_without_snapshots_returns_false() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        assert!(!rb.rollback_turn(1).unwrap());
    }

    #[test]
    fn rollback_turn_zero_is_an_error_not_a_panic() {
        let dir = tempfile::tempdir().unwrap();
        let rb = WorkspaceRollback::new(dir.path()).unwrap();
        rb.create_snapshot_at("one", &stamp("20260102_030405"))
            .unwrap();
        let err = rb.rollback_turn(0).unwrap_err();
        assert!(err.contains("at least 1"), "got: {err}");
    }

    fn tracker_repo() -> (tempfile::TempDir, TurnTracker) {
        let repo = init_repo();
        let tracker = TurnTracker::new(repo.path()).unwrap();
        (repo, tracker)
    }

    #[test]
    fn record_turn_persists_snapshot_and_history() {
        let (repo, mut tracker) = tracker_repo();
        fs::write(repo.path().join("tracked.txt"), "one\n").unwrap();
        let first = tracker
            .record_turn(serde_json::json!({"query": "q1"}))
            .unwrap();
        fs::write(repo.path().join("tracked.txt"), "two\n").unwrap();
        let second = tracker
            .record_turn(serde_json::json!({"query": "q2"}))
            .unwrap();

        assert!(first.contains("turn_1"), "got: {first}");
        assert!(second.contains("turn_2"), "got: {second}");
        assert_eq!(tracker.get_turn_history().len(), 2);
        assert_eq!(tracker.get_turn_history()[0].turn_number, 1);
        assert_eq!(tracker.get_turn_history()[1].data["query"], "q2");
        assert_eq!(tracker.get_turn_history()[0].timestamp.len(), 26);
        assert!(repo.path().join(".apex").join("turns.json").exists());

        // A fresh tracker reloads the persisted history.
        let reloaded = TurnTracker::new(repo.path()).unwrap();
        assert_eq!(reloaded.get_turn_history().len(), 2);
        assert_eq!(reloaded.get_turn_history()[0].data["query"], "q1");
    }

    #[test]
    fn revert_turn_restores_snapshot_from_that_turn() {
        let (repo, mut tracker) = tracker_repo();
        fs::write(repo.path().join("tracked.txt"), "one\n").unwrap();
        tracker
            .record_turn(serde_json::json!({"query": "q1"}))
            .unwrap();
        fs::write(repo.path().join("tracked.txt"), "two\n").unwrap();
        tracker
            .record_turn(serde_json::json!({"query": "q2"}))
            .unwrap();
        fs::write(repo.path().join("tracked.txt"), "three\n").unwrap();

        assert!(tracker.revert_turn(2).unwrap());
        assert_eq!(
            fs::read_to_string(repo.path().join("tracked.txt")).unwrap(),
            "one\n"
        );

        fs::write(repo.path().join("tracked.txt"), "four\n").unwrap();
        assert!(tracker.revert_turn(1).unwrap());
        assert_eq!(
            fs::read_to_string(repo.path().join("tracked.txt")).unwrap(),
            "two\n"
        );
    }

    #[test]
    fn revert_turn_zero_and_overflow_target_first_turn() {
        let (repo, mut tracker) = tracker_repo();
        fs::write(repo.path().join("tracked.txt"), "one\n").unwrap();
        tracker
            .record_turn(serde_json::json!({"query": "q1"}))
            .unwrap();
        fs::write(repo.path().join("tracked.txt"), "two\n").unwrap();
        tracker
            .record_turn(serde_json::json!({"query": "q2"}))
            .unwrap();
        fs::write(repo.path().join("tracked.txt"), "three\n").unwrap();

        assert!(tracker.revert_turn(0).unwrap());
        assert_eq!(
            fs::read_to_string(repo.path().join("tracked.txt")).unwrap(),
            "one\n"
        );

        fs::write(repo.path().join("tracked.txt"), "four\n").unwrap();
        assert!(tracker.revert_turn(99).unwrap());
        assert_eq!(
            fs::read_to_string(repo.path().join("tracked.txt")).unwrap(),
            "one\n"
        );
    }

    #[test]
    fn revert_turn_without_history_returns_false() {
        let (_repo, tracker) = tracker_repo();
        assert!(!tracker.revert_turn(1).unwrap());
    }

    #[test]
    fn corrupt_turn_history_is_an_error() {
        let repo = init_repo();
        fs::create_dir_all(repo.path().join(".apex")).unwrap();
        fs::write(repo.path().join(".apex").join("turns.json"), "{{{").unwrap();
        assert!(TurnTracker::new(repo.path()).is_err());
    }
}
