"""APEX Schema — Typed definitions for Agent, Command, Skill, Config.

Modelled on OpenCode's Effect schema (@opencode/schema) but expressed in
pure Python (dataclasses + typing) so the core can be imported without
the Effect runtime.

This module is the *single source of truth* for the shape of every
configured object in APEX.  The Core service layer
(``apex.core.service``) operates exclusively on these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------

AgentMode = Literal["primary", "subagent", "all"]
PermissionAction = Literal["ALLOW", "DENY", "ASK"]


@dataclass(frozen=True)
class AgentID:
    """Opaque identifier for an agent."""

    value: str


@dataclass(frozen=True)
class CommandID:
    """Opaque identifier for a command."""

    value: str


@dataclass(frozen=True)
class SkillID:
    """Opaque identifier for a skill."""

    value: str


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentPermission:
    tool: str
    action: PermissionAction
    pattern: str | None = None


@dataclass(frozen=True)
class AgentInfo:
    id: AgentID
    name: str
    model: str
    mode: AgentMode = "primary"
    hidden: bool = False
    color: str | None = None
    steps: int | None = None
    permissions: tuple[AgentPermission, ...] = ()
    description: str | None = None
    system: str | None = None
    variant: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommandInfo:
    id: CommandID
    name: str
    description: str
    model: str | None = None
    variant: str | None = None
    subtask: bool = False
    template: str | None = None
    agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Skill
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillInfo:
    id: SkillID
    name: str
    description: str
    path: str
    autoinvoke: bool = False
    disable_model_invocation: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MCPServerConfig:
    type: Literal["remote", "local"]
    url: str | None = None
    command: tuple[str, ...] | None = None
    environment: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolConfig:
    name: str
    enabled: bool = True
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class APEXConfig:
    provider: dict[str, Any] = field(default_factory=dict)
    permission: dict[str, Any] = field(default_factory=dict)
    mcp: dict[str, MCPServerConfig] = field(default_factory=dict)
    tools: tuple[ToolConfig, ...] = ()
    experimental: dict[str, Any] = field(default_factory=dict)
    skills: dict[str, Any] = field(default_factory=dict)
    agents: dict[str, Any] = field(default_factory=dict)
    commands: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentUpdated:
    agent_id: AgentID


@dataclass(frozen=True)
class SkillUpdated:
    skill_id: SkillID


@dataclass(frozen=True)
class CommandUpdated:
    command_id: CommandID


__all__ = [
    "APEXConfig",
    "AgentID",
    "AgentInfo",
    "AgentMode",
    "AgentPermission",
    "AgentUpdated",
    "CommandID",
    "CommandInfo",
    "CommandUpdated",
    "MCPServerConfig",
    "PermissionAction",
    "SkillID",
    "SkillInfo",
    "SkillUpdated",
    "ToolConfig",
]
