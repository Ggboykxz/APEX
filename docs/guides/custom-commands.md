# Custom Commands

Define custom slash commands for repetitive tasks using markdown files.

## Creating Commands

Create markdown files in:
- Global: `~/.config/apex/commands/`
- Project: `.apex/commands/`

### Format

```markdown
---
description: Run tests with coverage
agent: build
model: anthropic/claude-sonnet-4-5
subtask: false
---
Run the full test suite with coverage report and show any failures.
Focus on the failing tests and suggest fixes.
```

The filename (without `.md`) becomes the command name. `test.md` → `/test`

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `description` | string | — | Shown in command palette |
| `agent` | string | current | Agent to execute with |
| `model` | string | global | Model override |
| `subtask` | bool | false | Force subagent invocation |

### Template Variables

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments joined |
| `$1`, `$2`, `$3` | Positional arguments |
| `!command` | Inline shell execution |
| `@file` | Include file content |

### Examples

```markdown
---
description: Create a new React component
---
Create a new React component named $ARGUMENTS with TypeScript support.
Include proper typing and basic structure.
```

Usage: `/component Button`

```markdown
---
description: Review recent changes
---
Recent git commits:
!`git log --oneline -10`
Review these changes and suggest any improvements.
```

### Built-in Commands

These are available by default and can be overridden:

| Command | Description |
|---------|-------------|
| `/test` | Run tests with coverage |
| `/review` | Review current changes |
| `/commit` | Commit with AI message |
| `/docs` | Generate documentation |
