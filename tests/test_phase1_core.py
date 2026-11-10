"""Tests unitaires pour le cœur APEX (Phase 1 — parité OpenCode).

Couvre :
  - apex.schema : définitions typées Agent / Command / Skill / Config
  - apex.core   : services Agent, Command, Skill (enregistrement, résolution,
                  évaluation des permissions)
  - apex.plugin : définition, enregistrement et activation de plugins
  - apex.hooks  : enregistrement, déclenchement et refus (HookError)

Exécution : ``python3 -B tests/test_phase1_core.py``
"""

from __future__ import annotations

import asyncio
import sys

from apex.core import Core
from apex.hooks import HookError, PluginHooks
from apex.plugin import PluginManager, define
from apex.schema import (
    AgentID,
    AgentInfo,
    CommandID,
    CommandInfo,
    SkillID,
    SkillInfo,
)

# ---------------------------------------------------------------------------
# Agent service
# ---------------------------------------------------------------------------

def test_agent_register_and_list():
    core = Core()
    core.register_builtins()
    names = {a.name for a in core.agent.list()}
    assert {"build", "plan", "shell"} <= names


def test_agent_can_execute_tool_allow():
    core = Core()
    core.register_builtins()
    allowed, reason = core.agent.can_execute_tool(AgentID("plan"), "read_file")
    assert allowed is True
    assert "allowed" in reason


def test_agent_can_execute_tool_deny_by_default():
    core = Core()
    core.register_builtins()
    allowed, reason = core.agent.can_execute_tool(AgentID("plan"), "rm -rf /")
    assert allowed is False
    assert "no permission rule" in reason


def test_agent_resolve_by_name():
    core = Core()
    core.register_builtins()
    agent = core.agent.resolve("build")
    assert agent is not None
    assert agent.id.value == "build"


# ---------------------------------------------------------------------------
# Command service
# ---------------------------------------------------------------------------

def test_command_register_resolve():
    core = Core()
    core.command.register(
        CommandInfo(
            id=CommandID("commit"),
            name="commit",
            description="Commit changes",
            subtask=True,
        )
    )
    cmd = core.command.resolve("commit")
    assert cmd is not None
    assert cmd.name == "commit"
    assert cmd.subtask is True


# ---------------------------------------------------------------------------
# Skill service
# ---------------------------------------------------------------------------

def test_skill_register_resolve():
    core = Core()
    core.skill.register(
        SkillInfo(
            id=SkillID("frontend-design"),
            name="frontend-design",
            description="UI pro",
            path="skills/frontend-design",
        )
    )
    skill = core.skill.resolve("frontend-design")
    assert skill is not None
    assert skill.path == "skills/frontend-design"


# ---------------------------------------------------------------------------
# Plugin system
# ---------------------------------------------------------------------------

async def test_plugin_activation_async():
    core = Core()
    pm = PluginManager(core)

    async def effect(ctx):
        ctx.agent.register(
            AgentInfo(
                id=AgentID("plugin-agent"),
                name="plugin-agent",
                model="gpt-5",
                mode="subagent",
            )
        )

    plugin = define("test-plugin", effect)
    pm.register(plugin)
    assert pm.is_activated("test-plugin") is False

    await pm.activate("test-plugin")
    assert pm.is_activated("test-plugin") is True
    assert any(a.name == "plugin-agent" for a in core.agent.list())


def test_plugin_activation():
    asyncio.run(test_plugin_activation_async())


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

def test_hook_trigger():
    hooks = PluginHooks()
    seen = []

    hooks.register("tool", "execute.before", lambda e: seen.append(e["tool"]))
    err = hooks.trigger_tool_before({"tool": "bash"})
    assert err is None
    assert seen == ["bash"]


def test_hook_denial():
    hooks = PluginHooks()

    def deny(event):
        raise HookError("blocked by policy")

    hooks.register("tool", "execute.before", deny)
    err = hooks.trigger_tool_before({"tool": "rm"})
    assert err is not None
    assert "blocked" in str(err)


# ---------------------------------------------------------------------------
# Schema types
# ---------------------------------------------------------------------------

def test_agent_info_defaults():
    agent = AgentInfo(
        id=AgentID("x"),
        name="x",
        model="m",
    )
    assert agent.mode == "primary"
    assert agent.hidden is False
    assert agent.permissions == ()


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        ("agent_register_and_list", test_agent_register_and_list),
        ("agent_can_execute_tool_allow", test_agent_can_execute_tool_allow),
        ("agent_can_execute_tool_deny_by_default", test_agent_can_execute_tool_deny_by_default),
        ("agent_resolve_by_name", test_agent_resolve_by_name),
        ("command_register_resolve", test_command_register_resolve),
        ("skill_register_resolve", test_skill_register_resolve),
        ("plugin_activation", test_plugin_activation),
        ("hook_trigger", test_hook_trigger),
        ("hook_denial", test_hook_denial),
        ("agent_info_defaults", test_agent_info_defaults),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {name}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)
    print("=== TOUS LES TESTS PHASE 1 REUSSIS ===")
