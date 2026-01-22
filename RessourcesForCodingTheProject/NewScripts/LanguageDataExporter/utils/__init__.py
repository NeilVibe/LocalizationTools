"""
Utilities package for Language Data Exporter.

Shared utilities for language detection, text processing, and VRS ordering.
"""

from .language_utils import (
    contains_korean,
    count_source_words,
    count_words,
    count_chars,
    get_word_count_for_language,
    is_word_count_language,
    is_char_count_language,
    should_include_english_column,
    WORD_COUNT_LANGUAGES,
    CHAR_COUNT_LANGUAGES,
    ENGLISH_COLUMN_LANGUAGES,
    NO_ENGLISH_COLUMN_LANGUAGES,
    LANGUAGE_NAMES,
)

from .vrs_ordering import (
    VRSOrderer,
    find_most_recent_excel,
    load_vrs_order,
    load_vrs_with_categories,
)

__all__ = [
    # Language utilities
    "contains_korean",
    "count_source_words",
    "count_words",
    "count_chars",
    "get_word_count_for_language",
    "is_word_count_language",
    "is_char_count_language",
    "should_include_english_column",
    "WORD_COUNT_LANGUAGES",
    "CHAR_COUNT_LANGUAGES",
    "ENGLISH_COLUMN_LANGUAGES",
    "NO_ENGLISH_COLUMN_LANGUAGES",
    "LANGUAGE_NAMES",
    # VRS ordering
    "VRSOrderer",
    "find_most_recent_excel",
    "load_vrs_order",
    "load_vrs_with_categories",
]
