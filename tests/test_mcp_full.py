"""Tests for mcp module - simplified."""

from apex.mcp import MCPResource, MCPTool, MCPServerConfig, MCPMessage


class TestDataClasses:
    """Test MCP dataclasses."""

    def test_mcp_resource(self):
        r = MCPResource(uri="test://a", name="a", description="desc", mime_type="text")
        assert r.uri == "test://a"
        assert r.name == "a"

    def test_mcp_tool(self):
        t = MCPTool(name="tool", description="desc", input_schema={"type": "object"})
        assert t.name == "tool"

    def test_mcp_server_config(self):
        c = MCPServerConfig(name="srv", command="echo", args=["arg"], env={"K": "v"}, enabled=True, transport="stdio")
        assert c.name == "srv"
        assert c.enabled is True

    def test_mcp_message(self):
        m = MCPMessage(jsonrpc="2.0", id=1, method="test", params={}, result={}, error=None)
        assert m.jsonrpc == "2.0"