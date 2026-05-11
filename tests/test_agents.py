"""Tests for APEX multi-agent system — apex/agents.py.

Complete coverage of AgentConfig, AgentManager, BUILTIN_AGENTS, permission
constants, and the global agent_manager singleton.  No mocks.
"""

from apex.agents import (
    AGENT_ARCHITECT_PROMPT,
    AGENT_CODER_PROMPT,
    AGENT_PLANNER_PROMPT,
    AGENT_REVIEWER_PROMPT,
    AGENT_SHELL_PROMPT,
    BUILTIN_AGENTS,
    PERMISSION_ALLOW,
    PERMISSION_ASK,
    PERMISSION_DENY,
    AgentConfig,
    AgentManager,
    agent_manager,
)


# ---------------------------------------------------------------------------
# Permission constants
# ---------------------------------------------------------------------------


class TestPermissionConstants:
    """Test permission constant values."""

    def test_permission_allow_value(self):
        assert PERMISSION_ALLOW == "allow"

    def test_permission_deny_value(self):
        assert PERMISSION_DENY == "deny"

    def test_permission_ask_value(self):
        assert PERMISSION_ASK == "ask"


# ---------------------------------------------------------------------------
# Agent prompts
# ---------------------------------------------------------------------------


class TestAgentPrompts:
    """Test that each agent prompt is a non-empty string."""

    def test_coder_prompt(self):
        assert isinstance(AGENT_CODER_PROMPT, str)
        assert len(AGENT_CODER_PROMPT) > 0
        assert "Coder" in AGENT_CODER_PROMPT

    def test_architect_prompt(self):
        assert isinstance(AGENT_ARCHITECT_PROMPT, str)
        assert len(AGENT_ARCHITECT_PROMPT) > 0
        assert "Architect" in AGENT_ARCHITECT_PROMPT

    def test_planner_prompt(self):
        assert isinstance(AGENT_PLANNER_PROMPT, str)
        assert len(AGENT_PLANNER_PROMPT) > 0
        assert "Planner" in AGENT_PLANNER_PROMPT

    def test_reviewer_prompt(self):
        assert isinstance(AGENT_REVIEWER_PROMPT, str)
        assert len(AGENT_REVIEWER_PROMPT) > 0
        assert "Reviewer" in AGENT_REVIEWER_PROMPT

    def test_shell_prompt(self):
        assert isinstance(AGENT_SHELL_PROMPT, str)
        assert len(AGENT_SHELL_PROMPT) > 0
        assert "Shell" in AGENT_SHELL_PROMPT


# ---------------------------------------------------------------------------
# AgentConfig
# ---------------------------------------------------------------------------


