"""Snapshot system for APEX - Git-based undo/redo."""

import os
import subprocess
import hashlib
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ActionType(Enum):
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    FILE_DELETE = "file_delete"
    DIR_CREATE = "dir_create"
    DIR_DELETE = "dir_delete"
    COMMAND_EXEC = "command_exec"


@dataclass
class FileChange:
    path: str
    before: Optional[str] = None
    after: Optional[str] = None
    diff: Optional[str] = None


@dataclass
class Snapshot:
    id: str
    timestamp: datetime
    action_type: ActionType
    files: List[FileChange] = field(default_factory=list)
    command: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "action_type": self.action_type.value,
            "files": [
                {
                    "path": fc.path,
                    "before": fc.before,
                    "after": fc.after,
                    "diff": fc.diff
                }
                for fc in self.files
            ],
            "command": self.command,
            "message": self.message
        }


class SnapshotManager:
    """Git-based snapshot system for undo/redo."""

    def __init__(self, cwd: Path | str):
        self.cwd = Path(cwd)
        self._snapshots_dir = self.cwd / ".apex" / "snapshots"
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)
        self._init_git_repo()
        self._undo_stack: List[Snapshot] = []
        self._redo_stack: List[Snapshot] = []

    def _init_git_repo(self) -> None:
        """Initialize or use existing git repo for snapshots."""
        git_dir = self._snapshots_dir / ".git"
        if not git_dir.exists():
            subprocess.run(
                ["git", "init"],
                cwd=self._snapshots_dir,
                capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.email", "apex@snapshot.local"],
                cwd=self._snapshots_dir,
                capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.name", "APEX Snapshot"],
                cwd=self._snapshots_dir,
                capture_output=True
            )

    def _get_file_hash(self, path: Path) -> str:
        """Get SHA256 hash of a file."""
        if not path.exists():
            return ""
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def track(self, action_type: ActionType = ActionType.FILE_EDIT) -> str:
        """Start tracking changes. Returns snapshot ID."""
        snapshot_id = hashlib.sha256(
            f"{datetime.now().isoformat()}{os.urandom(8)}".encode()
        ).hexdigest()[:12]

        snapshot = Snapshot(
            id=snapshot_id,
            timestamp=datetime.now(),
            action_type=action_type
        )

        self._undo_stack.append(snapshot)
        self._redo_stack.clear()

        return snapshot_id

    def add_file_change(self, snapshot_id: str, path: str, before: str = None, after: str = None) -> None:
        """Add a file change to a snapshot."""
        for snapshot in self._undo_stack:
            if snapshot.id == snapshot_id:
                change = FileChange(
                    path=path,
                    before=before,
                    after=after
                )
                if before and after:
                    change.diff = self._compute_diff(before, after)
                snapshot.files.append(change)
                break

    def track_file(self, path: str, action_type: ActionType = ActionType.FILE_EDIT) -> Optional[Snapshot]:
        """Track a file before modification."""
        file_path = self.cwd / path
        if not file_path.exists():
            return None

        snapshot_id = self.track(action_type)
        before_content = file_path.read_text()

        self.add_file_change(snapshot_id, path, before=before_content)
        return self.get_snapshot(snapshot_id)

    def _compute_diff(self, before: str, after: str) -> str:
        """Compute diff between before and after content."""
        before_lines = before.splitlines(keepends=True)
        after_lines = after.splitlines(keepends=True)

        diff = []
        i = j = 0
        while i < len(before_lines) or j < len(after_lines):
            if i < len(before_lines) and j < len(after_lines) and before_lines[i] == after_lines[j]:
                diff.append(f"  {before_lines[i]}")
                i += 1
                j += 1
            elif j < len(after_lines) and (i >= len(before_lines) or before_lines[i] != after_lines[j]):
                diff.append(f"+ {after_lines[j]}")
                j += 1
            elif i < len(before_lines):
                diff.append(f"- {before_lines[i]}")
                i += 1

        return "".join(diff)

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Get a snapshot by ID."""
        for snapshot in self._undo_stack:
            if snapshot.id == snapshot_id:
                return snapshot
        return None

    def restore(self, snapshot_id: str) -> bool:
        """Restore files to snapshot state."""
        snapshot = self.get_snapshot(snapshot_id)
        if not snapshot:
            return False

        for file_change in snapshot.files:
            file_path = self.cwd / file_change.path
            if file_change.before is None:
                if file_path.exists():
                    file_path.unlink()
            else:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_change.before)

        return True

    def undo(self) -> Optional[Snapshot]:
        """Undo last action."""
        if not self._undo_stack:
            return None

        snapshot = self._undo_stack.pop()
        self.restore(snapshot.id)
        self._redo_stack.append(snapshot)

        return snapshot

    def redo(self) -> Optional[Snapshot]:
        """Redo last undone action."""
        if not self._redo_stack:
            return None

        snapshot = self._redo_stack.pop()

        for file_change in snapshot.files:
            file_path = self.cwd / file_change.path
            if file_change.after is not None:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_change.after)

        self._undo_stack.append(snapshot)

        return snapshot

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def save_snapshot_to_git(self, snapshot: Snapshot) -> None:
        """Save snapshot metadata to git."""
        meta_path = self._snapshots_dir / f"{snapshot.id}.json"
        meta_path.write_text(json.dumps(snapshot.to_dict(), indent=2))

        subprocess.run(
            ["git", "add", str(meta_path.relative_to(self._snapshots_dir))],
            cwd=self._snapshots_dir,
            capture_output=True
        )

    def get_history(self, limit: int = 50) -> List[Snapshot]:
        """Get undo history."""
        return self._undo_stack[-limit:]

    def clear(self) -> None:
        """Clear all snapshots."""
        self._undo_stack.clear()
        self._redo_stack.clear()


def create_snapshot_manager(cwd: Path | str) -> SnapshotManager:
    """Factory function to create a snapshot manager."""
    return SnapshotManager(cwd)