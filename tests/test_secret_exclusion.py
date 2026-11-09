"""Tests for secret-exclusion guarantees (audit recommendation U3)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_env_file_is_git_ignored(tmp_path: Path) -> None:
    """`.env` must never be committed: it may contain API keys."""
    repo_root = Path(__file__).resolve().parents[1]
    env_file = repo_root / ".env"
    # Create a temporary .env to confirm git would ignore it.
    env_file.write_text("OPENROUTER_API_KEY=sk-test\n", encoding="utf-8")
    try:
        result = subprocess.run(
            ["git", "check-ignore", ".env"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, ".env is not git-ignored"
        assert ".env" in result.stdout
    finally:
        if env_file.exists():
            env_file.unlink()


def test_env_example_is_not_git_ignored() -> None:
    """`.env.example` may be committed (it contains no real secrets)."""
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "check-ignore", ".env.example"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, ".env.example should be committable"


def test_auth_json_is_outside_repo() -> None:
    """`auth.json` lives in the user config dir, not in the repository."""
    from apex.cli_auth import _openrouter_auth_file

    auth_file = _openrouter_auth_file()
    repo_root = Path(__file__).resolve().parents[1]
    assert not auth_file.is_relative_to(repo_root), "auth.json must not live inside the repository"
