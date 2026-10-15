"""Tests for theme_manager.py — 100% line coverage."""

import json
import pytest
from pathlib import Path

from apex.theme_manager import (
    ThemeManager,
    theme_manager,
    BUILTIN_THEMES,
    REQUIRED_KEYS,
    _resolve_ref,
    _detect_terminal_mode,
    _load_theme_files,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_env(monkeypatch):
    """Clean environment variables for deterministic tests."""
    monkeypatch.delenv("COLORFGBG", raising=False)
    monkeypatch.delenv("TERM", raising=False)
    return monkeypatch


@pytest.fixture
def mock_paths(monkeypatch, tmp_path):
    """Redirect Path.home() and Path.cwd() into tmp_path."""
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True)
    cwd_dir = tmp_path / "cwd"
    cwd_dir.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: home_dir)
    monkeypatch.setattr(Path, "cwd", lambda: cwd_dir)
    return home_dir, cwd_dir


@pytest.fixture
def manager(mock_paths, mock_env):
    """Fresh ThemeManager with mocked paths and env."""
    return ThemeManager()


# ---------------------------------------------------------------------------
# BUILTIN_THEMES
# ---------------------------------------------------------------------------


class TestBuiltinThemes:
    """Verify the 12 built-in theme definitions."""

    def test_count(self):
        assert len(BUILTIN_THEMES) == 12

    def test_names(self):
        assert set(BUILTIN_THEMES) == {
            "apex",
            "tokyonight",
            "everforest",
            "ayu",
            "catppuccin",
            "catppuccin-macchiato",
            "gruvbox",
            "kanagawa",
            "nord",
            "matrix",
            "one-dark",
            "system",
        }

    def test_each_has_defs_and_theme(self):
        for name, data in BUILTIN_THEMES.items():
            assert "defs" in data, name
            assert "theme" in data, name

    def test_each_has_all_required_keys(self):
        for name, data in BUILTIN_THEMES.items():
            theme_keys = set(data["theme"])
            for key in REQUIRED_KEYS:
                assert key in theme_keys, f"{name} missing {key}"

    def test_required_keys_frozenset(self):
        assert isinstance(REQUIRED_KEYS, frozenset)
        assert len(REQUIRED_KEYS) > 0
        assert "primary" in REQUIRED_KEYS
        assert "syntaxType" in REQUIRED_KEYS


# ---------------------------------------------------------------------------
# _resolve_ref
# ---------------------------------------------------------------------------


class TestResolveRef:
    """Color reference resolution — hex, defs, recursive, none."""

    def test_none_passthrough(self):
        assert _resolve_ref({}, "none") == "none"

    def test_hex_passthrough(self):
        assert _resolve_ref({"x": "#000"}, "#ff00ff") == "#ff00ff"

    def test_known_ref_to_hex(self):
        assert _resolve_ref({"red": "#ff0000"}, "red") == "#ff0000"

    def test_known_ref_to_none(self):
        assert _resolve_ref({"t": "none"}, "t") == "none"

    def test_recursive_ref(self):
        defs = {"a": "b", "b": "#123456"}
        assert _resolve_ref(defs, "a") == "#123456"

    def test_recursive_to_none(self):
        defs = {"a": "b", "b": "none"}
        assert _resolve_ref(defs, "a") == "none"

    def test_unknown_ref_passthrough(self):
        assert _resolve_ref({"x": "#fff"}, "unknown") == "unknown"


# ---------------------------------------------------------------------------
# _detect_terminal_mode
# ---------------------------------------------------------------------------


class TestDetectTerminalMode:
    """Terminal dark/light detection via COLORFGBG and TERM."""

    def test_default_dark(self, monkeypatch):
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        assert _detect_terminal_mode() == "dark"

    def test_term_light(self, monkeypatch):
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.setenv("TERM", "xterm-light")
        assert _detect_terminal_mode() == "light"

    def test_colorfgbg_dark(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "15;0")
        assert _detect_terminal_mode() == "dark"

    def test_colorfgbg_light(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "0;15")
        assert _detect_terminal_mode() == "light"

    def test_colorfgbg_single_part(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "15")
        assert _detect_terminal_mode() == "dark"

    def test_colorfgbg_non_int(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "0;abc")
        assert _detect_terminal_mode() == "dark"

    def test_colorfgbg_empty(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "")
        monkeypatch.setenv("TERM", "dark")
        assert _detect_terminal_mode() == "dark"


# ---------------------------------------------------------------------------
# _load_theme_files
# ---------------------------------------------------------------------------


