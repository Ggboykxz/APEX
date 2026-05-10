"""InputBar — OpenCode-style input with mode indicator and @-mention support.

Refonte: Enhanced with:
- Multi-line input (TextArea)
- Mode indicator with color
- @-mention trigger for file completions
- Command detection with / prefix highlighting
- Thinking state with disabled input
- Shift+Enter for new lines
- Ctrl+E to open in $EDITOR
- Ctrl+R for attachment management
- Context info display
"""

from textual.widgets import TextArea, Static
from textual.widget import Widget
from textual.events import Key
from textual.message import Message
from textual.reactive import reactive


class InputBar(Widget):
    """Input bar with prompt prefix, mode indicator, and context info.

    OpenCode-style with:
    - `›` prompt prefix
    - Multi-line TextArea
    - Mode indicator (◆ Agent / ◇ Plan / ⚡ Yolo)
    - Context info (token count)
    - Command detection (/ prefix)
    - @-mention trigger
    """

    is_thinking = False
    _focused = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_input = ""
        self._history: list[str] = []
        self._history_index = -1

    def compose(self):
        yield Static("›", id="input-prefix")
        yield TextArea(
            placeholder="Message APEX... (Enter=send, Shift+Enter=new line, @=mention)",
            id="chat-input",
            theme="css",
        )
        yield Static("◆ Agent", id="mode-indicator")
        yield Static("", id="context-info")

    @property
    def value(self) -> str:
        input_el = self.query_one("#chat-input", TextArea)
        return input_el.text

    @value.setter
    def value(self, val: str) -> None:
        input_el = self.query_one("#chat-input", TextArea)
        input_el.text = val

    @property
    def cursor_position(self) -> int:
        input_el = self.query_one("#chat-input", TextArea)
        return input_el.cursor_position

    @cursor_position.setter
    def cursor_position(self, pos: int) -> None:
        input_el = self.query_one("#chat-input", TextArea)
        input_el.cursor_position = pos

    @property
    def is_focused(self) -> bool:
        return self._focused

    def on_focus(self) -> None:
        self._focused = True

    def on_blur(self) -> None:
        self._focused = False

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self.current_input = event.text

        # Command detection
        text = event.text
        if text.startswith("/"):
            event.text_area.add_class("command")
        else:
            event.text_area.remove_class("command")

        # @-mention detection — post completion trigger
        if "@" in text:
            at_pos = text.rfind("@")
            if at_pos >= 0:
                search_str = text[at_pos + 1:]
                # Only trigger if search string is short enough
                if len(search_str) < 30 and (not search_str or search_str.isalnum() or "/" in search_str):
                    self.post_message(MentionTrigger(search_str))

    def on_key(self, event: Key) -> None:
        input_el = self.query_one("#chat-input", TextArea)
        text = input_el.text.strip()

        if event.key == "enter" and not event.shift:
            if self.is_thinking:
                return
            if text:
                user_input = text
                if user_input.startswith("/"):
                    self.post_message(CommandInput(user_input))
                else:
                    self.post_message(UserMessage(user_input))
                if user_input not in self._history:
                    self._history.append(user_input)
                self._history_index = len(self._history)
                input_el.text = ""
            event.prevent_default()
        elif event.key == "ctrl+e":
            # Open in $EDITOR
            self._open_editor()
        elif event.key == "up" and not input_el.text:
            # History navigation (only when input is empty)
            if self._history_index > 0:
                self._history_index -= 1
                input_el.text = self._history[self._history_index]
        elif event.key == "down" and not input_el.text:
            if self._history_index < len(self._history) - 1:
                self._history_index += 1
                input_el.text = self._history[self._history_index]
            else:
                self._history_index = len(self._history)
                input_el.text = ""

    def _open_editor(self) -> None:
        """Open current input in $EDITOR."""
        import os
        import subprocess
        import tempfile

        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write(self.current_input)
            f.flush()
            try:
                subprocess.run([editor, f.name])
                with open(f.name) as rf:
                    content = rf.read().strip()
                if content:
                    input_el = self.query_one("#chat-input", TextArea)
                    input_el.text = content
            except Exception:
                pass
            finally:
                try:
                    os.unlink(f.name)
                except Exception:
                    pass

    def set_thinking(self, thinking: bool) -> None:
        self.is_thinking = thinking
        input_el = self.query_one("#chat-input", TextArea)
        input_el.disabled = thinking
        if thinking:
            input_el.placeholder = "APEX is thinking..."
            input_el.add_class("thinking")
        else:
            input_el.placeholder = "Message APEX... (Enter=send, Shift+Enter=new line, @=mention)"
            input_el.remove_class("thinking")

    def update_mode(self, mode: str) -> None:
        mode_labels = {
            "plan": "◇ Plan",
            "agent": "◆ Agent",
            "yolo": "⚡ Yolo",
        }
        mode_colors = {
            "plan": "yellow",
            "agent": "cyan",
            "yolo": "red",
        }
        try:
            mode_el = self.query_one("#mode-indicator", Static)
            mode_el.update(mode_labels.get(mode, "◆ Agent"))
            # Update prefix color
            prefix_el = self.query_one("#input-prefix", Static)
            color = mode_colors.get(mode, "cyan")
            mode_el.remove_class("mode-plan", "mode-agent", "mode-yolo")
            mode_el.add_class(f"mode-{mode}")
        except Exception:
            pass

    def update_context(self, tokens: int, pct: float) -> None:
        try:
            ctx_el = self.query_one("#context-info", Static)
            if tokens > 0:
                ctx_el.update(f"●{tokens}")
            else:
                ctx_el.update("")
        except Exception:
            pass


class UserMessage(Message):
    """User sent a message."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class CommandInput(Message):
    """User entered a /command."""

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command


class MentionTrigger(Message):
    """User typed @ — trigger completion dialog."""

    def __init__(self, search_string: str) -> None:
        super().__init__()
        self.search_string = search_string
