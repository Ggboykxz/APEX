"""APEX - The last coding agent you'll ever need."""

__version__ = "0.1.0"
__author__ = "APEX Team"

from .config import MODELS, MODEL_PROVIDERS, Config, SYSTEM_PROMPT
from .agent import Agent
from .tools import ToolExecutor, AsyncToolExecutor, TOOL_SCHEMAS
from .ui import UI
from .session import SessionManager
from .memory import Memory
from .context import get_repo_map
from .agents import agent_manager, AgentConfig, BUILTIN_AGENTS

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
]