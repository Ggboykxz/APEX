"""Custom tools defined from configuration for APEX."""

from pathlib import Path
from typing import Callable
from dataclasses import dataclass
import logging
import re
import shlex

logger = logging.getLogger(__name__)

ALLOWED_COMMANDS = {
    "git",
    "npm",
    "node",
    "python",
    "python3",
    "pip",
    "ruff",
    "pytest",
    "cargo",
    "go",
    "make",
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "curl",
    "wget",
    "touch",
    "mkdir",
    "rm",
    "cp",
    "mv",
    "chmod",
    "pwd",
    "echo",
    "env",
    "which",
    "whoami",
    "uname",
    "df",
    "du",
    "ps",
}


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
        self, name: str, description: str, parameters: dict, handler: Callable[[dict], str]
    ) -> None:
        self._tools[name] = CustomTool(
            name=name, description=description, parameters=parameters, handler=handler
        )

    def get(self, name: str) -> CustomTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {"name": tool.name, "description": tool.description, "parameters": tool.parameters}
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
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]


custom_tool_manager = CustomToolManager()
_tools_loaded = False


def ensure_tools_loaded() -> None:
    global _tools_loaded
    if not _tools_loaded:
        _tools_loaded = True
        load_tools_from_dirs()


def _find_tool_dirs() -> list[Path]:
    cwd = Path.cwd()
    home = Path.home()
    dirs = [
        home / ".config" / "opencode" / "tools",
        cwd / ".opencode" / "tools",
        home / ".config" / "apex" / "tools",
        cwd / ".apex" / "tools",
    ]
    seen = set()
    result = []
    for d in dirs:
        resolved = d.resolve()
        if resolved not in seen:
            seen.add(resolved)
            result.append(d)
    return result


def load_tools_from_dirs() -> None:
    for tools_dir in _find_tool_dirs():
        if not tools_dir.is_dir():
            continue
        for py_file in sorted(tools_dir.glob("*.py")):
            name = py_file.stem
            if custom_tool_manager.get(name):
                continue
            try:
                import importlib.util

                spec = importlib.util.spec_from_file_location(f"apex_custom_tool_{name}", py_file)
                if spec is None or spec.loader is None:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "TOOL_DEFINITION"):
                    td = mod.TOOL_DEFINITION
                    desc = td.get("description", f"Custom tool: {name}")
                    params = td.get("parameters", {"type": "object", "properties": {}})
                    handler = td.get("handler")
                    if handler and callable(handler):
                        custom_tool_manager.register(name, desc, params, handler)
            except Exception:
                logger.warning(f"Failed to load custom tool from {py_file}", exc_info=True)


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

            parts = command.strip().split()
            if parts and parts[0] not in ALLOWED_COMMANDS:
                logger.warning(
                    f"Custom tool '{tool_name}' blocked: command '{parts[0]}' not in allowlist"
                )
                continue

            def make_handler(cmd: str, wd: str):
                def handler(args: dict) -> str:
                    import subprocess

                    try:
                        safe_cmd = cmd.format(**args)
                        parts_check = safe_cmd.strip().split()
                        if parts_check and parts_check[0] not in ALLOWED_COMMANDS:
                            return f"ERROR: Command '{parts_check[0]}' not allowed"

                        for pattern in [r"\$\(", r"`", r"rm\s+-rf", r"chmod\s+777"]:
                            if re.search(pattern, safe_cmd):
                                return "ERROR: Dangerous pattern blocked"

                        result = subprocess.run(
                            shlex.split(safe_cmd),
                            shell=False,
                            cwd=wd,
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                        return result.stdout or result.stderr or "[no output]"
                    except Exception as e:
                        logger.error(f"Custom tool '{tool_name}' error: {e}")
                        return f"ERROR: {e}"

                return handler

            custom_tool_manager.register(
                name=tool_name,
                description=description,
                parameters=parameters,
                handler=make_handler(command, cwd),
            )
    except Exception as e:
        logger.error(f"Failed to load custom tools: {e}")
