"""Hierarchical JSON/JSONC config system for APEX v2 — mirrors OpenCode config UX.

Precedence (later overrides earlier):
  1. Global:   ~/.config/apex/apex.json(c)
  2. Custom:   $APEX_CONFIG
  3. Project:  ./apex.json(c)
  4. Inline:   $APEX_CONFIG_CONTENT (JSON string)
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from .config import MODELS, MODEL_PROVIDERS

# ────────────────────────────────────────────────────────────
# JSONC helpers
# ────────────────────────────────────────────────────────────

_JSONC_COMMENT_RE = re.compile(
    r"//(?:[^\"\n]|\"(?:\\.|[^\"\\])*\")*?(?=\n|$)|/\*[\s\S]*?\*/",
)


def strip_jsonc_comments(text: str) -> str:
    """Strip C-style comments from a JSONC string, preserving string contents."""

    def _replacer(m: re.Match) -> str:
        chunk = m.group(0)
        if chunk.startswith("//"):
            return ""
        return ""

    return _JSONC_COMMENT_RE.sub(_replacer, text)


def parse_jsonc(text: str) -> Any:
    cleaned = strip_jsonc_comments(text)
    return json.loads(cleaned)


def read_jsonc(path: Path) -> Any:
    return parse_jsonc(path.read_text(encoding="utf-8"))


# ────────────────────────────────────────────────────────────
# Variable substitution
# ────────────────────────────────────────────────────────────

_ENV_VAR_RE = re.compile(r"\{env:([^}]+)\}")
_FILE_VAR_RE = re.compile(r"\{file:([^}]+)\}")


def _substitute_vars(value: Any, seen: set | None = None, _depth: int = 0) -> Any:
    if _depth > 10:
        return value
    if seen is None:
        seen = set()

    if isinstance(value, str):

        def _replace_env(m: re.Match) -> str:
            var = m.group(1).strip()
            val = os.environ.get(var, "")
            if not val:
                val = os.environ.get(var.lower(), "")
            return val

        def _replace_file(m: re.Match) -> str:
            p = Path(m.group(1).strip()).expanduser()
            if p in seen:
                return ""
            seen.add(p)
            if p.is_file():
                return p.read_text(encoding="utf-8", errors="replace")
            return ""

        value = _ENV_VAR_RE.sub(_replace_env, value)
        value = _FILE_VAR_RE.sub(_replace_file, value)
        return value

    if isinstance(value, dict):
        return {k: _substitute_vars(v, seen, _depth + 1) for k, v in value.items()}

    if isinstance(value, list):
        return [_substitute_vars(v, seen, _depth + 1) for v in value]

    return value


# ────────────────────────────────────────────────────────────
# Defaults
# ────────────────────────────────────────────────────────────

DEFAULTS: dict[str, Any] = {
    "model": "or-gpt4o-mini",
    "small_model": None,
    "provider": {},
    "agent": {},
    "command": {},
    "server": {
        "port": 8080,
        "hostname": "127.0.0.1",
        "cors": {"origin": "*", "methods": "*", "headers": "*"},
    },
    "permission": {},
    "tools": {},
    "lsp": False,
    "mcp": {},
    "plugin": [],
    "formatter": False,
    "snapshot": True,
    "autoupdate": True,
    "share": "manual",
    "shell": os.environ.get("SHELL", "/bin/bash"),
    "compaction": {
        "auto": True,
        "prune": True,
        "reserved": 10000,
    },
    "watcher": {
        "ignore": [
            "**/node_modules/**",
            "**/.git/**",
            "**/__pycache__/**",
            "**/.venv/**",
            "**/venv/**",
            "**/dist/**",
            "**/build/**",
            "**/.next/**",
            "**/target/**",
        ],
    },
    "theme": "apex",
    "keybinds": {},
    "instructions": [],
    "disabled_providers": [],
    "enabled_providers": [],
    "default_agent": "build",
}

TUI_DEFAULTS: dict[str, Any] = {
    "theme": "apex",
    "keybinds": {},
    "scroll_speed": 3,
    "scroll_acceleration": {"enabled": False},
    "diff_style": "auto",
    "mouse": True,
    "leader_timeout": 2000,
}

# ────────────────────────────────────────────────────────────
# OpenCode env var aliases
# ────────────────────────────────────────────────────────────

_OPENCODE_ENV_MAP: dict[str, str] = {
    "OPENCODE_CONFIG": "APEX_CONFIG",
    "OPENCODE_CONFIG_DIR": "APEX_CONFIG_DIR",
    "OPENCODE_CONFIG_CONTENT": "APEX_CONFIG_CONTENT",
    "OPENCODE_PERMISSION": "APEX_PERMISSION",
    "OPENCODE_SERVER_PASSWORD": "APEX_SERVER_PASSWORD",
    "OPENCODE_SERVER_USERNAME": "APEX_SERVER_USERNAME",
    "OPENCODE_DISABLE_AUTOUPDATE": "APEX_DISABLE_AUTOUPDATE",
    "OPENCODE_DISABLE_PRUNE": "APEX_DISABLE_PRUNE",
    "OPENCODE_DISABLE_MOUSE": "APEX_DISABLE_MOUSE",
    "OPENCODE_DISABLE_TERMINAL_TITLE": "APEX_DISABLE_TERMINAL_TITLE",
}


def _apply_opencode_env_aliases() -> None:
    for opencode_var, apex_var in _OPENCODE_ENV_MAP.items():
        if opencode_var in os.environ and apex_var not in os.environ:
            os.environ[apex_var] = os.environ[opencode_var]


_apply_opencode_env_aliases()

# ────────────────────────────────────────────────────────────
# Config path helpers
# ────────────────────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".config" / "apex"
GLOBAL_JSON = CONFIG_DIR / "apex.json"
GLOBAL_JSONC = CONFIG_DIR / "apex.jsonc"
TUI_JSON = CONFIG_DIR / "tui.json"

OLD_CONFIG = Path.home() / ".apex" / "config.json"


def _find_global_config() -> Path | None:
    if GLOBAL_JSONC.is_file():
        return GLOBAL_JSONC
    if GLOBAL_JSON.is_file():
        return GLOBAL_JSON
    return None


def _find_project_config(start: Path | None = None) -> Path | None:
    cwd = start or Path.cwd()
    for name in ("apex.jsonc", "apex.json"):
        candidate = cwd / name
        if candidate.is_file():
            return candidate
    for name in ("opencode.jsonc", "opencode.json"):
        candidate = cwd / name
        if candidate.is_file():
            return candidate
    return None


def _load_json(path: Path) -> dict[str, Any]:
    try:
        if path.suffix == ".jsonc":
            data = read_jsonc(path)
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


# ────────────────────────────────────────────────────────────
# ApexConfig
# ────────────────────────────────────────────────────────────


class ApexConfig:
    """Hierarchical config that merges global → custom → project → inline.

    All properties save immediately on set (save-on-set semantics).
    """

    def __init__(self, project_dir: str | Path | None = None) -> None:
        self._data: dict[str, Any] = {}
        self._project_dir: Path | None = Path(project_dir).resolve() if project_dir else None
        self._migrated = False
        self._auto_migrate()
        self._load_all()

    # ── Loading ──────────────────────────────────────────────

    def _auto_migrate(self) -> None:
        if _find_global_config() is not None:
            return
        if OLD_CONFIG.is_file():
            try:
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                old_data = json.loads(OLD_CONFIG.read_text(encoding="utf-8"))
                GLOBAL_JSONC.write_text(
                    json.dumps(old_data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                backup = OLD_CONFIG.with_suffix(".json.bak")
                if not backup.exists():
                    shutil.copy2(str(OLD_CONFIG), str(backup))
                self._migrated = True
            except (OSError, json.JSONDecodeError):
                pass

    def _load_all(self) -> None:
        layers: list[dict[str, Any]] = []

        # 1) Global
        global_path = _find_global_config()
        if global_path:
            layers.append(_load_json(global_path))

        # 2) Custom from env
        custom_env = os.environ.get("APEX_CONFIG", "")
        if custom_env:
            custom_path = Path(custom_env).expanduser()
            if custom_path.is_file():
                layers.append(_load_json(custom_path))

        # 3) Project
        project_path = _find_project_config(self._project_dir)
        if project_path:
            layers.append(_load_json(project_path))

        # 4) Inline from env
        inline_raw = os.environ.get("APEX_CONFIG_CONTENT", "")
        if inline_raw:
            try:
                inline = parse_jsonc(inline_raw)
                if isinstance(inline, dict):
                    layers.append(inline)
            except (json.JSONDecodeError, ValueError):
                pass

        # Merge layers (later overrides)
        merged: dict[str, Any] = {}
        for layer in layers:
            self._deep_merge(merged, layer)

        # Fill in defaults
        self._deep_merge_defaults(merged, DEFAULTS)

        # Substitute variables
        merged = _substitute_vars(merged)

        self._data = merged

    @staticmethod
    def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> None:
        for key, val in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(val, dict):
                ApexConfig._deep_merge(target[key], val)
            else:
                target[key] = val

    @staticmethod
    def _deep_merge_defaults(target: dict[str, Any], defaults: dict[str, Any]) -> None:
        for key, val in defaults.items():
            if key not in target:
                target[key] = val
            elif isinstance(val, dict) and isinstance(target[key], dict):
                ApexConfig._deep_merge_defaults(target[key], val)

    # ── Save ─────────────────────────────────────────────────

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        GLOBAL_JSON.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Generic access ───────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def raw(self) -> dict[str, Any]:
        return dict(self._data)

    # ── Properties: model ────────────────────────────────────

    @property
    def model(self) -> str:
        return str(self._data.get("model", DEFAULTS["model"]))

    @model.setter
    def model(self, value: str) -> None:
        self._data["model"] = value
        self.save()

    @property
    def small_model(self) -> str | None:
        val = self._data.get("small_model", DEFAULTS["small_model"])
        return str(val) if val else None

    @small_model.setter
    def small_model(self, value: str | None) -> None:
        self._data["small_model"] = value
        self.save()

    # ── Properties: provider ─────────────────────────────────

    @property
    def provider(self) -> dict[str, Any]:
        return dict(self._data.get("provider", {}))

    @provider.setter
    def provider(self, value: dict[str, Any]) -> None:
        self._data["provider"] = value
        self.save()

    # ── Properties: agent ────────────────────────────────────

    @property
    def agent(self) -> dict[str, Any]:
        return dict(self._data.get("agent", {}))

    @agent.setter
    def agent(self, value: dict[str, Any]) -> None:
        self._data["agent"] = value
        self.save()

    # ── Properties: command ──────────────────────────────────

    @property
    def command(self) -> dict[str, Any]:
        return dict(self._data.get("command", {}))

    @command.setter
    def command(self, value: dict[str, Any]) -> None:
        self._data["command"] = value
        self.save()

    # ── Properties: server ───────────────────────────────────

    @property
    def server(self) -> dict[str, Any]:
        return dict(self._data.get("server", DEFAULTS["server"]))

    @server.setter
    def server(self, value: dict[str, Any]) -> None:
        self._data["server"] = value
        self.save()

    # ── Properties: permission ───────────────────────────────

    @property
    def permission(self) -> dict[str, Any]:
        return dict(self._data.get("permission", {}))

    @permission.setter
    def permission(self, value: dict[str, Any]) -> None:
        self._data["permission"] = value
        self.save()

    # ── Properties: tools ────────────────────────────────────

    @property
    def tools(self) -> dict[str, Any]:
        return dict(self._data.get("tools", {}))

    @tools.setter
    def tools(self, value: dict[str, Any]) -> None:
        self._data["tools"] = value
        self.save()

    # ── Properties: lsp ──────────────────────────────────────

    @property
    def lsp(self) -> bool | dict[str, Any]:
        return self._data.get("lsp", DEFAULTS["lsp"])

    @lsp.setter
    def lsp(self, value: bool | dict[str, Any]) -> None:
        self._data["lsp"] = value
        self.save()

    # ── Properties: mcp ──────────────────────────────────────

    @property
    def mcp(self) -> dict[str, Any]:
        return dict(self._data.get("mcp", {}))

    @mcp.setter
    def mcp(self, value: dict[str, Any]) -> None:
        self._data["mcp"] = value
        self.save()

    # ── Properties: plugin ───────────────────────────────────

    @property
    def plugin(self) -> list[Any]:
        return list(self._data.get("plugin", []))

    @plugin.setter
    def plugin(self, value: list[Any]) -> None:
        self._data["plugin"] = value
        self.save()

    # ── Properties: formatter ────────────────────────────────

    @property
    def formatter(self) -> bool | dict[str, Any]:
        return self._data.get("formatter", DEFAULTS["formatter"])

    @formatter.setter
    def formatter(self, value: bool | dict[str, Any]) -> None:
        self._data["formatter"] = value
        self.save()

    # ── Properties: snapshot ─────────────────────────────────

    @property
    def snapshot(self) -> bool:
        return bool(self._data.get("snapshot", DEFAULTS["snapshot"]))

    @snapshot.setter
    def snapshot(self, value: bool) -> None:
        self._data["snapshot"] = value
        self.save()

    # ── Properties: autoupdate ───────────────────────────────

    @property
    def autoupdate(self) -> bool:
        return bool(self._data.get("autoupdate", DEFAULTS["autoupdate"]))

    @autoupdate.setter
    def autoupdate(self, value: bool) -> None:
        self._data["autoupdate"] = value
        self.save()

    # ── Properties: share ────────────────────────────────────

    @property
    def share(self) -> str:
        val = self._data.get("share", DEFAULTS["share"])
        if val not in ("manual", "auto", "disabled"):
            return DEFAULTS["share"]
        return str(val)

    @share.setter
    def share(self, value: str) -> None:
        if value not in ("manual", "auto", "disabled"):
            value = DEFAULTS["share"]
        self._data["share"] = value
        self.save()

    # ── Properties: shell ────────────────────────────────────

    @property
    def shell(self) -> str:
        return str(self._data.get("shell", DEFAULTS["shell"]))

    @shell.setter
    def shell(self, value: str) -> None:
        self._data["shell"] = value
        self.save()

    # ── Properties: compaction ───────────────────────────────

    @property
    def compaction(self) -> dict[str, Any]:
        return dict(self._data.get("compaction", dict(DEFAULTS["compaction"])))

    @compaction.setter
    def compaction(self, value: dict[str, Any]) -> None:
        self._data["compaction"] = value
        self.save()

    # ── Properties: watcher ──────────────────────────────────

    @property
    def watcher(self) -> dict[str, Any]:
        return dict(self._data.get("watcher", dict(DEFAULTS["watcher"])))

    @watcher.setter
    def watcher(self, value: dict[str, Any]) -> None:
        self._data["watcher"] = value
        self.save()

    # ── Properties: theme ────────────────────────────────────

    @property
    def theme(self) -> str:
        return str(self._data.get("theme", DEFAULTS["theme"]))

    @theme.setter
    def theme(self, value: str) -> None:
        self._data["theme"] = value
        self.save()

    # ── Properties: keybinds ─────────────────────────────────

    @property
    def keybinds(self) -> dict[str, Any]:
        return dict(self._data.get("keybinds", {}))

    @keybinds.setter
    def keybinds(self, value: dict[str, Any]) -> None:
        self._data["keybinds"] = value
        self.save()

    # ── Properties: instructions ─────────────────────────────

    @property
    def instructions(self) -> list[str]:
        return list(self._data.get("instructions", []))

    @instructions.setter
    def instructions(self, value: list[str]) -> None:
        self._data["instructions"] = value
        self.save()

    # ── Properties: disabled_providers ───────────────────────

    @property
    def disabled_providers(self) -> list[str]:
        return list(self._data.get("disabled_providers", []))

    @disabled_providers.setter
    def disabled_providers(self, value: list[str]) -> None:
        self._data["disabled_providers"] = value
        self.save()

    # ── Properties: enabled_providers ────────────────────────

    @property
    def enabled_providers(self) -> list[str]:
        return list(self._data.get("enabled_providers", []))

    @enabled_providers.setter
    def enabled_providers(self, value: list[str]) -> None:
        self._data["enabled_providers"] = value
        self.save()

    # ── Properties: default_agent ────────────────────────────

    @property
    def default_agent(self) -> str:
        return str(self._data.get("default_agent", DEFAULTS["default_agent"]))

    @default_agent.setter
    def default_agent(self, value: str) -> None:
        self._data["default_agent"] = value
        self.save()

    # ── Model helpers ────────────────────────────────────────

    def resolve_model(self, name: str | None = None) -> str:
        target = name or self.model
        return MODELS.get(target, target)

    def model_provider_key(self, name: str | None = None) -> str | None:
        target = name or self.model
        short = None
        for k, v in MODELS.items():
            if v == target or k == target:
                short = k
                break
        if short is None:
            short = target
        return MODEL_PROVIDERS.get(short, None)

    def api_key_for_model(self, name: str | None = None) -> str | None:
        env_key = self.model_provider_key(name)
        if env_key is None:
            return None
        return os.environ.get(env_key, os.environ.get(env_key.lower(), None))

    # ── Provider helpers ─────────────────────────────────────

    def provider_option(self, provider_name: str, key: str, default: Any = None) -> Any:
        prov = self._data.get("provider", {}).get(provider_name, {})
        if isinstance(prov, dict):
            return prov.get(key, default)
        return default

    def all_provider_options(self, provider_name: str) -> dict[str, Any]:
        prov = self._data.get("provider", {}).get(provider_name, {})
        return dict(prov) if isinstance(prov, dict) else {}

    # ── Tool enabled check ───────────────────────────────────

    def is_tool_enabled(self, tool_name: str) -> bool:
        tools = self._data.get("tools", {})
        val = tools.get(tool_name)
        if val is None:
            return True
        return bool(val)

    def is_mcp_enabled(self) -> bool:
        return bool(self._data.get("mcp", {}))

    def is_lsp_enabled(self) -> bool:
        val = self._data.get("lsp", DEFAULTS["lsp"])
        if isinstance(val, bool):
            return val
        return True

    def is_snapshot_enabled(self) -> bool:
        return self.snapshot

    def is_formatter_enabled(self) -> bool:
        val = self._data.get("formatter", DEFAULTS["formatter"])
        if isinstance(val, bool):
            return val
        return True

    @property
    def migrated(self) -> bool:
        return self._migrated

    def __repr__(self) -> str:
        return f"ApexConfig(model={self.model!r}, theme={self.theme!r})"


# ────────────────────────────────────────────────────────────
# TuiConfig (separate file)
# ────────────────────────────────────────────────────────────


class TuiConfig:
    """TUI-specific config stored in ~/.config/apex/tui.json."""

    def __init__(self) -> None:
        self._path = TUI_JSON
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.is_file():
            try:
                raw = self._path.read_text(encoding="utf-8")
                data = parse_jsonc(raw) if self._path.suffix == ".jsonc" else json.loads(raw)
                if isinstance(data, dict):
                    self._data = data
            except (json.JSONDecodeError, OSError):
                self._data = {}
        self._fill_defaults()

    def _fill_defaults(self) -> None:
        for key, val in TUI_DEFAULTS.items():
            if key not in self._data:
                self._data[key] = val
            elif isinstance(val, dict) and isinstance(self._data.get(key), dict):
                for k2, v2 in val.items():
                    if k2 not in self._data[key]:
                        self._data[key][k2] = v2

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    @property
    def theme(self) -> str:
        return str(self._data.get("theme", TUI_DEFAULTS["theme"]))

    @theme.setter
    def theme(self, value: str) -> None:
        self._data["theme"] = value
        self.save()

    @property
    def keybinds(self) -> dict[str, Any]:
        return dict(self._data.get("keybinds", {}))

    @keybinds.setter
    def keybinds(self, value: dict[str, Any]) -> None:
        self._data["keybinds"] = value
        self.save()

    @property
    def scroll_speed(self) -> int:
        return int(self._data.get("scroll_speed", TUI_DEFAULTS["scroll_speed"]))

    @scroll_speed.setter
    def scroll_speed(self, value: int) -> None:
        self._data["scroll_speed"] = value
        self.save()

    @property
    def scroll_acceleration(self) -> dict[str, Any]:
        return dict(self._data.get("scroll_acceleration", dict(TUI_DEFAULTS["scroll_acceleration"])))

    @scroll_acceleration.setter
    def scroll_acceleration(self, value: dict[str, Any]) -> None:
        self._data["scroll_acceleration"] = value
        self.save()

    @property
    def diff_style(self) -> str:
        val = self._data.get("diff_style", TUI_DEFAULTS["diff_style"])
        if val not in ("auto", "stacked"):
            return TUI_DEFAULTS["diff_style"]
        return str(val)

    @diff_style.setter
    def diff_style(self, value: str) -> None:
        if value not in ("auto", "stacked"):
            value = TUI_DEFAULTS["diff_style"]
        self._data["diff_style"] = value
        self.save()

    @property
    def mouse(self) -> bool:
        return bool(self._data.get("mouse", TUI_DEFAULTS["mouse"]))

    @mouse.setter
    def mouse(self, value: bool) -> None:
        self._data["mouse"] = value
        self.save()

    @property
    def leader_timeout(self) -> int:
        return int(self._data.get("leader_timeout", TUI_DEFAULTS["leader_timeout"]))

    @leader_timeout.setter
    def leader_timeout(self, value: int) -> None:
        self._data["leader_timeout"] = value
        self.save()

    def __repr__(self) -> str:
        return f"TuiConfig(theme={self.theme!r}, scroll_speed={self.scroll_speed})"


# ────────────────────────────────────────────────────────────
# Singletons
# ────────────────────────────────────────────────────────────

apex_config = ApexConfig()
tui_config = TuiConfig()


__all__ = [
    "ApexConfig",
    "TuiConfig",
    "apex_config",
    "tui_config",
    "CONFIG_DIR",
    "GLOBAL_JSON",
    "GLOBAL_JSONC",
    "TUI_JSON",
    "strip_jsonc_comments",
    "parse_jsonc",
    "read_jsonc",
]
