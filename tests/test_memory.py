"""Tests for APEX memory system."""

import pytest
from apex.memory import Memory


@pytest.fixture
def memory(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return Memory()


def test_memory_init(memory):
    assert isinstance(memory.get_all(), list)


def test_memory_add(memory):
    memory.add("Test fact", ["python", "project"])
    facts = memory.get_all()
    assert len(facts) == 1
    assert facts[0]["fact"] == "Test fact"
    assert "python" in facts[0]["relevance"]


def test_memory_get_relevant(memory):
    memory.add("Uses pytest for testing", ["python", "testing"])
    memory.add("Built with React", ["frontend", "javascript"])
    memory.add("Python web server", ["python", "web"])

    relevant = memory.get_relevant(["python"])
    assert len(relevant) == 2


def test_memory_get_context_for_prompt(memory):
    memory.add("Project uses FastAPI", ["myproject"])
    memory.add("Database is PostgreSQL", ["myproject"])

    context = memory.get_context_for_prompt("myproject")
    assert "MEMORY" in context
    assert "FastAPI" in context


def test_memory_clear(memory):
    memory.add("Test fact", ["test"])
    memory.clear()
    assert len(memory.get_all()) == 0


def test_memory_remove(memory):
    memory.add("Fact 1", ["a"])
    memory.add("Fact 2", ["b"])
    assert memory.remove(0) is True
    assert len(memory.get_all()) == 1


def test_memory_remove_invalid_index(memory):
    memory.add("Fact", ["a"])
    assert memory.remove(5) is False


def test_memory_list_facts(memory):
    memory.add("First fact", ["a"])
    memory.add("Second fact", ["b"])
    facts = memory.list_facts()
    assert len(facts) == 2
    assert "First fact" in facts


def test_memory_search(memory):
    memory.add("Python is great", ["python"])
    memory.add("JavaScript is fast", ["javascript"])
    results = memory.search("python")
    assert len(results) == 1
    assert "Python is great" in results[0]["fact"]
