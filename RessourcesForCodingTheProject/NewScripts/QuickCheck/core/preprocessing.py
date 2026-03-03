"""
Preprocessing Module

KR BASE preprocessing for LINE CHECK and TERM CHECK.
QuickCheck uses KR BASE only (Korean StrOrigin as source).
"""
from __future__ import annotations

from typing import List, Optional, Callable
from dataclasses import dataclass

from core.xml_parser import LocStrEntry, parse_multiple_files


@dataclass
class PreprocessedEntry:
    """
    Entry preprocessed for consistency checking.

    source = StrOrigin (Korean text, KR BASE mode)
    """
    source: str       # The source text for comparison (StrOrigin)
    translation: str  # The translation text
    string_id: str    # StringID for reference
    file_path: str    # Source file
    original_str_origin: str  # Original Korean StrOrigin


def preprocess_for_consistency_check(
    target_files: List[str],
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> List[PreprocessedEntry]:
    """
    Preprocess entries for LINE CHECK or TERM CHECK (KR BASE mode).

    source = StrOrigin (Korean text)

    Args:
        target_files: List of target language XML files
        progress_callback: Optional callback(message, current, total)

    Returns:
        List of PreprocessedEntry objects
    """
    if progress_callback:
        progress_callback("Parsing target files...", 0, 1)

    target_entries = parse_multiple_files(target_files, progress_callback)

    return [
        PreprocessedEntry(
            source=entry.str_origin,
            translation=entry.str,
            string_id=entry.string_id,
            file_path=entry.file_path,
            original_str_origin=entry.str_origin
        )
        for entry in target_entries
        if entry.str_origin and entry.str
    ]


