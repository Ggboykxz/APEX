"""HeaderBar widget - Model selector, cwd, tokens, cost."""

from textual.widgets import Select, Button, Static
from textual.widget import Widget
from textual.reactive import reactive

from ..config import MODELS
from .messages import ModelChanged


class HeaderBar(Widget):
    model_alias = reactive("or-gpt4o-mini")
    cwd = reactive(".")
    token_count = reactive(0)
    cost_usd = reactive(0.0)

    def compose(self):
        yield Static("◆ APEX", id="logo")
        yield Select(
            [(alias, alias) for alias in MODELS.keys()],
            value=self.model_alias,
            id="model-select",
        )
        yield Static(f"📁 {self.cwd}", id="cwd-label")
        yield Static(id="token-label")
        yield Static(id="cost-label")
        yield Button("?", id="btn-help", variant="default")
        yield Button("⚙", id="btn-settings", variant="default")
        yield Button("✕", id="btn-quit", variant="error")

    def on_mount(self) -> None:
        self._update_labels()

    def watch_model_alias(self, model_alias: str) -> None:
        self._update_labels()

    def watch_cwd(self, cwd: str) -> None:
        try:
            cwd_label = self.query_one("#cwd-label", Static)
            cwd_label.update(f"📁 {cwd}")
        except Exception:
            pass

    def watch_token_count(self, count: int) -> None:
        self._update_labels()

    def watch_cost_usd(self, cost: float) -> None:
        self._update_labels()

    def _update_labels(self) -> None:
        try:
            token_label = self.query_one("#token-label", Static)
            token_label.update(f"●{self.token_count}k")
            if self.token_count > 1000:
                token_label.add_class("warn")
            if self.token_count > 2000:
                token_label.remove_class("warn")
                token_label.add_class("danger")
        except Exception:
            pass
        try:
            cost_label = self.query_one("#cost-label", Static)
            cost_label.update(f"${self.cost_usd:.4f}")
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "model-select":
            self.model_alias = event.value
            self.post_message(ModelChanged(event.value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-quit":
            self.app.exit()
        elif event.button.id == "btn-help":
            pass

    def update_tokens(self, count: int, cost: float) -> None:
        self.token_count = count
        self.cost_usd = cost
