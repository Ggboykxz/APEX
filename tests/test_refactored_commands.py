"""Tests for refactored commands module."""


from apex.refactored_commands import (
    Command, CommandManager, PlanApproval,
    create_command_manager, create_plan_approval
)


class TestCommand:
    def test_init(self):
        cmd = Command("test", "Test command", "Do something {arg}")
        assert cmd.name == "test"
        assert cmd.description == "Test command"
        assert cmd.prompt == "Do something {arg}"
        assert cmd.args == []

    def test_init_with_args(self):
        cmd = Command("test", "Test", "Prompt", ["arg1", "arg2"])
        assert cmd.args == ["arg1", "arg2"]

    def test_render_no_args(self):
        cmd = Command("test", "Test", "Simple prompt")
        result = cmd.render()
        assert result == "Simple prompt"

    def test_render_with_args(self):
        cmd = Command("test", "Test", "Hello {name}!")
        result = cmd.render(name="World")
        assert result == "Hello World!"

    def test_render_multiple_args(self):
        cmd = Command("test", "Test", "{greeting} {name}!")
        result = cmd.render(greeting="Hello", name="World")
        assert result == "Hello World!"

    def test_render_missing_arg(self):
        cmd = Command("test", "Test", "Hello {name}!")
        result = cmd.render()
        assert result == "Hello {name}!"


class TestCommandManager:
    def test_init(self, tmp_path):
        def mock_exists(p):
            return False
        
        manager = CommandManager(
            str(tmp_path),
            path_exists=mock_exists
        )
        assert manager.cwd == str(tmp_path)
        assert manager.commands == {}

    def test_load_commands_from_directory(self, tmp_path):
        commands_dir = tmp_path / ".apex" / "commands"
        commands_dir.mkdir(parents=True)
        
        (commands_dir / "test_cmd.md").write_text("""## Description: Test command

## Prompt
This is a test prompt with {arg}
""")

        manager = CommandManager(str(tmp_path))
        
        assert "test_cmd" in manager.commands

    def test_get_command(self, tmp_path):
        manager = CommandManager(str(tmp_path), path_exists=lambda p: False)
        manager.add_command("test", "Test", "Prompt")
        
        cmd = manager.get("test")
        assert cmd is not None
        assert cmd.name == "test"

    def test_get_command_not_found(self, tmp_path):
        manager = CommandManager(str(tmp_path), path_exists=lambda p: False)
        
        cmd = manager.get("nonexistent")
        assert cmd is None

    def test_list_commands(self, tmp_path):
        manager = CommandManager(str(tmp_path), path_exists=lambda p: False)
        manager.add_command("cmd1", "Description 1", "Prompt 1")
        manager.add_command("cmd2", "Description 2", "Prompt 2")
        
        commands = manager.list_commands()
        
        assert len(commands) == 2
        assert commands[0]["name"] == "cmd1"

    def test_execute_command(self, tmp_path):
        manager = CommandManager(str(tmp_path), path_exists=lambda p: False)
        manager.add_command("test", "Test", "Hello {who}")
        
        result = manager.execute("test", who="World")
        
        assert result == "Hello World"

    def test_execute_not_found(self, tmp_path):
        manager = CommandManager(str(tmp_path), path_exists=lambda p: False)
        
        result = manager.execute("nonexistent")
        
        assert result is None

    def test_add_command(self, tmp_path):
        manager = CommandManager(str(tmp_path), path_exists=lambda p: False)
        manager.add_command("new", "New command", "New prompt")
        
        assert "new" in manager.commands

    def test_remove_command(self, tmp_path):
        manager = CommandManager(str(tmp_path), path_exists=lambda p: False)
        manager.add_command("test", "Test", "Prompt")
        
        result = manager.remove_command("test")
        
        assert result is True
        assert "test" not in manager.commands

    def test_remove_command_not_found(self, tmp_path):
        manager = CommandManager(str(tmp_path), path_exists=lambda p: False)
        
        result = manager.remove_command("nonexistent")
        
        assert result is False


class TestPlanApproval:
    def test_init(self):
        approval = PlanApproval()
        assert approval.get_plan() is None
        assert approval.is_awaiting_approval() is False

    def test_set_plan(self):
        approval = PlanApproval()
        approval.set_plan("Step 1: Do this")
        
        assert approval.is_awaiting_approval() is True
        assert approval.get_plan() is None

    def test_approve(self):
        approval = PlanApproval()
        approval.set_plan("Step 1: Do this")
        approval.approve()
        
        assert approval.get_plan() == "Step 1: Do this"

    def test_reject(self):
        approval = PlanApproval()
        approval.set_plan("Step 1: Do this")
        approval.reject()
        
        assert approval.get_plan() is None
        assert approval.is_awaiting_approval() is False

    def test_clear(self):
        approval = PlanApproval()
        approval.set_plan("Step 1: Do this")
        approval.approve()
        approval.clear()
        
        assert approval.get_plan() is None
        assert approval.is_awaiting_approval() is False

    def test_set_plan_after_approve(self):
        approval = PlanApproval()
        approval.set_plan("Plan A")
        approval.approve()
        
        approval.set_plan("Plan B")
        
        assert approval.get_plan() is None
        assert approval.is_awaiting_approval() is True


class TestFactoryFunctions:
    def test_create_command_manager(self, tmp_path):
        manager = create_command_manager(str(tmp_path))
        assert isinstance(manager, CommandManager)

    def test_create_plan_approval(self):
        approval = create_plan_approval()
        assert isinstance(approval, PlanApproval)