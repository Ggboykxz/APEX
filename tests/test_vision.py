"""Tests for apex/vision.py — capability detection, image loading, content building."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from apex.agent import Agent
from apex.config import Config
from apex.vision import (
    MAX_IMAGE_BYTES,
    VisionNotSupportedError,
    build_vision_content,
    check_vision_support,
    detect_vision_support,
    load_image,
    prepare_vision_input,
)

# 1x1 transparent PNG.
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _make_response(content: str):
    """Build a mock litellm completion response with plain text content."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    usage = MagicMock()
    usage.prompt_tokens = 5
    usage.completion_tokens = 5
    usage.total_tokens = 10
    resp.usage = usage
    return resp


@pytest.fixture
def agent(tmp_path):
    """Fresh Agent with isolated config (no global config interference)."""
    cfg = Config(config_path=tmp_path / "test_config.json")
    return Agent(config=cfg)


# ---------------------------------------------------------------------------
# detect_vision_support
# ---------------------------------------------------------------------------


class TestDetectVisionSupport:
    def test_known_vision_model(self):
        assert detect_vision_support("gpt-4o") is True

    def test_provider_prefix_stripped_for_lookup(self):
        assert detect_vision_support("openai/gpt-4o") is True

    def test_model_cost_says_no_vision(self):
        # Deterministic: litellm's table decides even for unknown names.
        with patch("litellm.model_cost", {"texty-llm": {"supports_vision": False}}):
            assert detect_vision_support("texty-llm") is False

    def test_litellm_table_overrides_pattern_table(self):
        # A name matching a pattern ("claude-") is still decided by litellm.
        with patch("litellm.model_cost", {"myclaude-vision": {"supports_vision": False}}):
            assert detect_vision_support("myclaude-vision") is False

    def test_pattern_fallback_for_unknown_model(self):
        with patch("litellm.model_cost", {}):
            assert detect_vision_support("openrouter/qwen/qwen2.5-vl-72b") is True

    def test_unknown_model_fails_safe(self):
        with patch("litellm.model_cost", {}):
            assert detect_vision_support("totally-unknown-model") is False

    def test_empty_or_non_string(self):
        assert detect_vision_support("") is False
        assert detect_vision_support("   ") is False
        assert detect_vision_support(None) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# load_image
# ---------------------------------------------------------------------------


class TestLoadImage:
    def test_png_roundtrip(self, tmp_path):
        p = tmp_path / "a.png"
        p.write_bytes(PNG_BYTES)
        assert load_image(p) == (PNG_BYTES, "image/png")

    def test_jpeg_mime(self, tmp_path):
        p = tmp_path / "a.jpeg"
        p.write_bytes(PNG_BYTES)
        assert load_image(p) == (PNG_BYTES, "image/jpeg")

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_image(tmp_path / "nope.png")

    def test_unsupported_type(self, tmp_path):
        p = tmp_path / "a.txt"
        p.write_text("not an image")
        with pytest.raises(ValueError, match="Unsupported image type"):
            load_image(p)

    def test_empty_file(self, tmp_path):
        p = tmp_path / "a.png"
        p.write_bytes(b"")
        with pytest.raises(ValueError, match="empty"):
            load_image(p)

    def test_oversized_file(self, tmp_path):
        p = tmp_path / "big.png"
        p.write_bytes(b"\x00" * (MAX_IMAGE_BYTES + 1))
        with pytest.raises(ValueError, match="too large"):
            load_image(p)


# ---------------------------------------------------------------------------
# build_vision_content / prepare_vision_input
# ---------------------------------------------------------------------------


class TestBuildVisionContent:
    def test_text_plus_image(self):
        parts = build_vision_content("hello", [(b"img-bytes", "image/png")])
        assert parts[0] == {"type": "text", "text": "hello"}
        url = parts[1]["image_url"]["url"]
        assert url.startswith("data:image/png;base64,")
        assert base64.b64decode(url.split(",", 1)[1]) == b"img-bytes"

    def test_multiple_images_keep_order(self):
        parts = build_vision_content("t", [(b"one", "image/png"), (b"two", "image/webp")])
        assert [p["type"] for p in parts] == ["text", "image_url", "image_url"]
        assert parts[1]["image_url"]["url"].startswith("data:image/png;")
        assert parts[2]["image_url"]["url"].startswith("data:image/webp;")


class TestPrepareVisionInput:
    def test_no_images_returns_text_unchanged(self):
        assert prepare_vision_input("hello", None) == "hello"
        assert prepare_vision_input("hello", []) == "hello"

    def test_with_images_returns_multipart(self, tmp_path):
        p = tmp_path / "a.png"
        p.write_bytes(PNG_BYTES)
        out = prepare_vision_input("describe", [p])
        assert isinstance(out, list)
        assert out[0] == {"type": "text", "text": "describe"}
        assert out[1]["type"] == "image_url"

    def test_missing_image_propagates(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            prepare_vision_input("x", [tmp_path / "missing.png"])


# ---------------------------------------------------------------------------
# check_vision_support
# ---------------------------------------------------------------------------


class TestCheckVisionSupport:
    def test_vision_model_with_images_ok(self):
        check_vision_support("gpt-4o", 3)

    def test_any_model_without_images_ok(self):
        check_vision_support("totally-unknown-model", 0)

    def test_non_vision_model_with_images_raises(self):
        with pytest.raises(VisionNotSupportedError, match="does not support vision"):
            check_vision_support("totally-unknown-model", 1)


# ---------------------------------------------------------------------------
# Agent integration (mocked litellm)
# ---------------------------------------------------------------------------


class TestAgentVisionIntegration:
    def test_chat_with_images_sends_multipart(self, agent, tmp_path):
        img = tmp_path / "a.png"
        img.write_bytes(PNG_BYTES)
        agent.model = "gpt-4o"
        with patch("apex.agent.litellm.completion", return_value=_make_response("ok")) as m:
            out = agent.chat("describe this", images=[str(img)])
        assert out == "ok"
        assert m.called
        messages = m.call_args.kwargs["messages"]
        user = messages[-1]
        assert user["role"] == "user"
        assert isinstance(user["content"], list)
        assert user["content"][0] == {"type": "text", "text": "describe this"}
        assert user["content"][1]["type"] == "image_url"
        # The multipart content is what gets stored in history.
        assert agent.history[-2]["content"] == user["content"]

    def test_chat_with_images_non_vision_model_errors_without_llm_call(self, agent, tmp_path):
        img = tmp_path / "a.png"
        img.write_bytes(PNG_BYTES)
        agent.model = "totally-unknown-model"
        # Empty model_cost table: capability falls through to the pattern
        # table, which does not know this model -> fail safe.
        with (
            patch("litellm.model_cost", {}),
            patch("apex.agent.litellm.completion") as m,
        ):
            out = agent.chat("describe this", images=[str(img)])
        assert out.startswith("ERROR:")
        assert "does not support vision" in out
        m.assert_not_called()

    def test_chat_without_images_keeps_string_content(self, agent):
        agent.model = "gpt-4o"
        with patch("apex.agent.litellm.completion", return_value=_make_response("ok")) as m:
            out = agent.chat("plain")
        assert out == "ok"
        messages = m.call_args.kwargs["messages"]
        assert messages[-1]["content"] == "plain"
