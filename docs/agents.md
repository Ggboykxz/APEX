# Agents

APEX includes a powerful multi-agent system. Each agent is specialized for a different type of task, with distinct permission levels that control what tools they can use.

## Primary Agents

Primary agents handle your main conversation. Switch between them using `Tab` key or `/agent` command.

### Coder Agent (Default)

```
Agent: coder
Mode: primary
Permissions: All tools allowed (asks before destructive actions)
```

The default agent with full tool access for development work:
- Write, edit, delete files
- Run commands and tests
- Search and analyze code
- Install packages, format code

```bash
apex /agent coder
# or press Tab
```

### Architect Agent

```
Agent: architect
Mode: primary
Permissions: Read-only (denies edit, bash)
```

A restricted agent for planning and analysis:
- Analyze code structure
- Suggest improvements
- Create implementation plans
- Cannot modify files or run commands

```bash
apex /agent architect
```

### Reviewer Agent

```
Agent: reviewer
Mode: primary
Permissions: Read-only, never modifies files
```

A code review specialist:
- Review code for bugs and security issues
- Suggest improvements and best practices
- Analyze code quality and patterns
- Cannot modify any files

```bash
apex /agent reviewer
```

### Shell Agent

```
Agent: shell
Mode: primary
Permissions: System operations (asks before system changes)
```

An agent specialized for infrastructure and deployment:
- Manage Docker containers and images
- Configure CI/CD pipelines
- Handle cloud deployments
- System administration tasks

```bash
apex /agent shell
```

### Planner Agent

```
Agent: planner
Mode: primary
Permissions: Read-only with output generation
```

An agent for data analysis and reporting:
- Analyze data files and logs
- Generate reports and summaries
- Extract insights from codebases
- Produce documentation

```bash
apex /agent planner
```

## Switching Agents

### Using Commands

```bash
/agent coder      # Switch to coder
/agent architect  # Switch to architect
/agent reviewer   # Switch to reviewer
/agent shell      # Switch to shell
/agent planner    # Switch to planner
/agents           # List all agents
```

### Using Tab Key

Press `Tab` in the REPL to cycle through agents.

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

### Code Review with Architect Agent

```bash
apex /agent architect
# Now ask questions about code without making changes
What does this function do?
How can we improve the error handling?
```

### Code Review with Reviewer Agent

```bash
apex /agent reviewer
# Get a thorough code review
Review the authentication module for security issues
```

### Infrastructure with Shell Agent

```bash
apex /agent shell
# Set up deployment
Create a Docker Compose file for this project
```

## Best Practices

1. **Use Architect agent** for understanding code before making changes
2. **Use Reviewer agent** for thorough code reviews
3. **Use Coder agent** for active development and file modifications
4. **Use Shell agent** for infrastructure and deployment tasks
5. **Use Planner agent** for data analysis and documentation
6. **Switch agents mid-session** as your needs change
7. **Remember permissions** — Architect and Reviewer agents cannot modify files
