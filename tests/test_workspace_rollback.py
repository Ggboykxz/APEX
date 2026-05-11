"""Tests for apex/workspace_rollback.py — WorkspaceRollback, TurnTracker with real git operations."""

import pytest
import tempfile
import subprocess
from pathlib import Path
from apex.workspace_rollback import WorkspaceRollback, TurnTracker


def _git_init(path):
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True)


def _git_commit(path, msg="init"):
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
    subprocess.run(["git", "commit", "-m", msg, "--allow-empty"], cwd=path, capture_output=True)


class TestWorkspaceRollback:
    @pytest.fixture
    def git_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _git_init(repo)
            _git_commit(repo, "initial")
            yield repo

    @pytest.fixture
    def rollback(self, git_repo):
        return WorkspaceRollback(cwd=git_repo)

    def test_init(self, rollback, git_repo):
        assert rollback.cwd == git_repo
        assert rollback.snapshots_dir == git_repo / ".apex" / "snapshots"

    def test_is_git_repo(self, rollback):
        assert rollback.is_git_repo() is True

    def test_is_not_git_repo(self, tmp_path):
        rb = WorkspaceRollback(cwd=tmp_path)
        assert rb.is_git_repo() is False

    def test_create_snapshot(self, rollback):
        name = rollback.create_snapshot("test")
        assert name.startswith("snapshot_")
        assert "test" in name

    def test_create_snapshot_auto(self, rollback):
        name = rollback.create_snapshot()
        assert name.startswith("snapshot_")
        assert "auto" in name

    def test_list_snapshots_empty(self, rollback):
        snapshots = rollback.list_snapshots()
        assert snapshots == []

    def test_list_snapshots(self, rollback):
        rollback.create_snapshot("first")
        rollback.create_snapshot("second")
        snapshots = rollback.list_snapshots()
        assert len(snapshots) == 2

    def test_restore_snapshot(self, rollback, git_repo):
        # Create a file, snapshot it, then restore
        (git_repo / "test.txt").write_text("original")
        _git_commit(git_repo, "add test.txt")

        name = rollback.create_snapshot("before_change")

        # The restore should succeed even if no files were changed in snapshot
        result = rollback.restore_snapshot(name)
        assert result is True

    def test_restore_nonexistent(self, rollback):
        result = rollback.restore_snapshot("nonexistent_snapshot")
        assert result is False

    def test_delete_snapshot(self, rollback):
        name = rollback.create_snapshot("to_delete")
        result = rollback.delete_snapshot(name)
        assert result is True
        assert rollback.list_snapshots() == []

    def test_delete_nonexistent(self, rollback):
        result = rollback.delete_snapshot("nonexistent")
        assert result is False

    def test_rollback_turn(self, rollback):
        rollback.create_snapshot("turn1")
        rollback.create_snapshot("turn2")
        result = rollback.rollback_turn(1)
        assert result is True

    def test_rollback_turn_no_snapshots(self, rollback):
        result = rollback.rollback_turn()
        assert result is False

    def test_rollback_turn_all(self, rollback):
        rollback.create_snapshot("turn1")
        rollback.create_snapshot("turn2")
        # Rollback 2 turns ago -> go to first snapshot
        result = rollback.rollback_turn(2)
        assert result is True

    def test_snapshot_metadata(self, rollback, git_repo):
        name = rollback.create_snapshot("labeled")
        snapshots = rollback.list_snapshots()
        matching = [s for s in snapshots if s["name"] == name]
        assert len(matching) == 1
        assert matching[0]["label"] == "labeled"

    def test_snapshot_with_changed_files(self, git_repo):
        rb = WorkspaceRollback(cwd=git_repo)
        # Create a file and make it modified
        (git_repo / "newfile.py").write_text("print('hello')")
        # Don't commit - file is untracked/modified
        rb.create_snapshot("with_changes")
        snapshots = rb.list_snapshots()
        assert len(snapshots) == 1


class TestTurnTracker:
    @pytest.fixture
    def git_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _git_init(repo)
            _git_commit(repo, "initial")
            yield repo

    @pytest.fixture
    def tracker(self, git_repo):
        return TurnTracker(cwd=git_repo)

    def test_init(self, tracker, git_repo):
        assert tracker.cwd == git_repo
        assert tracker.turns == []

    def test_record_turn(self, tracker):
        snapshot_name = tracker.record_turn({"query": "test", "response": "ok"})
        assert snapshot_name.startswith("snapshot_")
        assert len(tracker.turns) == 1
        assert tracker.turns[0]["turn_number"] == 1

    def test_record_multiple_turns(self, tracker):
        tracker.record_turn({"query": "q1"})
        tracker.record_turn({"query": "q2"})
        tracker.record_turn({"query": "q3"})
        assert len(tracker.turns) == 3
        assert tracker.turns[2]["turn_number"] == 3

    def test_revert_turn(self, tracker):
        tracker.record_turn({"query": "q1"})
        tracker.record_turn({"query": "q2"})
        result = tracker.revert_turn(1)
        assert result is True

    def test_revert_turn_no_turns(self, tracker):
        result = tracker.revert_turn()
        assert result is False

    def test_get_turn_history(self, tracker):
        tracker.record_turn({"query": "q1"})
        tracker.record_turn({"query": "q2"})
        history = tracker.get_turn_history()
        assert len(history) == 2

    def test_turn_persistence(self, git_repo):
        # Create tracker and record
        t1 = TurnTracker(cwd=git_repo)
        t1.record_turn({"query": "persist_test"})

        # Create new tracker
        t2 = TurnTracker(cwd=git_repo)
        assert len(t2.turns) == 1
        assert t2.turns[0]["data"]["query"] == "persist_test"
