# APEX — Development Guide

*Built in Gabon 🇬🇦 for the world.*

## Language & Tools

- **Language**: Python 3.11+
- **Package Manager**: pip
- **Test Framework**: pytest
- **LSP Server**: pylsp
- **Formatter**: ruff
- **Type Checker**: pyright (optional)

## Project Structure

```
APEX/
├── apex/                    # Main source code
│   ├── __init__.py          # Package init, exports
│   ├── main.py              # CLI entry point, argument parsing
│   ├── agent.py             # Agent core, LLM interaction
│   ├── tools.py             # 31+ built-in tools (1,200+ lines)
│   ├── ui.py                # Rich terminal UI
│   ├── config.py            # Model definitions (85+ models)
│   │
│   ├── refactored_*.py      # Refactored testable modules (NEW!)
│   │   ├── refactored_tools.py
│   │   ├── refactored_workspace.py
│   │   ├── refactored_mcp.py
│   │   ├── refactored_plugins.py
│   │   ├── refactored_sandbox.py
│   │   ├── refactored_telemetry.py
│   │   ├── refactored_mentions.py
│   │   ├── refactored_slash.py
│   │   ├── refactored_config_tools.py
│   │   ├── refactored_session.py
│   │   ├── refactored_commands.py
│   │   ├── refactored_extras.py
│   │   ├── refactored_context.py
│   │   └── refactored_ui.py
│   │
│   └── original_*.py        # Original modules (being refactored)
│       ├── tools.py         # Main tools (needs refactoring)
│       ├── agent.py         # Agent (async, complex)
│       ├── workspace.py     # Workspace manager
│       ├── mcp.py           # MCP protocol
│       ├── plugins.py       # Plugin system
│       └── ...
│
├── tests/                   # Test suite
│   ├── test_tools.py        # Tools tests
│   ├── test_ui.py           # UI tests
│   ├── test_session.py      # Session tests
│   ├── test_tools_extended.py
│   │
│   └── test_refactored_*.py # Refactored module tests (16 files)
│
├── docs/                    # Documentation
│   ├── index.md             # Main doc
│   ├── installation.md
│   ├── commands.md
│   ├── configuration.md
│   ├── models.md            # 85+ supported models
│   ├── tools.md             # Tool reference
│   ├── agents.md            # Multi-agent system
│   └── ...
│
├── pyproject.toml           # Project config (ruff, pytest)
├── README.md                # Main readme
└── AGENTS.md                # This file
```

## Key Dependencies

```toml
litellm>=1.0.0          # Unified LLM interface (100+ models)
rich>=13.0.0            # Terminal UI
prompt_toolkit>=3.0.0   # Interactive REPL
python-dotenv>=1.0.0   # .env support
pyyaml>=6.0            # YAML config
aiohttp>=3.9.0          # Async HTTP
pyperclip>=1.8.0        # Clipboard
pytest>=7.0.0           # Test framework
ruff                     # Linter/formatter
```

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=apex --cov-report=term-missing

# Specific test file
pytest tests/test_refactored_tools.py -v

# Run refactored tests only
pytest tests/test_refactored_*.py -v
```

## Code Quality

```bash
# Lint check
ruff check apex/

# Fix auto-fixable issues
ruff check --fix apex/

# Type check (optional)
pyright apex/
```

## Testing Guidelines

When adding new functionality:

1. **Create testable code** — Use dependency injection, factory functions
2. **Write tests first** — Or alongside implementation
3. **Target 100% coverage** — On new refactored modules
4. **Keep lint 100%** — No warnings, no errors

### Refactoring Pattern

Instead of modifying original modules (risky), create `refactored_*.py`:

```python
# apex/refactored_example.py
class RefactoredClass:
    def __init__(self, dependency=None):
        self._dependency = dependency or default_dependency
    
    def method(self, param):
        # Testable implementation
        pass

def create_class(dependency=None):
    return RefactoredClass(dependency)
```

## Architecture

```
User Input (prompt_toolkit)
        │
        ▼
   ┌─────────────┐
   │  main.py    │  ← CLI, argument parsing
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐       ┌──────────────────┐
   │  agent.py   │──────▶│  litellm          │  ← 100+ models
   └──────┬──────┘       └──────────────────┘
          │
          ▼  tool_calls
   ┌─────────────┐
   │  tools.py   │  ← 31+ tools
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │    ui.py    │  ← Rich rendering
   └─────────────┘
```

## Model Support

APEX supports 85+ models via litellm:

- **Anthropic**: claude-3.5, claude-4, claude-sonnet
- **OpenAI**: gpt-4o, o1, o3, o4-mini
- **Google**: gemini-1.5, gemini-2.0, gemini-2.5
- **xAI**: grok-1, grok-2, grok-3, grok-4
- **DeepSeek**: deepseek-chat, deepseek-coder, deepseek-v3, deepseek-r1
- **Meta**: llama-3, llama-3.1, llama-4
- **Mistral**: mistral, mixtral, codestral
- **Qwen**: qwen2, qwen2.5, qwen3
- **And more**: Amazon Nova, Cohere, Microsoft Phi, etc.

## Configuration

Create `~/.apex/config.json`:

```json
{
  "model": "claude-4-sonnet",
  "cwd": "/home/user/projects",
  "max_tool_rounds": 20
}
```

API keys in `~/.apex/.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=...
```

## Contributing

1. Fork the repo
2. Create a feature branch
3. Add tests for new functionality
4. Ensure lint passes: `ruff check apex/`
5. Run tests: `pytest`
6. Commit with descriptive message
7. Submit PR

## Philosophy

- **Complete code** — Never truncate, never use `...rest of file...`
- **Production-ready** — Full error handling, tests, type hints
- **Language-agnostic** — Python, JS, Rust, Go, etc.
- **Senior mindset** — Opinionated, efficient, complete
- **Testable by default** — Refactor modules for testability

---

*Made with ❤️ in Gabon 🇬🇦*