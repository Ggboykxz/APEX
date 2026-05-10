# Configuration

APEX is highly configurable through multiple layers: a global `config.json` file, environment variables via `.env`, and command-line flags. Configuration precedence follows the order CLI flags > environment variables > config file > defaults, giving you flexibility to override any setting at the level you need.

## config.json

The primary configuration file lives at `~/.config/apex/config.json` (or `%APPDATA%\apex\config.json` on Windows). This JSON file controls model defaults, agent behavior, tool permissions, and UI preferences. A minimal config looks like:

```json
{
  "default_model": "gpt-4o",
  "theme": "dark",
  "agents": {
    "auto_approve": false,
    "max_turns": 50
  },
  "tools": {
    "shell": { "enabled": true, "timeout": 120 },
    "git": { "enabled": true, "auto_commit": false }
  }
}
```

You can generate a starter config by running `apex config init`, which creates the file with sensible defaults. Every key in the config file is optional — APEX will fall back to built-in defaults for any missing entry.

## Environment Variables (.env)

APEX reads a `.env` file from the current working directory and from `~/.config/apex/.env`. This is the recommended place to store API keys and other secrets so they never end up in version control. Supported variables include all major provider keys:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...
OLLAMA_HOST=http://localhost:11434
```

Environment variables can also be exported in your shell profile for global availability across all APEX sessions.

## Model Selection

With support for 100+ models, APEX lets you pick your preferred model at several levels. Set `default_model` in `config.json` for a persistent default, override it per session with `apex --model claude-sonnet-4-20250514`, or switch models on the fly inside the TUI using `Ctrl+K`. Local models via Ollama are fully supported — simply set the model name to `ollama/<model-name>` and ensure the Ollama daemon is running. APEX automatically detects available Ollama models and includes them in the model selector.

## Agents

APEX ships with 5 specialized agents, each designed for different tasks:

| Agent | Purpose | Default Behavior |
|-------|---------|-----------------|
| **Coder** | Write and edit code | Asks before destructive actions |
| **Architect** | Read and analyze codebase | Read-only by default |
| **Reviewer** | Code review and suggestions | Read-only, never modifies files |
| **DevOps** | Infrastructure and deployment | Asks before system changes |
| **Analyst** | Data analysis and reports | Read-only with output generation |

Switch agents with `Tab` in the TUI or use `/agent coder`, `/agent architect`, etc.
