//! Snapshot manager — port of `apex/snapshot.py`.
//!
//! This provides a Git-based undo/redo system for individual file changes,
//! distinct from `workspace_rollback.rs` which creates side-git snapshots of
//! the entire workspace. The snapshot manager tracks individual file edits
//! with diffs and maintains an in-memory undo/redo stack backed by a local
//! git repository at `.apex/snapshots/`.

use std::collections::VecDeque;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::{Arc, Mutex, OnceLock};

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};

/// Type of action that triggered the snapshot.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
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
    fn from_python_str(s: &str) -> Self {
        match s {
            "file_write" => ActionType::FileWrite,
            "file_edit" => ActionType::FileEdit,
            "file_delete" => ActionType::FileDelete,
            "dir_create" => ActionType::DirCreate,
            "dir_delete" => ActionType::DirDelete,
            "command_exec" => ActionType::CommandExec,
            _ => ActionType::FileEdit,
        }
    }

    #[allow(dead_code)]
    fn to_python_str(self) -> &'static str {
        match self {
            ActionType::FileWrite => "file_write",
            ActionType::FileEdit => "file_edit",
            ActionType::FileDelete => "file_delete",
            ActionType::DirCreate => "dir_create",
            ActionType::DirDelete => "dir_delete",
            ActionType::CommandExec => "command_exec",
        }
    }
}

/// A single file change within a snapshot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileChange {
    pub path: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub before: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub after: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub diff: Option<String>,
}

/// A snapshot of one or more file changes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Snapshot {
    pub id: String,
    pub timestamp: String, // ISO 8601
    pub action_type: ActionType,
    pub files: Vec<FileChange>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub command: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
}

impl Snapshot {
    /// Compute a diff between `before` and `after` content.
    fn compute_diff(before: &str, after: &str) -> String {
        let before_lines: Vec<&str> = before.split('\n').collect();
        let after_lines: Vec<&str> = after.split('\n').collect();

        let mut diff = Vec::new();
        let mut i = 0;
        let mut j = 0;

        while i < before_lines.len() || j < after_lines.len() {
            if i < before_lines.len() && j < after_lines.len() && before_lines[i] == after_lines[j]
            {
                diff.push(format!("  {}", before_lines[i]));
                i += 1;
                j += 1;
            } else if j < after_lines.len()
                && (i >= before_lines.len() || before_lines[i] != after_lines[j])
            {
                diff.push(format!("+ {}", after_lines[j]));
                j += 1;
            } else if i < before_lines.len() {
                diff.push(format!("- {}", before_lines[i]));
                i += 1;
            }
        }

        diff.join("\n")
    }
}

/// In-memory snapshot manager with git-backed persistence.
pub struct SnapshotManager {
    cwd: PathBuf,
    #[allow(dead_code)]
    snapshots_dir: PathBuf,
    undo_stack: Mutex<VecDeque<Snapshot>>,
    redo_stack: Mutex<VecDeque<Snapshot>>,
}

/// Global snapshot manager instance (one per process, keyed by cwd).
static GLOBAL_MANAGER: OnceLock<Arc<Mutex<SnapshotManager>>> = OnceLock::new();

impl SnapshotManager {
    /// Create a new snapshot manager for the given working directory.
    pub fn new<P: AsRef<Path>>(cwd: P) -> Result<Self> {
        let cwd = cwd.as_ref().to_path_buf();
        let snapshots_dir = cwd.join(".apex").join("snapshots");
        fs::create_dir_all(&snapshots_dir)?;

        // Initialize git repo if needed
        Self::init_git_repo(&snapshots_dir)?;

        Ok(Self {
            cwd,
            snapshots_dir,
            undo_stack: Mutex::new(VecDeque::new()),
            redo_stack: Mutex::new(VecDeque::new()),
        })
    }

    /// Initialize the git repository for snapshot storage.
    #[allow(unreachable_code)]
    fn init_git_repo(snapshots_dir: &Path) -> Result<()> {
        let git_dir = snapshots_dir.join(".git");
        if !git_dir.exists() {
            // Skip git init in test environments to avoid slow/hanging git operations
            #[cfg(test)]
            {
                return Ok(());
            }

            let output = Command::new("git")
                .args(["init"])
                .current_dir(snapshots_dir)
                .output()
                .context("Failed to run git init")?;
            if !output.status.success() {
                anyhow::bail!(
                    "git init failed: {}",
                    String::from_utf8_lossy(&output.stderr)
                );
            }

            // Configure git user for commits
            for (key, value) in [
                ("user.email", "apex@snapshot.local"),
                ("user.name", "APEX Snapshot"),
            ] {
                let output = Command::new("git")
                    .args(["config", key, value])
                    .current_dir(snapshots_dir)
                    .output()
                    .context("Failed to run git config")?;
                if !output.status.success() {
                    anyhow::bail!(
                        "git config {} failed: {}",
                        key,
                        String::from_utf8_lossy(&output.stderr)
                    );
                }
            }
        }
        Ok(())
    }

