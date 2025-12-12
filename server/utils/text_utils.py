"""
Centralized Text Utilities

Factor Power: Single source for all text normalization.
"""

import re
from typing import Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def normalize_text(text: str) -> str:
    """
    Normalize text for storage and comparison.

    - Remove unmatched quotes
    - Normalize Unicode whitespace
    - Normalize apostrophes
    - Strip whitespace

    Used by: LDM, QuickSearch
    """
    if not isinstance(text, str):
        return ""

    # Handle unmatched quotation marks
    balanced_indices = set()
    quote_indices = [i for i, char in enumerate(text) if char == '"']

    for i in range(0, len(quote_indices) - 1, 2):
        balanced_indices.add(quote_indices[i])
        balanced_indices.add(quote_indices[i + 1])

    result = []
    for i, char in enumerate(text):
        if char == '"' and i not in balanced_indices:
            continue
        result.append(char)

    text = ''.join(result)

    # Normalize Unicode whitespace
    text = re.sub(r'[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000\uFEFF]+', ' ', text)
    text = re.sub(r'[\u200B-\u200F\u202A-\u202E]+', '', text)

    # Normalize apostrophes
    text = re.sub(r'[\u2019\u2018\u02BC\u2032\u0060\u00B4]', "'", text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def normalize_korean_text(text: str) -> str:
    """
    Normalize Korean text by removing code markers and formatting.

    Removes:
    - Code markers like {ChangeScene()}, {AudioVoice()}
    - Triangle markers
    - Scale/Color tags
    - Extra whitespace

    Used by: KRSimilar
    """
    # Handle pandas NaN
    if PANDAS_AVAILABLE and pd.isna(text):
        return ''
    if not isinstance(text, str):
        return ''

    # Replace \n not followed by { with space
    text = re.sub(r'\\n(?![\{▶])', ' ', text)

    # Remove triangles
    text = re.sub(r'▶', '', text)

    # Remove various tags
    text = re.sub(r'<Scale[^>]*>|</Scale>', '', text)
    text = re.sub(r'<color[^>]*>|</color>', '', text)
    text = re.sub(r'<PAColor[^>]*>|<PAOldColor>', '', text)
    text = re.sub(r'\{[^}]*\}', '', text)  # Remove content in curly braces
    text = re.sub(r'<Style:[^>]*>', '', text)  # Handle Style tags

    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def normalize_for_hash(text: str) -> str:
    """
    Normalize text for hash comparison.

    More aggressive normalization for duplicate detection.
    """
    if not isinstance(text, str):
        return ""

    # Apply standard normalization first
    text = normalize_text(text)

    # Additional: lowercase for case-insensitive comparison
    text = text.lower()

    return text
