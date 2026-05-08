# API Reference

Core modules and their public APIs.

## apex.agent

Main agent implementation.

### Agent

```python
from apex.agent import Agent

agent = Agent(
    model="claude-4-sonnet",      # Model name
    cwd="/path/to/project",       # Working directory
    system_prompt=None,           # Custom system prompt
    max_rounds=20,                # Max tool call rounds
    temperature=0.3,             # Model temperature
)
```

#### Methods

| Method | Description |
|--------|-------------|
| `run(message)` | Run agent with user message |
| `run_stream(message)` | Run with streaming response |
| `execute(tool, args)` | Execute a specific tool |
| `add_tool(tool)` | Add custom tool |
| `clear_history()` | Clear conversation history |
| `save_session(name)` | Save session to disk |
| `load_session(name)` | Load session from disk |
| `set_agent(name)` | Switch to different agent |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `history` | List[Message] | Conversation history |
| `model` | str | Current model |
| `tools` | List[Tool] | Available tools |
| `agent_type` | str | Current agent type |

### AsyncAgent

```python
from apex.agent import AsyncAgent

agent = AsyncAgent(
    model="claude-4-sonnet",
    cwd="/path/to/project",
)

# Use async methods
await agent.run("hello")
```

## apex.config

Configuration management.

### Config

```python
from apex.config import Config

config = Config.load()  # Load from ~/.apex/config.yaml

# Access settings
config.model           # Default model
config.max_rounds      # Max tool rounds
config.get_model_info("gpt-4o")
```

#### Methods

| Method | Description |
|--------|-------------|
| `load(path=None)` | Load config from YAML file |
| `save(path=None)` | Save config to file |
| `get_model_info(name)` | Get model metadata |
| `get_mcp_servers()` | Get configured MCP servers |
| `get_custom_tools()` | Get custom tools |
| `get_plugins()` | Get plugin config |

## apex.tools

Tool implementations.

### ToolExecutor

```python
from apex.tools import ToolExecutor

executor = ToolExecutor(cwd="/project", max_output_chars=10000)

# Execute tool
result = executor.execute("read_file", {"path": "main.py"})
```

#### Methods

| Method | Description |
|--------|-------------|
| `execute(tool_name, args)` | Execute a tool by name |
| `register_tool(tool)` | Register custom tool |
| `list_tools()` | List all available tools |

### Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `read_file` | Read file contents | `path: str` |
| `write_file` | Write content to file | `path: str, content: str` |
| `edit_file` | Edit file | `path: str, old_string: str, new_string: str` |
| `delete_file` | Delete file | `path: str` |
| `list_files` | List directory | `path: str` |
| `glob_search` | Glob pattern search | `pattern: str` |
| `search_in_files` | Search in files | `pattern: str, path: str` |
| `run_command` | Run shell command | `command: str, timeout: int` |
| `web_search` | Web search | `query: str, num_results: int` |
| `fetch_url` | Fetch URL content | `url: str` |
| `git_status` | Git status | - |
| `git_diff` | Git diff | `file: str` |
| `git_log` | Git log | `n: int` |
| `git_branch` | Git branch info | - |
| `git_remote` | Git remote info | - |
| `git_pr` | GitHub PR info | - |
| `mcp_tool` | Call MCP server | `server: str, tool: str, args: dict` |
| `run_code` | Run code in sandbox | `code: str, language: str` |

### AsyncToolExecutor

```python
from apex.tools import AsyncToolExecutor

executor = AsyncToolExecutor(cwd="/project")

# Async execution
result = await executor.execute("read_file", {"path": "main.py"})

# Parallel execution
results = await executor.execute_all([
    ("read_file", {"path": "a.py"}),
    ("read_file", {"path": "b.py"}),
])
```

## apex.context_manager

Context window management.

### ContextWindow

```python
from apex.context_manager import ContextWindow

cw = ContextWindow(
    max_tokens=100000,
    compress_threshold=0.8,
    summary_messages=50,
)

# Compress history
compressed = cw.compress(messages)
```

#### Methods

| Method | Description |
|--------|-------------|
| `compress(messages)` | Compress messages |
| `estimate_tokens(text)` | Estimate token count |
| `summarize(messages)` | Summarize messages |

### AutoSaveManager

```python
from apex.context_manager import AutoSaveManager

asm = AutoSaveManager(session_dir="~/.apex/sessions")
asm.save_state(state)
state = asm.load_state()
asm.list_sessions()
asm.delete_session(name)
```

## apex.workspace

Workspace and git awareness.

### Workspace

