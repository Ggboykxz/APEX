"""Tests for APEX multi-agent system — apex/agents.py.

Complete coverage of AgentConfig, AgentManager, BUILTIN_AGENTS, permission
constants, and the global agent_manager singleton.  No mocks.
"""

import pathlib

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
from apex.config_v2 import apex_config


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

    def test_default_top_p_is_none(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x")
        assert cfg.top_p is None

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

    def test_is_primary(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x", mode="primary")
        assert cfg.is_primary is True
        assert cfg.is_subagent is False

    def test_is_subagent(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x", mode="subagent")
        assert cfg.is_primary is False
        assert cfg.is_subagent is True

    def test_is_primary_returns_true_for_all_mode(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x", mode="all")
        assert cfg.is_primary is True
        assert cfg.is_subagent is True

    def test_is_hidden(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x", hidden=True)
        assert cfg.is_hidden is True

    def test_is_hidden_false_by_default(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x")
        assert cfg.is_hidden is False

    def test_repr(self):
        cfg = AgentConfig(name="my-agent", description="x", system_prompt="x", mode="subagent", hidden=True)
        assert repr(cfg) == "AgentConfig(name='my-agent', mode='subagent', hidden=True)"

    def test_check_bash_permission_direct_bash_key(self):
        cfg = AgentConfig(
            name="test",
            description="test",
            system_prompt="test",
            permission={"bash": PERMISSION_ALLOW},
        )
        assert cfg.check_bash_permission("anything") == PERMISSION_ALLOW

    def test_check_bash_permission_glob_pattern_matches(self):
        cfg = AgentConfig(
            name="test",
            description="test",
            system_prompt="test",
            permission={"bash": PERMISSION_DENY, "bash:git clone *": PERMISSION_ALLOW},
        )
        assert cfg.check_bash_permission("git clone https://example.com") == PERMISSION_ALLOW

    def test_check_bash_permission_glob_no_match(self):
        cfg = AgentConfig(
            name="test",
            description="test",
            system_prompt="test",
            permission={"bash": PERMISSION_DENY, "bash:git clone *": PERMISSION_ALLOW},
        )
        assert cfg.check_bash_permission("rm -rf /") == PERMISSION_DENY

    def test_check_bash_permission_wildcard_fallback(self):
        cfg = AgentConfig(
            name="test",
            description="test",
            system_prompt="test",
            permission={"read": PERMISSION_ALLOW, "*": PERMISSION_ASK},
        )
        assert cfg.check_bash_permission("anything") == PERMISSION_ASK

    def test_check_bash_permission_non_bash_keys_ignored(self):
        cfg = AgentConfig(
            name="test",
            description="test",
            system_prompt="test",
            permission={"read": PERMISSION_ALLOW},
        )
        assert cfg.check_bash_permission("anything") == PERMISSION_DENY

    def test_top_p_can_be_set(self):
        cfg = AgentConfig(
            name="test",
            description="test",
            system_prompt="test",
            top_p=0.95,
        )
        assert cfg.top_p == 0.95

    def test_disabled_defaults_to_false(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x")
        assert cfg.disabled is False

    def test_disabled_can_be_set(self):
        cfg = AgentConfig(name="x", description="x", system_prompt="x", disabled=True)
        assert cfg.disabled is True


# ---------------------------------------------------------------------------
# BUILTIN_AGENTS
# ---------------------------------------------------------------------------


class TestBuiltinAgents:
    """Test the five built-in agents exist and have correct attributes."""

    EXPECTED_NAMES = {"coder", "architect", "planner", "reviewer", "shell", "general", "explore", "scout", "compaction", "title", "summary"}

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


class TestAgentManagerGetByMention:
    """Test AgentManager.get_by_mention()."""

    def test_get_by_mention_existing(self):
        mgr = AgentManager()
        agent = mgr.get_by_mention("coder")
        assert agent is not None
        assert agent.name == "coder"

    def test_get_by_mention_with_at_symbol(self):
        mgr = AgentManager()
        agent = mgr.get_by_mention("@coder")
        assert agent is not None
        assert agent.name == "coder"

    def test_get_by_mention_missing(self):
        mgr = AgentManager()
        assert mgr.get_by_mention("nonexistent_agent_xyz") is None
        assert mgr.get_by_mention("@nonexistent_agent_xyz") is None


class TestAgentManagerListAgents:
    """Test AgentManager.list_agents()."""

    def test_list_all_agents(self):
        mgr = AgentManager()
        all_agents = mgr.list_agents()
        assert len(all_agents) == 11
        names = {a.name for a in all_agents}
        assert names == {"coder", "architect", "planner", "reviewer", "shell", "general", "explore", "scout", "compaction", "title", "summary"}

    def test_list_all_agents_no_mode_arg(self):
        """list_agents() without mode returns all agents."""
        mgr = AgentManager()
        result = mgr.list_agents(mode=None)
        assert len(result) == 11

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


class TestAgentManagerListPrimary:
    """Test AgentManager.list_primary()."""

    def test_list_primary_includes_all_mode(self):
        mgr = AgentManager()
        mgr.register(AgentConfig(name="all-mode-agent", description="x", system_prompt="x", mode="all"))
        primary = mgr.list_primary()
        names = {a.name for a in primary}
        assert "all-mode-agent" in names
        assert "coder" in names

    def test_list_primary_excludes_subagent(self):
        mgr = AgentManager()
        primary = mgr.list_primary()
        names = {a.name for a in primary}
        assert "reviewer" not in names


class TestAgentManagerListSubagents:
    """Test AgentManager.list_subagents()."""

    def test_list_subagents_includes_all_mode(self):
        mgr = AgentManager()
        mgr.register(AgentConfig(name="all-mode-agent", description="x", system_prompt="x", mode="all"))
        subagents = mgr.list_subagents()
        names = {a.name for a in subagents}
        assert "all-mode-agent" in names

    def test_list_subagents_excludes_primary(self):
        mgr = AgentManager()
        subagents = mgr.list_subagents()
        names = {a.name for a in subagents}
        assert "coder" not in names


class TestAgentManagerListVisible:
    """Test AgentManager.list_visible()."""

    def test_list_visible_excludes_hidden(self):
        mgr = AgentManager()
        visible = mgr.list_visible()
        visible_names = {a.name for a in visible}
        assert "compaction" not in visible_names
        assert "title" not in visible_names
        assert "summary" not in visible_names

    def test_list_visible_includes_non_hidden(self):
        mgr = AgentManager()
        visible = mgr.list_visible()
        visible_names = {a.name for a in visible}
        assert "coder" in visible_names
        assert "reviewer" in visible_names


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


class TestAgentManagerCheckBashPermission:
    """Test AgentManager.check_bash_permission()."""

    def test_specific_bash_pattern(self):
        mgr = AgentManager()
        result = mgr.check_bash_permission("scout", "git clone https://example.com")
        assert result == PERMISSION_ALLOW

    def test_fallback_to_bash_key(self):
        mgr = AgentManager()
        result = mgr.check_bash_permission("shell", "some command")
        assert result == PERMISSION_ASK

    def test_wildcard_fallback(self):
        mgr = AgentManager()
        custom = AgentConfig(
            name="wildcard-agent",
            description="test",
            system_prompt="test",
            permission={"*": PERMISSION_ALLOW},
        )
        mgr.register(custom)
        result = mgr.check_bash_permission("wildcard-agent", "any command")
        assert result == PERMISSION_ALLOW

    def test_no_match_deny(self):
        mgr = AgentManager()
        assert mgr.check_bash_permission("reviewer", "some command") == PERMISSION_DENY

    def test_nonexistent_agent(self):
        mgr = AgentManager()
        assert mgr.check_bash_permission("nonexistent", "any command") == PERMISSION_DENY

    def test_bash_key_elif_pattern_star(self, monkeypatch):
        """Cover the elif pattern=='*' branch by making fnmatch return False for '*'."""
        import fnmatch as fnmod

        real_fnmatch = fnmod.fnmatch

        def fake_fnmatch(name, pat):
            if pat == "*":
                return False
            return real_fnmatch(name, pat)

        monkeypatch.setattr(fnmod, "fnmatch", fake_fnmatch)

        mgr = AgentManager()
        custom = AgentConfig(
            name="bash-only",
            description="test",
            system_prompt="test",
            permission={"bash": PERMISSION_ALLOW},
        )
        mgr.register(custom)
        result = mgr.check_bash_permission("bash-only", "anything")
        assert result == PERMISSION_ALLOW


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
# Loading custom agents — markdown
# ---------------------------------------------------------------------------


class TestAgentManagerParseMarkdownAgent:
    """Test AgentManager._parse_markdown_agent()."""

    def test_parse_valid_frontmatter(self, tmp_path):
        mgr = AgentManager()
        md_file = tmp_path / "my-agent.md"
        md_file.write_text("""\
---
description: A custom review agent
mode: subagent
model: gpt-4o
temperature: 0.3
top_p: 0.9
max_steps: 8
hidden: false
disabled: false
color: "#ff00ff"
permission:
  read: allow
  edit: deny
  bash: deny
---
You are a custom review agent.
""")
        config = mgr._parse_markdown_agent(md_file)
        assert config is not None
        assert config.name == "my-agent"
        assert config.description == "A custom review agent"
        assert config.mode == "subagent"
        assert config.model == "gpt-4o"
        assert config.temperature == 0.3
        assert config.top_p == 0.9
        assert config.max_steps == 8
        assert config.hidden is False
        assert config.disabled is False
        assert config.color == "#ff00ff"
        assert config.permission == {"read": "allow", "edit": "deny", "bash": "deny"}
        assert config.system_prompt == "You are a custom review agent."

    def test_parse_minimal_frontmatter(self, tmp_path):
        mgr = AgentManager()
        md_file = tmp_path / "minimal.md"
        md_file.write_text("""\
---
description: Minimal agent
---
Just a prompt.
""")
        config = mgr._parse_markdown_agent(md_file)
        assert config is not None
        assert config.name == "minimal"
        assert config.description == "Minimal agent"
        assert config.mode == "subagent"
        assert config.model is None
        assert config.temperature == 0.0
        assert config.top_p is None
        assert config.max_steps is None
        assert config.hidden is False
        assert config.disabled is False
        assert config.color == "cyan"
        assert config.permission == {}
        assert config.system_prompt == "Just a prompt."

    def test_parse_no_frontmatter_returns_none(self, tmp_path):
        mgr = AgentManager()
        md_file = tmp_path / "no-frontmatter.md"
        md_file.write_text("Just some text without frontmatter markers.")
        assert mgr._parse_markdown_agent(md_file) is None

    def test_parse_incomplete_frontmatter_returns_none(self, tmp_path):
        mgr = AgentManager()
        md_file = tmp_path / "incomplete.md"
        md_file.write_text("---\nOnly one split part")
        assert mgr._parse_markdown_agent(md_file) is None

    def test_parse_empty_yaml_frontmatter(self, tmp_path):
        mgr = AgentManager()
        md_file = tmp_path / "empty-front.md"
        md_file.write_text("""\
---
---
Body only.
""")
        config = mgr._parse_markdown_agent(md_file)
        assert config is not None
        assert config.name == "empty-front"
        assert config.description == "Custom agent: empty-front"
        assert config.permission == {}


class TestAgentManagerLoadMarkdownAgents:
    """Test AgentManager.load_markdown_agents()."""

    def test_load_from_home_dir(self, monkeypatch, tmp_path):
        home_dir = tmp_path / "home"
        agents_dir = home_dir / ".config" / "apex" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "review-bot.md").write_text("""\
---
description: Review bot from home
mode: subagent
---
You are a review bot.
""")
        monkeypatch.setattr(pathlib.Path, "home", lambda: home_dir)
        monkeypatch.setattr(pathlib.Path, "cwd", lambda: tmp_path)

        mgr = AgentManager()
        mgr.load_markdown_agents()
        agent = mgr.get("review-bot")
        assert agent is not None
        assert agent.description == "Review bot from home"
        assert agent.system_prompt == "You are a review bot."

    def test_load_from_project_dir(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "project"
        agents_dir = project_dir / ".apex" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "my-agent.md").write_text("""\
---
description: Project-level agent
mode: primary
---
You are a project agent.
""")
        monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path / "nonexistent")
        monkeypatch.setattr(pathlib.Path, "cwd", lambda: project_dir)

        mgr = AgentManager()
        mgr.load_markdown_agents()
        agent = mgr.get("my-agent")
        assert agent is not None
        assert agent.description == "Project-level agent"

    def test_load_from_both_dirs(self, monkeypatch, tmp_path):
        home_dir = tmp_path / "home"
        home_agents = home_dir / ".config" / "apex" / "agents"
        home_agents.mkdir(parents=True)
        (home_agents / "home-agent.md").write_text("""\
---
description: From home
mode: subagent
---
Home agent.
""")
        project_dir = tmp_path / "project"
        project_agents = project_dir / ".apex" / "agents"
        project_agents.mkdir(parents=True)
        (project_agents / "project-agent.md").write_text("""\
---
description: From project
mode: primary
---
Project agent.
""")
        monkeypatch.setattr(pathlib.Path, "home", lambda: home_dir)
        monkeypatch.setattr(pathlib.Path, "cwd", lambda: project_dir)

        mgr = AgentManager()
        mgr.load_markdown_agents()
        assert mgr.get("home-agent") is not None
        assert mgr.get("project-agent") is not None

    def test_load_multiple_agents(self, monkeypatch, tmp_path):
        agents_dir = tmp_path / ".config" / "apex" / "agents"
        agents_dir.mkdir(parents=True)
        for i in range(3):
            (agents_dir / f"agent-{i}.md").write_text(f"""\
---
description: Agent {i}
mode: subagent
---
Prompt {i}.
""")
        monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
        monkeypatch.setattr(pathlib.Path, "cwd", lambda: tmp_path)

        mgr = AgentManager()
        mgr.load_markdown_agents()
        assert mgr.get("agent-0") is not None
        assert mgr.get("agent-1") is not None
        assert mgr.get("agent-2") is not None

    def test_skip_non_md_files(self, monkeypatch, tmp_path):
        agents_dir = tmp_path / ".config" / "apex" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "agent.md").write_text("""\
---
description: Valid
---
Valid.
""")
        (agents_dir / "notes.txt").write_text("not an agent")
        monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
        monkeypatch.setattr(pathlib.Path, "cwd", lambda: tmp_path)

        mgr = AgentManager()
        mgr.load_markdown_agents()
        assert mgr.get("agent") is not None
        assert mgr.get("notes") is None

    def test_missing_dir_does_nothing(self, monkeypatch, tmp_path):
        """When neither agents directory exists, no agents are loaded."""
        monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path / "home")
        monkeypatch.setattr(pathlib.Path, "cwd", lambda: tmp_path / "project")

        mgr = AgentManager()
        initial_count = len(mgr.agents)
        mgr.load_markdown_agents()
        assert len(mgr.agents) == initial_count

    def test_load_markdown_handles_exception(self, monkeypatch, tmp_path):
        """Invalid YAML triggers exception handler (covers lines 558-559)."""
        agents_dir = tmp_path / ".config" / "apex" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "bad-agent.md").write_text("""\
---
invalid: [unclosed yaml list
---
Body
""")
        monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
        monkeypatch.setattr(pathlib.Path, "cwd", lambda: tmp_path)

        mgr = AgentManager()
        mgr.load_markdown_agents()
        assert mgr.get("bad-agent") is None


# ---------------------------------------------------------------------------
# Loading custom agents — JSON
# ---------------------------------------------------------------------------


class TestAgentManagerLoadJsonAgents:
    """Test AgentManager.load_json_agents()."""

    def test_load_json_agent(self, monkeypatch):
        monkeypatch.setattr(apex_config, "_data", {"agent": {
            "my-agent": {
                "description": "JSON loaded agent",
                "mode": "primary",
                "system_prompt": "You are a JSON agent.",
                "permission": {"read": "allow"},
            }
        }})
        mgr = AgentManager()
        mgr.load_json_agents()
        agent = mgr.get("my-agent")
        assert agent is not None
        assert agent.description == "JSON loaded agent"
        assert agent.mode == "primary"
        assert agent.system_prompt == "You are a JSON agent."
        assert agent.permission == {"read": "allow"}

    def test_load_json_agent_skip_non_dict(self, monkeypatch):
        monkeypatch.setattr(apex_config, "_data", {"agent": {
            "my-agent": "not a dict",
        }})
        mgr = AgentManager()
        mgr.load_json_agents()
        assert mgr.get("my-agent") is None

    def test_load_json_agent_empty_config(self, monkeypatch):
        monkeypatch.setattr(apex_config, "_data", {"agent": {}})
        mgr = AgentManager()
        initial_count = len(mgr.agents)
        mgr.load_json_agents()
        assert len(mgr.agents) == initial_count

    def test_load_json_agent_all_fields(self, monkeypatch):
        monkeypatch.setattr(apex_config, "_data", {"agent": {
            "custom-agent": {
                "name": "custom-agent",
                "description": "Fully specified agent",
                "system_prompt": "You are custom.",
                "prompt": "Should be ignored if system_prompt set",
                "mode": "primary",
                "model": "gpt-4o",
                "temperature": 0.7,
                "top_p": 0.9,
                "max_steps": 10,
                "hidden": True,
                "disabled": False,
                "color": "#ff0000",
                "permission": {"read": "allow", "edit": "deny"},
            }
        }})
        mgr = AgentManager()
        mgr.load_json_agents()
        agent = mgr.get("custom-agent")
        assert agent is not None
        assert agent.name == "custom-agent"
        assert agent.model == "gpt-4o"
        assert agent.temperature == 0.7
        assert agent.top_p == 0.9
        assert agent.max_steps == 10
        assert agent.hidden is True
        assert agent.disabled is False
        assert agent.color == "#ff0000"
        assert agent.permission == {"read": "allow", "edit": "deny"}
        assert agent.system_prompt == "You are custom."

    def test_load_json_agent_uses_prompt_fallback(self, monkeypatch):
        monkeypatch.setattr(apex_config, "_data", {"agent": {
            "fallback-agent": {
                "description": "Uses prompt key",
                "prompt": "Fallback prompt.",
            }
        }})
        mgr = AgentManager()
        mgr.load_json_agents()
        agent = mgr.get("fallback-agent")
        assert agent is not None
        assert agent.system_prompt == "Fallback prompt."


# ---------------------------------------------------------------------------
# Loading custom agents — combined
# ---------------------------------------------------------------------------


class TestAgentManagerLoadAllCustom:
    """Test AgentManager.load_all_custom()."""

    def test_load_all_custom(self, monkeypatch, tmp_path):
        home_dir = tmp_path / "home"
        agents_dir = home_dir / ".config" / "apex" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "md-agent.md").write_text("""\
---
description: From markdown
mode: subagent
---
From markdown.
""")
        monkeypatch.setattr(pathlib.Path, "home", lambda: home_dir)
        monkeypatch.setattr(pathlib.Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(apex_config, "_data", {"agent": {
            "json-agent": {
                "description": "From JSON",
                "mode": "primary",
                "system_prompt": "From JSON.",
            }
        }})

        mgr = AgentManager()
        mgr.load_all_custom()
        assert mgr.get("md-agent") is not None
        assert mgr.get("json-agent") is not None

    def test_load_all_custom_when_no_sources(self, monkeypatch, tmp_path):
        monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path / "home")
        monkeypatch.setattr(pathlib.Path, "cwd", lambda: tmp_path / "project")
        monkeypatch.setattr(apex_config, "_data", {"agent": {}})

        mgr = AgentManager()
        initial_count = len(mgr.agents)
        mgr.load_all_custom()
        assert len(mgr.agents) == initial_count


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

    def test_subagent_mention_resolution(self):
        for name in ("reviewer", "general", "explore", "scout"):
            agent = agent_manager.get_by_mention(name)
            assert agent is not None, f"{name} should be resolvable by mention"

    def test_hidden_agents_not_visible(self):
        visible = agent_manager.list_visible()
        visible_names = {a.name for a in visible}
        assert "compaction" not in visible_names
        assert "title" not in visible_names
        assert "summary" not in visible_names

    def test_primary_agents_list(self):
        primary = agent_manager.list_primary()
        names = {a.name for a in primary}
        assert names == {"coder", "architect", "planner", "shell"}

    def test_subagents_list(self):
        subagents = agent_manager.list_subagents()
        subagent_names = {a.name for a in subagents}
        assert "reviewer" in subagent_names
        assert "general" in subagent_names
        assert "explore" in subagent_names
        assert "scout" in subagent_names

    def test_bash_permission_check(self):
        perm = agent_manager.check_permission("shell", "bash")
        assert perm == PERMISSION_ASK

    def test_architect_edit_denied(self):
        allowed, msg = agent_manager.can_execute_tool("architect", "write_file")
        assert allowed is False

    def test_explore_edit_denied(self):
        allowed, msg = agent_manager.can_execute_tool("explore", "write_file")
        assert allowed is False

    def test_scout_edit_denied(self):
        allowed, msg = agent_manager.can_execute_tool("scout", "write_file")
        assert allowed is False

    def test_general_full_access(self):
        allowed, msg = agent_manager.can_execute_tool("general", "write_file")
        assert allowed is True

    def test_coder_full_access(self):
        allowed, msg = agent_manager.can_execute_tool("coder", "edit_file")
        assert allowed is True

    def test_shell_edit_requires_ask(self):
        allowed, msg = agent_manager.can_execute_tool("shell", "write_file")
        assert allowed is False
        assert "confirmation" in msg

    def test_planner_edit_denied(self):
        allowed, msg = agent_manager.can_execute_tool("planner", "write_file")
        assert allowed is False
        assert "denied" in msg
