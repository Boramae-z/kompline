"""Internationalization support module."""

from .ko import STRINGS as KO_STRINGS

__all__ = ["KO_STRINGS", "get_string"]


def get_string(key: str, lang: str = "ko") -> str:
    """Retrieve localized string.

    Args:
        key: String key to look up.
        lang: Language code (default: ko).

    Returns:
        Localized string, or key if not found.
    """
    if lang == "ko":
        return KO_STRINGS.get(key, key)
    return key
