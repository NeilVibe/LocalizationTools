"""
Text Utilities - Shared text normalization functions.

Single source of truth for text normalization across all modules.
"""

import html
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Formula / garbage text detection — shared across Excel and XML readers
# ---------------------------------------------------------------------------

_FORMULA_RE = re.compile(r'^[=+\-@][A-Za-z_]')
_ARRAY_FORMULA_RE = re.compile(r'^\{=.*\}$')

_EXCEL_ERRORS = frozenset({
    '#N/A', '#REF!', '#VALUE!', '#NAME?', '#NULL!',
    '#DIV/0!', '#NUM!', '#GETTING_DATA',
    '#SPILL!', '#CALC!', '#BLOCKED!', '#CONNECT!',
    '#FIELD!', '#UNKNOWN!',
})

# Match Excel errors anywhere in the string (not just exact match)
_EXCEL_ERROR_RE = re.compile(
    r'#(?:N/A|REF!|VALUE!|NAME\?|NULL!|DIV/0!|NUM!|GETTING_DATA'
    r'|SPILL!|CALC!|BLOCKED!|CONNECT!|FIELD!|UNKNOWN!)',
    re.IGNORECASE,
)


def is_formula_text(text: str) -> Optional[str]:
    """Check if a string looks like an Excel formula or error value.

    Works on any string regardless of source (Excel cell, XML attribute, etc.).
    Catches:
      - Formulas: =VLOOKUP, +SUM, -AVERAGE, @SUM, {=ARRAY}, _xlfn. prefixed
      - Excel errors: #N/A, #REF!, #VALUE!, #SPILL!, etc. (exact or embedded)
      - openpyxl object repr leaks

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
    if stripped.upper() in _EXCEL_ERRORS:
        return f'Excel error value ({stripped})'
    if _EXCEL_ERROR_RE.search(stripped):
        return f'Contains Excel error ({_EXCEL_ERROR_RE.search(stripped).group()})'
    if 'openpyxl.' in stripped:
        return f'openpyxl object repr ({stripped[:40]})'
    if '_xlfn.' in stripped.lower():
        return f'Excel internal function ({stripped[:40]})'
    return None


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
