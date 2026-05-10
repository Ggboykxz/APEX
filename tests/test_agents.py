"""Tests for APEX multi-agent system."""

from apex.agents import (
    AgentConfig,
    AgentManager,
    BUILTIN_AGENTS,
    agent_manager,
    PERMISSION_ALLOW,
    PERMISSION_DENY,
)


def test_builtin_agents_exist():
    assert "build" in BUILTIN_AGENTS
    assert "plan" in BUILTIN_AGENTS
    assert "explore" in BUILTIN_AGENTS
    assert "general" in BUILTIN_AGENTS


def test_build_agent_permissions():
    build = BUILTIN_AGENTS["build"]
    assert build.permission["read"] == PERMISSION_ALLOW
    assert build.permission["edit"] == PERMISSION_ALLOW
    assert build.permission["bash"] == PERMISSION_ALLOW


def test_plan_agent_permissions():
    plan = BUILTIN_AGENTS["plan"]
    assert plan.permission["read"] == PERMISSION_ALLOW
    assert plan.permission["edit"] == PERMISSION_DENY
    assert plan.permission["bash"] == PERMISSION_DENY


def test_explore_agent_permissions():
    explore = BUILTIN_AGENTS["explore"]
    assert explore.permission["read"] == PERMISSION_ALLOW
    assert explore.permission["edit"] == PERMISSION_DENY


def test_agent_manager_get():
    manager = AgentManager()
    build = manager.get("build")
    assert build is not None
    assert build.name == "build"


def test_agent_manager_list_primary():
    manager = AgentManager()
    primary = manager.list_agents("primary")
    names = [a.name for a in primary]
    assert "build" in names
    assert "plan" in names
    assert "explore" not in names


def test_agent_manager_list_subagent():
    manager = AgentManager()
    subagents = manager.list_agents("subagent")
    names = [a.name for a in subagents]
    assert "explore" in names
    assert "general" in names
    assert "build" not in names


def test_agent_manager_check_permission():
    manager = AgentManager()
    assert manager.check_permission("build", "read") == PERMISSION_ALLOW
    assert manager.check_permission("plan", "edit") == PERMISSION_DENY
    assert manager.check_permission("plan", "bash") == PERMISSION_DENY


def test_agent_manager_can_execute_tool():
    manager = AgentManager()

    allowed, msg = manager.can_execute_tool("build", "read_file")
    assert allowed is True

    allowed, msg = manager.can_execute_tool("plan", "write_file")
    assert allowed is False
    assert "denied" in msg


def test_agent_manager_get_tool_category():
    manager = AgentManager()

    assert manager._get_tool_category("read_file") == "read"
    assert manager._get_tool_category("write_file") == "edit"
    assert manager._get_tool_category("run_command") == "bash"
    assert manager._get_tool_category("web_search") == "websearch"


def test_custom_agent_registration():
    manager = AgentManager()
    custom = AgentConfig(
        name="review",
        description="Code review agent",
        system_prompt="You are a reviewer",
        mode="subagent",
        permission={"read": PERMISSION_ALLOW, "edit": PERMISSION_DENY},
    )
    manager.register(custom)

    assert manager.get("review") is not None
    assert manager.get("review").name == "review"


def test_agent_config_attributes():
    config = AgentConfig(
        name="test",
        description="Test agent",
        system_prompt="Test prompt",
        mode="subagent",
        model="gpt-4o",
        temperature=0.5,
        max_steps=10,
    )
    assert config.name == "test"
    assert config.mode == "subagent"
    assert config.model == "gpt-4o"
    assert config.temperature == 0.5
    assert config.max_steps == 10


def test_agent_manager_global():
    assert agent_manager.get("build") is not None
    assert agent_manager.get("plan") is not None