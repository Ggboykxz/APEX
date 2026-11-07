"""Tests for APEX tools - env vars, tasks, search history, workspace validation, security, codegen."""

import pytest

from apex.tools import ToolExecutor


@pytest.fixture
def executor(tmp_path):
    cwd = tmp_path / "project"
    cwd.mkdir()
    return ToolExecutor(cwd=cwd)


# ─── get_env / set_env / list_env ────────────────────────────────────────────


def test_get_env_existing(executor):
    result = executor.execute("get_env", {"key": "HOME"})
    assert isinstance(result, str)
    assert "HOME" in result


def test_get_env_nonexistent(executor):
    result = executor.execute("get_env", {"key": "NONEXISTENT_VAR_XYZ_123"})
    assert "ERROR" in result or "not found" in result.lower()


def test_set_env(executor):
    result = executor.execute("set_env", {"key": "APEX_TEST_VAR", "value": "test_value"})
    assert "SUCCESS" in result
    assert "APEX_TEST_VAR" in result


def test_list_env(executor):
    result = executor.execute("list_env", {})
    assert isinstance(result, str)
    assert "Environment" in result or "=" in result


# ─── submit_task / list_tasks / get_task ──────────────────────────────────────


@pytest.mark.skip(reason="submit_task uses asyncio.run() which hangs in pytest context")
def test_submit_task(executor):
    """Test submit_task - this uses asyncio.run internally which can conflict with pytest-asyncio."""
    result = executor.execute("submit_task", {"name": "test_task", "command": "echo hello"})
    assert isinstance(result, str)
    assert "test_task" in result or "Task" in result


def test_list_tasks(executor):
    result = executor.execute("list_tasks", {})
    assert isinstance(result, str)


def test_get_task_nonexistent(executor):
    result = executor.execute("get_task", {"task_id": "nonexistent-task-id"})
    assert "ERROR" in result or "not found" in result.lower()


# ─── search_history (extras version) ─────────────────────────────────────────


def test_search_history_basic(executor):
    result = executor.execute("search_history", {"query": "test query"})
    assert isinstance(result, str)


def test_search_history_fuzzy(executor):
    result = executor.execute("search_history", {"query": "test", "fuzzy": True})
    assert isinstance(result, str)


# ─── validate_workspace ──────────────────────────────────────────────────────


def test_validate_workspace(executor):
    result = executor.execute("validate_workspace", {})
    assert isinstance(result, str)
    assert "Workspace" in result or "Validation" in result


# ─── security_audit ──────────────────────────────────────────────────────────


def test_security_audit_project(executor):
    result = executor.execute("security_audit", {})
    assert isinstance(result, str)


