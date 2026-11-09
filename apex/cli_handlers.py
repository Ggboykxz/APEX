"""Slash-command handlers used by the interactive REPL.

`handle_command` resolves a slash command to a handler and returns True when it
was handled. Handlers keep their module-level imports local where the target
module is optional or expensive to import.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.panel import Panel
from rich.table import Table

from .agent import Agent
from .agents import agent_manager
from .commands_manager import commands_manager
from .config_v2 import apex_config
from .context import get_language_stats, get_repo_map
from .memory import Memory
from .session import SessionManager
from .ui import UI

memory = Memory()


# -- Slash command handlers -------------------------------------------------
# Each handler receives (arg, agent, ui, config) and returns True when handled.


def _handle_model(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
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


def _handle_models(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    ui.show_models(agent.model)
    return True


def _handle_reasoning(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    level = agent.cycle_reasoning_effort()
    ui.print_success(f"Reasoning effort: {level}")
    return True


def _handle_thinking(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    agent.show_thinking = not getattr(agent, "show_thinking", False)
    state = "enabled" if agent.show_thinking else "disabled"
    ui.print_success(f"Thinking blocks: {state}")
    return True


def _handle_details(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    agent.show_details = not getattr(agent, "show_details", False)
    state = "enabled" if agent.show_details else "disabled"
    ui.print_success(f"Tool execution details: {state}")
    return True


def _handle_cwd(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
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


def _handle_clear(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    agent.reset_history()
    ui.print_success("Conversation history cleared")
    return True


def _handle_compact(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    before = len(agent.history) if hasattr(agent, "history") else 0
    agent.compact_context()
    after = len(agent.history) if hasattr(agent, "history") else 0
    ui.print_success(f"Context compacted: {before} \u00e2\u2020\u2019 {after} messages")
    return True


def _handle_history(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    if not agent.history:
        ui.print_info("No conversation history")
        return True
    ui.console.print("[cyan]Conversation history:[/cyan]")
    for msg in agent.history[-10:]:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if content:
            truncated = content[:100] + "..." if len(content) > 100 else content
            ui.console.print(f"  [{role}]: {truncated}")
    return True


def _handle_save(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    sm = SessionManager()
    name = arg or "default"
    sm.save(agent, name)
    ui.print_success(f"Session saved as: {name}")
    return True


def _handle_load(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
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


def _handle_sessions(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
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


def _handle_export(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
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


def _handle_cost(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
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


def _print_memory_facts(ui: UI) -> None:
    facts = memory.get_all()
    if not facts:
        ui.print_info("No memory facts stored")
        return
    ui.console.print("[cyan]Memory facts:[/cyan]")
    for i, f in enumerate(facts):
        relevance = ", ".join(f.get("relevance", []))
        ui.console.print(f"  {i}: {f['fact']} [relevance: {relevance}]")


def _search_memory(query: str, ui: UI) -> None:
    results = memory.search(query)
    if not results:
        ui.print_info("No matching facts found")
        return
    ui.console.print("[cyan]Search results:[/cyan]")
    for f in results:
        ui.console.print(f"  \u2022 {f['fact']}")


def _memory_subcommand(parts: list[str], ui: UI) -> None:
    subcmd = parts[0]
    if subcmd == "add" and len(parts) >= 3:
        fact = parts[1].strip()
        relevance = [r.strip() for r in parts[2].split(",")]
        memory.add(fact, relevance)
        ui.print_success(f"Added to memory: {fact}")
    elif subcmd == "clear":
        memory.clear()
        ui.print_success("Memory cleared")
    elif subcmd == "search" and len(parts) >= 2:
        _search_memory(parts[1], ui)
    else:
        ui.print_info("Usage: /memory [add <fact> <relevance>|clear|search <query>]")


def _handle_memory(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    if not arg:
        _print_memory_facts(ui)
        return True
    _memory_subcommand(arg.split(maxsplit=2), ui)
    return True


def _handle_map(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    repo_map = get_repo_map(agent.cwd)
    ui.console.print(Panel(repo_map, title="[cyan]Repository Map[/cyan]", border_style="cyan"))
    return True


def _handle_stats(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    stats = get_language_stats(agent.cwd)
    if stats:
        ui.console.print("[cyan]Language stats:[/cyan]")
        for lang, count in sorted(stats.items(), key=lambda x: -x[1]):
            ui.console.print(f"  {lang}: {count} files")
    else:
        ui.print_info("No source files found")
    return True


def _handle_git(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    from .tools import ToolExecutor

    executor = ToolExecutor(cwd=agent.cwd)
    status = executor.execute("get_git_status", {})
    ui.console.print(Panel(status, title="[cyan]Git Status[/cyan]", border_style="cyan"))
    return True


def _handle_agent(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
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


def _handle_build(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    agent.switch_agent("build")
    config.set("agent_mode", "agent")
    ui.print_success("Build mode enabled \u00e2\u20ac\u201d full access")
    return True


def _handle_plan(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    agent.switch_agent("plan")
    config.set("agent_mode", "plan")
    ui.print_success("Plan mode enabled \u00e2\u20ac\u201d read-only analysis")
    return True


def _handle_planner(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    agent.switch_agent("planner")
    config.set("agent_mode", "plan")
    ui.print_success(
        "Planner mode enabled \u00e2\u20ac\u201d read-only planning without delegation"
    )
    return True


def _handle_coder(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    agent.switch_agent("build")
    config.set("agent_mode", "agent")
    ui.print_success("Build mode enabled \u00e2\u20ac\u201d full access")
    return True


def _handle_architect(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    agent.switch_agent("plan")
    config.set("agent_mode", "plan")
    ui.print_success("Plan mode enabled \u00e2\u20ac\u201d read-only analysis")
    return True


def _restore_snapshot(arg: str, wb, ui: UI) -> None:
    if wb.restore_snapshot(arg):
        ui.print_success(f"Restored snapshot: {arg}")
    else:
        ui.print_error(f"Failed to restore: {arg}")


def _print_snapshots(wb, ui: UI) -> None:
    snapshots = wb.list_snapshots()
    if not snapshots:
        ui.print_info("No snapshots available")
        return
    ui.console.print("[cyan]Available snapshots:[/cyan]")
    for s in snapshots[-10:]:
        ui.console.print(f"  {s['name']} - {s.get('label', '')}")


def _handle_restore(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    from .workspace_rollback import WorkspaceRollback

    wb = WorkspaceRollback(agent.cwd)
    if arg:
        _restore_snapshot(arg, wb, ui)
    else:
        _print_snapshots(wb, ui)
    return True


def _handle_revert(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    from .workspace_rollback import TurnTracker

    tt = TurnTracker(agent.cwd)
    turns = int(arg) if arg.isdigit() else 1
    if tt.revert_turn(turns):
        ui.print_success(f"Reverted {turns} turn(s)")
    else:
        ui.print_error("Failed to revert turn")
    return True


def _handle_undo(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
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


def _handle_redo(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
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


def _handle_skills(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    from .skills_system import skills_manager

    skills = skills_manager.list_skills()
    if skills:
        ui.console.print("[cyan]Available skills:[/cyan]")
        for s in skills:
            ui.console.print(f"  {s['name']} - {s['description']}")
    else:
        ui.print_info("No skills available")
    return True


def _print_github_issues(client, ui: UI) -> None:
    for issue in client.list_issues():
        ui.console.print(f"  #{issue.get('number')}: {issue.get('title')}")


def _print_github_prs(client, ui: UI) -> None:
    for pr in client.list_prs():
        ui.console.print(f"  PR #{pr.get('number')}: {pr.get('title')}")


def _handle_github(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    from .github_integration import gh_automation

    if not arg:
        ui.print_info("Usage: /github <command> [args]")
        ui.print_info("Commands: issues, prs, create-issue, create-pr")
        return True
    gcmd = arg.split(maxsplit=1)[0]
    if gcmd == "issues":
        _print_github_issues(gh_automation.client, ui)
    elif gcmd == "prs":
        _print_github_prs(gh_automation.client, ui)
    else:
        ui.print_error(f"Unknown github command: {gcmd}")
    return True


def _handle_local(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
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


def _handle_sessionsave(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    sm = SessionManager()
    name = arg or "default"
    path = sm.save(agent, name)
    ui.print_success(f"Session saved: {path}")
    return True


def _load_named_session(arg: str, agent: Agent, ui: UI) -> None:
    if SessionManager().load(arg, agent):
        ui.print_success(f"Loaded session: {arg}")
    else:
        ui.print_error(f"Session not found: {arg}")


def _handle_sessionload(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    if arg:
        _load_named_session(arg, agent, ui)
        return True
    ui.console.print("[cyan]Saved sessions:[/cyan]")
    for s in SessionManager().list_sessions():
        ui.console.print(f"  {s['name']} - {s['timestamp']}")
    return True


def _handle_tasks(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
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


def _handle_http(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    if arg == "start":
        ui.print_info("Starting HTTP API server...")
    else:
        ui.print_info("Usage: /http start - Start HTTP API server")
    return True


def _handle_agents(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
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


def _handle_subagents(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    table = Table(
        title="Subagents (use @name to invoke)", show_header=True, header_style="bold cyan"
    )
    table.add_column("Name", style="cyan", width=12)
    table.add_column("Description", style="white")
    for a in agent_manager.list_agents("subagent"):
        table.add_row(a.name, a.description)
    ui.console.print(table)
    return True


def _handle_connect(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    from .main import _interactive_provider_config

    _interactive_provider_config(agent, ui)
    return True


def _handle_key(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    from .main import _cmd_key

    _cmd_key(
        argparse.Namespace(key_value=arg, model=None, auth_subcommand=None, auth_provider=None),
        ui,
    )
    return True


def _handle_init(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    from .main import _cmd_init

    _cmd_init(ui)
    return True


def _switch_theme(arg: str, theme_manager, ui: UI) -> None:
    if theme_manager.set(arg):
        ui.print_success(f"Theme switched to: {arg}")
    else:
        ui.print_error(f"Unknown theme: {arg}")


def _handle_themes(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    from .theme_manager import theme_manager

    table = Table(title="Available Themes", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan", width=16)
    table.add_column("Description", style="white")
    current = theme_manager.current()
    for t in theme_manager.list():
        marker = "\u2713" if t["name"] == current else ""
        table.add_row(f"{t['name']} {marker}", t.get("description", ""))
    ui.console.print(table)
    if arg:
        _switch_theme(arg, theme_manager, ui)
    return True


def _handle_editor(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    import tempfile

    editor = os.environ.get("EDITOR", "vim")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as prompt_file:
        prompt_file.write("# Enter your prompt\n\n")
    try:
        subprocess.call([editor, prompt_file.name])
        content = Path(prompt_file.name).read_text()
        lines = [line for line in content.split("\n") if not line.startswith("#")]
        prompt = "\n".join(lines).strip()
        if prompt:
            ui.print_user(prompt)
            with ui.console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
                response = agent.chat(prompt)
            ui.print_response(response)
    finally:
        os.unlink(prompt_file.name)
    return True


def _handle_share(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    from .share import share_manager as sm

    share_id = arg or str(int(time.time()))
    url = sm.share_session(share_id)
    if url:
        ui.print_success(f"Session shared: {url}")
    else:
        ui.print_error("Failed to share session")
    return True


def _handle_unshare(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    from .share import share_manager as sm

    if not arg:
        ui.print_error("Usage: /unshare <share_id>")
        return True
    if sm.unshare_session(arg):
        ui.print_success(f"Session unshared: {arg}")
    else:
        ui.print_error(f"Share not found: {arg}")
    return True


def _handle_help(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    ui.show_help()
    return True


def _handle_exit(arg: str, agent: Agent, ui: UI, config: Any) -> bool:
    ui.print_info("Goodbye!")
    sys.exit(0)


CommandHandler = Callable[[str, Agent, UI, Any], bool]

COMMAND_DISPATCH: dict[str, CommandHandler] = {
    "model": _handle_model,
    "models": _handle_models,
    "reasoning": _handle_reasoning,
    "reason": _handle_reasoning,
    "thinking": _handle_thinking,
    "details": _handle_details,
    "cwd": _handle_cwd,
    "clear": _handle_clear,
    "new": _handle_clear,
    "compact": _handle_compact,
    "summarize": _handle_compact,
    "history": _handle_history,
    "save": _handle_save,
    "load": _handle_load,
    "sessions": _handle_sessions,
    "resume": _handle_sessions,
    "continue": _handle_sessions,
    "export": _handle_export,
    "cost": _handle_cost,
    "memory": _handle_memory,
    "map": _handle_map,
    "stats": _handle_stats,
    "git": _handle_git,
    "agent": _handle_agent,
    "build": _handle_build,
    "plan": _handle_plan,
    "planner": _handle_planner,
    "coder": _handle_coder,
    "architect": _handle_architect,
    "restore": _handle_restore,
    "revert": _handle_revert,
    "undo": _handle_undo,
    "redo": _handle_redo,
    "skills": _handle_skills,
    "github": _handle_github,
    "local": _handle_local,
    "sessionsave": _handle_sessionsave,
    "sessionload": _handle_sessionload,
    "tasks": _handle_tasks,
    "http": _handle_http,
    "agents": _handle_agents,
    "subagents": _handle_subagents,
    "connect": _handle_connect,
    "key": _handle_key,
    "init": _handle_init,
    "themes": _handle_themes,
    "editor": _handle_editor,
    "share": _handle_share,
    "unshare": _handle_unshare,
    "help": _handle_help,
    "exit": _handle_exit,
    "quit": _handle_exit,
    "q": _handle_exit,
}


def handle_command(
    command: str,
    agent: Agent,
    ui: UI,
    config: Any = None,
) -> bool:
    """Dispatch a slash command to its handler.

    Returns True when the command was handled (including unknown slash
    commands, which print an error), False when the input is not a command.
    """
    config = config or apex_config
    parts = command.split(maxsplit=1)
    raw = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    name = raw.removeprefix("/")

    handler = COMMAND_DISPATCH.get(name)
    if handler is not None:
        return handler(arg, agent, ui, config)

    if raw.startswith("/"):
        custom = commands_manager.get(name)
        if custom:
            response = commands_manager.execute(name, [arg] if arg else [], agent)
            ui.print_response(response)
            return True
        ui.print_error(f"Unknown command: {raw}. Type /help for commands.")
        return True
    return False
