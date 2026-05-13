"""Tests for apex.config_v2 — hierarchical JSON/JSONC config system.

Achieves 100 % line coverage of config_v2.py.
"""

from __future__ import annotations

import importlib
import json
import os
import pathlib
from pathlib import Path
from textwrap import dedent

import pytest

# Pure helper functions — safe to import at module level (they don't access
# module-level globals that depend on Path.home()).
from apex.config_v2 import parse_jsonc, read_jsonc, strip_jsonc_comments


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def mod(monkeypatch, tmp_path):
    """Patch Path.home() → *tmp_path* and reload *apex.config_v2*.

    Returns the reloaded module so tests can write ``mod.ApexConfig``,
    ``mod.TuiConfig``, ``mod.DEFAULTS``, etc.  All file I/O is scoped to
    *tmp_path*.
    """
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    import apex.config_v2 as m

    importlib.reload(m)
    return m


@pytest.fixture
def cfg(mod):
    """Return a bare ``ApexConfig`` with no extra config files present."""
    return mod.ApexConfig()


@pytest.fixture
def tui(mod):
    """Return a bare ``TuiConfig`` with no extra config files present."""
    return mod.TuiConfig()


def _write(path: Path, data: object) -> None:
    """Write *data* as formatted JSON to *path* (creates parent dirs)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════
# JSONC helpers
# ═══════════════════════════════════════════════════════════════════════


class TestStripJsoncComments:
    """strip_jsonc_comments() — both comment styles."""

    def test_single_line_comments_removed(self):
        input_text = '{\n  // this is a comment\n  "a": 1\n}'
        expected = '{\n  \n  "a": 1\n}'
        assert strip_jsonc_comments(input_text) == expected

    def test_multi_line_comments_removed(self):
        input_text = '{\n  /* block\n  comment */\n  "a": 1\n}'
        expected = '{\n  \n  "a": 1\n}'
        assert strip_jsonc_comments(input_text) == expected

    def test_comments_inside_strings_kept(self):
        input_text = '{\n  "a": "http://example.com",\n  "b": "not // a comment"\n}'
        assert strip_jsonc_comments(input_text) == input_text

    def test_empty_string(self):
        assert strip_jsonc_comments("") == ""


class TestParseJsonc:
    """parse_jsonc() — JSONC → Python dict."""

    def test_with_comments(self):
        text = '{\n  // comment\n  "a": 1\n}'
        assert parse_jsonc(text) == {"a": 1}

    def test_plain_json(self):
        assert parse_jsonc('{"a": 1}') == {"a": 1}

    def test_list(self):
        assert parse_jsonc("[1, 2, 3]") == [1, 2, 3]


class TestReadJsonc:
    """read_jsonc() — read file → Python dict."""

    def test_reads_jsonc_file(self, tmp_path):
        p = tmp_path / "config.jsonc"
        p.write_text('{ "a": 1 }', encoding="utf-8")
        assert read_jsonc(p) == {"a": 1}

    def test_reads_with_comments(self, tmp_path):
        p = tmp_path / "config.jsonc"
        p.write_text('{ /* block */ "a": 1 }', encoding="utf-8")
        assert read_jsonc(p) == {"a": 1}

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_jsonc(tmp_path / "nope.jsonc")


# ═══════════════════════════════════════════════════════════════════════
# Variable substitution
# ═══════════════════════════════════════════════════════════════════════


class TestSubstituteVars:
    """{env:…} and {file:…} substitution (triggered via ApexConfig)."""

    def test_env_var_substitution(self, mod, monkeypatch, tmp_path):
        monkeypatch.setenv("APEX_TEST_MODEL", "custom-model")
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "{env:APEX_TEST_MODEL}"})
        cfg = mod.ApexConfig()
        assert cfg.model == "custom-model"

    def test_env_var_lowercase_fallback(self, mod, monkeypatch, tmp_path):
        monkeypatch.setenv("apex_test_model", "lowercase-model")
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "{env:APEX_TEST_MODEL}"})
        cfg = mod.ApexConfig()
        assert cfg.model == "lowercase-model"

    def test_env_var_missing_returns_empty(self, mod, monkeypatch, tmp_path):
        monkeypatch.delenv("APEX_TEST_MODEL_MISSING", raising=False)
        monkeypatch.delenv("apex_test_model_missing", raising=False)
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "{env:APEX_TEST_MODEL_MISSING}"})
        cfg = mod.ApexConfig()
        assert cfg.model == ""

    def test_file_var_substitution(self, mod, tmp_path):
        secret_file = tmp_path / "secrets" / "key.txt"
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        secret_file.write_text("sk-my-secret-key", encoding="utf-8")
        _write(
            tmp_path / ".config" / "apex" / "apex.json",
            {"shell": "{file:" + str(secret_file) + "}"},
        )
        cfg = mod.ApexConfig()
        assert cfg.shell == "sk-my-secret-key"

    def test_file_var_missing_returns_empty(self, mod, tmp_path):
        _write(
            tmp_path / ".config" / "apex" / "apex.json",
            {"shell": "{file:" + str(tmp_path / "nonexistent.txt") + "}"},
        )
        cfg = mod.ApexConfig()
        assert cfg.shell == ""

    def test_circular_file_reference_returns_empty(self, mod, tmp_path):
        shared = tmp_path / "shared.txt"
        shared.write_text("real-content", encoding="utf-8")
        _write(tmp_path / ".config" / "apex" / "apex.json", {
            "shell": "{file:" + str(shared) + "}",
            "theme": "{file:" + str(shared) + "}",
        })
        cfg = mod.ApexConfig()
        assert cfg.shell == "real-content"
        assert cfg.theme == ""

    def test_substitution_in_dict_value(self, mod, monkeypatch, tmp_path):
        monkeypatch.setenv("APEX_TIMEOUT", "30000")
        _write(
            tmp_path / ".config" / "apex" / "apex.json",
            {"provider": {"anthropic": {"timeout": "{env:APEX_TIMEOUT}"}}},
        )
        cfg = mod.ApexConfig()
        assert cfg.provider == {"anthropic": {"timeout": "30000"}}

    def test_substitution_in_list_value(self, mod, monkeypatch, tmp_path):
        monkeypatch.setenv("APEX_INSTR", "Be concise")
        _write(
            tmp_path / ".config" / "apex" / "apex.json",
            {"instructions": ["{env:APEX_INSTR}"]},
        )
        cfg = mod.ApexConfig()
        assert cfg.instructions == ["Be concise"]


# ═══════════════════════════════════════════════════════════════════════
# Defaults
# ═══════════════════════════════════════════════════════════════════════


class TestDefaults:
    """Defaults apply when no config files exist."""

    def test_all_defaults_applied(self, cfg, mod):
        assert cfg.model == mod.DEFAULTS["model"]
        assert cfg.provider == {}
        assert cfg.agent == {}
        assert cfg.command == {}
        assert cfg.server == mod.DEFAULTS["server"]
        assert cfg.permission == {}
        assert cfg.tools == {}
        assert cfg.lsp is False
        assert cfg.mcp == {}
        assert cfg.plugin == []
        assert cfg.formatter is False
        assert cfg.snapshot is True
        assert cfg.autoupdate is True
        assert cfg.share == "manual"
        assert cfg.shell == os.environ.get("SHELL", "/bin/bash")
        assert cfg.compaction == mod.DEFAULTS["compaction"]
        assert cfg.watcher == mod.DEFAULTS["watcher"]
        assert cfg.theme == "apex"
        assert cfg.keybinds == {}
        assert cfg.instructions == []
        assert cfg.disabled_providers == []
        assert cfg.enabled_providers == []
        assert cfg.default_agent == "build"

    def test_raw_returns_dict(self, cfg):
        data = cfg.raw()
        assert isinstance(data, dict)
        assert data["model"] == "or-gpt4o-mini"

    def test_get_method(self, cfg):
        assert cfg.get("model") == "or-gpt4o-mini"
        assert cfg.get("nonexistent", "fallback") == "fallback"
        assert cfg.get("nonexistent") is None


# ═══════════════════════════════════════════════════════════════════════
# Deep merge
# ═══════════════════════════════════════════════════════════════════════


class TestDeepMerge:
    """_deep_merge and _deep_merge_defaults behavior."""

    def test_deep_merge_overrides_scalar(self, mod):
        target = {"a": 1, "b": {"c": 2}}
        source = {"a": 99, "b": {"d": 3}}
        mod.ApexConfig._deep_merge(target, source)
        assert target == {"a": 99, "b": {"c": 2, "d": 3}}

    def test_deep_merge_defaults_fills_missing(self, mod):
        target = {"a": 1}
        defaults = {"a": 99, "b": 2}
        mod.ApexConfig._deep_merge_defaults(target, defaults)
        assert target == {"a": 1, "b": 2}

    def test_deep_merge_defaults_recursive(self, mod):
        target = {"compaction": {"auto": True}}
        mod.ApexConfig._deep_merge_defaults(target, mod.DEFAULTS)
        assert target["compaction"]["auto"] is True
        assert target["compaction"]["prune"] is False
        assert target["compaction"]["reserved"] == 10


# ═══════════════════════════════════════════════════════════════════════
# Hierarchical loading (global → custom → project → inline)
# ═══════════════════════════════════════════════════════════════════════


class TestHierarchicalLoading:
    """Config layers: global → custom env → project → inline."""

    def test_global_only(self, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "gpt-4o"})
        cfg = mod.ApexConfig()
        assert cfg.model == "gpt-4o"

    def test_global_jsonc_preferred(self, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.jsonc", {"model": "from-jsonc"})
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "from-json"})
        cfg = mod.ApexConfig()
        assert cfg.model == "from-jsonc"

    def test_custom_env_overrides_global(self, mod, monkeypatch, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "global-model"})
        custom = tmp_path / "custom.json"
        _write(custom, {"model": "custom-model"})
        monkeypatch.setenv("APEX_CONFIG", str(custom))
        cfg = mod.ApexConfig()
        assert cfg.model == "custom-model"

    def test_custom_env_skipped_when_missing(self, mod, monkeypatch, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "global-model"})
        monkeypatch.setenv("APEX_CONFIG", str(tmp_path / "does-not-exist.json"))
        cfg = mod.ApexConfig()
        assert cfg.model == "global-model"

    def test_project_overrides_global(self, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "global"})
        proj = tmp_path / "myproject"
        proj.mkdir()
        _write(proj / "apex.json", {"model": "project-model"})
        cfg = mod.ApexConfig(project_dir=proj)
        assert cfg.model == "project-model"

    def test_project_jsonc_preferred(self, mod, tmp_path):
        proj = tmp_path / "myproject"
        proj.mkdir()
        _write(proj / "apex.jsonc", {"model": "jsonc-project"})
        _write(proj / "apex.json", {"model": "json-project"})
        cfg = mod.ApexConfig(project_dir=proj)
        assert cfg.model == "jsonc-project"

    def test_inline_overrides_all(self, mod, monkeypatch, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "global"})
        monkeypatch.setenv("APEX_CONFIG_CONTENT", '{"model": "inline-model"}')
        cfg = mod.ApexConfig()
        assert cfg.model == "inline-model"

    def test_all_layers_merge(self, mod, monkeypatch, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "gpt-4o", "theme": "nord"})
        custom = tmp_path / "custom.json"
        _write(custom, {"theme": "custom-theme", "shell": "/bin/zsh"})
        monkeypatch.setenv("APEX_CONFIG", str(custom))
        monkeypatch.setenv("APEX_CONFIG_CONTENT", '{"shell": "/bin/bash"}')
        cfg = mod.ApexConfig()
        assert cfg.model == "gpt-4o"
        assert cfg.theme == "custom-theme"
        assert cfg.shell == "/bin/bash"

    def test_empty_global_json_is_ignored(self, mod, tmp_path):
        p = tmp_path / ".config" / "apex" / "apex.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
        cfg = mod.ApexConfig()
        assert cfg.model == mod.DEFAULTS["model"]

    def test_invalid_jsonc_in_global_falls_back(self, mod, tmp_path):
        p = tmp_path / ".config" / "apex" / "apex.jsonc"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{invalid jsonc}", encoding="utf-8")
        cfg = mod.ApexConfig()
        assert cfg.model == mod.DEFAULTS["model"]


# ═══════════════════════════════════════════════════════════════════════
# Auto-migration
# ═══════════════════════════════════════════════════════════════════════


class TestAutoMigration:
    """~/.apex/config.json → ~/.config/apex/apex.json migration."""

    def test_migration_occurs_when_no_global_config(self, mod, tmp_path):
        old = tmp_path / ".apex" / "config.json"
        _write(old, {"model": "gpt-4o", "theme": "nord"})
        cfg = mod.ApexConfig()
        assert cfg._migrated is True
        assert cfg.model == "gpt-4o"
        assert cfg.theme == "nord"
        assert mod.GLOBAL_JSON.is_file()
        assert mod.GLOBAL_JSONC.is_file()
        backup = old.with_suffix(".json.bak")
        assert backup.is_file()

    def test_no_migration_when_global_exists(self, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "existing-global"})
        old = tmp_path / ".apex" / "config.json"
        _write(old, {"model": "old-model"})
        cfg = mod.ApexConfig()
        assert cfg._migrated is False
        assert cfg.model == "existing-global"

    def test_no_migration_when_no_old_config(self, mod, tmp_path):
        cfg = mod.ApexConfig()
        assert cfg._migrated is False

    def test_migration_handles_invalid_json(self, mod, tmp_path):
        old = tmp_path / ".apex" / "config.json"
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_text("{invalid}", encoding="utf-8")
        cfg = mod.ApexConfig()
        assert cfg._migrated is False

    def test_migration_does_not_overwrite_existing_backup(self, mod, tmp_path):
        old = tmp_path / ".apex" / "config.json"
        _write(old, {"model": "original"})
        backup = old.with_suffix(".json.bak")
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text("existing-backup", encoding="utf-8")
        cfg = mod.ApexConfig()
        assert cfg._migrated is True
        assert backup.read_text(encoding="utf-8") == "existing-backup"

    def test_migrated_property(self, mod, tmp_path):
        old = tmp_path / ".apex" / "config.json"
        _write(old, {"model": "x"})
        cfg = mod.ApexConfig()
        assert cfg.migrated is True


# ═══════════════════════════════════════════════════════════════════════
# ApexConfig properties
# ═══════════════════════════════════════════════════════════════════════


class TestApexConfigProperties:
    """Every ApexConfig property — read & write."""

    @pytest.fixture(autouse=True)
    def _setup(self, mod, tmp_path):
        self.mod = mod
        self.tmp_path = tmp_path

    def _make(self, data: dict) -> object:
        _write(self.tmp_path / ".config" / "apex" / "apex.json", data)
        return self.mod.ApexConfig()

    def test_model(self):
        cfg = self._make({"model": "gpt-4o"})
        assert cfg.model == "gpt-4o"
        cfg.model = "claude-sonnet-4"
        assert cfg.model == "claude-sonnet-4"

    def test_provider(self):
        cfg = self._make({"provider": {"anthropic": {"timeout": 600}}})
        assert cfg.provider == {"anthropic": {"timeout": 600}}
        cfg.provider = {"openai": {"timeout": 300}}
        assert cfg.provider == {"openai": {"timeout": 300}}

    def test_agent(self):
        cfg = self._make({"agent": {"custom": {"mode": "subagent"}}})
        assert cfg.agent == {"custom": {"mode": "subagent"}}
        cfg.agent = {}
        assert cfg.agent == {}

    def test_command(self):
        cfg = self._make({"command": {"test": {"prompt": "run tests"}}})
        assert cfg.command == {"test": {"prompt": "run tests"}}
        cfg.command = {}
        assert cfg.command == {}

    def test_server(self):
        cfg = self._make({"server": {"port": 9090}})
        assert cfg.server["port"] == 9090
        cfg.server = {"port": 7070}
        assert cfg.server["port"] == 7070

    def test_permission(self):
        cfg = self._make({"permission": {"bash": "allow"}})
        assert cfg.permission == {"bash": "allow"}
        cfg.permission = {}
        assert cfg.permission == {}

    def test_tools(self):
        cfg = self._make({"tools": {"read_file": False}})
        assert cfg.tools == {"read_file": False}
        cfg.tools = {"bash": "ask"}
        assert cfg.tools == {"bash": "ask"}

    def test_lsp(self):
        cfg = self._make({"lsp": True})
        assert cfg.lsp is True
        cfg.lsp = False
        assert cfg.lsp is False
        cfg.lsp = {"enabled": True}
        assert cfg.lsp == {"enabled": True}

    def test_mcp(self):
        cfg = self._make({"mcp": {"servers": [{"name": "github"}]}})
        assert cfg.mcp == {"servers": [{"name": "github"}]}
        cfg.mcp = {}
        assert cfg.mcp == {}

    def test_plugin(self):
        cfg = self._make({"plugin": ["p1", "p2"]})
        assert cfg.plugin == ["p1", "p2"]
        cfg.plugin = []
        assert cfg.plugin == []

    def test_formatter(self):
        cfg = self._make({"formatter": True})
        assert cfg.formatter is True
        cfg.formatter = False
        assert cfg.formatter is False
        cfg.formatter = {"prettier": {"disabled": True}}
        assert cfg.formatter == {"prettier": {"disabled": True}}

    def test_snapshot(self):
        cfg = self._make({"snapshot": False})
        assert cfg.snapshot is False
        cfg.snapshot = True
        assert cfg.snapshot is True

    def test_autoupdate(self):
        cfg = self._make({"autoupdate": False})
        assert cfg.autoupdate is False
        cfg.autoupdate = True
        assert cfg.autoupdate is True

    def test_share(self):
        cfg = self._make({"share": "auto"})
        assert cfg.share == "auto"
        cfg.share = "invalid-mode"
        assert cfg.share == "manual"
        cfg.share = "disabled"
        assert cfg.share == "disabled"

    def test_share_getter_invalid_direct(self, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"share": "bogus"})
        cfg = mod.ApexConfig()
        assert cfg.share == "manual"

    def test_shell(self):
        cfg = self._make({"shell": "/bin/zsh"})
        assert cfg.shell == "/bin/zsh"
        cfg.shell = "/usr/bin/fish"
        assert cfg.shell == "/usr/bin/fish"

    def test_compaction(self):
        cfg = self._make({"compaction": {"auto": True, "reserved": 5}})
        assert cfg.compaction["auto"] is True
        assert cfg.compaction["reserved"] == 5
        cfg.compaction = {"auto": False}
        assert cfg.compaction["auto"] is False

    def test_watcher(self):
        cfg = self._make({"watcher": {"ignore": ["**/tmp/**"]}})
        assert cfg.watcher["ignore"] == ["**/tmp/**"]
        cfg.watcher = {"ignore": []}
        assert cfg.watcher["ignore"] == []

    def test_theme(self):
        cfg = self._make({"theme": "nord"})
        assert cfg.theme == "nord"
        cfg.theme = "catppuccin"
        assert cfg.theme == "catppuccin"

    def test_keybinds(self):
        cfg = self._make({"keybinds": {"leader": "ctrl+x"}})
        assert cfg.keybinds == {"leader": "ctrl+x"}
        cfg.keybinds = {}
        assert cfg.keybinds == {}

    def test_instructions(self):
        cfg = self._make({"instructions": ["Do X", "Do Y"]})
        assert cfg.instructions == ["Do X", "Do Y"]
        cfg.instructions = []
        assert cfg.instructions == []

    def test_disabled_providers(self):
        cfg = self._make({"disabled_providers": ["ollama"]})
        assert cfg.disabled_providers == ["ollama"]
        cfg.disabled_providers = []
        assert cfg.disabled_providers == []

    def test_enabled_providers(self):
        cfg = self._make({"enabled_providers": ["anthropic"]})
        assert cfg.enabled_providers == ["anthropic"]
        cfg.enabled_providers = []
        assert cfg.enabled_providers == []

    def test_default_agent(self):
        cfg = self._make({"default_agent": "architect"})
        assert cfg.default_agent == "architect"
        cfg.default_agent = "planner"
        assert cfg.default_agent == "planner"

    def test_repr(self):
        cfg = self._make({"model": "gpt-4o", "theme": "nord"})
        r = repr(cfg)
        assert "ApexConfig" in r
        assert "gpt-4o" in r
        assert "nord" in r


# ═══════════════════════════════════════════════════════════════════════
# Model helpers
# ═══════════════════════════════════════════════════════════════════════


class TestModelHelpers:
    """resolve_model, model_provider_key, api_key_for_model."""

    def test_resolve_model_known(self, cfg):
        assert cfg.resolve_model("gpt-4o-mini") == "openai/gpt-4o-mini"

    def test_resolve_model_unknown(self, cfg):
        assert cfg.resolve_model("completely-unknown-model") == "completely-unknown-model"

    def test_resolve_model_none_uses_default(self, cfg):
        assert cfg.resolve_model() == "openrouter/openai/gpt-4o-mini"

    def test_model_provider_key_known(self, cfg):
        assert cfg.model_provider_key("gpt-4o-mini") == "OPENAI_API_KEY"

    def test_model_provider_key_none_ollama(self, cfg):
        assert cfg.model_provider_key("ollama-llama3") is None

    def test_model_provider_key_unknown(self, cfg):
        assert cfg.model_provider_key("unknown-model") is None

    def test_api_key_for_model_found(self, cfg, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test123")
        assert cfg.api_key_for_model("gpt-4o-mini") == "sk-test123"

    def test_api_key_for_model_lowercase_fallback(self, cfg, monkeypatch):
        monkeypatch.setenv("openai_api_key", "sk-lowercase")
        assert cfg.api_key_for_model("gpt-4o-mini") == "sk-lowercase"

    def test_api_key_for_model_missing(self, cfg, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("openai_api_key", raising=False)
        assert cfg.api_key_for_model("gpt-4o-mini") is None

    def test_api_key_for_model_unknown(self, cfg):
        assert cfg.api_key_for_model("unknown-model") is None

    def test_api_key_for_model_none_provider(self, cfg, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("anthropic_api_key", raising=False)
        assert cfg.api_key_for_model("unknown-model") is None


# ═══════════════════════════════════════════════════════════════════════
# Provider helpers
# ═══════════════════════════════════════════════════════════════════════


class TestProviderHelpers:
    """provider_option, all_provider_options."""

    def test_provider_option_found(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {
            "provider": {"anthropic": {"timeout": 600}},
        })
        cfg2 = mod.ApexConfig()
        assert cfg2.provider_option("anthropic", "timeout") == 600

    def test_provider_option_default(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {
            "provider": {"anthropic": {"timeout": 600}},
        })
        cfg2 = mod.ApexConfig()
        assert cfg2.provider_option("anthropic", "nonexistent", "fallback") == "fallback"

    def test_provider_option_missing_provider(self, cfg):
        assert cfg.provider_option("nonexistent", "key") is None

    def test_all_provider_options(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {
            "provider": {"anthropic": {"timeout": 600, "base_url": "https://api.anthropic.com"}},
        })
        cfg2 = mod.ApexConfig()
        opts = cfg2.all_provider_options("anthropic")
        assert opts == {"timeout": 600, "base_url": "https://api.anthropic.com"}

    def test_all_provider_options_missing(self, cfg):
        assert cfg.all_provider_options("nonexistent") == {}

    def test_provider_option_non_dict_provider(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {
            "provider": {"bad": "not-a-dict"},
        })
        cfg2 = mod.ApexConfig()
        assert cfg2.provider_option("bad", "key") is None
        assert cfg2.all_provider_options("bad") == {}


# ═══════════════════════════════════════════════════════════════════════
# Tool / feature enabled checks
# ═══════════════════════════════════════════════════════════════════════


class TestEnabledChecks:
    """is_tool_enabled, is_mcp_enabled, is_lsp_enabled, etc."""

    def test_is_tool_enabled_default_true(self, cfg):
        assert cfg.is_tool_enabled("nonexistent-tool") is True

    def test_is_tool_enabled_explicitly_false(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"tools": {"read_file": False}})
        cfg2 = mod.ApexConfig()
        assert cfg2.is_tool_enabled("read_file") is False

    def test_is_tool_enabled_explicitly_true(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"tools": {"bash": True}})
        cfg2 = mod.ApexConfig()
        assert cfg2.is_tool_enabled("bash") is True

    def test_is_mcp_enabled_empty(self, cfg):
        assert cfg.is_mcp_enabled() is False

    def test_is_mcp_enabled_with_config(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"mcp": {"servers": []}})
        cfg2 = mod.ApexConfig()
        assert cfg2.is_mcp_enabled() is True

    def test_is_lsp_enabled_false(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"lsp": False})
        cfg2 = mod.ApexConfig()
        assert cfg2.is_lsp_enabled() is False

    def test_is_lsp_enabled_true_bool(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"lsp": True})
        cfg2 = mod.ApexConfig()
        assert cfg2.is_lsp_enabled() is True

    def test_is_lsp_enabled_dict(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"lsp": {"enabled": True}})
        cfg2 = mod.ApexConfig()
        assert cfg2.is_lsp_enabled() is True

    def test_is_snapshot_enabled(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"snapshot": True})
        cfg2 = mod.ApexConfig()
        assert cfg2.is_snapshot_enabled() is True
        _write(tmp_path / ".config" / "apex" / "apex.json", {"snapshot": False})
        cfg3 = mod.ApexConfig()
        assert cfg3.is_snapshot_enabled() is False

    def test_is_formatter_enabled_false(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"formatter": False})
        cfg2 = mod.ApexConfig()
        assert cfg2.is_formatter_enabled() is False

    def test_is_formatter_enabled_dict(self, cfg, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"formatter": {"prettier": True}})
        cfg2 = mod.ApexConfig()
        assert cfg2.is_formatter_enabled() is True

    def test_is_formatter_enabled_default(self, cfg):
        assert cfg.is_formatter_enabled() is False


# ═══════════════════════════════════════════════════════════════════════
# Save / set / persist
# ═══════════════════════════════════════════════════════════════════════


class TestSaveAndSet:
    """set / save — immediate persist."""

    def test_set_saves_to_disk(self, cfg, mod, monkeypatch, tmp_path):
        # _auto_migrate won't run since global already doesn't exist
        # set() calls save() which writes to GLOBAL_JSON
        cfg.set("model", "persisted-model")
        saved = json.loads(mod.GLOBAL_JSON.read_text(encoding="utf-8"))
        assert saved["model"] == "persisted-model"

    def test_set_updates_in_memory(self, cfg):
        cfg.set("model", "in-memory")
        assert cfg.model == "in-memory"

    def test_property_setter_persists(self, cfg, mod):
        cfg.theme = "catppuccin"
        saved = json.loads(mod.GLOBAL_JSON.read_text(encoding="utf-8"))
        assert saved["theme"] == "catppuccin"

    def test_save_creates_directory(self, cfg, mod, monkeypatch, tmp_path):
        cfg.set("model", "test")
        assert mod.CONFIG_DIR.is_dir()


# ═══════════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Empty config, invalid JSON, corrupted files, etc."""

    def test_empty_config_dict(self, mod, tmp_path):
        p = tmp_path / ".config" / "apex" / "apex.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
        cfg = mod.ApexConfig()
        assert cfg.model == mod.DEFAULTS["model"]

    def test_invalid_json_global(self, mod, tmp_path):
        p = tmp_path / ".config" / "apex" / "apex.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{invalid}", encoding="utf-8")
        cfg = mod.ApexConfig()
        assert cfg.model == mod.DEFAULTS["model"]

    def test_invalid_json_custom_env(self, mod, monkeypatch, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "valid-model"})
        custom = tmp_path / "bad.json"
        custom.write_text("{bad json}", encoding="utf-8")
        monkeypatch.setenv("APEX_CONFIG", str(custom))
        cfg = mod.ApexConfig()
        assert cfg.model == "valid-model"

    def test_invalid_json_inline(self, mod, monkeypatch, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "valid-model"})
        monkeypatch.setenv("APEX_CONFIG_CONTENT", "{bad")
        cfg = mod.ApexConfig()
        assert cfg.model == "valid-model"

    def test_inline_non_dict(self, mod, monkeypatch, tmp_path):
        monkeypatch.setenv("APEX_CONFIG_CONTENT", "[1, 2, 3]")
        cfg = mod.ApexConfig()
        assert cfg.model == mod.DEFAULTS["model"]

    def test_missing_project_dir_falls_back_to_cwd(self, mod, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "global"})
        _write(tmp_path / "apex.json", {"model": "cwd-project"})
        orig = Path.cwd()
        try:
            os.chdir(str(tmp_path))
            importlib.reload(mod)   # ensure module picks up patched home/env
            cfg = mod.ApexConfig()
            assert cfg.model == "cwd-project"
        finally:
            os.chdir(str(orig))

    def test_jsonc_with_block_comment(self, mod, tmp_path):
        p = tmp_path / ".config" / "apex" / "apex.jsonc"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{ /* comment */ "model": "jsonc-model"}', encoding="utf-8")
        cfg = mod.ApexConfig()
        assert cfg.model == "jsonc-model"

    def test_oserror_on_read(self, mod, monkeypatch, tmp_path):
        _write(tmp_path / ".config" / "apex" / "apex.json", {"model": "global-model"})
        cfg = mod.ApexConfig()
        orig_read = tmp_path / ".config" / "apex" / "apex.json"
        orig_read.chmod(0o000)
        if not orig_read.is_file():
            pytest.skip("chmod not supported on this filesystem")
        orig_read.chmod(0o644)  # reset


