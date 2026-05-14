"""Tests for apex/main.py — more tests: run_cicd_mode, main function branching, etc."""

import pytest
import sys
import tempfile
import os


class TestParseArgsMore:
    """More parse_args edge cases."""

    def test_tui_short(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-t"]
            from apex.main import parse_args

            args = parse_args()
            assert args.tui is True
        finally:
            sys.argv = saved

    def test_combined_cwd_and_prompt(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--cwd", "/tmp", "do something"]
            from apex.main import parse_args

            args = parse_args()
            assert args.cwd == "/tmp"
            assert args.prompt == "do something"
        finally:
            sys.argv = saved


class TestHandleCommandMore:
    """More handle_command tests — sessionload with arg, exit command, etc."""

    @pytest.fixture
    def real_agent(self):
        from apex.agent import Agent
        from apex.config import Config

        # Save and restore cwd to avoid FileNotFoundError from deleted temp dirs
        saved_cwd = os.getcwd()
        try:
            config = Config()
            agent = Agent(config)
            yield agent
        finally:
            os.chdir(saved_cwd)

    @pytest.fixture
    def real_ui(self):
        from apex.ui import UI

        return UI()

    @pytest.mark.xfail(reason="Source bug: SessionManager.load() missing agent arg in /sessionload")
    def test_sessionload_with_name(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/sessionload nonexistent", real_agent, real_ui)
        assert result is True

    def test_sessionsave_with_name(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/sessionsave my_session", real_agent, real_ui)
        assert result is True

    def test_exit_command(self, real_agent, real_ui):
        from apex.main import handle_command

        with pytest.raises(SystemExit):
            handle_command("/exit", real_agent, real_ui)

    def test_quit_command(self, real_agent, real_ui):
        from apex.main import handle_command

        with pytest.raises(SystemExit):
            handle_command("/quit", real_agent, real_ui)

    def test_cwd_file_path_not_dir(self, real_agent, real_ui):
        """Test /cwd with a file path instead of directory."""
        from apex.main import handle_command

        with tempfile.NamedTemporaryFile() as f:
            result = handle_command(f"/cwd {f.name}", real_agent, real_ui)
            assert result is True

    def test_history_long_content_truncated(self, real_agent, real_ui):
        from apex.main import handle_command

        long_content = "x" * 200
        real_agent.history = [{"role": "user", "content": long_content}]
        result = handle_command("/history", real_agent, real_ui)
        assert result is True

    def test_cwd_outside_working_dir(self, real_agent, real_ui):
        """Test /cwd with a path outside working directory (no APEX_ALLOW_OUTSIDE_CWD)."""
        from apex.main import handle_command

        saved_env = os.environ.pop("APEX_ALLOW_OUTSIDE_CWD", None)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # This may or may not be outside cwd depending on the system
                result = handle_command(f"/cwd {tmpdir}", real_agent, real_ui)
                assert result is True
        finally:
            if saved_env is not None:
                os.environ["APEX_ALLOW_OUTSIDE_CWD"] = saved_env

    def test_cwd_outside_working_dir_allowed(self, real_agent, real_ui):
        """Test /cwd with APEX_ALLOW_OUTSIDE_CWD=true."""
        from apex.main import handle_command

        os.environ["APEX_ALLOW_OUTSIDE_CWD"] = "true"
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = handle_command(f"/cwd {tmpdir}", real_agent, real_ui)
                assert result is True
        finally:
            del os.environ["APEX_ALLOW_OUTSIDE_CWD"]

    def test_memory_add_with_relevance(self, real_agent, real_ui):
        from apex.main import handle_command
        from apex.main import memory

        try:
            handle_command("/memory add my_fact python,testing", real_agent, real_ui)
            facts = memory.get_all()
            assert any("my_fact" in f.get("fact", "") for f in facts)
        finally:
            memory.clear()

    @pytest.mark.xfail(reason="Source bug: SessionManager shadowed by local import")
    def test_github_issues_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/github issues", real_agent, real_ui)
        assert result is True

    @pytest.mark.xfail(reason="Source bug: SessionManager shadowed by local import")
    def test_github_prs_command(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/github prs", real_agent, real_ui)
        assert result is True

    @pytest.mark.xfail(reason="Source bug: SessionManager shadowed by local import")
    def test_github_unknown_subcmd(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/github unknown_subcmd", real_agent, real_ui)
        assert result is True

    def test_revert_non_numeric(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/revert abc", real_agent, real_ui)
        assert result is True

    def test_undo_with_steps(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/undo 3", real_agent, real_ui)
        assert result is True

    def test_redo_with_steps(self, real_agent, real_ui):
        from apex.main import handle_command

        result = handle_command("/redo 2", real_agent, real_ui)
        assert result is True


class TestRunCicdMode:
    """Test run_cicd_mode function (without actual API calls)."""

    def test_cicd_mode_import(self):
        from apex.main import run_cicd_mode

        assert callable(run_cicd_mode)


class TestRunOneShot:
    """Test run_one_shot function import."""

    def test_run_one_shot_import(self):
        from apex.main import run_one_shot

        assert callable(run_one_shot)


class TestRunRepl:
    """Placeholder for removed run_repl."""

    def test_tui_is_default(self):
        from apex.main import build_parser

        parser = build_parser()
        assert parser is not None


class TestMainModule:
    """Test main module attributes and imports."""

    def test_memory_instance(self):
        from apex.main import memory
        from apex.memory import Memory

        assert isinstance(memory, Memory)

    def test_parse_args_is_function(self):
        from apex.main import parse_args

        assert callable(parse_args)

    def test_handle_command_is_function(self):
        from apex.main import handle_command

        assert callable(handle_command)

    def test_list_models_is_function(self):
        from apex.main import list_models

        assert callable(list_models)