class TestAgentConfig:
    """Test AgentConfig dataclass-like class."""

    def test_all_attributes_set(self):
        cfg = AgentConfig(
            name="test",
            description="desc",
            system_prompt="prompt",
            mode="primary",
            model="gpt-4o",
            temperature=0.7,
            max_steps=5,
            permission={"read": PERMISSION_ALLOW},
            color="#ff0000",
        )
        assert cfg.name == "test"
        assert cfg.description == "desc"
        assert cfg.system_prompt == "prompt"
        assert cfg.mode == "primary"
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.7
        assert cfg.max_steps == 5
        assert cfg.permission == {"read": PERMISSION_ALLOW}
        assert cfg.color == "#ff0000"

    def test_default_mode(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x")
        assert cfg.mode == "primary"

    def test_default_model_is_none(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x")
        assert cfg.model is None

    def test_default_temperature(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x")
        assert cfg.temperature == 0.0

    def test_default_max_steps_is_none(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x")
        assert cfg.max_steps is None

    def test_default_permission_is_empty_dict(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x")
        assert cfg.permission == {}

    def test_default_color(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x")
        assert cfg.color == "cyan"

    def test_permission_none_becomes_empty_dict(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x", permission=None)
        assert cfg.permission == {}


# ---------------------------------------------------------------------------
# BUILTIN_AGENTS
# ---------------------------------------------------------------------------


class TestBuiltinAgents:
    """Test the five built-in agents exist and have correct attributes."""

    EXPECTED_NAMES = {"coder", "architect", "planner", "reviewer", "shell"}

    def test_all_builtin_agents_exist(self):
        assert set(BUILTIN_AGENTS.keys()) == self.EXPECTED_NAMES

    def test_coder_mode_primary(self):
        assert BUILTIN_AGENTS["coder"].mode == "primary"

    def test_architect_mode_primary(self):
        assert BUILTIN_AGENTS["architect"].mode == "primary"

    def test_planner_mode_primary(self):
        assert BUILTIN_AGENTS["planner"].mode == "primary"

    def test_reviewer_mode_subagent(self):
        assert BUILTIN_AGENTS["reviewer"].mode == "subagent"

    def test_shell_mode_primary(self):
        assert BUILTIN_AGENTS["shell"].mode == "primary"

    def test_coder_permissions_full_access(self):
        p = BUILTIN_AGENTS["coder"].permission
        assert p["read"] == PERMISSION_ALLOW
        assert p["edit"] == PERMISSION_ALLOW
        assert p["glob"] == PERMISSION_ALLOW
        assert p["grep"] == PERMISSION_ALLOW
        assert p["list"] == PERMISSION_ALLOW
        assert p["bash"] == PERMISSION_ALLOW
        assert p["task"] == PERMISSION_ALLOW
        assert p["webfetch"] == PERMISSION_ALLOW
        assert p["websearch"] == PERMISSION_ALLOW

    def test_architect_readonly_permissions(self):
        p = BUILTIN_AGENTS["architect"].permission
        assert p["read"] == PERMISSION_ALLOW
        assert p["edit"] == PERMISSION_DENY
        assert p["bash"] == PERMISSION_DENY
        assert p["task"] == PERMISSION_ALLOW

    def test_planner_readonly_no_task(self):
        p = BUILTIN_AGENTS["planner"].permission
        assert p["read"] == PERMISSION_ALLOW
        assert p["edit"] == PERMISSION_DENY
        assert p["bash"] == PERMISSION_DENY
        assert p["task"] == PERMISSION_DENY

    def test_reviewer_readonly_no_task(self):
        p = BUILTIN_AGENTS["reviewer"].permission
        assert p["read"] == PERMISSION_ALLOW
        assert p["edit"] == PERMISSION_DENY
        assert p["bash"] == PERMISSION_DENY
        assert p["task"] == PERMISSION_DENY

    def test_shell_ask_for_destructive(self):
        p = BUILTIN_AGENTS["shell"].permission
        assert p["read"] == PERMISSION_ALLOW
        assert p["edit"] == PERMISSION_ASK
        assert p["bash"] == PERMISSION_ASK
        assert p["task"] == PERMISSION_ALLOW

    def test_coder_color(self):
        assert BUILTIN_AGENTS["coder"].color == "#00e5ff"

    def test_architect_color(self):
        assert BUILTIN_AGENTS["architect"].color == "#a855f7"

    def test_planner_color(self):
        assert BUILTIN_AGENTS["planner"].color == "#ffaa00"

    def test_reviewer_color(self):
        assert BUILTIN_AGENTS["reviewer"].color == "#00ff88"

    def test_shell_color(self):
        assert BUILTIN_AGENTS["shell"].color == "#ff6b35"

    def test_coder_uses_coder_prompt(self):
        assert BUILTIN_AGENTS["coder"].system_prompt is AGENT_CODER_PROMPT

    def test_architect_uses_architect_prompt(self):
        assert BUILTIN_AGENTS["architect"].system_prompt is AGENT_ARCHITECT_PROMPT

    def test_planner_uses_planner_prompt(self):
        assert BUILTIN_AGENTS["planner"].system_prompt is AGENT_PLANNER_PROMPT

    def test_reviewer_uses_reviewer_prompt(self):
        assert BUILTIN_AGENTS["reviewer"].system_prompt is AGENT_REVIEWER_PROMPT

    def test_shell_uses_shell_prompt(self):
        assert BUILTIN_AGENTS["shell"].system_prompt is AGENT_SHELL_PROMPT

    def test_coder_description(self):
        assert "full tool access" in BUILTIN_AGENTS["coder"].description.lower()

    def test_reviewer_description(self):
        assert "review" in BUILTIN_AGENTS["reviewer"].description.lower()


# ---------------------------------------------------------------------------
# AgentManager
# ---------------------------------------------------------------------------


class TestAgentManagerInit:
    """Test AgentManager initialization."""

    def test_init_copies_builtin_agents(self):
        mgr = AgentManager()
        assert "coder" in mgr.agents
        assert "architect" in mgr.agents
        assert "planner" in mgr.agents
        assert "reviewer" in mgr.agents
        assert "shell" in mgr.agents

    def test_custom_agents_dict_exists(self):
        mgr = AgentManager()
        assert isinstance(mgr._custom_agents, dict)

    def test_agents_is_copy_not_reference(self):
        mgr = AgentManager()
        # Modifying mgr.agents should not affect BUILTIN_AGENTS
        mgr.agents["test_new"] = AgentConfig(name="test_new", description="x", system_prompt="x")
        assert "test_new" not in BUILTIN_AGENTS


class TestAgentManagerGet:
    """Test AgentManager.get()."""

    def test_get_existing_agent(self):
        mgr = AgentManager()
        cfg = mgr.get("coder")
        assert cfg is not None
        assert cfg.name == "coder"

    def test_get_nonexistent_agent(self):
        mgr = AgentManager()
        assert mgr.get("nonexistent_xyz") is None

    def test_get_returns_agentconfig(self):
        mgr = AgentManager()
        cfg = mgr.get("architect")
        assert isinstance(cfg, AgentConfig)


class TestAgentManagerRegister:
    """Test AgentManager.register()."""

    def test_register_custom_agent(self):
        mgr = AgentManager()
        custom = AgentConfig(
            name="custom_agent",
            description="A custom test agent",
            system_prompt="You are custom",
            mode="subagent",
            permission={"read": PERMISSION_ALLOW, "edit": PERMISSION_DENY},
        )
        mgr.register(custom)
        assert mgr.get("custom_agent") is not None
        assert mgr.get("custom_agent").name == "custom_agent"
        assert mgr.get("custom_agent").mode == "subagent"

    def test_register_overwrites_existing(self):
        mgr = AgentManager()
        new_coder = AgentConfig(
            name="coder",
            description="Overwritten coder",
            system_prompt="New prompt",
        )
        mgr.register(new_coder)
        assert mgr.get("coder").description == "Overwritten coder"


class TestAgentManagerListAgents:
    """Test AgentManager.list_agents()."""

    def test_list_all_agents(self):
        mgr = AgentManager()
        all_agents = mgr.list_agents()
        assert len(all_agents) == 5
        names = {a.name for a in all_agents}
        assert names == {"coder", "architect", "planner", "reviewer", "shell"}

    def test_list_all_agents_no_mode_arg(self):
        """list_agents() without mode returns all agents (covers line 259)."""
        mgr = AgentManager()
        result = mgr.list_agents(mode=None)
        assert len(result) == 5

    def test_list_primary_agents(self):
        mgr = AgentManager()
        primary = mgr.list_agents("primary")
        names = {a.name for a in primary}
        assert "coder" in names
        assert "architect" in names
        assert "planner" in names
        assert "shell" in names
        assert "reviewer" not in names

    def test_list_subagent_agents(self):
        mgr = AgentManager()
        subagents = mgr.list_agents("subagent")
        names = {a.name for a in subagents}
        assert "reviewer" in names
        assert "coder" not in names

    def test_list_agents_with_all_mode(self):
        """Agents with mode='all' should appear in any mode filter (covers line 258)."""
        mgr = AgentManager()
        all_mode_agent = AgentConfig(
            name="universal",
            description="Available in all modes",
            system_prompt="You are universal",
            mode="all",
        )
        mgr.register(all_mode_agent)

        # Should appear when filtering by "primary"
        primary = mgr.list_agents("primary")
        names = {a.name for a in primary}
        assert "universal" in names

        # Should also appear when filtering by "subagent"
        subagents = mgr.list_agents("subagent")
        names = {a.name for a in subagents}
        assert "universal" in names

        # Should appear in unfiltered list
        all_agents = mgr.list_agents()
        names = {a.name for a in all_agents}
        assert "universal" in names

    def test_list_agents_empty_mode_filter(self):
        """Filtering by a mode with no agents returns empty list."""
        mgr = AgentManager()
        result = mgr.list_agents("nonexistent_mode")
        assert result == []


class TestAgentManagerCheckPermission:
    """Test AgentManager.check_permission()."""

    def test_check_permission_allowed(self):
        mgr = AgentManager()
        assert mgr.check_permission("coder", "read") == PERMISSION_ALLOW

    def test_check_permission_denied(self):
        mgr = AgentManager()
        assert mgr.check_permission("planner", "edit") == PERMISSION_DENY

    def test_check_permission_ask(self):
        mgr = AgentManager()
        assert mgr.check_permission("shell", "edit") == PERMISSION_ASK

    def test_check_permission_missing_category_defaults_deny(self):
        mgr = AgentManager()
        # Coder doesn't have "custom_category" in its permission dict
        assert mgr.check_permission("coder", "custom_category") == PERMISSION_DENY

    def test_check_permission_nonexistent_agent_returns_deny(self):
        """check_permission for non-existent agent returns DENY (covers line 264)."""
        mgr = AgentManager()
        assert mgr.check_permission("nonexistent_agent_xyz", "read") == PERMISSION_DENY


class TestAgentManagerCanExecuteTool:
    """Test AgentManager.can_execute_tool()."""

    def test_allowed_tool(self):
        mgr = AgentManager()
        allowed, msg = mgr.can_execute_tool("coder", "read_file")
        assert allowed is True
        assert msg == ""

    def test_denied_tool(self):
        mgr = AgentManager()
        allowed, msg = mgr.can_execute_tool("planner", "write_file")
        assert allowed is False
        assert "denied" in msg

    def test_ask_permission_tool(self):
        """Tools with ASK permission return False with confirmation message (covers line 276)."""
        mgr = AgentManager()
        allowed, msg = mgr.can_execute_tool("shell", "write_file")
        assert allowed is False
        assert "requires confirmation" in msg

    def test_nonexistent_agent(self):
        mgr = AgentManager()
        allowed, msg = mgr.can_execute_tool("nonexistent", "read_file")
        assert allowed is False
        assert "denied" in msg


class TestAgentManagerGetToolCategory:
    """Test AgentManager._get_tool_category() — covers all branches."""

    def test_read_tools(self):
        mgr = AgentManager()
        read_tools = [
            "read_file",
            "list_files",
            "search_in_files",
            "glob_search",
            "get_file_tree",
            "get_git_status",
            "get_git_log",
            "git_diff",
            "get_repo_map",
            "get_language_stats",
            "fetch_url",
            "read_image",
        ]
        for tool in read_tools:
            assert mgr._get_tool_category(tool) == "read", f"{tool} should be read"

    def test_edit_tools(self):
        mgr = AgentManager()
        edit_tools = [
            "write_file",
            "edit_file",
            "delete_file",
            "create_directory",
            "run_test",
            "format_file",
            "install_package",
        ]
        for tool in edit_tools:
            assert mgr._get_tool_category(tool) == "edit", f"{tool} should be edit"

    def test_bash_tools(self):
        mgr = AgentManager()
        assert mgr._get_tool_category("run_command") == "bash"

    def test_task_tool(self):
        """'task' maps to 'task' category (covers line 312)."""
        mgr = AgentManager()
        assert mgr._get_tool_category("task") == "task"

    def test_websearch_tools(self):
        mgr = AgentManager()
        assert mgr._get_tool_category("web_search") == "websearch"

    def test_unknown_tool_defaults_to_read(self):
        """Unknown tool name defaults to 'read' category (covers line 315)."""
        mgr = AgentManager()
        assert mgr._get_tool_category("totally_unknown_tool") == "read"
        assert mgr._get_tool_category("some_new_tool_xyz") == "read"


# ---------------------------------------------------------------------------
# Global agent_manager singleton
# ---------------------------------------------------------------------------


class TestGlobalAgentManager:
    """Test the global agent_manager instance."""

    def test_is_agent_manager(self):
        assert isinstance(agent_manager, AgentManager)

    def test_has_all_builtin_agents(self):
        for name in ("coder", "architect", "planner", "reviewer", "shell"):
            assert agent_manager.get(name) is not None

    def test_coder_permissions_via_global(self):
        allowed, msg = agent_manager.can_execute_tool("coder", "read_file")
        assert allowed is True
