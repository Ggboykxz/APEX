"""Tests for refactored mentions module."""

from pathlib import Path

from apex.refactored_mentions import (
    FileMention,
    AgentMention,
    MentionParser,
    FileMentionCompleter,
    create_mention_parser,
    create_file_completer,
    DEFAULT_AGENT_NAMES,
)


class TestFileMention:
    def test_init(self):
        mention = FileMention("/path/file.txt", 0, 15)
        assert mention.path == "/path/file.txt"
        assert mention.start == 0
        assert mention.end == 15


class TestAgentMention:
    def test_init(self):
        mention = AgentMention("explore", 0, 7)
        assert mention.name == "explore"
        assert mention.start == 0
        assert mention.end == 7


class TestMentionParser:
    def test_init(self):
        parser = MentionParser("/workspace")
        assert parser.cwd == Path("/workspace")
        assert parser._agent_names == DEFAULT_AGENT_NAMES

    def test_init_custom_agents(self):
        parser = MentionParser("/workspace", agent_names={"custom"})
        assert "custom" in parser._agent_names

    def test_parse_file_mentions(self):
        parser = MentionParser("/workspace")
        text = "Check @README.md and @config.json"
        files, agents = parser.parse(text)

        assert len(files) == 2
        assert files[0].path == "README.md"
        assert files[1].path == "config.json"

    def test_parse_agent_mentions(self):
        parser = MentionParser("/workspace")
        text = "Ask @explore to check this"
        files, agents = parser.parse(text)

        assert len(agents) == 1
        assert agents[0].name == "explore"

    def test_parse_no_mentions(self):
        parser = MentionParser("/workspace")
        text = "Just some text without mentions"
        files, agents = parser.parse(text)

        assert len(files) == 0
        assert len(agents) == 0

    def test_parse_invalid_agent(self):
        parser = MentionParser("/workspace")
        text = "Ask @unknown to do something"
        files, agents = parser.parse(text)

        assert len(agents) == 0

    def test_parse_multiple_agents(self):
        parser = MentionParser("/workspace")
        text = "@explore and @build should work together"
        files, agents = parser.parse(text)

        assert len(agents) == 2

    def test_resolve_file_absolute(self):
        parser = MentionParser("/workspace")
        resolved = parser.resolve_file("/absolute/path.txt")
        assert resolved == Path("/absolute/path.txt")

    def test_resolve_file_relative(self):
        parser = MentionParser("/workspace")
        resolved = parser.resolve_file("relative/path.txt")
        assert resolved == Path("/workspace/relative/path.txt").resolve()

    def test_read_mentioned_files_with_reader(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("file content")

        parser = MentionParser(str(tmp_path))

        def mock_reader(path):
            if path.exists():
                return path.read_text()
            return None

        result = parser.read_mentioned_files("@test.txt", file_reader=mock_reader)

        assert "test.txt" in result
        assert result["test.txt"] == "file content"

    def test_read_mentioned_files_truncate(self, tmp_path):
        test_file = tmp_path / "large.txt"
        test_file.write_text("x" * 10000)

        parser = MentionParser(str(tmp_path))

        def mock_reader(path):
            if path.exists():
                return path.read_text()
            return None

        result = parser.read_mentioned_files("@large.txt", file_reader=mock_reader)

        assert len(result["large.txt"]) == 5000


class TestFileMentionCompleter:
    def test_init(self):
        completer = FileMentionCompleter("/workspace")
        assert completer.cwd == Path("/workspace")

    def test_complete_empty_prefix(self, tmp_path):
        completer = FileMentionCompleter(str(tmp_path))
        results = completer.complete("")
        assert results == []

    def test_complete_no_matches(self, tmp_path):
        completer = FileMentionCompleter(str(tmp_path))
        results = completer.complete("nonexistent_file_xyz")
        assert results == []

    def test_complete_with_matches(self, tmp_path):
        (tmp_path / "test_file.py").touch()
        (tmp_path / "another.py").touch()

        completer = FileMentionCompleter(str(tmp_path))
        results = completer.complete("test")

        assert "test_file.py" in results

    def test_complete_ignores_git_dir(self, tmp_path):
        git_dir = tmp_path / ".git" / "config"
        git_dir.parent.mkdir(parents=True)
        git_dir.touch()

        completer = FileMentionCompleter(str(tmp_path))
        results = completer.complete("")

        assert not any(".git" in r for r in results)

    def test_complete_ignores_node_modules(self, tmp_path):
        nm_dir = tmp_path / "node_modules" / "pkg" / "index.js"
        nm_dir.parent.mkdir(parents=True)
        nm_dir.touch()

        completer = FileMentionCompleter(str(tmp_path))
        results = completer.complete("")

        assert not any("node_modules" in r for r in results)

    def test_complete_limits_results(self, tmp_path):
        for i in range(25):
            (tmp_path / f"file{i}.txt").touch()

        completer = FileMentionCompleter(str(tmp_path))
        results = completer.complete("")

        assert len(results) <= 20

    def test_complete_with_rglob_mock(self, tmp_path):
        results = []

        def mock_rglob(pattern):
            return list(tmp_path.glob(pattern))

        completer = FileMentionCompleter(str(tmp_path), rglob_func=mock_rglob)
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.txt").touch()

        results = completer.complete("a")

        assert "a.txt" in results


class TestFactoryFunctions:
    def test_create_mention_parser(self):
        parser = create_mention_parser("/workspace")
        assert isinstance(parser, MentionParser)
        assert parser.cwd == Path("/workspace")

    def test_create_mention_parser_custom_agents(self):
        parser = create_mention_parser("/workspace", agent_names={"custom"})
        assert "custom" in parser._agent_names

    def test_create_file_completer(self):
        completer = create_file_completer("/workspace")
        assert isinstance(completer, FileMentionCompleter)
        assert completer.cwd == Path("/workspace")

    def test_create_file_completer_custom_ignored(self):
        completer = create_file_completer("/workspace", ignored_dirs={".custom"})
        assert ".custom" in completer._ignored_dirs
