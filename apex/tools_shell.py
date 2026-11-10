"""Shell and process tools: commands, tests, formatters and sessions.

Split out of ``apex.tools`` so that module keeps a single
responsibility: the tool executor core.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any

from .shell_security import CommandCategory, shell_analyzer

logger = logging.getLogger(__name__)

__all__ = [
    "ShellToolsMixin",
]


class ShellToolsMixin:
    def _check_command_allowed(self, command: str) -> str | None:
        """Check a command against the shell-security policy.

        Returns the refusal message when the command must not run, ``None``
        when it is allowed.
        """
        analysis = shell_analyzer.analyze(command)

        if analysis.category == CommandCategory.DANGEROUS:
            logger.warning(f"DANGEROUS command blocked: {command}")
            return f"ERROR: DANGEROUS command blocked: {'; '.join(analysis.warnings)}"

        if analysis.requires_confirmation and analysis.category not in [
            CommandCategory.WORKING_DIR,
            CommandCategory.FILE_READ,
            CommandCategory.BUILD,
        ]:
            logger.warning(f"Restricted command: {command}")
            return (
                f"WARNING: This command requires confirmation. "
                f"Category: {analysis.category.value}, "
                f"Warnings: {'; '.join(analysis.warnings)}"
            )
        return None

    def _execute_run_command(self, args: dict[str, Any]) -> str:
        command = args["command"]

        refusal = self._check_command_allowed(command)
        if refusal is not None:
            return refusal

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            output = []
            if result.stdout:
                output.append(result.stdout)
            if result.stderr:
                output.append(f"[STDERR]\n{result.stderr}")
            if result.returncode != 0:
                output.insert(0, f"[EXIT CODE: {result.returncode}]\n")
            return "\n".join(output) if output else "[no output]"
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out after 300 seconds"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Cannot run command: {e}"

    def _execute_run_test(self, args: dict[str, Any]) -> str:
        framework = args["framework"]
        path = args.get("path", ".")

        commands = {
            "pytest": ["pytest", "-v", path],
            "jest": ["npx", "jest", path],
            "cargo": ["cargo", "test", "--", "--test-threads=1"],
            "npm": ["npm", "test", "--", path],
        }

        if framework not in commands:
            return f"ERROR: Unknown framework: {framework}. Use pytest, jest, or cargo."

        try:
            result = subprocess.run(
                commands[framework],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            output = []
            if result.stdout:
                output.append(result.stdout)
            if result.stderr:
                output.append(result.stderr)
            return "\n".join(output) if output else "[no output]"
        except subprocess.TimeoutExpired:
            return "ERROR: Tests timed out after 300 seconds"
        except FileNotFoundError:
            return f"ERROR: {framework} not found. Install it first."
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Test execution failed: {e}"

    def _execute_format_file(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: File not found: {path}"

        from .formatter import formatter_manager

        success = formatter_manager.format_file(str(path))
        if success:
            return f"SUCCESS: Formatted {path}"
        return f"ERROR: No formatter available for {path.suffix}"

    def _execute_install_package(self, args: dict[str, Any]) -> str:
        manager = args["manager"]
        package = args["package"]

        commands = {
            "pip": ["pip", "install", package],
            "npm": ["npm", "install", package],
            "yarn": ["yarn", "add", package],
            "cargo": ["cargo", "install", package],
        }

        if manager not in commands:
            return f"ERROR: Unknown package manager: {manager}"

        try:
            result = subprocess.run(
                commands[manager],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            if result.returncode == 0:
                return f"SUCCESS: Installed {package} via {manager}"
            return f"ERROR: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "ERROR: Installation timed out"
        except FileNotFoundError:
            return f"ERROR: {manager} not found"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Installation failed: {e}"

    def _execute_run_command_custom(self, args: dict[str, Any]) -> str:
        from .commands import get_command_manager

        name = args["name"]
        cmd_args = args.get("args", {})
        cm = get_command_manager(str(self.cwd))
        result = cm.execute(name, **cmd_args)
        if result is None:
            return f"ERROR: Command '{name}' not found"
        return f"[COMMAND: {name}]\n{result}"

    def _execute_start_shell(self, args: dict[str, Any]) -> str:
        shell = args.get("shell", "bash")
        from .sandbox import ShellSession

        if not hasattr(self, "_shell_session"):
            self._shell_session = ShellSession(cwd=str(self.cwd))

        if self._shell_session.start(shell=shell):
            return f"SUCCESS: {shell} shell session started\n\nUse run_shell to execute commands."
        return "ERROR: Failed to start shell session"

    def _execute_run_shell(self, args: dict[str, Any]) -> str:
        command = args["command"]
        if not hasattr(self, "_shell_session"):
            return "ERROR: No shell session. Use start_shell first."

        try:
            return self._shell_session.run(command)
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {e}"

    def _execute_close_shell(self, args: dict[str, Any]) -> str:
        if hasattr(self, "_shell_session"):
            self._shell_session.close()
            del self._shell_session
            return "SUCCESS: Shell session closed"
        return "ERROR: No shell session to close"

    def _execute_run_code(self, args: dict[str, Any]) -> str:
        code = args["code"]
        language = args.get("language", "python")
        cmd_args = args.get("args", [])

        from .sandbox import sandbox

        return sandbox.run_code(code, language, cmd_args)

    def _execute_expand_vars(self, args: dict[str, Any]) -> str:
        from .extras import ShellExpander

        text = args["text"]
        vars = args.get("vars", {})
        return ShellExpander.expand(text, vars)
