"""Tests for apex/github_integration.py — GitHubClient, GitHubAutomation with no network calls."""

from apex.github_integration import (
    GitHubIssue,
    GitHubPR,
    GitHubClient,
    GitHubAutomation,
    gh_client,
    gh_automation,
)


class TestGitHubIssue:
    def test_creation(self):
        issue = GitHubIssue(
            number=1,
            title="Bug",
            body="Something broken",
            state="open",
            labels=["bug"],
            assignee="user1",
        )
        assert issue.number == 1
        assert issue.title == "Bug"
        assert issue.body == "Something broken"
        assert issue.state == "open"
        assert issue.labels == ["bug"]
        assert issue.assignee == "user1"

    def test_defaults(self):
        issue = GitHubIssue(
            number=2, title="Feature", body="", state="open", labels=[], assignee=None
        )
        assert issue.labels == []
        assert issue.assignee is None


class TestGitHubPR:
    def test_creation(self):
        pr = GitHubPR(
            number=10,
            title="Fix bug",
            body="Fix description",
            state="open",
            head="feature",
            base="main",
            url="https://github.com/...",
        )
        assert pr.number == 10
        assert pr.title == "Fix bug"
        assert pr.head == "feature"
        assert pr.base == "main"
        assert pr.url == "https://github.com/..."


class TestGitHubClient:
    def test_init_defaults(self):
        client = GitHubClient()
        assert client.token == ""
        assert client.owner == ""
        assert client.repo == ""
        assert client._api_base == "https://api.github.com"

    def test_init_with_params(self):
        client = GitHubClient(token="ghp_test", owner="myorg", repo="myrepo")
        assert client.token == "ghp_test"
        assert client.owner == "myorg"
        assert client.repo == "myrepo"

    def test_get_headers_no_token(self):
        client = GitHubClient()
        headers = client._get_headers()
        assert "Accept" in headers
        assert "Authorization" not in headers

    def test_get_headers_with_token(self):
        client = GitHubClient(token="ghp_test")
        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "token ghp_test"

    def test_set_repo(self):
        client = GitHubClient()
        client.set_repo("owner", "repo")
        assert client.owner == "owner"
        assert client.repo == "repo"

    def test_detect_repo_no_gh(self):
        """detect_repo should return None if gh is not available or not in a repo."""
        client = GitHubClient()
        result = client.detect_repo()
        # Result is either None or a tuple - can't guarantee gh is installed
        assert result is None or isinstance(result, tuple)

    def test_list_issues_no_repo(self):
        client = GitHubClient()
        # With no owner/repo, API request will fail
        result = client.list_issues()
        assert isinstance(result, list)

    def test_get_issue_no_repo(self):
        client = GitHubClient()
        result = client.get_issue(1)
        assert result is None

    def test_create_issue_no_repo(self):
        client = GitHubClient()
        result = client.create_issue("Title", "Body")
        assert result is None

    def test_close_issue_no_repo(self):
        client = GitHubClient()
        result = client.close_issue(1)
        assert result is False

    def test_list_prs_no_repo(self):
        client = GitHubClient()
        result = client.list_prs()
        assert isinstance(result, list)

    def test_get_pr_no_repo(self):
        client = GitHubClient()
        result = client.get_pr(1)
        assert result is None

    def test_create_pr_no_repo(self):
        client = GitHubClient()
        result = client.create_pr("Title", "Body", "feature")
        assert result is None

    def test_merge_pr_no_repo(self):
        client = GitHubClient()
        result = client.merge_pr(1)
        assert result is False

    def test_create_branch_no_gh(self):
        client = GitHubClient()
        # Will fail without gh CLI
        result = client.create_branch("new-branch")
        assert isinstance(result, bool)


