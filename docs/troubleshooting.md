# Troubleshooting

Common issues and solutions for APEX.

## Installation Issues

### "command not found: apex" after pip install

```bash
# Check if installed
pip show apex-ai

# Reinstall
pip uninstall apex-ai
pip install apex-ai

# Or use python module
python -m apex.main --version
```

### Import errors

```bash
# Ensure Python 3.11+
python --version

# Upgrade pip
pip install --upgrade pip

# Reinstall dependencies
pip install -r requirements.txt
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

```python
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
# List available models
apex --list-models

# Use exact model name
apex --model gpt-4o "hello"
```

### Model doesn't support tools

Some models (like o1) don't support function calling:

```
Switch to a tool-capable model:
/model gpt-4o
```

## Tool Execution Issues

### "File not found"

Paths are relative to current working directory:

```bash
# Check current directory
pwd

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

Available agents: coder, architect, reviewer, devops, analyst

```bash
/agents
/agent coder
```

### Permission denied errors

Some tools are blocked for certain agents:

- Architect agent: Cannot use write_file, edit_file, run_command
- Reviewer agent: Cannot modify any files

Switch to coder agent for full access.

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

```bash
# List configured servers
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

# Session summary
apex /cost
```

### Report issues

Include:
- APEX version: `apex --version`
- Python version: `python --version`
- Error message
- Steps to reproduce