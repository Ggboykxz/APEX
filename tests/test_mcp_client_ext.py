"""Tests for apex/mcp_client_ext.py."""

from unittest.mock import MagicMock, patch

import pytest

from apex.mcp_client_ext import (
    MCPConnection,
    MCPConnectionPool,
    MCPServerConfig,
    MCPTransportError,
)


class TestMCPTransportError:
    def test_is_exception(self):
        assert issubclass(MCPTransportError, Exception)
        err = MCPTransportError("test error")
        assert str(err) == "test error"


class TestMCPServerConfig:
    def test_defaults(self):
        cfg = MCPServerConfig(name="test", type="remote", url="http://localhost:1234")
        assert cfg.name == "test"
        assert cfg.type == "remote"
        assert cfg.url == "http://localhost:1234"
        assert cfg.command is None
        assert cfg.environment == {}
        assert cfg.headers == {}

    def test_with_command(self):
        cfg = MCPServerConfig(
            name="local",
            type="local",
            command=("npx", "@modelcontextprotocol/server-filesystem"),
            environment={"KEY": "val"},
            headers={"Authorization": "Bearer token"},
        )
        assert cfg.name == "local"
        assert cfg.type == "local"
        assert cfg.url is None
        assert cfg.command == ("npx", "@modelcontextprotocol/server-filesystem")
        assert cfg.environment == {"KEY": "val"}
        assert cfg.headers == {"Authorization": "Bearer token"}


class TestMCPConnection:
    def test_init(self):
        cfg = MCPServerConfig(name="test", type="remote", url="http://localhost:1234")
        conn = MCPConnection(cfg)
        assert conn.config is cfg
        assert conn.session_id is None
        assert conn.protocol_version is None
        assert conn.server_info is None
        assert conn._closed is False

    def test_open_not_remote(self):
        cfg = MCPServerConfig(name="local", type="local", command=("cmd",))
        conn = MCPConnection(cfg)
        with pytest.raises(MCPTransportError, match="remote url"):
            conn.open()

    def test_open_closed(self):
        cfg = MCPServerConfig(name="test", type="remote", url="http://localhost:1234")
        conn = MCPConnection(cfg)
        conn._closed = True
        with pytest.raises(MCPTransportError, match="connection is closed"):
            conn.open()

    def test_close(self):
        cfg = MCPServerConfig(name="test", type="remote", url="http://localhost:1234")
        conn = MCPConnection(cfg)
        conn.close()
        assert conn._closed is True

    def test_post_jsonrpc_non_notify(self):
        cfg = MCPServerConfig(name="test", type="remote", url="http://localhost:1234")
        conn = MCPConnection(cfg)
        with patch.object(conn, "_post_jsonrpc", return_value={"id": 1, "result": {}}) as mock_post:
            result = conn._post_jsonrpc("method", {"key": "val"})
            assert result == {"id": 1, "result": {}}
            mock_post.assert_called_once_with("method", {"key": "val"})

    def test_parse_response_json(self):
        result = MCPConnection._parse_response(
            '{"jsonrpc": "2.0", "id": 1, "result": {"ok": true}}'
        )
        assert result == {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}

    def test_parse_response_invalid_json(self):
        result = MCPConnection._parse_response("not json at all")
        assert result == {}

    def test_parse_response_sse(self):
        body = 'event: message\ndata: {"jsonrpc": "2.0", "id": 1, "result": {"ok": true}}\n\n'
        result = MCPConnection._parse_response(body)
        assert result == {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}

    def test_parse_response_sse_no_data(self):
        result = MCPConnection._parse_response("event: message\n\n")
        assert result == {}

    @patch("urllib.request.urlopen")
    def test_post_jsonrpc_success(self, mock_urlopen):
        cfg = MCPServerConfig(name="test", type="remote", url="http://localhost:1234")
        conn = MCPConnection(cfg)
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"jsonrpc": "2.0", "id": 1, "result": {"ok": true}}'
        mock_response.headers = {"Mcp-Session-Id": "sess-123"}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = conn._post_jsonrpc("test_method", {"key": "val"}, notify=False)
        assert result == {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
        assert conn.session_id == "sess-123"

    @patch("urllib.request.urlopen")
    def test_post_jsonrpc_url_error(self, mock_urlopen):
        cfg = MCPServerConfig(name="test", type="remote", url="http://localhost:1234")
        conn = MCPConnection(cfg)
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        with pytest.raises(MCPTransportError, match="transport error"):
            conn._post_jsonrpc("test_method", {"key": "val"}, notify=False)

    @patch("urllib.request.urlopen")
    def test_post_jsonrpc_notify(self, mock_urlopen):
        cfg = MCPServerConfig(name="test", type="remote", url="http://localhost:1234")
        conn = MCPConnection(cfg)
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_urlopen.return_value.__enter__.return_value = mock_response
        result = conn._post_jsonrpc("notify_method", {"key": "val"}, notify=True)
        assert result is None

    def test_list_tools_no_result(self):
        conn = MCPConnection.__new__(MCPConnection)
        conn._post_jsonrpc = MagicMock(return_value={})
        result = conn.list_tools()
        assert result == []

    def test_list_tools_with_result(self):
        conn = MCPConnection.__new__(MCPConnection)
        conn._post_jsonrpc = MagicMock(return_value={"result": {"tools": [{"name": "tool1"}]}})
        result = conn.list_tools()
        assert result == [{"name": "tool1"}]

    def test_call_tool_no_result(self):
        conn = MCPConnection.__new__(MCPConnection)
        conn._post_jsonrpc = MagicMock(return_value={})
        result = conn.call_tool("tool1", {})
        assert result is None

    def test_call_tool_with_result(self):
        conn = MCPConnection.__new__(MCPConnection)
        conn._post_jsonrpc = MagicMock(return_value={"result": {"output": "done"}})
        result = conn.call_tool("tool1", {})
        assert result == {"output": "done"}


class TestMCPConnectionPool:
    def test_init(self):
        pool = MCPConnectionPool()
        assert pool._connections == {}

    def test_get_nonexistent(self):
        pool = MCPConnectionPool()
        assert pool.get("nonexistent") is None

    def test_add_and_get(self):
        pool = MCPConnectionPool()
        conn = MagicMock()
        conn.config.name = "test-server"
        pool.add(conn)
        assert pool.get("test-server") is conn

    def test_add_replaces_existing(self):
        pool = MCPConnectionPool()
        old_conn = MagicMock()
        old_conn.config.name = "test-server"
        new_conn = MagicMock()
        new_conn.config.name = "test-server"
        pool.add(old_conn)
        pool.add(new_conn)
        old_conn.close.assert_called_once()
        assert pool.get("test-server") is new_conn

    def test_remove(self):
        pool = MCPConnectionPool()
        conn = MagicMock()
        conn.config.name = "test-server"
        pool.add(conn)
        pool.remove("test-server")
        assert pool.get("test-server") is None
        conn.close.assert_called_once()

    def test_remove_nonexistent(self):
        pool = MCPConnectionPool()
        pool.remove("nonexistent")

    def test_close_all(self):
        pool = MCPConnectionPool()
        conn1 = MagicMock()
        conn1.config.name = "server1"
        conn2 = MagicMock()
        conn2.config.name = "server2"
        pool.add(conn1)
        pool.add(conn2)
        pool.close_all()
        conn1.close.assert_called_once()
        conn2.close.assert_called_once()
        assert pool._connections == {}
