# Commands

APEX provides multiple ways to interact: **CLI subcommands**, **slash commands**, **keyboard shortcuts**, and **@mentions**.

## CLI Subcommands (v1.3.0+)

APEX supports convenient subcommands as positional arguments:

| Subcommand | Equivalent Flag | Description |
|---|---|---|
| `apex tui` | `apex --tui` | Launch the Terminal User Interface |
| `apex ui` | `apex --ui` | Same as `apex tui` |
| `apex models` | `apex --list-models` | List all available LLM models |
| `apex install-tui` | `apex --install-tui` | Install TUI dependencies (Bun + tui-frontend) |

## Slash Commands

### Agent Commands

| Command | Description |
|---------|-------------|
| `/agent [name]` | Switch to a different agent (coder/architect/planner/reviewer/shell) |
| `/agents` | List all available agents |
| `/subagents` | List all subagents |
| `/coder` | Switch to Coder mode (full tool access) |
| `/architect` | Switch to Architect mode (read-only) |

### Model Commands

| Command | Description |
|---------|-------------|
| `/model <alias>` | Switch to a different model |
| `/models` | List all available models |
| `/reasoning` | Cycle reasoning effort (off → high → max) |

### Navigation Commands

| Command | Description |
|---------|-------------|
| `/cwd <path>` | Change current working directory |
| `/map` | Show repository map |
| `/stats` | Show language statistics |

### Session Commands

| Command | Description |
|---------|-------------|
| `/save [name]` | Save current session |
| `/load <name]` | Load a previous session |
| `/sessions` | List saved sessions |
| `/clear` | Clear conversation history |
| `/history` | Show conversation history |

### Git Commands

| Command | Description |
|---------|-------------|
| `/git` | Show git status |
| `/undo` | Undo last AI action (Git-powered) |
| `/redo` | Redo previously undone action |
| `/restore [snapshot]` | Restore a workspace snapshot |
| `/revert [n]` | Revert n turns |

### Analysis Commands

| Command | Description |
|---------|-------------|
| `/map` | Show repository map |
| `/stats` | Show language statistics |

### Memory Commands

Store persistent facts across sessions:

```bash
# Add a fact
/memory add "Project uses FastAPI" python,fastapi
/memory add "Database is PostgreSQL" database,postgres

# Search memory
/memory search python
/memory search database

# View all facts
/memory

# Clear memory
/memory clear
```

### Utility Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help message |
| `/exit` | Exit APEX |
| `/skills` | List available skills |
| `/github [cmd]` | GitHub integration (issues, prs) |
| `/local [enable/disable]` | Toggle local execution |

## @Mentions

### File Mentions

Reference files for context:

```
@README.md          # Read and include file content
@src/main.py        # Include specific file
@*.json             # Include all JSON files
```

### Agent Mentions

Invoke subagents for specific tasks:

```
@reviewer "Review this code for bugs"
@shell "Deploy to staging"
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Tab` | Cycle through agents |
| `Ctrl+K` | Model selector overlay |
| `Ctrl+L` | Clear messages + reset metrics |
| `Ctrl+O` | Toggle sidebar |
| `Ctrl+T` | Toggle tools panel |
| `Ctrl+C` | Cancel current operation |
| `?` | Help panel |
| `Escape` | Close overlay |

## Examples

### Switching Models

```bash
apex> /model gpt-4o
apex> /model claude-sonnet-4
apex> /model deepseek-chat
```

### Working with Sessions

```bash
apex> /save my-project
apex> /load my-project
```

### Project Analysis

```bash
apex> /map
apex> /stats
apex> /git
```

### Using @Mentions

```bash
apex> @src/auth.py explain how authentication works
apex> @reviewer "Review the payment module"
```

## Custom Commands

Create custom commands in `.apex/commands/` or `~/.apex/commands/`:

```markdown
# .apex/commands/test.md
## Description: Run tests

## Prompt
Run the test suite for this project. Use appropriate test framework.
Report the results including:
- Total tests run
- Passed/Failed counts
- Any errors or warnings
```

---

*Use `/help` in APEX to see the most current command list.*