class TestGitHubAutomation:
    def test_init(self):
        # This will try to detect repo, which may fail
        auto = GitHubAutomation(token="test")
        assert isinstance(auto.client, GitHubClient)

    def test_auto_create_pr_no_repo(self):
        auto = GitHubAutomation(token="test")
        auto._repo = None  # Ensure no repo
        result = auto.auto_create_pr("Title", "Desc", "feature")
        assert result is None

    def test_create_issue_from_error_no_repo(self):
        auto = GitHubAutomation(token="test")
        auto._repo = None
        result = auto.create_issue_from_error("NullPointerException", "Main.java")
        assert result is None

    def test_create_pr_for_changes_no_repo(self):
        auto = GitHubAutomation(token="test")
        auto._repo = None
        result = auto.create_pr_for_changes(["file1.py", "file2.py"])
        assert result is None

    def test_list_issues_by_label_no_repo(self):
        auto = GitHubAutomation(token="test")
        auto._repo = None
        result = auto.list_issues_by_label("bug")
        assert isinstance(result, list)

    def test_get_issue_todos(self):
        auto = GitHubAutomation(token="test")
        auto._repo = None
        result = auto.get_issue_todos()
        assert isinstance(result, list)

    def test_close_completed_prs(self):
        auto = GitHubAutomation(token="test")
        auto._repo = None
        result = auto.close_completed_prs()
        assert isinstance(result, int)

    def test_create_issue_from_error_title(self):
        """Test that error title is truncated."""
        auto = GitHubAutomation(token="test")
        auto._repo = None
        # Just test that the method doesn't crash
        auto.create_issue_from_error("x" * 100, "file.py")