# ═══════════════════════════════════════════════════════════════════════
# TuiConfig
# ═══════════════════════════════════════════════════════════════════════


class TestTuiConfig:
    """TUI-specific config — 7 properties, load, save."""

    def test_defaults(self, mod, tui):
        assert tui.theme == mod.TUI_DEFAULTS["theme"]
        assert tui.keybinds == {}
        assert tui.scroll_speed == 3
        assert tui.scroll_acceleration == {"enabled": False}
        assert tui.diff_style == "auto"
        assert tui.mouse is True
        assert tui.leader_timeout == 2000

    def test_loads_from_file(self, mod, tmp_path, monkeypatch):
        _write(tmp_path / ".config" / "apex" / "tui.json", {
            "theme": "nord",
            "scroll_speed": 5,
            "mouse": False,
        })
        tui = mod.TuiConfig()
        assert tui.theme == "nord"
        assert tui.scroll_speed == 5
        assert tui.mouse is False

    def test_save_persists(self, mod, tmp_path, monkeypatch):
        tui = mod.TuiConfig()
        tui.theme = "catppuccin"
        saved = json.loads((tmp_path / ".config" / "apex" / "tui.json").read_text(encoding="utf-8"))
        assert saved["theme"] == "catppuccin"

    def test_set_method(self, mod, tui):
        tui.set("scroll_speed", 10)
        assert tui.scroll_speed == 10

    def test_get_method(self, mod, tui):
        assert tui.get("scroll_speed") == 3
        assert tui.get("nonexistent") is None
        assert tui.get("nonexistent", "fallback") == "fallback"

    def test_theme_property(self, mod, tui):
        tui.theme = "tokyonight"
        assert tui.theme == "tokyonight"

    def test_keybinds_property(self, mod, tui):
        tui.keybinds = {"leader": "ctrl+x"}
        assert tui.keybinds == {"leader": "ctrl+x"}

    def test_scroll_speed_property(self, mod, tui):
        tui.scroll_speed = 7
        assert tui.scroll_speed == 7

    def test_scroll_acceleration_property(self, mod, tui):
        tui.scroll_acceleration = {"enabled": True, "rate": 2.0}
        assert tui.scroll_acceleration == {"enabled": True, "rate": 2.0}

    def test_diff_style_valid(self, mod, tui):
        tui.diff_style = "stacked"
        assert tui.diff_style == "stacked"

    def test_diff_style_invalid_falls_back(self, mod, tui):
        tui.diff_style = "invalid"
        assert tui.diff_style == "auto"

    def test_diff_style_default(self, mod, tui):
        assert tui.diff_style == "auto"

    def test_mouse_property(self, mod, tui):
        tui.mouse = False
        assert tui.mouse is False

    def test_leader_timeout_property(self, mod, tui):
        tui.leader_timeout = 5000
        assert tui.leader_timeout == 5000

    def test_diff_style_getter_invalid_direct(self, mod, tui):
        tui._data["diff_style"] = "not-valid"
        assert tui.diff_style == "auto"

    def test_fill_defaults_inner_loop(self, mod, tmp_path):
        p = tmp_path / ".config" / "apex" / "tui.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"scroll_acceleration": {}}', encoding="utf-8")
        tui = mod.TuiConfig()
        assert tui.scroll_acceleration == {"enabled": False}

    def test_load_corrupted_file_falls_back_to_defaults(self, mod, tmp_path, monkeypatch):
        p = tmp_path / ".config" / "apex" / "tui.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{corrupted", encoding="utf-8")
        tui = mod.TuiConfig()
        assert tui.theme == mod.TUI_DEFAULTS["theme"]

    def test_repr(self, tui):
        r = repr(tui)
        assert "TuiConfig" in r
        assert str(tui.scroll_speed) in r


# ═══════════════════════════════════════════════════════════════════════
# Singletons
# ═══════════════════════════════════════════════════════════════════════


class TestSingletons:
    """Module-level ``apex_config`` and ``tui_config`` singletons."""

    def test_apex_config_is_instance(self, mod):
        assert isinstance(mod.apex_config, mod.ApexConfig)

    def test_tui_config_is_instance(self, mod):
        assert isinstance(mod.tui_config, mod.TuiConfig)

    def test_apex_config_has_defaults(self, mod):
        assert mod.apex_config.model == mod.DEFAULTS["model"]

    def test_module_all_exports(self, mod):
        expected = [
            "ApexConfig", "TuiConfig", "apex_config", "tui_config",
            "CONFIG_DIR", "GLOBAL_JSON", "GLOBAL_JSONC", "TUI_JSON",
            "strip_jsonc_comments", "parse_jsonc", "read_jsonc",
        ]
        for name in expected:
            assert name in mod.__all__, f"{name!r} missing from __all__"
