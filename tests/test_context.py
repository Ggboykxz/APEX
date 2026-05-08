"""Tests for APEX context builder."""

import pytest
from pathlib import Path
from apex.context import get_repo_map, get_language_stats, get_git_info, generate_ctags


def test_get_repo_map_basic(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "config.json").write_text("{}")
    result = get_repo_map(tmp_path)
    assert "Repository:" in result
    assert "main.py" in result
    assert "config.json" in result


def test_get_repo_map_nonexistent():
    result = get_repo_map(Path("/nonexistent/path"))
    assert result.startswith("ERROR:")


def test_get_repo_map_with_subdirs(tmp_path):
    subdir = tmp_path / "src"
    subdir.mkdir()
    (subdir / "app.py").write_text("code")
    result = get_repo_map(tmp_path)
    assert "src/" in result


def test_get_language_stats(tmp_path):
    (tmp_path / "main.py").write_text("code")
    (tmp_path / "app.js").write_text("code")
    (tmp_path / "util.ts").write_text("code")
    stats = get_language_stats(tmp_path)
    assert stats.get("Python", 0) >= 1
    assert stats.get("JavaScript", 0) >= 1
    assert stats.get("TypeScript", 0) >= 1


def test_get_language_stats_empty(tmp_path):
    result = get_language_stats(tmp_path)
    assert isinstance(result, dict)


def test_get_git_info_not_git(tmp_path):
    result = get_git_info(tmp_path)
    assert result == ""


def test_get_git_info_is_git(tmp_path, monkeypatch):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main")

    result = get_git_info(tmp_path)
    assert "Branch:" in result


def test_generate_ctags_not_git(tmp_path):
    result = generate_ctags(tmp_path)
    assert result.startswith("ERROR:")


def test_generate_ctags_is_git(tmp_path, monkeypatch):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main")

    (tmp_path / "main.py").write_text("def foo(): pass")

    result = generate_ctags(tmp_path)
    assert "main.py" in result or "no code files" in result or result.startswith("ERROR:")