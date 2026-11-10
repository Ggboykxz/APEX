"""Tests for apex/cli_misc.py — agent wizard, run dispatch, PR and github commands."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apex import cli_misc as cs


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


def _ns(**kw):
    base = {
        "model": None,
        "agent_name": None,
        "resume": False,
        "session_id": None,
        "prompt": None,
        "input_file": None,
        "output_format": "text",
        "stream": False,
        "pr_number": None,
        "agent_subcommand": None,
        "raw_args": [],
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


class TestListAgents:
    def test_empty(self):
        ui = MagicMock()
        with patch.object(cs, "agent_manager") as mgr:
            mgr.list_agents.return_value = []
            cs._list_agents(ui)
        ui.print_info.assert_called_once_with("No agents configured")

    def test_table(self):
        ui = MagicMock()
        agent = MagicMock()
        agent.name = "reviewer"
        agent.mode = "subagent"
        agent.model = "gpt-4o"
        agent.description = "Reviews code"
        with (
            patch.object(cs, "agent_manager") as mgr,
            patch.object(cs, "Table", FakeTable),
        ):
            mgr.list_agents.return_value = [agent]
            cs._list_agents(ui)
        table = ui.console.print.call_args.args[0]
        assert table.rows == [("reviewer", "subagent", "gpt-4o", "Reviews code")]


class TestCreateAgent:
    def test_name_required(self):
        ui = MagicMock()
        ui.input.return_value = "   "
        with (
            patch.object(cs, "agent_manager"),
            pytest.raises(SystemExit) as exc,
        ):
            cs._create_agent(ui)
        assert exc.value.code == 1
        ui.print_error.assert_called_once()

    def test_creates_file(self, fake_home):
        ui = MagicMock()
        ui.input.side_effect = ["review", "Reviews things", "", "", "allow", "deny", "ask"]
        with patch.object(cs, "agent_manager") as mgr:
            cs._create_agent(ui)
        agent_file = fake_home / ".config" / "apex" / "agents" / "review.md"
        assert agent_file.exists()
        content = agent_file.read_text()
        assert "description: Reviews things" in content
        assert "mode: subagent" in content
        assert "read: allow" in content
        assert "edit: deny" in content
        assert "bash: ask" in content
        mgr.load_markdown_agents.assert_called_once()
        assert "created at" in ui.print_success.call_args.args[0]


class TestCmdAgentCreateDispatch:
    def test_create(self):
        with patch.object(cs, "_create_agent") as mock_create:
            cs._cmd_agent(_ns(agent_subcommand="create"), MagicMock())
        mock_create.assert_called_once()


class TestCmdRun:
    @pytest.mark.parametrize(
        ("output_format", "stream"),
        [("text", False), ("text", True), ("json", False)],
    )
    def test_routes(self, output_format, stream):
        ui = MagicMock()
        agent = MagicMock()
        with (
            patch.object(cs, "_build_run_agent", return_value=agent),
            patch.object(cs, "_load_run_session"),
            patch.object(cs, "_resolve_run_prompt", return_value="hi"),
            patch("apex.main.run_one_shot") as mock_one,
            patch.object(cs, "_run_json") as mock_json,
        ):
            cs._cmd_run(_ns(prompt="hi", output_format=output_format, stream=stream), ui)
        if output_format == "json":
            mock_json.assert_called_once_with("hi", agent)
            mock_one.assert_not_called()
        else:
            mock_one.assert_called_once()
            assert mock_one.call_args.args[3].use_stream is stream
            mock_json.assert_not_called()


class TestCmdPr:
    def test_missing_number(self):
        ui = MagicMock()
        with pytest.raises(SystemExit) as exc:
            cs._cmd_pr(_ns(pr_number=None), ui)
        assert exc.value.code == 1

    def test_gh_missing(self):
        ui = MagicMock()
        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            pytest.raises(SystemExit) as exc,
        ):
            cs._cmd_pr(_ns(pr_number=7), ui)
        assert exc.value.code == 1
        assert "gh CLI not found" in ui.print_error.call_args.args[0]

    def test_view_failure(self):
        ui = MagicMock()
        view = MagicMock(returncode=1, stderr="boom")
        with (
            patch("subprocess.run", return_value=view),
            pytest.raises(SystemExit) as exc,
        ):
            cs._cmd_pr(_ns(pr_number=7), ui)
        assert exc.value.code == 1
        assert "Failed to fetch PR #7" in ui.print_error.call_args.args[0]

    def test_checkout_success(self):
        ui = MagicMock()
        view = MagicMock(returncode=0, stdout='{"headRefName": "feat/x"}')
        checkout = MagicMock(returncode=0)
        with patch("subprocess.run", side_effect=[view, checkout]):
            cs._cmd_pr(_ns(pr_number=7), ui)
        assert "Checked out PR #7" in ui.print_success.call_args.args[0]

    def test_checkout_failure(self):
        ui = MagicMock()
        view = MagicMock(returncode=0, stdout='{"headRefName": "feat/x"}')
        checkout = MagicMock(returncode=1, stderr="conflict")
        with (
            patch("subprocess.run", side_effect=[view, checkout]),
            pytest.raises(SystemExit) as exc,
        ):
            cs._cmd_pr(_ns(pr_number=7), ui)
        assert exc.value.code == 1
        assert "Failed to checkout" in ui.print_error.call_args.args[0]


class TestCmdGithub:
    def test_install(self):
        ui = MagicMock()
        cs._cmd_github(_ns(raw_args=["install"]), ui)
        assert "Installing GitHub agent" in ui.print_info.call_args_list[0].args[0]

    def test_run(self):
        ui = MagicMock()
        gh = MagicMock()
        gh.client.list_issues.return_value = [1, 2]
        gh.client.list_prs.return_value = [3]
        with patch("apex.github_integration.gh_automation", gh):
            cs._cmd_github(_ns(raw_args=["run"]), ui)
        assert "Found 2 issues and 1 PRs" in ui.print_success.call_args.args[0]

    def test_usage(self):
        ui = MagicMock()
        cs._cmd_github(_ns(raw_args=[]), ui)
        joined = " ".join(str(c) for c in ui.print_info.call_args_list)
        assert "Usage: apex github install|run" in joined
