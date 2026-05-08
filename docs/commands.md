# Commands

## Slash Commands

| Command | Description |
|---------|-------------|
| `/model <alias>` | Switch to a different model |
| `/models` | List all available models |
| `/cwd <path>` | Change current working directory |
| `/clear` | Clear conversation history |
| `/history` | Show conversation history |
| `/cost` | Show token usage and estimated cost |
| `/save [name]` | Save current session |
| `/load <name>` | Load a previous session |
| `/sessions` | List saved sessions |
| `/memory [add\|clear\|search]` | Manage persistent memory |
| `/map` | Show repository map |
| `/stats` | Show language statistics |
| `/git` | Show git status |
| `/help` | Show help message |
| `/exit`, `/quit` | Exit APEX |

## Memory Commands

```bash
/memory add "Project uses FastAPI" python,fastapi
/memory search python
/memory clear
```

## Examples

```bash
apex> /model gpt-4o
apex> /cwd /home/user/myproject
apex> /save my-session
apex> /load my-session
apex> /map
```