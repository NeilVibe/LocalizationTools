"""
Filter Functions

Filters for glossary extraction and consistency checks.
"""

import re
import string
from typing import List, Tuple, Optional, Dict
from collections import Counter

from .language_utils import is_korean, is_sentence


def sentence_filter(pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Filter out pairs where the source ends with sentence punctuation.

    Args:
        pairs: List of (source, translation) tuples

    Returns:
        Filtered list without sentence entries
    """
    return [(src, trans) for src, trans in pairs if not is_sentence(src)]


def punctuation_filter(pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Filter out pairs where the source contains punctuation or ellipsis.

    Args:
        pairs: List of (source, translation) tuples

    Returns:
        Filtered list without punctuation entries
    """
    filtered = []
    for src, trans in pairs:
        # Skip if any standard punctuation
        if any(ch in string.punctuation for ch in src):
            continue
        # Skip if contains special ellipsis character
        if '…' in src:
            continue
        filtered.append((src, trans))
    return filtered


def length_filter(pairs: List[Tuple[str, str]], max_length: int) -> List[Tuple[str, str]]:
    """
    Filter out pairs where the source exceeds max_length.

    Args:
        pairs: List of (source, translation) tuples
        max_length: Maximum allowed source length

    Returns:
        Filtered list
    """
    return [(src, trans) for src, trans in pairs if len(src) < max_length]


def korean_translation_filter(pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Filter out pairs where the translation contains Korean.

    This is used to ensure translations are actually in the target language.

    Args:
        pairs: List of (source, translation) tuples

    Returns:
        Filtered list without Korean translations
    """
    return [(src, trans) for src, trans in pairs if not is_korean(trans)]


def occurrence_filter(pairs: List[Tuple[str, str]], min_occurrence: int) -> List[Tuple[str, str]]:
    """
    Filter out pairs that occur less than min_occurrence times.

    Args:
        pairs: List of (source, translation) tuples
        min_occurrence: Minimum number of occurrences required

    Returns:
        Filtered list
    """
    if min_occurrence <= 1:
        return pairs

    # Count occurrences of each source
    source_counts = Counter(src for src, _ in pairs)

    return [(src, trans) for src, trans in pairs if source_counts[src] >= min_occurrence]


def glossary_filter(
    pairs: List[Tuple[str, str]],
    length_threshold: int = 15,
    filter_sentences: bool = True,
    min_occurrence: Optional[int] = None
) -> List[Tuple[str, str]]:
    """
    Apply all glossary filters in sequence.

    Filter criteria:
    - Source length < threshold
    - Both source and translation non-empty
    - Translation has no Korean
    - Optionally, source is not a sentence
    - Source contains no punctuation (including ellipsis)
    - Optionally, keep only entries that occur >= min_occurrence times

    Args:
        pairs: List of (source, translation) tuples
        length_threshold: Maximum source length
        filter_sentences: Whether to filter out sentence entries
        min_occurrence: Minimum occurrences required (None to skip)

    Returns:
        Filtered list of (source, translation) tuples
    """
    # Start with all pairs
    filtered = pairs

    # Filter out empty entries
    filtered = [(src, trans) for src, trans in filtered if src and trans]

    # Apply length filter
    filtered = length_filter(filtered, length_threshold)

    # Filter out Korean translations
    filtered = korean_translation_filter(filtered)

    # Optionally filter sentences
    if filter_sentences:
        filtered = sentence_filter(filtered)

    # Filter out punctuation
    filtered = punctuation_filter(filtered)

    # Build count map before occurrence filter
    count_map: Dict[str, int] = {}
    for src, _ in filtered:
        count_map[src] = count_map.get(src, 0) + 1

    # Apply occurrence filter if specified
    if min_occurrence is not None and min_occurrence > 1:
        filtered = [(src, trans) for src, trans in filtered if count_map.get(src, 0) >= min_occurrence]

    return filtered


def dedupe_glossary(pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Deduplicate glossary by keeping first occurrence of each source.

    Args:
        pairs: List of (source, translation) tuples

    Returns:
        Deduplicated list preserving first occurrence
    """
    seen = set()
    result = []
    for src, trans in pairs:
        if src not in seen:
            result.append((src, trans))
            seen.add(src)
    return result


def count_glossary_occurrences(pairs: List[Tuple[str, str]]) -> List[Tuple[str, str, int]]:
    """
    Count occurrences and return pairs with counts.

    Args:
        pairs: List of (source, translation) tuples

    Returns:
        List of (source, translation, count) tuples, deduplicated
    """
    # Count all occurrences
    source_counts = Counter(src for src, _ in pairs)

    # Get first translation for each source
    first_translation: Dict[str, str] = {}
    for src, trans in pairs:
        if src not in first_translation:
            first_translation[src] = trans

    return [
        (src, first_translation[src], source_counts[src])
        for src in first_translation
    ]
