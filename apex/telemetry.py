"""Telemetry and logging system for APEX."""

import time
import json
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EventType(Enum):
    AGENT_START = "agent_start"
    AGENT_MESSAGE = "agent_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    MODEL_SWITCH = "model_switch"
    AGENT_SWITCH = "agent_switch"
    ERROR = "error"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass
class TelemetryEvent:
    timestamp: str
    event_type: str
    data: dict = field(default_factory=dict)
    duration_ms: float | None = None


class Logger:
    def __init__(self, log_dir: Path | None = None):
        self._log_dir = log_dir or Path.home() / ".apex" / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._current_session = self._new_session_id()
        self._events: list[TelemetryEvent] = []
        self._start_time = time.time()

    def _new_session_id(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def log(self, event_type: EventType, data: dict | None = None, duration_ms: float | None = None) -> None:
        event = TelemetryEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type.value,
            data=data or {},
            duration_ms=duration_ms
        )
        self._events.append(event)

    def log_agent_start(self, model: str, agent: str) -> None:
        self.log(EventType.AGENT_START, {"model": model, "agent": agent})

    def log_tool_call(self, tool_name: str, args: dict) -> None:
        self.log(EventType.TOOL_CALL, {"tool": tool_name, "args": self._sanitize_args(args)})

    def log_tool_result(self, tool_name: str, result: str, duration_ms: float) -> None:
        self.log(EventType.TOOL_RESULT, {
            "tool": tool_name,
            "success": not result.startswith("ERROR"),
            "result_length": len(result)
        }, duration_ms)

    def log_model_switch(self, old_model: str, new_model: str) -> None:
        self.log(EventType.MODEL_SWITCH, {"old": old_model, "new": new_model})

    def log_agent_switch(self, old_agent: str, new_agent: str) -> None:
        self.log(EventType.AGENT_SWITCH, {"old": old_agent, "new": new_agent})

    def log_error(self, error_type: str, message: str, context: dict | None = None) -> None:
        self.log(EventType.ERROR, {
            "error_type": error_type,
            "message": message,
            "context": context or {}
        })

    def log_session_start(self, cwd: str) -> None:
        self._start_time = time.time()
        self.log(EventType.SESSION_START, {"cwd": cwd, "session_id": self._current_session})

    def log_session_end(self) -> None:
        duration = (time.time() - self._start_time) * 1000
        self.log(EventType.SESSION_END, {
            "session_id": self._current_session,
            "duration_ms": duration,
            "event_count": len(self._events)
        })

    def _sanitize_args(self, args: dict) -> dict:
        sensitive_keys = {
            "api_key", "password", "token", "secret", "key",
            "aws_access_key", "aws_secret_key", "aws_session_token",
            "access_key", "secret_key", "session_token",
            "private_key", "secret_token", "auth_token",
            "bearer", "credential", "credentials"
        }
        sanitized = {}
        for k, v in args.items():
            key_lower = k.lower()
            if any(sensitive in key_lower for s in sensitive_keys for sensitive in (s,)):
                if any(s in key_lower for s in sensitive_keys):
                    sanitized[k] = "***"
                else:
                    sanitized[k] = "***" if any(s in key_lower for s in {
                        "key", "secret", "password", "token", "credential", "api_key"
                    }) else str(v)[:100]
            else:
                sanitized[k] = str(v)[:100]
        return sanitized

    def save(self) -> None:
        log_file = self._log_dir / f"session_{self._current_session}.jsonl"
        with open(log_file, "w") as f:
            for event in self._events:
                f.write(json.dumps({
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "data": event.data,
                    "duration_ms": event.duration_ms
                }) + "\n")

    def get_stats(self) -> dict[str, Any]:
        tool_counts = {}
        error_count = 0
        total_duration = 0

        for event in self._events:
            if event.event_type == EventType.TOOL_CALL.value:
                tool = event.data.get("tool", "unknown")
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
            elif event.event_type == EventType.ERROR.value:
                error_count += 1
            if event.duration_ms:
                total_duration += event.duration_ms

        return {
            "session_id": self._current_session,
            "total_events": len(self._events),
            "tool_calls": tool_counts,
            "errors": error_count,
            "total_duration_ms": total_duration
        }

    def print_summary(self) -> None:
        stats = self.get_stats()
        print("\n=== Session Summary ===")
        print(f"Session: {stats['session_id']}")
        print(f"Total Events: {stats['total_events']}")
        print(f"Tool Calls: {sum(stats['tool_calls'].values())}")
        print(f"Errors: {stats['errors']}")
        print(f"Duration: {stats['total_duration_ms']:.0f}ms")
        if stats['tool_calls']:
            print("\nTop Tools:")
            for tool, count in sorted(stats['tool_calls'].items(), key=lambda x: -x[1])[:5]:
                print(f"  {tool}: {count}")


class PerformanceMonitor:
    def __init__(self):
        self._measurements: dict[str, list[float]] = {}

    def measure(self, operation: str) -> float:
        start = time.perf_counter()
        return start

    def record(self, operation: str, duration_ms: float) -> None:
        if operation not in self._measurements:
            self._measurements[operation] = []
        self._measurements[operation].append(duration_ms)

    def get_stats(self, operation: str) -> dict[str, float]:
        if operation not in self._measurements:
            return {}
        times = self._measurements[operation]
        return {
            "count": len(times),
            "avg": sum(times) / len(times),
            "min": min(times),
            "max": max(times)
        }

    def get_all_stats(self) -> dict[str, dict[str, float]]:
        return {op: self.get_stats(op) for op in self._measurements}


logger = Logger()
perf_monitor = PerformanceMonitor()