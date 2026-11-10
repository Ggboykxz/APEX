"""APEX Hook system.

Modelled on OpenCode's ``PluginHooks.Service``.  Hooks are organised by
*domain* and *name*:

- ``aisdk``   — AI SDK lifecycle (request / response / error)
- ``session`` — session lifecycle (start / end / save / load)
- ``permission`` — permission decisions (allow / deny / ask)
- ``shell``   — shell command execution (before / after / error)
- ``tool``    — tool execution (``tool.execute.before`` can reject an call)

A hook may be scoped to a specific ``providerID``.  Only
``tool.execute.before`` may fail: raising there rejects the tool call before
it executes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = [
    "HookCallback",
    "HookDomain",
    "HookError",
    "HookEvent",
    "HookOptions",
    "PluginHooks",
]


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

HookDomain = str
HookName = str
HookEvent = dict[str, Any]
HookCallback = Callable[[HookEvent], object | None]
HookOptions = dict[str, Any]


class HookError(Exception):
    """Raised by a ``tool.execute.before`` hook to reject a tool call."""


# ---------------------------------------------------------------------------
# Hook service
# ---------------------------------------------------------------------------


@dataclass
class _HookEntry:
    name: HookName
    callback: HookCallback
    options: HookOptions
    provider_id: str | None = None


class PluginHooks:
    """Register and trigger hooks across domains."""

    # Domains where a hook failure propagates and cancels the operation.
    FAILABLE_DOMAINS: frozenset[str] = frozenset({"tool"})

    def __init__(self) -> None:
        # (domain, name) -> list[_HookEntry]
        self._hooks: dict[tuple[HookDomain, HookName], list[_HookEntry]] = {}

    # -- registration -------------------------------------------------------

    def register(
        self,
        domain: HookDomain,
        name: HookName,
        callback: HookCallback,
        *,
        provider_id: str | None = None,
        **options: Any,
    ) -> None:
        key = (domain, name)
        self._hooks.setdefault(key, []).append(
            _HookEntry(name=name, callback=callback, options=options, provider_id=provider_id)
        )

    def unregister(
        self,
        domain: HookDomain,
        name: HookName,
        provider_id: str | None = None,
    ) -> None:
        key = (domain, name)
        if key not in self._hooks:
            return
        self._hooks[key] = [entry for entry in self._hooks[key] if entry.provider_id != provider_id]
        if not self._hooks[key]:
            del self._hooks[key]

    # -- queries ------------------------------------------------------------

    def has(self, domain: HookDomain, name: HookName, provider_id: str | None = None) -> bool:
        """Return ``True`` if at least one hook matches (optionally by provider)."""
        for entry in self._hooks.get((domain, name), ()):
            if provider_id is None or entry.provider_id == provider_id:
                return True
        return False

    def list(self, domain: HookDomain, name: HookName) -> tuple[_HookEntry, ...]:
        return tuple(self._hooks.get((domain, name), ()))

    # -- trigger ------------------------------------------------------------

    def trigger(self, domain: HookDomain, name: HookName, event: HookEvent) -> list[object]:
        """Run every hook matching ``(domain, name)``.

        Returns the list of return values.  If a hook in a failable domain
        (currently ``tool``) raises :class:`HookError`, the exception
        propagates and the caller should reject the operation.
        """
        results: list[object] = []
        for entry in self.list(domain, name):
            # Respect provider scoping: the event carries ``provider_id``.
            event_provider = event.get("provider_id")
            if entry.provider_id is not None and entry.provider_id != event_provider:
                continue
            result = entry.callback(event)
            results.append(result)
        return results

    # -- convenience --------------------------------------------------------

    def trigger_tool_before(self, event: HookEvent) -> HookError | None:
        """Run ``tool.execute.before`` hooks.

        Returns the first :class:`HookError` raised, or ``None`` if all hooks
        passed.  Callers should reject the tool call when a error is returned.
        """
        for entry in self.list("tool", "execute.before"):
            event_provider = event.get("provider_id")
            if entry.provider_id is not None and entry.provider_id != event_provider:
                continue
            try:
                entry.callback(event)
            except HookError as exc:
                return exc
        return None


__all__ = [
    "HookCallback",
    "HookDomain",
    "HookError",
    "HookEvent",
    "HookName",
    "HookOptions",
    "PluginHooks",
]
