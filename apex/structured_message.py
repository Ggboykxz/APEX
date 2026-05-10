"""Structured message system for APEX - Parts like OpenCode."""

from typing import Any, Optional, List, Dict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PartType(Enum):
    TEXT = "text"
    FILE = "file"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    IMAGE = "image"
    SNAPSHOT = "snapshot"


@dataclass
class MessagePart:
    part_type: PartType
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.part_type.value,
            "content": self.content,
            "metadata": self.metadata
        }


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
        }


@dataclass
class Message:
    id: str
    role: str
    parts: List[MessagePart] = field(default_factory=list)
    token_usage: Optional[TokenUsage] = None
    cost_usd: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "parts": [p.to_dict() for p in self.parts],
            "token_usage": self.token_usage.to_dict() if self.token_usage else None,
            "cost_usd": self.cost_usd,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            id=data["id"],
            role=data["role"],
            parts=[MessagePart(PartType(p["type"]), p["content"], p.get("metadata", {})) for p in data.get("parts", [])],
            token_usage=TokenUsage(**data["token_usage"]) if data.get("token_usage") else None,
            cost_usd=data.get("cost_usd"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now()
        )

    def add_text(self, text: str) -> None:
        self.parts.append(MessagePart(PartType.TEXT, text))

    def add_file(self, path: str, content: str = "") -> None:
        self.parts.append(MessagePart(
            PartType.FILE,
            {"path": path, "content": content},
            {"name": path.split("/")[-1]}
        ))

    def add_tool_call(self, tool_name: str, arguments: dict) -> None:
        self.parts.append(MessagePart(
            PartType.TOOL_CALL,
            {"name": tool_name, "arguments": arguments}
        ))

    def add_tool_result(self, tool_name: str, result: Any) -> None:
        self.parts.append(MessagePart(
            PartType.TOOL_RESULT,
            {"name": tool_name, "result": result}
        ))

    def add_image(self, path: str, base64_data: str = "") -> None:
        self.parts.append(MessagePart(
            PartType.IMAGE,
            {"path": path, "data": base64_data}
        ))

    def add_snapshot(self, snapshot_id: str) -> None:
        self.parts.append(MessagePart(
            PartType.SNAPSHOT,
            snapshot_id
        ))

    def get_text(self) -> str:
        return " ".join(p.content for p in self.parts if p.part_type == PartType.TEXT)

    def get_files(self) -> List[Dict]:
        return [p.content for p in self.parts if p.part_type == PartType.FILE]

    def get_tool_calls(self) -> List[Dict]:
        return [p.content for p in self.parts if p.part_type == PartType.TOOL_CALL]


def create_message(role: str, content: str = "") -> Message:
    """Factory function to create a message."""
    import hashlib
    import time

    msg_id = hashlib.sha256(f"{time.time()}{role}".encode()).hexdigest()[:16]
    msg = Message(id=msg_id, role=role)

    if content:
        msg.add_text(content)

    return msg


def serialize_messages(messages: List[Message]) -> List[dict]:
    """Serialize messages to list of dicts."""
    return [m.to_dict() for m in messages]


def deserialize_messages(data: List[dict]) -> List[Message]:
    """Deserialize messages from list of dicts."""
    return [Message.from_dict(d) for d in data]