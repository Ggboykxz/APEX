"""Tests for session_sharing_server module."""

import pytest
from datetime import datetime, timedelta
from apex.session_sharing_server import SessionSharingServer, SharedSession


class TestSessionSharingServer:
    """Test SessionSharingServer class."""

    def test_init(self):
        server = SessionSharingServer()
        assert server is not None

    def test_init_with_storage_path(self, tmp_path):
        server = SessionSharingServer(storage_path=tmp_path)
        assert server is not None
        assert server.storage_path == tmp_path

    def test_get_session_nonexistent(self):
        server = SessionSharingServer()
        session = server.get_session("nonexistent-id")
        assert session is None

    def test_list_shares(self):
        server = SessionSharingServer()
        shares = server.list_shares()
        assert isinstance(shares, list)


class TestSharedSession:
    """Test SharedSession dataclass."""

    def test_shared_session_creation(self):
        now = datetime.now()
        expires = now + timedelta(hours=24)
        session = SharedSession(
            id="share-123",
            data={"key": "value"},
            created_at=now,
            expires_at=expires,
        )
        assert session.id == "share-123"
        assert session.data["key"] == "value"
        assert session.views == 0
        assert session.max_views == 100

    def test_shared_session_with_views(self):
        now = datetime.now()
        expires = now + timedelta(hours=24)
        session = SharedSession(
            id="share-456",
            data={},
            created_at=now,
            expires_at=expires,
            views=5,
            max_views=50,
        )
        assert session.views == 5
        assert session.max_views == 50