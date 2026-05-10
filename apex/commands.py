"""Custom commands system for APEX - User and project commands."""

import os
from pathlib import Path
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass


@dataclass
class Command:
    name: str
    description: str
    content: str
    category: str = "general"
    short_help: str = ""

    @property
    def trigger(self) -> str:
        return f"{self.category}:{self.name}"


class CommandManager:
    """Manages custom commands for APEX."""

    USER_COMMANDS_DIR = Path.home() / ".apex" / "commands"
    PROJECT_COMMANDS_DIR = ".apex" / "commands"

    def __init__(self, cwd: Optional[Path] = None):
        self.cwd = cwd or Path.cwd()
        self._commands: Dict[str, Command] = {}
        self._handlers: Dict[str, Callable] = {}
        self._load_commands()

    def _load_commands(self) -> None:
        """Load commands from directories."""
        self._load_user_commands()
        self._load_project_commands()

    def _load_user_commands(self) -> None:
        """Load global user commands."""
        if self.USER_COMMANDS_DIR.exists():
            self._load_from_dir(self.USER_COMMANDS_DIR, "user")

    def _load_project_commands(self) -> None:
        """Load project-specific commands."""
        project_dir = self.cwd / self.PROJECT_COMMANDS_DIR
        if project_dir.exists():
            self._load_from_dir(project_dir, "project")

    def _load_from_dir(self, directory: Path, category: str) -> None:
        """Load all .md files from a directory."""
        for md_file in directory.glob("*.md"):
            try:
                content = md_file.read_text()
                command = self._parse_command(content, md_file.stem, category)
                if command:
                    self._commands[command.trigger] = command
            except Exception:
                pass

    def _parse_command(self, content: str, name: str, category: str) -> Optional[Command]:
        """Parse a command from markdown content."""
        lines = content.strip().split("\n")
        if not lines:
            return None

        lines[0].strip()
        description = ""
        if len(lines) > 1:
            description = " ".join(lines[1:]).strip()

        return Command(name=name, description=description, content=content, category=category)

    def register_command(
        self, name: str, handler: Callable, category: str = "user", description: str = ""
    ) -> None:
        """Register a programmatic command."""
        self._handlers[f"{category}:{name}"] = handler
        self._commands[f"{category}:{name}"] = Command(
            name=name,
            description=description,
            content=f"<!-- Programmatic command: {name} -->",
            category=category,
        )

    def get_command(self, trigger: str) -> Optional[Command]:
        """Get a command by trigger."""
        return self._commands.get(trigger)

    def execute(self, trigger: str, context: Dict) -> Optional[str]:
        """Execute a command."""
        if trigger in self._handlers:
            return self._handlers[trigger](context)

        command = self.get_command(trigger)
        if command:
            return self._expand_template(command.content, context)

        return None

    def _expand_template(self, content: str, context: Dict) -> str:
        """Expand template variables in command content."""
        result = content

        for key, value in context.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))

        for key, value in os.environ.items():
            placeholder = f"${{{key}}}"
            result = result.replace(placeholder, value)

        return result

    def list_commands(self, category: Optional[str] = None) -> List[Command]:
        """List all commands, optionally filtered by category."""
        commands = list(self._commands.values())
        if category:
            commands = [c for c in commands if c.category == category]
        return commands

    def search(self, query: str) -> List[Command]:
        """Search commands by name or description."""
        query_lower = query.lower()
        return [
            c
            for c in self._commands.values()
            if query_lower in c.name.lower() or query_lower in c.description.lower()
        ]

    def create_command(
        self, name: str, content: str, category: str = "user", description: str = ""
    ) -> None:
        """Create a new command file."""
        if category == "user":
            directory = self.USER_COMMANDS_DIR
        else:
            directory = self.cwd / self.PROJECT_COMMANDS_DIR

        directory.mkdir(parents=True, exist_ok=True)

        file_path = directory / f"{name}.md"
        full_content = f"# {name}\n\n{description}\n\n{content}"
        file_path.write_text(full_content)

        command = Command(name=name, description=description, content=content, category=category)
        self._commands[command.trigger] = command


def create_command_manager(cwd: Optional[Path] = None) -> CommandManager:
    """Factory function to create a command manager."""
    return CommandManager(cwd)
