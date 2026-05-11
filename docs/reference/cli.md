# CLI Reference

The APEX command-line interface provides full control over the application, from launching the TUI to running one-shot prompts in automated pipelines. All flags can be combined and overridden by configuration file values. This page documents every available command and flag.

## `apex`

Launches the APEX TUI (Terminal User Interface). This is the default command when no subcommand is specified. The TUI opens with the configured default model and the current working directory as the project root.

```bash
apex [OPTIONS]
```

### Options

| Flag | Short | Description | Default |
|---|---|---|---|
| `--model <name>` | `-m` | Set the default LLM model for this session. Accepts any of the 170+ supported model names (e.g., `gpt-4o`, `claude-sonnet-4-20250514`, `ollama/llama3`). | Value from `config.json` |
| `--ui` | | Launch the web-based UI instead of the TUI. Opens a browser tab at `http://localhost:3000`. | TUI |
| `--tui` | | Explicitly launch the terminal UI (default behavior). Useful when both UI modes are configured. | Enabled |
| `--cwd <path>` | | Set the working directory for the session. APEX will scope all file and shell operations to this directory. | Current directory |
| `--one-shot` | | Run in non-interactive mode. APEX processes the given prompt, outputs the result, and exits. Ideal for scripting and CI. | Interactive |
| `--stream` | | Stream the model's response to stdout in real time. Most useful with `--one-shot` for piping output. | Buffered |
| `--config <path>` | | Specify an alternative config file path. Overrides the default `~/.config/apex/config.json`. | Default path |
| `--verbose` | `-v` | Enable verbose logging. Outputs internal agent reasoning, tool selection, and API request details. | Quiet |
| `--version` | | Print the APEX version and exit. | — |
| `--help` | `-h` | Display help text and exit. | — |

## Examples

Launch with a specific model:
```bash
apex --model claude-sonnet-4-20250514
```

One-shot prompt with streaming output:
```bash
apex --one-shot --stream "List all TODO comments in src/"
```

Run in a specific project directory:
```bash
apex --cwd /path/to/my-project
```

Pipe input for automated workflows:
```bash
echo "Summarize the changes in the last 5 commits" | apex --one-shot --model gpt-4o
```
