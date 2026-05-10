# Advanced Features

## MCP (Model Context Protocol)

Connect to external tools and services via MCP.

### Configuration

```yaml
# .apex/config.yaml
mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/files"]
    enabled: true

  github:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: your_token_here
    enabled: true
```

### Usage

MCP tools are automatically available to the agent:

```
Search the filesystem for config files @filesystem

Get GitHub issues @github
```

## LSP Integration

Connect to Language Server Protocol servers for code intelligence.

### Configuration

```yaml
# .apex/config.yaml
lsp_servers:
  python:
    command: ["pylsp"]
    enabled: true
  typescript:
    command: ["typescript-language-server", "--stdio"]
    enabled: true
  go:
    command: ["gopls"]
    enabled: true
  rust:
    command: ["rust-analyzer"]
    enabled: true
```

### Supported Operations

| Operation | Description |
|-----------|-------------|
| `lsp_definition` | Go to definition |
| `lsp_references` | Find all references |
| `lsp_hover` | Show hover information |
| `lsp_diagnostics` | Get diagnostic errors |

### Usage

```
Go to definition of this function
Show me references to this variable
What does this type mean?
Check for errors in this file
```

## Custom Commands

Define reusable prompt templates.

### Command File Format

Create `.apex/commands/<name>.md`:

```markdown
## Description: Analyze code for issues

## Prompt
Analyze the codebase for common issues:
1. Look for TODO comments
2. Check for console.log statements
3. Find potential security vulnerabilities
Focus on files in {directory} if specified.
```

### Usage

```bash
/list_commands
/run_command_custom name directory=src
```

### Built-in Commands

APEX comes with these custom commands:
- Use `/list_commands` to see available commands
- Use `/run_command_custom <name>` to execute

## Custom Tools

Define your own tools in config:

```yaml
# .apex/config.yaml
custom_tools:
  deploy:
    description: Deploy application to production
    enabled: true
    command: "kubectl apply -f {manifest}"
    cwd: /path/to/project

  run_tests:
    description: Run test suite
    enabled: true
    command: "npm test -- --reporter=json"
    cwd: /path/to/project
```

### Tool Parameters

```yaml
custom_tools:
  mytool:
    description: Custom tool
    parameters:
      type: object
      properties:
        arg1:
          type: string
          description: First argument
        arg2:
          type: integer
          description: Second argument
      required: [arg1]
```

## Undo/Redo System

APEX tracks all file changes for undo/redo capability.

### Usage

```python
from apex.session import UndoManager

undo_mgr = UndoManager()

# After each file operation
undo_mgr.snapshot("edit_file", {"path": "main.py", "old": "...", "new": "..."})

# Undo
action = undo_mgr.undo()

# Redo
action = undo_mgr.redo()

# Check availability
undo_mgr.can_undo()  # bool
undo_mgr.can_redo()  # bool
```

### Commands

- `/undo` — Undo last change
- `/redo` — Redo last undone change

## Session Sharing

Share sessions with others via link.

```python
from apex.session import SessionManager

# Share current session
share_link = session_manager.share(agent)

# Load shared session
session_manager.load_shared("abc12345", agent)
```

### Usage

```
/share  # Generate shareable link
```

Share links can be opened by others to continue the conversation.

## Workspace Awareness

APEX automatically detects project context:

### Git Context

- Current branch
- Remote URL
- Commit status (dirty/clean)
- Commits ahead/behind
- PR information (if available)

### Language Detection

Automatically detects:
- Python (pyproject.toml, requirements.txt)
- JavaScript (package.json)
- Go (go.mod)
- Rust (Cargo.toml)
- And more...

### Package Manager

Detects: pip, poetry, npm, yarn, pnpm, cargo, bundler

### Test Framework

Detects: pytest, jest, vitest, go test, cargo test

## Context Management

### Automatic Compression

APEX automatically compresses long conversations:

```python
from apex.context_manager import ContextWindow

# Custom thresholds
cw = ContextWindow(
    max_tokens=100000,      # Max context size
    compress_threshold=0.8,  # Compress at 80%
    summary_messages=50     # Summarize every 50 messages
)
```

### Manual Bookmarks

```python
# Bookmark current position
agent.execute("bookmark_session", {"name": "important_point"})

# Later, restore
agent.execute("restore_bookmark", {"name": "important_point"})
```

### Search History

```python
agent.execute("search_history", {"query": "function_name"})
```

## Sandbox Execution

Run code safely in isolated environment:

```python
from apex.sandbox import sandbox

# Python
result = sandbox.run_code("print('hello')", "python")

# JavaScript
result = sandbox.run_code("console.log('hello')", "javascript")

# Bash
result = sandbox.run_code("ls -la", "bash")
```

### Supported Languages

- Python
- JavaScript
- Bash
- Ruby
- Go
- Rust

### Timeouts

Default 30 seconds, configurable:

```python
sandbox = CodeSandbox(timeout=60)  # 60 seconds
```

## Telemetry

Track usage and performance:

```python
from apex.telemetry import logger, perf_monitor

# Automatically logs:
logger.log_agent_start(model, agent)
logger.log_tool_call(tool_name, args)
logger.log_tool_result(tool_name, result, duration_ms)

# Get stats
stats = logger.get_stats()
logger.print_summary()

# Performance monitoring
perf_monitor.record("tool_execution", duration_ms)
stats = perf_monitor.get_all_stats()
```

## Session Management

### Save/Load

```bash
/save my_session      # Save current session
/load my_session     # Load saved session
```

### Auto-save

APEX automatically saves session state:

```python
from apex.context_manager import AutoSaveManager

asm = AutoSaveManager()
asm.save_state({"history": agent.history})
state = asm.load_state()
```

## Advanced Configuration

### Complete Config Example

```yaml
# .apex/config.yaml

# Model settings
model: claude-4-sonnet
max_tool_rounds: 20

# Agent settings
agents:
  build:
    temperature: 0.3
    max_steps: 50

# MCP servers
mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"]
    enabled: false

# Custom tools
custom_tools:
  deploy:
    description: Deploy to production
    command: "./deploy.sh {env}"
    parameters:
      type: object
      properties:
        env:
          type: string
          description: Environment (prod/staging)
    required: [env]

# Plugins
plugin_dirs:
  - ~/.apex/plugins

plugins:
  logger:
    enabled: true
  security_scanner:
    enabled: true

# Context management
context:
  max_tokens: 100000
  compress_threshold: 0.8
  auto_save: true
```

### Environment Variables

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=...

# Settings
APEX_MODEL=gpt-4o
APEX_CWD=/home/user/project
APEX_LOG_LEVEL=debug
```

## Performance Optimization

### Model Selection

| Use Case | Recommended Model |
|----------|------------------|
| Code generation | gpt-4o, claude-4-opus |
| Fast editing | gpt-4o-mini, claude-3.5-haiku |
| Complex reasoning | o3, deepseek-r1 |
| Cost-effective | gpt-4o-mini, qwen2.5 |
| Local/offline | ollama-llama3 |

### Tool Optimization

1. Use `glob_search` instead of `list_files` for large directories
2. Use `search_in_files` with specific patterns
3. Batch similar operations
4. Use `@explore` for read-only tasks

### Context Optimization

- Use `/clear` periodically
- Use bookmarks for important points
- Use Plan agent for analysis to save tokens