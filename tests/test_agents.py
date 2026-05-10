"""Tests for APEX multi-agent system."""

from apex.agents import (
    AgentConfig,
    AgentManager,
    BUILTIN_AGENTS,
    agent_manager,
    PERMISSION_ALLOW,
    PERMISSION_DENY,
    PERMISSION_ASK,
)


def test_builtin_agents_exist():
    assert "coder" in BUILTIN_AGENTS
    assert "architect" in BUILTIN_AGENTS
    assert "planner" in BUILTIN_AGENTS
    assert "reviewer" in BUILTIN_AGENTS
    assert "shell" in BUILTIN_AGENTS


def test_coder_agent_permissions():
    coder = BUILTIN_AGENTS["coder"]
    assert coder.permission["read"] == PERMISSION_ALLOW
    assert coder.permission["edit"] == PERMISSION_ALLOW
    assert coder.permission["bash"] == PERMISSION_ALLOW


def test_planner_agent_permissions():
    planner = BUILTIN_AGENTS["planner"]
    assert planner.permission["read"] == PERMISSION_ALLOW
    assert planner.permission["edit"] == PERMISSION_DENY
    assert planner.permission["bash"] == PERMISSION_DENY


def test_architect_agent_permissions():
    architect = BUILTIN_AGENTS["architect"]
    assert architect.permission["read"] == PERMISSION_ALLOW
    assert architect.permission["edit"] == PERMISSION_DENY


def test_shell_agent_permissions():
    shell = BUILTIN_AGENTS["shell"]
    assert shell.permission["read"] == PERMISSION_ALLOW
    assert shell.permission["edit"] == PERMISSION_ASK
    assert shell.permission["bash"] == PERMISSION_ASK


def test_agent_manager_get():
    manager = AgentManager()
    coder = manager.get("coder")
    assert coder is not None
    assert coder.name == "coder"


def test_agent_manager_list_primary():
    manager = AgentManager()
    primary = manager.list_agents("primary")
    names = [a.name for a in primary]
    assert "coder" in names
    assert "architect" in names
    assert "planner" in names
    assert "reviewer" not in names


def test_agent_manager_list_subagent():
    manager = AgentManager()
    subagents = manager.list_agents("subagent")
    names = [a.name for a in subagents]
    assert "reviewer" in names
    assert "coder" not in names


def test_agent_manager_check_permission():
    manager = AgentManager()
    assert manager.check_permission("coder", "read") == PERMISSION_ALLOW
    assert manager.check_permission("planner", "edit") == PERMISSION_DENY
    assert manager.check_permission("planner", "bash") == PERMISSION_DENY
    assert manager.check_permission("shell", "edit") == PERMISSION_ASK


def test_agent_manager_can_execute_tool():
    manager = AgentManager()

    allowed, msg = manager.can_execute_tool("coder", "read_file")
    assert allowed is True

    allowed, msg = manager.can_execute_tool("planner", "write_file")
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
    assert agent_manager.get("coder") is not None
    assert agent_manager.get("planner") is not None
