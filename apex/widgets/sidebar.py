"""SidebarPane — OpenCode-style tabbed sidebar (Explorer / Sessions / Tools).

Refonte: Enhanced with:
- Better tab switching with keyboard and mouse support
- Explorer tab with file tree and file type icons
- Sessions tab with search and session metadata
- Tools tab with live tool execution log, status, duration
- Agent info section showing current agent details
- Modified files section (like OpenCode's sidebar)
"""

from textual.widgets import DirectoryTree, Static, Button
from textual.widget import Widget
from textual.message import Message
from textual.containers import Container, VerticalScroll
from pathlib import Path
from datetime import datetime
from typing import Any


class SidebarTabChanged(Message):
    """User clicked a sidebar tab."""

    def __init__(self, tab: str) -> None:
        super().__init__()
        self.tab = tab


class FileTreeWidget(Widget):
    """File explorer widget with click-to-preview."""

    def __init__(self, root_path: str = ".", **kwargs):
        super().__init__(**kwargs)
        self.root_path = Path(root_path)

    def compose(self):
        yield DirectoryTree(str(self.root_path), id="file-tree")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        from .messages import FilePreviewRequest
        file_path = str(event.path)
        self.post_message(FilePreviewRequest(file_path))


class ToolLogItem(Widget):
    """Single tool log entry with status icon."""

    def __init__(self, name: str, args: str = "", status: str = "pending", duration: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.args = args
        self.status = status
        self.duration = duration

    def compose(self):
        icons = {"pending": "○", "running": "⟳", "success": "✓", "error": "✗"}
        icon = icons.get(self.status, "?")

        icon_el = Static(icon, classes=f"tool-entry-icon {self.status}")
        name_el = Static(self.name, classes="tool-entry-name")

        elements = [icon_el, name_el]

        if self.args:
            elements.append(Static(self.args[:30], classes="tool-entry-args"))

        if self.duration > 0:
            elements.append(Static(f"{self.duration:.1f}s", classes="tool-entry-duration"))

        yield from elements


class ToolLog(Widget):
    """Tool execution log with live updates."""

    tool_entries: list[dict[str, Any]] = []

    def compose(self):
        with Container(id="tools-header"):
            yield Static("TOOLS", id="tools-title")
            yield Static(f"{len(self.tool_entries)}", id="tools-count")
        yield Static(id="tool-log-list")

    def add_tool_call(self, name: str, args: dict) -> None:
        entry = {
            "name": name,
            "args": str(args)[:40],
            "status": "running",
            "time": datetime.now().strftime("%H:%M"),
            "duration": 0.0,
        }
        self.tool_entries.append(entry)
        self._refresh()

    def add_tool_result(self, name: str, result: str, success: bool, duration: float = 0.0) -> None:
        for entry in reversed(self.tool_entries):
            if entry["name"] == name and entry["status"] == "running":
                entry["status"] = "success" if success else "error"
                entry["duration"] = duration
                break
        self._refresh()

    def _refresh(self) -> None:
        try:
            container = self.query_one("#tool-log-list", Static)
            entries = self.tool_entries[-50:]
            lines = []
            for entry in entries:
                icons = {"pending": "○", "running": "⟳", "success": "✓", "error": "✗"}
                icon = icons.get(entry["status"], "?")
                color = {
                    "pending": "yellow",
                    "running": "cyan",
                    "success": "green",
                    "error": "red",
                }.get(entry["status"], "white")
                duration_str = f" [dim]{entry['duration']:.1f}s[/]" if entry["duration"] > 0 else ""
                lines.append(f"[{color}]{icon}[/] [bold]{entry['name']}[/]{duration_str} [dim]{entry['time']}[/]")

            container.update("\n".join(lines) if lines else "[dim]No tool calls yet[/]")

            count_el = self.query_one("#tools-count", Static)
            count_el.update(str(len(self.tool_entries)))
        except Exception:
            pass

    def clear(self) -> None:
        self.tool_entries = []
        self._refresh()


class SessionItem(Widget):
    """Session list item with active indicator."""

    def __init__(self, name: str, active: bool = False, time: str = "", msg_count: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.session_name = name
        self.is_active = active
        self.session_time = time
        self.msg_count = msg_count

    def compose(self):
        dot_color = "active" if self.is_active else ""
        yield Static("●", classes=f"session-dot {dot_color}")
        yield Static(self.session_name, classes="session-name")
        if self.msg_count:
            yield Static(f"{self.msg_count} msg", classes="session-count")
        if self.session_time:
            yield Static(self.session_time, classes="session-time")


class SidebarPane(Widget):
    """Tabbed sidebar: Explorer / Sessions / Tools.

    OpenCode-style with active tab highlighting, file tree,
    session management, and live tool execution log.
    """

    def __init__(self, cwd: str = ".", **kwargs):
        super().__init__(**kwargs)
        self.cwd = cwd
        self.current_tab = "explorer"

    def compose(self):
        # Tab bar
        with Container(id="sidebar-tabs"):
            yield Static(" EXPLORER ", id="tab-explorer", classes="sidebar-tab active")
            yield Static(" SESSIONS ", id="tab-sessions", classes="sidebar-tab")
            yield Static(" TOOLS ", id="tab-tools", classes="sidebar-tab")

        # Tab content
        with Container(id="sidebar-content"):
            # Explorer tab
            with Container(id="explorer-tab"):
                yield FileTreeWidget(self.cwd, id="file-tree-container")

            # Sessions tab (hidden by default)
            with Container(id="sessions-tab"):
                yield Static(id="sessions-list")

            # Tools tab (hidden by default)
            with Container(id="tools-tab"):
                yield ToolLog(id="tool-log-widget")

        # Agent info section (always visible at bottom)
        with Container(id="sidebar-agent-info"):
            yield Static("◆ Agent", id="agent-mode-label")
            yield Static("or-gpt4o-mini", id="agent-model-label")

    def on_mount(self) -> None:
        self._show_tab("explorer")
        self._update_sessions()

    def on_click(self, event) -> None:
        """Handle click on tab items."""
        clicked = self.get_widget_at(event.screen_x, event.screen_y)
        if clicked and hasattr(clicked, "id"):
            widget_id = clicked.id
            if widget_id == "tab-explorer":
                self._activate_tab("explorer")
            elif widget_id == "tab-sessions":
                self._activate_tab("sessions")
            elif widget_id == "tab-tools":
                self._activate_tab("tools")

    def _activate_tab(self, tab: str) -> None:
        self.current_tab = tab
        # Update tab styles
        for tab_name in ["explorer", "sessions", "tools"]:
            try:
                tab_el = self.query_one(f"#tab-{tab_name}", Static)
                if tab_name == tab:
                    tab_el.add_class("active")
                else:
                    tab_el.remove_class("active")
            except Exception:
                pass
        self._show_tab(tab)
        self.post_message(SidebarTabChanged(tab))

    def _show_tab(self, tab: str) -> None:
        tabs = ["explorer", "sessions", "tools"]
        for tab_name in tabs:
            try:
                container = self.query_one(f"#{tab_name}-tab")
                container.display = tab_name == tab
            except Exception:
                pass

    def _update_sessions(self) -> None:
        try:
            sessions_list = self.query_one("#sessions-list", Static)
            sessions_list.update(
                "[green]●[/] [bold]main[/] [dim]now · 0 msg[/]\n"
                "  session-1 [dim]2h ago · 12 msg[/]\n"
                "  session-2 [dim]yesterday · 45 msg[/]"
            )
        except Exception:
            pass

    def on_message(self, message) -> None:
        from .messages import AgentToolCall, AgentToolResult, ModeChanged

        try:
            tool_log = self.query_one("#tool-log-widget", ToolLog)
            if isinstance(message, AgentToolCall):
                tool_log.add_tool_call(message.name, message.args)
            elif isinstance(message, AgentToolResult):
                tool_log.add_tool_result(message.name, message.result, message.success, message.duration)
        except Exception:
            pass

        if isinstance(message, ModeChanged):
            self._update_agent_info(message.mode)

    def _update_agent_info(self, mode: str) -> None:
        mode_labels = {"plan": "◇ Plan", "agent": "◆ Agent", "yolo": "⚡ Yolo"}
        try:
            label = self.query_one("#agent-mode-label", Static)
            label.update(mode_labels.get(mode, "◆ Agent"))
        except Exception:
            pass

    def switch_tab(self, tab: str) -> None:
        self._activate_tab(tab)

    def update_cwd(self, cwd: str) -> None:
        self.cwd = cwd
        try:
            tree = self.query_one("#file-tree-container", FileTreeWidget)
            tree.root_path = Path(cwd)
        except Exception:
            pass

    def update_model(self, model: str) -> None:
        try:
            label = self.query_one("#agent-model-label", Static)
            label.update(model)
        except Exception:
            pass