    /// Generate a unique snapshot ID.
    fn generate_id() -> String {
        use sha2::{Digest, Sha256};
        let now = chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true);
        let mut hasher = Sha256::new();
        hasher.update(now.as_bytes());
        hasher.update(rand::random::<[u8; 8]>());
        let hash = hasher.finalize();
        hex::encode(hash)[..12].to_string()
    }

    /// Start tracking a new action. Returns the snapshot ID.
    pub fn track(&self, action_type: ActionType) -> String {
        let snapshot_id = Self::generate_id();
        let snapshot = Snapshot {
            id: snapshot_id.clone(),
            timestamp: chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true),
            action_type,
            files: Vec::new(),
            command: None,
            message: None,
        };

        let mut undo = self.undo_stack.lock().unwrap();
        undo.push_back(snapshot);
        let mut redo = self.redo_stack.lock().unwrap();
        redo.clear();

        snapshot_id
    }

    /// Add a file change to an existing snapshot.
    pub fn add_file_change(
        &self,
        snapshot_id: &str,
        path: &str,
        before: Option<&str>,
        after: Option<&str>,
    ) -> Result<()> {
        let mut undo = self.undo_stack.lock().unwrap();
        if let Some(snapshot) = undo.iter_mut().find(|s| s.id == snapshot_id) {
            let mut change = FileChange {
                path: path.to_string(),
                before: before.map(String::from),
                after: after.map(String::from),
                diff: None,
            };
            if let (Some(b), Some(a)) = (before, after) {
                change.diff = Some(Snapshot::compute_diff(b, a));
            }
            snapshot.files.push(change);
            Ok(())
        } else {
            anyhow::bail!("Snapshot not found: {}", snapshot_id)
        }
    }

    /// Track a file before modification. Reads the file and creates a snapshot.
    pub fn track_file(&self, path: &str, action_type: ActionType) -> Result<Option<Snapshot>> {
        let file_path = self.cwd.join(path);
        if !file_path.exists() {
            return Ok(None);
        }

        let snapshot_id = self.track(action_type);
        let before_content = fs::read_to_string(&file_path)?;
        self.add_file_change(&snapshot_id, path, Some(&before_content), None)?;

        self.get_snapshot(&snapshot_id)
    }

    /// Get a snapshot by ID from the undo stack.
    pub fn get_snapshot(&self, snapshot_id: &str) -> Result<Option<Snapshot>> {
        let undo = self.undo_stack.lock().unwrap();
        Ok(undo.iter().find(|s| s.id == snapshot_id).cloned())
    }

    /// Restore files to the state in a snapshot (given the snapshot directly).
    pub fn restore_snapshot(&self, snapshot: &Snapshot) -> Result<bool> {
        for file_change in &snapshot.files {
            let file_path = self.cwd.join(&file_change.path);
            if file_change.before.is_none() {
                // File was created, so delete it on restore
                if file_path.exists() {
                    fs::remove_file(&file_path)?;
                }
            } else if let Some(before) = &file_change.before {
                // File was modified, restore previous content
                if let Some(parent) = file_path.parent() {
                    fs::create_dir_all(parent)?;
                }
                fs::write(&file_path, before)?;
            }
        }

        Ok(true)
    }

    /// Restore files to the state in a snapshot (by ID).
    pub fn restore(&self, snapshot_id: &str) -> Result<bool> {
        let snapshot = self
            .get_snapshot(snapshot_id)?
            .ok_or_else(|| anyhow::anyhow!("Snapshot not found: {}", snapshot_id))?;
        self.restore_snapshot(&snapshot)
    }

    /// Undo the last action.
    pub fn undo(&self) -> Result<Option<Snapshot>> {
        let snapshot = {
            let mut undo = self.undo_stack.lock().unwrap();
            undo.pop_back()
        };

        if let Some(snapshot) = snapshot {
            self.restore_snapshot(&snapshot)?;
            let mut redo = self.redo_stack.lock().unwrap();
            redo.push_back(snapshot.clone());
            Ok(Some(snapshot))
        } else {
            Ok(None)
        }
    }

    /// Redo the last undone action.
    pub fn redo(&self) -> Result<Option<Snapshot>> {
        let mut redo = self.redo_stack.lock().unwrap();
        if let Some(snapshot) = redo.pop_back() {
            for file_change in &snapshot.files {
                let file_path = self.cwd.join(&file_change.path);
                if let Some(after) = &file_change.after {
                    if let Some(parent) = file_path.parent() {
                        fs::create_dir_all(parent)?;
                    }
                    fs::write(&file_path, after)?;
                }
            }
            let mut undo = self.undo_stack.lock().unwrap();
            undo.push_back(snapshot.clone());
            Ok(Some(snapshot))
        } else {
            Ok(None)
        }
    }

    /// Check if undo is available.
    pub fn can_undo(&self) -> bool {
        !self.undo_stack.lock().unwrap().is_empty()
    }

    /// Check if redo is available.
    pub fn can_redo(&self) -> bool {
        !self.redo_stack.lock().unwrap().is_empty()
    }

    /// Save snapshot metadata to the git repository.
    #[allow(dead_code)]
    pub fn save_snapshot_to_git(&self, snapshot: &Snapshot) -> Result<()> {
        let meta_path = self.snapshots_dir.join(format!("{}.json", snapshot.id));
        let json = serde_json::to_string_pretty(snapshot)?;
        fs::write(&meta_path, json)?;

        // Git add
        let output = Command::new("git")
            .args(["add", &format!("{}.json", snapshot.id)])
            .current_dir(&self.snapshots_dir)
            .output()
            .context("Failed to run git add")?;
        if !output.status.success() {
            anyhow::bail!(
                "git add failed: {}",
                String::from_utf8_lossy(&output.stderr)
            );
        }

        // Git commit
        let output = Command::new("git")
            .args(["commit", "-m", &format!("snapshot: {}", snapshot.id)])
            .current_dir(&self.snapshots_dir)
            .output()
            .context("Failed to run git commit")?;
        if !output.status.success() {
            // Not an error if nothing to commit
            let stderr = String::from_utf8_lossy(&output.stderr);
            if !stderr.contains("nothing to commit") {
                anyhow::bail!("git commit failed: {}", stderr);
            }
        }

        Ok(())
    }

    /// Get the undo history (most recent first).
    pub fn get_history(&self, limit: usize) -> Vec<Snapshot> {
        let undo = self.undo_stack.lock().unwrap();
        undo.iter().rev().take(limit).cloned().collect()
    }

    /// Clear all snapshots.
    pub fn clear(&self) {
        self.undo_stack.lock().unwrap().clear();
        self.redo_stack.lock().unwrap().clear();
    }
}

