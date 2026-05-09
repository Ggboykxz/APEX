"""StatusBar - Shortcuts and model status."""

from textual.widgets import Static
from textual.widget import Widget
from textual.reactive import reactive


class StatusBar(Widget):
    is_thinking = reactive(False)
    model = reactive("or-gpt4o-mini")

    def compose(self):
        yield Static("●", id="status-dot", classes="status-model-dot")
        yield Static(self.model, id="status-model")
        yield Static("·", classes="shortcut-hint")
        yield Static("Enter", classes="shortcut-key")
        yield Static("Envoyer", classes="shortcut-hint")
        yield Static("·", classes="shortcut-hint")
        yield Static("↑↓", classes="shortcut-key")
        yield Static("Historique", classes="shortcut-hint")
        yield Static("·", classes="shortcut-hint")
        yield Static("Ctrl+K", classes="shortcut-key")
        yield Static("Commandes", classes="shortcut-hint")
        yield Static("·", classes="shortcut-hint")
        yield Static("Ctrl+L", classes="shortcut-key")
        yield Static("Clear", classes="shortcut-hint")

    def watch_is_thinking(self, thinking: bool) -> None:
        dot = self.query_one("#status-dot", Static)
        if thinking:
            dot.add_class("active")
        else:
            dot.remove_class("active")

    def watch_model(self, model: str) -> None:
        try:
            model_el = self.query_one("#status-model", Static)
            model_el.update(model)
        except Exception:
            pass

    def update_status(self, thinking: bool, model: str) -> None:
        self.is_thinking = thinking
        self.model = model
