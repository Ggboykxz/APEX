"""@Mention system for APEX - OpenCode-style file/agent mentions."""

import re
from pathlib import Path
from typing import Optional
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


class MentionParser:
    FILE_PATTERN = re.compile(r'@(\S+\.\S+)')
    AGENT_PATTERN = re.compile(r'@(\w+)(?:\s|$)')

    def __init__(self, cwd: str):
        self.cwd = Path(cwd)

    def parse(self, text: str) -> tuple[list[FileMention], list[AgentMention]]:
        file_mentions = []
        agent_mentions = []

        for match in self.FILE_PATTERN.finditer(text):
            path = match.group(1)
            file_mentions.append(FileMention(path, match.start(), match.end()))

        agent_names = {"explore", "general", "build", "plan"}
        for match in self.AGENT_PATTERN.finditer(text):
            name = match.group(1).lower()
            if name in agent_names:
                agent_mentions.append(AgentMention(name, match.start(), match.end()))

        return file_mentions, agent_mentions

    def resolve_file(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.cwd / p).resolve()

    def read_mentioned_files(self, text: str) -> dict[str, str]:
        file_mentions, _ = self.parse(text)
        result = {}

        for fm in file_mentions:
            resolved = self.resolve_file(fm.path)
            if resolved.exists() and resolved.is_file():
                try:
                    content = resolved.read_text()
                    result[fm.path] = content[:5000]
                except Exception:
                    pass

        return result


class FileMentionCompleter:
    def __init__(self, cwd: str):
        self.cwd = Path(cwd)

    def complete(self, prefix: str) -> list[str]:
        if not prefix:
            return []

        results = []
        search_pattern = f"*{prefix}*"

        for p in self.cwd.rglob(search_pattern):
            if p.is_file() and not self._is_ignored(p):
                rel = p.relative_to(self.cwd)
                results.append(str(rel))

        return results[:20]

    def _is_ignored(self, path: Path) -> bool:
        ignore = {".git", "node_modules", "__pycache__", "venv", ".venv", "target", "dist", "build", ".pytest_cache"}
        return any(part in ignore for part in path.parts)


_mention_parser: Optional[MentionParser] = None
_file_completer: Optional[FileMentionCompleter] = None


def get_mention_parser(cwd: str) -> MentionParser:
    global _mention_parser
    _mention_parser = MentionParser(cwd)
    return _mention_parser


def get_file_completer(cwd: str) -> FileMentionCompleter:
    global _file_completer
    _file_completer = FileMentionCompleter(cwd)
    return _file_completer