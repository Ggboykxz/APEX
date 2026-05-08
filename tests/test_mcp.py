"""Tests for APEX MCP support."""

import pytest
from apex.mcp import MCP_SERVER, MCPClient, MCPManager, mcp_manager, MCPResource, MCPTool


def test_mcp_server_creation():
    server = MCP_SERVER(
        name="test-server",
        command="node",
        args=["server.js"],
        env={"KEY": "value"},
        enabled=True
    )
    assert server.name == "test-server"
    assert server.command == "node"
    assert server.enabled is True


def test_mcp_manager_add_server():
    manager = MCPManager()
    manager.add_server("files", "ls", enabled=False)
    assert "files" in manager._servers
    assert manager._servers["files"].server.enabled is False


def test_mcp_manager_list_servers():
    manager = MCPManager()
    manager.add_server("server1", "cmd", enabled=True)
    manager.add_server("server2", "cmd", enabled=False)

    servers = manager.list_servers()
    assert len(servers) == 2
    names = [s["name"] for s in servers]
    assert "server1" in names
    assert "server2" in names


def test_mcp_tool_schema_format():
    server = MCP_SERVER(name="test", command="cmd")
    client = MCPClient(server)
    client._tools = [
        MCPTool(name="tool1", description="Does things", input_schema={"type": "object"})
    ]

    schemas = client.get_tool_schemas()
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "mcp_test_tool1"


def test_mcp_resource_creation():
    resource = MCPResource(
        uri="file:///test.txt",
        name="test",
        description="A test file",
        mime_type="text/plain"
    )
    assert resource.uri == "file:///test.txt"
    assert resource.mime_type == "text/plain"


def test_mcp_manager_global():
    assert mcp_manager is not None
    assert isinstance(mcp_manager, MCPManager)