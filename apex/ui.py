"""UI components for APEX - Rich-based terminal interface - PRO design."""

from typing import Any, Optional
from datetime import datetime

from rich.console import Console, ConsoleOptions, RenderResult
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich.style import Style
from rich.box import Box, ROUNDED, SIMPLE_HEAVY, SIMPLE
from rich.columns import Columns
from rich.align import Align


class UI:
    def __init__(self, color_scheme: Optional[str] = None):
        self.console = Console()
        self._scheme = color_scheme or "default"
        
        # Color schemes
        self._color_schemes = {
            "default": {
                "primary": "cyan",
                "secondary": "blue",
                "accent": "magenta",
                "success": "green",
                "warning": "yellow",
                "error": "red",
                "text": "white",
                "dim": "dim",
                "highlight": "bold white",
            },
            "ocean": {
                "primary": "#00D9FF",
                "secondary": "#0099CC",
                "accent": "#FF6B6B",
                "success": "#51CF66",
                "warning": "#FCC419",
                "error": "#FF6B6B",
                "text": "white",
                "dim": "dim white",
                "highlight": "bold cyan",
            },
            "sunset": {
                "primary": "#FF922B",
                "secondary": "#FF6B6B",
                "accent": "#CC5DE8",
                "success": "#51CF66",
                "warning": "#FCC419",
                "error": "#FF6B6B",
                "text": "white",
                "dim": "dim white",
                "highlight": "bold yellow",
            },
        }
        
        self.colors = self._color_schemes[self._scheme]

    def _get(self, key: str) -> str:
        return self.colors.get(key, "cyan")

    def show_banner(self, model: str, cwd: str, agent: str = "build") -> None:
        primary = self._get("primary")
        accent = self._get("accent")
        dim = self._get("dim")
        
        # ASCII Art Logo
        logo = f"""
[bold {primary}]
   █████╗ ████████╗████████╗██████╗  ██████╗ ███████╗██╗     ███████╗
  ██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗██╔═══██╗██╔════╝██║     ██╔════╝
  ███████║   ██║   ██║   ██║██████╔╝██║   ██║███████╗██║     ███████╗
  ██╔══██║   ██║   ██║   ██║██╔══██╗██║   ██║╚════██║██║     ╚════██║
  ██║  ██║   ██║   ╚██████╔╝██║  ██║╚██████╔╝███████║███████╗███████║
  ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝╚══════╝
[/bold {primary}]"""
        
        # Status bar
        status = Table(box=None, show_header=False, padding=0)
        status.add_column(justify="left")
        status.add_row(
            f"[{dim}]Agent:[/{dim}] [{primary}]{agent}[/{primary}]  "
            f"[{dim}]Model:[/{dim}] [{primary}]{model}[/{primary}]  "
            f"[{dim}]Dir:[/{dim}] [{primary}]{cwd}[/{primary}]  "
            f"[{dim}]Time:[/{dim}] [{primary}]{datetime.now().strftime('%H:%M')}[/{primary}]"
        )
        
        self.console.print(logo)
        self.console.print(Panel(status, box=SIMPLE_HEAVY, padding=(0, 1), style="on black"))

    def show_help(self) -> None:
        primary = self._get("primary")
        dim = self._get("dim")
        
        help_table = Table(
            title=f"[{primary}]●[/] APEX Commands",
            show_header=True,
            header_style=f"bold {primary}",
            box=ROUNDED,
            padding=(0, 1),
        )
        help_table.add_column("Command", style=primary, width=18)
        help_table.add_column("Description", style="white")
        
        commands = [
            ("/agent [name]", "Switch between agents (build/plan/explore)"),
            ("/agents", "List all available agents"),
            ("/subagents", "Show subagents (@name to invoke)"),
            ("/model <alias>", "Change the AI model"),
            ("/models", "Browse all 85+ available models"),
            ("/cwd <path>", "Change working directory"),
            ("/map", "Show repository structure"),
            ("/git", "Display git status and branch"),
            ("/clear", "Clear conversation history"),
            ("/save [name]", "Save current session"),
            ("/load <name]", "Restore saved session"),
            ("/cost", "Show token usage and costs"),
            ("/help", "Display this help"),
            ("/exit", "Exit APEX"),
            ("@file.py", "Include file in context"),
            ("@agent task", "Invoke subagent"),
        ]
        
        for cmd, desc in commands:
            help_table.add_row(f"[{primary}]{cmd}[/{primary}]", desc)
        
        self.console.print(help_table)

    def show_models(self, current: str) -> None:
        from .config import MODELS
        
        primary = self._get("primary")
        success = self._get("success")
        
        models_table = Table(
            title=f"[{primary}]●[/] Available Models",
            show_header=True,
            header_style=f"bold {primary}",
            box=ROUNDED,
            padding=(0, 1),
        )
        models_table.add_column("Alias", style=primary, width=20)
        models_table.add_column("Provider", style="dim", width=25)
        models_table.add_column("Status", style=success, width=8)
        
        for alias in sorted(MODELS.keys())[:30]:
            model_str = MODELS[alias]
            # Extract provider
            if "/" in model_str:
                provider = model_str.split("/")[0]
            else:
                provider = "unknown"
            
            marker = "[{success}]● Active[/{success}]" if alias == current else ""
            models_table.add_row(alias, provider, marker)
        
        self.console.print(models_table)
        self.console.print(f"\n[dim]Showing 30 of {len(MODELS)} models. Use /models to see all.[/dim]")

    def print_user(self, text: str) -> None:
        primary = self._get("primary")
        self.console.print(f"[{primary}]›[/{primary}] [bold]{text}[/bold]")

    def print_thinking(self, message: str = "Thinking") -> None:
        primary = self._get("primary")
        return self.console.status(f"[{primary}]{message}...[/]", spinner="dots", speed=0.8)

    def print_response(self, text: str) -> None:
        primary = self._get("primary")
        
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
                        syntax = Syntax(code, lang or "python", theme="monokai", line_numbers=True, padding=1)
                        self.console.print(Panel(syntax, border_style=primary, box=ROUNDED))
        else:
            md = Markdown(text)
            self.console.print(md)

    def print_tool_call(self, name: str, args: dict[str, Any]) -> None:
        primary = self._get("primary")
        dim = self._get("dim")
        
        # Create a nice tool call display
        tool_name = f"[bold {primary}]{name}[/bold]"
        
        args_parts = []
        for k, v in args.items():
            v_str = str(v)[:40] + "..." if len(str(v)) > 40 else str(v)
            args_parts.append(f"[{dim}]{k}[/{dim}]=[{primary}]{v_str}[/{primary}]")
        
        args_str = ", ".join(args_parts) if args_parts else ""
        
        self.console.print(f"  [{primary}]⚡[/] {tool_name}({args_str})")

    def print_tool_result(self, name: str, result: str) -> None:
        primary = self._get("primary")
        success = self._get("success")
        error = self._get("error")
        warning = self._get("warning")
        
        if result.startswith("ERROR:"):
            self.console.print(
                Panel(
                    result,
                    title=f"[{error}]✗ {name}[/]",
                    border_style=error,
                    box=ROUNDED,
                )
            )
        elif result.startswith("SUCCESS:"):
            self.console.print(
                Panel(
                    result,
                    title=f"[{success}]✓ {name}[/]",
                    border_style=success,
                    box=ROUNDED,
                )
            )
        elif result.startswith("WARNING:"):
            self.console.print(
                Panel(
                    result,
                    title=f"[{warning}]⚠ {name}[/]",
                    border_style=warning,
                    box=ROUNDED,
                )
            )
        else:
            if len(result) > 2000:
                result = result[:2000] + f"\n[{self._get('dim')}]({len(result) - 2000} more characters)[/]"
            self.console.print(
                Panel(
                    result,
                    title=f"[{primary}]● {name}[/]",
                    border_style=primary,
                    box=ROUNDED,
                    padding=(0, 1),
                )
            )

    def print_error(self, message: str) -> None:
        error = self._get("error")
        self.console.print(f"[{error}]✗[/{error}] [bold]{message}[/bold]")

    def print_success(self, message: str) -> None:
        success = self._get("success")
        self.console.print(f"[{success}]✓[/{success}] [bold]{message}[/bold]")

    def print_warning(self, message: str) -> None:
        warning = self._get("warning")
        self.console.print(f"[{warning}]⚠[/{warning}] {message}")

    def print_info(self, message: str) -> None:
        dim = self._get("dim")
        self.console.print(f"[{dim}]ℹ[/{dim}] {message}")

    def print_cost(self, usage: dict[str, int]) -> None:
        primary = self._get("primary")
        dim = self._get("dim")
        
        table = Table(
            title=f"[{primary}]●[/] Token Usage",
            show_header=True,
            header_style=f"bold {primary}",
            box=ROUNDED,
        )
        table.add_column("Type", style=primary)
        table.add_column("Tokens", style="white", justify="right")
        
        total = sum(usage.values())
        for token_type, count in usage.items():
            table.add_row(token_type, f"{count:,}")
        
        table.add_row(f"[bold]{primary}[/bold]", f"[bold]{total:,}[/bold]")
        
        self.console.print(table)
        
        # Cost estimation (approximate)
        cost = total * 0.00001
        self.console.print(f"[{dim}]Estimated cost: ~${cost:.4f}[/dim]")

    def print_git_status(self, branch: str, status: str, files: list) -> None:
        primary = self._get("primary")
        success = self._get("success")
        dim = self._get("dim")
        
        # Branch indicator
        branch_panel = Panel(
            f"[{primary}]⎇[/] [bold]{branch}[/bold]",
            box=ROUNDED,
            border_style=primary,
        )
        
        # Files changed
        if files:
            files_table = Table(box=None, show_header=False)
            for f in files[:10]:
                files_table.add_row(f"  [{dim}]•[/{dim}] {f}")
            files_panel = Panel(
                files_table,
                title=f"[{primary}]Changes[/]",
                box=ROUNDED,
                border_style=primary,
            )
            self.console.print(Columns([branch_panel, files_panel], padding=1))
        else:
            no_changes = Panel(
                f"[{success}]✓ No changes[/]",
                box=ROUNDED,
                border_style=success,
            )
            self.console.print(Columns([branch_panel, no_changes], padding=1))

    def print_file_tree(self, path: str, items: list) -> None:
        primary = self._get("primary")
        dim = self._get("dim")
        
        tree = Text()
        for item in items:
            if item["type"] == "dir":
                tree.append(f"  [{primary}]📁[/] {item['name']}/\n", style=primary)
            else:
                ext = item.get("ext", "")
                icon = self._get_file_icon(ext)
                tree.append(f"  [{dim}]•[/{dim}] {icon} {item['name']}\n")
        
        self.console.print(
            Panel(
                tree,
                title=f"[{primary}]📂[/] {path}",
                border_style=primary,
                box=ROUNDED,
                padding=(0, 1),
            )
        )

    def _get_file_icon(self, ext: str) -> str:
        icons = {
            ".py": "🐍",
            ".js": "📜",
            ".ts": "🔷",
            ".jsx": "⚛️",
            ".tsx": "⚛️",
            ".md": "📝",
            ".json": "📋",
            ".yaml": "⚙️",
            ".yml": "⚙️",
            ".toml": "⚙️",
            ".sh": "🔧",
            ".rs": "🦀",
            ".go": "🐹",
            ".java": "☕",
            ".c": "🔩",
            ".cpp": "🔩",
            ".html": "🌐",
            ".css": "🎨",
            ".sql": "🗃️",
        }
        return icons.get(ext, "📄")

    def print_separator(self) -> None:
        dim = self._get("dim")
        self.console.print(f"[{dim}]─[/{dim}" * 40)

    def clear(self) -> None:
        self.console.clear()

    def set_color_scheme(self, scheme: str) -> None:
        if scheme in self._color_schemes:
            self._scheme = scheme
            self.colors = self._color_schemes[scheme]


def create_ui(scheme: Optional[str] = None) -> UI:
    return UI(scheme)