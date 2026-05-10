# Configuration File Reference

The APEX configuration file (`config.json`) controls every aspect of the application's behavior, from model selection to tool permissions to TUI appearance. This reference documents every available key, its type, default value, and effect.

## File Location

APEX looks for the configuration file in the following locations, in order of precedence:

1. Path specified by `--config` CLI flag
2. `./apex.config.json` in the current working directory
3. `~/.config/apex/config.json` (Linux/macOS) or `%APPDATA%\apex\config.json` (Windows)

If no config file is found, APEX uses built-in defaults for all settings.

## Top-Level Keys

| Key | Type | Default | Description |
|---|---|---|---|
| `default_model` | `string` | `"gpt-4o"` | The model used when no `--model` flag is provided |
| `theme` | `string` | `"dark"` | UI theme. Options: `"dark"`, `"light"` |
| `log_level` | `string` | `"warn"` | Logging verbosity: `"debug"`, `"info"`, `"warn"`, `"error"` |
| `history_size` | `integer` | `1000` | Maximum number of conversation turns retained per session |
| `context_window` | `integer` | `128000` | Target context window size in tokens for the agent |

## `agents`

Configuration for APEX's five built-in agents (Coder, Architect, Planner, Reviewer, Shell).

| Key | Type | Default | Description |
|---|---|---|---|
| `auto_approve` | `boolean` | `false` | Automatically approve tool executions without user confirmation |
| `max_turns` | `integer` | `50` | Maximum agent turns before requiring user intervention |
| `default_agent` | `string` | `"coder"` | The agent selected by default when the TUI launches |

## `tools`

Per-tool and per-category configuration. Each tool category can have `enabled` (boolean) and tool-specific options.

```json
{
  "tools": {
    "shell": {
      "enabled": true,
      "timeout": 120,
      "allowed_commands": ["git", "npm", "python", "cargo"]
    },
    "git": {
      "enabled": true,
      "auto_commit": false
    },
    "file": {
      "enabled": true,
      "max_file_size_mb": 10
    },
    "docker": {
      "enabled": true
    },
    "k8s": {
      "enabled": false
    },
    "web": {
      "enabled": true,
      "max_response_size_kb": 512
    }
  }
}
```

## `tui`

Terminal UI customization options.

| Key | Type | Default | Description |
|---|---|---|---|
| `bg_color` | `string` | `"#0d1117"` | Background color of the TUI |
| `accent_color` | `string` | `"#00e5ff"` | Primary accent color (cyan) for interactive elements |
| `success_color` | `string` | `"#00ff88"` | Success indicator color (green) |
| `sidebar_width` | `integer` | `30` | Width of the sidebar panel in characters |
| `show_tool_panel` | `boolean` | `true` | Display the tool execution panel by default |

## `providers`

API provider configuration, including base URLs and custom endpoints.

```json
{
  "providers": {
    "openai": {
      "api_key_env": "OPENAI_API_KEY",
      "base_url": "https://api.openai.com/v1"
    },
    "anthropic": {
      "api_key_env": "ANTHROPIC_API_KEY"
    },
    "ollama": {
      "base_url": "http://localhost:11434"
    },
    "custom": {
      "base_url": "https://my-inference-server.example.com/v1",
      "api_key_env": "CUSTOM_API_KEY"
    }
  }
}
```

## `mcp`

Model Context Protocol server connections for extending APEX's tool palette with external integrations.

```json
{
  "mcp": {
    "servers": {
      "my-server": {
        "command": "npx",
        "args": ["-y", "@my-org/mcp-server"],
        "env": {}
      }
    }
  }
}
```
