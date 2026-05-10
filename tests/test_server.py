"""Tests for server module."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from apex.server import APEXClient, APEXServer


class TestAPEXClient:
    """Test APEXClient class."""

    def test_init(self):
        """Test initialization."""
        client = APEXClient("test-id", "test-name")
        assert client.id == "test-id"
        assert client.name == "test-name"
        assert client.model == "gpt-4o-mini"
        assert client.agent_mode == "build"

    def test_to_dict(self):
        """Test to_dict method."""
        client = APEXClient("test-id", "test-name")
        data = client.to_dict()
        assert data["id"] == "test-id"
        assert data["name"] == "test-name"
        assert "connected_at" in data


class TestAPEXServer:
    """Test APEXServer class."""

    @pytest.fixture
    def server(self):
        """Create server instance."""
        return APEXServer(host="127.0.0.1", port=8080)

    def test_init(self):
        """Test server initialization."""
        server = APEXServer(host="0.0.0.0", port=9000)
        assert server.host == "0.0.0.0"
        assert server.port == 9000
        assert server.clients == {}

    def test_set_agent(self):
        """Test set_agent method."""
        server = APEXServer()
        mock_agent = MagicMock()
        server.set_agent(mock_agent)
        assert server._agent == mock_agent

    @pytest.mark.asyncio
    async def test_get_status_empty(self, server):
        """Test get_status with no clients."""
        status = await server.get_status()
        assert status["host"] == "127.0.0.1"
        assert status["port"] == 8080
        assert status["clients"] == 0

    @pytest.mark.asyncio
    async def test_get_status_with_client(self, server):
        """Test get_status with clients."""
        client = APEXClient("test-id", "test-name")
        server.clients["test-id"] = client
        server._agent = MagicMock()
        server._agent.model = "gpt-4o"
        server._agent.current_agent = "build"

        status = await server.get_status()
        assert status["clients"] == 1
        assert status["agent_model"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_broadcast(self, server):
        """Test broadcast to websockets."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        server._websockets = {ws1, ws2}

        await server.broadcast({"type": "test"})
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()


class TestAPEXServerMethods:
    """Test server HTTP handlers."""

    @pytest.fixture
    def server(self):
        """Create server with mock agent."""
        server = APEXServer()
        mock_agent = MagicMock()
        mock_agent.model = "gpt-4o-mini"
        mock_agent.current_agent = "build"
        mock_agent.usage = {"prompt_tokens": 100, "completion_tokens": 50}
        mock_agent.chat = MagicMock(return_value="test response")
        server.set_agent(mock_agent)
        return server

    @pytest.mark.asyncio
    async def test_process_chat_with_agent(self, server):
        """Test chat processing with agent."""
        result = await server._process_chat("client-id", {"message": "hello"})
        assert "response" in result

    @pytest.mark.asyncio
    async def test_process_chat_no_agent(self, server):
        """Test chat processing without agent."""
        server._agent = None
        result = await server._process_chat("client-id", {"message": "hello"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_tool_with_agent(self, server):
        """Test tool execution with agent."""
        result = await server._execute_tool("read_file", {"path": "test.py"})
        assert "ERROR" not in result

    @pytest.mark.asyncio
    async def test_execute_tool_no_agent(self, server):
        """Test tool execution without agent."""
        server._agent = None
        result = await server._execute_tool("read_file", {"path": "test.py"})
        assert "ERROR" in result
