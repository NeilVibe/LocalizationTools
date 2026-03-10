"""
Unicode Character Classification Utilities

Script detection, ratio computation, and text cleanup for language detection.
"""
from __future__ import annotations

import re
from typing import Dict


# ---------------------------------------------------------------------------
# Character classifiers
# ---------------------------------------------------------------------------

def _is_latin(ch: str) -> bool:
    cp = ord(ch)
    return (0x0041 <= cp <= 0x005A or 0x0061 <= cp <= 0x007A  # Basic Latin
            or 0x00C0 <= cp <= 0x024F  # Latin Extended-A/B
            or 0x1E00 <= cp <= 0x1EFF)  # Latin Extended Additional


def _is_cyrillic(ch: str) -> bool:
    cp = ord(ch)
    return 0x0400 <= cp <= 0x04FF or 0x0500 <= cp <= 0x052F


def _is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF       # CJK Unified Ideographs
            or 0x3400 <= cp <= 0x4DBF    # CJK Extension A
            or 0x20000 <= cp <= 0x2A6DF  # CJK Extension B
            or 0xF900 <= cp <= 0xFAFF)   # CJK Compatibility Ideographs


def _is_hangul(ch: str) -> bool:
    cp = ord(ch)
    return (0xAC00 <= cp <= 0xD7AF       # Hangul Syllables
            or 0x1100 <= cp <= 0x11FF    # Hangul Jamo
            or 0x3130 <= cp <= 0x318F)   # Hangul Compatibility Jamo


def _is_hiragana(ch: str) -> bool:
    cp = ord(ch)
    return 0x3040 <= cp <= 0x309F


def _is_katakana(ch: str) -> bool:
    cp = ord(ch)
    return 0x30A0 <= cp <= 0x30FF or 0x31F0 <= cp <= 0x31FF


# ---------------------------------------------------------------------------
# Script ratio computation
# ---------------------------------------------------------------------------

_CLASSIFIERS = [
    ("Latin", _is_latin),
    ("Cyrillic", _is_cyrillic),
    ("CJK", _is_cjk),
    ("Hangul", _is_hangul),
    ("Hiragana", _is_hiragana),
    ("Katakana", _is_katakana),
]


def compute_script_ratios(text: str) -> Dict[str, float]:
    """Compute the ratio of each Unicode script in the text (ignoring non-letter chars)."""
    counts: Dict[str, int] = {}
    total = 0
    for ch in text:
        for name, fn in _CLASSIFIERS:
            if fn(ch):
                counts[name] = counts.get(name, 0) + 1
                total += 1
                break
    if total == 0:
        return {}
    return {name: count / total for name, count in counts.items()}


# ---------------------------------------------------------------------------
# Text cleanup for language detection
# ---------------------------------------------------------------------------

_RE_CODE_PATTERN = re.compile(r'\{[^}]*\}')
_RE_HTML_TAG = re.compile(r'<[^>]+>')
_RE_NUMBERS_ONLY = re.compile(r'^[\d\s\W]+$')


def strip_codes_and_markup(text: str) -> str:
    """Remove {code} patterns and all HTML/XML tags from text."""
    text = _RE_CODE_PATTERN.sub('', text)
    text = _RE_HTML_TAG.sub(' ', text)
    return text.strip()


def is_numbers_only(text: str) -> bool:
    """Check if text contains only digits, whitespace, and punctuation (no letters)."""
    return bool(_RE_NUMBERS_ONLY.match(text))
