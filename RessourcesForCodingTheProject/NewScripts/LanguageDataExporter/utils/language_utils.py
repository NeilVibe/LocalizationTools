"""
Language Utilities for Language Data Exporter.

Provides:
- Korean text detection (for untranslated text identification)
- Word counting for European/SEA languages
- Character counting for CJK languages
- Language classification constants
"""

import re
from typing import Optional

# =============================================================================
# LANGUAGE CLASSIFICATION
# =============================================================================

# Languages that use WORD counting (space-separated)
WORD_COUNT_LANGUAGES = {
    "eng", "fre", "ger", "spa", "por", "ita", "rus", "tur", "pol",
    "kor", "tha", "vie", "ind", "msa"
}

# Languages that use CHARACTER counting (no whitespace delimiters)
CHAR_COUNT_LANGUAGES = {
    "jpn", "zho-cn", "zho-tw"
}

# Languages that get an English column in Excel output
# (European/SEA languages that benefit from English reference)
ENGLISH_COLUMN_LANGUAGES = {
    "fre", "ger", "spa", "por", "ita", "rus", "tur", "pol",
    "kor", "tha", "vie", "ind", "msa"
}

# Languages that do NOT get an English column
# (English itself, and Asian languages with culturally distinct translation)
NO_ENGLISH_COLUMN_LANGUAGES = {
    "eng", "jpn", "zho-cn", "zho-tw"
}

# Display names for language codes
LANGUAGE_NAMES = {
    "eng": "ENG",
    "fre": "FRE",
    "ger": "GER",
    "spa": "SPA",
    "por": "POR",
    "ita": "ITA",
    "rus": "RUS",
    "tur": "TUR",
    "pol": "POL",
    "zho-cn": "ZHO-CN",
    "zho-tw": "ZHO-TW",
    "jpn": "JPN",
    "kor": "KOR",
    "tha": "THA",
    "vie": "VIE",
    "ind": "IND",
    "msa": "MSA",
}

# =============================================================================
# KOREAN DETECTION
# =============================================================================

# Korean syllable block range: U+AC00 to U+D7A3
KOREAN_REGEX = re.compile(r'[\uac00-\ud7a3]')


def contains_korean(text: Optional[str]) -> bool:
    """
    Check if text contains any Korean syllable (Hangul).

    Used to identify untranslated text - if the target language text
    still contains Korean, it hasn't been translated yet.

    Args:
        text: Text to check (can be None)

    Returns:
        True if text contains Korean characters, False otherwise

    Example:
        >>> contains_korean("Hello World")
        False
        >>> contains_korean("안녕하세요")
        True
        >>> contains_korean("Mixed 안녕 text")
        True
    """
    if not text or not isinstance(text, str):
        return False
    return bool(KOREAN_REGEX.search(text))


# =============================================================================
# WORD/CHARACTER COUNTING
# =============================================================================

def count_words(text: Optional[str]) -> int:
    """
    Count words in text (for European/SEA languages).

    Splits by whitespace and counts tokens.
    Returns 0 if text is empty or contains Korean (untranslated).

    Args:
        text: Text to count words in

    Returns:
        Word count (0 if Korean detected, empty, or None)

    Example:
        >>> count_words("Hello World")
        2
        >>> count_words("This is a test.")
        4
        >>> count_words("안녕하세요")  # Korean - untranslated
        0
    """
    if not text or contains_korean(text):
        return 0
    return len(str(text).split())


def count_chars(text: Optional[str]) -> int:
    """
    Count characters in text excluding whitespace (for CJK languages).

    For Chinese/Japanese, character count is more meaningful than word count
    since these languages don't use spaces between words.
    Returns 0 if text is empty or contains Korean (untranslated).

    Args:
        text: Text to count characters in

    Returns:
        Character count excluding whitespace (0 if Korean detected or empty)

    Example:
        >>> count_chars("Hello World")  # Non-CJK but still works
        10
        >>> count_chars("こんにちは")  # Japanese
        5
        >>> count_chars("你好世界")  # Chinese
        4
    """
    if not text or contains_korean(text):
        return 0
    # Remove all whitespace characters
    cleaned = str(text).replace(" ", "").replace("\n", "").replace("\t", "").replace("\r", "")
    return len(cleaned)


def is_word_count_language(lang_code: str) -> bool:
    """Check if language uses word counting."""
    return lang_code.lower() in WORD_COUNT_LANGUAGES


def is_char_count_language(lang_code: str) -> bool:
    """Check if language uses character counting."""
    return lang_code.lower() in CHAR_COUNT_LANGUAGES


def get_word_count_for_language(text: Optional[str], lang_code: str) -> int:
    """
    Get appropriate count (word or character) based on language.

    Args:
        text: Text to count
        lang_code: Language code (e.g., "eng", "jpn")

    Returns:
        Word count for European/SEA languages, character count for CJK
    """
    lang = lang_code.lower()
    if lang in CHAR_COUNT_LANGUAGES:
        return count_chars(text)
    return count_words(text)


def should_include_english_column(lang_code: str) -> bool:
    """
    Determine if English column should be included for this language.

    English column is included for:
    - European languages (FRE, GER, SPA, POR, ITA, RUS, TUR, POL)
    - SEA languages (KOR, THA, VIE, IND, MSA)

    English column is excluded for:
    - English (ENG) - it IS the English
    - Asian languages with culturally distinct translation (JPN, ZHO-CN, ZHO-TW)

    Args:
        lang_code: Language code to check

    Returns:
        True if English column should be included
    """
    return lang_code.lower() in ENGLISH_COLUMN_LANGUAGES
