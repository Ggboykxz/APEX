"""Tests for widgets/messages.py - Textual message classes."""

import pytest
from apex.widgets.messages import (
    AgentThinking,
    AgentToolCall,
    AgentToolResult,
    AgentResponse,
    AgentError,
    TokenUpdate,
    ToggleSidebar,
    ModelChanged,
    CwdChanged,
    ClearChat,
    FilePreviewRequest,
)


class TestWidgetMessages:
    """Test Textual message classes."""

    def test_agent_thinking(self):
        """Test AgentThinking message."""
        msg = AgentThinking()
        assert isinstance(msg, AgentThinking)

    def test_agent_tool_call(self):
        """Test AgentToolCall message."""
        msg = AgentToolCall(name="read_file", args={"path": "test.py"})
        assert msg.name == "read_file"
        assert msg.args == {"path": "test.py"}

    def test_agent_tool_result_success(self):
        """Test successful AgentToolResult."""
        msg = AgentToolResult(name="read_file", result="content", success=True, duration=0.5)
        assert msg.name == "read_file"
        assert msg.result == "content"
        assert msg.success is True
        assert msg.duration == 0.5

    def test_agent_tool_result_failure(self):
        """Test failed AgentToolResult."""
        msg = AgentToolResult(name="read_file", result="Error", success=False, duration=0.1)
        assert msg.success is False

    def test_agent_response(self):
        """Test AgentResponse message."""
        msg = AgentResponse(text="Hello world", model="gpt-4o")
        assert msg.text == "Hello world"
        assert msg.model == "gpt-4o"

    def test_agent_error(self):
        """Test AgentError message."""
        msg = AgentError(error="Something went wrong")
        assert msg.error == "Something went wrong"

    def test_token_update(self):
        """Test TokenUpdate message."""
        msg = TokenUpdate(count=1500, cost=0.05)
        assert msg.count == 1500
        assert msg.cost == 0.05

    def test_toggle_sidebar(self):
        """Test ToggleSidebar message."""
        msg = ToggleSidebar()
        assert isinstance(msg, ToggleSidebar)

    def test_model_changed(self):
        """Test ModelChanged message."""
        msg = ModelChanged(model="claude-sonnet")
        assert msg.model == "claude-sonnet"

    def test_cwd_changed(self):
        """Test CwdChanged message."""
        msg = CwdChanged(cwd="/home/user")
        assert msg.cwd == "/home/user"

    def test_clear_chat(self):
        """Test ClearChat message."""
        msg = ClearChat()
        assert isinstance(msg, ClearChat)

    def test_file_preview_request(self):
        """Test FilePreviewRequest message."""
        msg = FilePreviewRequest(file_path="/path/to/file.py")
        assert msg.file_path == "/path/to/file.py"