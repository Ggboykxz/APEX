"""APEX CLI entry point â€” full OpenCode-like command suite.

Usage:
    apex [prompt]                  One-shot prompt
    apex [subcommand] [args...]    Run subcommand
    apex                           Launch TUI (default)
"""

import argparse
import json
import logging
import os
import sys
import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.table import Table

from . import __version__
from .agent import Agent
from .auto_commit import auto_commit
from .cli_auth import (  # noqa: F401 - re-exported
    _auth_file,
    _auth_list,
    _auth_login,
    _auth_logout,
    _cmd_auth,
    _cmd_connect,
    _cmd_key,
    _configure_openrouter,
    _interactive_provider_config,
    _persist_openrouter_env,
    _read_auth,
)
from .cli_handlers import handle_command, memory  # noqa: F401 - re-exported
from .cli_maint import (  # noqa: F401 - re-exported
    _cmd_init,
    _cmd_uninstall,
    _cmd_upgrade,
)
from .cli_misc import (  # noqa: F401 - re-exported
    _cmd_agent,
    _cmd_details,
    _cmd_github,
    _cmd_pr,
    _cmd_run,
    _cmd_thinking,
)
from .cli_server import (  # noqa: F401 - re-exported
    _cmd_attach,
    _cmd_debug,
    _cmd_gateway,
    _cmd_mcp,
    _cmd_plugin,
    _cmd_serve,
    _cmd_web,
)
from .cli_sessions import (  # noqa: F401 - re-exported
    _cmd_compact,
    _cmd_db,
    _cmd_export,
    _cmd_import,
    _cmd_session,
    _cmd_stats,
    _parse_ts,
)
from .config import MODELS
from .config_v2 import apex_config
from .session import SessionManager
from .tui_launcher import (  # noqa: F401 - re-exported
    _clone_tui_frontend,
    _download_tui_frontend,
    _ensure_bun,
    _ensure_tsx,
    _ensure_tui_frontend,
    _extract_tui_frontend,
    _find_bun,
    _find_free_port,
    _find_node,
    _find_npx,
    _find_tui_dir,
    _install_bun,
    _install_tsx,
    _install_tui_command,
    _patch_tui_package_json,
    _setup_tui_frontend,
    _try_run_tui_process,
    run_apex_tui,
)
from .ui import UI

logger = logging.getLogger("apex")

_SUBCOMMANDS: dict[str, dict[str, bool]] = {
    "tui": {"tui": True},
    "ui": {"tui": True},
    "models": {"list_models": True},
    "install-tui": {"install_tui": True},
}


# â”€â”€ Argument parser â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


_PARSER_EPILOG = textwrap.dedent(r"""\            subcommands:
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
              mcp serve         Expose tools over MCP stdio (read-only by default)
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
""")


def _add_core_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prompt", nargs="?", default=None, help="One-shot prompt to execute")
    parser.add_argument("--model", "-m", dest="model", default=None, help="Model alias to use")
    parser.add_argument("--cwd", "-C", dest="cwd", default=None, help="Working directory")
    parser.add_argument(
        "--allow-tool",
        dest="allow_tool",
        action="append",
        default=None,
        help="Expose a tool on the MCP server (repeatable; replaces the read-only default profile)",
    )
    parser.add_argument("--version", "-v", action="version", version=f"APEX {__version__}")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    parser.add_argument("--one-shot", "-1", action="store_true", help="One-shot mode")
    parser.add_argument("--stream", "-s", action="store_true", help="Streaming responses")
    parser.add_argument(
        "--auto-commit", action="store_true", dest="auto_commit", help="Auto commit after task"
    )
    parser.add_argument(
        "--image",
        "-i",
        dest="image",
        action="append",
        default=None,
        help="Attach a local image to the prompt (repeatable; vision-capable models only)",
    )
    parser.add_argument("--ui", action="store_true", help="Launch TUI")
    parser.add_argument("--tui", "-t", action="store_true", help="Launch TUI")
    parser.add_argument("-p", dest="prompt_direct", default=None, help="Direct prompt (CI/CD)")
    parser.add_argument(
        "-f",
        "--format",
        dest="output_format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode")
    parser.add_argument("--install-tui", action="store_true", help="Install TUI dependencies")


