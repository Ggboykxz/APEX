"""Durable task queue - persistent background tasks that survive restarts."""

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: str
    name: str
    description: str
    payload: dict[str, Any]
    status: TaskStatus
    created_at: str
    started_at: str | None
    completed_at: str | None
    result: dict[str, Any] | None
    error: str | None


class TaskQueue:
    """Durable task queue with persistence."""

    def __init__(self, queue_dir: Path | None = None):
        self.queue_dir = queue_dir or (Path.home() / ".apex" / "tasks")
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.queue_dir / "tasks.json"
        self._tasks: dict[str, Task] = {}
        self._workers: list[threading.Thread] = []
        self._running = False
        self._load_tasks()

    def _load_tasks(self):
        """Load tasks from disk."""
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file) as f:
                    data = json.load(f)
                    for task_data in data.values():
                        task_data["status"] = TaskStatus(task_data["status"])
                        self._tasks[task_data["id"]] = Task(**task_data)
            except (json.JSONDecodeError, TypeError):
                self._tasks = {}

    def _save_tasks(self):
        """Save tasks to disk."""
        def task_to_dict(t: Task) -> dict:
            d = asdict(t)
            d["status"] = t.status.value
            return d

        data = {tid: task_to_dict(t) for tid, t in self._tasks.items()}
        with open(self.tasks_file, "w") as f:
            json.dump(data, f, indent=2)

    def _generate_id(self) -> str:
        """Generate unique task ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"task_{timestamp}_{len(self._tasks) + 1}"

    def enqueue(
        self,
        name: str,
        description: str,
        payload: dict[str, Any],
        priority: int = 0
    ) -> str:
        """Add a task to the queue."""
        task_id = self._generate_id()
        
        task = Task(
            id=task_id,
            name=name,
            description=description,
            payload=payload,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
            started_at=None,
            completed_at=None,
            result=None,
            error=None
        )
        
        self._tasks[task_id] = task
        self._save_tasks()
        
        return task_id

    def get(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 100
    ) -> list[Task]:
        """List tasks, optionally filtered by status."""
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    def start_worker(self, handler: Callable[[Task], dict[str, Any]], max_workers: int = 2):
        """Start background workers to process tasks."""
        self._running = True
        
        def worker():
            while self._running:
                pending = self.list_tasks(TaskStatus.PENDING, 1)
                if not pending:
                    time.sleep(1)
                    continue
                
                task = pending[0]
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now().isoformat()
                self._save_tasks()
                
                try:
                    result = handler(task)
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                
                task.completed_at = datetime.now().isoformat()
                self._save_tasks()
        
        for _ in range(max_workers):
            worker_thread = threading.Thread(target=worker, daemon=True)
            worker_thread.start()
            self._workers.append(worker_thread)

    def stop_workers(self):
        """Stop all workers."""
        self._running = False
        for worker in self._workers:
            worker.join(timeout=1)
        self._workers.clear()

    def cancel(self, task_id: str) -> bool:
        """Cancel a task."""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False
        
        task.status = TaskStatus.CANCELLED
        self._save_tasks()
        return True

    def clear_completed(self) -> int:
        """Remove completed tasks."""
        completed = [tid for tid, t in self._tasks.items() 
                     if t.status == TaskStatus.COMPLETED]
        for tid in completed:
            del self._tasks[tid]
        
        self._save_tasks()
        return len(completed)

    def delete_task(self, task_id: str) -> bool:
        """Delete a task completely."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._save_tasks()
            return True
        return False