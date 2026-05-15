# TUI Interface

APEX features a rich terminal user interface built with Ink (React for terminals), delivering a modern, responsive experience directly inside your terminal. The TUI connects to the APEX backend via HTTP SSE streaming for real-time responses, with a WebSocket EventBus for bidirectional state synchronization following the OpenCode architecture pattern.

## Architecture

The TUI follows the OpenCode architecture pattern. When you launch `apex`, the Python backend starts an HTTP server on a random localhost port and writes the port to `~/.apex/state/` for discovery. The TUI frontend (Ink + React) reads this port and connects via both HTTP SSE for streaming responses and WebSocket for real-time event synchronization. This dual-channel architecture ensures low-latency token streaming while maintaining full state consistency between backend and frontend.

### Backend (Worker Thread)

The Python backend runs as the worker thread, handling all agent logic, tool execution, and LLM communication:

- **HTTP Server** — Hono-style API on random localhost port with SSE streaming
- **Agent Runtime** — 11 specialized agents with permission-aware tool execution
- **Session Storage** — SQLite-backed session persistence with Fernet encryption
- **Event Bus** — WebSocket-based event system for real-time state synchronization
- **LSP Integration** — Language Server Protocol for code intelligence
- **MCP Support** — Model Context Protocol for external tool integration
- **Plugin Loader** — Extensible plugin system with hooks

### Frontend (Main Thread)

The Ink + React TUI runs as the main thread, rendering the terminal UI at full speed:

- **Terminal Renderer** — Ink-based React renderer optimized for terminal output
- **Theme Detection** — Automatic dark/light mode detection from terminal settings
- **Mouse Support** — Click, scroll, and hover interactions in supported terminals
- **Router** — Home view (/) and Session view (/session/:id) with navigation
- **SyncProvider** — Real-time state synchronization via WebSocket EventBus
- **@ Autocomplete** — File, agent, and MCP server autocomplete when typing @
- **/ Slash Commands** — Built-in and custom command palette

## Layout

The TUI is divided into four main panels. The **Title Bar** at the top displays the current agent name, message count, context percentage (`X.X% ctx`), and total cost (`$X.XX`). The **Chat Panel** occupies the center and displays the conversation thread, including agent messages with per-message token counts (`+prompt/+completion · $cost`). The **Status Bar** at the bottom shows live In/Out/Total token counters, context percentage, and accumulated cost. The **Sidebar** on the left lists your session history. Overlays for **Model Selector** (Ctrl+K) and **Help Panel** (?) appear on demand.

## Keybindings

| Keybinding | Action |
|---|---|
| `Tab` / `Shift+Tab` | Cycle through agents (Coder, Architect, Planner, Shell) |
| `Ctrl+K` | Open the model selector to switch models mid-conversation |
| `Ctrl+P` | Open the command palette with fuzzy search |
| `Ctrl+L` | Clear all messages and reset token/cost metrics |
| `Ctrl+O` | Toggle the sidebar (session history and navigation) |
| `Ctrl+X` | Leader key prefix (see below) |
| `Ctrl+X N` | New session |
| `Ctrl+X U` | Undo last action |
| `Ctrl+X R` | Redo last undone action |
| `Ctrl+X C` | Compact context window |
| `Ctrl+X M` | List available models |
| `Ctrl+X T` | Theme selector |
| `Ctrl+X S` | Status overview |
| `Ctrl+X A` | Agent list |
| `Ctrl+X L` | Sessions list |
| `Ctrl+X B` | Toggle sidebar |
| `Ctrl+X E` | Open editor |
| `Ctrl+X X` | Export session |
| `Ctrl+X Q` | Quit |
| `@` | File/agent/MCP autocomplete |
| `!` | Bash command inline |
| `?` | Help overlay |
| `Ctrl+T` | Cycle reasoning variants |
| `Ctrl+C` | Cancel current execution |
| `Enter` | Send the current prompt |
| `Esc` | Dismiss overlays and return focus to the input bar |

## Live Metrics

The TUI displays real-time metrics as you interact with the agent, synchronized via the WebSocket EventBus:

- **Token Streaming**: Live prompt/completion token counts update as tokens arrive
- **Cost Tracking**: Per-message cost (`+promptTokens · $cost`) and session total
- **Context Percentage**: Context window utilization based on model's context limit (e.g., `2.3% ctx`)
- **Agent Theming**: Title bar, status bar, and panel borders change color based on the active agent

## Agent Switching

Pressing `Tab` cycles through APEX's five built-in agents: Coder, Architect, Planner, Reviewer, and Shell. Each agent has a specialized system prompt and tool preference set. The current agent's color is reflected throughout the interface (title bar, status bar, borders). You can also mention a specific agent inline using `@coder`, `@architect`, etc.

## Model Selector

Pressing `Ctrl+K` opens the model selector overlay with all 170+ supported models organized by provider (Anthropic, OpenAI, Google, Groq, Mistral, DeepSeek, Meta, xAI, Qwen, Cohere, Ollama, etc.). Each model entry shows its approximate context window size and cost category (e.g., `$0.00` for local models).

## @ Autocomplete

Typing `@` in the input opens an autocomplete menu with three categories:

- **Files** — Fuzzy search across your project files
- **Agents** — Quick mention of a specific agent (@reviewer, @explore, etc.)
- **MCP Servers** — Reference tools from connected MCP servers

## / Slash Commands

APEX supports built-in and custom slash commands:

- `/model <name>` — Switch model mid-session
- `/agent <name>` — Switch agent
- `/share` — Create shareable session URL
- `/undo` — Undo last change
- `/redo` — Redo last undone change
- `/compact` — Compact context window
- `/clear` — Clear conversation history
- `/help` — Show all commands
- Custom commands via `.apex/commands/*.md`

## Connection Error Handling

If the backend HTTP server becomes unreachable, the TUI displays a connection error banner that automatically dismisses after 5 seconds. The error message includes the specific error returned by the server (e.g., `"Unknown model: xxx"` for invalid model IDs). The WebSocket EventBus will automatically attempt to reconnect when the backend becomes available again.

## Customization

The TUI theme can be customized through `apex.json` or `tui.json` under the `tui` key. You can override colors, adjust panel sizes, and define custom keybindings. The default color scheme is optimized for readability on dark terminal backgrounds, but all colors are configurable to match your terminal emulator's palette. Custom themes can be placed in `~/.config/apex/themes/*.json` or `.apex/themes/*.json`.

## Startup Time

The TUI targets a 200-800ms startup time, following the OpenCode architecture pattern. The backend initializes first (HTTP server, agent runtime, session storage), then the frontend connects and renders. The state directory (`~/.apex/state/`) enables fast port discovery without manual configuration.
