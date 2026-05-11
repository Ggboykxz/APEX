"""Tests for refactored commands module — no mocks, real filesystem."""

from apex.refactored_commands import (
    Command,
    CommandManager,
    PlanApproval,
    create_command_manager,
    create_plan_approval,
)


class TestCommand:
    def test_init_defaults(self):
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

    def test_render_with_numeric_value(self):
        cmd = Command("test", "Test", "Count: {n}")
        result = cmd.render(n=42)
        assert result == "Count: 42"


class TestCommandManager:
    def test_init_with_no_commands_dir(self, tmp_path):
        manager = CommandManager(str(tmp_path), path_exists=lambda p: False)
        assert manager.cwd == str(tmp_path)
        assert manager.commands == {}

    def test_load_commands_from_directory(self, tmp_path):
        commands_dir = tmp_path / ".apex" / "commands"
        commands_dir.mkdir(parents=True)

        (commands_dir / "test_cmd.md").write_text(
            "## Description: Test command\n\n## Prompt\nThis is a test prompt with {arg}\n"
        )

        manager = CommandManager(str(tmp_path))
        assert "test_cmd" in manager.commands
        cmd = manager.get("test_cmd")
        assert cmd.description == "Test command"
        assert "test prompt" in cmd.prompt

    def test_load_commands_from_home_dir_via_injection(self, tmp_path):
        """Test loading from a second command dir using path injection."""
        second_cmd_dir = tmp_path / "extra_commands"
        second_cmd_dir.mkdir()
        (second_cmd_dir / "extra.md").write_text(
            "## Description: Extra command\n\n## Prompt\nExtra prompt\n"
        )

        # Track which directories are checked
        checked_dirs = []

        def tracking_exists(p):
            checked_dirs.append(p)
            return p == second_cmd_dir

        def tracking_glob(p, g):
            if p == second_cmd_dir:
                return list(second_cmd_dir.glob(g))
            return []

        CommandManager(
            str(tmp_path),
            path_exists=tracking_exists,
            path_glob=tracking_glob,
        )
        # The second directory checked should be Path.home()/.apex/commands
        # but since we control path_exists, we can make it match our test dir
        # Verify that both command dirs are checked
        assert len(checked_dirs) == 2

    def test_load_command_file_no_prompt(self, tmp_path):
        commands_dir = tmp_path / ".apex" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "noprompt.md").write_text("## Description: No prompt here\n")

        manager = CommandManager(str(tmp_path))
        assert "noprompt" not in manager.commands

    def test_load_command_file_exception(self, tmp_path):
        commands_dir = tmp_path / ".apex" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "bad.md").write_text("## Description: Bad\n\n## Prompt\nPrompt\n")

        def raise_error(p):
            raise OSError("read error")

        manager = CommandManager(str(tmp_path), path_read_text=raise_error)
        assert "bad" not in manager.commands

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
        names = [c["name"] for c in commands]
        assert "cmd1" in names
        assert "cmd2" in names

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

    def test_commands_property(self, tmp_path):
        manager = CommandManager(str(tmp_path), path_exists=lambda p: False)
        manager.add_command("a", "A", "PA")
        manager.add_command("b", "B", "PB")
        assert len(manager.commands) == 2


class TestPlanApproval:
    def test_init(self):
        approval = PlanApproval()
        assert approval.get_plan() is None
        assert approval.is_awaiting_approval() is False

    def test_set_plan(self):
        approval = PlanApproval()
        approval.set_plan("Step 1: Do this")
        assert approval.is_awaiting_approval() is True
        assert approval.get_plan() is None  # not approved yet

    def test_approve(self):
        approval = PlanApproval()
        approval.set_plan("Step 1: Do this")
        approval.approve()
        assert approval.get_plan() == "Step 1: Do this"
        assert approval.is_awaiting_approval() is False

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

    def test_approve_without_plan(self):
        approval = PlanApproval()
        approval.approve()
        assert approval.get_plan() is None


class TestFactoryFunctions:
    def test_create_command_manager(self, tmp_path):
        manager = create_command_manager(str(tmp_path))
        assert isinstance(manager, CommandManager)

    def test_create_plan_approval(self):
        approval = create_plan_approval()
        assert isinstance(approval, PlanApproval)
