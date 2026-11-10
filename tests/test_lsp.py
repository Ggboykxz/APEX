"""Tests for apex/lsp.py - LSP client and manager."""

from unittest.mock import MagicMock, patch

import pytest

from apex.lsp import LSPClient, LSPManager


def make_client(**kwargs):
    return LSPClient("/tmp/test", ["node", "server.js"], **kwargs)


class TestLSPClientInit:
    def test_init(self):
        client = LSPClient("/tmp/test", ["node", "server.js"], {"ENV": "val"})
        assert client.cwd == "/tmp/test"
        assert client.server_command == ["node", "server.js"]
        assert client.env == {"ENV": "val"}
        assert client.process is None
        assert client.request_id == 0
        assert client.capabilities == {}
        assert client._initialized is False

    def test_init_default_env(self):
        assert make_client().env == {}


class TestLSPClientStart:
    def test_start(self):
        client = make_client()
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_popen.return_value = mock_proc
            client.start()
        mock_popen.assert_called_once()
        assert client.process is mock_proc
        assert client._initialized is False
        kwargs = mock_popen.call_args.kwargs
        assert kwargs["cwd"] == "/tmp/test"
        assert kwargs["text"] is True

    def test_start_merges_env(self):
        client = make_client(env={"EXTRA": "1"})
        with patch("subprocess.Popen") as mock_popen:
            client.start()
        env = mock_popen.call_args.kwargs["env"]
        assert env["EXTRA"] == "1"


class TestLSPClientSendRequest:
    def test_send_request_no_process(self):
        with pytest.raises(RuntimeError, match="not running"):
            make_client()._send_request("test", {})

    def test_send_request(self):
        client = make_client()
        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = ""
        client.process = mock_proc
        result = client._send_request("test", {"key": "val"})
        assert result == {}
        assert client.request_id == 1
        payload = mock_proc.stdin.write.call_args.args[0].strip()
        assert '"method": "test"' in payload
        assert '"id": 1' in payload

    def test_read_response_empty(self):
        client = make_client()
        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = ""
        client.process = mock_proc
        assert client._read_response() == {}

    def test_read_response_valid(self):
        client = make_client()
        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = '{"jsonrpc": "2.0", "id": 1, "result": "ok"}'
        client.process = mock_proc
        assert client._read_response() == {"jsonrpc": "2.0", "id": 1, "result": "ok"}

    def test_read_response_skips_blank_lines(self):
        client = make_client()
        mock_proc = MagicMock()
        mock_proc.stdout.readline.side_effect = [
            "\n",
            '{"jsonrpc": "2.0", "id": 1, "result": 42}',
        ]
        client.process = mock_proc
        assert client._read_response() == {"jsonrpc": "2.0", "id": 1, "result": 42}

    def test_read_response_no_process(self):
        with pytest.raises(RuntimeError, match="not running"):
            make_client()._read_response()


class TestLSPClientLifecycle:
    def test_initialize(self):
        client = make_client()
        client.process = MagicMock()
        with patch.object(
            client,
            "_send_request",
            return_value={"result": {"capabilities": {"textDocument": True}}},
        ) as mock_send:
            client.initialize("/workspace")
        assert client.capabilities == {"textDocument": True}
        assert client._initialized is True
        assert mock_send.call_args_list[0].args[0] == "initialize"
        assert mock_send.call_args_list[1].args[0] == "initialized"

    def test_shutdown_initialized(self):
        client = make_client()
        client._initialized = True
        mock_proc = MagicMock()
        client.process = mock_proc
        with patch.object(client, "_send_request") as mock_send:
            client.shutdown()
        mock_send.assert_any_call("shutdown", {})
        mock_send.assert_any_call("exit", {})
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once()

    def test_shutdown_not_initialized(self):
        client = make_client()
        client._initialized = False
        mock_proc = MagicMock()
        client.process = mock_proc
        with patch.object(client, "_send_request") as mock_send:
            client.shutdown()
        mock_send.assert_not_called()
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once()


