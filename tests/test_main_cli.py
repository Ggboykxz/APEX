"""Tests for apex/main.py — CLI dispatch and verb routing."""

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from apex import main as main_module
from apex.main import (
    _apply_verb_overrides,
    _default_verb_namespace,
    _dispatch_verb,
    _is_mcp_serve,
    _paired_verb_parts,
    _parse_mcp_serve_args,
    _resolve_verb_handler,
    _run_direct_verb,
    _run_mcp_serve_if_requested,
    _run_paired_verb,
    _run_parsed,
    _run_subcommand,
    build_parser,
    main,
)


class TestMcpServe:
    def test_parse_args(self):

        cwd, allow = _parse_mcp_serve_args(
            ["--cwd", "/x", "--allow-tool", "a", "--allow-tool", "b"]
        )

        assert cwd == "/x"

        assert allow == ["a", "b"]

    def test_parse_short_cwd(self):

        cwd, allow = _parse_mcp_serve_args(["-C", "/y"])

        assert cwd == "/y"

        assert allow == []

    def test_unknown_arg_exits(self):

        with pytest.raises(SystemExit) as exc:
            _parse_mcp_serve_args(["--bogus"])

        assert exc.value.code == 2

    def test_is_mcp_serve(self):

        assert _is_mcp_serve(["mcp", "serve"])

        assert _is_mcp_serve(["MCP", "serve"])

        assert not _is_mcp_serve(["mcp"])

        assert not _is_mcp_serve(["mcp", "list"])

        assert not _is_mcp_serve([])

    def test_run_not_requested(self):

        assert _run_mcp_serve_if_requested(["models"]) is None

    def test_run_help_exits(self, capsys):

        with pytest.raises(SystemExit) as exc:
            _run_mcp_serve_if_requested(["mcp", "serve", "--help"])

        assert exc.value.code == 0

        assert "usage: apex mcp serve" in capsys.readouterr().err

    def test_run_calls_serve(self):

        with (
            patch("apex.mcp_server.serve", return_value=0) as mock_serve,
            pytest.raises(SystemExit),
        ):
            _run_mcp_serve_if_requested(["mcp", "serve", "--cwd", "/x"])

        mock_serve.assert_called_once_with(cwd=Path("/x"), allow_tools=[])


class TestPairedVerbs:
    def test_parts_explicit_subcommand(self):

        assert _paired_verb_parts("auth", ["auth", "login"]) == ("login", [])

    def test_parts_ls_alias(self):

        assert _paired_verb_parts("session", ["session", "ls"]) == ("list", [])

    def test_parts_defaults(self):

        assert _paired_verb_parts("auth", ["auth"]) == ("login", [])

        assert _paired_verb_parts("agent", ["agent"]) == ("list", [])

        assert _paired_verb_parts("mcp", ["mcp"]) == ("list", [])

        assert _paired_verb_parts("db", ["db"]) == ("path", [])

    def test_parts_flag_uses_default(self):

        assert _paired_verb_parts("session", ["session", "--json"]) == (
            "list",
            ["--json"],
        )

    def test_parts_keeps_rest(self):

        assert _paired_verb_parts("auth", ["auth", "logout", "gpt"]) == (
            "logout",
            ["gpt"],
        )

    def test_run_paired_verb_unknown(self):

        assert _run_paired_verb(build_parser(), ["models"]) is False

    def test_run_paired_verb_dispatches_subcommand_attr(self):

        with patch.object(main_module, "_dispatch_verb") as mock_disp:
            assert _run_paired_verb(build_parser(), ["auth", "login"]) is True

        verb, parsed = mock_disp.call_args.args

        assert verb == "auth"

        assert parsed.auth_subcommand == "login"

        assert parsed.prompt is None

    def test_run_paired_verb_fills_positional_attr(self):

        with patch.object(main_module, "_dispatch_verb") as mock_disp:
            _run_paired_verb(build_parser(), ["auth", "logout", "gpt"])

        parsed = mock_disp.call_args.args[1]

        assert parsed.auth_subcommand == "logout"

        assert parsed.auth_provider == "gpt"

    def test_run_paired_verb_session_delete_id(self):

        with patch.object(main_module, "_dispatch_verb") as mock_disp:
            _run_paired_verb(build_parser(), ["session", "delete", "abc123"])

        parsed = mock_disp.call_args.args[1]

        assert parsed.session_subcommand == "delete"

        assert parsed.session_id == "abc123"

    def test_run_paired_verb_mcp_name(self):

        with patch.object(main_module, "_dispatch_verb") as mock_disp:
            _run_paired_verb(build_parser(), ["mcp", "auth", "gh"])

        parsed = mock_disp.call_args.args[1]

        assert parsed.mcp_subcommand == "auth"

        assert parsed.mcp_name == "gh"

    def test_run_paired_verb_merges_global_flags(self):

        with patch.object(main_module, "_dispatch_verb") as mock_disp:
            _run_paired_verb(build_parser(), ["auth", "login", "-m", "gpt-4o"])

        parsed = mock_disp.call_args.args[1]

        assert parsed.model == "gpt-4o"

        assert parsed.auth_provider is None


