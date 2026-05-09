"""Textual TUI for APEX - Like OpenCode but better."""

import asyncio
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, Input, Label, 
    RichLog, DataTable, Tree, ListView, ListItem,
    Markdown, TextArea, LoadingIndicator
)
from textual.widget import Widget
from textual import work
from textual.binding import Binding


# APEX Theme - Better than OpenCode (built-in themes)
# Textual will use the default dark theme with custom CSS colors


class AgentBadge(Static):
    """Agent indicator widget."""
    
    def __init__(self, agent: str = "build", **kwargs):
        super().__init__(**kwargs)
        self.agent = agent
    
    def compose(self) -> ComposeResult:
        colors = {
            "build": "cyan",
            "plan": "yellow",
            "explore": "green",
            "general": "magenta",
        }
        color = colors.get(self.agent, "cyan")
        yield Static(
            f"[{color} bold]🤖 {self.agent.upper()}[/]",
            classes="agent-badge"
        )


class ModelBadge(Static):
    """Model indicator widget."""
    
    def __init__(self, model: str = "or-gpt4o-mini", **kwargs):
        super().__init__(**kwargs)
        self.model = model
    
    def compose(self) -> ComposeResult:
        yield Static(
            f"[cyan bold]🧠 {self.model}[/]",
            classes="model-badge"
        )


class StatusBar(Static):
    """Bottom status bar - Like OpenCode."""
    
    def __init__(self, cwd: str = ".", **kwargs):
        super().__init__(**kwargs)
        self.cwd = cwd
    
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static(f"[green]📁 {self.cwd}[/]", classes="cwd"),
            Static("[dim]│[/]", classes="separator"),
            Static("[cyan]Tab=Agent[/]", classes="hint"),
            Static("[dim]│[/]", classes="separator"),
            Static("[cyan]Ctrl+C=Exit[/]", classes="hint"),
            classes="status-bar"
        )


class MessageContainer(ScrollableContainer):
    """Chat messages container - Like OpenCode."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages: list[str] = []
    
    def add_user_message(self, text: str) -> None:
        """Add user message."""
        self.messages.append(f"[cyan bold]›[/] [bold]{text}[/bold]")
        self.refresh()
    
    def add_ai_message(self, text: str) -> None:
        """Add AI response."""
        self.messages.append(text)
        self.refresh()
    
    def add_tool_call(self, name: str, args: dict) -> None:
        """Add tool call."""
        args_str = ", ".join(f"[dim]{k}[/]=[white]{v}[/]" for k, v in list(args.items())[:2])
        self.messages.append(f"  [cyan]⚡[/] [bold magenta]{name}[/]([white]{args_str}[/])")
        self.refresh()
    
    def add_tool_result(self, name: str, result: str, success: bool = True) -> None:
        """Add tool result."""
        color = "green" if success else "red"
        icon = "✓" if success else "✗"
        if len(result) > 500:
            result = result[:500] + "..."
        msg = f"  [{color}]{icon}[/] [bold {color}]{name}[/]: {result}"
        self.messages.append(msg)
        self.refresh()
    
    def compose(self) -> ComposeResult:
        yield Vertical(
            *[Static(m, markup=True) for m in self.messages],
            id="messages"
        )


class InputBar(Static):
    """Input bar - Like OpenCode."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static("[cyan bold]›[/] ", classes="prompt"),
            Input(placeholder="Type your message...", classes="input-field"),
            classes="input-bar"
        )


