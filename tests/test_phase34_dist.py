"""Tests unitaires Phase 3+4 — interface & distribution (parité OpenCode).

Couvre :
  - apex.i18n_ext : registre de locales, traduction + fallback
  - apex.codegen_sdk : génération de client depuis un schéma API
  - playwright.config / e2e : présence de la suite de test configurée

Exécution : ``PYTHONPATH=/home/user/myapp/APEX python3 -B tests/test_phase34_dist.py``
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

from apex.i18n_ext import LocaleRegistry, t
from apex.codegen_sdk import generate_client, load_schema

SCHEMA = {
    "openapi": "3.0.0",
    "paths": {
        "/api/v1/health": {"get": {"operationId": "getHealth", "summary": "Health check"}},
        "/api/v1/sessions": {
            "get": {"operationId": "listSessions", "summary": "List sessions"},
            "post": {"operationId": "createSession", "summary": "Create session"},
        },
    },
    "components": {
        "schemas": {
            "Session": {
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                }
            }
        }
    },
}


def test_i18n_registry_load():
    reg = LocaleRegistry()
    data = reg.load("en")
    assert data["welcome"] == "Welcome to APEX"
    fr = reg.load("fr")
    assert fr["welcome"] == "Bienvenue sur APEX"


def test_i18n_t_key():
    assert t("welcome", locale="en") == "Welcome to APEX"
    assert t("welcome", locale="fr") == "Bienvenue sur APEX"


def test_i18n_interpolation():
    assert t("model_count", locale="en", n=170) == "170 models available"
    assert t("model_count", locale="fr", n=170) == "170 modèles disponibles"


def test_i18n_fallback_unknown_locale():
    # Locale inconnue -> fallback anglais
    assert t("welcome", locale="xx") == "Welcome to APEX"


def test_codegen_generates_functions():
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / "client.py"
        generate_client(SCHEMA, out)
        src = out.read_text(encoding="utf-8")
        assert "def get_health" in src
        assert "def list_sessions" in src
        assert "def create_session" in src
        assert "class session" in src


def test_codegen_schema_load():
    schema = load_schema()
    assert "paths" in schema
    assert "/api/v1/health" in schema["paths"]


def test_e2e_suite_present():
    root = pathlib.Path(__file__).resolve().parent.parent
    assert (root / "playwright.config.ts").exists()
    assert (root / "e2e").is_dir()
    assert any((root / "e2e").glob("*.spec.ts"))


if __name__ == "__main__":
    tests = [
        ("i18n_registry_load", test_i18n_registry_load),
        ("i18n_t_key", test_i18n_t_key),
        ("i18n_interpolation", test_i18n_interpolation),
        ("i18n_fallback_unknown_locale", test_i18n_fallback_unknown_locale),
        ("codegen_generates_functions", test_codegen_generates_functions),
        ("codegen_schema_load", test_codegen_schema_load),
        ("e2e_suite_present", test_e2e_suite_present),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)
    print("=== TOUS LES TESTS PHASE 3+4 REUSSIS ===")
