"""Refactored sandbox module - More testable."""

import subprocess
import shlex
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ALLOWED_SHELL_COMMANDS = {
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
    "top",
}

BLOCKED_PATTERNS = [
    r"\$\(",
    r"`",
    r"\$\{",
    r"\|\s*sh",
    r"rm\s+-rf",
    r"chmod\s+777",
    r">\s*/etc/",
    r"curl.*-X\s+(POST|PUT|DELETE)",
    r"wget.*--execute",
]


def _check_command_safety(command: str) -> tuple[bool, str]:
    import re

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command):
            return False, f"Blocked pattern: {pattern}"

    parts = command.strip().split()
    if parts and parts[0] not in ALLOWED_SHELL_COMMANDS:
        return False, f"Command '{parts[0]}' not allowed"

    return True, ""


class CodeExecutor:
    """Testable code executor."""

    def __init__(self, cwd: Path):
        self.cwd = cwd

    def execute_python(self, code: str, args: list = None) -> str:
        """Execute Python code."""
        cmd = ["python", "-c", code]
        if args:
            cmd.extend(args)
        try:
            result = subprocess.run(cmd, cwd=self.cwd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout if result.stdout else "[OK]"
            return f"ERROR: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "ERROR: Execution timed out after 30 seconds"
        except FileNotFoundError:
            return "ERROR: Python not found"
        except Exception as e:
            return f"ERROR: {e}"

    def execute_javascript(self, code: str, args: list = None) -> str:
        """Execute JavaScript code."""
        cmd = ["node", "-e", code]
        if args:
            cmd.extend(args)
        try:
            result = subprocess.run(cmd, cwd=self.cwd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout if result.stdout else "[OK]"
            return f"ERROR: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "ERROR: Execution timed out after 30 seconds"
        except FileNotFoundError:
            return "ERROR: Node.js not found"
        except Exception as e:
            return f"ERROR: {e}"

    def execute_shell(self, command: str) -> str:
        """Execute shell command."""
        safe, msg = _check_command_safety(command)
        if not safe:
            logger.warning(f"Blocked shell command: {msg}")
            return f"ERROR: {msg}"

        try:
            args = shlex.split(command)
            result = subprocess.run(
                args, shell=False, cwd=self.cwd, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                return result.stdout if result.stdout else "[OK]"
            return f"ERROR: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out"
        except Exception as e:
            logger.error(f"Shell execution error: {e}")
            return f"ERROR: {e}"


class CodeSandbox:
    """Testable code sandbox."""

    def __init__(self, cwd: str = "."):
        self.cwd = Path(cwd)
        self.executor = CodeExecutor(self.cwd)

    def run_code(self, code: str, language: str, args: list = None) -> str:
        """Run code in the specified language."""
        language = language.lower()

        if language == "python":
            return self.executor.execute_python(code, args)
        elif language == "javascript":
            return self.executor.execute_javascript(code, args)
        elif language in ("sh", "bash", "shell"):
            return self.executor.execute_shell(code)
        else:
            return f"ERROR: Unsupported language: {language}"

    def run_python_snippet(self, snippet: str) -> str:
        """Run a Python snippet."""
        return self.executor.execute_python(snippet)

    def run_javascript_snippet(self, snippet: str) -> str:
        """Run a JavaScript snippet."""
        return self.executor.execute_javascript(snippet)


class ShellSession:
    """Testable shell session."""

    def __init__(self, cwd: str = "."):
        self.cwd = Path(cwd)

    def run(self, command: str, cwd: Optional[str] = None) -> str:
        """Run a shell command."""
        safe, msg = _check_command_safety(command)
        if not safe:
            logger.warning(f"Blocked shell command in session: {msg}")
            return f"ERROR: {msg}"

        work_dir = Path(cwd) if cwd else self.cwd
        try:
            args = shlex.split(command)
            result = subprocess.run(
                args, shell=False, cwd=work_dir, capture_output=True, text=True, timeout=60
            )
            return result.stdout if result.returncode == 0 else f"ERROR: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out"
        except Exception as e:
            logger.error(f"Shell session error: {e}")
            return f"ERROR: {e}"

    def close(self) -> None:
        """Close the shell session."""
        pass


# Testable factory functions
def create_sandbox(cwd: str = ".") -> CodeSandbox:
    """Create a code sandbox."""
    return CodeSandbox(cwd)


def create_executor(cwd: str) -> CodeExecutor:
    """Create a code executor."""
    return CodeExecutor(Path(cwd))


def create_shell_session(cwd: str = ".") -> ShellSession:
    """Create a shell session."""
    return ShellSession(cwd)
