"""Tests for APEX session management."""

import pytest
from apex.session import SessionManager
from apex.agent import Agent
from apex.config import Config


@pytest.fixture
def session_mgr(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return SessionManager()


@pytest.fixture
def agent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config = Config(config_path=tmp_path / "config.json")
    return Agent(config=config)


def test_session_manager_init(session_mgr):
    assert session_mgr._sessions_dir.exists()


def test_session_save_and_load(session_mgr, agent):
    agent.history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    agent.model = "gpt-4o"

    filepath = session_mgr.save(agent, "test_session")
    assert filepath.exists()

    agent.history = []
    agent.model = "claude-sonnet"

    result = session_mgr.load("test_session", agent)
    assert result is True
    assert len(agent.history) == 2
    assert agent.model == "gpt-4o"


def test_session_load_nonexistent(session_mgr, agent):
    result = session_mgr.load("nonexistent", agent)
    assert result is False


def test_session_list_sessions(session_mgr, agent):
    session_mgr.save(agent, "session1")
    session_mgr.save(agent, "session2")

    sessions = session_mgr.list_sessions()
    assert len(sessions) >= 2


def test_session_latest_symlink(session_mgr, agent):
    session_mgr.save(agent, "latest_test")

    latest_link = session_mgr._sessions_dir / "latest_latest_test.json"
    assert latest_link.exists()
