"""Tests for skills_system module."""

import pytest
import tempfile
from pathlib import Path
from apex.skills_system import Skill, SkillsManager, CustomCommand, CommandRegistry


class TestSkill:
    """Test Skill dataclass."""

    def test_init(self):
        """Test skill initialization."""
        skill = Skill(
            name="test_skill",
            description="Test description",
            instructions="Test instructions",
            triggers=["test", "run"],
            parameters={"key": "value"},
            examples=["example1"],
        )
        assert skill.name == "test_skill"
        assert skill.description == "Test description"
        assert skill.triggers == ["test", "run"]
        assert skill.parameters == {"key": "value"}


class TestSkillsManager:
    """Test SkillsManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temp directory for skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create SkillsManager with temp dir."""
        return SkillsManager(skills_dir=temp_dir)

    def test_init(self, manager):
        """Test manager initialization."""
        assert len(manager._skills) > 0

    def test_builtin_skills(self, manager):
        """Test builtin skills are loaded."""
        assert "refactor" in manager._skills
        assert "debug" in manager._skills
        assert "test" in manager._skills
        assert "review" in manager._skills
        assert "explain" in manager._skills

    def test_get_skill(self, manager):
        """Test get_skill method."""
        skill = manager.get_skill("refactor")
        assert skill is not None
        assert skill.name == "refactor"

    def test_get_skill_nonexistent(self, manager):
        """Test get_skill with non-existent skill."""
        skill = manager.get_skill("nonexistent")
        assert skill is None

    def test_find_skill_by_trigger(self, manager):
        """Test find_skill by trigger."""
        skill = manager.find_skill("refactor this code")
        assert skill is not None
        assert skill.name == "refactor"

    def test_find_skill_by_name(self, manager):
        """Test find_skill by name."""
        skill = manager.find_skill("debug this")
        assert skill is not None
        assert skill.name == "debug"

    def test_find_skill_not_found(self, manager):
        """Test find_skill when not found."""
        skill = manager.find_skill("random text")
        assert skill is None

    def test_list_skills(self, manager):
        """Test list_skills method."""
        skills = manager.list_skills()
        assert len(skills) > 0
        assert all("name" in s for s in skills)
        assert all("description" in s for s in skills)

    def test_create_skill_file(self, manager, temp_dir):
        """Test create_skill_file method."""
        skill = Skill(
            name="custom_skill", description="Custom skill", instructions="Custom instructions"
        )
        filepath = manager.create_skill_file(skill)
        assert filepath.exists()
        assert filepath.name == "custom_skill.md"

        skill_loaded = manager.get_skill("custom_skill")
        assert skill_loaded is not None
        assert skill_loaded.name == "custom_skill"

    def test_delete_skill_custom(self, manager):
        """Test delete_skill for custom skill."""
        skill = Skill(name="delete_test", description="Test", instructions="Test")
        manager.create_skill_file(skill)
        assert manager.get_skill("delete_test") is not None

        result = manager.delete_skill("delete_test")
        assert result is True
        assert manager.get_skill("delete_test") is None

    def test_delete_skill_builtin(self, manager):
        """Test delete_skill for builtin skill."""
        result = manager.delete_skill("refactor")
        assert result is True
        assert manager.get_skill("refactor") is None


class TestCustomCommand:
    """Test CustomCommand class."""

    def test_init(self):
        """Test command initialization."""

        def handler(args):
            return "result"

        cmd = CustomCommand(
            name="test_cmd", handler=handler, description="Test command", aliases=["tc", "t"]
        )
        assert cmd.name == "test_cmd"
        assert cmd.handler is handler
        assert cmd.aliases == ["tc", "t"]

    def test_handler_execution(self):
        """Test handler execution."""

        def handler(args):
            return f"handled: {args}"

        cmd = CustomCommand(name="test", handler=handler)
        result = cmd.handler(["arg1", "arg2"])
        assert result == "handled: ['arg1', 'arg2']"


class TestCommandRegistry:
    """Test CommandRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create CommandRegistry."""
        return CommandRegistry()

    def test_init(self, registry):
        """Test registry initialization."""
        assert isinstance(registry._commands, dict)

    def test_register(self, registry):
        """Test register command."""

        def handler(args):
            return "done"

        cmd = CustomCommand(name="test", handler=handler, description="Test")
        registry.register(cmd)
        assert "test" in registry._commands

    def test_register_alias(self, registry):
        """Test register with aliases."""

        def handler(args):
            return "done"

        cmd = CustomCommand(name="test", handler=handler, aliases=["t"])
        registry.register(cmd)
        assert "test" in registry._commands
        assert "t" in registry._commands

    def test_get(self, registry):
        """Test get command."""

        def handler(args):
            return "done"

        cmd = CustomCommand(name="test", handler=handler)
        registry.register(cmd)

        retrieved = registry.get("test")
        assert retrieved is cmd

    def test_get_not_found(self, registry):
        """Test get with non-existent command."""
        result = registry.get("nonexistent")
        assert result is None

    def test_execute(self, registry):
        """Test execute command."""

        def handler(args):
            return f"args: {args}"

        cmd = CustomCommand(name="test", handler=handler)
        registry.register(cmd)

        result = registry.execute("test", ["arg1"])
        assert result == "args: ['arg1']"

    def test_execute_not_found(self, registry):
        """Test execute non-existent command."""
        result = registry.execute("nonexistent", [])
        assert "Unknown command" in result

    def test_execute_error(self, registry):
        """Test execute with error."""

        def handler(args):
            raise ValueError("test error")

        cmd = CustomCommand(name="test", handler=handler)
        registry.register(cmd)

        result = registry.execute("test", [])
        assert "Error" in result

    def test_list_commands(self, registry):
        """Test list_commands method."""

        def handler(args):
            return "done"

        cmd = CustomCommand(name="test", handler=handler, description="Test cmd")
        registry.register(cmd)

        commands = registry.list_commands()
        assert len(commands) > 0
        assert commands[0]["name"] == "test"
