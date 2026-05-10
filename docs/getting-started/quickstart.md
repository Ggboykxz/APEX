# Quick Start

Getting up and running with APEX takes just a few minutes. This guide walks you through the three essential steps: configuring your API key, launching the application, and issuing your first prompt. By the end, you will have a fully functional AI coding agent ready to assist with your development workflow.

## Step 1 — Set Your API Key

APEX requires at least one LLM provider API key to function. The most common choice is OpenAI, but APEX supports 100+ models across providers including Anthropic, Google, and local Ollama instances. Export your key as an environment variable:

```bash
export OPENAI_API_KEY="sk-..."
```

You can also add the key to a `.env` file in your project root or configure it through the `config.json` file. Multiple keys can be set simultaneously, and APEX will route requests to the correct provider based on the selected model.

## Step 2 — Launch APEX

Start the terminal UI by simply running:

```bash
apex
```

This opens the APEX TUI — a rich terminal interface built with OpenTUI and React featuring a dark theme (`#0d1117` background) with cyan (`#00e5ff`) and green (`#00ff88`) accents. The interface provides a chat panel, model selector, tool panel, and sidebar for managing sessions.

## Step 3 — Your First Prompt

Once the TUI is running, type your request in the input bar at the bottom of the screen. For example:

```
Refactor the authentication module in src/auth.py to use JWT tokens instead of session cookies.
```

APEX will analyze your project context, select the appropriate agent and tools, and begin executing the task. You can observe tool calls in real time, switch between agents with `Tab`, and review the full change set before accepting. Press `?` at any time to see all available keybindings.

Congratulations — you are now using APEX! Explore the rest of the documentation to learn about model selection, tool configuration, and advanced workflows.
