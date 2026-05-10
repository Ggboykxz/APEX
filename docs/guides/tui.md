# TUI Interface

APEX features a rich terminal user interface built with OpenTUI and React, delivering a modern, responsive experience directly inside your terminal. The TUI uses a dark theme with a `#0d1117` background accented by cyan (`#00e5ff`) for interactive elements and green (`#00ff88`) for success indicators. The interface is designed to keep you focused on the conversation while providing quick access to models, tools, and agents through intuitive keybindings.

## Layout

The TUI is divided into four main panels. The **Chat Panel** occupies the center and displays the conversation thread, including agent messages, tool calls, and their results. The **Sidebar** on the left lists your session history and allows you to switch between conversations. The **Model Selector** appears as an overlay when invoked, showing all 100+ available models. The **Tool Panel** on the right shows active tool executions and their real-time output.

## Keybindings

Efficient navigation is at the heart of the APEX TUI. The following keybindings are available throughout the interface:

| Keybinding | Action |
|---|---|
| `Tab` | Cycle through agents (Coder, Architect, Planner, Reviewer, Shell) |
| `Ctrl+K` | Open the model selector to switch models mid-conversation |
| `Ctrl+O` | Toggle the sidebar (session history and navigation) |
| `Ctrl+T` | Toggle the tool panel (active tool executions) |
| `?` | Open the help overlay with all keybindings and quick tips |
| `Ctrl+C` | Cancel the current agent execution |
| `Enter` | Send the current prompt |
| `Esc` | Dismiss overlays and return focus to the input bar |

## Agent Switching

Pressing `Tab` cycles through APEX's five built-in agents: Coder, Architect, Planner, Reviewer, and Shell. Each agent has a specialized system prompt and tool preference set. The current agent is displayed in the status bar with a colored indicator. You can also mention a specific agent inline using `@coder`, `@architect`, etc.

## Customization

The TUI theme can be customized through `config.json` under the `tui` key. You can override colors, adjust panel sizes, and define custom keybindings. The default color scheme is optimized for readability on dark terminal backgrounds, but all colors are configurable to match your terminal emulator's palette.
