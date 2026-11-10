import json
import os
import subprocess
from typing import Any


class LSPClient:
    def __init__(self, cwd: str, server_command: list[str], env: dict[str, str] | None = None):
        self.cwd = cwd
        self.server_command = server_command
        self.env = env or {}
        self.process: subprocess.Popen | None = None
        self.request_id = 0
        self.capabilities: dict[str, Any] = {}
        self._initialized = False

    def start(self):
        full_env = {**os.environ.copy(), **self.env}
        self.process = subprocess.Popen(
            self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            env=full_env,
            text=True,
        )
        self._initialized = False

    def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.process or not self.process.stdin:
            raise RuntimeError("LSP server not running")

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params,
        }

        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json)
        self.process.stdin.flush()

        return self._read_response()

    def _read_response(self) -> dict[str, Any]:
        if not self.process or not self.process.stdout:
            raise RuntimeError("LSP server not running")

        line = self.process.stdout.readline()
        while line:
            if line.strip():
                return json.loads(line)
            line = self.process.stdout.readline()
        return {}

    def initialize(self, root_path: str):
        result = self._send_request(
            "initialize",
            {
                "processId": os.getpid(),
                "rootUri": f"file://{root_path}",
                "capabilities": {},
            },
        )
        self.capabilities = result.get("result", {}).get("capabilities", {})
        self._initialized = True
        self._send_request("initialized", {})

    def shutdown(self):
        if self._initialized:
            self._send_request("shutdown", {})
            self._send_request("exit", {})
        if self.process:
            self.process.terminate()
            self.process.wait()

    def _position_params(self, uri: str, line: int, column: int) -> dict[str, Any]:
        """The LSP params that carry a position."""
        return {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": column},
        }

    def _request_result(self, method: str, params: dict[str, Any]) -> Any:
        """Send a request and return its ``result`` field."""
        if not self._initialized:
            return None
        result = self._send_request(method, params)
        return result.get("result")

    def get_definitions(self, uri: str, line: int, column: int) -> list[dict[str, Any]]:
        result = self._request_result(
            "textDocument/definition", self._position_params(uri, line, column)
        )
        return result if isinstance(result, list) else []

    def get_references(self, uri: str, line: int, column: int) -> list[dict[str, Any]]:
        params = self._position_params(uri, line, column)
        params["context"] = {"includeDeclaration": True}
        result = self._request_result("textDocument/references", params)
        return result if isinstance(result, list) else []

    def get_hover(self, uri: str, line: int, column: int) -> dict[str, Any] | None:
        result = self._request_result(
            "textDocument/hover", self._position_params(uri, line, column)
        )
        return result if isinstance(result, dict) else None

    def get_document_symbols(self, uri: str) -> list[dict[str, Any]]:
        if not self._initialized:
            return []

        result = self._send_request(
            "textDocument/documentSymbol",
            {"textDocument": {"uri": uri}},
        )
        return result.get("result", [])

    def get_workspace_symbols(self, query: str) -> list[dict[str, Any]]:
        if not self._initialized:
            return []

        result = self._send_request("workspace/symbol", {"query": query})
        return result.get("result", [])

    def get_diagnostics(self, uri: str) -> list[dict[str, Any]]:
        if not self._initialized:
            return []

        result = self._send_request(
            "textDocument/diagnostic",
            {"textDocument": {"uri": uri}},
        )
        return result.get("result", {}).get("items", [])