def _add_session_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--continue", dest="resume", action="store_true", help="Resume last session"
    )
    parser.add_argument("--session", dest="session_id", default=None, help="Session ID to load")
    parser.add_argument("--fork", dest="fork_session", default=None, help="Fork session")
    parser.add_argument("--agent", dest="agent_name", default=None, help="Agent to use")
    parser.add_argument("--print-logs", action="store_true", help="Print logs to stdout")
    parser.add_argument("--log-level", dest="log_level", default=None, help="Log level")
    parser.add_argument("--pure", action="store_true", help="Pure mode (no tools)")


def _add_utility_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--share", action="store_true", help="Share session")
    parser.add_argument("--file", dest="input_file", default=None, help="Read prompt from file")


def _add_server_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--port", type=int, default=None, help="Server port")
    parser.add_argument("--hostname", default=None, help="Server hostname")
    parser.add_argument("--cors", default=None, help="CORS origin")
    parser.add_argument("--mdns", action="store_true", help="Enable mDNS advertisement")


def _add_stats_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--refresh", action="store_true", help="Refresh model list")
    parser.add_argument("--verbose", action="store_true", help="Verbose output (show costs)")
    parser.add_argument("--days", type=int, default=None, help="Days for stats")
    parser.add_argument("--tools", action="store_true", help="Tool stats breakdown")
    parser.add_argument(
        "--models-flag", action="store_true", dest="models_flag", help="Model stats"
    )
    parser.add_argument("--project", default=None, help="Project path for stats")


def _add_install_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--sanitize", action="store_true", help="Sanitize export")
    parser.add_argument("--keep-config", action="store_true", help="Keep config on uninstall")
    parser.add_argument("--keep-data", action="store_true", help="Keep data on uninstall")
    parser.add_argument("--dry-run", action="store_true", help="Dry run uninstall")
    parser.add_argument("--force", action="store_true", help="Force uninstall")
    parser.add_argument("--method", default=None, help="Upgrade method (npm, native)")
    parser.add_argument(
        "--check", action="store_true", help="Check for a newer release without upgrading"
    )
    parser.add_argument(
        "--purge", action="store_true", help="Remove credentials and config on uninstall"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apex",
        description="APEX â€” The last coding agent you'll ever need",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_PARSER_EPILOG,
    )

    _add_core_args(parser)
    _add_session_args(parser)
    _add_utility_args(parser)
    _add_server_args(parser)
    _add_stats_args(parser)
    _add_install_args(parser)

    return parser


# â”€â”€ Model listing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def _matches_provider_filter(alias: str, model_id: str, provider_filter: str | None) -> bool:
    if not provider_filter:
        return True
    needle = provider_filter.lower()
    return needle in alias.lower() or needle in model_id.lower()


def _build_model_row(
    alias: str, model_id: str, config_model: str, verbose: bool
) -> tuple[str, str, str, str, str]:
    from .cost_local import MODEL_PRICING

    provider = alias.split("-")[0] if "-" in alias else "unknown"
    marker = "âœ“" if alias == config_model else " "
    pricing = MODEL_PRICING.get(alias)
    inp = f"${pricing.per_1k_input:.6f}" if pricing and verbose else ""
    out = f"${pricing.per_1k_output:.6f}" if pricing and verbose else ""
    return (f"{marker} {alias}", provider, model_id, inp, out)


def list_models(
    ui: UI, provider_filter: str | None = None, verbose: bool = False, refresh: bool = False
) -> None:
    if refresh:
        ui.print_success("Refreshing model list...")
    table = Table(
        title="Available Models" if not verbose else "Available Models (with pricing)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Alias", style="cyan", width=22)
    table.add_column("Provider", style="white", width=14)
    table.add_column("Model ID", style="green", width=40)
    if verbose:
        table.add_column("Input $/1K", style="yellow", width=12)
        table.add_column("Output $/1K", style="yellow", width=12)

    config_model = apex_config.model
    for alias, model_id in sorted(MODELS.items()):
        if not _matches_provider_filter(alias, model_id, provider_filter):
            continue
        table.add_row(*_build_model_row(alias, model_id, config_model, verbose))
    ui.console.print(table)


