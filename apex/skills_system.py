"""Skills and custom commands system for APEX."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _frontmatter_value(value: str) -> Any:
    """The value of a frontmatter entry, with its YAML scalar types."""
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value == "" or value == "null":
        return None
    return value


def _section_heading(line: str) -> str:
    """The kind of markdown heading the line carries."""
    if line.startswith("# "):
        return "title"
    if line.startswith("## Description"):
        return "description"
    if line.startswith("## Instructions"):
        return "instructions"
    if line.startswith("## "):
        return "other"
    return "text"


def _is_description_line(line: str) -> bool:
    """Whether the line can be the description of a flat skill."""
    if line.startswith("#"):
        return False
    return bool(line.strip())


@dataclass
class Skill:
    """Represents a skill/command definition."""

    name: str
    description: str
    instructions: str
    triggers: list[str] = field(default_factory=list)
    parameters: dict[str, str] = field(default_factory=dict)
    examples: list[str] = field(default_factory=list)


BUILTIN_SKILLS: dict[str, Skill] = {
    "refactor": Skill(
        name="refactor",
        description="Refactor code with AI assistance",
        instructions="""You are a refactoring expert. Analyze the code and suggest/implement improvements:
- Extract methods/functions
- Simplify complex logic
- Remove duplication
- Improve naming
- Add type hints where missing
- Apply design patterns where appropriate""",
        triggers=["refactor", "improve", "clean up"],
        parameters={"style": "modern"},
        examples=["refactor this function", "clean up this class"],
    ),
    "debug": Skill(
        name="debug",
        description="Debug and fix issues in code",
        instructions="""You are a debugging expert. Find and fix issues:
- Analyze error messages
- Add logging to trace execution
- Check for common issues (null, type errors, etc.)
- Write test cases to reproduce the bug
- Fix the root cause, not just symptoms""",
        triggers=["debug", "fix", "error", "issue", "bug"],
        parameters={"verbose": "true"},
        examples=["debug this error", "fix the crash"],
    ),
    "test": Skill(
        name="test",
        description="Write and run tests",
        instructions="""You are a testing expert. Create comprehensive tests:
- Write unit tests for new functionality
- Add integration tests for workflows
- Mock external dependencies
- Achieve good coverage
- Test edge cases""",
        triggers=["test", "spec", "verify"],
        parameters={"coverage": "80"},
        examples=["write tests for this", "add unit tests"],
    ),
    "review": Skill(
        name="review",
        description="Code review and security analysis",
        instructions="""You are a code reviewer. Analyze code for:
- Security vulnerabilities (SQL injection, XSS, etc.)
- Code quality and best practices
- Performance issues
- Memory leaks
- Race conditions
- Logic errors""",
        triggers=["review", "security", "check"],
        parameters={"depth": "detailed"},
        examples=["review this code", "check for bugs"],
    ),
    "explain": Skill(
        name="explain",
        description="Explain code and concepts",
        instructions="""You are a coding tutor. Explain clearly:
