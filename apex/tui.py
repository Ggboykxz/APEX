"""
APEX TUI - The Best Terminal UI Ever Built
Better than OpenCode · Better than Claude Code
Built with Textual 8.2.5
"""

import asyncio
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Static

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
)
from .widgets.input_bar import UserMessage
from .widgets.cmd_palette import PaletteCommand
from .config import MODELS

THEMES = ["apex-dark", "gabon", "synthwave", "solarized"]


class ApexApp(App):
    CSS_PATH = "tui.tcss"
    TITLE = "APEX"
    BINDINGS = [
        Binding("ctrl+k", "command_palette", "Commands", show=True),
        Binding("ctrl+l", "clear_chat", "Clear", show=True),
        Binding("ctrl+n", "new_session", "New", show=True),
        Binding("ctrl+s", "save_session", "Save", show=True),
        Binding("ctrl+slash", "toggle_sidebar", "Sidebar", show=False),
        Binding("ctrl+m", "model_picker", "Model", show=False),
        Binding("ctrl+t", "toggle_theme", "Theme", show=False),
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
        self.message_history = []
        self.history_index = -1
        self.sidebar_width = 26

    def compose(self) -> ComposeResult:
        with Container(id="app-grid"):
            yield HeaderBar(id="header-bar")

            with Container(id="main-pane"):
                yield SidebarPane(self.cwd, id="sidebar")

                yield Static("│", id="resize-handle")

                with Container(id="chat-area"):
                    yield Static("Session: main · 0 messages", id="chat-header")
                    yield ChatPane(id="chat-pane")
                    yield InputBar(id="input-bar")

            yield StatusBar(id="status-bar")

    def on_resize_handle_click(self, message) -> None:
        sidebar = self.query_one("#sidebar")

        new_width = 26 if self.sidebar_width != 26 else 35
        self.sidebar_width = new_width
        sidebar.styles.width = new_width

    def on_mount(self) -> None:
        if self.size.width < 80 or self.size.height < 24:
            self.exit(message="Terminal too small. Minimum 80×24 required.")
            return

        chat_pane = self.query_one("#chat-pane", ChatPane)
        chat_pane.add_ai_message(
            "Welcome to APEX!\n\nType your message and press Enter to start coding.\nUse /help for commands, Ctrl+K for command palette.",
            self.model,
        )

        if self.apex_agent:
            self.run_agent_task()

    def run_agent_task(self) -> None:
        pass

    def on_input_bar_message(self, message: UserMessage) -> None:
        chat_pane = self.query_one("#chat-pane", ChatPane)
        input_bar = self.query_one("#input-bar", InputBar)

        chat_pane.add_user_message(message.text)
        input_bar.set_thinking(True)

        if message.text.strip():
            self.message_history.append(message.text)
            self.history_index = len(self.message_history)

        if self.apex_agent:
            asyncio.create_task(self._process_message(message.text))

    async def _process_message(self, text: str) -> None:
        chat_pane = self.query_one("#chat-pane", ChatPane)
        input_bar = self.query_one("#input-bar", InputBar)
        header_bar = self.query_one("#header-bar", HeaderBar)

        try:
            chat_pane.post_message(AgentThinking())

            response = self.apex_agent.chat(text)

            chat_pane.post_message(AgentResponse(response, self.model))

            usage = self.apex_agent.usage
            header_bar.update_tokens(usage.get("total_tokens", 0), 0.0)

        except Exception as e:
            chat_pane.post_message(AgentError(str(e)))

        finally:
            input_bar.set_thinking(False)

    def action_clear_chat(self) -> None:
        chat_pane = self.query_one("#chat-pane", ChatPane)
        chat_pane.post_message(ClearChat())

    def action_toggle_sidebar(self) -> None:
        self.sidebar_visible = not self.sidebar_visible
        sidebar = self.query_one("#sidebar", SidebarPane)
        sidebar.display = "flex" if self.sidebar_visible else "none"

    def action_toggle_theme(self) -> None:
        self.current_theme_idx = (self.current_theme_idx + 1) % len(THEMES)
        theme_name = THEMES[self.current_theme_idx]
        self.theme = theme_name

        header_bar = self.query_one("#header-bar", HeaderBar)
        header_bar.add_class(f"theme-{theme_name}")

        chat_pane = self.query_one("#chat-pane", ChatPane)
        chat_pane.add_class(f"theme-{theme_name}")

        chat_pane.add_ai_message(f"Theme switched to: {theme_name.replace('-', ' ').title()}", self.model)

    def action_command_palette(self) -> None:
        self.push_screen(CommandPalette())

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
        chat_pane = self.query_one("#chat-pane", ChatPane)
        chat_pane.post_message(ClearChat())
        chat_pane.add_ai_message("New session started. History cleared.", self.model)

    def action_save_session(self) -> None:
        chat_pane = self.query_one("#chat-pane", ChatPane)
        chat_pane.add_ai_message("Session saved (placeholder)", self.model)

    def action_show_help(self) -> None:
        help_text = """APEX TUI SHORTCUTS:

• **Ctrl+K** - Command Palette
• **Ctrl+L** - Clear Chat  
• **Ctrl+N** - New Session
• **Ctrl+S** - Save Session
• **Ctrl+T** - Toggle Theme (APEX Dark / Gabon / Synthwave / Solarized)
• **Ctrl+\\** - Toggle Sidebar
• **Ctrl+M** - Model Picker
• **↑ / ↓** - Navigate Message History
• **F1** - Show Help
• **Esc** - Close Modal

THEMES:
• APEX Dark (default) - GitHub-inspired dark
• GABON - 🇬🇦 Green/Yellow/Blue flag colors
• SYNTHWAVE - Purple/Pink neon
• SOLARIZED - Warm earth tones"""
        chat_pane = self.query_one("#chat-pane", ChatPane)
        chat_pane.add_ai_message(help_text, self.model)

    def on_palette_command(self, message: PaletteCommand) -> None:
        chat_pane = self.query_one("#chat-pane", ChatPane)
        input_bar = self.query_one("#input-bar", InputBar)
        header_bar = self.query_one("#header-bar", HeaderBar)
        command = message.command

        if command == "/clear":
            chat_pane.post_message(ClearChat())
        elif command.startswith("/model "):
            model_name = command.replace("/model ", "").strip()
            if model_name in MODELS:
                self.model = model_name
                header_bar.model_alias = model_name
                chat_pane.add_ai_message(f"Model switched to: {model_name}", self.model)
            else:
                chat_pane.add_ai_message(f"Unknown model: {model_name}. Available: {', '.join(MODELS.keys())}", self.model)
        elif command == "/models":
            models_list = "\n".join([f"• {m}" for m in MODELS.keys()])
            chat_pane.add_ai_message(f"Available models:\n{models_list}", self.model)
        elif command == "/cwd":
            chat_pane.add_ai_message(f"Current directory: {self.cwd}", self.model)
        elif command == "/theme":
            self.action_toggle_theme()
        elif command == "/help":
            self.action_show_help()
        elif command.startswith("/"):
            input_bar.value = command

    def on_file_preview_request(self, message: FilePreviewRequest) -> None:
        chat_pane = self.query_one("#chat-pane", ChatPane)
        try:
            file_path = Path(message.file_path)
            if file_path.exists():
                content = file_path.read_text()
                preview = f"📄 `{file_path.name}`\n\n```\n{content[:2000]}\n```"
                if len(content) > 2000:
                    preview += f"\n... ({len(content) - 2000} more characters)"
                chat_pane.add_ai_message(preview, self.model)
            else:
                chat_pane.add_ai_message(f"File not found: {file_path}", self.model)
        except Exception as e:
            chat_pane.add_ai_message(f"Error reading file: {e}", self.model)

    def onToggleSidebar(self) -> None:
        self.action_toggle_sidebar()

    def onModelChanged(self, message) -> None:
        self.model = message.model
        header_bar = self.query_one("#header-bar", HeaderBar)
        header_bar.model_alias = message.model
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.update_status(status_bar.is_thinking, message.model)

    def onCwdChanged(self, message) -> None:
        self.cwd = message.cwd
        header_bar = self.query_one("#header-bar", HeaderBar)
        header_bar.cwd = message.cwd
        sidebar = self.query_one("#sidebar", SidebarPane)
        sidebar.update_cwd(message.cwd)

    def on_key(self, event) -> None:
        if event.key == "ctrl+q":
            self.exit()


def run_apex_tui(model: str = "or-gpt4o-mini", cwd: str = ".", agent: Any = None) -> None:
    """Run APEX TUI."""
    app = ApexApp(model=model, cwd=cwd, agent=agent)
    app.run()


if __name__ == "__main__":
    run_apex_tui()
