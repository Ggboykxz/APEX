# Agents

APEX includes **11 specialized agents** organized by type. Each agent has distinct permission levels, a dedicated system prompt, and a unique color in the TUI.

## Agent Types

### Primary Agents
Handle your main conversation. Switch between them using `Tab` key or `/agent` command.

| Agent | Color | Mode | Permissions |
|-------|-------|------|-------------|
| **Coder** | Cyan `#00e5ff` | primary | All tools allowed |
| **Architect** | Purple `#a855f7` | primary | Read-only (edit denied) |
| **Planner** | Yellow `#eab308` | primary | Read-only (edit denied) |
| **Shell** | Orange `#f97316` | primary | Ask before edits |

### Subagents
Invoke via `@mention` in your messages for specialized tasks.

| Agent | Mode | Description |
|-------|------|-------------|
| **@reviewer** | subagent | Code review & audit specialist (read-only) |
| **@general** | subagent | General-purpose multi-task assistant (full access) |
| **@explore** | subagent | Fast read-only codebase exploration |
| **@scout** | subagent | External docs & dependency research |

### System Agents (Hidden)
Run automatically — not user-selectable.

| Agent | Role |
|-------|------|
| **@compaction** | Context window compression when approaching token limits |
| **@title** | Session title generation |
| **@summary** | Session summary generation |

## Default Agent (Coder)

```bash
Agent: coder
Mode: primary
Permissions: All tools allowed
Temperature: 0.0
Max steps: 50
```

Full-access agent for development:
- Write, edit, delete files
- Run commands and tests
- Search and analyze code
- Install packages, format code
- Invoke subagents via Task tool

## Agent Switching

### TUI
```bash
Tab              # Cycle forward through primary agents
Shift+Tab        # Cycle backward
Ctrl+X A         # Agent list overlay
@reviewer        # Invoke subagent by name
```

### CLI
```bash
apex --agent architect       # Start with architect
apex --agent plan            # Start with planner
```

### Slash Commands
```bash
/agent             # Show current agent + list all agents
/agent coder       # Switch to coder
/agent architect   # Switch to architect
/agents            # Table of all agents
/subagents         # List subagents (@mention)
/coder             # Quick switch to coder
/architect         # Quick switch to architect
```

## Custom Agents

Define custom agents via markdown files in `~/.config/apex/agents/` or `.apex/agents/`:

```markdown
---
description: Reviews code for quality and best practices
mode: subagent
model: anthropic/claude-sonnet-4-5
temperature: 0.1
permission:
  edit: deny
  bash:
    "*": ask
    "git diff *": allow
    "grep *": allow
  webfetch: deny
---
You are a code review agent. Focus on security, performance, and maintainability.
```

Or via JSON config:

```json
{
  "agent": {
    "code-reviewer": {
      "description": "Reviews code for best practices",
      "mode": "subagent",
      "permission": { "edit": "deny" }
    }
  }
}
```

### Agent Config Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `description` | string | — | **Required.** What the agent does |
| `mode` | string | `"primary"` | `"primary"`, `"subagent"`, or `"all"` |
| `model` | string | global model | Override model for this agent |
| `temperature` | float | 0.0 | Response randomness (0.0-1.0) |
| `top_p` | float | — | Alternative to temperature |
| `steps` | int | — | Max tool iterations before forced text |
| `permission` | dict | — | Tool permissions (see below) |
| `color` | string | — | Hex color or theme color name |
| `hidden` | bool | false | Hide from UI |
| `disabled` | bool | false | Disable the agent |

### Permissions

Each permission key can be set to `"allow"`, `"ask"`, or `"deny"`:

```json
{
  "permission": {
    "read": "allow",
    "edit": "deny",
    "glob": "allow",
    "grep": "allow",
    "list": "allow",
    "bash": "allow",
    "task": "allow",
    "webfetch": "allow",
    "websearch": "allow",
    "lsp": "allow",
    "skill": "allow"
  }
}
```

Bash commands support glob patterns:

```json
{
  "permission": {
    "bash": {
      "*": "ask",
      "git status *": "allow",
      "grep *": "allow",
      "npm test *": "allow"
    }
  }
}
```
