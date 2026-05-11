"""APEX CLI entry point - command parsing and interactive REPL."""

import argparse
import os
import sys
import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from .agent import Agent
from .config import Config, MODELS
from .ui import UI
from .memory import Memory
from .session import SessionManager
from .context import get_repo_map, get_language_stats
from .http_api import start_tui_server, stop_tui_server
from . import __version__
from rich.panel import Panel


memory = Memory()


# Subcommands that can be used as positional args (e.g. `apex tui`)
_SUBCOMMANDS: dict[str, dict[str, bool]] = {
    "tui": {"tui": True},
    "ui": {"tui": True},
    "models": {"list_models": True},
    "install-tui": {"install_tui": True},
    "cli": {"cli": True},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="apex",
        description="APEX — The last coding agent you'll ever need",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "subcommands:\n"
            "  tui             Launch APEX TUI (default when no args given)\n"
            "  ui              Launch APEX TUI (same as tui)\n"
            "  cli             Launch APEX in CLI REPL mode\n"
            "  models          List all available models\n"
            "  install-tui     Install TUI dependencies (bun + tui-frontend)\n"
        ),
    )
    parser.add_argument("prompt", nargs="?", help="One-shot prompt to execute")
    parser.add_argument("--model", "-m", dest="model", help="Model alias to use")
    parser.add_argument("--cwd", "-C", dest="cwd", help="Working directory")
    parser.add_argument("--version", "-v", action="version", version=f"APEX {__version__}")
    parser.add_argument("--list-models", action="store_true", help="List all available models")
    parser.add_argument(
        "--one-shot", "-1", action="store_true", help="One-shot mode (non-interactive)"
    )
    parser.add_argument("--stream", "-s", action="store_true", help="Enable streaming responses")
    parser.add_argument(
        "--auto-commit",
        action="store_true",
        dest="auto_commit",
        help="Auto commit after successful task",
    )
    parser.add_argument("--ui", action="store_true", help="Launch APEX TUI (Ink + React)")
    parser.add_argument("--tui", "-t", action="store_true", help="Launch APEX TUI (same as --ui)")
    parser.add_argument(
        "--cli", action="store_true",
        help="Launch APEX in CLI REPL mode (default is TUI)",
    )
    parser.add_argument("-p", dest="prompt_direct", help="Direct prompt (CI/CD mode, no TUI)")
    parser.add_argument(
        "-f",
        "--format",
        dest="output_format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode (less output)")
    parser.add_argument(
        "--install-tui", action="store_true", help="Install TUI dependencies (Node.js + tui-frontend)"
    )
    return parser.parse_args()


def list_models(ui: UI) -> None:
    ui.show_models(Config().model)


