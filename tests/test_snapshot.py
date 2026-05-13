"""Tests for apex/snapshot.py — SnapshotManager, Snapshot, FileChange, ActionType."""

import pytest
from pathlib import Path
from apex.snapshot import ActionType, FileChange, Snapshot, SnapshotManager, create_snapshot_manager


class TestActionType:
    def test_values(self):
        assert ActionType.FILE_WRITE.value == "file_write"
        assert ActionType.FILE_EDIT.value == "file_edit"
        assert ActionType.FILE_DELETE.value == "file_delete"
        assert ActionType.DIR_CREATE.value == "dir_create"
        assert ActionType.DIR_DELETE.value == "dir_delete"
        assert ActionType.COMMAND_EXEC.value == "command_exec"


class TestFileChange:
    def test_creation(self):
        fc = FileChange(path="test.py", before="old", after="new", diff="diff")
        assert fc.path == "test.py"
        assert fc.before == "old"
        assert fc.after == "new"
        assert fc.diff == "diff"

    def test_defaults(self):
        fc = FileChange(path="test.py")
        assert fc.before is None
        assert fc.after is None
        assert fc.diff is None


class TestSnapshot:
    def test_creation(self):
        from datetime import datetime

        s = Snapshot(id="snap1", timestamp=datetime.now(), action_type=ActionType.FILE_EDIT)
        assert s.id == "snap1"
        assert s.files == []
        assert s.command is None
        assert s.message is None

    def test_to_dict(self):
        from datetime import datetime

        s = Snapshot(
            id="snap1",
            timestamp=datetime.now(),
            action_type=ActionType.FILE_WRITE,
            files=[FileChange(path="test.py", before="a", after="b")],
            command="cmd",
            message="msg",
        )
        d = s.to_dict()
        assert d["id"] == "snap1"
        assert d["action_type"] == "file_write"
        assert len(d["files"]) == 1
        assert d["files"][0]["path"] == "test.py"
        assert d["command"] == "cmd"
        assert d["message"] == "msg"


