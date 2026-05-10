"""InputBar — OpenCode-style input with mode indicator."""

from textual.widgets import TextArea, Static
from textual.widget import Widget
from textual.events import Key
from textual.message import Message


class InputBar(Widget):
    """Input bar with prompt prefix, mode indicator, and context info."""

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
            placeholder="Message APEX... (Enter=send, Shift+Enter=new line)",
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
        if event.text.startswith("/"):
            event.text_area.add_class("command")
        else:
            event.text_area.remove_class("command")

    def on_key(self, event: Key) -> None:
        input_el = self.query_one("#chat-input", TextArea)
        text = input_el.text.strip()

        if event.key == "enter" and not event.shift and text:
            if self.is_thinking:
                return
            user_input = text
            if user_input.startswith("/"):
                self.post_message(CommandInput(user_input))
            else:
                self.post_message(UserMessage(user_input))
            if user_input not in self._history:
                self._history.append(user_input)
            self._history_index = len(self._history)
            input_el.text = ""
        elif event.key == "up" and not event.shift:
            if self._history_index > 0:
                self._history_index -= 1
                input_el.text = self._history[self._history_index]
        elif event.key == "down" and not event.shift:
            if self._history_index < len(self._history) - 1:
                self._history_index += 1
                input_el.text = self._history[self._history_index]
            else:
                self._history_index = len(self._history)
                input_el.text = ""

    def set_thinking(self, thinking: bool) -> None:
        self.is_thinking = thinking
        input_el = self.query_one("#chat-input", TextArea)
        input_el.disabled = thinking
        if thinking:
            input_el.placeholder = "APEX is thinking..."
            input_el.add_class("thinking")
        else:
            input_el.placeholder = "Message APEX... (Enter=send, Shift+Enter=new line)"
            input_el.remove_class("thinking")

    def update_mode(self, mode: str) -> None:
        mode_labels = {"plan": "◇ Plan", "agent": "◆ Agent", "yolo": "⚡ Yolo"}
        try:
            mode_el = self.query_one("#mode-indicator", Static)
            mode_el.update(mode_labels.get(mode, "◆ Agent"))
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
