"""Tests for APEX session sharing — no mocks, real objects and file system."""

import json
import re

import pytest

from apex.share import ShareManager, share_manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Redirect home directory to tmp_path for isolated file operations."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def share_mgr(home):
    """ShareManager with an isolated home directory and no config."""
    return ShareManager()


@pytest.fixture
def share_mgr_with_config(home):
    """ShareManager with a custom config file (share mode = auto)."""
    cfg_path = home / "config.json"
    cfg_path.write_text(json.dumps({"share": "auto"}))
    return ShareManager(config_path=cfg_path)


@pytest.fixture
def session_data(home):
    """Create a real session file in ~/.apex/sessions/ for loading."""
    sess_dir = home / ".apex" / "sessions"
    sess_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "session_id": "test-session-1",
        "name": "Test Session",
        "model": "gpt-4",
        "agent": "build",
        "created_at": "2025-01-01T00:00:00",
        "cwd": "/home/user/project",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ],
    }
    (sess_dir / "test-session-1.json").write_text(json.dumps(data))
    return data


# ---------------------------------------------------------------------------
# ShareManager construction
# ---------------------------------------------------------------------------


class TestShareManagerInit:
    def test_default_creation(self, home):
        mgr = ShareManager()
        assert mgr._shares_dir == home / ".config" / "apex" / "shares"
        assert mgr._shares_dir.exists()
        assert mgr._config_path is None

    def test_with_config_path(self, home):
        cfg = home / "config.json"
        cfg.write_text("{}")
        mgr = ShareManager(config_path=cfg)
        assert mgr._config_path == cfg


# ---------------------------------------------------------------------------
# _mode property (3 sharing modes: manual, auto, disabled)
# ---------------------------------------------------------------------------


class TestShareManagerMode:
    def test_default_mode_is_manual(self, share_mgr):
        assert share_mgr._mode == "manual"

    def test_mode_auto_from_config(self, share_mgr_with_config):
        assert share_mgr_with_config._mode == "auto"

    def test_mode_disabled(self, home):
        cfg = home / "config.json"
        cfg.write_text(json.dumps({"share": "disabled"}))
        mgr = ShareManager(config_path=cfg)
        assert mgr._mode == "disabled"

    def test_fallback_to_apex_config(self, home):
        apex_cfg = home / ".apex" / "config.json"
        apex_cfg.parent.mkdir(parents=True, exist_ok=True)
        apex_cfg.write_text(json.dumps({"share": "auto"}))
        mgr = ShareManager()
        assert mgr._mode == "auto"

    def test_invalid_value_fallback_to_manual(self, home):
        cfg = home / "config.json"
        cfg.write_text(json.dumps({"share": "bogus"}))
        mgr = ShareManager(config_path=cfg)
        assert mgr._mode == "manual"

    def test_config_read_error_fallback(self, home):
        cfg = home / "config.json"
        cfg.write_text("{{{ not valid json }}}")
        mgr = ShareManager(config_path=cfg)
        assert mgr._mode == "manual"

    def test_nonexistent_config_path(self, home):
        mgr = ShareManager(config_path=home / "does_not_exist.json")
        assert mgr._mode == "manual"

    def test_mode_config_without_share_key(self, home):
        cfg = home / "config.json"
        cfg.write_text(json.dumps({"model": "gpt-4"}))
        mgr = ShareManager(config_path=cfg)
        assert mgr._mode == "manual"

    def test_apex_config_read_error_fallback(self, home):
        """Corrupt ~/.apex/config.json raises exception caught at line 57-58."""
        apex_cfg = home / ".apex" / "config.json"
        apex_cfg.parent.mkdir(parents=True, exist_ok=True)
        apex_cfg.write_text("{{{ broken json }}}")
        mgr = ShareManager()
        assert mgr._mode == "manual"


# ---------------------------------------------------------------------------
# _generate_id — UUID-based 8-char hex
# ---------------------------------------------------------------------------


