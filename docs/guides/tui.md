# TUI Interface

APEX features a rich terminal user interface built with OpenTUI and React, delivering a modern, responsive experience directly inside your terminal. The TUI connects to the APEX backend via HTTP SSE streaming for real-time responses. The interface uses a dark theme with agent-colored theming — each agent has its own color scheme applied to the titlebar, status bar, and borders.

## Architecture

The TUI communicates with the APEX backend through a local HTTP server started automatically when launching `apex --tui`. The server runs on `127.0.0.1:8080` and exposes a streaming endpoint at `/chat/stream`. Messages are streamed token-by-token using Server-Sent Events (SSE).

## Layout

The TUI is divided into four main panels. The **Title Bar** at the top displays the current agent name, message count, context percentage (`X.X% ctx`), and total cost (`$X.XX`). The **Chat Panel** occupies the center and displays the conversation thread, including agent messages with per-message token counts (`+prompt/+completion · $cost`). The **Status Bar** at the bottom shows live In/Out/Total token counters, context percentage, and accumulated cost. The **Sidebar** on the left lists your session history. Overlays for **Model Selector** (Ctrl+K) and **Help Panel** (?) appear on demand.

## Keybindings

| Keybinding | Action |
|---|---|
| `Tab` | Cycle through agents (Coder, Architect, Planner, Reviewer, Shell) |
| `Ctrl+K` | Open the model selector to switch models mid-conversation |
| `Ctrl+L` | Clear all messages and reset token/cost metrics |
| `Ctrl+O` | Toggle the sidebar (session history and navigation) |
| `Ctrl+T` | Toggle the tool panel (active tool executions) |
| `?` | Open the help overlay with all keybindings and quick tips |
| `Ctrl+C` | Cancel the current agent execution |
| `Enter` | Send the current prompt |
| `Esc` | Dismiss overlays and return focus to the input bar |

## Live Metrics

The TUI displays real-time metrics as you interact with the agent:

- **Token Streaming**: Live prompt/completion token counts update as tokens arrive
- **Cost Tracking**: Per-message cost (`+promptTokens · $cost`) and session total
- **Context Percentage**: Context window utilization based on model's context limit (e.g., `2.3% ctx`)
- **Agent Theming**: Title bar, status bar, and panel borders change color based on the active agent

## Agent Switching

Pressing `Tab` cycles through APEX's five built-in agents: Coder, Architect, Planner, Reviewer, and Shell. Each agent has a specialized system prompt and tool preference set. The current agent's color is reflected throughout the interface (title bar, status bar, borders). You can also mention a specific agent inline using `@coder`, `@architect`, etc.

## Model Selector

Pressing `Ctrl+K` opens the model selector overlay with all 170+ supported models organized by provider (Anthropic, OpenAI, Google, Groq, Mistral, DeepSeek, Meta, xAI, Qwen, Cohere, Ollama, etc.). Each model entry shows its approximate context window size and cost category (e.g., `$0.00` for local models).

## Connection Error Handling

If the backend HTTP server becomes unreachable, the TUI displays a connection error banner that automatically dismisses after 5 seconds. The error message includes the specific error returned by the server (e.g., `"Unknown model: xxx"` for invalid model IDs).

## Customization

The TUI theme can be customized through `config.json` under the `tui` key. You can override colors, adjust panel sizes, and define custom keybindings. The default color scheme is optimized for readability on dark terminal backgrounds, but all colors are configurable to match your terminal emulator's palette.
