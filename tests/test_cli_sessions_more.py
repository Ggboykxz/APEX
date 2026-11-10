"""Tests for apex/cli_sessions.py — session commands, stats, export/import and db."""

import argparse
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apex import cli_sessions as cs


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


def _ns(**kw):
    base = {
        "n": None,
        "list_format": "table",
        "session_id": None,
        "sanitize": False,
        "days": None,
        "tools": False,
        "models_flag": False,
        "file": None,
    }
    base.update(kw)
    return argparse.Namespace(**base)


class FakeTable:
    def __init__(self, *a, **k):
        self.rows = []
        self.columns = []

    def add_column(self, *a, **k):
        self.columns.append(a)

    def add_row(self, *cells):
        self.rows.append(cells)


def test_session_list_empty():
    ui = MagicMock()
    sm = MagicMock()
    sm.list_sessions.return_value = []
    cs._session_list(_ns(), sm, ui)
    ui.print_info.assert_called_once_with("No saved sessions")


def test_session_list_json():
    ui = MagicMock()
    sm = MagicMock()
    sm.list_sessions.return_value = [{"name": "s1", "model": "gpt"}]
    cs._session_list(_ns(list_format="json"), sm, ui)
    # JSON is printed to stdout, not through ui.
    ui.print_info.assert_not_called()


def test_session_list_table(capsys):
    ui = MagicMock()
    sm = MagicMock()
    sm.list_sessions.return_value = [
        {"name": "s1", "model": "gpt", "history_len": 5, "timestamp": "2026-01-01"}
    ]
    with patch.object(cs, "Table", FakeTable):
        cs._session_list(_ns(), sm, ui)
    ui.console.print.assert_called_once()
    table = ui.console.print.call_args.args[0]
    assert table.rows == [("s1", "gpt", "5", "2026-01-01")]


def test_session_list_n_limit():
    ui = MagicMock()
    sm = MagicMock()
    sm.list_sessions.return_value = [{"name": f"s{i}"} for i in range(10)]
    cs._session_list(_ns(n=3), sm, ui)
    assert sm.list_sessions.call_count == 1


def test_session_delete_missing_id():
    ui = MagicMock()
    with pytest.raises(SystemExit) as exc:
        cs._session_delete(_ns(session_id=None), ui)
    assert exc.value.code == 1
    ui.print_error.assert_called_once()


def test_session_delete_not_found(fake_home):
    sessions = fake_home / ".apex" / "sessions"
    sessions.mkdir(parents=True)
    ui = MagicMock()
    with pytest.raises(SystemExit) as exc:
        cs._session_delete(_ns(session_id="xyz"), ui)
    assert exc.value.code == 1
    assert "not found" in ui.print_error.call_args.args[0]


def test_session_delete_success(fake_home):
    sessions = fake_home / ".apex" / "sessions"
    sessions.mkdir(parents=True)
    (sessions / "abc123.json").write_text("{}")
    (sessions / "other.txt").write_text("x")
    ui = MagicMock()
    cs._session_delete(_ns(session_id="abc"), ui)
    assert not (sessions / "abc123.json").exists()
    assert (sessions / "other.txt").exists()
    ui.print_success.assert_called_once()


def test_cmd_session_list_dispatch():
    with (
        patch.object(cs, "_session_list") as mock_list,
        patch.object(cs, "SessionManager") as mock_sm,
    ):
        cs._cmd_session(_ns(session_subcommand="list"), MagicMock())
    mock_list.assert_called_once()
    assert mock_list.call_args.args[1] is mock_sm.return_value


def test_cmd_session_delete_dispatch():
    with patch.object(cs, "_session_delete") as mock_del:
        cs._cmd_session(_ns(session_subcommand="delete", session_id="abc"), MagicMock())
    mock_del.assert_called_once()


def test_cmd_session_unknown():
    ui = MagicMock()
    with pytest.raises(SystemExit) as exc:
        cs._cmd_session(_ns(session_subcommand="bogus"), ui)
    assert exc.value.code == 1
    ui.print_error.assert_called_once()


def test_recent_sessions_filters_time():
    from datetime import datetime, timedelta

    now = datetime.now()
    recent = (now - timedelta(days=2)).isoformat()
    old = (now - timedelta(days=60)).isoformat()
    sessions = [
        {"timestamp": old},  # older than 30 days → filtered
        {"timestamp": recent},  # within 30 days → kept
        {"timestamp": None},  # missing → filtered
        {"timestamp": "bad-ts"},  # unparsable → filtered
    ]
    assert cs._recent_sessions(sessions, 30) == [{"timestamp": recent}]


