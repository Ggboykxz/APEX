"""User-interaction tools: clipboard, prompts, files, skills and themes.

Split out of ``apex.tools`` so that module keeps a single
responsibility: the tool executor core.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "UxToolsMixin",
]


class UxToolsMixin:
    def _execute_clipboard_read(self, args: dict[str, Any]) -> str:
        try:
            import pyperclip

            return pyperclip.paste()
        except ImportError:
            try:
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    return result.stdout
            except Exception:
                logger.exception("Clipboard read via xclip failed")
            return "ERROR: No clipboard tool available. Install pyperclip or xclip."
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Cannot read clipboard: {e}"

    def _execute_clipboard_write(self, args: dict[str, Any]) -> str:
        text = args["text"]
        try:
            import pyperclip

            pyperclip.copy(text)
            return f"SUCCESS: Copied {len(text)} chars to clipboard"
        except ImportError:
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                return f"SUCCESS: Copied {len(text)} chars to clipboard"
            except Exception:
                logger.exception("Clipboard write via xclip failed")
            return "ERROR: No clipboard tool available. Install pyperclip or xclip."
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Cannot write to clipboard: {e}"

    def _execute_ask_user(self, args: dict[str, Any]) -> str:
        question = args["question"]
        options = args.get("options", [])
        return f"[WAITING FOR USER INPUT]\nQuestion: {question}\nOptions: {options if options else 'Free text answer'}\n\nUse /answer <response> to reply."

    def _execute_select_files(self, args: dict[str, Any]) -> str:
        patterns = args.get("patterns", [])
        if not patterns:
            return "ERROR: No patterns provided"

        from pathlib import Path

        files = []
        for pattern in patterns:
            for p in Path(self.cwd).rglob(pattern):
                if p.is_file():
                    files.append(str(p.relative_to(self.cwd)))

        if not files:
            return f"No files found matching: {patterns}"

        return f"Selected {len(files)} files:\n" + "\n".join(files[:20])

    def _execute_retry_last(self, args: dict[str, Any]) -> str:
        last_tool = getattr(self, "_last_tool", None)
        last_args = getattr(self, "_last_args", None)

        if not last_tool or not last_args:
            return "ERROR: No previous tool to retry"

        return self.execute(last_tool, last_args)

    def _execute_retry_tool(self, args: dict[str, Any]) -> str:
        from .advanced import get_retry_handler

        tool_name = args["tool"]
        tool_args = args.get("args", {})
        retries = args.get("retries", 3)

        handler = get_retry_handler()
        handler.config.max_retries = retries

        try:
            result = handler.execute(self.execute, tool_name, tool_args)
            return f"SUCCESS after {retries} retries:\n{result}"
        except Exception as e:  # noqa: BLE001
            return f"ERROR after {retries} retries: {e}"

    def _execute_list_skills(self, args: dict[str, Any]) -> str:
        from .skills import get_skill_manager

        sm = get_skill_manager(str(self.cwd))
        skills = sm.list_skills()
        if not skills:
            return "No skills available. Create .apex/skills/*.md files."
        output = ["Available skills:"]
        for s in skills:
            output.append(f"  {s['name']} - {s['description']}")
        return "\n".join(output)

    def _execute_use_skill(self, args: dict[str, Any]) -> str:
        from .skills import get_skill_manager

        name = args["name"]
        skill_args = args.get("args", {})
        sm = get_skill_manager(str(self.cwd))
        result = sm.render(name, **skill_args)
        if result is None:
            return f"ERROR: Skill '{name}' not found"
        return f"[SKILL: {name}]\n{result}"

    def _execute_get_keybindings(self, args: dict[str, Any]) -> str:
        return """Keyboard Shortcuts:
================
Tab         - Cycle agents
Ctrl+C      - Cancel
Ctrl+D      - Exit
Ctrl+L     - Clear screen
Ctrl+U     - Clear line
Up/Down    - History
Ctrl+R     - Search history
"""

    def _execute_set_theme(self, args: dict[str, Any]) -> str:
        theme = args.get("theme", "")
        themes = ["default", "dark", "light", "monokai", "dracula", "nord"]
        if theme not in themes:
            return f"Available themes: {', '.join(themes)}"
        return f"Theme set to: {theme}"
