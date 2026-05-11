"""Tests for refactored config_tools module — no mocks, real operations."""

from apex.refactored_config_tools import (
    CustomTool,
    CustomToolManager,
    create_custom_tool_manager,
    load_custom_tools,
)


class TestCustomTool:
    def test_init(self):
        def handler(args):
            return "result"

        tool = CustomTool(
            name="test_tool",
            description="Test tool",
            parameters={"type": "object"},
            handler=handler,
        )
        assert tool.name == "test_tool"
        assert tool.description == "Test tool"
        assert tool.parameters == {"type": "object"}
        assert tool.handler is handler


class TestCustomToolManager:
    def test_init(self):
        manager = CustomToolManager()
        assert manager.tools == {}

    def test_register(self):
        manager = CustomToolManager()

        def handler(args):
            return "result"

        manager.register("test", "Test tool", {"type": "object"}, handler)
        assert "test" in manager.tools

    def test_register_multiple(self):
        manager = CustomToolManager()

        def handler(args):
            return "result"

        manager.register("tool1", "Tool 1", {}, handler)
        manager.register("tool2", "Tool 2", {}, handler)
        assert len(manager.tools) == 2

    def test_unregister(self):
        manager = CustomToolManager()

        def handler(args):
            return "result"

        manager.register("test", "Test", {}, handler)
        result = manager.unregister("test")
        assert result is True
        assert "test" not in manager.tools

    def test_unregister_unknown(self):
        manager = CustomToolManager()
        result = manager.unregister("unknown")
        assert result is False

    def test_get(self):
        manager = CustomToolManager()

        def handler(args):
            return "result"

        manager.register("test", "Test", {}, handler)
        tool = manager.get("test")
        assert tool is not None
        assert tool.name == "test"

    def test_get_unknown(self):
        manager = CustomToolManager()
        tool = manager.get("unknown")
        assert tool is None

    def test_list_tools(self):
        manager = CustomToolManager()

        def handler(args):
            return "result"

        manager.register("tool1", "Description 1", {"type": "object"}, handler)
        manager.register("tool2", "Description 2", {"type": "string"}, handler)
        tools = manager.list_tools()
        assert len(tools) == 2
        names = [t["name"] for t in tools]
        assert "tool1" in names
        assert "tool2" in names

    def test_execute(self):
        manager = CustomToolManager()

        def handler(args):
            return f"processed: {args.get('value', '')}"

        manager.register("test", "Test", {}, handler)
        result = manager.execute("test", {"value": "hello"})
        assert result == "processed: hello"

    def test_execute_unknown_tool(self):
        manager = CustomToolManager()
        result = manager.execute("unknown", {})
        assert "ERROR" in result
        assert "Unknown" in result

    def test_execute_handler_exception(self):
        manager = CustomToolManager()

        def handler(args):
            raise ValueError("test error")

        manager.register("test", "Test", {}, handler)
        result = manager.execute("test", {})
        assert "ERROR" in result
        assert "test error" in result

    def test_get_schemas(self):
        manager = CustomToolManager()

        def handler(args):
            return "result"

        manager.register("test", "Test tool", {"type": "object", "properties": {}}, handler)
        schemas = manager.get_schemas()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "custom_test"
        assert schemas[0]["function"]["description"] == "Test tool"
        assert schemas[0]["function"]["parameters"] == {"type": "object", "properties": {}}

    def test_clear(self):
        manager = CustomToolManager()

        def handler(args):
            return "result"

        manager.register("test", "Test", {}, handler)
        manager.clear()
        assert len(manager.tools) == 0


class TestFactoryFunctions:
    def test_create_custom_tool_manager(self):
        manager = create_custom_tool_manager()
        assert isinstance(manager, CustomToolManager)

    def test_create_custom_tool_manager_independent(self):
        manager1 = create_custom_tool_manager()
        manager2 = create_custom_tool_manager()

        def handler(args):
            return "result"

        manager1.register("test", "Test", {}, handler)
        assert len(manager1.tools) == 1
        assert len(manager2.tools) == 0


class TestLoadCustomTools:
    def test_load_custom_tools_file_not_exists(self, tmp_path):
        manager = CustomToolManager()
        load_custom_tools(tmp_path / "nonexistent.yaml", manager)
        assert len(manager.tools) == 0

    def test_load_custom_tools_no_config(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        manager = CustomToolManager()
        load_custom_tools(config_file, manager)
        assert len(manager.tools) == 0

    def test_load_custom_tools_no_custom_tools_key(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("other: value")
        manager = CustomToolManager()
        load_custom_tools(config_file, manager)
        assert len(manager.tools) == 0

    def test_load_custom_tools_valid_config_with_echo(self, tmp_path):
        """Load a real tool config and execute it with the real echo command."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
custom_tools:
  echo_tool:
    description: Echo tool
    command: echo {message}
    cwd: .
    enabled: true
    parameters:
      type: object
      properties:
        message:
          type: string
"""
        )
        manager = CustomToolManager()
        load_custom_tools(config_file, manager)
        assert "echo_tool" in manager.tools

        # Execute with real subprocess (echo is safe)
        result = manager.execute("echo_tool", {"message": "hello"})
        assert "hello" in result

    def test_load_custom_tools_disabled_tool(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
custom_tools:
  my_tool:
    enabled: false
"""
        )
        manager = CustomToolManager()
        load_custom_tools(config_file, manager)
        assert "my_tool" not in manager.tools

    def test_load_custom_tools_default_description(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
custom_tools:
  nodesc_tool:
    command: echo hello
    cwd: .
"""
        )
        manager = CustomToolManager()
        load_custom_tools(config_file, manager)
        assert "nodesc_tool" in manager.tools
        tool = manager.get("nodesc_tool")
        assert tool.description == "Custom tool"

    def test_load_custom_tools_invalid_yaml(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{{invalid yaml::")
        manager = CustomToolManager()
        # Should not raise, just handle gracefully
        load_custom_tools(config_file, manager)
