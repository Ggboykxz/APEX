"""Tests for http_api.py module."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from apex.http_api import (
    HTTPServer,
    AuthMiddleware,
    RateLimitConfig,
)


class TestRateLimitConfig:
    """Test RateLimitConfig for HTTP API."""

    def test_default_config(self):
        config = RateLimitConfig()
        assert config.requests_per_minute == 60

    def test_custom_config(self):
        config = RateLimitConfig(requests_per_minute=100)
        assert config.requests_per_minute == 100


class TestAuthMiddleware:
    """Test AuthMiddleware class."""

    @pytest.fixture
    def middleware(self):
        return AuthMiddleware(require_auth=True)

    @pytest.fixture
    def middleware_no_auth(self):
        return AuthMiddleware(require_auth=False)

    @pytest.mark.asyncio
    async def test_authenticate_bearer_token(self, middleware):
        request = MagicMock()
        request.headers = {"Authorization": "Bearer apex_test_key_123"}
        request.query = {}

        with patch("apex.http_api.key_manager") as mock_km:
            mock_km.validate_key.return_value = {"key_id": "test"}
            success, key, info = await middleware.authenticate(request)
            assert success is True

    @pytest.mark.asyncio
    async def test_authenticate_x_api_key_header(self, middleware):
        request = MagicMock()
        request.headers = {"X-API-Key": "apex_test_key_123"}
        request.query = {}

        with patch("apex.http_api.key_manager") as mock_km:
            mock_km.validate_key.return_value = {"key_id": "test"}
            success, key, info = await middleware.authenticate(request)
            assert success is True

    @pytest.mark.asyncio
    async def test_authenticate_query_param(self, middleware):
        request = MagicMock()
        request.headers = {}
        request.query = {"api_key": "apex_test_key_123"}

        with patch("apex.http_api.key_manager") as mock_km:
            mock_km.validate_key.return_value = {"key_id": "test"}
            success, key, info = await middleware.authenticate(request)
            assert success is True

    @pytest.mark.asyncio
    async def test_authenticate_no_key(self, middleware):
        request = MagicMock()
        request.headers = {}
        request.query = {}

        success, key, info = await middleware.authenticate(request)
        assert success is False
        assert key is None

    @pytest.mark.asyncio
    async def test_authenticate_disabled(self, middleware_no_auth):
        request = MagicMock()
        request.headers = {}

        success, key, info = await middleware_no_auth.authenticate(request)
        assert success is True


class TestHTTPServer:
    """Test HTTPServer class."""

    @pytest.fixture
    def server(self):
        return HTTPServer(host="127.0.0.1", port=8080, require_auth=False)

    def test_init_default(self):
        server = HTTPServer()
        assert server.host == "127.0.0.1"
        assert server.port == 8080
        assert server.require_auth is True

    def test_init_custom(self):
        server = HTTPServer(host="0.0.0.0", port=9000, require_auth=False)
        assert server.host == "0.0.0.0"
        assert server.port == 9000
        assert server.require_auth is False

    def test_setup_routes(self, server):
        assert server.app is not None

    @pytest.mark.asyncio
    async def test_health(self, server):
        request = MagicMock()
        response = await server.health(request)
        assert response.status == 200
        data = json.loads(response.text)
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_index(self, server):
        request = MagicMock()
        response = await server.index(request)
        assert response.status == 200
        assert "text/html" in response.content_type

    @pytest.mark.asyncio
    async def test_list_models(self, server):
        request = MagicMock()
        response = await server.list_models(request)
        assert response.status == 200
        data = json.loads(response.text)
        assert "models" in data

    @pytest.mark.asyncio
    async def test_chat_without_auth(self):
        server = HTTPServer(host="127.0.0.1", port=8080, require_auth=True)

        request = MagicMock()
        request.json = AsyncMock(return_value={"message": "hello"})
        response = await server.chat(request)
        assert response.status == 401

    @pytest.mark.asyncio
    async def test_chat_rate_limited(self):
        server = HTTPServer(
            host="127.0.0.1",
            port=8080,
            require_auth=False,
            rate_limit_config=RateLimitConfig(requests_per_minute=1),
        )

        request = MagicMock()
        request.json = AsyncMock(return_value={"message": "hello"})
        server.rate_limiter.check_rate_limit = MagicMock(
            return_value=MagicMock(
                allowed=False, retry_after=60, remaining_minute=0, remaining_hour=0, remaining_day=0
            )
        )

        response = await server.chat(request)
        assert response.status == 429

    @pytest.mark.asyncio
    async def test_rate_limit_status(self, server):
        request = MagicMock()
        response = await server.rate_limit_status(request)
        assert response.status == 200
        data = json.loads(response.text)
        assert "minute" in data

    @pytest.mark.asyncio
    async def test_metrics_without_auth(self):
        server = HTTPServer(host="127.0.0.1", port=8080, require_auth=True)
        request = MagicMock()
        response = await server.metrics(request)
        assert response.status == 401

    @pytest.mark.asyncio
    async def test_session_save_without_auth(self):
        server = HTTPServer(host="127.0.0.1", port=8080, require_auth=True)
        request = MagicMock()
        response = await server.session_save(request)
        assert response.status == 401

    @pytest.mark.asyncio
    async def test_session_load_without_auth(self):
        server = HTTPServer(host="127.0.0.1", port=8080, require_auth=True)
        request = MagicMock()
        response = await server.session_load(request)
        assert response.status == 401

    @pytest.mark.asyncio
    async def test_chat_stream_without_auth(self):
        server = HTTPServer(host="127.0.0.1", port=8080, require_auth=True)
        request = MagicMock()
        response = await server.chat_stream(request)
        assert response.status == 401