class TestDirectVerbs:
    def test_run_direct_verb_unknown(self):

        assert _run_direct_verb(build_parser(), ["nope"]) is False

    def test_run_direct_verb_keeps_raw_args(self):

        with patch.object(main_module, "_dispatch_verb") as mock_disp:
            assert _run_direct_verb(build_parser(), ["serve", "--port", "9999"]) is True

        parsed = mock_disp.call_args.args[1]

        assert parsed.raw_args == ["--port", "9999"]

    def test_run_direct_verb_upgrade_applies_overrides(self):

        with patch.object(main_module, "_dispatch_verb") as mock_disp:
            _run_direct_verb(build_parser(), ["upgrade", "--check"])

        parsed = mock_disp.call_args.args[1]

        assert parsed.check is True

    def test_run_direct_verb_run_carries_prompt(self):

        with patch.object(main_module, "_dispatch_verb") as mock_disp:
            assert _run_direct_verb(build_parser(), ["run", "do the thing"]) is True

        verb, parsed = mock_disp.call_args.args

        assert verb == "run"

        assert parsed.prompt == "do the thing"

        assert parsed.raw_args == ["do the thing"]

    def test_run_direct_verb_run_with_flags(self):

        with patch.object(main_module, "_dispatch_verb") as mock_disp:
            _run_direct_verb(build_parser(), ["run", "task", "-m", "gpt-4o", "-q"])

        parsed = mock_disp.call_args.args[1]

        assert parsed.prompt == "task"

        assert parsed.model == "gpt-4o"

        assert parsed.quiet is True

    def test_run_direct_verb_run_without_prompt(self):

        with patch.object(main_module, "_dispatch_verb") as mock_disp:
            _run_direct_verb(build_parser(), ["run", "--model", "gpt-4o"])

        parsed = mock_disp.call_args.args[1]

        assert parsed.prompt is None


class TestSubcommands:
    def test_empty(self):

        assert _run_subcommand(build_parser(), []) is False

    def test_unknown(self):

        assert _run_subcommand(build_parser(), ["serve"]) is False

    def test_models(self):

        with patch.object(main_module, "_dispatch") as mock_disp:
            assert _run_subcommand(build_parser(), ["models"]) is True

        parsed = mock_disp.call_args.args[0]

        assert parsed.list_models is True

        assert parsed.prompt is None

        assert parsed.provider_filter is None

    def test_models_with_provider_filter(self):

        with patch.object(main_module, "_dispatch") as mock_disp:
            assert _run_subcommand(build_parser(), ["models", "gpt"]) is True

        parsed = mock_disp.call_args.args[0]

        assert parsed.list_models is True

        assert parsed.provider_filter == "gpt"

        assert parsed.prompt is None

    def test_models_with_flags(self):

        with patch.object(main_module, "_dispatch") as mock_disp:
            _run_subcommand(build_parser(), ["models", "--verbose"])

        parsed = mock_disp.call_args.args[0]

        assert parsed.provider_filter is None

        assert parsed.verbose is True

    def test_tui(self):

        with patch.object(main_module, "_dispatch") as mock_disp:
            assert _run_subcommand(build_parser(), ["tui"]) is True

        assert mock_disp.call_args.args[0].tui is True


