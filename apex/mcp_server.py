"""MCP stdio server exposing APEX tools to MCP clients.

Implements the server side of the Model Context Protocol (MCP) over
newline-delimited JSON-RPC 2.0 on stdin/stdout (ADR-0006).

- ``stdout`` carries protocol messages only; all diagnostics go to
  ``stderr``.
- The default profile is read-only. Destructive or side-effectful tools
  are exposed only when explicitly allowed via ``--allow-tool``, the
  ``mcp.server.allow_tools`` config key, or ``APEX_MCP_ALLOW_TOOLS``.
- Every call runs through the existing :class:`~apex.tools.ToolExecutor`
  so path resolution and tool behavior stay identical to the agent.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, TextIO

from . import __version__ as SERVER_VERSION
from .tools import ToolExecutor, get_all_tool_schemas

logger = logging.getLogger(__name__)

# Protocol (MCP spec, 2024-11-05 revision).
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "apex"

# Limits (ADR-0006).
MAX_REQUEST_BYTES = 1024 * 1024  # 1 MiB
MAX_RESPONSE_BYTES = 1024 * 1024  # 1 MiB
DEFAULT_CALL_TIMEOUT = 120.0  # seconds
TRUNCATE_MARK = "\n…[truncated]"

# JSON-RPC error codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Tools that only read the workspace, repository, environment, or LSP
# state. Everything else (writes, edits, patches, shell commands, git
# mutations, automation) is excluded unless explicitly allowed.
READ_ONLY_TOOLS = frozenset(
    {
        "batch_read",
        "diff_files",
        "expand_vars",
        "get_code_actions",
        "get_completions",
        "get_context_info",
        "get_conversation_stats",
        "get_env",
        "get_file_tree",
        "get_git_log",
        "get_git_status",
        "get_keybindings",
        "get_repo_map",
        "get_task",
        "get_tool_timeout",
        "git_diff",
        "glob_search",
        "lsp_definition",
        "lsp_diagnostics",
        "lsp_hover",
        "lsp_references",
        "list_commands",
        "list_env",
        "list_files",
        "list_skills",
        "list_tasks",
        "read_file",
        "read_image",
        "read_image_data",
        "redo_info",
        "repo_map",
        "search_history",
        "search_in_files",
        "undo_info",
    }
)


class MCPError(Exception):
    """JSON-RPC error carrying an MCP/JSON-RPC code."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def _function_schema(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the inner ``function`` object of an APEX tool schema entry."""
    fn = entry.get("function") if isinstance(entry, dict) else None
    return fn if isinstance(fn, dict) else None


def _known_tool_names() -> dict[str, dict[str, Any]]:
    """Map tool name → inner function schema for every registered tool."""
    names: dict[str, dict[str, Any]] = {}
    for entry in get_all_tool_schemas():
        fn = _function_schema(entry)
        if not fn or not isinstance(fn.get("name"), str):
            continue
        names[fn["name"]] = fn
    return names


def resolve_allow_tools(
    cli: list[str] | None = None, env: str | None = None, config: Any = None
) -> set[str]:
    """Merge allow-list sources into one set of tool names.

    Presence rules (union):
    - ``cli``: values from ``--allow-tool`` (repeatable).
    - ``env``: comma-separated values from ``APEX_MCP_ALLOW_TOOLS``.
    - ``config``: ``mcp.server.allow_tools`` list from the validated config.

    The caller still filters the result against known tool names.
    """
    allowed: set[str] = set()
    for value in cli or []:
        if isinstance(value, str) and value.strip():
            allowed.add(value.strip())
    if env:
        for part in env.split(","):
            part = part.strip()
            if part:
                allowed.add(part)
    if isinstance(config, dict):
        raw = (
            config.get("server", {}).get("allow_tools", [])
            if isinstance(config.get("server"), dict)
            else []
        )
        if isinstance(raw, list):
            for value in raw:
                if isinstance(value, str) and value.strip():
                    allowed.add(value.strip())
    return allowed


