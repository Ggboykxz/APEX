"""Tests for github_integration module."""

from apex.github_integration import (
    GitHubIssue, GitHubPR, GitHubClient, GitHubAutomation, gh_client, gh_automation
)


class TestGitHubIssue:
    """Test GitHubIssue dataclass."""

    def test_init(self):
        """Test initialization."""
        issue = GitHubIssue(
            number=1,
            title="Test Issue",
            body="Issue body",
            state="open",
            labels=["bug"],
            assignee="user"
        )
        assert issue.number == 1
        assert issue.title == "Test Issue"
        assert issue.state == "open"


class TestGitHubPR:
    """Test GitHubPR dataclass."""

    def test_init(self):
        """Test initialization."""
        pr = GitHubPR(
            number=1,
            title="Test PR",
            body="PR body",
            state="open",
            head="feature",
            base="main",
            url="https://github.com/test/repo/pull/1"
        )
        assert pr.number == 1
        assert pr.head == "feature"
        assert pr.base == "main"


class TestGitHubClient:
    """Test GitHubClient class."""

    def test_init_with_params(self):
        """Test initialization with params."""
        client = GitHubClient(token="test", owner="owner", repo="repo")
        assert client.token == "test"
        assert client.owner == "owner"
        assert client.repo == "repo"

    def test_set_repo(self):
        """Test set_repo method."""
        client = GitHubClient()
        client.set_repo("new-owner", "new-repo")
        assert client.owner == "new-owner"
        assert client.repo == "new-repo"


class TestGitHubAutomation:
    """Test GitHubAutomation class."""

    def test_init_with_token(self):
        """Test initialization with token."""
        automation = GitHubAutomation(token="test")
        assert automation.client.token == "test"


class TestGlobalInstances:
    """Test global instances."""

    def test_gh_client_global(self):
        """Test global gh_client."""
        assert gh_client is not None

    def test_gh_automation_global(self):
        """Test global gh_automation."""
        assert gh_automation is not None