"""The tool schemas exposed to the model."""

from __future__ import annotations

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to write"},
                    "content": {"type": "string", "description": "Content to write to the file"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a unique string in a file with new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to edit"},
                    "old_string": {
                        "type": "string",
                        "description": "Unique string to find and replace",
                    },
                    "new_string": {"type": "string", "description": "String to replace it with"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command in the current working directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List directory contents with file sizes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory to list (default: .)"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_files",
            "description": "Search for a pattern across files in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (default: .)",
                    },
                },
                "required": ["pattern", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file or empty directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to file or directory to delete"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a directory (and parent directories if needed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of directory to create"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob_search",
            "description": "Find files by name pattern (glob).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (e.g., '**/*.py')"},
                    "directory": {
                        "type": "string",
                        "description": "Directory to search in (default: .)",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_tree",
            "description": "Show directory structure as ASCII tree.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory to display (default: .)"},
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to display (default: 3)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diff_files",
            "description": "Show unified diff between two files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path_a": {"type": "string", "description": "Path to first file"},
                    "path_b": {"type": "string", "description": "Path to second file"},
                },
                "required": ["path_a", "path_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_git_status",
            "description": "Show git status of the repository.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_git_log",
            "description": "Show recent git commits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of commits to show (default: 10)",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Show git diff (working tree or vs a reference).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref": {
                        "type": "string",
                        "description": "Git reference (branch, tag, commit) to diff against",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch and clean a webpage.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to fetch"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_repo_map",
            "description": "Generate repository map showing file structure and key files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to repository (default: .)"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "repo_map",
            "description": "Generate a token-budgeted, symbol-level repository map with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to repository (default: .)",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum estimated map tokens (default: 2000)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_image",
            "description": "Read an image file and return base64 encoding for vision models.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Path to image file"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_test",
            "description": "Run tests using pytest, jest, or cargo test.",
            "parameters": {
                "type": "object",
                "properties": {
                    "framework": {
                        "type": "string",
                        "description": "Test framework (pytest, jest, cargo)",
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to run tests (file, directory, or specific test)",
                    },
                },
                "required": ["framework", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "format_file",
            "description": "Format a file using black, prettier, or rustfmt.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Path to file to format"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "install_package",
            "description": "Install a package using pip, npm, or cargo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "manager": {
                        "type": "string",
                        "description": "Package manager (pip, npm, cargo)",
                    },
                    "package": {"type": "string", "description": "Package name to install"},
                },
                "required": ["manager", "package"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task",
            "description": "Delegate a task to a subagent for parallel execution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "description": "Subagent to invoke (general, explore)",
                    },
                    "task": {"type": "string", "description": "Task description for the subagent"},
                },
                "required": ["agent", "task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "preview_edit",
            "description": "Preview an edit without applying it. Shows the diff before confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to edit"},
                    "old_string": {"type": "string", "description": "Unique string to find"},
                    "new_string": {"type": "string", "description": "String to replace it with"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_edit",
            "description": "Apply a previously previewed edit using a preview ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "preview_id": {"type": "string", "description": "ID from preview_edit result"}
                },
                "required": ["preview_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clipboard_read",
            "description": "Read text from system clipboard.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clipboard_write",
            "description": "Write text to system clipboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to copy to clipboard"}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "Ask the user a question and wait for their response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Question to ask the user"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional multiple choice options",
                    },
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_code",
            "description": "Run code in a sandboxed environment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to execute"},
                    "language": {
                        "type": "string",
                        "description": "Language (python, javascript, bash, ruby, go, rust)",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Command line arguments",
                    },
                },
                "required": ["code", "language"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bookmark_session",
            "description": "Bookmark the current conversation position for later.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Bookmark name"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restore_bookmark",
            "description": "Restore conversation from a bookmark.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Bookmark name to restore"}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_conversation_stats",
            "description": "Get statistics about the current conversation.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "undo",
            "description": "Undo the last file modification or command execution.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "redo",
            "description": "Redo the last undone action.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "undo_info",
            "description": "Get information about what can be undone.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "redo_info",
            "description": "Get information about what can be redone.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "share_session",
            "description": "Share the current session as a shareable link.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_patch",
            "description": (
                "Apply a multi-file patch atomically. Supports Codex-style patches "
                "(*** Begin Patch ... *** End Patch) and unified diffs "
                "(--- a/path, +++ b/path). All files are validated before any write; "
                "use dry_run to preview. Paths must be relative to the project root."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patch": {
                        "type": "string",
                        "description": "Patch content to apply",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Validate and preview without writing files",
                        "default": False,
                    },
                },
                "required": ["patch"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_commands",
            "description": "List available custom commands.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command_custom",
            "description": "Execute a custom command by name with arguments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Command name to execute"},
                    "args": {"type": "object", "description": "Arguments to pass to the command"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lsp_definition",
            "description": "Go to definition using LSP (requires LSP config).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "line": {"type": "integer", "description": "Line number"},
                    "column": {"type": "integer", "description": "Column number"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lsp_references",
            "description": "Find references using LSP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "line": {"type": "integer", "description": "Line number"},
                    "column": {"type": "integer", "description": "Column number"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lsp_hover",
            "description": "Show hover information using LSP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "line": {"type": "integer", "description": "Line number"},
                    "column": {"type": "integer", "description": "Column number"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lsp_diagnostics",
            "description": "Get diagnostic errors using LSP.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_approve",
            "description": "Approve the pending plan to proceed with execution.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_reject",
            "description": "Reject the pending plan.",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string", "description": "Reason for rejection"}},
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "init_project",
            "description": "Analyze and initialize the project with AGENTS.md.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_project",
            "description": "Get detailed project analysis (language, deps, test framework).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_code_actions",
            "description": "Get suggested code actions/fixes from LSP diagnostics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to get actions for"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_code_action",
            "description": "Apply a suggested code action/fix.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_id": {"type": "string", "description": "Action ID to apply"}
                },
                "required": ["action_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_shell",
            "description": "Start an interactive shell session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "shell": {"type": "string", "description": "Shell to use (bash, zsh, fish)"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run command in persistent shell session.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Command to run"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_shell",
            "description": "Close the persistent shell session.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "select_files",
            "description": "Select multiple files for context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Glob patterns",
                    }
                },
                "required": ["patterns"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_create_branch",
            "description": "Create a new git branch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Branch name"},
                    "checkout": {"type": "boolean", "description": "Switch to new branch"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_switch_branch",
            "description": "Switch to an existing git branch.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Branch name"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_delete_branch",
            "description": "Delete a git branch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Branch name"},
                    "force": {"type": "boolean", "description": "Force delete"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_list_branches",
            "description": "List all git branches.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_create_pr",
            "description": "Create a GitHub pull request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "PR title"},
                    "body": {"type": "string", "description": "PR description"},
                    "base": {"type": "string", "description": "Target branch"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completions",
            "description": "Get auto-completions for files or commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["file", "command", "agent", "model"],
                        "description": "Completion type",
                    },
                    "prefix": {"type": "string", "description": "Prefix to match"},
                },
                "required": ["type", "prefix"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_image_data",
            "description": "Read and encode image for vision analysis.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Path to image file"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inline_edit",
            "description": "Edit a file inline at specific line.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "line": {"type": "integer", "description": "Line number"},
                    "content": {"type": "string", "description": "New content"},
                    "replace": {"type": "integer", "description": "Number of lines to replace"},
                },
                "required": ["path", "line", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retry_last",
            "description": "Retry the last failed tool execution.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_stage",
            "description": "Stage files for commit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to stage",
                    }
                },
                "required": ["files"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_unstage",
            "description": "Unstage files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to unstage",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Commit staged changes.",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string", "description": "Commit message"}},
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "List available skills.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "use_skill",
            "description": "Use a skill with arguments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Skill name"},
                    "args": {"type": "object", "description": "Skill arguments"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_in_files",
            "description": "Search and replace across multiple files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex)"},
                    "replacement": {"type": "string", "description": "Replacement string"},
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File patterns",
                    },
                    "dry_run": {"type": "boolean", "description": "Preview without applying"},
                },
                "required": ["pattern", "replacement", "files"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_code",
            "description": "Analyze code structure and complexity.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File to analyze"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_code",
            "description": "Explain what a code block does.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File to explain"},
                    "start": {"type": "integer", "description": "Start line"},
                    "end": {"type": "integer", "description": "End line"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_tests",
            "description": "Generate unit tests for a file or function.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File to generate tests for"},
                    "framework": {"type": "string", "description": "Test framework (pytest/jest)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_pre_commit",
            "description": "Run git pre-commit checks.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_keybindings",
            "description": "Show keyboard shortcuts.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_theme",
            "description": "Set terminal theme.",
            "parameters": {
                "type": "object",
                "properties": {"theme": {"type": "string", "description": "Theme name"}},
                "required": ["theme"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_git_hook",
            "description": "Add a git hook.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hook": {"type": "string", "description": "Hook name (pre-commit, etc.)"},
                    "command": {"type": "string", "description": "Command to run"},
                },
                "required": ["hook", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "batch_read",
            "description": "Read multiple files at once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File paths to read",
                    }
                },
                "required": ["paths"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "batch_write",
            "description": "Write multiple files at once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operations": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Write operations",
                    }
                },
                "required": ["operations"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retry_tool",
            "description": "Retry a failed tool with exponential backoff.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "Tool name to retry"},
                    "args": {"type": "object", "description": "Tool arguments"},
                    "retries": {"type": "integer", "description": "Number of retries"},
                },
                "required": ["tool", "args"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_tool_timeout",
            "description": "Get timeout for a specific tool.",
            "parameters": {
                "type": "object",
                "properties": {"tool": {"type": "string", "description": "Tool name"}},
                "required": ["tool"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_tool_timeout",
            "description": "Set custom timeout for a tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "Tool name"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds"},
                },
                "required": ["tool", "timeout"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_file_cache",
            "description": "Clear the file operation cache.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_context_info",
            "description": "Get context optimization info.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_file_watch",
            "description": "Start watching files for changes.",
            "parameters": {
                "type": "object",
                "properties": {"patterns": {"type": "array", "items": {"type": "string"}}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_file_watch",
            "description": "Stop file watcher.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expand_vars",
            "description": "Expand shell variables in text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text with variables"},
                    "vars": {"type": "object", "description": "Additional variables"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_env",
            "description": "Get environment variable.",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string", "description": "Variable name"}},
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_env",
            "description": "Set environment variable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Variable name"},
                    "value": {"type": "string", "description": "Variable value"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_env",
            "description": "List environment variables.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_task",
            "description": "Submit async task to queue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Task name"},
                    "command": {"type": "string", "description": "Command to run"},
                },
                "required": ["name", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List all tasks.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_task",
            "description": "Get task status.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": {"type": "string", "description": "Task ID"}},
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_history",
            "description": "Search conversation history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "fuzzy": {"type": "boolean", "description": "Use fuzzy matching"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_workspace",
            "description": "Validate workspace configuration.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "security_audit",
            "description": "Run security audit on project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File or directory to audit"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "refactor_code",
            "description": "Refactor code (add types, make async, extract method).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File to refactor"},
                    "function": {"type": "string", "description": "Function name"},
                    "style": {"type": "string", "description": "Style: async, type_hints, modern"},
                },
                "required": ["path", "function"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_db_model",
            "description": "Generate database model from table schema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table name"},
                    "columns": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Column definitions",
                    },
                },
                "required": ["table", "columns"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_dockerfile",
            "description": "Generate Dockerfile for language.",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "Language: python, node, go, rust, java",
                    }
                },
                "required": ["language"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_docker_compose",
            "description": "Generate docker-compose.yml.",
            "parameters": {
                "type": "object",
                "properties": {
                    "services": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Service definitions",
                    }
                },
                "required": ["services"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_api_client",
            "description": "Generate API client from OpenAPI spec.",
            "parameters": {
                "type": "object",
                "properties": {"spec": {"type": "string", "description": "Path to OpenAPI spec"}},
                "required": ["spec"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_docs",
            "description": "Generate documentation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "description": "Type: readme, api, markdoc"},
                    "path": {"type": "string", "description": "File path for api docs"},
                },
                "required": ["type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "profile_code",
            "description": "Profile code complexity and performance.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File to profile"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_code",
            "description": "Get optimization suggestions.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File to analyze"}},
                "required": ["path"],
            },
        },
    },
]


__all__ = ["TOOL_SCHEMAS"]
