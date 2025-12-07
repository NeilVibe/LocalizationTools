"""
QuickSearch QA Tools - Glossary Checker Functions

Migrated from QuickSearch0818.py (lines 2152-3100):
1. Extract Glossary - Build glossary from files using Aho-Corasick
2. Line Check - Find inconsistent translations for same source
3. Term Check - Find missing terms in translations
4. Pattern Sequence Check - Match {code} patterns between source and translation
5. Character Count Check - Check special character count matching
"""

import os
import re
import csv
import string
from typing import List, Tuple, Dict, Optional, Set, Callable
from collections import defaultdict
from pathlib import Path

import pandas as pd
from loguru import logger

# Try to import lxml (optional - only needed for XML parsing in QA tools)
try:
    from lxml import etree
    HAS_LXML = True
except ImportError:
    HAS_LXML = False
    etree = None
    logger.warning("lxml not installed - XML QA functions will be disabled")

# Try to import ahocorasick (optional but recommended for performance)
try:
    import ahocorasick
    HAS_AHOCORASICK = True
except ImportError:
    HAS_AHOCORASICK = False
    logger.warning("ahocorasick not installed - using fallback matching (slower)")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_korean(text: str) -> bool:
    """Returns True if text contains any Korean syllable (U+AC00-U+D7A3)."""
    if not isinstance(text, str):
        return False
    return bool(re.search(r'[\uac00-\ud7a3]', text))


def is_sentence(text: str) -> bool:
    """Returns True if text ends with sentence-ending punctuation."""
    if not isinstance(text, str):
        return False
    return bool(re.search(r'[.?!]\s*$', text.strip()))


def has_punctuation(text: str) -> bool:
    """Returns True if text contains any punctuation or special ellipsis."""
    if not isinstance(text, str):
        return False
    return any(ch in string.punctuation for ch in text) or '…' in text


def extract_code_patterns(text: str) -> Set[str]:
    """Extract {code} patterns from text, non-greedy."""
    if not isinstance(text, str):
        return set()
    return set(re.findall(r'\{.*?\}', text))