class LSPManager:
    def __init__(self, cwd: str):
        self.cwd = cwd
        self.servers: dict[str, LSPClient] = {}
        self._config: dict[str, Any] = {}

    def load_config(self, config: dict[str, Any]):
        self._config = config

    def add_server(self, name: str, command: list[str], env: dict[str, str] | None = None):
        client = LSPClient(self.cwd, command, env)
        self.servers[name] = client

    def start_all(self):
        for name, client in self.servers.items():
            try:
                client.start()
                client.initialize(self.cwd)
            except Exception as e:  # noqa: BLE001
                print(f"Warning: Failed to start LSP server '{name}': {e}")

    def stop_all(self):
        for client in self.servers.values():
            try:
                client.shutdown()
            except Exception:  # noqa: BLE001, S110
                pass

    def get_tools(self) -> dict[str, Any]:
        tools = {}
        for name, client in self.servers.items():
            if client._initialized:
                tools[f"lsp_{name}_definition"] = {
                    "description": f"Go to definition (LSP: {name})",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "line": {"type": "integer"},
                            "column": {"type": "integer"},
                        },
                        "required": ["path"],
                    },
                }
                tools[f"lsp_{name}_references"] = {
                    "description": f"Find references (LSP: {name})",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "line": {"type": "integer"},
                            "column": {"type": "integer"},
                        },
                        "required": ["path"],
                    },
                }
                tools[f"lsp_{name}_hover"] = {
                    "description": f"Show hover info (LSP: {name})",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "line": {"type": "integer"},
                            "column": {"type": "integer"},
                        },
                        "required": ["path"],
                    },
                }
                tools[f"lsp_{name}_diagnostics"] = {
                    "description": f"Get diagnostics (LSP: {name})",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                        },
                        "required": ["path"],
                    },
                }
        return tools

    def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        try:
            return self._dispatch_lsp_tool(name, args)
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def _dispatch_lsp_tool(self, name: str, args: dict[str, Any]) -> Any:
        """Dispatch one LSP tool call."""
        server_name, operation = self._parse_lsp_tool(name)
        if server_name is None:
            return {"error": operation}
        client = self.servers.get(server_name)
        if client is None:
            return {"error": f"Unknown LSP server: {server_name}"}

        uri = self._tool_uri(args)
        line = args.get("line", 0)
        column = args.get("column", 0)

        handler = self._LSP_HANDLERS.get(operation)
        if handler is None:
            return {"error": f"Unknown operation: {operation}"}
        return handler(self, client, uri, line, column)

    def _parse_lsp_tool(self, name: str) -> tuple[str | None, str]:
        """The server name and the operation of an LSP tool name."""
        parts = name.split("_", 2)
        if len(parts) < 3:
            return None, "Invalid LSP tool name"
        return parts[1], parts[2]

    def _tool_uri(self, args: dict[str, Any]) -> str:
        """The file URI an LSP tool operates on."""
        path = args.get("path", "")
        return f"file://{os.path.abspath(path)}"

    def _handle_definition(self, client, uri, line, column) -> dict[str, Any]:
        results = client.get_definitions(uri, line, column)
        return {"definitions": [{"uri": r.get("uri"), "range": r.get("range")} for r in results]}

    def _handle_references(self, client, uri, line, column) -> dict[str, Any]:
        results = client.get_references(uri, line, column)
        return {"references": [{"uri": r.get("uri"), "range": r.get("range")} for r in results]}

    def _handle_hover(self, client, uri, line, column) -> dict[str, Any]:
        result = client.get_hover(uri, line, column)
        if result and result.get("contents"):
            content = result["contents"]
            if isinstance(content, dict):
                return {"content": content.get("value", "")}
            return {"content": str(content)}
        return {"content": ""}

    def _handle_diagnostics(self, client, uri, line, column) -> dict[str, Any]:
        results = client.get_diagnostics(uri)
        return {
            "diagnostics": [
                {
                    "message": d.get("message"),
                    "range": d.get("range"),
                    "severity": d.get("severity"),
                }
                for d in results
            ]
        }

    _LSP_HANDLERS = {  # noqa: RUF012
        "definition": _handle_definition,
        "references": _handle_references,
        "hover": _handle_hover,
        "diagnostics": _handle_diagnostics,
    }


_lsp_manager: LSPManager | None = None


def get_lsp_manager(cwd: str) -> LSPManager:
    global _lsp_manager
    if _lsp_manager is None:
        _lsp_manager = LSPManager(cwd)
    return _lsp_manager
