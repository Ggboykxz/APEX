"""Tests for apex/extras.py — ShellExpander, EnvManager, Task, TaskQueue, HistorySearch, WorkspaceValidator, SecurityAuditor."""

import pytest
import tempfile
import os
import asyncio
import time
from pathlib import Path
from apex.extras import (
    ShellExpander,
    EnvManager,
    Task,
    TaskQueue as ExtrasTaskQueue,
    HistorySearch,
    WorkspaceValidator,
    SecurityAuditor,
    get_env_manager,
    get_task_queue,
    get_history_search,
)


# ---------------------------------------------------------------------------
# ShellExpander
# ---------------------------------------------------------------------------


class TestShellExpander:
    def test_expand_no_vars(self):
        assert ShellExpander.expand("hello world") == "hello world"

    def test_expand_env_var(self):
        os.environ["TEST_APEX_VAR"] = "test_value"
        assert ShellExpander.expand("$TEST_APEX_VAR") == "test_value"
        del os.environ["TEST_APEX_VAR"]

    def test_expand_curly_braces(self):
        os.environ["TEST_APEX_VAR2"] = "test_value2"
        assert ShellExpander.expand("${TEST_APEX_VAR2}") == "test_value2"
        del os.environ["TEST_APEX_VAR2"]

    def test_expand_unknown_var(self):
        result = ShellExpander.expand("$NONEXISTENT_APEX_VAR_XYZ")
        assert result == "$NONEXISTENT_APEX_VAR_XYZ"

    def test_expand_custom_env(self):
        result = ShellExpander.expand("$CUSTOM", env={"CUSTOM": "custom_value"})
        assert result == "custom_value"

    def test_expand_mixed_text(self):
        os.environ["MY_TEST_PATH"] = "/usr/bin"
        result = ShellExpander.expand("path: $MY_TEST_PATH/end")
        assert result == "path: /usr/bin/end"
        del os.environ["MY_TEST_PATH"]

    def test_expand_path_with_home(self):
        result = ShellExpander.expand_path("~/test_dir")
        assert result.endswith("test_dir")
        assert Path(result).is_absolute()

    def test_expand_path_absolute(self):
        result = ShellExpander.expand_path("/tmp/test")
        assert result == "/tmp/test"

    def test_expand_path_with_env(self):
        os.environ["MY_APEX_DIR"] = "/tmp"
        result = ShellExpander.expand_path("$MY_APEX_DIR/sub")
        assert result == "/tmp/sub"
        del os.environ["MY_APEX_DIR"]

    def test_expand_command(self):
        os.environ["MY_ECHO_CMD"] = "echo"
        result = ShellExpander.expand_command("$MY_ECHO_CMD hello")
        assert result == "echo hello"
        del os.environ["MY_ECHO_CMD"]


# ---------------------------------------------------------------------------
# EnvManager
# ---------------------------------------------------------------------------