class TestLSPClientQueries:
    def test_position_params(self):
        client = make_client()
        assert client._position_params("file:///t.py", 10, 5) == {
            "textDocument": {"uri": "file:///t.py"},
            "position": {"line": 10, "character": 5},
        }

    def test_request_result_not_initialized(self):
        assert make_client()._request_result("test", {}) is None

    def test_request_result(self):
        client = make_client()
        client._initialized = True
        with patch.object(client, "_send_request", return_value={"result": "value"}) as mock_send:
            assert client._request_result("test", {}) == "value"
        mock_send.assert_called_once_with("test", {})

    def test_get_definitions(self):
        client = make_client()
        client._initialized = True
        locs = [{"uri": "file:///a.py", "range": {"start": {"line": 0}, "end": {"line": 0}}}]
        with patch.object(client, "_request_result", return_value=locs) as mock_rr:
            assert client.get_definitions("file:///t.py", 10, 5) == locs
        mock_rr.assert_called_once_with(
            "textDocument/definition",
            {"textDocument": {"uri": "file:///t.py"}, "position": {"line": 10, "character": 5}},
        )

    def test_get_definitions_not_list(self):
        client = make_client()
        client._initialized = True
        with patch.object(client, "_request_result", return_value=None):
            assert client.get_definitions("file:///t.py", 10, 5) == []

    def test_get_definitions_not_initialized(self):
        assert make_client().get_definitions("file:///t.py", 10, 5) == []

    def test_get_references(self):
        client = make_client()
        client._initialized = True
        refs = [{"uri": "file:///a.py"}]
        with patch.object(client, "_request_result", return_value=refs) as mock_rr:
            assert client.get_references("file:///t.py", 10, 5) == refs
        mock_rr.assert_called_once_with(
            "textDocument/references",
            {
                "textDocument": {"uri": "file:///t.py"},
                "position": {"line": 10, "character": 5},
                "context": {"includeDeclaration": True},
            },
        )

    def test_get_hover(self):
        client = make_client()
        client._initialized = True
        hover = {"contents": {"value": "hover text"}}
        with patch.object(client, "_request_result", return_value=hover):
            assert client.get_hover("file:///t.py", 10, 5) == hover

    def test_get_hover_not_dict(self):
        client = make_client()
        client._initialized = True
        with patch.object(client, "_request_result", return_value="plain"):
            assert client.get_hover("file:///t.py", 10, 5) is None

    def test_get_document_symbols(self):
        client = make_client()
        client._initialized = True
        symbols = [{"name": "func1", "kind": 12}]
        with patch.object(client, "_send_request", return_value={"result": symbols}) as mock_send:
            assert client.get_document_symbols("file:///t.py") == symbols
        mock_send.assert_called_once_with(
            "textDocument/documentSymbol", {"textDocument": {"uri": "file:///t.py"}}
        )

    def test_get_document_symbols_not_initialized(self):
        assert make_client().get_document_symbols("file:///t.py") == []

    def test_get_workspace_symbols(self):
        client = make_client()
        client._initialized = True
        symbols = [{"name": "func1", "kind": 12}]
        with patch.object(client, "_send_request", return_value={"result": symbols}) as mock_send:
            assert client.get_workspace_symbols("func") == symbols
        mock_send.assert_called_once_with("workspace/symbol", {"query": "func"})

    def test_get_workspace_symbols_not_initialized(self):
        assert make_client().get_workspace_symbols("func") == []

    def test_get_diagnostics(self):
        client = make_client()
        client._initialized = True
        items = [{"message": "error", "range": {"start": {"line": 0}}}]
        with patch.object(
            client, "_send_request", return_value={"result": {"items": items}}
        ) as mock_send:
            assert client.get_diagnostics("file:///t.py") == items
        mock_send.assert_called_once_with(
            "textDocument/diagnostic", {"textDocument": {"uri": "file:///t.py"}}
        )

    def test_get_diagnostics_not_initialized(self):
        assert make_client().get_diagnostics("file:///t.py") == []


