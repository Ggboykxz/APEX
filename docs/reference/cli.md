# CLI Reference

The APEX command-line interface provides full control over the application, from launching the TUI to running one-shot prompts in automated pipelines. All flags can be combined and overridden by configuration file values. This page documents every available command and flag.

## `apex`

Launches the APEX interactive REPL (Read-Eval-Print Loop). This is the default command when no subcommand or prompt is specified. The REPL opens with the configured default model and the current working directory as the project root.

```bash
apex [OPTIONS] [PROMPT]
```

### Subcommands

APEX supports convenient subcommands as positional arguments:

| Subcommand | Equivalent Flag | Description |
|---|---|---|
| `apex tui` | `apex --tui` | Launch the Terminal User Interface (OpenTUI + React) |
| `apex ui` | `apex --ui` | Same as `apex tui` |
| `apex models` | `apex --list-models` | List all available LLM models |
| `apex install-tui` | `apex --install-tui` | Install TUI dependencies (Bun + tui-frontend) |

### Options

| Flag | Short | Description | Default |
|---|---|---|---|
| `--model <name>` | `-m` | Set the default LLM model for this session. Accepts any of the 170+ supported model names (e.g., `gpt-4o`, `claude-sonnet-4-20250514`, `ollama/llama3`). | Value from `config.json` |
| `--ui` | | Launch the APEX TUI (OpenTUI + React). Same as `apex tui`. | REPL |
| `--tui` | `-t` | Launch the APEX TUI (same as `--ui`). | REPL |
| `--cwd <path>` | `-C` | Set the working directory for the session. APEX will scope all file and shell operations to this directory. | Current directory |
| `--one-shot` | `-1` | Run in non-interactive mode. APEX processes the given prompt, outputs the result, and exits. Ideal for scripting and CI. | Interactive |
| `--stream` | `-s` | Stream the model's response to stdout in real time. Most useful with `--one-shot` for piping output. | Buffered |
| `--auto-commit` | | Auto commit after successful task. | Disabled |
| `-p <prompt>` | | Direct prompt for CI/CD mode (no TUI). | — |
| `-f {text,json}` | `--format` | Output format for CI/CD mode. | `text` |
| `-q` | `--quiet` | Quiet mode (less output). | Verbose |
| `--list-models` | | List all available LLM models. Same as `apex models`. | — |
| `--install-tui` | | Install TUI dependencies (Bun + tui-frontend). Same as `apex install-tui`. | — |
| `--version` | `-v` | Print the APEX version and exit. | — |
| `--help` | `-h` | Display help text and exit. | — |

## Examples

Launch with a specific model:
```bash
apex --model claude-sonnet-4-20250514
```

Launch the TUI:
```bash
apex tui                    # Subcommand style
apex --tui                  # Flag style (same thing)
```

One-shot prompt with streaming output:
```bash
apex --one-shot --stream "List all TODO comments in src/"
```

List available models:
```bash
apex models                 # Subcommand style
apex --list-models          # Flag style (same thing)
```

Install TUI dependencies:
```bash
apex install-tui            # Subcommand style
apex --install-tui          # Flag style (same thing)
```

Run in a specific project directory:
```bash
apex --cwd /path/to/my-project
```

Pipe input for automated workflows:
```bash
echo "Summarize the changes in the last 5 commits" | apex --one-shot --model gpt-4o
```
