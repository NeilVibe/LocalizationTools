"""
Matching Algorithms.

Transfer matching is handled inline by xml_transfer.py (_fast_folder_merge).
This module provides shared utilities used by other core modules.
"""
from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)


def format_multiple_matches(translations: List[str]) -> str:
    """
    Format multiple matches as numbered list.

    Args:
        translations: List of translation strings

    Returns:
        Single value if one match, numbered list if multiple
    """
    translations = [t for t in translations if t and t.strip()]
    if not translations:
        return ""
    if len(translations) == 1:
        return translations[0]
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(translations))
