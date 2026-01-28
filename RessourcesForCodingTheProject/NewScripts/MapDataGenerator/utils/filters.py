"""
Text Filters Module

Text normalization, placeholder handling, and Korean detection utilities.
"""

import re
from typing import Optional


# =============================================================================
# REGEX PATTERNS
# =============================================================================

# Korean Hangul syllables range
_KOREAN_RE = re.compile(r'[\uAC00-\uD7AF]')

# Placeholder suffix pattern: {something#suffix} -> {something}
_PLACEHOLDER_SUFFIX_RE = re.compile(r'\{([^#}]+)#[^}]+\}')

# Whitespace normalization
_WHITESPACE_RE = re.compile(r'\s+', flags=re.UNICODE)

# HTML-like breaks
_BR_TAG_RE = re.compile(r'<br\s*/?\s*>', re.IGNORECASE)


# =============================================================================
# TEXT NORMALIZATION
# =============================================================================

def normalize_text(text: Optional[str]) -> str:
    """
    Basic text normalization.

    - Trim whitespace
    - Collapse multiple spaces to single space
    - Replace <br/> with newline

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    if not text:
        return ""

    # Replace <br/> tags with newlines
    text = _BR_TAG_RE.sub('\n', text)

    # Collapse whitespace (but preserve newlines)
    lines = text.split('\n')
    lines = [_WHITESPACE_RE.sub(' ', line).strip() for line in lines]

    return '\n'.join(lines).strip()


def normalize_placeholders(text: Optional[str]) -> str:
    """
    Normalize text for matching by removing placeholder suffixes.

    Example:
        "{player#format}" -> "{player}"

    This allows matching Korean text with different placeholder formats
    across different language files.

    Args:
        text: Input text

    Returns:
        Normalized text with placeholder suffixes removed
    """
    if not text:
        return ""

    # Remove #suffix inside placeholders
    text = _PLACEHOLDER_SUFFIX_RE.sub(r'{\1}', text)

    # Collapse whitespace to single space
    text = _WHITESPACE_RE.sub(' ', text).strip()

    return text


def normalize_for_search(text: Optional[str]) -> str:
    """
    Normalize text for search matching.

    - Lowercase
    - Remove extra whitespace
    - Remove placeholder suffixes

    Args:
        text: Input text

    Returns:
        Search-normalized text
    """
    if not text:
        return ""

    text = normalize_placeholders(text)
    return text.lower()


# =============================================================================
# KOREAN DETECTION
# =============================================================================

def contains_korean(text: Optional[str]) -> bool:
    """
    Check if text contains Korean characters.

    Uses Hangul syllables range (U+AC00 to U+D7AF).

    Args:
        text: Text to check

    Returns:
        True if text contains Korean characters
    """
    if not text:
        return False
    return bool(_KOREAN_RE.search(text))


def is_good_translation(text: Optional[str]) -> bool:
    """
    Check if translation is valid.

    A good translation is:
    - Non-empty
    - Does not contain Korean characters (was actually translated)

    Args:
        text: Translation text to check

    Returns:
        True if translation is valid
    """
    if not text or not text.strip():
        return False
    return not contains_korean(text)


def is_korean_only(text: Optional[str]) -> bool:
    """
    Check if text contains only Korean characters and whitespace.

    Args:
        text: Text to check

    Returns:
        True if text is Korean-only
    """
    if not text:
        return False

    # Remove whitespace and check if all remaining chars are Korean
    chars = ''.join(text.split())
    if not chars:
        return False

    return all(_KOREAN_RE.match(c) for c in chars)


# =============================================================================
# TEXT UTILITIES
# =============================================================================

def truncate(text: Optional[str], max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def clean_description(text: Optional[str]) -> str:
    """
    Clean description text for display.

    - Replace <br/> with newline
    - Remove excessive whitespace
    - Trim

    Args:
        text: Description text

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    text = _BR_TAG_RE.sub('\n', text)
    text = text.strip()

    return text
