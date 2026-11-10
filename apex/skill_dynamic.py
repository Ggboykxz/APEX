"""APEX Dynamic Skills System.

Modelled on OpenCode's skill service (@opencode/schema Skill + core skill.ts).
Provides:

- SKILL.md parsing with YAML frontmatter (name, description, metadata,
  disable-model-invocation)
- Auto-discovery: recursive scan (max depth 6) of directories containing
  SKILL.md files
- Sources: directory (local), url (remote git), embedded
- Filesystem watch with debounce (100ms default) + skill.updated event
- Skill registration into Core's SkillService
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from apex.core.service import Core, SkillInfo
from apex.hooks import PluginHooks
from apex.schema import SkillID
from apex.utils.frontmatter import parse_frontmatter_document

__all__ = [
    "DynamicSkillManager",
    "SkillDiscovery",
    "SkillSourceConfig",
    "SkillWatcher",
    "parse_skill_md",
]


# ---------------------------------------------------------------------------
# Skill source types
# ---------------------------------------------------------------------------

SkillSource = str  # "directory" | "url" | "embedded"


@dataclass
class SkillSourceConfig:
    kind: SkillSource
    path: str | None = None  # for directory
    url: str | None = None  # for url
    ref: str | None = None  # git ref for url
    max_depth: int = 6  # for directory scan


# ---------------------------------------------------------------------------
# SKILL.md parsing
# ---------------------------------------------------------------------------


def parse_skill_md(content: str, path: str) -> SkillInfo | None:
    """Parse a SKILL.md file into a :class:`SkillInfo`.

    Returns ``None`` if the file has no valid frontmatter or is missing the
    required ``name`` field.
    """
    metadata, _body = parse_frontmatter_document(content)
    if metadata is None:
        return None

    name = metadata.get("name")
    if not name:
        return None

    return SkillInfo(
        id=SkillID(name),
        name=name,
        description=metadata.get("description", ""),
        path=path,
        autoinvoke=bool(metadata.get("autoinvoke", False)),
        disable_model_invocation=bool(metadata.get("disable-model-invocation", False)),
        metadata=metadata.get("metadata", {}) or {},
    )


# ---------------------------------------------------------------------------
# Skill discovery (directory scan)
# ---------------------------------------------------------------------------


class SkillDiscovery:
    """Scan directories for SKILL.md files (recursive, max depth 6)."""

    def __init__(self, config: SkillSourceConfig) -> None:
        self.config = config

    def discover(self) -> dict[str, SkillInfo]:
        """Return {skill_id: SkillInfo} for every SKILL.md found."""
        skills: dict[str, SkillInfo] = {}
        root = Path(self.config.path or ".")
        if not root.exists():
            return skills

        for skill_md in self._walk_skill_files(root):
            try:
                content = skill_md.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            skill = parse_skill_md(content, str(skill_md))
            if skill is not None:
                skills[skill.id.value] = skill
        return skills

    def _walk_skill_files(self, root: Path):
        """Yield SKILL.md files under root, respecting max_depth."""
        for dirpath, dirnames, filenames in os.walk(root):
            rel = Path(dirpath).relative_to(root)
            depth = len(rel.parts)
            if depth > self.config.max_depth:
                dirnames[:] = []
                continue

            # Prune common non-skill directories
            dirnames[:] = [
                d
                for d in dirnames
                if d not in {".git", "node_modules", "__pycache__", ".next", "dist", "build"}
                and not d.startswith(".")
            ]

            if "SKILL.md" in filenames:
                yield Path(dirpath) / "SKILL.md"


# ---------------------------------------------------------------------------
# Skill watcher (filesystem debounce)
# ---------------------------------------------------------------------------


class SkillWatcher:
    """Watch a directory for SKILL.md changes with debounce.

    On change, re-discovers the directory and emits ``skill.updated`` via
    the provided hooks service.
    """

    def __init__(
        self,
        config: SkillSourceConfig,
        hooks: PluginHooks,
        debounce_ms: int = 100,
    ) -> None:
        self.config = config
        self.hooks = hooks
        self.debounce_ms = debounce_ms
        self._task: asyncio.Task | None = None
        self._pending: set[str] = set()
        self._running = False

    async def start(self, on_change: Callable[[dict[str, SkillInfo]], None]) -> None:
        """Begin polling for changes (polling fallback)."""
        self._running = True
        while self._running:
            await asyncio.sleep(self.debounce_ms / 1000.0)
            if self._pending:
                pending = self._pending.copy()
                self._pending.clear()
                discovery = SkillDiscovery(self.config)
                skills = discovery.discover()
                on_change(skills)
                for skill_id in pending:
                    self.hooks.trigger(
                        "skill", "updated", {"skill_id": skill_id, "source": self.config.path}
                    )

    def stop(self) -> None:
        self._running = False

    def notify_change(self, path: str) -> None:
        """Called by a filesystem watcher when a file changes."""
        if "SKILL.md" in path:
            self._pending.add(path)


# ---------------------------------------------------------------------------
# Dynamic skill manager
# ---------------------------------------------------------------------------


class DynamicSkillManager:
    """Orchestrates skill discovery, registration and watching."""

    def __init__(
        self,
        core: Core,
        hooks: PluginHooks,
        configs: list[SkillSourceConfig],
    ) -> None:
        self.core = core
        self.hooks = hooks
        self.configs = configs
        self._discoveries: list[SkillDiscovery] = []
        self._watchers: list[SkillWatcher] = []
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        for cfg in self.configs:
            discovery = SkillDiscovery(cfg)
            skills = discovery.discover()
            self._register_skills(skills)
            self._discoveries.append(discovery)

            if cfg.kind == "directory":
                watcher = SkillWatcher(cfg, self.hooks)
                self._watchers.append(watcher)
                task = asyncio.create_task(watcher.start(self._register_skills))
                self._tasks.append(task)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for watcher in self._watchers:
            watcher.stop()
        self._tasks.clear()
        self._watchers.clear()

    def _register_skills(self, skills: dict[str, SkillInfo]) -> None:
        for skill in skills.values():
            self.core.skill.register(skill)
            self.hooks.trigger(
                "skill", "registered", {"skill_id": skill.id.value, "path": skill.path}
            )


__all__ = [
    "DynamicSkillManager",
    "SkillDiscovery",
    "SkillInfo",
    "SkillSourceConfig",
    "SkillWatcher",
    "parse_skill_md",
]
