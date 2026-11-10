"""Tests for apex/main.py — runtime setup, session restore and route selection."""

import argparse
import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from apex import main as main_module
from apex.main import (
    _configure_logging,
    _default_verb_namespace,
    _restore_session,
    _route_mode,
    _validate_model,
)


class TestPrepareRuntime:
    def test_sets_env(self):

        with (
            patch.object(main_module, "_warn_if_not_source_checkout"),
            patch.object(main_module, "_init_state_dir"),
            patch.object(main_module, "_setup_file_logging"),
        ):
            main_module._prepare_runtime()

        assert os.environ["APEX"] == "1"

        assert os.environ["APEX_PID"] == str(os.getpid())


class TestWarnSourceCheckout:
    def test_no_warning_for_source(self, monkeypatch, capsys):

        monkeypatch.setattr("apex.__file__", "/home/user/myapp/APEX/apex/__init__.py")

        main_module._warn_if_not_source_checkout()

        assert "WARNING" not in capsys.readouterr().err

    def test_warns_for_site_packages(self, monkeypatch, capsys):

        monkeypatch.setattr("apex.__file__", "/opt/python/site-packages/apex/__init__.py")

        main_module._warn_if_not_source_checkout()

        assert "source-only development surface" in capsys.readouterr().err


class TestStateDir:
    def test_creates_state_dir(self):

        state_dir = main_module._init_state_dir()

        assert state_dir.is_dir()

        assert (state_dir / "log").is_dir()

        assert (state_dir / "data").is_dir()

    def test_file_logging_adds_handler(self):

        root = logging.getLogger()

        before = list(root.handlers)

        main_module._setup_file_logging()

        new = [h for h in root.handlers if h not in before]

        try:
            assert len(new) == 1

            assert isinstance(new[0], logging.FileHandler)

            assert new[0].baseFilename.endswith(".log")

        finally:
            root.removeHandler(new[0])

            new[0].close()


class TestConfigureLogging:
    def test_log_level(self):

        with patch("logging.basicConfig") as mock_bc:
            _configure_logging(argparse.Namespace(log_level="debug", print_logs=False))

        mock_bc.assert_called_once_with(level=logging.DEBUG)

    def test_print_logs(self):

        with patch("logging.basicConfig") as mock_bc:
            _configure_logging(argparse.Namespace(log_level=None, print_logs=True))

        assert mock_bc.call_args.kwargs["stream"] is sys.stdout

    def test_noop(self):

        with patch("logging.basicConfig") as mock_bc:
            _configure_logging(argparse.Namespace(log_level=None, print_logs=False))

        mock_bc.assert_not_called()


class TestValidateModel:
    def test_unknown_model_exits(self, monkeypatch, capsys):

        monkeypatch.setattr(main_module, "MODELS", {"only-one": "x/only"})

        with pytest.raises(SystemExit) as exc:
            _validate_model(argparse.Namespace(model="nope"))

        assert exc.value.code == 1

        assert "Unknown model 'nope'" in capsys.readouterr().err

    def test_known_model_ok(self, monkeypatch):

        monkeypatch.setattr(main_module, "MODELS", {"only-one": "x/only"})

        _validate_model(argparse.Namespace(model="only-one"))

    def test_none_ok(self, monkeypatch):

        monkeypatch.setattr(main_module, "MODELS", {})

        _validate_model(argparse.Namespace(model=None))


class TestRestoreSession:
    def test_resume(self):

        agent = MagicMock()

        with patch.object(main_module, "SessionManager") as mock_sm:
            sm = mock_sm.return_value

            sm.list_sessions.return_value = [{"name": "s1"}, {"name": "s2"}]

            _restore_session(
                argparse.Namespace(resume=True, session_id=None, fork_session=None), agent
            )

        sm.load.assert_called_once_with("s1", agent)

    def test_resume_no_sessions(self):

        with patch.object(main_module, "SessionManager") as mock_sm:
            mock_sm.return_value.list_sessions.return_value = []

            _restore_session(
                argparse.Namespace(resume=True, session_id=None, fork_session=None),
                MagicMock(),
            )

        mock_sm.return_value.load.assert_not_called()

    def test_session_id(self):

        agent = MagicMock()

        with patch.object(main_module, "SessionManager") as mock_sm:
            _restore_session(
                argparse.Namespace(resume=False, session_id="abc", fork_session=None), agent
            )

        mock_sm.return_value.load.assert_called_once_with("abc", agent)

    def test_fork(self):

        agent = MagicMock()

        with patch.object(main_module, "SessionManager") as mock_sm:
            _restore_session(
                argparse.Namespace(resume=False, session_id=None, fork_session="f1"), agent
            )

        mock_sm.return_value.load.assert_called_once_with("f1", agent)


