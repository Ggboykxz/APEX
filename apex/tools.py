"""Tools for APEX - file operations, command execution, git, web, and more."""

import base64
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
import aiohttp
import asyncio

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
                "required": ["path"]
            }
        }
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
                    "content": {"type": "string", "description": "Content to write to the file"}
                },
                "required": ["path", "content"]
            }
        }
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
                    "old_string": {"type": "string", "description": "Unique string to find and replace"},
                    "new_string": {"type": "string", "description": "String to replace it with"}
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
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
                "required": ["command"]
            }
        }
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
                "required": ["path"]
            }
        }
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
                    "path": {"type": "string", "description": "Directory to search in (default: .)"}
                },
                "required": ["pattern", "path"]
            }
        }
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
                "required": ["path"]
            }
        }
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
                "required": ["path"]
            }
        }
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
                    "directory": {"type": "string", "description": "Directory to search in (default: .)"}
                },
                "required": ["pattern"]
            }
        }
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
                    "max_depth": {"type": "integer", "description": "Maximum depth to display (default: 3)"}
                },
                "required": ["path"]
            }
        }
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
                    "path_b": {"type": "string", "description": "Path to second file"}
                },
                "required": ["path_a", "path_b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_git_status",
            "description": "Show git status of the repository.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_git_log",
            "description": "Show recent git commits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer", "description": "Number of commits to show (default: 10)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Show git diff (working tree or vs a reference).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref": {"type": "string", "description": "Git reference (branch, tag, commit) to diff against"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch and clean a webpage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"}
                },
                "required": ["url"]
            }
        }
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
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_image",
            "description": "Read an image file and return base64 encoding for vision models.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to image file"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_test",
            "description": "Run tests using pytest, jest, or cargo test.",
            "parameters": {
                "type": "object",
                "properties": {
                    "framework": {"type": "string", "description": "Test framework (pytest, jest, cargo)"},
                    "path": {"type": "string", "description": "Path to run tests (file, directory, or specific test)"}
                },
                "required": ["framework", "path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "format_file",
            "description": "Format a file using black, prettier, or rustfmt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to file to format"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "install_package",
            "description": "Install a package using pip, npm, or cargo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "manager": {"type": "string", "description": "Package manager (pip, npm, cargo)"},
                    "package": {"type": "string", "description": "Package name to install"}
                },
                "required": ["manager", "package"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "task",
            "description": "Delegate a task to a subagent for parallel execution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "description": "Subagent to invoke (general, explore)"},
                    "task": {"type": "string", "description": "Task description for the subagent"}
                },
                "required": ["agent", "task"]
            }
        }
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
                    "new_string": {"type": "string", "description": "String to replace it with"}
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
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
                "required": ["preview_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clipboard_read",
            "description": "Read text from system clipboard.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
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
                "required": ["text"]
            }
        }
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
                    "options": {"type": "array", "items": {"type": "string"}, "description": "Optional multiple choice options"}
                },
                "required": ["question"]
            }
        }
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
                    "language": {"type": "string", "description": "Language (python, javascript, bash, ruby, go, rust)"},
                    "args": {"type": "array", "items": {"type": "string"}, "description": "Command line arguments"}
                },
                "required": ["code", "language"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "bookmark_session",
            "description": "Bookmark the current conversation position for later.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Bookmark name"}
                },
                "required": ["name"]
            }
        }
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
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_history",
            "description": "Search the conversation history for a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_conversation_stats",
            "description": "Get statistics about the current conversation.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "undo",
            "description": "Undo the last file modification or command execution.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "redo",
            "description": "Redo the last undone action.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "undo_info",
            "description": "Get information about what can be undone.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "redo_info",
            "description": "Get information about what can be redone.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "share_session",
            "description": "Share the current session as a shareable link.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "apply_patch",
            "description": "Apply a patch/diff to files in the codebase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patch": {"type": "string", "description": "Patch content to apply"}
                },
                "required": ["patch"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_commands",
            "description": "List available custom commands.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
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
                    "args": {"type": "object", "description": "Arguments to pass to the command"}
                },
                "required": ["name"]
            }
        }
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
                    "column": {"type": "integer", "description": "Column number"}
                },
                "required": ["path"]
            }
        }
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
                    "column": {"type": "integer", "description": "Column number"}
                },
                "required": ["path"]
            }
        }
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
                    "column": {"type": "integer", "description": "Column number"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lsp_diagnostics",
            "description": "Get diagnostic errors using LSP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "plan_approve",
            "description": "Approve the pending plan to proceed with execution.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "plan_reject",
            "description": "Reject the pending plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Reason for rejection"}
                },
                "required": ["reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_repo_map",
            "description": "Get a comprehensive map of the repository structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "depth": {"type": "integer", "description": "Depth of directory traversal"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "init_project",
            "description": "Analyze and initialize the project with AGENTS.md.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_project",
            "description": "Get detailed project analysis (language, deps, test framework).",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
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
                "required": ["path"]
            }
        }
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
                "required": ["action_id"]
            }
        }
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
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run command in persistent shell session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to run"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_shell",
            "description": "Close the persistent shell session.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "select_files",
            "description": "Select multiple files for context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patterns": {"type": "array", "items": {"type": "string"}, "description": "Glob patterns"}
                },
                "required": ["patterns"]
            }
        }
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
                    "checkout": {"type": "boolean", "description": "Switch to new branch"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_switch_branch",
            "description": "Switch to an existing git branch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Branch name"}
                },
                "required": ["name"]
            }
        }
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
                    "force": {"type": "boolean", "description": "Force delete"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_list_branches",
            "description": "List all git branches.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
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
                    "base": {"type": "string", "description": "Target branch"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_completions",
            "description": "Get auto-completions for files or commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["file", "command", "agent", "model"], "description": "Completion type"},
                    "prefix": {"type": "string", "description": "Prefix to match"}
                },
                "required": ["type", "prefix"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_image_data",
            "description": "Read and encode image for vision analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to image file"}
                },
                "required": ["path"]
            }
        }
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
                    "replace": {"type": "integer", "description": "Number of lines to replace"}
                },
                "required": ["path", "line", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "retry_last",
            "description": "Retry the last failed tool execution.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_stage",
            "description": "Stage files for commit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Files to stage"}
                },
                "required": ["files"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_unstage",
            "description": "Unstage files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Files to unstage"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Commit staged changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"}
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "List available skills.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
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
                    "args": {"type": "object", "description": "Skill arguments"}
                },
                "required": ["name"]
            }
        }
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
                    "files": {"type": "array", "items": {"type": "string"}, "description": "File patterns"},
                    "dry_run": {"type": "boolean", "description": "Preview without applying"}
                },
                "required": ["pattern", "replacement", "files"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_code",
            "description": "Analyze code structure and complexity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File to analyze"}
                },
                "required": ["path"]
            }
        }
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
                    "end": {"type": "integer", "description": "End line"}
                },
                "required": ["path"]
            }
        }
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
                    "framework": {"type": "string", "description": "Test framework (pytest/jest)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_pre_commit",
            "description": "Run git pre-commit checks.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_keybindings",
            "description": "Show keyboard shortcuts.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_theme",
            "description": "Set terminal theme.",
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "description": "Theme name"}
                },
                "required": ["theme"]
            }
        }
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
                    "command": {"type": "string", "description": "Command to run"}
                },
                "required": ["hook", "command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "batch_read",
            "description": "Read multiple files at once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paths": {"type": "array", "items": {"type": "string"}, "description": "File paths to read"}
                },
                "required": ["paths"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "batch_write",
            "description": "Write multiple files at once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operations": {"type": "array", "items": {"type": "object"}, "description": "Write operations"}
                },
                "required": ["operations"]
            }
        }
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
                    "retries": {"type": "integer", "description": "Number of retries"}
                },
                "required": ["tool", "args"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tool_timeout",
            "description": "Get timeout for a specific tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "Tool name"}
                },
                "required": ["tool"]
            }
        }
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
                    "timeout": {"type": "integer", "description": "Timeout in seconds"}
                },
                "required": ["tool", "timeout"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear_file_cache",
            "description": "Clear the file operation cache.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_context_info",
            "description": "Get context optimization info.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_file_watch",
            "description": "Start watching files for changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patterns": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop_file_watch",
            "description": "Stop file watcher.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
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
                    "vars": {"type": "object", "description": "Additional variables"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_env",
            "description": "Get environment variable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Variable name"}
                },
                "required": ["key"]
            }
        }
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
                    "value": {"type": "string", "description": "Variable value"}
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_env",
            "description": "List environment variables.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
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
                    "command": {"type": "string", "description": "Command to run"}
                },
                "required": ["name", "command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List all tasks.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_task",
            "description": "Get task status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"}
                },
                "required": ["task_id"]
            }
        }
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
                    "fuzzy": {"type": "boolean", "description": "Use fuzzy matching"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_workspace",
            "description": "Validate workspace configuration.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
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
                }
            }
        }
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
                    "style": {"type": "string", "description": "Style: async, type_hints, modern"}
                },
                "required": ["path", "function"]
            }
        }
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
                    "columns": {"type": "array", "items": {"type": "object"}, "description": "Column definitions"}
                },
                "required": ["table", "columns"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_dockerfile",
            "description": "Generate Dockerfile for language.",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {"type": "string", "description": "Language: python, node, go, rust, java"}
                },
                "required": ["language"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_docker_compose",
            "description": "Generate docker-compose.yml.",
            "parameters": {
                "type": "object",
                "properties": {
                    "services": {"type": "array", "items": {"type": "object"}, "description": "Service definitions"}
                },
                "required": ["services"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_api_client",
            "description": "Generate API client from OpenAPI spec.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spec": {"type": "string", "description": "Path to OpenAPI spec"}
                },
                "required": ["spec"]
            }
        }
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
                    "path": {"type": "string", "description": "File path for api docs"}
                },
                "required": ["type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "profile_code",
            "description": "Profile code complexity and performance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File to profile"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_code",
            "description": "Get optimization suggestions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File to analyze"}
                },
                "required": ["path"]
            }
        }
    }
]


