"""Tests for workspace_rollback module."""

import pytest
import tempfile
from pathlib import Path
from apex.workspace_rollback import WorkspaceRollback, TurnTracker


class TestWorkspaceRollback:
    """Test WorkspaceRollback class."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def rollback(self, temp_cwd):
        """Create WorkspaceRollback instance."""
        return WorkspaceRollback(cwd=temp_cwd)

    def test_init(self, rollback, temp_cwd):
        """Test initialization."""
        assert rollback.cwd == temp_cwd
        assert rollback.snapshots_dir.exists()

    def test_is_git_repo_not_git(self, rollback):
        """Test is_git_repo when not a git repo."""
        assert rollback.is_git_repo() is False

    @pytest.mark.skipif(not hasattr(Path, "is_dir"), reason="Requires git")
    def test_create_snapshot(self, rollback):
        """Test create_snapshot method."""
        snapshot_name = rollback.create_snapshot("test snapshot")
        assert snapshot_name.startswith("snapshot_")

    def test_list_snapshots_empty(self, rollback):
        """Test list_snapshots when empty."""
        snapshots = rollback.list_snapshots()
        assert snapshots == []

    @pytest.mark.skipif(not hasattr(Path, "is_dir"), reason="Requires git")
    def test_list_snapshots_with_data(self, rollback):
        """Test list_snapshots with snapshots."""
        rollback.create_snapshot("test")
        snapshots = rollback.list_snapshots()
        assert len(snapshots) >= 1

    def test_restore_snapshot_not_found(self, rollback):
        """Test restore with non-existent snapshot."""
        result = rollback.restore_snapshot("nonexistent")
        assert result is False

    def test_delete_snapshot_not_found(self, rollback):
        """Test delete non-existent snapshot."""
        result = rollback.delete_snapshot("nonexistent")
        assert result is False


class TestTurnTracker:
    """Test TurnTracker class."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def tracker(self, temp_cwd):
        """Create TurnTracker instance."""
        return TurnTracker(cwd=temp_cwd)

    def test_init(self, tracker):
        """Test initialization."""
        assert tracker.turns == []
        assert tracker.rollback is not None

    def test_record_turn(self, tracker):
        """Test record_turn method."""
        snapshot = tracker.record_turn({"action": "test"})
        assert snapshot.startswith("snapshot_")
        assert len(tracker.turns) == 1

    def test_revert_turn_no_turns(self, tracker):
        """Test revert with no turns."""
        result = tracker.revert_turn(1)
        assert result is False

    def test_get_turn_history_empty(self, tracker):
        """Test get_turn_history when empty."""
        history = tracker.get_turn_history()
        assert history == []

    def test_get_turn_history_with_data(self, tracker):
        """Test get_turn_history with data."""
        tracker.record_turn({"action": "test"})
        history = tracker.get_turn_history()
        assert len(history) == 1
