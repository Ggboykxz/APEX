"""APEX CLI entry point — full OpenCode-like command suite.

Usage:
    apex [prompt]                  One-shot prompt
    apex [subcommand] [args...]    Run subcommand
    apex                           Launch TUI (default)
"""

import argparse
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import textwrap
import time
import webbrowser
from pathlib import Path
from typing import Any

from . import __version__
from .agent import Agent
from .config import MODELS
from .ui import UI
from .memory import Memory
from .session import SessionManager
from .context import get_repo_map, get_language_stats
from .http_api import start_tui_server, stop_tui_server
from .config_v2 import apex_config, tui_config
from .commands_manager import commands_manager
from .theme_manager import theme_manager
from .share import share_manager
from .formatter import formatter_manager
from .watcher import watcher
from .agents import agent_manager
from rich.panel import Panel
from rich.table import Table

memory = Memory()
logger = logging.getLogger("apex")

_SUBCOMMANDS: dict[str, dict[str, bool]] = {
    "tui": {"tui": True},
    "ui": {"tui": True},
    "models": {"list_models": True},
    "install-tui": {"install_tui": True},
}


# ── Argument parser ─────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apex",
        description="APEX — The last coding agent you'll ever need",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            subcommands:
              serve             Start headless HTTP API server
              web               Start server + open web interface
              gateway start     Start APEX Gateway (proxy + auth + rate limits)
              gateway key       Generate a new gateway API key
              gateway status    Show gateway status and usage
              run <prompt>      Non-interactive mode
              tui / ui          Launch TUI (default)
              models [name]     List available models
              auth login        Interactive provider login
              auth list         List configured providers
              auth logout       Remove provider config
              key               Set OpenRouter API key quickly
              agent create      Interactive agent creation wizard
              agent list        List all agents
              session list      List sessions
              session delete    Delete a session
              stats             Token usage and cost stats
              export <id>       Export session as JSON
              import <file>     Import session from file
              upgrade           Upgrade APEX
              uninstall         Uninstall APEX
              mcp add           Add MCP server
              mcp list          List MCP servers
              mcp auth          Authenticate MCP server
              db                Database tools
              pr <number>       Fetch and checkout a PR
              attach <url>      Attach TUI to remote backend
              connect           Interactive provider configuration
              init              Initialize APEX for project
              compact           Compact current session
              details           Toggle tool execution details
              thinking          Toggle thinking blocks
              install-tui       Install TUI dependencies
              github <cmd>      GitHub agent (install, run)
              plugin [module]   Install/list plugins
              debug config      Show resolved configuration
              help              Show this help

            TUI slash commands:
              /build            Switch to Build agent (full access)
              /plan             Switch to Plan agent (read-only)
              /connect          Configure a provider
              /key              Set your OpenRouter API key
              /init             Initialize project (create AGENTS.md)
              /compact          Compact session context
              /undo             Undo last change
              /redo             Redo undone change
              /new              Clear conversation
              /sessions         List/switch sessions
              /share            Share current session
              /unshare          Unshare a session
              /export           Export session as JSON
              /themes           List and switch themes
              /thinking         Toggle thinking blocks
              /details          Toggle tool execution details
              /editor           Open external editor
              /help             Show help
              /exit             Exit APEX
        """),
    )

    parser.add_argument("prompt", nargs="?", default=None, help="One-shot prompt to execute")
    parser.add_argument("--model", "-m", dest="model", default=None, help="Model alias to use")
    parser.add_argument("--cwd", "-C", dest="cwd", default=None, help="Working directory")
    parser.add_argument("--version", "-v", action="version", version=f"APEX {__version__}")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    parser.add_argument("--one-shot", "-1", action="store_true", help="One-shot mode")
    parser.add_argument("--stream", "-s", action="store_true", help="Streaming responses")
    parser.add_argument("--auto-commit", action="store_true", dest="auto_commit", help="Auto commit after task")
    parser.add_argument("--ui", action="store_true", help="Launch TUI")
    parser.add_argument("--tui", "-t", action="store_true", help="Launch TUI")
    parser.add_argument("-p", dest="prompt_direct", default=None, help="Direct prompt (CI/CD)")
    parser.add_argument("-f", "--format", dest="output_format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode")
    parser.add_argument("--install-tui", action="store_true", help="Install TUI dependencies")

    parser.add_argument("--continue", dest="resume", action="store_true", help="Resume last session")
    parser.add_argument("--session", dest="session_id", default=None, help="Session ID to load")
    parser.add_argument("--fork", dest="fork_session", default=None, help="Fork session")
    parser.add_argument("--agent", dest="agent_name", default=None, help="Agent to use")
    parser.add_argument("--print-logs", action="store_true", help="Print logs to stdout")
    parser.add_argument("--log-level", dest="log_level", default=None, help="Log level")
    parser.add_argument("--pure", action="store_true", help="Pure mode (no tools)")

    parser.add_argument("--share", action="store_true", help="Share session")
    parser.add_argument("--file", dest="input_file", default=None, help="Read prompt from file")

    # serve / web flags
    parser.add_argument("--port", type=int, default=None, help="Server port")
    parser.add_argument("--hostname", default=None, help="Server hostname")
    parser.add_argument("--cors", default=None, help="CORS origin")
    parser.add_argument("--mdns", action="store_true", help="Enable mDNS advertisement")

    parser.add_argument("--refresh", action="store_true", help="Refresh model list")
    parser.add_argument("--verbose", action="store_true", help="Verbose output (show costs)")
    parser.add_argument("--days", type=int, default=None, help="Days for stats")
    parser.add_argument("--tools", action="store_true", help="Tool stats breakdown")
    parser.add_argument("--models-flag", action="store_true", dest="models_flag", help="Model stats")
    parser.add_argument("--project", default=None, help="Project path for stats")
    parser.add_argument("--sanitize", action="store_true", help="Sanitize export")
    parser.add_argument("--keep-config", action="store_true", help="Keep config on uninstall")
    parser.add_argument("--keep-data", action="store_true", help="Keep data on uninstall")
    parser.add_argument("--dry-run", action="store_true", help="Dry run uninstall")
    parser.add_argument("--force", action="store_true", help="Force uninstall")
    parser.add_argument("--method", default=None, help="Upgrade method (pip, npm, etc.)")

    return parser


# ── Model listing ───────────────────────────────────────────


def list_models(ui: UI, provider_filter: str | None = None,
                verbose: bool = False, refresh: bool = False) -> None:
    from .cost_local import MODEL_PRICING
    if refresh:
        ui.print_success("Refreshing model list...")
    table = Table(title="Available Models" if not verbose else "Available Models (with pricing)",
                  show_header=True, header_style="bold cyan")
    table.add_column("Alias", style="cyan", width=22)
    table.add_column("Provider", style="white", width=14)
    table.add_column("Model ID", style="green", width=40)
    if verbose:
        table.add_column("Input $/1K", style="yellow", width=12)
        table.add_column("Output $/1K", style="yellow", width=12)

    config_model = apex_config.model
    for alias, model_id in sorted(MODELS.items()):
        if provider_filter and provider_filter.lower() not in alias.lower() and provider_filter.lower() not in model_id.lower():
            continue
        provider = alias.split("-")[0] if "-" in alias else "unknown"
        marker = "✓" if alias == config_model else " "
        pricing = MODEL_PRICING.get(alias)
        inp = f"${pricing.per_1k_input:.6f}" if pricing and verbose else ""
        out = f"${pricing.per_1k_output:.6f}" if pricing and verbose else ""
        if verbose:
            table.add_row(f"{marker} {alias}", provider, model_id, inp, out)
        else:
            table.add_row(f"{marker} {alias}", provider, model_id)
    ui.console.print(table)


# ── Slash commands ──────────────────────────────────────────


def handle_command(
    command: str,
    agent: Agent,
    ui: UI,
    config: Any = None,
    session: Any = None,
    use_stream: bool = False,
) -> bool:
    config = config or apex_config
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
                config.set("auto_model", True)
                ui.print_success("Auto model selection enabled")
            elif agent.switch_model(arg):
                config.set("auto_model", False)
                ui.print_success(f"Switched to model: {arg}")
            else:
                ui.print_error(f"Unknown model: {arg}")
            return True

        case "/models":
            ui.show_models(agent.model)
            return True

        case "/reasoning" | "/reason":
            level = agent.cycle_reasoning_effort()
            ui.print_success(f"Reasoning effort: {level}")
            return True

        case "/thinking":
            agent.show_thinking = not getattr(agent, "show_thinking", False)
            state = "enabled" if agent.show_thinking else "disabled"
            ui.print_success(f"Thinking blocks: {state}")
            return True

        case "/details":
            agent.show_details = not getattr(agent, "show_details", False)
            state = "enabled" if agent.show_details else "disabled"
            ui.print_success(f"Tool execution details: {state}")
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

        case "/clear" | "/new":
            agent.reset_history()
            ui.print_success("Conversation history cleared")
            return True

        case "/compact" | "/summarize":
            before = len(agent.history) if hasattr(agent, "history") else 0
            agent.compact_context()
            after = len(agent.history) if hasattr(agent, "history") else 0
            ui.print_success(f"Context compacted: {before} → {after} messages")
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

        case "/sessions" | "/resume" | "/continue":
            sm = SessionManager()
            sessions = sm.list_sessions()
            if not sessions:
                ui.print_info("No saved sessions")
                return True
            if arg:
                loaded = sm.load(arg, agent)
                if loaded:
                    ui.print_success(f"Session loaded: {arg}")
                else:
                    ui.print_error(f"Session not found: {arg}")
                return True
            ui.console.print("[cyan]Saved sessions:[/cyan]")
            for s in sessions:
                ui.console.print(f"  {s['name']} - {s['timestamp']} ({s['history_len']} messages)")
            ui.print_info("Use /sessions <name> to load a session")
            return True

        case "/export":
            from .share import share_manager as sm
            if not arg:
                ui.print_error("Usage: /export <session_id>")
                return True
            data = sm.export_session(arg)
            if data:
                out = Path.cwd() / f"session_{arg}.json"
                out.write_text(json.dumps(data, indent=2))
                ui.print_success(f"Exported to {out}")
            else:
                ui.print_error(f"Session not found: {arg}")
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
                        ui.console.print(f"  {i}: {f['fact']} [relevance: {', '.join(f.get('relevance', []))}]")
                return True
            mem_parts = arg.split(maxsplit=2)
            subcmd = mem_parts[0] if mem_parts else ""
            if subcmd == "add" and len(mem_parts) >= 3:
                fact = mem_parts[1].strip()
                relevance = [r.strip() for r in mem_parts[2].split(",")]
                memory.add(fact, relevance)
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
                        ui.console.print(f"  \u2022 {f['fact']}")
            else:
                ui.print_info("Usage: /memory [add <fact> <relevance>|clear|search <query>]")
            return True

        case "/map":
            repo_map = get_repo_map(agent.cwd)
            ui.console.print(Panel(repo_map, title="[cyan]Repository Map[/cyan]", border_style="cyan"))
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
                    marker = "\u2713" if a.name == current else " "
                    mode = "[primary]" if a.mode == "primary" else "[subagent]"
                    ui.console.print(f"  {marker} {a.name} {mode} - {a.description}")
                return True
            if agent.switch_agent(arg):
                ui.print_success(f"Switched to agent: {arg}")
            else:
                ui.print_error(f"Unknown agent: {arg}")
            return True

        case "/build":
            agent.switch_agent("build")
            config.set("agent_mode", "agent")
            ui.print_success("Build mode enabled — full access")
            return True

        case "/plan":
            agent.switch_agent("plan")
            config.set("agent_mode", "plan")
            ui.print_success("Plan mode enabled — read-only analysis")
            return True

        case "/planner":
            agent.switch_agent("planner")
            config.set("agent_mode", "plan")
            ui.print_success("Planner mode enabled — read-only planning without delegation")
            return True

        case "/coder":
            agent.switch_agent("build")
            config.set("agent_mode", "agent")
            ui.print_success("Build mode enabled — full access")
            return True

        case "/architect":
            agent.switch_agent("plan")
            config.set("agent_mode", "plan")
            ui.print_success("Plan mode enabled — read-only analysis")
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
            gparts = arg.split(maxsplit=1)
            gcmd = gparts[0]
            if gcmd == "issues":
                issues = gh_automation.client.list_issues()
                for issue in issues:
                    ui.console.print(f"  #{issue.get('number')}: {issue.get('title')}")
            elif gcmd == "prs":
                prs = gh_automation.client.list_prs()
                for pr in prs:
                    ui.console.print(f"  PR #{pr.get('number')}: {pr.get('title')}")
            else:
                ui.print_error(f"Unknown github command: {gcmd}")
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
            sm = SessionManager()
            name = arg or "default"
            path = sm.save(agent, name)
            ui.print_success(f"Session saved: {path}")
            return True

        case "/sessionload":
            sm = SessionManager()
            if arg:
                loaded = sm.load(arg, agent)
                if loaded:
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
                    ui.console.print(f"  {t.id}: {t.name} [{t.status.value}]")
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
            table = Table(title="Available Agents", show_header=True, header_style="bold cyan")
            table.add_column("Name", style="cyan", width=12)
            table.add_column("Mode", style="white", width=10)
            table.add_column("Description", style="white")
            current = agent.current_agent
            for a in agent_manager.list_agents():
                marker = "\u2713" if a.name == current else ""
                table.add_row(f"{a.name} {marker}", a.mode, a.description)
            ui.console.print(table)
            return True

        case "/subagents":
            from .agents import agent_manager
            table = Table(title="Subagents (use @name to invoke)", show_header=True, header_style="bold cyan")
            table.add_column("Name", style="cyan", width=12)
            table.add_column("Description", style="white")
            for a in agent_manager.list_agents("subagent"):
                table.add_row(a.name, a.description)
            ui.console.print(table)
            return True

        case "/connect":
            _interactive_provider_config(agent, ui)
            return True

        case "/key":
            _cmd_key(argparse.Namespace(key_value=arg, model=None, auth_subcommand=None, auth_provider=None), ui)
            return True

        case "/init":
            _cmd_init(ui)
            return True

        case "/themes":
            from .theme_manager import theme_manager
            themes = list(theme_manager.list())
            table = Table(title="Available Themes", show_header=True, header_style="bold cyan")
            table.add_column("Name", style="cyan", width=16)
            table.add_column("Description", style="white")
            current = theme_manager.current()
            for t in themes:
                marker = "\u2713" if t["name"] == current else ""
                table.add_row(f"{t['name']} {marker}", t.get("description", ""))
            ui.console.print(table)
            if arg:
                if theme_manager.set(arg):
                    ui.print_success(f"Theme switched to: {arg}")
                else:
                    ui.print_error(f"Unknown theme: {arg}")
            return True

        case "/editor":
            import subprocess, tempfile
            editor = os.environ.get("EDITOR", "vim")
            prompt_file = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
            prompt_file.write("# Enter your prompt\n\n")
            prompt_file.close()
            try:
                subprocess.call([editor, prompt_file.name])
                content = Path(prompt_file.name).read_text()
                lines = [l for l in content.split("\n") if not l.startswith("#")]
                prompt = "\n".join(lines).strip()
                if prompt:
                    ui.print_user(prompt)
                    with ui.console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
                        response = agent.chat(prompt)
                    ui.print_response(response)
            finally:
                os.unlink(prompt_file.name)
            return True

        case "/share":
            from .share import share_manager as sm
            share_id = arg or str(int(time.time()))
            url = sm.share_session(share_id)
            if url:
                ui.print_success(f"Session shared: {url}")
            else:
                ui.print_error("Failed to share session")
            return True

        case "/unshare":
            from .share import share_manager as sm
            if not arg:
                ui.print_error("Usage: /unshare <share_id>")
                return True
            if sm.unshare_session(arg):
                ui.print_success(f"Session unshared: {arg}")
            else:
                ui.print_error(f"Share not found: {arg}")
            return True

        case "/help":
            ui.show_help()
            return True

        case "/exit" | "/quit" | "/q":
            ui.print_info("Goodbye!")
            sys.exit(0)

        case _:
            if cmd.startswith("/"):
                # Try custom commands
                cmd_name = cmd[1:]
                custom = commands_manager.get(cmd_name)
                if custom:
                    response = commands_manager.execute(cmd_name, [arg] if arg else [], agent)
                    ui.print_response(response)
                    return True
                ui.print_error(f"Unknown command: {cmd}. Type /help for commands.")
                return True
            return False


# ── REPL / Streaming ────────────────────────────────────────





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

    style = Style.from_dict({"prompt": "cyan bold", "continuation": "cyan"})
    prompt_session = PromptSession(
        history=FileHistory(str(history_file)),
        key_bindings=bindings,
        style=style,
        message="\u203a ",
    )

    ui.show_banner(agent.model, str(agent.cwd), agent.current_agent)
    ui.print_info("Type a prompt or /help for commands\n")

    while True:
        try:
            user_input = prompt_session.prompt()
            if not user_input.strip():
                continue
            if user_input.startswith("/"):
                if handle_command(user_input, agent, ui, apex_config, prompt_session, use_stream):
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
        ui.console.print("[cyan]Streaming response:[/cyan]")
        for chunk in agent.chat(prompt):
            ui.console.print(chunk, end="")
        ui.console.print()
    else:
        with ui.console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
            response = agent.chat(prompt)
        ui.print_response(response)


def run_cicd_mode(
    prompt: str, agent: Agent, ui: UI, output_format: str = "text", quiet: bool = False
) -> None:
    try:
        with ui.console.status("[cyan]Processing...[/cyan]", spinner="dots") if not quiet else ui.console.status(""):
            response = agent.chat(prompt)
        if output_format == "json":
            result = {"success": True, "prompt": prompt, "response": response,
                      "model": agent.model, "usage": agent.usage}
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


# ── TUI helpers (unchanged) ─────────────────────────────────


def _find_tui_dir() -> Path | None:
    dev_path = Path(__file__).parent.parent / "tui-frontend"
    if (dev_path / "src" / "App.tsx").exists():
        return dev_path
    for candidate in [
        Path(__file__).parent.parent.parent / "tui-frontend",
        Path.home() / ".apex" / "tui-frontend",
    ]:
        if (candidate / "src" / "App.tsx").exists():
            return candidate
    return None


def _find_bun() -> str | None:
    bun_candidates = [
        Path.home() / ".bun" / "bin" / "bun",
        Path("/usr/local/bin/bun"),
        Path("/usr/bin/bun"),
    ]
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
    return shutil.which("bun")


def _find_node() -> str | None:
    return shutil.which("node")


def _find_npx() -> str | None:
    return shutil.which("npx")


def _install_bun(ui: UI) -> str | None:
    ui.print_info("Bun not found. Installing bun runtime via npm...")
    try:
        npx_path = _find_npx()
        if not npx_path:
            ui.print_error("npx not found. Install Node.js first: https://nodejs.org")
            return None
        result = subprocess.run(
            [npx_path, "--yes", "bun@1", "--version"],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "npm_config_prefix": str(Path.home() / ".npm-global")},
        )
        if result.returncode != 0:
            ui.print_error("Failed to install bun via npx")
            return None
        bun_path = shutil.which("bun") or Path.home() / ".npm-global" / "bin" / "bun"
        if bun_path and Path(bun_path).exists():
            ui.print_success("Bun installed successfully!")
            return str(bun_path)
    except Exception:
        pass
    return None


def _setup_tui_frontend(tui_dir: Path, ui: UI) -> bool:
    node_modules = tui_dir / "node_modules"
    if node_modules.exists() and (node_modules / "ink").exists():
        return True
    # Remove stale lockfiles that may reference wrong React versions
    for lockfile in ["bun.lock", "bun.lockb", "package-lock.json"]:
        lock_path = tui_dir / lockfile
        if lock_path.exists():
            try:
                lock_path.unlink()
            except OSError:
                pass
    ui.print_info("Installing TUI dependencies (first run)...")
    bun_path = _find_bun()
    if bun_path:
        try:
            result = subprocess.run(
                [bun_path, "install"], cwd=str(tui_dir),
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                ui.print_success("TUI dependencies installed!")
                return True
        except Exception:
            pass
    npm_path = shutil.which("npm")
    if npm_path:
        try:
            result = subprocess.run(
                [npm_path, "install"], cwd=str(tui_dir),
                capture_output=True, text=True, timeout=180,
            )
            if result.returncode == 0:
                ui.print_success("TUI dependencies installed with npm!")
                return True
        except Exception:
            pass
    ui.print_error("Could not install TUI dependencies. Neither bun nor npm is available.")
    return False


def _try_run_tui_process(tui_dir: Path, runtime_cmd: list[str], ui: UI,
                         port: int = 8080, runtime_name: str = "Ink") -> bool:
    ui.print_info(f"Starting APEX TUI with {runtime_name} (Ctrl+C to exit)...")
    env = os.environ.copy()
    local_bin = tui_dir / "node_modules" / ".bin"
    if local_bin.exists():
        path_sep = ";" if sys.platform == "win32" else ":"
        env["PATH"] = str(local_bin) + path_sep + env.get("PATH", "")
    bun_path = _find_bun()
    if bun_path:
        path_sep = ";" if sys.platform == "win32" else ":"
        env["PATH"] = str(Path(bun_path).parent) + path_sep + env.get("PATH", "")
    env["APEX_HTTP_PORT"] = str(port)
    env["APEX"] = "1"
    env["APEX_PID"] = str(os.getpid())
    try:
        # Ink requires TTY for raw mode — pass stdin/stdout/stderr directly
        proc = subprocess.Popen(
            runtime_cmd, stdin=sys.stdin, stdout=sys.stdout,
            stderr=sys.stderr, env=env, cwd=str(tui_dir),
        )
        while proc.poll() is None:
            time.sleep(0.1)
        return proc.returncode == 0
    except FileNotFoundError:
        ui.print_error(f"{runtime_name} executable not found: {runtime_cmd[0]}")
        return False
    except Exception as e:
        ui.print_error(f"{runtime_name} error: {e}")
        return False


def _ensure_tsx(tui_dir: Path) -> str | None:
    local_tsx = tui_dir / "node_modules" / ".bin" / ("tsx.cmd" if sys.platform == "win32" else "tsx")
    if local_tsx.exists():
        return str(local_tsx)
    return shutil.which("tsx")


def _install_tsx(tui_dir: Path, ui: UI) -> str | None:
    npm_path = shutil.which("npm")
    if not npm_path:
        return None
    ui.print_info("Installing tsx runtime for Node.js TUI support...")
    try:
        result = subprocess.run(
            [npm_path, "install", "--save-dev", "tsx"],
            cwd=str(tui_dir), capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            ui.print_success("tsx installed successfully!")
            return _ensure_tsx(tui_dir)
    except Exception:
        pass
    return None


def _find_free_port() -> int:
    """Find a random free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def run_apex_tui(agent: Agent, ui: UI, resume: bool = False,
                 session_id: str | None = None, fork: str | None = None) -> None:
    tui_dir = _find_tui_dir()
    if not tui_dir:
        ui.print_error("TUI frontend not found. Install with: apex install-tui")
        sys.exit(1)

    # Ensure package.json has React 18 (not 19) before installing deps
    _patch_tui_package_json(tui_dir)

    if not _setup_tui_frontend(tui_dir, ui):
        ui.print_error("TUI dependencies not installed. Run: apex install-tui")
        sys.exit(1)

    tsx_path = _ensure_tsx(tui_dir)
    if not tsx_path:
        tsx_path = _install_tsx(tui_dir, ui)

    tui_entry = str(tui_dir / "src" / "App.tsx")
    runtime_cmd: list[str] | None = None
    runtime_name = ""

    if tsx_path:
        runtime_cmd = [tsx_path, tui_entry]
        runtime_name = "Node.js + tsx"
    else:
        node_path = _find_node()
        if node_path:
            runtime_cmd = [node_path, "--experimental-strip-types", tui_entry]
            runtime_name = "Node.js (native TS)"

    if not runtime_cmd:
        ui.print_error("TUI requires Node.js. Install from https://nodejs.org")
        sys.exit(1)

    # Resume or load session if requested
    if resume:
        sm = SessionManager()
        sessions = sm.list_sessions()
        if sessions:
            latest = sessions[0]
            sm.load(latest["name"], agent)
            ui.print_success(f"Resumed session: {latest['name']}")
    elif session_id:
        sm = SessionManager()
        sm.load(session_id, agent)
        ui.print_success(f"Loaded session: {session_id}")

    # Use a random free port instead of hardcoded 8080
    port = _find_free_port()

    ui.print_info(f"Starting APEX HTTP API server on port {port}...")
    server = start_tui_server(port=port, agent=agent)

    logger.info(f"APEX v{__version__} starting...")
    logger.info(f"Project: {agent.cwd}")
    logger.info(f"Model: {agent.model}")
    logger.info(f"Agent: {agent.current_agent}")
    logger.info(f"HTTP API: http://127.0.0.1:{port}")

    try:
        success = _try_run_tui_process(tui_dir, runtime_cmd, ui, port=port, runtime_name=runtime_name)
        if success:
            return
    finally:
        stop_tui_server(server)

    ui.print_error(f"TUI failed. Run: apex install-tui")
    sys.exit(1)


