//! Snapshot system — port of `apex/snapshot.py` (Git-based undo/redo).
//!
//! Keeps an in-memory undo/redo stack of file changes (before/after content
//! plus a naive line diff) and can persist snapshot metadata to a side git
//! repository under `.apex/snapshots/`.
//!
//! Python exports `SnapshotManager` but never calls it (its `/undo` and
//! `/redo` routes use `session.UndoManager` instead). The Rust port is wired
//! further than Python, like `workspace.rs`: the HTTP server holds one
//! manager in `AppState` and the `/api/v1/snapshot/*` routes are the
//! production surface (the CLI is stateless, so the stacks only live across
//! requests inside a running `serve`).

use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

/// Type of action a snapshot guards (Python's `ActionType` enum).
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ActionType {
    FileWrite,
    FileEdit,
    FileDelete,
    DirCreate,
    DirDelete,
    CommandExec,
}

impl ActionType {
    /// Parse a Python `ActionType.value` string (`"file_write"`, …).
    pub fn parse(value: &str) -> Option<Self> {
        Some(match value {
            "file_write" => Self::FileWrite,
            "file_edit" => Self::FileEdit,
            "file_delete" => Self::FileDelete,
            "dir_create" => Self::DirCreate,
            "dir_delete" => Self::DirDelete,
            "command_exec" => Self::CommandExec,
            _ => return None,
        })
    }
}

/// A single file change inside a snapshot (Python's `FileChange`).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct FileChange {
    pub path: String,
    pub before: Option<String>,
    pub after: Option<String>,
    pub diff: Option<String>,
}

/// A snapshot of one action (Python's `Snapshot`).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct Snapshot {
    pub id: String,
    pub timestamp: String,
    pub action_type: ActionType,
    #[serde(default)]
    pub files: Vec<FileChange>,
    pub command: Option<String>,
    pub message: Option<String>,
}

impl Snapshot {
    /// The Python `to_dict` shape (null for unset command/message).
    pub fn to_dict(&self) -> serde_json::Value {
        serde_json::to_value(self).expect("snapshot serialization cannot fail")
    }
}

/// Git-based snapshot manager for undo/redo (Python's `SnapshotManager`).
pub struct SnapshotManager {
    cwd: PathBuf,
    snapshots_dir: PathBuf,
    undo_stack: Vec<Snapshot>,
    redo_stack: Vec<Snapshot>,
}

impl SnapshotManager {
    /// Create the manager for `cwd`, initializing `.apex/snapshots/` and the
    /// side git repository (best effort, like Python's captured subprocesses).
    pub fn new(cwd: impl AsRef<Path>) -> Self {
        let cwd = cwd.as_ref().to_path_buf();
        let snapshots_dir = cwd.join(".apex").join("snapshots");
        let _ = fs::create_dir_all(&snapshots_dir);
        let manager = Self {
            cwd,
            snapshots_dir,
            undo_stack: Vec::new(),
            redo_stack: Vec::new(),
        };
        manager.init_git_repo();
        manager
    }

    /// Initialize or use the existing side git repo (Python's `_init_git_repo`).
    fn init_git_repo(&self) {
        if self.snapshots_dir.join(".git").exists() {
            return;
        }
        let _ = Command::new("git")
            .arg("init")
            .current_dir(&self.snapshots_dir)
            .output();
        let _ = Command::new("git")
            .args(["config", "user.email", "apex@snapshot.local"])
            .current_dir(&self.snapshots_dir)
            .output();
        let _ = Command::new("git")
            .args(["config", "user.name", "APEX Snapshot"])
            .current_dir(&self.snapshots_dir)
            .output();
    }

    /// SHA256 of a file's bytes, empty for a missing file (Python's
    /// `_get_file_hash`).
    #[allow(dead_code)] // defined in Python but never called there either
    pub fn file_hash(&self, path: &Path) -> String {
        let Ok(bytes) = fs::read(path) else {
            return String::new();
        };
        let mut hasher = Sha256::new();
        hasher.update(&bytes);
        let digest = hasher.finalize();
        digest.iter().map(|b| format!("{b:02x}")).collect()
    }

    /// Start tracking a new action. Returns the snapshot id (Python's `track`).
    pub fn track(&mut self, action_type: ActionType) -> String {
        let snapshot_id = new_snapshot_id();
        let snapshot = Snapshot {
            id: snapshot_id.clone(),
            timestamp: now_iso(),
            action_type,
            files: Vec::new(),
            command: None,
            message: None,
        };
        self.undo_stack.push(snapshot);
        self.redo_stack.clear();
        snapshot_id
    }