class ToolExecutor:
    def __init__(self, cwd: Path | None = None):
        self.cwd = cwd or Path.cwd()

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p.resolve()
        return (self.cwd / p).resolve()

    def execute(self, tool_name: str, args: dict[str, Any]) -> str:
        method = getattr(self, f"_execute_{tool_name}", None)
        if not method:
            return f"ERROR: Unknown tool '{tool_name}'"
        try:
            return method(args)
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"

    def _execute_read_file(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: File not found: {path}"
        try:
            lines = path.read_text().splitlines()
            max_line_num = len(str(len(lines)))
            result = []
            for i, line in enumerate(lines, 1):
                result.append(f"{i:>{max_line_num}}  {line}")
            return "\n".join(result)
        except Exception as e:
            return f"ERROR: Cannot read file: {e}"

    def _execute_write_file(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args["content"])
            return f"SUCCESS: Written {len(args['content'])} bytes to {path}"
        except Exception as e:
            return f"ERROR: Cannot write file: {e}"

    def _execute_edit_file(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: File not found: {path}"
        try:
            content = path.read_text()
            old_string = args["old_string"]
            new_string = args["new_string"]
            if old_string not in content:
                return f"ERROR: String not found in file. Use read_file to see content."
            new_content = content.replace(old_string, new_string, 1)
            path.write_text(new_content)
            return f"SUCCESS: Edited {path}"
        except Exception as e:
            return f"ERROR: Cannot edit file: {e}"

    def _execute_run_command(self, args: dict[str, Any]) -> str:
        command = args["command"]
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=300
            )
            output = []
            if result.stdout:
                output.append(result.stdout)
            if result.stderr:
                output.append(f"[STDERR]\n{result.stderr}")
            if result.returncode != 0:
                output.insert(0, f"[EXIT CODE: {result.returncode}]\n")
            return "\n".join(output) if output else "[no output]"
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out after 300 seconds"
        except Exception as e:
            return f"ERROR: Cannot run command: {e}"

    def _execute_list_files(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: Directory not found: {path}"
        if not path.is_dir():
            return f"ERROR: Not a directory: {path}"
        try:
            entries = []
            for entry in sorted(path.iterdir()):
                try:
                    size = entry.stat().st_size
                    size_str = f"{size:>10}" if entry.is_file() else "<DIR>    "
                except:
                    size_str = "?          "
                entries.append(f"{size_str}  {entry.name}")
            return "\n".join(entries) if entries else "[empty directory]"
        except Exception as e:
            return f"ERROR: Cannot list directory: {e}"

    def _execute_search_in_files(self, args: dict[str, Any]) -> str:
        pattern = args["pattern"]
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: Path not found: {path}"
        try:
            regex = re.compile(pattern)
            results = []
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    try:
                        lines = file_path.read_text().splitlines()
                        for i, line in enumerate(lines, 1):
                            if regex.search(line):
                                results.append(f"{file_path}:{i}: {line.rstrip()}")
                    except:
                        pass
            return "\n".join(results) if results else "[no matches found]"
        except re.error as e:
            return f"ERROR: Invalid regex: {e}"
        except Exception as e:
            return f"ERROR: Search failed: {e}"

    def _execute_delete_file(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: Path not found: {path}"
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                if any(path.iterdir()):
                    return f"ERROR: Directory not empty: {path}"
                path.rmdir()
            return f"SUCCESS: Deleted {path}"
        except Exception as e:
            return f"ERROR: Cannot delete: {e}"

    def _execute_create_directory(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        try:
            path.mkdir(parents=True, exist_ok=True)
            return f"SUCCESS: Created directory {path}"
        except Exception as e:
            return f"ERROR: Cannot create directory: {e}"

    def _execute_glob_search(self, args: dict[str, Any]) -> str:
        pattern = args.get("pattern", "**/*")
        directory = self._resolve(args.get("directory", "."))
        if not directory.exists():
            return f"ERROR: Directory not found: {directory}"
        try:
            matches = list(directory.glob(pattern))
            if not matches:
                return f"[no files match pattern '{pattern}']"
            results = []
            for m in matches:
                rel = m.relative_to(directory.parent) if directory.parent != m.parent else m.name
                results.append(str(rel))
            return "\n".join(sorted(results))
        except Exception as e:
            return f"ERROR: Glob search failed: {e}"

    def _execute_get_file_tree(self, args: dict[str, Any]) -> str:
        path = self._resolve(args.get("path", "."))
        max_depth = args.get("max_depth", 3)
        if not path.exists():
            return f"ERROR: Path not found: {path}"

        lines = [f"{path.name}/" if path.is_dir() else path.name]

        def walk(dir_path: Path, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return []
            try:
                entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                return [f"{prefix}[permission denied]"]

            result = []
            for i, entry in enumerate(entries):
                if entry.name.startswith("."):
                    continue
                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "
                result.append(f"{prefix}{connector}{entry.name}")
                if entry.is_dir():
                    extension = "    " if is_last else "│   "
                    result.extend(walk(entry, prefix + extension, depth + 1))
            return result

        if path.is_dir():
            lines.extend(walk(path))
        return "\n".join(lines)

    def _execute_diff_files(self, args: dict[str, Any]) -> str:
        path_a = self._resolve(args["path_a"])
        path_b = self._resolve(args["path_b"])
        if not path_a.exists():
            return f"ERROR: File not found: {path_a}"
        if not path_b.exists():
            return f"ERROR: File not found: {path_b}"
        try:
            with open(path_a) as f:
                lines_a = f.read().splitlines()
            with open(path_b) as f:
                lines_b = f.read().splitlines()

            import difflib
            diff = list(difflib.unified_diff(lines_b, lines_a, fromfile=str(path_b), tofile=str(path_a), lineterm=""))
            return "\n".join(diff) if diff else "[files are identical]"
        except Exception as e:
            return f"ERROR: Cannot diff files: {e}"

    def _execute_get_git_status(self, args: dict[str, Any]) -> str:
        if not (self.cwd / ".git").exists():
            return "ERROR: Not a git repository"
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.cwd,
                capture_output=True,
                text=True
            )
            if not result.stdout.strip():
                return "[working tree clean]"
            return result.stdout
        except Exception as e:
            return f"ERROR: Git status failed: {e}"

    def _execute_get_git_log(self, args: dict[str, Any]) -> str:
        n = args.get("n", 10)
        if not (self.cwd / ".git").exists():
            return "ERROR: Not a git repository"
        try:
            result = subprocess.run(
                ["git", "log", f"-{n}", "--oneline", "--decorate"],
                cwd=self.cwd,
                capture_output=True,
                text=True
            )
            return result.stdout or "[no commits]"
        except Exception as e:
            return f"ERROR: Git log failed: {e}"

    def _execute_git_diff(self, args: dict[str, Any]) -> str:
        ref = args.get("ref")
        if not (self.cwd / ".git").exists():
            return "ERROR: Not a git repository"
        try:
            cmd = ["git", "diff"]
            if ref:
                cmd.append(ref)
            result = subprocess.run(cmd, cwd=self.cwd, capture_output=True, text=True)
            return result.stdout or "[no changes]"
        except Exception as e:
            return f"ERROR: Git diff failed: {e}"

    def _execute_web_search(self, args: dict[str, Any]) -> str:
        query = args["query"]
        try:
            import urllib.parse
            url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            result = subprocess.run(
                ["curl", "-s", "-L", url],
                capture_output=True,
                text=True,
                timeout=30
            )
            html = result.stdout

            import re
            titles = re.findall(r'<a class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)', html)
            snippets = re.findall(r'<a class="result__snippet"[^>]*>([^<]*)', html)

            output = []
            for i, (link, title) in enumerate(titles[:5]):
                snippet = snippets[i] if i < len(snippets) else ""
                output.append(f"{i+1}. {title.strip()}\n   {snippet.strip()}\n   {link}")
            return "\n\n".join(output) if output else "[no results]"
        except Exception as e:
            return f"ERROR: Web search failed: {e}"

    def _execute_fetch_url(self, args: dict[str, Any]) -> str:
        url = args["url"]
        try:
            result = subprocess.run(
                ["curl", "-s", "-L", url],
                capture_output=True,
                text=True,
                timeout=30
            )
            html = result.stdout

            import re
            scripts = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            styles = re.sub(r'<style[^>]*>.*?</style>', '', scripts, flags=re.DOTALL)
            cleaned = re.sub(r'<[^>]+>', '', styles)
            cleaned = re.sub(r'\s+', ' ', cleaned)
            cleaned = re.sub(r'&[a-z]+;', '', cleaned)
            cleaned = cleaned.strip()

            return cleaned[:3000] + ("..." if len(cleaned) > 3000 else "")
        except Exception as e:
            return f"ERROR: Fetch failed: {e}"

    def _execute_get_repo_map(self, args: dict[str, Any]) -> str:
        path = self._resolve(args.get("path", "."))
        if not path.exists():
            return f"ERROR: Path does not exist: {path}"

        def categorize_files(dir_path: Path) -> dict[str, list[str]]:
            categories = {"source": [], "config": [], "docs": [], "data": [], "other": []}
            try:
                for entry in dir_path.iterdir():
                    if entry.name.startswith(".") or entry.name in ("node_modules", "__pycache__", "venv", ".git", "target"):
                        continue
                    ext = entry.suffix.lower()
                    if ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".cpp", ".c", ".h"):
                        categories["source"].append(entry.name)
                    elif ext in (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"):
                        categories["config"].append(entry.name)
                    elif ext in (".md", ".txt", ".rst"):
                        categories["docs"].append(entry.name)
                    elif ext in (".db", ".sqlite", ".csv", ".jsonl"):
                        categories["data"].append(entry.name)
                    elif entry.is_dir():
                        categories["source"].append(f"{entry.name}/")
                    else:
                        categories["other"].append(entry.name)
            except PermissionError:
                pass
            return categories

        lines = [f"Repository: {path.name}", "=" * 50]
        cats = categorize_files(path)

        for cat_name, files in cats.items():
            if files:
                lines.append(f"\n[{cat_name.upper()}]")
                for f in sorted(files)[:15]:
                    lines.append(f"  • {f}")

        git_dir = path / ".git"
        if git_dir.exists():
            try:
                head = (git_dir / "HEAD").read_text().strip()
                if head.startswith("ref: "):
                    head = head[5:]
                lines.append(f"\n[GIT] Branch: {head}")
            except:
                pass

        return "\n".join(lines)

    def _execute_read_image(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: Image not found: {path}"
        try:
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/{path.suffix[1:]};base64,{data}"
        except Exception as e:
            return f"ERROR: Cannot read image: {e}"

    def _execute_run_test(self, args: dict[str, Any]) -> str:
        framework = args["framework"]
        path = args.get("path", ".")

        commands = {
            "pytest": ["pytest", "-v", path],
            "jest": ["npx", "jest", path],
            "cargo": ["cargo", "test", "--", "--test-threads=1"],
            "npm": ["npm", "test", "--", path],
        }

        if framework not in commands:
            return f"ERROR: Unknown framework: {framework}. Use pytest, jest, or cargo."

        try:
            result = subprocess.run(
                commands[framework],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=300
            )
            output = []
            if result.stdout:
                output.append(result.stdout)
            if result.stderr:
                output.append(result.stderr)
            return "\n".join(output) if output else "[no output]"
        except subprocess.TimeoutExpired:
            return "ERROR: Tests timed out after 300 seconds"
        except FileNotFoundError:
            return f"ERROR: {framework} not found. Install it first."
        except Exception as e:
            return f"ERROR: Test execution failed: {e}"

    def _execute_format_file(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: File not found: {path}"

        ext = path.suffix.lower()
        commands = {
            ".py": ["black", "-"],
            ".js": ["prettier", "--write", str(path)],
            ".ts": ["prettier", "--write", str(path)],
            ".jsx": ["prettier", "--write", str(path)],
            ".tsx": ["prettier", "--write", str(path)],
            ".rs": ["rustfmt", str(path)],
            ".go": ["gofmt", "-w", str(path)],
        }

        if ext not in commands:
            return f"ERROR: No formatter available for {ext}"

        try:
            if ext == ".py":
                result = subprocess.run(
                    ["black", "-"],
                    cwd=self.cwd,
                    input=path.read_text(),
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return f"SUCCESS: Formatted {path}"
                return f"ERROR: {result.stderr}"
            else:
                result = subprocess.run(commands[ext], cwd=self.cwd, capture_output=True, text=True)
                if result.returncode == 0:
                    return f"SUCCESS: Formatted {path}"
                return f"ERROR: {result.stderr}"
        except FileNotFoundError:
            return f"ERROR: Formatter not found. Install it first."
        except Exception as e:
            return f"ERROR: Formatting failed: {e}"

    def _execute_install_package(self, args: dict[str, Any]) -> str:
        manager = args["manager"]
        package = args["package"]

        commands = {
            "pip": ["pip", "install", package],
            "npm": ["npm", "install", package],
            "yarn": ["yarn", "add", package],
            "cargo": ["cargo", "install", package],
        }

        if manager not in commands:
            return f"ERROR: Unknown package manager: {manager}"

        try:
            result = subprocess.run(
                commands[manager],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                return f"SUCCESS: Installed {package} via {manager}"
            return f"ERROR: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "ERROR: Installation timed out"
        except FileNotFoundError:
            return f"ERROR: {manager} not found"
        except Exception as e:
            return f"ERROR: Installation failed: {e}"

    def _execute_task(self, args: dict[str, Any]) -> str:
        agent_name = args["agent"]
        task = args["task"]
        from .agents import agent_manager
        if agent_name not in agent_manager.agents:
            return f"ERROR: Unknown agent: {agent_name}"
        return f"[Delegated to @{agent_name}]: {task}"

    def _execute_preview_edit(self, args: dict[str, Any]) -> str:
        import uuid
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: File not found: {path}"

        try:
            content = path.read_text()
            old_string = args["old_string"]
            new_string = args["new_string"]

            if old_string not in content:
                return f"ERROR: String not found in file"

            import difflib
            old_lines = content.splitlines(keepends=True)
            new_lines = content.replace(old_string, new_string, 1).splitlines(keepends=True)

            diff = list(difflib.unified_diff(old_lines, new_lines, fromfile=str(path), tofile=f"{path} (modified)", lineterm=""))
            diff_text = "".join(diff)

            preview_id = str(uuid.uuid4())[:8]
            self._preview_cache = getattr(self, "_preview_cache", {})
            self._preview_cache[preview_id] = {
                "path": str(path),
                "old_string": old_string,
                "new_string": new_string
            }

            return f"[PREVIEW {preview_id}]\n{diff_text}\n\nUse apply_edit with preview_id={preview_id} to confirm, or the edit will be discarded."
        except Exception as e:
            return f"ERROR: Preview failed: {e}"

    def _execute_apply_edit(self, args: dict[str, Any]) -> str:
        preview_id = args["preview_id"]
        cache = getattr(self, "_preview_cache", {})

        if preview_id not in cache:
            return f"ERROR: Invalid or expired preview ID: {preview_id}"

        preview = cache.pop(preview_id)
        path = Path(preview["path"])

        try:
            content = path.read_text()
            if preview["old_string"] not in content:
                return "ERROR: File content changed since preview"
            new_content = content.replace(preview["old_string"], preview["new_string"], 1)
            path.write_text(new_content)
            return f"SUCCESS: Applied edit to {path}"
        except Exception as e:
            return f"ERROR: Apply failed: {e}"

    def _execute_clipboard_read(self, args: dict[str, Any]) -> str:
        try:
            import pyperclip
            return pyperclip.paste()
        except ImportError:
            try:
                result = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout
            except:
                pass
            return "ERROR: No clipboard tool available. Install pyperclip or xclip."
        except Exception as e:
            return f"ERROR: Cannot read clipboard: {e}"

    def _execute_clipboard_write(self, args: dict[str, Any]) -> str:
        text = args["text"]
        try:
            import pyperclip
            pyperclip.copy(text)
            return f"SUCCESS: Copied {len(text)} chars to clipboard"
        except ImportError:
            try:
                subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, capture_output=True)
                return f"SUCCESS: Copied {len(text)} chars to clipboard"
            except:
                pass
            return "ERROR: No clipboard tool available. Install pyperclip or xclip."
        except Exception as e:
            return f"ERROR: Cannot write to clipboard: {e}"

    def _execute_ask_user(self, args: dict[str, Any]) -> str:
        question = args["question"]
        options = args.get("options", [])
        return f"[WAITING FOR USER INPUT]\nQuestion: {question}\nOptions: {options if options else 'Free text answer'}\n\nUse /answer <response> to reply."

    def _execute_run_code(self, args: dict[str, Any]) -> str:
        code = args["code"]
        language = args.get("language", "python")
        cmd_args = args.get("args", [])

        from .sandbox import sandbox
        return sandbox.run_code(code, language, cmd_args)

    def _execute_bookmark_session(self, args: dict[str, Any]) -> str:
        from .context_manager import ConversationManager
        name = args["name"]
        conv_manager = getattr(self, "_conv_manager", None)
        if conv_manager is None:
            conv_manager = ConversationManager()
            self._conv_manager = conv_manager

        conv_manager.bookmark(name)
        return f"SUCCESS: Bookmarked current position as '{name}'"

    def _execute_restore_bookmark(self, args: dict[str, Any]) -> str:
        from .context_manager import ConversationManager
        name = args["name"]
        conv_manager = getattr(self, "_conv_manager", None)
        if conv_manager is None:
            return "ERROR: No bookmarks exist"

        restored = conv_manager.restore_bookmark(name)
        if restored is None:
            return f"ERROR: Bookmark '{name}' not found"
        return f"[RESTORED from bookmark '{name}']\nMessages: {len(restored)}"

    def _execute_search_history(self, args: dict[str, Any]) -> str:
        from .context_manager import ConversationManager
        query = args["query"]
        conv_manager = getattr(self, "_conv_manager", None)
        if conv_manager is None:
            return "ERROR: No conversation history"

        results = conv_manager.search(query)
        if not results:
            return f"No results found for: {query}"

        output = [f"Found {len(results)} matching messages:"]
        for r in results[:10]:
            msg = r["message"]
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]
            output.append(f"  [{role}] #{r['index']}: {content}...")

        return "\n".join(output)

    def _execute_get_conversation_stats(self, args: dict[str, Any]) -> str:
        from .context_manager import ConversationManager
        conv_manager = getattr(self, "_conv_manager", None)
        if conv_manager is None:
            return "No conversation statistics available"

        stats = conv_manager.get_stats()
        return f"Conversation stats:\n  Messages: {stats['message_count']}\n  Bookmarks: {stats['bookmarks']}\n  Roles: {stats['roles']}"

    def _execute_undo(self, args: dict[str, Any]) -> str:
        undo_manager = getattr(self, "_undo_manager", None)
        if undo_manager is None:
            return "ERROR: Undo manager not available"
        action = undo_manager.undo()
        if action is None:
            return "Nothing to undo"
        return f"UNDONE: {action.get('type', 'action')}\n{action.get('details', {})}"
    
    def _execute_redo(self, args: dict[str, Any]) -> str:
        undo_manager = getattr(self, "_undo_manager", None)
        if undo_manager is None:
            return "ERROR: Undo manager not available"
        action = undo_manager.redo()
        if action is None:
            return "Nothing to redo"
        return "REDONE: {action.get('type', 'action')}\n{action.get('details', {})}"

    def _execute_undo_info(self, args: dict[str, Any]) -> str:
        undo_manager = getattr(self, "_undo_manager", None)
        if undo_manager is None:
            return "Undo: Not available"
        can_undo = undo_manager.can_undo()
        desc = undo_manager.get_undo_description()
        return f"Can undo: {can_undo}\nLast action: {desc}"

    def _execute_redo_info(self, args: dict[str, Any]) -> str:
        undo_manager = getattr(self, "_undo_manager", None)
        if undo_manager is None:
            return "Redo: Not available"
        can_redo = undo_manager.can_redo()
        desc = undo_manager.get_redo_description()
        return f"Can redo: {can_redo}\nNext action: {desc}"

    def _execute_share_session(self, args: dict[str, Any]) -> str:
        from .session import SessionManager
        agent = getattr(self, "_agent", None)
        if agent is None:
            return "ERROR: Session sharing not available in this context"
        session_manager = SessionManager()
        share_link = session_manager.share(agent)
        return f"Session shared: {share_link}\nShare this link with others to collaborate."

    def _execute_apply_patch(self, args: dict[str, Any]) -> str:
        patch = args["patch"]
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
                f.write(patch)
                patch_file = f.name
            result = subprocess.run(
                ["patch", "-p1", "-i", patch_file],
                cwd=self.cwd,
                capture_output=True,
                text=True
            )
            os.unlink(patch_file)
            if result.returncode == 0:
                return f"SUCCESS: Patch applied\n{result.stdout}"
            else:
                return f"ERROR: Patch failed\n{result.stderr}"
        except FileNotFoundError:
            return "ERROR: patch command not found. Install it with: apt-get install patch"
        except Exception as e:
            return f"ERROR: Cannot apply patch: {e}"

    def _execute_list_commands(self, args: dict[str, Any]) -> str:
        from .commands import get_command_manager
        cm = get_command_manager(str(self.cwd))
        commands = cm.list_commands()
        if not commands:
            return "No custom commands available. Create .apex/commands/*.md files."
        output = ["Available commands:"]
        for cmd in commands:
            output.append(f"  /{cmd['name']} - {cmd['description']}")
        return "\n".join(output)

    def _execute_run_command_custom(self, args: dict[str, Any]) -> str:
        from .commands import get_command_manager
        name = args["name"]
        cmd_args = args.get("args", {})
        cm = get_command_manager(str(self.cwd))
        result = cm.execute(name, **cmd_args)
        if result is None:
            return f"ERROR: Command '{name}' not found"
        return f"[COMMAND: {name}]\n{result}"

    def _execute_lsp_definition(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        line = args.get("line", 0)
        column = args.get("column", 0)
        from .lsp import get_lsp_manager
        lsp = get_lsp_manager(str(self.cwd))
        result = lsp.call_tool("lsp_default_definition", {"path": str(path), "line": line, "column": column})
        return json.dumps(result)

    def _execute_lsp_references(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        line = args.get("line", 0)
        column = args.get("column", 0)
        from .lsp import get_lsp_manager
        lsp = get_lsp_manager(str(self.cwd))
        result = lsp.call_tool("lsp_default_references", {"path": str(path), "line": line, "column": column})
        return json.dumps(result)

    def _execute_lsp_hover(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        line = args.get("line", 0)
        column = args.get("column", 0)
        from .lsp import get_lsp_manager
        lsp = get_lsp_manager(str(self.cwd))
        result = lsp.call_tool("lsp_default_hover", {"path": str(path), "line": line, "column": column})
        return json.dumps(result)

    def _execute_lsp_diagnostics(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        from .lsp import get_lsp_manager
        lsp = get_lsp_manager(str(self.cwd))
        result = lsp.call_tool("lsp_default_diagnostics", {"path": str(path)})
        return json.dumps(result)

    def _execute_plan_approve(self, args: dict[str, Any]) -> str:
        from .commands import PlanApproval
        plan_approval = getattr(self, "_plan_approval", None)
        if plan_approval is None:
            return "ERROR: No pending plan to approve"
        plan_approval.approve()
        return "APPROVED: Plan has been approved. Proceeding with execution..."

    def _execute_plan_reject(self, args: dict[str, Any]) -> str:
        from .commands import PlanApproval
        plan_approval = getattr(self, "_plan_approval", None)
        if plan_approval is None:
            return "ERROR: No pending plan to reject"
        reason = args.get("reason", "No reason provided")
        plan_approval.reject()
        return f"REJECTED: Plan rejected. Reason: {reason}"

    def _execute_get_repo_map(self, args: dict[str, Any]) -> str:
        from .context import get_repo_map
        from pathlib import Path
        return get_repo_map(Path(self.cwd))

    def _execute_init_project(self, args: dict[str, Any]) -> str:
        from .project import get_project_initializer
        pi = get_project_initializer(str(self.cwd))
        try:
            output_path = pi.create_context_file()
            return f"SUCCESS: Project initialized\nCreated: {output_path}\n\nRun /map to see project context."
        except Exception as e:
            return f"ERROR: Failed to initialize project: {e}"

    def _execute_analyze_project(self, args: dict[str, Any]) -> str:
        from .project import get_project_initializer
        pi = get_project_initializer(str(self.cwd))
        analysis = pi.analyze()
        lines = ["Project Analysis", "=" * 40]
        lines.append(f"Language: {analysis.get('language', 'unknown')}")
        lines.append(f"Package Manager: {analysis.get('package_manager', 'unknown')}")
        lines.append(f"Test Framework: {analysis.get('test_framework', 'unknown')}")
        lines.append(f"LSP Server: {analysis.get('lsp_server', 'not configured')}")
        lines.append(f"Build System: {analysis.get('build_system', 'unknown')}")
        lines.append(f"Formatters: {', '.join(analysis.get('formatters', []))}")
        lines.append("")
        lines.append(f"Scripts: {len(analysis.get('scripts', {}))}")
        lines.append(f"Dependencies: {len(analysis.get('dependencies', []))}")
        lines.append(f"Dev Dependencies: {len(analysis.get('dev_dependencies', []))}")
        return "\n".join(lines)

    def _execute_get_code_actions(self, args: dict[str, Any]) -> str:
        from .lsp import get_lsp_manager
        path = self._resolve(args["path"])
        lsp = get_lsp_manager(str(self.cwd))
        result = lsp.call_tool("lsp_default_diagnostics", {"path": str(path)})
        if not result.get("diagnostics"):
            return "No diagnostic issues found."
        
        actions = []
        for diag in result.get("diagnostics", [])[:10]:
            actions.append(f"- {diag.get('message', 'Unknown issue')}")
        
        return "Available code actions:\n" + "\n".join(actions)

    def _execute_apply_code_action(self, args: dict[str, Any]) -> str:
        action_id = args["action_id"]
        return f"Applying code action: {action_id}\n\n(Note: LSP code actions require full LSP integration)"

    def _execute_start_shell(self, args: dict[str, Any]) -> str:
        shell = args.get("shell", "bash")
        from .sandbox import ShellSession
        if not hasattr(self, "_shell_session"):
            self._shell_session = ShellSession(cwd=str(self.cwd))
        
        if self._shell_session.start(shell=shell):
            return f"SUCCESS: {shell} shell session started\n\nUse run_shell to execute commands."
        return "ERROR: Failed to start shell session"

    def _execute_run_shell(self, args: dict[str, Any]) -> str:
        command = args["command"]
        if not hasattr(self, "_shell_session"):
            return "ERROR: No shell session. Use start_shell first."
        
        try:
            return self._shell_session.run(command)
        except Exception as e:
            return f"ERROR: {e}"

    def _execute_close_shell(self, args: dict[str, Any]) -> str:
        if hasattr(self, "_shell_session"):
            self._shell_session.close()
            del self._shell_session
            return "SUCCESS: Shell session closed"
        return "ERROR: No shell session to close"

    def _execute_select_files(self, args: dict[str, Any]) -> str:
        patterns = args.get("patterns", [])
        if not patterns:
            return "ERROR: No patterns provided"
        
        from pathlib import Path
        files = []
        for pattern in patterns:
            for p in Path(self.cwd).rglob(pattern):
                if p.is_file():
                    files.append(str(p.relative_to(self.cwd)))
        
        if not files:
            return f"No files found matching: {patterns}"
        
        return f"Selected {len(files)} files:\n" + "\n".join(files[:20])

    def _execute_git_create_branch(self, args: dict[str, Any]) -> str:
        name = args["name"]
        checkout = args.get("checkout", False)
        try:
            cmd = ["git", "branch", name]
            subprocess.run(cmd, cwd=self.cwd, capture_output=True)
            if checkout:
                subprocess.run(["git", "checkout", name], cwd=self.cwd, capture_output=True)
            return f"SUCCESS: Created branch '{name}'" + (" and checked out" if checkout else "")
        except Exception as e:
            return f"ERROR: {e}"

    def _execute_git_switch_branch(self, args: dict[str, Any]) -> str:
        name = args["name"]
        try:
            subprocess.run(["git", "checkout", name], cwd=self.cwd, capture_output=True)
            return f"SUCCESS: Switched to branch '{name}'"
        except Exception as e:
            return f"ERROR: {e}"

    def _execute_git_delete_branch(self, args: dict[str, Any]) -> str:
        name = args["name"]
        force = args.get("force", False)
        try:
            cmd = ["git", "branch", "-D" if force else "-d", name]
            subprocess.run(cmd, cwd=self.cwd, capture_output=True)
            return f"SUCCESS: Deleted branch '{name}'"
        except Exception as e:
            return f"ERROR: {e}"

    def _execute_git_list_branches(self, args: dict[str, Any]) -> str:
        try:
            result = subprocess.run(["git", "branch", "-a"], cwd=self.cwd, capture_output=True, text=True)
            return f"Branches:\n{result.stdout}"
        except Exception as e:
            return f"ERROR: {e}"

    def _execute_git_create_pr(self, args: dict[str, Any]) -> str:
        title = args.get("title", "")
        body = args.get("body", "")
        base = args.get("base", "main")
        return f"Creating PR: {title}\nBase: {base}\n\n(Note: Use gh CLI or GitHub API for actual PR creation)"

    def _execute_get_completions(self, args: dict[str, Any]) -> str:
        ctype = args.get("type", "file")
        prefix = args.get("prefix", "")
        
        if ctype == "file":
            from .mentions import get_file_completer
            fc = get_file_completer(str(self.cwd))
            results = fc.complete(prefix)
            return "Completions:\n" + "\n".join(results) if results else "No matches"
        elif ctype == "command":
            from .slash import get_slash_command_manager
            cm = get_slash_command_manager()
            commands = cm.list_commands()
            matches = [c["name"] for c in commands if c["name"].startswith(prefix)]
            return "Commands:\n" + "\n".join(matches) if matches else "No matches"
        elif ctype == "agent":
            return "Agents: build, plan\nSubagents: explore, general"
        elif ctype == "model":
            return "Use --model flag or /model command"
        return "Unknown completion type"

    def _execute_read_image_data(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: File not found: {path}"
        try:
            import base64
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            return f"[IMAGE DATA] {path.name} ({len(data)} bytes base64)"
        except Exception as e:
            return f"ERROR: {e}"

    def _execute_inline_edit(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        line = args.get("line", 1)
        content = args.get("content", "")
        replace = args.get("replace", 1)
        
        if not path.exists():
            return f"ERROR: File not found: {path}"
        
        try:
            lines = path.read_text().splitlines()
            start = max(0, line - 1)
            end = min(len(lines), start + replace)
            new_lines = lines[:start] + [content] + lines[end:]
            path.write_text("\n".join(new_lines))
            return f"SUCCESS: Edited {path} at line {line}"
        except Exception as e:
            return f"ERROR: {e}"

    def _execute_retry_last(self, args: dict[str, Any]) -> str:
        last_tool = getattr(self, "_last_tool", None)
        last_args = getattr(self, "_last_args", None)
        
        if not last_tool or not last_args:
            return "ERROR: No previous tool to retry"
        
        return self.execute(last_tool, last_args)

    def _execute_git_stage(self, args: dict[str, Any]) -> str:
        files = args.get("files", [])
        if not files:
            return "ERROR: No files specified"
        
        try:
            subprocess.run(["git", "add"] + files, cwd=self.cwd, capture_output=True)
            return f"SUCCESS: Staged {len(files)} file(s)"
        except Exception as e:
            return f"ERROR: {e}"

    def _execute_git_unstage(self, args: dict[str, Any]) -> str:
        files = args.get("files", [])
        try:
            if files:
                subprocess.run(["git", "reset"] + files, cwd=self.cwd, capture_output=True)
            else:
                subprocess.run(["git", "reset", "HEAD"], cwd=self.cwd, capture_output=True)
            return "SUCCESS: Unstaged files"
        except Exception as e:
            return f"ERROR: {e}"

    def _execute_git_commit(self, args: dict[str, Any]) -> str:
        message = args.get("message", "")
        if not message:
            return "ERROR: No commit message"
        
        try:
            result = subprocess.run(["git", "commit", "-m", message], cwd=self.cwd, capture_output=True, text=True)
            if result.returncode == 0:
                return f"SUCCESS: Committed\n{result.stdout}"
            return f"ERROR: {result.stderr}"
        except Exception as e:
            return f"ERROR: {e}"

    def _execute_list_skills(self, args: dict[str, Any]) -> str:
        from .skills import get_skill_manager
        sm = get_skill_manager(str(self.cwd))
        skills = sm.list_skills()
        if not skills:
            return "No skills available. Create .apex/skills/*.md files."
        output = ["Available skills:"]
        for s in skills:
            output.append(f"  {s['name']} - {s['description']}")
        return "\n".join(output)

    def _execute_use_skill(self, args: dict[str, Any]) -> str:
        from .skills import get_skill_manager
        name = args["name"]
        skill_args = args.get("args", {})
        sm = get_skill_manager(str(self.cwd))
        result = sm.render(name, **skill_args)
        if result is None:
            return f"ERROR: Skill '{name}' not found"
        return f"[SKILL: {name}]\n{result}"

    def _execute_replace_in_files(self, args: dict[str, Any]) -> str:
        from .skills import SearchReplace
        pattern = args["pattern"]
        replacement = args["replacement"]
        files = args.get("files", [])
        dry_run = args.get("dry_run", True)
        sr = SearchReplace(str(self.cwd))
        result = sr.replace_in_files(pattern, replacement, files, dry_run)
        
        if "error" in result:
            return result["error"]
        
        output = f"Found {result['replacements']} replacements in {len(result['files_modified'])} files"
        if dry_run:
            output += " (DRY RUN - use dry_run: false to apply)"
        output += "\n\nFiles:\n" + "\n".join(result["files_modified"][:10])
        return output

    def _execute_analyze_code(self, args: dict[str, Any]) -> str:
        from .skills import CodeAnalyzer
        path = args["path"]
        ca = CodeAnalyzer(str(self.cwd))
        result = ca.analyze_file(path)
        
        if "error" in result:
            return result["error"]
        
        lines = ["Code Analysis", "=" * 40]
        lines.append(f"File: {result['path']}")
        lines.append(f"Lines: {result['lines']}")
        lines.append(f"Code lines: {result['code_lines']}")
        lines.append(f"Comment lines: {result['comment_lines']}")
        lines.append(f"Blank lines: {result['blank_lines']}")
        lines.append("")
        lines.append(f"Functions ({len(result['functions'])}):")
        for f in result["functions"][:5]:
            lines.append(f"  - {f['name']} (line {f['line']})")
        lines.append("")
        lines.append(f"Classes ({len(result['classes'])}):")
        for c in result["classes"][:5]:
            lines.append(f"  - {c['name']} (line {c['line']})")
        lines.append("")
        lines.append(f"Imports ({len(result['imports'])}):")
        lines.append(", ".join(result["imports"][:10]))
        return "\n".join(lines)

    def _execute_explain_code(self, args: dict[str, Any]) -> str:
        from .skills import CodeAnalyzer
        path = args["path"]
        start = args.get("start", 1)
        end = args.get("end")
        ca = CodeAnalyzer(str(self.cwd))
        return ca.explain_code(path, start, end)

    def _execute_generate_tests(self, args: dict[str, Any]) -> str:
        path = args["path"]
        framework = args.get("framework", "pytest")
        
        from .skills import CodeAnalyzer
        ca = CodeAnalyzer(str(self.cwd))
        analysis = ca.analyze_file(path)
        
        if "error" in analysis:
            return analysis["error"]
        
        funcs = analysis.get("functions", [])
        if not funcs:
            return "No functions found to generate tests for."
        
        if framework == "pytest":
            lines = ['"""Tests for {}"""'.format(path.replace(".py", ""))]
            lines.append("")
            lines.append("import pytest")
            lines.append(f"from {path.replace('.py', '')} import *")
            lines.append("")
            for f in funcs[:5]:
                lines.append(f"def test_{f['name']}():")
                lines.append("    # TODO: implement test")
                lines.append("    pass")
        else:
            lines = ["// Tests for " + path]
            lines.append("")
            for f in funcs[:5]:
                lines.append(f"describe('{f['name']}', () => {{")
                lines.append("  it('should work', () => {")
                lines.append("    // TODO: implement test")
                lines.append("  });")
                lines.append("});")
        
        return "\n".join(lines)

    def _execute_git_pre_commit(self, args: dict[str, Any]) -> str:
        import subprocess
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=self.cwd,
                capture_output=True,
                text=True
            )
            if not result.stdout.strip():
                return "Nothing to commit (working tree clean)"
            
            staged = subprocess.run(
                ["git", "diff", "--cached", "--stat"],
                cwd=self.cwd,
                capture_output=True,
                text=True
            )
            return f"Pre-commit checks:\nStaged: {staged.stdout or 'none'}\nUnstaged: {result.stdout}"
        except Exception as e:
            return f"ERROR: {e}"

    def _execute_get_keybindings(self, args: dict[str, Any]) -> str:
        return """Keyboard Shortcuts:
================
Tab         - Cycle agents
Ctrl+C      - Cancel
Ctrl+D      - Exit
Ctrl+L     - Clear screen
Ctrl+U     - Clear line
Up/Down    - History
Ctrl+R     - Search history
"""

    def _execute_set_theme(self, args: dict[str, Any]) -> str:
        theme = args.get("theme", "")
        themes = ["default", "dark", "light", "monokai", "dracula", "nord"]
        if theme not in themes:
            return f"Available themes: {', '.join(themes)}"
        return f"Theme set to: {theme}"

    def _execute_add_git_hook(self, args: dict[str, Any]) -> str:
        hook = args["hook"]
        command = args["command"]
        
        git_dir = self.cwd / ".git"
        if not git_dir.exists():
            return "ERROR: Not a git repository"
        
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        
        hook_path = hooks_dir / hook
        hook_path.write_text(f"""#!/bin/sh
{command}
""")
        hook_path.chmod(0o755)
        return f"SUCCESS: Added {hook} hook"

    def _execute_batch_read(self, args: dict[str, Any]) -> str:
        from .advanced import BatchOperation
        paths = args.get("paths", [])
        if not paths:
            return "ERROR: No paths provided"
        
        results = BatchOperation.batch_read(paths, str(self.cwd))
        
        output = [f"Read {len(results)} files:"]
        for path, content in results.items():
            preview = content[:200] + "..." if len(content) > 200 else content
            output.append(f"\n--- {path} ---\n{preview}")
        
        return "\n".join(output)

    def _execute_batch_write(self, args: dict[str, Any]) -> str:
        from .advanced import BatchOperation
        operations = args.get("operations", [])
        if not operations:
            return "ERROR: No operations provided"
        
        results = BatchOperation.batch_write(operations, str(self.cwd))
        
        output = f"SUCCESS: {len(results['success'])} files written"
        if results['failed']:
            output += f"\nFailed: {len(results['failed'])}"
            for f in results['failed']:
                output += f"\n  - {f['path']}: {f['error']}"
        
        return output

    def _execute_retry_tool(self, args: dict[str, Any]) -> str:
        from .advanced import get_retry_handler
        tool_name = args["tool"]
        tool_args = args.get("args", {})
        retries = args.get("retries", 3)
        
        handler = get_retry_handler()
        handler.config.max_retries = retries
        
        try:
            result = handler.execute(self.execute, tool_name, tool_args)
            return f"SUCCESS after {retries} retries:\n{result}"
        except Exception as e:
            return f"ERROR after {retries} retries: {e}"

    def _execute_get_tool_timeout(self, args: dict[str, Any]) -> str:
        from .advanced import ToolTimeout
        tool = args["tool"]
        timeout = ToolTimeout.get_timeout(tool)
        return f"Timeout for {tool}: {timeout}s"

    def _execute_set_tool_timeout(self, args: dict[str, Any]) -> str:
        from .advanced import ToolTimeout
        tool = args["tool"]
        timeout = args["timeout"]
        ToolTimeout.set_timeout(tool, timeout)
        return f"Set timeout for {tool} to {timeout}s"

    def _execute_clear_file_cache(self, args: dict[str, Any]) -> str:
        from .advanced import get_file_cache
        cache = get_file_cache()
        cache.clear()
        return "SUCCESS: File cache cleared"

    def _execute_get_context_info(self, args: dict[str, Any]) -> str:
        from .advanced import ContextOptimizer
        agent = getattr(self, "_agent", None)
        if agent is None:
            return "No agent context available"
        
        messages = agent.history if hasattr(agent, "history") else []
        info = ContextOptimizer.extract_key_info(messages)
        
        output = ["Context Analysis", "=" * 40]
        output.append(f"Files mentioned: {', '.join(info['files_mentioned'][:10]) or 'none'}")
        output.append(f"Tools used: {', '.join(info['tools_used']) or 'none'}")
        output.append(f"Errors: {len(info['errors'])}")
        
        return "\n".join(output)

    def _execute_start_file_watch(self, args: dict[str, Any]) -> str:
        from .project import FileWatcher
        patterns = args.get("patterns")
        
        if not hasattr(self, "_file_watcher"):
            self._file_watcher = FileWatcher(str(self.cwd))
        
        observer = self._file_watcher.watch(patterns)
        if observer:
            return f"SUCCESS: Watching {patterns or ['default']} for changes"
        return "ERROR: Could not start watcher (install watchdog: pip install watchdog)"

    def _execute_stop_file_watch(self, args: dict[str, Any]) -> str:
        if hasattr(self, "_file_watcher"):
            self._file_watcher.stop()
            return "SUCCESS: File watcher stopped"
        return "ERROR: No file watcher running"

    def _execute_expand_vars(self, args: dict[str, Any]) -> str:
        from .extras import ShellExpander
        text = args["text"]
        vars = args.get("vars", {})
        return ShellExpander.expand(text, vars)

    def _execute_get_env(self, args: dict[str, Any]) -> str:
        from .extras import get_env_manager
        key = args["key"]
        em = get_env_manager(str(self.cwd))
        value = em.get(key)
        return f"{key}={value}" if value else f"ERROR: {key} not found"

    def _execute_set_env(self, args: dict[str, Any]) -> str:
        from .extras import get_env_manager
        key = args["key"]
        value = args["value"]
        em = get_env_manager(str(self.cwd))
        em.set(key, value)
        return f"SUCCESS: {key}={value}"

    def _execute_list_env(self, args: dict[str, Any]) -> str:
        from .extras import get_env_manager
        em = get_env_manager(str(self.cwd))
        env = em.list()
        lines = ["Environment Variables:", "=" * 40]
        for k, v in sorted(env.items())[:50]:
            lines.append(f"{k}={v[:50]}")
        return "\n".join(lines)

    def _execute_submit_task(self, args: dict[str, Any]) -> str:
        from .extras import get_task_queue
        import asyncio
        name = args["name"]
        command = args["command"]
        
        async def run_command():
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.cwd)
            )
            stdout, stderr = await proc.communicate()
            return stdout.decode() or stderr.decode()

        queue = get_task_queue()
        task_id = asyncio.run(queue.add(name, run_command))
        return f"Task submitted: {task_id} ({name})"

    def _execute_list_tasks(self, args: dict[str, Any]) -> str:
        from .extras import get_task_queue
        queue = get_task_queue()
        tasks = queue.list()
        if not tasks:
            return "No tasks"
        lines = ["Tasks:", "=" * 40]
        for t in tasks:
            lines.append(f"  {t['id']} - {t['name']} [{t['status']}]")
        return "\n".join(lines)

    def _execute_get_task(self, args: dict[str, Any]) -> str:
        from .extras import get_task_queue
        task_id = args["task_id"]
        queue = get_task_queue()
        task = queue.get(task_id)
        if not task:
            return f"ERROR: Task {task_id} not found"
        return f"Task: {task.name}\nStatus: {task.status}\nResult: {task.result}\nError: {task.error}"

    def _execute_search_history(self, args: dict[str, Any]) -> str:
        from .extras import get_history_search
        query = args["query"]
        fuzzy = args.get("fuzzy", True)
        hs = get_history_search()
        results = hs.search(query, fuzzy) if fuzzy else hs.fuzzy_match(query)
        if not results:
            return "No results found"
        lines = [f"Found {len(results)} results:", "=" * 40]
        for r in results[:5]:
            sim = r.get("similarity", 1.0)
            lines.append(f"  - {r['query'][:50]} (sim: {sim:.2f})")
        return "\n".join(lines)

    def _execute_validate_workspace(self, args: dict[str, Any]) -> str:
        from .extras import WorkspaceValidator
        wv = WorkspaceValidator(str(self.cwd))
        result = wv.validate_config()
        
        lines = ["Workspace Validation", "=" * 40]
        lines.append(f"Valid: {result['valid']}")
        if result['issues']:
            lines.append("\nIssues:")
            for issue in result['issues']:
                lines.append(f"  - {issue}")
        return "\n".join(lines)

    def _execute_security_audit(self, args: dict[str, Any]) -> str:
        from .extras import SecurityAuditor
        path = args.get("path")
        
        sa = SecurityAuditor(str(self.cwd))
        if path:
            result = sa.audit_file(self.cwd / path)
        else:
            result = sa.audit_project()
        
        if isinstance(result, dict) and "files" in result:
            lines = ["Security Audit", "=" * 40]
            lines.append(f"Total issues: {result['total_issues']}")
            for f in result['files'][:5]:
                lines.append(f"\n{f['path']}:")
                for issue in f['issues']:
                    lines.append(f"  - {issue['message']}")
            return "\n".join(lines)
        else:
            return f"Issues: {result}"

    def _execute_refactor_code(self, args: dict[str, Any]) -> str:
        from .codegen import CodeRefactorer
        path = args["path"]
        function = args["function"]
        style = args.get("style", "modern")
        
        cr = CodeRefactorer(str(self.cwd))
        result = cr.refactor_function(path, function, style)
        
        if "error" in result:
            return f"ERROR: {result['error']}"
        return f"SUCCESS: Refactored {function} with {style} style"

    def _execute_generate_db_model(self, args: dict[str, Any]) -> str:
        from .codegen import DatabaseManager
        table = args["table"]
        columns = args["columns"]
        
        dm = DatabaseManager(str(self.cwd))
        code = dm.generate_model(table, columns)
        return f"Generated model for {table}:\n\n{code}"

    def _execute_generate_dockerfile(self, args: dict[str, Any]) -> str:
        from .codegen import DockerManager
        language = args["language"]
        
        dm = DockerManager(str(self.cwd))
        dockerfile = dm.generate_dockerfile(language)
        return dockerfile

    def _execute_generate_docker_compose(self, args: dict[str, Any]) -> str:
        from .codegen import DockerManager
        services = args.get("services", [])
        
        dm = DockerManager(str(self.cwd))
        compose = dm.generate_docker_compose(services)
        return compose

    def _execute_generate_api_client(self, args: dict[str, Any]) -> str:
        from .codegen import APIClientGenerator
        spec = args["spec"]
        
        acg = APIClientGenerator(str(self.cwd))
        code = acg.generate_from_openapi(spec)
        return code

    def _execute_generate_docs(self, args: dict[str, Any]) -> str:
        from .codegen import DocumentationGenerator
        dtype = args["type"]
        path = args.get("path")
        
        dg = DocumentationGenerator(str(self.cwd))
        
        if dtype == "readme":
            return dg.generate_readme()
        elif dtype == "api" and path:
            return dg.generate_api_docs(path)
        elif dtype == "markdoc":
            return dg.generate_markdoc()
        
        return "ERROR: Invalid doc type or missing path"

    def _execute_profile_code(self, args: dict[str, Any]) -> str:
        from .codegen import PerformanceProfiler
        path = args["path"]
        
        pp = PerformanceProfiler(str(self.cwd))
        result = pp.profile_file(path)
        
        if "error" in result:
            return result["error"]
        
        lines = ["Code Profile", "=" * 40]
        lines.append(f"Lines: {result['lines']}")
        lines.append(f"Functions: {result['functions']}")
        lines.append(f"Classes: {result['classes']}")
        lines.append(f"Imports: {result['imports']}")
        lines.append(f"Complexity: {result['complexity_score']}")
        return "\n".join(lines)

    def _execute_optimize_code(self, args: dict[str, Any]) -> str:
        from .codegen import PerformanceProfiler
        path = args["path"]
        
        pp = PerformanceProfiler(str(self.cwd))
        suggestions = pp.suggest_optimizations(path)
        
        lines = ["Optimization Suggestions", "=" * 40]
        for s in suggestions:
            lines.append(f"- {s}")
        return "\n".join(lines)


class AsyncToolExecutor(ToolExecutor):
    async def execute_async(self, tool_name: str, args: dict[str, Any]) -> str:
        method = getattr(self, f"_execute_{tool_name}", None)
        if not method:
            return f"ERROR: Unknown tool '{tool_name}'"
        try:
            if hasattr(method, "__await__"):
                return await method(args)
            return method(args)
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"

    async def execute_all_parallel(self, tool_calls: list[tuple[str, dict[str, Any]]]) -> list[str]:
        tasks = [self.execute_async(name, args) for name, args in tool_calls]
        return await asyncio.gather(*tasks)