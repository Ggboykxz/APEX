"""Tests for i18n module — no mocks, real environment manipulation via monkeypatch."""

from apex.i18n import LOCALES, detect_locale, I18n, get_i18n, set_locale


# ---------------------------------------------------------------------------
# LOCALES dictionary
# ---------------------------------------------------------------------------


class TestLocales:
    def test_locales_not_empty(self):
        assert len(LOCALES) > 0

    def test_has_required_locales(self):
        assert "en" in LOCALES
        assert "ja" in LOCALES
        assert "zh-Hans" in LOCALES
        assert "pt-BR" in LOCALES

    def test_locale_has_required_keys(self):
        required_keys = [
            "app_name",
            "welcome",
            "prompt",
            "thinking",
            "working",
            "done",
            "error",
            "success",
            "help_title",
            "model",
            "agent",
            "cwd",
            "clear",
            "sessions",
            "agents",
            "help",
            "quit",
        ]
        for locale, strings in LOCALES.items():
            for key in required_keys:
                assert key in strings, f"Missing key '{key}' in locale '{locale}'"

    def test_all_locales_have_same_keys(self):
        """All locales should have the same set of keys."""
        keys = set(LOCALES["en"].keys())
        for locale, strings in LOCALES.items():
            assert set(strings.keys()) == keys, f"Key mismatch in locale '{locale}'"


# ---------------------------------------------------------------------------
# detect_locale
# ---------------------------------------------------------------------------


class TestDetectLocale:
    def test_detect_english(self, monkeypatch):
        monkeypatch.setenv("LANG", "en_US.UTF-8")
        assert detect_locale() == "en"

    def test_detect_japanese(self, monkeypatch):
        monkeypatch.setenv("LANG", "ja_JP.UTF-8")
        assert detect_locale() == "ja"

    def test_detect_chinese(self, monkeypatch):
        monkeypatch.setenv("LANG", "zh_CN.UTF-8")
        assert detect_locale() == "zh-Hans"

    def test_detect_portuguese(self, monkeypatch):
        monkeypatch.setenv("LANG", "pt_BR.UTF-8")
        assert detect_locale() == "pt-BR"

    def test_detect_no_lang_var(self, monkeypatch):
        monkeypatch.delenv("LANG", raising=False)
        assert detect_locale() == "en"

    def test_detect_empty_lang(self, monkeypatch):
        monkeypatch.setenv("LANG", "")
        assert detect_locale() == "en"

    def test_detect_unknown_lang(self, monkeypatch):
        monkeypatch.setenv("LANG", "fr_FR.UTF-8")
        assert detect_locale() == "en"

    def test_detect_strips_encoding(self, monkeypatch):
        monkeypatch.setenv("LANG", "ja_JP.eucJP")
        assert detect_locale() == "ja"


# ---------------------------------------------------------------------------
# I18n class
# ---------------------------------------------------------------------------


class TestI18n:
    def test_init_english(self):
        i18n = I18n("en")
        assert i18n.locale == "en"
        assert "app_name" in i18n._strings

    def test_init_japanese(self):
        i18n = I18n("ja")
        assert i18n.locale == "ja"

    def test_init_chinese(self):
        i18n = I18n("zh-Hans")
        assert i18n.locale == "zh-Hans"

    def test_init_portuguese(self):
        i18n = I18n("pt-BR")
        assert i18n.locale == "pt-BR"

    def test_init_auto(self, monkeypatch):
        monkeypatch.setenv("LANG", "ja_JP.UTF-8")
        i18n = I18n("auto")
        assert i18n.locale == "ja"

    def test_init_invalid_fallback(self):
        i18n = I18n("invalid_locale")
        assert i18n.locale == "en"

    def test_get_existing_key(self):
        i18n = I18n("en")
        assert i18n.get("app_name") == "APEX"

    def test_get_missing_key_default(self):
        i18n = I18n("en")
        assert i18n.get("nonexistent_key") == ""

    def test_get_missing_key_custom_default(self):
        i18n = I18n("en")
        assert i18n.get("nonexistent_key", "fallback") == "fallback"

    def test_bracket_notation_existing(self):
        i18n = I18n("en")
        assert i18n["app_name"] == "APEX"

    def test_bracket_notation_missing(self):
        i18n = I18n("en")
        # __getitem__ uses key as default
        result = i18n["nonexistent_key"]
        assert result == "nonexistent_key"

    def test_contains_true(self):
        i18n = I18n("en")
        assert "app_name" in i18n

    def test_contains_false(self):
        i18n = I18n("en")
        assert "nonexistent" not in i18n

    def test_available_locales(self):
        i18n = I18n("en")
        locales = i18n.available_locales
        assert "en" in locales
        assert "ja" in locales
        assert "zh-Hans" in locales
        assert "pt-BR" in locales

    def test_english_welcome_message(self):
        i18n = I18n("en")
        assert "Welcome" in i18n.get("welcome")

    def test_japanese_welcome_message(self):
        i18n = I18n("ja")
        assert "ようこそ" in i18n.get("welcome")

    def test_chinese_welcome_message(self):
        i18n = I18n("zh-Hans")
        assert "欢迎" in i18n.get("welcome")

    def test_portuguese_welcome_message(self):
        i18n = I18n("pt-BR")
        assert "Bem-vindo" in i18n.get("welcome")


# ---------------------------------------------------------------------------
# Global i18n instance
# ---------------------------------------------------------------------------


class TestGlobalI18n:
    def test_get_i18n_returns_instance(self):
        i18n = get_i18n()
        assert i18n is not None
        assert isinstance(i18n, I18n)

    def test_get_i18n_caches(self):
        """Repeated calls return the same instance."""
        import apex.i18n as mod

        mod._i18n_instance = None  # reset
        first = get_i18n()
        second = get_i18n()
        assert first is second

    def test_set_locale(self):
        set_locale("ja")
        i18n = get_i18n()
        assert i18n.locale == "ja"
        # Reset for other tests
        set_locale("en")

    def test_set_locale_to_chinese(self):
        set_locale("zh-Hans")
        i18n = get_i18n()
        assert i18n.locale == "zh-Hans"
        set_locale("en")

    def test_set_locale_invalid(self):
        set_locale("invalid")
        i18n = get_i18n()
        assert i18n.locale == "en"
