"""Home route - Main landing page."""

from typing import Optional
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .base import BaseRoute


class HomeRoute(BaseRoute):
    """Home route - like OpenCode's home route."""

    def __init__(self, console=None):
        super().__init__(RouteType.HOME, "home", console)
        self.title = "APEX - Universal AI Coding Agent"

    def render(self) -> Panel:
        welcome = Text.from_markup(
            "[bold cyan]◆ APEX[/] - Universal AI Coding Agent\n\n"
            "[dim]Your intelligent coding companion[/]"
        )

        info_table = Table(box=None, padding=0, title="[bold]Quick Info[/]")
        info_table.add_column("Key", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Version", "1.3.0")
        info_table.add_row("Sessions", "0 active")
        info_table.add_row("Plugins", "0 loaded")

        return Panel(
            welcome + "\n\n" + str(info_table),
            border_style="cyan",
            padding=(1, 2)
        )

    def on_mount(self) -> None:
        pass

    def on_destroy(self) -> None:
        pass

    def handle_action(self, action: str, data: dict = None) -> None:
        pass