class TestVerbDispatch:
    def test_resolve_known(self):

        assert _resolve_verb_handler("serve") is main_module._cmd_serve

    def test_resolve_unknown(self):

        assert _resolve_verb_handler("nope") is None

    def test_dispatch_verb_with_handler(self):

        parsed = argparse.Namespace()

        with (
            patch.object(main_module, "UI") as mock_ui,
            patch.object(main_module, "_cmd_serve") as mock_serve,
        ):
            _dispatch_verb("serve", parsed)

        mock_serve.assert_called_once_with(parsed, mock_ui.return_value)

    def test_dispatch_verb_init_uses_ui_only(self):

        with (
            patch.object(main_module, "UI") as mock_ui,
            patch.object(main_module, "_cmd_init") as mock_init,
        ):
            _dispatch_verb("init", argparse.Namespace())

        mock_init.assert_called_once_with(mock_ui.return_value)

    def test_dispatch_verb_unknown_with_prompt(self):

        parsed = argparse.Namespace(prompt="do it")

        with (
            patch.object(main_module, "UI"),
            patch.object(main_module, "_dispatch") as mock_d,
        ):
            _dispatch_verb("unknown", parsed)

        mock_d.assert_called_once_with(parsed)

    def test_dispatch_verb_unknown_exits(self):

        with (
            patch.object(main_module, "UI") as mock_ui,
            pytest.raises(SystemExit) as exc,
        ):
            _dispatch_verb("unknown", argparse.Namespace(prompt=None))

        assert exc.value.code == 1

        assert "Unknown command: unknown" in mock_ui.return_value.print_error.call_args.args[0]

    def test_run_parsed_dispatches(self):

        with patch.object(main_module, "_dispatch") as mock_disp:
            _run_parsed(build_parser(), ["--port", "1234"])

        assert mock_disp.call_args.args[0].port == 1234

    def test_run_parsed_bad_flag_exits(self):

        with pytest.raises(SystemExit) as exc:
            _run_parsed(build_parser(), ["--bogus"])

        assert exc.value.code == 1


class TestVerbNamespace:
    def test_defaults(self):

        parsed = _default_verb_namespace()

        assert parsed.prompt is None

        assert parsed.model is None

        assert parsed.output_format == "text"

        assert parsed.quiet is False

        assert parsed.port is None

        assert parsed.dry_run is False

    def test_apply_overrides(self):

        parsed = _default_verb_namespace()

        _apply_verb_overrides(build_parser(), ["--check", "--method", "npm"], parsed)

        assert parsed.check is True

        assert parsed.method == "npm"

    def test_apply_overrides_keeps_prompt(self):

        parsed = _default_verb_namespace()

        parsed.prompt = "keep me"

        _apply_verb_overrides(build_parser(), ["--check"], parsed)

        assert parsed.prompt == "keep me"

    def test_apply_overrides_ignores_unknown_flags(self):

        parsed = _default_verb_namespace()

        _apply_verb_overrides(build_parser(), ["--bogus"], parsed)

        assert parsed.check is False

        assert parsed.model is None

    def test_apply_overrides_invalid_choice_exits(self):

        with pytest.raises(SystemExit) as exc:
            _apply_verb_overrides(build_parser(), ["-f", "bogus"], _default_verb_namespace())

        assert exc.value.code == 1