class TestEnvManager:
    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def env_manager(self, temp_cwd):
        return EnvManager(temp_cwd)

    def test_init(self, temp_cwd):
        mgr = EnvManager(temp_cwd)
        assert mgr.cwd == Path(temp_cwd)
        assert mgr._local_env == {}

    def test_get_from_environ(self, env_manager):
        os.environ["TEST_APEX_GET"] = "from_environ"
        assert env_manager.get("TEST_APEX_GET") == "from_environ"
        del os.environ["TEST_APEX_GET"]

    def test_get_default(self, env_manager):
        assert env_manager.get("NONEXISTENT_KEY_XYZ", "default") == "default"

    def test_get_none_default(self, env_manager):
        assert env_manager.get("NONEXISTENT_KEY_XYZ") is None

    def test_set_and_get(self, env_manager):
        env_manager.set("MY_KEY", "my_value")
        assert env_manager.get("MY_KEY") == "my_value"

    def test_set_overrides_environ(self, env_manager):
        os.environ["OVERRIDE_APEX_KEY"] = "environ_value"
        env_manager.set("OVERRIDE_APEX_KEY", "local_value")
        assert env_manager.get("OVERRIDE_APEX_KEY") == "local_value"
        del os.environ["OVERRIDE_APEX_KEY"]

    def test_unset(self, env_manager):
        env_manager.set("UNSET_APEX_KEY", "value")
        env_manager.unset("UNSET_APEX_KEY")
        assert "UNSET_APEX_KEY" not in env_manager._local_env

    def test_unset_nonexistent(self, env_manager):
        # Should not raise
        env_manager.unset("NONEXISTENT_UNSET_KEY")

    def test_list(self, env_manager):
        env_manager.set("LIST_APEX_KEY", "value")
        result = env_manager.list()
        assert "LIST_APEX_KEY" in result
        assert "PATH" in result  # Should include os.environ

    def test_save_to_file(self, env_manager, temp_cwd):
        env_manager.set("SAVE_APEX_KEY", "save_value")
        result = env_manager.save_to_file()
        assert Path(result).exists()
        content = Path(result).read_text()
        assert "SAVE_APEX_KEY=save_value" in content

    def test_save_to_file_custom_name(self, env_manager, temp_cwd):
        env_manager.set("KEY1", "val1")
        result = env_manager.save_to_file(".env.custom")
        assert Path(result).exists()
        assert Path(result).name == ".env.custom"

    def test_load_from_file(self, temp_cwd):
        env_file = Path(temp_cwd) / ".env.apex"
        env_file.write_text("LOAD_KEY=load_value\nANOTHER=another_val\n")
        mgr = EnvManager(temp_cwd)
        mgr.load_from_file()
        assert mgr.get("LOAD_KEY") == "load_value"
        assert mgr.get("ANOTHER") == "another_val"

    def test_load_from_file_comments(self, temp_cwd):
        env_file = Path(temp_cwd) / ".env.apex"
        env_file.write_text("# comment\nKEY=val\n\n# another\n")
        mgr = EnvManager(temp_cwd)
        mgr.load_from_file()
        assert mgr.get("KEY") == "val"

    def test_load_from_file_nonexistent(self, env_manager):
        # Should not raise
        env_manager.load_from_file("nonexistent.env")

    def test_load_from_file_custom_path(self, temp_cwd):
        custom_file = Path(temp_cwd) / ".env.custom"
        custom_file.write_text("CUSTOM_KEY=custom_val\n")
        mgr = EnvManager(temp_cwd)
        mgr.load_from_file(".env.custom")
        assert mgr.get("CUSTOM_KEY") == "custom_val"


# ---------------------------------------------------------------------------
# Task (extras)
# ---------------------------------------------------------------------------


class TestTask:
    def test_creation(self):
        task = Task(id="1", name="test", status="pending")
        assert task.id == "1"
        assert task.name == "test"
        assert task.status == "pending"
        assert task.result is None
        assert task.error is None
        assert task.created_at > 0

    def test_with_result(self):
        task = Task(id="2", name="test2", status="completed", result="done")
        assert task.result == "done"


# ---------------------------------------------------------------------------
# TaskQueue (extras)
# ---------------------------------------------------------------------------


