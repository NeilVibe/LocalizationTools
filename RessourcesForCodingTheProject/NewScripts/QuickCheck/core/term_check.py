"""
TERM CHECK Module

Checks term consistency using Dual Aho-Corasick automaton for fast multi-pattern matching.
Finds instances where a glossary term appears in source but expected translation is missing.

Dual Automaton design:
  - Source automaton: scans source text for term matches
  - Translation automaton: scans target text ONCE for all expected translations
  - Translation presence check: O(1) lookup instead of O(target_len) per match

Match modes:
  - ISOLATED:  word-boundary check (same as QuickSearch)
  - SUBSTRING: any occurrence — no isolation check (finds more matches)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass, field

try:
    import ahocorasick
except ImportError:
    ahocorasick = None

import config
from core.preprocessing import preprocess_for_consistency_check
from utils.language_utils import is_korean
from utils.filters import glossary_filter
from utils.excel_writer import write_term_check_excel


MATCH_MODE_ISOLATED = config.MATCH_MODE_ISOLATED
MATCH_MODE_SUBSTRING = config.MATCH_MODE_SUBSTRING


@dataclass
class TermIssue:
    """A single term consistency issue."""
    source_text: str      # Full source text containing the term
    translation_text: str  # Translation that's missing the expected term


@dataclass
class TermCheckResult:
    """Result for a single term in TERM CHECK."""
    term: str                     # The Korean/source term
    reference_translation: str    # The expected translation
    issues: List[TermIssue] = field(default_factory=list)

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def build_dual_automatons(
    glossary_terms: List[Tuple[str, str]]
) -> Tuple[object, object, Dict[int, Tuple[str, str]]]:
    """
    Build two Aho-Corasick automatons for dual-automaton scan.

    Source automaton: maps term text -> (term_id, term)
    Translation automaton: maps translation text -> (term_id, translation)
    term_lookup: maps term_id -> (term, translation)

    Args:
        glossary_terms: List of (term, translation) tuples

    Returns:
        (source_automaton, translation_automaton, term_lookup)
    """
    if ahocorasick is None:
        raise ImportError("ahocorasick is required for TERM CHECK")
    if not glossary_terms:
        raise ValueError("glossary_terms cannot be empty")

    source_auto = ahocorasick.Automaton()
    trans_auto = ahocorasick.Automaton()
    term_lookup: Dict[int, Tuple[str, str]] = {}

    for idx, (term, translation) in enumerate(glossary_terms):
        # Skip entries with empty term or translation — would corrupt automaton results
        if not term or not translation:
            continue
        source_auto.add_word(term, (idx, term))
        trans_auto.add_word(translation.lower(), (idx, translation))
        term_lookup[idx] = (term, translation)

    if not term_lookup:
        raise ValueError("No valid (non-empty) glossary terms after filtering")

    source_auto.make_automaton()
    trans_auto.make_automaton()

    return source_auto, trans_auto, term_lookup


def is_isolated_match(text: str, start: int, end: int) -> bool:
    """
    Check if a match is isolated (at word boundaries).

    Args:
        text: The full text
        start: Start index of match
        end: End index of match (exclusive)

    Returns:
        True if match is isolated
    """
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""

    before_is_word = bool(re.match(r'[\w가-힣]', before))
    after_is_word = bool(re.match(r'[\w가-힣]', after))

    return not before_is_word and not after_is_word


def run_term_check(
    target_files: List[str],
    glossary_files: Optional[List[str]] = None,
    filter_sentences: bool = True,
    length_threshold: int = 15,
    min_occurrence: Optional[int] = None,
    max_issues_per_term: int = 6,
    match_mode: str = MATCH_MODE_ISOLATED,
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[TermCheckResult]:
    """
    Run TERM CHECK for a single language using Dual Aho-Corasick.

    Args:
        target_files: List of target XML files to check
        glossary_files: Files to extract glossary from (None = use target_files = auto-extract)
        filter_sentences: Whether to skip sentence entries
        length_threshold: Maximum source length for glossary terms
        min_occurrence: Minimum occurrences for glossary terms
        max_issues_per_term: Cap per term to avoid noise (default: 6)
        match_mode: MATCH_MODE_ISOLATED or MATCH_MODE_SUBSTRING
        progress_callback: Optional callback for progress updates

    Returns:
        List of TermCheckResult objects
    """
    if ahocorasick is None:
        raise ImportError("ahocorasick library is required for TERM CHECK")

    if progress_callback:
        progress_callback("Starting TERM CHECK...")

    glossary_source = glossary_files if glossary_files else target_files

    def progress_wrapper(msg: str, current: int, total: int) -> None:
        if progress_callback:
            progress_callback(f"{msg} ({current}/{total})")

    # --- Extract glossary ---
    if progress_callback:
        progress_callback("Extracting glossary terms...")

    glossary_entries = preprocess_for_consistency_check(glossary_source, progress_wrapper)
    glossary_pairs = [(e.source, e.translation) for e in glossary_entries]
    glossary_pairs = [(src, trans) for src, trans in glossary_pairs if not is_korean(trans)]
    glossary_pairs = glossary_filter(
        glossary_pairs,
        length_threshold=length_threshold,
        filter_sentences=filter_sentences,
        min_occurrence=min_occurrence,
    )

    # Dedupe by source (keep first translation)
    seen: Set[str] = set()
    glossary_terms: List[Tuple[str, str]] = []
    for src, trans in glossary_pairs:
        if src not in seen:
            glossary_terms.append((src, trans))
            seen.add(src)

    if not glossary_terms:
        if progress_callback:
            progress_callback("No glossary terms found")
        return []

    if progress_callback:
        progress_callback(f"Building dual automatons with {len(glossary_terms)} terms...")

    # --- Build dual automatons ---
    source_auto, trans_auto, term_lookup = build_dual_automatons(glossary_terms)

    # --- Parse target entries ---
    if progress_callback:
        progress_callback("Parsing target files for checking...")

    target_entries = preprocess_for_consistency_check(target_files, progress_wrapper)

    if progress_callback:
        progress_callback(f"Scanning {len(target_entries)} entries...")

    # --- Scan ---
    issues: Dict[int, List[TermIssue]] = defaultdict(list)
    total = len(target_entries)

    for idx, entry in enumerate(target_entries):
        if idx % 1000 == 0 and progress_callback:
            progress = (idx / total) * 100 if total else 0
            progress_callback(f"Scanning: {progress:.1f}%")

        src = entry.source
        tgt = entry.translation

        if not src or not tgt:
            continue

        # Skip if translation has Korean (untranslated)
        if is_korean(tgt):
            continue

        # Skip sentences if filter enabled
        if filter_sentences and re.search(r'[.?!]\s*$', src.strip()):
            continue

        # --- Source scan: find which terms appear in this source ---
        matches_found: Set[int] = set()
        for end_index, (pattern_id, original_term) in source_auto.iter(src):
            start_index = end_index - len(original_term) + 1
            if match_mode == MATCH_MODE_ISOLATED:
                if is_isolated_match(src, start_index, end_index + 1):
                    matches_found.add(pattern_id)
            else:
                # SUBSTRING mode: accept any occurrence
                matches_found.add(pattern_id)

        if not matches_found:
            continue

        # --- Translation scan: which translations are present in target (ONCE) ---
        # Uses the dual automaton: scan tgt.lower() once, collect all term_ids present
        tgt_lower = tgt.lower()
        present_translations: Set[int] = set()
        for _, (trans_id, _) in trans_auto.iter(tgt_lower):
            present_translations.add(trans_id)

        # --- Check: for each matched source term, is its translation present? ---
        for pattern_id in matches_found:
            if pattern_id not in present_translations:
                issues[pattern_id].append(TermIssue(
                    source_text=src,
                    translation_text=tgt
                ))

    if progress_callback:
        progress_callback("Filtering results...")

    # Filter out terms with too many issues (likely false positives)
    filtered_issues = {
        k: v for k, v in issues.items()
        if len(v) <= max_issues_per_term
    }

    # Build results sorted by term length
    results = []
    for pattern_id in sorted(filtered_issues.keys(), key=lambda x: len(term_lookup[x][0])):
        term, ref_trans = term_lookup[pattern_id]
        results.append(TermCheckResult(
            term=term,
            reference_translation=ref_trans,
            issues=filtered_issues[pattern_id],
        ))

    if progress_callback:
        progress_callback(f"Found {len(results)} terms with issues")

    return results


def save_term_check_results(
    results: List[TermCheckResult],
    output_path: str,
    lang_code: str = "",
    match_mode: str = "",
) -> bool:
    """
    Save TERM CHECK results to an Excel file.

    Args:
        results: List of TermCheckResult objects
        output_path: Path to output .xlsx file
        lang_code: Language code for sheet naming
        match_mode: Match mode label (Isolated / Substring)

    Returns:
        True if successful
    """
    return write_term_check_excel(
        results, output_path, lang_code=lang_code, match_mode=match_mode
    )


def run_term_check_all_languages(
    lang_files: Dict[str, List[Path]],
    output_dir: Path,
    glossary_lang_files: Optional[Dict[str, List[Path]]] = None,
    filter_sentences: bool = True,
    length_threshold: int = 15,
    min_occurrence: Optional[int] = None,
    max_issues_per_term: int = 6,
    match_mode: str = MATCH_MODE_ISOLATED,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, int]:
    """
    Run TERM CHECK for every language in lang_files.
    Writes TermCheck_{LANG}.txt per language.

    Args:
        lang_files: {lang_code: [list_of_xml_paths]}
        output_dir: Directory where output files are written
        glossary_lang_files: Optional external glossary {lang_code: [files]}.
                             None = auto-extract glossary from source files.
        filter_sentences: Whether to skip sentence entries
        length_threshold: Maximum source length for glossary terms
        min_occurrence: Minimum occurrences for glossary terms
        max_issues_per_term: Cap per term
        match_mode: MATCH_MODE_ISOLATED or MATCH_MODE_SUBSTRING
        progress_callback: Optional callback for progress updates

    Returns:
        {lang_code: issue_count}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: Dict[str, int] = {}
    languages = sorted(lang_files.keys())
    total = len(languages)

    for idx, lang in enumerate(languages, start=1):
        if progress_callback:
            progress_callback(f"TERM CHECK {lang} ({idx}/{total})...")

        target_files = [str(p) for p in lang_files[lang]]

        # Determine glossary source
        if glossary_lang_files is not None:
            if lang not in glossary_lang_files:
                if progress_callback:
                    progress_callback(f"TERM CHECK {lang}: no glossary — SKIPPED")
                continue
            glossary_files: Optional[List[str]] = [str(p) for p in glossary_lang_files[lang]]
        else:
            glossary_files = None  # auto-extract from target_files

        def lang_progress(msg: str, _lang: str = lang) -> None:
            if progress_callback:
                progress_callback(f"[{_lang}] {msg}")

        check_results = run_term_check(
            target_files=target_files,
            glossary_files=glossary_files,
            filter_sentences=filter_sentences,
            length_threshold=length_threshold,
            min_occurrence=min_occurrence,
            max_issues_per_term=max_issues_per_term,
            match_mode=match_mode,
            progress_callback=lang_progress,
        )

        output_path = output_dir / f"TermCheck_{lang}.xlsx"
        save_term_check_results(
            check_results, str(output_path),
            lang_code=lang, match_mode=match_mode
        )
        results[lang] = len(check_results)

        if progress_callback:
            progress_callback(f"TERM CHECK {lang}: {len(check_results)} issues → {output_path.name}")

    return results
