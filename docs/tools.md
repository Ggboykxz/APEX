# Tools

APEX provides 21 tools for file operations, git, web, testing, and more.

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

## Advanced Tools

| Tool | Description |
|------|-------------|
| `get_file_tree` | ASCII tree of directory |
| `diff_files` | Unified diff between files |
| `get_repo_map` | Repository structure overview |
| `read_image` | Base64 encode image for vision |

## Git Tools

| Tool | Description |
|------|-------------|
| `get_git_status` | Git status output |
| `get_git_log` | Recent commits |
| `git_diff` | Working tree diff |

## Web Tools

| Tool | Description |
|------|-------------|
| `web_search` | Search the web |
| `fetch_url` | Fetch and clean webpage |

## Development Tools

| Tool | Description |
|------|-------------|
| `run_command` | Execute shell command |
| `run_test` | Run pytest/jest/cargo tests |
| `format_file` | Format with black/prettier/rustfmt |
| `install_package` | Install pip/npm/cargo package |

## Usage

APEX automatically uses tools based on your prompts. Examples:

```
"Read the file at src/main.py"
"Create a new file called utils.py with helper functions"
"Search for all TODO comments in the codebase"
"Run the tests"
"Show me the git status"
"Search for how to use FastAPI"
```