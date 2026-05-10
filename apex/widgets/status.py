"""StatusBar — OpenCode-style compact status bar."""

from textual.widgets import Static
from textual.widget import Widget
from textual.reactive import reactive


class StatusBar(Widget):
    """Compact single-line status bar: status dot + shortcuts + model + agent mode."""

    is_thinking = reactive(False)
    is_error = reactive(False)
    model = reactive("or-gpt4o-mini")
    agent_mode = reactive("agent")

    def compose(self):
        yield Static("●", id="status-dot")
        yield Static(" Ready ", classes="status-label")
        yield Static("│", classes="status-sep")
        yield Static("Enter", classes="status-key")
        yield Static(" Send ", classes="status-desc")
        yield Static("│", classes="status-sep")
        yield Static("↑↓", classes="status-key")
        yield Static(" History ", classes="status-desc")
        yield Static("│", classes="status-sep")
        yield Static("Ctrl+K", classes="status-key")
        yield Static(" Commands ", classes="status-desc")
        yield Static("│", classes="status-sep")
        yield Static("Ctrl+\\", classes="status-key")
        yield Static(" Sidebar ", classes="status-desc")
        yield Static("│", classes="status-sep")
        yield Static("Ctrl+T", classes="status-key")
        yield Static(" Theme ", classes="status-desc")
        yield Static(self.agent_mode, id="status-agent")
        yield Static(f" ● {self.model}", id="status-model")

    def on_mount(self) -> None:
        self._update_status_dot()

    def watch_is_thinking(self, thinking: bool) -> None:
        self._update_status_dot()

    def watch_is_error(self, error: bool) -> None:
        self._update_status_dot()

    def watch_model(self, model: str) -> None:
        try:
            model_el = self.query_one("#status-model", Static)
            model_el.update(f" ● {model}")
        except Exception:
            pass

    def watch_agent_mode(self, mode: str) -> None:
        try:
            agent_el = self.query_one("#status-agent", Static)
            agent_el.update(mode)
        except Exception:
            pass

    def _update_status_dot(self) -> None:
        try:
            dot = self.query_one("#status-dot", Static)
            label = self.query_one(".status-label", Static)
            dot.remove_class("active", "thinking", "error")

            if self.is_error:
                dot.add_class("error")
                label.update(" Error ")
            elif self.is_thinking:
                dot.add_class("thinking")
                label.update(" Thinking... ")
            else:
                dot.add_class("active")
                label.update(" Ready ")
        except Exception:
            pass

    def set_thinking(self, thinking: bool) -> None:
        self.is_thinking = thinking
        if thinking:
            self.is_error = False

    def set_error(self, error: bool) -> None:
        self.is_error = error

    def update_status(self, thinking: bool, model: str) -> None:
        self.is_thinking = thinking
        self.model = model

    def update_model(self, model: str) -> None:
        self.model = model

    def update_agent(self, mode: str) -> None:
        self.agent_mode = mode
