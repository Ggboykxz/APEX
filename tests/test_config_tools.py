"""Tests for apex/config_tools.py — 100 % line coverage."""

from pathlib import Path
from unittest.mock import patch

import pytest

from apex.config_tools import (
    ALLOWED_COMMANDS,
    CustomTool,
    CustomToolManager,
    custom_tool_manager,
    load_custom_tools,
)


@pytest.fixture(autouse=True)
def reset_global_manager():
    custom_tool_manager._tools.clear()
    yield


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
        assert "sudo" not in ALLOWED_COMMANDS


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

    def test_register_and_get(self):
        mgr = CustomToolManager()
        mgr.register("test", "Test tool", {"type": "object"}, lambda args: "result")
        tool = mgr.get("test")
        assert tool is not None
        assert tool.name == "test"
        assert tool.description == "Test tool"
        assert tool.parameters == {"type": "object"}

    def test_get_nonexistent(self):
        mgr = CustomToolManager()
        assert mgr.get("nonexistent") is None

    def test_list_tools(self):
        mgr = CustomToolManager()
        mgr.register("t1", "Tool 1", {}, lambda a: "1")
        mgr.register("t2", "Tool 2", {}, lambda a: "2")
        tools = mgr.list_tools()
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert names == {"t1", "t2"}

    def test_list_tools_structure(self):
        mgr = CustomToolManager()
        mgr.register("t", "desc", {"type": "object"}, lambda a: "")
        tools = mgr.list_tools()
        assert len(tools) == 1
        assert tools[0] == {
            "name": "t",
            "description": "desc",
            "parameters": {"type": "object"},
        }

    def test_execute(self):
        mgr = CustomToolManager()
        mgr.register("test", "desc", {}, lambda args: f"got {args.get('x', '')}")
        result = mgr.execute("test", {"x": "hello"})
        assert result == "got hello"

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
        s = schemas[0]
        assert s["type"] == "function"
        assert s["function"]["name"] == "custom_test"
        assert s["function"]["description"] == "desc"
        assert s["function"]["parameters"] == {"type": "object"}

    def test_get_schemas_empty(self):
        mgr = CustomToolManager()
        assert mgr.get_schemas() == []

    def test_get_schemas_multiple(self):
        mgr = CustomToolManager()
        mgr.register("a", "Alpha", {"a": 1}, lambda a: "")
        mgr.register("b", "Beta", {"b": 2}, lambda a: "")
        schemas = mgr.get_schemas()
        assert len(schemas) == 2
        names = {s["function"]["name"] for s in schemas}
        assert names == {"custom_a", "custom_b"}


