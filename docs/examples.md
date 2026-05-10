# Configuration Examples

Complete configuration examples for different use cases.

## Basic Configuration

Minimal setup to get started:

```yaml
# ~/.apex/config.yaml

# Model settings
model: claude-4-sonnet
temperature: 0.3

# Tool settings
max_tool_rounds: 20

# Working directory
cwd: ~/projects/myapp
```

## Multi-Provider Setup

Use different models for different tasks:

```yaml
# ~/.apex/config.yaml

# Default model
model: claude-4-sonnet

# Model aliases for quick switching
model_aliases:
  fast: gpt-4o-mini
  cheap: gpt-4o-mini
  best: claude-4-opus
  reasoning: deepseek-r1

# Tool settings
max_tool_rounds: 25

# Environment-specific API keys
env:
  ANTHROPIC_API_KEY: "sk-ant-..."
  OPENAI_API_KEY: "sk-..."
  GEMINI_API_KEY: "..."
  GROQ_API_KEY: "gsk_..."

# Log settings
log_level: info
log_file: ~/.apex/logs/apex.log
```

## MCP Servers

Connect to external services via MCP:

```yaml
# ~/.apex/config.yaml

model: claude-4-sonnet

mcp_servers:
  # File system access
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"]
    enabled: true

  # GitHub integration
  github:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: "${GITHUB_TOKEN}"
    enabled: true

  # Custom MCP server
  myserver:
    command: python
    args: ["/path/to/server.py"]
    env:
      API_KEY: "${MY_API_KEY}"
    enabled: false
```

## Custom Tools

Define your own commands:

```yaml
# ~/.apex/config.yaml

model: claude-4-sonnet

custom_tools:
  # Simple command
  lint:
    description: Run ESLint on the project
    command: "npm run lint"
    cwd: ~/projects/webapp

  # Command with parameter
  test:
    description: Run tests
    command: "npm test -- --testPathPattern={pattern}"
    cwd: ~/projects/webapp
    parameters:
      type: object
      properties:
        pattern:
          type: string
          description: Test file pattern

  # Deploy command
  deploy:
    description: Deploy to environment
    command: "./scripts/deploy.sh {env}"
    cwd: ~/projects/webapp
    parameters:
      type: object
      properties:
        env:
          type: string
          enum: [staging, production]
          description: Target environment
      required: [env]

  # Docker commands
  docker_up:
    description: Start docker containers
    command: "docker-compose up -d"
    cwd: ~/projects/webapp

  docker_logs:
    description: View docker logs
    command: "docker-compose logs -f {service}"
    cwd: ~/projects/webapp
    parameters:
      type: object
      properties:
        service:
          type: string
          description: Service name
```

## Plugin Configuration

Enable and configure plugins:

```yaml
# ~/.apex/config.yaml

model: claude-4-sonnet

# Custom plugin directories
plugin_dirs:
  - ~/.apex/plugins
  - ~/my-plugins

# Plugin settings
plugins:
  # Built-in logger
  logger:
    enabled: true
    log_file: ~/.apex/logs/tools.log
    log_level: debug

  # Built-in security scanner
  security_scanner:
    enabled: true
    # Rules to check
    checks:
      - shell_injection
      - hardcoded_secrets
      - dangerous_functions

  # Custom plugin
  myplugin:
    enabled: true
    setting1: value1
    setting2: value2
```

## Agent Configuration

Customize agent behavior:

```yaml
# ~/.apex/config.yaml

model: claude-4-sonnet

agents:
  # Customize build agent
  build:
    temperature: 0.3
    max_steps: 50
    system_prompt: "You are an expert developer..."

  # Plan agent already restricted by default
  plan:
    temperature: 0.1

  # Custom agent
  reviewer:
    description: Code review agent
    mode: subagent
    permission:
      read: allow
      edit: deny
      bash: deny
      websearch: ask
    temperature: 0.2
```

## Context Management

