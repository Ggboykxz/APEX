"""APEX TUI Messages — Inter-widget communication via Textual messages.

Refonte: Complete message system matching OpenCode's event architecture.
All messages are typed and carry structured payloads.
"""

from textual.message import Message
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Agent Events ──────────────────────────────────────────────────────────────

class AgentThinking(Message):
    """Agent is processing a request."""

    def __init__(self, task: str = "") -> None:
        super().__init__()
        self.task = task


class AgentToolCall(Message):
    """Agent called a tool."""

    def __init__(self, name: str, args: dict, tool_id: str = "") -> None:
        super().__init__()
        self.name = name
        self.args = args
        self.tool_id = tool_id or name


class AgentToolResult(Message):
    """Tool execution completed."""

    def __init__(
        self,
        name: str,
        result: str,
        success: bool = True,
        duration: float = 0.0,
        tool_id: str = "",
    ) -> None:
        super().__init__()
        self.name = name
        self.result = result
        self.success = success
        self.duration = duration
        self.tool_id = tool_id or name


class AgentResponse(Message):
    """Agent responded with text."""

    def __init__(self, text: str, model: str = "") -> None:
        super().__init__()
        self.text = text
        self.model = model


class AgentError(Message):
    """Agent error occurred."""

    def __init__(self, error: str, tool: str = "") -> None:
        super().__init__()
        self.error = error
        self.tool = tool


class AgentStreamChunk(Message):
    """Streaming token chunk from the agent."""

    def __init__(self, token: str) -> None:
        super().__init__()
        self.token = token


class AgentStreamEnd(Message):
    """Streaming response completed."""

    def __init__(self, full_text: str, model: str = "") -> None:
        super().__init__()
        self.full_text = full_text
        self.model = model


# ── Token & Cost ─────────────────────────────────────────────────────────────

class TokenUpdate(Message):
    """Token count or cost updated."""

    def __init__(self, prompt_tokens: int = 0, completion_tokens: int = 0,
                 total_tokens: int = 0, cost: float = 0.0) -> None:
        super().__init__()
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.cost = cost


class ContextUpdate(Message):
    """Context window usage updated."""

    def __init__(self, used: int, total: int, percentage: float = 0.0) -> None:
        super().__init__()
        self.used = used
        self.total = total
        self.percentage = percentage


# ── Navigation & UI ──────────────────────────────────────────────────────────

class PageChange(Message):
    """Navigate to a different page (chat, logs)."""

    def __init__(self, page: str) -> None:
        super().__init__()
        self.page = page


class ToggleSidebar(Message):
    """Toggle sidebar visibility."""

    def __init__(self) -> None:
        super().__init__()


class ModelChanged(Message):
    """Model changed by user."""

    def __init__(self, model: str, provider: str = "") -> None:
        super().__init__()
        self.model = model
        self.provider = provider


class CwdChanged(Message):
    """Working directory changed."""

    def __init__(self, cwd: str) -> None:
        super().__init__()
        self.cwd = cwd


class ClearChat(Message):
    """Clear all chat messages."""

    def __init__(self) -> None:
        super().__init__()


class FilePreviewRequest(Message):
    """Request to preview a file in the chat."""

    def __init__(self, file_path: str) -> None:
        super().__init__()
        self.file_path = file_path


class ModeChanged(Message):
    """Agent mode changed (plan/agent/yolo)."""

    def __init__(self, mode: str) -> None:
        super().__init__()
        self.mode = mode


class SidebarTabChanged(Message):
    """Sidebar tab changed."""

    def __init__(self, tab: str) -> None:
        super().__init__()
        self.tab = tab


# ── Dialog Results ───────────────────────────────────────────────────────────

class DialogDismissed(Message):
    """A dialog was dismissed without selection."""

    def __init__(self, dialog_type: str = "") -> None:
        super().__init__()
        self.dialog_type = dialog_type


class ModelSelected(Message):
    """User selected a model from the model picker."""

    def __init__(self, model: str, provider: str = "") -> None:
        super().__init__()
        self.model = model
        self.provider = provider


class ThemeSelected(Message):
    """User selected a theme from the theme picker."""

    def __init__(self, theme: str) -> None:
        super().__init__()
        self.theme = theme


class SessionSelected(Message):
    """User selected a session from the session picker."""

    def __init__(self, session_id: str, session_name: str = "") -> None:
        super().__init__()
        self.session_id = session_id
        self.session_name = session_name


class PermissionResponse(Message):
    """User responded to a permission request."""

    def __init__(self, tool: str, action: str = "deny") -> None:
        super().__init__()
        self.tool = tool
        self.action = action  # "allow", "allow_session", "deny"


class QuitConfirmed(Message):
    """User confirmed quit."""

    def __init__(self) -> None:
        super().__init__()


class FileSelected(Message):
    """User selected a file from the file picker."""

    def __init__(self, file_path: str) -> None:
        super().__init__()
        self.file_path = file_path


class CompletionSelected(Message):
    """User selected a completion from @-mention dialog."""

    def __init__(self, search_string: str, completion_value: str) -> None:
        super().__init__()
        self.search_string = search_string
        self.completion_value = completion_value


# ── Status Bar ───────────────────────────────────────────────────────────────

class StatusInfo(Message):
    """Status bar info notification."""

    def __init__(self, msg: str, ttl: float = 3.0) -> None:
        super().__init__()
        self.msg = msg
        self.ttl = ttl


class StatusError(Message):
    """Status bar error notification."""

    def __init__(self, msg: str, ttl: float = 5.0) -> None:
        super().__init__()
        self.msg = msg
        self.ttl = ttl


class StatusWarning(Message):
    """Status bar warning notification."""

    def __init__(self, msg: str, ttl: float = 4.0) -> None:
        super().__init__()
        self.msg = msg
        self.ttl = ttl


class ClearStatus(Message):
    """Clear status bar notification."""

    def __init__(self) -> None:
        super().__init__()


# ── LSP ──────────────────────────────────────────────────────────────────────

class LSPDiagnostic(Message):
    """LSP diagnostic notification."""

    def __init__(self, count: int, errors: int = 0, warnings: int = 0) -> None:
        super().__init__()
        self.count = count
        self.errors = errors
        self.warnings = warnings
