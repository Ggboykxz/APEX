"""UI components for APEX - Premium terminal interface - Better than OpenCode."""

from typing import Any, Optional, List
from datetime import datetime
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table, Column
from rich.text import Text
from rich.style import Style, StyleType
from rich.box import Box, ROUNDED, SIMPLE_HEAVY, DOUBLE, HEAVY
from rich.columns import Columns
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.live import Live
from rich.console import ConsoleRenderable


class APEXTheme:
    """Premium color themes - Better than OpenCode."""
    
    # Dracula-inspired (default)
    DRACULA = {
        "bg": "#282A36",
        "fg": "#F8F8F2",
        "red": "#FF5555",
        "green": "#50FA7B",
        "yellow": "#F1FA8C",
        "orange": "#FFB86C",
        "purple": "#BD93F9",
        "cyan": "#8BE9FD",
        "pink": "#FF79C6",
        "white": "#F8F8F2",
        "gray": "#6272A4",
    }
    
    # Nord-inspired
    NORD = {
        "bg": "#2E3440",
        "fg": "#ECEFF4",
        "red": "#BF616A",
        "green": "#A3BE8C",
        "yellow": "#EBCB8B",
        "orange": "#D08770",
        "purple": "#B48EAD",
        "cyan": "#88C0D0",
        "pink": "#B48EAD",
        "white": "#ECEFF4",
        "gray": "#4C566A",
    }
    
    # One Dark
    ONE_DARK = {
        "bg": "#282C34",
        "fg": "#ABB2BF",
        "red": "#E06C75",
        "green": "#98C379",
        "yellow": "#E5C07B",
        "orange": "#D19A66",
        "purple": "#C678DD",
        "cyan": "#56B6C2",
        "pink": "#C678DD",
        "white": "#ABB2BF",
        "gray": "#5C6370",
    }
    
    @classmethod
    def get(cls, name: str = "dracula") -> dict:
        return getattr(cls, name.upper(), cls.DRACULA)


