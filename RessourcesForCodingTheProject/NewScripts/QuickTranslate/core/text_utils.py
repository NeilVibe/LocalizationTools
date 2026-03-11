"""
Text Utilities - Shared text normalization functions.

Single source of truth for text normalization across all modules.
"""

import html
import re
import unicodedata
from typing import Optional

# ---------------------------------------------------------------------------
# Formula / garbage text detection — shared across Excel and XML readers
# ---------------------------------------------------------------------------

# Formula prefix: = + @ are always formula indicators.
# Hyphen excluded — "-word" is common in game text (e.g. "-select", "-Default").
_FORMULA_RE = re.compile(r'^[=+@][A-Za-z_]')
_ARRAY_FORMULA_RE = re.compile(r'^\{=.*\}$')

# Match Excel errors anywhere in the string (exact or embedded)
_EXCEL_ERROR_RE = re.compile(
    r'#(?:N/A|REF!|VALUE!|NAME\?|NULL!|DIV/0!|NUM!|GETTING_DATA'
    r'|SPILL!|CALC!|BLOCKED!|CONNECT!|FIELD!|UNKNOWN!)',
    re.IGNORECASE,
)


def is_formula_text(text: str) -> Optional[str]:
    """Check if a string looks like an Excel formula or error value.

    Works on any string regardless of source (Excel cell, XML attribute, etc.).
    Catches:
      - Formulas: =VLOOKUP, +SUM, @SUM, {=ARRAY}, _xlfn. prefixed
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
    m = _EXCEL_ERROR_RE.search(stripped)
    if m:
        return f'Excel error value ({m.group()})'
    if 'openpyxl.' in stripped:
        return f'openpyxl object repr ({stripped[:40]})'
    if '_xlfn.' in stripped.lower():
        return f'Excel internal function ({stripped[:40]})'
    return None


# ---------------------------------------------------------------------------
# Text integrity detection — broken linebreaks, encoding artifacts, bad chars
# ---------------------------------------------------------------------------

# Broken <br/> variants that are NOT caught by postprocess or _has_wrong_newlines:
# 1. <br/ followed by non-> (missing >, text glued to tag)
# 2. <br at end of string or followed by non-/ non-> non-space (truncated)
# 3. < br/> (space between < and tag name)
# 4. orphaned br/> without < (missing opening)
_BROKEN_BR_RE = re.compile(
    r'<br/(?!>)'             # <br/ NOT followed by > (covers <br/エルナンド)
    r'|<br(?![/>\s])'        # <br NOT followed by / > or space (covers <brText)
    r'|<\s+br'               # < br (space after <)
    r'|(?<![<])br/>'         # br/> without preceding < (orphaned closing)
    , re.IGNORECASE
)

# Control chars that should never appear in game text
# Excludes tab \x09, LF \x0a, CR \x0d (handled by _has_wrong_newlines)
_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

# ---------------------------------------------------------------------------
# Invisible character buckets — auto-cleanup vs blocking vs warning
# ---------------------------------------------------------------------------

# Bucket 1 — Zs spaces: auto-replace with regular space (U+0020)
# Detected dynamically via unicodedata.category == 'Zs' (excluding U+0020)
# Common examples: NBSP (U+00A0), en-space (U+2002), em-space (U+2003)

# Bucket 2 — Safe invisible: auto-delete (silently remove)
_SAFE_INVISIBLE_DELETE = frozenset({
    '\u200b',   # Zero-width space
    '\ufeff',   # BOM / zero-width no-break space
    '\u200e',   # Left-to-right mark
    '\u200f',   # Right-to-left mark
    '\u2060',   # Word joiner
    '\u00ad',   # Soft hyphen
    '\u2061',   # Function application
    '\u2062',   # Invisible times
    '\u2063',   # Invisible separator
    '\u2064',   # Invisible plus
    '\u034f',   # Combining grapheme joiner
    '\u061c',   # Arabic letter mark
    '\u180e',   # Mongolian vowel separator
    '\u2066',   # Left-to-right isolate
    '\u2067',   # Right-to-left isolate
    '\u2068',   # First strong isolate
    '\u2069',   # Pop directional isolate
    '\u202a',   # Left-to-right embedding
    '\u202b',   # Right-to-left embedding
    '\u202c',   # Pop directional formatting
    '\u202d',   # Left-to-right override
    '\u202e',   # Right-to-left override
})

# Human-readable names for detail reporting
_SAFE_INVISIBLE_NAMES = {
    '\u200b': 'Zero-width space',
    '\ufeff': 'BOM',
    '\u200e': 'LTR mark',
    '\u200f': 'RTL mark',
    '\u2060': 'Word joiner',
    '\u00ad': 'Soft hyphen',
    '\u2061': 'Function application',
    '\u2062': 'Invisible times',
    '\u2063': 'Invisible separator',
    '\u2064': 'Invisible plus',
    '\u034f': 'Combining grapheme joiner',
    '\u061c': 'Arabic letter mark',
    '\u180e': 'Mongolian vowel separator',
    '\u2066': 'LTR isolate',
    '\u2067': 'RTL isolate',
    '\u2068': 'First strong isolate',
    '\u2069': 'Pop directional isolate',
    '\u202a': 'LTR embedding',
    '\u202b': 'RTL embedding',
    '\u202c': 'Pop directional formatting',
    '\u202d': 'LTR override',
    '\u202e': 'RTL override',
}

# Bucket 3 — Grey zone: warn only (don't touch, don't block)
_GREY_ZONE_CHARS = {
    '\u200c': 'Zero-width non-joiner (ZWNJ)',
    '\u200d': 'Zero-width joiner (ZWJ)',
}


def is_broken_linebreak(text: str) -> Optional[str]:
    """Check if text contains a broken/malformed <br/> tag.

    Only catches variants that are NOT auto-fixed by postprocess and NOT
    detected by _has_wrong_newlines. These are game-breaking corruptions
    where the tag structure itself is damaged.

    Returns:
        Reason string if broken linebreak found, None if clean.
    """
    if not text:
        return None
    m = _BROKEN_BR_RE.search(text)
    if m:
        # Show context around the match
        start = max(0, m.start() - 5)
        end = min(len(text), m.end() + 10)
        context = text[start:end]
        return f'Broken <br/> tag: ...{context}...'
    # Also catch <br at very end of string (truncated)
    stripped = text.rstrip()
    if stripped.endswith('<br') or stripped.endswith('<br/'):
        return f'Truncated <br/> at end of string'
    return None


def is_text_integrity_issue(text: str) -> Optional[str]:
    """Check if text has integrity issues (encoding artifacts, bad chars).

    Only catches truly corrupted text that should BLOCK transfer:
      - Broken <br/> tags (game-breaking)
      - Replacement character U+FFFD (encoding corruption)
      - Control characters (C0 range)

    Invisible characters (NBSP, zero-width space, BOM, bidi marks, etc.)
    are NOT blocked here — they are auto-cleaned by postprocess Step 5.
    Grey zone chars (ZWNJ, ZWJ) produce warnings but don't block.

    Returns:
        Reason string if issue found, None if clean.
    """
    if not text:
        return None

    # 1. Broken linebreaks (most critical — game-breaking)
    br_issue = is_broken_linebreak(text)
    if br_issue:
        return br_issue

    # 2. Replacement character U+FFFD (encoding broke somewhere)
    if '\ufffd' in text:
        return 'Encoding artifact: replacement character (U+FFFD)'

    # 3. Control characters
    m = _CONTROL_CHARS_RE.search(text)
    if m:
        return f'Control character U+{ord(m.group()):04X}'

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