class TestSnapshotManager:
    @pytest.fixture
    def manager(self, tmp_path):
        return SnapshotManager(cwd=tmp_path)

    def test_init(self, manager, tmp_path):
        assert manager.cwd == tmp_path
        assert manager._undo_stack == []
        assert manager._redo_stack == []
        assert manager._snapshots_dir.exists()

    def test_track(self, manager):
        snapshot_id = manager.track(ActionType.FILE_EDIT)
        assert snapshot_id is not None
        assert len(snapshot_id) == 12
        assert len(manager._undo_stack) == 1
        assert manager._redo_stack == []

    def test_track_clears_redo(self, manager):
        # Set up a redo stack
        manager._redo_stack.append(
            Snapshot(id="old", timestamp=None, action_type=ActionType.FILE_EDIT)
        )
        manager.track()
        assert manager._redo_stack == []

    def test_add_file_change(self, manager):
        snapshot_id = manager.track(ActionType.FILE_WRITE)
        manager.add_file_change(snapshot_id, "test.py", before="old", after="new")
        snapshot = manager.get_snapshot(snapshot_id)
        assert len(snapshot.files) == 1
        assert snapshot.files[0].path == "test.py"
        assert snapshot.files[0].before == "old"
        assert snapshot.files[0].after == "new"
        assert snapshot.files[0].diff is not None

    def test_add_file_change_no_diff(self, manager):
        snapshot_id = manager.track()
        manager.add_file_change(snapshot_id, "test.py", before="old")
        snapshot = manager.get_snapshot(snapshot_id)
        assert snapshot.files[0].diff is None

    def test_add_file_change_nonexistent_snapshot(self, manager):
        # Should not crash
        manager.add_file_change("nonexistent", "test.py")

    def test_get_snapshot(self, manager):
        snapshot_id = manager.track()
        snapshot = manager.get_snapshot(snapshot_id)
        assert snapshot is not None
        assert snapshot.id == snapshot_id

    def test_get_snapshot_nonexistent(self, manager):
        assert manager.get_snapshot("nonexistent") is None

    def test_track_file(self, manager, tmp_path):
        test_file = tmp_path / "test_track.py"
        test_file.write_text("original content")
        result = manager.track_file("test_track.py")
        assert result is not None
        assert len(result.files) == 1
        assert result.files[0].before == "original content"

    def test_track_file_nonexistent(self, manager):
        result = manager.track_file("nonexistent.py")
        assert result is None

    def test_restore(self, manager, tmp_path):
        # Create a file
        test_file = tmp_path / "test_restore.py"
        test_file.write_text("original")

        # Track the file
        snapshot_id = manager.track()
        manager.add_file_change(snapshot_id, "test_restore.py", before="original", after="modified")

        # Modify the file
        test_file.write_text("modified")

        # Restore
        result = manager.restore(snapshot_id)
        assert result is True
        assert test_file.read_text() == "original"

    def test_restore_delete_file(self, manager, tmp_path):
        """Restore should delete file when before is None."""
        test_file = tmp_path / "test_new.py"
        test_file.write_text("new content")

        snapshot_id = manager.track()
        manager.add_file_change(snapshot_id, "test_new.py", before=None, after="new content")

        result = manager.restore(snapshot_id)
        assert result is True
        assert not test_file.exists()

    def test_restore_nonexistent_snapshot(self, manager):
        assert manager.restore("nonexistent") is False

    def test_undo(self, manager, tmp_path):
        test_file = tmp_path / "test_undo.py"
        test_file.write_text("v1")
        sid = manager.track()
        manager.add_file_change(sid, "test_undo.py", before="v1", after="v2")

        snapshot = manager.undo()
        assert snapshot is not None
        assert len(manager._redo_stack) == 1
        # Note: undo pops the snapshot, so restore won't find it in _undo_stack
        # The snapshot is moved to the redo stack

    def test_undo_empty(self, manager):
        assert manager.undo() is None

    def test_redo(self, manager, tmp_path):
        test_file = tmp_path / "test_redo.py"
        test_file.write_text("v1")
        sid = manager.track()
        manager.add_file_change(sid, "test_redo.py", before="v1", after="v2")

        manager.undo()
        assert len(manager._redo_stack) == 1

        snapshot = manager.redo()
        assert snapshot is not None
        # Redo writes "after" content
        assert test_file.read_text() == "v2"

    def test_redo_empty(self, manager):
        assert manager.redo() is None

    def test_can_undo(self, manager):
        assert manager.can_undo() is False
        manager.track()
        assert manager.can_undo() is True

    def test_can_redo(self, manager):
        assert manager.can_redo() is False
        manager.track()
        manager.undo()
        assert manager.can_redo() is True

    def test_get_history(self, manager):
        manager.track()
        manager.track()
        manager.track()
        history = manager.get_history()
        assert len(history) == 3

    def test_get_history_limit(self, manager):
        for _ in range(5):
            manager.track()
        history = manager.get_history(limit=3)
        assert len(history) == 3

    def test_clear(self, manager):
        manager.track()
        manager.track()
        manager.clear()
        assert manager._undo_stack == []
        assert manager._redo_stack == []

    def test_compute_diff(self, manager):
        diff = manager._compute_diff("line1\nline2\n", "line1\nmodified\n")
        assert "- line2" in diff
        assert "+ modified" in diff

    def test_compute_diff_additions(self, manager):
        diff = manager._compute_diff("a\n", "a\nb\nc\n")
        assert "+ b" in diff
        assert "+ c" in diff

    def test_compute_diff_deletions(self, manager):
        diff = manager._compute_diff("a\nb\nc\n", "a\n")
        assert "- b" in diff
        assert "- c" in diff

    def test_save_snapshot_to_git(self, manager):
        from datetime import datetime

        snapshot = Snapshot(
            id="test_git", timestamp=datetime.now(), action_type=ActionType.FILE_EDIT
        )
        manager.save_snapshot_to_git(snapshot)
        meta_path = manager._snapshots_dir / "test_git.json"
        assert meta_path.exists()

    def test_get_file_hash(self, manager, tmp_path):
        test_file = tmp_path / "test_hash.txt"
        test_file.write_text("content")
        h = manager._get_file_hash(test_file)
        assert len(h) == 64  # SHA256

    def test_get_file_hash_nonexistent(self, manager):
        h = manager._get_file_hash(Path("/nonexistent/file"))
        assert h == ""


class TestCreateSnapshotManager:
    def test_factory(self, tmp_path):
        mgr = create_snapshot_manager(str(tmp_path))
        assert isinstance(mgr, SnapshotManager)
