"""Plugin system for TUI - like OpenCode's plugin system."""

from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import importlib.util
import sys


@dataclass
class PluginMetadata:
    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    enabled: bool = True


class Plugin:
    """Base plugin class - like OpenCode's Plugin class."""

    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self._enabled = metadata.enabled
        self._routes: Dict[str, Any] = {}
        self._commands: Dict[str, Callable] = {}
        self._keybindings: List[tuple] = []

    def on_install(self) -> None:
        """Called when plugin is installed."""
        pass

    def on_uninstall(self) -> None:
        """Called when plugin is uninstalled."""
        pass

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        self._enabled = True

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def register_route(self, name: str, route: Any) -> None:
        self._routes[name] = route

    def register_command(self, id: str, command: Callable) -> None:
        self._commands[id] = command

    def register_keybinding(self, key: str, handler: Callable, layer: str = "global") -> None:
        self._keybindings.append((key, handler, layer))


class PluginManager:
    """Plugin manager - like OpenCode's PluginManager."""

    def __init__(self, plugins_dir: Optional[Path] = None):
        self.plugins_dir = plugins_dir or Path(__file__).parent
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "on_tui_ready": [],
            "on_tui_exit": [],
            "on_route_change": [],
            "on_key_press": [],
            "on_theme_change": [],
        }

    def load_plugin(self, plugin_id: str, plugin_class: type) -> Plugin:
        metadata = PluginMetadata(id=plugin_id, name=plugin_id, version="0.0.1")
        plugin = plugin_class(metadata)
        self._plugins[plugin_id] = plugin
        plugin.on_install()
        return plugin

    def enable_plugin(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.on_enable()
            return True
        return False

    def disable_plugin(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.on_disable()
            return True
        return False

    def unload_plugin(self, plugin_id: str) -> bool:
        plugin = self._plugins.pop(plugin_id, None)
        if plugin:
            plugin.on_uninstall()
            return True
        return False

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> List[PluginMetadata]:
        return [p.metadata for p in self._plugins.values()]

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        if hook_name in self._hooks:
            self._hooks[hook_name].append(callback)

    def emit_hook(self, hook_name: str, *args, **kwargs) -> None:
        for callback in self._hooks.get(hook_name, []):
            callback(*args, **kwargs)

    def load_from_directory(self, directory: Path) -> List[str]:
        loaded = []
        if not directory.exists():
            return loaded

        for py_file in directory.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[py_file.stem] = module
                    spec.loader.exec_module(module)

                    if hasattr(module, "register"):
                        plugin_instance = module.register(self)
                        if plugin_instance:
                            loaded.append(plugin_instance.metadata.id)
            except Exception:
                pass

        return loaded