"""Slash commands for APEX - OpenCode-style command system."""

from typing import Callable, Any
from dataclasses import dataclass


@dataclass
class Command:
    name: str
    description: str
    handler: Callable[..., str]
    aliases: list[str] = None
    args: list[str] = None
    requires_argument: bool = False


class SlashCommandManager:
    def __init__(self):
        self._commands: dict[str, Command] = {}
        self._aliases: dict[str, str] = {}
        self._register_default_commands()

    def _register_default_commands(self):
        self.register(Command(
            name="agent",
            description="Switch to a different agent",
            handler=self._cmd_agent,
            args=["agent_name"],
            requires_argument=True
        ))
        self.register(Command(
            name="model",
            description="Switch to a different model",
            handler=self._cmd_model,
            args=["model_name"],
            requires_argument=True
        ))
        self.register(Command(
            name="cwd",
            description="Change working directory",
            handler=self._cmd_cwd,
            args=["path"],
            requires_argument=True
        ))
        self.register(Command(
            name="clear",
            description="Clear conversation history",
            handler=self._cmd_clear
        ))
        self.register(Command(
            name="save",
            description="Save current session",
            handler=self._cmd_save,
            args=["name"]
        ))
        self.register(Command(
            name="load",
            description="Load a saved session",
            handler=self._cmd_load,
            args=["name"],
            requires_argument=True
        ))
        self.register(Command(
            name="share",
            description="Share current session",
            handler=self._cmd_share
        ))
        self.register(Command(
            name="undo",
            description="Undo last change",
            handler=self._cmd_undo
        ))
        self.register(Command(
            name="redo",
            description="Redo last undone change",
            handler=self._cmd_redo
        ))
        self.register(Command(
            name="git",
            description="Show git status",
            handler=self._cmd_git
        ))
        self.register(Command(
            name="map",
            description="Show repository map",
            handler=self._cmd_map
        ))
        self.register(Command(
            name="help",
            description="Show available commands",
            handler=self._cmd_help
        ))
        self.register(Command(
            name="cost",
            description="Show token cost summary",
            handler=self._cmd_cost
        ))
        self.register(Command(
            name="agents",
            description="List all agents",
            handler=self._cmd_agents
        ))
        self.register(Command(
            name="subagents",
            description="List all subagents",
            handler=self._cmd_subagents
        ))
        self.register(Command(
            name="models",
            description="List all available models",
            handler=self._cmd_models
        ))
        self.register(Command(
            name="init",
            description="Initialize project (create AGENTS.md)",
            handler=self._cmd_init
        ))
        self.register(Command(
            name="analyze",
            description="Analyze project structure",
            handler=self._cmd_analyze
        ))
        self.register(Command(
            name="approve",
            description="Approve pending plan",
            handler=self._cmd_approve
        ))
        self.register(Command(
            name="reject",
            description="Reject pending plan",
            handler=self._cmd_reject,
            args=["reason"]
        ))
        self.register(Command(
            name="redo",
            description="Redo last undone change",
            handler=self._cmd_redo
        ))
        self.register(Command(
            name="shell",
            description="Start interactive shell",
            handler=self._cmd_shell,
            args=["shell_name"]
        ))
        self.register(Command(
            name="commands",
            description="List custom commands",
            handler=self._cmd_commands
        ))

    def register(self, command: Command):
        self._commands[command.name] = command
        if command.aliases:
            for alias in command.aliases:
                self._aliases[alias] = command.name

    def get(self, name: str) -> Command:
        if name in self._aliases:
            name = self._aliases[name]
        return self._commands.get(name)

    def list_commands(self) -> list[dict[str, str]]:
        return [
            {"name": cmd.name, "description": cmd.description}
            for cmd in self._commands.values()
        ]

    def parse(self, text: str) -> tuple[str, list[str]] | None:
        if not text.startswith("/"):
            return None

        parts = text[1:].split()
        if not parts:
            return None

        name = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        return (name, args)

    def execute(self, text: str, context: dict[str, Any] = None) -> str:
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
        agent_name = args[0] if args else "coder"
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


_command_manager: SlashCommandManager | None = None


def get_slash_command_manager() -> SlashCommandManager:
    global _command_manager
    if _command_manager is None:
        _command_manager = SlashCommandManager()
    return _command_manager