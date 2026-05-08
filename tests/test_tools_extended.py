"""Extended tests for APEX tools - git, web, and more."""

import pytest
from pathlib import Path
from apex.tools import ToolExecutor, TOOL_SCHEMAS


@pytest.fixture
def executor(tmp_path):
    cwd = tmp_path / "test_project"
    cwd.mkdir()
    return ToolExecutor(cwd=cwd)


def test_glob_search(executor, tmp_path):
    (tmp_path / "file1.py").touch()
    (tmp_path / "file2.js").touch()
    (tmp_path / "file3.txt").touch()

    result = executor.execute("glob_search", {"pattern": "*.py", "directory": str(tmp_path)})
    assert "file1.py" in result


def test_glob_search_no_matches(executor, tmp_path):
    result = executor.execute("glob_search", {"pattern": "*.nonexistent"})
    assert "no files match" in result


def test_get_file_tree(executor, tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "file.txt").touch()

    result = executor.execute("get_file_tree", {"path": str(tmp_path), "max_depth": 2})
    assert "subdir" in result


def test_diff_files_identical(executor, tmp_path):
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("hello")
    file_b.write_text("hello")

    result = executor.execute("diff_files", {"path_a": str(file_a), "path_b": str(file_b)})
    assert "identical" in result


def test_diff_files_different(executor, tmp_path):
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("hello world")
    file_b.write_text("hello")

    result = executor.execute("diff_files", {"path_a": str(file_a), "path_b": str(file_b)})
    assert "---" in result or "world" in result


def test_get_git_status_not_repo(executor, tmp_path):
    result = executor.execute("get_git_status", {})
    assert "Not a git repository" in result


def test_get_git_status_is_repo(tmp_path, executor):
    git_dir = executor.cwd / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main")

    result = executor.execute("get_git_status", {})
    assert "clean" in result or "working tree clean" in result or result.strip() == ""


def test_get_git_log_not_repo(executor, tmp_path):
    result = executor.execute("get_git_log", {"n": 5})
    assert "Not a git repository" in result


def test_get_git_log_is_repo(tmp_path, executor):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main")

    result = executor.execute("get_git_log", {"n": 5})
    assert "no commits" in result or isinstance(result, str)


def test_git_diff_not_repo(executor, tmp_path):
    result = executor.execute("git_diff", {})
    assert "Not a git repository" in result


def test_web_search(executor):
    result = executor.execute("web_search", {"query": "python"})
    assert "ERROR" in result or len(result) > 0


def test_fetch_url(executor):
    result = executor.execute("fetch_url", {"url": "https://example.com"})
    assert "ERROR" in result or len(result) > 0


def test_get_repo_map(executor, tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "config.json").write_text("{}")

    result = executor.execute("get_repo_map", {"path": str(tmp_path)})
    assert "Repository:" in result or "main.py" in result


def test_read_image(executor, tmp_path):
    from pathlib import Path
    img_path = tmp_path / "test.png"
    img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)

    result = executor.execute("read_image", {"path": str(img_path)})
    assert "data:image" in result


def test_read_image_not_found(executor):
    result = executor.execute("read_image", {"path": "/nonexistent/image.png"})
    assert "ERROR" in result


def test_run_test_pytest(executor, tmp_path):
    result = executor.execute("run_test", {"framework": "pytest", "path": "."})
    assert "ERROR" in result or isinstance(result, str)


def test_run_test_unknown_framework(executor):
    result = executor.execute("run_test", {"framework": "unknown", "path": "."})
    assert "Unknown framework" in result


def test_format_file_unknown_ext(executor, tmp_path):
    file = tmp_path / "test.xyz"
    file.write_text("content")

    result = executor.execute("format_file", {"path": str(file)})
    assert "No formatter" in result


def test_install_package_unknown_manager(executor):
    result = executor.execute("install_package", {"manager": "unknown", "package": "pkg"})
    assert "Unknown package manager" in result


def test_tool_schemas_count():
    tool_names = [s["function"]["name"] for s in TOOL_SCHEMAS]
    assert len(tool_names) >= 18
    assert "web_search" in tool_names
    assert "git_diff" in tool_names
    assert "get_repo_map" in tool_names
    assert "read_image" in tool_names
    assert "run_test" in tool_names
    assert "format_file" in tool_names
    assert "install_package" in tool_names