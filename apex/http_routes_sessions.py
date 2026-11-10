"""Session, share, diff and undo routes.

Split out of ``apex.http_api`` so that module keeps a single
responsibility: the HTTP server core.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from aiohttp import web

from .share import share_manager

__all__ = [
    "SessionRoutesMixin",
]


def _is_absolute_diff_path(candidate: str) -> bool:
    """Whether the candidate path points outside the repository root."""
    if candidate.startswith("/") or Path(candidate).is_absolute():
        return True
    # Reject Windows drive-qualified paths even on POSIX hosts.
    return len(candidate) >= 2 and candidate[1] == ":"


class SessionRoutesMixin:
    async def session_save(self, request: web.Request) -> web.Response:
        """Save current session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json()
            name = data.get("name", "http_session")
            path = self.session_manager.save(self.agent, name)
            return web.json_response({"saved": str(path)})
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

    async def session_load(self, request: web.Request) -> web.Response:
        """Load a session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json()
            name = data.get("name")
            if not name:
                return web.json_response({"error": "name required"}, status=400)

            success = self.session_manager.load(name, self.agent)
            if success:
                return web.json_response({"loaded": name})
            return web.json_response({"error": "session not found"}, status=404)
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

    async def api_sessions_list(self, request: web.Request) -> web.Response:
        """List all sessions."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        sessions = self.session_manager.list_sessions()
        return web.json_response({"sessions": sessions})

    @staticmethod
    def _delete_session_file(sessions_dir: Path, session_id: str) -> bool:
        """Delete the session file whose name matches the id."""
        # Sorted globs make duplicate deletion deterministic: filesystem
        # enumeration order differs across platforms and filesystems.
        for fpath in sorted(sessions_dir.glob(f"*{session_id}*")):
            if fpath.is_file() and not fpath.is_symlink():
                fpath.unlink()
                return True
        return False

    @staticmethod
    def _delete_session_by_content(sessions_dir: Path, session_id: str) -> bool:
        """Delete the session file whose content carries the id."""
        for fpath in sorted(sessions_dir.glob("*.json")):
            if fpath.is_symlink():
                continue
            try:
                data = json.loads(fpath.read_text())
            except Exception:  # noqa: BLE001, S112
                continue
            if data.get("name") == session_id or data.get("session_id") == session_id:
                fpath.unlink()
                return True
        return False

    async def api_sessions_delete(self, request: web.Request) -> web.Response:
        """Delete a session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        session_id = request.match_info.get("id", "")
        try:
            sessions_dir = Path.home() / ".apex" / "sessions"
            found = self._delete_session_file(sessions_dir, session_id)
            if not found:
                found = self._delete_session_by_content(sessions_dir, session_id)
            if found:
                return web.json_response({"deleted": session_id})
            return web.json_response({"error": "session not found"}, status=404)
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

    async def api_share(self, request: web.Request) -> web.Response:
        """Share current session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json() if request.can_read_body else {}
            title = data.get("title", "")
            session_id = data.get("session_id", "default")

            url = share_manager.share_session(session_id, title=title)
            if not url:
                return web.json_response({"error": "sharing is disabled"}, status=403)
            return web.json_response({"url": url, "share_id": url.rstrip("/").split("/")[-1]})
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

    async def api_unshare(self, request: web.Request) -> web.Response:
        """Unshare a session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        share_id = request.match_info.get("share_id", "")
        success = share_manager.unshare_session(share_id)
        if success:
            return web.json_response({"unshared": share_id})
        return web.json_response({"error": "share not found"}, status=404)

    async def api_shares_list(self, request: web.Request) -> web.Response:
        """List shared sessions."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        shares = share_manager.list_shared()
        return web.json_response({"shares": shares})

    async def api_compact(self, request: web.Request) -> web.Response:
        """Compact session context."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json() if request.can_read_body else {}
            strategy = data.get("strategy", "summarize")

            from .context_tracking import ContextManager

            ctx = ContextManager()
            for msg in self.agent.history:
                ctx.add_message(msg.get("role", "user"), msg.get("content", ""))

            saved = ctx.compact(strategy=strategy)
            self.agent.history = ctx.get_messages()

            await self.event_bus.publish("compact", {"tokens_saved": saved})

            return web.json_response(
                {
                    "compacted": True,
                    "strategy": strategy,
                    "tokens_saved": saved,
                    "history_length": len(self.agent.history),
                }
            )
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

    async def api_export(self, request: web.Request) -> web.Response:
        """Export session as JSON."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        session_id = request.match_info.get("session_id", "default")

        export_data = share_manager.export_session(session_id)
        if not export_data:
            return web.json_response({"error": "session not found"}, status=404)

        return web.json_response(export_data)

    async def api_import(self, request: web.Request) -> web.Response:
        """Import session from JSON."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json()
            file_path = data.get("file_path", "")
            session_data = data.get("data")

            if file_path:
                session_id = share_manager.import_session(file_path)
                if session_id:
                    return web.json_response({"imported": True, "session_id": session_id})
                return web.json_response({"error": "import failed"}, status=400)

            if session_data:
                import uuid as _uuid
                from datetime import datetime as _datetime

                session_id = session_data.get("session_id", _uuid.uuid4().hex[:12])
                safe = share_manager.sanitize_session_data(session_data)

                sessions_dir = Path.home() / ".apex" / "sessions"
                sessions_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{_datetime.now().strftime('%Y%m%d_%H%M%S')}_imported_{session_id}.json"
                filepath = sessions_dir / filename
                filepath.write_text(json.dumps(safe, indent=2))

                return web.json_response({"imported": True, "session_id": session_id})

            return web.json_response({"error": "file_path or data required"}, status=400)
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

    async def api_undo(self, request: web.Request) -> web.Response:
        """Undo last action."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        action = self.undo_manager.undo()
        if action:
            await self.event_bus.publish("undo", {"action": action.get("type")})
            return web.json_response(
                {
                    "undone": True,
                    "action": action.get("type"),
                    "details": action.get("details"),
                }
            )
        return web.json_response({"error": "nothing to undo"}, status=400)

    async def api_redo(self, request: web.Request) -> web.Response:
        """Redo last undone action."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        action = self.undo_manager.redo()
        if action:
            await self.event_bus.publish("redo", {"action": action.get("type")})
            return web.json_response(
                {
                    "redone": True,
                    "action": action.get("type"),
                    "details": action.get("details"),
                }
            )
        return web.json_response({"error": "nothing to redo"}, status=400)

    async def api_session_diff(self, request: web.Request) -> web.Response:
        """Get session diff (OpenCode /session/:id/diff compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        session_id = request.match_info.get("session_id", "")
        try:
            stat, diff_text, paths, fingerprint = self._collect_diff()
            return web.json_response(
                {
                    "files": stat or "(clean)",
                    "diff": diff_text,
                    "session_id": session_id,
                    "fingerprint": fingerprint,
                    "paths": paths,
                }
            )
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

    def _requested_diff_paths(self, raw_files: Any) -> tuple[list[str] | None, Any]:
        """Normalise the paths the client asked to act on.

        Returns ``(paths, error_response)``; ``paths`` is ``None`` when the
        client asked for every path of the diff.
        """
        if raw_files is None:
            return None, None
        if not isinstance(raw_files, list):
            return None, web.json_response({"error": "files must be a list"}, status=400)
        requested: list[str] = []
        for raw in raw_files:
            normalized = self._normalize_diff_path(raw)
            if normalized is None:
                return None, web.json_response({"error": f"invalid path: {raw!r}"}, status=400)
            requested.append(normalized)
        # Preserve preview order while restoring each path at most once.
        return list(dict.fromkeys(requested)), None

    def _check_fingerprint(self, supplied: Any, fingerprint: str) -> Any:
        """Verify the fingerprint the client previewed, if a reject is asked."""
        if not isinstance(supplied, str) or not supplied:
            return web.json_response({"error": "fingerprint required"}, status=400)
        if supplied != fingerprint:
            return web.json_response(
                {"error": "diff_changed", "fingerprint": fingerprint}, status=409
            )
        return None

    def _invalid_diff_paths(self, selected: list[str], current_paths: list[str]) -> Any:
        """Check the selected paths against the current diff and the working tree."""
        current_set = set(current_paths)
        cwd = Path(self.agent.cwd).resolve()
        for path in selected:
            if path not in current_set:
                return web.json_response({"error": f"path not in current diff: {path}"}, status=400)
            if not self._diff_path_within(cwd, path):
                return web.json_response(
                    {"error": f"path escapes working directory: {path}"}, status=400
                )
        return None

    def _revert_diff_paths(self, selected: list[str]) -> tuple[list[str], list[str]]:
        """Revert the selected paths; returns the reverted and the failed ones."""
        cwd = Path(self.agent.cwd).resolve()
        reverted: list[str] = []
        failed: list[str] = []
        for path in selected:
            if self._restore_diff_path(cwd, path) is None:
                reverted.append(path)
            else:
                failed.append(path)
        return reverted, failed

    async def _read_diff_decision(self, request: web.Request) -> tuple[dict | None, Any]:
        """Parse and validate the body of a diff-decision request.

        Returns ``(data, error_response)``.
        """
        try:
            data = await request.json()
        except (ValueError, TypeError):
            return None, web.json_response({"error": "invalid JSON body"}, status=400)
        if not isinstance(data, dict):
            return None, web.json_response({"error": "invalid JSON body"}, status=400)
        if data.get("decision") not in ("accept", "reject"):
            return None, web.json_response(
                {"error": "decision must be 'accept' or 'reject'"}, status=400
            )
        return data, None

    def _current_diff(self) -> tuple[list[str], str, Any]:
        """The changed paths and the fingerprint of the current working tree.

        Returns ``(paths, fingerprint, error_response)``.
        """
        try:
            _stat, _diff_text, current_paths, fingerprint = self._collect_diff()
        except Exception as e:  # noqa: BLE001
            return [], "", web.json_response({"error": str(e)}, status=500)
        return current_paths, fingerprint, None

    def _apply_diff_decision(self, decision: str, selected: list[str], fingerprint: str) -> dict:
        """Apply the accept/reject decision and return the response body."""
        if decision == "accept":
            return {"status": "accepted", "files": selected, "fingerprint": fingerprint}
        reverted, failed = self._revert_diff_paths(selected)
        return {
            "status": "rejected",
            "files": selected,
            "reverted": reverted,
            "failed": failed,
            "fingerprint": fingerprint,
        }

    async def api_session_diff_decision(self, request: web.Request) -> web.Response:
        """Accept or reject the previewed working-tree diff."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        data, body_error = await self._read_diff_decision(request)
        if body_error is not None:
            return body_error
        decision = data["decision"]

        requested, path_error = self._requested_diff_paths(data.get("files"))
        if path_error is not None:
            return path_error

        current_paths, fingerprint, diff_error = self._current_diff()
        if diff_error is not None:
            return diff_error

        selected = list(current_paths) if requested is None else requested

        if decision == "reject":
            fingerprint_error = self._check_fingerprint(data.get("fingerprint"), fingerprint)
            if fingerprint_error is not None:
                return fingerprint_error

        invalid = self._invalid_diff_paths(selected, current_paths)
        if invalid is not None:
            return invalid

        return web.json_response(self._apply_diff_decision(decision, selected, fingerprint))

    async def api_session_fork(self, request: web.Request) -> web.Response:
        """Fork current session (OpenCode /session/:id/fork compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        self.agent.reset_history()
        return web.json_response(
            {"forked": True, "session_id": request.match_info.get("session_id", "")}
        )

    async def api_session_abort(self, request: web.Request) -> web.Response:
        """Abort running session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        return web.json_response({"aborted": True})

    def _collect_diff(self) -> tuple[str, str, list[str], str]:
        """Return (stat, diff, changed paths, fingerprint) for the working tree."""
        cwd = Path(self.agent.cwd)
        stat = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=self._DIFF_GIT_TIMEOUT,
            check=False,
        )
        diff = subprocess.run(
            ["git", "diff"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=self._DIFF_GIT_TIMEOUT,
            check=False,
        )
        names = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=self._DIFF_GIT_TIMEOUT,
            check=False,
        )
        diff_text = diff.stdout or ""
        paths = [line.strip() for line in (names.stdout or "").splitlines() if line.strip()]
        return (
            stat.stdout.strip(),
            diff_text,
            paths,
            hashlib.sha256(diff_text.encode("utf-8")).hexdigest(),
        )

    @staticmethod
    def _normalize_diff_path(raw: Any) -> str | None:
        """Validate a client path as repo-relative, POSIX-style, without `..`."""
        if not isinstance(raw, str):
            return None
        candidate = raw.strip().replace("\\", "/")
        if not candidate or "\x00" in candidate:
            return None
        if _is_absolute_diff_path(candidate):
            return None
        if any(part == ".." for part in candidate.split("/")):
            return None
        return candidate

    @staticmethod
    def _diff_path_within(root: Path, relative_path: str) -> bool:
        """True when the path resolves inside the repository root."""
        try:
            (root / relative_path).resolve().relative_to(root)
        except (OSError, ValueError):
            return False
        return True

    def _restore_diff_path(self, root: Path, relative_path: str) -> str | None:
        """Restore one tracked path in the working tree; None means success."""
        last_error = ""
        for command in (
            ["git", "restore", "--worktree", "--", relative_path],
            ["git", "checkout", "--", relative_path],
        ):
            error = self._run_git_restore(root, command)
            if error is None:
                return None
            last_error = error
        return last_error or f"could not restore {relative_path}"

    def _run_git_restore(self, root: Path, command: list[str]) -> str | None:
        """Run one restore command; ``None`` means the file was restored."""
        try:
            result = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=self._DIFF_GIT_TIMEOUT,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return str(exc)
        if result.returncode == 0:
            return None
        return (result.stderr or result.stdout or "").strip() or (
            f"git exited with {result.returncode}"
        )
