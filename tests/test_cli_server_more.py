"""Tests for apex/cli_server.py — web, debug, attach, gateway commands."""

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apex import cli_server as cs


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


def _ns(**kw):
    base = {
        "hostname": None,
        "port": None,
        "url": None,
        "cwd": None,
        "allow_tool": None,
        "raw_args": [],
    }
    base.update(kw)
    return argparse.Namespace(**base)


class TestCmdWeb:
    def test_success_opens_browser(self):
        ui = MagicMock()
        with (
            patch.object(cs, "_start_http_server") as mock_start,
            patch("webbrowser.open"),
        ):
            cs._cmd_web(_ns(hostname="0.0.0.0", port=8080), ui)
        mock_start.assert_called_once()
        args = mock_start.call_args
        assert args.kwargs["open_browser"] is True

    def test_failure_exits(self):
        ui = MagicMock()
        with (
            patch.object(cs, "_start_http_server", side_effect=RuntimeError("boom")),
            pytest.raises(SystemExit) as exc,
        ):
            cs._cmd_web(_ns(), ui)
        assert exc.value.code == 1
        ui.print_error.assert_called_once()


class TestStartHttpServerWeb:
    def test_opens_browser(self):
        ui = MagicMock()
        with (
            patch.object(cs, "_resolve_endpoint", return_value=("127.0.0.1", 8080)),
            patch.object(cs, "Agent"),
            patch("webbrowser.open") as mock_br,
            patch("asyncio.run"),
        ):
            cs._start_http_server(_ns(), ui, open_browser=True)
        mock_br.assert_called_once_with("http://127.0.0.1:8080")
        assert "Opening" in ui.print_success.call_args.args[0]

    def test_server_message_when_headless(self):
        ui = MagicMock()
        with (
            patch.object(cs, "_resolve_endpoint", return_value=("127.0.0.1", 9000)),
            patch.object(cs, "Agent"),
            patch("asyncio.run"),
        ):
            cs._start_http_server(_ns(), ui, open_browser=False)
        assert "Server running at http://127.0.0.1:9000" in ui.print_success.call_args.args[0]


class TestCmdDebug:
    def test_config_subcommand(self, fake_home):
        ui = MagicMock()
        raw = {"model": "gpt-4o"}
        with patch("apex.config_v2.apex_config.raw", return_value=raw):
            cs._cmd_debug(_ns(raw_args=["config"]), ui)
        printed = "".join(str(c) for c in ui.console.print.call_args_list)
        assert "APEX v" in printed
        assert "gpt-4o" in printed

    def test_unknown_subcommand(self):
        ui = MagicMock()
        cs._cmd_debug(_ns(raw_args=["nope"]), ui)
        assert "unknown subcommand" in ui.print_info.call_args.args[0]

    def test_default_config_when_no_args(self, fake_home):
        ui = MagicMock()
        with patch("apex.config_v2.apex_config.raw", return_value={}):
            cs._cmd_debug(_ns(raw_args=[]), ui)
        assert "Resolved config" in "".join(str(c) for c in ui.console.print.call_args_list)


class TestMcpList:
    def test_empty(self):
        ui = MagicMock()
        mgr = MagicMock()
        mgr.list_servers.return_value = []
        with patch("apex.mcp.mcp_manager", mgr):
            cs._mcp_list(ui)
        ui.print_info.assert_called_once_with("No MCP servers configured")

    def test_table(self):
        ui = MagicMock()
        server = MagicMock()
        server.name = "gh"
        server.command = "npx server-gh"
        server.enabled = True
        mgr = MagicMock()
        mgr.list_servers.return_value = [server]
        with (
            patch("apex.mcp.mcp_manager", mgr),
            patch.object(cs, "Table") as mock_table,
        ):
            cs._mcp_list(ui)
        table = mock_table.return_value
        table.add_row.assert_called_once_with("gh", "npx server-gh", "✓")


