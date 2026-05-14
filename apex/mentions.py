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
    # Match @mention only when preceded by start-of-string or whitespace
    # Also match @ in middle of word if followed by something with a dot (file extension)
    _MENTION_AT_BOUNDARY = re.compile(r"(?:^|(?<=\s))@(\S+)")
    _MENTION_IN_WORD_WITH_DOT = re.compile(r"(?<=\S)@(\S+\.\S+)")
    AGENT_NAMES = {"build", "plan", "planner", "reviewer", "shell", "general", "explore", "scout", "compaction", "title", "summary"}

    def __init__(self, cwd: str):
        self.cwd = Path(cwd)

    def parse(self, text: str) -> tuple[list[FileMention], list[AgentMention]]:
        file_mentions = []
        agent_mentions = []
        seen_agents = set()
        seen_positions = set()

        # Collect all matches from both patterns
        matches = []

        for match in self._MENTION_AT_BOUNDARY.finditer(text):
            name = match.group(1)
            at_pos = match.start()
            # Handle @@ cases: if name starts with @, strip it and adjust position
            if name.startswith('@'):
                name = name[1:]  # @@test.py → test.py
                at_pos += 1      # The real @ is the second one
                if not name:
                    continue  # bare @@ → skip
            matches.append((name, at_pos))

        for match in self._MENTION_IN_WORD_WITH_DOT.finditer(text):
            name = match.group(1)
            # Find the @ position within the match
            at_pos = match.start()
            while at_pos < len(text) and text[at_pos] != '@':
                at_pos += 1
            # Skip if already covered by boundary pattern (dedup by @ position)
            if at_pos in {m[1] for m in matches}:
                continue
            matches.append((name, at_pos))

        for name, at_pos in matches:
            if at_pos in seen_positions:
                continue
            seen_positions.add(at_pos)

            mention_start = at_pos
            mention_end = at_pos + 1 + len(name)

            name_lower = name.lower()
            if name_lower in self.AGENT_NAMES and name_lower not in seen_agents:
                seen_agents.add(name_lower)
                agent_mentions.append(AgentMention(name_lower, mention_start, mention_end))
            else:
                file_mentions.append(FileMention(name, mention_start, mention_end))

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
        ignore = {
            ".git",
            "node_modules",
            "__pycache__",
            "venv",
            ".venv",
            "target",
            "dist",
            "build",
            ".pytest_cache",
        }
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
