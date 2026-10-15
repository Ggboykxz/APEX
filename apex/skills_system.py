"""Skills and custom commands system for APEX."""

from pathlib import Path
from typing import Callable
from dataclasses import dataclass, field


@dataclass
class Skill:
    """Represents a skill/command definition."""

    name: str
    description: str
    instructions: str
    triggers: list[str] = field(default_factory=list)
    parameters: dict[str, str] = field(default_factory=dict)
    examples: list[str] = field(default_factory=list)


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
        self._skills = {
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
        if not lines or lines[0].strip() != "---":
            return {}, text
        end = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end = i
                break
        if end == -1:
            return {}, text
        frontmatter_lines = lines[1:end]
        body = "\n".join(lines[end + 1 :]).strip()
        result = {}
        for line in frontmatter_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()
                if val.lower() in ("true", "false"):
                    val = val.lower() == "true"
                elif val == "" or val == "null":
                    val = None
                result[key] = val
        return result, body

    def _load_all_custom_skills(self):
        seen_names = set()
        for skills_dir in self._find_skill_dirs():
            if not skills_dir.is_dir():
                continue
            # OpenCode format: <name>/SKILL.md
            for sub in sorted(skills_dir.iterdir()):
                if sub.is_dir():
                    skill_file = sub / "SKILL.md"
                    if skill_file.is_file():
                        skill = self._parse_skill_file_opencode(skill_file)
                        if skill and skill.name not in seen_names:
                            seen_names.add(skill.name)
                            self._skills[skill.name] = skill
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
        except Exception:
            return None

    def _parse_skill_file(self, filepath: Path) -> Skill | None:
        """Parse a legacy flat Markdown skill file."""
        try:
            content = filepath.read_text()
            lines = content.split("\n")
            name = filepath.stem
            description = ""
            instructions = ""
            triggers = []
            parameters = {}
            examples = []

            in_instructions = False
            for line in lines:
                if line.startswith("# "):
                    name = line[2:].strip()
                elif line.startswith("## Description"):
                    continue
                elif line.startswith("## Instructions"):
                    in_instructions = True
                    continue
                elif line.startswith("## "):
                    in_instructions = False
                    if "Trigger" in line:
                        continue
                    if "Example" in line:
                        continue
                if in_instructions:
                    instructions += line + "\n"
                elif not line.startswith("#") and line.strip():
                    if not description:
                        description = line.strip()
            return Skill(
                name=name,
                description=description or filepath.stem,
                instructions=instructions.strip() or description,
                triggers=triggers,
                parameters=parameters,
                examples=examples,
            )
        except Exception:
            return None

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
        aliases: list[str] = None,
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
        pass

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
        except Exception as e:
            return f"Error: {e}"

    def list_commands(self) -> list[dict]:
        """List all commands."""
        return [
            {"name": cmd.name, "description": cmd.description, "aliases": cmd.aliases}
            for cmd in self._commands.values()
        ]


skills_manager = SkillsManager()
command_registry = CommandRegistry()
