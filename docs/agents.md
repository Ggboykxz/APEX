# Agents

APEX includes a powerful multi-agent system inspired by OpenCode. Agents are specialized AI assistants configured for specific tasks.

## Primary Agents

Primary agents handle your main conversation. Switch between them using `Tab` key or `/agent` command.

### Build Agent (Default)

```
Agent: build
Mode: primary
Permissions: All tools allowed
```

The default agent with full tool access for development work:
- Write, edit, delete files
- Run commands and tests
- Search and analyze code
- Install packages, format code

```bash
apex /agent build
# or press Tab
```

### Plan Agent

```
Agent: plan
Mode: primary
Permissions: Read-only (denies edit, bash)
```

A restricted agent for planning and analysis:
- Analyze code structure
- Suggest improvements
- Create implementation plans
- Cannot modify files or run commands

```bash
apex /agent plan
```

## Subagents

Subagents are specialized assistants invoked with `@mention`:

### Explore Agent

```
Agent: explore
Mode: subagent
Permissions: Read-only
```

Fast, read-only agent for exploring codebases:
- Find files by pattern
- Search code for keywords
- Show directory structure
- Analyze git history

```bash
apex @explore find all TODO comments
```

### General Agent

```
Agent: general
Mode: subagent
Permissions: Full (except ask_user)
```

General-purpose subagent for complex multi-step tasks:
- Research complex questions
- Execute multi-step workflows
- Coordinate file operations

```bash
apex @general research error handling patterns
```

## Switching Agents

### Using Commands

```bash
/agent build      # Switch to build
/agent plan      # Switch to plan
/agents          # List all agents
/subagents       # List subagents
```

### Using Tab Key

Press `Tab` in the REPL to cycle through primary agents.

### Using @Mention

Invoke subagents directly in your message:

```
Explain the architecture @explore

Search for authentication @general
```

## Custom Agents

Create custom agents in your config:

```yaml
# .apex/config.yaml
agents:
  reviewer:
    description: Code review agent
    mode: subagent
    permission:
      edit: deny
      bash: deny
    prompt: "You are a code reviewer focused on security..."
```

## Agent Permissions

Each agent has configurable permissions:

| Permission | Tools Controlled |
|-------------|------------------|
| `read` | read_file, list_files, search_in_files, glob_search |
| `edit` | write_file, edit_file, delete_file |
| `bash` | run_command |
| `websearch` | web_search, fetch_url |
| `task` | task (subagent invocation) |

Permission values:
- `allow` — Always permit
- `ask` — Prompt for confirmation
- `deny` — Block completely

## Example Workflows

### Code Review with Plan Agent

```bash
apex /agent plan
# Now ask questions about code without making changes
What does this function do?
How can we improve the error handling?
```

### Parallel Exploration with @explore

```bash
apex @explore find all API endpoints
apex @explore list all test files
```

### Complex Task with @general

```bash
apex @general refactor all error handling to use custom exceptions
```

## Best Practices

1. **Use Plan agent** for understanding code before making changes
2. **Use @explore** for quick file lookups and searches
3. **Use @general** for multi-step refactoring tasks
4. **Switch agents mid-session** as your needs change
5. **Remember permissions** — Plan agent cannot modify files