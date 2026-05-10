"""Refactored UI module - More testable."""

from typing import Any, Iterator, Optional, Callable
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table


AGENT_COLORS = {
    "build": "cyan",
    "plan": "yellow",
    "explore": "green",
    "general": "magenta",
}

COLOR_MAP = {
    "primary": "cyan",
    "text": "white",
    "metadata": "dim",
    "tools": "magenta",
    "success": "green",
    "error": "red",
}


@dataclass
class CommandHelp:
    command: str
    description: str


class UI:
    def __init__(
        self,
        console: Optional[Console] = None,
        color_map: Optional[dict[str, str]] = None,
        model_provider: Optional[Callable[[], dict[str, str]]] = None,
    ):
        self.console = console or Console()
        self._color_map = color_map or COLOR_MAP
        self._model_provider = model_provider or self._default_model_provider

    def _default_model_provider(self) -> dict[str, str]:
        from .config import MODELS

        return MODELS

    def show_banner(self, model: str, cwd: str, agent: str = "build") -> None:
        color = AGENT_COLORS.get(agent, "cyan")
        banner = f"""
[bold {color}]╔═══════════════════════════════════════════════════════╗
║   APEX — Agent for Programming EXecution                     ║
║   The last coding agent you'll ever need                     ║
╚═══════════════════════════════════════════════════════════════╝[/bold {color}]

[dim]Agent:[/] [{color}]{agent}[/{color}]  [dim]Model:[/] [cyan]{model}[/cyan]  [dim]CWD:[/] [cyan]{cwd}[/cyan]
"""
        self.console.print(banner.format(model=model, cwd=cwd, agent=agent))

    def show_help(self) -> None:
        table = Table(title="APEX Commands", show_header=True, header_style="bold cyan")
        table.add_column("Command", style="cyan", width=20)
        table.add_column("Description", style="white")

        commands = [
            ("/agent [name]", "Switch agent (build/plan)"),
            ("/agents", "List all available agents"),
            ("/subagents", "List subagents (use @name)"),
            ("Tab", "Cycle through primary agents"),
            ("/model <alias>", "Switch to a different model"),
            ("/models", "List all available models"),
            ("/cwd <path>", "Change current working directory"),
            ("/clear", "Clear conversation history"),
            ("/history", "Show conversation history"),
            ("/cost", "Show token usage and estimated cost"),
            ("/save [name]", "Save current session"),
            ("/load <name>", "Load a previous session"),
            ("/memory", "Manage persistent memory"),
            ("/map", "Show repository map"),
            ("/git", "Show git status"),
            ("/help", "Show this help message"),
            ("/exit, /quit", "Exit APEX"),
            ("@agent task", "Invoke subagent for task"),
        ]

        for cmd, desc in commands:
            table.add_row(cmd, desc)
        self.console.print(table)

    def show_models(self, current: str) -> None:
        models = self._model_provider()
        table = Table(title="Available Models", show_header=True, header_style="bold cyan")
        table.add_column("Alias", style="cyan", width=20)
        table.add_column("Model String", style="white")
        table.add_column("Current", style="green", width=8)

        for alias, model_str in sorted(models.items()):
            marker = "✓" if alias == current else ""
            table.add_row(alias, model_str, marker)

        self.console.print(table)

    def print_user(self, text: str) -> None:
        self.console.print(f"[bold cyan]›[/bold cyan] {text}")

    def print_thinking(self, message: str = "Thinking...") -> Iterator[None]:
        return self.console.status(f"[cyan]{message}[/cyan]", spinner="dots")

    def print_response(self, text: str) -> None:
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
                        syntax = Syntax(code, lang or "python", theme="monokai", line_numbers=True)
                        self.console.print(Panel(syntax, border_style="cyan"))
        else:
            md = Markdown(text)
            self.console.print(md)

    def print_tool_call(self, name: str, args: dict[str, Any]) -> None:
        args_str = ", ".join(f"{k}={repr(v)[:50]}" for k, v in args.items())
        self.console.print(f"[magenta]⚙[/magenta] [bold magenta]{name}[/bold magenta]({args_str})")

    def print_tool_result(self, name: str, result: str) -> None:
        if result.startswith("ERROR:"):
            self.console.print(Panel(result, title=f"[red]{name}[/red]", border_style="red"))
        elif result.startswith("SUCCESS:"):
            self.console.print(Panel(result, title=f"[green]{name}[/green]", border_style="green"))
        else:
            if len(result) > 2000:
                result = result[:2000] + "\n... [truncated]"
            self.console.print(Panel(result, title=f"[cyan]{name}[/cyan]", border_style="cyan"))

    def print_error(self, message: str) -> None:
        self.console.print(f"[bold red]✗[/bold red] {message}")

    def print_success(self, message: str) -> None:
        self.console.print(f"[bold green]✓[/bold green] {message}")

    def print_info(self, message: str) -> None:
        self.console.print(f"[dim]ℹ[/dim] {message}")

    def print_cost(self, usage: dict[str, int]) -> None:
        table = Table(title="Token Usage", show_header=True, header_style="bold cyan")
        table.add_column("Type", style="cyan")
        table.add_column("Tokens", style="white", justify="right")

        total = sum(usage.values())
        for token_type, count in usage.items():
            table.add_row(token_type, f"{count:,}")

        table.add_row("[bold]Total[/bold]", f"[bold]{total:,}[/bold]")
        self.console.print(table)

        cost_estimate = total * 0.00001
        self.console.print(f"[dim]Estimated cost: ~${cost_estimate:.4f}[/dim]")

    def get_color(self, key: str) -> str:
        return self._color_map.get(key, "white")


def create_ui(console: Optional[Console] = None, color_map: Optional[dict] = None) -> UI:
    return UI(console, color_map)
