"""APEX - The last coding agent you'll ever need."""

__version__ = "1.3.0"
__author__ = "APEX Team"

from .config import MODELS, MODEL_PROVIDERS, Config, SYSTEM_PROMPT
from .agent import Agent
from .tools import ToolExecutor, AsyncToolExecutor, TOOL_SCHEMAS
from .ui import UI
from .session import SessionManager, UndoManager
from .memory import Memory
from .context import get_repo_map
from .agents import agent_manager, AgentConfig, BUILTIN_AGENTS
from .mcp import MCPManager, MCPClient, MCPServerConfig, mcp_manager, load_mcp_config
from .context_manager import ContextWindow, ConversationManager, AutoSaveManager
from .sandbox import CodeSandbox, ShellSession, sandbox
from .plugins import PluginManager, PluginBase, plugin_manager, load_plugins_from_config
from .telemetry import logger, perf_monitor, Logger, PerformanceMonitor
from .config_tools import custom_tool_manager, CustomToolManager, load_custom_tools
from .workspace import workspace_manager, WorkspaceManager, WorkspaceContext, GitContext
from .lsp import LSPManager, get_lsp_manager
from .commands import CommandManager, get_command_manager, PlanApproval
from .project import ProjectInitializer, FileWatcher, get_project_initializer
from .slash import SlashCommandManager, get_slash_command_manager
from .mentions import MentionParser, get_mention_parser, get_file_completer
from .skills import SkillManager, get_skill_manager, DiffTool, SearchReplace, CodeAnalyzer
from .advanced import RetryHandler, BatchOperation, StreamingOutput, ToolTimeout, ContextOptimizer, FileOperationCache, get_retry_handler, get_file_cache
from .extras import ShellExpander, EnvManager, TaskQueue, HistorySearch, WorkspaceValidator, SecurityAuditor, get_env_manager, get_task_queue, get_history_search
from .codegen import CodeRefactorer, DatabaseManager, DockerManager, APIClientGenerator, DocumentationGenerator, PerformanceProfiler

__all__ = [
    "MODELS",
    "MODEL_PROVIDERS",
    "Config",
    "SYSTEM_PROMPT",
    "Agent",
    "ToolExecutor",
    "AsyncToolExecutor",
    "TOOL_SCHEMAS",
    "UI",
    "SessionManager",
    "UndoManager",
    "Memory",
    "get_repo_map",
    "agent_manager",
    "AgentConfig",
    "BUILTIN_AGENTS",
    "MCPManager",
    "MCPClient",
    "MCPServerConfig",
    "mcp_manager",
    "load_mcp_config",
    "ContextWindow",
    "ConversationManager",
    "AutoSaveManager",
    "CodeSandbox",
    "ShellSession",
    "sandbox",
    "PluginManager",
    "PluginBase",
    "plugin_manager",
    "load_plugins_from_config",
    "logger",
    "perf_monitor",
    "Logger",
    "PerformanceMonitor",
    "custom_tool_manager",
    "CustomToolManager",
    "load_custom_tools",
    "workspace_manager",
    "WorkspaceManager",
    "WorkspaceContext",
    "GitContext",
    "LSPManager",
    "get_lsp_manager",
    "CommandManager",
    "get_command_manager",
    "PlanApproval",
    "ProjectInitializer",
    "FileWatcher",
    "get_project_initializer",
    "SlashCommandManager",
    "get_slash_command_manager",
    "MentionParser",
    "get_mention_parser",
    "get_file_completer",
    "SkillManager",
    "get_skill_manager",
    "DiffTool",
    "SearchReplace",
    "CodeAnalyzer",
    "RetryHandler",
    "BatchOperation",
    "StreamingOutput",
    "ToolTimeout",
    "ContextOptimizer",
    "FileOperationCache",
    "get_retry_handler",
    "get_file_cache",
    "ShellExpander",
    "EnvManager",
    "TaskQueue",
    "HistorySearch",
    "WorkspaceValidator",
    "SecurityAuditor",
    "get_env_manager",
    "get_task_queue",
    "get_history_search",
    "CodeRefactorer",
    "DatabaseManager",
    "DockerManager",
    "APIClientGenerator",
    "DocumentationGenerator",
    "PerformanceProfiler",
]