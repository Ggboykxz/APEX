# Tips and Tricks

Getting the most out of APEX means understanding a few power-user techniques that dramatically improve your workflow. These tips cover everything from prompt engineering for AI agents to keyboard shortcuts that save you time in the TUI.

## Be Specific with Context

APEX works best when you provide clear, specific instructions. Instead of asking "fix the bug," tell it which file, which function, and what the expected behavior should be. The more context you give — file paths, error messages, stack traces — the more accurate and efficient the agent becomes. You can also use `@file:path/to/file` mentions to explicitly include files in the agent's context window.

## Leverage Agent Specialization

Don't use the Coder agent for everything. Switch to the **Architect** agent when designing systems, the **Planner** agent for breaking down complex tasks, the **Reviewer** agent for code reviews, and the **Shell** agent for DevOps and infrastructure work. Press `Tab` in the TUI to cycle agents, or prefix your prompt with `@architect` or `@reviewer` to route directly.

## Use One-Shot Mode for Scripts

The `--one-shot` flag runs APEX in non-interactive mode, making it perfect for CI pipelines and shell scripts. Pipe in a prompt, get a result, and exit. Combine with `--stream` for real-time output in automated workflows:

```bash
apex --one-shot --model gpt-4o "Explain what this project does based on README.md"
```

## Review Before Accepting

When `auto_approve` is disabled (the default), APEX will pause before executing destructive tools like `file_write` or `shell_exec`. Always review the proposed changes in the diff view before accepting. You can reject individual tool calls or cancel the entire operation with `Ctrl+C`.

## Manage Context Window

Long conversations can exhaust the context window and degrade performance. Use `/clear` to reset the conversation, or start a new session from the sidebar (`Ctrl+O`). The `context_tracking` system automatically summarizes older messages to keep the window efficient, but starting fresh is sometimes the fastest path.

## Combine Tools with Mentions

Use `@tool:shell` or `@tool:git` in your prompt to hint that a specific tool should be used. This is especially useful when the agent might not automatically select the right tool for an ambiguous task. APEX also respects MCP (Model Context Protocol) server connections — configure external MCP servers in `config.json` to extend the tool palette with custom integrations.
