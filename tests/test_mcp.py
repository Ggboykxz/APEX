"""Tests for apex/mcp.py — MCPClient, MCPManager, dataclasses, _format_content."""

from apex.mcp import (
    MCPResource,
    MCPTool,
    MCPServerConfig,
    MCPMessage,
    MCPClient,
    MCPManager,
    mcp_manager,
    load_mcp_config,
)


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestMCPResource:
    def test_creation(self):
        r = MCPResource(
            uri="file:///test.txt", name="test", description="A file", mime_type="text/plain"
        )
        assert r.uri == "file:///test.txt"
        assert r.name == "test"
        assert r.description == "A file"
        assert r.mime_type == "text/plain"

    def test_defaults(self):
        r = MCPResource(uri="u", name="n")
        assert r.description == ""
        assert r.mime_type == ""


class TestMCPTool:
    def test_creation(self):
        t = MCPTool(name="tool1", description="Does things", input_schema={"type": "object"})
        assert t.name == "tool1"
        assert t.description == "Does things"
        assert t.input_schema == {"type": "object"}

    def test_defaults(self):
        t = MCPTool(name="tool1", description="desc")
        assert t.input_schema == {}


class TestMCPServerConfig:
    def test_creation(self):
        cfg = MCPServerConfig(
            name="srv", command="node", args=["a"], env={"K": "v"}, enabled=False, transport="http"
        )
        assert cfg.name == "srv"
        assert cfg.command == "node"
        assert cfg.args == ["a"]
        assert cfg.env == {"K": "v"}
        assert cfg.enabled is False
        assert cfg.transport == "http"

    def test_defaults(self):
        cfg = MCPServerConfig(name="srv", command="cmd")
        assert cfg.args == []
        assert cfg.env == {}
        assert cfg.enabled is True
        assert cfg.transport == "stdio"


class TestMCPMessage:
    def test_defaults(self):
        msg = MCPMessage()
        assert msg.jsonrpc == "2.0"
        assert msg.id is None
        assert msg.method is None
        assert msg.params is None
        assert msg.result is None
        assert msg.error is None

    def test_with_values(self):
        msg = MCPMessage(id=1, method="initialize", params={"a": 1})
        assert msg.id == 1
        assert msg.method == "initialize"
        assert msg.params == {"a": 1}


# ---------------------------------------------------------------------------
# MCPClient tests
# ---------------------------------------------------------------------------


