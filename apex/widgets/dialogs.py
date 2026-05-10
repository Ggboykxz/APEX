"""APEX TUI Overlay Dialogs — OpenCode-style modal dialogs.

Refonte: All 10 dialog types from OpenCode, adapted for Textual ModalScreen.
- HelpDialog: Full keyboard shortcut reference
- QuitDialog: Confirm before exiting
- ModelPickerDialog: Browse and select models by provider
- ThemePickerDialog: Visual theme preview and selection
- SessionPickerDialog: Session list with search
- PermissionDialog: Tool permission request (Allow/Session/Deny)
- FilePickerDialog: File browser overlay
- InitDialog: First-run setup
- CompletionDialog: @-mention file/folder completions
"""

from textual.screen import ModalScreen
from textual.widgets import Input, Static, Button, DirectoryTree
from textual.widget import Widget
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.message import Message
from textual.binding import Binding
from textual.reactive import reactive
from pathlib import Path
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# HELP DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class HelpDialog(ModalScreen):
    """Full keyboard shortcut reference overlay (OpenCode-style)."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
    ]

    def compose(self):
        with Container(id="dialog-overlay"):
            with Container(id="help-dialog", classes="dialog-window"):
                yield Static(" ◆  APEX — Keyboard Shortcuts", id="help-title")
                with VerticalScroll(id="help-content"):
                    yield Static(self._render_help())
                yield Static(" ESC to close ", id="help-footer", classes="dialog-footer")

    def _render_help(self) -> str:
        return (
            "[bold cyan]General[/]\n"
            "  [bold]Ctrl+C[/]      Quit APEX\n"
            "  [bold]Ctrl+H[/]      Show this help\n"
            "  [bold]Ctrl+T[/]      Theme picker\n"
            "  [bold]Ctrl+L[/]      View logs\n"
            "  [bold]F1[/]           Help\n\n"

            "[bold cyan]Session[/]\n"
            "  [bold]Ctrl+S[/]      Switch session\n"
            "  [bold]Ctrl+N[/]      New session\n\n"

            "[bold cyan]Chat[/]\n"
            "  [bold]Ctrl+K[/]      Command palette\n"
            "  [bold]Ctrl+O[/]      Model picker\n"
            "  [bold]Ctrl+F[/]      File picker (attach)\n"
            "  [bold]Ctrl+\\[/]      Toggle sidebar\n"
            "  [bold]Ctrl+Tab[/]    Cycle mode\n"
            "  [bold]Enter[/]        Send message\n"
            "  [bold]Shift+Enter[/]  New line\n"
            "  [bold]Ctrl+E[/]       Open in $EDITOR\n"
            "  [bold]Esc[/]          Cancel generation\n\n"

            "[bold cyan]Navigation[/]\n"
            "  [bold]PgUp/b[/]      Page up\n"
            "  [bold]PgDn/f[/]      Page down\n"
            "  [bold]Ctrl+U[/]      Half page up\n"
            "  [bold]Ctrl+D[/]      Half page down\n"
            "  [bold]Up/Down[/]      Message history\n\n"

            "[bold cyan]Modes[/]\n"
            "  [bold]◆ Agent[/]     Standard mode, asks permission\n"
            "  [bold]◇ Plan[/]      Read-only, plan before acting\n"
            "  [bold]⚡ Yolo[/]     Auto-approve all actions\n"
        )

    def action_close(self) -> None:
        self.app.pop_screen()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.action_close()


# ══════════════════════════════════════════════════════════════════════════════
# QUIT DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class QuitDialog(ModalScreen):
    """Confirm quit dialog (OpenCode-style)."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
    ]

    def compose(self):
        with Container(id="dialog-overlay"):
            with Container(id="quit-dialog", classes="dialog-window dialog-small"):
                yield Static(" Quit APEX?", id="quit-title")
                yield Static("Are you sure you want to quit?", id="quit-message")
                with Horizontal(id="quit-buttons"):
                    yield Button("Yes", id="quit-yes", variant="error")
                    yield Button("No", id="quit-no", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit-yes":
            self.app.exit()
        else:
            self.app.pop_screen()

    def action_close(self) -> None:
        self.app.pop_screen()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.action_close()
        elif event.key == "y":
            self.app.exit()
        elif event.key == "n":
            self.app.pop_screen()


# ══════════════════════════════════════════════════════════════════════════════
# MODEL PICKER DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class ModelPickerDialog(ModalScreen):
    """Model selection overlay with provider tabs (OpenCode-style).

    Groups models by provider, supports search filtering.
    Navigate with arrow keys, switch providers with left/right.
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
        Binding("left", "prev_provider", "Prev provider", show=False),
        Binding("right", "next_provider", "Next provider", show=False),
        Binding("up", "prev_model", "Prev model", show=False),
        Binding("down", "next_model", "Next model", show=False),
        Binding("enter", "select_model", "Select", show=False),
    ]

    PROVIDERS = [
        ("Anthropic", ["claude-4-sonnet", "claude-3.7-sonnet", "claude-3.5-haiku", "claude-opus-4"]),
        ("OpenAI", ["gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o", "o3", "o4-mini"]),
        ("Google", ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]),
        ("xAI", ["grok-3", "grok-3-mini", "grok-2"]),
        ("DeepSeek", ["deepseek-v3", "deepseek-r1", "deepseek-chat"]),
        ("Meta", ["llama-4-maverick", "llama-4-scout", "llama-3.3-70b"]),
        ("Mistral", ["mistral-large", "mistral-medium", "codestral"]),
        ("Qwen", ["qwen3-235b", "qwen3-30b", "qwen3-coder"]),
        ("Ollama", ["llama3.1", "codellama", "mistral", "phi3"]),
    ]

    def __init__(self, current_model: str = "or-gpt4o-mini", **kwargs):
        super().__init__(**kwargs)
        self.current_model = current_model
        self.provider_index = 0
        self.model_index = 0
        self.search_query = ""

    def compose(self):
        with Container(id="dialog-overlay"):
            with Container(id="model-dialog", classes="dialog-window dialog-large"):
                yield Static(" ◆  Model Picker                    [ESC]", id="model-title")
                yield Input(placeholder="  Search models...", id="model-search")
                with Horizontal(id="model-provider-tabs"):
                    for i, (name, _) in enumerate(self.PROVIDERS):
                        tab_class = "provider-tab active" if i == 0 else "provider-tab"
                        yield Static(f" {name} ", classes=tab_class, id=f"prov-tab-{i}")
                yield Static(id="model-list")

    def on_mount(self) -> None:
        self._refresh_models()
        search = self.query_one("#model-search", Input)
        search.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.search_query = event.value.lower().strip()
        self.model_index = 0
        self._refresh_models()

    def action_prev_provider(self) -> None:
        self.provider_index = (self.provider_index - 1) % len(self.PROVIDERS)
        self.model_index = 0
        self._update_provider_tabs()
        self._refresh_models()

    def action_next_provider(self) -> None:
        self.provider_index = (self.provider_index + 1) % len(self.PROVIDERS)
        self.model_index = 0
        self._update_provider_tabs()
        self._refresh_models()

    def action_prev_model(self) -> None:
        models = self._get_filtered_models()
        if models:
            self.model_index = (self.model_index - 1) % len(models)
            self._refresh_models()

    def action_next_model(self) -> None:
        models = self._get_filtered_models()
        if models:
            self.model_index = (self.model_index + 1) % len(models)
            self._refresh_models()

    def action_select_model(self) -> None:
        models = self._get_filtered_models()
        if models and 0 <= self.model_index < len(models):
            provider_name = self.PROVIDERS[self.provider_index][0]
            self.post_message(self._make_model_selected(models[self.model_index], provider_name))
            self.app.pop_screen()

    def action_close(self) -> None:
        self.app.pop_screen()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.action_close()

    def _get_filtered_models(self) -> list[str]:
        provider_name, models = self.PROVIDERS[self.provider_index]
        if self.search_query:
            return [m for m in models if self.search_query in m.lower()]
        return models

    def _update_provider_tabs(self) -> None:
        for i in range(len(self.PROVIDERS)):
            try:
                tab = self.query_one(f"#prov-tab-{i}", Static)
                if i == self.provider_index:
                    tab.add_class("active")
                else:
                    tab.remove_class("active")
            except Exception:
                pass

    def _refresh_models(self) -> None:
        try:
            container = self.query_one("#model-list", Static)
            models = self._get_filtered_models()
            if not models:
                container.update("[dim]No models found[/]")
                return

            lines = []
            for i, model in enumerate(models):
                if i == self.model_index:
                    lines.append(f"  [bold cyan]▸ {model}[/]")
                elif model == self.current_model:
                    lines.append(f"  [green]✓[/] {model}")
                else:
                    lines.append(f"    {model}")

            container.update("\n".join(lines))
        except Exception:
            pass

    def _make_model_selected(self, model: str, provider: str):
        from .messages import ModelSelected
        return ModelSelected(model, provider)


# ══════════════════════════════════════════════════════════════════════════════
# THEME PICKER DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class ThemePickerDialog(ModalScreen):
    """Theme picker with visual preview (OpenCode-style)."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
        Binding("up", "prev_theme", "Prev", show=False),
        Binding("down", "next_theme", "Next", show=False),
        Binding("enter", "select_theme", "Select", show=False),
    ]

    THEMES = [
        ("apex-dark", "#00e5ff", "#0d1117", "#00ff88", "APEX Dark (default)"),
        ("gabon", "#009e60", "#0a0f0a", "#00ff88", "Gabon 🇬🇦"),
        ("synthwave", "#e94560", "#1a1a2e", "#00ff88", "Synthwave"),
        ("solarized", "#268bd2", "#002b36", "#859900", "Solarized"),
        ("dracula", "#bd93f9", "#282a36", "#50fa7b", "Dracula"),
        ("nord", "#88c0d0", "#2e3440", "#a3be8c", "Nord"),
        ("monokai", "#f92672", "#272822", "#a6e22e", "Monokai"),
        ("tron", "#00d9ff", "#0c141f", "#00ff8f", "Tron"),
        ("one-dark", "#5c9cf5", "#282c34", "#7fd88f", "One Dark"),
        ("tokyo-night", "#7aa2f7", "#1a1b26", "#9ece6a", "Tokyo Night"),
    ]

    def __init__(self, current_theme: str = "apex-dark", **kwargs):
        super().__init__(**kwargs)
        self.current_theme = current_theme
        self.selected_index = 0
        # Find current theme
        for i, (name, *_) in enumerate(self.THEMES):
            if name == current_theme:
                self.selected_index = i
                break

    def compose(self):
        with Container(id="dialog-overlay"):
            with Container(id="theme-dialog", classes="dialog-window dialog-medium"):
                yield Static(" ◆  Theme Picker                     [ESC]", id="theme-title")
                yield Static(id="theme-list")

    def on_mount(self) -> None:
        self._refresh()

    def action_prev_theme(self) -> None:
        self.selected_index = (self.selected_index - 1) % len(self.THEMES)
        self._refresh()

    def action_next_theme(self) -> None:
        self.selected_index = (self.selected_index + 1) % len(self.THEMES)
        self._refresh()

    def action_select_theme(self) -> None:
        theme_name = self.THEMES[self.selected_index][0]
        from .messages import ThemeSelected
        self.post_message(ThemeSelected(theme_name))
        self.app.pop_screen()

    def action_close(self) -> None:
        self.app.pop_screen()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.action_close()

    def _refresh(self) -> None:
        try:
            container = self.query_one("#theme-list", Static)
            lines = []
            for i, (name, accent, bg, success, desc) in enumerate(self.THEMES):
                is_current = name == self.current_theme
                is_selected = i == self.selected_index

                if is_selected:
                    marker = "[bold cyan]▸[/]"
                elif is_current:
                    marker = "[green]✓[/]"
                else:
                    marker = " "

                # Show color swatches as colored blocks (simplified Rich markup)
                swatch = f"[bold]██[/][{accent}]██[/][{success}]██[/]"
                line = f"  {marker} {swatch}  [bold]{name}[/]  [dim]{desc}[/]"
                if is_selected:
                    line = f"  {marker} {swatch}  [bold cyan]{name}[/]  [dim]{desc}[/]"
                lines.append(line)

            container.update("\n".join(lines))
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# SESSION PICKER DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class SessionPickerDialog(ModalScreen):
    """Session picker with search (OpenCode-style)."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
        Binding("up", "prev_session", "Prev", show=False),
        Binding("down", "next_session", "Next", show=False),
        Binding("enter", "select_session", "Select", show=False),
    ]

    SAMPLE_SESSIONS = [
        ("s1", "main", "2 min ago", "12 messages"),
        ("s2", "bug-fix-auth", "1 hour ago", "28 messages"),
        ("s3", "refactor-api", "yesterday", "45 messages"),
        ("s4", "feature-dashboard", "2 days ago", "67 messages"),
        ("s5", "test-coverage", "3 days ago", "19 messages"),
    ]

    def __init__(self, current_session: str = "main", **kwargs):
        super().__init__(**kwargs)
        self.current_session = current_session
        self.selected_index = 0
        self.search_query = ""

    def compose(self):
        with Container(id="dialog-overlay"):
            with Container(id="session-dialog", classes="dialog-window dialog-medium"):
                yield Static(" ◆  Sessions                          [ESC]", id="session-title")
                yield Input(placeholder="  Search sessions...", id="session-search")
                yield Static(id="session-list")

    def on_mount(self) -> None:
        self._refresh()
        search = self.query_one("#session-search", Input)
        search.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.search_query = event.value.lower().strip()
        self.selected_index = 0
        self._refresh()

    def action_prev_session(self) -> None:
        sessions = self._get_filtered_sessions()
        if sessions:
            self.selected_index = (self.selected_index - 1) % len(sessions)
            self._refresh()

    def action_next_session(self) -> None:
        sessions = self._get_filtered_sessions()
        if sessions:
            self.selected_index = (self.selected_index + 1) % len(sessions)
            self._refresh()

    def action_select_session(self) -> None:
        sessions = self._get_filtered_sessions()
        if sessions and 0 <= self.selected_index < len(sessions):
            sid, name, _, _ = sessions[self.selected_index]
            from .messages import SessionSelected
            self.post_message(SessionSelected(sid, name))
            self.app.pop_screen()

    def action_close(self) -> None:
        self.app.pop_screen()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.action_close()

    def _get_filtered_sessions(self) -> list:
        if self.search_query:
            return [s for s in self.SAMPLE_SESSIONS if self.search_query in s[1].lower()]
        return self.SAMPLE_SESSIONS

    def _refresh(self) -> None:
        try:
            container = self.query_one("#session-list", Static)
            sessions = self._get_filtered_sessions()
            if not sessions:
                container.update("[dim]No sessions found[/]")
                return

            lines = []
            for i, (sid, name, time, count) in enumerate(sessions):
                is_current = name == self.current_session
                is_selected = i == self.selected_index

                marker = "[bold cyan]▸[/]" if is_selected else ("[green]✓[/]" if is_current else " ")
                line = f"  {marker} [bold]{name}[/]  [dim]{time} · {count}[/]"
                lines.append(line)

            lines.append("")
            lines.append(f"  [bold cyan]Ctrl+N[/] New session")

            container.update("\n".join(lines))
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# PERMISSION DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class PermissionDialog(ModalScreen):
    """Tool permission request dialog (OpenCode-style).

    Actions: Allow (once), Allow Session (all for this session), Deny.
    """

    BINDINGS = [
        Binding("escape", "deny", "Deny", show=False),
        Binding("a", "allow", "Allow", show=False),
        Binding("s", "allow_session", "Allow Session", show=False),
        Binding("d", "deny", "Deny", show=False),
        Binding("tab", "cycle_focus", "Cycle", show=False),
    ]

    def __init__(self, tool: str, args: dict = None, risk: str = "medium", **kwargs):
        super().__init__(**kwargs)
        self.tool = tool
        self.args = args or {}
        self.risk = risk  # "low", "medium", "high"
        self.focus_index = 0  # 0=Allow, 1=Session, 2=Deny

    def compose(self):
        with Container(id="dialog-overlay"):
            with Container(id="permission-dialog", classes="dialog-window dialog-small"):
                risk_colors = {"low": "green", "medium": "yellow", "high": "red"}
                risk_labels = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH"}
                color = risk_colors.get(self.risk, "yellow")
                label = risk_labels.get(self.risk, "MEDIUM")

                yield Static(f" Permission Required", id="permission-title")
                yield Static(
                    f"  [bold]{self.tool}[/] wants to execute\n"
                    f"  Risk: [bold {color}]{label}[/]",
                    id="permission-message"
                )
                if self.args:
                    args_str = "\n".join(f"  [bold]{k}[/]: {v}" for k, v in list(self.args.items())[:5])
                    yield Static(args_str, id="permission-args")

                with Horizontal(id="permission-buttons"):
                    yield Button("[A]llow", id="perm-allow", variant="success")
                    yield Button("[S]ession", id="perm-session", variant="primary")
                    yield Button("[D]eny", id="perm-deny", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from .messages import PermissionResponse
        if event.button.id == "perm-allow":
            self.post_message(PermissionResponse(self.tool, "allow"))
        elif event.button.id == "perm-session":
            self.post_message(PermissionResponse(self.tool, "allow_session"))
        elif event.button.id == "perm-deny":
            self.post_message(PermissionResponse(self.tool, "deny"))
        self.app.pop_screen()

    def action_allow(self) -> None:
        from .messages import PermissionResponse
        self.post_message(PermissionResponse(self.tool, "allow"))
        self.app.pop_screen()

    def action_allow_session(self) -> None:
        from .messages import PermissionResponse
        self.post_message(PermissionResponse(self.tool, "allow_session"))
        self.app.pop_screen()

    def action_deny(self) -> None:
        from .messages import PermissionResponse
        self.post_message(PermissionResponse(self.tool, "deny"))
        self.app.pop_screen()

    def action_cycle_focus(self) -> None:
        buttons = ["perm-allow", "perm-session", "perm-deny"]
        self.focus_index = (self.focus_index + 1) % 3
        try:
            btn = self.query_one(f"#{buttons[self.focus_index]}", Button)
            btn.focus()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# FILE PICKER DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class FilePickerDialog(ModalScreen):
    """File picker overlay for attachments (OpenCode-style)."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
    ]

    def __init__(self, cwd: str = ".", **kwargs):
        super().__init__(**kwargs)
        self.cwd = cwd

    def compose(self):
        with Container(id="dialog-overlay"):
            with Container(id="filepicker-dialog", classes="dialog-window dialog-medium"):
                yield Static(" ◆  File Picker                       [ESC]", id="filepicker-title")
                yield Input(placeholder="  Search files...", id="filepicker-search")
                yield DirectoryTree(self.cwd, id="filepicker-tree")

    def on_mount(self) -> None:
        search = self.query_one("#filepicker-search", Input)
        search.focus()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        from .messages import FileSelected
        self.post_message(FileSelected(str(event.path)))
        self.app.pop_screen()

    def action_close(self) -> None:
        self.app.pop_screen()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.action_close()


