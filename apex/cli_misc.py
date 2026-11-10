"""Assorted top-level commands (agents, one-shot runs, GitHub, toggles)."""

import argparse
import json
import sys
from pathlib import Path

from rich.table import Table

from .agent import Agent
from .agents import agent_manager
from .config_v2 import apex_config
from .session import SessionManager
from .ui import UI


def _list_agents(ui: UI) -> None:
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
        table.add_row(a.name, a.mode, a.model or "default", a.description)
    ui.console.print(table)


def _agent_definition(name: str, spec: dict) -> str:
    desc, mode, model, perms = spec["desc"], spec["mode"], spec["model"], spec["perms"]
    return f"""---
description: {desc}
mode: {mode}
model: {model or ""}
permission:
  read: {perms["read"]}
  edit: {perms["edit"]}
  bash: {perms["bash"]}
---

You are the {name} agent for APEX.

{desc}

Your role:
- Analyze code and provide expert insights
- Follow best practices for the task at hand
- Be thorough and precise in all your work
"""


def _create_agent(ui: UI) -> None:
    ui.print_info("Creating new agent (interactive wizard)...")
    name = ui.input("Agent name: ").strip()
    if not name:
        ui.print_error("Name required")
        sys.exit(1)
    desc = ui.input("Description: ").strip()
    mode = ui.input("Mode (primary/subagent) [subagent]: ").strip() or "subagent"
    model = ui.input("Model (leave empty for default): ").strip() or None
    perms = {
        "read": ui.input("Read permission (allow/ask/deny) [allow]: ").strip() or "allow",
        "edit": ui.input("Edit permission (allow/ask/deny) [ask]: ").strip() or "ask",
        "bash": ui.input("Bash permission (allow/ask/deny) [ask]: ").strip() or "ask",
    }
    agent_dir = Path.home() / ".config" / "apex" / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_file = agent_dir / f"{name}.md"
    agent_file.write_text(
        _agent_definition(name, {"desc": desc, "mode": mode, "model": model, "perms": perms})
    )
    agent_manager.load_markdown_agents()
    ui.print_success(f"Agent '{name}' created at {agent_file}")


def _cmd_agent(args: argparse.Namespace, ui: UI) -> None:
    if args.agent_subcommand == "list":
        _list_agents(ui)
        return
    if args.agent_subcommand == "create":
        _create_agent(ui)
        return
    ui.print_error("Usage: apex agent <create|list>")
    sys.exit(1)


def _build_run_agent(args: argparse.Namespace) -> Agent:
    config = apex_config
    if args.model:
        config.model = args.model
    if args.agent_name:
        config.set("default_agent", args.agent_name)
    agent = Agent(config)
    if args.agent_name:
        agent.switch_agent(args.agent_name)
    return agent


def _load_run_session(args: argparse.Namespace, agent: Agent) -> None:
    if args.resume:
        sm = SessionManager()
        sessions = sm.list_sessions()
        if sessions:
            sm.load(sessions[0]["name"], agent)
    elif args.session_id:
        SessionManager().load(args.session_id, agent)


def _resolve_run_prompt(args: argparse.Namespace, ui: UI) -> str:
    prompt = args.prompt
    if args.input_file:
        prompt = Path(args.input_file).read_text().strip()
    if not prompt:
        ui.print_error("No prompt provided. Usage: apex run <prompt>")
        sys.exit(1)
    return prompt


def _run_json(prompt: str, agent: Agent) -> None:
    try:
        response = agent.chat(prompt)
        result = {
            "success": True,
            "prompt": prompt,
            "response": response,
            "model": agent.model,
            "usage": agent.usage,
        }
        print(json.dumps(result, indent=2))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        sys.exit(1)


def _cmd_run(args: argparse.Namespace, ui: UI) -> None:
    agent = _build_run_agent(args)
    _load_run_session(args, agent)
    prompt = _resolve_run_prompt(args, ui)
    if args.output_format == "json":
        _run_json(prompt, agent)
        return
    from .main import OneShotOptions, run_one_shot

    run_one_shot(prompt, agent, ui, OneShotOptions(use_stream=args.stream))


def _cmd_pr(args: argparse.Namespace, ui: UI) -> None:
    if not args.pr_number:
        ui.print_error("Usage: apex pr <number>")
        sys.exit(1)
    try:
        import subprocess

        result = subprocess.run(
            [
                "gh",
                "pr",
                "view",
                str(args.pr_number),
                "--json",
                "headRefName,headRepository,baseRefName,url",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            ui.print_error(f"Failed to fetch PR #{args.pr_number}: {result.stderr[:200]}")
            sys.exit(1)
        pr_info = json.loads(result.stdout)
        branch = pr_info.get("headRefName", "")
        ui.print_info(f"PR #{args.pr_number}: {branch}")
        checkout = subprocess.run(
            ["gh", "pr", "checkout", str(args.pr_number)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if checkout.returncode == 0:
            ui.print_success(f"Checked out PR #{args.pr_number} ({branch})")
        else:
            ui.print_error(f"Failed to checkout PR: {checkout.stderr[:200]}")
            sys.exit(1)
    except FileNotFoundError:
        ui.print_error("gh CLI not found. Install GitHub CLI: https://cli.github.com")
        sys.exit(1)


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
