# Custom Agents

Define custom agents using markdown files or JSON configuration.

## Markdown Agents

Create markdown files in:
- Global: `~/.config/apex/agents/`
- Project: `.apex/agents/`

### Format

```markdown
---
description: Reviews code for quality and best practices
mode: subagent
model: anthropic/claude-sonnet-4-5
temperature: 0.1
color: "#22c55e"
permission:
  edit: deny
  bash:
    "*": ask
    "git diff *": allow
    "git log*": allow
    "grep *": allow
  webfetch: deny
---
You are a code review agent. Focus on:
- Security vulnerabilities
- Code quality issues
- Performance bottlenecks
- Best practice violations

Provide specific, actionable feedback with line numbers.
```

## JSON Agents

Define agents in `apex.json`:

```json
{
  "agent": {
    "docs-writer": {
      "description": "Writes and maintains project documentation",
      "mode": "subagent",
      "model": "anthropic/claude-haiku-4-5",
      "permission": {
        "bash": "deny",
        "edit": "deny"
      }
    },
    "debug": {
      "description": "Debug agent focused on investigation",
      "mode": "primary",
      "permission": {
        "read": "allow",
        "bash": "allow",
        "edit": "ask"
      }
    }
  }
}
```

## Agent Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `description` | string | — | **Required.** Brief description |
| `mode` | string | `"primary"` | `"primary"`, `"subagent"`, or `"all"` |
| `model` | string | global model | Override model for this agent |
| `temperature` | float | 0.0 | Response creativity (0.0-1.0) |
| `top_p` | float | — | Nucleus sampling |
| `steps` | int | — | Max tool iterations |
| `permission` | dict | — | Tool permissions |
| `color` | string | — | Hex color or theme name |
| `hidden` | bool | false | Hide from UI |
| `disabled` | bool | false | Disable agent |

## Creating Agents via CLI

```bash
apex agent create
```

Interactive wizard that asks for:
1. Name
2. Description
3. Mode (primary/subagent)
4. Model
5. Permissions (select which to allow)
6. Generates markdown file automatically

## Using Agents

```bash
# Primary agents
Tab               # Cycle
/agent debug      # Switch by name

# Subagents
@docs-writer write documentation for the API module
@debug investigate the memory leak
```
