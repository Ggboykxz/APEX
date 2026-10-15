"""Workspace rollback system - side-git snapshots with /restore support."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from datetime import datetime


class WorkspaceRollback:
    """Side-git based workspace rollback with restore support."""

    def __init__(self, cwd: Path | None = None):
        self.cwd = cwd or Path.cwd()
        self.snapshots_dir = self.cwd / ".apex" / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def _run_git(self, *args) -> tuple[int, str, str]:
        """Run git command."""
        try:
            result = subprocess.run(
                ["git"] + list(args), cwd=self.cwd, capture_output=True, text=True
            )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            return -1, "", "git not found"

    def is_git_repo(self) -> bool:
        """Check if directory is a git repository."""
        code, _, _ = self._run_git("rev-parse", "--git-dir")
        return code == 0

    def create_snapshot(self, label: str = "") -> str:
        """Create a snapshot of the current workspace state."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"snapshot_{timestamp}_{label or 'auto'}"
        snapshot_path = self.snapshots_dir / snapshot_name

        snapshot_path.mkdir(parents=True, exist_ok=False)

        metadata = {
            "timestamp": timestamp,
            "label": label,
            "created_at": datetime.now().isoformat(),
        }

        with open(snapshot_path / "metadata.json", "w") as f:
            json.dump(metadata, f)

        if self.is_git_repo():
            code, stdout, stderr = self._run_git("diff", "--name-only")
            if code == 0 and stdout.strip():
                with open(snapshot_path / "changed_files.txt", "w") as f:
                    f.write(stdout)

                for file in stdout.strip().split("\n"):
                    if file:
                        src = self.cwd / file
                        if src.exists():
                            dst = snapshot_path / "files" / file
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src, dst)

            code, stdout, _ = self._run_git("status", "--porcelain")
            if code == 0:
                with open(snapshot_path / "git_status.txt", "w") as f:
                    f.write(stdout)

        return snapshot_name

    def restore_snapshot(self, snapshot_name: str) -> bool:
        """Restore workspace to a previous snapshot."""
        snapshot_path = self.snapshots_dir / snapshot_name

        if not snapshot_path.exists():
            return False

        files_dir = snapshot_path / "files"
        if files_dir.exists():
            for file in files_dir.rglob("*"):
                if file.is_file():
                    rel_path = file.relative_to(files_dir)
                    dst = self.cwd / rel_path
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file, dst)

        return True

    def list_snapshots(self) -> list[dict[str, Any]]:
        """List all available snapshots."""
        snapshots = []

        if not self.snapshots_dir.exists():
            return snapshots

        for snapshot_path in sorted(self.snapshots_dir.iterdir()):
            if not snapshot_path.is_dir():
                continue

            metadata_file = snapshot_path / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
            else:
                metadata = {}

            snapshots.append(
                {
                    "name": snapshot_path.name,
                    "created_at": metadata.get("created_at", "unknown"),
                    "label": metadata.get("label", ""),
                }
            )

        return snapshots

    def delete_snapshot(self, snapshot_name: str) -> bool:
        """Delete a snapshot."""
        snapshot_path = self.snapshots_dir / snapshot_name

        if not snapshot_path.exists():
            return False

        shutil.rmtree(snapshot_path)
        return True

    def rollback_turn(self, turns_ago: int = 1) -> bool:
        """Rollback the workspace by a number of turns."""
        snapshots = self.list_snapshots()

        if not snapshots:
            return False

        target_idx = len(snapshots) - turns_ago
        if target_idx < 0:
            target_idx = 0

        return self.restore_snapshot(snapshots[target_idx]["name"])


class TurnTracker:
    """Track turns for workspace rollback."""

    def __init__(self, cwd: Path | None = None):
        self.cwd = cwd or Path.cwd()
        self.rollback = WorkspaceRollback(self.cwd)
        self.turn_file = self.cwd / ".apex" / "turns.json"
        self.turns = self._load_turns()

    def _load_turns(self) -> list[dict]:
        """Load turn history."""
        if self.turn_file.exists():
            with open(self.turn_file) as f:
                return json.load(f)
        return []

    def _save_turns(self):
        """Save turn history."""
        self.turn_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.turn_file, "w") as f:
            json.dump(self.turns, f, indent=2)

    def record_turn(self, turn_data: dict[str, Any]) -> str:
        """Record a new turn with snapshot."""
        snapshot_name = self.rollback.create_snapshot(f"turn_{len(self.turns) + 1}")

        turn_record = {
            "turn_number": len(self.turns) + 1,
            "snapshot": snapshot_name,
            "timestamp": datetime.now().isoformat(),
            "data": turn_data,
        }

        self.turns.append(turn_record)
        self._save_turns()

        return snapshot_name

    def revert_turn(self, turns_ago: int = 1) -> bool:
        """Revert a number of turns."""
        if not self.turns:
            return False

        target_turn = self.turns[-turns_ago] if turns_ago <= len(self.turns) else self.turns[0]

        return self.rollback.restore_snapshot(target_turn["snapshot"])

    def get_turn_history(self) -> list[dict]:
        """Get turn history."""
        return self.turns
