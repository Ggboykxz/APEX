"""CommandPalette — OpenCode-style floating command palette with search."""

from textual.widgets import Input, Static
from textual.widget import Widget
from textual.message import Message
from textual.screen import ModalScreen


# Categorized commands (OpenCode-style)
COMMAND_CATEGORIES = [
    ("Session", [
        ("/clear", "Clear conversation", "Ctrl+L"),
        ("/new", "New session", "Ctrl+N"),
        ("/save", "Save session", "Ctrl+S"),
        ("/load", "Load session", ""),
        ("/history", "Message history", ""),
    ]),
    ("Model", [
        ("/model", "Switch model", "Ctrl+M"),
        ("/models", "List all models", ""),
        ("/cost", "Token usage & cost", ""),
    ]),
    ("Navigation", [
        ("/cwd", "Change directory", ""),
        ("/theme", "Toggle theme", "Ctrl+T"),
        ("/mode", "Cycle mode (Plan/Agent/Yolo)", "Ctrl+Tab"),
        ("/sidebar", "Toggle sidebar", "Ctrl+\\"),
    ]),
    ("Help", [
        ("/help", "Keyboard shortcuts", "F1"),
        ("/exit", "Exit APEX", "Ctrl+Q"),
    ]),
]


class CommandPaletteItem(Widget):
    """Single command entry in the palette."""

    def __init__(self, command: str, description: str, shortcut: str = "", **kwargs):
        super().__init__(**kwargs)
        self.command = command
        self.description = description
        self.shortcut = shortcut

    def compose(self):
        yield Static("›", classes="palette-item-icon")
        yield Static(self.command, classes="palette-item-cmd")
        yield Static(self.description, classes="palette-item-desc")
        if self.shortcut:
            yield Static(self.shortcut, classes="palette-item-shortcut")


class CommandPalette(ModalScreen):
    """OpenCode-style command palette overlay with categorized search."""

    # Flatten all commands for search
    all_commands = [
        (cat, cmd, desc, shortcut)
        for cat, cmds in COMMAND_CATEGORIES
        for cmd, desc, shortcut in cmds
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filtered_commands = self.all_commands
        self.selected_index = 0
        self.current_category = ""

    def compose(self):
        yield Static(" ⌘  Commands                              [ESC]", id="palette-header")
        yield Input(placeholder="  Type to search commands...", id="palette-search-input")
        yield Static(id="palette-results-container")

    def on_mount(self) -> None:
        self._refresh_results()
        search_input = self.query_one("#palette-search-input", Input)
        search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower().strip()
        if query:
            self.filtered_commands = [
                (cat, cmd, desc, shortcut)
                for cat, cmd, desc, shortcut in self.all_commands
                if query in cmd.lower() or query in desc.lower() or query in cat.lower()
            ]
        else:
            self.filtered_commands = self.all_commands
        self.selected_index = 0
        self._refresh_results()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.filtered_commands:
            _, cmd, _, _ = self.filtered_commands[self.selected_index]
            self.post_message(PaletteCommand(cmd))
            self.app.pop_screen()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
        elif event.key == "up":
            self.selected_index = max(0, self.selected_index - 1)
            self._refresh_results()
        elif event.key == "down":
            self.selected_index = min(len(self.filtered_commands) - 1, self.selected_index + 1)
            self._refresh_results()
        elif event.key == "enter":
            if self.filtered_commands:
                _, cmd, _, _ = self.filtered_commands[self.selected_index]
                self.post_message(PaletteCommand(cmd))
                self.app.pop_screen()

    def _refresh_results(self) -> None:
        container = self.query_one("#palette-results-container", Static)
        if not self.filtered_commands:
            container.update("  No commands found")
            return

        lines = []
        last_category = ""
        for i, (cat, cmd, desc, shortcut) in enumerate(self.filtered_commands):
            # Category header
            if cat != last_category:
                lines.append(f"[dim bold]{cat}[/]")
                last_category = cat

            marker = "▸" if i == self.selected_index else " "
            shortcut_str = f"  [dim]{shortcut}[/]" if shortcut else ""
            if i == self.selected_index:
                lines.append(f"  [bold cyan]{marker} {cmd}[/]  [dim]{desc}[/]{shortcut_str}")
            else:
                lines.append(f"  {marker} [cyan]{cmd}[/]  [dim]{desc}[/]{shortcut_str}")

        container.update("\n".join(lines))


class PaletteCommand(Message):
    """Command selected from palette."""

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command
