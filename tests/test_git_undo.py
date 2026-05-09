"""Tests for git_undo module."""

import pytest
import tempfile
from pathlib import Path
from apex.git_undo import UndoSnapshot, GitUndoManager


class TestUndoSnapshot:
    """Test UndoSnapshot dataclass."""

    def test_init(self):
        """Test snapshot initialization."""
        snapshot = UndoSnapshot(
            id="undo_001",
            timestamp="2024-01-01T00:00:00",
            description="Test snapshot",
            changed_files=["file1.py", "file2.py"],
            git_commit="abc123",
            parent_commit="def456"
        )
        assert snapshot.id == "undo_001"
        assert snapshot.description == "Test snapshot"
        assert len(snapshot.changed_files) == 2


class TestGitUndoManager:
    """Test GitUndoManager class."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_cwd):
        """Create GitUndoManager instance."""
        return GitUndoManager(cwd=temp_cwd)

    def test_init(self, manager, temp_cwd):
        """Test initialization."""
        assert manager.cwd == temp_cwd
        assert manager.snapshots == []
        assert manager.current_index == -1

    def test_can_undo_false_initially(self, manager):
        """Test can_undo when no snapshots."""
        assert manager.can_undo() is False

    def test_can_redo_false_initially(self, manager):
        """Test can_redo when no snapshots."""
        assert manager.can_redo() is False

    def test_get_history_empty(self, manager):
        """Test get_history when empty."""
        history = manager.get_history()
        assert history == []

    def test_clear_history(self, manager):
        """Test clear_history method."""
        manager.create_snapshot("test")
        manager.clear_history()
        assert manager.snapshots == []
        assert manager.current_index == -1

    @pytest.mark.skipif(not hasattr(Path, 'is_dir'), reason="Requires git")
    def test_create_snapshot(self, manager):
        """Test create_snapshot method."""
        snapshot_id = manager.create_snapshot("test description")
        assert snapshot_id.startswith("undo_")

    @pytest.mark.skipif(not hasattr(Path, 'is_dir'), reason="Requires git")
    def test_undo_with_snapshots(self, manager):
        """Test undo with snapshots."""
        manager.create_snapshot("first")
        manager.create_snapshot("second")

        result = manager.undo(1)
        assert result is not None
        assert manager.current_index >= 0

    @pytest.mark.skipif(not hasattr(Path, 'is_dir'), reason="Requires git")
    def test_redo_with_snapshots(self, manager):
        """Test redo with snapshots."""
        manager.create_snapshot("first")
        manager.create_snapshot("second")
        manager.undo(1)

        result = manager.redo(1)
        assert result is not None

    @pytest.mark.skipif(not hasattr(Path, 'is_dir'), reason="Requires git")
    def test_undo_multiple_steps(self, manager):
        """Test undo with multiple steps."""
        for i in range(3):
            manager.create_snapshot(f"snapshot{i}")

        result = manager.undo(2)
        assert result is not None

    @pytest.mark.skipif(not hasattr(Path, 'is_dir'), reason="Requires git")
    def test_redo_multiple_steps(self, manager):
        """Test redo with multiple steps."""
        for i in range(3):
            manager.create_snapshot(f"snapshot{i}")
        manager.undo(2)

        result = manager.redo(2)
        assert result is not None

    @pytest.mark.skipif(not hasattr(Path, 'is_dir'), reason="Requires git")
    def test_get_history_with_snapshots(self, manager):
        """Test get_history with snapshots."""
        manager.create_snapshot("first")
        manager.create_snapshot("second")

        history = manager.get_history()
        assert len(history) == 2
        assert history[0]["description"] == "first"
        assert history[1]["description"] == "second"