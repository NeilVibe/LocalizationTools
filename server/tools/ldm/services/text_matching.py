"""
Text Matching Utilities -- normalization for merge/transfer matching.

Ported from QuickTranslate core/text_utils.py.

IMPORTANT: This is NOT the same as server/utils/text_utils.py:normalize_text().
That module handles display normalization (strip quotes, remove zero-width chars).
This module handles merge-matching normalization (HTML unescape, whitespace collapse,
&desc; removal) -- used when building lookup tables for translation transfer.
"""

from __future__ import annotations

import html
import re
from typing import Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Formula / garbage text detection
# ---------------------------------------------------------------------------

# Formula prefix: = + @ are always formula indicators.
# Hyphen excluded -- "-word" is common in game text (e.g. "-select", "-Default").
_FORMULA_RE = re.compile(r'^[=+@][A-Za-z_]')
_ARRAY_FORMULA_RE = re.compile(r'^\{=.*\}$')

# Match Excel errors anywhere in the string
_EXCEL_ERROR_RE = re.compile(
    r'#(?:N/A|REF!|VALUE!|NAME\?|NULL!|DIV/0!|NUM!|GETTING_DATA'
    r'|SPILL!|CALC!|BLOCKED!|CONNECT!|FIELD!|UNKNOWN!)',
    re.IGNORECASE,
)


def is_formula_text(text: Optional[str]) -> Optional[str]:
    """Check if a string looks like an Excel formula or error value.

    Returns:
        Reason string if the text is suspicious, None if clean.
    """
    if not text:
        return None
    stripped = text.strip()
    if _FORMULA_RE.match(stripped):
        return f'Excel formula ({stripped[:40]})'
    if _ARRAY_FORMULA_RE.match(stripped):
        return f'Array formula ({stripped[:40]})'
    m = _EXCEL_ERROR_RE.search(stripped)
    if m:
        return f'Excel error value ({m.group()})'
    if 'openpyxl.' in stripped:
        return f'openpyxl object repr ({stripped[:40]})'
    if '_xlfn.' in stripped.lower():
        return f'Excel internal function ({stripped[:40]})'
    return None


# ---------------------------------------------------------------------------
# Text normalization for merge matching
# ---------------------------------------------------------------------------


def normalize_text_for_match(txt: Optional[str]) -> str:
    """Normalize text for consistent merge matching.

    This is the CANONICAL merge-matching normalization:
    1. HTML entity unescaping (&lt; -> <, &amp; -> &)
    2. Leading/trailing whitespace stripping
    3. Internal whitespace collapsing to single space
    4. &desc; marker removal (legacy description prefix)

    NOT the same as LocaNext's display normalize_text() which strips
    quotes and removes zero-width chars.

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
    """Normalize text for case-insensitive matching.

    Uses normalize_text_for_match() then lowercases.

    Args:
        txt: Text to normalize

    Returns:
        Lowercase normalized text
    """
    return normalize_text_for_match(txt).lower()


def normalize_nospace(txt: str) -> str:
    """Remove ALL whitespace from text for fallback matching.

    Used when exact match fails but text differs only in whitespace.

    Args:
        txt: Text to process

    Returns:
        Text with all whitespace removed
    """
    return re.sub(r'\s+', '', txt)
