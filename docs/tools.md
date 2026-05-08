# Tools

APEX provides 40+ tools for file operations, git, web, testing, LSP, and more.

## File Operations

| Tool | Description |
|------|-------------|
| `read_file` | Read file with line numbers |
| `write_file` | Create or overwrite file |
| `edit_file` | Replace unique string in file |
| `delete_file` | Delete file or empty directory |
| `create_directory` | Create directory tree |
| `list_files` | List directory with file sizes |
| `search_in_files` | Regex search across files |
| `glob_search` | Find files by pattern |
| `apply_patch` | Apply patch/diff to files |

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

## Session Management

| Tool | Description |
|------|-------------|
| `share_session` | Share session as link |
| `bookmark_session` | Bookmark current position |
| `restore_bookmark` | Restore from bookmark |

## Git Tools

| Tool | Description |
|------|-------------|
| `get_git_status` | Git status output |
| `get_git_log` | Recent commits |
| `git_diff` | Working tree diff |
| `git_branch` | Branch info |
| `git_remote` | Remote info |

## Web Tools

| Tool | Description |
|------|-------------|
| `web_search` | Search the web |
| `fetch_url` | Fetch and clean webpage |

## LSP Tools

| Tool | Description |
|------|-------------|
| `lsp_definition` | Go to definition |
| `lsp_references` | Find references |
| `lsp_hover` | Show hover info |
| `lsp_diagnostics` | Get diagnostic errors |

## Development Tools

| Tool | Description |
|------|-------------|
| `run_command` | Execute shell command |
| `run_test` | Run pytest/jest/cargo tests |
| `format_file` | Format with black/prettier/rustfmt |
| `install_package` | Install pip/npm/cargo package |
| `run_code` | Run code in sandbox |

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

## Usage

APEX automatically uses tools based on your prompts:

```
"Read the file at src/main.py"
"Create a new file called utils.py with helper functions"
"Search for all TODO comments"
"Go to definition of function foo"
"Find all references to this variable"
"Undo the last change"
"Share this session"
```