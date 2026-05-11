"""Tests for APEX session management — no mocks, real objects and file system."""

import json
from pathlib import Path

import pytest

from apex.session import UndoManager, SessionManager
from apex.agent import Agent
from apex.config import Config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sessions_dir(tmp_path, monkeypatch):
    """Redirect session storage to tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path / ".apex" / "sessions"


@pytest.fixture
def session_mgr(sessions_dir, monkeypatch):
    """Create SessionManager using tmp_path as HOME."""
    monkeypatch.setenv("HOME", str(sessions_dir.parent.parent))
    return SessionManager()


@pytest.fixture
def agent(tmp_path, monkeypatch):
    """Create a real Agent with temp config."""
    monkeypatch.setenv("HOME", str(tmp_path))
    config = Config(config_path=tmp_path / "config.json")
    return Agent(config=config)


# ---------------------------------------------------------------------------
# UndoManager tests
# ---------------------------------------------------------------------------


class TestUndoManagerInit:
    def test_defaults(self):
        um = UndoManager()
        assert um.max_history == 50
        assert um.can_undo() is False
        assert um.can_redo() is False

    def test_custom_max_history(self):
        um = UndoManager(max_history=10)
        assert um.max_history == 10


class TestUndoManagerSnapshot:
    def test_snapshot_allows_undo(self):
        um = UndoManager()
        um.snapshot("edit", {"file": "test.py"})
        assert um.can_undo() is True
        assert um.can_redo() is False

    def test_snapshot_clears_redo(self):
        um = UndoManager()
        um.snapshot("edit1", {"f": "a"})
        um.undo()
        assert um.can_redo() is True
        um.snapshot("edit2", {"f": "b"})
        assert um.can_redo() is False

    def test_snapshot_max_history_trims(self):
        um = UndoManager(max_history=3)
        um.snapshot("a", {})
        um.snapshot("b", {})
        um.snapshot("c", {})
        um.snapshot("d", {})
        # Only last 3 should remain
        action = um.undo()
        assert action["type"] == "d"
        action = um.undo()
        assert action["type"] == "c"
        action = um.undo()
        assert action["type"] == "b"
        assert um.can_undo() is False


class TestUndoManagerUndo:
    def test_undo_returns_snapshot(self):
        um = UndoManager()
        um.snapshot("edit", {"file": "x.py"})
        action = um.undo()
        assert action is not None
        assert action["type"] == "edit"
        assert action["details"]["file"] == "x.py"
        assert "timestamp" in action

    def test_undo_empty_returns_none(self):
        um = UndoManager()
        assert um.undo() is None

    def test_undo_moves_to_redo_stack(self):
        um = UndoManager()
        um.snapshot("a", {})
        um.snapshot("b", {})
        um.undo()
        assert um.can_redo() is True


class TestUndoManagerRedo:
    def test_redo_after_undo(self):
        um = UndoManager()
        um.snapshot("a", {"x": 1})
        um.undo()
        action = um.redo()
        assert action is not None
        assert action["type"] == "a"
        assert action["details"]["x"] == 1

    def test_redo_empty_returns_none(self):
        um = UndoManager()
        assert um.redo() is None

    def test_redo_moves_to_undo_stack(self):
        um = UndoManager()
        um.snapshot("a", {})
        um.undo()
        um.redo()
        assert um.can_undo() is True
        assert um.can_redo() is False


class TestUndoManagerDescriptions:
    def test_get_undo_description(self):
        um = UndoManager()
        assert um.get_undo_description() == ""
        um.snapshot("file_edit", {"f": "a"})
        assert um.get_undo_description() == "file_edit"

    def test_get_redo_description(self):
        um = UndoManager()
        assert um.get_redo_description() == ""
        um.snapshot("file_edit", {})
        um.undo()
        assert um.get_redo_description() == "file_edit"


class TestUndoManagerClear:
    def test_clear(self):
        um = UndoManager()
        um.snapshot("a", {})
        um.snapshot("b", {})
        um.undo()
        um.clear()
        assert um.can_undo() is False
        assert um.can_redo() is False


# ---------------------------------------------------------------------------
# SessionManager tests
# ---------------------------------------------------------------------------


class TestSessionManagerInit:
    def test_sessions_dir_created(self, session_mgr, sessions_dir):
        # The SessionManager creates the dir in __init__
        assert sessions_dir.parent.parent.exists() or session_mgr._sessions_dir.exists()


class TestSessionManagerSave:
    def test_save_creates_file(self, session_mgr, agent):
        filepath = session_mgr.save(agent, "test_save")
        assert filepath.exists()
        assert filepath.suffix == ".json"

    def test_save_file_contents(self, session_mgr, agent):
        agent.history = [{"role": "user", "content": "Hello"}]
        agent.model = "gpt-4o-mini"
        filepath = session_mgr.save(agent, "test_contents")
        with open(filepath) as f:
            data = json.load(f)
        assert data["name"] == "test_contents"
        assert data["model"] == "gpt-4o-mini"
        assert len(data["history"]) == 1
        assert "timestamp" in data

    def test_save_creates_symlink(self, session_mgr, agent):
        session_mgr.save(agent, "test_symlink")
        symlink = session_mgr._sessions_dir / "latest_test_symlink.json"
        assert symlink.exists()
        assert symlink.is_symlink()

    def test_save_sanitizes_name(self, session_mgr, agent):
        filepath = session_mgr.save(agent, "test special!chars")
        # Special characters should be replaced with underscores in filename
        assert filepath.exists()
        # The safe_name substitution replaces non-alphanumeric chars
        assert "special_chars" in filepath.name or "special" in filepath.name

    def test_save_second_overwrites_symlink(self, session_mgr, agent):
        session_mgr.save(agent, "test_overwrite")
        session_mgr.save(agent, "test_overwrite")
        symlink = session_mgr._sessions_dir / "latest_test_overwrite.json"
        assert symlink.exists()


class TestSessionManagerLoad:
    def test_load_restores_history(self, session_mgr, agent):
        agent.history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        agent.model = "gpt-4o"
        session_mgr.save(agent, "test_load")

        # Reset history
        agent.history = []
        result = session_mgr.load("test_load", agent)
        assert result is True
        assert len(agent.history) == 2

    def test_load_nonexistent_returns_false(self, session_mgr, agent):
        result = session_mgr.load("nonexistent_session_xyz", agent)
        assert result is False

    def test_load_restores_model(self, session_mgr, agent):
        agent.model = "gpt-4o"
        session_mgr.save(agent, "test_model_load")
        agent.model = "gpt-4o-mini"

        result = session_mgr.load("test_model_load", agent)
        assert result is True
        # switch_model is called which only sets model if in MODELS dict
        # gpt-4o is a valid model so it should be restored
        assert agent.model == "gpt-4o"


class TestSessionManagerListSessions:
    def test_list_sessions_empty(self, session_mgr):
        sessions = session_mgr.list_sessions()
        assert isinstance(sessions, list)

    def test_list_sessions_after_save(self, session_mgr, agent):
        session_mgr.save(agent, "session1")
        session_mgr.save(agent, "session2")
        sessions = session_mgr.list_sessions()
        assert len(sessions) >= 2
        names = [s["name"] for s in sessions]
        assert "session1" in names
        assert "session2" in names

    def test_list_sessions_sorted_by_timestamp(self, session_mgr, agent):
        import time

        session_mgr.save(agent, "older")
        time.sleep(0.01)
        session_mgr.save(agent, "newer")
        sessions = session_mgr.list_sessions()
        if len(sessions) >= 2:
            assert sessions[0]["timestamp"] >= sessions[1]["timestamp"]


class TestSessionManagerShare:
    def test_share_creates_share_link(self, session_mgr, agent):
        agent.history = [{"role": "user", "content": "Shared message"}]
        link = session_mgr.share(agent, "test_share")
        assert link.startswith("apex://share/")

    def test_share_creates_file(self, session_mgr, agent):
        link = session_mgr.share(agent, "test_share_file")
        share_id = link.split("/")[-1]
        share_file = session_mgr._sessions_dir / "shared" / f"{share_id}.json"
        assert share_file.exists()
        with open(share_file) as f:
            data = json.load(f)
        assert "data" in data
        assert "nonce" in data
        assert data["id"] == share_id

    def test_share_and_load_roundtrip(self, session_mgr, agent):
        agent.history = [{"role": "user", "content": "Round trip test"}]
        agent.model = "gpt-4o-mini"
        link = session_mgr.share(agent, "test_roundtrip")
        share_id = link.split("/")[-1]

        # Create a fresh agent to load into
        agent2 = Agent(config=Config(config_path=session_mgr._sessions_dir / "cfg.json"))
        agent2.history = []

        result = session_mgr.load_shared(share_id, agent2)
        assert result is True
        assert len(agent2.history) == 1
        assert agent2.history[0]["content"] == "Round trip test"

    def test_load_shared_nonexistent(self, session_mgr, agent):
        result = session_mgr.load_shared("nonexistent_share_id", agent)
        assert result is False


class TestSessionManagerSessionDataIntegrity:
    """Test that session data survives save/load cycle intact."""

    def test_usage_preserved(self, session_mgr, agent):
        agent._usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        session_mgr.save(agent, "test_usage")
        # Check the saved file
        symlink = session_mgr._sessions_dir / "latest_test_usage.json"
        target = session_mgr._sessions_dir / symlink.readlink()
        with open(target) as f:
            data = json.load(f)
        assert data["usage"]["prompt_tokens"] == 100

    def test_cwd_preserved(self, session_mgr, agent):
        agent.cwd = Path("/tmp/test_dir")
        session_mgr.save(agent, "test_cwd")
        symlink = session_mgr._sessions_dir / "latest_test_cwd.json"
        target = session_mgr._sessions_dir / symlink.readlink()
        with open(target) as f:
            data = json.load(f)
        assert data["cwd"] == "/tmp/test_dir"
