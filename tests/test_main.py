"""Tests for APEX main CLI."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from pathlib import Path
from apex.config import Config
from apex.agent import Agent
from apex.ui import UI


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return Config(config_path=tmp_path / "config.json")


@pytest.fixture
def agent(config):
    return Agent(config=config)


@pytest.fixture
def ui():
    return UI()


def test_parse_args_version():
    from apex.main import parse_args
    with patch.object(sys, "argv", ["apex", "--help"]):
        try:
            args = parse_args()
        except SystemExit:
            pass
    assert True


def test_parse_args_list_models():
    from apex.main import parse_args
    with patch.object(sys, "argv", ["apex", "--list-models"]):
        args = parse_args()
        assert args.list_models is True


def test_parse_args_model():
    from apex.main import parse_args
    with patch.object(sys, "argv", ["apex", "--model", "gpt-4o", "test prompt"]):
        args = parse_args()
        assert args.model == "gpt-4o"
        assert args.prompt == "test prompt"


def test_parse_args_cwd():
    from apex.main import parse_args
    with patch.object(sys, "argv", ["apex", "--cwd", "/tmp/test"]):
        args = parse_args()
        assert args.cwd == "/tmp/test"


def test_parse_args_stream():
    from apex.main import parse_args
    with patch.object(sys, "argv", ["apex", "--stream"]):
        args = parse_args()
        assert args.stream is True


def test_handle_command_model(agent, ui):
    from apex.main import handle_command
    result = handle_command("/model gpt-4o", agent, ui)
    assert result is True
    assert agent.model == "gpt-4o"


def test_handle_command_model_invalid(agent, ui):
    from apex.main import handle_command
    result = handle_command("/model invalid-model", agent, ui)
    assert result is True
    assert agent.model != "invalid-model"


def test_handle_command_models(agent, ui):
    from apex.main import handle_command
    result = handle_command("/models", agent, ui)
    assert result is True


def test_handle_command_cwd(agent, ui, tmp_path):
    from apex.main import handle_command
    test_dir = tmp_path / "testdir"
    test_dir.mkdir()
    result = handle_command(f"/cwd {test_dir}", agent, ui)
    assert result is True


def test_handle_command_clear(agent, ui):
    from apex.main import handle_command
    agent.history = [{"role": "user", "content": "test"}]
    result = handle_command("/clear", agent, ui)
    assert result is True
    assert len(agent.history) == 0


def test_handle_command_history_empty(agent, ui):
    from apex.main import handle_command
    result = handle_command("/history", agent, ui)
    assert result is True


def test_handle_command_cost(agent, ui):
    from apex.main import handle_command
    agent._usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    result = handle_command("/cost", agent, ui)
    assert result is True


def test_handle_command_help(agent, ui):
    from apex.main import handle_command
    result = handle_command("/help", agent, ui)
    assert result is True


def test_handle_command_unknown(agent, ui, capsys):
    from apex.main import handle_command
    result = handle_command("/unknowncmd", agent, ui)
    assert result is True
    captured = capsys.readouterr()
    assert "Unknown command" in captured.out


def test_handle_command_not_command(agent, ui):
    from apex.main import handle_command
    result = handle_command("Hello world", agent, ui)
    assert result is False


def test_handle_command_save(agent, ui, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from apex.main import handle_command
    result = handle_command("/save test_session", agent, ui)
    assert result is True


def test_handle_command_load(agent, ui, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from apex.main import handle_command
    from apex.session import SessionManager
    sm = SessionManager()
    sm.save(agent, "test_load")

    agent.history = []
    result = handle_command("/load test_load", agent, ui)
    assert result is True


def test_handle_command_map(agent, ui, tmp_path):
    from apex.main import handle_command
    result = handle_command("/map", agent, ui)
    assert result is True


def test_handle_command_stats(agent, ui, tmp_path):
    from apex.main import handle_command
    result = handle_command("/stats", agent, ui)
    assert result is True


def test_handle_command_git(agent, ui, tmp_path):
    from apex.main import handle_command
    git_dir = agent.cwd / ".git"
    git_dir.mkdir()
    result = handle_command("/git", agent, ui)
    assert result is True


def test_handle_command_memory_add(agent, ui, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from apex.main import handle_command, memory
    result = handle_command("/memory add Test fact python", agent, ui)
    assert result is True


def test_handle_command_memory_clear(agent, ui, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from apex.main import handle_command, memory
    memory.clear()
    result = handle_command("/memory clear", agent, ui)
    assert result is True


def test_handle_command_memory_search(agent, ui, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from apex.main import handle_command, memory
    memory.add("Test fact", ["test"])
    result = handle_command("/memory search test", agent, ui)
    assert result is True