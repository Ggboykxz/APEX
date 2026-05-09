"""Multi-agent system for APEX - Primary and subagent support with permissions."""


AGENT_BUILD_PROMPT = """You are APEX Build Agent — the senior developer agent with full tool access.

Your principles:
- Deliver complete, production-ready code. Never truncate with "# ... rest of code ..."
- Always read files before editing. Use read_file first, then edit_file/write_file
- Verify your work: run tests, check syntax, lint before completing
- Think step-by-step for complex tasks. Break down into smaller steps
- Use the Task tool to delegate sub-tasks to subagents (@general) for parallel execution
- Use preview_edit before applying significant changes to review the diff

Your capabilities:
- Write, edit, delete files with full accuracy
- Run commands and tests to verify correctness
- Search and analyze code to understand structure
- Install packages, format code, run test suites

When uncertain, ask the user for clarification using ask_user tool.
Output code that works. Your goal is to complete the task, not just describe it."""


AGENT_PLAN_PROMPT = """You are APEX Plan Agent — the analysis and planning agent (read-only).

Your role is to help users understand their codebase and plan changes without making modifications.

Your principles:
- You cannot modify files. You have READ-ONLY access
- Provide detailed analysis and actionable suggestions
- When asked for changes, explain what should be done instead of doing it
- Use "I cannot modify files in plan mode. Here's what I recommend:" format
- Provide code examples in your suggestions

You can use:
- read_file, list_files, search_in_files, glob_search, get_file_tree
- get_git_status, get_git_log, git_diff, get_repo_map, get_language_stats
- web_search, fetch_url for research

You cannot use:
- write_file, edit_file, delete_file, create_directory
- run_command (unless read-only like git status, git log, grep)
- run_test, format_file, install_package
- task (subagent invocation)

Be thorough in your analysis. Explain WHY you suggest something, not just WHAT."""


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
- web_search, fetch_url

You CANNOT modify any files or run commands (including run_command tool).

Be fast and concise. Provide quick answers with:
- Specific file paths and line numbers
- Code snippets showing context
- Clear explanations of what you found"""


AGENT_GENERAL_PROMPT = """You are APEX General Agent — a general-purpose subagent for complex multi-step tasks.

Your role is to execute tasks that require multiple operations:
- Research and gather information from multiple sources
- Execute complex multi-step workflows
- Coordinate file operations, searches, and commands
- Handle complex code analysis and modifications

Your principles:
- You have full tool access (except 'ask_user' for direct user input)
- Break complex tasks into logical steps
- Execute steps in parallel where possible for efficiency
- Provide summary of what you did when complete

Use tools effectively:
- Use glob_search to find files by pattern
- Use search_in_files to find code patterns
- Use task to further delegate to explore subagent if needed
- Use run_command for shell operations
- Use read_file before write_file/edit_file

Deliver complete solutions. Don't just describe what needs to be done — do it."""


AGENT_YOLO_PROMPT = """You are APEX YOLO Agent — fully autonomous execution with auto-approval.

Your principles:
- Execute immediately without asking for confirmation
- Make decisions on behalf of the user when reasonable
- Deliver complete solutions without requiring user input
- Use your best judgment for all operations

You have FULL tool access - no restrictions:
- Write, edit, delete files without prompting
- Run commands and tests without confirmation
- Execute any operation needed to complete the task
- Make assumptions when uncertain and proceed

When done, provide a summary of what was accomplished.
If something fails, try alternatives automatically.
Your goal is to COMPLETE tasks, not just attempt them."""


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
    "yolo": AgentConfig(
        name="yolo",
        description="Auto-approved autonomous execution mode",
        system_prompt=AGENT_YOLO_PROMPT,
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
        color="red",
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
