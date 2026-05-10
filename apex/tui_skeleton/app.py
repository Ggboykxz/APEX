"""APEX TUI Application - OpenTUI-like architecture."""

import asyncio
import sys
import signal
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

from .themes import ThemeManager, APEX_THEME
from .keymap import KeymapManager, KeymapBinding, KeymapLayer
from .routes import BaseRoute, RouteType, Route
from .routes.home import HomeRoute
from .routes.session import SessionRoute
from .routes.plugin import PluginRoute
from .components import ToastManager, StatusBar, CommandPalette


class RendererConfig:
    mouse: bool = True
    alternate_screen: bool = True
    title: str = "APEX"
    palette_size: int = 16
    scrollback: int = 10000


class Renderer:
    def __init__(self, config: Optional[RendererConfig] = None):
        self.config = config or RendererConfig()
        self.console = Console(force_terminal=True, quiet=True)
        self._title = self.config.title
        self._palette_warmed = False
        self._focused_editor: Optional[str] = None

    @property
    def current_focused_editor(self) -> Optional[str]:
        return self._focused_editor

    @property
    def title(self) -> str:
        return self._title

    def set_title(self, title: str) -> None:
        self._title = title
        print(f"\033]0;{title}\007", end="", flush=True)

    def get_palette(self, size: int = 16) -> dict:
        self._palette_warmed = True
        return self._get_default_palette(size)

    def _get_default_palette(self, size: int) -> dict:
        return {f"color_{i}": i for i in range(size)}

    def wait_for_theme_mode(self, timeout_ms: int = 1000) -> str:
        return "dark"

    def suspend(self) -> None:
        pass

    def resume(self) -> None:
        pass

    def clear(self) -> None:
        self.console.clear()

    def print(self, *args, **kwargs) -> None:
        self.console.print(*args, **kwargs)

    @property
    def console_output(self):
        return self.console


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def on(self, event: str, handler: Callable) -> None:
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def once(self, event: str, handler: Callable) -> None:
        original_handler = handler
        def wrapper(*args, **kwargs):
            original_handler(*args, **kwargs)
            self.off(event, wrapper)
        self.on(event, wrapper)

    def emit(self, event: str, *args, **kwargs) -> None:
        for handler in self._handlers.get(event, []):
            handler(*args, **kwargs)

    def off(self, event: str, handler: Callable) -> None:
        if event in self._handlers:
            self._handlers[event] = [h for h in self._handlers[event] if h != handler]

    def clear(self, event: str = None) -> None:
        if event:
            self._handlers.pop(event, None)
        else:
            self._handlers.clear()


class ThemeContext:
    def __init__(self, theme_manager: Optional[ThemeManager] = None):
        self.theme_manager = theme_manager or ThemeManager()
        self._current_theme = "opencode"
        self._mode = "dark"

    @property
    def theme(self) -> dict:
        return self.theme_manager.get_theme(self._current_theme)

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str) -> None:
        self._mode = value

    def set_theme(self, name: str) -> None:
        self._current_theme = name

    def get_color(self, key: str) -> str:
        return self.theme.get(key, "#000000")

    def list_themes(self) -> list[str]:
        return self.theme_manager.list_themes()


class RouteContext:
    def __init__(self):
        self._current_route: Optional[Route] = None
        self._route_handlers: dict[RouteType, Callable] = {}
        self._routes: Dict[str, BaseRoute] = {}

    @property
    def current_route(self) -> Optional[Route]:
        return self._current_route

    def register_route(self, name: str, route: BaseRoute) -> None:
        self._routes[name] = route

    def get_route(self, name: str) -> Optional[BaseRoute]:
        return self._routes.get(name)

    def navigate(self, route: Route) -> None:
        self._current_route = route

    def navigate_home(self) -> None:
        self.navigate(Route(RouteType.HOME, "home"))

    def navigate_session(self, session_id: str, title: str = "") -> None:
        self.navigate(Route(RouteType.SESSION, session_id, {"title": title or session_id}))

    def navigate_plugin(self, plugin_id: str) -> None:
        self.navigate(Route(RouteType.PLUGIN, plugin_id))

    def register_route_handler(self, route_type: RouteType, handler: Callable) -> None:
        self._route_handlers[route_type] = handler


