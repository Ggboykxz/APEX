"""Tests for apex/skills.py — SkillManager, DiffTool, SearchReplace, CodeAnalyzer."""

import pytest
from apex.skills import (
    Skill,
    SkillManager,
    DiffTool,
    SearchReplace,
    CodeAnalyzer,
    get_skill_manager,
)


class TestSkill:
    def test_creation(self):
        s = Skill(name="test", description="Test skill", prompt="You are a test assistant")
        assert s.name == "test"
        assert s.description == "Test skill"
        assert s.prompt == "You are a test assistant"
        assert s.args is None

    def test_with_args(self):
        s = Skill(name="test", description="desc", prompt="prompt", args=["arg1", "arg2"])
        assert s.args == ["arg1", "arg2"]


class TestSkillManager:
    @pytest.fixture
    def skills_dir(self, tmp_path):
        d = tmp_path / "skills"
        d.mkdir()
        return d

    def test_init(self, tmp_path):
        # Use tmp_path as cwd (may not have skills dirs)
        sm = SkillManager(str(tmp_path))
        assert sm.cwd == tmp_path

    def test_add_and_get(self, tmp_path):
        sm = SkillManager(str(tmp_path))
        sm.add("custom", "Custom skill", "You are a custom assistant")
        skill = sm.get("custom")
        assert skill is not None
        assert skill.name == "custom"
        assert skill.prompt == "You are a custom assistant"

    def test_get_nonexistent(self, tmp_path):
        sm = SkillManager(str(tmp_path))
        assert sm.get("nonexistent") is None

    def test_list_skills(self, tmp_path):
        sm = SkillManager(str(tmp_path))
        sm.add("skill1", "Skill 1", "prompt1")
        sm.add("skill2", "Skill 2", "prompt2")
        skills = sm.list_skills()
        assert len(skills) >= 2
        names = [s["name"] for s in skills]
        assert "skill1" in names
        assert "skill2" in names

    def test_render(self, tmp_path):
        sm = SkillManager(str(tmp_path))
        sm.add("greet", "Greeting", "Hello {person}, welcome to {place}!")
        result = sm.render("greet", person="Alice", place="Wonderland")
        assert result == "Hello Alice, welcome to Wonderland!"

    def test_render_nonexistent(self, tmp_path):
        sm = SkillManager(str(tmp_path))
        assert sm.render("nonexistent") is None

    def test_remove(self, tmp_path):
        sm = SkillManager(str(tmp_path))
        sm.add("to_remove", "desc", "prompt")
        result = sm.remove("to_remove")
        assert result is True
        assert sm.get("to_remove") is None

    def test_remove_nonexistent(self, tmp_path):
        sm = SkillManager(str(tmp_path))
        assert sm.remove("nonexistent") is False

    def test_load_skill_from_file(self, tmp_path):
        skills_dir = tmp_path / ".apex" / "skills"
        skills_dir.mkdir(parents=True)

        skill_file = skills_dir / "my_skill.md"
        skill_file.write_text(
            "# My Skill\n\n"
            "## Description: A custom skill\n\n"
            "## Prompt\n"
            "You are a helpful assistant for {task}\n"
        )

        sm = SkillManager(str(tmp_path))
        skill = sm.get("my_skill")
        assert skill is not None
        assert "helpful assistant" in skill.prompt

    def test_load_from_home_skills(self, tmp_path):
        # The home skills dir may or may not exist
        SkillManager(str(tmp_path))
        # Just ensure it doesn't crash


class TestDiffTool:
    @pytest.fixture
    def diff_tool(self, tmp_path):
        return DiffTool(str(tmp_path))

    def test_diff_identical(self, diff_tool, tmp_path):
        (tmp_path / "a.txt").write_text("hello\nworld\n")
        (tmp_path / "b.txt").write_text("hello\nworld\n")
        result = diff_tool.diff("a.txt", "b.txt")
        assert "identical" in result.lower() or result.strip() == ""

    def test_diff_different(self, diff_tool, tmp_path):
        (tmp_path / "a.txt").write_text("hello\n")
        (tmp_path / "b.txt").write_text("world\n")
        result = diff_tool.diff("a.txt", "b.txt")
        assert len(result) > 0

    def test_diff_nonexistent(self, diff_tool):
        result = diff_tool.diff("nonexistent1.txt", "nonexistent2.txt")
        assert "ERROR" in result or "not found" in result.lower()

    def test_three_way_diff(self, diff_tool, tmp_path):
        (tmp_path / "base.txt").write_text("line1\nline2\n")
        (tmp_path / "local.txt").write_text("line1\nline2\nlocal_change\n")
        (tmp_path / "remote.txt").write_text("line1\nline2\nremote_change\n")
        result = diff_tool.three_way_diff("base.txt", "local.txt", "remote.txt")
        assert isinstance(result, str)

    def test_three_way_diff_missing_file(self, diff_tool):
        result = diff_tool.three_way_diff("a.txt", "b.txt", "c.txt")
        assert "ERROR" in result or "not found" in result.lower()