def handle_command(
    command: str,
    agent: Agent,
    ui: UI,
    config: Config | None = None,
    session: Any = None,
    use_stream: bool = False,
) -> bool:
    config = config or Config()
    global memory
    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    match cmd:
        case "/model":
            if not arg:
                ui.print_error("Usage: /model <alias> or /model auto")
                return True
            if arg == "auto":
                config.auto_model = True
                ui.print_success("Auto model selection enabled")
            elif agent.switch_model(arg):
                config.auto_model = False
                ui.print_success(f"Switched to model: {arg}")
            else:
                ui.print_error(f"Unknown model: {arg}")
            return True

        case "/models":
            ui.show_models(agent.model)
            return True

        case "/reasoning":
            level = agent.cycle_reasoning_effort()
            ui.print_success(f"Reasoning effort: {level}")
            return True

        case "/reason":
            level = agent.cycle_reasoning_effort()
            ui.print_success(f"Reasoning effort: {level}")
            return True

        case "/cwd":
            if not arg:
                ui.print_info(f"Current directory: {agent.cwd}")
                return True
            try:
                new_cwd = Path(arg).expanduser().resolve()
            except (ValueError, OSError) as e:
                ui.print_error(f"Invalid path: {e}")
                return True
            if not new_cwd.exists():
                ui.print_error(f"Directory does not exist: {new_cwd}")
                return True
            if not new_cwd.is_dir():
                ui.print_error(f"Not a directory: {new_cwd}")
                return True
            try:
                new_cwd.relative_to(agent.cwd.resolve())
            except ValueError:
                if os.environ.get("APEX_ALLOW_OUTSIDE_CWD") != "true":
                    ui.print_error("Path outside working directory not allowed")
                    return True
            agent.cwd = new_cwd
            os.chdir(new_cwd)
            ui.print_success(f"Changed directory to: {new_cwd}")
            return True

        case "/clear":
            agent.reset_history()
            ui.print_success("Conversation history cleared")
            return True

        case "/history":
            if not agent.history:
                ui.print_info("No conversation history")
                return True
            ui.console.print("[cyan]Conversation history:[/cyan]")
            for i, msg in enumerate(agent.history[-10:]):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if content:
                    truncated = content[:100] + "..." if len(content) > 100 else content
                    ui.console.print(f"  [{role}]: {truncated}")
            return True

        case "/save":
            sm = SessionManager()
            name = arg or "default"
            sm.save(agent, name)
            ui.print_success(f"Session saved as: {name}")
            return True

        case "/load":
            if not arg:
                ui.print_error("Usage: /load <name>")
                return True
            sm = SessionManager()
            loaded = sm.load(arg, agent)
            if loaded:
                ui.print_success(f"Session loaded: {arg}")
            else:
                ui.print_error(f"Session not found: {arg}")
            return True

        case "/sessions":
            sm = SessionManager()
            sessions = sm.list_sessions()
            if not sessions:
                ui.print_info("No saved sessions")
                return True
            ui.console.print("[cyan]Saved sessions:[/cyan]")
            for s in sessions:
                ui.console.print(f"  {s['name']} - {s['timestamp']} ({s['history_len']} messages)")
            return True

        case "/cost":
            from .cost_local import cost_tracker

            usage = agent.usage
            cost_info = cost_tracker.get_session_cost()
            ui.console.print("[cyan]Session Cost:[/cyan]")
            ui.console.print(f"  Input tokens: {cost_info['input_tokens']}")
            ui.console.print(f"  Output tokens: {cost_info['output_tokens']}")
            ui.console.print(f"  Total: ${cost_info['total_cost']:.6f}")
            ui.console.print("[cyan]Token usage:[/cyan]")
            ui.console.print(f"  Prompt: {usage.get('prompt_tokens', 0)}")
            ui.console.print(f"  Completion: {usage.get('completion_tokens', 0)}")
            ui.console.print(f"  Total: {usage.get('total_tokens', 0)}")
            return True

        case "/memory":
            if not arg:
                facts = memory.get_all()
                if not facts:
                    ui.print_info("No memory facts stored")
                else:
                    ui.console.print("[cyan]Memory facts:[/cyan]")
                    for i, f in enumerate(facts):
                        ui.console.print(
                            f"  {i}: {f['fact']} [relevance: {', '.join(f.get('relevance', []))}]"
                        )
                return True

            mem_parts = arg.split(maxsplit=2)
            subcmd = mem_parts[0] if mem_parts else ""

            if subcmd == "add" and len(mem_parts) >= 3:
                fact = mem_parts[1]
                relevance = mem_parts[2].split(",") if len(mem_parts) > 2 else []
                memory.add(fact.strip(), [r.strip() for r in relevance])
                ui.print_success(f"Added to memory: {fact}")
            elif subcmd == "clear":
                memory.clear()
                ui.print_success("Memory cleared")
            elif subcmd == "search" and len(mem_parts) >= 2:
                results = memory.search(mem_parts[1])
                if not results:
                    ui.print_info("No matching facts found")
                else:
                    ui.console.print("[cyan]Search results:[/cyan]")
                    for f in results:
                        ui.console.print(f"  • {f['fact']}")
            else:
                ui.print_info("Usage: /memory [add <fact> <relevance>|clear|search <query>]")
            return True

        case "/map":
            repo_map = get_repo_map(agent.cwd)
            ui.console.print(
                Panel(repo_map, title="[cyan]Repository Map[/cyan]", border_style="cyan")
            )
            return True

        case "/stats":
            stats = get_language_stats(agent.cwd)
            if stats:
                ui.console.print("[cyan]Language stats:[/cyan]")
                for lang, count in sorted(stats.items(), key=lambda x: -x[1]):
                    ui.console.print(f"  {lang}: {count} files")
            else:
                ui.print_info("No source files found")
            return True

        case "/git":
            from .tools import ToolExecutor

            executor = ToolExecutor(cwd=agent.cwd)
            status = executor.execute("get_git_status", {})
            ui.console.print(Panel(status, title="[cyan]Git Status[/cyan]", border_style="cyan"))
            return True

        case "/agent":
            from .agents import agent_manager

            if not arg:
                current = agent.current_agent
                ui.console.print(f"[cyan]Current agent:[/cyan] {current}")
                ui.console.print("\n[cyan]Available agents:[/cyan]")
                for a in agent_manager.list_agents():
                    marker = "✓" if a.name == current else " "
                    mode = "[primary]" if a.mode == "primary" else "[subagent]"
                    ui.console.print(f"  {marker} {a.name} {mode} - {a.description}")
                return True
            if agent.switch_agent(arg):
                ui.print_success(f"Switched to agent: {arg}")
            else:
                ui.print_error(f"Unknown agent: {arg}. Use /agent to list available agents.")
            return True

        case "/coder":
            agent.switch_agent("coder")
            config.agent_mode = "agent"
            ui.print_success("Coder mode enabled — interactive with approval")
            return True

        case "/architect":
            agent.switch_agent("architect")
            config.agent_mode = "plan"
            ui.print_success("Architect mode enabled — read-only")
            return True

        case "/restore":
            from .workspace_rollback import WorkspaceRollback

            wb = WorkspaceRollback(agent.cwd)
            if arg:
                success = wb.restore_snapshot(arg)
                if success:
                    ui.print_success(f"Restored snapshot: {arg}")
                else:
                    ui.print_error(f"Failed to restore: {arg}")
            else:
                snapshots = wb.list_snapshots()
                if snapshots:
                    ui.console.print("[cyan]Available snapshots:[/cyan]")
                    for s in snapshots[-10:]:
                        ui.console.print(f"  {s['name']} - {s.get('label', '')}")
                else:
                    ui.print_info("No snapshots available")
            return True

        case "/revert":
            from .workspace_rollback import TurnTracker

            tt = TurnTracker(agent.cwd)
            turns = int(arg) if arg.isdigit() else 1
            if tt.revert_turn(turns):
                ui.print_success(f"Reverted {turns} turn(s)")
            else:
                ui.print_error("Failed to revert turn")
            return True

        case "/undo":
            from .git_undo import GitUndoManager

            gum = GitUndoManager(agent.cwd)
            if not gum.can_undo():
                ui.print_info("Nothing to undo")
                return True
            steps = int(arg) if arg.isdigit() else 1
            snapshot_id = gum.undo(steps)
            if snapshot_id:
                ui.print_success(f"Undone {steps} step(s)")
            else:
                ui.print_error("Failed to undo")
            return True

        case "/redo":
            from .git_undo import GitUndoManager

            gum = GitUndoManager(agent.cwd)
            if not gum.can_redo():
                ui.print_info("Nothing to redo")
                return True
            steps = int(arg) if arg.isdigit() else 1
            snapshot_id = gum.redo(steps)
            if snapshot_id:
                ui.print_success(f"Redone {steps} step(s)")
            else:
                ui.print_error("Failed to redo")
            return True

        case "/skills":
            from .skills_system import skills_manager

            skills = skills_manager.list_skills()
            if skills:
                ui.console.print("[cyan]Available skills:[/cyan]")
                for s in skills:
                    ui.console.print(f"  {s['name']} - {s['description']}")
            else:
                ui.print_info("No skills available")
            return True

        case "/github":
            from .github_integration import gh_automation

            if not arg:
                ui.print_info("Usage: /github <command> [args]")
                ui.print_info("Commands: issues, prs, create-issue, create-pr")
                return True
            parts = arg.split(maxsplit=1)
            cmd = parts[0]
            if cmd == "issues":
                issues = gh_automation.client.list_issues()
                for issue in issues:
                    ui.console.print(f"  #{issue.get('number')}: {issue.get('title')}")
            elif cmd == "prs":
                prs = gh_automation.client.list_prs()
                for pr in prs:
                    ui.console.print(f"  PR #{pr.get('number')}: {pr.get('title')}")
            else:
                ui.print_error(f"Unknown github command: {cmd}")
            return True

        case "/local":
            from .cost_local import local_manager

            if arg == "enable":
                local_manager.enable_local()
                ui.print_success("Local execution enabled")
            elif arg == "disable":
                local_manager.disable_local()
                ui.print_success("Local execution disabled")
            else:
                providers = local_manager.get_available_providers()
                status = "enabled" if local_manager.is_enabled() else "disabled"
                ui.console.print(f"Local execution: {status}")
                if providers:
                    ui.console.print(f"Available: {', '.join(providers.keys())}")
            return True

        case "/sessionsave":
            from .session import SessionManager

            sm = SessionManager()
            name = arg or "default"
            path = sm.save(agent, name)
            ui.print_success(f"Session saved: {path}")
            return True

        case "/sessionload":
            from .session import SessionManager

            sm = SessionManager()
            if arg:
                session = sm.load(arg)
                if session:
                    agent.history = session.get("history", [])
                    ui.print_success(f"Loaded session: {arg}")
                else:
                    ui.print_error(f"Session not found: {arg}")
            else:
                sessions = sm.list_sessions()
                ui.console.print("[cyan]Saved sessions:[/cyan]")
                for s in sessions:
                    ui.console.print(f"  {s['name']} - {s['timestamp']}")
            return True

        case "/tasks":
            from .task_queue import TaskQueue

            tq = TaskQueue()
            tasks = tq.list_tasks(limit=10)
            if tasks:
                ui.console.print("[cyan]Task queue:[/cyan]")
                for t in tasks:
                    status = t.status.value
                    ui.console.print(f"  {t.id}: {t.name} [{status}]")
            else:
                ui.print_info("No tasks in queue")
            return True

        case "/http":
            if arg == "start":
                ui.print_info("Starting HTTP API server...")
            else:
                ui.print_info("Usage: /http start - Start HTTP API server")
            return True

        case "/agents":
            from .agents import agent_manager
            from rich.table import Table

            table = Table(title="Available Agents", show_header=True, header_style="bold cyan")
            table.add_column("Name", style="cyan", width=12)
            table.add_column("Mode", style="white", width=10)
            table.add_column("Description", style="white")
            current = agent.current_agent
            for a in agent_manager.list_agents():
                marker = "✓" if a.name == current else ""
                table.add_row(f"{a.name} {marker}", a.mode, a.description)
            ui.console.print(table)
            return True

        case "/subagents":
            from .agents import agent_manager
            from rich.table import Table

            table = Table(
                title="Subagents (use @name to invoke)", show_header=True, header_style="bold cyan"
            )
            table.add_column("Name", style="cyan", width=12)
            table.add_column("Description", style="white")
            for a in agent_manager.list_agents("subagent"):
                table.add_row(a.name, a.description)
            ui.console.print(table)
            return True

        case "/help":
            ui.show_help()
            return True

        case "/exit" | "/quit":
            ui.print_info("Goodbye!")
            sys.exit(0)

        case _:
            if cmd.startswith("/"):
                ui.print_error(f"Unknown command: {cmd}. Type /help for available commands.")
                return True
            return False


