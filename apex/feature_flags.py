"""APEX Feature Flags (Phase 2 — OpenCode parity).

Modelled on OpenCode's ``experimental.<key>`` config + ``OPENCODE_FLAGS``
environment variable scheme.

Semantics:
- Flags are read from (highest precedence first):
    1. ``APEX_FLAGS`` / ``OPENCODE_FLAGS`` env var (comma-separated)
    2. config ``experimental`` dict
    3. built-in defaults
- A flag is enabled when its value is truthy (``"1"``, ``"true"``,
  ``"on"``, non-empty string).
"""

from __future__ import annotations

import os
from typing import Any

__all__ = ["FeatureFlags", "Flags"]

DEFAULT_FLAGS: dict[str, bool] = {
    "part_rows": True,
    "mcp_oauth": False,
    "skill_watch": True,
    "declarative_commands": True,
    "socket_mcp": True,
    "desktop": False,
    "i18n": False,
    "feature_flags": True,
}


class Flags:
    """A set of features (defaults + overrides)."""

    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self._values: dict[str, Any] = dict(DEFAULT_FLAGS)
        if values:
            self._values.update({k: v for k, v in values.items()})

    def __getitem__(self, key: str) -> Any:
        return self._values.get(key, False)

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def is_enabled(self, key: str) -> bool:
        return bool(self._values.get(key, False))

    def __contains__(self, key: str) -> bool:
        return key in self._values

    def __repr__(self) -> str:
        enabled = {k: v for k, v in self._values.items() if v}
        return f"Flags(enabled={sorted(enabled)})"


class FeatureFlags(Flags):
    """Feature flags with env + config layering."""

    def __init__(
        self,
        config_experimental: dict[str, Any] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        env = env or os.environ

        # 1. config -> defaults
        if config_experimental:
            self._values.update(
                {k: v for k, v in config_experimental.items() if v is not None}
            )

        # 2. env -> config
        for var in ("APEX_FLAGS", "OPENCODE_FLAGS"):
            raw = env.get(var)
            if not raw:
                continue
            for item in raw.split(","):
                item = item.strip()
                if not item:
                    continue
                if "=" in item:
                    key, _, value = item.partition("=")
                    self._values[key.strip()] = self._coerce(value.strip())
                else:
                    self._values[item] = True

    @staticmethod
    def _coerce(value: str) -> Any:
        lowered = value.lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off", ""):
            return False
        try:
            return int(value)
        except ValueError:
            return value
