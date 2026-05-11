"""Tests for apex/config_tools.py — CustomToolManager, load_custom_tools, ALLOWED_COMMANDS."""

from pathlib import Path
from apex.config_tools import (
    ALLOWED_COMMANDS,
    CustomTool,
    CustomToolManager,
    custom_tool_manager,
    load_custom_tools,
)


class TestAllowedCommands:
    def test_common_commands(self):
        assert "git" in ALLOWED_COMMANDS
        assert "python" in ALLOWED_COMMANDS
        assert "python3" in ALLOWED_COMMANDS
        assert "npm" in ALLOWED_COMMANDS
        assert "pytest" in ALLOWED_COMMANDS
        assert "make" in ALLOWED_COMMANDS
        assert "ls" in ALLOWED_COMMANDS
        assert "echo" in ALLOWED_COMMANDS


class TestCustomTool:
    def test_creation(self):
        tool = CustomTool(
            name="test",
            description="Test tool",
            parameters={"type": "object"},
            handler=lambda args: "ok",
        )
        assert tool.name == "test"
        assert tool.description == "Test tool"
        assert tool.parameters == {"type": "object"}
        assert tool.handler({"key": "val"}) == "ok"


class TestCustomToolManager:
    def test_init(self):
        mgr = CustomToolManager()
        assert mgr._tools == {}

    def test_register(self):
        mgr = CustomToolManager()
        mgr.register("test", "Test tool", {"type": "object"}, lambda args: "result")
        assert "test" in mgr._tools

    def test_get(self):
        mgr = CustomToolManager()
        mgr.register("test", "desc", {}, lambda args: "ok")
        tool = mgr.get("test")
        assert tool is not None
        assert tool.name == "test"

    def test_get_nonexistent(self):
        mgr = CustomToolManager()
        assert mgr.get("nonexistent") is None

    def test_list_tools(self):
        mgr = CustomToolManager()
        mgr.register("t1", "Tool 1", {}, lambda a: "1")
        mgr.register("t2", "Tool 2", {}, lambda a: "2")
        tools = mgr.list_tools()
        assert len(tools) == 2

    def test_execute(self):
        mgr = CustomToolManager()
        mgr.register("test", "desc", {}, lambda args: f"got {args.get('x', '')}")
        result = mgr.execute("test", {"x": "hello"})
        assert "hello" in result

    def test_execute_unknown(self):
        mgr = CustomToolManager()
        result = mgr.execute("unknown", {})
        assert "ERROR" in result

    def test_execute_exception(self):
        mgr = CustomToolManager()
        mgr.register("fail", "desc", {}, lambda args: 1 / 0)
        result = mgr.execute("fail", {})
        assert "ERROR" in result

    def test_get_schemas(self):
        mgr = CustomToolManager()
        mgr.register("test", "desc", {"type": "object"}, lambda a: "ok")
        schemas = mgr.get_schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "custom_test"

    def test_get_schemas_empty(self):
        mgr = CustomToolManager()
        assert mgr.get_schemas() == []


class TestLoadCustomTools:
    def test_nonexistent_file(self):
        load_custom_tools(Path("/nonexistent/config.yaml"))

    def test_empty_file(self, tmp_path):
        config_path = tmp_path / "empty.yaml"
        config_path.write_text("")
        try:
            load_custom_tools(config_path)
        except ImportError:
            pass

    def test_no_custom_tools_key(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("other_key: value\n")
        try:
            load_custom_tools(config_path)
        except ImportError:
            pass


class TestGlobalInstance:
    def test_custom_tool_manager(self):
        assert isinstance(custom_tool_manager, CustomToolManager)
