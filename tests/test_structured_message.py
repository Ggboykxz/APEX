"""Tests for apex/structured_message.py — Message, MessagePart, TokenUsage, PartType."""

from apex.structured_message import (
    PartType,
    MessagePart,
    TokenUsage,
    Message,
    create_message,
    serialize_messages,
    deserialize_messages,
)


class TestPartType:
    def test_values(self):
        assert PartType.TEXT.value == "text"
        assert PartType.FILE.value == "file"
        assert PartType.TOOL_CALL.value == "tool_call"
        assert PartType.TOOL_RESULT.value == "tool_result"
        assert PartType.IMAGE.value == "image"
        assert PartType.SNAPSHOT.value == "snapshot"


class TestMessagePart:
    def test_creation(self):
        mp = MessagePart(part_type=PartType.TEXT, content="hello")
        assert mp.part_type == PartType.TEXT
        assert mp.content == "hello"
        assert mp.metadata == {}

    def test_with_metadata(self):
        mp = MessagePart(
            part_type=PartType.FILE, content={"path": "f.py"}, metadata={"name": "f.py"}
        )
        assert mp.metadata == {"name": "f.py"}

    def test_to_dict(self):
        mp = MessagePart(part_type=PartType.TEXT, content="hello", metadata={"key": "val"})
        d = mp.to_dict()
        assert d["type"] == "text"
        assert d["content"] == "hello"
        assert d["metadata"] == {"key": "val"}


class TestTokenUsage:
    def test_defaults(self):
        tu = TokenUsage()
        assert tu.prompt_tokens == 0
        assert tu.completion_tokens == 0
        assert tu.total_tokens == 0

    def test_with_values(self):
        tu = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert tu.prompt_tokens == 100
        assert tu.total_tokens == 150

    def test_to_dict(self):
        tu = TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        d = tu.to_dict()
        assert d["prompt_tokens"] == 10
        assert d["completion_tokens"] == 5
        assert d["total_tokens"] == 15


