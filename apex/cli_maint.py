"""Upgrade, uninstall and project-initialisation commands."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .ui import UI


def _print_unknown_versions(install, latest: str, ui: UI) -> None:
    if latest == __version__:
        ui.print_success(f"APEX {__version__} is up to date")
    else:
        ui.print_info(f"Latest release: {latest}")


def _print_version_comparison(install, latest: str, ui: UI) -> None:
    current = install.version_key(__version__)
    candidate = install.version_key(latest)
    if current is None or candidate is None:
        _print_unknown_versions(install, latest, ui)
        return
    if candidate > current:
        ui.print_info(f"Update available: {__version__} -> {latest}")
        ui.print_info("Run: apex upgrade")
    elif candidate == current:
        ui.print_success(f"APEX {__version__} is up to date")
    else:
        ui.print_info(f"APEX {__version__} is ahead of the latest release ({latest}).")


def _report_upgrade_check(install, ui: UI) -> None:
    """Handle `apex upgrade --check`."""
    try:
        latest = install.fetch_latest_release()
    except install.ReleaseUnavailable:
        ui.print_info(
            f"No published release yet — you are running APEX {__version__} (source build)."
        )
        return
    except Exception as e:  # noqa: BLE001
        ui.print_error(f"Could not check for updates: {e}")
        sys.exit(1)
    _print_version_comparison(install, latest, ui)


def _resolve_upgrade_method(args: argparse.Namespace, install, ui: UI) -> str:
    requested = None if args.method in (None, "", "auto") else args.method
    try:
        return install.primary_method(install.detect(), requested)
    except install.InstallError as e:
        ui.print_error(str(e))
        sys.exit(1)


def _upgrade_native(install, pinned: str | None, ui: UI) -> None:
    try:
        destination = install.native_upgrade(pinned)
    except install.InstallError as e:
        ui.print_error(str(e))
        sys.exit(1)
    ui.print_success(f"Native backend updated: {destination}")


def _upgrade_with_command(command: list[str], ui: UI) -> None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    except Exception as e:  # noqa: BLE001
        ui.print_error(f"Upgrade error: {e}")
        sys.exit(1)
    if result.returncode != 0:
        detail = result.stderr or result.stdout or "unknown error"
        ui.print_error(f"Upgrade failed: {detail[:300]}")
        sys.exit(1)
    ui.print_success("APEX upgraded successfully!")


def _upgrade_source_notice(ui: UI) -> None:
    ui.print_info(
        "This copy runs from a source checkout. Update it with 'git pull' "
        "and reinstall the dev dependencies, or install a released channel "
        "with 'apex upgrade --method native' (or '--method npm')."
    )


def _run_channel_upgrade(install, method: str, pinned: str | None, ui: UI) -> None:
    ui.print_info(f"Upgrading APEX via {method}...")
    if method == "native":
        _upgrade_native(install, pinned, ui)
        return
    try:
        command = install.upgrade_command(method, pinned)
    except install.InstallError as e:
        ui.print_error(str(e))
        sys.exit(1)
    _upgrade_with_command(command, ui)


def _cmd_upgrade(args: argparse.Namespace, ui: UI) -> None:
    from . import install_manager as install

    if getattr(args, "check", False):
        _report_upgrade_check(install, ui)
        return

    pinned = os.environ.get("APEX_VERSION", "").strip() or None
    method = _resolve_upgrade_method(args, install, ui)
    if method == install.SOURCE_METHOD:
        _upgrade_source_notice(ui)
        return
    _run_channel_upgrade(install, method, pinned, ui)


def _confirm_uninstall(args: argparse.Namespace, ui: UI) -> bool:
    if args.dry_run or args.force:
        return True
    confirm = (
        ui.console.input("Are you sure you want to uninstall APEX? (yes/no): ").strip().lower()
    )
    if confirm != "yes":
        ui.print_info("Uninstall cancelled")
        return False
    return True


def _print_uninstall_plan(plan, ui: UI) -> None:
    ui.print_info("[DRY RUN] Would uninstall APEX")
    for path in plan.paths:
        ui.print_info(f"  Would remove: {path}")
    for command in plan.commands:
        ui.print_info(f"  Would run: {' '.join(command)}")
    if plan.kept:
        ui.print_info(f"  Would keep: {', '.join(plan.kept)}")


def _remove_single_path(path, ui: UI) -> None:
    try:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        ui.print_success(f"Removed {path}")
    except OSError as e:
        ui.print_warning(f"Could not remove {path}: {e}")


def _remove_install_paths(plan, ui: UI) -> None:
    for path in plan.paths:
        _remove_single_path(path, ui)


def _run_uninstall_command(command: list[str], ui: UI) -> None:
    label = " ".join(command)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    except Exception as e:  # noqa: BLE001
        ui.print_warning(f"{label} failed: {e}")
        return
    if result.returncode == 0:
        ui.print_success(f"Ran: {label}")
        return
    detail = result.stderr or result.stdout or "unknown error"
    ui.print_warning(f"{label}: {detail[:200]}")


def _run_uninstall_commands(plan, ui: UI) -> None:
    for command in plan.commands:
        _run_uninstall_command(command, ui)


def _cmd_uninstall(args: argparse.Namespace, ui: UI) -> None:
    from . import install_manager as install

    if not _confirm_uninstall(args, ui):
        return

    plan = install.uninstall_plan(
        detection=install.detect(),
        keep_config=args.keep_config,
        keep_data=args.keep_data,
        purge=getattr(args, "purge", False),
    )
    if args.dry_run:
        _print_uninstall_plan(plan, ui)
        return

    _remove_install_paths(plan, ui)
    _run_uninstall_commands(plan, ui)
    for path in plan.kept:
        ui.print_info(f"Kept: {path}")
    ui.print_info("APEX has been removed. We hope to see you again!")


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
