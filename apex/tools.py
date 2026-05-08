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