class TestMCPClient:
    def test_init(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)
        assert client.config is cfg
        assert client.process is None
        assert client._tools == []
        assert client._resources == []
        assert client._capabilities == {}
        assert client._request_id == 0
        assert client._pending_requests == {}
        assert client._reader_task is None
        assert client._notification_handlers == {}

    def test_connect_disabled(self):
        cfg = MCPServerConfig(name="test", command="echo", enabled=False)
        client = MCPClient(cfg)

        async def _test():
            result = await client.connect()
            assert result is False

        import asyncio

        asyncio.run(_test())

    def test_format_content_text(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)
        result = client._format_content([{"type": "text", "text": "hello"}])
        assert result == "hello"

    def test_format_content_image(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)
        result = client._format_content([{"type": "image", "mimeType": "image/png"}])
        assert "[Image: image/png]" in result

    def test_format_content_resource(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)
        result = client._format_content([{"type": "resource", "resource": {"uri": "file:///x"}}])
        assert "[Resource: file:///x]" in result

    def test_format_content_multiple(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)
        result = client._format_content(
            [
                {"type": "text", "text": "hello"},
                {"type": "image", "mimeType": "image/png"},
            ]
        )
        assert "hello" in result
        assert "[Image: image/png]" in result

    def test_get_tool_schemas_empty(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)
        assert client.get_tool_schemas() == []

    def test_get_tool_schemas_with_tools(self):
        cfg = MCPServerConfig(name="myserver", command="echo")
        client = MCPClient(cfg)
        client._tools = [
            MCPTool(name="tool1", description="desc1", input_schema={"type": "object"}),
            MCPTool(
                name="tool2", description="desc2", input_schema={"type": "object", "properties": {}}
            ),
        ]
        schemas = client.get_tool_schemas()
        assert len(schemas) == 2
        assert schemas[0]["function"]["name"] == "mcp_myserver_tool1"
        assert schemas[0]["function"]["description"] == "[myserver] desc1"
        assert schemas[1]["function"]["name"] == "mcp_myserver_tool2"

    def test_register_notification_handler(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        called = []

        def handler(params):
            called.append(params)

        client.register_notification_handler("test_method", handler)
        assert "test_method" in client._notification_handlers
        assert client._notification_handlers["test_method"] is handler

    def test_disconnect_no_process(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)
        # Should not raise
        import asyncio

        asyncio.run(client.disconnect())

    def test_call_tool_no_connection(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        async def _test():
            result = await client.call_tool("tool1", {})
            assert result == "ERROR: Tool call failed"

        import asyncio

        asyncio.run(_test())

    def test_list_tools_no_connection(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        async def _test():
            result = await client.list_tools()
            assert result == []

        import asyncio

        asyncio.run(_test())

    def test_list_resources_no_connection(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        async def _test():
            result = await client.list_resources()
            assert result == []

        import asyncio

        asyncio.run(_test())

    def test_read_resource_no_connection(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        async def _test():
            result = await client.read_resource("file:///test")
            assert result == "ERROR: Resource not found"

        import asyncio

        asyncio.run(_test())

    def test_list_prompts_no_connection(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        async def _test():
            result = await client.list_prompts()
            assert result == []

        import asyncio

        asyncio.run(_test())

    def test_get_prompt_no_connection(self):
        cfg = MCPServerConfig(name="test", command="echo")
        client = MCPClient(cfg)

        async def _test():
            result = await client.get_prompt("test_prompt")
            assert result == "ERROR: Prompt not found"

        import asyncio

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# MCPManager tests
# ---------------------------------------------------------------------------


class TestMCPManager:
    def test_init(self):
        mgr = MCPManager()
        assert mgr._servers == {}
        assert mgr._configs == {}

    def test_add_server(self):
        mgr = MCPManager()
        mgr.add_server("files", "ls", args=["-la"], env={}, enabled=True)
        assert "files" in mgr._configs
        assert "files" in mgr._servers
        assert mgr._configs["files"].command == "ls"
        assert mgr._configs["files"].enabled is True

    def test_add_server_defaults(self):
        mgr = MCPManager()
        mgr.add_server("test", "cmd")
        assert mgr._configs["test"].args == []
        assert mgr._configs["test"].env == {}
        assert mgr._configs["test"].enabled is True

    def test_list_servers(self):
        mgr = MCPManager()
        mgr.add_server("srv1", "cmd1", enabled=True)
        mgr.add_server("srv2", "cmd2", enabled=False)
        servers = mgr.list_servers()
        assert len(servers) == 2
        names = {s["name"] for s in servers}
        assert "srv1" in names
        assert "srv2" in names

    def test_list_servers_tools_count(self):
        mgr = MCPManager()
        mgr.add_server("srv1", "cmd1")
        servers = mgr.list_servers()
        assert servers[0]["tools_count"] == 0

    def test_get_all_tools(self):
        mgr = MCPManager()
        mgr.add_server("srv1", "cmd1")
        tools = mgr.get_all_tools()
        assert tools == []  # No tools loaded without connection

    def test_get_all_tools_with_tools(self):
        mgr = MCPManager()
        mgr.add_server("srv1", "cmd1")
        # Manually add tools to the client
        mgr._servers["srv1"]._tools = [MCPTool(name="tool1", description="desc", input_schema={})]
        tools = mgr.get_all_tools()
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "mcp_srv1_tool1"

    def test_call_tool_invalid_name(self):
        mgr = MCPManager()

        async def _test():
            result = await mgr.call_tool("invalid", {})
            assert "ERROR" in result

        import asyncio

        asyncio.run(_test())

    def test_call_tool_unknown_server(self):
        mgr = MCPManager()

        async def _test():
            result = await mgr.call_tool("unknown_tool", {})
            assert "ERROR" in result

        import asyncio

        asyncio.run(_test())

    def test_get_all_resources(self):
        mgr = MCPManager()
        mgr.add_server("srv1", "cmd1")
        resources = mgr.get_all_resources()
        assert resources == []

    def test_get_all_resources_with_data(self):
        mgr = MCPManager()
        mgr.add_server("srv1", "cmd1")
        mgr._servers["srv1"]._resources = [
            MCPResource(uri="file:///a", name="a", description="desc")
        ]
        resources = mgr.get_all_resources()
        assert len(resources) == 1
        assert resources[0]["server"] == "srv1"
        assert resources[0]["uri"] == "file:///a"

    def test_disconnect_all(self):
        mgr = MCPManager()
        mgr.add_server("srv1", "cmd1")

        async def _test():
            await mgr.disconnect_all()  # Should not raise

        import asyncio

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# Global instance and load_mcp_config
# ---------------------------------------------------------------------------


class TestGlobalInstances:
    def test_mcp_manager_global(self):
        assert mcp_manager is not None
        assert isinstance(mcp_manager, MCPManager)


class TestLoadMcpConfig:
    def test_nonexistent_file(self):
        from pathlib import Path

        # Should not raise
        load_mcp_config(Path("/nonexistent/config.yaml"))

    def test_empty_file(self, tmp_path):
        config_path = tmp_path / "empty.yaml"
        config_path.write_text("")
        # Should not raise (yaml may or may not be installed)
        try:
            load_mcp_config(config_path)
        except ImportError:
            pass  # yaml not installed, that's OK

    def test_no_mcp_servers_key(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("other_key: value\n")
        try:
            load_mcp_config(config_path)
        except ImportError:
            pass
