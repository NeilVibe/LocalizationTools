"""
Preprocessing Module

KR BASE preprocessing for LINE CHECK and TERM CHECK.
QuickCheck uses KR BASE only (Korean StrOrigin as source).
"""
from __future__ import annotations

import os
from typing import List, Dict, Optional, Tuple, Callable
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


def group_by_source(entries: List[PreprocessedEntry]) -> Dict[str, Dict[str, List[str]]]:
    """
    Group entries by source text for consistency checking.

    Returns a dictionary mapping:
        source -> {translation -> [file_paths]}

    Args:
        entries: List of PreprocessedEntry objects

    Returns:
        Nested dictionary for inconsistency detection
    """
    grouped: Dict[str, Dict[str, List[str]]] = {}

    for entry in entries:
        if entry.source not in grouped:
            grouped[entry.source] = {}

        if entry.translation not in grouped[entry.source]:
            grouped[entry.source][entry.translation] = []

        file_name = os.path.basename(entry.file_path)
        if file_name not in grouped[entry.source][entry.translation]:
            grouped[entry.source][entry.translation].append(file_name)

    return grouped


def find_inconsistent_sources(
    grouped: Dict[str, Dict[str, List[str]]]
) -> Dict[str, Dict[str, List[str]]]:
    """
    Find sources that have multiple different translations.

    Args:
        grouped: Output from group_by_source()

    Returns:
        Dictionary containing only inconsistent sources
    """
    return {
        source: translations
        for source, translations in grouped.items()
        if len(translations) > 1
    }


def build_term_glossary(
    entries: List[PreprocessedEntry],
    dedupe: bool = True
) -> List[Tuple[str, str]]:
    """
    Build a glossary of (source, translation) pairs from entries.

    Args:
        entries: List of PreprocessedEntry objects
        dedupe: Whether to deduplicate by source

    Returns:
        List of (source, translation) tuples
    """
    pairs = [(entry.source, entry.translation) for entry in entries]

    if dedupe:
        seen = set()
        deduped = []
        for src, trans in pairs:
            if src not in seen:
                deduped.append((src, trans))
                seen.add(src)
        return deduped

    return pairs