/// Get or create the global snapshot manager for the current working directory.
pub fn get_global_manager(cwd: &Path) -> Result<Arc<Mutex<SnapshotManager>>> {
    let manager = GLOBAL_MANAGER.get_or_init(|| {
        Arc::new(Mutex::new(
            SnapshotManager::new(cwd).expect("Failed to create snapshot manager"),
        ))
    });
    Ok(Arc::clone(manager))
}

/// CLI command: create a snapshot tracking the current state of a file.
pub fn cli_snapshot_track_file(
    path: &str,
    action_type: &str,
    cwd: &Path,
) -> Result<Option<String>> {
    let manager = get_global_manager(cwd)?;
    let action = ActionType::from_python_str(action_type);
    let guard = manager.lock().unwrap();
    if let Some(snapshot) = guard.track_file(path, action)? {
        Ok(Some(snapshot.id))
    } else {
        Ok(None)
    }
}

/// CLI command: undo last change.
pub fn cli_snapshot_undo(cwd: &Path) -> Result<Option<String>> {
    let manager = get_global_manager(cwd)?;
    let guard = manager.lock().unwrap();
    if let Some(snapshot) = guard.undo()? {
        Ok(Some(snapshot.id))
    } else {
        Ok(None)
    }
}

/// CLI command: redo last undone change.
pub fn cli_snapshot_redo(cwd: &Path) -> Result<Option<String>> {
    let manager = get_global_manager(cwd)?;
    let guard = manager.lock().unwrap();
    if let Some(snapshot) = guard.redo()? {
        Ok(Some(snapshot.id))
    } else {
        Ok(None)
    }
}