# â”€â”€ Slash commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


# Slash-command handlers and their dispatch table live in
# apex/cli_handlers.py; handle_command is re-exported here for callers.


# â”€â”€ REPL / Streaming â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


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
            if not user_input.strip() or not user_input.startswith("/"):
                continue
            if handle_command(user_input, agent, ui, apex_config):
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


@dataclass(frozen=True)
class OneShotOptions:
    """Options for a one-shot run."""

    use_stream: bool = False
    images: list[str] | None = None
    auto_commit_after: bool = False


def run_one_shot(
    prompt: str,
    agent: Agent,
    ui: UI,
    options: OneShotOptions | None = None,
) -> None:
    opts = options or OneShotOptions()
    if opts.use_stream:
        ui.console.print("[cyan]Streaming response:[/cyan]")
        for chunk in agent.chat(prompt, images=opts.images):
            ui.console.print(chunk, end="")
        ui.console.print()
    else:
        with ui.console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
            response = agent.chat(prompt, images=opts.images)
        ui.print_response(response)
    if opts.auto_commit_after:
        _run_auto_commit(agent, prompt, ui)


def _run_auto_commit(agent: Agent, task: str, ui: UI, quiet: bool = False) -> dict[str, Any]:
    """Commit working-tree changes after a one-shot task and report the outcome."""
    result = auto_commit(agent.cwd, task=task)
    status = result.get("status")
    if status == "committed":
        ui.print_info(f"Auto-committed {result.get('sha', '')[:7]}: {result.get('message', '')}")
    elif status == "no-changes" and not quiet:
        ui.print_info("Auto-commit: no changes to commit")
    elif status == "not-a-repo" and not quiet:
        ui.print_info("Auto-commit skipped: not a git repository")
    elif status != "no-changes" and status != "not-a-repo":
        ui.print_error(f"Auto-commit failed: {result.get('error', 'unknown error')}")
    return result


@dataclass(frozen=True)
class CicdOptions:
    """Options for CI/CD mode."""

    output_format: str = "text"
    quiet: bool = False
    images: list[str] | None = None
    auto_commit_after: bool = False


def _cicd_status(ui: UI, quiet: bool):
    return (
        ui.console.status("[cyan]Processing...[/cyan]", spinner="dots")
        if not quiet
        else ui.console.status("")
    )


def _cicd_json_result(
    prompt: str, response: str, agent: Agent, auto_commit_result: dict | None
) -> dict:
    result = {
        "success": True,
        "prompt": prompt,
        "response": response,
        "model": agent.model,
        "usage": agent.usage,
    }
    if auto_commit_result is not None:
        result["auto_commit"] = auto_commit_result
    return result


def _print_cicd_output(ui: UI, response: str, quiet: bool) -> None:
    if not quiet:
        ui.print_response(response)
    else:
        print(response)


def run_cicd_mode(
    prompt: str,
    agent: Agent,
    ui: UI,
    options: CicdOptions | None = None,
) -> None:
    opts = options or CicdOptions()
    try:
        with _cicd_status(ui, opts.quiet):
            response = agent.chat(prompt, images=opts.images)
        auto_commit_result: dict[str, Any] | None = None
        if opts.auto_commit_after:
            auto_commit_result = _run_auto_commit(agent, prompt, ui, quiet=opts.quiet)
        if opts.output_format == "json":
            result = _cicd_json_result(prompt, response, agent, auto_commit_result)
            print(json.dumps(result, indent=2))
        else:
            _print_cicd_output(ui, response, opts.quiet)
    except Exception as e:  # noqa: BLE001
        if opts.output_format == "json":
            print(json.dumps({"success": False, "error": str(e)}, indent=2))
        else:
            ui.print_error(f"Error: {e}")


# â”€â”€ TUI helpers (unchanged) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


# â”€â”€ Gateway â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


# â”€â”€ Backward compat aliases â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


