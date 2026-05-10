"""Components package - UI components like OpenCode's components."""

from .base import BaseComponent
from .dialog import Dialog, Dialog
from .toast import Toast, ToastManager
from .status_bar import StatusBar
from .command_palette import CommandPalette

__all__ = [
    "BaseComponent",
    "Dialog",
    "Toast",
    "ToastManager",
    "StatusBar",
    "CommandPalette",
]