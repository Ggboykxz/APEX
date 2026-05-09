# Contributing to APEX

Thank you for your interest in contributing to APEX! This guide will help you get started.

## Code of Conduct

Please be respectful and professional. We're building a tool for developers worldwide.

## Getting Started

### Prerequisites

- Python 3.11+
- pip or pipx
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/Ggboykxz/APEX.git
cd APEX

# Install in development mode
pip install -e .

# Install dev dependencies (testing, linting)
pip install -e ".[dev]"

# Verify installation
apex --version
```

## Making Changes

### 1. Create a branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make your changes

Follow the coding standards:
- Use type hints on all functions
- Use f-strings, never % formatting
- Use pathlib.Path for file operations
- Use dataclasses for structured data

### 3. Test your changes

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_refactored_your_module.py -v

# Run with coverage
pytest --cov=apex --cov-report=term-missing
```

### 4. Lint your code

```bash
# Check for issues
ruff check apex/

# Auto-fix issues
ruff check --fix apex/
```

### 5. Commit your changes

Follow the commit message format:

```
type(scope): description

Examples:
- feat(tools): add new file operation
- fix(agent): handle timeout gracefully
- refactor(workspace): improve git detection
- docs(readme): update installation guide
- test(sandbox): add timeout tests
- chore(deps): update litellm version
```

## Pull Request Process

1. **Ensure tests pass** — All tests must pass before submitting PR
2. **Update documentation** — If you add features, update relevant docs
3. **Describe your changes** — Explain what you changed and why
4. **Keep PRs focused** — One feature/fix per PR

## Project Structure

```
APEX/
├── apex/              # Source code
│   ├── refactored_*.py  # Testable modules
│   └── original_*.py    # Original modules
├── tests/             # Test suite
├── docs/              # Documentation
└── pyproject.toml     # Project config
```

## Testing Guidelines

- Write tests for new functionality
- Use descriptive test names
- Test edge cases and error conditions
- Target high coverage on new code

### Test File Structure

```python
# tests/test_refactored_example.py
import pytest
from apex.refactored_example import MyClass

class TestMyClass:
    def test_basic_functionality(self):
        # Test implementation
        pass
    
    def test_edge_case(self):
        # Test edge case
        pass
```

## Questions?

- Open an issue for bugs or feature requests
- Join our community (if available)
- Check existing issues before creating new ones

---

*Thank you for contributing to APEX! 🇬🇦*