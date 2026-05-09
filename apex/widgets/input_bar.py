"""InputBar - User message input."""

from textual.widgets import Input, Static
from textual.widget import Widget
from textual.events import Key
from textual.message import Message


class InputBar(Widget):
    is_thinking = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_input = ""
        self._history: list[str] = []
        self._history_index = -1

    def compose(self):
        yield Static("›", id="input-prefix")
        yield Input(
            placeholder="Message APEX... (Enter=send, Shift+Enter=new line)",
            id="chat-input",
            multiline=True,
        )

    @property
    def value(self) -> str:
        input_el = self.query_one("#chat-input", Input)
        return input_el.value

    @value.setter
    def value(self, val: str) -> None:
        input_el = self.query_one("#chat-input", Input)
        input_el.value = val

    @property
    def cursor_position(self) -> int:
        input_el = self.query_one("#chat-input", Input)
        return input_el.cursor_position

    @cursor_position.setter
    def cursor_position(self, pos: int) -> None:
        input_el = self.query_one("#chat-input", Input)
        input_el.cursor_position = pos

    def on_input_changed(self, event: Input.Changed) -> None:
        self.current_input = event.value
        input_el = self.query_one("#chat-input", Input)
        if event.value.startswith("/"):
            input_el.add_class("command")
        else:
            input_el.remove_class("command")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if not event.value.strip():
            return
        if self.is_thinking:
            return

        user_input = event.value.strip()

        if user_input.startswith("/"):
            self.post_message(CommandInput(user_input))
        else:
            self.post_message(UserMessage(user_input))

        if user_input not in self._history:
            self._history.append(user_input)
        self._history_index = len(self._history)

        input_el = self.query_one("#chat-input", Input)
        input_el.value = ""

    def on_key(self, event: Key) -> None:
        if event.key == "enter" and not event.shift:
            pass
        elif event.key == "up" and not event.shift:
            if self._history_index > 0:
                self._history_index -= 1
                input_el = self.query_one("#chat-input", Input)
                input_el.value = self._history[self._history_index]
        elif event.key == "down" and not event.shift:
            if self._history_index < len(self._history) - 1:
                self._history_index += 1
                input_el = self.query_one("#chat-input", Input)
                input_el.value = self._history[self._history_index]
            else:
                self._history_index = len(self._history)
                input_el = self.query_one("#chat-input", Input)
                input_el.value = ""

    def set_thinking(self, thinking: bool) -> None:
        self.is_thinking = thinking
        input_el = self.query_one("#chat-input", Input)
        input_el.disabled = thinking
        if thinking:
            input_el.placeholder = "APEX réfléchit..."
            input_el.add_class("thinking")
        else:
            input_el.placeholder = "Message APEX..."
            input_el.remove_class("thinking")


class UserMessage(Message):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class CommandInput(Message):
    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command
