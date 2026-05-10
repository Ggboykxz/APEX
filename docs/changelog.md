# Changelog

All notable changes to APEX are documented in this file. The project follows [Semantic Versioning](https://semver.org/) and each release includes a summary of features, fixes, and breaking changes.

## v1.3.0 (Current)

### Highlights

This release introduces the TUI v2.0 rebuilt from the ground up with OpenTUI and React, delivering a significantly faster and more responsive terminal interface. The new TUI features a dark theme with `#0d1117` background, cyan (`#00e5ff`) accents, and green (`#00ff88`) success indicators. Keybindings have been redesigned for efficiency: `Tab` to cycle agents, `Ctrl+K` for model selection, `Ctrl+O` to toggle the sidebar, `Ctrl+T` for the tool panel, and `?` for help.

### Features

- **TUI v2.0**: Complete rewrite using OpenTUI + React for improved rendering performance and component architecture
- **5 Agents**: Added Planner and Reviewer agents alongside Coder, Architect, and Shell
- **100+ Models**: Expanded model support including Gemini 2.5 Pro, Claude Sonnet 4, and GPT-4o
- **75+ Tools**: Added Kubernetes tools (`k8s_get`, `k8s_apply`, `k8s_logs`), cloud tools for AWS/GCP/Azure, and security scanning tools
- **MCP Integration**: Full Model Context Protocol support for extending tools via external servers
- **LSP Diagnostics**: Real-time language server integration for 30+ languages with inline error reporting
- **Session Management**: Persistent sessions with history, search, and restore across restarts

### Fixes

- Fixed streaming response truncation on large outputs
- Resolved context window overflow in long conversations with automatic summarization
- Fixed `git_undo` not properly restoring file permissions
- Corrected model routing for Ollama models with custom hosts

### Breaking Changes

- Configuration file format updated; run `apex config migrate` to upgrade
- `--no-tui` flag removed; use `--one-shot` for non-interactive mode
- Minimum Python version raised to 3.10

## v1.2.0

- Initial MCP (Model Context Protocol) support
- Added Docker and database tool categories
- Introduced agent specialization with dedicated system prompts
- Added `--one-shot` and `--stream` CLI flags
- Shell security policies and permission system

## v1.1.0

- Expanded model support to 80+ models
- Added Git tools with `git_undo` for safe rollback
- Introduced the first version of the TUI with basic keybindings
- Config file support (`config.json` and `.env`)
- HTTP API with OpenAI-compatible endpoints

## v1.0.0

- Initial release of APEX
- Core agent loop with tool execution
- Support for OpenAI and Anthropic models
- Basic CLI with interactive prompt mode
- File, Code, Shell, Git, and Web tool categories
