"""Skills system for APEX - reusable prompt templates."""

from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Skill:
    name: str
    description: str
    prompt: str
    args: list[str] = None


class SkillManager:
    def __init__(self, cwd: str):
        self.cwd = Path(cwd)
        self._skills: Dict[str, Skill] = {}
        self._load_skills()

    def _load_skills(self):
        skill_dirs = [
            self.cwd / ".apex" / "skills",
            Path.home() / ".apex" / "skills",
        ]

        for skill_dir in skill_dirs:
            if not skill_dir.exists():
                continue

            for file in skill_dir.glob("*.md"):
                self._load_skill_file(file)

    def _load_skill_file(self, filepath: Path):
        try:
            content = filepath.read_text()
            lines = content.strip().split("\n")

            name = filepath.stem
            description = ""
            prompt_lines = []
            in_prompt = False

            for line in lines:
                if line.startswith("## Description:"):
                    description = line.split(":", 1)[1].strip()
                elif line.strip() == "## Prompt":
                    in_prompt = True
                elif in_prompt:
                    prompt_lines.append(line)

            prompt = "\n".join(prompt_lines).strip()
            if prompt:
                self._skills[name] = Skill(name, description, prompt)
        except Exception:
            pass

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def list_skills(self) -> list[dict[str, str]]:
        return [
            {"name": skill.name, "description": skill.description}
            for skill in self._skills.values()
        ]

    def render(self, name: str, **kwargs) -> Optional[str]:
        skill = self.get(name)
        if not skill:
            return None

        result = skill.prompt
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))

        return result

    def add(self, name: str, description: str, prompt: str):
        self._skills[name] = Skill(name, description, prompt)

    def remove(self, name: str) -> bool:
        if name in self._skills:
            del self._skills[name]
            return True
        return False


class DiffTool:
    def __init__(self, cwd: str):
        self.cwd = Path(cwd)

    def diff(self, path1: str, path2: str) -> str:
        import subprocess

        p1 = self.cwd / path1
        p2 = self.cwd / path2

        if not p1.exists():
            return f"ERROR: File not found: {path1}"
        if not p2.exists():
            return f"ERROR: File not found: {path2}"

        try:
            result = subprocess.run(
                ["diff", "-u", str(p1), str(p2)], capture_output=True, text=True
            )
            return result.stdout if result.stdout else "Files are identical"
        except Exception as e:
            return f"ERROR: {e}"

    def three_way_diff(self, base: str, local: str, remote: str) -> str:
        import subprocess

        b = self.cwd / base
        local_path = self.cwd / local
        r = self.cwd / remote

        if not all(p.exists() for p in [b, local_path, r]):
            return "ERROR: One or more files not found"

        try:
            result = subprocess.run(
                ["diff3", "-m", "-E", str(b), str(local_path), str(r)],
                capture_output=True,
                text=True,
            )
            return result.stdout if result.stdout else "No conflicts"
        except Exception as e:
            return f"ERROR: {e}"


class SearchReplace:
    def __init__(self, cwd: str):
        self.cwd = Path(cwd)

    def replace_in_files(
        self, pattern: str, replacement: str, patterns: list[str], dry_run: bool = True
    ) -> Dict[str, Any]:
        import re

        results = {"files_modified": [], "replacements": 0, "errors": []}

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return {"error": f"Invalid regex: {e}"}

        for glob_pattern in patterns:
            for filepath in self.cwd.rglob(glob_pattern):
                if not filepath.is_file():
                    continue

                try:
                    content = filepath.read_text()
                    new_content, count = regex.subn(replacement, content)

                    if count > 0:
                        results["replacements"] += count
                        if not dry_run:
                            filepath.write_text(new_content)
                            results["files_modified"].append(str(filepath.relative_to(self.cwd)))
                        else:
                            results["files_modified"].append(
                                f"{filepath.relative_to(self.cwd)} ({count} replacements)"
                            )
                except Exception as e:
                    results["errors"].append(f"{filepath}: {e}")

        return results


class CodeAnalyzer:
    def __init__(self, cwd: str):
        self.cwd = Path(cwd)

    def analyze_file(self, path: str) -> Dict[str, Any]:
        filepath = self.cwd / path
        if not filepath.exists():
            return {"error": "File not found"}

        try:
            content = filepath.read_text()
            lines = content.split("\n")

            analysis = {
                "path": path,
                "lines": len(lines),
                "blank_lines": sum(1 for ln in lines if not ln.strip()),
                "code_lines": sum(
                    1 for ln in lines if ln.strip() and not ln.strip().startswith("#")
                ),
                "comment_lines": sum(1 for ln in lines if ln.strip().startswith("#")),
                "functions": [],
                "classes": [],
                "imports": [],
            }

            import re

            func_pattern = re.compile(r"^(\s*)def\s+(\w+)\s*\(")
            class_pattern = re.compile(r"^class\s+(\w+)")
            import_pattern = re.compile(r"^import\s+(\S+)|^from\s+(\S+)\s+import")

            for i, line in enumerate(lines, 1):
                if func_match := func_pattern.match(line):
                    analysis["functions"].append({"name": func_match.group(2), "line": i})
                if class_match := class_pattern.match(line):
                    analysis["classes"].append({"name": class_match.group(1), "line": i})
                if import_match := import_pattern.match(line):
                    imp = import_match.group(1) or import_match.group(2)
                    analysis["imports"].append(imp)

            return analysis
        except Exception as e:
            return {"error": str(e)}

    def explain_code(self, path: str, start_line: int = 1, end_line: int = None) -> str:
        analysis = self.analyze_file(path)
        if "error" in analysis:
            return analysis["error"]

        lines = analysis["lines"]
        if end_line is None:
            end_line = lines

        return f"""File: {path}
Lines: {lines} (showing {start_line}-{end_line})

Summary:
- {analysis["functions"]} functions defined
- {analysis["classes"]} classes defined
- {analysis["imports"]} imports

Functions: {", ".join(f["name"] for f in analysis["functions"])}
Classes: {", ".join(c["name"] for c in analysis["classes"])}
Imports: {", ".join(analysis["imports"][:10])}
"""


_skill_manager: Optional[SkillManager] = None


def get_skill_manager(cwd: str) -> SkillManager:
    global _skill_manager
    _skill_manager = SkillManager(cwd)
    return _skill_manager
