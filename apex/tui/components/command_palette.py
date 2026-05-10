"""CommandPalette component - Command palette like OpenCode's CommandPalette."""

from typing import Optional, Callable, List, Dict
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt


class CommandPalette(BaseComponent):
    """CommandPalette component - like OpenCode's CommandPalette."""

    def __init__(self, console=None):
        super().__init__(console)
        self.commands: Dict[str, Dict] = {}
        self.filtered_commands: List[str] = []
        self.query = ""
        self.selected_index = 0
        self._on_select_callbacks: List[Callable] = []

    def register_command(
        self,
        id: str,
        label: str,
        shortcut: str = "",
        action: Optional[Callable] = None,
        category: str = "General"
    ) -> None:
        self.commands[id] = {
            "id": id,
            "label": label,
            "shortcut": shortcut,
            "action": action,
            "category": category
        }
        self._update_filtered()

    def unregister_command(self, id: str) -> None:
        self.commands.pop(id, None)
        self._update_filtered()

    def _update_filtered(self) -> None:
        if not self.query:
            self.filtered_commands = sorted(self.commands.keys())
        else:
            query_lower = self.query.lower()
            self.filtered_commands = sorted([
                k for k, v in self.commands.items()
                if query_lower in v["label"].lower() or query_lower in k.lower()
            ])

    def set_query(self, query: str) -> None:
        self.query = query
        self.selected_index = 0
        self._update_filtered()

    def select_next(self) -> None:
        if self.filtered_commands:
            self.selected_index = (self.selected_index + 1) % len(self.filtered_commands)

    def select_prev(self) -> None:
        if self.filtered_commands:
            self.selected_index = (self.selected_index - 1 + len(self.filtered_commands)) % len(self.filtered_commands)

    def execute_selected(self) -> Optional[str]:
        if self.filtered_commands and 0 <= self.selected_index < len(self.filtered_commands):
            cmd_id = self.filtered_commands[self.selected_index]
            cmd = self.commands.get(cmd_id)
            if cmd and cmd["action"]:
                cmd["action"]()
                return cmd_id
        return None

    def on_select(self, callback: Callable) -> None:
        self._on_select_callbacks.append(callback)

    def render(self) -> Panel:
        cmd_table = Table(box=None, padding=0, show_header=False)

        if not self.filtered_commands:
            cmd_table.add_row("[dim]No commands found[/]")
        else:
            for i, cmd_id in enumerate(self.filtered_commands[:10]):
                cmd = self.commands[cmd_id]
                prefix = "[bold cyan]▸[/]" if i == self.selected_index else "  "
                shortcut = f" [{cmd['shortcut']}]" if cmd["shortcut"] else ""
                label = f"{prefix} {cmd['label']}{shortcut}"
                category = f" [dim]({cmd['category']})[/]"
                cmd_table.add_row(label + category)

        header = Text.from_markup(f"[bold]Command Palette[/] [dim]| {self.query or 'Type to filter...'}[/]")

        return Panel(
            cmd_table,
            title=str(header),
            border_style="cyan",
            padding=(0, 1)
        )

    def clear(self) -> None:
        self.commands.clear()
        self.filtered_commands.clear()
        self.query = ""
        self.selected_index = 0