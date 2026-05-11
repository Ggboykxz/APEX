"""Tests for apex/telemetry.py — Logger, TelemetryEvent, EventType, PerformanceMonitor."""

import pytest
import json
from apex.telemetry import (
    EventType,
    TelemetryEvent,
    Logger,
    PerformanceMonitor,
    logger,
    perf_monitor,
)


class TestEventType:
    def test_values(self):
        assert EventType.AGENT_START.value == "agent_start"
        assert EventType.AGENT_MESSAGE.value == "agent_message"
        assert EventType.TOOL_CALL.value == "tool_call"
        assert EventType.TOOL_RESULT.value == "tool_result"
        assert EventType.MODEL_SWITCH.value == "model_switch"
        assert EventType.AGENT_SWITCH.value == "agent_switch"
        assert EventType.ERROR.value == "error"
        assert EventType.SESSION_START.value == "session_start"
        assert EventType.SESSION_END.value == "session_end"


class TestTelemetryEvent:
    def test_creation(self):
        event = TelemetryEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="tool_call",
            data={"tool": "read_file"},
            duration_ms=100.5,
        )
        assert event.timestamp == "2024-01-01T00:00:00"
        assert event.event_type == "tool_call"
        assert event.data == {"tool": "read_file"}
        assert event.duration_ms == 100.5

    def test_defaults(self):
        event = TelemetryEvent(timestamp="t", event_type="error")
        assert event.data == {}
        assert event.duration_ms is None


