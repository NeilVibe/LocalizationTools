# Origin: QuickTranslate/core/korean_detection.py
"""
Korean Text Detection.

Detect Korean Hangul characters in text to identify untranslated strings.
"""
from __future__ import annotations

import re

# Korean: syllables (AC00-D7AF) + Jamo (1100-11FF) + Compat Jamo (3130-318F)
KOREAN_REGEX = re.compile(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]')


def is_korean_text(text: str) -> bool:
    """
    Check if text contains Korean characters.

    Used to identify untranslated strings (Korean = source language).

    Args:
        text: Text to check

    Returns:
        True if text contains Korean Hangul characters
    """
    if not text:
        return False
    return bool(KOREAN_REGEX.search(text))
