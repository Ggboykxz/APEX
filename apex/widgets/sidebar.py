"""SidebarPane - File explorer + Tool log."""

from textual.widgets import DirectoryTree, Static, Button
from textual.widget import Widget
from pathlib import Path
from datetime import datetime
from typing import Any

from .messages import AgentToolCall, AgentToolResult, FilePreviewRequest


class FileTreeWidget(Widget):
    def __init__(self, root_path: str = ".", **kwargs):
        super().__init__(**kwargs)
        self.root_path = Path(root_path)

    def compose(self):
        yield Static("📁 Files", classes="sidebar-section-title")
        yield Button("+", id="btn-refresh-tree", variant="default", classes="tree-refresh-btn")
        yield DirectoryTree(str(self.root_path), id="file-tree")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        file_path = str(event.path)
        self.post_message(FilePreviewRequest(file_path))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh-tree":
            tree = self.query_one("#file-tree", DirectoryTree)
            tree.refresh()


class ToolLogItem(Widget):
    def __init__(self, name: str, args: str = "", status: str = "pending", **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.args = args
        self.status = status

    def compose(self):
        icons = {"pending": "⟳", "running": "⟳", "success": "✓", "error": "✗"}
        icon = icons.get(self.status, "?")

        icon_el = Static(icon, classes=f"tool-log-icon {self.status}")
        name_el = Static(self.name, classes="tool-log-name")

        yield icon_el
        yield name_el


class ToolLog(Widget):
    tool_entries: list[dict[str, Any]] = []

    def compose(self):
        yield Static("🔧 Tool Log", classes="sidebar-section-title")
        yield Button("Clear", id="btn-clear-log", variant="default", classes="tool-log-clear")
        yield Static(id="tool-log-list")

    def add_tool_call(self, name: str, args: dict) -> None:
        entry = {
            "name": name,
            "args": str(args)[:30],
            "status": "running",
            "time": datetime.now().strftime("%H:%M"),
        }
        self.tool_entries.append(entry)
        self._refresh()

    def add_tool_result(self, name: str, result: str, success: bool) -> None:
        for entry in reversed(self.tool_entries):
            if entry["name"] == name and entry["status"] == "running":
                entry["status"] = "success" if success else "error"
                break
        self._refresh()

    def _refresh(self) -> None:
        container = self.query_one("#tool-log-list", Static)
        entries = self.tool_entries[-50:]
        lines = []
        for entry in entries:
            icons = {"pending": "⟳", "running": "⟳", "success": "✓", "error": "✗"}
            icon = icons.get(entry["status"], "?")
            lines.append(f"{icon} {entry['name']} {entry['time']}")
        container.update("\n".join(lines))

    def clear(self) -> None:
        self.tool_entries = []
        self._refresh()


class SidebarPane(Widget):
    def __init__(self, cwd: str = ".", **kwargs):
        super().__init__(**kwargs)
        self.cwd = cwd

    def compose(self):
        yield Static("EXPLORER", classes="sidebar-title")
        yield Button("+", id="btn-add-file", variant="default")
        yield FileTreeWidget(self.cwd, id="file-tree-container")
        yield ToolLog(id="tool-log-container")

    def on_message(self, message) -> None:
        
        tool_log = self.query_one(ToolLog)
        if isinstance(message, AgentToolCall):
            tool_log.add_tool_call(message.name, message.args)
        elif isinstance(message, AgentToolResult):
            tool_log.add_tool_result(message.name, message.result, message.success)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear-log":
            tool_log = self.query_one(ToolLog)
            tool_log.clear()

    def update_cwd(self, cwd: str) -> None:
        self.cwd = cwd