async def run_repl_streaming(agent: Agent, ui: UI) -> None:
    history_file = Path.home() / ".apex" / "history"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    bindings = KeyBindings()

    @bindings.add("c-c")
    def _(event):
        event.app.exit(exception=KeyboardInterrupt)

    @bindings.add("tab")
    def cycle_agent(event):
        new_agent = agent.cycle_agent()
        ui.print_success(f"Switched to agent: {new_agent}")
        event.app.current_buffer.text = ""

    style = Style.from_dict(
        {
            "prompt": "cyan bold",
            "continuation": "cyan",
        }
    )

    session = PromptSession(
        history=FileHistory(str(history_file)),
        key_bindings=bindings,
        style=style,
        message="› ",
    )

    ui.show_banner(agent.model, str(agent.cwd), agent.current_agent)
    ui.print_info("Type a prompt or /help for commands\n")

    while True:
        try:
            user_input = session.prompt()
            if not user_input.strip():
                continue
            if user_input.startswith("/"):
                if handle_command(user_input, agent, ui, session, use_stream=True):
                    continue
            ui.print_user(user_input)

            full_response = ""
            async for chunk in agent.chat_streaming(user_input):
                full_response += chunk
                ui.console.print(chunk, end="")
            ui.console.print()

        except KeyboardInterrupt:
            ui.print_info("\nType /exit to quit or /clear to clear history")
            continue
        except EOFError:
            break


