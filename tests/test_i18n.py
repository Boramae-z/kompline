"""Internationalization strings tests."""

from kompline.i18n import get_string, KO_STRINGS


def test_korean_strings_exist():
    """Test required Korean strings exist."""
    required_keys = [
        "page_title",
        "start_analysis",
        "compliant",
        "non_compliant",
        "settings",
        "github_import",
        "mapping_confirmation",
    ]
    for key in required_keys:
        assert key in KO_STRINGS
        assert len(KO_STRINGS[key]) > 0


def test_get_string_korean():
    """Test Korean string retrieval."""
    title = get_string("page_title", "ko")
    assert "Kompline" in title


def test_get_string_fallback():
    """Test fallback to key when not found."""
    result = get_string("nonexistent_key", "ko")
    assert result == "nonexistent_key"


def test_get_string_default_lang():
    """Test default language is Korean."""
    title = get_string("page_title")
    assert "Kompline" in title