# ══════════════════════════════════════════════════════════════════════════════
# INIT DIALOG (First Run)
# ══════════════════════════════════════════════════════════════════════════════

class InitDialog(ModalScreen):
    """First-run setup dialog (OpenCode-style)."""

    BINDINGS = [
        Binding("escape", "skip", "Skip", show=False),
        Binding("enter", "continue", "Continue", show=False),
    ]

    def compose(self):
        with Container(id="dialog-overlay"):
            with Container(id="init-dialog", classes="dialog-window dialog-medium"):
                yield Static(
                    "\n  [bold cyan]◆ APEX[/]\n"
                    "  [dim]The Universal AI Coding Agent[/]\n",
                    id="init-title"
                )
                yield Static(
                    "  Welcome! Let's set up your API key.\n\n"
                    "  Enter your API key below, or press ESC to skip\n"
                    "  and configure later with /model command.\n",
                    id="init-message"
                )
                yield Input(placeholder="  sk-... or your API key", id="init-api-key", password=True)
                yield Static(
                    "  [dim]Supported: Anthropic, OpenAI, Google, xAI, etc.[/]",
                    id="init-hint"
                )
                with Horizontal(id="init-buttons"):
                    yield Button("Continue", id="init-continue", variant="primary")
                    yield Button("Skip", id="init-skip")

    def on_mount(self) -> None:
        self.query_one("#init-api-key", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "init-continue":
            key = self.query_one("#init-api-key", Input).value
            if key:
                self._save_api_key(key)
        self.app.pop_screen()

    def action_skip(self) -> None:
        self.app.pop_screen()

    def action_continue(self) -> None:
        key = self.query_one("#init-api-key", Input).value
        if key:
            self._save_api_key(key)
        self.app.pop_screen()

    def _save_api_key(self, key: str) -> None:
        """Save API key to config."""
        try:
            from ..config import Config
            config = Config()
            # Detect provider from key prefix
            if key.startswith("sk-ant-"):
                config.set("api_key_anthropic", key)
            elif key.startswith("sk-"):
                config.set("api_key_openai", key)
            else:
                config.set("api_key_custom", key)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# COMPLETION DIALOG (@-mention)
# ══════════════════════════════════════════════════════════════════════════════

class CompletionDialog(ModalScreen):
    """@-mention file/folder completion dialog (OpenCode-style).

    Triggered by typing @ in the input bar.
    Shows matching files/folders for inline completion.
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
        Binding("up", "prev_item", "Prev", show=False),
        Binding("down", "next_item", "Next", show=False),
        Binding("enter", "select_item", "Select", show=False),
        Binding("tab", "select_item", "Select", show=False),
    ]

    def __init__(self, search_string: str = "", cwd: str = ".", **kwargs):
        super().__init__(**kwargs)
        self.search_string = search_string
        self.cwd = cwd
        self.items: list[str] = []
        self.selected_index = 0

    def compose(self):
        with Container(id="dialog-overlay"):
            with Container(id="completion-dialog", classes="dialog-window dialog-small"):
                yield Static(id="completion-list")

    def on_mount(self) -> None:
        self._load_completions()
        self._refresh()

    def _load_completions(self) -> None:
        """Load file/folder completions based on search string."""
        try:
            root = Path(self.cwd)
            query = self.search_string.lower()
            self.items = []
            for p in sorted(root.rglob("*")):
                if any(part.startswith(".") for part in p.parts):
                    continue
                rel = str(p.relative_to(root))
                if query in rel.lower():
                    self.items.append(rel)
                    if len(self.items) >= 20:
                        break
        except Exception:
            self.items = []

    def action_prev_item(self) -> None:
        if self.items:
            self.selected_index = (self.selected_index - 1) % len(self.items)
            self._refresh()

    def action_next_item(self) -> None:
        if self.items:
            self.selected_index = (self.selected_index + 1) % len(self.items)
            self._refresh()

    def action_select_item(self) -> None:
        if self.items and 0 <= self.selected_index < len(self.items):
            from .messages import CompletionSelected
            self.post_message(CompletionSelected(self.search_string, self.items[self.selected_index]))
        self.app.pop_screen()

    def action_close(self) -> None:
        self.app.pop_screen()

    def _refresh(self) -> None:
        try:
            container = self.query_one("#completion-list", Static)
            if not self.items:
                container.update("[dim]No completions found[/]")
                return

            lines = []
            for i, item in enumerate(self.items):
                if i == self.selected_index:
                    lines.append(f"  [bold cyan]▸ {item}[/]")
                else:
                    icon = "📁" if "/" in item and not item.endswith((".py", ".js", ".ts", ".md", ".txt", ".json")) else "📄"
                    lines.append(f"    {item}")

            container.update("\n".join(lines))
        except Exception:
            pass