class TestGenerateId:
    def test_eight_char_hex(self, share_mgr):
        share_id = share_mgr._generate_id()
        assert len(share_id) == 8
        assert re.match(r"^[0-9a-f]{8}$", share_id)

    def test_unique_values(self, share_mgr):
        ids = {share_mgr._generate_id() for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# _sanitize_string — redacts sensitive patterns
# ---------------------------------------------------------------------------


class TestSanitizeString:
    def test_openai_key(self, share_mgr):
        result = share_mgr._sanitize_string("sk-abc123def456ghijklmnopqrstuvwxyz")
        assert "***REDACTED***" in result
        assert "sk-abc123def456" not in result

    def test_anthropic_key(self, share_mgr):
        result = share_mgr._sanitize_string("sk-ant-abc123def456ghijklmnopqrstuvwxyz")
        assert "***REDACTED***" in result

    def test_github_token(self, share_mgr):
        result = share_mgr._sanitize_string("ghp_abcdefghijklmnopqrstuvwxyz1234567890")
        assert "***REDACTED***" in result

    def test_github_oauth_token(self, share_mgr):
        result = share_mgr._sanitize_string("gho_abcdefghijklmnopqrstuvwxyz1234567890")
        assert "***REDACTED***" in result

    def test_slack_bot_token(self, share_mgr):
        result = share_mgr._sanitize_string("xoxb-1234567890-abcdefghijklm")
        assert "***REDACTED***" in result

    def test_bearer_token(self, share_mgr):
        result = share_mgr._sanitize_string("Bearer eyJhbGciOiJIUzI1NiJ9.dGVzdA.dkjfl")
        assert "***REDACTED***" in result

    def test_uppercase_envvar_key(self, share_mgr):
        result = share_mgr._sanitize_string("ANTHROPIC_API_KEY")
        assert "***REDACTED***" in result

    def test_no_match(self, share_mgr):
        assert share_mgr._sanitize_string("hello world") == "hello world"

    def test_empty_string(self, share_mgr):
        assert share_mgr._sanitize_string("") == ""


# ---------------------------------------------------------------------------
# sanitize_session_data — removes sensitive keys and values recursively
# ---------------------------------------------------------------------------


class TestSanitizeSessionData:
    def test_removes_api_key_keys(self, share_mgr):
        data = {"api_key": "sk-abc", "name": "test", "token": "12345"}
        result = share_mgr.sanitize_session_data(data)
        assert "api_key" not in result
        assert "token" not in result
        assert result["name"] == "test"

    def test_redacts_sensitive_values(self, share_mgr):
        data = {"content": "My key is sk-abc123def456ghijklmnopqrstuvwxyz"}
        result = share_mgr.sanitize_session_data(data)
        assert "***REDACTED***" in result["content"]

    def test_recursive_dict(self, share_mgr):
        data = {"nested": {"api_key": "sk-abc", "name": "inner"}}
        result = share_mgr.sanitize_session_data(data)
        assert "api_key" not in result["nested"]
        assert result["nested"]["name"] == "inner"

    def test_list_with_dicts_strings_and_others(self, share_mgr):
        data = {
            "items": [
                {"secret": "s3cret!", "name": "item1"},
                "Bearer tokendata12345abcdefghij",
                42,
            ]
        }
        result = share_mgr.sanitize_session_data(data)
        assert "secret" not in result["items"][0]
        assert result["items"][0]["name"] == "item1"
        assert "***REDACTED***" in result["items"][1]
        assert result["items"][2] == 42

    def test_envvar_pattern_keys_skipped(self, share_mgr):
        data = {"OPENAI_API_KEY": "sk-abc", "MY_TOKEN": "tkn", "secret": "val"}
        result = share_mgr.sanitize_session_data(data)
        assert "OPENAI_API_KEY" not in result
        assert "MY_TOKEN" not in result
        assert result.get("secret") is None or "secret" not in result

    def test_preserves_non_sensitive_data(self, share_mgr):
        data = {"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}]}
        result = share_mgr.sanitize_session_data(data)
        assert result["model"] == "gpt-4"
        assert result["messages"] == [{"role": "user", "content": "hi"}]

    def test_non_string_values(self, share_mgr):
        data = {"count": 42, "ratio": 3.14, "active": True, "tags": None}
        result = share_mgr.sanitize_session_data(data)
        assert result["count"] == 42
        assert result["ratio"] == 3.14
        assert result["active"] is True
        assert result["tags"] is None

    def test_sensitive_keys_deleted_after_sanitize(self, share_mgr):
        data = {"my_api_key": "sk-abc", "my_secret_key": "s3cret", "safe": "value"}
        result = share_mgr.sanitize_session_data(data)
        assert "my_api_key" not in result
        assert "my_secret_key" not in result
        assert result["safe"] == "value"

    def test_key_value_both_sensitive(self, share_mgr):
        data = {"ANTHROPIC_API_KEY": "sk-ant-abc123def456ghijklmnopqrstuvwxyz"}
        result = share_mgr.sanitize_session_data(data)
        assert result == {}

    def test_empty_dict(self, share_mgr):
        assert share_mgr.sanitize_session_data({}) == {}

    def test_list_of_dicts_all_sensitive(self, share_mgr):
        data = {"items": [{"secret": "x"}, {"token": "y"}]}
        result = share_mgr.sanitize_session_data(data)
        assert result["items"] == [{}, {}]


# ---------------------------------------------------------------------------
# share_session — creates shared session and returns URL
# ---------------------------------------------------------------------------


class TestShareSession:
    def test_disabled_mode_returns_empty_string(self, home):
        cfg = home / "config.json"
        cfg.write_text(json.dumps({"share": "disabled"}))
        mgr = ShareManager(config_path=cfg)
        assert mgr.share_session("session-1") == ""

    def test_creates_file_and_returns_url(self, share_mgr, session_data):
        url = share_mgr.share_session("test-session-1", title="My Share")
        assert url.startswith("https://apex-ai.dev/s/")
        assert len(url) == len("https://apex-ai.dev/s/") + 8
        share_id = url.split("/")[-1]
        share_file = share_mgr._shares_dir / f"{share_id}.json"
        assert share_file.exists()
        content = json.loads(share_file.read_text())
        assert content["id"] == share_id
        assert content["session_id"] == "test-session-1"
        assert content["title"] == "My Share"
        assert content["messages_count"] == 2
        assert len(content["messages"]) == 2
        assert "created_at" in content
        assert "url" in content

    def test_title_falls_back_to_session_name(self, share_mgr, session_data):
        url = share_mgr.share_session("test-session-1")
        share_id = url.split("/")[-1]
        content = json.loads((share_mgr._shares_dir / f"{share_id}.json").read_text())
        assert content["title"] == "Test Session"

    def test_empty_session_data(self, share_mgr):
        url = share_mgr.share_session("nonexistent-session")
        assert url.startswith("https://apex-ai.dev/s/")
        share_id = url.split("/")[-1]
        content = json.loads((share_mgr._shares_dir / f"{share_id}.json").read_text())
        assert content["messages_count"] == 0
        assert content["messages"] == []
        assert content["title"] == ""
        assert content["metadata"] == {}

    def test_uses_history_key_fallback(self, home, share_mgr):
        sess_dir = home / ".apex" / "sessions"
        sess_dir.mkdir(parents=True, exist_ok=True)
        (sess_dir / "hist-session.json").write_text(
            json.dumps(
                {
                    "session_id": "hist-session",
                    "history": [{"role": "user", "content": "test"}],
                }
            )
        )
        url = share_mgr.share_session("hist-session")
        share_id = url.split("/")[-1]
        content = json.loads((share_mgr._shares_dir / f"{share_id}.json").read_text())
        assert content["messages_count"] == 1
        assert len(content["messages"]) == 1


# ---------------------------------------------------------------------------
# unshare_session — removes shared session
# ---------------------------------------------------------------------------


class TestUnshareSession:
    def test_removes_existing_share(self, share_mgr, session_data):
        url = share_mgr.share_session("test-session-1")
        share_id = url.split("/")[-1]
        assert share_mgr.unshare_session(share_id) is True
        assert not (share_mgr._shares_dir / f"{share_id}.json").exists()

    def test_returns_false_for_missing(self, share_mgr):
        assert share_mgr.unshare_session("does-not-exist") is False


# ---------------------------------------------------------------------------
# list_shared — returns all shared sessions
# ---------------------------------------------------------------------------


class TestListShared:
    def test_empty_when_no_shares(self, share_mgr):
        assert share_mgr.list_shared() == []

    def test_returns_multiple_shares(self, share_mgr, session_data, home):
        share_mgr.share_session("test-session-1", title="First")
        sess_dir = home / ".apex" / "sessions"
        (sess_dir / "session-2.json").write_text(
            json.dumps(
                {
                    "session_id": "session-2",
                    "name": "Second",
                    "messages": [{"role": "user", "content": "test"}],
                }
            )
        )
        share_mgr.share_session("session-2", title="Second")
        listed = share_mgr.list_shared()
        assert len(listed) == 2
        titles = [item["title"] for item in listed]
        assert "First" in titles
        assert "Second" in titles
        for item in listed:
            assert item["id"]
            assert item["url"]
            assert item["session_id"]
            assert item["messages_count"] >= 1
            assert "created_at" in item

    def test_skips_corrupt_json_files(self, share_mgr, session_data):
        share_mgr.share_session("test-session-1")
        (share_mgr._shares_dir / "corrupt.json").write_text("not-json")
        assert len(share_mgr.list_shared()) == 1


# ---------------------------------------------------------------------------
# get_share_url — returns proper URL format
# ---------------------------------------------------------------------------


class TestGetShareUrl:
    def test_returns_url_existing_share(self, share_mgr, session_data):
        url = share_mgr.share_session("test-session-1")
        share_id = url.split("/")[-1]
        assert share_mgr.get_share_url(share_id) == url

    def test_returns_empty_for_nonexistent(self, share_mgr):
        assert share_mgr.get_share_url("nonexistent") == ""

    def test_fallback_url_when_key_missing(self, share_mgr, session_data):
        url = share_mgr.share_session("test-session-1")
        share_id = url.split("/")[-1]
        share_file = share_mgr._shares_dir / f"{share_id}.json"
        content = json.loads(share_file.read_text())
        del content["url"]
        share_file.write_text(json.dumps(content))
        assert share_mgr.get_share_url(share_id) == f"https://apex-ai.dev/s/{share_id}"

    def test_empty_for_corrupt_file(self, share_mgr):
        (share_mgr._shares_dir / "bad.json").write_text("{{{")
        assert share_mgr.get_share_url("bad") == ""


# ---------------------------------------------------------------------------
# is_shared — checks correctly
# ---------------------------------------------------------------------------


class TestIsShared:
    def test_true_when_shared(self, share_mgr, session_data):
        url = share_mgr.share_session("test-session-1")
        assert share_mgr.is_shared(url.split("/")[-1]) is True

    def test_false_when_not_shared(self, share_mgr):
        assert share_mgr.is_shared("nonexistent") is False


# ---------------------------------------------------------------------------
# export_session — exports session as JSON dict with correct structure
# ---------------------------------------------------------------------------


class TestExportSession:
    def test_returns_export_dict(self, share_mgr, session_data):
        result = share_mgr.export_session("test-session-1")
        assert result["session_id"] == "test-session-1"
        assert result["apex_version"] == "2.0.0"
        assert "exported_at" in result
        assert "data" in result
        assert result["data"]["model"] == "gpt-4"
        assert len(result["data"]["messages"]) == 2

    def test_empty_dict_for_missing_session(self, share_mgr):
        assert share_mgr.export_session("nonexistent") == {}

    def test_sanitizes_sensitive_fields(self, share_mgr, home):
        sess_dir = home / ".apex" / "sessions"
        sess_dir.mkdir(parents=True, exist_ok=True)
        (sess_dir / "secret-sess.json").write_text(
            json.dumps(
                {
                    "session_id": "secret-sess",
                    "api_key": "sk-abc",
                    "name": "test",
                }
            )
        )
        result = share_mgr.export_session("secret-sess")
        assert "api_key" not in result["data"]


# ---------------------------------------------------------------------------
# import_session — imports from a JSON file and returns session ID
# ---------------------------------------------------------------------------


class TestImportSession:
    def test_import_export_format(self, share_mgr, home):
        path = home / "export.json"
        path.write_text(
            json.dumps(
                {
                    "exported_at": "2025-01-01T00:00:00",
                    "session_id": "imported-sess",
                    "apex_version": "1.3.0",
                    "data": {"session_id": "imported-sess", "model": "gpt-4", "messages": []},
                }
            )
        )
        result = share_mgr.import_session(str(path))
        assert result == "imported-sess"

    def test_import_bare_session_data(self, share_mgr, home):
        path = home / "bare.json"
        path.write_text(json.dumps({"session_id": "bare-123", "model": "gpt-4"}))
        result = share_mgr.import_session(str(path))
        assert result == "bare-123"

    def test_import_generates_id_when_missing(self, share_mgr, home):
        path = home / "no_id.json"
        path.write_text(json.dumps({"model": "gpt-4"}))
        result = share_mgr.import_session(str(path))
        assert result is not None
        assert len(result) == 12

    def test_import_missing_file_returns_none(self, share_mgr):
        assert share_mgr.import_session("/nonexistent/file.json") is None

    def test_import_invalid_json_returns_none(self, share_mgr, home):
        path = home / "bad.json"
        path.write_text("{{{ not json }}}")
        assert share_mgr.import_session(str(path)) is None

    def test_import_creates_session_file(self, share_mgr, home):
        path = home / "new.json"
        path.write_text(json.dumps({"session_id": "new-sess", "messages": []}))
        share_mgr.import_session(str(path))
        sess_dir = home / ".apex" / "sessions"
        matches = list(sess_dir.glob("*new-sess*"))
        assert len(matches) == 1

    def test_import_sanitizes_data(self, share_mgr, home):
        path = home / "tainted.json"
        path.write_text(
            json.dumps(
                {
                    "session_id": "clean-me",
                    "api_key": "sk-abc",
                    "messages": [{"content": "Bearer token12345abcdefghij"}],
                }
            )
        )
        result = share_mgr.import_session(str(path))
        assert result == "clean-me"
        sess_dir = home / ".apex" / "sessions"
        matches = list(sess_dir.glob("*clean-me*"))
        assert len(matches) == 1
        saved = json.loads(matches[0].read_text())
        assert "api_key" not in saved
        assert "***REDACTED***" in saved["messages"][0]["content"]


# ---------------------------------------------------------------------------
# _load_session_data — internal session loader (multiple search paths)
# ---------------------------------------------------------------------------


class TestLoadSessionData:
    def test_load_by_session_id(self, share_mgr, session_data):
        result = share_mgr._load_session_data("test-session-1")
        assert result["session_id"] == "test-session-1"
        assert result["name"] == "Test Session"

    def test_load_by_name(self, share_mgr, session_data):
        result = share_mgr._load_session_data("Test Session")
        assert result["session_id"] == "test-session-1"

    def test_load_from_config_sessions_dir(self, share_mgr, home):
        config_sess = home / ".config" / "apex" / "sessions"
        config_sess.mkdir(parents=True, exist_ok=True)
        (config_sess / "cfg-sess.json").write_text(
            json.dumps(
                {
                    "session_id": "cfg-sess",
                    "name": "Config session",
                }
            )
        )
        result = share_mgr._load_session_data("cfg-sess")
        assert result["session_id"] == "cfg-sess"

    def test_load_by_filename_glob_fallback(self, share_mgr, home):
        sess_dir = home / ".apex" / "sessions"
        sess_dir.mkdir(parents=True, exist_ok=True)
        (sess_dir / "abc123.json").write_text(json.dumps({"name": "from-glob"}))
        result = share_mgr._load_session_data("abc123")
        assert result["name"] == "from-glob"

    def test_load_nonexistent_returns_empty(self, share_mgr):
        assert share_mgr._load_session_data("nonexistent") == {}

    def test_skips_non_json_files(self, share_mgr, home):
        sess_dir = home / ".apex" / "sessions"
        sess_dir.mkdir(parents=True, exist_ok=True)
        (sess_dir / "notes.txt").write_text("hello")
        (sess_dir / "real.json").write_text(json.dumps({"session_id": "real"}))
        assert share_mgr._load_session_data("real")["session_id"] == "real"

    def test_skips_corrupt_json_files(self, share_mgr, home):
        sess_dir = home / ".apex" / "sessions"
        sess_dir.mkdir(parents=True, exist_ok=True)
        (sess_dir / "corrupt.json").write_text("{{{")
        (sess_dir / "good.json").write_text(json.dumps({"session_id": "good"}))
        result = share_mgr._load_session_data("good")
        assert result["session_id"] == "good"

    def test_skips_non_existent_base_dir(self, share_mgr):
        """When neither base dir exists, returns empty dict."""
        assert share_mgr._load_session_data("anything") == {}

    def test_glob_fallback_corrupt_file(self, share_mgr, home):
        """Second glob loop finds corrupt file — exception handled at lines 228-229."""
        sess_dir = home / ".apex" / "sessions"
        sess_dir.mkdir(parents=True, exist_ok=True)
        (sess_dir / "corrupt-sess.json").write_text("{{{ not json }}}")
        result = share_mgr._load_session_data("corrupt-sess")
        assert result == {}


# ---------------------------------------------------------------------------
# share_manager module-level singleton
# ---------------------------------------------------------------------------


class TestShareManagerSingleton:
    def test_singleton_exists(self):
        assert share_manager is not None
        assert isinstance(share_manager, ShareManager)

    def test_singleton_has_expected_methods(self):
        assert hasattr(share_manager, "share_session")
        assert hasattr(share_manager, "unshare_session")
        assert hasattr(share_manager, "list_shared")
        assert hasattr(share_manager, "get_share_url")
        assert hasattr(share_manager, "is_shared")
        assert hasattr(share_manager, "export_session")
        assert hasattr(share_manager, "import_session")
        assert hasattr(share_manager, "sanitize_session_data")