# â”€â”€ Main entry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def _prepare_runtime() -> None:
    """Export the APEX process markers and set up state dir + file logging."""
    os.environ["APEX"] = "1"
    os.environ["APEX_PID"] = str(os.getpid())
    # Warn when the Python CLI runs from a pip-installed package rather than a
    # source checkout: the Python CLI/TUI is a source-only development surface.
    _warn_if_not_source_checkout()
    _init_state_dir()
    _setup_file_logging()


def _parse_mcp_serve_args(args: list[str]) -> tuple[str | None, list[str]]:
    cwd: str | None = None
    allow_tools: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--cwd", "-C") and i + 1 < len(args):
            cwd = args[i + 1]
            i += 2
        elif arg == "--allow-tool" and i + 1 < len(args):
            allow_tools.append(args[i + 1])
            i += 2
        else:
            sys.stderr.write(f"apex: unknown mcp serve argument: {arg}\n")
            sys.exit(2)
    return cwd, allow_tools


def _is_mcp_serve(raw_args: list[str]) -> bool:
    return len(raw_args) >= 2 and raw_args[0].lower() == "mcp" and raw_args[1] == "serve"


def _run_mcp_serve_if_requested(raw_args: list[str]) -> None:
    """Run `apex mcp serve` before argparse: the protocol owns stdout."""
    if not _is_mcp_serve(raw_args):
        return
    if len(raw_args) == 3 and raw_args[2] in ("--help", "-h"):
        sys.stderr.write("usage: apex mcp serve [--cwd PATH] [--allow-tool NAME]...\n")
        sys.exit(0)
    cwd, allow_tools = _parse_mcp_serve_args(raw_args[2:])
    from .mcp_server import serve as mcp_serve

    sys.exit(mcp_serve(cwd=Path(cwd) if cwd else None, allow_tools=allow_tools))


def _run_subcommand(parser: argparse.ArgumentParser, raw_args: list[str]) -> bool:
    """Dispatch positional subcommands such as `apex models`."""
    if not raw_args or raw_args[0].lower() not in _SUBCOMMANDS:
        return False
    name = raw_args[0].lower()
    parsed = parser.parse_args(raw_args)
    for key, value in _SUBCOMMANDS[name].items():
        setattr(parsed, key, value)
    parsed.prompt = None
    _dispatch(parsed)
    return True


_PAIRED_VERB_DEFAULTS = {"auth": "login", "agent": "list", "session": "list", "mcp": "list"}


def _subcommand_value(verb: str, raw_args: list[str]) -> str:
    if len(raw_args) > 1:
        candidate = raw_args[1]
        if candidate == "ls":
            return "list"
        if not candidate.startswith("-"):
            return candidate
    return _PAIRED_VERB_DEFAULTS.get(verb, "")


def _paired_verb_args(verb: str, raw_args: list[str]) -> list[str]:
    if verb == "db":
        return ["db", "path"]
    modified = [verb]
    if len(raw_args) > 1 and not raw_args[1].startswith("-"):
        modified.append(raw_args[1])
        extra = raw_args[2:]
    else:
        modified.append(_subcommand_value(verb, raw_args))
        extra = raw_args[1:]
    modified.extend(extra)
    return modified


def _run_paired_verb(parser: argparse.ArgumentParser, raw_args: list[str]) -> bool:
    """Dispatch verbs whose action comes from a subparser (`apex auth login`)."""
    verb = raw_args[0].lower() if raw_args else ""
    if verb not in ("auth", "agent", "session", "mcp", "db"):
        return False
    parsed = parser.parse_args(_paired_verb_args(verb, raw_args))
    parsed.prompt = None
    _dispatch_verb(verb, parsed)
    return True


_VERB_NAMESPACE_DEFAULTS = {
    "model": None,
    "cwd": None,
    "agent_name": None,
    "resume": False,
    "session_id": None,
    "fork_session": None,
    "stream": False,
    "quiet": False,
    "output_format": "text",
    "port": None,
    "hostname": None,
    "cors": None,
    "mdns": False,
    "refresh": False,
    "verbose": False,
    "sanitize": False,
    "keep_config": False,
    "keep_data": False,
    "dry_run": False,
    "force": False,
    "method": None,
    "check": False,
    "purge": False,
    "share": False,
    "input_file": None,
    "print_logs": False,
    "log_level": None,
    "pure": False,
    "install_tui": False,
    "list_models": False,
    "auto_commit": False,
    "image": None,
}

