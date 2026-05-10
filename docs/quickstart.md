# Quick Start Guide

Get up and running with APEX in 5 minutes.

## Step 1: Installation

### Option A: pip (recommended)

```bash
pip install apex-ai
```

### Option B: pipx (isolated environment)

```bash
pipx install apex-ai
```

### Option C: From source

```bash
git clone https://github.com/Ggboykxz/APEX.git
cd APEX
pip install -e .
```

## Step 2: Configure API Keys

Create `~/.apex/.env` with your API keys:

```bash
# At least one of these:
ANTHROPIC_API_KEY=sk-ant-...    # For Claude models
OPENAI_API_KEY=sk-...          # For GPT models
DEEPSEEK_API_KEY=...           # For DeepSeek models
GEMINI_API_KEY=...             # For Gemini models
GROQ_API_KEY=gsk_...            # For Groq models
```

> **Tip:** Start with a free model like `deepseek-chat` or `gpt-4o-mini`

## Step 3: First Launch

```bash
apex
```

You should see the banner:

```
╔═══════════════════════════════════════════════════════╗
║   APEX — Agent for Programming EXecution             ║
║   The last coding agent you'll ever need             ║
╚═══════════════════════════════════════════════════════╝

Agent: coder  Model: gpt-4o-mini  CWD: /home/user
›
```

## Step 4: Try Your First Command

### Ask a simple question

```
› What is the current directory?
```

### Read a file

```
› Read the file main.py
```

### Create a file

```
› Create a hello.py file that prints "Hello World"
```

## Basic Workflow

### 1. Switch models mid-session

```
› /model gpt-4o
```

### 2. Check git status

```
› /git
```

### 3. Analyze project

```
› /map
```

### 4. Save your session

```
› /save my-project
```

### 5. Load a previous session

```
› /load my-project
```

## Common Commands

| Command | What it does |
|---------|--------------|
| `/help` | Show all commands |
| `/models` | List available models |
| `/agent coder` | Switch to coder agent |
| `/agent architect` | Switch to architect (read-only) agent |
| `@filename` | Include file in context |
| `/clear` | Clear conversation history |
| `/exit` | Exit APEX |

## Next Steps

- Read [Commands Guide](commands.md) — Learn all available commands
- Read [Configuration](configuration.md) — Customize your setup
- Read [Models](models.md) — See all supported models
- Read [Tools](tools.md) — Learn about built-in tools

## Troubleshooting

### "No API key found"

Make sure you have at least one API key in `~/.apex/.env`

### "Model not found"

Use `/models` to see available models, or check [Models](models.md)

### "Permission denied"

Check file permissions or run with appropriate access rights

---

*Happy coding! 🚀*