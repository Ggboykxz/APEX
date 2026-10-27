"""Regenerate the Python-written Fernet session fixtures.

Run from `rust/apex-rs`:

    python tests/fixtures/session/generate.py

The keys are deterministic test values, not secrets. The payload mirrors what
`apex/session.py`'s `SessionManager.save` writes: compact JSON with `name`,
`timestamp`, `model`, `cwd`, `history` and `usage`, encrypted with
`cryptography.fernet.Fernet`.
"""

import base64
import hashlib
import json
from pathlib import Path

from cryptography.fernet import Fernet

HERE = Path(__file__).resolve().parent


def key_from_label(label: bytes) -> bytes:
    return base64.urlsafe_b64encode(hashlib.sha256(label).digest())


PAYLOAD = {
    "name": "python-fixture",
    "timestamp": "2026-01-02T03:04:05.123456",
    "model": "anthropic/claude-sonnet-4-5",
    "cwd": "/home/python/project",
    "history": [
        {"role": "user", "content": "Add a health check to the API"},
        {
            "role": "assistant",
            "content": "I'll add a `/health` route and a test for it.",
        },
    ],
    "usage": {"prompt_tokens": 42, "completion_tokens": 17, "total_tokens": 59},
}

LEGACY_PAYLOAD = {
    "name": "python-legacy",
    "timestamp": "2026-01-02T03:04:06.654321",
    "model": "openai/gpt-5",
    "cwd": "C:\\python\\legacy",
    "history": [
        {"role": "user", "content": "Run the smoke tests"},
        {"role": "assistant", "content": "All smoke tests passed."},
    ],
    "usage": {"prompt_tokens": 8, "completion_tokens": 6, "total_tokens": 14},
}


def compact(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode()


def main() -> None:
    fernet_key = key_from_label(b"apex-rust-fixture-key")
    (HERE / "fernet.key").write_bytes(fernet_key)
    (HERE / "python_session.enc").write_bytes(Fernet(fernet_key).encrypt(compact(PAYLOAD)))

    # Legacy 32-byte raw key: Python derives the Fernet key as
    # urlsafe_b64encode(sha256(raw + b":fernet")).
    legacy_raw = b"apex-legacy-fixture-key-00000000"
    assert len(legacy_raw) == 32, len(legacy_raw)
    legacy_key = key_from_label(legacy_raw + b":fernet")
    (HERE / "legacy.key").write_bytes(legacy_raw)
    (HERE / "python_session_legacy.enc").write_bytes(
        Fernet(legacy_key).encrypt(compact(LEGACY_PAYLOAD))
    )

    print("wrote fernet.key, legacy.key and two encrypted fixtures")


if __name__ == "__main__":
    main()
