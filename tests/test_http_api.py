"""Tests for http_api module — full coverage."""

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from apex.http_api import (
    APEXHTTPServer,
    HTTPServer,
    RateLimitConfig,
    _sanitize_config,
    _sanitize_string,
    _get_configured_providers,
    _check_provider_configured,
    run_server,
    start_tui_server,
    stop_tui_server,
)
from apex.agent import Agent
from apex.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(tmp_path):
    """Create a real Agent with a temp config so no real API calls happen."""
    config = Config(config_path=tmp_path / "cfg.json")
    config._data["model"] = "gpt-4o-mini"
    agent = Agent(config=config)
    # Pre-set usage so handler code doesn't need a real LLM response
    agent._usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    return agent


# ---------------------------------------------------------------------------
# Module-level helper tests
# ---------------------------------------------------------------------------


class TestSanitizeConfig:
    """Test the _sanitize_config helper function."""

    def test_redacts_sensitive_keys(self):
        data = {"api_key": "sk-secret", "model": "gpt-4", "nested": {"token": "abc"}}
        result = _sanitize_config(data)
        assert result["api_key"] == "***REDACTED***"
        assert result["model"] == "gpt-4"
        assert result["nested"]["token"] == "***REDACTED***"

    def test_redacts_lowercase_variants(self):
        data = {"ApiKey": "val", "SECRET": "val"}
        result = _sanitize_config(data)
        assert result["ApiKey"] == "***REDACTED***"
        assert result["SECRET"] == "***REDACTED***"

    def test_handles_nested_lists(self):
        data = {"models": [{"api_token": "secret"}, "plain"]}
        result = _sanitize_config(data)
        assert result["models"][0]["api_token"] == "***REDACTED***"
        assert result["models"][1] == "plain"

    def test_depth_limit_returns_early(self):
        deep = {}
        cur = deep
        for _ in range(12):
            cur["nested"] = {}
            cur = cur["nested"]
        result = _sanitize_config(deep)
        assert "nested" in result

    def test_non_dict_non_str_values_passthrough(self):
        data = {"count": 42, "active": True, "rate": 3.14}
        result = _sanitize_config(data)
        assert result["count"] == 42
        assert result["active"] is True
        assert result["rate"] == 3.14


class TestSanitizeString:
    """Test the _sanitize_string helper function."""

    def test_redacts_api_key_pattern(self):
        result = _sanitize_string("sk-ant-mysecretkey12345")
        assert "***REDACTED***" in result
        assert "mysecretkey12345" not in result

    def test_redacts_bearer_token(self):
        result = _sanitize_string("Bearer eyJhbGciOiJIUzI1NiJ9.test")
        assert "***REDACTED***" in result

    def test_no_match_returns_original(self):
        result = _sanitize_string("hello world")
        assert result == "hello world"

    def test_exception_during_regex_is_caught(self):
        broken_pattern = MagicMock()
        broken_pattern.sub = MagicMock(side_effect=Exception("oops"))
        with patch("apex.http_api.SENSITIVE_PATTERNS", [broken_pattern]):
            result = _sanitize_string("any value")
            assert result == "any value"


class TestCheckProviderConfigured:
    """Test the _check_provider_configured helper."""

    def test_checks_env_var(self):
        with patch.dict(os.environ, {"MY_TEST_KEY": "value"}, clear=True):
            assert _check_provider_configured("MY_TEST_KEY") is True
            assert _check_provider_configured("OTHER_KEY") is False


class TestGetConfiguredProviders:
    """Test the _get_configured_providers helper."""

    def test_returns_list(self):
        providers = _get_configured_providers()
        assert isinstance(providers, list)
        for p in providers:
            assert "name" in p
            assert "env_var" in p
            assert "configured" in p
            assert "models" in p


# ---------------------------------------------------------------------------
# HTTPServer construction tests
# ---------------------------------------------------------------------------


class TestHTTPServerInit:
    """Test HTTPServer and APEXHTTPServer construction."""

    def test_default_init(self, tmp_path):
        server = HTTPServer(require_auth=False)
        assert server.host == "127.0.0.1"
        assert server.port == 8080
        assert server.require_auth is False
        assert server.app is not None
        assert server.agent is not None
        assert server.runner is None

    def test_custom_init(self, tmp_path):
        cfg = RateLimitConfig(requests_per_minute=10, requests_per_hour=100, requests_per_day=500)
        server = HTTPServer(
            host="0.0.0.0",
            port=9999,
            require_auth=False,
            rate_limit_config=cfg,
            use_sqlite_storage=False,
        )
        assert server.host == "0.0.0.0"
        assert server.port == 9999
        assert server.require_auth is False

    def test_apex_http_server_init(self, tmp_path):
        server = APEXHTTPServer(host="127.0.0.1", port=8080)
        assert server.host == "127.0.0.1"
        assert server.port == 8080
        assert server.require_auth is False

    def test_apex_http_server_default_host(self, tmp_path):
        server = APEXHTTPServer()
        assert server.host == "0.0.0.0"
        assert server.port == 8080

    def test_setup_routes(self, tmp_path):
        server = HTTPServer(require_auth=False)
        routes = [
            r.resource.canonical for r in server.app.router.routes() if r.resource is not None
        ]
        assert "/" in routes
        assert "/health" in routes
        assert "/chat" in routes
        assert "/stream" in routes
        assert "/models" in routes
        assert "/metrics" in routes

    def test_auth_middleware_attached(self, tmp_path):
        server = HTTPServer(require_auth=True)
        assert server.auth_middleware.require_auth is True
        server2 = HTTPServer(require_auth=False)
        assert server2.auth_middleware.require_auth is False

    def test_rate_limiter_attached(self, tmp_path):
        server = HTTPServer(require_auth=False)
        assert server.rate_limiter is not None