Configure context behavior:

```yaml
# ~/.apex/config.yaml

model: claude-4-sonnet

# Context settings
context:
  max_tokens: 100000
  compress_threshold: 0.75
  summary_messages: 30

# Auto-save settings
auto_save:
  enabled: true
  interval: 60  # seconds
  session_dir: ~/.apex/sessions

# Session settings
session:
  max_sessions: 10
  auto_cleanup: true
```

## Full Configuration

Complete example with all options:

```yaml
# ~/.apex/config.yaml

# ============ MODEL SETTINGS ============
model: claude-4-sonnet
temperature: 0.3
max_tokens: 4096

# Model aliases
model_aliases:
  fast: gpt-4o-mini
  cheap: qwen2.5-coder
  strong: claude-4-opus

# ============ TOOL SETTINGS ============
max_tool_rounds: 25
max_output_chars: 100000
tool_timeout: 30

# ============ WORKSPACE SETTINGS ============
cwd: ~/projects/myapp

# ============ GIT SETTINGS ============
git:
  auto_fetch: true
  fetch_interval: 300

# ============ MCP SETTINGS ============
mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "~/projects"]
    enabled: false

# ============ CUSTOM TOOLS ============
custom_tools:
  deploy:
    command: "./deploy.sh {env}"
    parameters:
      type: object
      properties:
        env:
          type: string
          enum: [staging, production]
    required: [env]

# ============ PLUGINS ============
plugin_dirs:
  - ~/.apex/plugins

plugins:
  logger:
    enabled: true
  security_scanner:
    enabled: true

# ============ AGENTS ============
agents:
  build:
    temperature: 0.3

# ============ CONTEXT ============
context:
  max_tokens: 100000
  compress_threshold: 0.8
  summary_messages: 50

# ============ SESSIONS ============
auto_save:
  enabled: true
  interval: 120
  session_dir: ~/.apex/sessions

# ============ TELEMETRY ============
telemetry:
  enabled: true
  log_file: ~/.apex/logs/apex.log

# ============ COST TRACKING ============
cost_tracking:
  enabled: true
  track_models:
    - claude-4-sonnet
    - gpt-4o
    - gpt-4o-mini

# ============ LOGGING ============
log_level: info
```

## Environment Variables

Alternatively, use environment variables:

```bash
# ~/.bashrc or ~/.zshrc

# Required: At least one API key
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# Optional: Additional providers
export GEMINI_API_KEY="..."
export GROQ_API_KEY="gsk_..."
export DEEPSEEK_API_KEY="..."

# Optional: Configuration
export APEX_MODEL="gpt-4o"
export APEX_CWD="/home/user/projects"
export APEX_LOG_LEVEL="debug"
export APEX_MAX_ROUNDS="25"
```

## Per-Project Config

Override settings per project with local config:

```yaml
# ~/projects/myapp/.apex.yaml (in project root)

model: gpt-4o-mini  # Use cheaper model for this project
max_tool_rounds: 15

custom_tools:
  test:
    command: "make test"
```

APEX looks for `.apex.yaml` in current directory and walks up to find config.

## Multiple Profiles

Use profiles for different setups:

```bash
# Use default profile
apex "hello"

# Use specific profile (set APEX_PROFILE env var)
APEX_PROFILE=work apex "deploy to staging"
```

Configure in config.yaml:

```yaml
# ~/.apex/config.yaml

profiles:
  default:
    model: gpt-4o-mini

  work:
    model: claude-4-sonnet
    cwd: ~/work/projects

  personal:
    model: gpt-4o
    cwd: ~/personal
```

## Testing Different Models

Quickly test different models:

```bash
# Using model alias
apex /model fast "hello"
apex /model cheap "hello"
apex /model best "hello"

# Using full name
apex /model gpt-4o-mini "hello"
apex /model deepseek-r1 "hello"
apex /model qwen2.5-coder "hello"

# List available models
apex --list-models
```