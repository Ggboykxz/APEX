"""Refactored workspace module - More testable."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import subprocess


@dataclass
class GitContext:
    """Testable Git context."""
    branch: str = ""
    remote: str = ""
    remote_url: str = ""
    is_dirty: bool = False
    commit: str = ""
    commits_ahead: int = 0
    commits_behind: int = 0
    pr_number: Optional[int] = None
    pr_title: str = ""
    pr_url: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class WorkspaceContext:
    """Testable workspace context."""
    root: Path
    git: Optional[GitContext] = None
    language: str = ""
    package_manager: str = ""
    test_framework: str = ""


class WorkspaceManager:
    """Testable workspace manager."""
    
    def __init__(self, root: Path = None):
        self._root = root or Path.cwd()
        self._context: Optional[WorkspaceContext] = None
    
    def analyze(self) -> WorkspaceContext:
        """Analyze the workspace."""
        self._context = WorkspaceContext(root=self._root)
        
        # Check if it's a git repo
        if (self._root / ".git").exists():
            self._context.git = self._get_git_info()
        
        return self._context
    
    def _get_git_info(self) -> GitContext:
        """Get git information."""
        git = GitContext()
        
        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self._root, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                git.branch = result.stdout.strip()
            
            # Check if dirty
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self._root, capture_output=True, text=True, timeout=5
            )
            git.is_dirty = bool(result.stdout.strip())
            
            # Get latest commit
            result = subprocess.run(
                ["git", "log", "-1", "--oneline"],
                cwd=self._root, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                git.commit = result.stdout.strip()
            
        except Exception:
            pass
        
        return git
    
    def get_context(self) -> Optional[WorkspaceContext]:
        """Get the workspace context."""
        return self._context
    
    def get_files(self) -> List[Path]:
        """Get all files in workspace."""
        if not self._context:
            self.analyze()
        return [f for f in self._root.rglob("*") if f.is_file()]
    
    def get_directories(self) -> List[Path]:
        """Get all directories in workspace."""
        if not self._context:
            self.analyze()
        return [d for d in self._root.rglob("*") if d.is_dir()]
    
    def get_language_stats(self) -> dict:
        """Get language statistics."""
        stats = {}
        for f in self.get_files():
            ext = f.suffix
            if ext:
                stats[ext] = stats.get(ext, 0) + 1
        return stats
    
    def search_files(self, pattern: str) -> List[Path]:
        """Search for files matching pattern."""
        import fnmatch
        return [f for f in self.get_files() if fnmatch.fnmatch(f.name, pattern)]
    
    def get_git_context(self) -> Optional[GitContext]:
        """Get git context."""
        if not self._context:
            self.analyze()
        return self._context.git
    
    def update_context(self, **kwargs) -> None:
        """Update workspace context."""
        if not self._context:
            self._context = WorkspaceContext(root=self._root)
        for key, value in kwargs.items():
            if hasattr(self._context, key):
                setattr(self._context, key, value)


def get_workspace_root(path: str = ".") -> Path:
    """Get the workspace root for a given path."""
    p = Path(path).resolve()
    # Walk up looking for markers
    markers = [".git", "pyproject.toml", "package.json", "Cargo.toml"]
    while p != p.parent:
        if any((p / m).exists() for m in markers):
            return p
        p = p.parent
    return Path.cwd()