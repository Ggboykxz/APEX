"""Tests for main module."""

from unittest.mock import patch, MagicMock
from apex.main import parse_args, list_models


class TestParseArgs:
    """Test parse_args function."""

    @patch("sys.argv", ["apex"])
    def test_parse_no_args(self):
        """Test parsing with no arguments."""
        args = parse_args()
        assert args.prompt is None

    @patch("sys.argv", ["apex", "test prompt"])
    def test_parse_with_prompt(self):
        """Test parsing with prompt."""
        args = parse_args()
        assert args.prompt == "test prompt"

    @patch("sys.argv", ["apex", "--model", "claude-3"])
    def test_parse_with_model(self):
        """Test parsing with model flag."""
        args = parse_args()
        assert args.model == "claude-3"

    @patch("sys.argv", ["apex", "-C", "/test/path"])
    def test_parse_with_cwd(self):
        """Test parsing with cwd flag."""
        args = parse_args()
        assert args.cwd == "/test/path"

    @patch("sys.argv", ["apex", "--list-models"])
    def test_parse_list_models(self):
        """Test parsing list models flag."""
        args = parse_args()
        assert args.list_models is True

    @patch("sys.argv", ["apex", "--one-shot"])
    def test_parse_one_shot(self):
        """Test parsing one-shot flag."""
        args = parse_args()
        assert args.one_shot is True

    @patch("sys.argv", ["apex", "--stream"])
    def test_parse_stream(self):
        """Test parsing stream flag."""
        args = parse_args()
        assert args.stream is True

    @patch("sys.argv", ["apex", "--tui"])
    def test_parse_tui(self):
        """Test parsing tui flag."""
        args = parse_args()
        assert args.tui is True


class TestListModels:
    """Test list_models function."""

    @patch("apex.main.UI")
    def test_list_models(self, mock_ui):
        """Test list_models calls UI."""
        mock_instance = MagicMock()
        mock_ui.return_value = mock_instance
        list_models(mock_instance)
        mock_instance.show_models.assert_called_once()


class TestAgentCreation:
    """Test agent creation in main."""

    def test_agent_init_with_config(self):
        """Test Agent can be initialized."""
        from apex.agent import Agent
        from apex.config import Config

        config = Config()
        agent = Agent(config=config)
        assert agent is not None
