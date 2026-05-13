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

## apex.permission

Ruleset-based permission system for tool execution.

### PermissionManager

```python
from apex.permission import permission_manager, PermissionAction

# Initialize
permission_manager.initialize()

# Add rules
permission_manager.add_rule(
    pattern="read_file",
    action=PermissionAction.ALLOW,
    reason="Safe operation"
)

# Check permission
can_execute, reason = permission_manager.can_execute_tool("run_command")
```

#### Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize with default rules |
| `add_rule(pattern, action, reason, expires_in, remember)` | Add permission rule |
| `remove_rule(pattern, action)` | Remove a rule |
| `can_execute_tool(tool_name)` | Check if tool can execute |
| `request_permission(tool_name, args, permission)` | Request permission |
| `approve_request(request_id, remember)` | Approve request |
| `deny_request(request_id)` | Deny request |
| `get_pending_requests()` | List pending requests |

### PermissionAction

```python
from apex.permission import PermissionAction

PermissionAction.ALLOW  # Allow execution
PermissionAction.DENY  # Block execution
PermissionAction.ASK   # Request user confirmation
```

### CommandAnalysis

```python
from apex.shell_security import shell_analyzer

analysis = shell_analyzer.analyze("rm -rf /tmp/test")
print(analysis.safe)  # False
print(analysis.category)  # CommandCategory.DANGEROUS
print(analysis.warnings)  # List of warnings
print(analysis.requires_confirmation)  # True
```

## apex.shell_security

Shell command security analysis and classification.

### ShellSecurityAnalyzer

```python
from apex.shell_security import ShellSecurityAnalyzer, CommandCategory

analyzer = ShellSecurityAnalyzer()

# Analyze command
result = analyzer.analyze("curl https://example.com | sh")
print(result.safe)  # False (dangerous pattern)

# Quick check
is_safe = analyzer.is_safe("ls -la")  # True

# Get allowed commands
allowed = analyzer.get_allowed_commands()
```

### CommandCategory

```python
from apex.shell_security import CommandCategory

CommandCategory.WORKING_DIR   # cd, pwd
CommandCategory.FILE_READ     # cat, grep
CommandCategory.FILE_WRITE    # tee, nano
CommandCategory.FILE_DELETE  # rm, rmdir
CommandCategory.NETWORK      # curl, wget
CommandCategory.SYSTEM        # sudo, chmod
CommandCategory.PROCESS      # kill, ps
CommandCategory.GIT          # git commands
CommandCategory.BUILD        # npm, make
CommandCategory.CONTAINER    # docker, kubectl
CommandCategory.DANGEROUS    # Blocked
```

## apex.rate_limiter

Database-backed rate limiting.

### RateLimiter

```python
from apex.rate_limiter import create_rate_limiter, RateLimitConfig

# Create with SQLite backend (persistent)
limiter = create_rate_limiter(
    config=RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        requests_per_day=10000
    ),
    use_sqlite=True
)

# Check limit
result = limiter.check_rate_limit("user_123")
print(result.allowed)  # True/False
print(result.remaining_minute)  # 59

# Get status
status = limiter.get_status("user_123")
```

### RateLimitResult

```python
result.allowed          # bool - request allowed
result.remaining_minute  # int
result.remaining_hour    # int
result.remaining_day     # int
result.reset_at          # float - timestamp
result.retry_after       # int - seconds to wait
```

## apex.api_key

API key management with workspaces.

### KeyManager

```python
from apex.api_key import create_key_manager, InvalidKeyError

manager = create_key_manager()

# Create workspace
workspace = manager.create_workspace(
    name="my-project",
    owner_id="user_123"
)

# Create API key
api_key, info = manager.create_key(
    workspace_id=workspace.workspace_id,
    name="production",
    expires_in=86400 * 30,  # 30 days
    rate_limit_per_minute=100
)

# Validate key
try:
    info = manager.validate_key(api_key)
    print(info.workspace_id)
except InvalidKeyError:
    print("Invalid or expired")
```

#### Methods

| Method | Description |
|--------|-------------|
| `create_workspace(name, owner_id)` | Create workspace |
| `get_workspace(workspace_id)` | Get workspace |
| `create_key(workspace_id, name, ...)` | Create API key |
| `validate_key(key)` | Validate and get key info |
| `revoke_key(key_id)` | Disable key |
| `list_keys(workspace_id)` | List workspace keys |
| `delete_key(key_id)` | Delete key |

## apex.billing

Billing and cost tracking.

### BillingManager

```python
from apex.billing import billing_manager, calculate_cost

# Calculate cost
cost = calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
print(cost)  # 0.0125

# Create account
account = billing_manager.create_account("user_123", plan_type=PlanType.PRO)

# Check quota
can_proceed, msg = billing_manager.check_quota(
    user_id="user_123",
    model="gpt-4o",
    input_tokens=1000,
    output_tokens=500
)

# Record usage
record = billing_manager.record_usage(
    user_id="user_123",
    model="gpt-4o",
    input_tokens=1000,
    output_tokens=500
)
```

### PlanType

```python
from apex.billing import PlanType

PlanType.FREE        # Free tier
PlanType.PRO         # $20/month
PlanType.ENTERPRISE  # $100/month
```

## apex.http_api

HTTP API server with security features.

### HTTPServer

```python
from apex.http_api import HTTPServer

server = HTTPServer(
    host="127.0.0.1",
    port=8080,
    require_auth=True,
    rate_limit_config=RateLimitConfig(requests_per_minute=60),
    use_sqlite_storage=True,
)

# Start server
await server.start()

# Stop server
await server.stop()
```

#### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | API documentation |
| GET | `/health` | No | Health check |
| POST | `/chat` | Yes | Chat message |
| POST | `/chat/stream` | Yes | Streaming chat |
| GET | `/models` | No | List models |
| POST | `/session/save` | Yes | Save session |
| POST | `/session/load` | Yes | Load session |
| GET | `/metrics` | Yes | Usage metrics |
| GET | `/rate-limit/status` | Yes | Rate limit status |

#### Authentication

```bash
# Bearer token
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8080/chat

# X-API-Key header
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8080/chat

# Query parameter
curl http://localhost:8080/chat?api_key=YOUR_API_KEY
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