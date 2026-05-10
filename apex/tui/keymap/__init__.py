"""Keymap system - Like OpenCode's @opentui/keymap."""

from typing import Callable, Optional, Any
from dataclasses import dataclass
from enum import Enum
from functools import partial


@dataclass
class KeymapBinding:
    """Key binding - like OpenCode's KeymapBinding."""
    key: str
    handler: Callable
    description: str = ""
    enabled: Callable[[], bool] = None
    layer: str = "global"
    mode: str = "normal"


class KeymapLayer:
    """Keymap layer - like OpenCode's layer system."""

    def __init__(self, name: str, enabled: Callable[[], bool] = None):
        self.name = name
        self.enabled = enabled or (lambda: True)
        self._bindings: dict[str, KeymapBinding] = {}

    def bind(self, key: str, handler: Callable, description: str = "") -> None:
        binding = KeymapBinding(key=key, handler=handler, description=description, layer=self.name)
        self._bindings[key] = binding

    def unbind(self, key: str) -> None:
        self._bindings.pop(key, None)

    def get_binding(self, key: str) -> Optional[KeymapBinding]:
        return self._bindings.get(key)

    def get_all_bindings(self) -> list[KeymapBinding]:
        return list(self._bindings.values())

    def clear(self) -> None:
        self._bindings.clear()


class KeymapManager:
    """Keymap manager - like OpenCode's keymap system."""

    def __init__(self, renderer=None):
        self.renderer = renderer
        self._layers: dict[str, KeymapLayer] = {}
        self._leader_key: Optional[str] = None
        self._leader_timeout: int = 1000
        self._leader_pending: bool = False
        self._leader_start_time: float = 0
        self._pending_keys: list[str] = []

        self._setup_default_layers()

    def _setup_default_layers(self) -> None:
        self.register_layer("global")
        self.register_layer("input")
        self.register_layer("command")
        self.register_layer("navigation")

    def register_layer(self, name: str, enabled: Callable = None) -> KeymapLayer:
        layer = KeymapLayer(name, enabled)
        self._layers[name] = layer
        return layer

    def unregister_layer(self, name: str) -> None:
        self._layers.pop(name, None)

    def get_layer(self, name: str) -> Optional[KeymapLayer]:
        return self._layers.get(name)

    def bind(self, key: str, handler: Callable, description: str = "", layer: str = "global") -> None:
        layer_obj = self._layers.get(layer)
        if layer_obj:
            layer_obj.bind(key, handler, description)

    def unbind(self, key: str, layer: str = "global") -> None:
        layer_obj = self._layers.get(layer)
        if layer_obj:
            layer_obj.unbind(key)

    def set_leader_key(self, key: str, timeout_ms: int = 1000) -> None:
        self._leader_key = key
        self._leader_timeout = timeout_ms

    def handle_key(self, key: str, context: dict = None) -> bool:
        """Handle a key press - returns True if consumed."""
        context = context or {}

        for layer_name in ["input", "command", "navigation", "global"]:
            layer = self._layers.get(layer_name)
            if not layer or not layer.enabled():
                continue

            binding = layer.get_binding(key)
            if binding:
                if binding.enabled and not binding.enabled():
                    continue
                binding.handler(context)
                return True

        return False

    def get_bindings_for_display(self) -> list[tuple[str, str, str]]:
        """Get all bindings for help display."""
        bindings = []
        for layer_name, layer in self._layers.items():
            for binding in layer.get_all_bindings():
                bindings.append((layer_name, binding.key, binding.description))
        return bindings


def create_default_apex_keymap(renderer) -> KeymapManager:
    """Create default APEX keymap - like OpenCode's createDefaultOpenTuiKeymap."""

    keymap = KeymapManager(renderer)

    global_layer = keymap.get_layer("global")
    if global_layer:
        global_layer.bind("q", lambda c: exit(0), "Quit")
        global_layer.bind("?", lambda c: print("Help"), "Show help")
        global_layer.bind(":", lambda c: keymap.register_layer("command"), "Open command palette")
        global_layer.bind("gg", lambda c: print("Go to top"), "Go to top")
        global_layer.bind("G", lambda c: print("Go to bottom"), "Go to bottom")
        global_layer.bind("zz", lambda c: print("Center view"), "Center view")

    nav_layer = keymap.get_layer("navigation")
    if nav_layer:
        nav_layer.bind("h", lambda c: print("Move left"), "Move left")
        nav_layer.bind("j", lambda c: print("Move down"), "Move down")
        nav_layer.bind("k", lambda c: print("Move up"), "Move up")
        nav_layer.bind("l", lambda c: print("Move right"), "Move right")
        nav_layer.bind("0", lambda c: print("Go to start"), "Go to start")
        nav_layer.bind("$", lambda c: print("Go to end"), "Go to end")
        nav_layer.bind("w", lambda c: print("Next word"), "Next word")
        nav_layer.bind("b", lambda c: print("Prev word"), "Prev word")

    return keymap


def register_apex_keymap(keymap: KeymapManager, renderer, config: dict) -> Callable:
    """Register APEX-specific keybindings - like OpenCode's registerOpencodeKeymap."""

    global_layer = keymap.get_layer("global")
    if global_layer:
        global_layer.bind("m", lambda c: print("Models"), "Show models")
        global_layer.bind("a", lambda c: print("Agents"), "Show agents")
        global_layer.bind("s", lambda c: print("Sessions"), "Show sessions")
        global_layer.bind("t", lambda c: print("Theme"), "Switch theme")
        global_layer.bind("c", lambda c: print("Console"), "Toggle console")
        global_layer.bind("p", lambda c: print("Plugins"), "Show plugins")

        keymap.set_leader_key("Space", timeout_ms=1000)

    input_layer = keymap.get_layer("input")
    input_enabled = lambda: renderer and renderer.current_focused_editor is not None
    input_layer.enabled = input_enabled

    def exit_handler(c):
        print("Exiting APEX...")
        exit(0)

    keymap.bind("q", exit_handler, "Quit", layer="global")

    return keymap