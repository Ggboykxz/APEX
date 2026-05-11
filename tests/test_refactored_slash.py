"""Tests for refactored slash commands module — no mocks."""

from apex.refactored_slash import Command, SlashCommandManager, create_command_manager


class TestCommand:
    def test_init(self):
        def handler(args, context):
            return "ok"

        cmd = Command(
            name="test",
            description="Test command",
            handler=handler,
            aliases=["t"],
            args=["arg1"],
            requires_argument=True,
        )
        assert cmd.name == "test"
        assert cmd.description == "Test command"
        assert cmd.handler is handler
        assert cmd.aliases == ["t"]
        assert cmd.args == ["arg1"]
        assert cmd.requires_argument is True

    def test_init_defaults(self):
        cmd = Command(name="test", description="Test", handler=lambda a, c: "ok")
        assert cmd.aliases == []
        assert cmd.args == []
        assert cmd.requires_argument is False


class TestSlashCommandManager:
    def test_init(self):
        manager = SlashCommandManager()
        assert len(manager.commands) > 0

    def test_init_with_factory(self):
        def factory(name, desc, handler, requires_arg, args=None, aliases=None):
            return Command(name, desc, handler, aliases or [], args or [], requires_arg)

        manager = SlashCommandManager(command_factory=factory)
        assert len(manager.commands) > 0

    def test_register(self):
        manager = SlashCommandManager()

        def custom_handler(args, context):
            return "custom"

        cmd = Command("custom", "Custom command", custom_handler)
        manager.register(cmd)
        assert manager.get("custom") is not None

    def test_unregister(self):
        manager = SlashCommandManager()
        result = manager.unregister("help")
        assert result is True
        assert manager.get("help") is None

    def test_unregister_unknown(self):
        manager = SlashCommandManager()
        result = manager.unregister("unknown_command_xyz")
        assert result is False

    def test_unregister_removes_aliases(self):
        manager = SlashCommandManager()

        def handler(args, context):
            return "ok"

        cmd = Command("test_cmd", "Test", handler, aliases=["tc"])
        manager.register(cmd)
        assert manager.get("tc") is not None
        manager.unregister("test_cmd")
        assert manager.get("tc") is None

    def test_register_with_aliases(self):
        manager = SlashCommandManager()

        def handler(args, context):
            return "ok"

        cmd = Command("test", "Test", handler, aliases=["t"])
        manager.register(cmd)
        assert manager.get("t") is not None
        assert manager.get("t").name == "test"

    def test_get(self):
        manager = SlashCommandManager()
        cmd = manager.get("help")
        assert cmd is not None
        assert cmd.name == "help"

    def test_get_unknown(self):
        manager = SlashCommandManager()
        cmd = manager.get("unknown_command_xyz")
        assert cmd is None

    def test_list_commands(self):
        manager = SlashCommandManager()
        commands = manager.list_commands()
        assert len(commands) > 0
        assert all("name" in c and "description" in c for c in commands)

    def test_parse_valid(self):
        manager = SlashCommandManager()
        result = manager.parse("/help")
        assert result == ("help", [])

    def test_parse_with_args(self):
        manager = SlashCommandManager()
        result = manager.parse("/agent build")
        assert result == ("agent", ["build"])

    def test_parse_multiple_args(self):
        manager = SlashCommandManager()
        result = manager.parse("/model gpt-4 turbo")
        assert result == ("model", ["gpt-4", "turbo"])

    def test_parse_no_slash(self):
        manager = SlashCommandManager()
        result = manager.parse("help")
        assert result is None

    def test_parse_empty(self):
        manager = SlashCommandManager()
        result = manager.parse("/")
        assert result is None

    def test_parse_case_insensitive(self):
        manager = SlashCommandManager()
        result = manager.parse("/HELP")
        assert result == ("help", [])

    def test_execute_valid(self):
        manager = SlashCommandManager()
        result = manager.execute("/help")
        assert "Available Commands" in result

    def test_execute_with_args(self):
        manager = SlashCommandManager()
        result = manager.execute("/agent build")
        assert "build" in result

    def test_execute_invalid_command(self):
        manager = SlashCommandManager()
        result = manager.execute("/unknown_command_xyz")
        assert "ERROR" in result

    def test_execute_requires_argument(self):
        manager = SlashCommandManager()
        result = manager.execute("/agent")
        assert "requires argument" in result

    def test_execute_no_slash(self):
        manager = SlashCommandManager()
        result = manager.execute("help")
        assert "ERROR" in result

    def test_execute_with_context(self):
        manager = SlashCommandManager()

        def custom_handler(args, context):
            return f"cwd: {context.get('cwd', 'none')}"

        cmd = Command("test", "Test", custom_handler)
        manager.register(cmd)
        result = manager.execute("/test", {"cwd": "/workspace"})
        assert "/workspace" in result

    def test_execute_handler_exception(self):
        manager = SlashCommandManager()

        def bad_handler(args, context):
            raise RuntimeError("handler error")

        cmd = Command("bad", "Bad", bad_handler)
        manager.register(cmd)
        result = manager.execute("/bad")
        assert "ERROR" in result
        assert "handler error" in result

    def test_cmd_agent_default(self):
        manager = SlashCommandManager()
        result = manager._cmd_agent([], {})
        assert "build" in result

    def test_cmd_agent_with_arg(self):
        manager = SlashCommandManager()
        result = manager._cmd_agent(["explore"], {})
        assert "explore" in result

    def test_cmd_model(self):
        manager = SlashCommandManager()
        result = manager._cmd_model(["gpt-4"], {})
        assert "gpt-4" in result

    def test_cmd_model_empty(self):
        manager = SlashCommandManager()
        result = manager._cmd_model([], {})
        assert "SWITCH MODEL" in result

    def test_cmd_cwd(self):
        manager = SlashCommandManager()
        result = manager._cmd_cwd(["/workspace"], {})
        assert "/workspace" in result

    def test_cmd_cwd_default(self):
        manager = SlashCommandManager()
        result = manager._cmd_cwd([], {})
        assert "." in result

    def test_cmd_clear(self):
        manager = SlashCommandManager()
        result = manager._cmd_clear([], {})
        assert "CLEAR" in result

    def test_cmd_save_default(self):
        manager = SlashCommandManager()
        result = manager._cmd_save([], {})
        assert "default" in result

    def test_cmd_save_with_name(self):
        manager = SlashCommandManager()
        result = manager._cmd_save(["my_session"], {})
        assert "my_session" in result

    def test_cmd_load(self):
        manager = SlashCommandManager()
        result = manager._cmd_load(["session1"], {})
        assert "session1" in result

    def test_cmd_load_no_arg(self):
        manager = SlashCommandManager()
        result = manager._cmd_load([], {})
        assert "LOAD" in result

    def test_cmd_share(self):
        manager = SlashCommandManager()
        result = manager._cmd_share([], {})
        assert "SHARE" in result

    def test_cmd_undo(self):
        manager = SlashCommandManager()
        result = manager._cmd_undo([], {})
        assert "UNDO" in result

    def test_cmd_redo(self):
        manager = SlashCommandManager()
        result = manager._cmd_redo([], {})
        assert "REDO" in result

    def test_cmd_git(self):
        manager = SlashCommandManager()
        result = manager._cmd_git([], {})
        assert "GIT" in result

    def test_cmd_map(self):
        manager = SlashCommandManager()
        result = manager._cmd_map([], {})
        assert "MAP" in result

    def test_cmd_cost(self):
        manager = SlashCommandManager()
        result = manager._cmd_cost([], {})
        assert "COST" in result

    def test_cmd_agents(self):
        manager = SlashCommandManager()
        result = manager._cmd_agents([], {})
        assert "AGENTS" in result

    def test_cmd_subagents(self):
        manager = SlashCommandManager()
        result = manager._cmd_subagents([], {})
        assert "SUBAGENTS" in result

    def test_cmd_models(self):
        manager = SlashCommandManager()
        result = manager._cmd_models([], {})
        assert "MODELS" in result

    def test_cmd_init(self):
        manager = SlashCommandManager()
        result = manager._cmd_init([], {})
        assert "INIT" in result

    def test_cmd_analyze(self):
        manager = SlashCommandManager()
        result = manager._cmd_analyze([], {})
        assert "ANALYZE" in result

    def test_cmd_approve(self):
        manager = SlashCommandManager()
        result = manager._cmd_approve([], {})
        assert "APPROVE" in result

    def test_cmd_reject_with_reason(self):
        manager = SlashCommandManager()
        result = manager._cmd_reject(["too", "expensive"], {})
        assert "too expensive" in result

    def test_cmd_reject_no_reason(self):
        manager = SlashCommandManager()
        result = manager._cmd_reject([], {})
        assert "No reason" in result

    def test_cmd_shell_default(self):
        manager = SlashCommandManager()
        result = manager._cmd_shell([], {})
        assert "bash" in result

    def test_cmd_shell_with_arg(self):
        manager = SlashCommandManager()
        result = manager._cmd_shell(["zsh"], {})
        assert "zsh" in result

    def test_cmd_commands(self):
        manager = SlashCommandManager()
        result = manager._cmd_commands([], {})
        assert "COMMANDS" in result

    def test_commands_property(self):
        manager = SlashCommandManager()
        assert isinstance(manager.commands, dict)
        assert "help" in manager.commands


class TestFactoryFunctions:
    def test_create_command_manager(self):
        manager = create_command_manager()
        assert isinstance(manager, SlashCommandManager)

    def test_create_command_manager_with_factory(self):
        def factory(name, desc, handler, requires_arg, args=None, aliases=None):
            return Command(name, desc, handler, aliases or [], args or [], requires_arg)

        manager = create_command_manager(factory)
        assert isinstance(manager, SlashCommandManager)