def run_repl(agent: Agent, ui: UI, use_stream: bool = False) -> None:
    history_file = Path.home() / ".apex" / "history"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    bindings = KeyBindings()

    @bindings.add("c-c")
    def _(event):
        event.app.exit(exception=KeyboardInterrupt)

    @bindings.add("tab")
    def cycle_agent(event):
        new_agent = agent.cycle_agent()
        ui.print_success(f"Switched to agent: {new_agent}")
        event.app.current_buffer.text = ""

    style = Style.from_dict(
        {
            "prompt": "cyan bold",
            "continuation": "cyan",
        }
    )

    session = PromptSession(
        history=FileHistory(str(history_file)),
        key_bindings=bindings,
        style=style,
        message="› ",
    )

    ui.show_banner(agent.model, str(agent.cwd), agent.current_agent)
    ui.print_info("Type a prompt or /help for commands\n")

    while True:
        try:
            user_input = session.prompt()
            if not user_input.strip():
                continue
            if user_input.startswith("/"):
                if handle_command(user_input, agent, ui, session, use_stream):
                    continue
            ui.print_user(user_input)
            with ui.console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
                response = agent.chat(user_input)
            ui.print_response(response)
        except KeyboardInterrupt:
            ui.print_info("\nType /exit to quit or /clear to clear history")
            continue
        except EOFError:
            break


