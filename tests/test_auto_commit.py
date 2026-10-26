"""Tests for apex/auto_commit.py — message sanitization, git staging, failure paths."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from apex import auto_commit as ac
from apex.auto_commit import (
    auto_commit,
    generate_commit_message,
    has_changes,
    is_git_repo,
    sanitize_message,
)

FALLBACK = "chore: auto commit after apex task"


def _git(cwd, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A git repo with one commit and repo-local identity (hermetic)."""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "Apex Test")
    _git(tmp_path, "config", "user.email", "apex@test.local")
    (tmp_path / "initial.txt").write_text("start\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "chore: initial")
    return tmp_path


# ---------------------------------------------------------------------------
# sanitize_message
# ---------------------------------------------------------------------------


class TestSanitizeMessage:
    def test_none_and_empty(self):
        assert sanitize_message(None) is None
        assert sanitize_message("") is None

    def test_valid_message_unchanged(self):
        assert sanitize_message("feat: add login") == "feat: add login"

    def test_scope_preserved(self):
        assert sanitize_message("fix(ci): fix glob") == "fix(ci): fix glob"

    def test_breaking_bang_preserved(self):
        assert sanitize_message("feat!: drop legacy") == "feat!: drop legacy"

    def test_trailing_punctuation_stripped(self):
        assert sanitize_message("feat: add login.") == "feat: add login"

    def test_first_line_used(self):
        assert sanitize_message("feat: add login\nbody line") == "feat: add login"

    def test_wrapping_quotes_stripped(self):
        assert sanitize_message('"feat: add login"') == "feat: add login"
        assert sanitize_message("`feat: add login`") == "feat: add login"

    def test_commit_message_prefix_stripped(self):
        assert sanitize_message("Commit message: feat: add login") == "feat: add login"

    def test_subject_whitespace_collapsed(self):
        assert sanitize_message("feat:  add    login") == "feat: add login"

    def test_long_subject_truncated(self):
        out = sanitize_message("feat: " + "a" * 100)
        assert out is not None
        assert out.startswith("feat: ")
        assert out.endswith("…")
        subject = out[len("feat: ") :]
        assert len(subject) == 72

    def test_uppercase_type_rejected(self):
        assert sanitize_message("Feat: add login") is None

    def test_invalid_type_rejected(self):
        assert sanitize_message("foo: add login") is None


# ---------------------------------------------------------------------------
# repo helpers
# ---------------------------------------------------------------------------


class TestRepoHelpers:
    def test_is_git_repo(self, repo):
        assert is_git_repo(repo) is True
        with tempfile.TemporaryDirectory() as d:
            assert is_git_repo(d) is False

    def test_has_changes(self, repo):
        assert has_changes(repo) is False
        (repo / "x.txt").write_text("x\n")
        assert has_changes(repo) is True


# ---------------------------------------------------------------------------
# generate_commit_message
# ---------------------------------------------------------------------------


class TestGenerateCommitMessage:
    def test_llm_message_sanitized(self, repo):
        (repo / "f.txt").write_text("x\n")
        out = generate_commit_message(repo, task="t", llm=lambda p: "feat: add f")
        assert out == "feat: add f"

    def test_llm_garbage_falls_back(self, repo):
        (repo / "f.txt").write_text("x\n")
        out = generate_commit_message(repo, task="t", llm=lambda p: "blah blah")
        assert out == FALLBACK

    def test_llm_exception_falls_back(self, repo):
        (repo / "f.txt").write_text("x\n")

        def boom(_p: str) -> str:
            raise RuntimeError("no llm available")

        out = generate_commit_message(repo, task="t", llm=boom)
        assert out == FALLBACK

    def test_llm_receives_task_and_diff(self, repo):
        (repo / "f.txt").write_text("hello\n")
        seen: dict[str, str] = {}

        def spy(p: str) -> str:
            seen["p"] = p
            return "feat: add f"

        generate_commit_message(repo, task="my task", llm=spy)
        assert "my task" in seen["p"]
        assert "f.txt" in seen["p"]


# ---------------------------------------------------------------------------
# auto_commit
# ---------------------------------------------------------------------------


class TestAutoCommit:
    def test_not_a_repo(self, tmp_path):
        with tempfile.TemporaryDirectory() as d:
            out = auto_commit(d)
        assert out["status"] == "not-a-repo"
        assert str(Path(d)) in out["cwd"]

    def test_no_changes(self, repo):
        out = auto_commit(repo)
        assert out["status"] == "no-changes"

    def test_commits_with_llm_message(self, repo):
        (repo / "new.txt").write_text("data\n")
        out = auto_commit(repo, task="add data", llm=lambda p: "feat: add data file")
        assert out["status"] == "committed"
        assert out["message"] == "feat: add data file"
        assert len(out["sha"]) == 40
        assert _git(repo, "log", "-1", "--pretty=%s") == "feat: add data file"
        assert _git(repo, "status", "--porcelain") == ""

    def test_untracked_files_included(self, repo):
        (repo / "a.txt").write_text("1\n")
        (repo / "b.txt").write_text("2\n")
        out = auto_commit(repo, llm=lambda p: "feat: add a and b")
        assert out["status"] == "committed"
        names = _git(repo, "show", "--name-only", "--pretty=", "HEAD")
        assert "a.txt" in names
        assert "b.txt" in names

    def test_commit_failure_rolls_back_staging(self, repo, monkeypatch):
        (repo / "new.txt").write_text("data\n")
        real = ac._run_git

        def fake(cwd, *args):
            if args and args[0] == "commit":
                return subprocess.CompletedProcess(
                    args=["git", *args],
                    returncode=128,
                    stdout="",
                    stderr="commit failed (forced)\n",
                )
            return real(cwd, *args)

        monkeypatch.setattr(ac, "_run_git", fake)
        out = auto_commit(repo, llm=lambda p: "feat: x")
        assert out["status"] == "error"
        assert "git commit failed" in out["error"]
        # Rollback: nothing staged, the file stays in the working tree.
        assert _git(repo, "status", "--porcelain") == "?? new.txt"
        assert _git(repo, "rev-list", "--count", "HEAD") == "1"

    def test_add_failure_reports_error(self, repo, monkeypatch):
        (repo / "new.txt").write_text("data\n")
        real = ac._run_git

        def fake(cwd, *args):
            if args and args[0] == "add":
                return subprocess.CompletedProcess(
                    args=["git", *args],
                    returncode=128,
                    stdout="",
                    stderr="add failed (forced)\n",
                )
            return real(cwd, *args)

        monkeypatch.setattr(ac, "_run_git", fake)
        out = auto_commit(repo, llm=lambda p: "feat: x")
        assert out["status"] == "error"
        assert "git add failed" in out["error"]
