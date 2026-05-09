"""Tests for refactored telemetry module."""


from apex.refactored_telemetry import (
    EventType, TelemetryEvent, Logger, PerformanceMonitor,
    create_logger, create_performance_monitor
)


class TestTelemetryEvent:
    def test_init(self):
        event = TelemetryEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="test_event",
            data={"key": "value"},
            duration_ms=100.0
        )
        assert event.timestamp == "2024-01-01T00:00:00"
        assert event.event_type == "test_event"
        assert event.data == {"key": "value"}
        assert event.duration_ms == 100.0

    def test_default_data(self):
        event = TelemetryEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="test_event"
        )
        assert event.data == {}
        assert event.duration_ms is None


class TestLogger:
    def test_init_default(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test_session")
        assert logger.session_id == "test_session"

    def test_log_basic(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        logger.log(EventType.AGENT_START, {"model": "gpt-4"})
        
        assert len(logger.events) == 1
        assert logger.events[0].event_type == "agent_start"
        assert logger.events[0].data == {"model": "gpt-4"}

    def test_log_agent_start(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        logger.log_agent_start("gpt-4", "default")
        
        event = logger.events[0]
        assert event.event_type == "agent_start"
        assert event.data["model"] == "gpt-4"
        assert event.data["agent"] == "default"

    def test_log_tool_call(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        logger.log_tool_call("read_file", {"path": "/test.txt"})
        
        event = logger.events[0]
        assert event.event_type == "tool_call"
        assert event.data["tool"] == "read_file"

    def test_log_tool_call_sanitize(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        logger.log_tool_call("api_call", {"api_key": "secret123", "path": "/test"})
        
        event = logger.events[0]
        assert event.data["args"]["api_key"] == "***"
        assert event.data["args"]["path"] == "/test"

    def test_log_tool_call_long_value(self, tmp_path):
        long_value = "x" * 200
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        logger.log_tool_call("test", {"value": long_value})
        
        event = logger.events[0]
        assert len(event.data["args"]["value"]) == 100

    def test_log_tool_result_success(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        logger.log_tool_result("read_file", "file content", 50.0)
        
        event = logger.events[0]
        assert event.event_type == "tool_result"
        assert event.data["success"] is True

    def test_log_tool_result_error(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        logger.log_tool_result("read_file", "ERROR: file not found", 50.0)
        
        event = logger.events[0]
        assert event.data["success"] is False

    def test_log_model_switch(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        logger.log_model_switch("gpt-4", "claude-3")
        
        event = logger.events[0]
        assert event.event_type == "model_switch"
        assert event.data["old"] == "gpt-4"
        assert event.data["new"] == "claude-3"

    def test_log_agent_switch(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        logger.log_agent_switch("default", "research")
        
        event = logger.events[0]
        assert event.event_type == "agent_switch"
        assert event.data["old"] == "default"
        assert event.data["new"] == "research"

    def test_log_error(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        logger.log_error("FileNotFound", "file not found", {"path": "/test"})
        
        event = logger.events[0]
        assert event.event_type == "error"
        assert event.data["error_type"] == "FileNotFound"
        assert event.data["message"] == "file not found"

    def test_log_session_start(self, tmp_path):
        mock_time = 1000.0
        logger = Logger(
            log_dir=tmp_path,
            session_id_factory=lambda: "test",
            time_factory=lambda: mock_time
        )
        logger.log_session_start("/workspace")
        
        event = logger.events[0]
        assert event.event_type == "session_start"
        assert event.data["cwd"] == "/workspace"

    def test_log_session_end(self, tmp_path):
        mock_time = 1000.0
        logger = Logger(
            log_dir=tmp_path,
            session_id_factory=lambda: "test",
            time_factory=lambda: mock_time
        )
        logger.log_agent_start("gpt-4", "default")
        
        mock_time_later = lambda: mock_time + 1.0
        logger._time_factory = mock_time_later
        logger.log_session_end()
        
        event = logger.events[1]
        assert event.event_type == "session_end"
        assert event.data["event_count"] == 1

    def test_save(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test_session")
        logger.log(EventType.AGENT_START, {"model": "gpt-4"})
        logger.save()
        
        log_file = tmp_path / "session_test_session.jsonl"
        assert log_file.exists()

    def test_get_stats(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        logger.log_tool_call("read_file", {"path": "/a"})
        logger.log_tool_call("read_file", {"path": "/b"})
        logger.log_tool_call("write_file", {"path": "/c"})
        logger.log_error("Error", "error message")
        
        stats = logger.get_stats()
        assert stats["total_events"] == 4
        assert stats["tool_calls"]["read_file"] == 2
        assert stats["tool_calls"]["write_file"] == 1
        assert stats["errors"] == 1

    def test_get_stats_empty(self, tmp_path):
        logger = Logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        stats = logger.get_stats()
        assert stats["total_events"] == 0
        assert stats["tool_calls"] == {}
        assert stats["errors"] == 0


class TestPerformanceMonitor:
    def test_init(self):
        monitor = PerformanceMonitor()
        assert monitor._measurements == {}

    def test_record(self):
        monitor = PerformanceMonitor()
        monitor.record("test_op", 10.0)
        assert "test_op" in monitor._measurements
        assert 10.0 in monitor._measurements["test_op"]

    def test_record_multiple(self):
        monitor = PerformanceMonitor()
        monitor.record("test_op", 10.0)
        monitor.record("test_op", 20.0)
        assert len(monitor._measurements["test_op"]) == 2

    def test_get_stats(self):
        monitor = PerformanceMonitor()
        monitor.record("test_op", 10.0)
        monitor.record("test_op", 20.0)
        monitor.record("test_op", 30.0)
        
        stats = monitor.get_stats("test_op")
        assert stats["count"] == 3
        assert stats["avg"] == 20.0
        assert stats["min"] == 10.0
        assert stats["max"] == 30.0

    def test_get_stats_unknown_operation(self):
        monitor = PerformanceMonitor()
        stats = monitor.get_stats("unknown")
        assert stats == {}

    def test_get_all_stats(self):
        monitor = PerformanceMonitor()
        monitor.record("op1", 10.0)
        monitor.record("op2", 20.0)
        
        all_stats = monitor.get_all_stats()
        assert "op1" in all_stats
        assert "op2" in all_stats


class TestFactoryFunctions:
    def test_create_logger_default(self):
        logger = create_logger(session_id_factory=lambda: "test")
        assert logger.session_id == "test"

    def test_create_logger_with_dir(self, tmp_path):
        logger = create_logger(log_dir=tmp_path, session_id_factory=lambda: "test")
        assert logger._log_dir == tmp_path

    def test_create_performance_monitor(self):
        monitor = create_performance_monitor()
        assert isinstance(monitor, PerformanceMonitor)