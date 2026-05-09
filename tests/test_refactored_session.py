"""Tests for refactored session module."""

import json
from pathlib import Path
from unittest.mock import MagicMock
from datetime import datetime

from apex.refactored_session import (
    UndoManager, SessionManager,
    create_undo_manager, create_session_manager
)


class TestUndoManager:
    def test_init_default(self):
        manager = UndoManager()
        assert manager.max_history == 50
        assert manager.undo_count == 0
        assert manager.redo_count == 0

    def test_init_custom_max(self):
        manager = UndoManager(max_history=10)
        assert manager.max_history == 10

    def test_snapshot(self):
        manager = UndoManager()
        manager.snapshot("edit_file", {"path": "/test.py"})
        
        assert manager.undo_count == 1
        assert manager.can_undo() is True

    def test_snapshot_multiple(self):
        manager = UndoManager()
        manager.snapshot("action1", {"data": "a"})
        manager.snapshot("action2", {"data": "b"})
        
        assert manager.undo_count == 2
        assert manager.can_redo() is False

    def test_snapshot_clears_redo(self):
        manager = UndoManager()
        manager.snapshot("action1", {})
        manager.undo()
        manager.snapshot("action2", {})
        
        assert manager.redo_count == 0

    def test_undo(self):
        manager = UndoManager()
        manager.snapshot("edit_file", {"path": "/test.py"})
        
        action = manager.undo()
        
        assert action is not None
        assert action["type"] == "edit_file"
        assert manager.redo_count == 1

    def test_undo_empty_stack(self):
        manager = UndoManager()
        action = manager.undo()
        
        assert action is None

    def test_redo(self):
        manager = UndoManager()
        manager.snapshot("action", {})
        manager.undo()
        
        action = manager.redo()
        
        assert action is not None
        assert action["type"] == "action"

    def test_redo_empty_stack(self):
        manager = UndoManager()
        action = manager.redo()
        
        assert action is None

    def test_can_undo(self):
        manager = UndoManager()
        assert manager.can_undo() is False
        
        manager.snapshot("action", {})
        assert manager.can_undo() is True

    def test_can_redo(self):
        manager = UndoManager()
        assert manager.can_redo() is False
        
        manager.snapshot("action", {})
        manager.undo()
        assert manager.can_redo() is True

    def test_get_undo_description(self):
        manager = UndoManager()
        manager.snapshot("edit_file", {})
        
        desc = manager.get_undo_description()
        
        assert desc == "edit_file"

    def test_get_undo_description_empty(self):
        manager = UndoManager()
        desc = manager.get_undo_description()
        
        assert desc == ""

    def test_get_redo_description(self):
        manager = UndoManager()
        manager.snapshot("action", {})
        manager.undo()
        
        desc = manager.get_redo_description()
        
        assert desc == "action"

    def test_clear(self):
        manager = UndoManager()
        manager.snapshot("action", {})
        manager.clear()
        
        assert manager.undo_count == 0
        assert manager.redo_count == 0

    def test_max_history(self):
        manager = UndoManager(max_history=3)
        for i in range(5):
            manager.snapshot(f"action{i}", {})
        
        assert manager.undo_count == 3

    def test_with_time_factory(self):
        time_factory = lambda: "2024-01-01T00:00:00"
        manager = UndoManager(time_factory=time_factory)
        manager.snapshot("action", {})
        
        assert manager._undo_stack[0]["timestamp"] == "2024-01-01T00:00:00"


