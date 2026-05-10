"""Refactored slash commands module - More testable."""

from typing import Callable, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Command:
    name: str
    description: str
    handler: Callable[..., str]
    aliases: list[str] = field(default_factory=list)
    args: list[str] = field(default_factory=list)
    requires_argument: bool = False


class SlashCommandManager:
    def __init__(
        self, command_factory: Optional[Callable[[str, str, Callable, bool], Command]] = None
    ):
        self._commands: dict[str, Command] = {}
        self._aliases: dict[str, str] = {}
        self._command_factory = command_factory
        self._register_default_commands()

    def _create_command(
        self,
        name: str,
        description: str,
        handler: Callable,
        args: Optional[list[str]] = None,
        requires_argument: bool = False,
        aliases: Optional[list[str]] = None,
    ) -> Command:
        if self._command_factory:
            return self._command_factory(
                name, description, handler, requires_argument, args, aliases
            )
        return Command(
            name=name,
            description=description,
            handler=handler,
            args=args or [],
            requires_argument=requires_argument,
            aliases=aliases or [],
        )

    def _register_default_commands(self):
        self.register(
            self._create_command(
                "agent", "Switch to a different agent", self._cmd_agent, ["agent_name"], True
            )
        )
        self.register(
            self._create_command(
                "model", "Switch to a different model", self._cmd_model, ["model_name"], True
            )
        )
        self.register(
            self._create_command("cwd", "Change working directory", self._cmd_cwd, ["path"], True)
        )
        self.register(self._create_command("clear", "Clear conversation history", self._cmd_clear))
        self.register(
            self._create_command("save", "Save current session", self._cmd_save, ["name"])
        )
        self.register(
            self._create_command("load", "Load a saved session", self._cmd_load, ["name"], True)
        )
        self.register(self._create_command("share", "Share current session", self._cmd_share))
        self.register(self._create_command("undo", "Undo last change", self._cmd_undo))
        self.register(self._create_command("redo", "Redo last undone change", self._cmd_redo))
        self.register(self._create_command("git", "Show git status", self._cmd_git))
        self.register(self._create_command("map", "Show repository map", self._cmd_map))
        self.register(self._create_command("help", "Show available commands", self._cmd_help))
        self.register(self._create_command("cost", "Show token cost summary", self._cmd_cost))
        self.register(self._create_command("agents", "List all agents", self._cmd_agents))
        self.register(self._create_command("subagents", "List all subagents", self._cmd_subagents))
        self.register(self._create_command("models", "List all available models", self._cmd_models))
        self.register(self._create_command("init", "Initialize project", self._cmd_init))
        self.register(
            self._create_command("analyze", "Analyze project structure", self._cmd_analyze)
        )
        self.register(self._create_command("approve", "Approve pending plan", self._cmd_approve))
        self.register(
            self._create_command("reject", "Reject pending plan", self._cmd_reject, ["reason"])
        )
        self.register(
            self._create_command(
                "shell", "Start interactive shell", self._cmd_shell, ["shell_name"]
            )
        )
        self.register(self._create_command("commands", "List custom commands", self._cmd_commands))

    def register(self, command: Command) -> None:
        self._commands[command.name] = command
        if command.aliases:
            for alias in command.aliases:
                self._aliases[alias] = command.name

    def unregister(self, name: str) -> bool:
        if name in self._commands:
            self._commands.pop(name)
            self._aliases = {k: v for k, v in self._aliases.items() if v != name}
            return True
        return False

    def get(self, name: str) -> Optional[Command]:
        if name in self._aliases:
            name = self._aliases[name]
        return self._commands.get(name)

    def list_commands(self) -> list[dict[str, str]]:
        return [
            {"name": cmd.name, "description": cmd.description} for cmd in self._commands.values()
        ]

    def parse(self, text: str) -> Optional[tuple[str, list[str]]]:
        if not text.startswith("/"):
            return None

        parts = text[1:].split()
        if not parts:
            return None

        name = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        return (name, args)

    def execute(self, text: str, context: Optional[dict[str, Any]] = None) -> str:
        context = context or {}
        parsed = self.parse(text)
        if not parsed:
            return "ERROR: Invalid command"

        name, args = parsed
        cmd = self.get(name)
        if not cmd:
            return f"ERROR: Unknown command: {name}"

        if cmd.requires_argument and not args:
            return f"ERROR: Command {name} requires argument"

        try:
            return cmd.handler(args, context)
        except Exception as e:
            return f"ERROR: {e}"

    def _cmd_agent(self, args: list[str], context: dict) -> str:
        agent_name = args[0] if args else "build"
        return f"[SWITCH AGENT] {agent_name}"

    def _cmd_model(self, args: list[str], context: dict) -> str:
        model = args[0] if args else ""
        return f"[SWITCH MODEL] {model}"

    def _cmd_cwd(self, args: list[str], context: dict) -> str:
        path = args[0] if args else "."
        return f"[CHANGE DIR] {path}"

    def _cmd_clear(self, args: list[str], context: dict) -> str:
        return "[CLEAR] Conversation history cleared"

    def _cmd_save(self, args: list[str], context: dict) -> str:
        name = args[0] if args else "default"
        return f"[SAVE] Session saved as '{name}'"

    def _cmd_load(self, args: list[str], context: dict) -> str:
        name = args[0] if args else ""
        return f"[LOAD] Loading session '{name}'..."

    def _cmd_share(self, args: list[str], context: dict) -> str:
        return "[SHARE] Generating share link..."

    def _cmd_undo(self, args: list[str], context: dict) -> str:
        return "[UNDO] Undoing last change..."

    def _cmd_redo(self, args: list[str], context: dict) -> str:
        return "[REDO] Redoing last change..."

    def _cmd_git(self, args: list[str], context: dict) -> str:
        return "[GIT] Git status:\nbranch: main\nstatus: clean"

    def _cmd_map(self, args: list[str], context: dict) -> str:
        return "[MAP] Repository map:\nsrc/\ntests/\nconfig/"

    def _cmd_help(self, args: list[str], context: dict) -> str:
        lines = ["Available Commands:", "=" * 40]
        for cmd in sorted(self._commands.values(), key=lambda c: c.name):
            lines.append(f"  /{cmd.name} - {cmd.description}")
        return "\n".join(lines)

    def _cmd_cost(self, args: list[str], context: dict) -> str:
        return "[COST] Token usage:\nInput: 0\nOutput: 0\nTotal: $0.00"

    def _cmd_agents(self, args: list[str], context: dict) -> str:
        return "[AGENTS] Primary: build, plan\nSubagents: explore, general"

    def _cmd_subagents(self, args: list[str], context: dict) -> str:
        return "[SUBAGENTS] explore (read-only), general (full access)"

    def _cmd_models(self, args: list[str], context: dict) -> str:
        return "[MODELS] Run /model <name> to switch"

    def _cmd_init(self, args: list[str], context: dict) -> str:
        return "[INIT] Initializing project..."

    def _cmd_analyze(self, args: list[str], context: dict) -> str:
        return "[ANALYZE] Analyzing project..."

    def _cmd_approve(self, args: list[str], context: dict) -> str:
        return "[APPROVE] Plan approved"

    def _cmd_reject(self, args: list[str], context: dict) -> str:
        reason = " ".join(args) if args else "No reason"
        return f"[REJECT] Plan rejected: {reason}"

    def _cmd_shell(self, args: list[str], context: dict) -> str:
        shell = args[0] if args else "bash"
        return f"[SHELL] Starting {shell}..."

    def _cmd_commands(self, args: list[str], context: dict) -> str:
        return "[COMMANDS] Custom commands:\nNone defined"

    @property
    def commands(self) -> dict[str, Command]:
        return self._commands


def create_command_manager(command_factory: Optional[Callable] = None) -> SlashCommandManager:
    return SlashCommandManager(command_factory)
