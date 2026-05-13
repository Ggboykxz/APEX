# Contributing to APEX

Thank you for your interest in contributing to APEX! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Ggboykxz/APEX
cd APEX

# Install dependencies
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=apex --cov-report=term-missing

# Lint check
ruff check apex/
```

## Code Style

- We use **ruff** for linting and formatting
- Target Python 3.11+
- Maximum line length: 100 characters
- Type hints are encouraged but not strictly required for new code

## Testing

All new features should include tests. We use pytest with:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_refactored_tools.py -v

# Run with coverage
pytest --cov=apex --cov-report=term-missing
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Run `ruff check apex/` to ensure lint passes
5. Commit with descriptive messages
6. Push to your fork and submit a PR

## Issue Types

- 🐛 **Bug**: Something isn't working
- 💡 **Feature**: New functionality
- 📖 **Documentation**: Docs improvements
- 🎨 **Refactoring**: Code improvements

## Code of Conduct

Please read our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before participating.

---

*Made with ❤️ in Gabon 🇬🇦*