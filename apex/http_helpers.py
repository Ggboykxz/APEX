"""Shared helpers of the APEX HTTP API."""

from __future__ import annotations

import logging
import os
from typing import Any

from .config import MODEL_PROVIDERS, MODELS
from .share import SENSITIVE_PATTERNS

logger = logging.getLogger(__name__)

SENSITIVE_CONFIG_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "token",
        "secret",
        "password",
        "credential",
        "auth_token",
        "access_key",
        "secret_key",
        "private_key",
    }
)


def _sanitize_value(value: Any, depth: int) -> Any:
    """Sanitize one configuration value, recursing into dicts and list items.

    *depth* is the depth of the value's parent, so that every nested level
    counts once. Nested lists are left untouched, as before.
    """
    if isinstance(value, dict):
        return _sanitize_config(value, depth)
    if isinstance(value, list):
        return [
            _sanitize_value(item, depth)
            if isinstance(item, dict)
            else _sanitize_string(item)
            if isinstance(item, str)
            else item
            for item in value
        ]
    if isinstance(value, str):
        return _sanitize_string(value)
    return value


def _sanitize_config(data: dict, _depth: int = 0) -> dict:
    if _depth > 10:
        return data
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(s in key_lower for s in SENSITIVE_CONFIG_KEYS):
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = _sanitize_value(value, _depth + 1)
    return sanitized


def _sanitize_string(value: str) -> str:
    for pattern in SENSITIVE_PATTERNS:
        try:
            value = pattern.sub("***REDACTED***", value)
        except Exception:  # noqa: BLE001, S110
            pass
    return value


def _check_provider_configured(env_var: str) -> bool:
    return bool(os.environ.get(env_var) or os.environ.get(env_var.lower()))


def _get_configured_providers() -> list[dict]:
    configured = []
    seen = set()
    for alias in MODELS:
        env_key = MODEL_PROVIDERS.get(alias)
        if env_key is None:
            continue
        if env_key in seen:
            continue
        seen.add(env_key)
        provider_name = (
            env_key.replace("_API_KEY", "").replace("_TOKEN", "").replace("_", " ").title().strip()
        )
        configured.append(
            {
                "name": provider_name,
                "env_var": env_key,
                "configured": _check_provider_configured(env_key),
                "models": [a for a, e in MODEL_PROVIDERS.items() if e == env_key],
            }
        )
    return configured