class TestLoadCustomTools:
    def test_nonexistent_file(self):
        load_custom_tools(Path("/nonexistent/config.yaml"))
        assert custom_tool_manager.list_tools() == []

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.yaml"
        p.write_text("")
        load_custom_tools(p)
        assert custom_tool_manager.list_tools() == []

    def test_no_custom_tools_key(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("other_key: value\n")
        load_custom_tools(p)
        assert custom_tool_manager.list_tools() == []

    def test_empty_config_object(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("~")
        load_custom_tools(p)
        assert custom_tool_manager.list_tools() == []

    def test_disabled_tool(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  off:\n    enabled: false\n    command: echo hi\n")
        load_custom_tools(p)
        assert custom_tool_manager.get("off") is None
        assert custom_tool_manager.list_tools() == []

    def test_blocked_command_logs_warning(self, tmp_path, caplog):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  bad:\n    command: sudo rm -rf /\n")
        load_custom_tools(p)
        assert custom_tool_manager.get("bad") is None
        assert any("sudo" in msg and "not in allowlist" in msg for msg in caplog.messages)

    def test_default_description(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  nodesc:\n    command: echo hi\n")
        load_custom_tools(p)
        tool = custom_tool_manager.get("nodesc")
        assert tool is not None
        assert tool.description == "Custom tool"

    def test_explicit_description(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  withdesc:\n    description: My Tool\n    command: echo hi\n")
        load_custom_tools(p)
        tool = custom_tool_manager.get("withdesc")
        assert tool is not None
        assert tool.description == "My Tool"

    def test_default_parameters(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  simple:\n    command: echo hi\n")
        load_custom_tools(p)
        tool = custom_tool_manager.get("simple")
        assert tool is not None
        assert tool.parameters == {"type": "object", "properties": {}}

    def test_explicit_parameters(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text(
            "custom_tools:\n  explicit:\n    command: echo hi\n"
            "    parameters:\n      type: object\n      properties:\n"
            "        name:\n          type: string\n"
        )
        load_custom_tools(p)
        tool = custom_tool_manager.get("explicit")
        assert tool is not None
        assert tool.parameters == {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }

    def test_custom_cwd(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "marker.txt").write_text("present")
        p = tmp_path / "config.yaml"
        p.write_text(
            "custom_tools:\n  lstool:\n    command: ls\n    cwd: "
            + str(subdir).replace("\\", "/")
            + "\n"
        )
        load_custom_tools(p)
        result = custom_tool_manager.execute("lstool", {})
        assert "marker.txt" in result

    def test_default_cwd_is_dot(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  pwdtool:\n    command: pwd\n")
        load_custom_tools(p)
        result = custom_tool_manager.execute("pwdtool", {})
        assert result.strip()

    def test_successful_execution(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text(
            "custom_tools:\n  greeter:\n"
            "    description: Say hello\n"
            "    command: echo Hello {name}\n"
        )
        load_custom_tools(p)
        tool = custom_tool_manager.get("greeter")
        assert tool is not None
        result = custom_tool_manager.execute("greeter", {"name": "World"})
        assert "Hello World" in result

    def test_stderr_output(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text(
            "custom_tools:\n  errwriter:\n"
            "    command: python3 -c \"import sys; sys.stderr.write('stderr msg')\"\n"
        )
        load_custom_tools(p)
        result = custom_tool_manager.execute("errwriter", {})
        assert "stderr msg" in result

    def test_no_output(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text('custom_tools:\n  silent:\n    command: python3 -c "import sys"\n')
        load_custom_tools(p)
        result = custom_tool_manager.execute("silent", {})
        assert result == "[no output]"

    def test_handler_format_key_error(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  missing_key:\n    command: echo {nonexistent}\n")
        load_custom_tools(p)
        result = custom_tool_manager.execute("missing_key", {})
        assert "ERROR" in result

    def test_dollar_paren_pattern_blocked(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  t:\n    command: echo {x}\n")
        load_custom_tools(p)
        result = custom_tool_manager.execute("t", {"x": "$(whoami)"})
        assert "Dangerous pattern" in result

    def test_backtick_pattern_blocked(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  t:\n    command: echo {x}\n")
        load_custom_tools(p)
        result = custom_tool_manager.execute("t", {"x": "`whoami`"})
        assert "Dangerous pattern" in result

    def test_rm_rf_pattern_blocked(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  t:\n    command: echo {x}\n")
        load_custom_tools(p)
        result = custom_tool_manager.execute("t", {"x": "rm -rf /"})
        assert "Dangerous pattern" in result

    def test_chmod_777_pattern_blocked(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  t:\n    command: echo {x}\n")
        load_custom_tools(p)
        result = custom_tool_manager.execute("t", {"x": "chmod 777 file"})
        assert "Dangerous pattern" in result

    def test_handler_rejects_disallowed_command_after_format(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  runner:\n    command: echo {cmd}\n")
        load_custom_tools(p)
        without_echo = ALLOWED_COMMANDS - {"echo"}
        with patch("apex.config_tools.ALLOWED_COMMANDS", without_echo):
            result = custom_tool_manager.execute("runner", {"cmd": "test"})
            assert "not allowed" in result

    def test_yaml_import_error(self, tmp_path, caplog):
        p = tmp_path / "config.yaml"
        p.write_text("custom_tools:\n  test:\n    command: echo hi\n")
        import builtins

        original = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError(f"No module named '{name}'", name=name)
            return original(name, *args, **kwargs)

        builtins.__import__ = mock_import
        try:
            load_custom_tools(p)
        finally:
            builtins.__import__ = original
        assert any("Failed to load custom tools" in msg for msg in caplog.messages)

    def test_yaml_parse_error(self, tmp_path, caplog):
        p = tmp_path / "bad.yaml"
        p.write_text("custom_tools:\n  broken: [unclosed\n")
        load_custom_tools(p)
        assert any("Failed to load custom tools" in msg for msg in caplog.messages)

    def test_schema_generation_after_load(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text(
            "custom_tools:\n  fmt:\n"
            "    description: Formatter\n"
            "    command: ruff check {path}\n"
            "    parameters:\n      type: object\n"
            "      properties:\n"
            "        path:\n          type: string\n"
        )
        load_custom_tools(p)
        schemas = custom_tool_manager.get_schemas()
        matching = [s for s in schemas if s["function"]["name"] == "custom_fmt"]
        assert len(matching) == 1
        fn = matching[0]["function"]
        assert fn["description"] == "Formatter"
        assert fn["parameters"]["properties"]["path"]["type"] == "string"

    def test_multiple_tools_loaded(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text(
            "custom_tools:\n  tool_a:\n    command: echo A\n  tool_b:\n    command: echo B\n"
        )
        load_custom_tools(p)
        assert custom_tool_manager.get("tool_a") is not None
        assert custom_tool_manager.get("tool_b") is not None
        assert len(custom_tool_manager.list_tools()) == 2


class TestGlobalInstance:
    def test_is_custom_tool_manager(self):
        assert isinstance(custom_tool_manager, CustomToolManager)

    def test_starts_empty(self):
        assert custom_tool_manager.list_tools() == []
