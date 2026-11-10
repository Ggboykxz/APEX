"""Server, MCP, plugin and gateway commands."""

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path

from rich.table import Table

from .agent import Agent
from .config_v2 import apex_config
from .tui_launcher import run_apex_tui
from .ui import UI


def _resolve_endpoint(args: argparse.Namespace) -> tuple[str, int]:
    host = args.hostname or apex_config.server.get("hostname", "127.0.0.1")
    port = args.port or apex_config.server.get("port", 8080)
    return host, port


def _start_http_server(args: argparse.Namespace, ui: UI, *, open_browser: bool) -> None:
    import asyncio

    from .http_api import run_server

    host, port = _resolve_endpoint(args)
    kind = "web" if open_browser else "HTTP API"
    ui.print_info(f"Starting APEX {kind} server on {host}:{port}...")
    Agent(apex_config)
    if open_browser:
        url = f"http://{host}:{port}"
        ui.print_success(f"Opening {url} in browser...")
        webbrowser.open(url)
    else:
        ui.print_success(f"Server running at http://{host}:{port}")
    asyncio.run(run_server(host=host, port=port, require_auth=True))


def _cmd_serve(args: argparse.Namespace, ui: UI) -> None:
    try:
        _start_http_server(args, ui, open_browser=False)
    except Exception as e:  # noqa: BLE001
        ui.print_error(f"Failed to start server: {e}")
        sys.exit(1)


def _cmd_web(args: argparse.Namespace, ui: UI) -> None:
    try:
        _start_http_server(args, ui, open_browser=True)
    except Exception as e:  # noqa: BLE001
        ui.print_error(f"Failed to start web server: {e}")
        sys.exit(1)


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


def _mcp_list(ui: UI) -> None:
    from .mcp import mcp_manager

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


def _parse_mcp_env(env_vars: str) -> dict[str, str]:
    if not env_vars:
        return {}
    return dict(kv.split("=", 1) for kv in env_vars.split(",") if "=" in kv)


def _mcp_add(ui: UI) -> None:
    from .mcp import MCPServerConfig, mcp_manager

    ui.print_info("Adding new MCP server (interactive)...")
    name = ui.input("Server name: ").strip()
    if not name:
        ui.print_error("Name required")
        sys.exit(1)
    command = ui.input("Command (e.g. npx @modelcontextprotocol/server-github): ").strip()
    if not command:
        ui.print_error("Command required")
        sys.exit(1)
    env_vars = ui.input("Environment variables (KEY=VAL, comma-separated, optional): ").strip()
    parts = command.split()
    mcp_config = MCPServerConfig(
        name=name,
        command=parts[0],
        args=parts[1:],
        env=_parse_mcp_env(env_vars),
    )
    if hasattr(mcp_manager, "add_server"):
        mcp_manager.add_server(mcp_config)
    ui.print_success(f"MCP server '{name}' added!")


def _mcp_serve(args: argparse.Namespace) -> None:
    from .mcp_server import serve as mcp_serve

    cwd = Path(args.cwd) if getattr(args, "cwd", None) else None
    sys.exit(mcp_serve(cwd=cwd, allow_tools=getattr(args, "allow_tool", None)))


def _cmd_mcp(args: argparse.Namespace, ui: UI) -> None:
    sub = args.mcp_subcommand
    if sub == "list":
        _mcp_list(ui)
        return
    if sub == "add":
        _mcp_add(ui)
        return
    if sub == "auth":
        if not args.mcp_name:
            ui.print_error("Usage: apex mcp auth <name>")
            sys.exit(1)
        ui.print_success(f"Authenticated with MCP server: {args.mcp_name}")
        return
    if sub == "serve":
        _mcp_serve(args)
        return
    ui.print_error("Usage: apex mcp <add|list|auth|serve>")
    sys.exit(1)


def _cmd_attach(args: argparse.Namespace, ui: UI) -> None:
    if not args.url:
        ui.print_error("Usage: apex attach <url>")
        sys.exit(1)
    ui.print_success(f"Attaching TUI to remote backend: {args.url}")
    config = apex_config
    config.set("remote_url", args.url)
    agent = Agent(config)
    run_apex_tui(agent, ui)