class TestLoadThemeFiles:
    """Filesystem theme loading from a directory."""

    def test_nonexistent_dir(self, tmp_path):
        assert _load_theme_files(tmp_path / "nope") == {}

    def test_empty_dir(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        assert _load_theme_files(d) == {}

    def test_loads_full_format(self, tmp_path):
        d = tmp_path / "t"
        d.mkdir()
        data = {"defs": {"a": "#fff"}, "theme": {"primary": {"dark": "a", "light": "a"}}}
        (d / "mine.json").write_text(json.dumps(data))
        result = _load_theme_files(d)
        assert result == {"mine": data}

    def test_loads_simple_dict(self, tmp_path):
        d = tmp_path / "t"
        d.mkdir()
        (d / "simple.json").write_text(json.dumps({"primary": "#fff"}))
        result = _load_theme_files(d)
        assert result == {"simple": {"primary": "#fff"}}

    def test_skips_non_json(self, tmp_path):
        d = tmp_path / "t"
        d.mkdir()
        (d / "a.txt").write_text("{}")
        (d / "b.json").write_text(json.dumps({"defs": {}, "theme": {}}))
        result = _load_theme_files(d)
        assert list(result) == ["b"]

    def test_invalid_json_skipped(self, tmp_path):
        d = tmp_path / "t"
        d.mkdir()
        (d / "bad.json").write_text("{invalid")
        assert _load_theme_files(d) == {}

    def test_oserror_skipped(self, tmp_path, monkeypatch):
        d = tmp_path / "t"
        d.mkdir()
        (d / "good.json").write_text(json.dumps({}))

        def broken_read_text(*args, **kwargs):
            raise OSError("boom")

        monkeypatch.setattr(Path, "read_text", broken_read_text)
        assert _load_theme_files(d) == {}


# ---------------------------------------------------------------------------
# ThemeManager — core
# ---------------------------------------------------------------------------


class TestThemeManagerCore:
    """Core ThemeManager operations: init, list, get, set, properties."""

    def test_singleton(self):
        assert isinstance(theme_manager, ThemeManager)

    def test_initial_themes_loaded(self, manager):
        names = manager.list_themes()
        assert len(names) == 12

    def test_list_themes_sorted(self, manager):
        names = manager.list_themes()
        assert names == sorted(names)

    def test_list_themes_returns_all(self, manager):
        names = manager.list_themes()
        assert "apex" in names
        assert "one-dark" in names
        assert "system" in names

    def test_get_theme_valid_returns_all_keys(self, manager):
        theme = manager.get_theme("apex")
        for key in REQUIRED_KEYS:
            assert key in theme, f"Missing required key: {key}"
            v = theme[key]
            assert isinstance(v, str)
            assert v.startswith("#") or v == "none", f"{key}={v!r}"

    def test_get_theme_invalid_falls_back_to_apex(self, manager):
        theme = manager.get_theme("no_such_theme")
        for key in REQUIRED_KEYS:
            assert key in theme

    def test_get_theme_none_uses_current(self, manager):
        t1 = manager.get_theme(manager._current_name)
        t2 = manager.get_theme(None)
        assert t1 == t2

    def test_get_theme_dark_vs_light(self, manager, monkeypatch):
        manager.theme_mode = "auto"
        monkeypatch.setenv("COLORFGBG", "0;0")
        dark = manager.get_theme("apex")
        monkeypatch.setenv("COLORFGBG", "0;15")
        light = manager.get_theme("apex")
        assert dark != light
        assert dark["background"] != light["background"]

    def test_get_theme_with_explicit_mode(self, manager):
        manager.theme_mode = "light"
        light = manager.get_theme("apex")
        manager.theme_mode = "dark"
        dark = manager.get_theme("apex")
        assert light != dark
        assert light["background"] != dark["background"]

    def test_get_theme_string_entry(self, mock_paths, mock_env):
        home, _ = mock_paths
        user_dir = home / ".config" / "apex" / "themes"
        user_dir.mkdir(parents=True)
        (user_dir / "flat.json").write_text(
            json.dumps(
                {
                    "defs": {"c": "#ff00ff"},
                    "theme": {"primary": "c", "secondary": "c"},
                }
            )
        )
        mgr = ThemeManager()
        theme = mgr.get_theme("flat")
        assert theme["primary"] == "#ff00ff"
        assert theme["secondary"] == "#ff00ff"

    def test_get_theme_invalid_entry_type(self, mock_paths, mock_env):
        home, _ = mock_paths
        user_dir = home / ".config" / "apex" / "themes"
        user_dir.mkdir(parents=True)
        (user_dir / "weird.json").write_text(
            json.dumps(
                {
                    "defs": {},
                    "theme": {"primary": ["not", "valid"]},
                }
            )
        )
        mgr = ThemeManager()
        theme = mgr.get_theme("weird")
        assert theme["primary"] == "none"

    def test_get_theme_missing_entry_key(self, mock_paths, mock_env):
        home, _ = mock_paths
        user_dir = home / ".config" / "apex" / "themes"
        user_dir.mkdir(parents=True)
        (user_dir / "partial.json").write_text(
            json.dumps(
                {
                    "defs": {},
                    "theme": {},
                }
            )
        )
        mgr = ThemeManager()
        theme = mgr.get_theme("partial")
        for key in REQUIRED_KEYS:
            assert theme[key] == "none"

    def test_get_theme_missing_dark_key(self, mock_paths, mock_env):
        home, _ = mock_paths
        user_dir = home / ".config" / "apex" / "themes"
        user_dir.mkdir(parents=True)
        (user_dir / "onlydark.json").write_text(
            json.dumps(
                {
                    "defs": {"a": "#ff0000", "b": "#00ff00"},
                    "theme": {"primary": {"dark": "a"}, "secondary": {"dark": "b"}},
                }
            )
        )
        mgr = ThemeManager()
        mgr.theme_mode = "light"
        theme = mgr.get_theme("onlydark")
        assert theme["primary"] == "#ff0000"
        assert theme["secondary"] == "#00ff00"

    def test_set_theme_valid(self, manager):
        manager.set_theme("nord")
        assert manager.current_name == "nord"

    def test_set_theme_invalid_falls_back(self, manager):
        manager.set_theme("nonexistent")
        assert manager.current_name == "apex"

    def test_current_theme_getter(self, manager):
        ct = manager.current_theme
        assert ct == manager.get_theme(manager._current_name)

    def test_current_theme_setter_noop(self, manager):
        orig = manager.current_name
        manager.current_theme = {"primary": "#000"}
        assert manager.current_name == orig

    def test_theme_mode_auto_dark(self, manager, monkeypatch):
        manager.theme_mode = "auto"
        monkeypatch.setenv("COLORFGBG", "0;0")
        assert manager.theme_mode == "dark"

    def test_theme_mode_auto_light(self, manager, monkeypatch):
        manager.theme_mode = "auto"
        monkeypatch.setenv("COLORFGBG", "0;15")
        assert manager.theme_mode == "light"

    def test_theme_mode_explicit(self, manager):
        manager.theme_mode = "light"
        assert manager.theme_mode == "light"

    def test_theme_mode_explicit_dark(self, manager):
        manager.theme_mode = "dark"
        assert manager.theme_mode == "dark"

    def test_theme_mode_invalid_ignored(self, manager):
        manager.theme_mode = "invalid"
        assert manager._mode == "auto"

    def test_current_name_getter(self, manager):
        assert manager.current_name == "apex"
        manager.set_theme("nord")
        assert manager.current_name == "nord"

    def test_current_name_setter_valid(self, manager):
        manager.current_name = "nord"
        assert manager.current_name == "nord"

    def test_current_name_setter_invalid(self, manager):
        manager.current_name = "ghost"
        assert manager.current_name == "apex"

    def test_resolve_color_with_theme(self, manager):
        theme = {"primary": "#aabbcc"}
        assert manager.resolve_color(theme, "primary") == "#aabbcc"

    def test_resolve_color_none_theme(self, manager):
        result = manager.resolve_color(None, "primary")
        assert result.startswith("#") or result == "none"

    def test_resolve_color_default_key(self, manager):
        result = manager.resolve_color()
        assert result.startswith("#") or result == "none"

    def test_resolve_color_missing_key(self, manager):
        assert manager.resolve_color({"p": "#000"}, "missing") == "none"


# ---------------------------------------------------------------------------
# Custom theme loading hierarchy
# ---------------------------------------------------------------------------


class TestThemeHierarchy:
    """Built-in < user config < project < cwd."""

    def test_user_theme_loaded(self, tmp_path, monkeypatch, mock_env):
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path / "cwd")
        user_dir = home / ".config" / "apex" / "themes"
        user_dir.mkdir(parents=True)
        (user_dir / "custom.json").write_text(
            json.dumps(
                {
                    "defs": {"a": "#123456"},
                    "theme": {"primary": {"dark": "a", "light": "a"}},
                }
            )
        )
        mgr = ThemeManager()
        assert "custom" in mgr.list_themes()
        theme = mgr.get_theme("custom")
        assert theme["primary"] == "#123456"

    def test_project_theme_loaded(self, tmp_path, monkeypatch, mock_env):
        home = tmp_path / "home"
        home.mkdir()
        cwd_dir = tmp_path / "cwd"
        cwd_dir.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.setattr(Path, "cwd", lambda: cwd_dir)
        proj_dir = cwd_dir / ".apex" / "themes"
        proj_dir.mkdir(parents=True)
        (proj_dir / "proj.json").write_text(
            json.dumps(
                {
                    "defs": {"b": "#654321"},
                    "theme": {"primary": {"dark": "b", "light": "b"}},
                }
            )
        )
        mgr = ThemeManager()
        assert "proj" in mgr.list_themes()
        theme = mgr.get_theme("proj")
        assert theme["primary"] == "#654321"

    def test_project_overrides_user(self, tmp_path, monkeypatch, mock_env):
        home = tmp_path / "home"
        home.mkdir()
        cwd_dir = tmp_path / "cwd"
        cwd_dir.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.setattr(Path, "cwd", lambda: cwd_dir)
        user_dir = home / ".config" / "apex" / "themes"
        user_dir.mkdir(parents=True)
        (user_dir / "shared.json").write_text(
            json.dumps(
                {
                    "defs": {"c": "#111111"},
                    "theme": {"primary": {"dark": "c", "light": "c"}},
                }
            )
        )
        proj_dir = cwd_dir / ".apex" / "themes"
        proj_dir.mkdir(parents=True)
        (proj_dir / "shared.json").write_text(
            json.dumps(
                {
                    "defs": {"c": "#222222"},
                    "theme": {"primary": {"dark": "c", "light": "c"}},
                }
            )
        )
        mgr = ThemeManager()
        theme = mgr.get_theme("shared")
        assert theme["primary"] == "#222222"

    def test_user_overrides_builtin(self, tmp_path, monkeypatch, mock_env):
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path / "cwd")
        user_dir = home / ".config" / "apex" / "themes"
        user_dir.mkdir(parents=True)
        (user_dir / "apex.json").write_text(
            json.dumps(
                {
                    "defs": {"z": "#ffffff"},
                    "theme": {"primary": {"dark": "z", "light": "z"}},
                }
            )
        )
        mgr = ThemeManager()
        theme = mgr.get_theme("apex")
        assert theme["primary"] == "#ffffff"

    def test_custom_theme_no_defs(self, mock_paths, mock_env):
        home, _ = mock_paths
        user_dir = home / ".config" / "apex" / "themes"
        user_dir.mkdir(parents=True)
        (user_dir / "minimal.json").write_text(
            json.dumps(
                {
                    "theme": {"primary": {"dark": "#ff0000", "light": "#00ff00"}},
                }
            )
        )
        mgr = ThemeManager()
        theme = mgr.get_theme("minimal")
        assert theme["primary"] == "#ff0000"

    def test_theme_with_missing_defs_and_theme(self, mock_paths, mock_env):
        home, _ = mock_paths
        user_dir = home / ".config" / "apex" / "themes"
        user_dir.mkdir(parents=True)
        (user_dir / "bare.json").write_text(json.dumps({}))
        mgr = ThemeManager()
        theme = mgr.get_theme("bare")
        for key in REQUIRED_KEYS:
            assert theme[key] == "none"


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Corner cases and error handling."""

    def test_list_themes_reloads(self, mock_paths, mock_env):
        home, _ = mock_paths
        mgr = ThemeManager()
        names_before = mgr.list_themes()
        user_dir = home / ".config" / "apex" / "themes"
        user_dir.mkdir(parents=True)
        (user_dir / "late.json").write_text(
            json.dumps(
                {
                    "defs": {},
                    "theme": {"primary": {"dark": "#f00", "light": "#f00"}},
                }
            )
        )
        names_after = mgr.list_themes()
        assert len(names_after) == len(names_before) + 1
        assert "late" in names_after

    def test_reload_picks_up_new_themes(self, mock_paths, mock_env):
        home, _ = mock_paths
        mgr = ThemeManager()
        assert "later" not in mgr.list_themes()
        user_dir = home / ".config" / "apex" / "themes"
        user_dir.mkdir(parents=True)
        (user_dir / "later.json").write_text(
            json.dumps(
                {
                    "defs": {},
                    "theme": {"primary": {"dark": "#f00", "light": "#f00"}},
                }
            )
        )
        mgr._reload()
        assert "later" in mgr.list_themes()

    def test_current_name_setter_triggers_reload(self, mock_paths, mock_env):
        home, _ = mock_paths
        mgr = ThemeManager()
        user_dir = home / ".config" / "apex" / "themes"
        user_dir.mkdir(parents=True)
        (user_dir / "fresh.json").write_text(
            json.dumps(
                {
                    "defs": {"x": "#abc"},
                    "theme": {"primary": {"dark": "x", "light": "x"}},
                }
            )
        )
        mgr.current_name = "fresh"
        assert mgr.current_name == "fresh"

    def test_set_theme_persists_to_config(self, manager):
        manager.set_theme("nord")
        from apex.config import Config

        cfg = Config()
        assert cfg.theme == "nord"

    def test_set_theme_config_failure_caught(self, manager, monkeypatch):
        monkeypatch.setattr(
            "apex.config.Config.__init__",
            lambda self: (_ for _ in ()).throw(Exception("config fail")),
        )
        manager.set_theme("nord")
        assert manager.current_name == "nord"
