"""Tests for refactored extras module."""


from apex.refactored_extras import (
    ShellExpander, EnvManager, Task, TaskQueue, HistorySearch,
    create_shell_expander, create_env_manager, create_task_queue, create_history_search
)


class TestShellExpander:
    def test_expand_no_vars(self):
        expander = ShellExpander()
        result = expander.expand("hello world")
        assert result == "hello world"

    def test_expand_simple_var(self):
        expander = ShellExpander(env_provider=lambda: {"KEY": "value"})
        result = expander.expand("$KEY")
        assert result == "value"

    def test_expand_braced_var(self):
        expander = ShellExpander(env_provider=lambda: {"KEY": "value"})
        result = expander.expand("${KEY}")
        assert result == "value"

    def test_expand_unknown_var(self):
        expander = ShellExpander(env_provider=lambda: {})
        result = expander.expand("$UNKNOWN")
        assert result == "$UNKNOWN"

    def test_expand_multiple_vars(self):
        expander = ShellExpander(env_provider=lambda: {"A": "1", "B": "2"})
        result = expander.expand("$A and $B")
        assert result == "1 and 2"

    def test_expand_with_custom_env(self):
        expander = ShellExpander()
        result = expander.expand("$KEY", env={"KEY": "custom"})
        assert result == "custom"

    def test_expand_path(self):
        expander = ShellExpander(
            path_expanduser=lambda p: p.replace("~", "/home/user"),
            path_expandvars=lambda p: p,
            path_abspath=lambda p: "/abs/" + p
        )
        result = expander.expand_path("~/file.txt")
        assert result == "/abs//home/user/file.txt"

    def test_expand_command(self):
        expander = ShellExpander(env_provider=lambda: {"CMD": "ls"})
        result = expander.expand_command("$CMD -la")
        assert result == "ls -la"


class TestEnvManager:
    def test_init(self, tmp_path):
        manager = EnvManager(str(tmp_path))
        assert manager.cwd == tmp_path

    def test_get_local(self, tmp_path):
        manager = EnvManager(str(tmp_path), env_provider=lambda: {})
        manager.set("KEY", "local_value")
        
        result = manager.get("KEY")
        
        assert result == "local_value"

    def test_get_env_fallback(self, tmp_path):
        manager = EnvManager(str(tmp_path), env_provider=lambda: {"KEY": "env_value"})
        
        result = manager.get("KEY")
        
        assert result == "env_value"

    def test_get_default(self, tmp_path):
        manager = EnvManager(str(tmp_path), env_provider=lambda: {})
        
        result = manager.get("NONEXISTENT", "default")
        
        assert result == "default"

    def test_set(self, tmp_path):
        manager = EnvManager(str(tmp_path), env_provider=lambda: {})
        manager.set("KEY", "value")
        
        assert manager._local_env["KEY"] == "value"

    def test_unset(self, tmp_path):
        manager = EnvManager(str(tmp_path), env_provider=lambda: {})
        manager.set("KEY", "value")
        manager.unset("KEY")
        
        assert "KEY" not in manager._local_env

    def test_unset_not_found(self, tmp_path):
        manager = EnvManager(str(tmp_path), env_provider=lambda: {})
        result = manager.unset("NONEXISTENT")
        
        assert result is False

    def test_list(self, tmp_path):
        manager = EnvManager(str(tmp_path), env_provider=lambda: {"A": "1"})
        manager.set("B", "2")
        
        env = manager.list()
        
        assert env["A"] == "1"
        assert env["B"] == "2"

    def test_save_to_file(self, tmp_path):
        manager = EnvManager(str(tmp_path), env_provider=lambda: {})
        manager.set("KEY", "value")
        
        manager.save_to_file(".env.test")
        
        assert (tmp_path / ".env.test").exists()
        assert "KEY=value" in (tmp_path / ".env.test").read_text()

    def test_load_from_file(self, tmp_path):
        env_file = tmp_path / ".env.test"
        env_file.write_text("KEY1=value1\nKEY2=value2\n# comment")
        
        manager = EnvManager(str(tmp_path), env_provider=lambda: {})
        manager.load_from_file(".env.test")
        
        assert manager.get("KEY1") == "value1"
        assert manager.get("KEY2") == "value2"


