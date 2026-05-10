"""Tests for refactored MCP module."""

import asyncio

from apex.refactored_mcp import (
    MCPResource, MCPTool, MCPServerConfig,
    MCPProtocolHandler, MCPToolManager, MCPClient, MCPManager,
    create_mcp_client, create_mcp_manager
)


class TestMCPResource:
    def test_create(self):
        resource = MCPResource(uri="file:///test", name="test", description="Test file")
        assert resource.uri == "file:///test"
        assert resource.name == "test"


class TestMCPTool:
    def test_create(self):
        tool = MCPTool(name="test_tool", description="A test tool", input_schema={"type": "object"})
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
    
    def test_to_dict(self):
        tool = MCPTool(name="test", description="Test", input_schema={"type": "object"})
        d = tool.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "Test"
        assert d["inputSchema"] == {"type": "object"}


class TestMCPServerConfig:
    def test_create_defaults(self):
        config = MCPServerConfig(name="test", command="echo")
        assert config.name == "test"
        assert config.command == "echo"
        assert config.enabled is True
        assert config.transport == "stdio"
    
    def test_create_full(self):
        config = MCPServerConfig(
            name="test", command="echo", args=["arg"], env={"VAR": "val"}, 
            enabled=False, transport="http"
        )
        assert config.args == ["arg"]
        assert config.env == {"VAR": "val"}
        assert config.enabled is False
        assert config.transport == "http"


class TestMCPProtocolHandler:
    def test_create_request(self):
        handler = MCPProtocolHandler()
        req = handler.create_request("test_method", {"param": "value"})
        assert req["jsonrpc"] == "2.0"
        assert req["method"] == "test_method"
        assert req["params"] == {"param": "value"}
        assert req["id"] == 1
    
    def test_create_response_with_result(self):
        handler = MCPProtocolHandler()
        resp = handler.create_response(1, result={"data": "value"})
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert resp["result"] == {"data": "value"}
    
    def test_create_response_with_error(self):
        handler = MCPProtocolHandler()
        resp = handler.create_response(1, error={"code": -32600, "message": "Invalid request"})
        assert resp["error"]["code"] == -32600
    
    def test_parse_message_valid(self):
        handler = MCPProtocolHandler()
        msg = handler.parse_message('{"jsonrpc": "2.0", "id": 1, "result": {}}')
        assert msg["jsonrpc"] == "2.0"
    
    def test_parse_message_invalid(self):
        handler = MCPProtocolHandler()
        msg = handler.parse_message("invalid json")
        assert msg is None
    
    def test_serialize_message(self):
        handler = MCPProtocolHandler()
        msg = {"jsonrpc": "2.0", "id": 1, "result": {}}
        serialized = handler.serialize_message(msg)
        assert '"jsonrpc"' in serialized


class TestMCPToolManager:
    def test_add_tool(self):
        mgr = MCPToolManager()
        tool = MCPTool(name="test", description="Test")
        mgr.add_tool(tool)
        assert "test" in mgr._tools
    
    def test_get_tool_exists(self):
        mgr = MCPToolManager()
        tool = MCPTool(name="test", description="Test")
        mgr.add_tool(tool)
        retrieved = mgr.get_tool("test")
        assert retrieved is tool
    
    def test_get_tool_not_exists(self):
        mgr = MCPToolManager()
        retrieved = mgr.get_tool("nonexistent")
        assert retrieved is None
    
    def test_get_all_tools(self):
        mgr = MCPToolManager()
        mgr.add_tool(MCPTool(name="t1", description="T1"))
        mgr.add_tool(MCPTool(name="t2", description="T2"))
        tools = mgr.get_all_tools()
        assert len(tools) == 2
    
    def test_get_tool_schemas(self):
        mgr = MCPToolManager()
        mgr.add_tool(MCPTool(name="test", description="Test", input_schema={"type": "object"}))
        schemas = mgr.get_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "test"


class TestMCPClient:
    def test_init(self):
        config = MCPServerConfig(name="test", command="echo")
        client = MCPClient(config)
        assert client.config == config
        assert client.protocol is not None
        assert client.tool_manager is not None
    
    def test_list_tools_empty(self):
        config = MCPServerConfig(name="test", command="echo")
        client = MCPClient(config)
        tools = client.list_tools()
        assert tools == []
    
    def test_list_tools_with_tools(self):
        config = MCPServerConfig(name="test", command="echo")
        client = MCPClient(config)
        client.tool_manager.add_tool(MCPTool(name="test", description="Test"))
        tools = client.list_tools()
        assert len(tools) == 1
    
    def test_get_tool_schemas(self):
        config = MCPServerConfig(name="test", command="echo")
        client = MCPClient(config)
        client.tool_manager.add_tool(MCPTool(name="test", description="Test", input_schema={}))
        schemas = client.get_tool_schemas()
        assert len(schemas) == 1
    
    def test_call_tool_not_exists(self):
        config = MCPServerConfig(name="test", command="echo")
        client = MCPClient(config)
        result = asyncio.run(client.call_tool("nonexistent", {}))
        assert "ERROR" in result
    
    def test_call_tool_exists(self):
        config = MCPServerConfig(name="test", command="echo")
        client = MCPClient(config)
        client.tool_manager.add_tool(MCPTool(name="test", description="Test"))
        result = asyncio.run(client.call_tool("test", {"arg": "value"}))
        assert "test" in result


class TestMCPManager:
    def test_init(self):
        mgr = MCPManager()
        assert mgr._servers == {}
        assert mgr._configs == {}
    
    def test_add_server(self):
        mgr = MCPManager()
        mgr.add_server("test", "echo", ["arg"], {"VAR": "val"}, True)
        assert "test" in mgr._servers
        assert "test" in mgr._configs
    
    def test_get_all_tools_empty(self):
        mgr = MCPManager()
        tools = mgr.get_all_tools()
        assert tools == []


class TestFactoryFunctions:
    def test_create_mcp_client(self):
        client = create_mcp_client("test", "echo", ["arg"], {"VAR": "val"}, True)
        assert isinstance(client, MCPClient)
        assert client.config.name == "test"
    
    def test_create_mcp_manager(self):
        mgr = create_mcp_manager()
        assert isinstance(mgr, MCPManager)