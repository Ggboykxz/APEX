from pathlib import Path
from typing import Optional, Dict, List


class Command:
    def __init__(self, name: str, description: str, prompt: str, args: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.prompt = prompt
        self.args = args or []

    def render(self, **kwargs) -> str:
        result = self.prompt
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result


class CommandManager:
    def __init__(self, cwd: str):
        self.cwd = cwd
        self._commands: Dict[str, Command] = {}
        self._load_commands()

    def _load_commands(self):
        command_dirs = [
            Path(self.cwd) / ".apex" / "commands",
            Path.home() / ".apex" / "commands",
        ]

        for command_dir in command_dirs:
            if not command_dir.exists():
                continue
            for file in command_dir.glob("*.md"):
                self._load_command_file(file)

    def _load_command_file(self, filepath: Path):
        try:
            content = filepath.read_text()
            lines = content.strip().split("\n")

            name = filepath.stem
            description = ""
            prompt_lines = []
            in_prompt = False

            for line in lines:
                if line.startswith("## Description:"):
                    description = line.split(":", 1)[1].strip()
                    continue
                if line.strip() == "## Prompt":
                    in_prompt = True
                    continue
                if in_prompt:
                    prompt_lines.append(line)

            prompt = "\n".join(prompt_lines).strip()
            if prompt:
                self._commands[name] = Command(name, description, prompt)
        except Exception:
            pass

    def get(self, name: str) -> Optional[Command]:
        return self._commands.get(name)

    def list_commands(self) -> List[Dict[str, str]]:
        return [
            {"name": name, "description": cmd.description}
            for name, cmd in self._commands.items()
        ]

    def execute(self, name: str, **kwargs) -> Optional[str]:
        cmd = self._commands.get(name)
        if not cmd:
            return None
        return cmd.render(**kwargs)

    def add_command(self, name: str, description: str, prompt: str):
        self._commands[name] = Command(name, description, prompt)

    def remove_command(self, name: str) -> bool:
        if name in self._commands:
            del self._commands[name]
            return True
        return False


class PlanApproval:
    def __init__(self):
        self._pending_plan: Optional[str] = None
        self._approved: bool = False

    def set_plan(self, plan: str):
        self._pending_plan = plan
        self._approved = False

    def approve(self):
        self._approved = True

    def reject(self):
        self._pending_plan = None
        self._approved = False

    def get_plan(self) -> Optional[str]:
        if self._approved:
            return self._pending_plan
        return None

    def is_awaiting_approval(self) -> bool:
        return self._pending_plan is not None and not self._approved

    def clear(self):
        self._pending_plan = None
        self._approved = False


_command_manager: Optional[CommandManager] = None


def get_command_manager(cwd: str) -> CommandManager:
    global _command_manager
    if _command_manager is None:
        _command_manager = CommandManager(cwd)
    return _command_manager