# APEX — Development Guide

*Built in Gabon 🇬🇦 for the world.*

## Project Status

- **Version**: 1.3.0
- **Tests**: 1148 passing
- **Coverage**: 56%
- **License**: MIT

## Language & Tools

- **Language**: Python 3.11+
- **Package Manager**: pip
- **Test Framework**: pytest
- **LSP Server**: pylsp
- **Formatter**: ruff
- **Type Checker**: mypy
- **CI**: GitHub Actions

## Project Structure

```
APEX/
├── apex/                    # Main source code
│   ├── __init__.py          # Package init, exports (v1.3.0)
│   ├── main.py              # CLI entry point, argument parsing
│   ├── agent.py             # Agent core, LLM interaction
│   ├── tools.py             # 75+ built-in tools
│   ├── ui.py                # Rich terminal UI
│   ├── config.py            # Model definitions (95 models)
│   ├── tui.py               # Textual TUI
│   │
│   ├── refactored_*.py      # Refactored testable modules
│   │   ├── refactored_tools.py        (82%)
│   │   ├── refactored_workspace.py    (93%)
│   │   ├── refactored_mcp.py          (76%)
│   │   ├── refactored_plugins.py      (87%)
│   │   ├── refactored_sandbox.py      (82%)
│   │   ├── refactored_telemetry.py    (88%)
│   │   ├── refactored_mentions.py     (91%)
│   │   ├── refactored_slash.py        (88%)
│   │   ├── refactored_config_tools.py (94%)
│   │   ├── refactored_session.py      (92%)
│   │   ├── refactored_commands.py     (98%)
│   │   ├── refactored_extras.py       (97%)
│   │   ├── refactored_context.py      (88%)
│   │   ├── refactored_ui.py           (96%)
│   │   ├── refactored_tui_core.py     (98%)
│   │   ├── refactored_tui_theme.py    (100%)
│   │   └── refactored_tui_messages.py (100%)
│   │
│   └── original_*.py        # Original modules
│       ├── tools.py         # Main tools
│       ├── agent.py         # Agent
│       ├── workspace.py     # Workspace manager
│       ├── mcp.py           # MCP protocol
│       ├── plugins.py       # Plugin system
│       └── ...
│
├── tests/                   # Test suite (1148 tests)
│   ├── test_*.py           # Original tests
│   └── test_refactored_*.py # Refactored module tests
│
├── .github/
│   ├── workflows/          # CI/CD
│   │   ├── ci.yml         # Tests + lint
│   │   ├── release.yml    # PyPI publish
│   │   └── docs.yml       # MkDocs deploy
│   └── FUNDING.yml        # Sponsors
│
├── scripts/
│   ├── install.sh         # curl install
│   └── install.ps1        # PowerShell install
│
├── docs/                   # Documentation (MkDocs)
├── website/               # Landing page
├── pyproject.toml        # Project config
├── mkdocs.yml            # Docs config
├── README.md             # Main readme
├── CHANGELOG.md          # Version history
├── ROADMAP.md            # Public roadmap
├── CONTRIBUTING.md       # Contribution guide
├── CODE_OF_CONDUCT.md    # Community code
├── SECURITY.md           # Security policy
└── AGENTS.md             # This file
```

## Key Dependencies

```toml
litellm>=1.40.0        # Unified LLM interface (100+ models)
rich>=13.7.0           # Terminal UI
prompt_toolkit>=3.0.43 # Interactive REPL
textual>=0.1.0        # TUI framework
python-dotenv>=1.0.0  # .env support
pyyaml>=6.0           # YAML config
aiohttp>=3.9.0        # Async HTTP
click>=8.1.0          # CLI
pytest>=8.0.0         # Test framework
ruff>=0.4.0           # Linter
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

# Quick run (no coverage)
pytest --tb=no -q
```

## Code Quality

```bash
# Lint check (tests only for CI)
ruff check tests/ --select=E,F --ignore=E501,F841,E731,F811,E402

# Lint fix
ruff check --fix tests/

# Type check
mypy apex/ || true
```

## Testing Guidelines

When adding new functionality:

1. **Create testable code** — Use dependency injection, factory functions
2. **Write tests first** — Or alongside implementation
3. **Target 100% coverage** — On new refactored modules
4. **Keep lint clean** — No errors on new code
5. **Run full test suite** — Before committing

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
   │  tools.py   │  ← 75+ tools
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │    ui.py    │  ← Rich rendering
   └─────────────┘
```

## Model Support (95+ models)

APEX supports 95+ models via litellm:

- **Anthropic**: claude-3.5-sonnet, claude-4-sonnet, claude-4-opus
- **OpenAI**: gpt-4o, o1, o3-mini, o4-mini
- **Google**: gemini-2.0, gemini-flash
- **xAI**: grok-1, grok-2, grok-3
- **DeepSeek**: deepseek-chat, deepseek-coder, deepseek-v3, deepseek-r1
- **Meta**: llama-3, llama-3.1, llama-4
- **Mistral**: mistral, mixtral, codestral
- **Qwen**: qwen2, qwen2.5, qwen3
- **Groq**: llama-groq, mixtral-groq
- **Ollama**: llama3, codellama, mistral (local, no API key)

## Configuration

Create `~/.apex/config.json`:

```json
{
  "model": "claude-4-sonnet",
  "cwd": "/home/user/projects",
  "max_tool_rounds": 20,
  "theme": "apex-dark",
  "auto_commit": false
}
```

API keys in `~/.apex/.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=...
```

## GitHub Actions CI

```yaml
# .github/workflows/ci.yml
- Test: pytest (Python 3.11, 3.12)
- Lint: ruff (tests only)
- Coverage: codecov
```

## Installation

```bash
# pip
pip install apex-agent

# pipx (recommended)
pipx install apex-agent

# From source
git clone https://github.com/Ggboykxz/APEX
cd APEX
pip install -e ".[dev]"
```

## Contributing

1. Fork the repo
2. Create a feature branch
3. Add tests for new functionality
4. Ensure lint passes
5. Run tests: `pytest`
6. Commit with descriptive message
7. Submit PR

## Philosophy

- **Complete code** — Never truncate
- **Production-ready** — Full error handling, tests, type hints
- **Language-agnostic** — Python, JS, Rust, Go, etc.
- **Senior mindset** — Opinionated, efficient, complete
- **Testable by default** — Refactor modules for testability

---

*Made with ❤️ in Gabon 🇬🇦*
*APEX v1.3.0 — Day 1*