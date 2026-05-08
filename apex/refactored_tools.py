"""Refactored tools module - More testable and modular."""

from pathlib import Path
from typing import Optional


class FileOperations:
    """Testable file operations."""
    
    def __init__(self, cwd: Path):
        self.cwd = cwd
    
    def resolve_path(self, path: str) -> Path:
        """Resolve path relative to cwd."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.cwd / p
    
    def read_file(self, path: str) -> str:
        """Read a file."""
        full_path = self.resolve_path(path)
        if not full_path.exists():
            return f"ERROR: File not found: {path}"
        try:
            lines = full_path.read_text().splitlines()
            return "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines))
        except Exception as e:
            return f"ERROR: Cannot read file: {e}"
    
    def write_file(self, path: str, content: str) -> str:
        """Write content to file."""
        full_path = self.resolve_path(path)
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            return f"SUCCESS: Wrote {len(content)} chars to {path}"
        except Exception as e:
            return f"ERROR: Cannot write file: {e}"
    
    def edit_file(self, path: str, old_string: str, new_string: str) -> str:
        """Edit a file by replacing old_string with new_string."""
        full_path = self.resolve_path(path)
        if not full_path.exists():
            return f"ERROR: File not found: {path}"
        try:
            content = full_path.read_text()
            if old_string not in content:
                return "ERROR: String not found in file"
            new_content = content.replace(old_string, new_string, 1)
            full_path.write_text(new_content)
            return f"SUCCESS: Edited {path}"
        except Exception as e:
            return f"ERROR: Cannot edit file: {e}"
    
    def delete_file(self, path: str) -> str:
        """Delete a file or directory."""
        full_path = self.resolve_path(path)
        if not full_path.exists():
            return f"ERROR: Path not found: {path}"
        try:
            if full_path.is_file():
                full_path.unlink()
            elif full_path.is_dir():
                import shutil
                shutil.rmtree(full_path)
            return f"SUCCESS: Deleted {path}"
        except Exception as e:
            return f"ERROR: Cannot delete: {e}"
    
    def create_directory(self, path: str) -> str:
        """Create a directory."""
        full_path = self.resolve_path(path)
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            return f"SUCCESS: Created directory {path}"
        except Exception as e:
            return f"ERROR: Cannot create directory: {e}"
    
    def list_files(self, path: str = ".") -> str:
        """List files in directory."""
        full_path = self.resolve_path(path)
        if not full_path.exists():
            return f"ERROR: Directory not found: {path}"
        if not full_path.is_dir():
            return f"ERROR: Not a directory: {path}"
        try:
            entries = []
            for entry in sorted(full_path.iterdir()):
                try:
                    size = entry.stat().st_size
                    size_str = f"{size:>10}" if entry.is_file() else "<DIR>    "
                except Exception:
                    size_str = "?          "
                entries.append(f"{size_str}  {entry.name}")
            return "\n".join(entries) if entries else "[empty directory]"
        except Exception as e:
            return f"ERROR: Cannot list directory: {e}"
    
    def search_in_files(self, pattern: str, path: str = ".") -> str:
        """Search for pattern in files."""
        import re
        full_path = self.resolve_path(path)
        if not full_path.exists():
            return f"ERROR: Path not found: {path}"
        try:
            regex = re.compile(pattern)
            results = []
            for file_path in full_path.rglob("*"):
                if file_path.is_file():
                    try:
                        lines = file_path.read_text().splitlines()
                        for i, line in enumerate(lines, 1):
                            if regex.search(line):
                                results.append(f"{file_path}:{i}: {line.rstrip()}")
                    except Exception:
                        pass
            return "\n".join(results) if results else "[no matches found]"
        except re.error as e:
            return f"ERROR: Invalid regex: {e}"
        except Exception as e:
            return f"ERROR: Search failed: {e}"
    
    def glob_search(self, pattern: str, path: str = ".") -> str:
        """Glob search for files."""
        import fnmatch
        full_path = self.resolve_path(path)
        if not full_path.exists():
            return f"ERROR: Path not found: {path}"
        results = []
        for file_path in full_path.rglob("*"):
            if file_path.is_file() and fnmatch.fnmatch(file_path.name, pattern):
                results.append(str(file_path.relative_to(full_path)))
        return "\n".join(results) if results else "[no matches found]"


class GitOperations:
    """Testable git operations."""
    
    def __init__(self, cwd: Path):
        self.cwd = cwd
    
    def resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return self.cwd / p
    
    def get_git_status(self, path: str = ".") -> str:
        """Get git status."""
        full_path = self.resolve_path(path)
        git_dir = full_path / ".git"
        if not git_dir.exists():
            return "[Not a git repository]"
        
        try:
            import subprocess
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=full_path, capture_output=True, text=True
            )
            if result.returncode != 0:
                return "[Git command failed]"
            
            lines = ["[GIT] Status:"]
            for line in result.stdout.strip().split("\n"):
                if line:
                    status = line[:2]
                    filename = line[3:]
                    lines.append(f"  {status} {filename}")
            return "\n".join(lines) if lines else "[Clean]"
        except FileNotFoundError:
            return "[Git not found]"
        except Exception as e:
            return f"[Error: {e}]"
    
    def get_git_log(self, path: str = ".", max_count: int = 10) -> str:
        """Get git log."""
        full_path = self.resolve_path(path)
        git_dir = full_path / ".git"
        if not git_dir.exists():
            return "[Not a git repository]"
        
        try:
            import subprocess
            result = subprocess.run(
                ["git", "log", f"-{max_count}", "--oneline"],
                cwd=full_path, capture_output=True, text=True
            )
            if result.returncode != 0:
                return "[Git command failed]"
            return result.stdout if result.stdout else "[No commits]"
        except FileNotFoundError:
            return "[Git not found]"
        except Exception as e:
            return f"[Error: {e}]"
    
    def git_diff(self, path: str = ".") -> str:
        """Get git diff."""
        full_path = self.resolve_path(path)
        git_dir = full_path / ".git"
        if not git_dir.exists():
            return "[Not a git repository]"
        
        try:
            import subprocess
            result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=full_path, capture_output=True, text=True
            )
            return result.stdout if result.stdout else "[No changes]"
        except FileNotFoundError:
            return "[Git not found]"
        except Exception as e:
            return f"[Error: {e}]"


class CommandOperations:
    """Testable command execution."""
    
    def __init__(self, cwd: Path):
        self.cwd = cwd
    
    def resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return self.cwd / p
    
    def run_command(self, command: str, cwd: Optional[str] = None) -> str:
        """Run a shell command."""
        import subprocess
        work_dir = self.resolve_path(cwd) if cwd else self.cwd
        try:
            result = subprocess.run(
                command, shell=True, cwd=work_dir,
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                return result.stdout if result.stdout else "[Command completed with no output]"
            return f"ERROR: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out after 60 seconds"
        except FileNotFoundError:
            return "ERROR: Command not found"
        except Exception as e:
            return f"ERROR: {e}"


class WebOperations:
    """Testable web operations."""
    
    def __init__(self, cwd: Path):
        self.cwd = cwd
    
    def web_search(self, query: str) -> str:
        """Perform web search."""
        return f"[Web search placeholder: {query}]"
    
    def fetch_url(self, url: str) -> str:
        """Fetch URL content."""
        import aiohttp
        import asyncio
        
        async def _fetch():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        return await response.text()
            except Exception as e:
                return f"ERROR: {e}"
        
        try:
            return asyncio.run(_fetch())
        except Exception as e:
            return f"ERROR: {e}"


# Testable factory function
def create_file_ops(cwd: str) -> FileOperations:
    """Factory for FileOperations."""
    return FileOperations(Path(cwd))


def create_git_ops(cwd: str) -> GitOperations:
    """Factory for GitOperations."""
    return GitOperations(Path(cwd))


def create_command_ops(cwd: str) -> CommandOperations:
    """Factory for CommandOperations."""
    return CommandOperations(Path(cwd))


def create_web_ops(cwd: str) -> WebOperations:
    """Factory for WebOperations."""
    return WebOperations(Path(cwd))