class TestTask:
    def test_init(self):
        task = Task(id="1", name="test")
        assert task.id == "1"
        assert task.name == "test"
        assert task.status == "pending"
        assert task.result is None
        assert task.error is None


class TestTaskQueue:
    def test_init(self):
        queue = TaskQueue()
        assert queue.list_all() == []

    def test_add(self):
        queue = TaskQueue()
        task = queue.add("task1", "Test task")
        
        assert task.id == "task1"
        assert task.name == "Test task"

    def test_get(self):
        queue = TaskQueue()
        queue.add("task1", "Test")
        
        task = queue.get("task1")
        
        assert task is not None
        assert task.id == "task1"

    def test_get_not_found(self):
        queue = TaskQueue()
        task = queue.get("nonexistent")
        
        assert task is None

    def test_start(self):
        queue = TaskQueue()
        queue.add("task1", "Test")
        
        result = queue.start("task1")
        
        assert result is True
        assert queue.get("task1").status == "running"

    def test_start_not_pending(self):
        queue = TaskQueue()
        queue.add("task1", "Test")
        queue.start("task1")
        
        result = queue.start("task1")
        
        assert result is False

    def test_complete(self):
        queue = TaskQueue()
        queue.add("task1", "Test")
        queue.start("task1")
        
        result = queue.complete("task1", "result_data")
        
        assert result is True
        task = queue.get("task1")
        assert task.status == "completed"
        assert task.result == "result_data"

    def test_fail(self):
        queue = TaskQueue()
        queue.add("task1", "Test")
        queue.start("task1")
        
        result = queue.fail("task1", "error message")
        
        assert result is True
        task = queue.get("task1")
        assert task.status == "failed"
        assert task.error == "error message"

    def test_cancel(self):
        queue = TaskQueue()
        queue.add("task1", "Test")
        
        result = queue.cancel("task1")
        
        assert result is True
        assert queue.get("task1").status == "cancelled"

    def test_list_pending(self):
        queue = TaskQueue()
        queue.add("task1", "Test 1")
        queue.add("task2", "Test 2")
        
        pending = queue.list_pending()
        
        assert len(pending) == 2


class TestHistorySearch:
    def test_init(self):
        search = HistorySearch()
        assert search.get_recent() == []

    def test_add(self):
        search = HistorySearch()
        search.add("query", "result", {"context": "data"})
        
        recent = search.get_recent(1)
        
        assert len(recent) == 1
        assert recent[0]["query"] == "query"

    def test_search_found(self):
        search = HistorySearch()
        search.add("python print", "result1")
        search.add("python import", "result2")
        search.add("javascript", "result3")
        
        results = search.search("python")
        
        assert len(results) == 2

    def test_search_not_found(self):
        search = HistorySearch()
        search.add("python", "result")
        
        results = search.search("golang")
        
        assert results == []

    def test_get_recent_limit(self):
        search = HistorySearch()
        for i in range(15):
            search.add(f"query{i}", f"result{i}")
        
        recent = search.get_recent(5)
        
        assert len(recent) == 5
        assert recent[0]["query"] == "query10"

    def test_clear(self):
        search = HistorySearch()
        search.add("query", "result")
        search.clear()
        
        assert search.get_recent() == []


class TestFactoryFunctions:
    def test_create_shell_expander(self):
        expander = create_shell_expander()
        assert isinstance(expander, ShellExpander)

    def test_create_env_manager(self, tmp_path):
        manager = create_env_manager(str(tmp_path))
        assert isinstance(manager, EnvManager)

    def test_create_task_queue(self):
        queue = create_task_queue()
        assert isinstance(queue, TaskQueue)

    def test_create_history_search(self):
        search = create_history_search()
        assert isinstance(search, HistorySearch)