class TestMcpAdd:
    @pytest.mark.parametrize(
        "inputs",
        [
            ["  ", "ignored"],
            ["srv", "  "],
        ],
    )
    def test_required_fields_exit(self, inputs):
        ui = MagicMock()
        ui.input.side_effect = inputs
        with (
            patch("apex.mcp.mcp_manager"),
            pytest.raises(SystemExit) as exc,
        ):
            cs._mcp_add(ui)
        assert exc.value.code == 1
        ui.print_error.assert_called_once()

    def test_success_with_env(self):
        ui = MagicMock()
        ui.input.side_effect = ["srv", "npx github-srv --x", "KEY=val,GLOBAL=1"]
        with (
            patch("apex.mcp.MCPServerConfig") as mock_cfg,
            patch("apex.mcp.mcp_manager") as mock_mgr,
        ):
            cs._mcp_add(ui)
        cfg = mock_cfg.return_value
        mock_mgr.add_server.assert_called_once_with(cfg)
        assert "added" in ui.print_success.call_args.args[0]


class TestMcpServe:
    def test_serve_exits_through_server(self):
        with (
            patch("apex.mcp_server.serve", return_value=0) as mock_serve,
            pytest.raises(SystemExit) as exc,
        ):
            cs._mcp_serve(_ns(cwd="/tmp", allow_tool=["read_file"]))
        assert exc.value.code == 0
        mock_serve.assert_called_once_with(cwd=Path("/tmp"), allow_tools=["read_file"])

    def test_serve_defaults(self):
        with (
            patch("apex.mcp_server.serve", return_value=0),
            pytest.raises(SystemExit),
        ):
            cs._mcp_serve(_ns(cwd=None, allow_tool=None))


class TestCmdMcpServeDispatch:
    def test_serve_subcommand(self):
        with patch.object(cs, "_mcp_serve") as mock_serve:
            cs._cmd_mcp(_ns(mcp_subcommand="serve"), MagicMock())
        mock_serve.assert_called_once()


class TestCmdAttach:
    def test_missing_url(self):
        ui = MagicMock()
        with pytest.raises(SystemExit) as exc:
            cs._cmd_attach(_ns(url=None), ui)
        assert exc.value.code == 1
        assert "Usage:" in ui.print_error.call_args.args[0]

    def test_success(self):
        ui = MagicMock()
        agent = MagicMock()
        with (
            patch.object(cs, "apex_config") as cfg,
            patch.object(cs, "Agent", return_value=agent),
            patch.object(cs, "run_apex_tui") as mock_tui,
        ):
            cs._cmd_attach(_ns(url="https://backend.example"), ui)
        cfg.set.assert_called_once_with("remote_url", "https://backend.example")
        mock_tui.assert_called_once_with(agent, ui)


class TestRegisterPluginModule:
    def test_writes_yaml(self, fake_home):
        cs._register_plugin_module("myplugin")
        out = fake_home / ".apex" / "plugins.yaml"
        assert out.exists()
        import yaml

        data = yaml.safe_load(out.read_text())
        assert data["plugins"]["myplugin"]["enabled"] is True

    def test_reuses_existing(self, fake_home):
        out = fake_home / ".apex" / "plugins.yaml"
        out.parent.mkdir(parents=True)
        out.write_text("plugins:\n  other:\n    enabled: true\n")
        cs._register_plugin_module("mine")
        import yaml

        data = yaml.safe_load(out.read_text())
        assert set(data["plugins"]) == {"other", "mine"}


class TestInstallPlugin:
    def test_pip_failure_warns(self):
        ui = MagicMock()
        result = MagicMock(returncode=1, stderr="boom stderr")
        with (
            patch("subprocess.run", return_value=result),
            patch.object(cs, "_register_plugin_module"),
            patch("apex.plugins.load_plugins_from_config"),
        ):
            cs._install_plugin("pkg", ui)
        assert "returned non-zero" in ui.print_warning.call_args.args[0]

    def test_success(self):
        ui = MagicMock()
        with (
            patch("subprocess.run", return_value=MagicMock(returncode=0)),
            patch.object(cs, "_register_plugin_module") as mock_reg,
            patch("apex.plugins.load_plugins_from_config"),
        ):
            cs._install_plugin("pkg", ui)
        mock_reg.assert_called_once_with("pkg")
        assert "installed and loaded" in ui.print_success.call_args.args[0]

    def test_exception(self):
        ui = MagicMock()
        with (
            patch("subprocess.run", side_effect=RuntimeError("spawn failed")),
            patch.object(cs, "_register_plugin_module"),
            patch("apex.plugins.load_plugins_from_config"),
        ):
            cs._install_plugin("pkg", ui)
        ui.print_error.assert_called_once()