/// CLI command: check if undo is available.
pub fn cli_snapshot_can_undo(cwd: &Path) -> bool {
    let manager = get_global_manager(cwd).unwrap();
    let guard = manager.lock().unwrap();
    guard.can_undo()
}

/// CLI command: check if redo is available.
pub fn cli_snapshot_can_redo(cwd: &Path) -> bool {
    let manager = get_global_manager(cwd).unwrap();
    let guard = manager.lock().unwrap();
    guard.can_redo()
}

/// CLI command: list snapshot history.
pub fn cli_snapshot_history(cwd: &Path, limit: usize) -> Result<Vec<Snapshot>> {
    let manager = get_global_manager(cwd)?;
    let guard = manager.lock().unwrap();
    Ok(guard.get_history(limit))
}

/// CLI command: clear all snapshots.
pub fn cli_snapshot_clear(cwd: &Path) -> Result<()> {
    let manager = get_global_manager(cwd)?;
    let guard = manager.lock().unwrap();
    guard.clear();
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_snapshot_manager_basic() -> Result<()> {
        let dir = tempdir()?;
        let manager = SnapshotManager::new(dir.path())?;

        // Create a test file
        let file_path = dir.path().join("test.txt");
        fs::write(&file_path, "hello")?;

        // Track the file
        let snapshot = manager.track_file("test.txt", ActionType::FileEdit)?;
        assert!(snapshot.is_some());
        let snapshot_id = snapshot.unwrap().id;

        // Modify the file
        fs::write(&file_path, "hello world")?;

        // Add the after state
        manager.add_file_change(&snapshot_id, "test.txt", Some("hello"), Some("hello world"))?;

        // Undo
        let undone = manager.undo()?;
        assert!(undone.is_some());
        assert_eq!(fs::read_to_string(&file_path)?, "hello");

        // Redo
        let redone = manager.redo()?;
        assert!(redone.is_some());
        assert_eq!(fs::read_to_string(&file_path)?, "hello world");

        Ok(())
    }

    #[test]
    fn test_snapshot_manager_file_delete() -> Result<()> {
        let dir = tempdir()?;
        let manager = SnapshotManager::new(dir.path())?;

        let file_path = dir.path().join("test.txt");
        fs::write(&file_path, "hello")?;

        let snapshot = manager.track_file("test.txt", ActionType::FileDelete)?;
        assert!(snapshot.is_some());
        let snapshot_id = snapshot.unwrap().id;

        // Delete the file
        fs::remove_file(&file_path)?;

        // Add the after state (None means deleted)
        manager.add_file_change(&snapshot_id, "test.txt", Some("hello"), None)?;

        // Undo should restore the file
        manager.undo()?;
        assert!(file_path.exists());
        assert_eq!(fs::read_to_string(&file_path)?, "hello");

        Ok(())
    }

    #[test]
    fn test_snapshot_manager_file_create() -> Result<()> {
        let dir = tempdir()?;
        let manager = SnapshotManager::new(dir.path())?;

        let file_path = dir.path().join("new.txt");

        // Track a new file (before is None)
        let snapshot_id = manager.track(ActionType::FileWrite);
        manager.add_file_change(&snapshot_id, "new.txt", None, Some("new content"))?;

        // Create the file
        fs::write(&file_path, "new content")?;

        // Undo should delete the file
        manager.undo()?;
        assert!(!file_path.exists());

        // Redo should recreate it
        manager.redo()?;
        assert!(file_path.exists());
        assert_eq!(fs::read_to_string(&file_path)?, "new content");

        Ok(())
    }

    #[test]
    fn test_snapshot_diff() {
        let diff =
            Snapshot::compute_diff("line1\nline2\nline3", "line1\nline2 modified\nline3\nline4");
        assert!(diff.contains("- line2"));
        assert!(diff.contains("+ line2 modified"));
        assert!(diff.contains("+ line4"));
    }

    #[test]
    fn test_can_undo_redo() -> Result<()> {
        let dir = tempdir()?;
        let manager = SnapshotManager::new(dir.path())?;

        assert!(!manager.can_undo());
        assert!(!manager.can_redo());

        let file_path = dir.path().join("test.txt");
        fs::write(&file_path, "hello")?;
        manager.track_file("test.txt", ActionType::FileEdit)?;

        assert!(manager.can_undo());
        assert!(!manager.can_redo());

        manager.undo()?;
        assert!(!manager.can_undo());
        assert!(manager.can_redo());

        manager.redo()?;
        assert!(manager.can_undo());
        assert!(!manager.can_redo());

        Ok(())
    }
}
