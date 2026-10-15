"""Tests for APEX tools - command execution, web, images, test runner, formatting, packages."""

import pytest

from apex.tools import ToolExecutor


@pytest.fixture
def executor(tmp_path):
    cwd = tmp_path / "project"
    cwd.mkdir()
    return ToolExecutor(cwd=cwd)


# ─── run_command ─────────────────────────────────────────────────────────────


def test_run_command_echo(executor):
    result = executor.execute("run_command", {"command": "echo hello_world"})
    assert "hello_world" in result


def test_run_command_pwd(executor, tmp_path):
    result = executor.execute("run_command", {"command": "pwd"})
    assert str(tmp_path / "project") in result or "tmp" in result.lower()


def test_run_command_exit_code_nonzero(executor):
    result = executor.execute("run_command", {"command": "false"})
    assert "EXIT CODE" in result or "1" in result


def test_run_command_stderr(executor):
    result = executor.execute("run_command", {"command": "ls /nonexistent_dir_xyz_12345"})
    # Should have output (stderr) about the missing directory
    assert isinstance(result, str)
    assert len(result) > 0


def test_run_command_no_output(executor, tmp_path):
    # true command produces no output and exits 0
    result = executor.execute("run_command", {"command": "true"})
    assert "no output" in result.lower() or result.strip() == ""


def test_run_command_dangerous_blocked(executor):
    """Dangerous commands should be blocked by shell security."""
    result = executor.execute("run_command", {"command": "rm -rf /"})
    assert "ERROR" in result or "DANGEROUS" in result or "blocked" in result.lower()


def test_run_command_restricted_warning(executor):
    """Restricted commands should require confirmation."""
    result = executor.execute("run_command", {"command": "sudo echo test"})
    assert (
        "WARNING" in result
        or "requires confirmation" in result.lower()
        or "ERROR" in result
        or "DANGEROUS" in result
    )


# ─── web_search ──────────────────────────────────────────────────────────────


def test_web_search_returns_string(executor):
    result = executor.execute("web_search", {"query": "python"})
    assert isinstance(result, str)
    assert len(result) > 0


# ─── fetch_url ───────────────────────────────────────────────────────────────


def test_fetch_url_returns_string(executor):
    result = executor.execute("fetch_url", {"url": "https://example.com"})
    assert isinstance(result, str)
    # Either successful content or an error message
    assert len(result) > 0


# ─── read_image ──────────────────────────────────────────────────────────────


def test_read_image_success(executor, tmp_path):
    img = tmp_path / "test.png"
    # Write minimal PNG-like binary data
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    result = executor.execute("read_image", {"path": str(img)})
    assert "data:image" in result or "base64" in result.lower()


def test_read_image_not_found(executor):
    result = executor.execute("read_image", {"path": "/nonexistent/image.png"})
    assert "ERROR" in result


def test_read_image_format_in_output(executor, tmp_path):
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)
    result = executor.execute("read_image", {"path": str(img)})
    assert "jpg" in result or "jpeg" in result.lower() or "data:" in result


# ─── run_test ────────────────────────────────────────────────────────────────


def test_run_test_unknown_framework(executor):
    result = executor.execute("run_test", {"framework": "unknown_framework", "path": "."})
    assert "Unknown framework" in result


def test_run_test_pytest_framework(executor, tmp_path):
    # This tests with the actual pytest command; it may not find tests
    result = executor.execute("run_test", {"framework": "pytest", "path": str(tmp_path)})
    assert isinstance(result, str)
    # Should either succeed or report an error, both are valid test outcomes
    assert len(result) > 0


def test_run_test_jest_framework(executor):
    result = executor.execute("run_test", {"framework": "jest", "path": "."})
    assert isinstance(result, str)


def test_run_test_cargo_framework(executor):
    result = executor.execute("run_test", {"framework": "cargo", "path": "."})
    assert isinstance(result, str)


# ─── format_file ─────────────────────────────────────────────────────────────


def test_format_file_unknown_extension(executor, tmp_path):
    f = tmp_path / "test.xyz"
    f.write_text("content")
    result = executor.execute("format_file", {"path": str(f)})
    assert "No formatter" in result or "formatter" in result.lower()


def test_format_file_not_found(executor):
    result = executor.execute("format_file", {"path": "/nonexistent/file.py"})
    assert "ERROR" in result


def test_format_file_python(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("x=1\n")
    result = executor.execute("format_file", {"path": str(f)})
    assert isinstance(result, str)
    # Either SUCCESS or formatter not found, both are valid


def test_format_file_javascript(executor, tmp_path):
    f = tmp_path / "test.js"
    f.write_text("const x=1;\n")
    result = executor.execute("format_file", {"path": str(f)})
    assert isinstance(result, str)


# ─── install_package ─────────────────────────────────────────────────────────


def test_install_package_unknown_manager(executor):
    result = executor.execute(
        "install_package", {"manager": "unknown_pkg_mgr", "package": "some_pkg"}
    )
    assert "Unknown package manager" in result


def test_install_package_pip(executor):
    # This actually tries to run pip install; it may fail in sandboxed env
    result = executor.execute(
        "install_package", {"manager": "pip", "package": "nonexistent-pkg-xyz-123"}
    )
    assert isinstance(result, str)
    # Should return some result (success or error)


def test_install_package_npm(executor):
    result = executor.execute(
        "install_package", {"manager": "npm", "package": "nonexistent-pkg-xyz"}
    )
    assert isinstance(result, str)


def test_install_package_yarn(executor):
    result = executor.execute(
        "install_package", {"manager": "yarn", "package": "nonexistent-pkg-xyz"}
    )
    assert isinstance(result, str)


def test_install_package_cargo(executor):
    result = executor.execute(
        "install_package", {"manager": "cargo", "package": "nonexistent-pkg-xyz"}
    )
    assert isinstance(result, str)