class TestGatewayStart:
    def test_missing_keys_exits(self):
        ui = MagicMock()
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(SystemExit) as exc,
        ):
            cs._gateway_start(ui)
        assert exc.value.code == 1
        ui.print_error.assert_called_once()

    def test_runs_server(self):
        ui = MagicMock()
        server = MagicMock()
        with (
            patch.dict("os.environ", {"OPENROUTER_API_KEY": "k"}, clear=False),
            patch("apex.gateway.GatewayServer", return_value=server) as mock_gs,
            patch("apex.gateway.config.GatewayConfig"),
            patch("asyncio.new_event_loop") as mock_loop,
            patch("asyncio.set_event_loop"),
        ):
            cs._gateway_start(ui)
        mock_gs.assert_called_once()
        loop = mock_loop.return_value
        loop.run_until_complete.assert_any_call(server.start())
        loop.run_until_complete.assert_any_call(server.stop())
        loop.close.assert_called_once()

    def test_exception_exits(self):
        ui = MagicMock()
        with (
            patch.dict("os.environ", {"APEX_GATEWAY_KEY": "k"}, clear=False),
            patch("apex.gateway.GatewayServer", side_effect=RuntimeError("boom")),
            patch("apex.gateway.config.GatewayConfig"),
            pytest.raises(SystemExit) as exc,
        ):
            cs._gateway_start(ui)
        assert exc.value.code == 1
        ui.print_error.assert_called_once()


def _gateway_stub(server):
    """A GatewayServer stub whose auth store is the given mock."""
    return (
        patch("apex.gateway.GatewayServer", return_value=server),
        patch("apex.gateway.config.GatewayConfig"),
    )


class TestGatewayKey:
    def test_generates_key(self):
        ui = MagicMock()
        server = MagicMock()
        server.auth.generate_key.return_value = "sk-new"
        stub_server, stub_config = _gateway_stub(server)
        with stub_server, stub_config:
            cs._gateway_key(["key", "pro", "ci"], ui)
        server.auth.generate_key.assert_called_once_with("pro", "ci")
        assert "sk-new" in ui.print_info.call_args.args[0]

    def test_default_tier_and_label(self):
        ui = MagicMock()
        server = MagicMock()
        server.auth.generate_key.return_value = "sk-new"
        stub_server, stub_config = _gateway_stub(server)
        with stub_server, stub_config:
            cs._gateway_key(["key"], ui)
        server.auth.generate_key.assert_called_once_with("free", "")


class TestGatewayStatus:
    def test_empty(self):
        ui = MagicMock()
        server = MagicMock()
        server.auth.list_keys.return_value = []
        stub_server, stub_config = _gateway_stub(server)
        with stub_server, stub_config:
            cs._gateway_status(ui)
        ui.print_info.assert_called_once_with("No API keys registered")

    def test_lists_keys(self):
        ui = MagicMock()
        server = MagicMock()
        server.auth.list_keys.return_value = [
            {"key_id": "k1", "tier": "free", "label": "ci", "is_active": True}
        ]
        with (
            patch("apex.gateway.GatewayServer", return_value=server),
            patch("apex.gateway.config.GatewayConfig"),
        ):
            cs._gateway_status(ui)
        joined = " ".join(str(c) for c in ui.print_info.call_args_list)
        assert "k1" in joined
        assert "active" in joined


class TestCmdGatewayDispatch:
    def test_start_dispatch(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["apex", "gateway", "start"])
        with patch.object(cs, "_gateway_start") as mock_start:
            cs._cmd_gateway(_ns(), MagicMock())
        mock_start.assert_called_once()

    def test_key_dispatch(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["apex", "gateway", "key", "pro"])
        with patch.object(cs, "_gateway_key") as mock_key:
            cs._cmd_gateway(_ns(), MagicMock())
        mock_key.assert_called_once_with(["key", "pro"], mock_key.call_args.args[1])

    def test_status_dispatch(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["apex", "gateway", "status"])
        with patch.object(cs, "_gateway_status") as mock_status:
            cs._cmd_gateway(_ns(), MagicMock())
        mock_status.assert_called_once()

    def test_default_help(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["apex", "gateway"])
        with patch.object(cs, "_gateway_help") as mock_help:
            cs._cmd_gateway(_ns(), MagicMock())
        mock_help.assert_called_once()
