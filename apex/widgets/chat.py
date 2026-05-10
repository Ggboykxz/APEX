"""ChatPane — OpenCode-style polished chat with proper markdown & diff rendering.

Refonte: Complete rewrite with:
- Proper markdown rendering (headings, bold, italic, code blocks, lists, links, blockquotes)
- Diff rendering with + and - lines, color coded
- Inline tool cards with expand/collapse
- Thinking indicator with spinner animation
- Message grouping and timestamps
- RichLog-based rendering with Rich markup
"""

import re
import time
from textual.widgets import Static, RichLog
from textual.widget import Widget
from textual.message import Message
from textual.reactive import reactive
from datetime import datetime
from typing import Optional


# ── Syntax Highlighting ───────────────────────────────────────────────────────

def highlight_syntax(code: str, language: str = "") -> str:
    """Enhanced syntax highlighting for Rich markup.

    Applies keyword, string, comment, number, and type highlighting
    with support for Python, JS/TS, Go, Rust, and shell scripts.
    """
    keywords = {
        "python": ["def", "class", "return", "if", "else", "elif", "for", "while",
                    "try", "except", "finally", "import", "from", "as", "with",
                    "async", "await", "raise", "pass", "break", "continue",
                    "lambda", "yield", "True", "False", "None", "and", "or", "not",
                    "in", "is", "global", "nonlocal", "assert", "del"],
        "javascript": ["function", "const", "let", "var", "class", "return", "if",
                        "else", "for", "while", "try", "catch", "finally", "import",
                        "export", "from", "as", "async", "await", "new", "this",
                        "typeof", "instanceof", "switch", "case", "break", "default",
                        "throw", "yield", "true", "false", "null", "undefined"],
        "typescript": ["function", "const", "let", "var", "class", "return", "if",
                        "else", "for", "while", "try", "catch", "finally", "import",
                        "export", "from", "as", "async", "await", "new", "this",
                        "type", "interface", "enum", "implements", "extends",
                        "typeof", "instanceof", "switch", "case", "break", "default",
                        "throw", "yield", "true", "false", "null", "undefined",
                        "never", "unknown", "any", "void"],
        "go": ["func", "package", "import", "return", "if", "else", "for", "range",
               "switch", "case", "default", "break", "continue", "go", "defer",
               "chan", "select", "type", "struct", "interface", "map", "slice",
               "var", "const", "true", "false", "nil", "err"],
        "rust": ["fn", "let", "mut", "pub", "impl", "struct", "enum", "trait",
                 "match", "if", "else", "for", "while", "loop", "return", "use",
                 "mod", "crate", "self", "super", "where", "async", "await",
                 "true", "false", "Some", "None", "Ok", "Err"],
        "sh": ["if", "then", "else", "elif", "fi", "for", "while", "do", "done",
               "case", "esac", "function", "return", "exit", "local", "export",
               "source", "echo", "cd", "rm", "cp", "mv", "mkdir", "chmod"],
    }

    # Default to python keywords if language not found
    lang_key = language.lower().replace("bash", "sh").replace("zsh", "sh").replace("shell", "sh")
    lang_key = lang_key.replace("js", "javascript").replace("ts", "typescript").replace("tsx", "typescript").replace("jsx", "javascript")
    kws = keywords.get(lang_key, keywords["python"])

    # Escape existing Rich markup
    code = code.replace("[", "\\[")

    # Comments (single line)
    if lang_key in ("python",):
        code = re.sub(r"(#[^\n]*)", r"[dim]\1[/]", code)
    else:
        code = re.sub(r"(//[^\n]*)", r"[dim]\1[/]", code)

    # Strings (double and single quoted)
    code = re.sub(r'("(?:[^"\\]|\\.)*")', r"[yellow]\1[/]", code)
    code = re.sub(r"('(?:[^'\\]|\\.)*')", r"[yellow]\1[/]", code)

    # Keywords
    for kw in kws:
        pattern = rf"\b({kw})\b"
        code = re.sub(pattern, r"[bold magenta]\1[/]", code, flags=re.IGNORECASE if lang_key == "sh" else 0)

    # Numbers
    code = re.sub(r"\b(\d+\.?\d*)\b", r"[violet]\1[/]", code)

    # Decorators / annotations
    code = re.sub(r"(@\w+)", r"[bold cyan]\1[/]", code)

    return code


