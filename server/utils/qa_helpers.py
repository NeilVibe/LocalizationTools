"""
QA Helper Functions - Centralized Quality Assurance Utilities

Factor Power: Single source for all QA check helpers.
Used by: LDM Auto-LQA, QuickSearch QA tools

Migrated from: server/tools/quicksearch/qa_tools.py
"""

import re
import string
from typing import Set, Optional


def is_korean(text: str) -> bool:
    """
    Check if text contains any Korean syllable (Hangul).

    Korean syllables are in Unicode range U+AC00-U+D7A3.

    Args:
        text: Text to check

    Returns:
        True if text contains Korean characters

    Example:
        >>> is_korean("안녕하세요")
        True
        >>> is_korean("Hello")
        False
    """
    if not isinstance(text, str):
        return False
    return bool(re.search(r'[\uac00-\ud7a3]', text))


def is_sentence(text: str) -> bool:
    """
    Check if text ends with sentence-ending punctuation.

    Sentence endings: . ? !

    Args:
        text: Text to check

    Returns:
        True if text ends with sentence punctuation

    Example:
        >>> is_sentence("Hello world.")
        True
        >>> is_sentence("Hello world")
        False
    """
    if not isinstance(text, str):
        return False
    return bool(re.search(r'[.?!]\s*$', text.strip()))


def has_punctuation(text: str) -> bool:
    """
    Check if text contains any punctuation or special ellipsis.

    Args:
        text: Text to check

    Returns:
        True if text contains punctuation

    Example:
        >>> has_punctuation("Hello, world!")
        True
        >>> has_punctuation("Hello world")
        False
    """
    if not isinstance(text, str):
        return False
    return any(ch in string.punctuation for ch in text) or '…' in text


def extract_code_patterns(text: str) -> Set[str]:
    """
    Extract {code} patterns from text using non-greedy matching.

    Finds all patterns like {variable}, {ItemID:123}, etc.

    Args:
        text: Text containing code patterns

    Returns:
        Set of unique code patterns found

    Example:
        >>> extract_code_patterns("Hello {name}, you have {count} items")
        {'{name}', '{count}'}
        >>> extract_code_patterns("No codes here")
        set()
    """
    if not isinstance(text, str):
        return set()
    return set(re.findall(r'\{.*?\}', text))


def preprocess_text_for_char_count(text: str) -> str:
    """
    Remove formatting codes that interfere with character counting.

    Removes:
    - <color:...> tags
    - <PAColor...> and <PAOldColor> tags

    Args:
        text: Text with formatting codes

    Returns:
        Text with formatting codes removed

    Example:
        >>> preprocess_text_for_char_count("<color:#FF0000>Red text</color>")
        'Red text'
    """
    if not isinstance(text, str):
        return ""
    text = re.sub(r'<color:.*?>', '', text)
    text = re.sub(r'<PAColor.*?>|<PAOldColor>', '', text)
    return text


def is_isolated(text: str, start: int, end: int) -> bool:
    """
    Check if match is isolated (not part of larger word).

    Used for term matching to avoid partial matches.

    Args:
        text: Full text
        start: Start index of match
        end: End index of match

    Returns:
        True if match is isolated (word boundary on both sides)
    """
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    # Not isolated if adjacent to word char or Korean
    return (not re.match(r'[\w가-힣]', before)) and (not re.match(r'[\w가-힣]', after))


def check_pattern_match(source: str, target: str) -> Optional[dict]:
    """
    Check if {code} patterns match between source and target.

    Used for Pattern QA check - ensures code patterns are preserved
    in translation.

    Args:
        source: Source text (e.g., Korean)
        target: Target text (e.g., translated)

    Returns:
        Dict with mismatch info if patterns don't match, None if they match

    Example:
        >>> check_pattern_match("{0} items", "items")  # Missing {0}
        {'source_patterns': ['{0}'], 'target_patterns': []}
        >>> check_pattern_match("{0} items", "{0} things")  # Match
        None
    """
    patterns_source = extract_code_patterns(source)
    patterns_target = extract_code_patterns(target)

    if patterns_source != patterns_target:
        return {
            "source_patterns": sorted(patterns_source),
            "target_patterns": sorted(patterns_target)
        }
    return None


def check_character_count(source: str, target: str, symbols: list = None) -> Optional[dict]:
    """
    Check if special character counts match between source and target.

    Used for Character QA check - ensures formatting characters
    are preserved in translation.

    Args:
        source: Source text
        target: Target text
        symbols: List of symbols to check (default: ["{", "}"])

    Returns:
        Dict with mismatch info if counts don't match, None if they match

    Example:
        >>> check_character_count("{a}{b}", "{a}")  # Missing }
        {'symbol': '}', 'source_count': 2, 'target_count': 1}
    """
    if symbols is None:
        symbols = ["{", "}"]

    source_clean = preprocess_text_for_char_count(source)
    target_clean = preprocess_text_for_char_count(target)

    for sym in symbols:
        source_count = source_clean.count(sym)
        target_count = target_clean.count(sym)
        if source_count != target_count:
            return {
                "symbol": sym,
                "source_count": source_count,
                "target_count": target_count
            }
    return None
