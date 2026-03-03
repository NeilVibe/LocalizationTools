"""
Glossary Extractor

Automatically extracts a glossary from language data files.
Based on the reference filter_excel_by_xml_str.py pipeline, adapted for QuickCheck.

Pipeline:
  1. Parse all XML/Excel files for a language → (StrOrigin, Str) pairs
  2. Apply filters: max char length, is_phrase(), no punctuation
  3. Count occurrences of each unique source term
  4. Apply min_occurrence filter
  5. Output glossary_LANG.xlsx

Uses: glossary_filter() + count_glossary_occurrences() from utils/filters.py
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple

from core.preprocessing import preprocess_for_consistency_check
from utils.filters import glossary_filter, count_glossary_occurrences
from utils.language_utils import is_korean
from utils.excel_writer import write_glossary_excel

logger = logging.getLogger(__name__)


def extract_glossary_for_files(
    target_files: List[str],
    max_term_length: int = 20,
    min_occurrence: int = 2,
    filter_sentences: bool = True,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[Tuple[str, str, int]]:
    """
    Extract a glossary from language data files with occurrence counts.

    Pipeline:
      1. Parse files → PreprocessedEntry list
      2. Extract (source, translation) pairs — skip Korean translations
      3. Apply glossary_filter (max length, is_phrase, no punctuation, min_occurrence)
      4. Count occurrences per unique source term
      5. Return [(source, translation, count), ...]

    Args:
        target_files: List of XML/Excel file paths to parse
        max_term_length: Maximum source text character length
        min_occurrence: Minimum times a term must appear
        filter_sentences: Whether to exclude phrase/sentence entries
        progress_callback: Optional callback for progress updates

    Returns:
        List of (source, translation, occurrence_count) tuples, sorted by count desc
    """
    if progress_callback:
        progress_callback("Parsing files...")

    def progress_wrapper(msg: str, current: int, total: int) -> None:
        if progress_callback:
            progress_callback(f"{msg} ({current}/{total})")

    entries = preprocess_for_consistency_check(target_files, progress_wrapper)

    if progress_callback:
        progress_callback(f"Parsed {len(entries)} entries, extracting pairs...")

    # Raw pairs — skip untranslated (Korean) translations
    raw_pairs = [
        (e.source, e.translation)
        for e in entries
        if e.source and e.translation and not is_korean(e.translation)
    ]

    # Apply all filters (length, is_phrase, no punctuation, min_occurrence)
    filtered_pairs = glossary_filter(
        raw_pairs,
        length_threshold=max_term_length,
        filter_sentences=filter_sentences,
        min_occurrence=min_occurrence,
    )

    if progress_callback:
        progress_callback(f"After filtering: {len(filtered_pairs)} pairs, counting occurrences...")

    # Count and deduplicate
    glossary_with_counts = count_glossary_occurrences(filtered_pairs)

    if progress_callback:
        progress_callback(f"Glossary built: {len(glossary_with_counts)} terms")

    return glossary_with_counts


def extract_glossary_all_languages(
    lang_files: Dict[str, List[Path]],
    output_dir: Path,
    max_term_length: int = 20,
    min_occurrence: int = 2,
    filter_sentences: bool = True,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, int]:
    """
    Extract glossary for every language in lang_files.
    Writes glossary_LANG.xlsx per language.

    Args:
        lang_files: {lang_code: [list_of_file_paths]}
        output_dir: Directory where output files are written
        max_term_length: Maximum source character length
        min_occurrence: Minimum occurrences required
        filter_sentences: Whether to exclude phrase/sentence entries
        progress_callback: Optional callback for progress updates

    Returns:
        {lang_code: term_count}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: Dict[str, int] = {}
    languages = sorted(lang_files.keys())
    total = len(languages)

    for idx, lang in enumerate(languages, start=1):
        if progress_callback:
            progress_callback(f"Extracting glossary {lang} ({idx}/{total})...")

        files = [str(p) for p in lang_files[lang]]

        def lang_progress(msg: str, _lang: str = lang) -> None:
            if progress_callback:
                progress_callback(f"[{_lang}] {msg}")

        glossary = extract_glossary_for_files(
            target_files=files,
            max_term_length=max_term_length,
            min_occurrence=min_occurrence,
            filter_sentences=filter_sentences,
            progress_callback=lang_progress,
        )

        output_path = output_dir / f"glossary_{lang}.xlsx"
        ok = write_glossary_excel(glossary, str(output_path), lang_code=lang)
        results[lang] = len(glossary)

        if progress_callback:
            if ok:
                progress_callback(f"Glossary {lang}: {len(glossary)} terms → {output_path.name}")
            else:
                progress_callback(f"Glossary {lang}: ERROR writing {output_path.name}")

    return results
