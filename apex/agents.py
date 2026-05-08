"""Multi-agent system for APEX - Primary and subagent support with permissions."""

from typing import Any
from .config import SYSTEM_PROMPT, MODELS

AGENT_BUILD_PROMPT = """You are APEX Build Agent - the default development agent with full tool access.

Your role is to execute development tasks:
- Write, edit, and delete files
- Run commands and tests
- Search and analyze code
- Create and modify codebases

You have full access to all tools. Use them freely to complete tasks.
Always verify your work by running tests or checking syntax.
Output complete code - never truncate.

Remember: You are a senior, opinionated developer. Deliver production-ready code."""


AGENT_PLAN_PROMPT = """You are APEX Plan Agent - a read-only agent for analysis and planning.

Your role is to:
- Analyze code and explain structure
- Suggest improvements and refactoring
- Create implementation plans
- Review code without making changes

You have READ-ONLY access. You can:
- read_file, list_files, search_in_files, glob_search, get_file_tree
- get_git_status, get_git_log, git_diff
- web_search, fetch_url, get_repo_map

You CANNOT:
- write_file, edit_file, delete_file, create_directory
- run_command (except read-only like git, grep)
- run_test, format_file, install_package

When the user asks for changes, provide detailed plans and suggestions instead of making changes.
Use "I cannot modify files in plan mode. Here's my suggested approach:" for any modification requests."""


AGENT_EXPLORE_PROMPT = """You are APEX Explore Agent - a fast, read-only agent for exploring codebases.

Your role is to quickly find and analyze:
- Files by name pattern
- Code by keyword search
- Directory structure
- Git history and status
- Repository overview

You have READ-ONLY access to:
- read_file, list_files, search_in_files, glob_search, get_file_tree
- get_git_status, get_git_log, git_diff
- get_repo_map, get_language_stats

You CANNOT modify any files or run commands.

Be fast and concise. Provide quick answers with specific file paths and line numbers."""


AGENT_GENERAL_PROMPT = """You are APEX General Agent - a general-purpose subagent for complex multi-step tasks.

Your role is to:
- Research complex questions
- Execute multi-step tasks that require multiple tool calls
- Coordinate between different operations
- Handle complex searches and analysis

You have full tool access (except todo). Make file changes and run commands as needed.
Break complex tasks into steps and execute them efficiently.

Remember: Output complete solutions, never truncate."""


PERMISSION_ALLOW = "allow"
PERMISSION_ASK = "ask"
PERMISSION_DENY = "deny"


class AgentConfig:
    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        mode: str = "primary",
        model: str | None = None,
        temperature: float = 0.0,
        max_steps: int | None = None,
        permission: dict[str, str] | None = None,
        color: str = "cyan",
    ):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.mode = mode
        self.model = model
        self.temperature = temperature
        self.max_steps = max_steps
        self.permission = permission or {}
        self.color = color


BUILTIN_AGENTS: dict[str, AgentConfig] = {
    "build": AgentConfig(
        name="build",
        description="Default agent with full tool access for development work",
        system_prompt=AGENT_BUILD_PROMPT,
        mode="primary",
        permission={
            "read": PERMISSION_ALLOW,
            "edit": PERMISSION_ALLOW,
            "glob": PERMISSION_ALLOW,
            "grep": PERMISSION_ALLOW,
            "list": PERMISSION_ALLOW,
            "bash": PERMISSION_ALLOW,
            "task": PERMISSION_ALLOW,
            "webfetch": PERMISSION_ALLOW,
            "websearch": PERMISSION_ALLOW,
        },
        color="cyan",
    ),
    "plan": AgentConfig(
        name="plan",
        description="Read-only agent for analysis and planning",
        system_prompt=AGENT_PLAN_PROMPT,
        mode="primary",
        permission={
            "read": PERMISSION_ALLOW,
            "edit": PERMISSION_DENY,
            "glob": PERMISSION_ALLOW,
            "grep": PERMISSION_ALLOW,
            "list": PERMISSION_ALLOW,
            "bash": PERMISSION_DENY,
            "task": PERMISSION_ALLOW,
            "webfetch": PERMISSION_ALLOW,
            "websearch": PERMISSION_ALLOW,
        },
        color="yellow",
    ),
    "explore": AgentConfig(
        name="explore",
        description="Fast read-only agent for exploring codebases",
        system_prompt=AGENT_EXPLORE_PROMPT,
        mode="subagent",
        permission={
            "read": PERMISSION_ALLOW,
            "edit": PERMISSION_DENY,
            "glob": PERMISSION_ALLOW,
            "grep": PERMISSION_ALLOW,
            "list": PERMISSION_ALLOW,
            "bash": PERMISSION_DENY,
            "task": PERMISSION_DENY,
            "webfetch": PERMISSION_ALLOW,
            "websearch": PERMISSION_ALLOW,
        },
        color="green",
    ),
    "general": AgentConfig(
        name="general",
        description="General-purpose subagent for complex multi-step tasks",
        system_prompt=AGENT_GENERAL_PROMPT,
        mode="subagent",
        permission={
            "read": PERMISSION_ALLOW,
            "edit": PERMISSION_ALLOW,
            "glob": PERMISSION_ALLOW,
            "grep": PERMISSION_ALLOW,
            "list": PERMISSION_ALLOW,
            "bash": PERMISSION_ALLOW,
            "task": PERMISSION_ALLOW,
            "webfetch": PERMISSION_ALLOW,
            "websearch": PERMISSION_ALLOW,
        },
        color="magenta",
    ),
}


class AgentManager:
    def __init__(self):
        self.agents = BUILTIN_AGENTS.copy()
        self._custom_agents: dict[str, AgentConfig] = {}

    def register(self, config: AgentConfig) -> None:
        self.agents[config.name] = config

    def get(self, name: str) -> AgentConfig | None:
        return self.agents.get(name)

    def list_agents(self, mode: str | None = None) -> list[AgentConfig]:
        if mode:
            return [a for a in self.agents.values() if a.mode == mode or a.mode == "all"]
        return list(self.agents.values())

    def check_permission(self, agent_name: str, tool_category: str) -> str:
        agent = self.get(agent_name)
        if not agent:
            return PERMISSION_DENY
        return agent.permission.get(tool_category, PERMISSION_DENY)

    def can_execute_tool(self, agent_name: str, tool_name: str) -> tuple[bool, str]:
        tool_category = self._get_tool_category(tool_name)
        permission = self.check_permission(agent_name, tool_category)

        if permission == PERMISSION_ALLOW:
            return True, ""
        elif permission == PERMISSION_DENY:
            return False, f"Tool '{tool_name}' is denied for agent '{agent_name}'"
        else:
            return False, f"Tool '{tool_name}' requires confirmation for agent '{agent_name}'"

    def _get_tool_category(self, tool_name: str) -> str:
        read_tools = {"read_file", "list_files", "search_in_files", "glob_search",
                      "get_file_tree", "get_git_status", "get_git_log", "git_diff",
                      "get_repo_map", "get_language_stats", "fetch_url", "read_image"}
        edit_tools = {"write_file", "edit_file", "delete_file", "create_directory",
                      "run_test", "format_file", "install_package"}
        bash_tools = {"run_command"}
        task_tools = {"task"}
        web_tools = {"web_search", "fetch_url"}

        if tool_name in read_tools:
            return "read"
        elif tool_name in edit_tools:
            return "edit"
        elif tool_name in bash_tools:
            return "bash"
        elif tool_name == "task":
            return "task"
        elif tool_name in web_tools:
            return "websearch"
        return "read"


agent_manager = AgentManager()