def run_one_shot(prompt: str, agent: Agent, ui: UI, use_stream: bool = False) -> None:
    if use_stream:
        full_response = ""
        ui.console.print("[cyan]Streaming response:[/cyan]")
        for chunk in agent.chat(prompt):
            full_response += chunk
            ui.console.print(chunk, end="")
        ui.console.print()
    else:
        with ui.console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
            response = agent.chat(prompt)
        ui.print_response(response)


def run_cicd_mode(
    prompt: str, agent: Agent, ui: UI, output_format: str = "text", quiet: bool = False
) -> None:
    """CI/CD mode - Direct prompt execution with optional JSON output."""
    try:
        with (
            ui.console.status("[cyan]Processing...[/cyan]", spinner="dots")
            if not quiet
            else ui.console.status("")
        ):
            response = agent.chat(prompt)

        if output_format == "json":
            result = {
                "success": True,
                "prompt": prompt,
                "response": response,
                "model": agent.model,
                "usage": agent.usage,
            }
            print(json.dumps(result, indent=2))
        else:
            if not quiet:
                ui.print_response(response)
            else:
                print(response)

    except Exception as e:
        if output_format == "json":
            print(json.dumps({"success": False, "error": str(e)}, indent=2))
        else:
            ui.print_error(f"Error: {e}")


def _find_tui_dir() -> Path | None:
    """Find the tui-frontend directory, supporting both dev and pip-installed layouts."""
    # 1. Development mode: tui-frontend/ is a sibling of apex/ package dir
    dev_path = Path(__file__).parent.parent / "tui-frontend"
    if (dev_path / "src" / "App.tsx").exists():
        return dev_path

    # 2. Installed package: tui-frontend/ is a sibling of site-packages
    for candidate in [
        Path(__file__).parent.parent.parent / "tui-frontend",  # site-packages/tui-frontend/
        Path.home() / ".apex" / "tui-frontend",  # ~/.apex/tui-frontend/
    ]:
        if (candidate / "src" / "App.tsx").exists():
            return candidate

    return None


def _find_bun() -> str | None:
    """Find the bun executable."""
    # Check common locations (cross-platform)
    bun_candidates = [
        Path.home() / ".bun" / "bin" / "bun",
        Path("/usr/local/bin/bun"),
        Path("/usr/bin/bun"),
    ]
    # Windows-specific paths
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        user_profile = os.environ.get("USERPROFILE", "")
        bun_candidates.extend([
            Path(user_profile) / ".bun" / "bin" / "bun.exe",
            Path(user_profile) / ".bun" / "bin" / "bun",
            Path(local_app) / "bun" / "bun.exe",
        ])
    for candidate in bun_candidates:
        if candidate.exists():
            return str(candidate)

    # Check PATH
    import shutil

    bun_in_path = shutil.which("bun")
    if bun_in_path:
        return bun_in_path

    return None


def _find_node() -> str | None:
    """Find the node executable."""
    import shutil
    return shutil.which("node")


def _find_npx() -> str | None:
    """Find the npx executable."""
    import shutil
    return shutil.which("npx")