    /// Add a file change to a tracked snapshot (Python's `add_file_change`).
    pub fn add_file_change(
        &mut self,
        snapshot_id: &str,
        path: &str,
        before: Option<String>,
        after: Option<String>,
    ) {
        let Some(snapshot) = self.undo_stack.iter_mut().find(|s| s.id == snapshot_id) else {
            return;
        };
        let mut change = FileChange {
            path: path.to_string(),
            before,
            after,
            diff: None,
        };
        // Python: `if before and after` — both must be present and non-empty.
        if let (Some(b), Some(a)) = (&change.before, &change.after) {
            if !b.is_empty() && !a.is_empty() {
                change.diff = Some(Self::compute_diff(b, a));
            }
        }
        snapshot.files.push(change);
    }

    /// Track a file before modification (Python's `track_file`). Returns the
    /// snapshot with the pre-change content, or `None` when the file is absent.
    pub fn track_file(&mut self, path: &str, action_type: ActionType) -> Option<Snapshot> {
        let before_content = fs::read_to_string(self.cwd.join(path)).ok()?;
        let snapshot_id = self.track(action_type);
        self.add_file_change(&snapshot_id, path, Some(before_content), None);
        self.get_snapshot(&snapshot_id).cloned()
    }

    /// Naive line diff (Python's `_compute_diff`): `  ` context lines, `+ `
    /// added lines, `- ` removed lines.
    pub fn compute_diff(before: &str, after: &str) -> String {
        let before_lines: Vec<&str> = before.split_inclusive('\n').collect();
        let after_lines: Vec<&str> = after.split_inclusive('\n').collect();
        let mut diff = String::new();
        let (mut i, mut j) = (0usize, 0usize);
        while i < before_lines.len() || j < after_lines.len() {
            if i < before_lines.len() && j < after_lines.len() && before_lines[i] == after_lines[j]
            {
                diff.push_str("  ");
                diff.push_str(before_lines[i]);
                i += 1;
                j += 1;
            } else if j < after_lines.len()
                && (i >= before_lines.len() || before_lines[i] != after_lines[j])
            {
                diff.push_str("+ ");
                diff.push_str(after_lines[j]);
                j += 1;
            } else if i < before_lines.len() {
                diff.push_str("- ");
                diff.push_str(before_lines[i]);
                i += 1;
            }
        }
        diff
    }

    /// Get a tracked snapshot by id (Python's `get_snapshot`).
    pub fn get_snapshot(&self, snapshot_id: &str) -> Option<&Snapshot> {
        self.undo_stack.iter().find(|s| s.id == snapshot_id)
    }

    /// Restore the files of a tracked snapshot to their pre-change state
    /// (Python's `restore`).
    pub fn restore(&self, snapshot_id: &str) -> bool {
        let Some(snapshot) = self.get_snapshot(snapshot_id) else {
            return false;
        };
        self.apply_restore(snapshot);
        true
    }

    /// Apply a snapshot's file changes to disk (shared by `restore` and `undo`).
    fn apply_restore(&self, snapshot: &Snapshot) {
        for change in &snapshot.files {
            let file_path = self.cwd.join(&change.path);
            match &change.before {
                None => {
                    if file_path.exists() {
                        let _ = fs::remove_file(&file_path);
                    }
                }
                Some(before) => {
                    if let Some(parent) = file_path.parent() {
                        let _ = fs::create_dir_all(parent);
                    }
                    let _ = fs::write(&file_path, before);
                }
            }
        }
    }

    /// Undo the last action (Python's `undo`).
    ///
    /// Divergence (bug fix): Python pops the snapshot and then calls
    /// `restore(snapshot.id)`, which looks the snapshot up in the undo stack —
    /// where it no longer exists — so Python's undo never restored any file.
    /// The port applies the popped snapshot's changes directly.
    pub fn undo(&mut self) -> Option<Snapshot> {
        let snapshot = self.undo_stack.pop()?;
        self.apply_restore(&snapshot);
        self.redo_stack.push(snapshot.clone());
        Some(snapshot)
    }

    /// Redo the last undone action (Python's `redo`).
    pub fn redo(&mut self) -> Option<Snapshot> {
        let snapshot = self.redo_stack.pop()?;
        for change in &snapshot.files {
            let Some(after) = &change.after else {
                continue;
            };
            let file_path = self.cwd.join(&change.path);
            if let Some(parent) = file_path.parent() {
                let _ = fs::create_dir_all(parent);
            }
            let _ = fs::write(&file_path, after);
        }
        self.undo_stack.push(snapshot.clone());
        Some(snapshot)
    }