class UI:
    """Premium UI - Outperforms OpenCode."""
    
    def __init__(self, theme: str = "dracula"):
        self.console = Console()
        self.theme_name = theme
        self.theme = APEXTheme.get(theme)
        
        # Icons for different elements
        self.ICONS = {
            "agent": "🤖",
            "model": "🧠",
            "folder": "📁",
            "file": "📄",
            "git": "📊",
            "success": "✓",
            "error": "✗",
            "warning": "⚠",
            "info": "ℹ",
            "code": "⚡",
            "thinking": "💭",
            "tool": "🔧",
            "search": "🔍",
            "edit": "✏️",
            "delete": "🗑️",
            "create": "✨",
            "git_branch": "⎇",
            "git_add": "+",
            "git_mod": "~",
            "git_del": "-",
        }
    
    def _c(self, color: str, text: str, bold: bool = False) -> str:
        """Color helper."""
        style = f"bold {color}" if bold else color
        return f"[{style}]{text}[/{style}]"

    def _t(self, key: str) -> str:
        """Get themed color."""
        return self.theme.get(key, "white")

    def show_banner(self, model: str, cwd: str, agent: str = "build") -> None:
        """Show premium banner - Better than OpenCode."""
        bg = self._t("bg")
        cyan = self._c("cyan", "")
        orange = self._c("orange", "")
        green = self._c("green", "")
        dim = self._c("gray", "")
        
        # ASCII Logo
        logo = f"""
[cyan bold]  █████╗ ████████╗████████╗██████╗  ██████╗ ███████╗██╗     ███████╗[/]
[purple bold] ██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗██╔═══██╗██╔════╝██║     ██╔════╝[/]
[pink bold] ███████║   ██║   ██║   ██║██████╔╝██║   ██║███████╗██║     ███████╗[/]
[orange bold] ██╔══██║   ██║   ██║   ██║██╔══██╗██║   ██║╚════██║██║     ╚════██║[/]
[yellow bold] ██║  ██║   ██║   ╚██████╔╝██║  ██║╚██████╔╝███████║███████╗███████║[/]
[green bold] ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝╚══════╝[/]

[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]
{datetime.now().strftime('%Y-%m-%d')} [dim]│[/] {datetime.now().strftime('%H:%M:%S')} [dim]│[/] APEX v1.3.0"""
        
        # Status bar with agent badges
        status = Table(box=None, show_header=False, padding=(0, 2))
        
        # Agent badge
        agent_colors = {
            "build": "cyan",
            "plan": "yellow", 
            "explore": "green",
            "general": "magenta",
        }
        agent_color = agent_colors.get(agent, "cyan")
        
        status.add_row(
            f"{self._c(agent_color, self.ICONS['agent'])} {self._c(agent_color, f' {agent.upper()}', True)}  "
            f"{self._c('gray', '│')}  "
            f"{self._c('cyan', self.ICONS['model'])} {model}  "
            f"{self._c('gray', '│')}  "
            f"{self._c('green', self.ICONS['folder'])} {cwd}  "
            f"{self._c('gray', '│')}  "
            f"{self._c('purple', '⌨')} Tab=Agent ⌨ Ctrl+C=Exit"
        )
        
        self.console.print(Panel(logo, box=SIMPLE_HEAVY, style=f"on {bg}", padding=(1, 2)))
        self.console.print(Panel(status, box=SIMPLE_HEAVY, padding=(0, 1), border_style="cyan"))

    def show_help(self) -> None:
        """Show beautiful help - Better than OpenCode."""
        cyan = self._c("cyan", "")
        
        help_table = Table(
            title=f" {self.ICONS['info']} APEX Commands ",
            show_header=True,
            header_style="bold cyan",
            box=ROUNDED,
            padding=(0, 1),
        )
        
        commands = [
            (f"{cyan}/agent[cyan] [name]", "Switch agent (build/plan/explore/general)"),
            (f"{cyan}/agents", "List all agents"),
            (f"{cyan}/subagents", "Show subagents (@name to invoke)"),
            (f"{cyan}/model [name]", "Change AI model"),
            (f"{cyan}/models", "Browse 85+ models"),
            (f"{cyan}/cwd [path]", "Change directory"),
            (f"{cyan}/map", "Show repo structure"),
            (f"{cyan}/git", "Git status & branch"),
            (f"{cyan}/clear", "Clear history"),
            (f"{cyan}/save [name]", "Save session"),
            (f"{cyan}/load [name]", "Restore session"),
            (f"{cyan}/cost", "Token usage"),
            (f"{cyan}/help", "This help"),
            (f"{cyan}/exit", "Exit APEX"),
            (f"{cyan}@file.py", "Include file"),
            (f"{cyan}@agent task", "Invoke subagent"),
        ]
        
        for cmd, desc in commands:
            help_table.add_row(cmd, desc)
        
        self.console.print(help_table)
        
        # Keyboard shortcuts
        shortcuts = Table(box=None, show_header=False, padding=(1, 0))
        shortcuts.add_row(
            f"{self._c('gray', 'Shortcuts:')} "
            f"{self._c('cyan', 'Tab')} Cycle agents | "
            f"{self._c('cyan', '↑↓')} History | "
            f"{self._c('cyan', 'Ctrl+C')} Interrupt | "
            f"{self._c('cyan', 'Ctrl+L')} Clear"
        )
        self.console.print(shortcuts)

    def show_models(self, current: str) -> None:
        """Show models table - Better than OpenCode."""
        cyan = self._c("cyan", "")
        green = self._c("green", "")
        
        from .config import MODELS
        
        models_table = Table(
            title=f" {self.ICONS['model']} Available Models ",
            show_header=True,
            header_style="bold cyan",
            box=ROUNDED,
            padding=(0, 1),
        )
        models_table.add_column("Alias", style="cyan", width=22)
        models_table.add_column("Provider", style="dim", width=20)
        models_table.add_column("Status", width=12)
        
        for alias in sorted(MODELS.keys())[:25]:
            model_str = MODELS[alias]
            provider = model_str.split("/")[0] if "/" in model_str else "unknown"
            
            if alias == current:
                status = f"{green}● Active"
            elif "free" in alias.lower():
                status = f"{self._c('yellow', '○ Free')}"
            else:
                status = ""
            
            models_table.add_row(alias, provider, status)
        
        self.console.print(models_table)
        self.console.print(f"\n{self._c('dim', f'Showing 25 of {len(MODELS)} models. Use /models for full list.')}")

    def print_user(self, text: str) -> None:
        """Print user input - Better styling."""
        cyan = self._c("cyan", "")
        self.console.print(f"\n{cyan}›[›] {text}")

    def print_thinking(self, message: str = "Thinking") -> Any:
        """Premium thinking indicator."""
        cyan = self._c("cyan", "")
        return self.console.status(f"{cyan}{self.ICONS['thinking']} {message}...", spinner="dots", speed=0.7)

    def print_response(self, text: str) -> None:
        """Print response with code highlighting - Better than OpenCode."""
        cyan = self._c("cyan", "")
        purple = self._c("purple", "")
        
        if "```" in text:
            parts = text.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    if part.strip():
                        md = Markdown(part.strip())
                        self.console.print(md)
                else:
                    lines = part.split("\n", 1)
                    lang = lines[0].strip() if lines else ""
                    code = lines[1] if len(lines) > 1 else ""
                    if code:
                        syntax = Syntax(
                            code, 
                            lang or "python", 
                            theme="monokai", 
                            line_numbers=True,
                            padding=1,
                            indent_guides=True,
                        )
                        self.console.print(
                            Panel(
                                syntax,
                                title=f" {lang.upper() if lang else 'CODE'} ",
                                border_style="cyan",
                                box=ROUNDED,
                            )
                        )
        else:
            md = Markdown(text)
            self.console.print(md)

    def print_tool_call(self, name: str, args: dict[str, Any]) -> None:
        """Tool call display - Premium."""
        cyan = self._c("cyan", "")
        gray = self._c("gray", "")
        
        # Truncate args for display
        args_str = ", ".join(
            f"{gray}{k}{cyan}={self._c('white', str(v)[:30])}" 
            for k, v in list(args.items())[:3]
        )
        
        self.console.print(f"  {self._c('cyan', '▶')} {self._c('white', name)}({args_str}{self._c('gray', '...)' if len(args) > 3 else '')})")

    def print_tool_result(self, name: str, result: str) -> None:
        """Tool result - Better than OpenCode."""
        cyan = self._c("cyan", "")
        green = self._c("green", "")
        red = self._c("red", "")
        yellow = self._c("yellow", "")
        
        border_color = {
            "ERROR:": red,
            "SUCCESS:": green,
            "WARNING:": yellow,
        }.get(result.split(":")[0] if ":" in result else "", cyan)
        
        icon = {
            "ERROR:": "✗",
            "SUCCESS:": "✓", 
            "WARNING:": "⚠",
        }.get(result.split(":")[0] if ":" in result else "", "●")
        
        if len(result) > 2500:
            result = result[:2500] + f"\n{self._c('dim', f'... ({len(result)-2500} more chars)')}"
        
        self.console.print(
            Panel(
                result,
                title=f" {icon} {name} ",
                border_style=border_color,
                box=ROUNDED,
                padding=(0, 1),
            )
        )

    def print_error(self, message: str) -> None:
        red = self._c("red", "")
        self.console.print(f"\n  {red}✗ {message}")

    def print_success(self, message: str) -> None:
        green = self._c("green", "")
        self.console.print(f"\n  {green}✓ {message}")

    def print_warning(self, message: str) -> None:
        yellow = self._c("yellow", "")
        self.console.print(f"\n  {yellow}⚠ {message}")

    def print_info(self, message: str) -> None:
        gray = self._c("gray", "")
        self.console.print(f"  {gray}ℹ {message}")

    def print_separator(self) -> None:
        """Premium separator."""
        gray = self._c("gray", "")
        self.console.print(f"\n{gray}{'─' * 50}")

    def print_git_status(self, branch: str, status: str, files: List[str]) -> None:
        """Git status - Better than OpenCode."""
        cyan = self._c("cyan", "")
        green = self._c("green", "")
        gray = self._c("gray", "")
        
        branch_panel = Panel(
            f" {self._c('cyan', '⎇')} {branch} ",
            box=ROUNDED,
            border_style="cyan",
        )
        
        if files:
            files_text = "\n".join([
                f"  {gray}{f}[/{gray}]" 
                for f in files[:8]
            ])
            files_panel = Panel(
                files_text,
                title=f" {len(files)} changed ",
                box=ROUNDED,
                border_style="yellow",
            )
            self.console.print(Columns([branch_panel, files_panel], padding=1))
        else:
            clean = Panel(
                f" {green}✓ Clean ",
                box=ROUNDED,
                border_style="green",
            )
            self.console.print(Columns([branch_panel, clean], padding=1))

    def print_cost(self, usage: dict[str, int]) -> None:
        """Token cost display."""
        cyan = self._c("cyan", "")
        
        table = Table(
            title=f" {self.ICONS['code']} Token Usage ",
            show_header=True,
            header_style="bold cyan",
            box=ROUNDED,
        )
        table.add_column("Type", style="cyan")
        table.add_column("Tokens", justify="right", style="white")
        
        total = sum(usage.values())
        for token_type, count in usage.items():
            table.add_row(token_type, f"{count:,}")
        
        table.add_row(f"[bold]{cyan}Total[/]", f"[bold]{total:,}[/]")
        
        self.console.print(table)
        
        cost = total * 0.00001
        self.console.print(f"  {self._c('gray', f'Estimated: ~${cost:.4f}')}")

    def clear(self) -> None:
        """Clear screen with style."""
        self.console.clear()

    def print_welcome_message(self) -> None:
        """Welcome message - Better than OpenCode."""
        cyan = self._c("cyan", "")
        gray = self._c("gray", "")
        purple = self._c("purple", "")
        
        welcome = f"""
{gray}┌─────────────────────────────────────────────────────────────────────┐
│  {cyan}Welcome to APEX{gray}                                                       │
│  {gray}│                                                                     │
│  {gray}│  {purple}Type a prompt and press Enter to start coding{gray}                   │
│  {gray}│  {purple}Use /help to see all commands{gray}                                      │
│  {gray}│  {purple}Press Tab to cycle through agents{gray}                                  │
│  {gray}│  {purple}Press Ctrl+C to interrupt{gray}                                       │
│  {gray}└─────────────────────────────────────────────────────────────────────┘[/]"""
        
        self.console.print(welcome)


def create_ui(theme: str = "dracula") -> UI:
    """Create UI with theme."""
    return UI(theme)


def get_available_themes() -> List[str]:
    """List available themes."""
    return ["dracula", "nord", "one_dark"]