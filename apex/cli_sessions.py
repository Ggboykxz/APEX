"""Session, statistics, export/import and database commands."""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from rich.table import Table

from .agent import Agent
from .config_v2 import apex_config
from .session import SessionManager
from .ui import UI


def _session_list(args: argparse.Namespace, sm: SessionManager, ui: UI) -> None:
    count = args.n if hasattr(args, "n") and args.n else 20
    sessions = sm.list_sessions()[:count]
    if not sessions:
        ui.print_info("No saved sessions")
        return
    if getattr(args, "list_format", "table") == "json":
        print(json.dumps(sessions, indent=2))
        return
    table = Table(title="Sessions", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan", width=16)
    table.add_column("Model", style="green", width=20)
    table.add_column("Messages", style="yellow", width=10)
    table.add_column("Timestamp", style="white")
    for s in sessions:
        table.add_row(
            s["name"],
            s.get("model", ""),
            str(s.get("history_len", 0)),
            s.get("timestamp", ""),
        )
    ui.console.print(table)


def _session_delete(args: argparse.Namespace, ui: UI) -> None:
    if not args.session_id:
        ui.print_error("Usage: apex session delete <session_id>")
        sys.exit(1)
    sessions_dir = Path.home() / ".apex" / "sessions"
    deleted = False
    for f in sessions_dir.glob(f"*{args.session_id}*"):
        if f.is_file() and f.suffix == ".json":
            f.unlink()
            deleted = True
    if not deleted:
        ui.print_error(f"Session not found: {args.session_id}")
        sys.exit(1)
    ui.print_success(f"Deleted session: {args.session_id}")


def _cmd_session(args: argparse.Namespace, ui: UI) -> None:
    if args.session_subcommand == "list":
        _session_list(args, SessionManager(), ui)
        return
    if args.session_subcommand == "delete":
        _session_delete(args, ui)
        return
    ui.print_error("Usage: apex session <list|delete>")
    sys.exit(1)


def _recent_sessions(sessions: list[dict], days: int) -> list[dict]:
    cutoff = time.time() - (days * 86400)
    return [
        s
        for s in sessions
        if s.get("timestamp")
        and _parse_ts(s["timestamp"]) > 0
        and _parse_ts(s["timestamp"]) > cutoff
    ]


def _session_cost(history_len: int, pricing) -> tuple[int, int, float]:
    tokens = history_len * 250
    if not pricing:
        return tokens, tokens, 0.0
    cost = (tokens / 1000 * pricing.per_1k_input) + (tokens / 1000 * pricing.per_1k_output)
    return tokens, tokens, cost


def _accumulate_stats(recent: list[dict], model_pricing) -> dict[str, Any]:
    totals: dict[str, Any] = {"input": 0, "output": 0, "cost": 0.0, "models": {}}
    for s in recent:
        model = s.get("model", "unknown")
        inp, out, cost = _session_cost(s.get("history_len", 0), model_pricing.get(model))
        totals["input"] += inp
        totals["output"] += out
        totals["cost"] += cost
        stats = totals["models"].setdefault(
            model, {"sessions": 0, "input": 0, "output": 0, "cost": 0.0}
        )
        stats["sessions"] += 1
        stats["input"] += inp
        stats["output"] += out
        stats["cost"] += cost
    return totals


def _print_usage_table(days: int, recent: list[dict], totals: dict[str, Any], ui: UI) -> None:
    table = Table(
        title=f"Usage Stats (last {days} days)", show_header=True, header_style="bold cyan"
    )
    table.add_column("Metric", style="white", width=16)
    table.add_column("Value", style="green")
    table.add_row("Sessions", str(len(recent)))
    table.add_row("Total Input Tokens", f"{totals['input']:,}")
    table.add_row("Total Output Tokens", f"{totals['output']:,}")
    table.add_row("Total Tokens", f"{totals['input'] + totals['output']:,}")
    table.add_row("Estimated Cost", f"${totals['cost']:.4f}")
    ui.console.print(table)


def _print_model_table(model_stats: dict[str, dict], ui: UI) -> None:
    model_table = Table(title="Per-Model Breakdown", show_header=True, header_style="bold cyan")
    model_table.add_column("Model", style="cyan", width=24)
    model_table.add_column("Sessions", style="yellow", width=10)
    model_table.add_column("Input", style="white", width=14)
    model_table.add_column("Output", style="white", width=14)
    model_table.add_column("Cost", style="green", width=12)
    for model_name, ms in sorted(model_stats.items(), key=lambda x: -x[1]["cost"]):
        model_table.add_row(
            model_name,
            str(ms["sessions"]),
            f"{ms['input']:,}",
            f"{ms['output']:,}",
            f"${ms['cost']:.4f}",
        )
    ui.console.print(model_table)


def _cmd_stats(args: argparse.Namespace, ui: UI) -> None:
    from .cost_local import MODEL_PRICING

    days = args.days or 30
    recent = _recent_sessions(SessionManager().list_sessions(), days)
    totals = _accumulate_stats(recent, MODEL_PRICING)

    _print_usage_table(days, recent, totals, ui)
    if args.tools or args.models_flag:
        _print_model_table(totals["models"], ui)


def _parse_ts(ts: str) -> float:
    from datetime import datetime

    try:
        return datetime.fromisoformat(ts).timestamp()
    except Exception:  # noqa: BLE001
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


def _import_url_target(file_path: str) -> str:
    if file_path.startswith("apex://share/"):
        share_id = file_path.split("/")[-1]
        return f"https://apex-ai.dev/s/{share_id}.json"
    return file_path


def _import_from_url(file_path: str, sm, ui: UI) -> None:
    import urllib.request

    try:
        resp = urllib.request.urlopen(_import_url_target(file_path))
        data = json.loads(resp.read())
        session_id = sm._generate_id()
        sessions_dir = Path.home() / ".apex" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        out = sessions_dir / f"imported_{session_id}.json"
        out.write_text(json.dumps(data, indent=2))
        ui.print_success(f"Imported from URL as session: {session_id}")
    except Exception as e:  # noqa: BLE001
        ui.print_error(f"Failed to import from URL: {e}")
        sys.exit(1)


def _cmd_import(args: argparse.Namespace, ui: UI) -> None:
    from .share import share_manager as sm

    if not args.file:
        ui.print_error("Usage: apex import <file>")
        sys.exit(1)
    if args.file.startswith(("http://", "https://", "apex://")):
        _import_from_url(args.file, sm, ui)
        return
    result = sm.import_session(args.file)
    if not result:
        ui.print_error(f"Failed to import from: {args.file}")
        sys.exit(1)
    ui.print_success(f"Imported session: {result}")


def _cmd_compact(args: argparse.Namespace, ui: UI) -> None:
    config = apex_config
    agent = Agent(config)
    if hasattr(agent, "compact_context"):
        before = len(agent.history) if hasattr(agent, "history") else 0
        agent.compact_context()
        after = len(agent.history) if hasattr(agent, "history") else 0
        ui.print_success(f"Context compacted: {before} â†’ {after} messages")
    else:
        ui.print_info("Compaction not available in this context")


def _db_paths() -> list[Path]:
    return [
        Path.home() / ".apex" / "api_keys.db",
        Path.home() / ".apex" / "sessions",
        Path.home() / ".config" / "apex" / "apex.json",
    ]


def _print_query_rows(rows: list, col_names: list[str], ui: UI) -> None:
    if col_names:
        ui.console.print(" | ".join(col_names))
        ui.console.print("-" * 40)
    for row in rows[:50]:
        ui.console.print(" | ".join(str(c) for c in row))
    if len(rows) > 50:
        ui.console.print(f"... and {len(rows) - 50} more rows")


def _db_query(raw_args: list[str], ui: UI) -> None:
    import sqlite3

    query = " ".join(raw_args[1:]) if len(raw_args) > 1 else ""
    if not query:
        ui.print_error("Usage: apex db <path|sql_query>")
        return
    db_path = Path.home() / ".apex" / "api_keys.db"
    if not db_path.exists():
        ui.print_info("No database found at " + str(db_path))
        return
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            col_names = [d[0] for d in cursor.description] if cursor.description else []
    except sqlite3.Error as e:
        ui.print_error(f"Database error: {e}")
        return
    _print_query_rows(rows, col_names, ui)


def _cmd_db(args: argparse.Namespace, ui: UI) -> None:
    raw_args = getattr(args, "raw_args", sys.argv[1:])
    sub = args.db_subcommand if hasattr(args, "db_subcommand") else ""

    if sub == "path":
        for p in _db_paths():
            if p.exists():
                print(p)
    elif sub == "query":
        _db_query(raw_args, ui)
    else:
        ui.print_info("Usage: apex db <path|sql_query>")
