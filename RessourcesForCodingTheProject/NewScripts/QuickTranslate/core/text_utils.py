"""
Text Utilities - Shared text normalization functions.

Single source of truth for text normalization across all modules.
"""

import html
import re
from typing import Optional


def normalize_text(txt: Optional[str]) -> str:
    """
    Normalize text for consistent matching.

    This is the CANONICAL implementation used across all modules:
    1. HTML entity unescaping (&lt; -> <, &amp; -> &)
    2. Leading/trailing whitespace stripping
    3. Internal whitespace collapsing to single space
    4. &desc; marker removal (legacy description prefix)

    Args:
        txt: Text to normalize

    Returns:
        Normalized text string
    """
    if not txt:
        return ""
    # Unescape HTML entities
    txt = html.unescape(str(txt))
    # Strip and collapse whitespace
    txt = re.sub(r'\s+', ' ', txt.strip())
    # Remove legacy &desc; markers
    if txt.lower().startswith("&desc;"):
        txt = txt[6:].lstrip()
    elif txt.lower().startswith("&amp;desc;"):
        txt = txt[10:].lstrip()
    return txt


def normalize_for_matching(txt: Optional[str]) -> str:
    """
    Normalize text for case-insensitive matching.

    Uses normalize_text() then lowercases for matching comparisons.

    Args:
        txt: Text to normalize

    Returns:
        Lowercase normalized text
    """
    return normalize_text(txt).lower()


def normalize_nospace(txt: str) -> str:
    """
    Remove ALL whitespace from text for fallback matching.

    Used when exact match fails but text differs only in whitespace.

    Args:
        txt: Text to process

    Returns:
        Text with all whitespace removed
    """
    return re.sub(r'\s+', '', txt)
