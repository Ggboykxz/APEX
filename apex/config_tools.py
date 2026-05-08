"""Custom tools defined from configuration for APEX."""

import json
from pathlib import Path
from typing import Any, Callable
from dataclasses import dataclass


@dataclass
class CustomTool:
    name: str
    description: str
    parameters: dict
    handler: Callable[[dict], str]


class CustomToolManager:
    def __init__(self):
        self._tools: dict[str, CustomTool] = {}

    def register(self, name: str, description: str, parameters: dict, handler: Callable[[dict], str]) -> None:
        self._tools[name] = CustomTool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler
        )

    def get(self, name: str) -> CustomTool | None:
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


custom_tool_manager = CustomToolManager()


def load_custom_tools(config_path: Path) -> None:
    if not config_path.exists():
        return

    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)

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
                    import subprocess
                    try:
                        result = subprocess.run(
                            cmd.format(**args),
                            shell=True,
                            cwd=wd,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        return result.stdout or result.stderr or "[no output]"
                    except Exception as e:
                        return f"ERROR: {e}"
                return handler

            custom_tool_manager.register(
                name=tool_name,
                description=description,
                parameters=parameters,
                handler=make_handler(command, cwd)
            )
    except Exception as e:
        print(f"Failed to load custom tools: {e}")