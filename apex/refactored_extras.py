"""Refactored extras module - More testable."""

import os
import re
from pathlib import Path
from typing import Any, Optional, Callable, Dict
from dataclasses import dataclass


class ShellExpander:
    VAR_PATTERN = re.compile(r"\$\{?([a-zA-Z_][a-zA-Z0-9_]*)\}?")

    def __init__(
        self,
        env_provider: Optional[Callable[[], Dict[str, str]]] = None,
        path_expanduser: Optional[Callable[[str], str]] = None,
        path_expandvars: Optional[Callable[[str], str]] = None,
        path_abspath: Optional[Callable[[str], str]] = None,
    ):
        self._env_provider = env_provider or (lambda: os.environ)
        self._expanduser = path_expanduser or os.path.expanduser
        self._expandvars = path_expandvars or os.path.expandvars
        self._abspath = path_abspath or os.path.abspath

    def expand(self, text: str, env: Optional[Dict[str, str]] = None) -> str:
        env = env or self._env_provider()

        def replace_var(match):
            var_name = match.group(1)
            return env.get(var_name, match.group(0))

        return self.VAR_PATTERN.sub(replace_var, text)

    def expand_path(self, path: str) -> str:
        path = self.expand(path)
        path = self._expanduser(path)
        path = self._expandvars(path)
        return self._abspath(path)

    def expand_command(self, command: str) -> str:
        return self.expand(command)


class EnvManager:
    def __init__(
        self,
        cwd: str,
        env_provider: Optional[Callable[[], Dict[str, str]]] = None,
        path_class: Optional[type] = None,
        path_read_text: Optional[Callable[[Path], str]] = None,
        path_write_text: Optional[Callable[[Path, str], None]] = None,
        path_exists: Optional[Callable[[Path], bool]] = None,
    ):
        self.cwd = path_class(Path) if path_class else Path(cwd)
        self._local_env: dict[str, str] = {}

        self._env_provider = env_provider or (lambda: os.environ)
        self._path_read_text = path_read_text or (lambda p: p.read_text())
        self._path_write_text = path_write_text or (lambda p, t: p.write_text(t))
        self._path_exists = path_exists or (lambda p: p.exists())

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._local_env.get(key, self._env_provider().get(key, default))

    def set(self, key: str, value: str) -> None:
        self._local_env[key] = value

    def unset(self, key: str) -> bool:
        if key in self._local_env:
            del self._local_env[key]
            return True
        return False

    def list(self) -> dict[str, str]:
        return {**self._env_provider(), **self._local_env}

    def save_to_file(self, filepath: str = ".env.apex") -> str:
        env_path = self.cwd / filepath
        lines = [f"{k}={v}" for k, v in self._local_env.items()]
        self._path_write_text(env_path, "\n".join(lines))
        return str(env_path)

    def load_from_file(self, filepath: str = ".env.apex") -> None:
        env_path = self.cwd / filepath
        if not self._path_exists(env_path):
            return

        for line in self._path_read_text(env_path).split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                self._local_env[key.strip()] = value.strip()


@dataclass
class Task:
    id: str
    name: str
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None


class TaskQueue:
    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._pending: list[str] = []

    def add(self, task_id: str, name: str) -> Task:
        task = Task(id=task_id, name=name)
        self._tasks[task_id] = task
        self._pending.append(task_id)
        return task

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def start(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.status != "pending":
            return False
        task.status = "running"
        return True

    def complete(self, task_id: str, result: Any) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.status != "running":
            return False
        task.status = "completed"
        task.result = result
        return True

    def fail(self, task_id: str, error: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.status != "running":
            return False
        task.status = "failed"
        task.error = error
        return True

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = "cancelled"
        return True

    def list_pending(self) -> list[Task]:
        return [self._tasks[tid] for tid in self._pending if tid in self._tasks]

    def list_all(self) -> list[Task]:
        return list(self._tasks.values())


class HistorySearch:
    def __init__(self):
        self._entries: list[dict[str, Any]] = []

    def add(self, query: str, result: str, context: Optional[dict] = None) -> None:
        self._entries.append(
            {
                "query": query,
                "result": result,
                "context": context or {},
            }
        )

    def search(self, query: str) -> list[dict[str, Any]]:
        results = []
        for entry in self._entries:
            if query.lower() in entry["query"].lower():
                results.append(entry)
        return results

    def get_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._entries[-limit:]

    def clear(self) -> None:
        self._entries.clear()


def create_shell_expander(
    env_provider: Optional[Callable] = None,
    path_expanduser: Optional[Callable] = None,
    path_expandvars: Optional[Callable] = None,
    path_abspath: Optional[Callable] = None,
) -> ShellExpander:
    return ShellExpander(env_provider, path_expanduser, path_expandvars, path_abspath)


def create_env_manager(cwd: str) -> EnvManager:
    return EnvManager(cwd)


def create_task_queue() -> TaskQueue:
    return TaskQueue()


def create_history_search() -> HistorySearch:
    return HistorySearch()
