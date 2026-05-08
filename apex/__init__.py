"""APEX - The last coding agent you'll ever need."""

__version__ = "0.6.0"
__author__ = "APEX Team"

from .config import MODELS, MODEL_PROVIDERS, Config, SYSTEM_PROMPT
from .agent import Agent
from .tools import ToolExecutor, AsyncToolExecutor, TOOL_SCHEMAS
from .ui import UI
from .session import SessionManager
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
]