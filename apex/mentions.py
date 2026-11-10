"""@Mention system for APEX - OpenCode-style file/agent mentions."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


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


from dataclasses import dataclass


@dataclass
class _ParseState:
    """The state of one parse run."""

    file_mentions: list[FileMention]
    agent_mentions: list[AgentMention]
    seen_agents: set[str]
    seen_positions: set[int]


class MentionParser:
    # Match @mention only when preceded by start-of-string or whitespace
    # Also match @ in middle of word if followed by something with a dot (file extension)
    _MENTION_AT_BOUNDARY = re.compile(r"(?:^|(?<=\s))@(\S+)")
    _MENTION_IN_WORD_WITH_DOT = re.compile(r"(?<=\S)@(\S+\.\S+)")
    AGENT_NAMES: ClassVar[set[str]] = {
        "build",
        "plan",
        "planner",
        "reviewer",
        "shell",
        "general",
        "explore",
        "scout",
        "compaction",
        "title",
        "summary",
    }

    def __init__(self, cwd: str):
        self.cwd = Path(cwd)

    def parse(self, text: str) -> tuple[list[FileMention], list[AgentMention]]:
        file_mentions: list[FileMention] = []
        agent_mentions: list[AgentMention] = []
        seen_agents: set[str] = set()
        seen_positions: set[int] = set()

        state = _ParseState(file_mentions, agent_mentions, seen_agents, seen_positions)
        matches = self._collect_matches(text)
        for name, at_pos in matches:
            self._record(name, at_pos, state)

        return file_mentions, agent_mentions

    def _collect_matches(self, text: str) -> list[tuple[str, int]]:
        """The candidate mentions, with their @ position."""
        matches: list[tuple[str, int]] = []
        self._collect_boundary_matches(text, matches)
        self._collect_in_word_matches(text, matches)
        return matches

    def _collect_boundary_matches(self, text: str, matches: list[tuple[str, int]]) -> None:
        """Add the mentions matched at a word boundary."""
        for match in self._MENTION_AT_BOUNDARY.finditer(text):
            name = match.group(1)
            at_pos = match.start()
            if name.startswith("@"):
                name = name[1:]
                at_pos += 1
                if not name:
                    continue
            matches.append((name, at_pos))

    def _collect_in_word_matches(self, text: str, matches: list[tuple[str, int]]) -> None:
        """Add the mentions matched inside a word that carries a dot."""
        covered = {pos for _, pos in matches}
        for match in self._MENTION_IN_WORD_WITH_DOT.finditer(text):
            name = match.group(1)
            at_pos = self._at_position(text, match.start())
            if at_pos in covered:
                continue
            matches.append((name, at_pos))

    @staticmethod
    def _at_position(text: str, start: int) -> int:
        """The position of the @ inside a match."""
        at_pos = start
        while at_pos < len(text) and text[at_pos] != "@":
            at_pos += 1
        return at_pos

    def _record(self, name: str, at_pos: int, state: "_ParseState") -> None:
        """Classify one mention as a file or an agent."""
        if at_pos in state.seen_positions:
            return
        state.seen_positions.add(at_pos)

        mention_start = at_pos
        mention_end = at_pos + 1 + len(name)

        name_lower = name.lower()
        if name_lower in self.AGENT_NAMES and name_lower not in state.seen_agents:
            state.seen_agents.add(name_lower)
            state.agent_mentions.append(AgentMention(name_lower, mention_start, mention_end))
        else:
            state.file_mentions.append(FileMention(name, mention_start, mention_end))

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
                    # Explicit UTF-8 so binary files raise UnicodeDecodeError and are
                    # skipped on every platform (the locale default, e.g. cp1252 on
                    # Windows, would decode arbitrary bytes instead of rejecting them).
                    content = resolved.read_text(encoding="utf-8")
                    result[fm.path] = content[:5000]
                except Exception:  # noqa: S110, BLE001
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


_mention_parser: MentionParser | None = None
_file_completer: FileMentionCompleter | None = None


def get_mention_parser(cwd: str) -> MentionParser:
    global _mention_parser
    _mention_parser = MentionParser(cwd)
    return _mention_parser


def get_file_completer(cwd: str) -> FileMentionCompleter:
    global _file_completer
    _file_completer = FileMentionCompleter(cwd)
    return _file_completer
