"""Language-server tools: definitions, references, hover and diagnostics.

Split out of ``apex.tools`` so that module keeps a single
responsibility: the tool executor core.
"""

from __future__ import annotations

import json
from typing import Any

__all__ = [
    "LspToolsMixin",
]


class LspToolsMixin:
    def _lsp_position_call(self, args: dict[str, Any], tool: str) -> str:
        """Call an LSP tool that needs a path and a position."""
        path = self._resolve(args["path"])
        line = args.get("line", 0)
        column = args.get("column", 0)
        from .lsp import get_lsp_manager

        lsp = get_lsp_manager(str(self.cwd))
        result = lsp.call_tool(tool, {"path": str(path), "line": line, "column": column})
        return json.dumps(result)

    def _execute_lsp_definition(self, args: dict[str, Any]) -> str:
        return self._lsp_position_call(args, "lsp_default_definition")

    def _execute_lsp_references(self, args: dict[str, Any]) -> str:
        return self._lsp_position_call(args, "lsp_default_references")

    def _execute_lsp_hover(self, args: dict[str, Any]) -> str:
        return self._lsp_position_call(args, "lsp_default_hover")

    def _execute_lsp_diagnostics(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        from .lsp import get_lsp_manager

        lsp = get_lsp_manager(str(self.cwd))
        result = lsp.call_tool("lsp_default_diagnostics", {"path": str(path)})
        return json.dumps(result)

    def _execute_get_completions(self, args: dict[str, Any]) -> str:
        ctype = args.get("type", "file")
        prefix = args.get("prefix", "")

        if ctype == "file":
            from .mentions import get_file_completer

            fc = get_file_completer(str(self.cwd))
            results = fc.complete(prefix)
            return "Completions:\n" + "\n".join(results) if results else "No matches"
        elif ctype == "command":
            from .slash import get_slash_command_manager

            cm = get_slash_command_manager()
            commands = cm.list_commands()
            matches = [c["name"] for c in commands if c["name"].startswith(prefix)]
            return "Commands:\n" + "\n".join(matches) if matches else "No matches"
        elif ctype == "agent":
            return "Agents: build, plan\nSubagents: explore, general"
        elif ctype == "model":
            return "Use --model flag or /model command"
        return "Unknown completion type"

    def _execute_get_code_actions(self, args: dict[str, Any]) -> str:
        from .lsp import get_lsp_manager

        path = self._resolve(args["path"])
        lsp = get_lsp_manager(str(self.cwd))
        result = lsp.call_tool("lsp_default_diagnostics", {"path": str(path)})
        if not result.get("diagnostics"):
            return "No diagnostic issues found."

        actions = []
        for diag in result.get("diagnostics", [])[:10]:
            actions.append(f"- {diag.get('message', 'Unknown issue')}")

        return "Available code actions:\n" + "\n".join(actions)

    def _execute_apply_code_action(self, args: dict[str, Any]) -> str:
        action_id = args["action_id"]
        return f"Applying code action: {action_id}\n\n(Note: LSP code actions require full LSP integration)"
