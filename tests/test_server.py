"""Comprehensive tests for apex.server — targeting 100% line coverage."""

import asyncio
import hashlib
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apex.server import APEXClient, APEXServer, APIKeyManager, run_server


# =========================================================================
# Helper: async-iterable mock WebSocket for handle_websocket tests
# =========================================================================

class _AsyncIterableWS:
    """Mock WebSocket that acts as an async iterable of messages."""
    def __init__(self, messages=None):
        self.messages = messages or []
        self.sent = []
        self._idx = 0
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self.messages):
            raise StopAsyncIteration
        msg = self.messages[self._idx]
        self._idx += 1
        return msg

    async def send_json(self, data):
        self.sent.append(data)

    async def close(self):
        self.closed = True


class _BrokenWS:
    """WebSocket that raises on send_json."""
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration

    async def send_json(self, data):
        raise ConnectionError("connection failed")

    async def close(self):
        self.closed = True


# =========================================================================
# APEXClient tests
# =========================================================================

class TestAPEXClientInit:
    def test_init_defaults(self):
        client = APEXClient("c1")
        assert client.id == "c1"
        assert client.name == "anonymous"
        assert client.model == "gpt-4o-mini"
        assert client.agent_mode == "build"
        assert client.token is None

    def test_init_custom(self):
        client = APEXClient("c2", name="alice", token="tok123")
        assert client.id == "c2"
        assert client.name == "alice"
        assert client.token == "tok123"

    def test_connected_at_set(self):
        client = APEXClient("c3")
        assert client.connected_at is not None
        assert client.last_activity is not None


class TestAPEXClientRateCheck:
    def test_rate_check_allows_under_limit(self):
        client = APEXClient("rc1")
        for _ in range(10):
            assert client.rate_check() is True

    def test_rate_check_blocks_over_limit(self):
        client = APEXClient("rc2")
        client._rate_limit = 3
        if "rc2" in client._request_times:
            del client._request_times["rc2"]
        assert client.rate_check() is True
        assert client.rate_check() is True
        assert client.rate_check() is True
        assert client.rate_check() is False

    def test_rate_check_cleans_old_entries(self):
        client = APEXClient("rc3")
        client._rate_limit = 2
        if "rc3" in client._request_times:
            del client._request_times["rc3"]
        assert client.rate_check() is True
        assert client.rate_check() is True
        assert client.rate_check() is False

    def test_rate_check_creates_list_for_new_id(self):
        client = APEXClient("rc4")
        if "rc4" in client._request_times:
            del client._request_times["rc4"]
        assert client.rate_check() is True


class TestAPEXClientToDict:
    def test_to_dict_keys(self):
        client = APEXClient("c4", name="bob")
        d = client.to_dict()
        assert d["id"] == "c4"
        assert d["name"] == "bob"
        assert "connected_at" in d
        assert "last_activity" in d
        assert d["model"] == "gpt-4o-mini"
        assert d["agent_mode"] == "build"


# =========================================================================
# APIKeyManager tests
# =========================================================================

class TestAPIKeyManager:
    def test_no_auth_by_default(self):
        km = APIKeyManager()
        assert km._require_auth is False
        assert km.is_valid("anything") is True
        assert km.is_valid("") is True

    def test_auth_with_tokens_env(self, monkeypatch):
        monkeypatch.setenv("APEX_SERVER_TOKENS", "tok1,tok2")
        km = APIKeyManager()
        assert km._require_auth is True
        assert km.is_valid("tok1") is True
        assert km.is_valid("tok2") is True
        assert km.is_valid("bad") is False
        assert km.is_valid("") is False

    def test_auth_require_env(self, monkeypatch):
        monkeypatch.setenv("APEX_REQUIRE_AUTH", "true")
        km = APIKeyManager()
        assert km._require_auth is True
        assert km.is_valid("anything") is False

    def test_invalid_token_with_auth(self, monkeypatch):
        monkeypatch.setenv("APEX_SERVER_TOKENS", "valid_token")
        km = APIKeyManager()
        assert km.is_valid("invalid") is False

    def test_empty_token_with_auth(self, monkeypatch):
        monkeypatch.setenv("APEX_SERVER_TOKENS", "valid_token")
        km = APIKeyManager()
        assert km.is_valid("") is False

    def test_empty_tokens_env_ignored(self, monkeypatch):
        monkeypatch.setenv("APEX_SERVER_TOKENS", "")
        km = APIKeyManager()
        assert km._require_auth is False

    def test_whitespace_tokens_ignored(self, monkeypatch):
        monkeypatch.setenv("APEX_SERVER_TOKENS", " , , ")
        km = APIKeyManager()
        assert km._require_auth is False


