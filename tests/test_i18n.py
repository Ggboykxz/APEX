"""Tests for i18n module."""

import os
from unittest.mock import patch
from apex.i18n import LOCALES, detect_locale, I18n, get_i18n, set_locale


class TestLOCALES:
    """Test LOCALES dictionary."""

    def test_locales_not_empty(self):
        """Test that LOCALES is not empty."""
        assert len(LOCALES) > 0

    def test_has_required_locales(self):
        """Test required locales exist."""
        assert "en" in LOCALES
        assert "ja" in LOCALES
        assert "zh-Hans" in LOCALES
        assert "pt-BR" in LOCALES

    def test_locale_has_required_keys(self):
        """Test each locale has required keys."""
        for locale, strings in LOCALES.items():
            assert "app_name" in strings
            assert "welcome" in strings
            assert "prompt" in strings
            assert "error" in strings


class TestDetectLocale:
    """Test detect_locale function."""

    def test_detect_english(self):
        """Test English detection."""
        with patch.dict(os.environ, {"LANG": "en_US.UTF-8"}):
            locale = detect_locale()
            assert locale == "en"

    def test_detect_japanese(self):
        """Test Japanese detection."""
        with patch.dict(os.environ, {"LANG": "ja_JP.UTF-8"}):
            locale = detect_locale()
            assert locale == "ja"

    def test_detect_chinese(self):
        """Test Chinese detection."""
        with patch.dict(os.environ, {"LANG": "zh_CN.UTF-8"}):
            locale = detect_locale()
            assert locale == "zh-Hans"

    def test_detect_portuguese(self):
        """Test Portuguese detection."""
        with patch.dict(os.environ, {"LANG": "pt_BR.UTF-8"}):
            locale = detect_locale()
            assert locale == "pt-BR"

    def test_detect_fallback(self):
        """Test fallback to English."""
        with patch.dict(os.environ, {}, clear=True):
            locale = detect_locale()
            assert locale == "en"


class TestI18n:
    """Test I18n class."""

    def test_init_english(self):
        """Test initialization with English."""
        i18n = I18n("en")
        assert i18n.locale == "en"
        assert "app_name" in i18n._strings

    def test_init_japanese(self):
        """Test initialization with Japanese."""
        i18n = I18n("ja")
        assert i18n.locale == "ja"
        assert i18n["app_name"] == "APEX"

    def test_init_auto(self):
        """Test auto-detection."""
        i18n = I18n("auto")
        assert i18n.locale in LOCALES

    def test_init_invalid_fallback(self):
        """Test invalid locale falls back to English."""
        i18n = I18n("invalid_locale")
        assert i18n.locale == "en"

    def test_get_existing_key(self):
        """Test get existing key."""
        i18n = I18n("en")
        result = i18n.get("app_name")
        assert result == "APEX"

    def test_get_missing_key(self):
        """Test get missing key with default."""
        i18n = I18n("en")
        result = i18n.get("nonexistent_key", "default_value")
        assert result == "default_value"

    def test_bracket_notation(self):
        """Test bracket notation access."""
        i18n = I18n("en")
        assert i18n["app_name"] == "APEX"

    def test_contains_true(self):
        """Test __contains__ with existing key."""
        i18n = I18n("en")
        assert "app_name" in i18n

    def test_contains_false(self):
        """Test __contains__ with missing key."""
        i18n = I18n("en")
        assert "nonexistent" not in i18n

    def test_available_locales(self):
        """Test available_locales property."""
        i18n = I18n("en")
        locales = i18n.available_locales
        assert "en" in locales
        assert "ja" in locales
        assert "zh-Hans" in locales
        assert "pt-BR" in locales


class TestGlobalI18n:
    """Test global i18n instance."""

    def test_get_i18n(self):
        """Test get_i18n returns instance."""
        i18n = get_i18n()
        assert i18n is not None
        assert isinstance(i18n, I18n)

    def test_set_locale(self):
        """Test set_locale changes global."""
        set_locale("ja")
        i18n = get_i18n()
        assert i18n.locale == "ja"

        set_locale("en")