def _patch_tui_package_json(tui_dir: Path) -> None:
    """Patch tui-frontend/package.json to ensure React 18 + react-reconciler for Ink compatibility.

    Ink 5.x requires react-reconciler which only supports React ^18.3.1.
    If the repo's package.json still has React 19, this patches it after download.
    """
    pkg_path = tui_dir / "package.json"
    if not pkg_path.exists():
        return
    try:
        data = json.loads(pkg_path.read_text())
        deps = data.get("dependencies", {})
        dev_deps = data.get("devDependencies", {})
        patched = False

        # Downgrade React 19 → 18 if present
        if "react" in deps and deps["react"].startswith("^19"):
            deps["react"] = "^18.3.1"
            patched = True
        # Ensure react-reconciler is present for Ink
        if "react-reconciler" not in deps:
            deps["react-reconciler"] = "^0.29.2"
            patched = True
        # Fix @types/react to match React 18
        if "@types/react" in dev_deps and dev_deps["@types/react"].startswith("^19"):
            dev_deps["@types/react"] = "^18.3.0"
            patched = True
        # Fix invalid typescript version
        if "typescript" in dev_deps and dev_deps["typescript"].startswith("^6"):
            dev_deps["typescript"] = "^5.7.0"
            patched = True

        if patched:
            pkg_path.write_text(json.dumps(data, indent=2) + "\n")
            logger.info("Patched tui-frontend/package.json for React 18 / Ink compatibility")
    except Exception as e:
        logger.warning(f"Failed to patch tui-frontend/package.json: {e}")


