# Tools

APEX provides **75+ built-in tools** for file operations, git, web, testing, LSP, MCP, Docker, databases, and more. These tools are automatically selected by the AI based on your requests.

## File Operations

| Tool | Description | Example |
|------|-------------|---------|
| `read_file` | Read file with line numbers | "Read src/main.py" |
| `write_file` | Create or overwrite file | "Create config.json" |
| `edit_file` | Replace unique string in file | "Fix the bug on line 42" |
| `delete_file` | Delete file or directory | "Delete old_file.txt" |
| `create_directory` | Create directory tree | "Create src/utils/" |
| `list_files` | List directory contents | "List files in src/" |
| `search_in_files` | Regex search | "Find all TODO comments" |
| `glob_search` | Find by pattern | "Find all .py files" |
| `apply_patch` | Apply diff/patch | "Apply the fix" |

## Advanced Tools

| Tool | Description |
|------|-------------|
| `get_file_tree` | ASCII tree of directory |
| `diff_files` | Unified diff between files |
| `get_repo_map` | Repository structure overview |
| `read_image` | Base64 encode image for vision |
| `preview_edit` | Preview changes before applying |
| `apply_edit` | Confirm previewed edit |

## Undo/Redo

| Tool | Description |
|------|-------------|
| `undo` | Undo last file modification |
| `redo` | Redo last undone action |
| `undo_info` | Show what can be undone |
| `redo_info` | Show what can be redone |

## Git Tools

| Tool | Description | Example |
|------|-------------|---------|
| `get_git_status` | Git status output | "Show git status" |
| `get_git_log` | Recent commits | "Show recent commits" |
| `git_diff` | Working tree diff | "Show changes" |
| `git_branch` | Branch info | "Current branch?" |
| `git_remote` | Remote info | "Show remote URL" |

## Web Tools

| Tool | Description | Example |
|------|-------------|---------|
| `web_search` | Search the web | "Search for Python asyncio" |
| `fetch_url` | Fetch webpage content | "Read this documentation" |

## LSP Tools

| Tool | Description | Example |
|------|-------------|---------|
| `lsp_definition` | Go to definition | "Go to definition of function" |
| `lsp_references` | Find references | "Find all references" |
| `lsp_hover` | Show hover info | "What's this function?" |
| `lsp_diagnostics` | Get errors/warnings | "Show all errors" |

## Development Tools

| Tool | Description | Example |
|------|-------------|---------|
| `run_command` | Execute shell command | "Run pytest" |
| `run_test` | Run test suite | "Run all tests" |
| `format_file` | Format code | "Format this file" |
| `install_package` | Install dependency | "Install requests" |
| `run_code` | Run code in sandbox | "Test this snippet" |

## Plan Workflow

| Tool | Description |
|------|-------------|
| `plan_approve` | Approve pending plan |
| `plan_reject` | Reject pending plan |

## Custom Commands

| Tool | Description |
|------|-------------|
| `list_commands` | List available custom commands |
| `run_command_custom` | Execute custom command |

## How Tools Work

APEX automatically selects and uses tools based on your natural language requests:

```
"You can read the file at src/main.py"
"Create a new file called utils.py with helper functions"
"Search for all TODO comments in the project"
"Go to the definition of the login function"
"Find all references to this variable"
"Show me the git status"
"Run the tests to see what's failing"
"Undo the last change"
"Share this session so my colleague can review"
```

### Tool Selection

The agent analyzes your request and selects the appropriate tool:

1. **File operations** → For reading/writing/editing files
2. **Git tools** → For version control operations
3. **LSP tools** → For code navigation and diagnostics
4. **Web tools** → For searching and fetching online content
5. **Development tools** → For running commands and tests

### Error Handling

If a tool fails, APEX will:
1. Show the error message
2. Try an alternative approach
3. Ask for clarification if needed

---

*See [Commands](commands.md) for slash commands and keyboard shortcuts.*