def test_print_usage_table():
    ui = MagicMock()
    with patch.object(cs, "Table", FakeTable):
        cs._print_usage_table(30, [{"name": "s"}], {"input": 1000, "output": 500, "cost": 0.25}, ui)
    table = ui.console.print.call_args.args[0]
    values = dict(table.rows)
    assert values["Sessions"] == "1"
    assert values["Total Input Tokens"] == "1,000"
    assert values["Total Tokens"] == "1,500"
    assert values["Estimated Cost"] == "$0.2500"


def test_print_model_table_sorted_by_cost_desc():
    ui = MagicMock()
    stats = {
        "cheap": {"sessions": 1, "input": 10, "output": 10, "cost": 0.1},
        "pricy": {"sessions": 2, "input": 20, "output": 20, "cost": 9.9},
    }
    with patch.object(cs, "Table", FakeTable):
        cs._print_model_table(stats, ui)
    table = ui.console.print.call_args.args[0]
    assert table.rows[0][0] == "pricy"
    assert table.rows[1][0] == "cheap"


@pytest.mark.parametrize(("models_flag", "expected_tables"), [(False, 1), (True, 2)])
def test_cmd_stats_tables(models_flag, expected_tables):
    ui = MagicMock()
    sm = MagicMock()
    sm.list_sessions.return_value = [{"name": "s", "model": "gpt", "history_len": 2}]
    with (
        patch.object(cs, "SessionManager", return_value=sm),
        patch("apex.cost_local.MODEL_PRICING", {}),
        patch.object(cs, "Table", FakeTable),
    ):
        cs._cmd_stats(_ns(days=7, models_flag=models_flag), ui)
    assert ui.console.print.call_count == expected_tables


def test_cmd_export_missing_id():
    ui = MagicMock()
    with pytest.raises(SystemExit) as exc:
        cs._cmd_export(_ns(session_id=None), ui)
    assert exc.value.code == 1


@pytest.mark.parametrize(
    ("use_export", "target"), [(True, cs._cmd_export), (False, cs._cmd_import)]
)
@pytest.mark.parametrize("return_value", [None])
def test_cmd_share_missing_exits(use_export, target, return_value):
    share = MagicMock()
    if use_export:
        share.export_session.return_value = return_value
    else:
        share.import_session.return_value = return_value
    ui = MagicMock()
    with (
        patch("apex.share.share_manager", share),
        pytest.raises(SystemExit) as exc,
    ):
        target(_ns(session_id="abc", file="/tmp/x.json"), ui)
    assert exc.value.code == 1
    ui.print_error.assert_called_once()


def test_cmd_export_writes_file(tmp_path, monkeypatch):
    share = MagicMock()
    share.export_session.return_value = {"name": "s"}
    monkeypatch.chdir(tmp_path)
    ui = MagicMock()
    with patch("apex.share.share_manager", share):
        cs._cmd_export(_ns(session_id="abc"), ui)
    out = tmp_path / "session_abc.json"
    assert json.loads(out.read_text()) == {"name": "s"}
    assert "Exported to" in ui.print_success.call_args.args[0]


def test_cmd_export_sanitize(tmp_path, monkeypatch):
    share = MagicMock()
    share.export_session.return_value = {"name": "s"}
    share.sanitize_session_data.return_value = {"sanitized": True}
    monkeypatch.chdir(tmp_path)
    ui = MagicMock()
    with patch("apex.share.share_manager", share):
        cs._cmd_export(_ns(session_id="abc", sanitize=True), ui)
    share.sanitize_session_data.assert_called_once_with({"name": "s"})
    assert json.loads((tmp_path / "session_abc.json").read_text()) == {"sanitized": True}


def test_import_url_target_apex_share():
    assert cs._import_url_target("apex://share/xyz123") == "https://apex-ai.dev/s/xyz123.json"
    assert cs._import_url_target("https://example.com/a.json") == "https://example.com/a.json"


def test_import_from_url_success(fake_home, monkeypatch):
    sm = MagicMock()
    sm._generate_id.return_value = "gen1"
    resp = MagicMock()
    resp.read.return_value = b'{"name": "remote"}'
    monkeypatch.setattr("urllib.request.urlopen", lambda url: resp)
    ui = MagicMock()
    cs._import_from_url("https://example.com/s.json", sm, ui)
    out = fake_home / ".apex" / "sessions" / "imported_gen1.json"
    assert json.loads(out.read_text()) == {"name": "remote"}
    assert "Imported from URL" in ui.print_success.call_args.args[0]


