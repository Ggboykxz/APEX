"""Render ``Formula/apex-ai.rb`` from its template.

The Homebrew formula needs the SHA256 of the PyPI sdist, which only exists
after the release build. The release workflow builds the sdist first, hashes
it, then renders the formula and uploads it as a release asset.

Usage::

    python scripts/render_homebrew.py --version 2.5.0 --sha256 <digest> \
        [--url URL] [--output PATH]

``--url`` defaults to the PyPI files URL built from the sdist filename that
``python -m build`` produced. Pass it explicitly when the release workflow
knows the exact filename.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT / "Formula" / "apex-ai.rb.tmpl"
DEFAULT_OUTPUT = ROOT / "Formula" / "apex-ai.rb"


def rendered_url(version: str) -> str:
    """Return the PyPI sdist URL for a version (legacy redirect path)."""
    filename = f"apex_ai-{version}.tar.gz"
    return f"https://files.pythonhosted.org/packages/source/a/apex-ai/{filename}"


def render(version: str, sha256: str, url: str, template: Path = DEFAULT_TEMPLATE) -> str:
    """Return the formula body with every placeholder replaced."""
    text = template.read_text(encoding="utf-8")
    replacements = {
        "__SDIST_URL__": url,
        "__SDIST_SHA256__": sha256.lower(),
    }
    for placeholder, value in replacements.items():
        if placeholder not in text:
            raise SystemExit(f"template is missing {placeholder}")
        text = text.replace(placeholder, value)
    if not version or any(ch not in "0123456789." for ch in version):
        raise SystemExit(f"invalid version: {version!r}")
    return text


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="release version (without the v)")
    parser.add_argument("--sha256", required=True, help="SHA256 of the PyPI sdist")
    parser.add_argument("--url", default=None, help="sdist URL (defaults to the PyPI path)")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    digest = args.sha256.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        print(f"invalid SHA256: {args.sha256!r}", file=sys.stderr)
        return 2

    url = args.url or rendered_url(args.version)
    body = render(args.version, digest, url, args.template)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(body, encoding="utf-8", newline="")
    print(f"rendered {args.output} for {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