_DIRECT_VERBS = frozenset(
    {
        "serve",
        "web",
        "connect",
        "init",
        "compact",
        "details",
        "thinking",
        "stats",
        "export",
        "import",
        "upgrade",
        "uninstall",
        "pr",
        "attach",
        "debug",
        "github",
        "plugin",
        "gateway",
        "key",
    }
)


def _default_verb_namespace() -> argparse.Namespace:
    parsed = argparse.Namespace()
    for key, value in _VERB_NAMESPACE_DEFAULTS.items():
        setattr(parsed, key, value)
    parsed.prompt = None
    return parsed


def _apply_verb_overrides(
    parser: argparse.ArgumentParser, args: list[str], parsed: argparse.Namespace
) -> None:
    try:
        overrides, _ = parser.parse_known_args(args)
    except SystemExit:
        sys.exit(1)
    for key, value in vars(overrides).items():
        if key != "prompt":
            setattr(parsed, key, value)


def _run_direct_verb(parser: argparse.ArgumentParser, raw_args: list[str]) -> bool:
    """Dispatch verbs that carry their flags directly (`apex upgrade --check`)."""
    verb = raw_args[0].lower() if raw_args else ""
    if verb not in _DIRECT_VERBS:
        return False
    parsed = _default_verb_namespace()
    # Upgrade/uninstall accept flags after the verb (e.g. `apex uninstall
    # --dry-run`); the generic verb path used to drop them.
    if verb in ("upgrade", "uninstall"):
        _apply_verb_overrides(parser, raw_args[1:], parsed)
    parsed.raw_args = raw_args[1:]
    _dispatch_verb(verb, parsed)
    return True


def _run_parsed(parser: argparse.ArgumentParser, raw_args: list[str]) -> None:
    try:
        parsed = parser.parse_args(raw_args)
    except SystemExit:
        sys.exit(1)
    _dispatch(parsed)


def main() -> None:
    _prepare_runtime()
    parser = build_parser()

    # Handle --help first to show the full epilog.
    if len(sys.argv) == 1:
        sys.argv.append("tui")
    if len(sys.argv) == 2 and sys.argv[1] in ("--help", "-h"):
        parser.print_help()
        sys.exit(0)

    raw_args = sys.argv[1:]
    _run_mcp_serve_if_requested(raw_args)
    if _run_subcommand(parser, raw_args):
        return
    if _run_paired_verb(parser, raw_args):
        return
    if _run_direct_verb(parser, raw_args):
        return
    _run_parsed(parser, raw_args)


def _warn_if_not_source_checkout() -> None:
    """Warn if the Python CLI is invoked from a pip-installed package.

    The Python CLI/TUI is a source-only development surface. APEX is
    distributed via npm and the native backend only. When running from
    site-packages (pip install), the user should migrate to npm or the
    native backend instead.
    """
    try:
        import apex

        apex_file = Path(apex.__file__).resolve()
        parts = {p.lower() for p in apex_file.parts}
        if "site-packages" in parts or "dist-packages" in parts:
            sys.stderr.write(
                "WARNING: The APEX Python CLI/TUI is a source-only development surface.\n"
                "  It is not distributed via PyPI/pip/pipx/uv.\n"
                "  Install via npm:  npm install -g apex-ai\n"
                "  Or native backend: bash install.sh --method native\n"
                '  For development, use a source checkout: pip install -e ".[dev]"\n'
            )
    except Exception:  # noqa: BLE001, S110
        pass


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


def _configure_logging(parsed: argparse.Namespace) -> None:
    if parsed.log_level:
        logging.basicConfig(level=getattr(logging, parsed.log_level.upper(), logging.INFO))
    if parsed.print_logs:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def _validate_model(parsed: argparse.Namespace) -> None:
    if parsed.model and parsed.model not in MODELS:
        print(f"Error: Unknown model '{parsed.model}'", file=sys.stderr)
        print("Use --list-models to see available models", file=sys.stderr)
        sys.exit(1)


