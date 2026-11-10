"""Tests for apex/cli_sessions.py — pure helpers."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from apex import cli_sessions


def test_recent_sessions_filters():
    now = datetime.now().isoformat()
    old = (datetime.now() - timedelta(days=10)).isoformat()
    sessions = [
        {"name": "a", "timestamp": now, "model": "gpt-4o", "history_len": 5},
        {"name": "b", "timestamp": old, "model": "gpt-4o", "history_len": 3},
        {"name": "c", "timestamp": "not-a-date", "model": "gpt-4o", "history_len": 1},
    ]
    recent = cli_sessions._recent_sessions(sessions, 7)
    assert len(recent) == 1
    assert recent[0]["name"] == "a"


def test_session_cost_no_pricing():
    inp, out, cost = cli_sessions._session_cost(10, None)
    assert inp == 2500
    assert out == 2500
    assert cost == 0.0


def test_session_cost_with_pricing():
    pricing = type("P", (), {"per_1k_input": 0.01, "per_1k_output": 0.02})()
    inp, out, cost = cli_sessions._session_cost(4, pricing)
    assert inp == 1000
    assert out == 1000
    assert abs(cost - 0.03) < 1e-9


def test_accumulate_stats():
    recent = [
        {"name": "a", "timestamp": "2026-01-01", "model": "gpt-4o", "history_len": 4},
        {"name": "b", "timestamp": "2026-01-02", "model": "claude", "history_len": 2},
    ]
    pricing = {"gpt-4o": type("P", (), {"per_1k_input": 0.01, "per_1k_output": 0.02})()}
    totals = cli_sessions._accumulate_stats(recent, pricing)
    assert totals["input"] == 1000 + 500
    assert totals["output"] == 1000 + 500
    assert "gpt-4o" in totals["models"]
    assert "claude" in totals["models"]
    assert totals["models"]["claude"]["cost"] == 0.0


def test_parse_ts_valid():
    ts = "2026-01-01T12:00:00"
    assert cli_sessions._parse_ts(ts) > 0


def test_parse_ts_invalid():
    assert cli_sessions._parse_ts("not-a-date") == 0


def test_import_url_target_share():
    assert (
        cli_sessions._import_url_target("apex://share/abc123")
        == "https://apex-ai.dev/s/abc123.json"
    )


def test_import_url_target_passthrough():
    assert (
        cli_sessions._import_url_target("https://example.com/x.json")
        == "https://example.com/x.json"
    )


def test_db_paths():
    paths = cli_sessions._db_paths()
    assert len(paths) == 3
    assert all(isinstance(p, __import__("pathlib").Path) for p in paths)


def test_print_query_rows():
    ui = MagicMock()
    cli_sessions._print_query_rows([(1, "a"), (2, "b")], ["id", "name"], ui)
    assert ui.console.print.called


def test_session_cost_zero_history():
    inp, out, cost = cli_sessions._session_cost(0, None)
    assert inp == 0
    assert out == 0
    assert cost == 0.0
