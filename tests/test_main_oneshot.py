"""Tests for apex/main.py — model listing, one-shot runs and CI/CD mode."""

import json
from unittest.mock import MagicMock, patch

from apex import main as main_module
from apex.main import (
    CicdOptions,
    OneShotOptions,
    _build_model_row,
    _matches_provider_filter,
    _print_cicd_output,
    _run_auto_commit,
    list_models,
    run_cicd_mode,
    run_one_shot,
)


def make_agent(reply="hello"):

    agent = MagicMock()

    agent.chat.return_value = reply

    agent.model = "gpt-4o"

    agent.usage = {}

    return agent


class TestProviderFilter:
    def test_no_filter_matches_all(self):

        assert _matches_provider_filter("gpt-4o", "openai/gpt-4o", None)

        assert _matches_provider_filter("gpt-4o", "openai/gpt-4o", "")

    def test_matches_alias(self):

        assert _matches_provider_filter("gemini-2.5-pro", "google/gemini", "gemini")

    def test_matches_model_id(self):

        assert _matches_provider_filter("my-model", "anthropic/claude", "claude")

    def test_case_insensitive(self):

        assert _matches_provider_filter("gpt-4o", "openai/gpt-4o", "OPENAI")

    def test_no_match(self):

        assert not _matches_provider_filter("gpt-4o", "openai/gpt-4o", "gemini")


class TestBuildModelRow:
    def test_without_price(self):

        row = _build_model_row("plainmodel", "pid", "other", verbose=False)

        assert row == ("  plainmodel", "unknown", "pid", "", "")

    def test_provider_from_alias(self):

        row = _build_model_row("anthropic-x", "pid", "other", verbose=False)

        assert row[1] == "anthropic"

    def test_marker_on_configured_model(self):

        row = _build_model_row("gpt-4o", "pid", "gpt-4o", verbose=False)

        assert "✓" in row[0]

    def test_with_price(self):

        from apex.cost_local import MODEL_PRICING

        priced = next(iter(MODEL_PRICING))

        row = _build_model_row(priced, "pid", "other", verbose=True)

        assert row[0].endswith(priced)

        assert row[3].startswith("$")

        assert row[4].startswith("$")


class TestListModels:
    def test_filtering_and_print(self, monkeypatch):

        monkeypatch.setattr(main_module, "apex_config", MagicMock(model="gpt-4o"))

        ui = MagicMock()

        rows = []

        class FakeTable:
            def __init__(self, **kwargs):

                pass

            def add_column(self, *args, **kwargs):

                pass

            def add_row(self, *cells):

                rows.append(cells)

        with (
            patch.object(
                main_module,
                "MODELS",
                {"gpt-4o": "openai/gpt-4o", "gemini-x": "google/gemini"},
            ),
            patch.object(main_module, "Table", FakeTable),
        ):
            list_models(ui, provider_filter="gpt", verbose=False)

        assert len(rows) == 1

        assert "gpt-4o" in rows[0][0]

        ui.console.print.assert_called_once()

    def test_refresh_prints_info(self, monkeypatch):

        monkeypatch.setattr(main_module, "apex_config", MagicMock(model="gpt-4o"))

        ui = MagicMock()

        class FakeTable:
            def __init__(self, **kwargs):

                pass

            def add_column(self, *args, **kwargs):

                pass

            def add_row(self, *cells):

                pass

        with (
            patch.object(main_module, "MODELS", {}),
            patch.object(main_module, "Table", FakeTable),
        ):
            list_models(ui, refresh=True)

        ui.print_success.assert_called_once_with("Refreshing model list...")


class TestCicdHelpers:
    def test_cicd_json_result(self):

        agent = make_agent()

        result = main_module._cicd_json_result("p", "r", agent, None)

        assert result == {
            "success": True,
            "prompt": "p",
            "response": "r",
            "model": "gpt-4o",
            "usage": {},
        }

    def test_cicd_json_result_with_auto_commit(self):

        agent = make_agent()

        ac = {"status": "committed", "sha": "abc1234"}

        result = main_module._cicd_json_result("p", "r", agent, ac)

        assert result["auto_commit"] == ac

    def test_print_cicd_output_quiet(self, capsys):

        ui = MagicMock()

        _print_cicd_output(ui, "out", quiet=True)

        assert "out" in capsys.readouterr().out

        ui.print_response.assert_not_called()

    def test_print_cicd_output_loud(self):

        ui = MagicMock()

        _print_cicd_output(ui, "out", quiet=False)

        ui.print_response.assert_called_once_with("out")


