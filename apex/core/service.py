"""APEX Core — Heart of the agent platform.

Provides the Agent, Command and Skill services that operate exclusively on
the typed definitions in ``apex.schema``.  This module is intentionally
free of CLI, TUI, HTTP or filesystem concerns so it can be reused by any
surface (CLI, TUI, HTTP server, MCP, tests).
"""

from __future__ import annotations

from typing import Optional

from apex.schema import (
    AgentID,
    AgentInfo,
    AgentPermission,
    CommandID,
    CommandInfo,
    SkillID,
    SkillInfo,
)

__all__ = ["AgentService", "CommandService", "SkillService", "Core"]


# ---------------------------------------------------------------------------
# Agent Service
# ---------------------------------------------------------------------------


class AgentService:
    """Manage agent definitions.

    Responsibilities:
      - register / resolve / list agents
      - evaluate whether an agent may execute a tool
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentInfo] = {}

    # -- registration -------------------------------------------------------

    def register(self, agent: AgentInfo) -> None:
        self._agents[agent.id.value] = agent

    def unregister(self, agent_id: AgentID) -> None:
        self._agents.pop(agent_id.value, None)

    # -- queries ------------------------------------------------------------

    def get(self, agent_id: AgentID) -> Optional[AgentInfo]:
        return self._agents.get(agent_id.value)

    def resolve(self, name_or_id: str) -> Optional[AgentInfo]:
        """Resolve an agent by id or by name."""
        if name_or_id in self._agents:
            return self._agents[name_or_id]
        for agent in self._agents.values():
            if agent.name == name_or_id:
                return agent
        return None

    def list(self) -> tuple[AgentInfo, ...]:
        return tuple(self._agents.values())

    # -- permission ---------------------------------------------------------

    def can_execute_tool(self, agent_id: AgentID, tool: str) -> tuple[bool, Optional[str]]:
        """Return ``(allowed, reason)`` for an agent + tool.

        Resolution order (first match wins):
          1. explicit deny rule matching the tool
          2. explicit allow rule matching the tool
          3. catch-all ``*`` rule
        """
        agent = self.get(agent_id)
        if agent is None:
            return False, f"unknown agent {agent_id.value}"

        for perm in agent.permissions:
            pattern = perm.pattern or perm.tool
            matches = (
                pattern is None
                or pattern == "*"
                or pattern == tool
                or pattern.endswith("*")
                and tool.startswith(pattern[:-1])
            )
            if not matches:
                continue
            if perm.action == "DENY":
                return False, f"tool '{tool}' denied for agent {agent.name}"
            if perm.action == "ALLOW":
                return True, f"tool '{tool}' allowed for agent {agent.name}"

        # No rule matched — fall back to ASK semantics (deny by default here
        # so callers must explicitly opt-in to interactive prompts).
        return False, f"no permission rule for tool '{tool}' on agent {agent.name}"


# ---------------------------------------------------------------------------
# Command Service
# ---------------------------------------------------------------------------


class CommandService:
    """Manage slash commands."""

    def __init__(self) -> None:
        self._commands: dict[str, CommandInfo] = {}

    def register(self, command: CommandInfo) -> None:
        self._commands[command.id.value] = command

    def unregister(self, command_id: CommandID) -> None:
        self._commands.pop(command_id.value, None)

    def get(self, command_id: CommandID) -> Optional[CommandInfo]:
        return self._commands.get(command_id.value)

    def resolve(self, name_or_id: str) -> Optional[CommandInfo]:
        if name_or_id in self._commands:
            return self._commands[name_or_id]
        for cmd in self._commands.values():
            if cmd.name == name_or_id:
                return cmd
        return None

    def list(self) -> tuple[CommandInfo, ...]:
        return tuple(self._commands.values())


# ---------------------------------------------------------------------------
# Skill Service
# ---------------------------------------------------------------------------


class SkillService:
    """Manage skill definitions."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillInfo] = {}
        self._files: dict[str, tuple[str, ...]] = {}

    def register(self, skill: SkillInfo) -> None:
        self._skills[skill.id.value] = skill

    def unregister(self, skill_id: SkillID) -> None:
        self._skills.pop(skill_id.value, None)
        self._files.pop(skill_id.value, None)

    def get(self, skill_id: SkillID) -> Optional[SkillInfo]:
        return self._skills.get(skill_id.value)

    def resolve(self, name_or_id: str) -> Optional[SkillInfo]:
        if name_or_id in self._skills:
            return self._skills[name_or_id]
        for skill in self._skills.values():
            if skill.name == name_or_id:
                return skill
        return None

    def list(self) -> tuple[SkillInfo, ...]:
        return tuple(self._skills.values())

    def files(self, skill_id: SkillID) -> tuple[str, ...]:
        return self._files.get(skill_id.value, ())

    def set_files(self, skill_id: SkillID, files: tuple[str, ...]) -> None:
        self._files[skill_id.value] = files


# ---------------------------------------------------------------------------
# Core facade
# ---------------------------------------------------------------------------


class Core:
    """Single entry point exposing all Core services."""

    def __init__(self) -> None:
        self.agent = AgentService()
        self.command = CommandService()
        self.skill = SkillService()

    def register_builtins(self) -> None:
        """Register the built-in agents/commands/skills shipped with APEX."""
        # Built-in primary agents -------------------------------------------
        self.agent.register(
            AgentInfo(
                id=AgentID("build"),
                name="build",
                model="claude-sonnet-4-5",
                mode="primary",
                color="#00e5ff",
                description="Full-access development agent",
            )
        )
        self.agent.register(
            AgentInfo(
                id=AgentID("plan"),
                name="plan",
                model="claude-sonnet-4-5",
                mode="subagent",
                color="#a855f7",
                description="Read-only architecture & planning agent",
                permissions=(
                    AgentPermission(tool="read_file", action="ALLOW"),
                    AgentPermission(tool="grep", action="ALLOW"),
                    AgentPermission(tool="glob", action="ALLOW"),
                    AgentPermission(tool="*", action="ASK"),
                ),
            )
        )
        self.agent.register(
            AgentInfo(
                id=AgentID("shell"),
                name="shell",
                model="claude-sonnet-4-5",
                mode="primary",
                color="#f97316",
                description="Infrastructure, DevOps, CI/CD",
                permissions=(AgentPermission(tool="*", action="ASK"),),
            )
        )


__all__ = ["Core", "AgentService", "CommandService", "SkillService"]
