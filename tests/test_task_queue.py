"""Tests for task_queue module."""

import pytest
import tempfile
from pathlib import Path
from apex.task_queue import Task, TaskStatus, TaskQueue


class TestTask:
    """Test Task dataclass."""

    def test_init(self):
        """Test task initialization."""
        task = Task(
            id="test-1",
            name="test_task",
            description="Test description",
            payload={"key": "value"},
            status=TaskStatus.PENDING,
            created_at="2024-01-01T00:00:00",
            started_at=None,
            completed_at=None,
            result=None,
            error=None,
        )
        assert task.id == "test-1"
        assert task.name == "test_task"
        assert task.status == TaskStatus.PENDING


class TestTaskQueue:
    """Test TaskQueue class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def queue(self, temp_dir):
        """Create TaskQueue with temp dir."""
        return TaskQueue(queue_dir=temp_dir)

    def test_init(self, queue):
        """Test queue initialization."""
        assert queue._tasks == {}
        assert queue._running is False

    def test_enqueue(self, queue):
        """Test enqueue method."""
        task_id = queue.enqueue(name="test_task", description="Test", payload={"key": "value"})
        assert task_id.startswith("task_")
        task = queue.get(task_id)
        assert task is not None
        assert task.name == "test_task"
        assert task.status == TaskStatus.PENDING

    def test_get(self, queue):
        """Test get method."""
        task_id = queue.enqueue(name="test", description="Test", payload={})
        task = queue.get(task_id)
        assert task is not None
        assert task.id == task_id

    def test_get_nonexistent(self, queue):
        """Test get with non-existent task."""
        task = queue.get("nonexistent")
        assert task is None

    def test_list_tasks_empty(self, queue):
        """Test list_tasks with no tasks."""
        tasks = queue.list_tasks()
        assert tasks == []

    def test_list_tasks_pending(self, queue):
        """Test list_tasks with pending tasks."""
        queue.enqueue(name="task1", description="T1", payload={})
        queue.enqueue(name="task2", description="T2", payload={})
        tasks = queue.list_tasks(TaskStatus.PENDING)
        assert len(tasks) == 2

    def test_list_tasks_with_status_filter(self, queue):
        """Test list_tasks with status filter."""
        task_id = queue.enqueue(name="task1", description="T1", payload={})
        task = queue.get(task_id)
        task.status = TaskStatus.RUNNING

        pending = queue.list_tasks(TaskStatus.PENDING)
        running = queue.list_tasks(TaskStatus.RUNNING)

        assert len(pending) == 0
        assert len(running) == 1

    def test_list_tasks_limit(self, queue):
        """Test list_tasks with limit."""
        for i in range(5):
            queue.enqueue(name=f"task{i}", description=f"T{i}", payload={})

        tasks = queue.list_tasks(limit=2)
        assert len(tasks) == 2

    def test_start_worker(self, queue):
        """Test start_worker method."""

        def handler(task):
            return {"result": "success"}

        queue.start_worker(handler, max_workers=1)
        assert queue._running is True
        assert len(queue._workers) == 1

        queue.stop_workers()
        assert queue._running is False

    def test_cancel(self, queue):
        """Test cancel method."""
        task_id = queue.enqueue(name="task", description="Test", payload={})
        result = queue.cancel(task_id)
        assert result is True

        task = queue.get(task_id)
        assert task.status == TaskStatus.CANCELLED

    def test_cancel_not_pending(self, queue):
        """Test cancel non-pending task."""
        task_id = queue.enqueue(name="task", description="Test", payload={})
        task = queue.get(task_id)
        task.status = TaskStatus.RUNNING

        result = queue.cancel(task_id)
        assert result is False

    def test_cancel_nonexistent(self, queue):
        """Test cancel non-existent task."""
        result = queue.cancel("nonexistent")
        assert result is False

    def test_clear_completed(self, queue):
        """Test clear_completed method."""
        task_id = queue.enqueue(name="task", description="Test", payload={})
        task = queue.get(task_id)
        task.status = TaskStatus.COMPLETED
        task.result = {"done": True}

        count = queue.clear_completed()
        assert count == 1
        assert queue.get(task_id) is None

    def test_delete_task(self, queue):
        """Test delete_task method."""
        task_id = queue.enqueue(name="task", description="Test", payload={})
        result = queue.delete_task(task_id)
        assert result is True
        assert queue.get(task_id) is None

    def test_delete_task_nonexistent(self, queue):
        """Test delete non-existent task."""
        result = queue.delete_task("nonexistent")
        assert result is False


class TestTaskQueuePersistence:
    """Test TaskQueue persistence."""

    @pytest.fixture
    def temp_dir(self):
        """Create temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_tasks_saved_to_disk(self, temp_dir):
        """Test that tasks are saved to disk."""
        queue1 = TaskQueue(queue_dir=temp_dir)
        queue1.enqueue(name="persistent", description="Test", payload={})

        queue2 = TaskQueue(queue_dir=temp_dir)
        tasks = queue2.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].name == "persistent"
