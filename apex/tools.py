"""Tools for APEX - file operations, command execution, git, web, and more.

The executor core lives here; the tool families are implemented by the mixins
in the sibling ``apex.tools_*`` modules.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from .tools_codegen import CodegenToolsMixin
from .tools_env import EnvToolsMixin
from .tools_files import FileToolsMixin
from .tools_git import GitToolsMixin
from .tools_lsp import LspToolsMixin
from .tools_project import ProjectToolsMixin
from .tools_schemas import TOOL_SCHEMAS
from .tools_search import SearchToolsMixin
from .tools_session import SessionToolsMixin
from .tools_shell import ShellToolsMixin
from .tools_ux import UxToolsMixin
from .tools_web import WebToolsMixin

__all__ = [
    "TOOL_SCHEMAS",
    "AsyncToolExecutor",
    "ToolExecutor",
    "get_all_tool_schemas",
]


class ToolExecutor(
    CodegenToolsMixin,
    EnvToolsMixin,
    FileToolsMixin,
    GitToolsMixin,
    LspToolsMixin,
    ProjectToolsMixin,
    SearchToolsMixin,
    SessionToolsMixin,
    ShellToolsMixin,
    UxToolsMixin,
    WebToolsMixin,
):
    def __init__(self, cwd: Path | None = None):
        self.cwd = cwd or Path.cwd()
        self._doom_counter: dict[str, int] = {}
        self._doom_last: tuple[str, str] | None = None

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p.resolve()
        return (self.cwd / p).resolve()

    def execute(self, tool_name: str, args: dict[str, Any]) -> str:
        method = getattr(self, f"_execute_{tool_name}", None)
        if not method:
            return self._dispatch_unknown_tool(tool_name, args)

        doom_error = self._check_doom_loop(tool_name, args)
        if doom_error is not None:
            return doom_error

        try:
            result = method(args)
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {type(e).__name__}: {e}"
        try:
            from .plugins import plugin_manager

            plugin_manager.trigger_hook("tool_call", tool_name, args, result)
        except Exception:
            logger.exception("Plugin hook failed for tool %s", tool_name)
        return result

    def _dispatch_unknown_tool(self, tool_name: str, args: dict[str, Any]) -> str:
        """Dispatch a tool that has no native implementation.

        Custom tools win over MCP tools; anything else is unknown.
        """
        from .config_tools import custom_tool_manager, ensure_tools_loaded

        ensure_tools_loaded()
        result = custom_tool_manager.execute(tool_name, args)
        if not result.startswith("ERROR: Unknown custom tool"):
            return result
        if tool_name.startswith("mcp_"):
            return self._dispatch_mcp_tool(tool_name, args)
        return f"ERROR: Unknown tool '{tool_name}'"

    def _dispatch_mcp_tool(self, tool_name: str, args: dict[str, Any]) -> str:
        """Call an MCP tool, from a worker thread when a loop is running."""
        try:
            from .mcp import mcp_manager

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Defer to a fresh loop in a worker thread.
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        fut = pool.submit(asyncio.run, mcp_manager.call_tool(tool_name, args))
                        return fut.result()
                return loop.run_until_complete(mcp_manager.call_tool(tool_name, args))
            except RuntimeError:
                return asyncio.run(mcp_manager.call_tool(tool_name, args))
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {type(e).__name__}: {e}"

    def _check_doom_loop(self, tool_name: str, args: dict[str, Any]) -> str | None:
        """Guard against a tool repeating itself with identical arguments.

        Returns the error message when the loop must be stopped, ``None``
        otherwise.
        """
        key = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
        if self._doom_last is not None and key == self._doom_last[0]:
            self._doom_counter[key] = self._doom_counter.get(key, 0) + 1
        else:
            self._doom_counter.clear()
        self._doom_last = (key, tool_name)
        if self._doom_counter.get(key, 0) < 3:
            return None
        self._doom_counter.clear()
        return (
            f"ERROR: Doom loop detected — '{tool_name}' called 3+ times with "
            "identical arguments. Stopping to prevent infinite loop."
        )


class AsyncToolExecutor(ToolExecutor):
    async def execute_async(self, tool_name: str, args: dict[str, Any]) -> str:

        method = getattr(self, f"_execute_{tool_name}", None)

        if not method:
            if tool_name.startswith("mcp_"):
                try:
                    from .mcp import mcp_manager

                    return await mcp_manager.call_tool(tool_name, args)

                except Exception as e:  # noqa: BLE001
                    return f"ERROR: {type(e).__name__}: {e}"

            return f"ERROR: Unknown tool '{tool_name}'"

        try:
            if hasattr(method, "__await__"):
                return await method(args)

            return method(args)

        except Exception as e:  # noqa: BLE001
            return f"ERROR: {type(e).__name__}: {e}"

    async def execute_all_parallel(self, tool_calls: list[tuple[str, dict[str, Any]]]) -> list[str]:

        tasks = [self.execute_async(name, args) for name, args in tool_calls]

        return await asyncio.gather(*tasks)


def _append_unique(schemas: list[dict], tools: list[dict]) -> None:
    """Append the tools that are not already exposed."""
    for tool in tools:
        if tool not in schemas:
            schemas.append(tool)


def _mcp_tool_schemas() -> list[dict]:
    """The schemas of the connected MCP servers, if any."""
    try:
        from .mcp import mcp_manager

        return mcp_manager.get_all_tools()
    except Exception:
        logger.exception("Failed to expose MCP tool schemas")
        return []


def _plugin_tool_schemas() -> list[dict]:
    """The schemas of the plugin-provided tools, if any."""
    try:
        from .plugins import plugin_manager

        return plugin_manager.get_tools()
    except Exception:
        logger.exception("Failed to expose plugin tool schemas")
        return []


def get_all_tool_schemas() -> list[dict]:
    """Every tool schema the model may call: native, custom, MCP and plugins."""
    from .config_tools import custom_tool_manager, ensure_tools_loaded

    ensure_tools_loaded()
    schemas = list(TOOL_SCHEMAS) + custom_tool_manager.get_schemas()
    _append_unique(schemas, _mcp_tool_schemas())
    _append_unique(schemas, _plugin_tool_schemas())
    return schemas