class TestSessionManager:
    def test_init_default(self, tmp_path):
        manager = SessionManager(sessions_dir=tmp_path)
        assert manager._sessions_dir == tmp_path

    def test_init_creates_directory(self, tmp_path):
        manager = SessionManager(sessions_dir=tmp_path / "new_sessions")
        assert (tmp_path / "new_sessions").exists()

    def test_save(self, tmp_path):
        manager = SessionManager(sessions_dir=tmp_path, time_factory=lambda: datetime(2024, 1, 1, 12, 0, 0))
        
        mock_agent = MagicMock()
        mock_agent.model = "gpt-4"
        mock_agent.cwd = Path("/workspace")
        mock_agent.history = ["msg1", "msg2"]
        mock_agent.usage = {"tokens": 1000}
        
        filepath = manager.save(mock_agent, "test_session")
        
        assert filepath.exists()
        assert "20240101" in filepath.name
        assert "test_session" in filepath.name

    def test_save_creates_latest_link(self, tmp_path):
        manager = SessionManager(sessions_dir=tmp_path, time_factory=lambda: datetime(2024, 1, 1, 12, 0, 0))
        
        mock_agent = MagicMock()
        mock_agent.model = "gpt-4"
        mock_agent.cwd = Path("/workspace")
        mock_agent.history = []
        mock_agent.usage = {}
        
        manager.save(mock_agent, "test")
        
        latest_link = tmp_path / "latest_test.json"
        assert latest_link.exists()
        assert latest_link.is_symlink()

    def test_load_not_found(self, tmp_path):
        manager = SessionManager(sessions_dir=tmp_path)
        mock_agent = MagicMock()
        
        result = manager.load("nonexistent", mock_agent)
        
        assert result is False

    def test_load_success(self, tmp_path):
        session_file = tmp_path / "20240101_120000_test.json"
        session_file.write_text(json.dumps({
            "name": "test",
            "timestamp": "2024-01-01T12:00:00",
            "model": "gpt-4",
            "cwd": "/workspace",
            "history": ["msg1"],
            "usage": {}
        }))
        
        manager = SessionManager(sessions_dir=tmp_path)
        mock_agent = MagicMock()
        
        result = manager.load("test", mock_agent)
        
        assert result is True

    def test_list_sessions(self, tmp_path):
        (tmp_path / "20240101_test1.json").write_text(json.dumps({
            "name": "session1",
            "timestamp": "2024-01-01T12:00:00",
            "model": "gpt-4",
            "history": [1, 2, 3]
        }))
        (tmp_path / "20240102_test2.json").write_text(json.dumps({
            "name": "session2",
            "timestamp": "2024-01-02T12:00:00",
            "model": "claude",
            "history": [1]
        }))
        
        manager = SessionManager(sessions_dir=tmp_path)
        sessions = manager.list_sessions()
        
        assert len(sessions) == 2
        assert sessions[0]["name"] == "session2"
        assert sessions[1]["name"] == "session1"

    def test_share(self, tmp_path):
        manager = SessionManager(sessions_dir=tmp_path, time_factory=lambda: datetime(2024, 1, 1, 12, 0, 0))
        
        mock_agent = MagicMock()
        mock_agent.model = "gpt-4"
        mock_agent.cwd = Path("/workspace")
        mock_agent.history = []
        mock_agent.usage = {}
        
        share_url = manager.share(mock_agent, "test")
        
        assert share_url.startswith("apex://share/")
        assert (tmp_path / "shared").exists()

    def test_load_shared_not_found(self, tmp_path):
        manager = SessionManager(sessions_dir=tmp_path)
        mock_agent = MagicMock()
        
        result = manager.load_shared("nonexistent_id", mock_agent)
        
        assert result is False

    def test_load_shared_success(self, tmp_path):
        shared_dir = tmp_path / "shared"
        shared_dir.mkdir()
        
        import base64
        session_data = {"model": "gpt-4", "cwd": "/workspace", "history": []}
        json_str = json.dumps(session_data)
        compressed = base64.b64encode(json_str.encode()).decode()
        
        (shared_dir / "abc12345.json").write_text(json.dumps({"data": compressed}))
        
        manager = SessionManager(sessions_dir=tmp_path)
        mock_agent = MagicMock()
        
        result = manager.load_shared("abc12345", mock_agent)
        
        assert result is True


class TestFactoryFunctions:
    def test_create_undo_manager(self):
        manager = create_undo_manager()
        assert isinstance(manager, UndoManager)

    def test_create_undo_manager_with_params(self):
        manager = create_undo_manager(max_history=20)
        assert manager.max_history == 20

    def test_create_session_manager(self, tmp_path):
        manager = create_session_manager(tmp_path)
        assert isinstance(manager, SessionManager)

    def test_create_session_manager_default(self):
        manager = create_session_manager()
        assert isinstance(manager, SessionManager)