def preprocess_text_for_char_count(text: str) -> str:
    """Remove formatting codes that may interfere with character counting."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r'<color:.*?>', '', text)
    text = re.sub(r'<PAColor.*?>|<PAOldColor>', '', text)
    return text


def extract_all_pairs_from_files(
    file_paths: List[str],
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> List[Tuple[str, str]]:
    """
    Extract all (StrOrigin, Str) pairs from XML and TXT/TSV files.

    Args:
        file_paths: List of file paths to process
        progress_callback: Optional callback(current, total, filename)

    Returns:
        List of (korean, translation) tuples
    """
    all_pairs = []
    total = len(file_paths)

    for idx, file_path in enumerate(file_paths, start=1):
        if progress_callback:
            progress_callback(idx, total, os.path.basename(file_path))

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".xml":
                parser = etree.XMLParser(recover=True, resolve_entities=False)
                tree = etree.parse(file_path, parser)
                for locstr in tree.xpath('//LocStr'):
                    kr = locstr.get('StrOrigin', '').strip()
                    tr = locstr.get('Str', '').strip()
                    if kr or tr:
                        all_pairs.append((kr, tr))

            elif ext in (".txt", ".tsv"):
                try:
                    df = pd.read_csv(
                        file_path,
                        delimiter="\t",
                        header=None,
                        dtype=str,
                        quoting=csv.QUOTE_NONE,
                        quotechar=None,
                        escapechar=None,
                        na_values=[''],
                        keep_default_na=False
                    )

                    if len(df.columns) >= 7:
                        for _, row in df.iterrows():
                            kr = str(row[5]).strip() if pd.notna(row[5]) else ""
                            tr = str(row[6]).strip() if pd.notna(row[6]) else ""
                            if kr or tr:
                                all_pairs.append((kr, tr))
                    else:
                        logger.warning(f"{file_path} has only {len(df.columns)} columns, expected at least 7")

                except Exception as e:
                    logger.error(f"Error reading TXT {file_path}: {e}")
                    continue

            else:
                logger.debug(f"Skipping unsupported file type: {file_path}")

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")

    return all_pairs


def extract_all_locstrs_from_files(
    file_paths: List[str],
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> List[Dict]:
    """
    Extract all LocStr entries with full metadata from files.

    Returns:
        List of dicts with: StrOrigin, Str, file_path, locstr_id
    """
    all_entries = []
    total = len(file_paths)

    for idx, file_path in enumerate(file_paths, start=1):
        if progress_callback:
            progress_callback(idx, total, os.path.basename(file_path))

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".xml":
                parser = etree.XMLParser(recover=True, resolve_entities=False)
                tree = etree.parse(file_path, parser)
                for locstr in tree.xpath('//LocStr'):
                    entry = {
                        'StrOrigin': locstr.get('StrOrigin', '').strip(),
                        'Str': locstr.get('Str', '').strip(),
                        'file_path': file_path,
                        'locstr_id': locstr.get('StringId', '') or locstr.get('ID', '')
                    }
                    all_entries.append(entry)

            elif ext in (".txt", ".tsv"):
                try:
                    df = pd.read_csv(
                        file_path,
                        delimiter="\t",
                        header=None,
                        dtype=str,
                        quoting=csv.QUOTE_NONE,
                        quotechar=None,
                        escapechar=None,
                        na_values=[''],
                        keep_default_na=False
                    )

                    if len(df.columns) >= 7:
                        for _, row in df.iterrows():
                            str_key = " ".join(
                                str(row[i]).strip() if pd.notna(row[i]) else ''
                                for i in range(min(5, len(row)))
                            )
                            entry = {
                                'StrOrigin': str(row[5]).strip() if pd.notna(row[5]) else "",
                                'Str': str(row[6]).strip() if pd.notna(row[6]) else "",
                                'file_path': file_path,
                                'locstr_id': str_key
                            }
                            all_entries.append(entry)

                except Exception as e:
                    logger.error(f"Error reading TXT {file_path}: {e}")

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")

    return all_entries


def glossary_filter(
    pairs: List[Tuple[str, str]],
    length_threshold: int = 15,
    filter_sentences: bool = True,
    min_occurrence: Optional[int] = None
) -> List[Tuple[str, str]]:
    """
    Filter pairs for glossary extraction.

    Filters:
    - Source length < threshold
    - Both non-empty
    - Translation has no Korean
    - Optionally filter sentences
    - Filter punctuation
    - Optionally min_occurrence threshold
    """
    filtered = []
    count_map = {}

    for kr, tr in pairs:
        if not kr or not tr:
            continue
        if len(kr) >= length_threshold:
            continue
        if is_korean(tr):
            continue
        if filter_sentences and is_sentence(kr):
            continue
        if has_punctuation(kr):
            continue

        filtered.append((kr, tr))
        count_map[kr] = count_map.get(kr, 0) + 1

    if min_occurrence is not None:
        filtered = [(kr, tr) for kr, tr in filtered if count_map.get(kr, 0) >= min_occurrence]

    return filtered


# =============================================================================
# QA TOOL 1: EXTRACT GLOSSARY
# =============================================================================

def extract_glossary(
    file_paths: List[str],
    filter_sentences: bool = True,
    glossary_length_threshold: int = 15,
    min_occurrence: int = 2,
    sort_method: str = "alphabetical",
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict:
    """
    Extract glossary terms from files using Aho-Corasick for occurrence counting.

    Args:
        file_paths: List of XML/TXT files to process
        filter_sentences: Filter out entries ending with . ? !
        glossary_length_threshold: Max source length
        min_occurrence: Minimum occurrence count to include
        sort_method: "alphabetical", "length", or "frequency"
        progress_callback: Optional callback(progress_percent, message)

    Returns:
        Dict with: glossary, total_candidates, total_terms, files_processed
    """
    logger.info(f"Starting glossary extraction from {len(file_paths)} files")

    # Step 1: Extract all pairs
    if progress_callback:
        progress_callback(10, "Extracting initial glossary terms...")

    all_pairs = extract_all_pairs_from_files(file_paths)

    # Filter out pairs where translation contains Korean
    all_pairs = [(kr, tr) for kr, tr in all_pairs if not is_korean(tr)]

    # Apply glossary filter
    filtered = glossary_filter(
        all_pairs,
        length_threshold=glossary_length_threshold,
        filter_sentences=filter_sentences
    )

    # Dedupe by first-seen StrOrigin
    seen = set()
    candidate_terms = []
    for kr, tr in filtered:
        if kr not in seen:
            candidate_terms.append((kr, tr))
            seen.add(kr)

    if not candidate_terms:
        logger.warning("No candidate terms found with current filters")
        return {
            "glossary": [],
            "total_candidates": 0,
            "total_terms": 0,
            "files_processed": len(file_paths)
        }

    logger.info(f"Found {len(candidate_terms)} candidate terms")

    # Step 2: Count occurrences using Aho-Corasick (or fallback)
    if progress_callback:
        progress_callback(30, "Counting term occurrences...")

    term_text_sets = {kr: set() for kr, _ in candidate_terms}
    total_texts_scanned = 0

    if HAS_AHOCORASICK:
        # Build automaton
        automaton = ahocorasick.Automaton()
        for kr, tr in candidate_terms:
            automaton.add_word(kr, kr)
        automaton.make_automaton()

        # Scan all files
        for file_idx, file_path in enumerate(file_paths):
            if progress_callback and file_idx % 10 == 0:
                progress = 30 + int((file_idx / len(file_paths)) * 40)
                progress_callback(progress, f"Scanning file {file_idx + 1}/{len(file_paths)}")

            ext = os.path.splitext(file_path)[1].lower()

            try:
                if ext == ".xml":
                    parser = etree.XMLParser(recover=True, resolve_entities=False)
                    tree = etree.parse(file_path, parser)

                    for locstr_idx, locstr in enumerate(tree.xpath('//LocStr')):
                        src = locstr.get('StrOrigin', '').strip()
                        tgt = locstr.get('Str', '').strip()

                        if is_korean(tgt) or not src:
                            continue

                        total_texts_scanned += 1

                        found_terms = set()
                        for end_idx, found_term in automaton.iter(src):
                            found_terms.add(found_term)

                        text_id = f"{file_path}_{locstr_idx}"
                        for term in found_terms:
                            term_text_sets[term].add(text_id)

                elif ext in (".txt", ".tsv"):
                    df = pd.read_csv(
                        file_path, delimiter="\t", header=None, dtype=str,
                        quoting=csv.QUOTE_NONE, on_bad_lines='skip'
                    )
                    if len(df.columns) >= 7:
                        for row_idx, row in df.iterrows():
                            src = str(row[5]).strip() if pd.notna(row[5]) else ""
                            tgt = str(row[6]).strip() if pd.notna(row[6]) else ""

                            if is_korean(tgt) or not src:
                                continue

                            total_texts_scanned += 1

                            found_terms = set()
                            for end_idx, found_term in automaton.iter(src):
                                found_terms.add(found_term)

                            text_id = f"{file_path}_{row_idx}"
                            for term in found_terms:
                                term_text_sets[term].add(text_id)

            except Exception as e:
                logger.error(f"Error scanning {file_path}: {e}")
    else:
        # Fallback: simple substring matching
        for kr, _ in candidate_terms:
            for file_path in file_paths:
                pairs = extract_all_pairs_from_files([file_path])
                for idx, (src, _) in enumerate(pairs):
                    if kr in src:
                        term_text_sets[kr].add(f"{file_path}_{idx}")
                    total_texts_scanned += 1

    # Step 3: Filter by min_occurrence
    if progress_callback:
        progress_callback(75, "Filtering by minimum occurrence...")

    final_glossary = []
    source_translations = defaultdict(lambda: defaultdict(int))

    for kr, tr in candidate_terms:
        source_translations[kr][tr] += 1

    for kr, translations in source_translations.items():
        occurrence_count = len(term_text_sets.get(kr, set()))

        if occurrence_count >= min_occurrence:
            most_frequent_tr = max(translations.items(), key=lambda x: x[1])[0]
            final_glossary.append({
                "korean": kr,
                "translation": most_frequent_tr,
                "occurrence_count": occurrence_count
            })

    # Step 4: Sort results
    if progress_callback:
        progress_callback(90, "Sorting results...")

    if sort_method == "alphabetical":
        final_glossary.sort(key=lambda x: x["korean"])
    elif sort_method == "length":
        final_glossary.sort(key=lambda x: len(x["korean"]))
    elif sort_method == "frequency":
        final_glossary.sort(key=lambda x: x["occurrence_count"], reverse=True)

    logger.success(f"Glossary extraction complete: {len(final_glossary)} terms from {total_texts_scanned} texts")

    return {
        "glossary": final_glossary,
        "total_candidates": len(candidate_terms),
        "total_terms": len(final_glossary),
        "total_texts_scanned": total_texts_scanned,
        "files_processed": len(file_paths)
    }


# =============================================================================
# QA TOOL 2: LINE CHECK
# =============================================================================

def line_check(
    file_paths: List[str],
    glossary_file_paths: Optional[List[str]] = None,
    filter_sentences: bool = True,
    glossary_length_threshold: int = 15,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict:
    """
    Find inconsistent translations - same source with different translations.

    Args:
        file_paths: Files to check
        glossary_file_paths: Optional external glossary files (if None, use self)
        filter_sentences: Filter out sentences
        glossary_length_threshold: Max source length for glossary filter
        progress_callback: Optional callback(progress_percent, message)

    Returns:
        Dict with inconsistent entries
    """
    logger.info(f"Starting line check on {len(file_paths)} files")

    # Build glossary
    if progress_callback:
        progress_callback(10, "Building glossary...")

    glossary_source = glossary_file_paths if glossary_file_paths else file_paths
    glossary_pairs = extract_all_pairs_from_files(glossary_source)
    glossary_pairs = [(kr, tr) for kr, tr in glossary_pairs if not is_korean(tr)]
    glossary_pairs = glossary_filter(
        glossary_pairs,
        length_threshold=glossary_length_threshold,
        filter_sentences=filter_sentences
    )

    # Build mapping: source -> {translation -> [files]}
    if progress_callback:
        progress_callback(40, "Analyzing translations...")

    src_tr_file = defaultdict(lambda: defaultdict(set))

    for file_idx, file_path in enumerate(file_paths):
        if progress_callback and file_idx % 10 == 0:
            progress = 40 + int((file_idx / len(file_paths)) * 40)
            progress_callback(progress, f"Parsing {file_idx + 1}/{len(file_paths)}")

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".xml":
                parser = etree.XMLParser(recover=True, resolve_entities=False)
                tree = etree.parse(file_path, parser)

                for locstr in tree.xpath('//LocStr'):
                    src = locstr.get('StrOrigin', '').strip()
                    tgt = locstr.get('Str', '').strip()

                    if not src or not tgt or is_korean(tgt):
                        continue
                    if filter_sentences and is_sentence(src):
                        continue
                    if has_punctuation(src):
                        continue

                    src_tr_file[src][tgt].add(os.path.basename(file_path))

            elif ext in (".txt", ".tsv"):
                df = pd.read_csv(
                    file_path, delimiter="\t", header=None, dtype=str,
                    quoting=csv.QUOTE_NONE, on_bad_lines='skip'
                )
                if len(df.columns) >= 7:
                    for _, row in df.iterrows():
                        src = str(row[5]).strip() if pd.notna(row[5]) else ""
                        tgt = str(row[6]).strip() if pd.notna(row[6]) else ""

                        if not src or not tgt or is_korean(tgt):
                            continue
                        if filter_sentences and is_sentence(src):
                            continue
                        if has_punctuation(src):
                            continue

                        src_tr_file[src][tgt].add(os.path.basename(file_path))

        except Exception as e:
            logger.error(f"Failed parsing {file_path}: {e}")

    # Find inconsistent entries
    if progress_callback:
        progress_callback(85, "Finding inconsistencies...")

    inconsistent = []
    for src, tr_dict in src_tr_file.items():
        if len(tr_dict) > 1:
            translations = []
            for tr, files in sorted(tr_dict.items()):
                translations.append({
                    "translation": tr,
                    "files": sorted(files)
                })
            inconsistent.append({
                "source": src,
                "translations": translations,
                "translation_count": len(tr_dict)
            })

    # Sort by source length
    inconsistent.sort(key=lambda x: len(x["source"]))

    logger.success(f"Line check complete: {len(inconsistent)} inconsistent sources")

    return {
        "inconsistent_entries": inconsistent,
        "total_sources_checked": len(src_tr_file),
        "inconsistent_count": len(inconsistent),
        "files_processed": len(file_paths)
    }


# =============================================================================
# QA TOOL 3: TERM CHECK
# =============================================================================

def term_check(
    file_paths: List[str],
    glossary_file_paths: Optional[List[str]] = None,
    filter_sentences: bool = True,
    glossary_length_threshold: int = 15,
    max_issues_per_term: int = 6,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict:
    """
    Check if glossary terms appear in source but their translations are missing from target.

    Args:
        file_paths: Files to check
        glossary_file_paths: Optional external glossary files
        filter_sentences: Filter out sentences
        glossary_length_threshold: Max source length
        max_issues_per_term: Filter out terms with more issues (likely false positives)
        progress_callback: Optional callback

    Returns:
        Dict with issues
    """
    logger.info(f"Starting term check on {len(file_paths)} files")

    # Build glossary
    if progress_callback:
        progress_callback(10, "Extracting glossary...")

    glossary_source = glossary_file_paths if glossary_file_paths else file_paths
    glossary_pairs = extract_all_pairs_from_files(glossary_source)
    glossary_pairs = [(kr, tr) for kr, tr in glossary_pairs if not is_korean(tr)]
    glossary_pairs = glossary_filter(
        glossary_pairs,
        length_threshold=glossary_length_threshold,
        filter_sentences=filter_sentences
    )

    # Dedupe
    seen = set()
    glossary_terms = []
    for kr, tr in glossary_pairs:
        if kr not in seen:
            glossary_terms.append((kr, tr))
            seen.add(kr)

    if not glossary_terms:
        return {
            "issues": [],
            "terms_checked": 0,
            "issues_count": 0,
            "files_processed": len(file_paths)
        }

    logger.info(f"Glossary extracted: {len(glossary_terms)} terms")

    # Build Aho-Corasick automaton or fallback
    if progress_callback:
        progress_callback(30, "Building term matcher...")

    term_to_translation = {}

    if HAS_AHOCORASICK:
        automaton = ahocorasick.Automaton()
        for idx, (kr_term, ref_tr) in enumerate(glossary_terms):
            automaton.add_word(kr_term, (idx, kr_term))
            term_to_translation[idx] = (kr_term, ref_tr)
        automaton.make_automaton()
    else:
        for idx, (kr_term, ref_tr) in enumerate(glossary_terms):
            term_to_translation[idx] = (kr_term, ref_tr)

    def is_isolated(text: str, start: int, end: int) -> bool:
        """Check if match is isolated (not part of larger word)."""
        before = text[start - 1] if start > 0 else ""
        after = text[end] if end < len(text) else ""
        return (not re.match(r'[\w가-힣]', before)) and (not re.match(r'[\w가-힣]', after))

    # Scan files
    if progress_callback:
        progress_callback(40, "Scanning files for term issues...")

    issues = defaultdict(list)

    for file_idx, file_path in enumerate(file_paths):
        if progress_callback and file_idx % 10 == 0:
            progress = 40 + int((file_idx / len(file_paths)) * 40)
            progress_callback(progress, f"Scanning {file_idx + 1}/{len(file_paths)}")

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".xml":
                parser = etree.XMLParser(recover=True, resolve_entities=False)
                tree = etree.parse(file_path, parser)

                for locstr in tree.xpath('//LocStr'):
                    src = locstr.get('StrOrigin', '').strip()
                    tgt = locstr.get('Str', '').strip()

                    if not src or not tgt or is_korean(tgt):
                        continue
                    if filter_sentences and is_sentence(src):
                        continue

                    matches_found = set()

                    if HAS_AHOCORASICK:
                        for end_index, (pattern_id, original_term) in automaton.iter(src):
                            start_index = end_index - len(original_term) + 1
                            if is_isolated(src, start_index, end_index + 1):
                                matches_found.add(pattern_id)
                    else:
                        for idx, (kr_term, _) in term_to_translation.items():
                            pos = src.find(kr_term)
                            if pos >= 0 and is_isolated(src, pos, pos + len(kr_term)):
                                matches_found.add(idx)

                    for pattern_id in matches_found:
                        kr_term, ref_tr = term_to_translation[pattern_id]
                        # Case-insensitive containment check
                        if ref_tr.lower() not in tgt.lower():
                            issues[(kr_term, ref_tr)].append({
                                "source": src,
                                "translation": tgt,
                                "file": os.path.basename(file_path)
                            })

            elif ext in (".txt", ".tsv"):
                df = pd.read_csv(
                    file_path, delimiter="\t", header=None, dtype=str,
                    quoting=csv.QUOTE_NONE, on_bad_lines='skip'
                )
                if len(df.columns) >= 7:
                    for _, row in df.iterrows():
                        src = str(row[5]).strip() if pd.notna(row[5]) else ""
                        tgt = str(row[6]).strip() if pd.notna(row[6]) else ""

                        if not src or not tgt or is_korean(tgt):
                            continue
                        if filter_sentences and is_sentence(src):
                            continue

                        matches_found = set()

                        if HAS_AHOCORASICK:
                            for end_index, (pattern_id, original_term) in automaton.iter(src):
                                start_index = end_index - len(original_term) + 1
                                if is_isolated(src, start_index, end_index + 1):
                                    matches_found.add(pattern_id)
                        else:
                            for idx, (kr_term, _) in term_to_translation.items():
                                pos = src.find(kr_term)
                                if pos >= 0 and is_isolated(src, pos, pos + len(kr_term)):
                                    matches_found.add(idx)

                        for pattern_id in matches_found:
                            kr_term, ref_tr = term_to_translation[pattern_id]
                            if ref_tr.lower() not in tgt.lower():
                                issues[(kr_term, ref_tr)].append({
                                    "source": src,
                                    "translation": tgt,
                                    "file": os.path.basename(file_path)
                                })

        except Exception as e:
            logger.error(f"Failed scanning {file_path}: {e}")

    # Filter by max issues (avoid false positives)
    if progress_callback:
        progress_callback(90, "Filtering results...")

    filtered_issues = []
    for (kr_term, ref_tr), problem_list in issues.items():
        if len(problem_list) <= max_issues_per_term:
            filtered_issues.append({
                "korean_term": kr_term,
                "expected_translation": ref_tr,
                "issues": problem_list,
                "issue_count": len(problem_list)
            })

    # Sort by term length
    filtered_issues.sort(key=lambda x: len(x["korean_term"]))

    logger.success(f"Term check complete: {len(filtered_issues)} terms with issues")

    return {
        "issues": filtered_issues,
        "terms_checked": len(glossary_terms),
        "issues_count": len(filtered_issues),
        "files_processed": len(file_paths)
    }


# =============================================================================
# QA TOOL 4: PATTERN SEQUENCE CHECK
# =============================================================================

def pattern_sequence_check(
    file_paths: List[str],
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict:
    """
    Check if {code} patterns in StrOrigin match {code} patterns in Str.

    Args:
        file_paths: XML/TXT files to check
        progress_callback: Optional callback

    Returns:
        Dict with mismatches
    """
    logger.info(f"Starting pattern sequence check on {len(file_paths)} files")

    if progress_callback:
        progress_callback(10, "Extracting entries...")

    all_entries = extract_all_locstrs_from_files(file_paths)
    mismatches = []

    if progress_callback:
        progress_callback(50, "Checking patterns...")

    for entry in all_entries:
        source = entry['StrOrigin']
        translation = entry['Str']

        patterns_source = extract_code_patterns(source)
        patterns_trans = extract_code_patterns(translation)

        if patterns_source != patterns_trans:
            mismatches.append({
                "source": source,
                "translation": translation,
                "file": os.path.basename(entry['file_path']),
                "source_patterns": sorted(patterns_source),
                "translation_patterns": sorted(patterns_trans),
                "locstr_id": entry.get('locstr_id', '')
            })

    logger.success(f"Pattern check complete: {len(mismatches)} mismatches found")

    return {
        "mismatches": mismatches,
        "total_entries_checked": len(all_entries),
        "mismatch_count": len(mismatches),
        "files_processed": len(file_paths)
    }


# =============================================================================
# QA TOOL 5: CHARACTER COUNT CHECK
# =============================================================================

def character_count_check(
    file_paths: List[str],
    symbols: List[str] = None,
    symbol_set: str = "BDO",
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict:
    """
    Check if special character counts match between StrOrigin and Str.

    Args:
        file_paths: XML/TXT files to check
        symbols: Custom list of symbols to check (overrides symbol_set)
        symbol_set: Predefined set - "BDO" or "BDM" (default: "BDO")
        progress_callback: Optional callback

    Returns:
        Dict with mismatches
    """
    # Define symbol sets
    SYMBOL_SETS = {
        "BDO": ["{", "}"],
        "BDM": ["▶", "{", "}", "🔗", "|"]
    }

    if symbols is None:
        symbols = SYMBOL_SETS.get(symbol_set, SYMBOL_SETS["BDO"])

    logger.info(f"Starting character count check on {len(file_paths)} files with symbols: {symbols}")

    if progress_callback:
        progress_callback(10, "Extracting entries...")

    all_entries = extract_all_locstrs_from_files(file_paths)
    mismatches = []

    if progress_callback:
        progress_callback(50, "Checking character counts...")

    for entry in all_entries:
        source = preprocess_text_for_char_count(entry['StrOrigin'])
        translation = preprocess_text_for_char_count(entry['Str'])

        for sym in symbols:
            if source.count(sym) != translation.count(sym):
                mismatches.append({
                    "source": entry['StrOrigin'],
                    "translation": entry['Str'],
                    "file": os.path.basename(entry['file_path']),
                    "mismatched_symbol": sym,
                    "source_count": source.count(sym),
                    "translation_count": translation.count(sym),
                    "locstr_id": entry.get('locstr_id', '')
                })
                break  # Only add once per entry

    logger.success(f"Character count check complete: {len(mismatches)} mismatches found")

    return {
        "mismatches": mismatches,
        "total_entries_checked": len(all_entries),
        "mismatch_count": len(mismatches),
        "symbols_checked": symbols,
        "files_processed": len(file_paths)
    }
