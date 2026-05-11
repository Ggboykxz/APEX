"""Tests for apex/git_undo.py — GitUndoManager with real git operations."""

import pytest
import tempfile
import subprocess
from pathlib import Path
from apex.git_undo import UndoSnapshot, GitUndoManager


def _git_init(path):
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True)


def _git_commit(path, msg="init"):
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
    subprocess.run(["git", "commit", "-m", msg, "--allow-empty"], cwd=path, capture_output=True)


class TestUndoSnapshot:
    def test_creation(self):
        s = UndoSnapshot(
            id="undo_001",
            timestamp="2024-01-01T00:00:00",
            description="Test snapshot",
            changed_files=["file1.py", "file2.py"],
            git_commit="abc123",
            parent_commit="def456",
        )
        assert s.id == "undo_001"
        assert s.description == "Test snapshot"
        assert len(s.changed_files) == 2
        assert s.git_commit == "abc123"
        assert s.parent_commit == "def456"

    def test_defaults(self):
        s = UndoSnapshot(
            id="u1",
            timestamp="t",
            description="d",
            changed_files=[],
            git_commit=None,
            parent_commit=None,
        )
        assert s.git_commit is None
        assert s.parent_commit is None


class TestGitUndoManager:
    @pytest.fixture
    def git_repo(self):
        """Create a temporary git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _git_init(repo)
            _git_commit(repo, "initial commit")
            yield repo

    @pytest.fixture
    def manager(self, git_repo):
        return GitUndoManager(cwd=git_repo)

    def test_init(self, manager, git_repo):
        assert manager.cwd == git_repo
        assert manager.snapshots == []
        assert manager.current_index == -1

    def test_can_undo_false_initially(self, manager):
        assert manager.can_undo() is False

    def test_can_redo_false_initially(self, manager):
        assert manager.can_redo() is False

    def test_get_history_empty(self, manager):
        assert manager.get_history() == []

    def test_create_snapshot(self, manager, git_repo):
        snapshot_id = manager.create_snapshot("test description")
        assert snapshot_id.startswith("undo_")
        assert len(manager.snapshots) == 1
        assert manager.current_index == 0

    def test_create_snapshot_auto_description(self, manager, git_repo):
        snapshot_id = manager.create_snapshot()
        assert snapshot_id.startswith("undo_")
        assert "Auto-snapshot" in manager.snapshots[0].description

    def test_undo_no_snapshots(self, manager):
        result = manager.undo()
        assert result is None

    def test_can_undo_after_snapshot(self, manager, git_repo):
        manager.create_snapshot("first")
        assert manager.can_undo() is False  # Only 1 snapshot, current_index = 0
        manager.create_snapshot("second")
        assert manager.can_undo() is True  # current_index = 1

    def test_undo_with_snapshots(self, manager, git_repo):
        manager.create_snapshot("first")
        # Add a file and commit
        (git_repo / "test.py").write_text("print('hello')")
        _git_commit(git_repo, "add test.py")
        manager.create_snapshot("second")

        assert manager.can_undo() is True
        result = manager.undo(1)
        assert result is not None
        assert manager.current_index == 0

    def test_redo_after_undo(self, manager, git_repo):
        manager.create_snapshot("first")
        manager.create_snapshot("second")
        manager.undo(1)
        assert manager.can_redo() is True

        result = manager.redo(1)
        assert result is not None
        assert manager.current_index == 1

    def test_redo_no_snapshots(self, manager):
        result = manager.redo()
        assert result is None

    def test_can_redo_after_undo(self, manager, git_repo):
        manager.create_snapshot("first")
        manager.create_snapshot("second")
        manager.undo(1)
        assert manager.can_redo() is True

    def test_undo_multiple_steps(self, manager, git_repo):
        for i in range(4):
            manager.create_snapshot(f"snapshot{i}")

        result = manager.undo(2)
        assert result is not None
        assert manager.current_index == 1

    def test_redo_multiple_steps(self, manager, git_repo):
        for i in range(4):
            manager.create_snapshot(f"snapshot{i}")
        manager.undo(2)

        result = manager.redo(2)
        assert result is not None
        assert manager.current_index == 3

    def test_get_history_with_snapshots(self, manager, git_repo):
        manager.create_snapshot("first")
        manager.create_snapshot("second")

        history = manager.get_history()
        assert len(history) == 2
        assert history[0]["description"] == "first"
        assert history[1]["description"] == "second"
        assert history[0]["is_current"] is False
        assert history[1]["is_current"] is True

    def test_clear_history(self, manager, git_repo):
        manager.create_snapshot("test")
        manager.clear_history()
        assert manager.snapshots == []
        assert manager.current_index == -1

    def test_history_persistence(self, git_repo):
        """Test that history is saved and loaded correctly."""
        manager1 = GitUndoManager(cwd=git_repo)
        manager1.create_snapshot("persistent")
        manager1.clear_history()
        manager1.create_snapshot("test1")
        manager1.create_snapshot("test2")

        # Create a new manager from the same repo
        manager2 = GitUndoManager(cwd=git_repo)
        assert len(manager2.snapshots) == 2
        assert manager2.current_index == 1

    def test_create_snapshot_truncates_future(self, manager, git_repo):
        """After undo, creating a new snapshot should truncate the redo stack."""
        manager.create_snapshot("first")
        manager.create_snapshot("second")
        manager.create_snapshot("third")
        manager.undo(1)  # back to "second"
        manager.create_snapshot("new")  # should truncate "third"
        assert len(manager.snapshots) == 3  # first, second, new
        assert manager.current_index == 2
        assert manager.can_redo() is False

    def test_undo_at_index_zero(self, manager, git_repo):
        manager.create_snapshot("only")
        result = manager.undo(1)
        assert result is not None  # Goes to index 0 (same position)
        assert manager.current_index == 0

    def test_run_git_no_git(self):
        """Test _run_git in a non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = GitUndoManager(cwd=Path(tmpdir))
            # Should handle gracefully
            code, stdout, stderr = mgr._run_git("status")
            assert code != 0  # Not a git repo

    def test_get_current_files(self, manager, git_repo):
        (git_repo / "file1.py").write_text("hello")
        (git_repo / "file2.py").write_text("world")
        _git_commit(git_repo, "add files")
        files = manager._get_current_files()
        assert "file1.py" in files
        assert "file2.py" in files