class TestMain:
    def test_help(self, monkeypatch):

        monkeypatch.setattr(sys, "argv", ["apex", "--help"])

        with (
            patch.object(main_module, "_prepare_runtime"),
            pytest.raises(SystemExit) as exc,
        ):
            main()

        assert exc.value.code == 0

    def test_empty_argv_defaults_to_tui(self, monkeypatch):

        monkeypatch.setattr(sys, "argv", ["apex"])

        with (
            patch.object(main_module, "_prepare_runtime"),
            patch.object(main_module, "_run_mcp_serve_if_requested"),
            patch.object(main_module, "_run_subcommand", return_value=True) as mock_sub,
        ):
            main()

        assert mock_sub.call_args.args[1] == ["tui"]

    def test_mcp_serve_precedes_parsing(self, monkeypatch):

        monkeypatch.setattr(sys, "argv", ["apex", "mcp", "serve", "--cwd", "/x"])

        with (
            patch.object(main_module, "_prepare_runtime"),
            # The real mcp serve path never returns: it runs the server and
            # exits. Simulate that so dispatch is provably unreachable.
            patch.object(
                main_module, "_run_mcp_serve_if_requested", side_effect=SystemExit(0)
            ) as mock_mcp,
            patch.object(main_module, "_run_subcommand") as mock_sub,
            pytest.raises(SystemExit) as exc,
        ):
            main()

        assert exc.value.code == 0

        mock_mcp.assert_called_once_with(["mcp", "serve", "--cwd", "/x"])

        mock_sub.assert_not_called()

    def test_subcommand_wins(self, monkeypatch):

        monkeypatch.setattr(sys, "argv", ["apex", "models"])

        with (
            patch.object(main_module, "_prepare_runtime"),
            patch.object(main_module, "_run_mcp_serve_if_requested"),
            patch.object(main_module, "_run_subcommand", return_value=True),
            patch.object(main_module, "_run_paired_verb") as mock_paired,
            patch.object(main_module, "_run_direct_verb") as mock_direct,
            patch.object(main_module, "_run_parsed") as mock_parsed,
        ):
            main()

        mock_paired.assert_not_called()

        mock_direct.assert_not_called()

        mock_parsed.assert_not_called()

    def test_paired_verb_wins(self, monkeypatch):

        monkeypatch.setattr(sys, "argv", ["apex", "auth", "login"])

        with (
            patch.object(main_module, "_prepare_runtime"),
            patch.object(main_module, "_run_mcp_serve_if_requested"),
            patch.object(main_module, "_run_subcommand", return_value=False),
            patch.object(main_module, "_run_paired_verb", return_value=True),
            patch.object(main_module, "_run_direct_verb") as mock_direct,
            patch.object(main_module, "_run_parsed") as mock_parsed,
        ):
            main()

        mock_direct.assert_not_called()

        mock_parsed.assert_not_called()

    def test_direct_verb_wins(self, monkeypatch):

        monkeypatch.setattr(sys, "argv", ["apex", "upgrade", "--check"])

        with (
            patch.object(main_module, "_prepare_runtime"),
            patch.object(main_module, "_run_mcp_serve_if_requested"),
            patch.object(main_module, "_run_subcommand", return_value=False),
            patch.object(main_module, "_run_paired_verb", return_value=False),
            patch.object(main_module, "_run_direct_verb", return_value=True),
            patch.object(main_module, "_run_parsed") as mock_parsed,
        ):
            main()

        mock_parsed.assert_not_called()

    def test_falls_through_to_parsed(self, monkeypatch):

        monkeypatch.setattr(sys, "argv", ["apex", "some-prompt"])

        with (
            patch.object(main_module, "_prepare_runtime"),
            patch.object(main_module, "_run_mcp_serve_if_requested"),
            patch.object(main_module, "_run_subcommand", return_value=False),
            patch.object(main_module, "_run_paired_verb", return_value=False),
            patch.object(main_module, "_run_direct_verb", return_value=False),
            patch.object(main_module, "_run_parsed") as mock_parsed,
        ):
            main()

        mock_parsed.assert_called_once_with(mock_parsed.call_args.args[0], ["some-prompt"])