class TestRunCicdMode:
    def test_text_output(self):

        ui = MagicMock()

        run_cicd_mode("p", make_agent(), ui, CicdOptions(output_format="text", quiet=False))

        ui.print_response.assert_called_once_with("hello")

    def test_json_output(self, capsys):

        ui = MagicMock()

        run_cicd_mode("p", make_agent(), ui, CicdOptions(output_format="json", quiet=True))

        data = json.loads(capsys.readouterr().out)

        assert data["success"] is True

        assert data["response"] == "hello"

    def test_error_json(self, capsys):

        ui = MagicMock()

        agent = make_agent()

        agent.chat.side_effect = RuntimeError("boom")

        run_cicd_mode("p", agent, ui, CicdOptions(output_format="json", quiet=True))

        data = json.loads(capsys.readouterr().out)

        assert data == {"success": False, "error": "boom"}

    def test_error_text(self):

        ui = MagicMock()

        agent = make_agent()

        agent.chat.side_effect = RuntimeError("boom")

        run_cicd_mode("p", agent, ui, CicdOptions(output_format="text", quiet=False))

        ui.print_error.assert_called_once_with("Error: boom")

    def test_auto_commit_included(self, capsys):

        ui = MagicMock()

        with patch.object(
            main_module, "_run_auto_commit", return_value={"status": "no-changes"}
        ) as mock_ac:
            run_cicd_mode(
                "p",
                make_agent(),
                ui,
                CicdOptions(output_format="json", quiet=True, auto_commit_after=True),
            )

        mock_ac.assert_called_once()

        data = json.loads(capsys.readouterr().out)

        assert data["auto_commit"] == {"status": "no-changes"}


class TestRunOneShot:
    def test_streaming(self):

        ui = MagicMock()

        agent = MagicMock()

        agent.chat.return_value = iter(["a", "b"])

        run_one_shot("p", agent, ui, OneShotOptions(use_stream=True))

        ui.console.print.assert_any_call("a", end="")

        ui.console.print.assert_any_call("b", end="")

    def test_blocking(self):

        ui = MagicMock()

        agent = make_agent("done")

        run_one_shot("p", agent, ui)

        ui.print_response.assert_called_once_with("done")

    def test_auto_commit(self):

        ui = MagicMock()

        agent = make_agent("done")

        with patch.object(main_module, "_run_auto_commit") as mock_ac:
            run_one_shot("p", agent, ui, OneShotOptions(auto_commit_after=True))

        mock_ac.assert_called_once_with(agent, "p", ui)


class TestRunAutoCommit:
    @patch.object(main_module, "auto_commit")
    def test_committed(self, mock_ac):

        mock_ac.return_value = {"status": "committed", "sha": "abcdef123", "message": "fix: x"}

        ui, agent = MagicMock(), MagicMock(cwd="/tmp/x")

        result = _run_auto_commit(agent, "task", ui)

        assert result["status"] == "committed"

        ui.print_info.assert_called_once_with("Auto-committed abcdef1: fix: x")

    @patch.object(main_module, "auto_commit")
    def test_no_changes(self, mock_ac):

        mock_ac.return_value = {"status": "no-changes"}

        ui, agent = MagicMock(), MagicMock(cwd="/tmp/x")

        _run_auto_commit(agent, "t", ui)

        ui.print_info.assert_called_once_with("Auto-commit: no changes to commit")

    @patch.object(main_module, "auto_commit")
    def test_no_changes_quiet(self, mock_ac):

        mock_ac.return_value = {"status": "no-changes"}

        ui, agent = MagicMock(), MagicMock(cwd="/tmp/x")

        _run_auto_commit(agent, "t", ui, quiet=True)

        ui.print_info.assert_not_called()

    @patch.object(main_module, "auto_commit")
    def test_not_a_repo(self, mock_ac):

        mock_ac.return_value = {"status": "not-a-repo"}

        ui, agent = MagicMock(), MagicMock(cwd="/tmp/x")

        _run_auto_commit(agent, "t", ui)

        ui.print_info.assert_called_once_with("Auto-commit skipped: not a git repository")

    @patch.object(main_module, "auto_commit")
    def test_error(self, mock_ac):

        mock_ac.return_value = {"status": "error", "error": "git died"}

        ui, agent = MagicMock(), MagicMock(cwd="/tmp/x")

        _run_auto_commit(agent, "t", ui)

        ui.print_error.assert_called_once_with("Auto-commit failed: git died")
