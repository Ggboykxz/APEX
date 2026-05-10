"""StatusBar — OpenCode-style compact status bar.

Refonte: Enhanced with:
- Status dot with color states (ready/thinking/error)
- Context window info (token count + cost)
- LSP diagnostic count
- Keyboard shortcut hints
- Current model name (right-aligned)
- Agent mode indicator (right-aligned)
- Status notifications with TTL
"""

from textual.widgets import Static
from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message


class StatusBar(Widget):
    """Compact single-line status bar matching OpenCode's design.

    Layout: ● Ready | Enter Send | ↑↓ History | Ctrl+K Commands | ... | agent | model
    """

    is_thinking = reactive(False)
    is_error = reactive(False)
    model = reactive("or-gpt4o-mini")
    agent_mode = reactive("agent")
    token_count = reactive(0)
    cost_usd = reactive(0.0)
    lsp_errors = reactive(0)
    lsp_warnings = reactive(0)
    status_msg = reactive("")
    status_ttl = reactive(0.0)

    def compose(self):
        # Left side: status + shortcuts
        yield Static("●", id="status-dot")
        yield Static(" Ready ", classes="status-label")
        yield Static("│", classes="status-sep")

        # Keyboard shortcuts (shown when not thinking)
        yield Static("Enter", classes="status-key")
        yield Static(" Send ", classes="status-desc")
        yield Static("│", classes="status-sep")
        yield Static("Ctrl+K", classes="status-key")
        yield Static(" Commands ", classes="status-desc")
        yield Static("│", classes="status-sep")
        yield Static("Ctrl+H", classes="status-key")
        yield Static(" Help ", classes="status-desc")
        yield Static("│", classes="status-sep")

        # LSP diagnostics
        yield Static("", id="status-lsp")

        # Context info
        yield Static("", id="status-context")

        # Right side: mode + model
        yield Static(self.agent_mode, id="status-agent")
        yield Static(f" ● {self.model}", id="status-model")

    def on_mount(self) -> None:
        self._update_status_dot()
        self._update_context()
        self._update_lsp()

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
            mode_labels = {"plan": "◇ Plan", "agent": "◆ Agent", "yolo": "⚡ Yolo"}
            agent_el.update(mode_labels.get(mode, mode))
        except Exception:
            pass

    def watch_token_count(self, count: int) -> None:
        self._update_context()

    def watch_cost_usd(self, cost: float) -> None:
        self._update_context()

    def watch_lsp_errors(self, count: int) -> None:
        self._update_lsp()

    def watch_lsp_warnings(self, count: int) -> None:
        self._update_lsp()

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

    def _update_context(self) -> None:
        try:
            ctx_el = self.query_one("#status-context", Static)
            if self.token_count > 0:
                cost_str = f"${self.cost_usd:.4f}" if self.cost_usd < 1 else f"${self.cost_usd:.2f}"
                ctx_el.update(f"│ {self._format_tokens()} · {cost_str} ")
            else:
                ctx_el.update("")
        except Exception:
            pass

    def _update_lsp(self) -> None:
        try:
            lsp_el = self.query_one("#status-lsp", Static)
            if self.lsp_errors > 0 or self.lsp_warnings > 0:
                parts = []
                if self.lsp_errors > 0:
                    parts.append(f"[red]⚠ {self.lsp_errors}[/]")
                if self.lsp_warnings > 0:
                    parts.append(f"[yellow]⚠ {self.lsp_warnings}[/]")
                lsp_el.update(" " + " ".join(parts) + " ")
            else:
                lsp_el.update("")
        except Exception:
            pass

    def _format_tokens(self) -> str:
        if self.token_count >= 1000:
            return f"●{self.token_count / 1000:.1f}k"
        return f"●{self.token_count}"

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

    def update_tokens(self, count: int, cost: float) -> None:
        self.token_count = count
        self.cost_usd = cost

    def update_lsp(self, errors: int, warnings: int) -> None:
        self.lsp_errors = errors
        self.lsp_warnings = warnings

    def show_status(self, msg: str, ttl: float = 3.0) -> None:
        """Show a temporary status message."""
        try:
            label = self.query_one(".status-label", Static)
            label.update(f" {msg} ")
            if ttl > 0:
                self.set_timer(ttl, self._clear_status)
        except Exception:
            pass

    def _clear_status(self) -> None:
        self._update_status_dot()
