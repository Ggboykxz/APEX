"""Tests for refactored MCP module — no mocks, real operations."""

import asyncio

from apex.refactored_mcp import (
    MCPResource,
    MCPTool,
    MCPServerConfig,
    MCPProtocolHandler,
    MCPToolManager,
    MCPClient,
    MCPManager,
    create_mcp_client,
    create_mcp_manager,
)


class TestMCPResource:
    def test_create(self):
        resource = MCPResource(uri="file:///test", name="test", description="Test file")
        assert resource.uri == "file:///test"
        assert resource.name == "test"
        assert resource.description == "Test file"

    def test_defaults(self):
        resource = MCPResource(uri="file:///test", name="test")
        assert resource.description == ""
        assert resource.mime_type == ""


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

    def test_to_dict_default_schema(self):
        tool = MCPTool(name="test", description="Test")
        d = tool.to_dict()
        assert d["inputSchema"] == {}


class TestMCPServerConfig:
    def test_create_defaults(self):
        config = MCPServerConfig(name="test", command="echo")
        assert config.name == "test"
        assert config.command == "echo"
        assert config.args == []
        assert config.env == {}
        assert config.enabled is True
        assert config.transport == "stdio"

    def test_create_full(self):
        config = MCPServerConfig(
            name="test",
            command="echo",
            args=["arg"],
            env={"VAR": "val"},
            enabled=False,
            transport="http",
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

    def test_create_request_increments_id(self):
        handler = MCPProtocolHandler()
        req1 = handler.create_request("m1")
        req2 = handler.create_request("m2")
        assert req1["id"] == 1
        assert req2["id"] == 2

    def test_create_request_no_params(self):
        handler = MCPProtocolHandler()
        req = handler.create_request("test")
        assert "params" not in req

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

    def test_create_response_result_and_error(self):
        handler = MCPProtocolHandler()
        resp = handler.create_response(1, result="ok", error={"code": -1})
        assert resp["result"] == "ok"
        assert resp["error"]["code"] == -1

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

    def test_round_trip(self):
        handler = MCPProtocolHandler()
        original = handler.create_request("test_method", {"key": "value"})
        serialized = handler.serialize_message(original)
        parsed = handler.parse_message(serialized)
        assert parsed["method"] == "test_method"
        assert parsed["params"]["key"] == "value"


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

    def test_get_all_tools_empty(self):
        mgr = MCPToolManager()
        tools = mgr.get_all_tools()
        assert tools == []

    def test_get_tool_schemas(self):
        mgr = MCPToolManager()
        mgr.add_tool(MCPTool(name="test", description="Test", input_schema={"type": "object"}))
        schemas = mgr.get_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "test"
        assert schemas[0]["inputSchema"] == {"type": "object"}


class TestMCPClient:
    def test_init(self):
        config = MCPServerConfig(name="test", command="echo")
        client = MCPClient(config)
        assert client.config == config
        assert client.protocol is not None
        assert client.tool_manager is not None
        assert client.process is None

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

    def test_connect_disabled(self):
        config = MCPServerConfig(name="test", command="echo", enabled=False)
        client = MCPClient(config)
        result = asyncio.run(client.connect())
        assert result is False

    def test_disconnect_no_process(self):
        config = MCPServerConfig(name="test", command="echo")
        client = MCPClient(config)
        # Should not raise
        asyncio.run(client.disconnect())


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

    def test_add_server_defaults(self):
        mgr = MCPManager()
        mgr.add_server("test", "echo")
        config = mgr._configs["test"]
        assert config.args == []
        assert config.env == {}
        assert config.enabled is True

    def test_get_all_tools_empty(self):
        mgr = MCPManager()
        tools = mgr.get_all_tools()
        assert tools == []

    def test_get_all_tools_with_tools(self):
        mgr = MCPManager()
        mgr.add_server("server1", "echo")
        mgr._servers["server1"].tool_manager.add_tool(
            MCPTool(name="tool1", description="T1", input_schema={})
        )
        tools = mgr.get_all_tools()
        assert len(tools) == 1

    def test_call_tool_invalid_name(self):
        mgr = MCPManager()
        result = asyncio.run(mgr.call_tool("invalidname", {}))
        assert "ERROR" in result
        assert "Invalid tool name" in result

    def test_call_tool_unknown_server(self):
        mgr = MCPManager()
        result = asyncio.run(mgr.call_tool("unknown_toolname", {}))
        assert "ERROR" in result
        assert "Unknown server" in result

    def test_call_tool_known_server(self):
        mgr = MCPManager()
        mgr.add_server("myserver", "echo")
        mgr._servers["myserver"].tool_manager.add_tool(MCPTool(name="mytool", description="T"))
        result = asyncio.run(mgr.call_tool("myserver_mytool", {"arg": "val"}))
        assert "mytool" in result

    def test_disconnect_all(self):
        mgr = MCPManager()
        mgr.add_server("s1", "echo")
        mgr.add_server("s2", "echo")
        # Should not raise
        asyncio.run(mgr.disconnect_all())


class TestFactoryFunctions:
    def test_create_mcp_client(self):
        client = create_mcp_client("test", "echo", ["arg"], {"VAR": "val"}, True)
        assert isinstance(client, MCPClient)
        assert client.config.name == "test"

    def test_create_mcp_manager(self):
        mgr = create_mcp_manager()
        assert isinstance(mgr, MCPManager)
