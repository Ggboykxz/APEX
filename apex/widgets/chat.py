"""ChatPane — OpenCode-style polished chat with inline tool cards."""

import re
from textual.widgets import Static, RichLog
from textual.widget import Widget
from textual.message import Message
from datetime import datetime

from .messages import AgentThinking, AgentToolCall, AgentToolResult, AgentResponse, AgentError, ClearChat


class ToolCard(Widget):
    """Inline tool card with status indicator."""

    def __init__(self, name: str = "", args: str = "", status: str = "pending", duration: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = name
        self.tool_args = args
        self.tool_status = status
        self.tool_duration = duration
        self.output = ""
        self.expanded = False

    def compose(self):
        icons = {"pending": "○", "running": "⟳", "success": "✓", "error": "✗"}
        icon = icons.get(self.tool_status, "?")

        yield Static(
            f"{icon} {self.tool_name}" + (f" · {self.tool_duration:.1f}s" if self.tool_duration > 0 else ""),
            classes=f"tool-card-header",
        )
        if self.tool_args:
            yield Static(self.tool_args, classes="tool-card-args")

    def update_status(self, status: str, duration: float = 0.0, output: str = "") -> None:
        self.tool_status = status
        self.tool_duration = duration
        self.output = output
        self.refresh()


class ThinkingIndicator(Widget):
    """Animated thinking indicator."""

    def compose(self):
        yield Static("⠋", classes="thinking-spinner")
        yield Static(" Thinking...", classes="thinking-text")


def highlight_syntax(code: str, language: str = "") -> str:
    """Basic syntax highlighting for Rich markup."""
    keywords = [
        "def", "class", "return", "if", "else", "elif", "for", "while",
        "try", "except", "finally", "import", "from", "as", "with",
        "async", "await", "raise", "pass", "break", "continue",
        "lambda", "yield", "True", "False", "None",
        "function", "const", "let", "var", "type", "interface",
    ]

    for kw in keywords:
        code = re.sub(rf"\b({kw})\b", r"[bold magenta]\1[/]", code, flags=re.MULTILINE)

    # Strings (simple)
    code = re.sub(r'"[^"]*"', r"[yellow]\0[/]", code)
    code = re.sub(r"'[^']*'", r"[yellow]\0[/]", code)

    # Comments
    code = re.sub(r"#.*$", r"[dim]\0[/]", code, flags=re.MULTILINE)
    code = re.sub(r"//.*$", r"[dim]\0[/]", code, flags=re.MULTILINE)

    # Numbers
    code = re.sub(r"\b(\d+\.?\d*)\b", r"[violet]\1[/]", code)

    return code


class ChatPane(Widget):
    """OpenCode-style chat area with RichLog rendering."""

    message_count = 0

    def compose(self):
        yield RichLog(id="chat-scroll", markup=True, auto_scroll=True)

    def add_user_message(self, content: str) -> None:
        """Add a user message (right-aligned, subtle)."""
        log = self.query_one("#chat-scroll", RichLog)
        timestamp = datetime.now().strftime("%H:%M")
        self.message_count += 1

        log.write(f"[bold]You[/] · {timestamp}")
        log.write(f"[dim]│[/] {content}")
        log.write("")

    def add_ai_message(self, content: str, model: str = "") -> None:
        """Add an AI message (left-aligned, accent border)."""
        log = self.query_one("#chat-scroll", RichLog)
        timestamp = datetime.now().strftime("%H:%M")
        self.message_count += 1

        log.write(f"[bold cyan]APEX[/] {model} · {timestamp}")
        formatted = self._format_content(content)
        log.write(formatted)
        log.write("")

    def add_system_message(self, content: str) -> None:
        """Add a system/notification message."""
        log = self.query_one("#chat-scroll", RichLog)

        log.write(f"[bold green]◆[/] [dim]system[/]")
        formatted = self._format_content(content)
        log.write(formatted)
        log.write("")

    def add_tool_call(self, name: str, args: dict, command: str = "") -> None:
        """Add an inline tool call card."""
        log = self.query_one("#chat-scroll", RichLog)
        args_str = ", ".join(f"{k}={v}" for k, v in list(args.items())[:3])
        if len(args) > 3:
            args_str += ", ..."

        log.write(f"  [cyan]⟳[/] [bold magenta]{name}[/]([dim]{args_str}[/])")

    def add_tool_result(self, name: str, result: str, success: bool, duration: float = 0.0) -> None:
        """Add an inline tool result."""
        log = self.query_one("#chat-scroll", RichLog)
        color = "green" if success else "red"
        icon = "✓" if success else "✗"

        lines = result.split("\n")
        if len(lines) > 8:
            truncated = "\n".join(lines[:8])
            truncated += f"\n  [dim]... {len(lines) - 8} more lines[/]"
        else:
            truncated = result[:500] + ("..." if len(result) > 500 else "")

        log.write(f"  [{color}]{icon}[/] [bold {color}]{name}[/] [dim]{duration:.1f}s[/]")
        for line in truncated.split("\n"):
            log.write(f"  [dim]│[/] {line}")

    def add_thinking(self) -> None:
        """Add thinking indicator."""
        log = self.query_one("#chat-scroll", RichLog)
        log.write("[dim]  ⠋  Thinking...[/]")

    def remove_thinking(self) -> None:
        """Remove thinking indicator (placeholder — RichLog doesn't support removal)."""
        pass

    def clear(self) -> None:
        """Clear all messages."""
        log = self.query_one("#chat-scroll", RichLog)
        log.clear()
        self.message_count = 0

    def scroll_end(self) -> None:
        """Scroll to bottom."""
        log = self.query_one("#chat-scroll", RichLog)
        log.scroll_end()

    def _format_content(self, content: str) -> str:
        """Format message content with code block highlighting."""
        code_block_pattern = r"```(\w*)\n?([\s\S]*?)```"

        def replace_code_block(m):
            lang = m.group(1) or "text"
            code = m.group(2).rstrip()
            highlighted = highlight_syntax(code, lang)
            border_char = "─"
            width = min(60, max(20, len(max(code.split("\n"), key=len))))
            top = f"[dim]┌─ {lang} {'─' * (width - len(lang) - 4)}┐[/]"
            bottom = f"[dim]└{'─' * width}┘[/]"
            return f"{top}\n{highlighted}\n{bottom}"

        formatted = re.sub(code_block_pattern, replace_code_block, content)
        return formatted

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
            log.write(f"[bold red]Error:[/] {message.error}")
            log.write("")
        elif isinstance(message, ClearChat):
            self.clear()
