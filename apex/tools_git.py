"""Git tools: status, history, branches, staging, commits and pull requests.

Split out of ``apex.tools`` so that module keeps a single
responsibility: the tool executor core.
"""

from __future__ import annotations

import subprocess
from typing import Any

from .shell_security import shell_analyzer

__all__ = [
    "GitToolsMixin",
]


class GitToolsMixin:
    def _execute_get_git_status(self, args: dict[str, Any]) -> str:
        if not (self.cwd / ".git").exists():
            return "ERROR: Not a git repository"
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            if not result.stdout.strip():
                return "[working tree clean]"
            return result.stdout
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Git status failed: {e}"

    def _execute_get_git_log(self, args: dict[str, Any]) -> str:
        n = args.get("n", 10)
        if not (self.cwd / ".git").exists():
            return "ERROR: Not a git repository"
        try:
            result = subprocess.run(
                ["git", "log", f"-{n}", "--oneline", "--decorate"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.stdout or "[no commits]"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Git log failed: {e}"

    def _execute_git_diff(self, args: dict[str, Any]) -> str:
        ref = args.get("ref")
        if not (self.cwd / ".git").exists():
            return "ERROR: Not a git repository"
        try:
            cmd = ["git", "diff"]
            if ref:
                cmd.append(ref)
            result = subprocess.run(cmd, cwd=self.cwd, capture_output=True, text=True, check=False)
            return result.stdout or "[no changes]"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Git diff failed: {e}"

    def _execute_git_create_branch(self, args: dict[str, Any]) -> str:
        name = args["name"]
        checkout = args.get("checkout", False)
        try:
            cmd = ["git", "branch", name]
            subprocess.run(cmd, cwd=self.cwd, capture_output=True, check=False)
            if checkout:
                subprocess.run(
                    ["git", "checkout", name], cwd=self.cwd, capture_output=True, check=False
                )
            return f"SUCCESS: Created branch '{name}'" + (" and checked out" if checkout else "")
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {e}"

    def _execute_git_switch_branch(self, args: dict[str, Any]) -> str:
        name = args["name"]
        try:
            subprocess.run(
                ["git", "checkout", name], cwd=self.cwd, capture_output=True, check=False
            )
            return f"SUCCESS: Switched to branch '{name}'"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {e}"

    def _execute_git_delete_branch(self, args: dict[str, Any]) -> str:
        name = args["name"]
        force = args.get("force", False)
        try:
            cmd = ["git", "branch", "-D" if force else "-d", name]
            subprocess.run(cmd, cwd=self.cwd, capture_output=True, check=False)
            return f"SUCCESS: Deleted branch '{name}'"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {e}"

    def _execute_git_list_branches(self, args: dict[str, Any]) -> str:
        try:
            result = subprocess.run(
                ["git", "branch", "-a"], cwd=self.cwd, capture_output=True, text=True, check=False
            )
            return f"Branches:\n{result.stdout}"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {e}"

    def _create_pr_with_gh(self, title: str, body: str, base: str, head: str | None) -> str | None:
        """Create the pull request with the ``gh`` CLI, if it is installed."""
        import shutil

        if not shutil.which("gh"):
            return None
        cmd = ["gh", "pr", "create", "--title", title, "--base", base]
        if body:
            cmd += ["--body", body]
        if head:
            cmd += ["--head", head]
        result = subprocess.run(
            cmd, cwd=self.cwd, capture_output=True, text=True, timeout=60, check=False
        )
        if result.returncode == 0:
            return result.stdout.strip() or "PR created."
        return f"ERROR: gh pr create failed: {result.stderr.strip()}"

    def _git_output(self, *args: str) -> str:
        """Run a git command and return its trimmed standard output."""
        return subprocess.run(
            ["git", *args],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

    def _create_pr_with_api(self, title: str, body: str, base: str, head: str | None) -> str:
        """Create the pull request through the GitHub REST API."""
        import json as _json
        import os
        import urllib.request

        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            return "ERROR: gh CLI not found and no GITHUB_TOKEN/GH_TOKEN set."
        # Resolve owner/repo from git remote.
        remote = self._git_output("remote", "get-url", "origin")
        import re

        m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote)
        if not m:
            return "ERROR: Could not parse GitHub remote URL."
        repo = m.group(1)
        # Determine head branch.
        if not head:
            head = self._git_output("branch", "--show-current")
        payload = _json.dumps({"title": title, "body": body, "base": base, "head": head}).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/pulls",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "User-Agent": "APEX",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read().decode())
        return data.get("html_url", "PR created.")

    def _execute_git_create_pr(self, args: dict[str, Any]) -> str:
        title = args.get("title", "")
        body = args.get("body", "")
        base = args.get("base", "main")
        head = args.get("head")
        try:
            # Prefer gh CLI when available.
            via_cli = self._create_pr_with_gh(title, body, base, head)
            if via_cli is not None:
                return via_cli
            # Fallback: GitHub REST API using GITHUB_TOKEN/GH_TOKEN.
            return self._create_pr_with_api(title, body, base, head)
        except Exception as e:  # noqa: BLE001
            return f"ERROR: PR creation failed: {e}"

    def _execute_git_stage(self, args: dict[str, Any]) -> str:
        files = args.get("files", [])
        if not files:
            return "ERROR: No files specified"

        try:
            subprocess.run(["git", "add"] + files, cwd=self.cwd, capture_output=True, check=False)
            return f"SUCCESS: Staged {len(files)} file(s)"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {e}"

    def _execute_git_unstage(self, args: dict[str, Any]) -> str:
        files = args.get("files", [])
        try:
            if files:
                subprocess.run(
                    ["git", "reset"] + files, cwd=self.cwd, capture_output=True, check=False
                )
            else:
                subprocess.run(
                    ["git", "reset", "HEAD"], cwd=self.cwd, capture_output=True, check=False
                )
            return "SUCCESS: Unstaged files"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {e}"

    def _execute_git_commit(self, args: dict[str, Any]) -> str:
        message = args.get("message", "")
        if not message:
            return "ERROR: No commit message"

        try:
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return f"SUCCESS: Committed\n{result.stdout}"
            return f"ERROR: {result.stderr}"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {e}"

    def _execute_git_pre_commit(self, args: dict[str, Any]) -> str:
        import subprocess

        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            if not result.stdout.strip():
                return "Nothing to commit (working tree clean)"

            staged = subprocess.run(
                ["git", "diff", "--cached", "--stat"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            return (
                f"Pre-commit checks:\nStaged: {staged.stdout or 'none'}\nUnstaged: {result.stdout}"
            )
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {e}"

    def _execute_add_git_hook(self, args: dict[str, Any]) -> str:
        hook = args["hook"]
        command = args["command"]

        valid_hooks = {
            "applypatch-msg",
            "pre-applypatch",
            "post-applypatch",
            "pre-commit",
            "pre-merge-commit",
            "prepare-commit-msg",
            "commit-msg",
            "post-commit",
            "pre-rebase",
            "post-checkout",
            "post-merge",
            "pre-push",
            "pre-receive",
            "update",
            "post-receive",
            "post-update",
            "push-to-checkout",
            "pre-auto-gc",
            "post-rewrite",
            "sendemail-validate",
            "fsmonitor-watchman",
        }
        if hook not in valid_hooks:
            return f"ERROR: Invalid git hook name: {hook}. Valid hooks: {', '.join(sorted(valid_hooks))}"

        git_dir = self.cwd / ".git"
        if not git_dir.exists():
            return "ERROR: Not a git repository"

        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        hook_path = hooks_dir / hook
        analysis = shell_analyzer.analyze(command)
        if not analysis.safe:
            return f"ERROR: Command rejected by security analyzer: {analysis.category}"
        hook_path.write_text(f"""#!/bin/sh
{command}
""")
        hook_path.chmod(0o755)
        return f"SUCCESS: Added {hook} hook"
