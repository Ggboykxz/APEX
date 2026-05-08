"""Refactored mentions module - More testable."""

import re
from pathlib import Path
from typing import Optional, Callable, List
from dataclasses import dataclass


@dataclass
class FileMention:
    path: str
    start: int
    end: int


@dataclass
class AgentMention:
    name: str
    start: int
    end: int


DEFAULT_AGENT_NAMES = {"explore", "general", "build", "plan"}
DEFAULT_IGNORED_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "target", "dist", "build", ".pytest_cache"}


class MentionParser:
    FILE_PATTERN = re.compile(r'@(\S+\.\S+)')
    AGENT_PATTERN = re.compile(r'@(\w+)(?:\s|$)')
    
    def __init__(
        self,
        cwd: str,
        agent_names: Optional[set[str]] = None,
        path_resolver: Optional[Callable[[Path], Path]] = None
    ):
        self.cwd = Path(cwd)
        self._agent_names = agent_names or DEFAULT_AGENT_NAMES
        self._path_resolver = path_resolver

    def parse(self, text: str) -> tuple[list[FileMention], list[AgentMention]]:
        file_mentions = []
        agent_mentions = []

        for match in self.FILE_PATTERN.finditer(text):
            path = match.group(1)
            file_mentions.append(FileMention(path, match.start(), match.end()))

        for match in self.AGENT_PATTERN.finditer(text):
            name = match.group(1).lower()
            if name in self._agent_names:
                agent_mentions.append(AgentMention(name, match.start(), match.end()))

        return file_mentions, agent_mentions

    def resolve_file(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.cwd / p).resolve()

    def read_mentioned_files(self, text: str, file_reader: Optional[Callable[[Path], Optional[str]]] = None) -> dict[str, str]:
        file_mentions, _ = self.parse(text)
        result = {}

        for fm in file_mentions:
            resolved = self.resolve_file(fm.path)
            reader = file_reader or self._default_reader
            try:
                content = reader(resolved)
                if content:
                    result[fm.path] = content[:5000]
            except Exception:
                pass

        return result

    def _default_reader(self, path: Path) -> Optional[str]:
        if path.exists() and path.is_file():
            return path.read_text()
        return None


class FileMentionCompleter:
    def __init__(
        self,
        cwd: str,
        ignored_dirs: Optional[set[str]] = None,
        rglob_func: Optional[Callable[[str], List[Path]]] = None
    ):
        self.cwd = Path(cwd)
        self._ignored_dirs = ignored_dirs or DEFAULT_IGNORED_DIRS
        self._rglob_func = rglob_func

    def complete(self, prefix: str) -> list[str]:
        if not prefix:
            return []

        results = []
        search_pattern = f"*{prefix}*"

        paths = self._rglob_func(search_pattern) if self._rglob_func else self.cwd.rglob(search_pattern)

        for p in paths:
            if p.is_file() and not self._is_ignored(p):
                try:
                    rel = p.relative_to(self.cwd)
                    results.append(str(rel))
                except ValueError:
                    pass

        return results[:20]

    def _is_ignored(self, path: Path) -> bool:
        return any(part in self._ignored_dirs for part in path.parts)


def create_mention_parser(cwd: str, agent_names: Optional[set[str]] = None) -> MentionParser:
    return MentionParser(cwd, agent_names)


def create_file_completer(cwd: str, ignored_dirs: Optional[set[str]] = None) -> FileMentionCompleter:
    return FileMentionCompleter(cwd, ignored_dirs)