class TestRouteMode:
    def _parsed(self, **kw):

        base = {
            "ui": False,
            "tui": False,
            "prompt_direct": None,
            "prompt": None,
            "output_format": "text",
            "quiet": False,
            "image": None,
            "auto_commit": False,
            "stream": False,
            "resume": False,
            "session_id": None,
        }

        base.update(kw)

        return argparse.Namespace(**base)

    def test_ui_flag(self):

        agent, ui = MagicMock(), MagicMock()

        with patch.object(main_module, "run_apex_tui") as mock_tui:
            _route_mode(self._parsed(ui=True), agent, ui)

        mock_tui.assert_called_once_with(agent, ui, resume=False, session_id=None)

    def test_prompt_direct(self):

        agent, ui = MagicMock(), MagicMock()

        with patch.object(main_module, "run_cicd_mode") as mock_cicd:
            _route_mode(self._parsed(prompt_direct="ci"), agent, ui)

        mock_cicd.assert_called_once()

        options = mock_cicd.call_args.args[3]

        assert options.output_format == "text"

    def test_prompt(self):

        agent, ui = MagicMock(), MagicMock()

        with patch.object(main_module, "run_one_shot") as mock_one:
            _route_mode(self._parsed(prompt="hi", stream=True), agent, ui)

        mock_one.assert_called_once()

        options = mock_one.call_args.args[3]

        assert options.use_stream is True

    def test_default_tui(self):

        agent, ui = MagicMock(), MagicMock()

        with patch.object(main_module, "run_apex_tui") as mock_tui:
            _route_mode(self._parsed(), agent, ui)

        mock_tui.assert_called_once_with(agent, ui)


class TestDispatch:
    def test_list_models_exits(self):

        parsed = _default_verb_namespace()

        parsed.list_models = True

        with (
            patch("apex.config.Config"),
            patch.object(main_module, "UI"),
            patch.object(main_module, "list_models") as mock_lm,
            pytest.raises(SystemExit) as exc,
        ):
            main_module._dispatch(parsed)

        assert exc.value.code == 0

        mock_lm.assert_called_once()

    def test_install_tui_exits(self):

        parsed = _default_verb_namespace()

        parsed.install_tui = True

        with (
            patch("apex.config.Config"),
            patch.object(main_module, "UI"),
            patch.object(main_module, "_install_tui_command") as mock_install,
            pytest.raises(SystemExit) as exc,
        ):
            main_module._dispatch(parsed)

        assert exc.value.code == 0

        mock_install.assert_called_once()

    def test_full_path(self):

        parsed = _default_verb_namespace()

        parsed.model = "gpt-4o"

        parsed.agent_name = "plan"

        parsed.cwd = "/tmp"

        parsed.pure = True

        parsed.prompt = "do it"

        with (
            patch("apex.config.Config") as mock_cfg,
            patch.object(main_module, "UI"),
            patch.object(main_module, "Agent") as mock_agent,
            patch.object(main_module, "_restore_session") as mock_restore,
            patch.object(main_module, "_route_mode") as mock_route,
        ):
            main_module._dispatch(parsed)

        cfg = mock_cfg.return_value

        assert cfg.cwd == "/tmp"

        assert cfg.model == "gpt-4o"

        cfg.set.assert_any_call("default_agent", "plan")

        cfg.set.assert_any_call("pure_mode", True)

        mock_agent.return_value.switch_agent.assert_called_once_with("plan")

        mock_restore.assert_called_once()

        mock_route.assert_called_once()
