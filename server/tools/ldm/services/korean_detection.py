"""
Korean Text Detection.

Detect Korean Hangul characters in text. Used for CJK language detection
in postprocess pipeline (ellipsis skip) and untranslated string detection.

Ported from QuickTranslate core/korean_detection.py.
"""

from __future__ import annotations

import re

# Korean: syllables (AC00-D7AF) + Jamo (1100-11FF) + Compat Jamo (3130-318F)
# NEVER use syllables-only -- Jamo and Compat Jamo are valid Korean characters
KOREAN_REGEX = re.compile(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]')


def is_korean_text(text: str | None) -> bool:
    """Check if text contains Korean characters.

    Covers all three Unicode ranges:
    - Hangul Syllables (U+AC00-U+D7AF)
    - Hangul Jamo (U+1100-U+11FF)
    - Hangul Compatibility Jamo (U+3130-U+318F)

    Args:
        text: Text to check

    Returns:
        True if text contains Korean Hangul characters
    """
    if not text:
        return False
    return bool(KOREAN_REGEX.search(text))
