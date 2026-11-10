"""Tests for apex/cli_misc.py — pure helpers."""

import json
from unittest.mock import MagicMock, patch

from apex import cli_misc, cli_sessions


def test_agent_definition():
    spec = {
        "desc": "Reviews code",
        "mode": "subagent",
        "model": "gpt-4o",
        "perms": {"read": "allow", "edit": "deny", "bash": "ask"},
    }
    out = cli_misc._agent_definition("reviewer", spec)
    assert "reviewer" in out
    assert "Reviews code" in out
    assert "mode: subagent" in out
    assert "model: gpt-4o" in out
    assert "read: allow" in out
    assert "edit: deny" in out


def test_agent_definition_no_model():
    spec = {
        "desc": "Explains",
        "mode": "primary",
        "model": None,
        "perms": {"read": "allow", "edit": "allow", "bash": "allow"},
    }
    out = cli_misc._agent_definition("explainer", spec)
    assert "model: " in out
    assert "explainer" in out


def test_resolve_run_prompt_from_arg():
    args = type("Args", (), {"prompt": "hello world", "input_file": None})()
    ui = MagicMock()
    assert cli_misc._resolve_run_prompt(args, ui) == "hello world"


def test_resolve_run_prompt_from_file(tmp_path):
    f = tmp_path / "prompt.txt"
    f.write_text("  file prompt  \n")
    args = type("Args", (), {"prompt": None, "input_file": str(f)})()
    ui = MagicMock()
    assert cli_misc._resolve_run_prompt(args, ui) == "file prompt"


def test_resolve_run_prompt_empty_exits():
    args = type("Args", (), {"prompt": "", "input_file": None})()
    ui = MagicMock()
    with __import__("pytest").raises(SystemExit):
        cli_misc._resolve_run_prompt(args, ui)


def test_build_run_agent():
    args = type("Args", (), {"model": "gpt-4o", "agent_name": None})()
    agent = cli_misc._build_run_agent(args)
    assert agent.model == "gpt-4o"


def test_build_run_agent_with_agent_name():
    args = type("Args", (), {"model": None, "agent_name": "plan"})()
    agent = cli_misc._build_run_agent(args)
    assert agent.current_agent == "plan"


def test_load_run_session_resume():
    args = type("Args", (), {"resume": True, "session_id": None})()
    agent = MagicMock()
    with patch("apex.cli_misc.SessionManager") as mock_sm:
        instance = mock_sm.return_value
        instance.list_sessions.return_value = [{"name": "s1"}]
        cli_misc._load_run_session(args, agent)
        instance.load.assert_called_with("s1", agent)


def test_load_run_session_resume_empty():
    args = type("Args", (), {"resume": True, "session_id": None})()
    agent = MagicMock()
    with patch("apex.cli_misc.SessionManager") as mock_sm:
        instance = mock_sm.return_value
        instance.list_sessions.return_value = []
        cli_misc._load_run_session(args, agent)
        instance.load.assert_not_called()


def test_load_run_session_session_id():
    args = type("Args", (), {"resume": False, "session_id": "abc"})()
    agent = MagicMock()
    with patch("apex.cli_misc.SessionManager") as mock_sm:
        instance = mock_sm.return_value
        cli_misc._load_run_session(args, agent)
        instance.load.assert_called_with("abc", agent)


def test_run_json_success():
    agent = MagicMock()
    agent.chat.return_value = "hello"
    agent.model = "gpt-4o"
    agent.usage = {"prompt_tokens": 10, "completion_tokens": 5}
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli_misc._run_json("test prompt", agent)
    out = json.loads(buf.getvalue())
    assert out["success"] is True
    assert out["response"] == "hello"
    assert out["model"] == "gpt-4o"


def test_run_json_failure():
    agent = MagicMock()
    agent.chat.side_effect = RuntimeError("boom")
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf), __import__("pytest").raises(SystemExit):
        cli_misc._run_json("test prompt", agent)
    out = json.loads(buf.getvalue())
    assert out["success"] is False
    assert "boom" in out["error"]


def test_cmd_details():
    ui = MagicMock()
    args = type("Args", (), {})()
    import unittest.mock as m

    from apex.config_v2 import apex_config

    with m.patch.object(apex_config, "get", return_value=False), m.patch.object(apex_config, "set"):
        cli_misc._cmd_details(args, ui)
    ui.print_success.assert_called()


def test_cmd_thinking():
    ui = MagicMock()
    args = type("Args", (), {})()
    import unittest.mock as m

    from apex.config_v2 import apex_config

    with m.patch.object(apex_config, "get", return_value=True), m.patch.object(apex_config, "set"):
        cli_misc._cmd_thinking(args, ui)
    ui.print_success.assert_called()


def test_import_url_target():
    assert cli_sessions._import_url_target("apex://share/abc") == "https://apex-ai.dev/s/abc.json"
    assert cli_sessions._import_url_target("https://example.com/x") == "https://example.com/x"


def test_cmd_agent_list():
    ui = MagicMock()
    args = type("Args", (), {"agent_subcommand": "list"})()
    import unittest.mock as m

    with m.patch("apex.cli_misc.agent_manager") as am:
        am.list_agents.return_value = []
        cli_misc._cmd_agent(args, ui)
    ui.print_info.assert_called()


def test_cmd_agent_unknown():
    ui = MagicMock()
    args = type("Args", (), {"agent_subcommand": "foo"})()
    with __import__("pytest").raises(SystemExit):
        cli_misc._cmd_agent(args, ui)