    pub fn can_undo(&self) -> bool {
        !self.undo_stack.is_empty()
    }

    pub fn can_redo(&self) -> bool {
        !self.redo_stack.is_empty()
    }

    /// Stack depths (Python only exposes `can_undo`/`can_redo`; the counts
    /// feed the Rust-only `GET /api/v1/snapshot/status` route).
    pub fn counts(&self) -> (usize, usize) {
        (self.undo_stack.len(), self.redo_stack.len())
    }

    /// Persist snapshot metadata to the side git repo (Python's
    /// `save_snapshot_to_git`).
    #[allow(dead_code)] // Python exposes it but never calls it — TODO(v2.6): add a save route
    pub fn save_snapshot_to_git(&self, snapshot: &Snapshot) {
        let meta_name = format!("{}.json", snapshot.id);
        let meta_path = self.snapshots_dir.join(&meta_name);
        let json = match serde_json::to_string_pretty(&snapshot.to_dict()) {
            Ok(j) => j,
            Err(_) => return,
        };
        if fs::write(meta_path, json).is_err() {
            return;
        }
        let _ = Command::new("git")
            .args(["add", &meta_name])
            .current_dir(&self.snapshots_dir)
            .output();
    }

    /// The last `limit` snapshots (Python's `get_history`); `0` returns all,
    /// matching Python's `[-0:]` slice.
    pub fn get_history(&self, limit: usize) -> Vec<&Snapshot> {
        if limit == 0 {
            return self.undo_stack.iter().collect();
        }
        let start = self.undo_stack.len().saturating_sub(limit);
        self.undo_stack[start..].iter().collect()
    }

    /// Clear both stacks (Python's `clear`).
    #[allow(dead_code)] // Python exposes it but never calls it — TODO(v2.6): expose a clear route
    pub fn clear(&mut self) {
        self.undo_stack.clear();
        self.redo_stack.clear();
    }
}

/// Factory mirroring Python's `create_snapshot_manager`.
pub fn create_snapshot_manager(cwd: impl AsRef<Path>) -> SnapshotManager {
    SnapshotManager::new(cwd)
}

/// 12-hex snapshot id: sha256 of the timestamp + 8 random bytes, like Python
/// (`hashlib.sha256(f"{datetime.now().isoformat()}{os.urandom(8)}")[:12]`).
fn new_snapshot_id() -> String {
    let mut random = [0u8; 8];
    let _ = getrandom::getrandom(&mut random);
    let mut hasher = Sha256::new();
    hasher.update(now_iso().as_bytes());
    hasher.update(random);
    let digest = hasher.finalize();
    let hex: String = digest.iter().map(|b| format!("{b:02x}")).collect();
    hex[..12].to_string()
}

