"""HeaderBar — OpenCode-style single-line header with APEX branding."""

from textual.widgets import Static
from textual.widget import Widget
from textual.reactive import reactive


class HeaderBar(Widget):
    """Compact single-line header: logo + session + model + cwd + tokens + cost + mode."""

    model_name = reactive("or-gpt4o-mini")
    session_name = reactive("main")
    cwd_path = reactive(".")
    token_count = reactive(0)
    cost_usd = reactive(0.0)
    current_mode = reactive("agent")

    def compose(self):
        yield Static("◆", id="header-logo")
        yield Static(" APEX", id="header-logo-text")
        yield Static("▸", id="header-session")
        yield Static(self.session_name, id="header-session-name")
        yield Static("│", id="header-sep")
        yield Static("●", id="header-model-dot")
        yield Static(self.model_name, id="header-model-name")
        yield Static("│", id="header-sep-model")
        yield Static("📁", id="header-cwd-icon")
        yield Static(self._short_cwd(), id="header-cwd-path")
        yield Static("│", id="header-sep-cwd")
        yield Static(self._format_tokens(), id="header-tokens")
        yield Static("│", id="header-sep-tokens")
        yield Static(self._format_cost(), id="header-cost")
        yield Static("│", id="header-sep-cost")
        yield Static(self._format_mode(), id="header-mode")

    def on_mount(self) -> None:
        self._update_all()

    # ── Reactive Watchers ──────────────────────────────────────────────────

    def watch_model_name(self, model_name: str) -> None:
        self._update_model()

    def watch_session_name(self, session_name: str) -> None:
        self._update_session()

    def watch_cwd_path(self, cwd_path: str) -> None:
        self._update_cwd()

    def watch_token_count(self, count: int) -> None:
        self._update_tokens()

    def watch_cost_usd(self, cost: float) -> None:
        self._update_cost()

    def watch_current_mode(self, mode: str) -> None:
        self._update_mode()

    # ── Update Methods ─────────────────────────────────────────────────────

    def _update_all(self) -> None:
        self._update_model()
        self._update_session()
        self._update_cwd()
        self._update_tokens()
        self._update_cost()
        self._update_mode()

    def _update_model(self) -> None:
        try:
            el = self.query_one("#header-model-name", Static)
            el.update(self.model_name)
        except Exception:
            pass

    def _update_session(self) -> None:
        try:
            el = self.query_one("#header-session-name", Static)
            el.update(self.session_name)
        except Exception:
            pass

    def _update_cwd(self) -> None:
        try:
            el = self.query_one("#header-cwd-path", Static)
            el.update(self._short_cwd())
        except Exception:
            pass

    def _update_tokens(self) -> None:
        try:
            el = self.query_one("#header-tokens", Static)
            el.update(self._format_tokens())
            el.remove_class("warn", "danger")
            if self.token_count > 100:
                el.add_class("warn")
            if self.token_count > 200:
                el.remove_class("warn")
                el.add_class("danger")
        except Exception:
            pass

    def _update_cost(self) -> None:
        try:
            el = self.query_one("#header-cost", Static)
            el.update(self._format_cost())
        except Exception:
            pass

    def _update_mode(self) -> None:
        try:
            el = self.query_one("#header-mode", Static)
            el.update(self._format_mode())
        except Exception:
            pass

    # ── Format Helpers ─────────────────────────────────────────────────────

    def _short_cwd(self) -> str:
        path = self.cwd_path
        home = "~"
        if path.startswith("/home/") or path.startswith("/Users/"):
            parts = path.split("/")
            if len(parts) >= 3:
                return f"~/{'/'.join(parts[3:])}" if len(parts) > 3 else "~"
        if len(path) > 25:
            return f"...{path[-22:]}"
        return path

    def _format_tokens(self) -> str:
        if self.token_count >= 1000:
            return f"●{self.token_count // 1000}k"
        return f"●{self.token_count}"

    def _format_cost(self) -> str:
        return f"${self.cost_usd:.4f}"

    def _format_mode(self) -> str:
        mode_labels = {"plan": "◇ Plan", "agent": "◆ Agent", "yolo": "⚡ Yolo"}
        return mode_labels.get(self.current_mode, "◆ Agent")

    # ── Public API ─────────────────────────────────────────────────────────

    def update_tokens(self, count: int, cost: float) -> None:
        self.token_count = count
        self.cost_usd = cost

    def update_model(self, model: str) -> None:
        self.model_name = model

    def update_session(self, session: str) -> None:
        self.session_name = session

    def update_cwd(self, cwd: str) -> None:
        self.cwd_path = cwd

    def update_mode(self, mode: str) -> None:
        self.current_mode = mode
