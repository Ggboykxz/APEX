# Contributing to APEX

We are thrilled that you want to contribute to APEX! Whether you are fixing a bug, adding a new tool, improving documentation, or proposing a new agent, your contributions make APEX better for everyone. This guide covers the standard workflow for contributing to the project.

## Clone the Repository

Start by forking the repository on GitHub and cloning your fork locally:

```bash
git clone https://github.com/YOUR_USERNAME/APEX.git
cd APEX
git remote add upstream https://github.com/Ggboykxz/APEX.git
```

Keep your fork synchronized with the upstream repository by regularly running `git fetch upstream` and merging changes into your local branch.

## Install Development Dependencies

APEX uses Python 3.10+ and Bun for the TUI frontend. Install the full development environment with:

```bash
# Python backend
pip install -e ".[dev]"

# TUI frontend (OpenTUI + React)
cd tui-frontend
bun install
```

This installs all testing frameworks, linters, and pre-commit hooks. The pre-commit configuration runs `ruff` for linting and `black` for formatting on every commit.

## Run Tests

APEX has a comprehensive test suite covering the agent system, tools, MCP integration, LSP diagnostics, and the HTTP API. Run the full suite with:

```bash
# Run all tests
pytest

# Run a specific test module
pytest tests/test_tools.py

# Run with coverage
pytest --cov=apex --cov-report=html
```

For the TUI frontend, run:

```bash
cd tui-frontend
bun test
```

All tests must pass before submitting a pull request. If you are adding a new feature, include corresponding test cases in the `tests/` directory.

## Submit a Pull Request

1. Create a feature branch: `git checkout -b feature/my-new-feature`
2. Make your changes with clear, descriptive commit messages
3. Ensure all tests pass and linting is clean
4. Push to your fork: `git push origin feature/my-new-feature`
5. Open a pull request against the `main` branch of `Ggboykxz/APEX`

In your PR description, explain the motivation for the change, reference any related issues, and note any breaking changes. A maintainer will review your code, provide feedback, and merge once approved. Thank you for contributing!
