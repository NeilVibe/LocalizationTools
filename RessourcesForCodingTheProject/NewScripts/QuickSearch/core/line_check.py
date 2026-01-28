"""
LINE CHECK Module

Checks translation consistency - finds sources with multiple different translations.
Supports both KR BASE and ENG BASE modes.
"""

import os
import re
import string
from typing import List, Dict, Optional, Callable, Tuple
from collections import defaultdict
from dataclasses import dataclass

try:
    from core.xml_parser import parse_multiple_files, parse_folder
    from core.preprocessing import (
        PreprocessedEntry,
        preprocess_for_consistency_check,
        group_by_source,
        find_inconsistent_sources
    )
    from utils.language_utils import is_korean
    from utils.filters import glossary_filter
    from config import SOURCE_BASE_KR, SOURCE_BASE_ENG
except ImportError:
    from .xml_parser import parse_multiple_files, parse_folder
    from .preprocessing import (
        PreprocessedEntry,
        preprocess_for_consistency_check,
        group_by_source,
        find_inconsistent_sources
    )
    from ..utils.language_utils import is_korean
    from ..utils.filters import glossary_filter
    from ..config import SOURCE_BASE_KR, SOURCE_BASE_ENG


@dataclass
class LineCheckResult:
    """Result of a LINE CHECK operation."""
    source: str
    translations: List[str]  # Multiple translations found


def run_line_check(
    target_files: List[str],
    eng_file: Optional[str] = None,
    source_base: str = SOURCE_BASE_KR,
    filter_sentences: bool = True,
    length_threshold: int = 15,
    min_occurrence: Optional[int] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[LineCheckResult]:
    """
    Run LINE CHECK to find translation inconsistencies.

    A source is "inconsistent" if it has multiple different translations.

    Args:
        target_files: List of target XML/TXT files to check
        eng_file: English XML file (required for ENG BASE mode)
        source_base: SOURCE_BASE_KR or SOURCE_BASE_ENG
        filter_sentences: Whether to skip sentence entries
        length_threshold: Maximum source length to include
        min_occurrence: Minimum occurrences required
        progress_callback: Optional callback for progress updates

    Returns:
        List of LineCheckResult objects (inconsistent sources)
    """
    if progress_callback:
        progress_callback("Starting LINE CHECK...")

    # Preprocess entries based on source base mode
    def progress_wrapper(msg: str, current: int, total: int):
        if progress_callback:
            progress_callback(f"{msg} ({current}/{total})")

    entries = preprocess_for_consistency_check(
        target_files,
        eng_file=eng_file,
        source_base=source_base,
        progress_callback=progress_wrapper
    )

    if progress_callback:
        progress_callback(f"Parsed {len(entries)} entries")

    # Filter entries
    filtered_entries = []
    for entry in entries:
        # Skip if translation contains Korean
        if is_korean(entry.translation):
            continue

        # Skip sentences if filter enabled
        if filter_sentences and re.search(r'[.?!]\s*$', entry.source.strip()):
            continue

        # Skip if source contains punctuation
        if any(ch in string.punctuation for ch in entry.source) or '…' in entry.source:
            continue

        # Skip if source too long
        if len(entry.source) >= length_threshold:
            continue

        filtered_entries.append(entry)

    if progress_callback:
        progress_callback(f"Filtered to {len(filtered_entries)} entries")

    # Group by source
    src_trans_mapping: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for entry in filtered_entries:
        src_trans_mapping[entry.source][entry.translation] += 1

    # Find inconsistent sources (>1 different translation)
    inconsistent = {
        src: trans_dict
        for src, trans_dict in src_trans_mapping.items()
        if len(trans_dict) > 1
    }

    if progress_callback:
        progress_callback(f"Found {len(inconsistent)} inconsistent sources")

    # Build results
    results = []
    for source in sorted(inconsistent.keys(), key=len):
        translations = list(inconsistent[source].keys())
        results.append(LineCheckResult(
            source=source,
            translations=translations
        ))

    return results


def format_line_check_results(
    results: List[LineCheckResult],
    include_filenames: bool = False
) -> str:
    """
    Format LINE CHECK results for output.

    Args:
        results: List of LineCheckResult objects
        include_filenames: Whether to include file names (default: False for clean output)

    Returns:
        Formatted string output
    """
    lines = []

    for result in results:
        lines.append(result.source)
        for translation in result.translations:
            lines.append(f"  {translation}")
        lines.append("")  # Blank line between entries

    return "\n".join(lines)


def save_line_check_results(
    results: List[LineCheckResult],
    output_path: str,
    include_filenames: bool = False
) -> bool:
    """
    Save LINE CHECK results to a file.

    Args:
        results: List of LineCheckResult objects
        output_path: Path to output file
        include_filenames: Whether to include file names

    Returns:
        True if successful
    """
    try:
        formatted = format_line_check_results(results, include_filenames)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted)
        return True
    except Exception:
        return False


def run_line_check_from_pairs(
    pairs: List[Tuple[str, str]],
    filter_sentences: bool = True,
    length_threshold: int = 15,
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[LineCheckResult]:
    """
    Run LINE CHECK from pre-extracted (source, translation) pairs.

    Simpler interface when pairs are already available.

    Args:
        pairs: List of (source, translation) tuples
        filter_sentences: Whether to skip sentence entries
        length_threshold: Maximum source length to include
        progress_callback: Optional callback for progress updates

    Returns:
        List of LineCheckResult objects
    """
    if progress_callback:
        progress_callback("Filtering pairs...")

    # Apply filters
    filtered = glossary_filter(
        pairs,
        length_threshold=length_threshold,
        filter_sentences=filter_sentences
    )

    # Remove entries where translation has Korean
    filtered = [(src, trans) for src, trans in filtered if not is_korean(trans)]

    if progress_callback:
        progress_callback(f"Filtered to {len(filtered)} pairs")

    # Group by source
    src_trans_mapping: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for src, trans in filtered:
        src_trans_mapping[src][trans] += 1

    # Find inconsistent sources
    inconsistent = {
        src: trans_dict
        for src, trans_dict in src_trans_mapping.items()
        if len(trans_dict) > 1
    }

    if progress_callback:
        progress_callback(f"Found {len(inconsistent)} inconsistent sources")

    # Build results
    results = []
    for source in sorted(inconsistent.keys(), key=len):
        translations = list(inconsistent[source].keys())
        results.append(LineCheckResult(
            source=source,
            translations=translations
        ))

    return results