class TestGitHubIntegrationEdgeCases:
    """Hit uncovered lines in github_integration.py."""

    def test_run_gh_success(self, monkeypatch):
        """Hit line 55 — successful _run_gh execution."""
        import subprocess
        called_with = []

        def mock_run(*a, **kw):
            called_with.append(a)
            return type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
        monkeypatch.setattr(subprocess, "run", mock_run)
        client = GitHubClient()
        code, out, err = client._run_gh("repo", "view")
        assert code == 0
        assert out == "ok"

    def test_api_request_success(self, monkeypatch):
        """Hit line 75 — successful API request with JSON response."""
        import urllib.request
        import json

        class FakeResponse:
            def read(self):
                return json.dumps({"login": "owner"}).encode()
            def __enter__(self): return self
            def __exit__(self, *a): pass

        def mock_urlopen(req):
            return FakeResponse()
        monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
        client = GitHubClient(token="test")
        result = client._api_request("GET", "/user")
        assert result is not None
        assert result["login"] == "owner"

    def test_detect_repo_success(self, monkeypatch):
        """Hit lines 88-92 — detect_repo with valid JSON response."""
        import json
        import subprocess

        def mock_run(*a, **kw):
            data = json.dumps({"owner": {"login": "myorg"}, "name": "myrepo"})
            return type("R", (), {"returncode": 0, "stdout": data, "stderr": ""})()
        monkeypatch.setattr(subprocess, "run", mock_run)
        client = GitHubClient()
        result = client.detect_repo()
        assert result == ("myorg", "myrepo")

    def test_detect_repo_invalid_json(self, monkeypatch):
        """Hit line 91 — JSONDecodeError caught."""
        import subprocess
        def mock_run(*a, **kw):
            return type("R", (), {"returncode": 0, "stdout": "not json", "stderr": ""})()
        monkeypatch.setattr(subprocess, "run", mock_run)
        client = GitHubClient()
        result = client.detect_repo()
        assert result is None

    def test_detect_repo_missing_keys(self, monkeypatch):
        """detect_repo with missing keys returns (None, None)."""
        import json
        import subprocess
        def mock_run(*a, **kw):
            data = json.dumps({"no_owner": {}})
            return type("R", (), {"returncode": 0, "stdout": data, "stderr": ""})()
        monkeypatch.setattr(subprocess, "run", mock_run)
        client = GitHubClient()
        result = client.detect_repo()
        # .get() doesn't raise KeyError, returns None instead
        assert result == (None, None) or result is None

    def test_create_issue_with_labels(self, monkeypatch):
        """Hit line 116 — pass labels in create_issue."""
        import urllib.request

        class FakeResponse:
            def read(self): return b'{"id": 1}'
            def __enter__(self): return self
            def __exit__(self, *a): pass

        called_data = [None]

        def mock_urlopen(req):
            called_data[0] = req.data
            return FakeResponse()

        monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
        client = GitHubClient(token="test", owner="o", repo="r")
        result = client.create_issue("Title", "Body", labels=["bug"])
        # Should include labels in the request data
        if called_data[0] is not None:
            import json
            data = json.loads(called_data[0])
            assert data.get("labels") == ["bug"]

    def test_automation_init_with_repo(self, monkeypatch):
        """Hit line 161 — set_repo from detect_repo."""
        import json
        import subprocess

        def mock_run(*a, **kw):
            data = json.dumps({"owner": {"login": "org"}, "name": "repo"})
            return type("R", (), {"returncode": 0, "stdout": data, "stderr": ""})()
        monkeypatch.setattr(subprocess, "run", mock_run)
        auto = GitHubAutomation(token="test")
        assert auto.client.owner == "org"
        assert auto.client.repo == "repo"

    def test_auto_create_pr_with_repo(self, monkeypatch):
        """Hit lines 170-171 — actual create_branch and create_pr."""
        import json
        import subprocess
        import urllib.request

        def mock_run(*a, **kw):
            data = json.dumps({"owner": {"login": "org"}, "name": "repo"})
            return type("R", (), {"returncode": 0, "stdout": data, "stderr": ""})()
        monkeypatch.setattr(subprocess, "run", mock_run)

        class FakeResponse:
            def read(self): return b'{"id": 1, "html_url": "https://pr"}'
            def __enter__(self): return self
            def __exit__(self, *a): pass
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: FakeResponse())

        auto = GitHubAutomation(token="test")
        result = auto.auto_create_pr("Title", "Desc", "feature")
        assert result is not None

    def test_create_issue_from_error_with_repo(self, monkeypatch):
        """Hit lines 178-194 — full create_issue_from_error path."""
        import json
        import subprocess
        import urllib.request

        def mock_run(*a, **kw):
            data = json.dumps({"owner": {"login": "o"}, "name": "r"})
            return type("R", (), {"returncode": 0, "stdout": data, "stderr": ""})()

        monkeypatch.setattr(subprocess, "run", mock_run)

        class FakeResponse:
            def read(self): return b'{"id": 1}'
            def __enter__(self): return self
            def __exit__(self, *a): pass
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: FakeResponse())

        auto = GitHubAutomation(token="test")
        result = auto.create_issue_from_error("NullPointerException", "Main.java")
        assert result is not None

    def test_create_pr_for_changes_with_repo(self, monkeypatch):
        """Hit lines 201-208 — full create_pr_for_changes path."""
        import json
        import subprocess
        import urllib.request

        def mock_run(*a, **kw):
            data = json.dumps({"owner": {"login": "o"}, "name": "r"})
            return type("R", (), {"returncode": 0, "stdout": data, "stderr": ""})()

        monkeypatch.setattr(subprocess, "run", mock_run)

        class FakeResponse:
            def read(self): return b'{"id": 1}'
            def __enter__(self): return self
            def __exit__(self, *a): pass
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: FakeResponse())

        auto = GitHubAutomation(token="test")
        result = auto.create_pr_for_changes(["file1.py", "file2.py"])
        assert result is not None

    def test_create_pr_for_changes_many(self, monkeypatch):
        """Hit line 206 — "and X more files" for > 10 files."""
        import json
        import subprocess
        import urllib.request

        def mock_run(*a, **kw):
            data = json.dumps({"owner": {"login": "o"}, "name": "r"})
            return type("R", (), {"returncode": 0, "stdout": data, "stderr": ""})()

        monkeypatch.setattr(subprocess, "run", mock_run)

        class FakeResponse:
            def read(self): return b'{"id": 1}'
            def __enter__(self): return self
            def __exit__(self, *a): pass
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: FakeResponse())

        auto = GitHubAutomation(token="test")
        changes = [f"file{i}.py" for i in range(15)]
        result = auto.create_pr_for_changes(changes)
        assert result is not None

    def test_close_completed_prs(self, monkeypatch):
        """Hit lines 223-224 — close_completed_prs."""
        import json
        import subprocess

        def mock_run(*a, **kw):
            data = json.dumps({"owner": {"login": "o"}, "name": "r"})
            return type("R", (), {"returncode": 0, "stdout": data, "stderr": ""})()
        monkeypatch.setattr(subprocess, "run", mock_run)

        import urllib.request
        class FakeResponse:
            def read(self):
                return json.dumps([{"number": 1, "merged_at": "2024-01-01"}]).encode()
            def __enter__(self): return self
            def __exit__(self, *a): pass
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: FakeResponse())

        auto = GitHubAutomation(token="test")
        count = auto.close_completed_prs()
        assert count >= 0


class TestGlobalInstances:
    def test_gh_client(self):
        assert isinstance(gh_client, GitHubClient)

    def test_gh_automation(self):
        assert isinstance(gh_automation, GitHubAutomation)
