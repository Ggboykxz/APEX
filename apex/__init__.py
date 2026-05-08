"""APEX - The last coding agent you'll ever need."""

__version__ = "0.4.0"
__author__ = "APEX Team"

from .config import MODELS, MODEL_PROVIDERS, Config, SYSTEM_PROMPT
from .agent import Agent
from .tools import ToolExecutor, AsyncToolExecutor, TOOL_SCHEMAS
from .ui import UI
from .session import SessionManager
from .memory import Memory
from .context import get_repo_map
from .agents import agent_manager, AgentConfig, BUILTIN_AGENTS
from .mcp import MCPManager, MCPClient, MCP_SERVER, mcp_manager, load_mcp_config
from .context_manager import ContextWindow, ConversationManager, AutoSaveManager
from .sandbox import CodeSandbox, ShellSession, sandbox

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
    "MCP_SERVER",
    "mcp_manager",
    "load_mcp_config",
    "ContextWindow",
    "ConversationManager",
    "AutoSaveManager",
    "CodeSandbox",
    "ShellSession",
    "sandbox",
]