"""
Preprocessing Module

ENG BASE / KR BASE preprocessing for LINE CHECK and TERM CHECK.
Handles StringID matching for ENG BASE mode.
"""

from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass

try:
    from core.xml_parser import LocStrEntry, parse_multiple_files, build_stringid_lookup
    from config import SOURCE_BASE_KR, SOURCE_BASE_ENG
except ImportError:
    from .xml_parser import LocStrEntry, parse_multiple_files, build_stringid_lookup
    from ..config import SOURCE_BASE_KR, SOURCE_BASE_ENG


@dataclass
class PreprocessedEntry:
    """
    Entry preprocessed for consistency checking.

    In KR BASE mode: source = str_origin (Korean)
    In ENG BASE mode: source = English text matched via StringID
    """
    source: str  # The source text to use for comparison
    translation: str  # The translation text
    string_id: str  # StringID for reference
    file_path: str  # Source file
    original_str_origin: str  # Original Korean StrOrigin (for reference)


def preprocess_for_consistency_check(
    target_files: List[str],
    eng_file: Optional[str] = None,
    source_base: str = SOURCE_BASE_KR,
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> List[PreprocessedEntry]:
    """
    Preprocess entries for LINE CHECK or TERM CHECK.

    In KR BASE mode:
        - source = StrOrigin (Korean text)
        - No English file needed

    In ENG BASE mode:
        - source = English text matched via StringID
        - Falls back to StrOrigin if no StringID match

    Args:
        target_files: List of target language XML/TXT files
        eng_file: Path to English XML file (required for ENG BASE)
        source_base: SOURCE_BASE_KR or SOURCE_BASE_ENG
        progress_callback: Optional callback(message, current, total)

    Returns:
        List of PreprocessedEntry objects
    """
    # Parse target files
    if progress_callback:
        progress_callback("Parsing target files...", 0, 1)

    target_entries = parse_multiple_files(target_files, progress_callback)

    if source_base == SOURCE_BASE_KR or eng_file is None:
        # KR BASE: Use StrOrigin directly as source
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

    # ENG BASE: Match StringIDs to get English source
    if progress_callback:
        progress_callback("Parsing English file for StringID matching...", 0, 1)

    eng_entries = parse_multiple_files([eng_file], progress_callback)
    eng_lookup = build_stringid_lookup(eng_entries)

    preprocessed = []
    matched = 0
    unmatched = 0

    for entry in target_entries:
        if not entry.str_origin or not entry.str:
            continue

        # Try to find English source via StringID
        if entry.string_id and entry.string_id in eng_lookup:
            eng_source, _ = eng_lookup[entry.string_id]
            source = eng_source if eng_source else entry.str_origin
            matched += 1
        else:
            # Fallback to Korean StrOrigin
            source = entry.str_origin
            unmatched += 1

        preprocessed.append(PreprocessedEntry(
            source=source,
            translation=entry.str,
            string_id=entry.string_id,
            file_path=entry.file_path,
            original_str_origin=entry.str_origin
        ))

    if progress_callback:
        total = matched + unmatched
        progress_callback(
            f"StringID matching: {matched}/{total} matched ({100*matched/total:.1f}%)",
            total, total
        )

    return preprocessed


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

        # Add file path (basename only)
        import os
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
