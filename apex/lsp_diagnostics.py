"""Enhanced LSP integration - Feed diagnostics to model after edits."""

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class Diagnostic:
    """ LSP diagnostic information."""
    severity: str
    message: str
    line: int
    column: int
    source: str


LANGUAGE_SERVERS = {
    "python": ["pyright-langserver", "--stdio"],
    "javascript": ["typescript-language-server", "--stdio"],
    "typescript": ["typescript-language-server", "--stdio"],
    "go": ["gopls"],
    "rust": ["rust-analyzer"],
    "cpp": ["clangd"],
    "java": ["java-language-server"],
    "csharp": ["OmniSharp"],
}


class LSPDiagnostics:
    """Enhanced LSP client with diagnostics feeding."""

    def __init__(self, cwd: Path | None = None):
        self.cwd = cwd or Path.cwd()
        self._servers: dict[str, Any] = {}
        self._initialized = False
        self._last_diagnostics: dict[str, list[Diagnostic]] = {}

    def detect_language(self, filepath: Path) -> Optional[str]:
        """Detect language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "cpp",
            ".h": "cpp",
            ".java": "java",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
        }
        return ext_map.get(filepath.suffix)

    def start_server(self, language: str) -> bool:
        """Start LSP server for a language."""
        if language in self._servers:
            return True

        if language not in LANGUAGE_SERVERS:
            return False

        cmd = LANGUAGE_SERVERS[language]
        try:
            process = subprocess.Popen(
                cmd,
                cwd=str(self.cwd),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._servers[language] = {
                "process": process,
                "initialized": False,
            }
            return True
        except FileNotFoundError:
            return False

    def initialize(self, language: str, filepath: Path) -> bool:
        """Initialize LSP server for a file."""
        if language not in self._servers:
            if not self.start_server(language):
                return False

        server = self._servers[language]
        if server.get("initialized"):
            return True

        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": server["process"].pid,
                "rootUri": f"file://{self.cwd}",
                "capabilities": {}
            }
        }

        response = self._send_request(language, init_request)
        if response:
            server["initialized"] = True
            self._send_notification(language, {
                "jsonrpc": "2.0",
                "method": "initialized",
                "params": {}
            })
            return True

        return False

    def _send_request(self, language: str, request: dict) -> Optional[dict]:
        """Send request to LSP server."""
        if language not in self._servers:
            return None

        server = self._servers[language]
        process = server.get("process")
        if not process or not process.stdin:
            return None

        try:
            request_json = json.dumps(request) + "\n"
            process.stdin.write(request_json)
            process.stdin.flush()

            time.sleep(0.1)

            line = process.stdout.readline()
            while line:
                if line.strip():
                    return json.loads(line)
                line = process.stdout.readline()

        except Exception:
            pass

        return None

    def _send_notification(self, language: str, notification: dict):
        """Send notification to LSP server."""
        if language not in self._servers:
            return

        server = self._servers[language]
        process = server.get("process")
        if not process or not process.stdin:
            return

        try:
            notification_json = json.dumps(notification) + "\n"
            process.stdin.write(notification_json)
            process.stdin.flush()
        except Exception:
            pass

    def get_diagnostics(self, filepath: Path) -> list[Diagnostic]:
        """Get diagnostics for a file."""
        language = self.detect_language(filepath)
        if not language:
            return []

        if not self.initialize(language, filepath):
            return []

        self._send_notification(language, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": f"file://{filepath}",
                    "languageId": language,
                    "version": 1,
                    "text": filepath.read_text() if filepath.exists() else ""
                }
            }
        })

        time.sleep(0.3)

        diagnostics_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/diagnostics",
            "params": {
                "textDocument": {"uri": f"file://{filepath}"}
            }
        }

        response = self._send_request(language, diagnostics_request)
        if not response:
            return []

        result = response.get("result", [])
        if isinstance(result, dict):
            result = result.get("items", [])

        diagnostics = []
        for item in result:
            severity_map = {1: "error", 2: "warning", 3: "info", 4: "hint"}
            diagnostics.append(Diagnostic(
                severity=severity_map.get(item.get("severity", 1), "error"),
                message=item.get("message", ""),
                line=item.get("range", {}).get("start", {}).get("line", 0) + 1,
                column=item.get("range", {}).get("start", {}).get("character", 0) + 1,
                source=item.get("source", "lsp")
            ))

        self._last_diagnostics[str(filepath)] = diagnostics
        return diagnostics

    def format_diagnostics_for_model(self, filepath: Path) -> str:
        """Format diagnostics as context for the model."""
        diagnostics = self.get_diagnostics(filepath)

        if not diagnostics:
            return ""

        lines = [f"LSP Diagnostics for {filepath.name}:"]
        for d in diagnostics:
            lines.append(f"  [{d.severity.upper()}] {d.message} (line {d.line}, col {d.column})")

        return "\n".join(lines)

    def has_errors(self, filepath: Path) -> bool:
        """Check if file has error-level diagnostics."""
        diagnostics = self.get_diagnostics(filepath)
        return any(d.severity == "error" for d in diagnostics)

    def stop_servers(self):
        """Stop all LSP servers."""
        for server in self._servers.values():
            process = server.get("process")
            if process:
                process.terminate()

        self._servers.clear()


class DiagnosticContextBuilder:
    """Build diagnostic context for model prompts."""

    def __init__(self, lsp: LSPDiagnostics | None = None):
        self.lsp = lsp or LSPDiagnostics()

    def build_fix_prompt(self, filepath: Path, tool_result: str) -> str:
        """Build a prompt with diagnostics after a tool execution."""
        diagnostics_text = self.lsp.format_diagnostics_for_model(filepath)

        if not diagnostics_text:
            return tool_result

        return f"""{tool_result}

{diagnostics_text}

Please fix any errors above and re-apply the changes."""

    def build_pre_edit_context(self, filepath: Path) -> str:
        """Get diagnostics before making edits."""
        diagnostics = self.lsp.get_diagnostics(filepath)

        if not diagnostics:
            return ""

        errors = [d for d in diagnostics if d.severity == "error"]
        warnings = [d for d in diagnostics if d.severity == "warning"]

        context = f"Current issues in {filepath.name}:\n"
        if errors:
            context += f"Errors: {len(errors)}\n"
            for e in errors[:3]:
                context += f"  - {e.message} (line {e.line})\n"
        if warnings:
            context += f"Warnings: {len(warnings)}\n"

        return context