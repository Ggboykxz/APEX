"""Tests for http_api module — no mocks, real objects only."""

import pytest
from aiohttp.test_utils import TestClient, TestServer

from apex.http_api import (
    APEXHTTPServer,
    HTTPServer,
    RateLimitConfig,
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
            # Each model should have alias and model keys
            for m in data["models"]:
                assert "alias" in m
                assert "model" in m


class TestRateLimitStatusHandler:
    """Test the rate-limit status endpoint (no auth)."""

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


class TestChatHandlerNoAuth:
    """Test the chat endpoint without auth (require_auth=False)."""

    @pytest.mark.asyncio
    async def test_chat_rate_limited(self):
        """Trigger rate limiting by exhausting the minute limit."""
        cfg = RateLimitConfig(requests_per_minute=1, requests_per_hour=10, requests_per_day=100)
        server = HTTPServer(require_auth=False, rate_limit_config=cfg)
        async with TestClient(TestServer(server.app)) as client:
            # First request may succeed or get rate limited depending on
            # whether the chat handler actually calls the LLM.
            # We exhaust the rate limiter directly then check the response.
            # Pre-exhaust the rate limiter for the "anonymous" key.
            for _ in range(2):
                server.rate_limiter.check_rate_limit("anonymous")

            resp = await client.post("/chat", json={"message": "hello"})
            # After exhausting, the next request should be 429
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


class TestStartStop:
    """Test server start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        server = HTTPServer(host="127.0.0.1", port=0, require_auth=False)
        await server.start()
        assert server.runner is not None
        await server.stop()
        # runner should be cleaned up — second stop is a no-op
        await server.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        server = HTTPServer(require_auth=False)
        await server.stop()  # Should not raise


class TestCheckAuthViaEndpoints:
    """Test _check_auth behavior through actual endpoints."""

    @pytest.mark.asyncio
    async def test_check_auth_disabled_allows_access(self):
        """When auth is disabled, protected endpoints are accessible."""
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            # /metrics is a protected endpoint
            resp = await client.get("/metrics")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_check_auth_enabled_blocks_no_key(self):
        """When auth is enabled and no key is provided, return 401."""
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
        # Exhaust the limit
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
