"""Tests for apex/commands.py — Command, CommandManager, create_command_manager."""

import pytest
import os

from apex.commands import Command, CommandManager, create_command_manager


class TestCommand:
    def test_creation(self):
        cmd = Command(name="test", description="Test command", content="Hello {name}")
        assert cmd.name == "test"
        assert cmd.description == "Test command"
        assert cmd.content == "Hello {name}"
        assert cmd.category == "general"
        assert cmd.short_help == ""

    def test_trigger_property(self):
        cmd = Command(name="test", description="", content="", category="project")
        assert cmd.trigger == "project:test"

    def test_trigger_default_category(self):
        cmd = Command(name="hello", description="", content="")
        assert cmd.trigger == "general:hello"

    def test_with_all_fields(self):
        cmd = Command(
            name="test", description="desc", content="content", category="user", short_help="help"
        )
        assert cmd.category == "user"
        assert cmd.short_help == "help"


class TestCommandManager:
    @pytest.fixture
    def manager(self, tmp_path):
        return CommandManager(cwd=tmp_path)

    def test_init(self, manager):
        assert isinstance(manager._commands, dict)
        assert isinstance(manager._handlers, dict)

    def test_register_command(self, manager):
        manager.register_command("test", lambda ctx: "result", category="user", description="Test")
        assert "user:test" in manager._commands
        assert "user:test" in manager._handlers

    def test_get_command(self, manager):
        manager.register_command("test", lambda ctx: "ok", description="Test")
        cmd = manager.get_command("user:test")
        assert cmd is not None
        assert cmd.name == "test"

    def test_get_command_nonexistent(self, manager):
        assert manager.get_command("nonexistent:cmd") is None

    def test_execute_handler(self, manager):
        manager.register_command(
            "test", lambda ctx: f"hello {ctx.get('name', '')}", description="Test"
        )
        result = manager.execute("user:test", {"name": "world"})
        assert result == "hello world"

    def test_execute_template(self, manager):
        manager._commands["user:tmpl"] = Command(
            name="tmpl", description="", content="Hello {name}", category="user"
        )
        result = manager.execute("user:tmpl", {"name": "World"})
        assert result == "Hello World"

    def test_execute_nonexistent(self, manager):
        result = manager.execute("nonexistent:cmd", {})
        assert result is None

    def test_expand_template_env_vars(self, manager):
        os.environ["TEST_APEX_CMD_VAR"] = "env_value"
        manager._commands["user:envtest"] = Command(
            name="envtest", description="", content="Value: ${TEST_APEX_CMD_VAR}", category="user"
        )
        result = manager.execute("user:envtest", {})
        assert "env_value" in result
        del os.environ["TEST_APEX_CMD_VAR"]

    def test_list_commands(self, manager):
        manager.register_command("cmd1", lambda ctx: "1", description="First")
        manager.register_command("cmd2", lambda ctx: "2", description="Second")
        commands = manager.list_commands()
        assert len(commands) >= 2

    def test_list_commands_by_category(self, manager):
        manager.register_command("cmd1", lambda ctx: "1", category="user", description="U1")
        manager.register_command("cmd2", lambda ctx: "2", category="project", description="P1")
        user_cmds = manager.list_commands(category="user")
        assert all(c.category == "user" for c in user_cmds)

    def test_search_commands(self, manager):
        manager.register_command("deploy", lambda ctx: "ok", description="Deploy the app")
        manager.register_command("test_cmd", lambda ctx: "ok", description="Run tests")
        results = manager.search("deploy")
        assert len(results) >= 1
        assert results[0].name == "deploy"

    def test_search_by_description(self, manager):
        manager.register_command("cmd1", lambda ctx: "ok", description="Run deployment pipeline")
        results = manager.search("deployment")
        assert len(results) >= 1

    def test_search_no_results(self, manager):
        results = manager.search("zzzz_nonexistent_command")
        assert len(results) == 0

    def test_parse_command(self, manager):
        result = manager._parse_command("# My Command\n\nDescription here", "my_cmd", "user")
        assert result is not None
        assert result.name == "my_cmd"
        assert result.description == "Description here"

    def test_parse_command_empty(self, manager):
        result = manager._parse_command("", "empty", "user")
        # Empty string split produces [''], which is truthy
        assert result is None or result.name == "empty"

    def test_parse_command_single_line(self, manager):
        result = manager._parse_command("# Just a title", "single", "user")
        assert result is not None
        assert result.name == "single"

    def test_load_user_commands_nonexistent(self, tmp_path):
        mgr = CommandManager(cwd=tmp_path)
        mgr._load_user_commands()

    def test_load_project_commands_from_dir(self, tmp_path):
        cmd_dir = tmp_path / ".apex" / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "hello.md").write_text("# Hello\n\nSays hello\n\nHello {name}!")
        mgr = CommandManager(cwd=tmp_path)
        cmd = mgr.get_command("project:hello")
        assert cmd is not None
        assert cmd.name == "hello"

    def test_create_command_file(self, manager, tmp_path):
        manager.create_command("newcmd", "Content here", category="project", description="New cmd")
        cmd = manager.get_command("project:newcmd")
        assert cmd is not None

    def test_project_commands_dir_is_path(self):
        assert isinstance(CommandManager.PROJECT_COMMANDS_DIR, type(Path(".")))

    def test_load_user_commands_from_existing_dir(self, manager):
        """Hit line 42 — load from existing USER_COMMANDS_DIR."""
        manager.USER_COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
        cmd_file = manager.USER_COMMANDS_DIR / "user_cmd.md"
        cmd_file.write_text("# User Cmd\n\nA user command\n\ncontent here")
        # Re-initialize from new manager to trigger load
        manager._load_user_commands()
        cmd = manager.get_command("user:user_cmd")
        assert cmd is not None

    def test_load_from_dir_invalid_md(self, manager):
        """Hit lines 58-59 — catch exception during md file parsing."""
        cmd_dir = Path(manager.USER_COMMANDS_DIR) / ".." / "bad_commands"
        cmd_dir = cmd_dir.resolve()
        cmd_dir.mkdir(parents=True, exist_ok=True)
        bad_file = cmd_dir / "bad.md"
        bad_file.write_bytes(b"\xff\xfe\x00\x01")  # invalid UTF-8
        manager._load_from_dir(cmd_dir, "user")

    def test_parse_command_empty_content(self, manager):
        """_parse_command always returns a Command (empty lines not possible)."""
        result = manager._parse_command("", "empty", "user")
        assert result is not None

    def test_create_command_user_category(self, manager):
        """Hit line 136 — user category branch in create_command."""
        # Ensure USER_COMMANDS_DIR is valid
        manager.USER_COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
        manager.create_command("usr_cmd", "content", category="user", description="desc")
        cmd = manager.get_command("user:usr_cmd")
        assert cmd is not None


class TestCreateCommandManager:
    def test_returns_instance(self, tmp_path):
        mgr = create_command_manager(cwd=tmp_path)
        assert isinstance(mgr, CommandManager)

    def test_default_cwd(self):
        mgr = create_command_manager()
        assert isinstance(mgr, CommandManager)


from pathlib import Path