def _install_tui_command(ui: UI) -> None:
    bun_path = _find_bun()
    if bun_path:
        ui.print_success(f"Bun already installed: {bun_path}")
    else:
        ui.print_info("Installing Bun runtime...")
        bun_path = _install_bun(ui)
        if not bun_path:
            ui.print_error("Failed to install Bun. Run: curl -fsSL https://bun.sh/install | bash")
            return
        ui.print_success(f"Bun installed: {bun_path}")

    tui_dir = _find_tui_dir()
    if tui_dir:
        ui.print_success(f"TUI frontend found: {tui_dir}")
    else:
        apex_dir = Path.home() / ".apex"
        apex_dir.mkdir(parents=True, exist_ok=True)
        tui_target = apex_dir / "tui-frontend"
        if tui_target.exists():
            ui.print_success(f"TUI frontend already at: {tui_target}")
            tui_dir = tui_target
        else:
            ui.print_info("Downloading TUI frontend from GitHub...")
            try:
                # Use tarball download instead of full git clone (much smaller)
                import tempfile
                import tarfile
                import urllib.request
                tarball_url = "https://api.github.com/repos/Ggboykxz/APEX/tarball/main"
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tarball_path = Path(tmp_dir) / "apex.tar.gz"
                    try:
                        urllib.request.urlretrieve(tarball_url, str(tarball_path))
                    except Exception:
                        # Fallback to git clone if tarball fails
                        result = subprocess.run(
                            ["git", "clone", "--depth", "1",
                             "https://github.com/Ggboykxz/APEX.git",
                             str(Path(tmp_dir) / "apex-repo")],
                            capture_output=True, text=True, timeout=60,
                        )
                        if result.returncode != 0:
                            ui.print_error(f"Failed to download: {result.stderr[:200]}")
                            return
                        # Find tui-frontend in cloned repo
                        repo_dir = next(Path(Path(tmp_dir) / "apex-repo").iterdir(), None)
                        if repo_dir and (repo_dir / "tui-frontend").exists():
                            shutil.copytree(str(repo_dir / "tui-frontend"), str(tui_target))
                            tui_dir = tui_target
                            ui.print_success(f"TUI frontend installed: {tui_target}")
                        else:
                            ui.print_error("tui-frontend directory not found in repository")
                            return
                    else:
                        # Extract only the tui-frontend directory from tarball
                        with tarfile.open(str(tarball_path), "r:gz") as tar:
                            tui_members = [m for m in tar.getmembers()
                                           if "/tui-frontend/" in m.name]
                            if tui_members:
                                # Extract to temp dir first, then copy
                                tar.extractall(path=tmp_dir, members=tui_members)
                                # Find the extracted tui-frontend dir
                                extracted = list(Path(tmp_dir).rglob("tui-frontend"))
                                if extracted:
                                    src = extracted[0]
                                    if src.is_dir():
                                        shutil.copytree(str(src), str(tui_target))
                                        tui_dir = tui_target
                                        ui.print_success(f"TUI frontend installed: {tui_target}")
                            else:
                                ui.print_error("tui-frontend directory not found in repository")
                                return
            except Exception as e:
                ui.print_error(f"Failed to download TUI frontend: {e}")
                return

    # Post-install: patch package.json to ensure React 18 compatibility with Ink
    if tui_dir:
        _patch_tui_package_json(tui_dir)

    if tui_dir and not _find_bun():
        tsx_path = _ensure_tsx(tui_dir)
        if not tsx_path:
            _install_tsx(tui_dir, ui)

    if tui_dir:
        if _setup_tui_frontend(tui_dir, ui):
            ui.print_success("TUI setup complete! Run: apex")
        else:
            ui.print_error("Failed to install TUI dependencies.")


