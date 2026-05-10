"""Session route - Active coding session."""

from typing import Optional, List
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import SIMPLE

from .base import BaseRoute
from .route_type import RouteType


class SessionRoute(BaseRoute):
    """Session route - like OpenCode's session route."""

    def __init__(self, session_id: str, title: str = "", console=None):
        super().__init__(RouteType.SESSION, session_id, console)
        self.session_id = session_id
        self.title = title or f"Session {session_id[:8]}"
        self.messages: List[dict] = []
        self.input_mode = "command"

    def render(self) -> Panel:
        messages_table = Table(box=SIMPLE, padding=0, show_header=False)
        messages_table.add_column("role", style="bold cyan", width=8)
        messages_table.add_column("content")

        for msg in self.messages[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:100]
            messages_table.add_row(role, content)

        if not self.messages:
            messages_table.add_row("system", "No messages yet. Start typing!")

        header = Text.from_markup(
            f"[bold cyan]Session:[/] {self.title}\n"
            f"[dim]ID: {self.session_id[:8]}... | Mode: {self.input_mode}[/]"
        )

        return Panel(
            messages_table,
            title=str(header),
            border_style="green",
            padding=(1, 1)
        )

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def set_input_mode(self, mode: str) -> None:
        self.input_mode = mode

    def on_mount(self) -> None:
        pass

    def on_destroy(self) -> None:
        pass

    def handle_action(self, action: str, data: dict = None) -> None:
        if action == "clear":
            self.messages.clear()
        elif action == "export":
            self.console.print("[cyan]Exporting session...[/]")