"""Toast component - Notification toasts like OpenCode's toast."""

from typing import Optional, Callable
from rich.panel import Panel
from rich.text import Text
from datetime import datetime
import threading


class Toast(BaseComponent):
    """Toast component - like OpenCode's Toast."""

    TYPES = ["info", "success", "warning", "error"]

    def __init__(
        self,
        message: str,
        toast_type: str = "info",
        duration: int = 3000,
        console=None
    ):
        super().__init__(console)
        self.message = message
        self.toast_type = toast_type if toast_type in self.TYPES else "info"
        self.duration = duration
        self.created_at = datetime.now()
        self._timer: Optional[threading.Timer] = None

    def render(self) -> Panel:
        type_colors = {
            "info": "cyan",
            "success": "green",
            "warning": "yellow",
            "error": "red"
        }
        color = type_colors.get(self.toast_type, "cyan")

        icon = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗"
        }.get(self.toast_type, "ℹ")

        content = Text.from_markup(f"[{color}]{icon}[/] {self.message}")

        border_style = color

        return Panel(
            content,
            border_style=border_style,
            padding=(0, 1),
            title=f"[dim]{self.toast_type.upper()}[/]",
            style="none"
        )

    def show_timed(self, callback: Optional[Callable] = None) -> None:
        self.show()
        self._timer = threading.Timer(self.duration / 1000, self._auto_hide, [callback])
        self._timer.start()

    def _auto_hide(self, callback: Optional[Callable] = None) -> None:
        self.hide()
        if callback:
            callback()

    def cancel(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def destroy(self) -> None:
        self.cancel()


class ToastManager:
    """Toast manager - manages multiple toasts."""

    def __init__(self, console=None):
        self.console = console or Console()
        self._toasts: list[Toast] = []
        self._max_toasts = 5

    def show(
        self,
        message: str,
        toast_type: str = "info",
        duration: int = 3000
    ) -> Toast:
        toast = Toast(message, toast_type, duration, self.console)
        toast.show_timed()

        self._toasts.append(toast)
        if len(self._toasts) > self._max_toasts:
            self._toasts.pop(0)

        return toast

    def info(self, message: str, duration: int = 3000) -> Toast:
        return self.show(message, "info", duration)

    def success(self, message: str, duration: int = 3000) -> Toast:
        return self.show(message, "success", duration)

    def warning(self, message: str, duration: int = 3000) -> Toast:
        return self.show(message, "warning", duration)

    def error(self, message: str, duration: int = 5000) -> Toast:
        return self.show(message, "error", duration)

    def clear(self) -> None:
        for toast in self._toasts:
            toast.destroy()
        self._toasts.clear()

    def render_all(self) -> list[Panel]:
        return [toast.render() for toast in self._toasts if toast.visible]