"""Tests for apex/cli_server.py"""

from unittest.mock import MagicMock, patch

import pytest

from apex import cli_server


class TestResolveEndpoint:
    def test_explicit(self):
        args = MagicMock()
        args.hostname = "0.0.0.0"
        args.port = 9090
        host, port = cli_server._resolve_endpoint(args)
        assert host == "0.0.0.0"
        assert port == 9090


class TestStartHttpServer:
    @patch("apex.cli_server._start_http_server")
    def test_start(self, mock_start):
        args = MagicMock()
        args.hostname = "127.0.0.1"
        args.port = 8080
        ui = MagicMock()
        cli_server._start_http_server(args, ui, open_browser=False)
        mock_start.assert_called_once_with(args, ui, open_browser=False)


class TestCmdServe:
    def test_success(self):
        ui = MagicMock()
        args = MagicMock()
        args.hostname = None
        args.port = None
        with patch("apex.cli_server._start_http_server") as mock_start:
            cli_server._cmd_serve(args, ui)
            mock_start.assert_called_once()

    def test_failure(self):
        ui = MagicMock()
        args = MagicMock()
        with patch("apex.cli_server._start_http_server", side_effect=Exception("fail")):
            try:
                cli_server._cmd_serve(args, ui)
            except SystemExit:
                pass
        ui.print_error.assert_called()


class TestParseMcpEnv:
    def test_empty(self):
        assert cli_server._parse_mcp_env("") == {}
        assert cli_server._parse_mcp_env(None) == {}

    def test_single(self):
        assert cli_server._parse_mcp_env("KEY=VAL") == {"KEY": "VAL"}

    def test_multiple(self):
        assert cli_server._parse_mcp_env("A=1,B=2,C=3") == {"A": "1", "B": "2", "C": "3"}


class TestCmdMcp:
    def test_list(self):
        ui = MagicMock()
        args = MagicMock()
        args.mcp_subcommand = "list"
        with patch("apex.mcp.mcp_manager") as mock_mgr:
            mock_mgr.list_servers.return_value = []
            cli_server._cmd_mcp(args, ui)
            ui.print_info.assert_called()

    def test_add(self):
        ui = MagicMock()
        ui.input.side_effect = ["test-server", "npx -y @mcp/server", ""]
        args = MagicMock()
        args.mcp_subcommand = "add"
        with patch("apex.mcp.mcp_manager") as mock_mgr:
            mock_mgr.list_servers.return_value = []
            with patch("apex.mcp.MCPServerConfig") as mock_cfg:
                cli_server._cmd_mcp(args, ui)
                mock_cfg.assert_called_once()

    def test_auth(self):
        ui = MagicMock()
        args = MagicMock()
        args.mcp_subcommand = "auth"
        args.mcp_name = "test-server"
        cli_server._cmd_mcp(args, ui)
        ui.print_success.assert_called_with("Authenticated with MCP server: test-server")

    def test_unknown(self):
        ui = MagicMock()
        args = MagicMock()
        args.mcp_subcommand = "invalid"
        with pytest.raises(SystemExit):
            cli_server._cmd_mcp(args, ui)


class TestCmdPlugin:
    def test_list(self):
        ui = MagicMock()
        args = MagicMock()
        args.raw_args = []
        with patch("apex.plugins.plugin_manager") as mock_pm:
            mock_pm.list_plugins.return_value = []
            cli_server._cmd_plugin(args, ui)
            ui.print_info.assert_called()

    def test_install(self):
        ui = MagicMock()
        args = MagicMock()
        args.raw_args = ["test-module"]
        with patch("apex.cli_server._install_plugin") as mock_install:
            cli_server._cmd_plugin(args, ui)
            mock_install.assert_called_once_with("test-module", ui)


class TestCmdGateway:
    def test_help(self):
        ui = MagicMock()
        args = MagicMock()
        args.raw_args = []
        cli_server._cmd_gateway(args, ui)
        ui.print_info.assert_called()
