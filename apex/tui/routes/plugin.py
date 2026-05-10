"""Plugin route - Plugin management view."""

from typing import Optional, List
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED

from .base import BaseRoute
from .route_type import RouteType


class PluginRoute(BaseRoute):
    """Plugin route - like OpenCode's plugin route."""

    def __init__(self, plugin_id: str = "", console=None):
        super().__init__(RouteType.PLUGIN, plugin_id, console)
        self.plugin_id = plugin_id
        self.plugins: List[dict] = []

    def render(self) -> Panel:
        plugins_table = Table(box=ROUNDED, padding=1, show_header=True)
        plugins_table.add_column("Plugin", style="cyan", width=20)
        plugins_table.add_column("Version", style="dim", width=10)
        plugins_table.add_column("Status", style="green", width=10)

        if self.plugins:
            for plugin in self.plugins:
                name = plugin.get("name", "Unknown")
                version = plugin.get("version", "0.0.0")
                enabled = plugin.get("enabled", True)
                status = "[green]enabled[/]" if enabled else "[red]disabled[/]"
                plugins_table.add_row(name, version, status)
        else:
            plugins_table.add_row("[dim]No plugins loaded[/]", "", "")

        header = Text.from_markup("[bold cyan]Plugins[/]")
        footer = Text.from_markup(
            f"[dim]Total: {len(self.plugins)} plugins[/]"
        )

        return Panel(
            plugins_table,
            title=str(header),
            subtitle=str(footer),
            border_style="magenta",
            padding=(1, 2)
        )

    def load_plugins(self, plugins: List[dict]) -> None:
        self.plugins = plugins

    def on_mount(self) -> None:
        pass

    def on_destroy(self) -> None:
        pass

    def handle_action(self, action: str, data: dict = None) -> None:
        if action == "refresh":
            self.console.print("[cyan]Refreshing plugins...[/]")
        elif action == "install":
            self.console.print("[cyan]Opening plugin installer...[/]")