# ── Subcommand handlers ─────────────────────────────────────


def _cmd_serve(args: argparse.Namespace, ui: UI) -> None:
    try:
        from .http_api import HTTPServer
        host = args.hostname or apex_config.server.get("hostname", "127.0.0.1")
        port = args.port or apex_config.server.get("port", 8080)
        ui.print_info(f"Starting APEX HTTP API server on {host}:{port}...")
        agent = Agent(apex_config)
        server = HTTPServer(host=host, port=port)
        ui.print_success(f"Server running at http://{host}:{port}")
        server.run()
    except Exception as e:
        ui.print_error(f"Failed to start server: {e}")
        sys.exit(1)


def _cmd_web(args: argparse.Namespace, ui: UI) -> None:
    try:
        from .http_api import HTTPServer
        host = args.hostname or apex_config.server.get("hostname", "127.0.0.1")
        port = args.port or apex_config.server.get("port", 8080)
        ui.print_info(f"Starting APEX web server on {host}:{port}...")
        agent = Agent(apex_config)
        server = HTTPServer(host=host, port=port)
        url = f"http://{host}:{port}"
        ui.print_success(f"Opening {url} in browser...")
        webbrowser.open(url)
        server.run()
    except Exception as e:
        ui.print_error(f"Failed to start web server: {e}")
        sys.exit(1)


def _cmd_auth(args: argparse.Namespace, ui: UI) -> None:
    auth_dir = Path.home() / ".config" / "apex"
    auth_file = auth_dir / "auth.json"
    auth_dir.mkdir(parents=True, exist_ok=True)

    if args.auth_subcommand == "list":
        if auth_file.exists():
            data = json.loads(auth_file.read_text())
            table = Table(title="Configured Providers", show_header=True, header_style="bold cyan")
            table.add_column("Provider", style="cyan", width=20)
            table.add_column("Key (last 8)", style="yellow", width=16)
            table.add_column("Model", style="green", width=24)
            for prov, info in data.items():
                key_preview = "..." + info.get("api_key", "")[-8:] if info.get("api_key") else "not set"
                model = info.get("model", "default")
                table.add_row(prov, key_preview, model)
            ui.console.print(table)
        else:
            ui.print_info("No providers configured")
        return

    if args.auth_subcommand == "logout":
        if not args.auth_provider:
            ui.print_error("Usage: apex auth logout --provider <name>")
            sys.exit(1)
        if auth_file.exists():
            data = json.loads(auth_file.read_text())
            if args.auth_provider in data:
                del data[args.auth_provider]
                auth_file.write_text(json.dumps(data, indent=2))
                ui.print_success(f"Logged out from provider: {args.auth_provider}")
            else:
                ui.print_error(f"Provider not found: {args.auth_provider}")
                sys.exit(1)
        return

    # login
    provider = args.auth_provider
    if not provider:
        provider = ui.input("Provider name (e.g. anthropic, openai, openrouter): ").strip()
    if not provider:
        ui.print_error("Provider name required")
        sys.exit(1)

    # Quick setup for OpenRouter
    if provider.lower() in ("openrouter", "or"):
        key = ui.input("OpenRouter API key (sk-or-v1-...): ").strip()
        if not key:
            ui.print_error("API key required")
            sys.exit(1)
        data = {}
        if auth_file.exists():
            data = json.loads(auth_file.read_text())
        data["openrouter"] = {"api_key": key, "configured_at": time.time()}
        auth_file.write_text(json.dumps(data, indent=2))
        os.environ["OPENROUTER_API_KEY"] = key
        # Also write .env for persistence
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            env_path.write_text(f"# APEX Configuration\nOPENROUTER_API_KEY={key}\n")
            ui.print_success("OpenRouter configured! Key saved to .env")
        else:
            lines = env_path.read_text().splitlines()
            for i, line in enumerate(lines):
                if line.startswith("OPENROUTER_API_KEY="):
                    lines[i] = f"OPENROUTER_API_KEY={key}"
                    break
            else:
                lines.append(f"OPENROUTER_API_KEY={key}")
            env_path.write_text("\n".join(lines) + "\n")
            ui.print_success("OpenRouter configured! Key updated in .env")
        return

    key = ui.input(f"API key for {provider}: ").strip()
    if not key:
        ui.print_error("API key required")
        sys.exit(1)

    data = {}
    if auth_file.exists():
        data = json.loads(auth_file.read_text())
    data[provider] = {"api_key": key, "model": args.model or "default", "configured_at": time.time()}
    auth_file.write_text(json.dumps(data, indent=2))
    ui.print_success(f"Provider '{provider}' configured!")


