"""APEX Declarative Slash Commands.

Modelled on OpenCode's in-session commands (.opencode/command/*.md) with
frontmatter V2:

- name, description, model, variant, subtask, template, agent
- Template variables: $ARGUMENTS, $1, $2, $3
- Shell interpolation: !`command` (executed inline)
- Subtask/subagent execution via Core's command service
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from apex.core.service import Core
from apex.hooks import PluginHooks
from apex.schema import CommandID, CommandInfo
from apex.utils.frontmatter import parse_frontmatter_document

__all__ = [
    "CommandDiscovery",
    "CommandResult",
    "DeclarativeCommandManager",
    "parse_command_md",
]


# ---------------------------------------------------------------------------
# Command frontmatter parsing
# ---------------------------------------------------------------------------


def parse_command_md(content: str, path: str) -> CommandInfo | None:
    """Parse a command markdown file into a :class:`CommandInfo`.

    Frontmatter fields:
      - description (required)
      - model (optional)
      - variant (optional)
      - subtask (bool, optional)
      - agent (optional)
      - template (optional)
    """
    metadata, body = parse_frontmatter_document(content)
    if metadata is None:
        return None

    name = Path(path).stem
    return CommandInfo(
        id=CommandID(name),
        name=name,
        description=metadata.get("description", ""),
        model=metadata.get("model"),
        variant=metadata.get("variant"),
        subtask=bool(metadata.get("subtask", False)),
        agent=metadata.get("agent"),
        template=metadata.get("template"),
        metadata={
            "path": path,
            "body": body,
        },
    )


# ---------------------------------------------------------------------------
# Command discovery
# ---------------------------------------------------------------------------


class CommandDiscovery:
    """Scan directories for command markdown files."""

    def __init__(self, roots: list[str]) -> None:
        self.roots = roots

    def discover(self) -> dict[str, CommandInfo]:
        commands: dict[str, CommandInfo] = {}
        for root in self.root_iter():
            if not root.exists():
                continue
            for md in root.rglob("*.md"):
                if md.name == "SKILL.md":
                    continue
                try:
                    content = md.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                cmd = parse_command_md(content, str(md))
                if cmd is not None:
                    commands[cmd.id.value] = cmd
        return commands

    def root_iter(self):
        for root in self.roots:
            yield Path(root)


# ---------------------------------------------------------------------------
# Declarative command manager
# ---------------------------------------------------------------------------


@dataclass
class CommandResult:
    output: str
    exit_code: int
    shell_commands: list[str] = field(default_factory=list)


class DeclarativeCommandManager:
    """Register and execute declarative slash commands."""

    def __init__(
        self,
        core: Core,
        hooks: PluginHooks,
        roots: list[str] | None = None,
    ) -> None:
        self.core = core
        self.hooks = hooks
        self.roots = roots or [".opencode/command", ".opencode/commands", ".apex/commands"]
        self._discovery = CommandDiscovery(self.roots)
        self._commands: dict[str, CommandInfo] = {}

    def load(self) -> dict[str, CommandInfo]:
        """Discover and register all commands from the configured roots."""
        commands = self._discovery.discover()
        for cmd in commands.values():
            self.core.command.register(cmd)
            self._commands[cmd.id.value] = cmd
            self.hooks.trigger(
                "command", "registered", {"command_id": cmd.id.value, "path": cmd.metadata.get("path")}
            )
        return self._commands

    def reload(self) -> dict[str, CommandInfo]:
        """Clear and re-discover all commands."""
        self._commands.clear()
        return self.load()

    def list(self) -> dict[str, CommandInfo]:
        return dict(self._commands)

    # -- execution ---------------------------------------------------------

    def render_template(self, cmd: CommandInfo, arguments: str) -> str:
        r"""Interpolate template variables ($ARGUMENTS, $1..$3) and shell
        interpolation (!\`cmd\`)."""
        body = cmd.metadata.get("body", "") if cmd.metadata else ""
        template = cmd.template or body

        parts = arguments.split()
        replacements: dict[str, str] = {
            "$ARGUMENTS": arguments,
        }
        for i in range(1, 10):
            replacements[f"${i}"] = parts[i - 1] if i - 1 < len(parts) else ""

        def replace_shell(match: re.Match[str]) -> str:
            shell_cmd = match.group(1)
            try:
                result = subprocess.run(
                    shell_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
                return result.stdout or result.stderr
            except Exception as exc:  # noqa: BLE001
                return f"[shell error: {exc}]"

        rendered = re.sub(r"!`([^`]+)`", replace_shell, template)

        for key, value in replacements.items():
            rendered = rendered.replace(key, value)

        return rendered

    def execute(
        self,
        command_id: str,
        arguments: str = "",
        provider_id: str | None = None,
    ) -> CommandResult:
        """Execute a registered command."""
        cmd = self.core.command.resolve(command_id)
        if cmd is None:
            return CommandResult(
                output=f"[error] unknown command: {command_id}",
                exit_code=1,
            )

        rendered = self.render_template(cmd, arguments)
        shell_commands: list[str] = []

        for match in re.finditer(r"!`([^`]+)`", rendered):
            shell_commands.append(match.group(1))

        self.hooks.trigger(
            "command",
            "executed",
            {
                "command_id": cmd.id.value,
                "arguments": arguments,
                "subtask": cmd.subtask,
                "provider_id": provider_id,
            },
        )

        if cmd.subtask:
            return CommandResult(
                output=(
                    f"[subtask] {cmd.name}\n{rendered}\n"
                    f"---\nDelegate to subagent '{cmd.agent or cmd.name}'"
                ),
                exit_code=0,
                shell_commands=shell_commands,
            )

        return CommandResult(
            output=rendered,
            exit_code=0,
            shell_commands=shell_commands,
        )