- What the code does
- How it works
- Why it's written that way
- Alternative approaches
- Usage examples""",
        triggers=["explain", "what does", "how does", "understand"],
        parameters={"verbosity": "detailed"},
        examples=["explain this function", "what is this"],
    ),
}


class SkillsManager:
    """Manages skills and custom commands.

    Loads skills from (later wins):
      1. Built-in skills
      2. ~/.claude/skills/<name>/SKILL.md  (Claude Code compat)
      3. .claude/skills/<name>/SKILL.md     (Claude Code project)
      4. ~/.config/opencode/skills/<name>/SKILL.md  (OpenCode compat)
      5. .opencode/skills/<name>/SKILL.md           (OpenCode project)
      6. ~/.config/apex/skills/<name>/SKILL.md
      7. .apex/skills/<name>/SKILL.md
      8. ~/.apex/skills/*.md (legacy flat format)
      9. .apex/skills/*.md (legacy flat format)
    """

    def __init__(self, skills_dir: Path | None = None):
        self.skills_dir = skills_dir or (Path.home() / ".apex" / "skills")
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._skills: dict[str, Skill] = {}
        self._custom_commands: dict[str, Callable] = {}
        self._load_builtin_skills()
        self._load_all_custom_skills()

    def _load_builtin_skills(self):
        """Load built-in skills."""
        self._skills = dict(BUILTIN_SKILLS)

    def _find_skill_dirs(self) -> list[Path]:
        cwd = Path.cwd()
        home = Path.home()
        dirs = [
            home / ".claude" / "skills",
            cwd / ".claude" / "skills",
            home / ".config" / "opencode" / "skills",
            cwd / ".opencode" / "skills",
            home / ".config" / "apex" / "skills",
            cwd / ".apex" / "skills",
            self.skills_dir,
        ]
        seen = set()
        result = []
        for d in dirs:
            resolved = d.resolve()
            if resolved not in seen:
                seen.add(resolved)
                result.append(d)
        return result

    def _parse_yaml_frontmatter(self, text: str) -> tuple[dict, str]:
        lines = text.split("\n")
        end = self._frontmatter_end(lines)
        if end == -1:
            return {}, text
        frontmatter_lines = lines[1:end]
        body = "\n".join(lines[end + 1 :]).strip()
        result = {}
        for line in frontmatter_lines:
            key, value = self._frontmatter_entry(line)
            if key is not None:
                result[key] = value
        return result, body

    @staticmethod
    def _frontmatter_end(lines: list[str]) -> int:
        """The index of the line that closes the frontmatter, or -1."""
        if not lines or lines[0].strip() != "---":
            return -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i
        return -1

    @staticmethod
    def _frontmatter_entry(line: str) -> tuple[str | None, Any]:
        """One ``key: value`` entry of a frontmatter block."""
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            return None, None
        if ":" not in stripped:
            return None, None
        key, _, val = stripped.partition(":")
        return key.strip(), _frontmatter_value(val.strip())

    def _load_all_custom_skills(self):
        seen_names: set[str] = set()
        for skills_dir in self._find_skill_dirs():
            if not skills_dir.is_dir():
                continue
            self._load_opencode_skills(skills_dir, seen_names)
            self._load_flat_skills(skills_dir, seen_names)

    def _load_opencode_skills(self, skills_dir: Path, seen_names: set[str]) -> None:
        """Load the OpenCode-format skills of one directory."""
        # OpenCode format: <name>/SKILL.md
        for sub in sorted(skills_dir.iterdir()):
            if not sub.is_dir():
                continue
            skill_file = sub / "SKILL.md"
            if not skill_file.is_file():
                continue
            skill = self._parse_skill_file_opencode(skill_file)
            if skill and skill.name not in seen_names:
                seen_names.add(skill.name)
                self._skills[skill.name] = skill

    def _load_flat_skills(self, skills_dir: Path, seen_names: set[str]) -> None:
        """Load the legacy flat skills of one directory."""
        # Legacy flat format: *.md
        for md_file in sorted(skills_dir.glob("*.md")):
            skill = self._parse_skill_file(md_file)
            if skill and skill.name not in seen_names:
                seen_names.add(skill.name)
                self._skills[skill.name] = skill

    def _parse_skill_file_opencode(self, filepath: Path) -> Skill | None:
        """Parse an OpenCode-style SKILL.md with YAML frontmatter."""
        try:
            content = filepath.read_text()
            frontmatter, body = self._parse_yaml_frontmatter(content)
            name = frontmatter.get("name", filepath.parent.stem)
            description = frontmatter.get("description", "")
            instructions = body or description
            if not name or not description:
                return None
            return Skill(
                name=str(name),
                description=str(description),
                instructions=instructions,
                triggers=[],
                parameters={},
                examples=[],
            )
        except Exception:  # noqa: BLE001
            return None

    def _parse_skill_file(self, filepath: Path) -> Skill | None:
        """Parse a legacy flat Markdown skill file."""
        try:
            content = filepath.read_text()
        except Exception:  # noqa: BLE001
            return None
        name, description, instructions = self._read_skill_sections(content.split("\n"), filepath)
        return Skill(
            name=name,
            description=description or filepath.stem,
            instructions=instructions.strip() or description,
            triggers=[],
            parameters={},
            examples=[],
        )

    def _read_skill_sections(self, lines: list[str], filepath: Path) -> tuple[str, str, str]:
        """The name, the description and the instructions of a flat skill."""
        name = filepath.stem
        description = ""
        instructions = ""
        in_instructions = False
        for line in lines:
            heading = _section_heading(line)
            if heading == "title":
                name = line[2:].strip()
                continue
            if heading == "instructions":
                in_instructions = True
                continue
            if heading == "other":
                in_instructions = False
            if in_instructions:
                instructions += line + "\n"
            elif _is_description_line(line) and not description:
                description = line.strip()
        return name, description, instructions

    def get_skill(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def find_skill(self, text: str) -> Skill | None:
        """Find a skill that matches the input."""
        text_lower = text.lower()

        for skill in self._skills.values():
            if any(trigger in text_lower for trigger in skill.triggers):
                return skill

            if skill.name in text_lower:
                return skill

        return None

    def list_skills(self) -> list[dict]:
        """List all available skills."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "triggers": s.triggers,
            }
            for s in self._skills.values()
        ]

    def create_skill_file(self, skill: Skill) -> Path:
        """Create an OpenCode-compatible SKILL.md for a skill."""
        skill_dir = self.skills_dir / skill.name
        skill_dir.mkdir(parents=True, exist_ok=True)
        filepath = skill_dir / "SKILL.md"

        content = f"""---
name: {skill.name}
description: {skill.description}
---

{skill.instructions}
"""
        filepath.write_text(content)
        self._skills[skill.name] = skill
        return filepath

    def delete_skill(self, name: str) -> bool:
        """Delete a custom skill."""
        if name in self._skills:
            del self._skills[name]
            filepath = self.skills_dir / f"{name}.md"
            if filepath.exists():
                filepath.unlink()
            return True
        return False


class CustomCommand:
    """Represents a custom command."""

    def __init__(
        self,
        name: str,
        handler: Callable[[list[str]], str],
        description: str = "",
        aliases: list[str] | None = None,
    ):
        self.name = name
        self.handler = handler
        self.description = description
        self.aliases = aliases or []


class CommandRegistry:
    """Registry for custom commands."""

    def __init__(self):
        self._commands: dict[str, CustomCommand] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register built-in custom commands."""

    def register(self, cmd: CustomCommand):
        """Register a command."""
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._commands[alias] = cmd

    def get(self, name: str) -> CustomCommand | None:
        """Get a command by name."""
        return self._commands.get(name)

    def execute(self, name: str, args: list[str]) -> str:
        """Execute a command."""
        cmd = self.get(name)
        if not cmd:
            return f"Unknown command: {name}"
        try:
            return cmd.handler(args)
        except Exception as e:  # noqa: BLE001
            return f"Error: {e}"

    def list_commands(self) -> list[dict]:
        """List all commands."""
        return [
            {"name": cmd.name, "description": cmd.description, "aliases": cmd.aliases}
            for cmd in self._commands.values()
        ]


skills_manager = SkillsManager()
command_registry = CommandRegistry()