class APEXTUI:
    def __init__(self, config: Optional[RendererConfig] = None):
        self.config = config or RendererConfig()
        self.renderer = Renderer(self.config)
        self.console = self.renderer.console_output
        self.event_bus = EventBus()
        self.theme = ThemeContext()
        self.route = RouteContext()
        self.keymap = KeymapManager(self.renderer)
        self.toast_manager = ToastManager(self.console)
        self.status_bar = StatusBar(self.console)
        self.command_palette = CommandPalette(self.console)

        self._running = False
        self._ready = False
        self._layout: Optional[Layout] = None
        self._current_view: Optional[BaseRoute] = None

        self._setup_signal_handlers()
        self._setup_keymap()
        self._setup_routes()
        self._setup_status_bar()

    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGTSTP, lambda s, f: self.renderer.suspend())
        signal.signal(signal.SIGCONT, lambda s, f: self.renderer.resume())

    def _setup_keymap(self) -> None:
        from .keymap import create_default_apex_keymap, register_apex_keymap

        create_default_apex_keymap(self.renderer)
        register_apex_keymap(self.keymap, self.renderer, {})

        global_layer = self.keymap.get_layer("global")
        if global_layer:
            global_layer.bind("q", lambda c: self.stop(), "Quit")
            global_layer.bind("?", lambda c: self._show_help(), "Show help")
            global_layer.bind(":", lambda c: self._open_command_palette(), "Command palette")
            global_layer.bind("t", lambda c: self._cycle_theme(), "Cycle theme")
            global_layer.bind("n", lambda c: self._new_session(), "New session")
            global_layer.bind("p", lambda c: self._show_plugins(), "Show plugins")

    def _setup_routes(self) -> None:
        home_route = HomeRoute(self.console)
        self.route.register_route("home", home_route)
        self.route.navigate_home()

    def _setup_status_bar(self) -> None:
        self.status_bar.set_left(["APEX v1.3.0"])
        self.status_bar.set_center(["Normal Mode"])
        self.status_bar.set_right(["UTF-8"])

    def _show_help(self) -> None:
        self.console.print(Panel(
            "[bold cyan]APEX Keyboard Shortcuts[/]\n\n"
            "[cyan]q[reset] - Quit\n"
            "[cyan]?[reset] - Show this help\n"
            "[cyan]:[reset] - Command palette\n"
            "[cyan]t[reset] - Cycle theme\n"
            "[cyan]n[reset] - New session\n"
            "[cyan]p[reset] - Show plugins\n"
            "[cyan]Ctrl+C[reset] - Exit\n",
            title="Help",
            border_style="cyan"
        ))

    def _open_command_palette(self) -> None:
        self.command_palette.register_command("quit", "Quit", "q", lambda: self.stop())
        self.command_palette.register_command("help", "Show Help", "?", self._show_help)
        self.command_palette.register_command("new_session", "New Session", "n", self._new_session)
        self.console.print(self.command_palette.render())

    def _cycle_theme(self) -> None:
        themes = self.theme.list_themes()
        current = themes.index(self.theme._current_theme) if self.theme._current_theme in themes else 0
        next_idx = (current + 1) % len(themes)
        self.theme.set_theme(themes[next_idx])
        self.toast_manager.info(f"Theme: {themes[next_idx]}")

    def _new_session(self) -> None:
        import uuid
        session_id = str(uuid.uuid4())[:8]
        session_route = SessionRoute(session_id, f"Session {session_id}", self.console)
        self.route.register_route(session_id, session_route)
        self.route.navigate_session(session_id, session_route.title)
        self._current_view = session_route

    def _show_plugins(self) -> None:
        plugin_route = PluginRoute("", self.console)
        self.route.register_route("plugins", plugin_route)
        self.route.navigate_plugin("plugins")
        self._current_view = plugin_route

    async def start(self) -> None:
        self._running = True
        self.renderer.set_title(self.config.title)
        self.renderer.get_palette(self.config.palette_size)
        self._ready = True
        self.event_bus.emit("tui:ready")
        self.event_bus.on("tui:exit", lambda: self.stop())

    async def run(self) -> None:
        await self.start()

        welcome = Panel(
            "[bold cyan]◆ APEX[/] - Universal AI Coding Agent\n\n"
            "[dim]Press [cyan]?[/] for help, [cyan]:[/] for commands[/]",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(welcome)

        try:
            while self._running:
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            self._running = False

    def stop(self) -> None:
        self._running = False
        self.event_bus.emit("tui:exit")

    def navigate_home(self) -> None:
        self.route.navigate_home()
        self._current_view = self.route.get_route("home")
        self.event_bus.emit("route:change", self.route.current_route)

    def navigate_session(self, session_id: str, title: str = "") -> None:
        self.route.navigate_session(session_id, title)
        self._current_view = self.route.get_route(session_id)
        self.event_bus.emit("route:change", self.route.current_route)


def run_tui(config: Optional[RendererConfig] = None) -> None:
    app = APEXTUI(config)

    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print("\nExiting APEX TUI...")


if __name__ == "__main__":
    run_tui()