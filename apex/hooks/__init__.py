"""APEX Hooks package — re-export the public API."""

from apex.hooks.service import (
    HookCallback,
    HookDomain,
    HookError,
    HookEvent,
    HookOptions,
    PluginHooks,
)

__all__ = [
    "HookCallback",
    "HookDomain",
    "HookError",
    "HookEvent",
    "HookOptions",
    "PluginHooks",
]