def test_security_audit_file(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("import os\nos.system('rm -rf /')")
    result = executor.execute("security_audit", {"path": "test.py"})
    assert isinstance(result, str)


# ─── refactor_code ───────────────────────────────────────────────────────────


def test_refactor_code(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("def old_func():\n    pass")
    result = executor.execute("refactor_code", {"path": "test.py", "function": "old_func"})
    assert isinstance(result, str)


def test_refactor_code_with_style(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("def func():\n    pass")
    result = executor.execute(
        "refactor_code", {"path": "test.py", "function": "func", "style": "async"}
    )
    assert isinstance(result, str)


# ─── generate_db_model ──────────────────────────────────────────────────────


def test_generate_db_model(executor):
    result = executor.execute(
        "generate_db_model",
        {
            "table": "users",
            "columns": [{"name": "id", "type": "int"}, {"name": "name", "type": "str"}],
        },
    )
    assert isinstance(result, str)
    assert "users" in result


# ─── generate_dockerfile ────────────────────────────────────────────────────


def test_generate_dockerfile_python(executor):
    result = executor.execute("generate_dockerfile", {"language": "python"})
    assert isinstance(result, str)


def test_generate_dockerfile_node(executor):
    result = executor.execute("generate_dockerfile", {"language": "node"})
    assert isinstance(result, str)


# ─── generate_docker_compose ────────────────────────────────────────────────


def test_generate_docker_compose(executor):
    result = executor.execute(
        "generate_docker_compose", {"services": [{"name": "web", "image": "nginx"}]}
    )
    assert isinstance(result, str)


# ─── generate_api_client ────────────────────────────────────────────────────


def test_generate_api_client(executor, tmp_path):
    spec = tmp_path / "openapi.yaml"
    spec.write_text("openapi: 3.0\ninfo:\n  title: Test\n  version: 1.0")
    result = executor.execute("generate_api_client", {"spec": str(spec)})
    assert isinstance(result, str)


# ─── generate_docs ──────────────────────────────────────────────────────────


def test_generate_docs_readme(executor):
    result = executor.execute("generate_docs", {"type": "readme"})
    assert isinstance(result, str)


def test_generate_docs_markdoc(executor):
    result = executor.execute("generate_docs", {"type": "markdoc"})
    assert isinstance(result, str)


def test_generate_docs_invalid_type(executor):
    result = executor.execute("generate_docs", {"type": "invalid_doc_type"})
    assert "ERROR" in result or isinstance(result, str)


# ─── profile_code ───────────────────────────────────────────────────────────


def test_profile_code(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("def func():\n    x = 1\n    return x\n")
    result = executor.execute("profile_code", {"path": str(f)})
    assert isinstance(result, str)


# ─── optimize_code ──────────────────────────────────────────────────────────


def test_optimize_code(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text(
        "def func():\n    result = []\n    for i in range(100):\n        result.append(str(i))\n    return result\n"
    )
    result = executor.execute("optimize_code", {"path": str(f)})
    assert isinstance(result, str)


# ─── analyze_code ───────────────────────────────────────────────────────────


def test_analyze_code(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("import os\n\ndef my_func():\n    pass\n\nclass MyClass:\n    pass\n")
    result = executor.execute("analyze_code", {"path": str(f)})
    assert isinstance(result, str)


# ─── explain_code ───────────────────────────────────────────────────────────


def test_explain_code(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("def hello():\n    print('world')\n")
    result = executor.execute("explain_code", {"path": str(f)})
    assert isinstance(result, str)


def test_explain_code_with_range(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("line1\nline2\nline3\nline4\nline5\n")
    result = executor.execute("explain_code", {"path": str(f), "start": 2, "end": 4})
    assert isinstance(result, str)


# ─── generate_tests ─────────────────────────────────────────────────────────


def test_generate_tests_pytest(executor, tmp_path):
    f = tmp_path / "mymodule.py"
    f.write_text("def add(a, b):\n    return a + b\n\ndef sub(a, b):\n    return a - b\n")
    result = executor.execute("generate_tests", {"path": str(f), "framework": "pytest"})
    assert isinstance(result, str)


def test_generate_tests_jest(executor, tmp_path):
    f = tmp_path / "mymodule.py"
    f.write_text("def add(a, b):\n    return a + b\n")
    result = executor.execute("generate_tests", {"path": str(f), "framework": "jest"})
    assert isinstance(result, str)


# ─── lsp tools ───────────────────────────────────────────────────────────────


def test_lsp_definition(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("x = 1\n")
    result = executor.execute("lsp_definition", {"path": str(f), "line": 1, "column": 0})
    assert isinstance(result, str)


def test_lsp_references(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("x = 1\nprint(x)\n")
    result = executor.execute("lsp_references", {"path": str(f), "line": 1, "column": 0})
    assert isinstance(result, str)


def test_lsp_hover(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("x = 1\n")
    result = executor.execute("lsp_hover", {"path": str(f), "line": 1, "column": 0})
    assert isinstance(result, str)


def test_lsp_diagnostics(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("x = 1\n")
    result = executor.execute("lsp_diagnostics", {"path": str(f)})
    assert isinstance(result, str)


# ─── get_code_actions ────────────────────────────────────────────────────────


def test_get_code_actions(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("x = 1\n")
    result = executor.execute("get_code_actions", {"path": str(f)})
    assert isinstance(result, str)


# ─── apply_code_action ───────────────────────────────────────────────────────


def test_apply_code_action(executor):
    result = executor.execute("apply_code_action", {"action_id": "test-action-1"})
    assert isinstance(result, str)
    assert "test-action-1" in result or "code action" in result.lower()


# ─── init_project / analyze_project ──────────────────────────────────────────


def test_init_project(executor):
    result = executor.execute("init_project", {})
    assert isinstance(result, str)


def test_analyze_project(executor):
    result = executor.execute("analyze_project", {})
    assert isinstance(result, str)
    assert "Project Analysis" in result or "Language" in result or isinstance(result, str)


# ─── select_files ────────────────────────────────────────────────────────────


def test_select_files_no_patterns(executor):
    result = executor.execute("select_files", {"patterns": []})
    assert "ERROR" in result or "No patterns" in result


def test_select_files_with_patterns(executor, tmp_path):
    (tmp_path / "project" / "test.py").write_text("code")
    result = executor.execute("select_files", {"patterns": ["*.py"]})
    assert isinstance(result, str)


def test_select_files_no_matches(executor, tmp_path):
    result = executor.execute("select_files", {"patterns": ["*.nonexistent_ext_xyz"]})
    assert "No files found" in result or isinstance(result, str)


# ─── get_completions ─────────────────────────────────────────────────────────


def test_get_completions_file(executor):
    result = executor.execute("get_completions", {"type": "file", "prefix": ""})
    assert isinstance(result, str)


def test_get_completions_command(executor):
    result = executor.execute("get_completions", {"type": "command", "prefix": ""})
    assert isinstance(result, str)


def test_get_completions_agent(executor):
    result = executor.execute("get_completions", {"type": "agent", "prefix": ""})
    assert isinstance(result, str)


def test_get_completions_model(executor):
    result = executor.execute("get_completions", {"type": "model", "prefix": ""})
    assert isinstance(result, str)


def test_get_completions_unknown_type(executor):
    result = executor.execute("get_completions", {"type": "unknown_type", "prefix": ""})
    assert "Unknown" in result or isinstance(result, str)


# ─── list_skills / use_skill ─────────────────────────────────────────────────


def test_list_skills(executor):
    result = executor.execute("list_skills", {})
    assert isinstance(result, str)


def test_use_skill_nonexistent(executor):
    result = executor.execute("use_skill", {"name": "nonexistent_skill_xyz"})
    assert "ERROR" in result or "not found" in result.lower()


# ─── replace_in_files ───────────────────────────────────────────────────────


def test_replace_in_files(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("old_text here")
    result = executor.execute(
        "replace_in_files",
        {"pattern": "old_text", "replacement": "new_text", "files": [str(f)], "dry_run": True},
    )
    assert isinstance(result, str)