```python
from apex.workspace import Workspace

ws = Workspace(cwd="/project")

# Git info
ws.is_git_repo          # bool
ws.current_branch       # str
ws.remote_url           # str | None
ws.is_dirty             # bool
ws.ahead                # int
ws.behind               # int

# Project detection
ws.language             # str | None
ws.package_manager      # str | None
ws.test_framework       # str | None

# Context string
context = ws.get_context_string()
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_git_repo` | bool | Is git repository |
| `current_branch` | str | Current branch name |
| `remote_url` | str | Remote URL |
| `is_dirty` | bool | Has uncommitted changes |
| `language` | str | Project language |
| `package_manager` | str | Package manager |
| `test_framework` | str | Test framework |

## apex.mcp

MCP client implementation.

### MCPClient

```python
from apex.mcp import MCPClient

client = MCPClient(
    name="myserver",
    command="npx",
    args=["-y", "server-package"],
    env={"KEY": "value"},
)

# Connect and use tools
await client.connect()
tools = await client.list_tools()
result = await client.call_tool("tool_name", args)
await client.close()
```

#### Methods

| Method | Description |
|--------|-------------|
| `connect()` | Connect to MCP server |
| `close()` | Close connection |
| `list_tools()` | List available tools |
| `call_tool(name, args)` | Call a tool |
| `ping()` | Health check |

### MCPManager

```python
from apex.mcp import MCPManager

manager = MCPManager(cwd="/project")
manager.load_config(config.get_mcp_servers())
await manager.connect_all()

# List all MCP tools
tools = manager.get_all_tools()

# Call tool
result = await manager.call_tool("server", "tool", args)

await manager.close_all()
```

## apex.plugins

Plugin system.

### PluginBase

```python
from apex.plugins import PluginBase, PluginInfo

class MyPlugin(PluginBase):
    info = PluginInfo(
        name="my-plugin",
        version="0.1.0",
        description="Description",
        author="Author",
        hooks=["tool_call", "agent_message"],
    )

    def initialize(self, app):
        pass

    def cleanup(self):
        pass
```

### PluginManager

```python
from apex.plugins import plugin_manager

# Set app reference
plugin_manager.set_app(app)

# Add plugin directory
plugin_manager.add_plugin_dir(Path("~/.apex/plugins"))

# Load plugins
plugin_manager.load_plugin("my-plugin")
plugin_manager.load_all()

# Get plugins
plugins = plugin_manager.list_plugins()
plugin = plugin_manager.get_plugin("name")

# Hooks
plugin_manager.register_hook("event", callback)
plugin_manager.unregister_hook("event", callback)
plugin_manager.emit_hook("event", *args)

# Get tools from plugins
tools = plugin_manager.get_tools()
```

### BuiltInPlugins

```python
from apex.plugins import BuiltInPlugins

# Create logger plugin
logger = BuiltInPlugins.create_logger_plugin()

# Create security scanner
scanner = BuiltInPlugins.create_security_scanner()
```

## apex.telemetry

Logging and performance monitoring.

### Logger

```python
from apex.telemetry import logger

# Start tracking
logger.log_agent_start(model, agent_type)
logger.log_model_request(model, prompt, response)
logger.log_tool_call(tool_name, args)
logger.log_tool_result(tool_name, result, duration_ms)

# Session stats
stats = logger.get_stats()
logger.print_summary()
logger.print_token_summary()
```

### PerformanceMonitor

```python
from apex.telemetry import perf_monitor

# Record metrics
perf_monitor.record("operation", duration_ms)
perf_monitor.record("tool", duration_ms, tool_name="read_file")

# Get stats
stats = perf_monitor.get_all_stats()
perf_monitor.get_stats("operation")
perf_monitor.get_stats_by_label("tool")

# Print
perf_monitor.print_stats()
```

## apex.ui

Terminal UI components.

### UIRenderer

```python
from apex.ui import UIRenderer

renderer = UIRenderer()

# Render markdown
renderer.render_markdown(text)

# Render code
renderer.render_code(code, language="python")

# Render panels
renderer.render_panel(content, title="Title")

# Render tables
renderer.render_table(data, headers)
```

### ToolCallFormatter

```python
from apex.ui import ToolCallFormatter

formatter = ToolCallFormatter()

# Format tool call
formatted = formatter.format_call(tool_name, args)
formatted = formatter.format_result(result)
```

## apex.utils

Utility functions.

### cost_tracker

```python
from apex.utils import cost_tracker

cost_tracker.add_tokens(model, input_tokens, output_tokens)
total = cost_tracker.get_total_cost()
report = cost_tracker.get_cost_report()
```

### format

```python
from apex.utils import format

format.truncate(text, max_length)
format.indent(text, spaces)
format.code_block(code, language)
```

### validators

```python
from apex.utils import validators

validators.validate_path(path)
validators.validate_command(command)
validators.validate_url(url)
validators.validate_model(model_name)
```