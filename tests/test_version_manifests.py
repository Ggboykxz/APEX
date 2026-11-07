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


def test_homebrew_formula_renders_from_the_template(tmp_path):
    output = tmp_path / "apex-ai.rb"
    digest = "a" * 64
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "render_homebrew.py"),
            "--version",
            "2.5.0",
            "--sha256",
            digest,
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    body = output.read_text(encoding="utf-8")
    assert "__SDIST_URL__" not in body
    assert "__SDIST_SHA256__" not in body
    assert digest in body
    assert "apex_ai-2.5.0.tar.gz" in body
    assert "class ApexAi < Formula" in body


def test_homebrew_render_rejects_a_bad_digest(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "render_homebrew.py"),
            "--version",
            "2.5.0",
            "--sha256",
            "not-a-digest",
            "--output",
            str(tmp_path / "apex-ai.rb"),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 2
    assert "invalid SHA256" in result.stderr
