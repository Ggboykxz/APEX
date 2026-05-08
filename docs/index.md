# APEX — Agent for Programming EXecution

*Built in Gabon 🇬🇦 for the world.*

APEX is a production-grade, terminal-native AI coding agent that works with **any LLM** via a unified interface powered by litellm.

## Features

- **Multi-model support** — 20+ models including Claude, GPT-4, Gemini, Groq, Mistral, DeepSeek, Ollama, Cohere
- **Rich terminal UI** — Syntax highlighting, markdown rendering, panels
- **18+ tools** — File operations, git, web search, testing, formatting
- **Session persistence** — Save and load conversations
- **Token cost tracking** — Monitor usage and estimated costs
- **Streaming responses** — Real-time output with `--stream`
- **Memory system** — Persistent facts across sessions
- **Async tool execution** — Parallel tool calls

## Quick Start

```bash
# Installation
pip install apex-agent

# Interactive REPL
apex

# One-shot prompt
apex "write a hello world program"

# Specific model
apex --model gpt-4o --stream "explain this code"
```

## Why APEX?

| Feature | APEX | OpenCode | Claude Code | Aider |
|---------|:----:|:--------:|:-----------:|:-----:|
| All models via one CLI | ✅ | ⚠️ some | ❌ | ⚠️ |
| No cloud lock-in | ✅ | ❌ | ❌ | ✅ |
| Offline (Ollama) | ✅ | ❌ | ❌ | ✅ |
| Rich syntax UI | ✅ | ✅ | ✅ | ❌ |
| Session persistence | ✅ | ❌ | ✅ | ❌ |
| Model switch mid-session | ✅ | ❌ | ❌ | ⚠️ |
| Token cost tracking | ✅ | ❌ | ❌ | ✅ |
| French/multilingual UI | ✅ | ❌ | ❌ | ❌ |

## Philosophy

APEX is built by a Gabonese developer for the world. Every developer deserves a world-class coding agent — regardless of which model they can afford.

- **Complete code, no truncation** — Never use `...rest of file...`
- **Production-ready** — Full error handling, tests, type hints
- **Language-agnostic** — Python, JavaScript, Rust, Go, etc.
- **Senior developer mindset** — Opinionated, but effective