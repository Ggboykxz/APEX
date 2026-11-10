"""Authentication, API-key and provider-connection commands."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from rich.table import Table

from .agent import Agent
from .ui import UI


def _auth_file() -> Path:
    auth_dir = Path.home() / ".config" / "apex"
    auth_dir.mkdir(parents=True, exist_ok=True)
    return auth_dir / "auth.json"


def _read_auth(auth_file: Path) -> dict[str, Any]:
    if auth_file.exists():
        return json.loads(auth_file.read_text())
    return {}


def _auth_list(auth_file: Path, ui: UI) -> None:
    if not auth_file.exists():
        ui.print_info("No providers configured")
        return
    data = _read_auth(auth_file)
    table = Table(title="Configured Providers", show_header=True, header_style="bold cyan")
    table.add_column("Provider", style="cyan", width=20)
    table.add_column("Key (last 8)", style="yellow", width=16)
    table.add_column("Model", style="green", width=24)
    for prov, info in data.items():
        key_preview = "..." + info.get("api_key", "")[-8:] if info.get("api_key") else "not set"
        table.add_row(prov, key_preview, info.get("model", "default"))
    ui.console.print(table)


def _auth_logout(auth_file: Path, provider: str | None, ui: UI) -> None:
    if not provider:
        ui.print_error("Usage: apex auth logout --provider <name>")
        sys.exit(1)
    if not auth_file.exists():
        return
    data = _read_auth(auth_file)
    if provider not in data:
        ui.print_error(f"Provider not found: {provider}")
        sys.exit(1)
    del data[provider]
    auth_file.write_text(json.dumps(data, indent=2))
    ui.print_success(f"Logged out from provider: {provider}")


def _persist_openrouter_env(key: str, ui: UI) -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        env_path.write_text(f"# APEX Configuration\nOPENROUTER_API_KEY={key}\n")
        ui.print_success("OpenRouter configured! Key saved to .env")
        return
    lines = env_path.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("OPENROUTER_API_KEY="):
            lines[i] = f"OPENROUTER_API_KEY={key}"
            break
    else:
        lines.append(f"OPENROUTER_API_KEY={key}")
    env_path.write_text("\n".join(lines) + "\n")
    ui.print_success("OpenRouter configured! Key updated in .env")


def _configure_openrouter(auth_file: Path, ui: UI) -> None:
    key = ui.input("OpenRouter API key (sk-or-v1-...): ").strip()
    if not key:
        ui.print_error("API key required")
        sys.exit(1)
    data = _read_auth(auth_file)
    data["openrouter"] = {"api_key": key, "configured_at": time.time()}
    auth_file.write_text(json.dumps(data, indent=2))
    os.environ["OPENROUTER_API_KEY"] = key
    _persist_openrouter_env(key, ui)


def _auth_login(args: argparse.Namespace, auth_file: Path, ui: UI) -> None:
    provider = args.auth_provider
    if not provider:
        provider = ui.input("Provider name (e.g. anthropic, openai, openrouter): ").strip()
    if not provider:
        ui.print_error("Provider name required")
        sys.exit(1)

    # Quick setup for OpenRouter.
    if provider.lower() in ("openrouter", "or"):
        _configure_openrouter(auth_file, ui)
        return

    key = ui.input(f"API key for {provider}: ").strip()
    if not key:
        ui.print_error("API key required")
        sys.exit(1)

    data = _read_auth(auth_file)
    data[provider] = {
        "api_key": key,
        "model": args.model or "default",
        "configured_at": time.time(),
    }
    auth_file.write_text(json.dumps(data, indent=2))
    ui.print_success(f"Provider '{provider}' configured!")


def _cmd_auth(args: argparse.Namespace, ui: UI) -> None:
    auth_file = _auth_file()
    if args.auth_subcommand == "list":
        _auth_list(auth_file, ui)
        return
    if args.auth_subcommand == "logout":
        _auth_logout(auth_file, args.auth_provider, ui)
        return
    _auth_login(args, auth_file, ui)


def _openrouter_auth_file() -> "Path":
    auth_dir = Path.home() / ".config" / "apex"
    auth_dir.mkdir(parents=True, exist_ok=True)
    return auth_dir / "auth.json"


def _read_openrouter_key(args: argparse.Namespace, ui: UI) -> str:
    key = getattr(args, "key_value", None) or args.prompt or ""
    if not key:
        key = ui.input("OpenRouter API key (sk-or-v1-...): ").strip()
    if not key:
        ui.print_error("Usage: apex key <your-openrouter-key>")
        sys.exit(1)
    return key


def _store_openrouter_key(key: str) -> None:
    auth_file = _openrouter_auth_file()
    data = json.loads(auth_file.read_text()) if auth_file.exists() else {}
    data["openrouter"] = {"api_key": key, "configured_at": time.time()}
    auth_file.write_text(json.dumps(data, indent=2))
    auth_file.chmod(0o600)


def _warn_missing_gitignore(ui: UI) -> None:
    gitignore = Path.cwd() / ".gitignore"
    if gitignore.exists() and ".env" in gitignore.read_text():
        return
    ui.print_warning("WARNING: .env file will be created/updated in the current directory.")
    ui.print_warning("Make sure .env is in your .gitignore to avoid committing secrets!")


def _write_env_key(key: str) -> None:
    env_path = Path.cwd() / ".env"
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    for i, line in enumerate(lines):
        if line.startswith("OPENROUTER_API_KEY="):
            lines[i] = f"OPENROUTER_API_KEY={key}"
            break
    else:
        lines.append(f"OPENROUTER_API_KEY={key}")
    env_path.write_text("\n".join(lines) + "\n")
    env_path.chmod(0o600)


def _cmd_key(args: argparse.Namespace, ui: UI) -> None:
    """Quick setup: set OpenRouter API key."""
    key = _read_openrouter_key(args, ui)
    _store_openrouter_key(key)
    os.environ["OPENROUTER_API_KEY"] = key
    _warn_missing_gitignore(ui)
    _write_env_key(key)
    ui.print_success("OpenRouter key configured!")
    ui.print_info("   Stored in ~/.config/apex/auth.json and .env (permissions: 0600)")


_PROVIDERS: list[tuple[str, str, str]] = [
    ("anthropic", "ANTHROPIC_API_KEY", "claude-sonnet-4-5"),
    ("openai", "OPENAI_API_KEY", "gpt-4o"),
    ("google", "GEMINI_API_KEY", "gemini-2.5-pro"),
    ("deepseek", "DEEPSEEK_API_KEY", "deepseek-chat"),
    ("groq", "GROQ_API_KEY", "llama-3.3-70b"),
    ("mistral", "MISTRAL_API_KEY", "mistral-large-latest"),
    ("xai", "XAI_API_KEY", "grok-4"),
]


def _prompt_provider_key(name: str, default_model: str, ui: UI) -> dict[str, str] | None:
    answer = ui.input(f"  Configure {name}? (y/N): ").strip().lower()
    if answer != "y":
        return None
    key = ui.input(f"    API key for {name}: ").strip()
    if not key:
        return None
    model = ui.input(f"    Default model [{default_model}]: ").strip() or default_model
    return {"api_key": key, "model": model}


def _configure_provider(
    data: dict, provider: tuple[str, str, str], ui: UI
) -> dict[str, str] | None:
    name, env_var, default_model = provider
    existing = data.get(name, {})
    env_val = os.environ.get(env_var, "")
    if existing.get("api_key"):
        ui.print_info(f"  [{name}] Already configured (key: ...{existing['api_key'][-8:]})")
        return existing
    if env_val:
        ui.print_success(f"  [{name}] Found {env_var} in environment")
        return {"api_key": env_val, "model": default_model}
    entry = _prompt_provider_key(name, default_model, ui)
    if entry:
        os.environ[env_var] = entry["api_key"]
        return entry
    return None


def _interactive_provider_config(agent: Agent | None = None, ui: UI | None = None) -> None:
    if ui is None:
        from .ui import UI

        ui = UI()
    ui.print_info("Welcome to APEX provider configuration!")
    ui.print_info("You can set API keys via environment variables or configure them here.\n")

    auth_file = _openrouter_auth_file()
    data = json.loads(auth_file.read_text()) if auth_file.exists() else {}

    for provider in _PROVIDERS:
        entry = _configure_provider(data, provider, ui)
        if entry is not None:
            data[provider[0]] = entry

    auth_file.write_text(json.dumps(data, indent=2))
    ui.print_success("Provider configuration saved!")


def _cmd_connect(args: argparse.Namespace, ui: UI) -> None:
    _interactive_provider_config(None, ui)
