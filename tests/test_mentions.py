"""Tests for apex/mentions.py — MentionParser, FileMentionCompleter, singleton functions."""

import pytest
from pathlib import Path
from apex.mentions import (
    FileMention,
    AgentMention,
    MentionParser,
    FileMentionCompleter,
    get_mention_parser,
    get_file_completer,
)


class TestFileMention:
    def test_creation(self):
        fm = FileMention(path="test.py", start=0, end=8)
        assert fm.path == "test.py"
        assert fm.start == 0
        assert fm.end == 8


class TestAgentMention:
    def test_creation(self):
        am = AgentMention(name="build", start=0, end=6)
        assert am.name == "build"
        assert am.start == 0
        assert am.end == 6


class TestMentionParser:
    @pytest.fixture
    def parser(self, tmp_path):
        return MentionParser(str(tmp_path))

    def test_init(self, parser):
        assert parser.cwd is not None

    # --- parse() tests ---

    def test_parse_empty(self, parser):
        files, agents = parser.parse("")
        assert files == []
        assert agents == []

    def test_parse_no_mentions(self, parser):
        files, agents = parser.parse("hello world")
        assert files == []
        assert agents == []

    def test_parse_file_mention_py(self, parser):
        files, agents = parser.parse("check @file.py")
        assert len(files) == 1
        assert files[0].path == "file.py"
        assert agents == []

    def test_parse_file_mention_ts(self, parser):
        files, agents = parser.parse("@component.ts")
        assert len(files) == 1
        assert files[0].path == "component.ts"

    def test_parse_file_mention_js(self, parser):
        files, agents = parser.parse("@index.js")
        assert len(files) == 1
        assert files[0].path == "index.js"

    def test_parse_file_mention_relative(self, parser):
        files, agents = parser.parse("@src/utils/helper.py")
        assert len(files) == 1
        assert files[0].path == "src/utils/helper.py"

    def test_parse_file_mention_absolute(self, parser):
        files, agents = parser.parse("@/absolute/path/file.py")
        assert len(files) == 1
        assert files[0].path == "/absolute/path/file.py"

    def test_parse_file_mention_multi_dot(self, parser):
        files, agents = parser.parse("@file.min.js")
        assert len(files) == 1
        assert files[0].path == "file.min.js"

    def test_parse_agent_coder(self, parser):
        files, agents = parser.parse("hello @build")
        assert files == []
        assert len(agents) == 1
        assert agents[0].name == "build"

    def test_parse_agent_architect(self, parser):
        files, agents = parser.parse("@plan")
        assert len(agents) == 1
        assert agents[0].name == "plan"

    def test_parse_agent_planner(self, parser):
        files, agents = parser.parse("use @planner please")
        assert len(agents) == 1
        assert agents[0].name == "planner"

    def test_parse_agent_reviewer(self, parser):
        files, agents = parser.parse("hey @reviewer")
        assert len(agents) == 1
        assert agents[0].name == "reviewer"

    def test_parse_agent_shell(self, parser):
        files, agents = parser.parse("@shell run this")
        assert len(agents) == 1
        assert agents[0].name == "shell"

    def test_parse_agent_at_end_of_input(self, parser):
        files, agents = parser.parse("@build")
        assert len(agents) == 1
        assert agents[0].name == "build"

    def test_parse_agent_case_insensitive(self, parser):
        files, agents = parser.parse("@Build and @PLAN")
        assert len(agents) == 2
        names = {a.name for a in agents}
        assert names == {"build", "plan"}

    def test_parse_both_types(self, parser):
        files, agents = parser.parse("update @file.py with @build")
        assert len(files) == 1
        assert files[0].path == "file.py"
        assert len(agents) == 1
        assert agents[0].name == "build"

    def test_parse_multiple_files(self, parser):
        files, agents = parser.parse("@a.py @b.ts @c.js")
        assert len(files) == 3
        assert [f.path for f in files] == ["a.py", "b.ts", "c.js"]
        assert agents == []

    def test_parse_multiple_agents(self, parser):
        files, agents = parser.parse("@build and @plan then @planner")
        assert len(agents) == 3
        assert [a.name for a in agents] == ["build", "plan", "planner"]

    def test_parse_agent_not_in_list(self, parser):
        files, agents = parser.parse("@unknown")
        # Unknown agent name is treated as a file mention
        assert len(agents) == 0

    def test_parse_at_at_end_of_input(self, parser):
        files, agents = parser.parse("hello @")
        assert files == []
        assert agents == []

    def test_parse_double_at_no_dot(self, parser):
        files, agents = parser.parse("@@")
        assert files == []
        assert agents == []

    def test_parse_double_at_with_file(self, parser):
        files, agents = parser.parse("@@test.py")
        assert len(files) == 1

    def test_parse_at_in_middle_of_word_no_dot(self, parser):
        files, agents = parser.parse("hello@there")
        assert files == []

    def test_parse_at_in_middle_of_word_with_dot(self, parser):
        files, agents = parser.parse("checkout@file.py for details")
        assert len(files) == 1
        assert files[0].path == "file.py"

    def test_parse_positions(self, parser):
        files, agents = parser.parse("a @file.py b")
        assert len(files) == 1
        assert files[0].start == 2
        assert files[0].end == 10

    def test_parse_agent_positions(self, parser):
        files, agents = parser.parse("x @build y")
        assert len(agents) == 1
        assert agents[0].start == 2
        assert agents[0].end == 8

    # --- resolve_file() tests ---

    def test_resolve_relative(self, parser):
        resolved = parser.resolve_file("test.py")
        assert resolved == (parser.cwd / "test.py").resolve()

    def test_resolve_absolute(self, parser):
        resolved = parser.resolve_file("/tmp/test.py")
        assert resolved == Path("/tmp/test.py")

    def test_resolve_with_subdir(self, parser):
        resolved = parser.resolve_file("subdir/file.py")
        assert resolved == (parser.cwd / "subdir/file.py").resolve()

    # --- read_mentioned_files() tests ---

    def test_read_mentioned_no_mentions(self, parser):
        result = parser.read_mentioned_files("no mentions here")
        assert result == {}

    def test_read_mentioned_file_exists(self, parser, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("print('hello')")
        result = parser.read_mentioned_files("read @test.py")
        assert "test.py" in result
        assert result["test.py"] == "print('hello')"

    def test_read_mentioned_file_not_exist(self, parser):
        result = parser.read_mentioned_files("read @nonexistent.py")
        assert result == {}

    def test_read_mentioned_directory_with_dot(self, parser, tmp_path):
        (tmp_path / "my.dir").mkdir()
        result = parser.read_mentioned_files("read @my.dir")
        assert result == {}

    def test_read_mentioned_truncates_at_5000(self, parser, tmp_path):
        f = tmp_path / "big.py"
        content = "x" * 6000
        f.write_text(content)
        result = parser.read_mentioned_files("read @big.py")
        assert len(result["big.py"]) == 5000

    def test_read_mentioned_binary_file(self, parser, tmp_path):
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\xff\xfe\x00\x01")
        result = parser.read_mentioned_files("read @binary.bin")
        assert result == {}

    def test_read_mentioned_multiple_files(self, parser, tmp_path):
        (tmp_path / "a.py").write_text("aaa")
        (tmp_path / "b.py").write_text("bbb")
        result = parser.read_mentioned_files("read @a.py and @b.py")
        assert result["a.py"] == "aaa"
        assert result["b.py"] == "bbb"

    def test_read_mentioned_absolute_path(self, parser, tmp_path):
        f = tmp_path / "abs.py"
        f.write_text("absolute")
        result = parser.read_mentioned_files(f"read @{f}")
        assert list(result.keys())[0] == str(f)
        assert result[str(f)] == "absolute"


class TestFileMentionCompleter:
    @pytest.fixture
    def completer(self, tmp_path):
        return FileMentionCompleter(str(tmp_path))

    def test_init(self, completer):
        assert completer.cwd is not None

    def test_complete_empty_prefix(self, completer):
        assert completer.complete("") == []

    def test_complete_no_matches(self, completer):
        assert completer.complete("nonexistent") == []

    def test_complete_matches_py(self, completer, tmp_path):
        (tmp_path / "file.py").write_text("")
        results = completer.complete("file")
        assert "file.py" in results

    def test_complete_matches_ts(self, completer, tmp_path):
        (tmp_path / "file.ts").write_text("")
        results = completer.complete("file")
        assert "file.ts" in results

    def test_complete_matches_js(self, completer, tmp_path):
        (tmp_path / "file.js").write_text("")
        results = completer.complete("file")
        assert "file.js" in results

    def test_complete_with_subdirs(self, completer, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "helper.py").write_text("")
        results = completer.complete("helper")
        assert "subdir/helper.py" in results

    def test_complete_limit_20(self, completer, tmp_path):
        for i in range(25):
            (tmp_path / f"file{i}.py").write_text("")
        results = completer.complete("file")
        assert len(results) == 20

    def test_complete_no_results(self, completer):
        assert completer.complete("zzz_no_match_xyz") == []

    def test_is_ignored_git(self, completer):
        p = Path("/tmp/.git/config")
        assert completer._is_ignored(p) is True

    def test_is_ignored_node_modules(self, completer):
        p = Path("/tmp/node_modules/pkg/index.js")
        assert completer._is_ignored(p) is True

    def test_is_ignored_pycache(self, completer):
        p = Path("/tmp/__pycache__/mod.pyc")
        assert completer._is_ignored(p) is True

    def test_is_ignored_venv(self, completer):
        p = Path("/tmp/venv/bin/python")
        assert completer._is_ignored(p) is True

    def test_is_ignored_dot_venv(self, completer):
        p = Path("/tmp/.venv/bin/python")
        assert completer._is_ignored(p) is True

    def test_is_ignored_target(self, completer):
        p = Path("/tmp/target/debug/app")
        assert completer._is_ignored(p) is True

    def test_is_ignored_dist(self, completer):
        p = Path("/tmp/dist/bundle.js")
        assert completer._is_ignored(p) is True

    def test_is_ignored_build(self, completer):
        p = Path("/tmp/build/output.o")
        assert completer._is_ignored(p) is True

    def test_is_ignored_pytest_cache(self, completer):
        p = Path("/tmp/.pytest_cache/data")
        assert completer._is_ignored(p) is True

    def test_is_not_ignored_normal(self, completer):
        p = Path("/tmp/src/main.py")
        assert completer._is_ignored(p) is False

    def test_complete_ignores_ignored_dirs(self, completer, tmp_path):
        (tmp_path / "node_modules" / "pkg" / "index.js").parent.mkdir(parents=True)
        (tmp_path / "node_modules" / "pkg" / "index.js").write_text("")
        (tmp_path / "src" / "index.js").parent.mkdir(parents=True)
        (tmp_path / "src" / "index.js").write_text("")
        results = completer.complete("index")
        assert "src/index.js" in results
        assert "node_modules/pkg/index.js" not in results


class TestGetMentionParser:
    def test_returns_instance(self):
        parser = get_mention_parser("/tmp")
        assert isinstance(parser, MentionParser)

    def test_overwrites_global(self):
        import apex.mentions as mod

        mod._mention_parser = None
        p1 = get_mention_parser("/tmp")
        p2 = get_mention_parser("/other")
        assert p1 is not p2
        assert p2.cwd == Path("/other")


class TestGetFileCompleter:
    def test_returns_instance(self):
        completer = get_file_completer("/tmp")
        assert isinstance(completer, FileMentionCompleter)

    def test_overwrites_global(self):
        import apex.mentions as mod

        mod._file_completer = None
        c1 = get_file_completer("/tmp")
        c2 = get_file_completer("/other")
        assert c1 is not c2
        assert c2.cwd == Path("/other")
