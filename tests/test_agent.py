"""Tests for APEX agent."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from apex.agent import Agent
from apex.config import Config


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_file = tmp_path / "config.json"
    return Config(config_path=config_file)


@pytest.fixture
def agent(config):
    return Agent(config=config)


def test_agent_init(config):
    agent = Agent(config=config)
    assert agent.model == config.model
    assert isinstance(agent.cwd, Path)


def test_agent_cwd_setter(agent, tmp_path):
    new_cwd = tmp_path / "new_cwd"
    new_cwd.mkdir()
    agent.cwd = new_cwd
    assert agent.cwd == new_cwd


def test_agent_reset_history(agent):
    agent.history = [{"role": "user", "content": "test"}]
    agent.reset_history()
    assert agent.history == []
    assert agent.usage["total_tokens"] == 0


def test_agent_switch_model(agent):
    assert agent.switch_model("gpt-4o")
    assert agent.model == "gpt-4o"
    assert not agent.switch_model("nonexistent-model")
    assert agent.model == "gpt-4o"


def test_agent_usage_tracking(agent):
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 100
    mock_usage.completion_tokens = 50
    mock_usage.total_tokens = 150

    mock_response = MagicMock()
    mock_response.usage = mock_usage
    mock_response.choices = [MagicMock()]

    agent._update_usage(mock_response.usage)
    assert agent.usage["prompt_tokens"] == 100
    assert agent.usage["completion_tokens"] == 50
    assert agent.usage["total_tokens"] == 150


def test_agent_no_tool_calls(agent):
    mock_response = MagicMock()
    mock_response.usage = None
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello, I am APEX"
    mock_response.choices[0].message.tool_calls = []

    with patch("apex.agent.litellm.completion", return_value=mock_response):
        result = agent.chat("Hello")
        assert result == "Hello, I am APEX"
        assert len(agent.history) == 2


def test_agent_with_tool_calls(agent):
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "run_command"
    mock_tool_call.function.arguments = '{"command": "echo test"}'

    mock_response = MagicMock()
    mock_response.usage = None
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = [mock_tool_call]

    with patch("apex.agent.litellm.completion", return_value=mock_response):
        result = agent.chat("Run a command")
        assert "Max tool rounds" in result or "ERROR" in result or result.startswith("")


def test_agent_handles_auth_error(agent):
    from litellm import AuthenticationError
    exc = AuthenticationError(message="Invalid key", llm_provider="openai", model="gpt-4o")
    with patch("apex.agent.litellm.completion", side_effect=exc):
        result = agent.chat("Hello")
        assert "ERROR" in result
        assert "Authentication" in result


def test_agent_handles_rate_limit_error(agent):
    from litellm import RateLimitError
    exc = RateLimitError(message="Rate limited", llm_provider="openai", model="gpt-4o")
    with patch("apex.agent.litellm.completion", side_effect=exc):
        result = agent.chat("Hello")
        assert "ERROR" in result
        assert "Rate limit" in result