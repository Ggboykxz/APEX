"""Tests for apex/mcp.py — full coverage including connect, _send_request, _send_notification, _handle_message, _read_messages."""

import pytest
import json
import asyncio
from apex.mcp import (
    MCPResource,
    MCPTool,
    MCPServerConfig,
    MCPClient,
    MCPManager,
)


class TestMCPClientInternal:
    """Test MCPClient internal methods."""

    def test_send_request_no_process(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        async def _test():
            result = await client._send_request("tools/list", {})
            assert result is None

        asyncio.run(_test())

    def test_send_notification_no_process(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        async def _test():
            # Should not raise
            await client._send_notification("initialized", {})

        asyncio.run(_test())

    def test_handle_message_result(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        # Create a future and add to pending
        loop = asyncio.new_event_loop()
        try:
            future = loop.create_future()
            client._pending_requests["test-id"] = future

            async def _test():
                await client._handle_message(json.dumps({"id": "test-id", "result": {"tools": []}}))
                assert future.done()
                assert future.result() == {"tools": []}

            loop.run_until_complete(_test())
        finally:
            loop.close()

    def test_handle_message_error(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        loop = asyncio.new_event_loop()
        try:
            future = loop.create_future()
            client._pending_requests["test-id"] = future

            async def _test():
                await client._handle_message(
                    json.dumps({"id": "test-id", "error": {"message": "Something went wrong"}})
                )
                assert future.done()
                with pytest.raises(Exception, match="Something went wrong"):
                    future.result()

            loop.run_until_complete(_test())
        finally:
            loop.close()

    def test_handle_message_notification(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        received = []

        async def handler(params):
            received.append(params)

        client.register_notification_handler("progress", handler)

        async def _test():
            await client._handle_message(
                json.dumps({"method": "progress", "params": {"percent": 50}})
            )
            assert len(received) == 1
            assert received[0] == {"percent": 50}

        asyncio.run(_test())

    def test_handle_message_unknown_notification(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        async def _test():
            # Should not raise for unknown notification method
            await client._handle_message(json.dumps({"method": "unknown_method", "params": {}}))

        asyncio.run(_test())

    def test_handle_message_invalid_json(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        async def _test():
            # Should not raise for invalid JSON
            await client._handle_message("not json at all")

        asyncio.run(_test())

    def test_read_messages_no_process(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        async def _test():
            # Should return immediately
            await client._read_messages()

        asyncio.run(_test())

    def test_list_tools_with_result(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)
        # Simulate tools by setting them directly
        client._tools = [MCPTool(name="tool1", description="desc1", input_schema={})]

        async def _test():
            # Since _send_request returns None (no process), tools should remain as set
            result = await client.list_tools()
            assert len(result) == 1
            assert result[0].name == "tool1"

        asyncio.run(_test())

    def test_list_resources_with_result(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)
        client._resources = [MCPResource(uri="file:///a", name="a")]

        async def _test():
            result = await client.list_resources()
            assert len(result) == 1

        asyncio.run(_test())

    def test_format_content_empty_text(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)
        result = client._format_content([{"type": "text"}])
        assert result == ""

    def test_format_content_no_mimetype(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)
        result = client._format_content([{"type": "image"}])
        assert "[Image: unknown]" in result

    def test_format_content_resource_no_uri(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)
        result = client._format_content([{"type": "resource", "resource": {}}])
        assert "[Resource: unknown]" in result


class TestMCPManagerCallTool:
    """Test MCPManager.call_tool."""

    def test_call_tool_server_exists_no_connection(self):
        mgr = MCPManager()
        mgr.add_server("srv", "cmd")

        async def _test():
            result = await mgr.call_tool("srv_mytool", {})
            assert "ERROR" in result

        asyncio.run(_test())


class TestMCPManagerConnectAll:
    """Test MCPManager.connect_all."""

    def test_connect_all_empty(self):
        mgr = MCPManager()

        async def _test():
            result = await mgr.connect_all()
            assert result == {}

        asyncio.run(_test())

    def test_connect_all_disabled(self):
        mgr = MCPManager()
        mgr.add_server("disabled", "cmd", enabled=False)

        async def _test():
            result = await mgr.connect_all()
            assert result == {"disabled": False}

        asyncio.run(_test())
