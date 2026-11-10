"""Environment, task-queue, watcher and timeout tools.

Split out of ``apex.tools`` so that module keeps a single
responsibility: the tool executor core.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "EnvToolsMixin",
]


class EnvToolsMixin:
    def _execute_get_env(self, args: dict[str, Any]) -> str:
        from .extras import get_env_manager

        key = args["key"]
        if key.endswith(("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD")):
            return "ERROR: Reading secret environment variables is blocked"
        em = get_env_manager(str(self.cwd))
        value = em.get(key)
        return f"{key}={value}" if value else f"ERROR: {key} not found"

    def _execute_set_env(self, args: dict[str, Any]) -> str:
        from .extras import get_env_manager

        key = args["key"]
        value = args["value"]
        em = get_env_manager(str(self.cwd))
        em.set(key, value)
        return f"SUCCESS: {key}={value}"

    def _execute_list_env(self, args: dict[str, Any]) -> str:
        from .extras import get_env_manager

        em = get_env_manager(str(self.cwd))
        env = em.list()
        lines = ["Environment Variables:", "=" * 40]
        for k, v in sorted(env.items())[:50]:
            if k.endswith(("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD")):
                lines.append(f"{k}=***REDACTED***")
            else:
                lines.append(f"{k}={v[:50]}")
        return "\n".join(lines)

    def _execute_submit_task(self, args: dict[str, Any]) -> str:
        import asyncio

        from .extras import get_task_queue

        name = args["name"]
        command = args["command"]

        async def run_command():
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.cwd),
            )
            stdout, stderr = await proc.communicate()
            return stdout.decode() or stderr.decode()

        queue = get_task_queue()
        task_id = asyncio.run(queue.add(name, run_command))
        return f"Task submitted: {task_id} ({name})"

    def _execute_list_tasks(self, args: dict[str, Any]) -> str:
        from .extras import get_task_queue

        queue = get_task_queue()
        tasks = queue.list()
        if not tasks:
            return "No tasks"
        lines = ["Tasks:", "=" * 40]
        for t in tasks:
            lines.append(f"  {t['id']} - {t['name']} [{t['status']}]")
        return "\n".join(lines)

    def _execute_get_task(self, args: dict[str, Any]) -> str:
        from .extras import get_task_queue

        task_id = args["task_id"]
        queue = get_task_queue()
        task = queue.get(task_id)
        if not task:
            return f"ERROR: Task {task_id} not found"
        return (
            f"Task: {task.name}\nStatus: {task.status}\nResult: {task.result}\nError: {task.error}"
        )

    def _execute_get_tool_timeout(self, args: dict[str, Any]) -> str:
        from .advanced import ToolTimeout

        tool = args["tool"]
        timeout = ToolTimeout.get_timeout(tool)
        return f"Timeout for {tool}: {timeout}s"

    def _execute_set_tool_timeout(self, args: dict[str, Any]) -> str:
        from .advanced import ToolTimeout

        tool = args["tool"]
        timeout = args["timeout"]
        ToolTimeout.set_timeout(tool, timeout)
        return f"Set timeout for {tool} to {timeout}s"

    def _execute_get_context_info(self, args: dict[str, Any]) -> str:
        from .advanced import ContextOptimizer

        agent = getattr(self, "_agent", None)
        if agent is None:
            return "No agent context available"

        messages = agent.history if hasattr(agent, "history") else []
        info = ContextOptimizer.extract_key_info(messages)

        output = ["Context Analysis", "=" * 40]
        output.append(f"Files mentioned: {', '.join(info['files_mentioned'][:10]) or 'none'}")
        output.append(f"Tools used: {', '.join(info['tools_used']) or 'none'}")
        output.append(f"Errors: {len(info['errors'])}")

        return "\n".join(output)

    def _execute_start_file_watch(self, args: dict[str, Any]) -> str:
        from .project import FileWatcher

        patterns = args.get("patterns")

        if not hasattr(self, "_file_watcher"):
            self._file_watcher = FileWatcher(str(self.cwd))

        observer = self._file_watcher.watch(patterns)
        if observer:
            return f"SUCCESS: Watching {patterns or ['default']} for changes"
        return "ERROR: Could not start watcher (install watchdog: pip install watchdog)"

    def _execute_stop_file_watch(self, args: dict[str, Any]) -> str:
        if hasattr(self, "_file_watcher"):
            self._file_watcher.stop()
            return "SUCCESS: File watcher stopped"
        return "ERROR: No file watcher running"
