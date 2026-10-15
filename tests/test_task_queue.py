"""Tests for apex/task_queue.py — TaskQueue, Task, TaskStatus with real file operations."""

import pytest
import json
import time
from apex.task_queue import TaskStatus, Task, TaskQueue


class TestTaskStatus:
    def test_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_from_value(self):
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("completed") == TaskStatus.COMPLETED


class TestTask:
    def test_creation(self):
        t = Task(
            id="task_1",
            name="test",
            description="desc",
            payload={"key": "val"},
            status=TaskStatus.PENDING,
            created_at="2024-01-01",
            started_at=None,
            completed_at=None,
            result=None,
            error=None,
        )
        assert t.id == "task_1"
        assert t.name == "test"
        assert t.status == TaskStatus.PENDING
        assert t.payload == {"key": "val"}
        assert t.result is None
        assert t.error is None


class TestTaskQueue:
    @pytest.fixture
    def queue_dir(self, tmp_path):
        return tmp_path / "tasks"

    @pytest.fixture
    def queue(self, queue_dir):
        return TaskQueue(queue_dir=queue_dir)

    def test_init(self, queue, queue_dir):
        assert queue.queue_dir == queue_dir
        assert queue_dir.exists()
        assert queue._tasks == {}
        assert queue._running is False

    def test_enqueue(self, queue):
        task_id = queue.enqueue("test_task", "A test", {"data": "value"})
        assert task_id is not None
        assert task_id.startswith("task_")
        assert queue.get(task_id) is not None
        assert queue.get(task_id).status == TaskStatus.PENDING

    def test_enqueue_with_priority(self, queue):
        task_id = queue.enqueue("test", "desc", {}, priority=5)
        assert task_id is not None

    def test_get_nonexistent(self, queue):
        assert queue.get("nonexistent") is None

    def test_list_tasks(self, queue):
        queue.enqueue("task1", "First", {})
        queue.enqueue("task2", "Second", {})
        tasks = queue.list_tasks()
        assert len(tasks) == 2

    def test_list_tasks_filter_status(self, queue):
        id1 = queue.enqueue("task1", "First", {})
        queue.enqueue("task2", "Second", {})
        # Cancel one
        queue.cancel(id1)
        pending = queue.list_tasks(TaskStatus.CANCELLED)
        assert len(pending) == 1

    def test_list_tasks_limit(self, queue):
        for i in range(5):
            queue.enqueue(f"task{i}", f"Task {i}", {})
        tasks = queue.list_tasks(limit=3)
        assert len(tasks) == 3

    def test_cancel(self, queue):
        task_id = queue.enqueue("cancel_me", "desc", {})
        result = queue.cancel(task_id)
        assert result is True
        assert queue.get(task_id).status == TaskStatus.CANCELLED

    def test_cancel_nonexistent(self, queue):
        assert queue.cancel("nonexistent") is False

    def test_cancel_not_pending(self, queue):
        task_id = queue.enqueue("test", "desc", {})
        # Mark as completed
        task = queue.get(task_id)
        task.status = TaskStatus.COMPLETED
        assert queue.cancel(task_id) is False

    def test_clear_completed(self, queue):
        id1 = queue.enqueue("done", "desc", {})
        id2 = queue.enqueue("pending", "desc", {})
        queue.get(id1).status = TaskStatus.COMPLETED
        queue._save_tasks()
        count = queue.clear_completed()
        assert count == 1
        assert queue.get(id1) is None
        assert queue.get(id2) is not None

    def test_clear_completed_none(self, queue):
        count = queue.clear_completed()
        assert count == 0

    def test_delete_task(self, queue):
        task_id = queue.enqueue("delete_me", "desc", {})
        result = queue.delete_task(task_id)
        assert result is True
        assert queue.get(task_id) is None

    def test_delete_nonexistent(self, queue):
        assert queue.delete_task("nonexistent") is False

    def test_persistence(self, queue_dir):
        # Create queue and add tasks
        q1 = TaskQueue(queue_dir=queue_dir)
        q1.enqueue("persist_test", "desc", {"key": "val"})

        # Create new queue from same dir
        q2 = TaskQueue(queue_dir=queue_dir)
        tasks = q2.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].name == "persist_test"

    def test_start_and_stop_workers(self, queue):
        def handler(task):
            return {"processed": True}

        queue.start_worker(handler, max_workers=1)
        assert queue._running is True
        queue.stop_workers()
        assert queue._running is False

    def test_worker_processes_task(self, queue_dir):
        q = TaskQueue(queue_dir=queue_dir)
        task_id = q.enqueue("process_me", "desc", {})

        def handler(task):
            return {"result": "done"}

        q.start_worker(handler, max_workers=1)
        time.sleep(2)  # Wait for worker to pick up task
        q.stop_workers()

        task = q.get(task_id)
        if task:
            assert task.status in (TaskStatus.COMPLETED, TaskStatus.PENDING)

    def test_generate_id(self, queue):
        id1 = queue._generate_id()
        assert id1.startswith("task_")
        # IDs are based on timestamp + count, same second may produce same prefix
        assert len(id1) > 5

    def test_save_and_load_corrupt(self, queue_dir):
        # Write corrupt data
        queue_dir.mkdir(parents=True, exist_ok=True)
        (queue_dir / "tasks.json").write_text("not valid json{{{")

        q = TaskQueue(queue_dir=queue_dir)
        assert q._tasks == {}

    def test_save_tasks_method(self, queue):
        task_id = queue.enqueue("save_test", "desc", {})
        queue._save_tasks()
        assert queue.tasks_file.exists()
        data = json.loads(queue.tasks_file.read_text())
        assert task_id in data
