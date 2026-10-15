"""Custom commands system for APEX — mirrors OpenCode custom commands UX.

Loading hierarchy (later overrides earlier):
  1. Built-in defaults (/test, /review, /commit, /docs)
  2. Global:   ~/.config/apex/commands/*.md
  3. Project:  .apex/commands/*.md
  4. Config:   apex_config.command dict
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .config_v2 import apex_config

if TYPE_CHECKING:
    from .agent import Agent


# ────────────────────────────────────────────────────────────
# CommandConfig
# ────────────────────────────────────────────────────────────


@dataclass
class CommandConfig:
    name: str
    template: str
    description: str = ""
    agent: str | None = None
    model: str | None = None
    subtask: bool = False


# ────────────────────────────────────────────────────────────
# Built-in defaults (can be overridden by user commands)
# ────────────────────────────────────────────────────────────

_BUILTIN_COMMANDS: dict[str, CommandConfig] = {
    "test": CommandConfig(
        name="test",
        template="Run the full test suite for this project. Show the results including any failures or errors. If there are failures, analyze them and suggest fixes. Fix any failing tests.",
        description="Run tests",
        agent="build",
    ),
    "review": CommandConfig(
        name="review",
        template="Review the current uncommitted changes in this project. Analyze the diff, provide feedback on code quality, potential bugs, security issues, and suggest improvements.",
        description="Review current changes",
        agent="reviewer",
    ),
    "commit": CommandConfig(
        name="commit",
        template="Analyze the current changes in the repository. Create a concise, well-structured commit message summarizing the changes. Stage all modified files and commit with the generated message.",
        description="Commit with AI message",
        agent="build",
    ),
    "docs": CommandConfig(
        name="docs",
        template="Generate documentation for the recent changes and the relevant parts of the codebase. Focus on APIs, public interfaces, and any new functionality.",
        description="Generate documentation",
        agent="plan",
    ),
}


# ────────────────────────────────────────────────────────────
# YAML frontmatter parser (stdlib only)
# ────────────────────────────────────────────────────────────


def _parse_yaml_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text

    end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break

    if end == -1:
        return {}, text

    frontmatter_lines = lines[1:end]
    body = "\n".join(lines[end + 1 :]).strip()

    result: dict[str, Any] = {}
    for line in frontmatter_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val.lower() in ("true", "false"):
                val = val.lower() == "true"
            elif val == "" or val == "null":
                val = None
            result[key] = val

    return result, body


# ────────────────────────────────────────────────────────────
# Template rendering
# ────────────────────────────────────────────────────────────


def _render_template(template: str, args: list[str], project_dir: str) -> str:
    result = template

    result = result.replace("$ARGUMENTS", " ".join(args))

    for i, arg in enumerate(args, start=1):
        result = result.replace(f"${i}", arg)

    def _exec_shell(m: re.Match) -> str:
        cmd = m.group(1).strip()
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=project_dir,
            )
            return proc.stdout.strip() or proc.stderr.strip()
        except subprocess.TimeoutExpired:
            return ""
        except Exception:
            return ""

    result = re.sub(r"!([^\n]+)", _exec_shell, result)

    def _include_file(m: re.Match) -> str:
        path_str = m.group(1).strip()
        p = Path(path_str)
        if not p.is_absolute():
            p = Path(project_dir) / p
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")
        return ""

    result = re.sub(r"@(\S+)", _include_file, result)

    return result


# ────────────────────────────────────────────────────────────
# CustomCommandManager
# ────────────────────────────────────────────────────────────


class CustomCommandManager:
    def __init__(self) -> None:
        self._commands: dict[str, CommandConfig] = {}
        self._load_builtins()

    def _load_builtins(self) -> None:
        self._commands.clear()
        for name, cmd in _BUILTIN_COMMANDS.items():
            self._commands[name] = cmd

    def load_all(self, project_dir: str | None = None) -> None:
        self._load_builtins()

        resolved = project_dir or os.getcwd()

        global_dir = Path.home() / ".config" / "apex" / "commands"
        if global_dir.is_dir():
            self._load_from_dir(global_dir)

        project_cmds = Path(resolved) / ".apex" / "commands"
        if project_cmds.is_dir():
            self._load_from_dir(project_cmds)

        config_cmds = apex_config.command
        for name, cfg in config_cmds.items():
            if isinstance(cfg, dict):
                self._commands[name] = CommandConfig(
                    name=name,
                    template=cfg.get("template", ""),
                    description=cfg.get("description", ""),
                    agent=cfg.get("agent"),
                    model=cfg.get("model"),
                    subtask=bool(cfg.get("subtask", False)),
                )

    def _load_from_dir(self, directory: Path) -> None:
        for md_file in sorted(directory.glob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
                frontmatter, body = _parse_yaml_frontmatter(content)
                name = md_file.stem
                self._commands[name] = CommandConfig(
                    name=name,
                    template=body or content,
                    description=frontmatter.get("description", ""),
                    agent=frontmatter.get("agent"),
                    model=frontmatter.get("model"),
                    subtask=bool(frontmatter.get("subtask", False)),
                )
            except Exception:
                continue

    def get(self, name: str) -> CommandConfig | None:
        return self._commands.get(name)

    def list(self) -> list[CommandConfig]:
        return list(self._commands.values())

    def add(self, config: CommandConfig) -> None:
        self._commands[config.name] = config

    def remove(self, name: str) -> bool:
        if name in self._commands:
            del self._commands[name]
            return True
        return False

    def render_template(self, template: str, args: list[str], project_dir: str) -> str:
        return _render_template(template, args, project_dir)

    def execute(self, name: str, args: list[str], agent: Agent) -> str:
        cmd = self.get(name)
        if cmd is None:
            return f"ERROR: Unknown command: {name}"

        project_dir = str(getattr(agent, "cwd", Path.cwd()))
        prompt = self.render_template(cmd.template, args, project_dir)

        if cmd.model and hasattr(agent, "switch_model"):
            agent.switch_model(cmd.model)

        if cmd.agent and hasattr(agent, "switch_agent"):
            agent.switch_agent(cmd.agent)

        return agent.chat(prompt)


# ────────────────────────────────────────────────────────────
# Singleton
# ────────────────────────────────────────────────────────────

commands_manager = CustomCommandManager()


__all__ = [
    "CommandConfig",
    "CustomCommandManager",
    "commands_manager",
]
