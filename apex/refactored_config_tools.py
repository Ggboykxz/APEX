"""Refactored config_tools module - More testable."""

from pathlib import Path
from typing import Callable, Optional
from dataclasses import dataclass
import shlex
import subprocess


@dataclass
class CustomTool:
    name: str
    description: str
    parameters: dict
    handler: Callable[[dict], str]


class CustomToolManager:
    def __init__(self):
        self._tools: dict[str, CustomTool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable[[dict], str]
    ) -> None:
        self._tools[name] = CustomTool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler
        )

    def unregister(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[CustomTool]:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, args: dict) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"ERROR: Unknown custom tool: {name}"
        try:
            return tool.handler(args)
        except Exception as e:
            return f"ERROR: Tool execution failed: {e}"

    def get_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": f"custom_{tool.name}",
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in self._tools.values()
        ]

    def clear(self) -> None:
        self._tools.clear()

    @property
    def tools(self) -> dict[str, CustomTool]:
        return self._tools


def create_custom_tool_manager() -> CustomToolManager:
    return CustomToolManager()


def load_custom_tools(
    config_path: Path,
    tool_manager: Optional[CustomToolManager] = None,
    yaml_loader: Optional[Callable] = None,
    subprocess_runner: Optional[Callable] = None
) -> None:
    manager = tool_manager or CustomToolManager()
    loader = yaml_loader or __import__('yaml').safe_load
    runner = subprocess_runner or __import__('subprocess').run

    if not config_path.exists():
        return

    try:
        with open(config_path) as f:
            config = loader(f)

        if not config or "custom_tools" not in config:
            return

        for tool_name, tool_config in config["custom_tools"].items():
            if not tool_config.get("enabled", True):
                continue

            description = tool_config.get("description", "Custom tool")
            parameters = tool_config.get("parameters", {"type": "object", "properties": {}})
            command = tool_config.get("command", "")
            cwd = tool_config.get("cwd", ".")

            def make_handler(cmd: str, wd: str):
                def handler(args: dict) -> str:
                    try:
                        result = subprocess.run(
                            shlex.split(cmd.format(**args)),
                            shell=False,
                            cwd=wd,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        return result.stdout or result.stderr or "[no output]"
                    except Exception as e:
                        return f"ERROR: {e}"
                return handler

            manager.register(
                name=tool_name,
                description=description,
                parameters=parameters,
                handler=make_handler(command, cwd)
            )
    except Exception as e:
        print(f"Failed to load custom tools: {e}")