# ── Markdown Rendering ────────────────────────────────────────────────────────

def render_markdown(text: str) -> str:
    """Convert markdown to Rich markup for display in RichLog.

    Handles: code blocks, inline code, bold, italic, links,
    headings, lists, blockquotes, horizontal rules.
    """
    # Code blocks
    code_block_pattern = r"```(\w*)\n?([\s\S]*?)```"

    def replace_code_block(m):
        lang = m.group(1) or "text"
        code = m.group(2).rstrip()
        highlighted = highlight_syntax(code, lang)
        # Calculate width for border
        max_line_len = max(len(line) for line in code.split("\n")) if code else 0
        width = min(70, max(20, max_line_len + 4))
        top = f"[dim]┌─ {lang} {'─' * max(1, width - len(lang) - 4)}┐[/]"
        bottom = f"[dim]└{'─' * width}┘[/]"
        # Add line numbers
        lines = highlighted.split("\n")
        numbered = []
        for i, line in enumerate(lines, 1):
            num = f"[dim]{i:>3} │[/] "
            numbered.append(f"{num}{line}")
        body = "\n".join(numbered)
        return f"{top}\n{body}\n{bottom}"

    text = re.sub(code_block_pattern, replace_code_block, text)

    # Inline code
    text = re.sub(r"`([^`]+)`", r"[bold cyan]\1[/]", text)

    # Bold
    text = re.sub(r"\*\*([^*]+)\*\*", r"[bold]\1[/]", text)

    # Italic
    text = re.sub(r"\*([^*]+)\*", r"[italic]\1[/]", text)

    # Headings
    text = re.sub(r"^### (.+)$", r"[bold cyan]   \1[/]", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"[bold cyan]  \1[/]", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"[bold cyan] \1[/]", text, flags=re.MULTILINE)

    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"[bold cyan]\1[/] [dim](\2)[/]", text)

    # Bullet lists
    text = re.sub(r"^  - (.+)$", r"  [cyan]•[/] \1", text, flags=re.MULTILINE)
    text = re.sub(r"^- (.+)$", r"[cyan]•[/] \1", text, flags=re.MULTILINE)

    # Numbered lists
    text = re.sub(r"^  (\d+)\. (.+)$", r"  [cyan]\1.[/] \2", text, flags=re.MULTILINE)

    # Blockquotes
    text = re.sub(r"^> (.+)$", r"[dim]┃[/] [italic]\1[/]", text, flags=re.MULTILINE)

    # Horizontal rules
    text = re.sub(r"^---+$", r"[dim]─────[/]", text, flags=re.MULTILINE)

    return text


# ── Diff Rendering ────────────────────────────────────────────────────────────

def render_diff(text: str) -> str:
    """Render unified diff with color coding.

    - Added lines: green with + prefix
    - Removed lines: red with - prefix
    - Context lines: dim
    - File headers: bold cyan
    - Hunk headers: dim with @@ delimiters
    """
    lines = text.split("\n")
    result = []
    in_diff = False

    for line in lines:
        # Diff file header
        if line.startswith("--- ") or line.startswith("+++ "):
            in_diff = True
            result.append(f"[bold cyan]{line}[/]")
        # Hunk header
        elif line.startswith("@@"):
            in_diff = True
            result.append(f"[dim cyan]{line}[/]")
        # Added line
        elif in_diff and line.startswith("+"):
            result.append(f"[green]{line}[/]")
        # Removed line
        elif in_diff and line.startswith("-"):
            result.append(f"[red]{line}[/]")
        # Context line
        elif in_diff and line.startswith(" "):
            result.append(f"[dim]{line}[/]")
        # Non-diff line
        else:
            in_diff = False
            result.append(line)

    return "\n".join(result)


