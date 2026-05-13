"""Tests for apex/main.py — parse_args, handle_command, _dispatch_verb, and all CLI subcommands."""

import argparse
import pytest
import sys
from unittest.mock import patch


# ---------------------------------------------------------------------------
# parse_args — we must manipulate sys.argv directly (no mock/patch)
# ---------------------------------------------------------------------------


class TestParseArgs:
    """Test parse_args function with real argument parsing."""

    def test_no_args(self):
        saved = sys.argv
        try:
            sys.argv = ["apex"]
            from apex.main import parse_args

            args = parse_args()
            assert isinstance(args, argparse.Namespace)
            assert args.prompt is None
            assert args.model is None
            assert args.cwd is None
            assert args.list_models is False
            assert args.one_shot is False
            assert args.stream is False
            assert args.auto_commit is False
            assert args.ui is False
            assert args.tui is False
            assert args.prompt_direct is None
            assert args.output_format == "text"
            assert args.quiet is False
        finally:
            sys.argv = saved

    def test_with_prompt(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "hello world"]
            from apex.main import parse_args

            args = parse_args()
            assert args.prompt == "hello world"
        finally:
            sys.argv = saved

    def test_model_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--model", "gpt-4o", "hello"]
            from apex.main import parse_args

            args = parse_args()
            assert args.model == "gpt-4o"
            assert args.prompt == "hello"
        finally:
            sys.argv = saved

    def test_model_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-m", "sonnet", "test"]
            from apex.main import parse_args

            args = parse_args()
            assert args.model == "sonnet"
        finally:
            sys.argv = saved

    def test_cwd_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--cwd", "/tmp"]
            from apex.main import parse_args

            args = parse_args()
            assert args.cwd == "/tmp"
        finally:
            sys.argv = saved

    def test_cwd_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-C", "/home"]
            from apex.main import parse_args

            args = parse_args()
            assert args.cwd == "/home"
        finally:
            sys.argv = saved

    def test_list_models_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--list-models"]
            from apex.main import parse_args

            args = parse_args()
            assert args.list_models is True
        finally:
            sys.argv = saved

    def test_one_shot_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--one-shot", "hello"]
            from apex.main import parse_args

            args = parse_args()
            assert args.one_shot is True
        finally:
            sys.argv = saved

    def test_one_shot_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-1", "hello"]
            from apex.main import parse_args

            args = parse_args()
            assert args.one_shot is True
        finally:
            sys.argv = saved

    def test_stream_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--stream", "hello"]
            from apex.main import parse_args

            args = parse_args()
            assert args.stream is True
        finally:
            sys.argv = saved

    def test_stream_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-s", "hello"]
            from apex.main import parse_args

            args = parse_args()
            assert args.stream is True
        finally:
            sys.argv = saved

    def test_auto_commit_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--auto-commit", "hello"]
            from apex.main import parse_args

            args = parse_args()
            assert args.auto_commit is True
        finally:
            sys.argv = saved

    def test_ui_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--ui"]
            from apex.main import parse_args

            args = parse_args()
            assert args.ui is True
        finally:
            sys.argv = saved

    def test_tui_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--tui"]
            from apex.main import parse_args

            args = parse_args()
            assert args.tui is True
        finally:
            sys.argv = saved

    def test_tui_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-t"]
            from apex.main import parse_args

            args = parse_args()
            assert args.tui is True
        finally:
            sys.argv = saved

    def test_prompt_direct_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-p", "direct prompt"]
            from apex.main import parse_args

            args = parse_args()
            assert args.prompt_direct == "direct prompt"
        finally:
            sys.argv = saved

    def test_format_text(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--format", "text"]
            from apex.main import parse_args

            args = parse_args()
            assert args.output_format == "text"
        finally:
            sys.argv = saved

    def test_format_json(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--format", "json"]
            from apex.main import parse_args

            args = parse_args()
            assert args.output_format == "json"
        finally:
            sys.argv = saved

    def test_format_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-f", "json"]
            from apex.main import parse_args

            args = parse_args()
            assert args.output_format == "json"
        finally:
            sys.argv = saved

    def test_quiet_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--quiet"]
            from apex.main import parse_args

            args = parse_args()
            assert args.quiet is True
        finally:
            sys.argv = saved

    def test_quiet_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-q"]
            from apex.main import parse_args

            args = parse_args()
            assert args.quiet is True
        finally:
            sys.argv = saved

    def test_version_flag_exits(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--version"]
            from apex.main import parse_args

            with pytest.raises(SystemExit):
                parse_args()
        finally:
            sys.argv = saved

    def test_version_short_flag_exits(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-v"]
            from apex.main import parse_args

            with pytest.raises(SystemExit):
                parse_args()
        finally:
            sys.argv = saved

    def test_invalid_format_exits(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--format", "xml"]
            from apex.main import parse_args

            with pytest.raises(SystemExit):
                parse_args()
        finally:
            sys.argv = saved

    def test_combined_flags(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--stream", "--quiet", "-f", "json", "test prompt"]
            from apex.main import parse_args

            args = parse_args()
            assert args.stream is True
            assert args.quiet is True
            assert args.output_format == "json"
            assert args.prompt == "test prompt"
        finally:
            sys.argv = saved

    def test_continue_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--continue"]
            from apex.main import parse_args
            args = parse_args()
            assert args.resume is True
        finally:
            sys.argv = saved

    def test_session_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--session", "mysession"]
            from apex.main import parse_args
            args = parse_args()
            assert args.session_id == "mysession"
        finally:
            sys.argv = saved

    def test_agent_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--agent", "architect"]
            from apex.main import parse_args
            args = parse_args()
            assert args.agent_name == "architect"
        finally:
            sys.argv = saved

    def test_pure_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--pure"]
            from apex.main import parse_args
            args = parse_args()
            assert args.pure is True
        finally:
            sys.argv = saved

    def test_port_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--port", "9090"]
            from apex.main import parse_args
            args = parse_args()
            assert args.port == 9090
        finally:
            sys.argv = saved

    def test_hostname_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--hostname", "0.0.0.0"]
            from apex.main import parse_args
            args = parse_args()
            assert args.hostname == "0.0.0.0"
        finally:
            sys.argv = saved

    def test_refresh_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--refresh"]
            from apex.main import parse_args
            args = parse_args()
            assert args.refresh is True
        finally:
            sys.argv = saved

    def test_log_level_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--log-level", "DEBUG"]
            from apex.main import parse_args
            args = parse_args()
            assert args.log_level == "DEBUG"
        finally:
            sys.argv = saved

    def test_print_logs_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--print-logs"]
            from apex.main import parse_args
            args = parse_args()
            assert args.print_logs is True
        finally:
            sys.argv = saved


class TestHandleCommand:
    """Test handle_command with various slash commands."""

    @pytest.fixture
    def agent(self):
        from apex.agent import Agent
        from apex.config import Config
        return Agent(Config())

    @pytest.fixture
    def ui(self):
        from apex.ui import UI
        return UI()

    def test_clear(self, agent, ui):
        from apex.main import handle_command
        agent.reset_history()
        assert handle_command("/clear", agent, ui) is True

    def test_new(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/new", agent, ui)
        assert result is True

    def test_help(self, agent, ui):
        from apex.main import handle_command
        with patch("sys.exit"):
            result = handle_command("/help", agent, ui)
            assert result is True

    def test_exit(self, agent, ui):
        from apex.main import handle_command
        with patch("sys.exit") as mock_exit:
            handle_command("/exit", agent, ui)
            assert mock_exit.called

    def test_quit(self, agent, ui):
        from apex.main import handle_command
        with patch("sys.exit") as mock_exit:
            handle_command("/quit", agent, ui)
            assert mock_exit.called

    def test_unknown_command(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/unknown", agent, ui)
        assert result is True

    def test_model_switch(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/model gpt-4o", agent, ui)
        assert result is True

    def test_model_no_arg(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/model", agent, ui)
        assert result is True

    def test_models_list(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/models", agent, ui)
        assert result is True

    def test_agent_list(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/agent", agent, ui)
        assert result is True

    def test_agent_switch(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/agent architect", agent, ui)
        assert result is True

    def test_coder(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/coder", agent, ui)
        assert result is True

    def test_architect(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/architect", agent, ui)
        assert result is True

    def test_sessions(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/sessions", agent, ui)
        assert result is True

    def test_sessionsave(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/sessionsave test", agent, ui)
        assert result is True

    def test_cost(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/cost", agent, ui)
        assert result is True

    def test_skills(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/skills", agent, ui)
        assert result is True

    def test_history(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/history", agent, ui)
        assert result is True

    def test_map(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/map", agent, ui)
        assert result is True

    def test_stats(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/stats", agent, ui)
        assert result is True

    def test_cwd(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/cwd", agent, ui)
        assert result is True

    def test_git(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/git", agent, ui)
        assert result is True

    def test_tasks(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/tasks", agent, ui)
        assert result is True

    def test_subagents(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/subagents", agent, ui)
        assert result is True

    def test_agents(self, agent, ui):
        from apex.main import handle_command
        result = handle_command("/agents", agent, ui)
        assert result is True


class TestDispatchVerb:
    """Test _dispatch_verb routing for all subcommands."""

    def _make_args(self, **overrides):
        from apex.main import build_parser
        build_parser()
        return argparse.Namespace(**{
            "prompt": None, "model": None, "cwd": None, "list_models": False,
            "one_shot": False, "stream": False, "auto_commit": False,
            "ui": False, "tui": False, "prompt_direct": None,
            "output_format": "text", "quiet": False, "install_tui": False,
            "resume": False, "session_id": None, "fork_session": None,
            "agent_name": None, "print_logs": False, "log_level": None,
            "pure": False, "share": False, "input_file": None,
            "port": None, "hostname": None, "cors": None, "mdns": False,
            "refresh": False, "verbose": False, "days": None,
            "tools": False, "models_flag": False, "project": None,
            "sanitize": False, "keep_config": False, "keep_data": False,
            "dry_run": False, "force": False, "method": None,
            "raw_args": [],
            **overrides,
        })

    def test_serve(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_serve") as mock:
            _dispatch_verb("serve", self._make_args())
            mock.assert_called_once()

    def test_web(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_web") as mock:
            _dispatch_verb("web", self._make_args())
            mock.assert_called_once()

    def test_auth(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_auth") as mock:
            _dispatch_verb("auth", self._make_args())
            mock.assert_called_once()

    def test_agent(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_agent") as mock:
            _dispatch_verb("agent", self._make_args())
            mock.assert_called_once()

    def test_session(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_session") as mock:
            _dispatch_verb("session", self._make_args())
            mock.assert_called_once()

    def test_run(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_run") as mock:
            _dispatch_verb("run", self._make_args())
            mock.assert_called_once()

    def test_stats(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_stats") as mock:
            _dispatch_verb("stats", self._make_args())
            mock.assert_called_once()

    def test_export(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_export") as mock:
            _dispatch_verb("export", self._make_args())
            mock.assert_called_once()

    def test_import_cmd(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_import") as mock:
            _dispatch_verb("import", self._make_args())
            mock.assert_called_once()

    def test_upgrade(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_upgrade") as mock:
            _dispatch_verb("upgrade", self._make_args())
            mock.assert_called_once()

    def test_uninstall(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_uninstall") as mock:
            _dispatch_verb("uninstall", self._make_args())
            mock.assert_called_once()

    def test_mcp(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_mcp") as mock:
            _dispatch_verb("mcp", self._make_args())
            mock.assert_called_once()

    def test_db(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_db") as mock:
            _dispatch_verb("db", self._make_args())
            mock.assert_called_once()

    def test_pr(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_pr") as mock:
            _dispatch_verb("pr", self._make_args())
            mock.assert_called_once()

    def test_attach(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_attach") as mock:
            _dispatch_verb("attach", self._make_args())
            mock.assert_called_once()

    def test_connect(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_connect") as mock:
            _dispatch_verb("connect", self._make_args())
            mock.assert_called_once()

    def test_init(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_init") as mock:
            _dispatch_verb("init", self._make_args())
            mock.assert_called_once()

    def test_compact(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_compact") as mock:
            _dispatch_verb("compact", self._make_args())
            mock.assert_called_once()

    def test_details(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_details") as mock:
            _dispatch_verb("details", self._make_args())
            mock.assert_called_once()

    def test_thinking(self):
        from apex.main import _dispatch_verb
        with patch("apex.main._cmd_thinking") as mock:
            _dispatch_verb("thinking", self._make_args())
            mock.assert_called_once()

    def test_unknown_verb(self):
        from apex.main import _dispatch_verb
        with patch("sys.exit") as mock_exit:
            _dispatch_verb("nonexistent", self._make_args())
            assert mock_exit.called
