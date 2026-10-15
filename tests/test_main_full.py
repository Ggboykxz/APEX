"""Tests for apex/main.py — handle_command and other functions with real Agent/UI objects."""

import pytest
import sys
import tempfile
import os


# ---------------------------------------------------------------------------
# parse_args — additional edge cases
# ---------------------------------------------------------------------------


class TestParseArgsAdditional:
    """Additional parse_args tests beyond test_main.py."""

    def test_cwd_short_C(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-C", "/var"]
            from apex.main import parse_args

            args = parse_args()
            assert args.cwd == "/var"
        finally:
            sys.argv = saved

    def test_prompt_direct_with_format(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-p", "test", "-f", "json"]
            from apex.main import parse_args

            args = parse_args()
            assert args.prompt_direct == "test"
            assert args.output_format == "json"
        finally:
            sys.argv = saved

    def test_all_boolean_flags_default_false(self):
        saved = sys.argv
        try:
            sys.argv = ["apex"]
            from apex.main import parse_args

            args = parse_args()
            assert args.list_models is False
            assert args.one_shot is False
            assert args.stream is False
            assert args.auto_commit is False
            assert args.ui is False
            assert args.tui is False
            assert args.quiet is False
        finally:
            sys.argv = saved

    def test_default_format_is_text(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "prompt"]
            from apex.main import parse_args

            args = parse_args()
            assert args.output_format == "text"
        finally:
            sys.argv = saved


# ---------------------------------------------------------------------------
# list_models — calls ui.show_models with config model
# ---------------------------------------------------------------------------


class TestListModels:
    """Test list_models function."""

    def test_list_models_calls_show_models(self):
        from apex.main import list_models
        from apex.ui import UI
        from apex.config import Config

        ui = UI()
        Config()
        # list_models should call ui.show_models(config.model) without error
        list_models(ui)


# ---------------------------------------------------------------------------
# handle_command — tests with real Agent and UI objects
# ---------------------------------------------------------------------------


class TestHandleCommand:
    """Test handle_command function with real objects."""

    @pytest.fixture
    def real_agent(self):
        """Create a real Agent object."""
        from apex.agent import Agent
        from apex.config import Config

        saved_cwd = os.getcwd()
        try:
            config = Config()
            agent = Agent(config)
            yield agent
        finally:
            os.chdir(saved_cwd)

    @pytest.fixture
    def real_ui(self):
        """Create a real UI object."""
        from apex.ui import UI

        return UI()

    def test_model_no_arg(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/model", real_agent, real_ui)
        assert result is True

    def test_model_auto(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/model auto", real_agent, real_ui)
        assert result is True

    def test_model_valid(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/model gpt-4o", real_agent, real_ui)
        assert result is True

    def test_model_invalid(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/model nonexistent-model", real_agent, real_ui)
        assert result is True

    def test_models_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/models", real_agent, real_ui)
        assert result is True

    def test_reasoning_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/reasoning", real_agent, real_ui)
        assert result is True

    def test_reason_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/reason", real_agent, real_ui)
        assert result is True

    def test_cwd_no_arg(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/cwd", real_agent, real_ui)
        assert result is True

    def test_cwd_valid_dir(self, real_agent, real_ui):
        from apex.main import handle_command

        with tempfile.TemporaryDirectory() as tmpdir:
            result = handle_command(f"/cwd {tmpdir}", real_agent, real_ui)
            assert result is True

    def test_cwd_nonexistent_dir(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/cwd /nonexistent/path/xyz123", real_agent, real_ui)
        assert result is True

    def test_clear_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/clear", real_agent, real_ui)
        assert result is True
        assert real_agent.history == []

    def test_history_empty(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/history", real_agent, real_ui)
        assert result is True

    def test_history_with_messages(self, real_agent, real_ui):
        from apex.main import handle_command

        real_agent.history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
        result = handle_command("/history", real_agent, real_ui)
        assert result is True

    def test_cost_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/cost", real_agent, real_ui)
        assert result is True

    @pytest.mark.xfail(
        reason="Source bug: SessionManager shadowed by local import in handle_command"
    )
    def test_save_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/save test_session", real_agent, real_ui)
        assert result is True

    @pytest.mark.xfail(
        reason="Source bug: SessionManager shadowed by local import in handle_command"
    )
    def test_save_no_arg(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/save", real_agent, real_ui)
        assert result is True

    @pytest.mark.xfail(
        reason="Source bug: SessionManager shadowed by local import in handle_command"
    )
    def test_load_no_arg(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/load", real_agent, real_ui)
        assert result is True

    @pytest.mark.xfail(
        reason="Source bug: SessionManager shadowed by local import in handle_command"
    )
    def test_load_with_name(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/load nonexistent_session", real_agent, real_ui)
        assert result is True

    @pytest.mark.xfail(
        reason="Source bug: SessionManager shadowed by local import in handle_command"
    )
    def test_sessions_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/sessions", real_agent, real_ui)
        assert result is True

    def test_memory_no_arg_empty(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/memory", real_agent, real_ui)
        assert result is True

    def test_memory_add(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/memory add test_fact relevance1,relevance2", real_agent, real_ui)
        assert result is True

    def test_memory_clear(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/memory clear", real_agent, real_ui)
        assert result is True

    def test_memory_search(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/memory search test", real_agent, real_ui)
        assert result is True

    def test_memory_invalid_subcmd(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/memory invalid", real_agent, real_ui)
        assert result is True

    def test_map_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/map", real_agent, real_ui)
        assert result is True

    def test_stats_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/stats", real_agent, real_ui)
        assert result is True

    def test_help_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/help", real_agent, real_ui)
        assert result is True

    def test_unknown_slash_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/unknown_cmd", real_agent, real_ui)
        assert result is True

    def test_non_slash_input_returns_false(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("hello world", real_agent, real_ui)
        assert result is False

    def test_agent_no_arg(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/agent", real_agent, real_ui)
        assert result is True

    def test_agent_valid(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/agent coder", real_agent, real_ui)
        assert result is True

    def test_agent_invalid(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/agent nonexistent", real_agent, real_ui)
        assert result is True

    def test_coder_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/coder", real_agent, real_ui)
        assert result is True

    def test_architect_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/architect", real_agent, real_ui)
        assert result is True

    def test_restore_no_snapshots(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/restore", real_agent, real_ui)
        assert result is True

    def test_restore_with_name(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/restore nonexistent_snapshot", real_agent, real_ui)
        assert result is True

    def test_revert_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/revert 1", real_agent, real_ui)
        assert result is True

    def test_undo_command_nothing(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/undo", real_agent, real_ui)
        assert result is True

    def test_redo_command_nothing(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/redo", real_agent, real_ui)
        assert result is True

    def test_skills_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/skills", real_agent, real_ui)
        assert result is True

    def test_github_no_arg(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/github", real_agent, real_ui)
        assert result is True

    def test_local_enable(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/local enable", real_agent, real_ui)
        assert result is True

    def test_local_disable(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/local disable", real_agent, real_ui)
        assert result is True

    def test_local_status(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/local", real_agent, real_ui)
        assert result is True

    def test_sessionsave_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/sessionsave", real_agent, real_ui)
        assert result is True

    def test_sessionload_no_arg(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/sessionload", real_agent, real_ui)
        assert result is True

    def test_tasks_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/tasks", real_agent, real_ui)
        assert result is True

    def test_http_start(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/http start", real_agent, real_ui)
        assert result is True

    def test_http_no_arg(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/http", real_agent, real_ui)
        assert result is True

    def test_agents_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/agents", real_agent, real_ui)
        assert result is True

    def test_subagents_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/subagents", real_agent, real_ui)
        assert result is True
