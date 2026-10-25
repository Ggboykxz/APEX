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

## `context`

Context-window budget for repository maps and tool output. Values are read from the nested `context` object after the normal config layers are merged (global → `$APEX_CONFIG` → project → `$APEX_CONFIG_CONTENT`, later wins). Missing keys use their defaults; a key with the wrong type is ignored and replaced by its default without discarding the other values.

| Key | Type | Default | Description |
|---|---|---|---|
| `max_repo_map_tokens` | `integer` | `2000` | Token budget for the symbol map injected into the system prompt. `0` disables injection. |
| `prune_tool_outputs` | `boolean` | `true` | Replace old, oversized tool results before each model request. |
| `tool_output_max_chars` | `integer` | `4000` | Maximum characters kept for a non-recent tool result. |
| `keep_recent_tool_results` | `integer` | `3` | Number of most recent tool results that are never pruned. |

```json
{
  "context": {
    "max_repo_map_tokens": 2000,
    "prune_tool_outputs": true,
    "tool_output_max_chars": 4000,
    "keep_recent_tool_results": 3
  }
}
```

Behavior:

- **Repository map.** On the first model request of a session, APEX renders a symbol-level map with `apex.repomap.build_repo_map` and appends it under `## Repository map`. The result is cached per repository root and budget, so later turns and agent switches do not rescan or duplicate the section. Empty repositories and `max_repo_map_tokens: 0` append nothing.
- **Tool output pruning.** Before each request, tool messages older than the last `keep_recent_tool_results` are replaced with `[tool output pruned: N chars, sha256:xxxxxxxx]` when they exceed `tool_output_max_chars`. System, user and assistant messages are never modified, and a second pass is a no-op.
- **Stats.** The last pass is available as `agent.last_context_stats` and `agent.get_context_stats()`, with `tokens_before`, `tokens_after`, `pruned_messages`, `pruned_chars` and `repo_map_tokens`.
