# APEX TUI

Terminal User Interface for APEX - AI-Powered Engineering eXtended.

Built with [OpenTUI](https://github.com/anomalyco/opentui) + React.

## Quick Start

```bash
cd tui-frontend
bun install
bun run start
```

## Keybindings

| Key | Action |
|-----|--------|
| `Tab` | Switch agent |
| `Ctrl+K` | Model selector |
| `Ctrl+O` | Toggle sidebar |
| `Ctrl+T` | Toggle tools panel |
| `?` | Help panel |
| `Escape` | Close overlay |
| `Ctrl+Q` | Quit APEX |

## Architecture

```
src/
├── App.tsx                    # Entry point
├── theme/
│   └── apex.ts                # APEX visual charter
├── data/
│   └── apex-data.ts           # Models, agents, tools, MCP/LSP data
└── components/
    ├── ApexApp.tsx            # Main application component
    ├── Sidebar.tsx            # Agent selector, sessions, server status
    ├── ChatPanel.tsx          # Chat interface with messages & input
    ├── StatusBar.tsx          # Bottom status bar
    ├── ModelSelector.tsx      # Model picker overlay
    ├── HelpPanel.tsx          # Help & keybindings overlay
    └── ToolPanel.tsx          # Tools & MCP/LSP panel
```

## Features

- **5 Agents**: Coder, Architect, Reviewer, DevOps, Analyst
- **100+ Models**: OpenAI, Anthropic, Google, Meta, Mistral, DeepSeek, xAI, etc.
- **75+ Tools**: File, Code, Shell, Git, Web, Database, Docker, K8s, Cloud, Security
- **MCP/LSP**: Server status monitoring
- **Theme**: Dark (#0d1117), Cyan (#00e5ff), Green (#00ff88)
