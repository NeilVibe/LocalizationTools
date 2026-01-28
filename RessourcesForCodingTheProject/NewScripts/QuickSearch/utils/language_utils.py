"""
Language Utility Functions

Korean detection, text normalization, and language-related utilities.
"""

import re
from typing import Optional


def is_korean(text: str) -> bool:
    """
    Check if text contains any Korean syllables (Hangul).

    Args:
        text: The text to check

    Returns:
        True if text contains Korean characters (U+AC00-U+D7A3)
    """
    if not text:
        return False
    return bool(re.search(r'[\uac00-\ud7a3]', text))


def normalize_text(text: str) -> str:
    """
    Normalize text for dictionary comparison.

    - Handles unmatched quotation marks by keeping only balanced pairs
    - Normalizes Unicode whitespace variants
    - Normalizes apostrophes to straight apostrophe
    - Collapses multiple whitespace to single space

    Args:
        text: The text to normalize

    Returns:
        Normalized text string
    """
    if not isinstance(text, str):
        return ""

    # Handle unmatched quotation marks by identifying balanced pairs
    balanced_indices = set()
    quote_indices = [i for i, char in enumerate(text) if char == '"']

    # Greedily match quotes from left to right in pairs
    for i in range(0, len(quote_indices) - 1, 2):
        balanced_indices.add(quote_indices[i])
        balanced_indices.add(quote_indices[i + 1])

    # Create a new string without unmatched quotes
    result = []
    for i, char in enumerate(text):
        if char == '"' and i not in balanced_indices:
            continue  # Skip this unmatched quote
        result.append(char)

    text = ''.join(result)

    # Normalize all Unicode whitespace variants
    text = re.sub(r'[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000\uFEFF]+', ' ', text)

    # Remove zero-width and directional characters
    text = re.sub(r'[\u200B-\u200F\u202A-\u202E]+', '', text)

    # Normalize apostrophes to straight apostrophe
    text = re.sub(r'[\u2019\u2018\u02BC\u2032\u0060\u00B4]', "'", text)

    # Normalize remaining whitespace
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def tokenize(text: str) -> list:
    """
    Tokenize text by newlines for line-by-line matching.

    Args:
        text: The text to tokenize

    Returns:
        List of tokens (lines), or empty list if invalid
    """
    if isinstance(text, str) and text.strip() != '' and '\t' not in text:
        return re.split(r'\\?\n|\n', text)
    else:
        return []


def is_sentence(text: str) -> bool:
    """
    Check if text ends with sentence-ending punctuation.

    Args:
        text: The text to check

    Returns:
        True if text ends with . ? or !
    """
    return bool(re.search(r'[.?!]\s*$', text.strip()))


def contains_cjk(text: str) -> bool:
    """
    Check if text contains any CJK (Chinese/Japanese/Korean) characters.

    Args:
        text: The text to check

    Returns:
        True if text contains CJK characters
    """
    if not text:
        return False
    # CJK Unified Ideographs + Hangul + Hiragana + Katakana
    return bool(re.search(r'[\u4e00-\u9fff\uac00-\ud7a3\u3040-\u309f\u30a0-\u30ff]', text))


def is_word_boundary(text: str, start: int, end: int) -> bool:
    """
    Check if a match at the given position is at a word boundary.

    For CJK text, considers non-word/non-CJK characters as boundaries.

    Args:
        text: The full text
        start: Start index of the match
        end: End index of the match (exclusive)

    Returns:
        True if the match is isolated (at word boundaries)
    """
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""

    # Check if before/after are word characters (including Korean/CJK)
    before_is_word = bool(re.match(r'[\w가-힣]', before))
    after_is_word = bool(re.match(r'[\w가-힣]', after))

    return not before_is_word and not after_is_word
