"""
Glossary Module

Glossary extraction and filtering functionality.
"""

import os
import time
from typing import List, Dict, Optional, Callable, Tuple, Set
from collections import Counter

try:
    import ahocorasick
except ImportError:
    ahocorasick = None

try:
    from core.xml_parser import parse_multiple_files, extract_pairs
    from utils.language_utils import is_korean, is_word_boundary
    from utils.filters import glossary_filter, dedupe_glossary, count_glossary_occurrences
except ImportError:
    from .xml_parser import parse_multiple_files, extract_pairs
    from ..utils.language_utils import is_korean, is_word_boundary
    from ..utils.filters import glossary_filter, dedupe_glossary, count_glossary_occurrences


def extract_glossary(
    source_files: List[str],
    length_threshold: int = 15,
    filter_sentences: bool = True,
    min_occurrence: Optional[int] = None,
    sort_method: str = "alphabetical",
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[Tuple[str, str, int]]:
    """
    Extract glossary terms from source files.

    Uses Aho-Corasick for efficient validation that terms actually
    appear in the source texts.

    Args:
        source_files: List of XML/TXT files
        length_threshold: Maximum source length
        filter_sentences: Whether to filter sentence entries
        min_occurrence: Minimum occurrences required
        sort_method: "alphabetical", "length", or "frequency"
        progress_callback: Optional callback for progress updates

    Returns:
        List of (term, translation, count) tuples
    """
    if progress_callback:
        progress_callback("Extracting initial glossary terms...")

    # Parse all files
    def progress_wrapper(msg: str, current: int, total: int):
        if progress_callback:
            progress_callback(f"{msg} ({current}/{total})")

    entries = parse_multiple_files(source_files, progress_wrapper)
    pairs = extract_pairs(entries)

    if progress_callback:
        progress_callback(f"Found {len(pairs)} total pairs")

    # Filter out Korean translations
    pairs = [(src, trans) for src, trans in pairs if not is_korean(trans)]

    # Apply glossary filters
    filtered = glossary_filter(
        pairs,
        length_threshold=length_threshold,
        filter_sentences=filter_sentences,
        min_occurrence=min_occurrence
    )

    if progress_callback:
        progress_callback(f"Filtered to {len(filtered)} pairs")

    # Dedupe and count
    result = count_glossary_occurrences(filtered)

    if progress_callback:
        progress_callback(f"Final glossary: {len(result)} unique terms")

    # Sort
    if sort_method == "alphabetical":
        result.sort(key=lambda x: x[0])
    elif sort_method == "length":
        result.sort(key=lambda x: len(x[0]))
    elif sort_method == "frequency":
        result.sort(key=lambda x: x[2], reverse=True)

    return result


def extract_glossary_with_validation(
    source_files: List[str],
    length_threshold: int = 15,
    filter_sentences: bool = True,
    min_occurrence: Optional[int] = None,
    sort_method: str = "alphabetical",
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[Tuple[str, str, int]]:
    """
    Extract glossary with Aho-Corasick validation.

    This validates that candidate terms actually appear as isolated
    words in the source texts, reducing false positives.

    Args:
        source_files: List of XML/TXT files
        length_threshold: Maximum source length
        filter_sentences: Whether to filter sentence entries
        min_occurrence: Minimum occurrences required
        sort_method: "alphabetical", "length", or "frequency"
        progress_callback: Optional callback for progress updates

    Returns:
        List of (term, translation, count) tuples
    """
    if ahocorasick is None:
        # Fall back to simple extraction
        return extract_glossary(
            source_files, length_threshold, filter_sentences,
            min_occurrence, sort_method, progress_callback
        )

    start_time = time.time()

    if progress_callback:
        progress_callback("Extracting candidate terms...")

    # Parse all files
    def progress_wrapper(msg: str, current: int, total: int):
        if progress_callback:
            progress_callback(f"{msg} ({current}/{total})")

    entries = parse_multiple_files(source_files, progress_wrapper)
    pairs = extract_pairs(entries)

    # Filter out Korean translations
    pairs = [(src, trans) for src, trans in pairs if not is_korean(trans)]

    # Apply glossary filters
    filtered = glossary_filter(
        pairs,
        length_threshold=length_threshold,
        filter_sentences=filter_sentences
    )

    # Dedupe candidates
    seen: Set[str] = set()
    candidates: List[Tuple[str, str]] = []
    for src, trans in filtered:
        if src not in seen:
            candidates.append((src, trans))
            seen.add(src)

    if not candidates:
        if progress_callback:
            progress_callback("No candidate terms found")
        return []

    if progress_callback:
        progress_callback(f"Building automaton with {len(candidates)} candidates...")

    # Build Aho-Corasick automaton
    automaton = ahocorasick.Automaton()
    term_info: Dict[int, Tuple[str, str]] = {}

    for idx, (term, trans) in enumerate(candidates):
        automaton.add_word(term, (idx, term))
        term_info[idx] = (term, trans)

    automaton.make_automaton()

    # Scan all source texts for isolated occurrences
    if progress_callback:
        progress_callback("Scanning for term occurrences...")

    occurrence_counts: Dict[int, int] = Counter()

    all_sources = [entry.str_origin for entry in entries if entry.str_origin]
    total_sources = len(all_sources)

    for idx, src in enumerate(all_sources):
        if idx % 5000 == 0 and progress_callback:
            progress = (idx / total_sources) * 100
            progress_callback(f"Scanning: {progress:.1f}%")

        # Find all matches
        for end_index, (pattern_id, original_term) in automaton.iter(src):
            start_index = end_index - len(original_term) + 1

            # Check if isolated
            before = src[start_index - 1] if start_index > 0 else ""
            after = src[end_index + 1] if end_index + 1 < len(src) else ""

            import re
            before_is_word = bool(re.match(r'[\w가-힣]', before))
            after_is_word = bool(re.match(r'[\w가-힣]', after))

            if not before_is_word and not after_is_word:
                occurrence_counts[pattern_id] += 1

    # Filter by min_occurrence
    final_terms: List[Tuple[str, str, int]] = []

    for pattern_id, count in occurrence_counts.items():
        if min_occurrence is not None and count < min_occurrence:
            continue
        term, trans = term_info[pattern_id]
        final_terms.append((term, trans, count))

    # Sort
    if sort_method == "alphabetical":
        final_terms.sort(key=lambda x: x[0])
    elif sort_method == "length":
        final_terms.sort(key=lambda x: len(x[0]))
    elif sort_method == "frequency":
        final_terms.sort(key=lambda x: x[2], reverse=True)

    elapsed = time.time() - start_time

    if progress_callback:
        progress_callback(f"Extracted {len(final_terms)} terms in {elapsed:.1f}s")

    return final_terms


def save_glossary(
    glossary: List[Tuple[str, str, int]],
    output_path: str,
    include_counts: bool = True
) -> bool:
    """
    Save glossary to a tab-separated file.

    Args:
        glossary: List of (term, translation, count) tuples
        output_path: Path to output file
        include_counts: Whether to include occurrence counts

    Returns:
        True if successful
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for term, trans, count in glossary:
                if include_counts:
                    f.write(f"{term}\t{trans}\t[{count}]\n")
                else:
                    f.write(f"{term}\t{trans}\n")
        return True
    except Exception:
        return False


def load_glossary(file_path: str) -> List[Tuple[str, str]]:
    """
    Load glossary from a tab-separated file.

    Args:
        file_path: Path to glossary file

    Returns:
        List of (term, translation) tuples
    """
    glossary = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split('\t')
                if len(parts) >= 2:
                    term = parts[0].strip()
                    trans = parts[1].strip()
                    if term and trans:
                        glossary.append((term, trans))

    except Exception:
        pass

    return glossary
