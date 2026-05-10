# Commands

APEX provides multiple ways to interact: **slash commands**, **keyboard shortcuts**, and **@mentions**.

## Slash Commands

### Agent Commands

| Command | Description |
|---------|-------------|
| `/agent [name]` | Switch to a different agent (build/plan/explore/general) |
| `/agents` | List all available agents |
| `/subagents` | List all subagents |

### Model Commands

| Command | Description |
|---------|-------------|
| `/model <alias>` | Switch to a different model |
| `/models` | List all available models |

### Navigation Commands

| Command | Description |
|---------|-------------|
| `/cwd <path>` | Change current working directory |
| `/cd <path>` | Alias for `/cwd` |

### Session Commands

| Command | Description |
|---------|-------------|
| `/save [name]` | Save current session |
| `/load <name]` | Load a previous session |
| `/sessions` | List saved sessions |
| `/share` | Generate share link for current session |

### Git Commands

| Command | Description |
|---------|-------------|
| `/git` | Show git status |
| `/branch` | Show current branch |
| `/branches` | List all branches |
| `/checkout <branch>` | Switch to branch |
| `/commit <message>` | Commit changes |

### Analysis Commands

| Command | Description |
|---------|-------------|
| `/map` | Show repository map |
| `/stats` | Show language statistics |
| `/analyze` | Analyze project structure |

### Utility Commands

| Command | Description |
|---------|-------------|
| `/clear` | Clear conversation history |
| `/history` | Show conversation history |
| `/cost` | Show token usage and estimated cost |
| `/help` | Show this help message |
| `/exit` | Exit APEX |

### Plan Approval Commands

| Command | Description |
|---------|-------------|
| `/approve` | Approve pending plan |
| `/reject [reason]` | Reject pending plan |

## Memory Commands

Store persistent facts across sessions:

```bash
# Add a fact
/memory add "Project uses FastAPI" python,fastapi
/memory add "Database is PostgreSQL" database,postgres

# Search memory
/memory search python
/memory search database

# Clear memory
/memory clear
```

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
@explore "Find all API endpoints"
@general "Search for authentication logic"
@build "Refactor this function"
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Tab` | Cycle through agents |
| `Ctrl+C` | Cancel current operation |
| `Ctrl+L` | Clear screen |
| `Ctrl+D` | Exit APEX |
| `Up/Down` | Navigate command history |

## Examples

### Switching Models

```bash
apex> /model gpt-4o
apex> /model claude-4-sonnet
apex> /model deepseek-chat
```

### Working with Sessions

```bash
apex> /save my-project
apex> /load my-project
apex> /share
```

### Project Analysis

```bash
apex> /map
apex> /stats
apex> /git
apex> /analyze
```

### Using @Mentions

```bash
apex> @src/auth.py explain how authentication works
apex> @explore "Find all database queries"
apex> @general "Search for TODO comments"
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