# =========================================================================
# APEXServer tests
# =========================================================================

class TestAPEXServerInit:
    def test_defaults(self):
        server = APEXServer()
        assert server.host == "127.0.0.1"
        assert server.port == 8080
        assert server.clients == {}
        assert server._agent is None
        assert len(server._websockets) == 0
        assert server._runner is None

    def test_custom(self):
        server = APEXServer(host="0.0.0.0", port=9999)
        assert server.host == "0.0.0.0"
        assert server.port == 9999


class TestAPEXServerSetAgent:
    def test_set_agent(self, tmp_path):
        from apex.agent import Agent
        from apex.config import Config

        config = Config(config_path=tmp_path / "cfg.json")
        agent = Agent(config=config)
        server = APEXServer()
        server.set_agent(agent)
        assert server._agent is agent


class TestAPEXServerGetStatus:
    @pytest.mark.asyncio
    async def test_empty_status(self):
        server = APEXServer()
        status = await server.get_status()
        assert status["host"] == "127.0.0.1"
        assert status["port"] == 8080
        assert status["clients"] == 0
        assert status["client_list"] == []
        assert status["agent_model"] is None
        assert status["agent_mode"] is None

    @pytest.mark.asyncio
    async def test_status_with_client(self):
        server = APEXServer()
        client = APEXClient("c1", "alice")
        server.clients["c1"] = client

        status = await server.get_status()
        assert status["clients"] == 1
        assert len(status["client_list"]) == 1
        assert status["client_list"][0]["id"] == "c1"

    @pytest.mark.asyncio
    async def test_status_with_agent(self, tmp_path):
        from apex.agent import Agent
        from apex.config import Config

        config = Config(config_path=tmp_path / "cfg.json")
        agent = Agent(config=config)
        server = APEXServer()
        server.set_agent(agent)

        status = await server.get_status()
        assert status["agent_model"] is not None
        assert status["agent_mode"] is not None


class TestAPEXServerHandleWebSocket:
    """Tests for APEXServer.handle_websocket — covers auth, flow, rate limiting, errors."""

    @pytest.mark.asyncio
    async def test_auth_rejection(self):
        server = APEXServer()
        server._key_manager._require_auth = True
        ws = _AsyncIterableWS()
        await server.handle_websocket(ws, token="bad")
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "error"
        assert "Unauthorized" in ws.sent[0]["message"]

    @pytest.mark.asyncio
    async def test_auth_with_valid_token(self):
        server = APEXServer()
        server._key_manager._require_auth = True
        token = "valid-token"
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        server._key_manager._tokens[token_hash] = {"token": token, "created_at": 0}

        ws = _AsyncIterableWS()
        await server.handle_websocket(ws, token=token)
        assert len(ws.sent) >= 1
        assert ws.sent[0]["type"] == "welcome"

    @pytest.mark.asyncio
    async def test_welcome_and_disconnect(self):
        ws = _AsyncIterableWS()
        server = APEXServer()
        await server.handle_websocket(ws)
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "welcome"
        assert ws.sent[0]["client_id"] is not None
        assert len(server.clients) == 0
        assert len(server._websockets) == 0

    @pytest.mark.asyncio
    async def test_message_processing(self):
        msg = json.dumps({"type": "chat", "message": "hi"})
        ws = _AsyncIterableWS(messages=[msg])
        server = APEXServer()
        await server.handle_websocket(ws)
        assert len(ws.sent) >= 2
        assert ws.sent[0]["type"] == "welcome"
        assert ws.sent[1]["type"] == "error"

    @pytest.mark.asyncio
    async def test_rate_limit(self):
        original = APEXClient._rate_limit
        APEXClient._rate_limit = 0
        try:
            ws = _AsyncIterableWS(messages=["hello world"])
            server = APEXServer()
            await server.handle_websocket(ws)
            assert any(
                s.get("type") == "error" and "Rate limit" in s.get("message", "")
                for s in ws.sent
            )
            assert len(server.clients) == 0
        finally:
            APEXClient._rate_limit = original

    @pytest.mark.asyncio
    async def test_connection_error_during_send(self):
        ws = _BrokenWS()
        server = APEXServer()
        await server.handle_websocket(ws)
        assert len(server.clients) == 0
        assert len(server._websockets) == 0