# ── Tool Card Widget ──────────────────────────────────────────────────────────

class ToolCard(Widget):
    """Inline tool card with status indicator, expand/collapse for output."""

    def __init__(
        self,
        name: str = "",
        args: str = "",
        status: str = "pending",
        duration: float = 0.0,
        output: str = "",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.tool_name = name
        self.tool_args = args
        self.tool_status = status
        self.tool_duration = duration
        self.tool_output = output
        self.expanded = False

    def compose(self):
        icons = {"pending": "○", "running": "⟳", "success": "✓", "error": "✗"}
        icon = icons.get(self.tool_status, "?")

        duration_str = f" [dim]{self.tool_duration:.1f}s[/]" if self.tool_duration > 0 else ""
        args_str = f" [dim]{self.tool_args[:50]}[/]" if self.tool_args else ""

        yield Static(
            f"  {icon} [bold]{self.tool_name}[/]{args_str}{duration_str}",
            classes="tool-card-header",
        )
        if self.tool_output:
            if self.expanded:
                yield Static(f"  {self.tool_output}", classes="tool-card-output")
            else:
                first_lines = self.tool_output.split("\n")[:3]
                preview = "\n".join(first_lines)
                if len(self.tool_output.split("\n")) > 3:
                    preview += f"\n  [dim cyan]... click to expand[/]"
                yield Static(f"  {preview}", classes="tool-card-output collapsed")

    def update_status(self, status: str, duration: float = 0.0, output: str = "") -> None:
        self.tool_status = status
        self.tool_duration = duration
        self.tool_output = output
        self.refresh()

    def on_click(self) -> None:
        if self.tool_output:
            self.expanded = not self.expanded
            self.refresh()


# ── Thinking Indicator ────────────────────────────────────────────────────────

class ThinkingIndicator(Widget):
    """Animated thinking indicator with spinner."""

    spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    _frame = reactive(0)

    def compose(self):
        yield Static("⠋", id="thinking-spinner", classes="thinking-spinner")
        yield Static(" APEX is thinking...", id="thinking-text", classes="thinking-text")

    def on_mount(self) -> None:
        self._animate()

    def _animate(self) -> None:
        self._frame = (self._frame + 1) % len(self.spinner_frames)
        try:
            spinner = self.query_one("#thinking-spinner", Static)
            spinner.update(self.spinner_frames[self._frame])
        except Exception:
            pass
        self.set_timer(0.08, self._animate)

    def watch__frame(self, frame: int) -> None:
        pass


# ── Main Chat Pane ────────────────────────────────────────────────────────────

class ChatPane(Widget):
    """OpenCode-style chat area with RichLog rendering.

    Features:
    - User messages with right-aligned header
    - AI messages with accent-colored left border
    - System messages with green indicator
    - Inline tool cards with status
    - Thinking indicator with spinner
    - Diff rendering for code changes
    - Markdown rendering for AI responses
    - Message timestamps
    """

    message_count = 0
    _thinking_active = False

    def compose(self):
        yield RichLog(
            id="chat-scroll",
            markup=True,
            auto_scroll=True,
            highlight=True,
        )

    def add_user_message(self, content: str) -> None:
        """Add a user message with right-aligned header."""
        log = self.query_one("#chat-scroll", RichLog)
        timestamp = datetime.now().strftime("%H:%M")
        self.message_count += 1

        log.write(f"[dim]{'─' * 60}[/]")
        log.write(f"[bold]You[/] · [dim]{timestamp}[/]")
        log.write(f"  {content}")
        log.write("")

    def add_ai_message(self, content: str, model: str = "") -> None:
        """Add an AI message with accent border and markdown rendering."""
        log = self.query_one("#chat-scroll", RichLog)
        timestamp = datetime.now().strftime("%H:%M")
        self.message_count += 1

        model_str = f" [dim]{model}[/]" if model else ""
        log.write(f"[bold cyan]◆ APEX[/]{model_str} · [dim]{timestamp}[/]")

        # Detect if content is a diff
        if "--- " in content and "+++" in content and "@@" in content:
            formatted = render_diff(content)
        else:
            formatted = render_markdown(content)

        # Add left border to AI messages
        for line in formatted.split("\n"):
            log.write(f"[cyan]│[/] {line}")
        log.write("")

    def add_system_message(self, content: str) -> None:
        """Add a system/notification message."""
        log = self.query_one("#chat-scroll", RichLog)

        log.write(f"[bold green]◆[/] [dim]system[/]")
        formatted = render_markdown(content)
        for line in formatted.split("\n"):
            log.write(f"[dim]│[/] {line}")
        log.write("")

    def add_tool_call(self, name: str, args: dict, command: str = "") -> None:
        """Add an inline tool call card."""
        log = self.query_one("#chat-scroll", RichLog)
        args_str = ", ".join(f"{k}={v}" for k, v in list(args.items())[:3])
        if len(args) > 3:
            args_str += ", ..."

        log.write(f"  [cyan]⟳[/] [bold magenta]{name}[/]([dim]{args_str}[/])")

    def add_tool_result(self, name: str, result: str, success: bool, duration: float = 0.0) -> None:
        """Add an inline tool result with status icon."""
        log = self.query_one("#chat-scroll", RichLog)
        color = "green" if success else "red"
        icon = "✓" if success else "✗"
        duration_str = f" [dim]{duration:.1f}s[/]" if duration > 0 else ""

        log.write(f"  [{color}]{icon}[/] [bold {color}]{name}[/]{duration_str}")

        # Show result preview
        lines = result.split("\n")
        if len(lines) > 10:
            for line in lines[:8]:
                log.write(f"  [dim]│[/] {line}")
            log.write(f"  [dim]│ ... {len(lines) - 8} more lines[/]")
        else:
            truncated = result[:800]
            for line in truncated.split("\n"):
                log.write(f"  [dim]│[/] {line}")

    def add_diff(self, filename: str, diff_content: str) -> None:
        """Add a diff display for a file change."""
        log = self.query_one("#chat-scroll", RichLog)
        log.write(f"  [bold cyan]◆ {filename}[/]")
        rendered = render_diff(diff_content)
        for line in rendered.split("\n"):
            log.write(f"  {line}")
        log.write("")

    def add_thinking(self) -> None:
        """Add thinking indicator."""
        self._thinking_active = True
        log = self.query_one("#chat-scroll", RichLog)
        log.write(f"[cyan]⠋[/] [dim]APEX is thinking...[/]")

    def remove_thinking(self) -> None:
        """Remove thinking indicator (RichLog doesn't support removal)."""
        self._thinking_active = False

    def add_error(self, error: str, tool: str = "") -> None:
        """Add an error message."""
        log = self.query_one("#chat-scroll", RichLog)
        if tool:
            log.write(f"[bold red]✗ {tool}:[/] {error}")
        else:
            log.write(f"[bold red]Error:[/] {error}")
        log.write("")

    def clear(self) -> None:
        """Clear all messages."""
        log = self.query_one("#chat-scroll", RichLog)
        log.clear()
        self.message_count = 0
        self._thinking_active = False

    def scroll_end(self) -> None:
        """Scroll to bottom."""
        log = self.query_one("#chat-scroll", RichLog)
        log.scroll_end()

    def on_message(self, message) -> None:
        from .messages import (
            AgentThinking, AgentToolCall, AgentToolResult,
            AgentResponse, AgentError, ClearChat,
        )

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
            self.add_error(message.error, message.tool)
        elif isinstance(message, ClearChat):
            self.clear()
