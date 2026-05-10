"""APEX TUI Widgets — OpenCode-inspired design with APEX theme.

Refonte: Complete widget system with all components.
"""

from .header import HeaderBar
from .sidebar import SidebarPane, FileTreeWidget, ToolLog, SidebarTabChanged
from .chat import ChatPane, ToolCard, ThinkingIndicator
from .input_bar import InputBar, UserMessage, CommandInput, MentionTrigger
from .status import StatusBar
from .cmd_palette import CommandPalette, PaletteCommand
from .dialogs import (
    HelpDialog,
    QuitDialog,
    ModelPickerDialog,
    ThemePickerDialog,
    SessionPickerDialog,
    PermissionDialog,
    FilePickerDialog,
    InitDialog,
    CompletionDialog,
)
from .messages import (
    AgentThinking,
    AgentToolCall,
    AgentToolResult,
    AgentResponse,
    AgentError,
    AgentStreamChunk,
    AgentStreamEnd,
    TokenUpdate,
    ContextUpdate,
    PageChange,
    ToggleSidebar,
    ModelChanged,
    ModelSelected,
    CwdChanged,
    ClearChat,
    FilePreviewRequest,
    FileSelected,
    ModeChanged,
    SidebarTabChanged,
    DialogDismissed,
    ThemeSelected,
    SessionSelected,
    PermissionResponse,
    QuitConfirmed,
    CompletionSelected,
    StatusInfo,
    StatusError,
    StatusWarning,
    ClearStatus,
    LSPDiagnostic,
)

__all__ = [
    # Core widgets
    "HeaderBar",
    "SidebarPane",
    "FileTreeWidget",
    "ToolLog",
    "ChatPane",
    "ToolCard",
    "ThinkingIndicator",
    "InputBar",
    "StatusBar",
    "CommandPalette",
    # Dialogs
    "HelpDialog",
    "QuitDialog",
    "ModelPickerDialog",
    "ThemePickerDialog",
    "SessionPickerDialog",
    "PermissionDialog",
    "FilePickerDialog",
    "InitDialog",
    "CompletionDialog",
    # Input messages
    "UserMessage",
    "CommandInput",
    "MentionTrigger",
    "PaletteCommand",
    "SidebarTabChanged",
    # Agent messages
    "AgentThinking",
    "AgentToolCall",
    "AgentToolResult",
    "AgentResponse",
    "AgentError",
    "AgentStreamChunk",
    "AgentStreamEnd",
    # UI messages
    "TokenUpdate",
    "ContextUpdate",
    "PageChange",
    "ToggleSidebar",
    "ModelChanged",
    "ModelSelected",
    "CwdChanged",
    "ClearChat",
    "FilePreviewRequest",
    "FileSelected",
    "ModeChanged",
    "DialogDismissed",
    "ThemeSelected",
    "SessionSelected",
    "PermissionResponse",
    "QuitConfirmed",
    "CompletionSelected",
    # Status messages
    "StatusInfo",
    "StatusError",
    "StatusWarning",
    "ClearStatus",
    "LSPDiagnostic",
]