class TestAPEXServerProcessChat:
    @pytest.mark.asyncio
    async def test_no_agent(self):
        server = APEXServer()
        result = await server._process_chat("c1", {"message": "hello"})
        assert result["type"] == "error"
        assert "Agent not initialized" in result["message"]

    @pytest.mark.asyncio
    async def test_with_agent_stream(self, tmp_path):
        from apex.agent import Agent
        from apex.config import Config

        config = Config(config_path=tmp_path / "cfg.json")
        agent = Agent(config=config)
        server = APEXServer()
        server.set_agent(agent)
        server.clients["c1"] = APEXClient("c1")

        result = await server._process_chat("c1", {"message": "test", "stream": True})
        assert result["type"] == "chat_stream"

    @pytest.mark.asyncio
    async def test_with_agent_non_stream(self, tmp_path):
        from apex.agent import Agent
        from apex.config import Config

        config = Config(config_path=tmp_path / "cfg.json")
        agent = Agent(config=config)
        server = APEXServer()
        server.set_agent(agent)
        server.clients["c1"] = APEXClient("c1")

        result = await server._process_chat("c1", {"message": "test", "stream": False})
        assert "response" in result
        assert "type" in result


class TestAPEXServerExecuteTool:
    @pytest.mark.asyncio
    async def test_no_agent(self):
        server = APEXServer()
        result = await server._execute_tool("read_file", {"path": "test.py"})
        assert "ERROR" in result
        assert "Agent not initialized" in result

    @pytest.mark.asyncio
    async def test_with_agent_unknown_tool(self, tmp_path):
        from apex.agent import Agent
        from apex.config import Config

        config = Config(config_path=tmp_path / "cfg.json")
        agent = Agent(config=config)
        server = APEXServer()
        server.set_agent(agent)

        result = await server._execute_tool("nonexistent_tool_xyz", {})
        assert "ERROR" in result
        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_with_agent_known_tool(self, tmp_path):
        from apex.agent import Agent
        from apex.config import Config

        config = Config(config_path=tmp_path / "cfg.json")
        agent = Agent(config=config)
        server = APEXServer()
        server.set_agent(agent)

        result = await server._execute_tool("read_file", {"path": "some_file.py"})
        assert "ERROR: Unknown tool" not in result


