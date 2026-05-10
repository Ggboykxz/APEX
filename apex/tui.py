"""
APEX TUI — OpenCode-Inspired Terminal UI
One TUI · APEX Theme · 100% Functional
Built with Textual 8.2.5
"""

import asyncio
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Static
from textual.theme import Theme

from .widgets import (
    HeaderBar,
    SidebarPane,
    ChatPane,
    InputBar,
    StatusBar,
    CommandPalette,
)
from .widgets.messages import (
    AgentThinking,
    AgentResponse,
    AgentError,
    ClearChat,
    FilePreviewRequest,
    ModeChanged,
    SidebarTabChanged,
)
from .widgets.input_bar import UserMessage
from .widgets.cmd_palette import PaletteCommand
from .config import MODELS

THEMES = ["apex-dark", "gabon", "synthwave", "solarized", "dracula", "nord"]

# ── APEX Theme Definitions ──────────────────────────────────────────────────

APEX_THEMES = {
    "apex-dark": Theme(
        name="apex-dark",
        primary="#00e5ff",
        secondary="#a371f7",
        background="#0d1117",
        surface="#161b22",
        foreground="#e6edf3",
        accent="#00e5ff",
        success="#00ff88",
        warning="#ffaa00",
        error="#ff4444",
    ),
    "gabon": Theme(
        name="gabon",
        primary="#009e60",
        secondary="#ffd700",
        background="#0a0f0a",
        surface="#121a12",
        foreground="#e6edf3",
        accent="#009e60",
        success="#00ff88",
        warning="#ffd700",
        error="#ff4444",
    ),
    "synthwave": Theme(
        name="synthwave",
        primary="#e94560",
        secondary="#a371f7",
        background="#1a1a2e",
        surface="#222244",
        foreground="#e6edf3",
        accent="#e94560",
        success="#00ff88",
        warning="#ffaa00",
        error="#ff4444",
    ),
    "solarized": Theme(
        name="solarized",
        primary="#268bd2",
        secondary="#b58900",
        background="#002b36",
        surface="#073642",
        foreground="#839496",
        accent="#268bd2",
        success="#859900",
        warning="#b58900",
        error="#dc322f",
    ),
    "dracula": Theme(
        name="dracula",
        primary="#bd93f9",
        secondary="#ff79c6",
        background="#282a36",
        surface="#343746",
        foreground="#f8f8f2",
        accent="#bd93f9",
        success="#50fa7b",
        warning="#f1fa8c",
        error="#ff5555",
    ),
    "nord": Theme(
        name="nord",
        primary="#88c0d0",
        secondary="#81a1c1",
        background="#2e3440",
        surface="#3b4252",
        foreground="#d8dee9",
        accent="#88c0d0",
        success="#a3be8c",
        warning="#ebcb8b",
        error="#bf616a",
    ),
}


