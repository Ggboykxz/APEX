"""Tests for apex/slash.py — SlashCommandManager, Command, get_slash_command_manager."""

import pytest
from apex.slash import Command, SlashCommandManager, get_slash_command_manager


class TestCommand:
    def test_creation(self):
        cmd = Command(name="test", description="Test", handler=lambda args, ctx: "ok")
        assert cmd.name == "test"
        assert cmd.description == "Test"
        assert cmd.aliases is None
        assert cmd.args is None
        assert cmd.requires_argument is False

    def test_with_all_fields(self):
        cmd = Command(
            name="test",
            description="Test",
            handler=lambda args, ctx: "ok",
            aliases=["t"],
            args=["arg1"],
            requires_argument=True,
        )
        assert cmd.aliases == ["t"]
        assert cmd.args == ["arg1"]
        assert cmd.requires_argument is True


class TestSlashCommandManager:
    @pytest.fixture
    def manager(self):
        return SlashCommandManager()

    def test_init(self, manager):
        assert len(manager._commands) > 0
        assert "help" in manager._commands
        assert "clear" in manager._commands
        assert "model" in manager._commands

    def test_default_commands_registered(self, manager):
        expected = [
            "agent",
            "model",
            "cwd",
            "clear",
            "save",
            "load",
            "share",
            "undo",
            "redo",
            "git",
            "map",
            "help",
            "cost",
            "agents",
            "subagents",
            "models",
            "init",
            "analyze",
            "approve",
            "reject",
            "shell",
            "commands",
        ]
        for name in expected:
            assert name in manager._commands, f"Command '{name}' not registered"

    def test_register(self, manager):
        cmd = Command(name="custom", description="Custom", handler=lambda args, ctx: "custom")
        manager.register(cmd)
        assert "custom" in manager._commands

    def test_register_with_aliases(self, manager):
        cmd = Command(
            name="custom", description="Custom", handler=lambda args, ctx: "custom", aliases=["c"]
        )
        manager.register(cmd)
        assert "c" in manager._aliases
        assert manager._aliases["c"] == "custom"

    def test_get(self, manager):
        cmd = manager.get("help")
        assert cmd is not None
        assert cmd.name == "help"

    def test_get_nonexistent(self, manager):
        assert manager.get("nonexistent") is None

    def test_get_via_alias(self, manager):
        # Register a command with alias
        cmd = Command(
            name="mycmd", description="My Cmd", handler=lambda args, ctx: "ok", aliases=["mc"]
        )
        manager.register(cmd)
        assert manager.get("mc") is cmd

    def test_list_commands(self, manager):
        commands = manager.list_commands()
        assert len(commands) > 0
        assert all("name" in c and "description" in c for c in commands)

    def test_parse_slash_command(self, manager):
        result = manager.parse("/help")
        assert result is not None
        assert result[0] == "help"
        assert result[1] == []

    def test_parse_with_args(self, manager):
        result = manager.parse("/model gpt-4o")
        assert result is not None
        assert result[0] == "model"
        assert result[1] == ["gpt-4o"]

    def test_parse_no_slash(self, manager):
        assert manager.parse("help") is None

    def test_parse_slash_only(self, manager):
        assert manager.parse("/") is None

    def test_parse_multiple_args(self, manager):
        result = manager.parse("/cwd /tmp/test")
        assert result is not None
        assert result[0] == "cwd"
        assert result[1] == ["/tmp/test"]

    def test_execute_help(self, manager):
        result = manager.execute("/help")
        assert "Available Commands" in result

    def test_execute_clear(self, manager):
        result = manager.execute("/clear")
        assert "CLEAR" in result

    def test_execute_agent(self, manager):
        result = manager.execute("/agent coder")
        assert "coder" in result

    def test_execute_model(self, manager):
        result = manager.execute("/model gpt-4o")
        assert "gpt-4o" in result

    def test_execute_cwd(self, manager):
        result = manager.execute("/cwd /tmp")
        assert "/tmp" in result

    def test_execute_save(self, manager):
        result = manager.execute("/save my_session")
        assert "my_session" in result

    def test_execute_load(self, manager):
        result = manager.execute("/load my_session")
        assert "my_session" in result

    def test_execute_share(self, manager):
        result = manager.execute("/share")
        assert "SHARE" in result

    def test_execute_undo(self, manager):
        result = manager.execute("/undo")
        assert "UNDO" in result

    def test_execute_redo(self, manager):
        result = manager.execute("/redo")
        assert "REDO" in result

    def test_execute_git(self, manager):
        result = manager.execute("/git")
        assert "GIT" in result

    def test_execute_map(self, manager):
        result = manager.execute("/map")
        assert "MAP" in result

    def test_execute_cost(self, manager):
        result = manager.execute("/cost")
        assert "COST" in result

    def test_execute_agents(self, manager):
        result = manager.execute("/agents")
        assert "AGENTS" in result

    def test_execute_subagents(self, manager):
        result = manager.execute("/subagents")
        assert "SUBAGENTS" in result

    def test_execute_models(self, manager):
        result = manager.execute("/models")
        assert "MODELS" in result

    def test_execute_init(self, manager):
        result = manager.execute("/init")
        assert "INIT" in result

    def test_execute_analyze(self, manager):
        result = manager.execute("/analyze")
        assert "ANALYZE" in result

    def test_execute_approve(self, manager):
        result = manager.execute("/approve")
        assert "APPROVE" in result

    def test_execute_reject(self, manager):
        result = manager.execute("/reject bad idea")
        assert "REJECT" in result
        assert "bad idea" in result

    def test_execute_reject_no_reason(self, manager):
        result = manager.execute("/reject")
        assert "No reason" in result

    def test_execute_shell(self, manager):
        result = manager.execute("/shell bash")
        assert "bash" in result

    def test_execute_shell_default(self, manager):
        result = manager.execute("/shell")
        assert "bash" in result

    def test_execute_commands(self, manager):
        result = manager.execute("/commands")
        assert "COMMANDS" in result

    def test_execute_unknown(self, manager):
        result = manager.execute("/unknown")
        assert "Unknown command" in result

    def test_execute_invalid_command(self, manager):
        result = manager.execute("not a command")
        assert "Invalid command" in result

    def test_execute_requires_argument(self, manager):
        # "agent" requires argument
        result = manager.execute("/agent")
        assert "ERROR" in result

    def test_execute_with_context(self, manager):
        result = manager.execute("/help", context={"key": "value"})
        assert "Available Commands" in result

    def test_cmd_model_default(self, manager):
        result = manager._cmd_model([], {})
        assert "[SWITCH MODEL]" in result

    def test_cmd_cwd_default(self, manager):
        result = manager._cmd_cwd([], {})
        assert "[CHANGE DIR]" in result

    def test_cmd_save_default(self, manager):
        result = manager._cmd_save([], {})
        assert "default" in result

    def test_cmd_load_default(self, manager):
        result = manager._cmd_load([], {})
        assert "[LOAD]" in result

    def test_cmd_reject_with_args(self, manager):
        result = manager._cmd_reject(["bad", "idea"], {})
        assert "bad idea" in result


class TestSlashExecuteException:
    """Hit lines 179-180 — exception in execute handler."""

    @pytest.fixture
    def manager(self):
        return SlashCommandManager()

    def test_execute_handler_raises(self, manager):
        """Register a handler that raises and verify error is caught."""
        def crash_handler(args, ctx):
            raise ValueError("boom")
        cmd = Command(name="crash", description="crashes", handler=crash_handler)
        manager.register(cmd)
        result = manager.execute("/crash")
        assert "ERROR" in result




class TestGetSlashCommandManager:
    def test_returns_instance(self):
        mgr = get_slash_command_manager()
        assert isinstance(mgr, SlashCommandManager)

    def test_singleton(self):
        import apex.slash as slash_mod

        slash_mod._command_manager = None
        mgr1 = get_slash_command_manager()
        mgr2 = get_slash_command_manager()
        assert mgr1 is mgr2
