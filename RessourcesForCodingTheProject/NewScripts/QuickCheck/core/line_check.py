"""
LINE CHECK Module

Checks translation consistency — finds sources with multiple different translations.
Uses KR BASE mode: Korean StrOrigin as the source for comparison.
"""
from __future__ import annotations

import string
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple
from collections import defaultdict
from dataclasses import dataclass

from core.preprocessing import preprocess_for_consistency_check
from utils.language_utils import is_korean, is_phrase
from utils.filters import glossary_filter
from utils.excel_writer import write_line_check_excel


@dataclass
class LineCheckResult:
    """Result of a LINE CHECK operation."""
    source: str
    translations: List[str]       # Multiple different translations found
    string_ids: List[str]         # First StringID seen for each translation (parallel to translations)


def run_line_check(
    target_files: List[str],
    filter_sentences: bool = True,
    length_threshold: int = 15,
    min_occurrence: Optional[int] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[LineCheckResult]:
    """
    Run LINE CHECK to find translation inconsistencies.

    A source is "inconsistent" if it has multiple different translations.

    Args:
        target_files: List of target XML files to check
        filter_sentences: Whether to skip sentence entries
        length_threshold: Maximum source length to include
        min_occurrence: Minimum occurrences required
        progress_callback: Optional callback for progress updates

    Returns:
        List of LineCheckResult objects (inconsistent sources only)
    """
    if progress_callback:
        progress_callback("Starting LINE CHECK...")

    def progress_wrapper(msg: str, current: int, total: int) -> None:
        if progress_callback:
            progress_callback(f"{msg} ({current}/{total})")

    entries = preprocess_for_consistency_check(target_files, progress_wrapper)

    if progress_callback:
        progress_callback(f"Parsed {len(entries)} entries")

    # Filter entries
    filtered_entries = []
    for entry in entries:
        # Skip if translation contains Korean
        if is_korean(entry.translation):
            continue

        # Skip sentences if filter enabled
        if filter_sentences and is_phrase(entry.source):
            continue

        # Skip if source contains punctuation
        if any(ch in string.punctuation for ch in entry.source) or '…' in entry.source:
            continue

        # Skip if source too long
        if len(entry.source) > length_threshold:
            continue

        filtered_entries.append(entry)

    if progress_callback:
        progress_callback(f"Filtered to {len(filtered_entries)} entries")

    # Group by source — track occurrence count, first StringID and first FileName per translation
    src_trans_count: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    src_trans_sid:  Dict[str, Dict[str, str]] = defaultdict(dict)

    for entry in filtered_entries:
        src_trans_count[entry.source][entry.translation] += 1
        if entry.translation not in src_trans_sid[entry.source]:
            src_trans_sid[entry.source][entry.translation] = entry.string_id

    # Apply min_occurrence filter if requested
    if min_occurrence is not None and min_occurrence > 1:
        src_trans_count = {
            src: trans_dict
            for src, trans_dict in src_trans_count.items()
            if sum(trans_dict.values()) >= min_occurrence
        }

    # Find inconsistent sources (>1 different translation)
    inconsistent = {
        src: trans_dict
        for src, trans_dict in src_trans_count.items()
        if len(trans_dict) > 1
    }

    if progress_callback:
        progress_callback(f"Found {len(inconsistent)} inconsistent sources")

    # Build results, sorted by source length (shortest first)
    results = []
    for source in sorted(inconsistent.keys(), key=len):
        translations = list(inconsistent[source].keys())
        string_ids = [src_trans_sid[source].get(t, "") for t in translations]
        results.append(LineCheckResult(source=source, translations=translations, string_ids=string_ids))

    return results


def save_line_check_results(
    results: List[LineCheckResult],
    output_path: str,
    lang_code: str = "",
) -> bool:
    """
    Save LINE CHECK results to an Excel file.

    Args:
        results: List of LineCheckResult objects
        output_path: Path to output .xlsx file
        lang_code: Language code for sheet naming

    Returns:
        True if successful
    """
    return write_line_check_excel(results, output_path, lang_code=lang_code)


def run_line_check_all_languages(
    lang_files: Dict[str, List[Path]],
    output_dir: Path,
    filter_sentences: bool = True,
    length_threshold: int = 15,
    min_occurrence: Optional[int] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, int]:
    """
    Run LINE CHECK for every language in lang_files.
    Writes LineCheck_{LANG}.txt per language.

    Args:
        lang_files: {lang_code: [list_of_xml_paths]}
        output_dir: Directory where output files are written
        filter_sentences: Whether to skip sentence entries
        length_threshold: Maximum source length
        min_occurrence: Minimum occurrences required
        progress_callback: Optional callback for progress updates

    Returns:
        {lang_code: inconsistency_count}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: Dict[str, int] = {}
    languages = sorted(lang_files.keys())
    total = len(languages)

    for idx, lang in enumerate(languages, start=1):
        if progress_callback:
            progress_callback(f"LINE CHECK {lang} ({idx}/{total})...")

        files = [str(p) for p in lang_files[lang]]

        def lang_progress(msg: str, _lang: str = lang) -> None:
            if progress_callback:
                progress_callback(f"[{_lang}] {msg}")

        check_results = run_line_check(
            target_files=files,
            filter_sentences=filter_sentences,
            length_threshold=length_threshold,
            min_occurrence=min_occurrence,
            progress_callback=lang_progress,
        )

        output_path = output_dir / f"LineCheck_{lang}.xlsx"
        ok = save_line_check_results(check_results, str(output_path), lang_code=lang)
        results[lang] = len(check_results)

        if progress_callback:
            if ok:
                progress_callback(f"LINE CHECK {lang}: {len(check_results)} issues → {output_path.name}")
            else:
                progress_callback(f"LINE CHECK {lang}: ERROR writing {output_path.name}")

    return results
