"""Tests for http_api module."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from apex.http_api import APEXHTTPServer


class TestAPEXHTTPServer:
    """Test APEXHTTPServer class."""

    @pytest.fixture
    def server(self):
        """Create server instance."""
        return APEXHTTPServer(host="127.0.0.1", port=8080)

    def test_init_default(self):
        """Test default initialization."""
        server = APEXHTTPServer()
        assert server.host == "0.0.0.0"
        assert server.port == 8080

    def test_init_custom(self):
        """Test custom initialization."""
        server = APEXHTTPServer(host="192.168.1.1", port=9000)
        assert server.host == "192.168.1.1"
        assert server.port == 9000

    def test_setup_routes(self, server):
        """Test route setup."""
        assert server.app is not None

    def test_agent_property(self, server):
        """Test agent property."""
        assert server.agent is not None


class TestHandlers:
    """Test HTTP handlers."""

    @pytest.fixture
    def server(self):
        """Create server with mock agent."""
        server = APEXHTTPServer()
        mock_agent = MagicMock()
        mock_agent.model = "gpt-4o"
        mock_agent.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        server._agent = mock_agent
        return server

    @pytest.mark.asyncio
    async def test_index(self, server):
        """Test index handler."""
        request = MagicMock()
        response = await server.index(request)
        assert "APEX" in response.text

    @pytest.mark.asyncio
    async def test_health(self, server):
        """Test health handler."""
        request = MagicMock()
        response = await server.health(request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_list_models(self, server):
        """Test list_models handler."""
        request = MagicMock()
        response = await server.list_models(request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_metrics(self, server):
        """Test metrics handler."""
        request = MagicMock()
        response = await server.metrics(request)
        assert response.status == 200