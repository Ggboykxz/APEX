# Configuration

## Config File

APEX stores configuration in `~/.apex/config.json`:

```json
{
  "model": "claude-sonnet",
  "cwd": "/home/user/projects",
  "theme": "monokai",
  "max_tool_rounds": 20,
  "auto_commit": false
}
```

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `model` | `claude-sonnet` | Default model alias |
| `cwd` | current directory | Working directory |
| `theme` | `monokai` | Syntax highlighting theme |
| `max_tool_rounds` | 20 | Max tool calls per message |
| `auto_commit` | false | Auto git commit after changes |

## CLI Options

```bash
apex tui                    # Launch TUI (subcommand)
apex --tui                  # Same thing (flag)
apex --model gpt-4o          # Use specific model
apex --cwd /path/to/project  # Set working directory
apex --stream                # Enable streaming
apex --auto-commit           # Auto commit changes
apex models                  # List available models
apex install-tui             # One-time TUI setup
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic/Claude API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `GROQ_API_KEY` | Groq API key |
| `MISTRAL_API_KEY` | Mistral API key |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `COHERE_API_KEY` | Cohere API key |

No API key needed for Ollama (local models).