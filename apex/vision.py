"""Vision input support: model capability detection and image content building.

APEX can attach local image files to one-shot prompts. Whether an image can
actually be sent depends on the selected model, so this module answers two
questions:

1. Does the model support vision? (``detect_vision_support``)
   Primary source: litellm's ``model_cost`` table (``supports_vision``),
   keyed by the canonical model name (with or without the provider prefix).
   Fallback: a conservative pattern table for models litellm does not know
   (OpenRouter, Ollama, custom endpoints).

2. How do we encode a local image for the wire? (``load_image`` /
   ``build_vision_content``) Images are inlined as base64 data URLs in
   OpenAI-style multi-part user content, which litellm converts for
   Anthropic, Bedrock and other providers.

The module is deliberately dependency-light: it must work even when litellm
is not installed (capability detection then relies on the pattern table).
"""

from __future__ import annotations

import base64
import logging
import mimetypes
from pathlib import Path
from typing import Any

__all__ = [
    "MAX_IMAGE_BYTES",
    "VisionNotSupportedError",
    "detect_vision_support",
    "load_image",
    "build_vision_content",
    "prepare_vision_input",
    "check_vision_support",
]

logger = logging.getLogger(__name__)

#: Hard cap on a single inlined image (data URL grows ~4/3 over the raw bytes).
MAX_IMAGE_BYTES = 10 * 1024 * 1024

#: Explicit extension -> MIME map (mimetypes is missing entries on some platforms).
_IMAGE_MIME: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}

#: Conservative substring table used only when litellm has no entry for the
#: model. Every entry must be a model family that is genuinely vision-capable.
_VISION_PATTERNS: tuple[str, ...] = (
    "-vl",
    "vl-",
    "vision",
    "gpt-4o",
    "gpt-4.1",
    "gpt-5",
    "o1",
    "o3",
    "o4",
    "claude-",
    "gemini",
    "grok",
    "llava",
    "pixtral",
    "minicpm-v",
    "mistral-small",
    "internvl",
    "cogvlm",
)


class VisionNotSupportedError(RuntimeError):
    """Raised when images are attached but the selected model has no vision."""


def detect_vision_support(model: str) -> bool:
    """Return True when *model* can accept image inputs.

    Resolution order:

    1. litellm's ``model_cost`` table, probed with the full string and then
       with the suffix after the ``provider/`` prefix.
    2. The conservative :data:`_VISION_PATTERNS` table.

    Unknown models are assumed *not* vision-capable (fail safe: a clear error
    beats a provider 400 mid-task).
    """
    if not isinstance(model, str) or not model.strip():
        return False

    candidates = [model]
    if "/" in model:
        candidates.append(model.split("/", 1)[1])

    try:
        from litellm import model_cost
    except Exception:  # pragma: no cover - litellm optional at import time
        model_cost = None

    if isinstance(model_cost, dict):
        for candidate in candidates:
            info = model_cost.get(candidate)
            if isinstance(info, dict) and "supports_vision" in info:
                return bool(info["supports_vision"])

    lowered = model.lower()
    return any(pattern in lowered for pattern in _VISION_PATTERNS)


def load_image(path: Path | str) -> tuple[bytes, str]:
    """Read *path* and return ``(raw_bytes, mime_type)``.

    Raises:
        FileNotFoundError: the file does not exist.
        ValueError: the file is empty, oversized, or has an unsupported type.
    """
    image_path = Path(path).expanduser()
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    mime = _IMAGE_MIME.get(image_path.suffix.lower())
    if mime is None:
        guessed = mimetypes.guess_type(image_path.name)[0]
        if guessed and guessed.startswith("image/"):
            mime = guessed
    if mime is None:
        raise ValueError(
            f"Unsupported image type '{image_path.suffix or '(none)'}'; "
            "expected png, jpg, webp, gif or bmp"
        )

    raw = image_path.read_bytes()
    if not raw:
        raise ValueError(f"Image file is empty: {image_path}")
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError(f"Image too large ({len(raw)} bytes); maximum is {MAX_IMAGE_BYTES} bytes")
    return raw, mime


def build_vision_content(text: str, images: list[tuple[bytes, str]]) -> list[dict[str, Any]]:
    """Build OpenAI-style multi-part user content with inlined images."""
    parts: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for raw, mime in images:
        encoded = base64.b64encode(raw).decode("ascii")
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{encoded}"},
            }
        )
    return parts


def prepare_vision_input(
    text: str, image_paths: list[Path | str] | None
) -> str | list[dict[str, Any]]:
    """Return *text* unchanged when there are no images, else multi-part content.

    Raises the same errors as :func:`load_image` for each attached path.
    """
    if not image_paths:
        return text
    loaded = [load_image(p) for p in image_paths]
    return build_vision_content(text, loaded)


def check_vision_support(model: str, image_count: int) -> None:
    """Raise :class:`VisionNotSupportedError` when images outpace capability."""
    if image_count and not detect_vision_support(model):
        raise VisionNotSupportedError(
            f"Model '{model}' does not support vision input. "
            "Remove the image(s) or select a vision-capable model (e.g. gpt-4o, "
            "claude-sonnet-4-5, gemini-2.5-pro) with --model."
        )
