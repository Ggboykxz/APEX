"""CommandPalette - Ctrl+K command picker."""

from textual.widgets import Input, Static
from textual.widget import Widget
from textual.message import Message
from textual.screen import ModalScreen


class CommandPaletteItem(Widget):
    def __init__(self, command: str, description: str, **kwargs):
        super().__init__(**kwargs)
        self.command = command
        self.description = description

    def compose(self):
        yield Static(">", classes="palette-item-icon")
        yield Static(self.command, classes="palette-item-cmd")
        yield Static(self.description, classes="palette-item-desc")


class CommandPalette(ModalScreen):
    commands = [
        ("/model", "Switch to a specific model"),
        ("/models", "List all available models"),
        ("/clear", "Clear the conversation"),
        ("/save", "Save current session"),
        ("/load", "Load a saved session"),
        ("/cwd", "Show/change working directory"),
        ("/theme", "Toggle between themes"),
        ("/history", "Show message history"),
        ("/cost", "Show token usage and cost"),
        ("/help", "Show keyboard shortcuts"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filtered_commands = self.commands
        self.selected_index = 0

    def compose(self):
        yield Static("╔════════════════════════════════════════╗", classes="palette-border-top")
        yield Static("║ ⌘ APEX Commands                    [ESC] ║", classes="palette-header")
        yield Static("╠════════════════════════════════════════╣", classes="palette-border")
        yield Input(placeholder="Type to search commands...", id="palette-search", classes="palette-input")
        yield Static("╠════════════════════════════════════════╣", classes="palette-border")
        yield Static(id="palette-results", classes="palette-results")
        yield Static("╚════════════════════════════════════════╝", classes="palette-border-bottom")

    def on_mount(self) -> None:
        self._refresh_results()
        search_input = self.query_one("#palette-search", Input)
        search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        if query:
            self.filtered_commands = [
                (cmd, desc) for cmd, desc in self.commands if query in cmd.lower() or query in desc.lower()
            ]
        else:
            self.filtered_commands = self.commands
        self.selected_index = 0
        self._refresh_results()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.filtered_commands:
            cmd, _ = self.filtered_commands[self.selected_index]
            self.post_message(PaletteCommand(cmd))
            self.app.pop_screen()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
        elif event.key == "up":
            self.selected_index = max(0, self.selected_index - 1)
            self._update_selection()
        elif event.key == "down":
            self.selected_index = min(len(self.filtered_commands) - 1, self.selected_index + 1)
            self._update_selection()

    def _refresh_results(self) -> None:
        container = self.query_one("#palette-results", Static)
        if not self.filtered_commands:
            container.update("║ No commands found                      ║")
            return
        lines = ["║"]
        for i, (cmd, desc) in enumerate(self.filtered_commands):
            marker = "▶" if i == self.selected_index else " "
            cmd_padded = cmd.ljust(18)
            desc_padded = desc[:25].ljust(25)
            lines.append(f"║  {marker} {cmd_padded}  {desc_padded}║")
        lines.append("╚" + "═" * 42 + "╝")
        container.update("\n".join(lines))

    def _update_selection(self) -> None:
        self._refresh_results()


class PaletteCommand(Message):
    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command
