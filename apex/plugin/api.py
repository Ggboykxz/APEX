"""APEX Plugin system.

Modelled on OpenCode's ``@opencode/plugin`` (Promise + Effect APIs).  A plugin
is a declarative unit that receives a rich ``PluginContext`` and can register
agents, commands, skills, hooks, MCP servers, tools, etc. against the Core.

Plugins are loaded asynchronously and never block the server.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from apex.core.service import Core

__all__ = ["Plugin", "PluginContext", "PluginManager", "define"]


# ---------------------------------------------------------------------------
# Plugin context
# ---------------------------------------------------------------------------


@dataclass
class PluginContext:
    """Rich context injected into every plugin.

    Mirrors OpenCode's plugin context (app, location, options, agent, aisdk,
    command, credential, event, experimental, integration, mcp, model,
    permission, plugin, provider, reference, rpc, session, shell, skill,
    storage, tool, vcs, websearch, worktree).
    """

    core: Core
    options: dict[str, Any] = field(default_factory=dict)

    # Convenience aliases for the most-used services.
    @property
    def agent(self):
        return self.core.agent

    @property
    def command(self):
        return self.core.command

    @property
    def skill(self):
        return self.core.skill


# ---------------------------------------------------------------------------
# Plugin definition
# ---------------------------------------------------------------------------


@runtime_checkable
class Plugin(Protocol):
    """A plugin unit.

    ``effect`` receives a :class:`PluginContext` and returns an awaitable.
    It may register anything against the Core (agents, commands, skills,
    hooks, MCP servers, tools …).
    """

    id: str
    effect: Callable[[PluginContext], object]


def define(plugin_id: str, effect: Callable[[PluginContext], object]) -> Plugin:
    """Create a plugin.

    Example::

        from apex.plugin import define
        from apex.core.service import AgentInfo, AgentID
        from apex.schema import AgentMode, PermissionAction, AgentPermission

        async def my_effect(ctx: PluginContext):
            ctx.agent.register(AgentInfo(
                id=AgentID("my-agent"),
                name="my-agent",
                model="claude-sonnet-4-5",
                mode=AgentMode.SUBAGENT,
            ))

        my_plugin = define("my-plugin", my_effect)
    """
    return _Plugin(plugin_id, effect)


class _Plugin:
    def __init__(self, plugin_id: str, effect: Callable[[PluginContext], object]):
        self.id = plugin_id
        self.effect = effect

    def __repr__(self) -> str:
        return f"Plugin(id={self.id!r})"


# ---------------------------------------------------------------------------
# Plugin manager
# ---------------------------------------------------------------------------


class PluginManager:
    """Load, activate and unload plugins.

    Plugins are activated asynchronously; the manager never blocks the
    caller while a plugin's ``effect`` runs.
    """

    def __init__(self, core: Core) -> None:
        self.core = core
        self._plugins: dict[str, Plugin] = {}
        self._activated: set[str] = set()

    # -- registration -------------------------------------------------------

    def register(self, plugin: Plugin) -> None:
        self._plugins[plugin.id] = plugin

    def unregister(self, plugin_id: str) -> None:
        self._plugins.pop(plugin_id, None)
        self._activated.discard(plugin_id)

    # -- queries ------------------------------------------------------------

    def get(self, plugin_id: str) -> Plugin | None:
        return self._plugins.get(plugin_id)

    def list(self) -> tuple[Plugin, ...]:
        return tuple(self._plugins.values())

    def is_activated(self, plugin_id: str) -> bool:
        return plugin_id in self._activated

    # -- activation ---------------------------------------------------------

    async def activate(self, plugin_id: str) -> None:
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise KeyError(f"unknown plugin {plugin_id}")
        if plugin_id in self._activated:
            return

        ctx = PluginContext(core=self.core)
        result = plugin.effect(ctx)
        # Support both sync and async effects.
        if hasattr(result, "__await__"):
            # The value of an effect is not used; awaiting it is the point.
            _ = await result

        self._activated.add(plugin_id)

    async def activate_all(self) -> None:
        for plugin_id in list(self._plugins):
            await self.activate(plugin_id)

    async def deactivate(self, plugin_id: str) -> None:
        self._activated.discard(plugin_id)

    async def deactivate_all(self) -> None:
        self._activated.clear()


__all__ = ["Plugin", "PluginContext", "PluginManager", "define"]