def test_import_from_url_error(fake_home, monkeypatch):
    def boom(url):
        raise OSError("network down")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    ui = MagicMock()
    with pytest.raises(SystemExit) as exc:
        cs._import_from_url("https://example.com/s.json", MagicMock(), ui)
    assert exc.value.code == 1
    assert "Failed to import" in ui.print_error.call_args.args[0]


def test_cmd_import_missing_file():
    ui = MagicMock()
    with pytest.raises(SystemExit) as exc:
        cs._cmd_import(_ns(file=None), ui)
    assert exc.value.code == 1


def test_cmd_import_url_route():
    ui = MagicMock()
    with (
        patch.object(cs, "_import_from_url") as mock_url,
        patch("apex.share.share_manager"),
    ):
        cs._cmd_import(_ns(file="https://example.com/s.json"), ui)
    mock_url.assert_called_once()


def test_cmd_import_file_success():
    sm = MagicMock()
    sm.import_session.return_value = "session-1"
    ui = MagicMock()
    with (
        patch("apex.share.share_manager", sm),
        patch.object(Path, "cwd", return_value=Path("/tmp")),
    ):
        cs._cmd_import(_ns(file="/tmp/x.json"), ui)
    sm.import_session.assert_called_once_with("/tmp/x.json")
    assert "Imported session" in ui.print_success.call_args.args[0]


def test_cmd_compact_success():
    ui = MagicMock()
    agent = MagicMock()
    agent.history = [1, 2, 3, 4, 5]
    with patch.object(cs, "Agent", return_value=agent):
        cs._cmd_compact(_ns(), ui)
    agent.compact_context.assert_called_once()
    assert "5 → 5" in ui.print_success.call_args.args[0]


def test_cmd_compact_no_agent():
    ui = MagicMock()
    agent = MagicMock()
    del agent.compact_context
    with patch.object(cs, "Agent", return_value=agent):
        cs._cmd_compact(_ns(), ui)
    ui.print_info.assert_called_once_with("Compaction not available in this context")


def test_db_query_empty():
    ui = MagicMock()
    cs._db_query(["db"], ui)
    ui.print_error.assert_called_once()


def test_db_query_no_db_file(fake_home):
    ui = MagicMock()
    cs._db_query(["db", "SELECT 1"], ui)
    ui.print_info.assert_called_once()


@pytest.mark.parametrize(("row_count", "expect_more"), [(2, False), (60, True)])
def test_db_query_table(fake_home, row_count, expect_more):
    db = fake_home / ".apex"
    db.mkdir(parents=True)
    conn = sqlite3.connect(str(db / "api_keys.db"))
    conn.execute("CREATE TABLE t (id INTEGER)")
    conn.executemany("INSERT INTO t VALUES (?)", [(i,) for i in range(row_count)])
    conn.commit()
    conn.close()
    ui = MagicMock()
    cs._db_query(["db", "SELECT * FROM t"], ui)
    assert ui.console.print.call_count >= 3  # header + separator + rows
    if expect_more:
        assert any("... and 10 more rows" in str(c) for c in ui.console.print.call_args_list)


def test_db_query_sql_error(fake_home):
    db = fake_home / ".apex"
    db.mkdir(parents=True)
    sqlite3.connect(str(db / "api_keys.db")).close()
    ui = MagicMock()
    cs._db_query(["db", "SELECT * FROM missing"], ui)
    assert "Database error" in ui.print_error.call_args.args[0]


def test_cmd_db_path(fake_home, capsys):
    (fake_home / ".apex").mkdir(parents=True)
    (fake_home / ".apex" / "api_keys.db").write_text("")
    cs._cmd_db(_ns(raw_args=["db", "path"], db_subcommand="path"), MagicMock())
    out = capsys.readouterr().out
    assert str(fake_home / ".apex" / "api_keys.db") in out


def test_cmd_db_query_dispatch():
    ui = MagicMock()
    with patch.object(cs, "_db_query") as mock_q:
        cs._cmd_db(_ns(raw_args=["db", "query", "SELECT 1"], db_subcommand="query"), ui)
    mock_q.assert_called_once_with(["db", "query", "SELECT 1"], ui)


def test_cmd_db_unknown():
    ui = MagicMock()
    cs._cmd_db(_ns(raw_args=["db"], db_subcommand=""), ui)
    ui.print_info.assert_called_once()