class TestMessage:
    def test_creation(self):
        msg = Message(id="msg1", role="user")
        assert msg.id == "msg1"
        assert msg.role == "user"
        assert msg.parts == []
        assert msg.token_usage is None
        assert msg.cost_usd is None

    def test_with_all_fields(self):
        tu = TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        msg = Message(id="msg2", role="assistant", token_usage=tu, cost_usd=0.01)
        assert msg.token_usage is tu
        assert msg.cost_usd == 0.01

    def test_add_text(self):
        msg = Message(id="m1", role="user")
        msg.add_text("hello world")
        assert len(msg.parts) == 1
        assert msg.parts[0].part_type == PartType.TEXT
        assert msg.parts[0].content == "hello world"

    def test_add_file(self):
        msg = Message(id="m2", role="assistant")
        msg.add_file("test.py", "print('hi')")
        assert len(msg.parts) == 1
        assert msg.parts[0].part_type == PartType.FILE
        assert msg.parts[0].content["path"] == "test.py"

    def test_add_tool_call(self):
        msg = Message(id="m3", role="assistant")
        msg.add_tool_call("read_file", {"path": "test.py"})
        assert len(msg.parts) == 1
        assert msg.parts[0].part_type == PartType.TOOL_CALL

    def test_add_tool_result(self):
        msg = Message(id="m4", role="tool")
        msg.add_tool_result("read_file", "file contents")
        assert len(msg.parts) == 1
        assert msg.parts[0].part_type == PartType.TOOL_RESULT

    def test_add_image(self):
        msg = Message(id="m5", role="user")
        msg.add_image("image.png", "base64data")
        assert len(msg.parts) == 1
        assert msg.parts[0].part_type == PartType.IMAGE

    def test_add_snapshot(self):
        msg = Message(id="m6", role="assistant")
        msg.add_snapshot("snap_001")
        assert len(msg.parts) == 1
        assert msg.parts[0].part_type == PartType.SNAPSHOT

    def test_get_text(self):
        msg = Message(id="m7", role="user")
        msg.add_text("hello")
        msg.add_file("f.py")
        msg.add_text("world")
        assert msg.get_text() == "hello world"

    def test_get_text_empty(self):
        msg = Message(id="m8", role="user")
        assert msg.get_text() == ""

    def test_get_files(self):
        msg = Message(id="m9", role="assistant")
        msg.add_file("a.py")
        msg.add_text("text")
        msg.add_file("b.py")
        files = msg.get_files()
        assert len(files) == 2

    def test_get_tool_calls(self):
        msg = Message(id="m10", role="assistant")
        msg.add_tool_call("tool1", {})
        msg.add_text("text")
        msg.add_tool_call("tool2", {})
        calls = msg.get_tool_calls()
        assert len(calls) == 2

    def test_to_dict(self):
        msg = Message(id="msg1", role="user")
        msg.add_text("hello")
        d = msg.to_dict()
        assert d["id"] == "msg1"
        assert d["role"] == "user"
        assert len(d["parts"]) == 1
        assert d["token_usage"] is None
        assert d["cost_usd"] is None
        assert "timestamp" in d

    def test_to_dict_with_usage(self):
        tu = TokenUsage(10, 5, 15)
        msg = Message(id="msg2", role="assistant", token_usage=tu, cost_usd=0.01)
        d = msg.to_dict()
        assert d["token_usage"]["prompt_tokens"] == 10
        assert d["cost_usd"] == 0.01

    def test_from_dict(self):
        msg = Message(id="msg1", role="user")
        msg.add_text("hello")
        msg.add_tool_call("tool1", {"arg": "val"})
        d = msg.to_dict()
        restored = Message.from_dict(d)
        assert restored.id == "msg1"
        assert restored.role == "user"
        assert len(restored.parts) == 2
        assert restored.parts[0].part_type == PartType.TEXT
        assert restored.parts[1].part_type == PartType.TOOL_CALL

    def test_from_dict_with_usage(self):
        tu = TokenUsage(10, 5, 15)
        msg = Message(id="msg2", role="assistant", token_usage=tu, cost_usd=0.05)
        d = msg.to_dict()
        restored = Message.from_dict(d)
        assert restored.token_usage is not None
        assert restored.token_usage.prompt_tokens == 10
        assert restored.cost_usd == 0.05

    def test_roundtrip(self):
        msg = Message(id="rt1", role="user", cost_usd=0.02)
        msg.add_text("hello")
        msg.add_file("test.py", "code")
        msg.add_snapshot("snap_1")
        d = msg.to_dict()
        restored = Message.from_dict(d)
        assert restored.id == msg.id
        assert len(restored.parts) == 3
        assert restored.cost_usd == 0.02


class TestCreateMessage:
    def test_basic(self):
        msg = create_message("user", "hello")
        assert msg.role == "user"
        assert len(msg.parts) == 1
        assert msg.parts[0].content == "hello"

    def test_no_content(self):
        msg = create_message("assistant")
        assert msg.role == "assistant"
        assert len(msg.parts) == 0


class TestSerializeDeserialize:
    def test_serialize(self):
        msgs = [create_message("user", "hello"), create_message("assistant", "world")]
        data = serialize_messages(msgs)
        assert len(data) == 2
        assert data[0]["role"] == "user"

    def test_deserialize(self):
        msgs = [create_message("user", "hello")]
        data = serialize_messages(msgs)
        restored = deserialize_messages(data)
        assert len(restored) == 1
        assert restored[0].role == "user"

    def test_roundtrip(self):
        msgs = [create_message("user", "hello"), create_message("assistant", "world")]
        data = serialize_messages(msgs)
        restored = deserialize_messages(data)
        assert len(restored) == 2
        assert restored[0].get_text() == "hello"
        assert restored[1].get_text() == "world"
