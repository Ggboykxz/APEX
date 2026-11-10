"""Rule and instruction loading for the APEX agent.

Split out of ``apex.agent`` so that module keeps a single responsibility: the
chat loop itself. The mixin expects its host class to expose a ``cwd``
property pointing at the working directory.
"""

from __future__ import annotations

from pathlib import Path

from . import config_v2

__all__ = ["RulesMixin"]


class RulesMixin:
    """Assemble the instruction blocks handed to the model.

    Three sources, in order: project rules, global rules, and custom
    instructions (remote URLs and local glob patterns).
    """

    def _load_rules(self) -> str:
        """Assemble the instruction blocks handed to the model."""
        parts = [
            *self._load_project_rules(),
            *self._load_global_rules(),
            *self._load_custom_instructions(),
        ]
        return "\n\n".join(parts) if parts else ""

    def _load_project_rules(self) -> list[str]:
        """Project-level rules: AGENTS.md or CLAUDE.md in the working dir."""
        project_dir = self.cwd
        for name in ("AGENTS.md", "CLAUDE.md"):
            path = project_dir / name
            if path.is_file():
                content = path.read_text(encoding="utf-8", errors="replace").strip()
                if content:
                    return [f"## {name} (project rules)\n{content}"]
                break
        return []

    def _load_global_rules(self) -> list[str]:
        """Global rules: ~/.config/apex/AGENTS.md or ~/.claude/CLAUDE.md."""
        global_rules = Path.home() / ".config" / "apex" / "AGENTS.md"
        if not global_rules.is_file():
            global_rules = Path.home() / ".claude" / "CLAUDE.md"
        if not global_rules.is_file():
            return []
        content = global_rules.read_text(encoding="utf-8", errors="replace").strip()
        if not content:
            return []
        return [f"## {global_rules.name} (global rules)\n{content}"]

    def _load_custom_instructions(self) -> list[str]:
        """Custom instructions from config: remote URLs and local globs."""
        parts: list[str] = []
        project_dir = self.cwd
        for instr in config_v2.apex_config.instructions:
            if instr.startswith(("http://", "https://")):
                parts.extend(self._load_remote_instructions(instr))
                continue
            parts.extend(self._load_glob_instructions(instr, project_dir))
        return parts

    def _load_remote_instructions(self, url: str) -> list[str]:
        """Fetch one instruction block over HTTPS. Failures are ignored."""
        try:
            import ssl
            import urllib.request

            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, headers={"User-Agent": "APEX/1.0"})
            resp = urllib.request.urlopen(req, timeout=5, context=ctx)
            content = resp.read().decode("utf-8", errors="replace").strip()
        except Exception:  # noqa: BLE001
            return []
        if not content:
            return []
        return [f"## Instructions from {url}\n{content}"]

    def _glob_matches(self, pattern: str, project_dir: Path) -> list[Path]:
        """Resolve one glob pattern to a list of candidate paths."""
        path = Path(pattern)
        if path.is_absolute():
            parent = path.parent
            if not parent.is_dir():
                return []
            return list(parent.glob(path.name))

        matches = list(project_dir.glob(pattern))
        if not matches:
            matches = list(Path.cwd().glob(pattern))
        return matches

    def _load_glob_instructions(self, pattern: str, project_dir: Path) -> list[str]:
        """Expand one glob pattern into instruction blocks."""
        parts: list[str] = []
        for match in self._glob_matches(pattern, project_dir):
            if not match.is_file():
                continue
            content = match.read_text(encoding="utf-8", errors="replace").strip()
            if content:
                parts.append(f"## Instructions from {match}\n{content}")
        return parts
