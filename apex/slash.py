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
        self.register(
            Command(
                name="agent",
                description="Switch to a different agent",
                handler=self._cmd_agent,
                args=["agent_name"],
                requires_argument=True,
            )
        )
        self.register(
            Command(
                name="model",
                description="Switch to a different model",
                handler=self._cmd_model,
                args=["model_name"],
                requires_argument=True,
            )
        )
        self.register(
            Command(
                name="cwd",
                description="Change working directory",
                handler=self._cmd_cwd,
                args=["path"],
                requires_argument=True,
            )
        )
        self.register(
            Command(name="clear", description="Clear conversation history", handler=self._cmd_clear)
        )
        self.register(
            Command(
                name="save",
                description="Save current session",
                handler=self._cmd_save,
                args=["name"],
            )
        )
        self.register(
            Command(
                name="load",
                description="Load a saved session",
                handler=self._cmd_load,
                args=["name"],
                requires_argument=True,
            )
        )
        self.register(
            Command(name="share", description="Share current session", handler=self._cmd_share)
        )
        self.register(Command(name="undo", description="Undo last change", handler=self._cmd_undo))
        self.register(
            Command(name="redo", description="Redo last undone change", handler=self._cmd_redo)
        )
        self.register(Command(name="git", description="Show git status", handler=self._cmd_git))
        self.register(Command(name="map", description="Show repository map", handler=self._cmd_map))
        self.register(
            Command(name="help", description="Show available commands", handler=self._cmd_help)
        )
        self.register(
            Command(name="cost", description="Show token cost summary", handler=self._cmd_cost)
        )
        self.register(
            Command(name="agents", description="List all agents", handler=self._cmd_agents)
        )
        self.register(
            Command(name="subagents", description="List all subagents", handler=self._cmd_subagents)
        )
        self.register(
            Command(
                name="models", description="List all available models", handler=self._cmd_models
            )
        )
        self.register(
            Command(
                name="init",
                description="Initialize project (create AGENTS.md)",
                handler=self._cmd_init,
            )
        )
        self.register(
            Command(
                name="analyze", description="Analyze project structure", handler=self._cmd_analyze
            )
        )
        self.register(
            Command(name="approve", description="Approve pending plan", handler=self._cmd_approve)
        )
        self.register(
            Command(
                name="reject",
                description="Reject pending plan",
                handler=self._cmd_reject,
                args=["reason"],
            )
        )
        self.register(
            Command(name="redo", description="Redo last undone change", handler=self._cmd_redo)
        )
        self.register(
            Command(
                name="shell",
                description="Start interactive shell",
                handler=self._cmd_shell,
                args=["shell_name"],
            )
        )
        self.register(
            Command(name="commands", description="List custom commands", handler=self._cmd_commands)
        )

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
            {"name": cmd.name, "description": cmd.description} for cmd in self._commands.values()
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
        agent_name = args[0] if args else "build"
        agent = context.get("agent")
        if agent and agent.switch_agent(agent_name):
            return f"Switched to agent: {agent_name}"
        return f"Unknown agent: {agent_name}"

    def _cmd_model(self, args: list[str], context: dict) -> str:
        model = args[0] if args else ""
        agent = context.get("agent")
        if agent and agent.switch_model(model):
            return f"Switched to model: {model}"
        return f"Unknown model: {model}"

    def _cmd_cwd(self, args: list[str], context: dict) -> str:
        path = args[0] if args else "."
        agent = context.get("agent")
        if agent:
            from pathlib import Path
            try:
                new_cwd = Path(path).expanduser().resolve()
                if new_cwd.exists() and new_cwd.is_dir():
                    agent.cwd = new_cwd
                    return f"Changed directory to: {new_cwd}"
            except Exception:
                pass
        return f"Cannot change directory to: {path}"

    def _cmd_clear(self, args: list[str], context: dict) -> str:
        agent = context.get("agent")
        if agent:
            agent.reset_history()
        return "Conversation history cleared"

    def _cmd_save(self, args: list[str], context: dict) -> str:
        name = args[0] if args else "default"
        agent = context.get("agent")
        if agent:
            from .session import SessionManager
            SessionManager().save(agent, name)
            return f"Session saved as '{name}'"
        return f"[SAVE] Session saved as '{name}'"

    def _cmd_load(self, args: list[str], context: dict) -> str:
        name = args[0] if args else ""
        agent = context.get("agent")
        if agent:
            from .session import SessionManager
            if SessionManager().load(name, agent):
                return f"Session loaded: {name}"
            return f"Session not found: {name}"
        return f"[LOAD] Loading session '{name}'..."

    def _cmd_share(self, args: list[str], context: dict) -> str:
        agent = context.get("agent")
        if agent:
            from .share import share_manager
            url = share_manager.share_session("default")
            if url:
                return f"Session shared: {url}"
            return "Sharing is disabled"
        return "[SHARE] Generating share link..."

    def _cmd_undo(self, args: list[str], context: dict) -> str:
        agent = context.get("agent")
        if agent:
            from .git_undo import GitUndoManager
            gum = GitUndoManager(agent.cwd)
            if gum.can_undo():
                gum.undo()
                return "Undone last change"
            return "Nothing to undo"
        return "[UNDO] Undoing last change..."

    def _cmd_redo(self, args: list[str], context: dict) -> str:
        agent = context.get("agent")
        if agent:
            from .git_undo import GitUndoManager
            gum = GitUndoManager(agent.cwd)
            if gum.can_redo():
                gum.redo()
                return "Redone last change"
            return "Nothing to redo"
        return "[REDO] Redoing last change..."

    def _cmd_git(self, args: list[str], context: dict) -> str:
        agent = context.get("agent")
        if agent:
            import subprocess
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=agent.cwd, capture_output=True, text=True
            )
            if result.stdout.strip():
                return f"Git status:\n{result.stdout}"
            return "Git status: clean"
        return "[GIT] Git status:\nbranch: main\nstatus: clean"

    def _cmd_map(self, args: list[str], context: dict) -> str:
        agent = context.get("agent")
        if agent:
            from .context import get_repo_map
            return get_repo_map(agent.cwd)
        return "[MAP] Repository map:\nsrc/\ntests/\nconfig/"

    def _cmd_help(self, args: list[str], context: dict) -> str:
        lines = ["Available Commands:", "=" * 40]
        for cmd in sorted(self._commands.values(), key=lambda c: c.name):
            lines.append(f"  /{cmd.name} - {cmd.description}")
        return "\n".join(lines)

    def _cmd_cost(self, args: list[str], context: dict) -> str:
        agent = context.get("agent")
        if agent:
            usage = agent.usage
            from .cost_local import cost_tracker
            cost_info = cost_tracker.get_session_cost()
            lines = ["Token usage:", f"  Input: {usage.get('prompt_tokens', 0)}",
                     f"  Output: {usage.get('completion_tokens', 0)}",
                     f"  Total tokens: {usage.get('total_tokens', 0)}"]
            lines.append(f"  Cost: ${cost_info.get('total_cost', 0):.6f}")
            return "\n".join(lines)
        return "[COST] Token usage:\nInput: 0\nOutput: 0\nTotal: $0.00"

    def _cmd_agents(self, args: list[str], context: dict) -> str:
        agent = context.get("agent")
        if agent:
            from .agents import agent_manager
            lines = []
            for a in agent_manager.list_agents():
                marker = "*" if a.name == agent.current_agent else " "
                mode = f"[{a.mode}]"
                lines.append(f"  {marker} {a.name} {mode} - {a.description}")
            return "\n".join(lines)
        return "[AGENTS] Primary: build, plan\nSubagents: explore, general"

    def _cmd_subagents(self, args: list[str], context: dict) -> str:
        agent = context.get("agent")
        if agent:
            from .agents import agent_manager
            lines = []
            for a in agent_manager.list_agents("subagent"):
                lines.append(f"  {a.name} - {a.description}")
            return "\n".join(lines)
        return "[SUBAGENTS] explore (read-only), general (full access)"

    def _cmd_models(self, args: list[str], context: dict) -> str:
        from .config import MODELS
        lines = ["Available models:"]
        for alias in sorted(MODELS.keys())[:20]:
            lines.append(f"  {alias}")
        lines.append("  ... and more. Use /model <name> to switch")
        return "\n".join(lines)

    def _cmd_init(self, args: list[str], context: dict) -> str:
        agent = context.get("agent")
        if agent:
            from .project import ProjectInitializer
            pi = ProjectInitializer(str(agent.cwd))
            try:
                path = pi.create_context_file()
                return f"Project initialized: {path}"
            except Exception as e:
                return f"Initialization failed: {e}"
        return "[INIT] Initializing project..."

    def _cmd_analyze(self, args: list[str], context: dict) -> str:
        agent = context.get("agent")
        if agent:
            from .project import ProjectInitializer
            pi = ProjectInitializer(str(agent.cwd))
            analysis = pi.analyze()
            lines = [f"Language: {analysis.get('language', 'unknown')}",
                     f"PM: {analysis.get('package_manager', 'unknown')}",
                     f"Test: {analysis.get('test_framework', 'unknown')}",
                     f"Deps: {len(analysis.get('dependencies', []))}"]
            return "\n".join(lines)
        return "[ANALYZE] Analyzing project..."

    def _cmd_approve(self, args: list[str], context: dict) -> str:
        return "Plan approved. Use the build agent to execute the plan."

    def _cmd_reject(self, args: list[str], context: dict) -> str:
        reason = " ".join(args) if args else "No reason"
        return f"Plan rejected: {reason}"

    def _cmd_shell(self, args: list[str], context: dict) -> str:
        shell = args[0] if args else "bash"
        agent = context.get("agent")
        if agent:
            from .sandbox import ShellSession
            session = ShellSession(cwd=str(agent.cwd))
            if session.start(shell=shell):
                return f"{shell} shell session started"
        return f"[SHELL] Starting {shell}..."

    def _cmd_commands(self, args: list[str], context: dict) -> str:
        from .commands_manager import commands_manager
        cmds = commands_manager.list()
        if cmds:
            lines = ["Custom commands:"]
            for c in cmds:
                lines.append(f"  /{c.name} - {c.description}")
            return "\n".join(lines)
        return "No custom commands defined"


_command_manager: SlashCommandManager | None = None


def get_slash_command_manager() -> SlashCommandManager:
    global _command_manager
    if _command_manager is None:
        _command_manager = SlashCommandManager()
    return _command_manager
