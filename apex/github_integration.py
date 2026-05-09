"""GitHub integration - PRs, Issues, and automation."""

import os
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime


@dataclass
class GitHubIssue:
    """GitHub issue representation."""
    number: int
    title: str
    body: str
    state: str
    labels: list[str]
    assignee: str | None


@dataclass
class GitHubPR:
    """GitHub pull request representation."""
    number: int
    title: str
    body: str
    state: str
    head: str
    base: str
    url: str


class GitHubClient:
    """GitHub API client for PRs, Issues, and more."""

    def __init__(self, token: str | None = None, owner: str = "", repo: str = ""):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.owner = owner
        self.repo = repo
        self._api_base = "https://api.github.com"

    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def _run_gh(self, *args) -> tuple[int, str, str]:
        """Run gh CLI command."""
        try:
            result = subprocess.run(
                ["gh"] + list(args),
                capture_output=True,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            return -1, "", "gh not found"

    def _api_request(self, method: str, path: str, data: dict | None = None) -> dict | None:
        """Make GitHub API request."""
        import urllib.request
        import urllib.parse

        url = f"{self._api_base}{path}"
        headers = self._get_headers()

        req = urllib.request.Request(url, headers=headers, method=method)

        if data:
            req.data = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"

        try:
            response = urllib.request.urlopen(req)
            return json.loads(response.read().decode())
        except Exception:
            return None

    def set_repo(self, owner: str, repo: str):
        """Set repository context."""
        self.owner = owner
        self.repo = repo

    def detect_repo(self) -> tuple[str, str] | None:
        """Detect current repo from git config."""
        code, remote, _ = self._run_gh("repo", "view", "--json", "owner,name")
        if code == 0:
            try:
                data = json.loads(remote)
                return data.get("owner", {}).get("login"), data.get("name")
            except:
                pass
        return None

    def list_issues(self, state: str = "open", labels: str = "") -> list[dict]:
        """List repository issues."""
        path = f"/repos/{self.owner}/{self.repo}/issues"
        if state:
            path += f"?state={state}"
        if labels:
            path += f"&labels={labels}"

        result = self._api_request("GET", path)
        return result if result else []

    def get_issue(self, issue_num: int) -> dict | None:
        """Get a specific issue."""
        path = f"/repos/{self.owner}/{self.repo}/issues/{issue_num}"
        return self._api_request("GET", path)

    def create_issue(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None
    ) -> dict | None:
        """Create a new issue."""
        path = f"/repos/{self.owner}/{self.repo}/issues"
        data = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        return self._api_request("POST", path, data)

    def close_issue(self, issue_num: int) -> bool:
        """Close an issue."""
        path = f"/repos/{self.owner}/{self.repo}/issues/{issue_num}"
        result = self._api_request("PATCH", path, {"state": "closed"})
        return result is not None

    def list_prs(self, state: str = "open") -> list[dict]:
        """List pull requests."""
        path = f"/repos/{self.owner}/{self.repo}/pulls?state={state}"
        result = self._api_request("GET", path)
        return result if result else []

    def get_pr(self, pr_num: int) -> dict | None:
        """Get a specific PR."""
        path = f"/repos/{self.owner}/{self.repo}/pulls/{pr_num}"
        return self._api_request("GET", path)

    def create_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> dict | None:
        """Create a pull request."""
        path = f"/repos/{self.owner}/{self.repo}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }
        return self._api_request("POST", path, data)

    def merge_pr(self, pr_num: int, method: str = "squash") -> bool:
        """Merge a pull request."""
        path = f"/repos/{self.owner}/{self.repo}/pulls/{pr_num}/merge"
        result = self._api_request("PUT", path, {"merge_method": method})
        return result is not None and "merged" in str(result)

    def create_branch(self, branch_name: str, base: str = "main") -> bool:
        """Create a new branch."""
        code, _, _ = self._run_gh("git", "checkout", "-b", branch_name, f"origin/{base}")
        return code == 0


class GitHubAutomation:
    """High-level GitHub automation."""

    def __init__(self, token: str = ""):
        self.client = GitHubClient(token)
        self._repo = self.client.detect_repo()
        if self._repo:
            self.client.set_repo(*self._repo)

    def auto_create_pr(
        self,
        title: str,
        description: str,
        branch: str,
        base: str = "main"
    ) -> dict | None:
        """Automatically create branch and PR."""
        if not self._repo:
            return None

        self.client.create_branch(branch, base)
        return self.client.create_pr(title, description, branch, base)

    def create_issue_from_error(self, error_msg: str, file_path: str) -> dict | None:
        """Create an issue from an error message."""
        if not self._repo:
            return None

        title = f"Bug: {error_msg[:50]}..."
        body = f"""## Error
```
{error_msg}
```

## Location
- File: `{file_path}`
- Timestamp: {datetime.now().isoformat()}

## Steps to Reproduce
1. (Add steps here)

## Expected Behavior
(Describe what should happen)
"""
        return self.client.create_issue(title, body, ["bug"])

    def create_pr_for_changes(self, changes: list[str]) -> dict | None:
        """Create a PR describing file changes."""
        if not self._repo:
            return None

        branch = f"apex-changes-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        title = "APEX: Automated changes"
        body = "## Changes\n" + "\n".join(f"- {f}" for f in changes[:10])

        if len(changes) > 10:
            body += f"\n\n... and {len(changes) - 10} more files"

        return self.auto_create_pr(title, body, branch)

    def list_issues_by_label(self, label: str) -> list[dict]:
        """List issues with a specific label."""
        return self.client.list_issues(labels=label)

    def get_issue_todos(self) -> list[dict]:
        """Get issues marked as todo."""
        return self.list_issues_by_label("todo")

    def close_completed_prs(self) -> int:
        """Close merged PRs."""
        prs = self.client.list_prs("merged")
        count = 0
        for pr in prs:
            if pr.get("merged_at"):
                count += 1
        return count


gh_client = GitHubClient()
gh_automation = GitHubAutomation()