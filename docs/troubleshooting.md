# Troubleshooting

Common issues and solutions for APEX.

## Installation Issues

### "command not found: apex"

```bash
# npm channel: add the global npm bin directory to PATH, then
npm install -g apex-ai

# native channel: installs apex-rs, not apex
bash install.sh --method native
~/.apex/bin/apex-rs --version

# Override the resolved binary explicitly
export APEX_BINARY=/path/to/apex
```

### Import errors

```bash
# The Python CLI/TUI is a source-only development surface:
# pip, pipx and uv are no longer installation channels.
git clone https://github.com/Ggboykxz/APEX.git
cd APEX
pip install -e ".[dev]"
```

## API Key Issues

### "Authentication failed"

Check your API key is correct:

```bash
# Test with echo
echo $ANTHROPIC_API_KEY

# Or set explicitly
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Rate limit exceeded"

```bash
# Switch to a faster model
/model gpt-4o-mini

# Or wait and retry
```

### Wrong API key for model

Each provider needs its own key:

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
OPENAI_API_KEY=sk-...

# Google
GEMINI_API_KEY=...

# Groq
GROQ_API_KEY=gsk_...
```

## Model Issues

### Model not found

```bash
# List available models (subcommand)
apex models

# Or use flag
apex --list-models

# Use exact model name
apex --model gpt-4o "hello"
```

### Model doesn't support tools

Some models don't support function calling:

```
Switch to a tool-capable model:
/model gpt-4o
```

## Tool Execution Issues

### "File not found"

Paths are relative to current working directory:

```bash
# Check current directory
/cwd

# Change directory
/cwd /path/to/project
```

### "Permission denied"

Check file permissions:

```bash
ls -la filename
chmod 644 filename
```

### Command timeout

Increase timeout in config:

```json
{
  "max_tool_rounds": 30
}
```

## Agent Issues

### "Unknown agent"

Available agents: coder, architect, planner, reviewer, shell

```bash
/agents
/agent coder
```

### Permission denied errors

Some tools are blocked for certain agents:

- Architect agent: Cannot use write_file, edit_file, run_command
- Planner agent: Read-only, cannot modify any files
- Reviewer agent: Subagent mode, cannot modify any files

Switch to coder agent for full access: `/coder`

## TUI Issues

### "TUI frontend not found"

The TUI frontend ships in the repository and needs its dependencies installed from a source checkout:

```bash
# One-time TUI setup (installs Bun + downloads tui-frontend)
apex install-tui

# Or use the flag
apex --install-tui

# Then launch the TUI
apex tui
```

### "Bun not found"

The TUI requires the Bun runtime. Install it:

```bash
curl -fsSL https://bun.sh/install | bash

# Then launch TUI
apex tui
```

### TUI doesn't start from a source checkout

The Python CLI/TUI is not distributed through a package index:

```bash
# 1. Clone the repository
git clone https://github.com/Ggboykxz/APEX.git
cd APEX

# 2. Install the dev dependencies
pip install -e ".[dev]"

# 3. Launch the TUI
apex tui
```
```

For dev/git users, the TUI works directly: `apex tui` (auto-installs deps on first run).

## Performance Issues

### Slow responses

- Use smaller models: `/model gpt-4o-mini`
- Use streaming: `apex --stream "prompt"`
- Reduce history: `/clear`

### Memory issues

Clear conversation history:

```bash
/clear
```

### Token limit reached

APEX handles context automatically, but you can manually compress:

```python
from apex.context_manager import ContextWindow

cw = ContextWindow(max_tokens=50000)
messages = cw.compress_messages(agent.history)
```

## Session Issues

### Lost session

Sessions auto-save to `~/.apex/sessions/`:

```bash
# List saved sessions
ls ~/.apex/sessions/

# Load session
/load session_name
```

### Crash recovery

APEX auto-saves to `~/.apex/autosave/`:

```python
from apex.context_manager import AutoSaveManager

asm = AutoSaveManager()
state = asm.load_state()
if state:
    # Restore session
    agent.history = state.get("history", [])
```

## MCP Issues

### MCP server not connecting

Check server is running:

```python
mcp_manager.list_servers()
```

Verify config:

```yaml
mcp_servers:
  myserver:
    command: node
    args: ["server.js"]
    enabled: true
```

## Git Issues

### "Not a git repository"

Initialize git:

```bash
cd your/project
git init
git add .
git commit -m "Initial commit"
```

### Git permission errors

Check git status:

```bash
/git
```

### Undo AI changes

```bash
# Undo last AI action
/undo

# Undo last 3 actions
/undo 3

# Redo
/redo
```

## Getting Help

### Debug mode

Run with verbose output:

```bash
apex --verbose "your prompt"
```

### Check logs

```bash
# View session logs
ls ~/.apex/logs/
```

### Report issues

Include:
- APEX version: `apex --version`
- Python version: `python --version`
- Error message
- Steps to reproduce