class TestLogger:
    @pytest.fixture
    def log_dir(self, tmp_path):
        return tmp_path / "logs"

    @pytest.fixture
    def log(self, log_dir):
        return Logger(log_dir=log_dir)

    def test_init(self, log, log_dir):
        assert log._log_dir == log_dir
        assert log._log_dir.exists()
        assert log._events == []
        assert log._current_session is not None

    def test_log_event(self, log):
        log.log(EventType.TOOL_CALL, {"tool": "read_file"})
        assert len(log._events) == 1
        assert log._events[0].event_type == EventType.TOOL_CALL.value

    def test_log_with_duration(self, log):
        log.log(EventType.TOOL_RESULT, {}, duration_ms=50.0)
        assert log._events[0].duration_ms == 50.0

    def test_log_agent_start(self, log):
        log.log_agent_start("gpt-4o", "coder")
        assert len(log._events) == 1
        assert log._events[0].data["model"] == "gpt-4o"
        assert log._events[0].data["agent"] == "coder"

    def test_log_tool_call(self, log):
        log.log_tool_call("read_file", {"path": "test.py"})
        assert len(log._events) == 1
        assert log._events[0].data["tool"] == "read_file"

    def test_log_tool_call_sanitizes_api_key(self, log):
        log.log_tool_call("api_call", {"api_key": "sk-secret123", "normal_arg": "value"})
        assert log._events[0].data["args"]["api_key"] == "***"
        assert log._events[0].data["args"]["normal_arg"] == "value"

    def test_log_tool_result_success(self, log):
        log.log_tool_result("read_file", "file contents", 100.0)
        assert log._events[0].data["success"] is True
        assert log._events[0].duration_ms == 100.0

    def test_log_tool_result_error(self, log):
        log.log_tool_result("write_file", "ERROR: permission denied", 50.0)
        assert log._events[0].data["success"] is False

    def test_log_model_switch(self, log):
        log.log_model_switch("gpt-4o", "claude-4-opus")
        assert log._events[0].data["old"] == "gpt-4o"
        assert log._events[0].data["new"] == "claude-4-opus"

    def test_log_agent_switch(self, log):
        log.log_agent_switch("coder", "architect")
        assert log._events[0].data["old"] == "coder"
        assert log._events[0].data["new"] == "architect"

    def test_log_error(self, log):
        log.log_error("timeout", "Request timed out", {"url": "http://api"})
        assert log._events[0].data["error_type"] == "timeout"

    def test_log_session_start(self, log):
        log.log_session_start("/home/user/project")
        assert log._events[0].data["cwd"] == "/home/user/project"

    def test_log_session_end(self, log):
        log.log_session_end()
        assert log._events[0].data["session_id"] is not None

    def test_save(self, log, log_dir):
        log.log(EventType.AGENT_START, {"model": "test"})
        log.save()
        log_file = log_dir / f"session_{log._current_session}.jsonl"
        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["event_type"] == "agent_start"

    def test_save_multiple_events(self, log, log_dir):
        log.log(EventType.AGENT_START, {})
        log.log(EventType.TOOL_CALL, {"tool": "read"})
        log.save()
        log_file = log_dir / f"session_{log._current_session}.jsonl"
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_get_stats(self, log):
        log.log(EventType.TOOL_CALL, {"tool": "read_file"})
        log.log(EventType.TOOL_CALL, {"tool": "write_file"})
        log.log(EventType.ERROR, {"error_type": "timeout"})
        log.log(EventType.TOOL_RESULT, {"tool": "read"}, duration_ms=100)

        stats = log.get_stats()
        assert stats["total_events"] == 4
        assert stats["tool_calls"]["read_file"] == 1
        assert stats["tool_calls"]["write_file"] == 1
        assert stats["errors"] == 1
        assert stats["total_duration_ms"] == 100

    def test_get_stats_empty(self, log):
        stats = log.get_stats()
        assert stats["total_events"] == 0
        assert stats["tool_calls"] == {}
        assert stats["errors"] == 0

    def test_print_summary(self, log, capsys):
        log.log(EventType.TOOL_CALL, {"tool": "test"})
        log.print_summary()
        captured = capsys.readouterr()
        assert "Session Summary" in captured.out

    def test_sanitize_args_password(self, log):
        result = log._sanitize_args({"password": "secret123"})
        assert result["password"] == "***"

    def test_sanitize_args_token(self, log):
        result = log._sanitize_args({"token": "abc123"})
        assert result["token"] == "***"

    def test_sanitize_args_normal(self, log):
        result = log._sanitize_args({"path": "/tmp/test.py", "count": 5})
        assert result["path"] == "/tmp/test.py"

    def test_sanitize_args_long_value(self, log):
        result = log._sanitize_args({"data": "x" * 200})
        assert len(result["data"]) <= 100

    def test_new_session_id(self, log):
        sid = log._new_session_id()
        assert len(sid) > 0
        # Should be a valid datetime format string
        assert "_" in sid


class TestPerformanceMonitor:
    def test_init(self):
        pm = PerformanceMonitor()
        assert pm._measurements == {}

    def test_measure(self):
        pm = PerformanceMonitor()
        start = pm.measure("test_op")
        assert isinstance(start, float)

    def test_record(self):
        pm = PerformanceMonitor()
        pm.record("test_op", 100.0)
        pm.record("test_op", 200.0)
        assert len(pm._measurements["test_op"]) == 2

    def test_get_stats(self):
        pm = PerformanceMonitor()
        pm.record("test_op", 100.0)
        pm.record("test_op", 200.0)
        pm.record("test_op", 300.0)
        stats = pm.get_stats("test_op")
        assert stats["count"] == 3
        assert stats["avg"] == 200.0
        assert stats["min"] == 100.0
        assert stats["max"] == 300.0

    def test_get_stats_nonexistent(self):
        pm = PerformanceMonitor()
        assert pm.get_stats("nonexistent") == {}

    def test_get_all_stats(self):
        pm = PerformanceMonitor()
        pm.record("op1", 100.0)
        pm.record("op2", 200.0)
        stats = pm.get_all_stats()
        assert "op1" in stats
        assert "op2" in stats


class TestGlobalInstances:
    def test_logger(self):
        assert isinstance(logger, Logger)

    def test_perf_monitor(self):
        assert isinstance(perf_monitor, PerformanceMonitor)
