"""Refactored plugins module - More testable and modular."""

from pathlib import Path
from typing import Any, Callable, Optional
from dataclasses import dataclass


@dataclass
class PluginInfo:
    """Information about a plugin."""

    name: str
    version: str
    description: str
    author: str = ""
    homepage: str = ""


@dataclass
class PluginHook:
    """A plugin hook/callback."""

    name: str
    callback: Callable
    priority: int = 0


class PluginRegistry:
    """Testable plugin registry."""

    def __init__(self):
        self._plugins: dict[str, Any] = {}
        self._enabled: dict[str, bool] = {}

    def register(self, name: str, plugin: Any) -> None:
        """Register a plugin."""
        self._plugins[name] = plugin
        self._enabled[name] = True

    def unregister(self, name: str) -> None:
        """Unregister a plugin."""
        self._plugins.pop(name, None)
        self._enabled.pop(name, None)

    def get(self, name: str) -> Optional[Any]:
        """Get a plugin."""
        return self._plugins.get(name)

    def is_enabled(self, name: str) -> bool:
        """Check if plugin is enabled."""
        return self._enabled.get(name, False)

    def enable(self, name: str) -> None:
        """Enable a plugin."""
        if name in self._plugins:
            self._enabled[name] = True

    def disable(self, name: str) -> None:
        """Disable a plugin."""
        self._enabled[name] = False

    def list_plugins(self) -> list[str]:
        """List all plugin names."""
        return list(self._plugins.keys())

    def list_enabled(self) -> list[str]:
        """List enabled plugin names."""
        return [name for name, enabled in self._enabled.items() if enabled]


class PluginHookManager:
    """Testable hook manager."""

    def __init__(self):
        self._hooks: dict[str, list[PluginHook]] = {}

    def register_hook(self, event: str, hook: PluginHook) -> None:
        """Register a hook."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(hook)
        # Sort by priority
        self._hooks[event].sort(key=lambda h: h.priority, reverse=True)

    def trigger_hook(self, event: str, *args, **kwargs) -> list:
        """Trigger all hooks for an event."""
        results = []
        if event in self._hooks:
            for hook in self._hooks[event]:
                try:
                    result = hook.callback(*args, **kwargs)
                    results.append(result)
                except Exception:
                    pass
        return results

    def clear_hooks(self, event: str = None) -> None:
        """Clear hooks."""
        if event:
            self._hooks.pop(event, None)
        else:
            self._hooks.clear()


class PluginManager(PluginRegistry, PluginHookManager):
    """Main plugin manager - combines registry and hooks."""

    def __init__(self, plugin_dirs: list[Path] = None):
        PluginRegistry.__init__(self)
        PluginHookManager.__init__(self)
        self._plugin_dirs = plugin_dirs or []
        self._app: Any = None

    def set_app(self, app: Any) -> None:
        """Set the application instance."""
        self._app = app

    def get_app(self) -> Any:
        """Get the application instance."""
        return self._app

    def load_plugins_from_directory(self, plugin_dir: Path) -> list[str]:
        """Load plugins from a directory."""
        loaded = []
        if not plugin_dir.is_dir():
            return loaded

        for plugin_file in plugin_dir.glob("*.py"):
            if plugin_file.stem.startswith("_"):
                continue
            loaded.append(plugin_file.stem)

        return loaded

    def get_all_tools(self) -> list[dict]:
        """Get all tools from enabled plugins."""
        tools = []
        for name, plugin in self._plugins.items():
            if not self._enabled.get(name, False):
                continue
            if hasattr(plugin, "get_tools"):
                try:
                    tools.extend(plugin.get_tools())
                except Exception:
                    pass
        return tools

    def cleanup(self, name: str) -> None:
        """Cleanup a specific plugin."""
        plugin = self._plugins.get(name)
        if plugin and hasattr(plugin, "cleanup"):
            try:
                plugin.cleanup()
            except Exception:
                pass
        self.unregister(name)


# Built-in plugins
class BuiltInPlugins:
    """Factory for built-in plugins."""

    @staticmethod
    def create_logger_plugin() -> type:
        """Create a logger plugin class."""

        class LoggerPlugin:
            info = PluginInfo(
                name="logger", version="1.0.0", description="Logs all tool calls and agent actions"
            )

            def __init__(self):
                self._logs = []

            def initialize(self, app) -> None:
                pass

            def cleanup(self) -> None:
                pass

            def get_tools(self) -> list[dict]:
                return []

            def log(self, event: str, data: dict) -> None:
                self._logs.append({"event": event, "data": data})

            def get_logs(self) -> list[dict]:
                return self._logs

        return LoggerPlugin

    @staticmethod
    def create_telemetry_plugin() -> type:
        """Create a telemetry plugin class."""

        class TelemetryPlugin:
            info = PluginInfo(
                name="telemetry", version="1.0.0", description="Collects telemetry data"
            )

            def __init__(self):
                self._events = []

            def initialize(self, app) -> None:
                pass

            def cleanup(self) -> None:
                pass

            def track_event(self, event: str, properties: dict = None) -> None:
                self._events.append({"event": event, "properties": properties or {}})

            def get_events(self) -> list[dict]:
                return self._events

        return TelemetryPlugin


# Testable factory
def create_plugin_manager(plugin_dirs: list = None) -> PluginManager:
    """Create a plugin manager."""
    return PluginManager([Path(d) for d in (plugin_dirs or [])])