class TestLSPManager:
    def test_init(self):
        mgr = LSPManager("/tmp/test")
        assert mgr.cwd == "/tmp/test"
        assert mgr.servers == {}
        assert mgr._config == {}

    def test_load_config(self):
        mgr = LSPManager("/tmp/test")
        mgr.load_config({"servers": []})
        assert mgr._config == {"servers": []}

    def test_add_server(self):
        mgr = LSPManager("/tmp/test")
        mgr.add_server("test", ["node", "server.js"], {"ENV": "val"})
        client = mgr.servers["test"]
        assert isinstance(client, LSPClient)
        assert client.cwd == "/tmp/test"
        assert client.server_command == ["node", "server.js"]
        assert client.env == {"ENV": "val"}

    def test_start_all(self):
        mgr = LSPManager("/tmp/test")
        client1, client2 = MagicMock(), MagicMock()
        mgr.servers = {"s1": client1, "s2": client2}
        mgr.start_all()
        client1.start.assert_called_once()
        client1.initialize.assert_called_once_with("/tmp/test")
        client2.start.assert_called_once()
        client2.initialize.assert_called_once_with("/tmp/test")

    def test_start_all_handles_errors(self, capsys):
        mgr = LSPManager("/tmp/test")
        client1, client2 = MagicMock(), MagicMock()
        client1.start.side_effect = Exception("boom")
        mgr.servers = {"s1": client1, "s2": client2}
        mgr.start_all()
        client1.initialize.assert_not_called()
        client2.start.assert_called_once()
        client2.initialize.assert_called_once_with("/tmp/test")
        assert "Failed to start LSP server 's1'" in capsys.readouterr().out

    def test_stop_all(self):
        mgr = LSPManager("/tmp/test")
        client1, client2 = MagicMock(), MagicMock()
        mgr.servers = {"s1": client1, "s2": client2}
        mgr.stop_all()
        client1.shutdown.assert_called_once()
        client2.shutdown.assert_called_once()

    def test_stop_all_handles_errors(self):
        mgr = LSPManager("/tmp/test")
        client1, client2 = MagicMock(), MagicMock()
        client1.shutdown.side_effect = Exception("boom")
        mgr.servers = {"s1": client1, "s2": client2}
        mgr.stop_all()
        client2.shutdown.assert_called_once()

    def test_get_tools(self):
        mgr = LSPManager("/tmp/test")
        client = MagicMock()
        client._initialized = True
        mgr.servers = {"test": client}
        tools = mgr.get_tools()
        assert set(tools) == {
            "lsp_test_definition",
            "lsp_test_references",
            "lsp_test_hover",
            "lsp_test_diagnostics",
        }
        assert tools["lsp_test_definition"]["description"] == "Go to definition (LSP: test)"
        assert tools["lsp_test_definition"]["parameters"]["required"] == ["path"]

    def test_get_tools_not_initialized(self):
        mgr = LSPManager("/tmp/test")
        client = MagicMock()
        client._initialized = False
        mgr.servers = {"test": client}
        assert mgr.get_tools() == {}

    def test_call_tool_definition(self):
        import os

        mgr = LSPManager("/tmp/test")
        client = MagicMock()
        client.get_definitions.return_value = [
            {"uri": "file:///a.py", "range": {"start": {"line": 3}}}
        ]
        mgr.servers = {"test": client}
        result = mgr.call_tool("lsp_test_definition", {"path": "/test.py", "line": 1, "column": 2})
        assert result == {"definitions": [{"uri": "file:///a.py", "range": {"start": {"line": 3}}}]}
        client.get_definitions.assert_called_once_with(
            f"file://{os.path.abspath('/test.py')}", 1, 2
        )

    def test_call_tool_references(self):
        import os

        mgr = LSPManager("/tmp/test")
        client = MagicMock()
        client.get_references.return_value = [{"uri": "file:///a.py", "range": {}}]
        mgr.servers = {"test": client}
        result = mgr.call_tool("lsp_test_references", {"path": "t.py"})
        assert result == {"references": [{"uri": "file:///a.py", "range": {}}]}
        client.get_references.assert_called_once_with(f"file://{os.path.abspath('t.py')}", 0, 0)

    def test_call_tool_hover_value(self):
        mgr = LSPManager("/tmp/test")
        client = MagicMock()
        client.get_hover.return_value = {"contents": {"value": "hover text"}}
        mgr.servers = {"test": client}
        assert mgr.call_tool("lsp_test_hover", {"path": "/t.py"}) == {"content": "hover text"}

    def test_call_tool_hover_string(self):
        mgr = LSPManager("/tmp/test")
        client = MagicMock()
        client.get_hover.return_value = {"contents": "plain text"}
        mgr.servers = {"test": client}
        assert mgr.call_tool("lsp_test_hover", {"path": "/t.py"}) == {"content": "plain text"}

    def test_call_tool_hover_empty(self):
        mgr = LSPManager("/tmp/test")
        client = MagicMock()
        client.get_hover.return_value = {}
        mgr.servers = {"test": client}
        assert mgr.call_tool("lsp_test_hover", {"path": "/t.py"}) == {"content": ""}

    def test_call_tool_diagnostics(self):
        mgr = LSPManager("/tmp/test")
        client = MagicMock()
        client.get_diagnostics.return_value = [{"message": "err", "range": {}, "severity": 1}]
        mgr.servers = {"test": client}
        result = mgr.call_tool("lsp_test_diagnostics", {"path": "/t.py"})
        assert result == {"diagnostics": [{"message": "err", "range": {}, "severity": 1}]}

    def test_call_tool_unknown_server(self):
        mgr = LSPManager("/tmp/test")
        assert mgr.call_tool("lsp_nope_definition", {"path": "/t.py"}) == {
            "error": "Unknown LSP server: nope"
        }

    def test_call_tool_unknown_operation(self):
        mgr = LSPManager("/tmp/test")
        client = MagicMock()
        client._initialized = True
        mgr.servers = {"test": client}
        assert mgr.call_tool("lsp_test_fly", {"path": "/t.py"}) == {
            "error": "Unknown operation: fly"
        }

    def test_call_tool_invalid_name(self):
        mgr = LSPManager("/tmp/test")
        assert mgr.call_tool("lsp_definition", {"path": "/t.py"}) == {
            "error": "Invalid LSP tool name"
        }

    def test_call_tool_catches_exception(self):
        mgr = LSPManager("/tmp/test")
        client = MagicMock()
        client.get_definitions.side_effect = RuntimeError("boom")
        mgr.servers = {"test": client}
        result = mgr.call_tool("lsp_test_definition", {"path": "/t.py"})
        assert result == {"error": "boom"}


class TestGetLSPManager:
    def test_creates_and_caches(self):
        import apex.lsp

        original = apex.lsp._lsp_manager
        apex.lsp._lsp_manager = None
        try:
            first = apex.lsp.get_lsp_manager("/tmp/test")
            second = apex.lsp.get_lsp_manager("/other")
            assert first is second
            assert first.cwd == "/tmp/test"
        finally:
            apex.lsp._lsp_manager = original
