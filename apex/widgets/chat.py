"""ChatPane - Messages and tool cards."""

from textual.widgets import Static, RichLog
from textual.widget import Widget
from datetime import datetime

from .messages import AgentThinking, AgentToolCall, AgentToolResult, AgentResponse, AgentError


class MessageBubble(Widget):
    def __init__(self, role: str = "assistant", content: str = "", model: str = "", **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content = content
        self.model = model

    def compose(self):
        timestamp = datetime.now().strftime("%H:%M")
        role_class = "role-apex" if self.role == "assistant" else "role-user"

        header = Static(
            f"[{role_class}]{role_class}[/] {self.model} · {timestamp}",
            classes="msg-header",
        )
        content = Static(self.content, classes="msg-content")

        yield header
        yield content

    def update_content(self, content: str) -> None:
        content_el = self.query_one(".msg-content", Static)
        content_el.update(content)


class ToolCard(Widget):
    def __init__(self, name: str = "", command: str = "", status: str = "pending", **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.command = command
        self.status = status
        self.duration = 0.0
        self.output = ""
        self.expanded = False

    def compose(self):
        status_icon = {"pending": "⚙", "running": "⚙", "success": "✓", "error": "✗"}
        icon = status_icon.get(self.status, "?")

        header = Static(
            f"{icon} {self.name}" + (f" · {self.duration:.1f}s" if self.duration > 0 else ""),
            classes="tool-header",
        )
        command_el = Static(f"$ {self.command}", classes="tool-command")
        output_el = Static("", classes="tool-output")

        yield header
        yield command_el
        yield output_el

    def update_status(self, status: str, duration: float = 0.0, output: str = "") -> None:
        self.status = status
        self.duration = duration
        self.output = output
        self.refresh()

    def toggle_expand(self) -> None:
        self.expanded = not self.expanded
        output_el = self.query_one(".tool-output", Static)
        if self.expanded:
            output_el.update(self.output[:500] + ("..." if len(self.output) > 500 else ""))
        else:
            lines = self.output.split("\n")
            if len(lines) > 5:
                output_el.update("\n".join(lines[:5]) + f"\n... ({len(lines) - 5} more lines)")
            else:
                output_el.update(self.output)


class ThinkingIndicator(Widget):
    def compose(self):
        yield Static("⠋", classes="thinking-spinner")
        yield Static("  Réflexion en cours...", classes="thinking-text")


class ChatPane(Widget):
    messages: list[Widget] = []

    def compose(self):
        yield RichLog(id="chat-scroll", markup=True)

    def add_user_message(self, content: str) -> None:
        log = self.query_one("#chat-scroll", RichLog)
        log.write(f"[cyan bold]›[/] [bold]{content}[/]")
        log.write("")

    def add_ai_message(self, content: str, model: str = "") -> None:
        log = self.query_one("#chat-scroll", RichLog)
        timestamp = datetime.now().strftime("%H:%M")
        log.write(f"[bold cyan]APEX[/] {model} · {timestamp}")
        log.write(content)
        log.write("")

    def add_tool_call(self, name: str, args: dict, command: str = "") -> None:
        log = self.query_one("#chat-scroll", RichLog)
        args_str = ", ".join(f"[dim]{k}[/]=[white]{v}" for k, v in list(args.items())[:2])
        log.write(f"[cyan]⚙[/] [bold magenta]{name}[/]([white]{args_str}[/])")

    def add_tool_result(self, name: str, result: str, success: bool, duration: float = 0.0) -> None:
        log = self.query_one("#chat-scroll", RichLog)
        color = "green" if success else "red"
        icon = "✓" if success else "✗"
        truncated = result[:200] + "..." if len(result) > 200 else result
        log.write(f"[{color}]{icon}[/] [bold {color}]{name}[/]: {truncated}")

    def add_thinking(self) -> None:
        log = self.query_one("#chat-scroll", RichLog)
        log.write("[dim]⠋  Réflexion en cours...[/]")

    def remove_thinking(self) -> None:
        pass

    def clear(self) -> None:
        log = self.query_one("#chat-scroll", RichLog)
        log.clear()

    def scroll_end(self) -> None:
        log = self.query_one("#chat-scroll", RichLog)
        log.scroll_end()

    def on_message(self, message) -> None:
        from .messages import ClearChat
        
        if isinstance(message, AgentThinking):
            self.add_thinking()
        elif isinstance(message, AgentToolCall):
            self.add_tool_call(message.name, message.args)
        elif isinstance(message, AgentToolResult):
            self.add_tool_result(message.name, message.result, message.success, message.duration)
        elif isinstance(message, AgentResponse):
            self.remove_thinking()
            self.add_ai_message(message.text, message.model)
            self.scroll_end()
        elif isinstance(message, AgentError):
            self.remove_thinking()
            log = self.query_one("#chat-scroll", RichLog)
            log.write(f"[red bold]Error:[/] {message.error}")
        elif isinstance(message, ClearChat):
            self.clear()
