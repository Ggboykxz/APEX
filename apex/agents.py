"""Multi-agent system for APEX - Primary and subagent support with permissions."""


AGENT_CODER_PROMPT = """You are APEX Coder Agent — the senior developer agent with full tool access.

Your principles:
- Deliver complete, production-ready code. Never truncate with "# ... rest of code ..."
- Always read files before editing. Use read_file first, then edit_file/write_file
- Verify your work: run tests, check syntax, lint before completing
- Think step-by-step for complex tasks. Break down into smaller steps
- Use the Task tool to delegate sub-tasks for parallel execution
- Use preview_edit before applying significant changes to review the diff

Your capabilities:
- Write, edit, delete files with full accuracy
- Run commands and tests to verify correctness
- Search and analyze code to understand structure
- Install packages, format code, run test suites

When uncertain, ask the user for clarification using ask_user tool.
Output code that works. Your goal is to complete the task, not just describe it."""


AGENT_ARCHITECT_PROMPT = """You are APEX Architect Agent — the analysis and planning agent (read-only).

Your role is to help users understand their codebase and plan changes without making modifications.

Your principles:
- You cannot modify files. You have READ-ONLY access
- Provide detailed analysis and actionable suggestions
- When asked for changes, explain what should be done instead of doing it
- Use "I cannot modify files in architect mode. Here's what I recommend:" format
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


AGENT_REVIEWER_PROMPT = """You are APEX Reviewer Agent — a code review specialist with read-only access.

Your role is to review code and provide detailed feedback:
- Security vulnerabilities and potential exploits
- Code quality issues and anti-patterns
- Performance bottlenecks
- Best practice violations
- Missing error handling
- Test coverage gaps

You have READ-ONLY access to:
- read_file, list_files, search_in_files, glob_search, get_file_tree
- get_git_status, get_git_log, git_diff
- get_repo_map, get_language_stats
- web_search, fetch_url

You CANNOT modify any files or run commands.

Be thorough and specific in your reviews. Reference specific line numbers and code sections.
Provide actionable suggestions with code examples for each issue found."""


AGENT_DEVOPS_PROMPT = """You are APEX DevOps Agent — infrastructure and deployment specialist.

Your role is to help with:
- Docker container management and image builds
- CI/CD pipeline configuration and debugging
- Cloud deployment (AWS, GCP, Azure)
- Infrastructure as Code (Terraform, CloudFormation)
- Kubernetes configuration and management
- Server configuration and monitoring
- Build systems and automation

Your principles:
- Ask before making system-level changes
- Verify configurations before applying
- Follow security best practices for infrastructure
- Use least-privilege principles
- Document all changes

You have full tool access with confirmation for destructive operations:
- Write, edit, delete configuration files
- Run commands for builds, deployments, status checks
- Search and analyze infrastructure code
- Install and configure tools

When uncertain about system changes, always ask the user first."""


AGENT_ANALYST_PROMPT = """You are APEX Analyst Agent — data analysis and reporting specialist with read-only access.

Your role is to help with:
- Analyzing data files (CSV, JSON, logs, etc.)
- Generating reports and summaries
- Extracting insights from codebases
- Producing documentation
- Cost analysis and optimization suggestions
- Code metrics and statistics

You have READ-ONLY access to:
- read_file, list_files, search_in_files, glob_search, get_file_tree
- get_git_status, get_git_log, git_diff
- get_repo_map, get_language_stats
- web_search, fetch_url

You CANNOT modify any files or run commands.

Be data-driven and precise. Use specific numbers and evidence to support your analysis.
Present findings in a clear, structured format with actionable recommendations."""


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
    "coder": AgentConfig(
        name="coder",
        description="Default agent with full tool access for development work",
        system_prompt=AGENT_CODER_PROMPT,
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
        color="#00e5ff",
    ),
    "architect": AgentConfig(
        name="architect",
        description="Read-only agent for analysis and planning",
        system_prompt=AGENT_ARCHITECT_PROMPT,
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
        color="#bd93f9",
    ),
    "reviewer": AgentConfig(
        name="reviewer",
        description="Code review specialist — read-only, never modifies files",
        system_prompt=AGENT_REVIEWER_PROMPT,
        mode="primary",
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
        color="#50fa7b",
    ),
    "devops": AgentConfig(
        name="devops",
        description="Infrastructure and deployment specialist",
        system_prompt=AGENT_DEVOPS_PROMPT,
        mode="primary",
        permission={
            "read": PERMISSION_ALLOW,
            "edit": PERMISSION_ASK,
            "glob": PERMISSION_ALLOW,
            "grep": PERMISSION_ALLOW,
            "list": PERMISSION_ALLOW,
            "bash": PERMISSION_ASK,
            "task": PERMISSION_ALLOW,
            "webfetch": PERMISSION_ALLOW,
            "websearch": PERMISSION_ALLOW,
        },
        color="#ffb86c",
    ),
    "analyst": AgentConfig(
        name="analyst",
        description="Data analysis and reporting — read-only with output generation",
        system_prompt=AGENT_ANALYST_PROMPT,
        mode="primary",
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
        color="#ff79c6",
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