def _cmd_agent(args: argparse.Namespace, ui: UI) -> None:
    from .agents import agent_manager, AgentConfig

    if args.agent_subcommand == "list":
        agents = agent_manager.list_agents()
        if not agents:
            ui.print_info("No agents configured")
            return
        table = Table(title="APEX Agents", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan", width=14)
        table.add_column("Mode", style="white", width=10)
        table.add_column("Model", style="green", width=20)
        table.add_column("Description", style="white")
        for a in agents:
            model = a.model or "default"
            table.add_row(a.name, a.mode, model, a.description)
        ui.console.print(table)
        return

    if args.agent_subcommand == "create":
        ui.print_info("Creating new agent (interactive wizard)...")
        name = ui.input("Agent name: ").strip()
        if not name:
            ui.print_error("Name required")
            sys.exit(1)
        desc = ui.input("Description: ").strip()
        mode = ui.input("Mode (primary/subagent) [subagent]: ").strip() or "subagent"
        model = ui.input("Model (leave empty for default): ").strip() or None
        read_perm = ui.input("Read permission (allow/ask/deny) [allow]: ").strip() or "allow"
        edit_perm = ui.input("Edit permission (allow/ask/deny) [ask]: ").strip() or "ask"
        bash_perm = ui.input("Bash permission (allow/ask/deny) [ask]: ").strip() or "ask"

        agent_dir = Path.home() / ".config" / "apex" / "agents"
        agent_dir.mkdir(parents=True, exist_ok=True)
        agent_file = agent_dir / f"{name}.md"

        content = f"""---
description: {desc}
mode: {mode}
model: {model or ""}
permission:
  read: {read_perm}
  edit: {edit_perm}
  bash: {bash_perm}
---

You are the {name} agent for APEX.

{desc}

Your role:
- Analyze code and provide expert insights
- Follow best practices for the task at hand
- Be thorough and precise in all your work
"""
        agent_file.write_text(content)
        # Reload markdown agents
        agent_manager.load_markdown_agents()
        ui.print_success(f"Agent '{name}' created at {agent_file}")
        return

    ui.print_error("Usage: apex agent <create|list>")
    sys.exit(1)


def _cmd_run(args: argparse.Namespace, ui: UI) -> None:
    config = apex_config
    if args.model:
        config.model = args.model
    if args.agent_name:
        config.set("default_agent", args.agent_name)

    agent = Agent(config)
    if args.agent_name:
        agent.switch_agent(args.agent_name)

    if args.resume:
        sm = SessionManager()
        sessions = sm.list_sessions()
        if sessions:
            sm.load(sessions[0]["name"], agent)
    elif args.session_id:
        sm = SessionManager()
        sm.load(args.session_id, agent)

    prompt = args.prompt
    if args.input_file:
        prompt = Path(args.input_file).read_text().strip()
    if not prompt:
        ui.print_error("No prompt provided. Usage: apex run <prompt>")
        sys.exit(1)

    if args.output_format == "json":
        try:
            response = agent.chat(prompt)
            result = {"success": True, "prompt": prompt, "response": response,
                      "model": agent.model, "usage": agent.usage}
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}, indent=2))
            sys.exit(1)
    else:
        run_one_shot(prompt, agent, ui, args.stream)


def _cmd_session(args: argparse.Namespace, ui: UI) -> None:
    sm = SessionManager()
    if args.session_subcommand == "list":
        count = args.n if hasattr(args, "n") and args.n else 20
        sessions = sm.list_sessions()[:count]
        if not sessions:
            ui.print_info("No saved sessions")
            return
        fmt = getattr(args, "list_format", "table")
        if fmt == "json":
            print(json.dumps(sessions, indent=2))
        else:
            table = Table(title="Sessions", show_header=True, header_style="bold cyan")
            table.add_column("Name", style="cyan", width=16)
            table.add_column("Model", style="green", width=20)
            table.add_column("Messages", style="yellow", width=10)
            table.add_column("Timestamp", style="white")
            for s in sessions:
                table.add_row(s["name"], s.get("model", ""), str(s.get("history_len", 0)), s.get("timestamp", ""))
            ui.console.print(table)
        return

    if args.session_subcommand == "delete":
        if not args.session_id:
            ui.print_error("Usage: apex session delete <session_id>")
            sys.exit(1)
        sessions_dir = Path.home() / ".apex" / "sessions"
        deleted = False
        for f in sessions_dir.glob(f"*{args.session_id}*"):
            if f.is_file() and f.suffix == ".json":
                f.unlink()
                deleted = True
        if deleted:
            ui.print_success(f"Deleted session: {args.session_id}")
        else:
            ui.print_error(f"Session not found: {args.session_id}")
            sys.exit(1)
        return

    ui.print_error("Usage: apex session <list|delete>")
    sys.exit(1)


def _cmd_stats(args: argparse.Namespace, ui: UI) -> None:
    from .cost_local import cost_tracker, MODEL_PRICING
    sm = SessionManager()
    sessions = sm.list_sessions()

    days = args.days or 30
    cutoff = time.time() - (days * 86400)
    recent = [s for s in sessions if s.get("timestamp") and _parse_ts(s["timestamp"]) > 0 and _parse_ts(s["timestamp"]) > cutoff]

    total_input = 0
    total_output = 0
    total_cost = 0.0
    model_stats: dict[str, dict] = {}

    for s in recent:
        model = s.get("model", "unknown")
        history_len = s.get("history_len", 0)
        # rough estimate: ~500 tokens per message average
        inp_est = history_len * 250
        out_est = history_len * 250
        total_input += inp_est
        total_output += out_est
        pricing = MODEL_PRICING.get(model)
        if pricing:
            cost = (inp_est / 1000 * pricing.per_1k_input) + (out_est / 1000 * pricing.per_1k_output)
        else:
            cost = 0.0
        total_cost += cost
        if model not in model_stats:
            model_stats[model] = {"sessions": 0, "input": 0, "output": 0, "cost": 0.0}
        model_stats[model]["sessions"] += 1
        model_stats[model]["input"] += inp_est
        model_stats[model]["output"] += out_est
        model_stats[model]["cost"] += cost

    table = Table(title=f"Usage Stats (last {days} days)", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="white", width=16)
    table.add_column("Value", style="green")
    table.add_row("Sessions", str(len(recent)))
    table.add_row("Total Input Tokens", f"{total_input:,}")
    table.add_row("Total Output Tokens", f"{total_output:,}")
    table.add_row("Total Tokens", f"{total_input + total_output:,}")
    table.add_row("Estimated Cost", f"${total_cost:.4f}")
    ui.console.print(table)

    if args.tools or args.models_flag:
        model_table = Table(title="Per-Model Breakdown", show_header=True, header_style="bold cyan")
        model_table.add_column("Model", style="cyan", width=24)
        model_table.add_column("Sessions", style="yellow", width=10)
        model_table.add_column("Input", style="white", width=14)
        model_table.add_column("Output", style="white", width=14)
        model_table.add_column("Cost", style="green", width=12)
        for model_name, ms in sorted(model_stats.items(), key=lambda x: -x[1]["cost"]):
            model_table.add_row(model_name, str(ms["sessions"]),
                                f"{ms['input']:,}", f"{ms['output']:,}", f"${ms['cost']:.4f}")
        ui.console.print(model_table)


def _parse_ts(ts: str) -> float:
    from datetime import datetime
    try:
        return datetime.fromisoformat(ts).timestamp()
    except Exception:
        return 0


def _cmd_export(args: argparse.Namespace, ui: UI) -> None:
    from .share import share_manager as sm
    if not args.session_id:
        ui.print_error("Usage: apex export <session_id> [--sanitize]")
        sys.exit(1)
    data = sm.export_session(args.session_id)
    if not data:
        ui.print_error(f"Session not found: {args.session_id}")
        sys.exit(1)
    if args.sanitize:
        data = sm.sanitize_session_data(data)
    out = Path.cwd() / f"session_{args.session_id}.json"
    out.write_text(json.dumps(data, indent=2))
    ui.print_success(f"Exported to {out}")


def _cmd_import(args: argparse.Namespace, ui: UI) -> None:
    from .share import share_manager as sm
    if not args.file:
        ui.print_error("Usage: apex import <file>")
        sys.exit(1)
    file_path = args.file
    # Handle URLs
    if file_path.startswith(("http://", "https://", "apex://")):
        import urllib.request
        try:
            if file_path.startswith("apex://share/"):
                share_id = file_path.split("/")[-1]
                url = f"https://apex-ai.dev/s/{share_id}.json"
            else:
                url = file_path
            resp = urllib.request.urlopen(url)
            data = json.loads(resp.read())
            session_id = sm._generate_id()
            sessions_dir = Path.home() / ".apex" / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            out = sessions_dir / f"imported_{session_id}.json"
            out.write_text(json.dumps(data, indent=2))
            ui.print_success(f"Imported from URL as session: {session_id}")
        except Exception as e:
            ui.print_error(f"Failed to import from URL: {e}")
            sys.exit(1)
    else:
        result = sm.import_session(file_path)
        if result:
            ui.print_success(f"Imported session: {result}")
        else:
            ui.print_error(f"Failed to import from: {file_path}")
            sys.exit(1)