class TestExtrasTaskQueue:
    def test_init(self):
        tq = ExtrasTaskQueue()
        assert tq._tasks == {}
        assert tq._running is False

    def test_add_sync_task(self):
        tq = ExtrasTaskQueue()

        async def _test():
            def sync_func():
                return "result"

            task_id = await tq.add("sync_task", sync_func)
            assert task_id is not None
            assert len(task_id) == 8
            # Wait for task to complete
            await asyncio.sleep(0.1)
            task = tq.get(task_id)
            assert task is not None
            assert task.status == "completed"
            assert task.result == "result"

        asyncio.run(_test())

    def test_add_async_task(self):
        tq = ExtrasTaskQueue()

        async def _test():
            async def async_func():
                return "async_result"

            task_id = await tq.add("async_task", async_func)
            await asyncio.sleep(0.1)
            task = tq.get(task_id)
            assert task is not None
            assert task.status == "completed"
            assert task.result == "async_result"

        asyncio.run(_test())

    def test_add_failing_task(self):
        tq = ExtrasTaskQueue()

        async def _test():
            def failing_func():
                raise ValueError("test error")

            task_id = await tq.add("fail_task", failing_func)
            await asyncio.sleep(0.1)
            task = tq.get(task_id)
            assert task is not None
            assert task.status == "failed"
            assert "test error" in task.error

        asyncio.run(_test())

    def test_get_nonexistent(self):
        tq = ExtrasTaskQueue()
        assert tq.get("nonexistent") is None

    def test_list(self):
        tq = ExtrasTaskQueue()

        async def _test():
            def func():
                return "ok"

            await tq.add("task1", func)
            await tq.add("task2", func)
            await asyncio.sleep(0.1)
            tasks = tq.list()
            assert len(tasks) == 2

        asyncio.run(_test())

    def test_cancel(self):
        tq = ExtrasTaskQueue()

        task_id = None

        async def _test():
            nonlocal task_id

            def slow_func():
                time.sleep(10)

            task_id = await tq.add("slow_task", slow_func)
            result = tq.cancel(task_id)
            assert result is True
            task = tq.get(task_id)
            assert task.status == "cancelled"

        asyncio.run(_test())

    def test_cancel_nonexistent(self):
        tq = ExtrasTaskQueue()
        assert tq.cancel("nonexistent") is False


# ---------------------------------------------------------------------------
# HistorySearch
# ---------------------------------------------------------------------------


class TestHistorySearch:
    def test_init(self):
        hs = HistorySearch()
        assert hs.max_items == 1000
        assert hs._history == []

    def test_add(self):
        hs = HistorySearch()
        hs.add("query1", "response1")
        assert len(hs._history) == 1
        assert hs._history[0]["query"] == "query1"

    def test_add_with_metadata(self):
        hs = HistorySearch()
        hs.add("q", "r", metadata={"source": "test"})
        assert hs._history[0]["metadata"] == {"source": "test"}

    def test_search_fuzzy(self):
        hs = HistorySearch()
        hs.add("python debugging", "debug response")
        hs.add("javascript testing", "test response")
        results = hs.search("python")
        assert len(results) == 1
        assert results[0]["query"] == "python debugging"

    def test_search_non_fuzzy(self):
        hs = HistorySearch()
        hs.add("python debugging", "debug response")
        hs.add("javascript testing", "test response")
        results = hs.search("python debugging", fuzzy=False)
        assert len(results) == 1

    def test_search_no_results(self):
        hs = HistorySearch()
        hs.add("python", "response")
        results = hs.search("javascript")
        assert results == []

    def test_fuzzy_match(self):
        hs = HistorySearch()
        hs.add("python debugging tips", "response")
        results = hs.fuzzy_match("python debug", threshold=0.5)
        assert len(results) >= 1

    def test_fuzzy_match_no_results(self):
        hs = HistorySearch()
        hs.add("python", "response")
        results = hs.fuzzy_match("zzzzzzzz", threshold=0.9)
        assert results == []

    def test_max_items_trimming(self):
        hs = HistorySearch(max_items=3)
        for i in range(5):
            hs.add(f"query{i}", f"response{i}")
        assert len(hs._history) == 3


# ---------------------------------------------------------------------------
# WorkspaceValidator
# ---------------------------------------------------------------------------