class StdioMCPServer:
    """A single MCP server session bound to the given text streams."""

    def __init__(
        self,
        cwd: Path | str | None = None,
        allow_tools: list[str] | None = None,
        call_timeout: float = DEFAULT_CALL_TIMEOUT,
    ) -> None:
        self.cwd = Path(cwd).resolve() if cwd else Path.cwd().resolve()
        self.executor = ToolExecutor(cwd=self.cwd)
        self._schemas = _known_tool_names()
        self._allowed = self._build_profile(allow_tools)
        self._call_timeout = call_timeout
        self._client_version = PROTOCOL_VERSION

    def _build_profile(self, cli_allow: list[str] | None) -> frozenset[str]:
        """Compute the effective tool profile.

        With no explicit allow-list the profile is the read-only default.
        With one, it replaces the default (the caller opted into control)
        but is still filtered to known tool names.
        """
        from .config_v2 import apex_config

        try:
            config_mcp = apex_config.mcp
        except Exception:
            config_mcp = {}
        explicit = resolve_allow_tools(
            cli_allow, os.environ.get("APEX_MCP_ALLOW_TOOLS"), config_mcp
        )
        if explicit:
            return frozenset(name for name in explicit if name in self._schemas)
        return frozenset(READ_ONLY_TOOLS & set(self._schemas))

    # ── JSON-RPC handlers ─────────────────────────────────────

    def _handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Dispatch one request; returns a response dict or None for notifications."""
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params")

        if method is None:
            raise MCPError(INVALID_REQUEST, "missing method")
        if method.startswith("notifications/"):
            return None
        if method == "initialize":
            return self._initialize(msg_id, params)
        if method == "ping":
            return self._result(msg_id, {})
        if method == "tools/list":
            return self._tools_list(msg_id)
        if method == "tools/call":
            return self._tools_call(msg_id, params)
        raise MCPError(METHOD_NOT_FOUND, f"method not found: {method}")

    def _initialize(self, msg_id: Any, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            raise MCPError(INVALID_PARAMS, "initialize params must be an object")
        client_version = params.get("protocolVersion")
        if isinstance(client_version, str) and client_version.startswith("2025-"):
            self._client_version = client_version
        else:
            self._client_version = PROTOCOL_VERSION
        return self._result(
            msg_id,
            {
                "protocolVersion": self._client_version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    def _tools_list(self, msg_id: Any) -> dict[str, Any]:
        tools = []
        for name, fn in self._schemas.items():
            if name not in self._allowed:
                continue
            description = fn.get("description", "")
            input_schema = fn.get("parameters") or {"type": "object", "properties": {}}
            tool: dict[str, Any] = {
                "name": name,
                "description": description if isinstance(description, str) else "",
                "inputSchema": input_schema,
            }
            tools.append(tool)
        tools.sort(key=lambda item: item["name"])
        return self._result(msg_id, {"tools": tools})

    def _tools_call(self, msg_id: Any, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            raise MCPError(INVALID_PARAMS, "tools/call params must be an object")
        name = params.get("name")
        arguments = params.get("arguments")
        if not isinstance(name, str) or not name:
            raise MCPError(INVALID_PARAMS, "tool name required")
        if name not in self._schemas:
            raise MCPError(INVALID_PARAMS, f"unknown tool: {name}")
        if name not in self._allowed:
            raise MCPError(INVALID_PARAMS, f"tool not allowed: {name}")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise MCPError(INVALID_PARAMS, "tool arguments must be an object")

        try:
            text = self._execute_with_timeout(name, arguments)
        except MCPError:
            raise
        except Exception as exc:
            text = f"ERROR: {type(exc).__name__}: {exc}"

        is_error = text.startswith("ERROR:")
        text = self._clamp_response(text)
        return self._result(
            msg_id,
            {
                "content": [{"type": "text", "text": text}],
                "isError": is_error,
            },
        )

    def _execute_with_timeout(self, name: str, arguments: dict[str, Any]) -> str:
        """Run one tool call, enforcing the per-call timeout."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.executor.execute, name, arguments)
            try:
                return future.result(timeout=self._call_timeout)
            except concurrent.futures.TimeoutError:
                future.cancel()
                raise MCPError(
                    INTERNAL_ERROR, f"tool call timed out after {self._call_timeout:g}s"
                ) from None

    @staticmethod
    def _clamp_response(text: str) -> str:
        if len(text.encode("utf-8")) <= MAX_RESPONSE_BYTES:
            return text
        cut = MAX_RESPONSE_BYTES - len(TRUNCATE_MARK.encode("utf-8"))
        return text.encode("utf-8")[:cut].decode("utf-8", errors="ignore") + TRUNCATE_MARK

    @staticmethod
    def _result(msg_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    @staticmethod
    def _error(msg_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
        error: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {"jsonrpc": "2.0", "id": msg_id, "error": error}


def _write_message(out: TextIO, message: dict[str, Any]) -> None:
    out.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")))
    out.write("\n")
    out.flush()


def _process_line(server: StdioMCPServer, line: str, out: TextIO) -> None:
    """Process one input line; may emit zero, one, or many responses."""
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        _write_message(out, server._error(None, PARSE_ERROR, f"parse error: {exc}"))
        return

    if isinstance(payload, list):
        # JSON-RPC batch: respond to every request; notifications contribute
        # nothing. An empty batch is itself invalid.
        responses = []
        for item in payload:
            if not isinstance(item, dict):
                responses.append(
                    server._error(None, INVALID_REQUEST, "batch entries must be objects")
                )
                continue
            try:
                response = server._handle(item)
            except MCPError as exc:
                response = server._error(item.get("id"), exc.code, exc.message, exc.data)
            except Exception as exc:  # pragma: no cover - defensive boundary
                response = server._error(item.get("id"), INTERNAL_ERROR, f"internal error: {exc}")
            if response is not None:
                responses.append(response)
        if responses:
            _write_message(out, responses)
        return

    if not isinstance(payload, dict):
        _write_message(out, server._error(None, INVALID_REQUEST, "request must be an object"))
        return

    try:
        response = server._handle(payload)
    except MCPError as exc:
        response = server._error(payload.get("id"), exc.code, exc.message, exc.data)
    except Exception as exc:  # pragma: no cover - defensive boundary
        response = server._error(payload.get("id"), INTERNAL_ERROR, f"internal error: {exc}")
    if response is not None:
        _write_message(out, response)


def serve(
    cwd: Path | str | None = None,
    allow_tools: list[str] | None = None,
    call_timeout: float = DEFAULT_CALL_TIMEOUT,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Run the stdio MCP server until stdin closes. Returns exit code."""
    server = StdioMCPServer(cwd=cwd, allow_tools=allow_tools, call_timeout=call_timeout)
    inp = stdin if stdin is not None else sys.stdin
    out = stdout if stdout is not None else sys.stdout

    for line in inp:
        if not line:
            break
        line = line.rstrip("\r\n")
        if not line:
            continue
        if len(line.encode("utf-8")) > MAX_REQUEST_BYTES:
            _write_message(out, server._error(None, INVALID_REQUEST, "request exceeds 1 MiB"))
            continue
        try:
            _process_line(server, line, out)
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.exception("unhandled MCP server error: %s", exc)
            try:
                _write_message(out, server._error(None, INTERNAL_ERROR, f"internal error: {exc}"))
            except Exception:
                break
    return 0


__all__ = [
    "DEFAULT_CALL_TIMEOUT",
    "MAX_REQUEST_BYTES",
    "MAX_RESPONSE_BYTES",
    "MCPError",
    "PROTOCOL_VERSION",
    "READ_ONLY_TOOLS",
    "SERVER_NAME",
    "StdioMCPServer",
    "resolve_allow_tools",
    "serve",
]
