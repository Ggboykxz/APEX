"""APEX TUI Messages — Inter-widget communication via Textual messages."""

from textual.message import Message


class AgentThinking(Message):
    """Agent is thinking (started processing)."""

    def __init__(self) -> None:
        super().__init__()


class AgentToolCall(Message):
    """Agent called a tool."""

    def __init__(self, name: str, args: dict) -> None:
        super().__init__()
        self.name = name
        self.args = args


class AgentToolResult(Message):
    """Tool execution completed."""

    def __init__(self, name: str, result: str, success: bool = True, duration: float = 0.0) -> None:
        super().__init__()
        self.name = name
        self.result = result
        self.success = success
        self.duration = duration


class AgentResponse(Message):
    """Agent responded with text."""

    def __init__(self, text: str, model: str) -> None:
        super().__init__()
        self.text = text
        self.model = model


class AgentError(Message):
    """Agent error occurred."""

    def __init__(self, error: str) -> None:
        super().__init__()
        self.error = error


class TokenUpdate(Message):
    """Token count or cost updated."""

    def __init__(self, count: int, cost: float) -> None:
        super().__init__()
        self.count = count
        self.cost = cost


class ToggleSidebar(Message):
    """Toggle sidebar visibility."""

    def __init__(self) -> None:
        super().__init__()


class ModelChanged(Message):
    """Model changed by user."""

    def __init__(self, model: str) -> None:
        super().__init__()
        self.model = model


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
