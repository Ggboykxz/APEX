"""Tests for APEX memory system — no mocks, real file system via monkeypatch."""

import json
from pathlib import Path

import pytest

from apex.memory import Memory


@pytest.fixture
def memory(tmp_path, monkeypatch):
    """Create a Memory instance that stores files in a temp directory."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return Memory()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestMemoryInit:
    def test_init_empty(self, memory):
        assert isinstance(memory.get_all(), list)
        assert len(memory.get_all()) == 0

    def test_init_loads_existing(self, tmp_path, monkeypatch):
        """Memory loads existing facts from file."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # Pre-create the memory file
        mem_dir = tmp_path / ".apex"
        mem_dir.mkdir()
        mem_file = mem_dir / "memory.json"
        mem_file.write_text(
            json.dumps([{"fact": "saved fact", "added": "2024-01-01", "relevance": []}])
        )
        mem = Memory()
        assert len(mem.get_all()) == 1
        assert mem.get_all()[0]["fact"] == "saved fact"

    def test_init_handles_corrupt_json(self, tmp_path, monkeypatch):
        """Memory handles corrupt JSON gracefully."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        mem_dir = tmp_path / ".apex"
        mem_dir.mkdir()
        mem_file = mem_dir / "memory.json"
        mem_file.write_text("{invalid json")
        mem = Memory()
        assert mem.get_all() == []


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


class TestMemoryAdd:
    def test_add_basic(self, memory):
        memory.add("Test fact", ["python", "project"])
        facts = memory.get_all()
        assert len(facts) == 1
        assert facts[0]["fact"] == "Test fact"
        assert "python" in facts[0]["relevance"]

    def test_add_no_relevance(self, memory):
        memory.add("No tags")
        facts = memory.get_all()
        assert facts[0]["relevance"] == []

    def test_add_persists_to_disk(self, memory, tmp_path):
        memory.add("Persisted fact", ["test"])
        mem_file = tmp_path / ".apex" / "memory.json"
        assert mem_file.exists()
        data = json.loads(mem_file.read_text())
        assert len(data) == 1
        assert data[0]["fact"] == "Persisted fact"

    def test_add_sets_timestamp(self, memory):
        memory.add("Timestamped")
        facts = memory.get_all()
        assert "added" in facts[0]
        assert len(facts[0]["added"]) > 0


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------


class TestMemoryGetAll:
    def test_returns_copy(self, memory):
        memory.add("Fact", [])
        result = memory.get_all()
        result.append({"fact": "extra"})
        assert len(memory.get_all()) == 1


# ---------------------------------------------------------------------------
# get_relevant
# ---------------------------------------------------------------------------


class TestMemoryGetRelevant:
    def test_get_relevant(self, memory):
        memory.add("Uses pytest for testing", ["python", "testing"])
        memory.add("Built with React", ["frontend", "javascript"])
        memory.add("Python web server", ["python", "web"])

        relevant = memory.get_relevant(["python"])
        assert len(relevant) == 2

    def test_get_relevant_no_match(self, memory):
        memory.add("Uses pytest", ["python"])
        relevant = memory.get_relevant(["rust"])
        assert len(relevant) == 0

    def test_get_relevant_empty_keywords(self, memory):
        memory.add("Fact", ["tag"])
        relevant = memory.get_relevant([])
        assert len(relevant) == 0

    def test_get_relevant_no_relevance_tags(self, memory):
        memory.add("Fact without tags", [])
        relevant = memory.get_relevant(["python"])
        assert len(relevant) == 0


# ---------------------------------------------------------------------------
# get_context_for_prompt
# ---------------------------------------------------------------------------


class TestMemoryGetContextForPrompt:
    def test_with_matching_project(self, memory):
        memory.add("Project uses FastAPI", ["myproject"])
        memory.add("Database is PostgreSQL", ["myproject"])

        context = memory.get_context_for_prompt("myproject")
        assert "MEMORY" in context
        assert "FastAPI" in context

    def test_no_matching_project(self, memory):
        memory.add("Some fact", ["otherproject"])
        context = memory.get_context_for_prompt("myproject")
        assert context == ""

    def test_no_project_name(self, memory):
        memory.add("Generic fact", [])
        context = memory.get_context_for_prompt("")
        assert context == ""

    def test_limits_to_five_facts(self, memory):
        for i in range(8):
            memory.add(f"Fact {i}", ["project"])
        context = memory.get_context_for_prompt("project")
        assert "MEMORY" in context
        # Should contain last 5 facts
        assert "Fact 7" in context


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


class TestMemoryClear:
    def test_clear(self, memory):
        memory.add("Test fact", ["test"])
        memory.clear()
        assert len(memory.get_all()) == 0

    def test_clear_persists(self, memory, tmp_path):
        memory.add("Test fact", ["test"])
        memory.clear()
        mem_file = tmp_path / ".apex" / "memory.json"
        data = json.loads(mem_file.read_text())
        assert data == []


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------


class TestMemoryRemove:
    def test_remove_valid_index(self, memory):
        memory.add("Fact 1", ["a"])
        memory.add("Fact 2", ["b"])
        assert memory.remove(0) is True
        assert len(memory.get_all()) == 1
        assert memory.get_all()[0]["fact"] == "Fact 2"

    def test_remove_last_index(self, memory):
        memory.add("Fact 1", ["a"])
        memory.add("Fact 2", ["b"])
        assert memory.remove(1) is True
        assert len(memory.get_all()) == 1
        assert memory.get_all()[0]["fact"] == "Fact 1"

    def test_remove_negative_index(self, memory):
        memory.add("Fact", ["a"])
        assert memory.remove(-1) is False

    def test_remove_out_of_range(self, memory):
        memory.add("Fact", ["a"])
        assert memory.remove(5) is False

    def test_remove_empty_list(self, memory):
        assert memory.remove(0) is False

    def test_remove_persists(self, memory, tmp_path):
        memory.add("Fact 1", ["a"])
        memory.add("Fact 2", ["b"])
        memory.remove(0)
        mem_file = tmp_path / ".apex" / "memory.json"
        data = json.loads(mem_file.read_text())
        assert len(data) == 1


# ---------------------------------------------------------------------------
# list_facts
# ---------------------------------------------------------------------------


class TestMemoryListFacts:
    def test_list_facts(self, memory):
        memory.add("First fact", ["a"])
        memory.add("Second fact", ["b"])
        facts = memory.list_facts()
        assert len(facts) == 2
        assert "First fact" in facts
        assert "Second fact" in facts

    def test_list_facts_empty(self, memory):
        facts = memory.list_facts()
        assert facts == []


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestMemorySearch:
    def test_search_finds_match(self, memory):
        memory.add("Python is great", ["python"])
        memory.add("JavaScript is fast", ["javascript"])
        results = memory.search("python")
        assert len(results) == 1
        assert "Python is great" in results[0]["fact"]

    def test_search_case_insensitive(self, memory):
        memory.add("PYTHON IS LOUD", [])
        results = memory.search("python")
        assert len(results) == 1

    def test_search_no_match(self, memory):
        memory.add("Hello", [])
        results = memory.search("xyz")
        assert len(results) == 0

    def test_search_empty_memory(self, memory):
        results = memory.search("anything")
        assert len(results) == 0

    def test_search_partial_match(self, memory):
        memory.add("The Python programming language", ["python"])
        results = memory.search("program")
        assert len(results) == 1


# ---------------------------------------------------------------------------
# _save
# ---------------------------------------------------------------------------


class TestMemorySave:
    def test_save_creates_directory(self, tmp_path, monkeypatch):
        """_save creates .apex directory if missing."""
        home = tmp_path / "newhome"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        mem = Memory()
        mem.add("test")
        assert (home / ".apex" / "memory.json").exists()