class TestSearchReplace:
    @pytest.fixture
    def sr(self, tmp_path):
        return SearchReplace(str(tmp_path))

    def test_dry_run(self, sr, tmp_path):
        (tmp_path / "test.py").write_text("hello world\nhello python\n")
        result = sr.replace_in_files(r"hello", "hi", ["test.py"], dry_run=True)
        assert result["replacements"] == 2
        assert len(result["files_modified"]) > 0

    def test_actual_replace(self, sr, tmp_path):
        (tmp_path / "test.py").write_text("foo bar\nfoo baz\n")
        result = sr.replace_in_files(r"foo", "qux", ["test.py"], dry_run=False)
        assert result["replacements"] == 2
        content = (tmp_path / "test.py").read_text()
        assert "qux" in content

    def test_invalid_regex(self, sr):
        result = sr.replace_in_files(r"[invalid", "x", ["*.py"])
        assert "error" in result

    def test_no_matches(self, sr, tmp_path):
        (tmp_path / "test.py").write_text("hello world\n")
        result = sr.replace_in_files(r"xyz123", "abc", ["test.py"])
        assert result["replacements"] == 0


class TestCodeAnalyzer:
    @pytest.fixture
    def analyzer(self, tmp_path):
        return CodeAnalyzer(str(tmp_path))

    def test_analyze_file(self, analyzer, tmp_path):
        (tmp_path / "test.py").write_text(
            "import os\nimport sys\n\ndef hello():\n    pass\n\nclass Foo:\n    pass\n"
        )
        result = analyzer.analyze_file("test.py")
        assert result["lines"] > 0
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "hello"
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "Foo"
        assert "os" in result["imports"]

    def test_analyze_nonexistent(self, analyzer):
        result = analyzer.analyze_file("nonexistent.py")
        assert "error" in result

    def test_analyze_blank_lines(self, analyzer, tmp_path):
        (tmp_path / "test.py").write_text("x = 1\n\n\ny = 2\n# comment\n")
        result = analyzer.analyze_file("test.py")
        assert result["blank_lines"] >= 2
        assert result["comment_lines"] >= 1

    def test_explain_code(self, analyzer, tmp_path):
        (tmp_path / "test.py").write_text("def foo():\n    pass\n")
        result = analyzer.explain_code("test.py")
        assert "foo" in result

    def test_explain_nonexistent(self, analyzer):
        result = analyzer.explain_code("nonexistent.py")
        assert "not found" in result.lower() or "error" in result.lower()


class TestSkillEdgeCases:
    """Hit uncovered lines in skills.py."""

    def test_load_skills_from_dir_exception(self, tmp_path):
        """Hit lines 56-57 — exception during skill loading is caught."""
        skills_dir = tmp_path / ".apex" / "skills"
        skills_dir.mkdir(parents=True)
        bad_file = skills_dir / "bad.md"
        bad_file.write_bytes(b"\xff\xfe\x00\x01\x02")  # invalid UTF-8
        # Should not raise
        sm = SkillManager(str(tmp_path))

    def test_diff_second_file_not_found(self, tmp_path):
        """Hit line 102 — second file not found."""
        dt = DiffTool(str(tmp_path))
        (tmp_path / "a.txt").write_text("hello")
        result = dt.diff("a.txt", "nonexistent.txt")
        assert "ERROR" in result or "not found" in result.lower()

    def test_diff_subprocess_exception(self, tmp_path, monkeypatch):
        """Hit lines 109-110 — subprocess exception in diff."""
        import subprocess
        def broken_run(*a, **kw):
            raise RuntimeError("diff failed")
        monkeypatch.setattr(subprocess, "run", broken_run)
        dt = DiffTool(str(tmp_path))
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        result = dt.diff("a.txt", "b.txt")
        assert "ERROR" in result

    def test_three_way_diff_exception(self, tmp_path, monkeypatch):
        """Hit lines 129-130 — subprocess exception in three_way_diff."""
        import subprocess
        def broken_run(*a, **kw):
            raise RuntimeError("diff3 failed")
        monkeypatch.setattr(subprocess, "run", broken_run)
        dt = DiffTool(str(tmp_path))
        for f in ("base.txt", "local.txt", "remote.txt"):
            (tmp_path / f).write_text("content")
        result = dt.three_way_diff("base.txt", "local.txt", "remote.txt")
        assert "ERROR" in result

    def test_replace_in_files_skip_non_file(self, tmp_path):
        """Hit line 152 — skip non-file entries."""
        sr = SearchReplace(str(tmp_path))
        (tmp_path / "subdir").mkdir()
        # This glob will match the directory. rglob returns dirs too.
        result = sr.replace_in_files(r"hello", "hi", ["subdir"], dry_run=True)
        assert "error" not in result

    def test_replace_in_files_exception(self, tmp_path):
        """Hit lines 167-168 — file read error is caught."""
        sr = SearchReplace(str(tmp_path))
        f = tmp_path / "test.py"
        f.write_text("hello world")
        import stat
        f.chmod(0o000)  # no permissions
        result = sr.replace_in_files(r"hello", "hi", ["test.py"], dry_run=False)
        assert len(result.get("errors", [])) >= 1
        f.chmod(0o644)

    def test_analyze_file_exception(self, tmp_path):
        """Hit lines 215-216 — exception in analyze_file."""
        ca = CodeAnalyzer(str(tmp_path))
        import stat
        f = tmp_path / "bad.py"
        f.write_text("x = 1")
        f.chmod(0o000)  # no read permission
        result = ca.analyze_file("bad.py")
        assert "error" in result
        f.chmod(0o644)


class TestGetSkillManager:
    def test_returns_instance(self, tmp_path):
        sm = get_skill_manager(str(tmp_path))
        assert isinstance(sm, SkillManager)
