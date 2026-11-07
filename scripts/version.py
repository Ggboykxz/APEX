"""Single source of truth for the APEX release version.

``VERSION`` at the repository root is canonical. Every other manifest is
verified against it by ``check`` (the CI gate) and rewritten from it by
``sync`` (run by the release workflow, or by hand when bumping).

Usage::

    python scripts/version.py current   # print the canonical version
    python scripts/version.py check     # exit 1 when a manifest drifted
    python scripts/version.py sync      # rewrite every manifest from VERSION

The Homebrew formula is *not* handled here: its SHA256 values can only be
computed after the release artifacts exist, so it is rendered by
``scripts/render_homebrew.py`` during the release.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

# Files where the version is one literal assignment at the start of a line.
LINE_TARGETS = {
    "apex/__init__.py": re.compile(r'^(__version__ = ")([^"]+)(")', re.MULTILINE),
    "pyproject.toml": re.compile(r'^(version = ")([^"]+)(")', re.MULTILINE),
    "rust/apex-rs/Cargo.toml": re.compile(r'^(version = ")([^"]+)(")', re.MULTILINE),
}

NPM_PACKAGE = "integrations/npm/package.json"
CARGO_LOCK = "rust/apex-rs/Cargo.lock"
CARGO_PACKAGE = "apex-rs"


def read_version() -> str:
    """Return the canonical version, refusing anything but MAJOR.MINOR.PATCH."""
    text = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not SEMVER.match(text):
        raise SystemExit(f"VERSION must be MAJOR.MINOR.PATCH, got {text!r}")
    return text


def _line_version(rel: str) -> str | None:
    match = LINE_TARGETS[rel].search((ROOT / rel).read_text(encoding="utf-8"))
    return match.group(2) if match else None


def _npm_version() -> str | None:
    data = json.loads((ROOT / NPM_PACKAGE).read_text(encoding="utf-8"))
    return data.get("version")


def _cargo_lock_version() -> str | None:
    text = (ROOT / CARGO_LOCK).read_text(encoding="utf-8")
    match = re.search(rf'name = "{re.escape(CARGO_PACKAGE)}"\nversion = "([^"]+)"', text)
    return match.group(1) if match else None


def manifest_versions() -> dict[str, str | None]:
    """Map every versioned manifest to the version it currently declares."""
    versions: dict[str, str | None] = {rel: _line_version(rel) for rel in LINE_TARGETS}
    versions[NPM_PACKAGE] = _npm_version()
    versions[CARGO_LOCK] = _cargo_lock_version()
    return versions


def check() -> int:
    """Return 0 when every manifest matches ``VERSION``, 1 otherwise."""
    version = read_version()
    drifts = {rel: found for rel, found in manifest_versions().items() if found != version}
    if not drifts:
        print(f"version {version}: all manifests in sync")
        return 0
    print(f"version drift (canonical VERSION={version}):", file=sys.stderr)
    for rel, found in drifts.items():
        print(f"  {rel}: {found or 'missing'}", file=sys.stderr)
    print("run: python scripts/version.py sync", file=sys.stderr)
    return 1


def _rewrite(path: Path, new: str) -> bool:
    old = path.read_text(encoding="utf-8")
    if old == new:
        return False
    path.write_text(new, encoding="utf-8", newline="")
    return True


def sync() -> int:
    """Rewrite every manifest from ``VERSION``; return the number of changes."""
    version = read_version()
    changed = 0

    for rel, pattern in LINE_TARGETS.items():
        path = ROOT / rel
        new = pattern.sub(rf"\g<1>{version}\g<3>", path.read_text(encoding="utf-8"), count=1)
        if _rewrite(path, new):
            changed += 1
            print(f"updated {rel} -> {version}")

    npm_path = ROOT / NPM_PACKAGE
    npm = json.loads(npm_path.read_text(encoding="utf-8"))
    if npm.get("version") != version:
        npm["version"] = version
        if _rewrite(npm_path, json.dumps(npm, indent=2) + "\n"):
            changed += 1
            print(f"updated {NPM_PACKAGE} -> {version}")

    lock_path = ROOT / CARGO_LOCK
    lock = re.sub(
        rf'(name = "{re.escape(CARGO_PACKAGE)}"\nversion = ")[^"]+(")',
        rf"\g<1>{version}\g<2>",
        lock_path.read_text(encoding="utf-8"),
        count=1,
    )
    if _rewrite(lock_path, lock):
        changed += 1
        print(f"updated {CARGO_LOCK} -> {version}")

    print(f"version {version}: {changed} manifest(s) updated")
    return 0


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "current"
    if command == "current":
        print(read_version())
        return 0
    if command == "check":
        return check()
    if command == "sync":
        return sync()
    print(f"unknown command: {command} (expected current, check or sync)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
