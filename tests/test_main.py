"""Tests for main module."""

import pytest
import argparse
from unittest.mock import MagicMock, patch
from pathlib import Path


class TestParseArgs:
    """Test parse_args function."""

    def test_parse_args_no_args(self):
        """Test parsing with no arguments."""
        with patch("sys.argv", ["apex"]):
            from apex.main import parse_args

            args = parse_args()
            assert isinstance(args, argparse.Namespace)
            assert args.prompt is None

    def test_parse_args_with_prompt(self):
        """Test parsing with prompt argument."""
        with patch("sys.argv", ["apex", "hello world"]):
            from apex.main import parse_args

            args = parse_args()
            assert args.prompt == "hello world"

    def test_parse_args_model_flag(self):
        """Test parsing with --model flag."""
        with patch("sys.argv", ["apex", "--model", "gpt-4o", "hello"]):
            from apex.main import parse_args

            args = parse_args()
            assert args.model == "gpt-4o"
            assert args.prompt == "hello"

    def test_parse_args_cwd_flag(self):
        """Test parsing with --cwd flag."""
        with patch("sys.argv", ["apex", "--cwd", "/tmp"]):
            from apex.main import parse_args

            args = parse_args()
            assert args.cwd == "/tmp"

    def test_parse_args_list_models(self):
        """Test parsing with --list-models flag."""
        with patch("sys.argv", ["apex", "--list-models"]):
            from apex.main import parse_args

            args = parse_args()
            assert args.list_models is True

    def test_parse_args_one_shot(self):
        """Test parsing with --one-shot flag."""
        with patch("sys.argv", ["apex", "--one-shot", "hello"]):
            from apex.main import parse_args

            args = parse_args()
            assert args.one_shot is True

    def test_parse_args_stream(self):
        """Test parsing with --stream flag."""
        with patch("sys.argv", ["apex", "--stream", "hello"]):
            from apex.main import parse_args

            args = parse_args()
            assert args.stream is True

    def test_parse_args_auto_commit(self):
        """Test parsing with --auto-commit flag."""
        with patch("sys.argv", ["apex", "--auto-commit", "hello"]):
            from apex.main import parse_args

            args = parse_args()
            assert args.auto_commit is True

    def test_parse_args_version(self):
        """Test parsing with --version flag."""
        with patch("sys.argv", ["apex", "--version"]):
            from apex.main import parse_args

            with pytest.raises(SystemExit):
                parse_args()


class TestHandleCommand:
    """Test handle_command function."""

    @pytest.fixture
    def mock_agent(self):
        """Create mock agent."""
        agent = MagicMock()
        agent.switch_model.return_value = True
        agent.model = "gpt-4o"
        agent.cwd = Path.cwd()
        agent.history = []
        agent.reset_history = MagicMock()
        return agent

    @pytest.fixture
    def mock_ui(self):
        """Create mock UI."""
        ui = MagicMock()
        return ui

    def test_handle_command_model(self, mock_agent, mock_ui):
        """Test /model command."""
        from apex.main import handle_command

        result = handle_command("/model gpt-4o", mock_agent, mock_ui)
        assert result is True
        mock_agent.switch_model.assert_called_once_with("gpt-4o")

    def test_handle_command_models(self, mock_agent, mock_ui):
        """Test /models command."""
        from apex.main import handle_command

        result = handle_command("/models", mock_agent, mock_ui)
        assert result is True
        mock_ui.show_models.assert_called_once()

    def test_handle_command_cwd_current(self, mock_agent, mock_ui):
        """Test /cwd command without argument."""
        from apex.main import handle_command

        result = handle_command("/cwd", mock_agent, mock_ui)
        assert result is True

    def test_handle_command_clear(self, mock_agent, mock_ui):
        """Test /clear command."""
        from apex.main import handle_command

        result = handle_command("/clear", mock_agent, mock_ui)
        assert result is True
        mock_agent.reset_history.assert_called_once()

    def test_handle_command_history_empty(self, mock_agent, mock_ui):
        """Test /history command with empty history."""
        from apex.main import handle_command

        result = handle_command("/history", mock_agent, mock_ui)
        assert result is True

    def test_handle_command_unknown(self, mock_agent, mock_ui):
        """Test unknown command - returns True for unknown /command but False for non-/input."""
        from apex.main import handle_command

        result = handle_command("/unknown", mock_agent, mock_ui)
        assert result is True
        mock_ui.print_error.assert_called_once()

    def test_handle_command_not_slash(self, mock_agent, mock_ui):
        """Test non-slash command returns False to pass to agent."""
        from apex.main import handle_command

        result = handle_command("hello world", mock_agent, mock_ui)
        assert result is False
