"""The release version is declared once and every manifest agrees with it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "version.py"


def test_version_manifests_are_in_sync():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "check"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_current_command_prints_semver():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "current"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0
    parts = result.stdout.strip().split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
