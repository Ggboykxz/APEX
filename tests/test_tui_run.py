"""Tests for apex/tui_launcher.py — the TUI launch path."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apex import tui_launcher
from apex.tui_launcher import (
    _find_free_port,
    _require_tui_dir,
    _resolve_tui_runtime,
    _restore_tui_session,
    _tui_env,
    run_apex_tui,
)


class TestTuiEnv:
    def test_base_env(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_bun", lambda: None)
        env = _tui_env(tmp_path, 9876)
        assert env["APEX_HTTP_PORT"] == "9876"
        assert env["APEX"] == "1"
        assert env["APEX_PID"] == str(os.getpid())

    def test_prepends_local_bin_and_bun(self, tmp_path, monkeypatch):
        (tmp_path / "node_modules" / ".bin").mkdir(parents=True)
        bun_parent = tmp_path / "bunbin"
        bun_parent.mkdir()
        (bun_parent / "bun").write_text("")
        monkeypatch.setattr(tui_launcher, "_find_bun", lambda: str(bun_parent / "bun"))
        env = _tui_env(tmp_path, 1234)
        assert env["PATH"].startswith(str(bun_parent) + os.pathsep)
        assert str(tmp_path / "node_modules" / ".bin") + os.pathsep in env["PATH"]

    def test_windows_separator(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr(tui_launcher, "_find_bun", lambda: None)
        (tmp_path / "node_modules" / ".bin").mkdir(parents=True)
        env = _tui_env(tmp_path, 1)
        assert env["PATH"].startswith(str(tmp_path / "node_modules" / ".bin") + ";")


class TestFindFreePort:
    def test_returns_listening_port_range(self):
        port = _find_free_port()
        assert isinstance(port, int)
        assert 0 < port < 65536

    def test_valid_port(self):
        a, b = _find_free_port(), _find_free_port()
        assert 0 < a < 65536
        assert 0 < b < 65536


class TestRequireTuiDir:
    def test_found(self):
        with patch.object(tui_launcher, "_find_tui_dir", return_value=Path("/tui")):
            assert _require_tui_dir(MagicMock()) == Path("/tui")

    def test_missing_exits(self):
        ui = MagicMock()
        with (
            patch.object(tui_launcher, "_find_tui_dir", return_value=None),
            pytest.raises(SystemExit) as exc,
        ):
            _require_tui_dir(ui)
        assert exc.value.code == 1
        ui.print_error.assert_called_once()


class TestResolveTuiRuntime:
    def test_tsx_runtime(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_ensure_tsx", lambda d: "/fake/tsx")
        runtime, name = _resolve_tui_runtime(tmp_path, MagicMock())
        assert runtime == ["/fake/tsx", str(tmp_path / "src" / "App.tsx")]
        assert name == "Node.js + tsx"

    def test_tsx_via_install(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_ensure_tsx", lambda d: None)
        monkeypatch.setattr(tui_launcher, "_install_tsx", lambda d, ui: "/inst/tsx")
        runtime, name = _resolve_tui_runtime(tmp_path, MagicMock())
        assert runtime[0] == "/inst/tsx"
        assert name == "Node.js + tsx"

    def test_native_node_ts(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_ensure_tsx", lambda d: None)
        monkeypatch.setattr(tui_launcher, "_install_tsx", lambda d, ui: None)
        monkeypatch.setattr(tui_launcher, "_find_node", lambda: "/fake/node")
        runtime, name = _resolve_tui_runtime(tmp_path, MagicMock())
        assert runtime == [
            "/fake/node",
            "--experimental-strip-types",
            str(tmp_path / "src" / "App.tsx"),
        ]
        assert name == "Node.js (native TS)"

    def test_no_runtime_exits(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_ensure_tsx", lambda d: None)
        monkeypatch.setattr(tui_launcher, "_install_tsx", lambda d, ui: None)
        monkeypatch.setattr(tui_launcher, "_find_node", lambda: None)
        ui = MagicMock()
        with pytest.raises(SystemExit) as exc:
            _resolve_tui_runtime(tmp_path, ui)
        assert exc.value.code == 1
        ui.print_error.assert_called_once()


class TestRestoreTuiSession:
    def test_resume_last_session(self):
        agent, ui = MagicMock(), MagicMock()
        with patch.object(tui_launcher, "SessionManager") as mock_sm:
            sm = mock_sm.return_value
            sm.list_sessions.return_value = [{"name": "s1"}, {"name": "s2"}]
            _restore_tui_session(agent, ui, resume=True, session_id=None)
        sm.load.assert_called_once_with("s1", agent)
        assert "Resumed session: s1" in ui.print_success.call_args.args[0]

    def test_resume_no_sessions(self):
        with patch.object(tui_launcher, "SessionManager") as mock_sm:
            mock_sm.return_value.list_sessions.return_value = []
            _restore_tui_session(MagicMock(), MagicMock(), resume=True, session_id=None)
        mock_sm.return_value.load.assert_not_called()

    def test_explicit_session_id(self):
        agent, ui = MagicMock(), MagicMock()
        with patch.object(tui_launcher, "SessionManager") as mock_sm:
            _restore_tui_session(agent, ui, resume=False, session_id="abc")
        mock_sm.return_value.load.assert_called_once_with("abc", agent)
        assert "Loaded session: abc" in ui.print_success.call_args.args[0]

    def test_noop(self):
        with patch.object(tui_launcher, "SessionManager") as mock_sm:
            _restore_tui_session(MagicMock(), MagicMock(), resume=False, session_id=None)
        mock_sm.return_value.load.assert_not_called()


class TestRunApexTui:
    def _patches(self, setup_ok=True, process_ok=True, port=4567):
        tui_dir = Path("/fake/tui")
        return {
            "require": patch.object(tui_launcher, "_require_tui_dir", return_value=tui_dir),
            "pkg": patch.object(tui_launcher, "_patch_tui_package_json"),
            "setup": patch.object(tui_launcher, "_setup_tui_frontend", return_value=setup_ok),
            "runtime": patch.object(
                tui_launcher, "_resolve_tui_runtime", return_value=(["/bin/true"], "test")
            ),
            "restore": patch.object(tui_launcher, "_restore_tui_session"),
            "port": patch.object(tui_launcher, "_find_free_port", return_value=port),
            "start": patch.object(tui_launcher, "start_tui_server", return_value="server"),
            "stop": patch.object(tui_launcher, "stop_tui_server"),
            "proc": patch.object(tui_launcher, "_try_run_tui_process", return_value=process_ok),
        }

    def test_success_path(self):
        p = self._patches()
        agent = MagicMock(cwd="/proj", model="gpt-4o", current_agent="build")
        ui = MagicMock()
        with (
            p["require"],
            p["pkg"],
            p["setup"],
            p["runtime"],
            p["restore"] as mock_restore,
            p["port"],
            p["start"] as mock_start,
            p["stop"] as mock_stop,
            p["proc"],
        ):
            run_apex_tui(agent, ui, resume=True, session_id="s1")
        mock_start.assert_called_once_with(port=4567, agent=agent)
        mock_stop.assert_called_once_with("server")
        mock_restore.assert_called_once_with(agent, ui, True, "s1")

    def test_setup_failure_exits(self):
        p = self._patches(setup_ok=False)
        ui = MagicMock()
        with (
            p["require"],
            p["pkg"],
            p["setup"],
            pytest.raises(SystemExit) as exc,
        ):
            run_apex_tui(MagicMock(), ui)
        assert exc.value.code == 1
        ui.print_error.assert_called_once()

    def test_process_failure_exits_and_stops_server(self):
        p = self._patches(process_ok=False)
        ui = MagicMock()
        with (
            p["require"],
            p["pkg"],
            p["setup"],
            p["runtime"],
            p["restore"],
            p["port"],
            p["start"],
            p["stop"] as mock_stop,
            p["proc"],
            pytest.raises(SystemExit) as exc,
        ):
            run_apex_tui(MagicMock(), ui)
        assert exc.value.code == 1
        mock_stop.assert_called_once()


class TestTryRunTuiProcess:
    def test_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tui_launcher.time, "sleep", lambda s: None)
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(returncode=0, poll=MagicMock(return_value=0))
            assert (
                tui_launcher._try_run_tui_process(
                    tmp_path, (["/bin/true"], "test"), MagicMock(), 1234
                )
                is True
            )

    def test_failure_exit_code(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tui_launcher.time, "sleep", lambda s: None)
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(returncode=1, poll=MagicMock(return_value=1))
            assert (
                tui_launcher._try_run_tui_process(
                    tmp_path, (["/bin/false"], "test"), MagicMock(), 1234
                )
                is False
            )

    def test_executable_missing(self, tmp_path):
        ui = MagicMock()
        with patch("subprocess.Popen", side_effect=FileNotFoundError("gone")):
            assert tui_launcher._try_run_tui_process(tmp_path, (["/gone"], "x"), ui, 1) is False
        ui.print_error.assert_called_once()

    def test_generic_error(self, tmp_path):
        ui = MagicMock()
        with patch("subprocess.Popen", side_effect=RuntimeError("boom")):
            assert tui_launcher._try_run_tui_process(tmp_path, (["x"], "x"), ui, 1) is False
        ui.print_error.assert_called_once()