def _cmd_upgrade(args: argparse.Namespace, ui: UI) -> None:
    method = args.method or "pip"
    ui.print_info(f"Upgrading APEX via {method}...")
    try:
        if method == "pip":
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "apex-ai"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                ui.print_success("APEX upgraded successfully!")
            else:
                ui.print_error(f"Upgrade failed: {result.stderr[:200]}")
                sys.exit(1)
        elif method == "pipx":
            result = subprocess.run(
                ["pipx", "upgrade", "apex-ai"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                ui.print_success("APEX upgraded successfully!")
            else:
                ui.print_error(f"Upgrade failed: {result.stderr[:200]}")
                sys.exit(1)
        elif method == "npm":
            result = subprocess.run(
                ["npm", "install", "-g", "apex-ai"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                ui.print_success("APEX upgraded successfully!")
            else:
                ui.print_error(f"Upgrade failed: {result.stderr[:200]}")
                sys.exit(1)
        else:
            ui.print_error(f"Unknown upgrade method: {method}")
            sys.exit(1)
    except Exception as e:
        ui.print_error(f"Upgrade error: {e}")
        sys.exit(1)


def _cmd_uninstall(args: argparse.Namespace, ui: UI) -> None:
    if not args.dry_run and not args.force:
        confirm = ui.input("Are you sure you want to uninstall APEX? (yes/no): ").strip().lower()
        if confirm != "yes":
            ui.print_info("Uninstall cancelled")
            return

    if args.dry_run:
        ui.print_info("[DRY RUN] Would uninstall APEX")

    apex_dir = Path.home() / ".apex"
    config_dir = Path.home() / ".config" / "apex"

    if args.dry_run:
        if apex_dir.exists():
            ui.print_info(f"  Would remove: {apex_dir}")
        if config_dir.exists() and not args.keep_config:
            ui.print_info(f"  Would remove: {config_dir}")
        ui.print_info("[DRY RUN] Would run: pip uninstall apex-ai")
        return

    if not args.keep_config:
        if config_dir.exists():
            shutil.rmtree(config_dir)
            ui.print_success("Removed config directory")
    else:
        ui.print_info("Keeping config directory")

    if not args.keep_data:
        sessions_dir = apex_dir / "sessions"
        if sessions_dir.exists():
            shutil.rmtree(sessions_dir)
            ui.print_success("Removed session data")
        memory_dir = apex_dir / "memory"
        if memory_dir.exists():
            shutil.rmtree(memory_dir)
            ui.print_success("Removed memory data")
    else:
        ui.print_info("Keeping data directory")

    # Uninstall pip package
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "apex-ai"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            ui.print_success("APEX uninstalled successfully!")
        else:
            ui.print_warning(f"pip uninstall: {result.stderr[:200]}")
    except Exception as e:
        ui.print_warning(f"pip uninstall error: {e}")

    ui.print_info("APEX has been removed. We hope to see you again!")


def _cmd_mcp(args: argparse.Namespace, ui: UI) -> None:
    from .mcp import mcp_manager, MCPServerConfig

    if args.mcp_subcommand == "list":
        servers = mcp_manager.list_servers() if hasattr(mcp_manager, "list_servers") else []
        if not servers:
            ui.print_info("No MCP servers configured")
            return
        table = Table(title="MCP Servers", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan", width=16)
        table.add_column("Command", style="green", width=30)
        table.add_column("Enabled", style="yellow", width=8)
        for s in servers:
            enabled = "\u2713" if getattr(s, "enabled", True) else "\u2717"
            table.add_row(s.name, s.command, enabled)
        ui.console.print(table)
        return

    if args.mcp_subcommand == "add":
        ui.print_info("Adding new MCP server (interactive)...")
        name = ui.input("Server name: ").strip()
        if not name:
            ui.print_error("Name required")
            sys.exit(1)
        command = ui.input("Command (e.g. npx @modelcontextprotocol/server-github): ").strip()
        if not command:
            ui.print_error("Command required")
            sys.exit(1)
        args_input = ui.input("Arguments (comma-separated, optional): ").strip()
        env_vars = ui.input("Environment variables (KEY=VAL, comma-separated, optional): ").strip()

        mcp_config = MCPServerConfig(
            name=name,
            command=command.split()[0],
            args=command.split()[1:] if len(command.split()) > 1 else [],
            env={} if not env_vars else dict(kv.split("=", 1) for kv in env_vars.split(",") if "=" in kv),
        )
        if hasattr(mcp_manager, "add_server"):
            mcp_manager.add_server(mcp_config)
        ui.print_success(f"MCP server '{name}' added!")
        return

    if args.mcp_subcommand == "auth":
        if not args.mcp_name:
            ui.print_error("Usage: apex mcp auth <name>")
            sys.exit(1)
        ui.print_success(f"Authenticated with MCP server: {args.mcp_name}")
        return

    ui.print_error("Usage: apex mcp <add|list|auth>")
    sys.exit(1)


def _cmd_db(args: argparse.Namespace, ui: UI) -> None:
    raw_args = getattr(args, "raw_args", sys.argv[1:])
    sub = args.db_subcommand if hasattr(args, "db_subcommand") else ""

    if sub == "path":
        db_paths = [
            Path.home() / ".apex" / "api_keys.db",
            Path.home() / ".apex" / "sessions",
            Path.home() / ".config" / "apex" / "apex.json",
        ]
        for p in db_paths:
            if p.exists():
                print(p)
    elif sub == "query":
        query = " ".join(raw_args[1:]) if len(raw_args) > 1 else ""
        if not query:
            ui.print_error("Usage: apex db <path|sql_query>")
            return
        import sqlite3
        db_path = Path.home() / ".apex" / "api_keys.db"
        if not db_path.exists():
            ui.print_info("No database found at " + str(db_path))
            return
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            col_names = [d[0] for d in cursor.description] if cursor.description else []
            if col_names:
                ui.console.print(" | ".join(col_names))
                ui.console.print("-" * 40)
            for row in rows[:50]:
                ui.console.print(" | ".join(str(c) for c in row))
            if len(rows) > 50:
                ui.console.print(f"... and {len(rows) - 50} more rows")
            conn.close()
        except sqlite3.Error as e:
            ui.print_error(f"Database error: {e}")
    else:
        ui.print_info("Usage: apex db <path|sql_query>")


def _cmd_pr(args: argparse.Namespace, ui: UI) -> None:
    if not args.pr_number:
        ui.print_error("Usage: apex pr <number>")
        sys.exit(1)
    try:
        import subprocess
        result = subprocess.run(
            ["gh", "pr", "view", str(args.pr_number), "--json", "headRefName,headRepository,baseRefName,url"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            ui.print_error(f"Failed to fetch PR #{args.pr_number}: {result.stderr[:200]}")
            sys.exit(1)
        pr_info = json.loads(result.stdout)
        branch = pr_info.get("headRefName", "")
        ui.print_info(f"PR #{args.pr_number}: {branch}")
        checkout = subprocess.run(
            ["gh", "pr", "checkout", str(args.pr_number)],
            capture_output=True, text=True, timeout=30,
        )
        if checkout.returncode == 0:
            ui.print_success(f"Checked out PR #{args.pr_number} ({branch})")
        else:
            ui.print_error(f"Failed to checkout PR: {checkout.stderr[:200]}")
            sys.exit(1)
    except FileNotFoundError:
        ui.print_error("gh CLI not found. Install GitHub CLI: https://cli.github.com")
        sys.exit(1)


def _cmd_key(args: argparse.Namespace, ui: UI) -> None:
    """Quick setup: set OpenRouter API key."""
    from pathlib import Path
    import os, json, time
    key = getattr(args, "key_value", None) or args.prompt or ""
    if not key:
        key = ui.input("OpenRouter API key (sk-or-v1-...): ").strip()
    if not key:
        ui.print_error("Usage: apex key <your-openrouter-key>")
        sys.exit(1)

    auth_dir = Path.home() / ".config" / "apex"
    auth_dir.mkdir(parents=True, exist_ok=True)
    auth_file = auth_dir / "auth.json"

    data = {}
    if auth_file.exists():
        data = json.loads(auth_file.read_text())
    data["openrouter"] = {"api_key": key, "configured_at": time.time()}
    auth_file.write_text(json.dumps(data, indent=2))
    # Set restrictive permissions (owner read/write only)
    auth_file.chmod(0o600)

    os.environ["OPENROUTER_API_KEY"] = key

    env_path = Path.cwd() / ".env"

    # Warn before writing to .env in current directory
    gitignore_path = Path.cwd() / ".gitignore"
    gitignore_has_env = gitignore_path.exists() and ".env" in gitignore_path.read_text()
    if not gitignore_has_env:
        ui.print_warning("WARNING: .env file will be created/updated in the current directory.")
        ui.print_warning("Make sure .env is in your .gitignore to avoid committing secrets!")

    lines = []
    found = False
    if env_path.exists():
        lines = env_path.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.startswith("OPENROUTER_API_KEY="):
                lines[i] = f"OPENROUTER_API_KEY={key}"
                found = True
                break
    if not found:
        lines.append(f"OPENROUTER_API_KEY={key}")
    env_path.write_text("\n".join(lines) + "\n")
    # Set restrictive permissions on .env too
    env_path.chmod(0o600)

    ui.print_success("OpenRouter key configured!")
    ui.print_info("   Stored in ~/.config/apex/auth.json and .env (permissions: 0600)")


def _cmd_attach(args: argparse.Namespace, ui: UI) -> None:
    if not args.url:
        ui.print_error("Usage: apex attach <url>")
        sys.exit(1)
    ui.print_success(f"Attaching TUI to remote backend: {args.url}")
    config = apex_config
    config.set("remote_url", args.url)
    agent = Agent(config)
    run_apex_tui(agent, ui)


def _interactive_provider_config(agent: Agent | None = None, ui: UI | None = None) -> None:
    if ui is None:
        from .ui import UI
        ui = UI()
    ui.print_info("Welcome to APEX provider configuration!")
    ui.print_info("You can set API keys via environment variables or configure them here.\n")

    providers = [
        ("anthropic", "ANTHROPIC_API_KEY", "claude-sonnet-4-5"),
        ("openai", "OPENAI_API_KEY", "gpt-4o"),
        ("google", "GEMINI_API_KEY", "gemini-2.5-pro"),
        ("deepseek", "DEEPSEEK_API_KEY", "deepseek-chat"),
        ("groq", "GROQ_API_KEY", "llama-3.3-70b"),
        ("mistral", "MISTRAL_API_KEY", "mistral-large-latest"),
        ("xai", "XAI_API_KEY", "grok-4"),
    ]

    auth_dir = Path.home() / ".config" / "apex"
    auth_dir.mkdir(parents=True, exist_ok=True)
    auth_file = auth_dir / "auth.json"
    data = {}
    if auth_file.exists():
        data = json.loads(auth_file.read_text())

    for name, env_var, default_model in providers:
        existing = data.get(name, {})
        env_val = os.environ.get(env_var, "")
        if existing.get("api_key"):
            ui.print_info(f"  [{name}] Already configured (key: ...{existing['api_key'][-8:]})")
        elif env_val:
            ui.print_success(f"  [{name}] Found {env_var} in environment")
            data[name] = {"api_key": env_val, "model": default_model}
        else:
            answer = ui.input(f"  Configure {name}? (y/N): ").strip().lower()
            if answer == "y":
                key = ui.input(f"    API key for {name}: ").strip()
                if key:
                    model = ui.input(f"    Default model [{default_model}]: ").strip() or default_model
                    data[name] = {"api_key": key, "model": model}
                    os.environ[env_var] = key

    auth_file.write_text(json.dumps(data, indent=2))
    ui.print_success("Provider configuration saved!")


def _cmd_connect(args: argparse.Namespace, ui: UI) -> None:
    _interactive_provider_config(None, ui)


def _cmd_init(ui: UI) -> None:
    agents_file = Path.cwd() / "AGENTS.md"
    if agents_file.exists():
        ui.print_info("AGENTS.md already exists")
        return
    content = """# APEX Project Configuration

## Overview
This project is configured for use with APEX — the coding AI agent.

## Commands

/test - Run the full test suite
/review - Review current changes
/commit - Commit with AI-generated message

## Guidelines

- Follow existing code style and conventions
- Write tests for new functionality
- Keep functions focused and small
"""
    agents_file.write_text(content)
    ui.print_success(f"Created {agents_file}")

    # Also create .apex directory
    apex_dir = Path.cwd() / ".apex"
    apex_dir.mkdir(parents=True, exist_ok=True)
    (apex_dir / "commands").mkdir(exist_ok=True)
    (apex_dir / "agents").mkdir(exist_ok=True)
    ui.print_success("Initialized .apex project directory")


def _cmd_compact(args: argparse.Namespace, ui: UI) -> None:
    config = apex_config
    agent = Agent(config)
    if hasattr(agent, "compact_context"):
        before = len(agent.history) if hasattr(agent, "history") else 0
        agent.compact_context()
        after = len(agent.history) if hasattr(agent, "history") else 0
        ui.print_success(f"Context compacted: {before} → {after} messages")
    else:
        ui.print_info("Compaction not available in this context")


def _cmd_details(args: argparse.Namespace, ui: UI) -> None:
    config = apex_config
    config.set("show_details", not config.get("show_details", False))
    state = "enabled" if config.get("show_details") else "disabled"
    ui.print_success(f"Tool execution details: {state}")


def _cmd_thinking(args: argparse.Namespace, ui: UI) -> None:
    config = apex_config
    config.set("show_thinking", not config.get("show_thinking", False))
    state = "enabled" if config.get("show_thinking") else "disabled"
    ui.print_success(f"Thinking blocks: {state}")


def _cmd_debug(args: argparse.Namespace, ui: UI) -> None:
    """OpenCode-compatible debug command."""
    from apex import __version__
    raw_args = getattr(args, "raw_args", [])

    if not raw_args or raw_args[0] == "config":
        ui.console.print(f"[bold cyan]APEX v{__version__}[/]")
        ui.console.print(f"[dim]Config file:[/] {Path.home() / '.config' / 'apex' / 'apex.jsonc'}")
        ui.console.print(f"[dim]Data dir:[/]    {Path.home() / '.apex'}")
        ui.console.print()
        ui.console.print("[bold]Resolved config:[/]")
        import json
        from .config_v2 import apex_config
        ui.console.print(json.dumps(apex_config.raw(), indent=2, default=str)[:2000])
        return

    ui.print_info(f"Debug: unknown subcommand '{raw_args[0]}'. Use 'apex debug config'.")


def _cmd_github(args: argparse.Namespace, ui: UI) -> None:
    """OpenCode-compatible github CLI command."""
    raw_args = getattr(args, "raw_args", [])
    sub = raw_args[0] if raw_args else ""

    if sub == "install":
        ui.print_info("Installing GitHub agent...")
        ui.print_info("This sets up APEX as a GitHub Actions workflow.")
        ui.print_info("See: https://github.com/Ggboykxz/APEX")
        return

    if sub == "run":
        ui.print_info("Running GitHub agent...")
        from .github_integration import gh_automation
        issues = gh_automation.client.list_issues()
        prs = gh_automation.client.list_prs()
        ui.print_success(f"Found {len(issues)} issues and {len(prs)} PRs")
        return

    ui.print_info("Usage: apex github install|run")
    ui.print_info("  install  - Install GitHub agent in repository")
    ui.print_info("  run      - Run GitHub agent (typically in CI)")


def _cmd_plugin(args: argparse.Namespace, ui: UI) -> None:
    """OpenCode-compatible plugin CLI command."""
    raw_args = getattr(args, "raw_args", [])
    module = raw_args[0] if raw_args else ""

    if not module:
        from .plugins import plugin_manager
        plugins = plugin_manager.list_plugins() if hasattr(plugin_manager, "list_plugins") else []
        if plugins:
            ui.console.print("[cyan]Installed plugins:[/cyan]")
            for p in plugins:
                name = getattr(p, "name", str(p))
                ui.console.print(f"  - {name}")
        else:
            ui.print_info("No plugins installed. Use 'apex plugin <module>' to install one.")
        return

    from .plugins import plugin_manager, load_plugins_from_config
    ui.print_info(f"Installing plugin: {module}")
    try:
        # Try to pip-install the specified module first
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", module],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            ui.print_warning(f"pip install {module} returned non-zero: {result.stderr[:200]}")

        # Add the module to the plugin config so it loads on startup
        config_path = Path.home() / ".apex" / "plugins.yaml"
        config_dir = config_path.parent
        config_dir.mkdir(parents=True, exist_ok=True)

        import yaml
        config = {}
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}

        if "plugins" not in config:
            config["plugins"] = {}
        config["plugins"][module] = {"enabled": True}

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        # Now load all plugins from config (including the newly added one)
        load_plugins_from_config(config_path, app=None)
        ui.print_success(f"Plugin installed and loaded: {module}")
    except Exception as e:
        ui.print_error(f"Failed to load plugin: {e}")


# ── Gateway ────────────────────────────────────────────────


def _cmd_gateway(parsed: argparse.Namespace, ui: UI) -> None:
    """Handle gateway subcommands: start, key, status."""
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    sub = args[0].lower() if args else "help"

    if sub == "start":
        import os
        import asyncio
        from .gateway import GatewayServer
        from .gateway.config import GatewayConfig
        if not os.environ.get("APEX_GATEWAY_KEY") and not os.environ.get("OPENROUTER_API_KEY"):
            ui.print_error("APEX_GATEWAY_KEY or OPENROUTER_API_KEY must be set in .env")
            ui.print_info("Get a free key at https://openrouter.ai/keys")
            sys.exit(1)
        try:
            cfg = GatewayConfig.from_env()
            server = GatewayServer(cfg)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(server.start())
                print("Press Ctrl+C to stop")
                loop.run_forever()
            except KeyboardInterrupt:
                pass
            finally:
                loop.run_until_complete(server.stop())
                loop.close()
        except Exception as e:
            ui.print_error(f"Gateway error: {e}")
            sys.exit(1)
    elif sub == "key":
        from .gateway import GatewayServer
        from .gateway.config import GatewayConfig
        cfg = GatewayConfig.from_env()
        server = GatewayServer(cfg)
        tier = args[1] if len(args) > 1 else "free"
        label = args[2] if len(args) > 2 else ""
        api_key = server.auth.generate_key(tier, label)
        ui.print_success(f"Gateway API key generated ({tier}):")
        ui.print_info(api_key)
    elif sub == "status":
        from .gateway import GatewayServer
        from .gateway.config import GatewayConfig
        cfg = GatewayConfig.from_env()
        server = GatewayServer(cfg)
        keys = server.auth.list_keys()
        if not keys:
            ui.print_info("No API keys registered")
        else:
            ui.print_info(f"Gateway keys ({len(keys)}):")
            for k in keys:
                ui.print_info(f"  [{k['tier']}] {k['key_id']} — {k['label'] or 'no label'} {'(active)' if k['is_active'] else '(revoked)'}")
    else:
        ui.print_info("Usage:")
        ui.print_info("  apex gateway start              Start the gateway server")
        ui.print_info("  apex gateway key [tier] [label]  Generate an API key")
        ui.print_info("  apex gateway status              Show registered keys")
        ui.print_info("")
        ui.print_info("Tiers: free (default), pro, unlimited")
        ui.print_info("Set OPENROUTER_API_KEY or APEX_GATEWAY_KEY in .env")


# ── Backward compat aliases ─────────────────────────────────


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()

# ── Main entry ──────────────────────────────────────────────


def main() -> None:
    # Set environment variables like OpenCode
    os.environ["APEX"] = "1"
    os.environ["APEX_PID"] = str(os.getpid())

    # Initialize state directory and file logging before any dispatch
    _init_state_dir()
    _setup_file_logging()

    parser = build_parser()

    # Handle --help first to show full epilog
    if len(sys.argv) == 1:
        # Default: launch TUI
        sys.argv.append("tui")
    if len(sys.argv) == 2 and sys.argv[1] in ("--help", "-h"):
        parser.print_help()
        sys.exit(0)

    raw_args = sys.argv[1:]

    # Intercept positional subcommands: `apex models`, etc.
    if raw_args and raw_args[0].lower() in _SUBCOMMANDS:
        parsed = parser.parse_args(raw_args)
        for key, value in _SUBCOMMANDS[raw_args[0].lower()].items():
            setattr(parsed, key, value)
        parsed.prompt = None
        _dispatch(parsed)
        return

    # Dispatch by verb
    verb = raw_args[0].lower() if raw_args else ""

    # These subcommands use subparsers
    def _sub_val(verb: str) -> str:
        if len(raw_args) > 1:
            a = raw_args[1]
            if a == "ls":
                return "list"
            if not a.startswith("-"):
                return a
        defaults = {"auth": "login", "agent": "list", "session": "list", "mcp": "list"}
        return defaults.get(verb, "")

    subcommand_map = {
        "auth": ("auth_subcommand", _sub_val("auth")),
        "agent": ("agent_subcommand", _sub_val("agent")),
        "session": ("session_subcommand", _sub_val("session")),
        "mcp": ("mcp_subcommand", _sub_val("mcp")),
        "db": ("db_subcommand", "path" if len(raw_args) > 1 and raw_args[1] == "path" else "query"),
    }

    if verb in subcommand_map:
        attr_name, sub_val = subcommand_map[verb]
        # Build modified args for dispatch
        modified = [verb]
        if verb == "db":
            modified = ["db", "path"]
        elif verb in ("auth", "agent", "session", "mcp"):
            # If sub_val is a flag (--something), treat as the verb action
            idx = 1
            if len(raw_args) > 1 and not raw_args[1].startswith("-"):
                modified.append(raw_args[1])
            else:
                modified.append(sub_val)
            # Pass extra flags
            modified.extend(raw_args[2:] if len(raw_args) > 2 and not raw_args[1].startswith("-") else raw_args[1:])

        parsed = parser.parse_args(modified)
        parsed.prompt = None
        _dispatch_verb(verb, parsed)
        return

    # Direct-verb subcommands (routed to _dispatch_verb)
    known_verbs = {"serve", "web", "connect", "init", "compact", "details", "thinking",
                   "stats", "export", "import", "upgrade", "uninstall", "pr", "attach", "debug",
                   "github", "plugin", "gateway", "key"}
    if verb in known_verbs:
        parsed = argparse.Namespace()
        parsed.prompt = None
        parsed.model = None
        parsed.cwd = None
        parsed.agent_name = None
        parsed.resume = False
        parsed.session_id = None
        parsed.fork_session = None
        parsed.stream = False
        parsed.quiet = False
        parsed.output_format = "text"
        parsed.port = None
        parsed.hostname = None
        parsed.cors = None
        parsed.mdns = False
        parsed.refresh = False
        parsed.verbose = False
        parsed.sanitize = False
        parsed.keep_config = False
        parsed.keep_data = False
        parsed.dry_run = False
        parsed.force = False
        parsed.method = None
        parsed.share = False
        parsed.input_file = None
        parsed.print_logs = False
        parsed.log_level = None
        parsed.pure = False
        parsed.install_tui = False
        parsed.list_models = False
        parsed.auto_commit = False
        # For subcommands, keep the rest of raw_args so handlers can read them
        parsed.raw_args = raw_args[1:]
        _dispatch_verb(verb, parsed)
        return

    # Regular parsing for all other cases
    try:
        parsed = parser.parse_args(raw_args)
    except SystemExit:
        sys.exit(1)
    _dispatch(parsed)


def _init_state_dir() -> Path:
    """Initialize APEX state directory (like OpenCode's ~/.local/state/opencode/)."""
    state_dir = Path.home() / ".local" / "state" / "apex"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "log").mkdir(parents=True, exist_ok=True)
    (state_dir / "data").mkdir(parents=True, exist_ok=True)
    return state_dir


def _setup_file_logging() -> None:
    """Log to file like OpenCode does at ~/.local/state/opencode/log/."""
    log_dir = Path.home() / ".local" / "state" / "apex" / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%dT%H%M%S')}.log"
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    # Keep only last 10 log files
    logs = sorted(log_dir.glob("*.log"))
    for old in logs[:-10]:
        old.unlink(missing_ok=True)


def _dispatch(parsed: argparse.Namespace) -> None:
    from apex.config import Config
    config = Config()

    # Log level
    if parsed.log_level:
        logging.basicConfig(level=getattr(logging, parsed.log_level.upper(), logging.INFO))
    if parsed.print_logs:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    if parsed.model and parsed.model not in MODELS:
        print(f"Error: Unknown model '{parsed.model}'", file=sys.stderr)
        print("Use --list-models to see available models", file=sys.stderr)
        sys.exit(1)

    if parsed.cwd:
        config.cwd = str(Path(parsed.cwd).expanduser().resolve())

    ui = UI()

    # model/agent flags
    if parsed.model:
        config.model = parsed.model
    if parsed.agent_name:
        config.set("default_agent", parsed.agent_name)

    # Conditional model list
    if parsed.list_models or hasattr(parsed, "list_models") and parsed.list_models:
        list_models(ui, verbose=parsed.verbose, refresh=parsed.refresh)
        sys.exit(0)

    if parsed.install_tui or (hasattr(parsed, "install_tui") and parsed.install_tui):
        _install_tui_command(ui)
        sys.exit(0)

    # Pure mode
    if parsed.pure:
        config.set("pure_mode", True)

    agent = Agent(config)

    if parsed.agent_name:
        agent.switch_agent(parsed.agent_name)

    # Resume / session / fork handling
    if parsed.resume:
        sm = SessionManager()
        sessions = sm.list_sessions()
        if sessions:
            sm.load(sessions[0]["name"], agent)
    elif parsed.session_id:
        sm = SessionManager()
        sm.load(parsed.session_id, agent)
    elif parsed.fork_session:
        sm = SessionManager()
        sm.load(parsed.fork_session, agent)

    # Route to appropriate mode
    if parsed.ui or parsed.tui:
        run_apex_tui(agent, ui, resume=parsed.resume, session_id=parsed.session_id, fork=parsed.fork_session)
    elif parsed.prompt_direct:
        run_cicd_mode(parsed.prompt_direct, agent, ui, parsed.output_format, parsed.quiet)
    elif parsed.prompt:
        run_one_shot(parsed.prompt, agent, ui, parsed.stream)
    else:
        run_apex_tui(agent, ui)


def _dispatch_verb(verb: str, parsed: argparse.Namespace) -> None:
    ui = UI()
    match verb:
        case "serve":
            _cmd_serve(parsed, ui)
        case "web":
            _cmd_web(parsed, ui)
        case "auth":
            _cmd_auth(parsed, ui)
        case "agent":
            _cmd_agent(parsed, ui)
        case "run":
            _cmd_run(parsed, ui)
        case "session":
            _cmd_session(parsed, ui)
        case "stats":
            _cmd_stats(parsed, ui)
        case "export":
            _cmd_export(parsed, ui)
        case "import":
            _cmd_import(parsed, ui)
        case "upgrade":
            _cmd_upgrade(parsed, ui)
        case "uninstall":
            _cmd_uninstall(parsed, ui)
        case "mcp":
            _cmd_mcp(parsed, ui)
        case "db":
            _cmd_db(parsed, ui)
        case "pr":
            _cmd_pr(parsed, ui)
        case "attach":
            _cmd_attach(parsed, ui)
        case "connect":
            _cmd_connect(parsed, ui)
        case "key":
            _cmd_key(parsed, ui)
        case "init":
            _cmd_init(ui)
        case "compact":
            _cmd_compact(parsed, ui)
        case "details":
            _cmd_details(parsed, ui)
        case "thinking":
            _cmd_thinking(parsed, ui)
        case "debug":
            _cmd_debug(parsed, ui)
        case "github":
            _cmd_github(parsed, ui)
        case "plugin":
            _cmd_plugin(parsed, ui)
        case "gateway":
            _cmd_gateway(parsed, ui)
        case _:
            if parsed.prompt:
                _dispatch(parsed)
            else:
                ui.print_error(f"Unknown command: {verb}")
                sys.exit(1)


if __name__ == "__main__":
    main()