/// Local ISO-8601 timestamp (Python's `datetime.now().isoformat()`).
fn now_iso() -> String {
    chrono::Local::now()
        .format("%Y-%m-%dT%H:%M:%S%.6f")
        .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_manager() -> (tempfile::TempDir, SnapshotManager) {
        let dir = tempfile::tempdir().unwrap();
        let manager = SnapshotManager::new(dir.path());
        (dir, manager)
    }

    #[test]
    fn action_type_roundtrip() {
        let values = [
            "file_write",
            "file_edit",
            "file_delete",
            "dir_create",
            "dir_delete",
            "command_exec",
        ];
        for value in values {
            let t = ActionType::parse(value).unwrap();
            assert_eq!(serde_json::to_value(t).unwrap(), serde_json::json!(value));
        }
        assert!(ActionType::parse("bogus").is_none());
    }

    #[test]
    fn compute_diff_context_insert_and_delete() {
        // An insertion at the end keeps every context line.
        let diff = SnapshotManager::compute_diff("a\nb\n", "a\nb\nc\n");
        assert_eq!(diff, "  a\n  b\n+ c\n");
        // A mid-file replacement: the naive two-pointer walk emits the `+`
        // lines before the `-` lines (Python parity with
        // `apex/snapshot.py::_compute_diff`).
        let diff = SnapshotManager::compute_diff("a\nb\nc\n", "a\nx\nc\n");
        assert_eq!(diff, "  a\n+ x\n+ c\n- b\n- c\n");
    }

    #[test]
    fn track_assigns_a_12_hex_id() {
        let (_dir, mut manager) = temp_manager();
        let id = manager.track(ActionType::FileEdit);
        assert_eq!(id.len(), 12);
        assert!(id.chars().all(|c| c.is_ascii_hexdigit()));
        assert!(manager.can_undo());
        assert!(!manager.can_redo());
    }

    #[test]
    fn track_file_captures_before_content() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("a.txt"), "v1").unwrap();
        let mut manager = SnapshotManager::new(dir.path());

        assert!(manager
            .track_file("missing.txt", ActionType::FileEdit)
            .is_none());

        let snap = manager.track_file("a.txt", ActionType::FileWrite).unwrap();
        assert_eq!(snap.files.len(), 1);
        assert_eq!(snap.files[0].path, "a.txt");
        assert_eq!(snap.files[0].before.as_deref(), Some("v1"));
        assert!(snap.files[0].after.is_none());
    }

    #[test]
    fn undo_restores_before_content() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("a.txt"), "v1").unwrap();
        let mut manager = SnapshotManager::new(dir.path());

        manager.track_file("a.txt", ActionType::FileEdit).unwrap();
        std::fs::write(dir.path().join("a.txt"), "v2").unwrap();

        let undone = manager.undo().expect("must undo");
        assert_eq!(
            std::fs::read_to_string(dir.path().join("a.txt")).unwrap(),
            "v1",
            "undo must restore the pre-change content"
        );
        assert!(!manager.can_undo());
        assert!(manager.can_redo());
        assert_eq!(undone.id, manager.redo_stack[0].id);

        // track_file captured no `after`, so redo does not rewrite the file
        // (Python parity) but the snapshot returns to the undo stack.
        manager.redo().unwrap();
        assert!(manager.can_undo());
        assert!(!manager.can_redo());
    }

    #[test]
    fn redo_applies_after_content() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("a.txt"), "v1").unwrap();
        let mut manager = SnapshotManager::new(dir.path());

        let id = manager.track(ActionType::FileEdit);
        manager.add_file_change(&id, "a.txt", Some("v1".into()), Some("v2".into()));
        // Both sides present: the diff is computed on add.
        assert!(manager.get_snapshot(&id).unwrap().files[0].diff.is_some());

        std::fs::write(dir.path().join("a.txt"), "v2").unwrap();
        let _ = manager.undo().unwrap();
        assert_eq!(
            std::fs::read_to_string(dir.path().join("a.txt")).unwrap(),
            "v1"
        );

        let redone = manager.redo().unwrap();
        assert_eq!(
            std::fs::read_to_string(dir.path().join("a.txt")).unwrap(),
            "v2",
            "redo must re-apply the after content"
        );
        assert_eq!(redone.files[0].after.as_deref(), Some("v2"));
    }

    #[test]
    fn restore_with_none_before_deletes_file() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("tmp.txt"), "x").unwrap();
        let mut manager = SnapshotManager::new(dir.path());

        let id = manager.track(ActionType::FileDelete);
        manager.add_file_change(&id, "tmp.txt", None, None);
        assert!(manager.restore(&id));
        assert!(!dir.path().join("tmp.txt").exists());
        assert!(!manager.restore("unknown-id"));
    }

    #[test]
    fn history_limit_and_clear() {
        let (_dir, mut manager) = temp_manager();
        for _ in 0..5 {
            manager.track(ActionType::FileEdit);
        }
        assert_eq!(manager.get_history(2).len(), 2);
        assert_eq!(manager.get_history(50).len(), 5);
        assert_eq!(manager.get_history(0).len(), 5); // Python: `[-0:]` → all
        manager.clear();
        assert!(!manager.can_undo());
        assert!(manager.get_history(10).is_empty());
    }

    #[test]
    fn snapshot_to_dict_shape() {
        let (_dir, mut manager) = temp_manager();
        let id = manager.track(ActionType::CommandExec);
        let snap = manager.get_snapshot(&id).unwrap().to_dict();
        assert_eq!(snap["id"], id);
        assert_eq!(snap["action_type"], "command_exec");
        assert!(snap["files"].is_array());
        assert!(snap["command"].is_null());
        assert!(snap["message"].is_null());
        assert!(snap["timestamp"].as_str().unwrap().contains('T'));
    }

    #[test]
    fn new_manager_creates_snapshots_dir() {
        let dir = tempfile::tempdir().unwrap();
        let _manager = SnapshotManager::new(dir.path());
        assert!(dir.path().join(".apex").join("snapshots").is_dir());
    }
}
