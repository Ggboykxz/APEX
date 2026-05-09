"""Git-based undo/redo system for workspace changes."""

import subprocess
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class UndoSnapshot:
    """Represents a snapshot for undo/redo."""
    id: str
    timestamp: str
    description: str
    changed_files: list[str]
    git_commit: Optional[str]
    parent_commit: Optional[str]


class GitUndoManager:
    """Git-based undo/redo with precise snapshots."""

    def __init__(self, cwd: Path | None = None):
        self.cwd = cwd or Path.cwd()
        self.snapshots: list[UndoSnapshot] = []
        self.current_index = -1
        self._undo_dir = self.cwd / ".apex" / "undo"
        self._undo_dir.mkdir(parents=True, exist_ok=True)
        self._load_history()

    def _run_git(self, *args) -> tuple[int, str, str]:
        """Run git command."""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=self.cwd,
                capture_output=True,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            return -1, "", "git not found"

    def _load_history(self):
        """Load undo history from disk."""
        history_file = self._undo_dir / "history.json"
        if history_file.exists():
            try:
                with open(history_file) as f:
                    data = json.load(f)
                    self.snapshots = [UndoSnapshot(**s) for s in data.get("snapshots", [])]
                    self.current_index = data.get("current_index", -1)
            except:
                pass

    def _save_history(self):
        """Save undo history to disk."""
        history_file = self._undo_dir / "history.json"
        with open(history_file, "w") as f:
            json.dump({
                "snapshots": [asdict(s) for s in self.snapshots],
                "current_index": self.current_index
            }, f, indent=2)

    def _get_current_files(self) -> list[str]:
        """Get list of current tracked files."""
        code, stdout, _ = self._run_git("ls-files")
        if code != 0:
            return []
        return [f for f in stdout.strip().split("\n") if f]

    def create_snapshot(self, description: str = "") -> str:
        """Create a snapshot before changes."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        snapshot_id = f"undo_{timestamp}"

        code, stdout, _ = self._run_git("rev-parse", "HEAD")
        parent_commit = stdout.strip() if code == 0 else None

        changed_files = self._get_current_files()

        code, _, _ = self._run_git("add", ".")
        if code == 0:
            code, stdout, _ = self._run_git("commit", "-m", f"APEX: {description or 'snapshot'}")

            if code == 0:
                code, commit, _ = self._run_git("rev-parse", "HEAD")
                git_commit = commit.strip() if code == 0 else parent_commit
            else:
                git_commit = parent_commit
        else:
            git_commit = parent_commit

        snapshot = UndoSnapshot(
            id=snapshot_id,
            timestamp=datetime.now().isoformat(),
            description=description or f"Auto-snapshot at {timestamp}",
            changed_files=changed_files,
            git_commit=git_commit,
            parent_commit=parent_commit
        )

        if self.current_index < len(self.snapshots) - 1:
            self.snapshots = self.snapshots[:self.current_index + 1]

        self.snapshots.append(snapshot)
        self.current_index = len(self.snapshots) - 1
        self._save_history()

        return snapshot_id

    def undo(self, steps: int = 1) -> Optional[str]:
        """Undo changes by reverting to previous snapshot."""
        if not self.snapshots or self.current_index < 0:
            return None

        target_index = max(0, self.current_index - steps)
        target_snapshot = self.snapshots[target_index]

        if target_snapshot.git_commit:
            self._run_git("checkout", target_snapshot.git_commit)

        self.current_index = target_index
        self._save_history()

        return target_snapshot.id

    def redo(self, steps: int = 1) -> Optional[str]:
        """Redo previously undone changes."""
        if not self.snapshots or self.current_index >= len(self.snapshots) - 1:
            return None

        target_index = min(len(self.snapshots) - 1, self.current_index + steps)
        target_snapshot = self.snapshots[target_index]

        if target_snapshot.git_commit:
            self._run_git("checkout", target_snapshot.git_commit)

        self.current_index = target_index
        self._save_history()

        return target_snapshot.id

    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return self.current_index > 0

    def can_redo(self) -> bool:
        """Check if redo is possible."""
        return self.current_index < len(self.snapshots) - 1

    def get_history(self) -> list[dict]:
        """Get undo/redo history."""
        return [
            {
                "index": i,
                "id": s.id,
                "timestamp": s.timestamp,
                "description": s.description,
                "is_current": i == self.current_index
            }
            for i, s in enumerate(self.snapshots)
        ]

    def clear_history(self):
        """Clear undo history."""
        self.snapshots.clear()
        self.current_index = -1
        self._save_history()