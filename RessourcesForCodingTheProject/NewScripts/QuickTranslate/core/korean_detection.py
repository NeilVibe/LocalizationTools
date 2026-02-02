"""
Korean Text Detection.

Detect Korean Hangul characters in text to identify untranslated strings.
"""

import re

# Korean Hangul syllables range (AC00-D7A3)
KOREAN_REGEX = re.compile(r'[\uac00-\ud7a3]')


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
