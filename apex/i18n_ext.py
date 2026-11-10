"""APEX i18n — infrastructure de localisation.

Phase 4 (parité OpenCode : 18 langues). Fournit :

- un registre de locales (langues supportées),
- la fonction ``t(key, locale, **kwargs)`` avec fallback vers l'anglais,
- le chargement des fichiers JSON ``locales/<code>.json``.

Structure attendue dans ``apex/locales/`` (ou chemin custom via
``APEX_LOCALES_DIR``) :

    locales/
      en.json
      fr.json
      es.json
      ...
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

__all__ = ["SUPPORTED_LOCALES", "t", "load_locale", "LocaleRegistry"]

SUPPORTED_LOCALES = (
    "en", "fr", "es", "de", "it", "pt", "ru", "ja", "ko",
    "zh-CN", "zh-TW", "ar", "he", "pl", "nl", "tr", "th", "vi",
)

DEFAULT_LOCALE = "en"


class LocaleRegistry:
    """Charge et met en cache les fichiers de locale."""

    def __init__(self, locales_dir: Optional[str] = None) -> None:
        env_dir = os.environ.get("APEX_LOCALES_DIR")
        self.dir = Path(locales_dir or env_dir or Path(__file__).parent / "locales")
        self._cache: dict[str, dict[str, Any]] = {}

    def available(self) -> list[str]:
        if not self.dir.exists():
            return []
        return sorted(
            p.stem for p in self.dir.glob("*.json") if p.stem in SUPPORTED_LOCALES
        )

    def load(self, code: str) -> dict[str, Any]:
        code = code if code in SUPPORTED_LOCALES else DEFAULT_LOCALE
        if code in self._cache:
            return self._cache[code]
        path = self.dir / f"{code}.json"
        if not path.exists():
            self._cache[code] = {}
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        self._cache[code] = data
        return data

    def translate(self, key: str, locale: str = DEFAULT_LOCALE, **kwargs: Any) -> str:
        data = self.load(locale)
        template = data.get(key)
        if template is None and locale != DEFAULT_LOCALE:
            template = self.load(DEFAULT_LOCALE).get(key)
        if template is None:
            return key
        if kwargs:
            for k, v in kwargs.items():
                template = template.replace(f"{{{k}}}", str(v))
        return template

_registry: Optional[LocaleRegistry] = None


def get_registry() -> LocaleRegistry:
    global _registry
    if _registry is None:
        _registry = LocaleRegistry()
    return _registry


def t(key: str, locale: str = DEFAULT_LOCALE, **kwargs: Any) -> str:
    """Traduit une clé (fallback anglais)."""
    return get_registry().translate(key, locale, **kwargs)