# ---------------------------------------------------------------------------
# Handler tests using aiohttp test client (real HTTP, no mocks)
# ---------------------------------------------------------------------------


class TestIndexHandler:
    """Test the index / documentation endpoint."""

    @pytest.mark.asyncio
    async def test_index_returns_html(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/")
            assert resp.status == 200
            text = await resp.text()
            assert "APEX" in text
            assert "text/html" in resp.content_type


class TestHealthHandler:
    """Test the health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/health")
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "ok"
            assert "timestamp" in data
            assert "agent" in data


class TestChatHandler:
    """Test the chat endpoint in detail."""

    @pytest.mark.asyncio
    async def test_chat_with_model_switch(self):
        server = HTTPServer(require_auth=False)
        with patch.object(server.agent, "chat", return_value="test response"):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/chat", json={"message": "hi", "model": "gpt-4o"})
                assert resp.status == 200
                data = await resp.json()
                assert "test response" in data["response"]

    @pytest.mark.asyncio
    async def test_chat_with_key_info(self):
        server = HTTPServer(require_auth=False)
        with patch.object(server.agent, "chat", return_value="resp"):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/chat", json={"message": "hi"})
                assert resp.status == 200

    @pytest.mark.asyncio
    async def test_chat_invalid_json_returns_500(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/chat", data=b"not json", headers={"Content-Type": "application/json"})
            assert resp.status == 500


class TestStreamHandler:
    """Test the SSE stream endpoint."""

    @pytest.mark.asyncio
    async def test_stream_returns_sse(self):
        server = HTTPServer(require_auth=False)
        async def mock_stream(msg):
            yield "chunk1"
            yield "chunk2"
        with patch.object(server.agent, "chat_streaming", mock_stream):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.get("/stream")
                assert resp.status == 200
                assert resp.content_type == "text/event-stream"
                text = await resp.text()
                assert "chunk1" in text


class TestChatStreamHandler:
    """Test the chat with streaming endpoint."""

    @pytest.mark.asyncio
    async def test_chat_stream_success(self):
        server = HTTPServer(require_auth=False)
        async def mock_stream(msg):
            yield "token1"
            yield "token2"
        with patch.object(server.agent, "chat_streaming", mock_stream):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/chat/stream", json={"message": "hi"})
                assert resp.status == 200
                assert resp.content_type == "text/event-stream"
                text = await resp.text()
                assert "token1" in text
                assert "usage" in text

    @pytest.mark.asyncio
    async def test_chat_stream_model_switch(self):
        server = HTTPServer(require_auth=False)
        async def mock_stream(msg):
            yield "t"
        with patch.object(server.agent, "chat_streaming", mock_stream):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/chat/stream", json={"message": "hi", "model": "gpt-4o"})
                assert resp.status == 200

    @pytest.mark.asyncio
    async def test_chat_stream_rate_limited(self):
        cfg = RateLimitConfig(requests_per_minute=1, requests_per_hour=10, requests_per_day=100)
        server = HTTPServer(require_auth=False, rate_limit_config=cfg)
        for _ in range(2):
            server.rate_limiter.check_rate_limit("anonymous")
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/chat/stream", json={"message": "hi"})
            assert resp.status == 429

    @pytest.mark.asyncio
    async def test_chat_stream_invalid_json_returns_500(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/chat/stream", data=b"not json",
                                      headers={"Content-Type": "application/json"})
            assert resp.status == 500


class TestListModelsHandler:
    """Test the models listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_models(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/models")
            assert resp.status == 200
            data = await resp.json()
            assert "models" in data
            assert len(data["models"]) > 0
            for m in data["models"]:
                assert "alias" in m
                assert "model" in m


class TestRateLimitStatusHandler:
    """Test the rate-limit status endpoint."""

    @pytest.mark.asyncio
    async def test_rate_limit_status_no_auth(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/rate-limit/status")
            assert resp.status == 200
            data = await resp.json()
            assert "minute" in data
            assert "hour" in data
            assert "day" in data

    @pytest.mark.asyncio
    async def test_rate_limit_status_with_auth_required(self):
        server = HTTPServer(require_auth=True)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/rate-limit/status")
            assert resp.status == 401


class TestMetricsHandler:
    """Test the metrics endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_no_auth(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/metrics")
            assert resp.status == 200
            data = await resp.json()
            assert "prompt_tokens" in data
            assert "completion_tokens" in data
            assert "total_tokens" in data
            assert "model" in data


class TestSessionSaveHandler:
    """Test session save endpoint error paths."""

    @pytest.mark.asyncio
    async def test_session_save_invalid_json_returns_500(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/session/save", data=b"not json",
                                      headers={"Content-Type": "application/json"})
            assert resp.status == 500


class TestSessionLoadHandler:
    """Test session load endpoint success and error paths."""

    @pytest.mark.asyncio
    async def test_session_load_success(self):
        server = HTTPServer(require_auth=False)
        with patch.object(server.session_manager, "load", return_value=True):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/session/load", json={"name": "my_session"})
                assert resp.status == 200
                data = await resp.json()
                assert data["loaded"] == "my_session"

    @pytest.mark.asyncio
    async def test_session_load_not_found(self):
        server = HTTPServer(require_auth=False)
        with patch.object(server.session_manager, "load", return_value=False):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/session/load", json={"name": "nonexistent"})
                assert resp.status == 404

    @pytest.mark.asyncio
    async def test_session_load_invalid_json_returns_500(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/session/load", data=b"not json",
                                      headers={"Content-Type": "application/json"})
            assert resp.status == 500


# ---------------------------------------------------------------------------
# Auth required endpoints
# ---------------------------------------------------------------------------


class TestAuthRequiredEndpoints:
    """Test that auth-required endpoints reject unauthenticated requests."""

    @pytest.mark.asyncio
    async def test_chat_requires_auth(self):
        server = HTTPServer(require_auth=True)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/chat", json={"message": "hello"})
            assert resp.status == 401
            data = await resp.json()
            assert "AUTH_REQUIRED" in data.get("code", "")

    @pytest.mark.asyncio
    async def test_chat_stream_requires_auth(self):
        server = HTTPServer(require_auth=True)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/chat/stream", json={"message": "hello"})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_stream_requires_auth(self):
        server = HTTPServer(require_auth=True)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/stream")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_session_save_requires_auth(self):
        server = HTTPServer(require_auth=True)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/session/save", json={"name": "test"})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_session_load_requires_auth(self):
        server = HTTPServer(require_auth=True)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/session/load", json={"name": "test"})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_metrics_requires_auth(self):
        server = HTTPServer(require_auth=True)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/metrics")
            assert resp.status == 401


class TestV1AuthRequiredEndpoints:
    """All v1 endpoints that should require auth."""

    @pytest.fixture
    def server(self):
        return HTTPServer(host="127.0.0.1", port=0, require_auth=True)

    @pytest.mark.asyncio
    async def test_v1_config_get_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/config")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_config_set_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/config", json={"model": "gpt-4"})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_agents_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/agents")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_agents_by_name_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/agents/coder")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_sessions_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/sessions")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_sessions_delete_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.delete("/api/v1/sessions/test")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_share_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/share", json={})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_unshare_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/unshare/test")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_shares_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/shares")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_themes_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/themes")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_themes_set_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/themes", json={"theme": "nord"})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_stats_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/stats")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_formatters_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/formatters")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_format_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/format", json={"code": "print(1)"})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_compact_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/compact")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_models_refresh_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/models/refresh")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_providers_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/providers")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_auth_login_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/auth/login", json={"provider": "x", "api_key": "y"})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_auth_logout_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/auth/logout", json={"provider": "x"})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_auth_status_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/auth/status")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_commands_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/commands")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_commands_execute_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/commands/execute", json={"name": "test"})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_undo_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/undo")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_redo_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/redo")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_init_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/init")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_export_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/export/test")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_v1_import_requires_auth(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/import", json={"data": {}})
            assert resp.status == 401


# ---------------------------------------------------------------------------
# Chat handler with rate limiting
# ---------------------------------------------------------------------------


class TestChatHandlerNoAuth:
    """Test the chat endpoint without auth."""

    @pytest.mark.asyncio
    async def test_chat_rate_limited(self):
        """Trigger rate limiting by exhausting the minute limit."""
        cfg = RateLimitConfig(requests_per_minute=1, requests_per_hour=10, requests_per_day=100)
        server = HTTPServer(require_auth=False, rate_limit_config=cfg)
        async with TestClient(TestServer(server.app)) as client:
            for _ in range(2):
                server.rate_limiter.check_rate_limit("anonymous")
            resp = await client.post("/chat", json={"message": "hello"})
            assert resp.status == 429
            data = await resp.json()
            assert data["code"] == "RATE_LIMITED"
            assert "retry_after" in data


class TestSessionLoadMissingName:
    """Test session/load with missing name returns 400."""

    @pytest.mark.asyncio
    async def test_session_load_no_name(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/session/load", json={})
            assert resp.status == 400


# ---------------------------------------------------------------------------
# Server start/stop
# ---------------------------------------------------------------------------


class TestStartStop:
    """Test server start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        server = HTTPServer(host="127.0.0.1", port=0, require_auth=False)
        await server.start()
        assert server.runner is not None
        await server.stop()
        await server.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        server = HTTPServer(require_auth=False)
        await server.stop()


# ---------------------------------------------------------------------------
# Auth middleware tests
# ---------------------------------------------------------------------------


class TestCheckAuthViaEndpoints:
    """Test _check_auth behavior through actual endpoints."""

    @pytest.mark.asyncio
    async def test_check_auth_disabled_allows_access(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/metrics")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_check_auth_enabled_blocks_no_key(self):
        server = HTTPServer(require_auth=True)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/metrics")
            assert resp.status == 401


class TestCheckRateLimitMethod:
    """Test _check_rate_limit internal method."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self):
        server = HTTPServer(require_auth=False)
        err, result = await server._check_rate_limit(None)
        assert err is None
        assert result is not None
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self):
        cfg = RateLimitConfig(requests_per_minute=1, requests_per_hour=1, requests_per_day=1)
        server = HTTPServer(require_auth=False, rate_limit_config=cfg)
        server.rate_limiter.check_rate_limit("anonymous")
        server.rate_limiter.check_rate_limit("anonymous")
        err, result = await server._check_rate_limit(None)
        assert err is not None
        assert err.status == 429

    @pytest.mark.asyncio
    async def test_check_rate_limit_with_key_info(self):
        server = HTTPServer(require_auth=False)
        key_info = {"key_id": "test123"}
        err, result = await server._check_rate_limit(key_info)
        assert err is None
        assert result is not None


class TestAPEXHTTPServerRoutes:
    """Test APEXHTTPServer backward-compat wrapper has routes."""

    @pytest.mark.asyncio
    async def test_apex_server_health(self):
        server = APEXHTTPServer(host="127.0.0.1", port=0)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/health")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_apex_server_index(self):
        server = APEXHTTPServer(host="127.0.0.1", port=0)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/")
            assert resp.status == 200


# ---------------------------------------------------------------------------
# V1 endpoint tests - detailed coverage
# ---------------------------------------------------------------------------


class TestV1Endpoints:
    """Test all /api/v1/ endpoints."""

    @pytest.fixture
    def server(self):
        return HTTPServer(host="127.0.0.1", port=0, require_auth=False)

    @pytest.mark.asyncio
    async def test_v1_config_get(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/config")
            assert resp.status == 200
            data = await resp.json()
            assert "config" in data
            assert "model" in data["config"]

    @pytest.mark.asyncio
    async def test_v1_config_post(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/config", json={"model": "gpt-4o"})
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_v1_config_set_error(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/config", data=b"not json",
                                      headers={"Content-Type": "application/json"})
            assert resp.status == 500

    @pytest.mark.asyncio
    async def test_v1_agents(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/agents")
            assert resp.status == 200
            data = await resp.json()
            assert "agents" in data
            assert len(data["agents"]) >= 8

    @pytest.mark.asyncio
    async def test_v1_agents_by_name(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/agents/coder")
            assert resp.status == 200
            data = await resp.json()
            assert data["name"] == "coder"

    @pytest.mark.asyncio
    async def test_v1_agents_not_found(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/agents/nonexistent999")
            assert resp.status == 404
            data = await resp.json()
            assert "not found" in data.get("error", "")

    @pytest.mark.asyncio
    async def test_v1_sessions(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/sessions")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_v1_sessions_delete_not_found(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.delete("/api/v1/sessions/nonexistent_id_xyz")
            assert resp.status == 404

    @pytest.mark.asyncio
    async def test_v1_themes(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/themes")
            assert resp.status == 200
            data = await resp.json()
            assert "themes" in data

    @pytest.mark.asyncio
    async def test_v1_themes_set(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/themes", json={"theme": "nord"})
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_v1_themes_set_empty_name(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/themes", json={"theme": ""})
            assert resp.status == 400
            data = await resp.json()
            assert "theme name required" in data.get("error", "")

    @pytest.mark.asyncio
    async def test_v1_themes_set_error(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/themes", data=b"not json",
                                      headers={"Content-Type": "application/json"})
            assert resp.status == 500

    @pytest.mark.asyncio
    async def test_v1_stats(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/stats")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_v1_formatters(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/formatters")
            assert resp.status == 200
            data = await resp.json()
            assert "formatters" in data

    @pytest.mark.asyncio
    async def test_v1_providers(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/providers")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_v1_auth_status(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/auth/status")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_v1_auth_login(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/auth/login", json={"provider": "anthropic", "api_key": "sk-test"})
            assert resp.status in (200, 400)

    @pytest.mark.asyncio
    async def test_v1_commands(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/api/v1/commands")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_v1_undo_redo(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/undo")
            assert resp.status in (200, 400)
            resp2 = await client.post("/api/v1/redo")
            assert resp2.status in (200, 400)

    @pytest.mark.asyncio
    async def test_v1_compact(self, server):
        server.agent.history = [{"role": "user", "content": "hello"}]
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/compact")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_v1_init(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/init")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_v1_models_refresh(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/models/refresh")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_v1_share(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/share", json={})
            assert resp.status in (200, 400, 403)
            if resp.status == 200:
                data = await resp.json()
                assert "url" in data

    @pytest.mark.asyncio
    async def test_v1_share_no_body(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/share")
            assert resp.status in (200, 403)


class TestV1ShareDetailed:
    """Detailed tests for share endpoints."""

    @pytest.mark.asyncio
    async def test_share_disabled(self):
        server = HTTPServer(require_auth=False)
        with patch.object(server, "auth_middleware") as mock_auth:
            mock_auth.require_auth = False
            mock_auth.authenticate = AsyncMock(return_value=(True, None, None))
            with patch("apex.http_api.share_manager.share_session", return_value=""):
                async with TestClient(TestServer(server.app)) as client:
                    resp = await client.post("/api/v1/share", json={"title": "test"})
                    assert resp.status == 403
                    data = await resp.json()
                    assert "sharing is disabled" in data.get("error", "")

    @pytest.mark.asyncio
    async def test_unshare_not_found(self):
        server = HTTPServer(require_auth=False)
        with patch.object(server, "auth_middleware") as mock_auth:
            mock_auth.require_auth = False
            mock_auth.authenticate = AsyncMock(return_value=(True, None, None))
            with patch("apex.http_api.share_manager.unshare_session", return_value=False):
                async with TestClient(TestServer(server.app)) as client:
                    resp = await client.post("/api/v1/unshare/nonexistent")
                    assert resp.status == 404

    @pytest.mark.asyncio
    async def test_unshare_success(self):
        server = HTTPServer(require_auth=False)
        with patch.object(server, "auth_middleware") as mock_auth:
            mock_auth.require_auth = False
            mock_auth.authenticate = AsyncMock(return_value=(True, None, None))
            with patch("apex.http_api.share_manager.unshare_session", return_value=True):
                async with TestClient(TestServer(server.app)) as client:
                    resp = await client.post("/api/v1/unshare/test123")
                    assert resp.status == 200
                    data = await resp.json()
                    assert data["unshared"] == "test123"

    @pytest.mark.asyncio
    async def test_shares_list(self):
        server = HTTPServer(require_auth=False)
        with patch.object(server, "auth_middleware") as mock_auth:
            mock_auth.require_auth = False
            mock_auth.authenticate = AsyncMock(return_value=(True, None, None))
            with patch("apex.http_api.share_manager.list_shared", return_value=[{"id": "abc"}]):
                async with TestClient(TestServer(server.app)) as client:
                    resp = await client.get("/api/v1/shares")
                    assert resp.status == 200
                    data = await resp.json()
                    assert data["shares"] == [{"id": "abc"}]

    @pytest.mark.asyncio
    async def test_share_exception(self):
        server = HTTPServer(require_auth=False)
        with patch.object(server, "auth_middleware") as mock_auth:
            mock_auth.require_auth = False
            mock_auth.authenticate = AsyncMock(return_value=(True, None, None))
            with patch("apex.http_api.share_manager.share_session", side_effect=ValueError("fail")):
                async with TestClient(TestServer(server.app)) as client:
                    resp = await client.post("/api/v1/share", json={})
                    assert resp.status == 500


class TestV1FormatEndpoint:
    """Test the format endpoint."""

    @pytest.mark.asyncio
    async def test_format_code_snippet(self):
        server = HTTPServer(require_auth=False)
        with patch("apex.http_api.formatter_manager.format_code", return_value="formatted code"):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/format", json={"code": "print(1)", "extension": ".py"})
                assert resp.status == 200
                data = await resp.json()
                assert data["formatted"] is True
                assert data["code"] == "formatted code"

    @pytest.mark.asyncio
    async def test_format_file_success(self):
        server = HTTPServer(require_auth=False)
        with patch("apex.http_api.formatter_manager.format_file", return_value=True):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/format", json={"file_path": "/tmp/test.py"})
                assert resp.status == 200
                data = await resp.json()
                assert data["formatted"] is True

    @pytest.mark.asyncio
    async def test_format_file_no_formatter(self):
        server = HTTPServer(require_auth=False)
        with patch("apex.http_api.formatter_manager.format_file", return_value=False):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/format", json={"file_path": "/tmp/test.xyz"})
                assert resp.status == 400

    @pytest.mark.asyncio
    async def test_format_no_input(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/format", json={})
            assert resp.status == 400

    @pytest.mark.asyncio
    async def test_format_exception(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/format", data=b"not json",
                                      headers={"Content-Type": "application/json"})
            assert resp.status == 500


class TestV1CompactEndpoint:
    """Test compact endpoint error paths."""

    @pytest.mark.asyncio
    async def test_compact_exception(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/compact", data=b"not json",
                                      headers={"Content-Type": "application/json"})
            assert resp.status == 500


class TestV1AuthLoginDetailed:
    """Detailed tests for auth login endpoint."""

    @pytest.mark.asyncio
    async def test_login_missing_fields(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/auth/login", json={"provider": "test", "api_key": ""})
            assert resp.status == 400
            data = await resp.json()
            assert "provider and api_key required" in data.get("error", "")

    @pytest.mark.asyncio
    async def test_login_missing_provider(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/auth/login", json={"provider": "", "api_key": "key123"})
            assert resp.status == 400

    @pytest.mark.asyncio
    async def test_login_hf_provider(self):
        server = HTTPServer(require_auth=False)
        with patch.dict(os.environ, {}, clear=True):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/auth/login", json={"provider": "hf", "api_key": "hf_test"})
                assert resp.status == 200
                data = await resp.json()
                assert data["env_var"] == "HF_TOKEN"

    @pytest.mark.asyncio
    async def test_login_github_provider(self):
        server = HTTPServer(require_auth=False)
        with patch.dict(os.environ, {}, clear=True):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/auth/login", json={"provider": "github", "api_key": "gh_test"})
                assert resp.status == 200
                data = await resp.json()
                assert data["env_var"] == "GITHUB_TOKEN"

    @pytest.mark.asyncio
    async def test_login_exception(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/auth/login", data=b"not json",
                                      headers={"Content-Type": "application/json"})
            assert resp.status == 500


class TestV1AuthLogoutDetailed:
    """Detailed tests for auth logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_specific_provider(self):
        server = HTTPServer(require_auth=False)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/auth/logout", json={"provider": "anthropic"})
                assert resp.status == 200
                data = await resp.json()
                assert data["removed"] is True
                assert data["env_var"] == "ANTHROPIC_API_KEY"

    @pytest.mark.asyncio
    async def test_logout_hf_provider(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/auth/logout", json={"provider": "hf"})
            assert resp.status == 200
            data = await resp.json()
            assert data["env_var"] == "HF_TOKEN"

    @pytest.mark.asyncio
    async def test_logout_github_provider(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/auth/logout", json={"provider": "github"})
            assert resp.status == 200
            data = await resp.json()
            assert data["env_var"] == "GITHUB_TOKEN"

    @pytest.mark.asyncio
    async def test_logout_all_providers(self):
        server = HTTPServer(require_auth=False)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/auth/logout", json={})
                assert resp.status == 200
                data = await resp.json()
                assert data["removed"] is True
                assert len(data["env_vars"]) > 0

    @pytest.mark.asyncio
    async def test_logout_exception(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/auth/logout", data=b"not json",
                                      headers={"Content-Type": "application/json"})
            assert resp.status == 500


class TestV1CommandsExecute:
    """Test the commands execute endpoint."""

    @pytest.mark.asyncio
    async def test_execute_missing_name(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/commands/execute", json={})
            assert resp.status == 400

    @pytest.mark.asyncio
    async def test_execute_unknown_command(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/commands/execute", json={"name": "nonexistent_cmd"})
            assert resp.status == 404

    @pytest.mark.asyncio
    async def test_execute_rate_limited(self):
        cfg = RateLimitConfig(requests_per_minute=1, requests_per_hour=10, requests_per_day=100)
        server = HTTPServer(require_auth=False, rate_limit_config=cfg)
        for _ in range(2):
            server.rate_limiter.check_rate_limit("anonymous")
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/commands/execute", json={"name": "test"})
            assert resp.status == 429

    @pytest.mark.asyncio
    async def test_execute_success(self):
        server = HTTPServer(require_auth=False)
        with patch.object(server.agent, "chat", return_value="done"):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/commands/execute", json={"name": "test", "args": ["a"]})
                assert resp.status == 200
                data = await resp.json()
                assert data["executed"] is True

    @pytest.mark.asyncio
    async def test_execute_exception(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/commands/execute", data=b"not json",
                                      headers={"Content-Type": "application/json"})
            assert resp.status == 500


class TestV1UndoRedoDetailed:
    """Detailed tests for undo/redo endpoints."""

    @pytest.mark.asyncio
    async def test_undo_with_action(self):
        server = HTTPServer(require_auth=False)
        server.undo_manager.snapshot("edit", {"file": "test.py"})
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/undo")
            assert resp.status == 200
            data = await resp.json()
            assert data["undone"] is True
            assert data["action"] == "edit"

    @pytest.mark.asyncio
    async def test_redo_with_action(self):
        server = HTTPServer(require_auth=False)
        server.undo_manager.snapshot("edit", {"file": "test.py"})
        async with TestClient(TestServer(server.app)) as client:
            await client.post("/api/v1/undo")
            resp = await client.post("/api/v1/redo")
            assert resp.status == 200
            data = await resp.json()
            assert data["redone"] is True
            assert data["action"] == "edit"


class TestV1InitDetailed:
    """Test the init endpoint error paths."""

    @pytest.mark.asyncio
    async def test_init_exception(self):
        server = HTTPServer(require_auth=False)
        with patch("apex.http_api.ProjectInitializer", side_effect=ValueError("fail")):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/init", data=b"not json",
                                          headers={"Content-Type": "application/json"})
                assert resp.status == 500


class TestV1ExportImport:
    """Test export and import endpoints."""

    @pytest.mark.asyncio
    async def test_export_session_not_found(self):
        server = HTTPServer(require_auth=False)
        with patch("apex.http_api.share_manager.export_session", return_value={}):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.get("/api/v1/export/nonexistent")
                assert resp.status == 404

    @pytest.mark.asyncio
    async def test_export_session_success(self):
        server = HTTPServer(require_auth=False)
        export_data = {"session_id": "abc", "data": {"history": []}}
        with patch("apex.http_api.share_manager.export_session", return_value=export_data):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.get("/api/v1/export/test_session")
                assert resp.status == 200
                data = await resp.json()
                assert data["session_id"] == "abc"

    @pytest.mark.asyncio
    async def test_import_from_file_path(self):
        server = HTTPServer(require_auth=False)
        with patch("apex.http_api.share_manager.import_session", return_value="new_session_id"):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/import", json={"file_path": "/tmp/test.json"})
                assert resp.status == 200
                data = await resp.json()
                assert data["imported"] is True
                assert data["session_id"] == "new_session_id"

    @pytest.mark.asyncio
    async def test_import_from_file_path_failure(self):
        server = HTTPServer(require_auth=False)
        with patch("apex.http_api.share_manager.import_session", return_value=None):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/import", json={"file_path": "/tmp/nonexistent.json"})
                assert resp.status == 400

    @pytest.mark.asyncio
    async def test_import_from_data(self):
        server = HTTPServer(require_auth=False)
        with patch.object(Path, "home", return_value=Path("/tmp")):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/import", json={"data": {"session_id": "abc123", "history": []}})
                assert resp.status == 200
                data = await resp.json()
                assert data["imported"] is True

    @pytest.mark.asyncio
    async def test_import_no_input(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/import", json={})
            assert resp.status == 400

    @pytest.mark.asyncio
    async def test_import_exception(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/api/v1/import", data=b"not json",
                                      headers={"Content-Type": "application/json"})
            assert resp.status == 500


# ---------------------------------------------------------------------------
# Test metrics with authenticated key_info
# ---------------------------------------------------------------------------


class TestMetricsWithKeyInfo:
    """Test metrics endpoint with key_info."""

    @pytest.mark.asyncio
    async def test_metrics_with_key_info(self):
        server = HTTPServer(require_auth=False)
        key_info = {"key_id": "test123", "workspace_id": "ws1"}
        with patch.object(server.auth_middleware, "authenticate",
                          return_value=(True, "test-key", key_info)):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.get("/metrics")
                assert resp.status == 200
                data = await resp.json()
                assert "rate_limit" in data
                assert "usage_summary" in data


class TestStatsWithKeyInfo:
    """Test stats endpoint with key_info."""

    @pytest.mark.asyncio
    async def test_stats_with_key_info(self):
        server = HTTPServer(require_auth=False)
        key_info = {"key_id": "test123", "workspace_id": "ws1"}
        with patch.object(server.auth_middleware, "authenticate",
                          return_value=(True, "test-key", key_info)):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.get("/api/v1/stats")
                assert resp.status == 200
                data = await resp.json()
                assert "rate_limit" in data


# ---------------------------------------------------------------------------
# Test session delete with file glob matching
# ---------------------------------------------------------------------------


class TestV1SessionsDeleteDetailed:
    """Test session delete with various scenarios."""

    @pytest.fixture
    def server(self):
        return HTTPServer(host="127.0.0.1", port=0, require_auth=False)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.delete("/api/v1/sessions/nonexistent")
            assert resp.status == 404

    @pytest.mark.asyncio
    async def test_delete_no_sessions_dir(self, server):
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.delete("/api/v1/sessions/any_id")
            assert resp.status == 404


# ---------------------------------------------------------------------------
# Test run_server function
# ---------------------------------------------------------------------------


class TestRunServer:
    """Test the run_server convenience function."""

    @pytest.mark.asyncio
    async def test_run_server_cancelled(self):
        async def do_test():
            task = asyncio.create_task(run_server(host="127.0.0.1", port=0, require_auth=False))
            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await do_test()


# ---------------------------------------------------------------------------
# Test TUI server start/stop
# ---------------------------------------------------------------------------


class TestTuiServer:
    """Test start_tui_server and stop_tui_server functions."""

    def test_start_and_stop_tui_server(self):
        with patch.object(sys, "platform", "linux"):
            with patch("apex.http_api.asyncio.new_event_loop") as mock_new_loop:
                mock_loop = MagicMock()
                mock_loop.is_running.return_value = True
                mock_new_loop.return_value = mock_loop
                with patch("threading.Thread") as mock_thread:
                    mock_thread_instance = MagicMock()
                    mock_thread.return_value = mock_thread_instance
                    server = start_tui_server(port=9999)
                    assert server is not None
                    assert server._thread is not None
                    assert server._loop is not None
                    stop_tui_server(server)
                    mock_loop.call_soon_threadsafe.assert_called_once()

    def test_start_and_stop_win32(self):
        with patch.object(sys, "platform", "win32"):
            with patch("apex.http_api.asyncio.SelectorEventLoop") as mock_loop_cls:
                mock_loop = MagicMock()
                mock_loop.is_running.return_value = True
                mock_loop_cls.return_value = mock_loop
                with patch("threading.Thread") as mock_thread:
                    mock_thread_instance = MagicMock()
                    mock_thread.return_value = mock_thread_instance
                    server = start_tui_server(port=9999)
                    assert server is not None
                    stop_tui_server(server)
                    mock_loop.call_soon_threadsafe.assert_called_once()

    def test_stop_with_agent(self):
        agent = MagicMock()
        with patch("threading.Thread"):
            with patch("apex.http_api.asyncio.new_event_loop") as mock_new_loop:
                mock_loop = MagicMock()
                mock_loop.is_running.return_value = True
                mock_new_loop.return_value = mock_loop
                server = start_tui_server(port=9999, agent=agent)
                assert server.agent is agent
                stop_tui_server(server)

    def test_stop_none_server(self):
        stop_tui_server(None)

    def test_stop_already_stopped_loop(self):
        server = MagicMock()
        server._loop = None
        stop_tui_server(server)

    def test_stop_loop_not_running(self):
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = False
        server = MagicMock()
        server._loop = mock_loop
        stop_tui_server(server)
        mock_loop.call_soon_threadsafe.assert_not_called()

    def test_stop_loop_runtime_error(self):
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        mock_loop.call_soon_threadsafe.side_effect = RuntimeError("already stopped")
        server = MagicMock()
        server._loop = mock_loop
        stop_tui_server(server)


class TestTuiServerCleanup:
    """Test TUI server _run() cleanup code paths."""

    def test_cleanup_normal(self):
        loop = asyncio.SelectorEventLoop()
        loop.run_forever = MagicMock()
        loop.run_until_complete = MagicMock(return_value=None)
        loop.shutdown_asyncgens = MagicMock(return_value=None)
        loop.close = MagicMock(wraps=loop.close)

        with patch("apex.http_api.asyncio.new_event_loop", return_value=loop):
            with patch("threading.Thread") as mock_thread_cls:
                mock_thread_instance = MagicMock()
                mock_thread_cls.return_value = mock_thread_instance
                start_tui_server(port=9999)
                target_fn = mock_thread_cls.call_args[1]["target"]
                target_fn()
                loop.close.assert_called_once()

    def test_cleanup_with_exception(self):
        loop = asyncio.SelectorEventLoop()
        loop.run_forever = MagicMock(side_effect=RuntimeError("fail"))
        loop.run_until_complete = MagicMock(return_value=None)
        loop.shutdown_asyncgens = MagicMock(return_value=None)
        loop.close = MagicMock(wraps=loop.close)

        with patch("apex.http_api.asyncio.new_event_loop", return_value=loop):
            with patch("threading.Thread") as mock_thread_cls:
                mock_thread_instance = MagicMock()
                mock_thread_cls.return_value = mock_thread_instance
                start_tui_server(port=9999)
                target_fn = mock_thread_cls.call_args[1]["target"]
                target_fn()
                loop.close.assert_called_once()

    def test_cleanup_with_pending_tasks(self):
        loop = asyncio.SelectorEventLoop()
        loop.run_forever = MagicMock()
        loop.run_until_complete = MagicMock(return_value=None)
        loop.shutdown_asyncgens = MagicMock(return_value=None)
        loop.close = MagicMock(wraps=loop.close)

        async def dummy():
            await asyncio.sleep(3600)

        task = loop.create_task(dummy())

        with patch("asyncio.all_tasks", return_value={task}):
            with patch("apex.http_api.asyncio.new_event_loop", return_value=loop):
                with patch("threading.Thread") as mock_thread_cls:
                    mock_thread_instance = MagicMock()
                    mock_thread_cls.return_value = mock_thread_instance
                    start_tui_server(port=9999)
                    target_fn = mock_thread_cls.call_args[1]["target"]
                    target_fn()
                    loop.close.assert_called_once()

    def test_cleanup_inner_exception_caught(self):
        loop = asyncio.SelectorEventLoop()
        loop.run_forever = MagicMock()
        async def broken_shutdown():
            raise RuntimeError("shutdown failed")
        loop.shutdown_asyncgens = broken_shutdown
        loop.close = MagicMock()

        with patch("asyncio.all_tasks", return_value=set()):
            with patch("apex.http_api.asyncio.new_event_loop", return_value=loop):
                with patch("threading.Thread") as mock_thread_cls:
                    mock_thread_instance = MagicMock()
                    mock_thread_cls.return_value = mock_thread_instance
                    server = start_tui_server(port=9999)
                    server.start = AsyncMock()
                    target_fn = mock_thread_cls.call_args[1]["target"]
                    target_fn()
                loop.close.assert_not_called()


class TestRunServerKeyboardInterrupt:
    """Test run_server KeyboardInterrupt path."""

    @pytest.mark.asyncio
    async def test_run_server_keyboard_interrupt(self):
        with patch("apex.http_api.asyncio.Event.wait", side_effect=KeyboardInterrupt()):
            with patch.object(HTTPServer, "start", new_callable=AsyncMock):
                with patch.object(HTTPServer, "stop", new_callable=AsyncMock) as mock_stop:
                    await run_server(host="127.0.0.1", port=0, require_auth=False)
                    mock_stop.assert_called_once()


class TestSessionSaveSuccess:
    """Test session save success path."""

    @pytest.mark.asyncio
    async def test_session_save_success(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/session/save", json={"name": "test_session"})
            assert resp.status == 200
            data = await resp.json()
            assert "saved" in data


class TestChatBilling:
    """Test chat endpoint billing with key_info."""

    @pytest.mark.asyncio
    async def test_chat_with_billing(self):
        server = HTTPServer(require_auth=True)
        key_info = {"key_id": "test123", "workspace_id": "ws1"}
        with patch.object(server.auth_middleware, "authenticate",
                          return_value=(True, "test-key", key_info)):
            with patch.object(server.agent, "chat", return_value="response"):
                with patch("apex.http_api.billing_manager.record_usage") as mock_billing:
                    async with TestClient(TestServer(server.app)) as client:
                        resp = await client.post(
                            "/chat", json={"message": "hi"},
                            headers={"Authorization": "Bearer test-key"},
                        )
                        assert resp.status == 200
                        mock_billing.assert_called_once()


class TestChatStreamBilling:
    """Test chat_stream endpoint billing with key_info."""

    @pytest.mark.asyncio
    async def test_chat_stream_with_billing(self):
        server = HTTPServer(require_auth=True)
        key_info = {"key_id": "test123", "workspace_id": "ws1"}
        async def mock_stream(msg):
            yield "token"
        with patch.object(server.auth_middleware, "authenticate",
                          return_value=(True, "test-key", key_info)):
            with patch.object(server.agent, "chat_streaming", mock_stream):
                with patch("apex.http_api.billing_manager.record_usage") as mock_billing:
                    async with TestClient(TestServer(server.app)) as client:
                        resp = await client.post(
                            "/chat/stream", json={"message": "hi"},
                            headers={"Authorization": "Bearer test-key"},
                        )
                        assert resp.status == 200
                        mock_billing.assert_called_once()


class TestV1SessionsDeleteDetailedFull:
    """Comprehensive session delete endpoint testing."""

    @pytest.fixture
    def server(self):
        return HTTPServer(host="127.0.0.1", port=0, require_auth=False)

    @pytest.mark.asyncio
    async def test_delete_by_filename_pattern(self, server, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            sessions_dir = tmp_path / ".apex" / "sessions"
            sessions_dir.mkdir(parents=True)
            sfile = sessions_dir / "20250101_test_myid123.json"
            sfile.write_text(json.dumps({"name": "test", "session_id": "myid123"}))
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.delete("/api/v1/sessions/myid123")
                assert resp.status == 200
                data = await resp.json()
                assert data["deleted"] == "myid123"
                assert not sfile.exists()

    @pytest.mark.asyncio
    async def test_delete_by_json_content(self, server, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            sessions_dir = tmp_path / ".apex" / "sessions"
            sessions_dir.mkdir(parents=True)
            file1 = sessions_dir / "random_name.json"
            file1.write_text(json.dumps({"session_id": "target_id", "name": "myname"}))
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.delete("/api/v1/sessions/target_id")
                assert resp.status == 200
                assert not file1.exists()

    @pytest.mark.asyncio
    async def test_delete_by_name(self, server, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            sessions_dir = tmp_path / ".apex" / "sessions"
            sessions_dir.mkdir(parents=True)
            file1 = sessions_dir / "other.json"
            file1.write_text(json.dumps({"name": "session_name", "session_id": "sid1"}))
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.delete("/api/v1/sessions/session_name")
                assert resp.status == 200

    @pytest.mark.asyncio
    async def test_delete_second_loop_exception_skipped(self, server, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            sessions_dir = tmp_path / ".apex" / "sessions"
            sessions_dir.mkdir(parents=True)
            real_read_text = Path.read_text
            call_count = 0
            def mock_read_text(self_inst):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return "{{{not valid json"
                return real_read_text(self_inst)
            with patch.object(Path, "read_text", mock_read_text):
                bad = sessions_dir / "aaa_bad.json"
                bad.write_text("{invalid}")
                good = sessions_dir / "zzz_good.json"
                good.write_text(json.dumps({"session_id": "valid_id"}))
                async with TestClient(TestServer(server.app)) as client:
                    resp = await client.delete("/api/v1/sessions/valid_id")
                    assert resp.status == 200

    @pytest.mark.asyncio
    async def test_delete_second_loop_parse_error_only(self, server, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            sessions_dir = tmp_path / ".apex" / "sessions"
            sessions_dir.mkdir(parents=True)
            f = sessions_dir / "a.json"
            f.write_text("{broken")
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.delete("/api/v1/sessions/x")
                assert resp.status == 404

    @pytest.mark.asyncio
    async def test_delete_exception_handler(self, server):
        with patch("apex.http_api.Path.home", side_effect=PermissionError("denied")):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.delete("/api/v1/sessions/test")
                assert resp.status == 500


class TestV1AuthLogoutLowercase:
    """Test auth_logout lowercase env var handling."""

    @pytest.mark.asyncio
    async def test_logout_lowercase_env_var(self):
        server = HTTPServer(require_auth=False)
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
            "openai_api_key": "sk-test-lower",
        }, clear=True):
            async with TestClient(TestServer(server.app)) as client:
                resp = await client.post("/api/v1/auth/logout", json={})
                assert resp.status == 200
                data = await resp.json()
                assert "openai_api_key" in data["env_vars"]
