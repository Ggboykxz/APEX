#!/usr/bin/env python3
"""Vérifie que le site web APEX affiche les chiffres réels du dépôt.

Sources de vérité (lues depuis le code, jamais codées en dur) :
  VERSION                                  -> src/lib/version.ts APP_VERSION
  apex/config.py MODELS                    -> nombre de modèles
  apex/tools.py TOOL_SCHEMAS              -> nombre d'outils
  apex/agents.py BUILTIN_AGENTS            -> nombre d'agents
  apex/formatter.py BUILTIN_FORMATTERS     -> nombre de formatters
  apex/theme_manager.py BUILTIN_THEMES     -> nombre de thèmes
  apex/http_api.py                         -> nombre de routes HTTP

Usage :  python3 scripts/check-site-stats.py
Sortie : 0 = site à jour, 1 = divergence détectée
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

sys.path.insert(0, str(ROOT))


def _python(*args: str) -> str:
    out = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def truth() -> dict[str, object]:
    """Read the real values from the backend."""
    models = _python("-c", "from apex.config import MODELS; print(len(MODELS))")
    tools = _python("-c", "from apex.tools import TOOL_SCHEMAS; print(len(TOOL_SCHEMAS))")
    agents = _python("-c", "from apex.agents import BUILTIN_AGENTS; print(len(BUILTIN_AGENTS))")
    formatters = _python(
        "-c", "from apex.formatter import BUILTIN_FORMATTERS; print(len(BUILTIN_FORMATTERS))"
    )
    themes = _python(
        "-c", "from apex.theme_manager import BUILTIN_THEMES; print(len(BUILTIN_THEMES))"
    )
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    routes = len(
        re.findall(
            r"router\.add_(get|post|delete|put|patch)",
            (ROOT / "apex" / "http_api.py").read_text(encoding="utf-8"),
        )
    )
    return {
        "version": version,
        "models": int(models),
        "tools": int(tools),
        "agents": int(agents),
        "formatters": int(formatters),
        "themes": int(themes),
        "routes": routes,
    }


def site_text() -> str:
    """Concatenate every site file so a single grep covers all pages."""
    parts = []
    for path in sorted(SRC.rglob("*.tsx")) + sorted(SRC.rglob("*.ts")):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def expected_needles(t: dict[str, object]) -> list[tuple[str, str]]:
    """Build the (label, needle) pairs the site must contain."""
    version = str(t["version"])
    models = int(t["models"])
    tools = int(t["tools"])
    agents = int(t["agents"])
    formatters = int(t["formatters"])
    themes = int(t["themes"])
    routes = int(t["routes"])
    return [
        ("version", f'APP_VERSION = "{version}"'),
        ("version (badges)", f"v{version}"),
        ("modèles", f'APP_MODEL_COUNT = "{models}+"'),
        ("modèles (accueil)", f"{models} Models"),
        ("outils", f"{tools} Tools"),
        ("outils (accueil)", f"'{tools}+'"),
        ("agents", f"'{agents} Specialized Agents'"),
        ("formatters", f"{formatters} Auto-Formatters"),
        ("thèmes", f"{themes} Built-in Themes"),
        ("routes HTTP", f"{routes} HTTP API Endpoints"),
    ]


STALE_VALUES = ("170+ Models", "75+ Tools", "2,094+", "2,842+", "monokai")


def main() -> int:
    t = truth()
    site = site_text()

    missing = [
        f"{label}: {needle!r} absent du site"
        for label, needle in expected_needles(t)
        if needle not in site
    ]
    stale = [
        f"valeur obsolète encore présente: {value!r}" for value in STALE_VALUES if value in site
    ]

    print("Valeurs réelles du dépôt :")
    for key, value in t.items():
        print(f"  {key:12s} = {value}")
    print()

    errors = missing + stale
    if errors:
        print("DIVERGENCES :")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Le site web est à jour avec le dépôt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