class TestWorkspaceValidator:
    def test_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wv = WorkspaceValidator(tmpdir)
            assert wv.cwd == Path(tmpdir)

    def test_validate_no_rules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wv = WorkspaceValidator(tmpdir)
            result = wv.validate()
            assert result["passed"] == []
            assert result["failed"] == []
            assert result["warnings"] == []

    def test_validate_passing_rule(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wv = WorkspaceValidator(tmpdir)
            wv.add_rule("has_readme", lambda cwd: (cwd / "README.md").exists(), "No README")
            Path(tmpdir, "README.md").write_text("# Test")
            result = wv.validate()
            assert "has_readme" in result["passed"]

    def test_validate_failing_rule(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wv = WorkspaceValidator(tmpdir)
            wv.add_rule("has_readme", lambda cwd: (cwd / "README.md").exists(), "No README")
            result = wv.validate()
            assert len(result["failed"]) == 1
            assert result["failed"][0]["name"] == "has_readme"

    def test_validate_exception_rule(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wv = WorkspaceValidator(tmpdir)

            def bad_check(cwd):
                raise RuntimeError("check failed")

            wv.add_rule("bad", bad_check, "error")
            result = wv.validate()
            assert len(result["warnings"]) == 1

    def test_validate_config_no_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wv = WorkspaceValidator(tmpdir)
            result = wv.validate_config()
            assert result["valid"] is False
            assert len(result["issues"]) > 0

    def test_validate_config_with_git(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, ".git").mkdir()
            Path(tmpdir, "test.py").write_text("print('hello')")
            wv = WorkspaceValidator(tmpdir)
            result = wv.validate_config()
            # May or may not be valid depending on config file presence
            assert isinstance(result["valid"], bool)
            assert isinstance(result["issues"], list)


# ---------------------------------------------------------------------------
# SecurityAuditor
# ---------------------------------------------------------------------------


class TestSecurityAuditor:
    def test_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            assert sa.cwd == Path(tmpdir)

    def test_audit_file_eval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("eval('1+1')")
            issues = sa.audit_file(test_file)
            assert len(issues) > 0
            assert any("eval" in i["message"].lower() for i in issues)

    def test_audit_file_exec(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("exec('code')")
            issues = sa.audit_file(test_file)
            assert any("exec" in i["message"].lower() for i in issues)

    def test_audit_file_shell_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("subprocess.run(cmd, shell=True)")
            issues = sa.audit_file(test_file)
            assert any("shell" in i["message"].lower() for i in issues)

    def test_audit_file_hardcoded_password(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('password = "secret123"')
            issues = sa.audit_file(test_file)
            assert any("password" in i["message"].lower() for i in issues)

    def test_audit_file_hardcoded_api_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('api_key = "sk-12345"')
            issues = sa.audit_file(test_file)
            assert any("api" in i["message"].lower() for i in issues)

    def test_audit_file_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("x = 1 + 2\nprint(x)")
            issues = sa.audit_file(test_file)
            assert len(issues) == 0

    def test_audit_file_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            issues = sa.audit_file(Path(tmpdir) / "nonexistent.py")
            assert issues == []

    def test_audit_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            test_file = Path(tmpdir) / "bad.py"
            test_file.write_text("eval('1+1')")
            results = sa.audit_project()
            assert results["total_issues"] > 0

    def test_audit_project_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            test_file = Path(tmpdir) / "clean.py"
            test_file.write_text("x = 1")
            results = sa.audit_project()
            assert results["total_issues"] == 0


# ---------------------------------------------------------------------------
# Module-level functions
# ---------------------------------------------------------------------------


class TestModuleFunctions:
    def test_get_env_manager(self, tmp_path):
        mgr = get_env_manager(str(tmp_path))
        assert isinstance(mgr, EnvManager)
        assert mgr.cwd == Path(str(tmp_path))

    def test_get_task_queue(self):
        import apex.extras

        # Reset global
        apex.extras._task_queue = None
        tq = get_task_queue()
        assert isinstance(tq, ExtrasTaskQueue)

    def test_get_history_search(self):
        import apex.extras

        # Reset global
        apex.extras._history_search = None
        hs = get_history_search()
        assert isinstance(hs, HistorySearch)