class TestAPEXServerHandleMessage:
    """Tests for APEXServer._handle_message — all message types + error paths."""

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        class FakeWS:
            def __init__(self):
                self.sent = []
            async def send_json(self, data):
                self.sent.append(data)

        ws = FakeWS()
        server = APEXServer()
        server.clients["c1"] = APEXClient("c1")
        await server._handle_message("c1", "not valid json {{{", ws)
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "error"
        assert "Invalid JSON" in ws.sent[0]["message"]

    @pytest.mark.asyncio
    async def test_chat_message_type(self):
        class FakeWS:
            def __init__(self):
                self.sent = []
            async def send_json(self, data):
                self.sent.append(data)

        ws = FakeWS()
        server = APEXServer()
        client = APEXClient("c1")
        server.clients["c1"] = client
        await server._handle_message("c1", json.dumps({"type": "chat", "message": "hi"}), ws)
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "error"

    @pytest.mark.asyncio
    async def test_switch_model(self):
        class FakeWS:
            def __init__(self):
                self.sent = []
            async def send_json(self, data):
                self.sent.append(data)

        ws = FakeWS()
        server = APEXServer()
        client = APEXClient("c1")
        server.clients["c1"] = client
        await server._handle_message(
            "c1", json.dumps({"type": "switch_model", "model": "gpt-4o"}), ws
        )
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "success"
        assert client.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_switch_model_with_agent(self):
        ws = AsyncMock()
        server = APEXServer()
        server._agent = MagicMock()
        server.clients["c1"] = APEXClient("c1")
        await server._handle_message(
            "c1", json.dumps({"type": "switch_model", "model": "gpt-4o"}), ws
        )
        server._agent.switch_model.assert_called_once_with("gpt-4o")
        ws.send_json.assert_called_once_with({"type": "success", "message": "Model: gpt-4o"})
        assert server.clients["c1"].model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_switch_agent(self):
        class FakeWS:
            def __init__(self):
                self.sent = []
            async def send_json(self, data):
                self.sent.append(data)

        ws = FakeWS()
        server = APEXServer()
        client = APEXClient("c1")
        server.clients["c1"] = client
        await server._handle_message(
            "c1", json.dumps({"type": "switch_agent", "agent": "architect"}), ws
        )
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "success"
        assert client.agent_mode == "architect"

    @pytest.mark.asyncio
    async def test_switch_agent_with_agent(self):
        ws = AsyncMock()
        server = APEXServer()
        server._agent = MagicMock()
        server.clients["c1"] = APEXClient("c1")
        await server._handle_message(
            "c1", json.dumps({"type": "switch_agent", "agent": "architect"}), ws
        )
        server._agent.switch_agent.assert_called_once_with("architect")
        ws.send_json.assert_called_once_with({"type": "success", "message": "Agent: architect"})
        assert server.clients["c1"].agent_mode == "architect"

    @pytest.mark.asyncio
    async def test_execute_message(self):
        class FakeWS:
            def __init__(self):
                self.sent = []
            async def send_json(self, data):
                self.sent.append(data)

        ws = FakeWS()
        server = APEXServer()
        client = APEXClient("c1")
        server.clients["c1"] = client
        await server._handle_message(
            "c1",
            json.dumps({"type": "execute", "tool": "read_file", "args": {"path": "t.py"}}),
            ws,
        )
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "tool_result"

    @pytest.mark.asyncio
    async def test_message_updates_last_activity(self):
        class FakeWS:
            def __init__(self):
                self.sent = []
            async def send_json(self, data):
                self.sent.append(data)

        ws = FakeWS()
        server = APEXServer()
        client = APEXClient("c1")
        old_activity = client.last_activity
        server.clients["c1"] = client
        time.sleep(0.01)
        await server._handle_message("c1", json.dumps({"type": "chat", "message": "hi"}), ws)
        assert client.last_activity != old_activity

    @pytest.mark.asyncio
    async def test_generic_exception_caught(self):
        ws = AsyncMock()
        server = APEXServer()
        server.clients["c1"] = APEXClient("c1")
        with patch.object(server, "_process_chat", side_effect=ValueError("boom")):
            await server._handle_message(
                "c1", json.dumps({"type": "chat", "message": "hi"}), ws
            )
        ws.send_json.assert_called_with({"type": "error", "message": "boom"})

    @pytest.mark.asyncio
    async def test_last_activity_key_error(self):
        """Missing client in clients dict triggers generic Exception handler."""
        class FakeWS:
            def __init__(self):
                self.sent = []
            async def send_json(self, data):
                self.sent.append(data)

        ws = FakeWS()
        server = APEXServer()
        await server._handle_message("c1", json.dumps({"type": "chat", "message": "hi"}), ws)
        assert len(ws.sent) >= 1


class TestAPEXServerBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_to_websockets(self):
        sent1 = []
        sent2 = []

        class FakeWS1:
            async def send_json(self, data):
                sent1.append(data)

        class FakeWS2:
            async def send_json(self, data):
                sent2.append(data)

        server = APEXServer()
        ws1 = FakeWS1()
        ws2 = FakeWS2()
        server._websockets = {ws1, ws2}

        await server.broadcast({"type": "notification", "data": "test"})
        assert len(sent1) == 1
        assert len(sent2) == 1
        assert sent1[0]["type"] == "notification"

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed(self):
        class GoodWS:
            def __init__(self):
                self.sent = []
            async def send_json(self, data):
                self.sent.append(data)

        class BadWS:
            async def send_json(self, data):
                raise ConnectionError("disconnected")

        server = APEXServer()
        good = GoodWS()
        bad = BadWS()
        server._websockets = {good, bad}

        await server.broadcast({"type": "test"})
        assert bad not in server._websockets
        assert good in server._websockets

    @pytest.mark.asyncio
    async def test_broadcast_empty(self):
        server = APEXServer()
        server._websockets = set()
        await server.broadcast({"type": "test"})


# =========================================================================
# run_server tests — fully mocked aiohttp
# =========================================================================

class TestRunServer:
    """Test the standalone run_server entry point."""

    @pytest.mark.asyncio
    async def _run_with_mocks(self, mock_web, mock_server_cls,
                              server_agent=None):
        """Helper: capture handlers, run server, trigger KeyboardInterrupt."""
        mock_server = MagicMock()
        mock_server._agent = server_agent
        mock_server.get_status = AsyncMock(return_value={
            "host": "127.0.0.1", "port": 9999, "clients": 0,
            "client_list": [], "agent_model": None, "agent_mode": None,
        })
        mock_server.handle_websocket = AsyncMock()
        mock_server_cls.return_value = mock_server

        get_routes = {}
        post_routes = {}

        def capture_get(p, h):
            get_routes[p] = h

        def capture_post(p, h):
            post_routes[p] = h

        mock_app = MagicMock()
        mock_app.router.add_get.side_effect = capture_get
        mock_app.router.add_post.side_effect = capture_post
        mock_web.Application.return_value = mock_app

        mock_runner = AsyncMock()
        mock_web.AppRunner.return_value = mock_runner

        mock_site = AsyncMock()
        mock_web.TCPSite.return_value = mock_site

        mock_ws_resp = AsyncMock()
        mock_ws_resp.prepare = AsyncMock()
        mock_web.WebSocketResponse.return_value = mock_ws_resp

        with patch.object(asyncio, "Event") as mock_ev_cls:
            mock_ev = MagicMock()
            mock_ev.wait = AsyncMock(side_effect=KeyboardInterrupt())
            mock_ev_cls.return_value = mock_ev
            await run_server(host="127.0.0.1", port=9999)

        return mock_server, mock_runner, mock_site, mock_ws_resp, get_routes, post_routes

    @pytest.mark.asyncio
    async def test_lifecycle(self):
        with (
            patch("aiohttp.web", create=True) as mock_web,
            patch("apex.server.APEXServer") as mock_server_cls,
        ):
            mock_server, mock_runner, mock_site, _, _, _ = (
                await self._run_with_mocks(mock_web, mock_server_cls)
            )

        mock_server_cls.assert_called_once_with("127.0.0.1", 9999)
        mock_web.Application.assert_called_once()
        mock_web.AppRunner.assert_called_once()
        mock_runner.setup.assert_called_once()
        mock_web.TCPSite.assert_called_once_with(mock_runner, "127.0.0.1", 9999)
        mock_site.start.assert_called_once()
        mock_runner.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_routes_registered(self):
        with (
            patch("aiohttp.web", create=True) as mock_web,
            patch("apex.server.APEXServer") as mock_server_cls,
        ):
            _, _, _, _, get_routes, post_routes = (
                await self._run_with_mocks(mock_web, mock_server_cls)
            )

        assert "/" in get_routes
        assert "/ws" in get_routes
        assert "/status" in get_routes
        assert "/chat" in post_routes

    @pytest.mark.asyncio
    async def test_index_handler(self):
        with (
            patch("aiohttp.web", create=True) as mock_web,
            patch("apex.server.APEXServer") as mock_server_cls,
        ):
            _, _, _, _, get_routes, _ = (
                await self._run_with_mocks(mock_web, mock_server_cls)
            )

            resp = await get_routes["/"](MagicMock())
            mock_web.Response.assert_called_once()
            kwargs = mock_web.Response.call_args.kwargs
            assert kwargs["content_type"] == "text/html"
            assert "DOCTYPE html" in kwargs["text"]

    @pytest.mark.asyncio
    async def test_ws_handler(self):
        with (
            patch("aiohttp.web", create=True) as mock_web,
            patch("apex.server.APEXServer") as mock_server_cls,
        ):
            mock_server, _, _, mock_ws_resp, get_routes, _ = (
                await self._run_with_mocks(mock_web, mock_server_cls)
            )

            req = MagicMock()
            resp = await get_routes["/ws"](req)
            assert resp is mock_ws_resp
            mock_ws_resp.prepare.assert_called_once_with(req)
            mock_server.handle_websocket.assert_called_once_with(mock_ws_resp)

    @pytest.mark.asyncio
    async def test_status_handler(self):
        with (
            patch("aiohttp.web", create=True) as mock_web,
            patch("apex.server.APEXServer") as mock_server_cls,
        ):
            mock_server, _, _, _, get_routes, _ = (
                await self._run_with_mocks(mock_web, mock_server_cls)
            )

            mock_web.json_response = MagicMock(return_value={"status": "ok"})
            resp = await get_routes["/status"](MagicMock())
            mock_server.get_status.assert_called_once()
            mock_web.json_response.assert_called_once()
            assert resp == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_chat_handler_no_agent(self):
        with (
            patch("aiohttp.web", create=True) as mock_web,
            patch("apex.server.APEXServer") as mock_server_cls,
        ):
            _, _, _, _, _, post_routes = (
                await self._run_with_mocks(mock_web, mock_server_cls, server_agent=None)
            )

            req = AsyncMock()
            req.json = AsyncMock(return_value={"message": "hello"})
            mock_web.json_response = MagicMock(return_value="resp")
            resp = await post_routes["/chat"](req)
            mock_web.json_response.assert_called_once_with(
                {"error": "Agent not initialized"}, status=500
            )
            assert resp == "resp"

    @pytest.mark.asyncio
    async def test_chat_handler_with_agent(self):
        with (
            patch("aiohttp.web", create=True) as mock_web,
            patch("apex.server.APEXServer") as mock_server_cls,
        ):
            mock_agent = MagicMock()
            mock_agent.chat.return_value = "agent reply"
            mock_agent.usage = {"total_tokens": 42}

            _, _, _, _, _, post_routes = (
                await self._run_with_mocks(mock_web, mock_server_cls, server_agent=mock_agent)
            )

            req = AsyncMock()
            req.json = AsyncMock(return_value={"message": "hello"})
            mock_web.json_response = MagicMock(return_value="resp")
            resp = await post_routes["/chat"](req)
            mock_agent.chat.assert_called_once_with("hello")
            mock_web.json_response.assert_called_once_with(
                {"response": "agent reply", "usage": {"total_tokens": 42}}
            )
            assert resp == "resp"
