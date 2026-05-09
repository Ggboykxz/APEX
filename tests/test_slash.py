"""Tests for slash module."""

import pytest
from apex.slash import Command, SlashCommandManager


class TestCommand:
    """Test Command dataclass."""

    def test_command_init(self):
        """Test Command initialization."""
        def handler():
            return "test"
        
        cmd = Command(
            name="test",
            description="Test command",
            handler=handler,
            aliases=["t", "testing"],
            args=["arg1", "arg2"],
            requires_argument=True
        )
        
        assert cmd.name == "test"
        assert cmd.description == "Test command"
        assert cmd.handler is handler
        assert cmd.aliases == ["t", "testing"]
        assert cmd.args == ["arg1", "arg2"]
        assert cmd.requires_argument is True

    def test_command_defaults(self):
        """Test Command default values."""
        def handler():
            return "test"
        
        cmd = Command(
            name="test",
            description="Test command",
            handler=handler
        )
        
        assert cmd.aliases is None
        assert cmd.args is None
        assert cmd.requires_argument is False


class TestSlashCommandManager:
    """Test SlashCommandManager class."""

    @pytest.fixture
    def manager(self):
        """Create manager instance."""
        return SlashCommandManager()

    def test_init(self):
        """Test initialization."""
        manager = SlashCommandManager()
        assert len(manager._commands) > 0

    def test_register(self, manager):
        """Test register method."""
        def custom_handler(args, context):
            return "result"
        
        cmd = Command(
            name="custom",
            description="Custom command",
            handler=custom_handler,
            requires_argument=False
        )
        
        manager.register(cmd)
        assert "custom" in manager._commands

    def test_get(self, manager):
        """Test get method."""
        cmd = manager.get("agent")
        assert cmd is not None
        assert cmd.name == "agent"

    def test_get_alias(self, manager):
        """Test get with alias."""
        cmd = manager.get("clear")
        assert cmd is not None

    def test_get_not_found(self, manager):
        """Test get not found."""
        cmd = manager.get("nonexistent")
        assert cmd is None

    def test_list_commands(self, manager):
        """Test list_commands method."""
        commands = manager.list_commands()
        assert isinstance(commands, list)
        assert len(commands) > 0

    def test_parse(self, manager):
        """Test parse method."""
        result = manager.parse("/agent build")
        assert result is not None
        assert result[0] == "agent"
        assert result[1] == ["build"]

    def test_parse_no_slash(self, manager):
        """Test parse without slash."""
        result = manager.parse("agent build")
        assert result is None

    def test_parse_empty(self, manager):
        """Test parse empty."""
        result = manager.parse("/")
        assert result is None

    def test_execute(self, manager):
        """Test execute method."""
        result = manager.execute("/clear")
        assert isinstance(result, str)

    def test_execute_with_args(self, manager):
        """Test execute with arguments."""
        result = manager.execute("/model gpt-4o")
        assert isinstance(result, str)

    def test_execute_unknown(self, manager):
        """Test execute unknown command."""
        result = manager.execute("/unknown_command")
        assert "ERROR" in result

    def test_execute_requires_arg(self, manager):
        """Test execute command that requires argument."""
        result = manager.execute("/model")
        assert "ERROR" in result