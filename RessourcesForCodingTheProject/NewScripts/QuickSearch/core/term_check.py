"""
TERM CHECK Module

Checks term consistency using Aho-Corasick automaton for fast multi-pattern matching.
Finds instances where a glossary term appears in source but expected translation is missing.
Supports both KR BASE and ENG BASE modes.
"""

import os
import re
from typing import List, Dict, Optional, Callable, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass, field

try:
    import ahocorasick
except ImportError:
    ahocorasick = None

from .xml_parser import parse_multiple_files
from .preprocessing import (
    PreprocessedEntry,
    preprocess_for_consistency_check,
    build_term_glossary
)
from ..utils.language_utils import is_korean, is_word_boundary
from ..utils.filters import glossary_filter
from ..config import SOURCE_BASE_KR, SOURCE_BASE_ENG


@dataclass
class TermIssue:
    """A single term consistency issue."""
    source_text: str  # The full source text containing the term
    translation_text: str  # The translation that's missing the term


@dataclass
class TermCheckResult:
    """Result for a single term in TERM CHECK."""
    term: str  # The Korean/source term
    reference_translation: str  # The expected translation
    issues: List[TermIssue] = field(default_factory=list)

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def build_automaton(glossary_terms: List[Tuple[str, str]]) -> Tuple[any, Dict[int, Tuple[str, str]]]:
    """
    Build Aho-Corasick automaton from glossary terms.

    Args:
        glossary_terms: List of (term, translation) tuples

    Returns:
        Tuple of (automaton, term_lookup_dict)
    """
    if ahocorasick is None:
        raise ImportError("ahocorasick is required for TERM CHECK")

    automaton = ahocorasick.Automaton()
    term_to_translation: Dict[int, Tuple[str, str]] = {}

    for idx, (term, translation) in enumerate(glossary_terms):
        automaton.add_word(term, (idx, term))
        term_to_translation[idx] = (term, translation)

    automaton.make_automaton()
    return automaton, term_to_translation


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

    # Check for word/CJK characters before and after
    before_is_word = bool(re.match(r'[\w가-힣]', before))
    after_is_word = bool(re.match(r'[\w가-힣]', after))

    return not before_is_word and not after_is_word


def run_term_check(
    target_files: List[str],
    glossary_files: Optional[List[str]] = None,
    eng_file: Optional[str] = None,
    source_base: str = SOURCE_BASE_KR,
    filter_sentences: bool = True,
    length_threshold: int = 15,
    min_occurrence: Optional[int] = None,
    max_issues_per_term: int = 6,
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[TermCheckResult]:
    """
    Run TERM CHECK to find term consistency issues.

    Uses Aho-Corasick for efficient multi-pattern matching.

    Args:
        target_files: List of target XML/TXT files to check
        glossary_files: Files to extract glossary from (None = use target_files)
        eng_file: English XML file (required for ENG BASE mode)
        source_base: SOURCE_BASE_KR or SOURCE_BASE_ENG
        filter_sentences: Whether to skip sentence entries
        length_threshold: Maximum source length for glossary terms
        min_occurrence: Minimum occurrences for glossary terms
        max_issues_per_term: Max issues per term to avoid noise (default: 6)
        progress_callback: Optional callback for progress updates

    Returns:
        List of TermCheckResult objects
    """
    if ahocorasick is None:
        raise ImportError("ahocorasick library is required for TERM CHECK")

    if progress_callback:
        progress_callback("Starting TERM CHECK...")

    # Determine glossary source
    glossary_source = glossary_files if glossary_files else target_files

    # Progress wrapper
    def progress_wrapper(msg: str, current: int, total: int):
        if progress_callback:
            progress_callback(f"{msg} ({current}/{total})")

    # Extract glossary entries
    if progress_callback:
        progress_callback("Extracting glossary terms...")

    glossary_entries = preprocess_for_consistency_check(
        glossary_source,
        eng_file=eng_file,
        source_base=source_base,
        progress_callback=progress_wrapper
    )

    # Build glossary pairs and filter
    glossary_pairs = [(e.source, e.translation) for e in glossary_entries]
    glossary_pairs = [(src, trans) for src, trans in glossary_pairs if not is_korean(trans)]
    glossary_pairs = glossary_filter(
        glossary_pairs,
        length_threshold=length_threshold,
        filter_sentences=filter_sentences,
        min_occurrence=min_occurrence
    )

    # Dedupe glossary
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
        progress_callback(f"Building Aho-Corasick automaton with {len(glossary_terms)} terms...")

    # Build automaton
    automaton, term_lookup = build_automaton(glossary_terms)

    # Get target entries for checking
    if progress_callback:
        progress_callback("Parsing target files for checking...")

    target_entries = preprocess_for_consistency_check(
        target_files,
        eng_file=eng_file,
        source_base=source_base,
        progress_callback=progress_wrapper
    )

    if progress_callback:
        progress_callback(f"Checking {len(target_entries)} entries...")

    # Scan for issues
    issues: Dict[int, List[TermIssue]] = defaultdict(list)
    total = len(target_entries)

    for idx, entry in enumerate(target_entries):
        if idx % 1000 == 0 and progress_callback:
            progress = (idx / total) * 100
            progress_callback(f"Aho-Corasick scan: {progress:.1f}%")

        src = entry.source
        tgt = entry.translation

        if not src or not tgt:
            continue

        # Skip if translation has Korean
        if is_korean(tgt):
            continue

        # Skip sentences if filter enabled
        if filter_sentences and re.search(r'[.?!]\s*$', src.strip()):
            continue

        # Find all term matches in source
        matches_found: Set[int] = set()
        for end_index, (pattern_id, original_term) in automaton.iter(src):
            start_index = end_index - len(original_term) + 1
            if is_isolated_match(src, start_index, end_index + 1):
                matches_found.add(pattern_id)

        # Check if expected translations are present
        for pattern_id in matches_found:
            _, ref_translation = term_lookup[pattern_id]

            # Case-insensitive containment check
            if ref_translation.lower() not in tgt.lower():
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

    # Build results
    results = []
    for pattern_id in sorted(filtered_issues.keys(), key=lambda x: len(term_lookup[x][0])):
        term, ref_trans = term_lookup[pattern_id]
        results.append(TermCheckResult(
            term=term,
            reference_translation=ref_trans,
            issues=filtered_issues[pattern_id]
        ))

    if progress_callback:
        progress_callback(f"Found {len(results)} terms with issues")

    return results


def format_term_check_results(
    results: List[TermCheckResult],
    include_filenames: bool = False
) -> str:
    """
    Format TERM CHECK results for output.

    Clean output format (no filenames):
    korean_term // reference_translation
      Source: "full source text"
      Trans: "translation text"

    Args:
        results: List of TermCheckResult objects
        include_filenames: Whether to include file names (default: False)

    Returns:
        Formatted string output
    """
    lines = []

    for result in results:
        lines.append(f"{result.term} // {result.reference_translation}")

        for issue in result.issues:
            lines.append(f'  Source: "{issue.source_text}"')
            lines.append(f'  Trans: "{issue.translation_text}"')

        lines.append("")  # Blank line between terms

    return "\n".join(lines)


def save_term_check_results(
    results: List[TermCheckResult],
    output_path: str,
    include_filenames: bool = False
) -> bool:
    """
    Save TERM CHECK results to a file.

    Args:
        results: List of TermCheckResult objects
        output_path: Path to output file
        include_filenames: Whether to include file names

    Returns:
        True if successful
    """
    try:
        formatted = format_term_check_results(results, include_filenames)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted)
        return True
    except Exception:
        return False
