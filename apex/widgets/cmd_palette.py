"""CommandPalette — OpenCode-style floating command palette with search.

Refonte: Enhanced with:
- Better category headers
- Keyboard navigation (up/down/enter/escape)
- Search filtering across all categories
- Shortcut display for each command
- Highlight selected item
- APEX-specific commands (agents, modes, skills)
"""

from textual.widgets import Input, Static
from textual.widget import Widget
from textual.message import Message
from textual.screen import ModalScreen
from textual.binding import Binding


# ── Command Categories ────────────────────────────────────────────────────────

COMMAND_CATEGORIES = [
    ("Session", [
        ("/clear", "Clear conversation", "Ctrl+L"),
        ("/new", "New session", "Ctrl+N"),
        ("/save", "Save session", "Ctrl+S"),
        ("/load", "Load session", ""),
        ("/history", "Message history", ""),
    ]),
    ("Model", [
        ("/model", "Switch model", "Ctrl+O"),
        ("/models", "List all models", ""),
        ("/cost", "Token usage & cost", ""),
    ]),
    ("Agent", [
        ("/agent", "Switch agent (build/plan/explore/general/yolo)", ""),
        ("/agents", "List all agents", ""),
        ("/mode", "Cycle mode (Plan/Agent/Yolo)", "Ctrl+Tab"),
        ("/plan", "Switch to Plan mode (read-only)", ""),
        ("/build", "Switch to Build mode (interactive)", ""),
        ("/yolo", "Switch to Yolo mode (auto-approve)", ""),
    ]),
    ("Navigation", [
        ("/cwd", "Change directory", ""),
        ("/theme", "Theme picker", "Ctrl+T"),
        ("/sidebar", "Toggle sidebar", "Ctrl+\\"),
        ("/logs", "View logs", "Ctrl+L"),
    ]),
    ("Tools", [
        ("/skills", "List available skills", ""),
        ("/map", "Show repository map", ""),
        ("/git", "Git status", ""),
        ("/undo", "Undo last change", ""),
        ("/redo", "Redo last change", ""),
    ]),
    ("Help", [
        ("/help", "Keyboard shortcuts", "Ctrl+H"),
        ("/exit", "Exit APEX", "Ctrl+C"),
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
    """OpenCode-style command palette overlay with categorized search.

    Features:
    - Categorized commands with section headers
    - Fuzzy search across commands and descriptions
    - Keyboard navigation (up/down/enter/escape)
    - Selected item highlighting
    - Shortcut display
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
        Binding("up", "prev_item", "Prev", show=False),
        Binding("down", "next_item", "Next", show=False),
        Binding("enter", "select_item", "Select", show=False),
    ]

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

    def compose(self):
        yield Static(" ◆  Command Palette                    [ESC]", id="palette-header")
        yield Input(placeholder="  Type to search commands...", id="palette-search-input")
        yield Static(id="palette-results-container")

    def on_mount(self) -> None:
        self._refresh_results()
        search_input = self.query_one("#palette-search-input", Input)
        search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower().strip()
        if query:
            # Fuzzy search: match against command name, description, and category
            self.filtered_commands = [
                (cat, cmd, desc, shortcut)
                for cat, cmd, desc, shortcut in self.all_commands
                if (query in cmd.lower()
                    or query in desc.lower()
                    or query in cat.lower())
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

    def action_prev_item(self) -> None:
        if self.filtered_commands:
            self.selected_index = max(0, self.selected_index - 1)
            self._refresh_results()

    def action_next_item(self) -> None:
        if self.filtered_commands:
            self.selected_index = min(len(self.filtered_commands) - 1, self.selected_index + 1)
            self._refresh_results()

    def action_select_item(self) -> None:
        if self.filtered_commands:
            _, cmd, _, _ = self.filtered_commands[self.selected_index]
            self.post_message(PaletteCommand(cmd))
            self.app.pop_screen()

    def action_close(self) -> None:
        self.app.pop_screen()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.action_close()

    def _refresh_results(self) -> None:
        try:
            container = self.query_one("#palette-results-container", Static)
            if not self.filtered_commands:
                container.update("  [dim]No commands found[/]")
                return

            lines = []
            last_category = ""
            for i, (cat, cmd, desc, shortcut) in enumerate(self.filtered_commands):
                # Category header
                if cat != last_category:
                    lines.append(f"[dim bold]{cat}[/]")
                    last_category = cat

                if i == self.selected_index:
                    lines.append(
                        f"  [bold cyan]▸ {cmd}[/]  [dim]{desc}[/]"
                        + (f"  [dim]{shortcut}[/]" if shortcut else "")
                    )
                else:
                    lines.append(
                        f"    [cyan]{cmd}[/]  [dim]{desc}[/]"
                        + (f"  [dim]{shortcut}[/]" if shortcut else "")
                    )

            container.update("\n".join(lines))
        except Exception:
            pass


class PaletteCommand(Message):
    """Command selected from palette."""

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command
