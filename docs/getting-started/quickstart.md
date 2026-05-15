# Quick Start

Getting up and running with APEX takes just a few minutes. This guide walks you through the three essential steps: configuring your API key, launching the application, and issuing your first prompt. By the end, you will have a fully functional AI coding agent ready to assist with your development workflow.

## Step 1 — Set Your API Key

APEX requires at least one LLM provider API key to function. The most common choice is OpenAI, but APEX supports 170+ models across providers including Anthropic, Google, and local Ollama instances. Export your key as an environment variable:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

You can also add the key to a `.env` file in your project root or configure it through the `config.json` file. Multiple keys can be set simultaneously, and APEX will route requests to the correct provider based on the selected model.

## Step 2 — Launch APEX

Start the interactive REPL by simply running:

```bash
apex
```

Or launch the TUI (Terminal User Interface) directly:

```bash
apex tui
```

The TUI launches by default when you run `apex`. It is a rich terminal interface built with Ink and React featuring a dark theme (`#0d1117` background) with cyan (`#00e5ff`) and green (`#00ff88`) accents. The backend starts on a random localhost port with a WebSocket EventBus for real-time synchronization. The interface provides a chat panel, model selector, tool panel, and sidebar for managing sessions.

## Step 3 — Your First Prompt

Once the TUI is running, type your request in the input bar at the bottom of the screen. For example:

```
Fix the authentication bug in auth.py
```

APEX will analyze your project context, select the appropriate agent (Coder, Architect, Reviewer, Shell, or Planner), and begin executing the task. You can observe tool calls in real time, switch between agents with `Tab`, and review the full change set before accepting. Press `?` at any time to see all available keybindings.

## Switching Models

You can switch between any of the 170+ supported models mid-session using `Ctrl+K`. This allows you to compare outputs from different providers, optimize costs, or use a local Ollama model when you don't have internet access.

Congratulations — you are now using APEX! Explore the rest of the documentation to learn about model selection, tool configuration, and advanced workflows.