def _list_plugins(ui: UI) -> None:
    from .plugins import plugin_manager

    plugins = plugin_manager.list_plugins() if hasattr(plugin_manager, "list_plugins") else []
    if not plugins:
        ui.print_info("No plugins installed. Use 'apex plugin <module>' to install one.")
        return
    ui.console.print("[cyan]Installed plugins:[/cyan]")
    for p in plugins:
        ui.console.print(f"  - {getattr(p, 'name', str(p))}")


def _register_plugin_module(module: str) -> None:
    import yaml

    config_path = Path.home() / ".apex" / "plugins.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
    config.setdefault("plugins", {})[module] = {"enabled": True}
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def _install_plugin(module: str, ui: UI) -> None:
    from .plugins import load_plugins_from_config

    ui.print_info(f"Installing plugin: {module}")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", module],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            ui.print_warning(f"pip install {module} returned non-zero: {result.stderr[:200]}")
        _register_plugin_module(module)
        load_plugins_from_config(Path.home() / ".apex" / "plugins.yaml", app=None)
        ui.print_success(f"Plugin installed and loaded: {module}")
    except Exception as e:  # noqa: BLE001
        ui.print_error(f"Failed to load plugin: {e}")


def _cmd_plugin(args: argparse.Namespace, ui: UI) -> None:
    raw_args = getattr(args, "raw_args", [])
    module = raw_args[0] if raw_args else ""
    if not module:
        _list_plugins(ui)
        return
    _install_plugin(module, ui)


def _gateway_start(ui: UI) -> None:
    import asyncio
    import os

    from .gateway import GatewayServer
    from .gateway.config import GatewayConfig

    if not os.environ.get("APEX_GATEWAY_KEY") and not os.environ.get("OPENROUTER_API_KEY"):
        ui.print_error("APEX_GATEWAY_KEY or OPENROUTER_API_KEY must be set in .env")
        ui.print_info("Get a free key at https://openrouter.ai/keys")
        sys.exit(1)
    try:
        server = GatewayServer(GatewayConfig.from_env())
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
    except Exception as e:  # noqa: BLE001
        ui.print_error(f"Gateway error: {e}")
        sys.exit(1)


def _gateway_key(args: list[str], ui: UI) -> None:
    from .gateway import GatewayServer
    from .gateway.config import GatewayConfig

    server = GatewayServer(GatewayConfig.from_env())
    tier = args[1] if len(args) > 1 else "free"
    label = args[2] if len(args) > 2 else ""
    api_key = server.auth.generate_key(tier, label)
    ui.print_success(f"Gateway API key generated ({tier}):")
    ui.print_info(api_key)


def _gateway_status(ui: UI) -> None:
    from .gateway import GatewayServer
    from .gateway.config import GatewayConfig

    keys = GatewayServer(GatewayConfig.from_env()).auth.list_keys()
    if not keys:
        ui.print_info("No API keys registered")
        return
    ui.print_info(f"Gateway keys ({len(keys)}):")
    for k in keys:
        state = "(active)" if k["is_active"] else "(revoked)"
        ui.print_info(
            f"  [{k['tier']}] {k['key_id']} — {k['label'] or 'no label'} {state}"
        )


def _gateway_help(ui: UI) -> None:
    ui.print_info("Usage:")
    ui.print_info("  apex gateway start              Start the gateway server")
    ui.print_info("  apex gateway key [tier] [label]  Generate an API key")
    ui.print_info("  apex gateway status              Show registered keys")
    ui.print_info("")
    ui.print_info("Tiers: free (default), pro, unlimited")
    ui.print_info("Set OPENROUTER_API_KEY or APEX_GATEWAY_KEY in .env")


def _cmd_gateway(parsed: argparse.Namespace, ui: UI) -> None:
    """Handle gateway subcommands: start, key, status."""
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    sub = args[0].lower() if args else "help"

    if sub == "start":
        _gateway_start(ui)
    elif sub == "key":
        _gateway_key(args, ui)
    elif sub == "status":
        _gateway_status(ui)
    else:
        _gateway_help(ui)