def _install_bun(ui: UI) -> str | None:
    """Attempt to install bun automatically."""
    ui.print_info("Bun not found. Installing bun runtime...")
    try:
        if sys.platform == "win32":
            # Windows: use PowerShell to install bun
            ps_cmd = (
                'irm bun.sh/install.ps1 | iex'
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "BUN_INSTALL": str(Path.home() / ".bun")},
            )
            if result.returncode != 0:
                ui.print_warning(f"Bun install failed: {result.stderr[:200]}")
                return None
        else:
            # Unix: use curl + bash
            install_cmd = ["curl", "-fsSL", "https://bun.sh/install"]
            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return None

            install_result = subprocess.run(
                ["bash", "-c", result.stdout],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "BUN_INSTALL": str(Path.home() / ".bun")},
            )
            if install_result.returncode != 0:
                return None

        bun_path = Path.home() / ".bun" / "bin" / "bun"
        if sys.platform == "win32":
            bun_path = bun_path.with_suffix(".exe") if not bun_path.exists() else bun_path
        if bun_path.exists():
            ui.print_success("Bun installed successfully!")
            return str(bun_path)
    except Exception:
        pass
    return None


def _setup_tui_frontend(tui_dir: Path, ui: UI) -> bool:
    """Install TUI dependencies if needed (bun install, with npm fallback)."""
    node_modules = tui_dir / "node_modules"
    if node_modules.exists() and (node_modules / "ink").exists():
        return True

    ui.print_info("Installing TUI dependencies (first run)...")

    # Try bun first
    bun_path = _find_bun()
    if bun_path:
        try:
            result = subprocess.run(
                [bun_path, "install"],
                cwd=str(tui_dir),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                ui.print_success("TUI dependencies installed!")
                return True
            else:
                ui.print_warning(f"bun install failed: {result.stderr[:200]}")
                ui.print_info("Trying npm as fallback...")
        except Exception as e:
            ui.print_warning(f"bun install error: {e}")
            ui.print_info("Trying npm as fallback...")

    # Fallback to npm (works on Windows where bun may not be compatible)
    import shutil
    npm_path = shutil.which("npm")
    if npm_path:
        try:
            result = subprocess.run(
                [npm_path, "install"],
                cwd=str(tui_dir),
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode == 0:
                ui.print_success("TUI dependencies installed with npm!")
                return True
            else:
                ui.print_error(f"npm install failed: {result.stderr[:200]}")
                return False
        except Exception as e:
            ui.print_error(f"npm install error: {e}")
            return False

    ui.print_error(
        "Could not install TUI dependencies. Neither bun nor npm is available.\n"
        "Install bun: https://bun.sh\n"
        "Or install Node.js: https://nodejs.org"
    )
    return False


def _try_run_tui_process(
    tui_dir: Path, runtime_cmd: list[str], ui: UI,
    runtime_name: str = "OpenTUI",
) -> bool:
    """Try to run the TUI frontend with the given runtime command.

    The HTTP API server must already be started before calling this.

    Args:
        tui_dir: Path to tui-frontend directory.
        runtime_cmd: Command list to run (e.g. ["bun", "src/App.tsx"] or ["tsx", "src/App.tsx"]).
        ui: UI instance for messages.
        runtime_name: Display name for the runtime.

    Returns True if TUI ran and exited normally. False if it crashed.
    """
    ui.print_info(f"Starting APEX TUI with {runtime_name} (Ctrl+C to exit)...")

    env = os.environ.copy()
    # Add local node_modules/.bin to PATH so tsx is found
    local_bin = tui_dir / "node_modules" / ".bin"
    if local_bin.exists():
        path_sep = ";" if sys.platform == "win32" else ":"
        env["PATH"] = str(local_bin) + path_sep + env.get("PATH", "")
    # Add bun directory to PATH (in case runtime needs it for resolution)
    bun_path = _find_bun()
    if bun_path:
        path_sep = ";" if sys.platform == "win32" else ":"
        env["PATH"] = str(Path(bun_path).parent) + path_sep + env.get("PATH", "")
    env["APEX_HTTP_PORT"] = "8080"

    try:
        proc = subprocess.Popen(
            runtime_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
            cwd=str(tui_dir),
        )

        # Read stderr in a separate thread to avoid deadlock
        stderr_lines: list[str] = []

        def read_stderr():
            try:
                for line in iter(proc.stderr.readline, ""):
                    if line.strip():
                        stderr_lines.append(line.rstrip())
            except Exception:
                pass

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        # Read stdout for JSON quit signals
        def read_stdout():
            try:
                for line in iter(proc.stdout.readline, ""):
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line)
                        if msg.get("type") == "quit":
                            proc.terminate()
                            return
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass

        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stdout_thread.start()

        # Wait to check if the runtime crashes immediately
        time.sleep(2.0)
        if proc.poll() is not None:
            stderr_output = "\n".join(stderr_lines)
            if "not compatible" in stderr_output.lower() or "version de" in stderr_output.lower():
                ui.print_error(f"{runtime_name} is not compatible with this Windows version.")
                return False
            elif proc.returncode != 0:
                ui.print_error(f"{runtime_name} exited with code {proc.returncode}")
                if stderr_output:
                    ui.print_info(f"Error: {stderr_output[:400]}")
                return False
            else:
                # Exited with code 0 immediately - probably didn't start properly
                ui.print_error(f"{runtime_name} exited immediately")
                return False

        # TUI is running - block until it exits
        while proc.poll() is None:
            time.sleep(0.1)

        return True

    except FileNotFoundError:
        ui.print_error(f"{runtime_name} executable not found: {runtime_cmd[0]}")
        return False
    except Exception as e:
        ui.print_error(f"{runtime_name} error: {e}")
        return False


def _ensure_tsx(tui_dir: Path) -> str | None:
    """Ensure tsx is available for running TSX files with Node.js.

    Returns the path to tsx executable, or None if not available.
    """
    # Check if tsx is already in local node_modules
    local_tsx = tui_dir / "node_modules" / ".bin" / ("tsx.cmd" if sys.platform == "win32" else "tsx")
    if local_tsx.exists():
        return str(local_tsx)

    # Check if tsx is in PATH
    import shutil
    tsx_in_path = shutil.which("tsx")
    if tsx_in_path:
        return tsx_in_path

    return None


def _install_tsx(tui_dir: Path, ui: UI) -> str | None:
    """Install tsx as a devDependency for the TUI frontend."""
    import shutil
    npm_path = shutil.which("npm")
    if not npm_path:
        return None

    ui.print_info("Installing tsx runtime for Node.js TUI support...")
    try:
        result = subprocess.run(
            [npm_path, "install", "--save-dev", "tsx"],
            cwd=str(tui_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            ui.print_success("tsx installed successfully!")
            return _ensure_tsx(tui_dir)
        else:
            ui.print_warning(f"tsx install failed: {result.stderr[:200]}")
    except Exception as e:
        ui.print_warning(f"tsx install error: {e}")
    return None


def run_apex_tui(agent: Agent, ui: UI) -> None:
    """Run APEX TUI - Ink + React terminal interface with real backend.

    The TUI uses Ink (React for terminal) which works with Node.js.
    Falls back to CLI REPL only if Node.js is not available.
    """
    # Find tui-frontend directory
    tui_dir = _find_tui_dir()
    if not tui_dir:
        ui.print_warning("TUI frontend not found. Install with: apex install-tui")
        ui.print_info("Falling back to CLI mode.\n")
        run_repl(agent, ui)
        return

    # Ensure TUI dependencies are installed
    if not _setup_tui_frontend(tui_dir, ui):
        ui.print_warning("TUI dependencies not installed. Falling back to CLI mode.\n")
        run_repl(agent, ui)
        return

    # Ensure tsx is available for running TSX files with Node.js
    tsx_path = _ensure_tsx(tui_dir)
    if not tsx_path:
        tsx_path = _install_tsx(tui_dir, ui)

    tui_entry = str(tui_dir / "src" / "App.tsx")

    # Build the runtime command
    runtime_cmd: list[str] | None = None
    runtime_name: str = ""

    if tsx_path:
        runtime_cmd = [tsx_path, tui_entry]
        runtime_name = "Node.js + tsx"
    else:
        # Fallback: try node with native TS support (Node 22+)
        node_path = _find_node()
        if node_path:
            runtime_cmd = [node_path, "--experimental-strip-types", tui_entry]
            runtime_name = "Node.js (native TS)"

    if not runtime_cmd:
        ui.print_error("\nNo TUI runtime available. Install Node.js: https://nodejs.org")
        ui.print_info("Or use CLI mode: apex --cli\n")
        ui.print_warning("Falling back to CLI mode...\n")
        run_repl(agent, ui)
        return

    # Start the HTTP API server ONCE (shared with TUI)
    ui.print_info("Starting APEX HTTP API server on port 8080...")
    server = start_tui_server(port=8080, agent=agent)
    time.sleep(0.5)

    try:
        success = _try_run_tui_process(tui_dir, runtime_cmd, ui, runtime_name=runtime_name)
        if success:
            return
    finally:
        stop_tui_server(server)

    # TUI failed
    ui.print_error(f"\n{runtime_name} TUI failed. Possible fixes:")
    ui.print_info("  1. Install Node.js: https://nodejs.org (LTS recommended)")
    ui.print_info("  2. Run: apex install-tui")
    ui.print_info("  3. Use CLI mode: apex --cli\n")
    ui.print_warning("Falling back to CLI mode...\n")
    run_repl(agent, ui)


def _install_tui_command(ui: UI) -> None:
    """Install TUI dependencies: bun runtime + tui-frontend source files."""

    # Step 1: Install bun
    bun_path = _find_bun()
    if bun_path:
        ui.print_success(f"Bun already installed: {bun_path}")
    else:
        ui.print_info("Installing Bun runtime...")
        bun_path = _install_bun(ui)
        if not bun_path:
            ui.print_error("Failed to install Bun. Install manually:")
            ui.print_info("  curl -fsSL https://bun.sh/install | bash")
            return
        ui.print_success(f"Bun installed: {bun_path}")

    # Step 2: Check for tui-frontend
    tui_dir = _find_tui_dir()
    if tui_dir:
        ui.print_success(f"TUI frontend found: {tui_dir}")
    else:
        # Clone tui-frontend to ~/.apex/
        apex_dir = Path.home() / ".apex"
        apex_dir.mkdir(parents=True, exist_ok=True)
        tui_target = apex_dir / "tui-frontend"

        if tui_target.exists():
            ui.print_success(f"TUI frontend already at: {tui_target}")
            tui_dir = tui_target
        else:
            ui.print_info("Downloading TUI frontend from GitHub...")
            try:
                result = subprocess.run(
                    [
                        "git",
                        "clone",
                        "--depth",
                        "1",
                        "https://github.com/Ggboykxz/APEX.git",
                        str(apex_dir / "apex-tmp"),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    # Copy only tui-frontend
                    import shutil as sh

                    sh.copytree(
                        str(apex_dir / "apex-tmp" / "tui-frontend"),
                        str(tui_target),
                    )
                    sh.rmtree(str(apex_dir / "apex-tmp"), ignore_errors=True)
                    tui_dir = tui_target
                    ui.print_success(f"TUI frontend installed: {tui_target}")
                else:
                    ui.print_error(f"Failed to download: {result.stderr[:200]}")
                    return
            except Exception as e:
                ui.print_error(f"Failed to download TUI frontend: {e}")
                return

    # Step 3: Install tsx for Node.js fallback
    if tui_dir and not _find_bun():
        tsx_path = _ensure_tsx(tui_dir)
        if not tsx_path:
            _install_tsx(tui_dir, ui)

    # Step 4: Install TUI npm dependencies
    if tui_dir:
        if _setup_tui_frontend(tui_dir, ui):
            ui.print_success("TUI setup complete! Run: apex")
        else:
            ui.print_error("Failed to install TUI dependencies.")
            ui.print_info("Try manually: cd ~/.apex/tui-frontend && npm install")


def main() -> None:
    args = parse_args()

    # Intercept positional subcommands: `apex tui`, `apex models`, etc.
    if args.prompt and args.prompt.lower() in _SUBCOMMANDS:
        for key, value in _SUBCOMMANDS[args.prompt.lower()].items():
            setattr(args, key, value)
        args.prompt = None

    config = Config()
    if args.model:
        if args.model not in MODELS:
            print(f"Error: Unknown model '{args.model}'", file=sys.stderr)
            print("Use --list-models to see available models", file=sys.stderr)
            sys.exit(1)
        config.model = args.model
    if args.cwd:
        config.cwd = Path(args.cwd).expanduser().resolve()

    agent = Agent(config)
    ui = UI()

    if args.list_models:
        list_models(ui)
        sys.exit(0)

    if args.install_tui:
        _install_tui_command(ui)
        sys.exit(0)

    if args.cli:
        # Explicit CLI mode requested
        run_repl(agent, ui, args.stream)
    elif args.ui or args.tui:
        run_apex_tui(agent, ui)
    elif args.prompt_direct:
        run_cicd_mode(args.prompt_direct, agent, ui, args.output_format, args.quiet)
    elif args.prompt:
        run_one_shot(args.prompt, agent, ui, args.stream)
    else:
        # Default: launch TUI
        run_apex_tui(agent, ui)


if __name__ == "__main__":
    main()
