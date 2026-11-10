"""Tests for apex/cli_auth.py — pure helpers and file I/O."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from apex import cli_auth


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def test_auth_file_path(tmp_home):
    assert cli_auth._auth_file() == tmp_home / ".config" / "apex" / "auth.json"


def test_read_auth_missing(tmp_home):
    assert cli_auth._read_auth(tmp_home / "nope.json") == {}


def test_read_auth_valid(tmp_home):
    f = tmp_home / "auth.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"openai": {"api_key": "sk-123", "model": "gpt-4o"}}))
    assert cli_auth._read_auth(f) == {"openai": {"api_key": "sk-123", "model": "gpt-4o"}}


def test_persist_openrouter_env_creates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ui = MagicMock()
    cli_auth._persist_openrouter_env("sk-or-v1-abc", ui)
    env = (tmp_path / ".env").read_text()
    assert "OPENROUTER_API_KEY=sk-or-v1-abc" in env
    ui.print_success.assert_called()


def test_persist_openrouter_env_updates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("FOO=bar\nOPENROUTER_API_KEY=old\nBAZ=qux\n")
    ui = MagicMock()
    cli_auth._persist_openrouter_env("sk-or-v1-new", ui)
    lines = (tmp_path / ".env").read_text().splitlines()
    assert "OPENROUTER_API_KEY=sk-or-v1-new" in lines
    assert "FOO=bar" in lines
    assert "BAZ=qux" in lines


def test_store_openrouter_key(tmp_home):
    cli_auth._store_openrouter_key("sk-or-v1-xyz")
    auth_file = tmp_home / ".config" / "apex" / "auth.json"
    assert auth_file.exists()
    data = json.loads(auth_file.read_text())
    assert data["openrouter"]["api_key"] == "sk-or-v1-xyz"
    assert auth_file.stat().st_mode & 0o777 == 0o600


def test_store_openrouter_key_merges(tmp_home):
    auth_file = tmp_home / ".config" / "apex" / "auth.json"
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    auth_file.write_text(json.dumps({"anthropic": {"api_key": "sk-ant"}}))
    cli_auth._store_openrouter_key("sk-or-v1-xyz")
    data = json.loads(auth_file.read_text())
    assert data["anthropic"]["api_key"] == "sk-ant"
    assert data["openrouter"]["api_key"] == "sk-or-v1-xyz"


def test_write_env_key_creates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli_auth._write_env_key("sk-or-v1-abc")
    env = (tmp_path / ".env").read_text()
    assert "OPENROUTER_API_KEY=sk-or-v1-abc" in env
    assert (tmp_path / ".env").stat().st_mode & 0o777 == 0o600


def test_write_env_key_updates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("FOO=bar\nOPENROUTER_API_KEY=old\n")
    cli_auth._write_env_key("sk-or-v1-new")
    lines = (tmp_path / ".env").read_text().splitlines()
    assert "OPENROUTER_API_KEY=sk-or-v1-new" in lines
    assert "FOO=bar" in lines


def test_warn_missing_gitignore_no_gitignore(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ui = MagicMock()
    cli_auth._warn_missing_gitignore(ui)
    ui.print_warning.assert_called()


def test_warn_missing_gitignore_with_gitignore(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".gitignore").write_text(".env\n")
    ui = MagicMock()
    cli_auth._warn_missing_gitignore(ui)
    ui.print_warning.assert_not_called()


def test_read_openrouter_key_from_args():
    args = type("Args", (), {"key_value": "sk-or-v1-abc", "prompt": None})()
    ui = MagicMock()
    assert cli_auth._read_openrouter_key(args, ui) == "sk-or-v1-abc"


def test_read_openrouter_key_from_prompt():
    args = type("Args", (), {"key_value": None, "prompt": "sk-or-v1-xyz"})()
    ui = MagicMock()
    assert cli_auth._read_openrouter_key(args, ui) == "sk-or-v1-xyz"


def test_read_openrouter_key_interactive():
    args = type("Args", (), {"key_value": None, "prompt": None})()
    ui = MagicMock()
    ui.input.return_value = "  sk-or-v1-interactive  "
    assert cli_auth._read_openrouter_key(args, ui) == "sk-or-v1-interactive"


def test_read_openrouter_key_empty_exits():
    args = type("Args", (), {"key_value": None, "prompt": None})()
    ui = MagicMock()
    ui.input.return_value = ""
    with pytest.raises(SystemExit):
        cli_auth._read_openrouter_key(args, ui)


def test_prompt_provider_key_declined():
    ui = MagicMock()
    ui.input.return_value = "n"
    assert cli_auth._prompt_provider_key("anthropic", "claude-sonnet", ui) is None


def test_prompt_provider_key_accepted():
    ui = MagicMock()
    ui.input.side_effect = ["y", "sk-ant-123", "claude-opus"]
    result = cli_auth._prompt_provider_key("anthropic", "claude-sonnet", ui)
    assert result == {"api_key": "sk-ant-123", "model": "claude-opus"}


def test_prompt_provider_key_default_model():
    ui = MagicMock()
    ui.input.side_effect = ["y", "sk-ant-123", ""]
    result = cli_auth._prompt_provider_key("anthropic", "claude-sonnet", ui)
    assert result == {"api_key": "sk-ant-123", "model": "claude-sonnet"}


def test_prompt_provider_key_empty_key():
    ui = MagicMock()
    ui.input.side_effect = ["y", ""]
    assert cli_auth._prompt_provider_key("anthropic", "claude-sonnet", ui) is None


def test_configure_provider_existing():
    data = {"anthropic": {"api_key": "sk-ant-old"}}
    ui = MagicMock()
    result = cli_auth._configure_provider(
        data, ("anthropic", "ANTHROPIC_API_KEY", "claude-sonnet"), ui
    )
    assert result == {"api_key": "sk-ant-old"}
    ui.print_info.assert_called()


def test_configure_provider_env():
    import os

    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-env"
    try:
        data = {}
        ui = MagicMock()
        result = cli_auth._configure_provider(
            data, ("anthropic", "ANTHROPIC_API_KEY", "claude-sonnet"), ui
        )
        assert result == {"api_key": "sk-ant-env", "model": "claude-sonnet"}
        ui.print_success.assert_called()
    finally:
        del os.environ["ANTHROPIC_API_KEY"]


def test_configure_provider_declined():
    data = {}
    ui = MagicMock()
    ui.input.return_value = "n"
    result = cli_auth._configure_provider(
        data, ("anthropic", "ANTHROPIC_API_KEY", "claude-sonnet"), ui
    )
    assert result is None


def test_auth_logout_no_provider():
    ui = MagicMock()
    with pytest.raises(SystemExit):
        cli_auth._auth_logout(Path("/tmp/nope.json"), None, ui)


def test_auth_logout_missing_file():
    ui = MagicMock()
    cli_auth._auth_logout(Path("/tmp/nonexistent_auth.json"), "openai", ui)
    # Should return without error


def test_auth_logout_provider_not_found(tmp_path):
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps({"openai": {"api_key": "sk-123"}}))
    ui = MagicMock()
    with pytest.raises(SystemExit):
        cli_auth._auth_logout(auth_file, "anthropic", ui)


def test_auth_logout_success(tmp_path):
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps({"openai": {"api_key": "sk-123"}}))
    ui = MagicMock()
    cli_auth._auth_logout(auth_file, "openai", ui)
    data = json.loads(auth_file.read_text())
    assert "openai" not in data
    ui.print_success.assert_called()


def test_auth_list_empty(tmp_path):
    ui = MagicMock()
    cli_auth._auth_list(tmp_path / "nope.json", ui)
    ui.print_info.assert_called()


def test_auth_list_with_data(tmp_path):
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps({"openai": {"api_key": "sk-12345678", "model": "gpt-4o"}}))
    ui = MagicMock()
    cli_auth._auth_list(auth_file, ui)
    ui.console.print.assert_called()


def test_auth_login_openrouter(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    auth_file = tmp_path / "auth.json"
    ui = MagicMock()
    ui.input.side_effect = ["sk-or-v1-abc"]
    args = type("Args", (), {"auth_provider": "openrouter", "model": None})()
    cli_auth._auth_login(args, auth_file, ui)
    data = json.loads(auth_file.read_text())
    assert data["openrouter"]["api_key"] == "sk-or-v1-abc"


def test_auth_login_empty_provider():
    ui = MagicMock()
    ui.input.return_value = ""
    args = type("Args", (), {"auth_provider": None, "model": None})()
    with pytest.raises(SystemExit):
        cli_auth._auth_login(args, Path("/tmp/nope.json"), ui)


def test_auth_login_empty_key():
    ui = MagicMock()
    ui.input.side_effect = ["openai", ""]
    args = type("Args", (), {"auth_provider": None, "model": None})()
    with pytest.raises(SystemExit):
        cli_auth._auth_login(args, Path("/tmp/nope.json"), ui)


def test_cmd_auth_list(tmp_path):
    ui = MagicMock()
    args = type("Args", (), {"auth_subcommand": "list", "auth_provider": None, "model": None})()
    cli_auth._cmd_auth(args, ui)
    ui.print_info.assert_called()


def test_cmd_auth_logout(tmp_path):
    ui = MagicMock()
    args = type(
        "Args", (), {"auth_subcommand": "logout", "auth_provider": "openai", "model": None}
    )()
    cli_auth._cmd_auth(args, ui)
    # No auth file exists, so it returns without error
    ui.print_error.assert_not_called()


def test_cmd_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tmp_home = tmp_path / "home"
    tmp_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_home)
    ui = MagicMock()
    ui.input.side_effect = ["sk-or-v1-abc"]
    args = type("Args", (), {"key_value": None, "prompt": None})()
    cli_auth._cmd_key(args, ui)
    ui.print_success.assert_called()


def test_openrouter_auth_file(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert cli_auth._openrouter_auth_file() == tmp_path / ".config" / "apex" / "auth.json"