class SidePanel(Vertical):
    """Side panel - Like OpenCode's agent info."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]Files[/]", classes="panel-title")
        yield Tree("Root", classes="file-tree")
        yield Static("[bold cyan]Tools[/]", classes="panel-title")
        yield ListView(
            ListItem(Static("📄 read_file")),
            ListItem(Static("✏️ write_file")),
            ListItem(Static("🔧 run_command")),
            ListItem(Static("📊 git")),
            ListItem(Static("🔍 search")),
            ListItem(Static("🌐 web_search")),
            ListItem(Static("🧪 run_tests")),
        )


class APEXTUI(App):
    """APEX Textual TUI - Better than OpenCode!"""
    
    CSS = """
    /* Main Layout - Like OpenCode */
    Screen {
        layout: grid;
        grid-size: 1 3;
        grid-rows: 1fr 0fr 3fr;
    }
    
    /* Header */
    #header {
        height: auto;
        background: $surface;
        padding: 1;
    }
    
    /* Logo */
    .logo {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    
    /* Status Bar */
    .status-bar {
        height: 3;
        background: $surface;
        padding: 0 1;
    }
    
    .cwd, .hint, .separator {
        margin-right: 1;
    }
    
    .separator {
        color: $text-muted;
    }
    
    /* Main Content */
    #main {
        layout: grid;
        grid-size: 3 1;
        grid-columns: 1fr 3fr 1fr;
    }
    
    /* Side Panels */
    #left-panel, #right-panel {
        background: $surface;
        padding: 1;
    }
    
    .panel-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    
    .file-tree {
        height: 40%;
    }
    
    /* Center - Chat */
    #chat {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr auto;
    }
    
    #messages {
        background: $background;
        padding: 1;
        overflow-y: scroll;
    }
    
    .user-message {
        color: $primary;
        margin-bottom: 1;
    }
    
    .ai-message {
        color: $text;
        margin-bottom: 2;
    }
    
    .tool-call {
        color: $accent;
        margin-bottom: 1;
    }
    
    .tool-result {
        margin-bottom: 2;
    }
    
    /* Input Bar */
    #input-area {
        height: auto;
        background: $surface;
        padding: 1;
    }
    
    .input-bar {
        height: 3;
    }
    
    .prompt {
        width: 3;
    }
    
    Input {
        width: 100%;
    }
    
    /* Tool Panel */
    #tools-panel {
        background: $surface;
        padding: 1;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Exit", show=False),
        Binding("ctrl+l", "clear", "Clear", show=False),
        Binding("tab", "cycle_agent", "Agent", show=False),
        Binding("ctrl+k", "command_palette", "Commands", show=True),
    ]
    
    def __init__(
        self,
        model: str = "or-gpt4o-mini",
        cwd: str = ".",
        agent: str = "build",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.model = model
        self.cwd = cwd
        self.current_agent = agent
    
    def compose(self) -> ComposeResult:
        """Create the layout - Like OpenCode."""
        # Header with logo and status
        yield Container(
            Static(
                """
[cyan bold]   █████╗ ████████╗████████╗██████╗  ██████╗ ███████╗██╗     ███████╗[/]
[purple bold]  ██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗██╔═══██╗██╔════╝██║     ██╔════╝[/]
[pink bold]    ███████║   ██║   ██║   ██║██████╔╝██║   ██║███████╗██║     ███████║[/]
[orange bold]  ██╔══██║   ██║   ██║   ██║██╔══██╗██║   ██║╚════██║██║     ╚════██║[/]
[yellow bold]  ██║  ██║   ██║   ╚██████╔╝██║  ██║╚██████╔╝███████║███████╗███████║[/]
[green bold]   ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝╚══════╝[/]
                """,
                markup=True,
                classes="logo"
            ),
            Horizontal(
                Static(f"[bold cyan]🤖 {self.current_agent.upper()}[/]", id="agent-badge"),
                Static("[dim]│[/]"),
                Static(f"[cyan]🧠 {self.model}[/]", id="model-badge"),
                Static("[dim]│[/]"),
                Static(f"[green]📁 {self.cwd}[/]"),
            ),
            id="header"
        )
        
        # Main content area - 3 columns
        with Container(id="main"):
            # Left panel - Files
            with Vertical(id="left-panel"):
                yield Static("[bold cyan]📁 Files[/]", classes="panel-title")
                yield Tree(".", classes="file-tree")
            
            # Center - Chat
            with Vertical(id="chat"):
                yield ScrollableContainer(
                    RichLog(id="chat-log", markup=True),
                    id="messages"
                )
                yield Container(
                    Horizontal(
                        Static("[cyan bold]›[/] ", classes="prompt"),
                        Input(placeholder="Type your message... (Enter to send)", id="input"),
                    ),
                    id="input-area"
                )
            
            # Right panel - Tools
            with Vertical(id="right-panel"):
                yield Static("[bold cyan]🔧 Tools[/]", classes="panel-title")
                yield ListView(
                    ListItem(Static("📄 read_file")),
                    ListItem(Static("✏️ write_file")),
                    ListItem(Static("📝 edit_file")),
                    ListItem(Static("🔧 run_command")),
                    ListItem(Static("📊 git status")),
                    ListItem(Static("🔍 search")),
                    ListItem(Static("🌐 web_search")),
                    ListItem(Static("🧪 run_tests")),
                )
        
        # Status bar
        yield Container(
            Horizontal(
                Static(f"[green]📁 {self.cwd}[/]"),
                Static("[dim]│[/]", classes="sep"),
                Static("[cyan]Tab[/] agent"),
                Static("[dim]│[/]", classes="sep"),
                Static("[cyan]↑↓[/] history"),
                Static("[dim]│[/]", classes="sep"),
                Static("[cyan]Ctrl+L[/] clear"),
            ),
            classes="status-bar"
        )
    
    def on_mount(self) -> None:
        """Initialize the app."""
        self.title = "APEX - Terminal AI Coding Agent"
        self.sub_title = f"Model: {self.model} | Agent: {self.current_agent}"
        
        # Add welcome message
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(
            f"[cyan bold]Welcome to APEX![/]\n\n"
            f"[dim]Type your message and press Enter to start coding.[/]\n"
            f"[dim]Use /help for commands, Tab to cycle agents.[/]\n"
        )
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input."""
        if not event.value.strip():
            return
        
        chat_log = self.query_one("#chat-log", RichLog)
        input_field = self.query_one("#input", Input)
        
        # Show user message
        chat_log.write(f"\n[cyan bold]›[/] [bold]{event.value}[/]\n")
        
        # Clear input
        input_field.value = ""
        
        # Show thinking
        chat_log.write("[dim]💭 Thinking...[/]\n")
        
        # Process with AI (placeholder)
        chat_log.write(f"\n[white]{event.value}[/]\n")
    
    def action_cycle_agent(self) -> None:
        """Cycle through agents."""
        agents = ["build", "plan", "explore", "general"]
        current_idx = agents.index(self.current_agent)
        self.current_agent = agents[(current_idx + 1) % len(agents)]
        
        badge = self.query_one("#agent-badge", Static)
        badge.update(f"[bold cyan]🤖 {self.current_agent.upper()}[/]")
        
        self.sub_title = f"Model: {self.model} | Agent: {self.current_agent}"
    
    def action_clear(self) -> None:
        """Clear chat."""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.clear()
    
    def action_quit(self) -> None:
        """Quit the app."""
        self.exit()


def run_apex_tui(model: str = "or-gpt4o-mini", cwd: str = ".") -> None:
    """Run APEX TUI."""
    app = APEXTUI(model=model, cwd=cwd)
    app.run()


if __name__ == "__main__":
    run_apex_tui()