def _restore_session(parsed: argparse.Namespace, agent: Agent) -> None:
    if parsed.resume:
        sm = SessionManager()
        sessions = sm.list_sessions()
        if sessions:
            sm.load(sessions[0]["name"], agent)
    elif parsed.session_id:
        SessionManager().load(parsed.session_id, agent)
    elif parsed.fork_session:
        SessionManager().load(parsed.fork_session, agent)


def _route_mode(parsed: argparse.Namespace, agent: Agent, ui: UI) -> None:
    if parsed.ui or parsed.tui:
        run_apex_tui(agent, ui, resume=parsed.resume, session_id=parsed.session_id)
    elif parsed.prompt_direct:
        run_cicd_mode(
            parsed.prompt_direct,
            agent,
            ui,
            CicdOptions(
                output_format=parsed.output_format,
                quiet=parsed.quiet,
                images=parsed.image,
                auto_commit_after=parsed.auto_commit,
            ),
        )
    elif parsed.prompt:
        run_one_shot(
            parsed.prompt,
            agent,
            ui,
            OneShotOptions(
                use_stream=parsed.stream,
                images=parsed.image,
                auto_commit_after=parsed.auto_commit,
            ),
        )
    else:
        run_apex_tui(agent, ui)


def _dispatch(parsed: argparse.Namespace) -> None:
    from apex.config import Config

    config = Config()
    _configure_logging(parsed)
    _validate_model(parsed)
    if parsed.cwd:
        config.cwd = str(Path(parsed.cwd).expanduser().resolve())

    ui = UI()
    if parsed.model:
        config.model = parsed.model
    if parsed.agent_name:
        config.set("default_agent", parsed.agent_name)

    if parsed.list_models:
        list_models(ui, verbose=parsed.verbose, refresh=parsed.refresh)
        sys.exit(0)
    if parsed.install_tui:
        _install_tui_command(ui)
        sys.exit(0)
    if parsed.pure:
        config.set("pure_mode", True)

    agent = Agent(config)
    if parsed.agent_name:
        agent.switch_agent(parsed.agent_name)
    _restore_session(parsed, agent)
    _route_mode(parsed, agent, ui)


# Verb -> command function name. The handler is resolved at call time so tests
# (and plugins) can patch `apex.main._cmd_*` after the module is imported.
_VERB_HANDLER_NAMES: dict[str, str] = {
    "serve": "_cmd_serve",
    "web": "_cmd_web",
    "auth": "_cmd_auth",
    "agent": "_cmd_agent",
    "run": "_cmd_run",
    "session": "_cmd_session",
    "stats": "_cmd_stats",
    "export": "_cmd_export",
    "import": "_cmd_import",
    "upgrade": "_cmd_upgrade",
    "uninstall": "_cmd_uninstall",
    "mcp": "_cmd_mcp",
    "db": "_cmd_db",
    "pr": "_cmd_pr",
    "attach": "_cmd_attach",
    "connect": "_cmd_connect",
    "key": "_cmd_key",
    "init": "_cmd_init",
    "compact": "_cmd_compact",
    "details": "_cmd_details",
    "thinking": "_cmd_thinking",
    "debug": "_cmd_debug",
    "github": "_cmd_github",
    "plugin": "_cmd_plugin",
    "gateway": "_cmd_gateway",
}


def _resolve_verb_handler(verb: str) -> Callable[..., None] | None:
    name = _VERB_HANDLER_NAMES.get(verb)
    if name is None:
        return None
    return getattr(sys.modules[__name__], name, None)


def _call_verb_handler(
    verb: str, handler: Callable[..., None], parsed: argparse.Namespace, ui: UI
) -> None:
    # `init` takes only the UI; every other verb takes (args, ui).
    if verb == "init":
        handler(ui)
    else:
        handler(parsed, ui)


def _dispatch_verb(verb: str, parsed: argparse.Namespace) -> None:
    ui = UI()
    handler = _resolve_verb_handler(verb)
    if handler is not None:
        _call_verb_handler(verb, handler, parsed, ui)
        return
    if parsed.prompt:
        _dispatch(parsed)
        return
    ui.print_error(f"Unknown command: {verb}")
    sys.exit(1)


if __name__ == "__main__":
    main()