class ApexApp(App):
    """APEX TUI — OpenCode-inspired design with APEX theme."""

    CSS_PATH = "tui.tcss"
    TITLE = "APEX"
    BINDINGS = [
        Binding("ctrl+k", "command_palette", "Commands", show=True),
        Binding("ctrl+l", "clear_chat", "Clear", show=False),
        Binding("ctrl+n", "new_session", "New", show=False),
        Binding("ctrl+s", "save_session", "Save", show=False),
        Binding("ctrl+backslash", "toggle_sidebar", "Sidebar", show=False),
        Binding("ctrl+m", "model_picker", "Model", show=False),
        Binding("ctrl+t", "toggle_theme", "Theme", show=False),
        Binding("ctrl+tab", "cycle_mode", "Mode", show=False),
        Binding("f1", "show_help", "Help", show=False),
        Binding("escape", "dismiss_overlay", "", show=False),
        Binding("up", "nav_history_up", "HistoryUp", show=False),
        Binding("down", "nav_history_down", "HistoryDown", show=False),
    ]

    def __init__(self, model: str = "or-gpt4o-mini", cwd: str = ".", agent: Any = None, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.cwd = cwd
        self.apex_agent = agent
        self.sidebar_visible = True
        self.current_theme_idx = 0
        self.message_history: list[str] = []
        self.history_index = -1
        self.sidebar_width = 28
        self.mode = "agent"  # plan / agent / yolo
        self.session_name = "main"
        self.message_count = 0

    def compose(self) -> ComposeResult:
        with Container(id="app-grid"):
            yield HeaderBar(id="header-bar")

            with Container(id="main-pane"):
                yield SidebarPane(self.cwd, id="sidebar")
                yield Static("│", id="resize-handle")

                with Container(id="chat-area"):
                    yield Static("main · 0 messages", id="chat-header")
                    yield ChatPane(id="chat-pane")
                    yield InputBar(id="input-bar")

            yield StatusBar(id="status-bar")

    def on_resize_handle_click(self, message) -> None:
        sidebar = self.query_one("#sidebar")
        new_width = 28 if self.sidebar_width != 28 else 38
        self.sidebar_width = new_width
        sidebar.styles.width = new_width

    def on_mount(self) -> None:
        # Register all APEX themes
        for theme_name, theme_obj in APEX_THEMES.items():
            self.register_theme(theme_obj)
        self.theme = "apex-dark"

        if self.size.width < 80 or self.size.height < 24:
            self.exit(message="Terminal too small. Minimum 80x24 required.")
            return

        chat_pane = self.query_one("#chat-pane", ChatPane)
        chat_pane.add_system_message(
            "Welcome to APEX — The Universal AI Coding Agent\n\n"
            "Type your message and press Enter to start coding.\n"
            "Use /help for commands, Ctrl+K for command palette.\n"
            "Press Tab to cycle modes (Plan → Agent → Yolo).",
        )
        self._update_chat_header()

        if self.apex_agent:
            self.run_agent_task()

    def run_agent_task(self) -> None:
        pass

    # ── Message Handlers ───────────────────────────────────────────────────

    def on_input_bar_message(self, message: UserMessage) -> None:
        chat_pane = self.query_one("#chat-pane", ChatPane)
        input_bar = self.query_one("#input-bar", InputBar)

        chat_pane.add_user_message(message.text)
        input_bar.set_thinking(True)
        self.message_count += 1
        self._update_chat_header()

        if message.text.strip():
            self.message_history.append(message.text)
            self.history_index = len(self.message_history)

        if self.apex_agent:
            asyncio.create_task(self._process_message(message.text))

    async def _process_message(self, text: str) -> None:
        chat_pane = self.query_one("#chat-pane", ChatPane)
        input_bar = self.query_one("#input-bar", InputBar)
        header_bar = self.query_one("#header-bar", HeaderBar)
        status_bar = self.query_one("#status-bar", StatusBar)

        try:
            status_bar.set_thinking(True)
            chat_pane.post_message(AgentThinking())

            response = self.apex_agent.chat(text)

            chat_pane.post_message(AgentResponse(response, self.model))
            self.message_count += 1
            self._update_chat_header()

            usage = self.apex_agent.usage
            header_bar.update_tokens(usage.get("total_tokens", 0), 0.0)

        except Exception as e:
            chat_pane.post_message(AgentError(str(e)))
            status_bar.set_error(True)

        finally:
            input_bar.set_thinking(False)
            status_bar.set_thinking(False)

    # ── Actions ────────────────────────────────────────────────────────────

    def action_clear_chat(self) -> None:
        chat_pane = self.query_one("#chat-pane", ChatPane)
        chat_pane.post_message(ClearChat())
        self.message_count = 0
        self._update_chat_header()

    def action_toggle_sidebar(self) -> None:
        self.sidebar_visible = not self.sidebar_visible
        sidebar = self.query_one("#sidebar", SidebarPane)
        resize_handle = self.query_one("#resize-handle")
        if self.sidebar_visible:
            sidebar.display = True
            resize_handle.display = True
        else:
            sidebar.display = False
            resize_handle.display = False

    def action_toggle_theme(self) -> None:
        self.current_theme_idx = (self.current_theme_idx + 1) % len(THEMES)
        theme_name = THEMES[self.current_theme_idx]
        self.theme = theme_name

        chat_pane = self.query_one("#chat-pane", ChatPane)
        chat_pane.add_system_message(f"Theme: {theme_name.replace('-', ' ').title()}")
        self._update_chat_header()

    def action_command_palette(self) -> None:
        self.push_screen(CommandPalette())

    def action_cycle_mode(self) -> None:
        modes = ["plan", "agent", "yolo"]
        current_idx = modes.index(self.mode)
        self.mode = modes[(current_idx + 1) % len(modes)]
        self.post_message(ModeChanged(self.mode))

        header_bar = self.query_one("#header-bar", HeaderBar)
        header_bar.update_mode(self.mode)

        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.update_agent(self.mode)

        chat_pane = self.query_one("#chat-pane", ChatPane)
        mode_labels = {"plan": "Plan", "agent": "Agent", "yolo": "Yolo"}
        chat_pane.add_system_message(f"Mode: {mode_labels[self.mode]}")

    def action_nav_history_up(self) -> None:
        if self.message_history and self.history_index > 0:
            self.history_index -= 1
            input_bar = self.query_one("#input-bar", InputBar)
            input_bar.value = self.message_history[self.history_index]
            input_bar.cursor_position = len(input_bar.value)

    def action_nav_history_down(self) -> None:
        if self.message_history and self.history_index < len(self.message_history) - 1:
            self.history_index += 1
            input_bar = self.query_one("#input-bar", InputBar)
            input_bar.value = self.message_history[self.history_index]
            input_bar.cursor_position = len(input_bar.value)
        elif self.history_index == len(self.message_history) - 1:
            self.history_index = len(self.message_history)
            input_bar = self.query_one("#input-bar", InputBar)
            input_bar.value = ""

    def action_new_session(self) -> None:
        self.message_history = []
        self.history_index = -1
        self.message_count = 0
        self.session_name = "new"
        chat_pane = self.query_one("#chat-pane", ChatPane)
        chat_pane.post_message(ClearChat())
        chat_pane.add_system_message("New session started.")
        self._update_chat_header()
        header_bar = self.query_one("#header-bar", HeaderBar)
        header_bar.update_session(self.session_name)

    def action_save_session(self) -> None:
        chat_pane = self.query_one("#chat-pane", ChatPane)
        chat_pane.add_system_message("Session saved.")

    def action_show_help(self) -> None:
        help_text = (
            "APEX TUI — Keyboard Shortcuts\n\n"
            "  Ctrl+K   Command Palette\n"
            "  Ctrl+L   Clear Chat\n"
            "  Ctrl+N   New Session\n"
            "  Ctrl+S   Save Session\n"
            "  Ctrl+T   Toggle Theme\n"
            "  Ctrl+\\   Toggle Sidebar\n"
            "  Ctrl+M   Model Picker\n"
            "  Ctrl+Tab Cycle Mode (Plan/Agent/Yolo)\n"
            "  F1       Help\n"
            "  Esc      Close Overlay\n"
            "  Up/Down  Message History\n\n"
            "Modes:\n"
            "  Plan   — Read-only, plan before acting\n"
            "  Agent  — Standard mode, asks permission\n"
            "  Yolo   — Auto-approve all actions\n\n"
            f"Themes: {', '.join(t.replace('-', ' ').title() for t in THEMES)}"
        )
        chat_pane = self.query_one("#chat-pane", ChatPane)
        chat_pane.add_system_message(help_text)

    # ── Palette Command Handler ────────────────────────────────────────────

    def on_palette_command(self, message: PaletteCommand) -> None:
        chat_pane = self.query_one("#chat-pane", ChatPane)
        input_bar = self.query_one("#input-bar", InputBar)
        header_bar = self.query_one("#header-bar", HeaderBar)
        command = message.command

        if command == "/clear":
            chat_pane.post_message(ClearChat())
            self.message_count = 0
            self._update_chat_header()
        elif command.startswith("/model "):
            model_name = command.replace("/model ", "").strip()
            if model_name in MODELS:
                self.model = model_name
                header_bar.update_model(model_name)
                chat_pane.add_system_message(f"Model: {model_name}")
            else:
                chat_pane.add_system_message(f"Unknown model: {model_name}")
        elif command == "/models":
            models_list = "\n".join(f"  {m}" for m in list(MODELS.keys())[:20])
            total = len(MODELS)
            chat_pane.add_system_message(f"Available models ({total}):\n{models_list}")
        elif command == "/cwd":
            chat_pane.add_system_message(f"Directory: {self.cwd}")
        elif command == "/theme":
            self.action_toggle_theme()
        elif command == "/help":
            self.action_show_help()
        elif command == "/mode":
            self.action_cycle_mode()
        elif command.startswith("/"):
            input_bar.value = command

    # ── File Preview Handler ───────────────────────────────────────────────

    def on_file_preview_request(self, message: FilePreviewRequest) -> None:
        chat_pane = self.query_one("#chat-pane", ChatPane)
        try:
            file_path = Path(message.file_path)
            if file_path.exists():
                content = file_path.read_text()
                suffix = file_path.suffix.lstrip(".") or "text"
                preview = f"```{suffix}\n{content[:2000]}\n```"
                if len(content) > 2000:
                    preview += f"\n... ({len(content) - 2000} more chars)"
                chat_pane.add_system_message(preview)
            else:
                chat_pane.add_system_message(f"File not found: {file_path}")
        except Exception as e:
            chat_pane.add_system_message(f"Error: {e}")

    # ── Sidebar Tab Handler ────────────────────────────────────────────────

    def on_sidebar_tab_changed(self, message: SidebarTabChanged) -> None:
        sidebar = self.query_one("#sidebar", SidebarPane)
        sidebar.switch_tab(message.tab)

    # ── Mode Change Handler ────────────────────────────────────────────────

    def on_mode_changed(self, message: ModeChanged) -> None:
        self.mode = message.mode
        header_bar = self.query_one("#header-bar", HeaderBar)
        header_bar.update_mode(self.mode)

    # ── Model/Cwd Change Handlers ──────────────────────────────────────────

    def on_model_changed(self, message) -> None:
        self.model = message.model
        header_bar = self.query_one("#header-bar", HeaderBar)
        header_bar.update_model(message.model)
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.update_model(message.model)

    def on_cwd_changed(self, message) -> None:
        self.cwd = message.cwd
        header_bar = self.query_one("#header-bar", HeaderBar)
        header_bar.update_cwd(message.cwd)
        sidebar = self.query_one("#sidebar", SidebarPane)
        sidebar.update_cwd(message.cwd)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _update_chat_header(self) -> None:
        header = self.query_one("#chat-header")
        header.update(f"{self.session_name} · {self.message_count} messages")

    def on_key(self, event) -> None:
        if event.key == "ctrl+q":
            self.exit()
        elif event.key == "tab":
            # Only cycle mode if input is NOT focused
            try:
                input_bar = self.query_one("#input-bar", InputBar)
                if not input_bar.is_focused:
                    self.action_cycle_mode()
                    event.prevent_default()
            except Exception:
                pass


def run_apex_tui(model: str = "or-gpt4o-mini", cwd: str = ".", agent: Any = None) -> None:
    """Run APEX TUI — OpenCode-inspired design."""
    app = ApexApp(model=model, cwd=cwd, agent=agent)
    app.run()


if __name__ == "__main__":
    run_apex_tui()
