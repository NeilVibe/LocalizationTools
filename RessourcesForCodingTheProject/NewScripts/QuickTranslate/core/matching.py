"""
Matching Algorithms.

All matching algorithms for QuickTranslate:
- Substring match (original, lookup only)
- StringID-only (SCRIPT strings)
- Strict (StringID + StrOrigin, with optional fuzzy StrOrigin)
- Special key match (legacy)
- Reverse lookup (text -> StringID)
"""

import logging
from typing import Callable, Dict, List, Optional, Set, Tuple

import config
from .text_utils import normalize_for_matching
from .korean_detection import is_korean_text

logger = logging.getLogger(__name__)

# SCRIPT categories - imported from config for single source of truth
SCRIPT_CATEGORIES = config.SCRIPT_CATEGORIES
SCRIPT_EXCLUDE_SUBFOLDERS = config.SCRIPT_EXCLUDE_SUBFOLDERS


def normalize_text(text: str) -> str:
    """
    Normalize text for case-insensitive matching.

    Uses shared normalize_for_matching from text_utils.
    """
    return normalize_for_matching(text)


def find_matches(korean_input: str, strorigin_index: Dict[str, str]) -> List[str]:
    """
    Find all StringIDs where korean_input is a substring of StrOrigin.

    Original matching algorithm - substring match.

    Args:
        korean_input: Korean text to search for
        strorigin_index: Dict mapping StringID to StrOrigin

    Returns:
        List of matching StringIDs
    """
    if not korean_input.strip():
        return []

    matches = []
    search_text = korean_input.strip()

    for string_id, str_origin in strorigin_index.items():
        if search_text in str_origin:
            matches.append(string_id)

    return matches


def find_matches_with_stats(
    korean_inputs: List[str],
    strorigin_index: Dict[str, str],
) -> Tuple[List[List[str]], Dict[str, int]]:
    """
    Find matches for multiple inputs with statistics.

    Args:
        korean_inputs: List of Korean text to search for
        strorigin_index: Dict mapping StringID to StrOrigin

    Returns:
        Tuple of (matches_per_input, stats_dict)
        stats_dict has keys: total, matched, no_match, multi_match, empty_input
    """
    matches_per_input = []
    stats = {
        "total": len(korean_inputs),
        "matched": 0,       # Inputs with exactly 1 match
        "no_match": 0,      # Inputs with 0 matches
        "multi_match": 0,   # Inputs with 2+ matches
        "empty_input": 0,   # Empty/whitespace inputs
        "total_matches": 0, # Sum of all matches found
    }

    for korean_text in korean_inputs:
        if not korean_text or not korean_text.strip():
            stats["empty_input"] += 1
            matches_per_input.append([])
            continue

        matches = find_matches(korean_text, strorigin_index)
        matches_per_input.append(matches)
        stats["total_matches"] += len(matches)

        if len(matches) == 0:
            stats["no_match"] += 1
        elif len(matches) == 1:
            stats["matched"] += 1
        else:
            stats["multi_match"] += 1

    return matches_per_input, stats


def find_matches_stringid_only(
    corrections: List[Dict],
    stringid_to_category: Dict[str, str],
    stringid_to_subfolder: Optional[Dict[str, str]] = None,
) -> Tuple[List[Dict], int]:
    """
    Filter corrections to SCRIPT-only and match by StringID.

    For SCRIPT strings from export/Dialog/ and export/Sequencer/ folders,
    StrOrigin is just the raw KOR text, so StringID is sufficient for matching.

    Also excludes StringIDs in SCRIPT_EXCLUDE_SUBFOLDERS (e.g. NarrationDialog).

    Args:
        corrections: List of correction dicts with "string_id" key
        stringid_to_category: Dict mapping StringID to category (folder) name
        stringid_to_subfolder: Optional dict mapping StringID to subfolder name

    Returns:
        Tuple of (script_corrections, skipped_count)
    """
    script_corrections = []
    skipped = 0

    # Pre-compute lowercase exclusion set for case-insensitive matching
    exclude_lower = {s.lower() for s in SCRIPT_EXCLUDE_SUBFOLDERS}

    for c in corrections:
        string_id = c.get("string_id", "")
        category = stringid_to_category.get(string_id, "Uncategorized")

        if category in SCRIPT_CATEGORIES:
            # Check if subfolder is in exclusion list (case-insensitive)
            if stringid_to_subfolder:
                subfolder = stringid_to_subfolder.get(string_id, "")
                if subfolder.lower() in exclude_lower:
                    skipped += 1
                    continue
            script_corrections.append(c)
        else:
            skipped += 1

    return script_corrections, skipped


def find_matches_strict(
    corrections: List[Dict],
    xml_entries: Dict[Tuple[str, str], dict],
) -> Tuple[List[Dict], int]:
    """
    Match by (StringID, normalized_StrOrigin) tuple.

    Strict matching requires both StringID AND StrOrigin to match.
    This is the most precise matching mode.

    Args:
        corrections: List of correction dicts with "string_id" and "str_origin" keys
        xml_entries: Dict keyed by (StringID, normalized_StrOrigin) tuples

    Returns:
        Tuple of (matched_corrections, not_found_count)
    """
    matched = []
    not_found = 0

    for c in corrections:
        string_id = c.get("string_id", "")
        str_origin = c.get("str_origin", "")
        key = (string_id, normalize_text(str_origin))

        if key in xml_entries:
            matched.append(c)
        else:
            not_found += 1

    return matched, not_found


def find_matches_special_key(
    corrections: List[Dict],
    xml_entries: Dict[str, dict],
    key_fields: List[str],
) -> Tuple[List[Dict], int]:
    """
    Match by user-defined composite key pattern.

    Build keys from specified fields and match against XML entries.

    Args:
        corrections: List of correction dicts
        xml_entries: Dict keyed by composite keys
        key_fields: List of field names to combine into key (e.g., ["string_id", "category"])

    Returns:
        Tuple of (matched_corrections, not_found_count)
    """
    matched = []
    not_found = 0

    for c in corrections:
        # Build composite key from specified fields
        key_parts = []
        for field in key_fields:
            val = c.get(field, "")
            key_parts.append(normalize_text(val) if val else "")

        key = ":".join(key_parts)

        if key in xml_entries:
            matched.append(c)
        else:
            not_found += 1

    return matched, not_found


def _is_entry_untranslated(entry: dict) -> bool:
    """Check if entry needs translation (str_value is empty or Korean)."""
    str_value = entry.get("str_value", "")
    if not str_value or not str_value.strip():
        return True
    return is_korean_text(str_value)


def find_matches_strict_fuzzy(
    corrections: List[Dict],
    xml_entries: Dict[Tuple[str, str], dict],
    fuzzy_model,
    fuzzy_index,
    fuzzy_texts: List[str],
    fuzzy_entries: List[dict],
    fuzzy_threshold: float = 0.85,
    only_untranslated: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[List[Dict], int]:
    """
    Strict match with fuzzy StrOrigin verification via SBERT.

    OPTIMIZED: StringID pool pre-filtering + FAISS on pool only.

    Standard FAISS workflow (like KRSIMILAR), but on a SMALLER pool:
    1. Try exact match first (StringID + normalized_StrOrigin tuple)
    2. Group remaining corrections by StringID
    3. For each unique StringID:
       a. Get pool of target entries with that StringID (typically 1-10 entries)
       b. Encode pool texts, normalize, build temporary FAISS index
       c. Encode queries, normalize
       d. Search pool FAISS index for best match

    This is DRAMATICALLY faster because:
    - StringID pre-filtering reduces pool from 100,000+ to typically 1-10 entries
    - FAISS search on tiny pool is instant
    - Each pool encoded once, not per-query

    Args:
        corrections: List of correction dicts with "string_id" and "str_origin" keys
        xml_entries: Dict keyed by (StringID, normalized_StrOrigin) tuples
        fuzzy_model: Loaded SentenceTransformer model
        fuzzy_index: Unused (kept for backward compatibility)
        fuzzy_texts: Unused (kept for backward compatibility)
        fuzzy_entries: Target entry dicts to build StringID pool index
        fuzzy_threshold: Minimum similarity score (default 0.85)
        only_untranslated: If True, filter pool to entries that need translation
        progress_callback: Optional callback for detailed progress logging

    Returns:
        Tuple of (matched_corrections, not_found_count)
    """
    import numpy as np
    import faiss as faiss_lib
    from collections import defaultdict

    matched = []
    not_found = 0

    # Build StringID -> entries index for fast pool lookup
    stringid_to_entries: Dict[str, List[dict]] = defaultdict(list)
    filtered_count = 0
    for entry in fuzzy_entries:
        sid = entry.get("string_id", "")
        if sid:
            if only_untranslated and not _is_entry_untranslated(entry):
                filtered_count += 1
                continue  # Skip already-translated
            stringid_to_entries[sid].append(entry)

    logger.info(f"Built StringID pool index: {len(stringid_to_entries)} unique StringIDs")

    # Phase 1: Pool index built
    if progress_callback:
        progress_callback(f"[Phase 1/4] Pool index: {len(stringid_to_entries):,} StringIDs from {len(fuzzy_entries):,} entries")
        if only_untranslated:
            progress_callback(f"  - Filtered out {filtered_count:,} already-translated entries")

    # Separate corrections: exact matches vs need fuzzy, grouped by StringID
    need_fuzzy_by_stringid: Dict[str, List[Dict]] = defaultdict(list)

    for c in corrections:
        string_id = c.get("string_id", "")
        str_origin = c.get("str_origin", "")

        if not string_id:
            not_found += 1
            continue

        # Try exact strict match first (cheap)
        key = (string_id, normalize_text(str_origin))
        if key in xml_entries:
            matched.append(c)
            continue

        # Need fuzzy matching - group by StringID for batched processing
        if str_origin.strip() and string_id in stringid_to_entries:
            need_fuzzy_by_stringid[string_id].append(c)
        else:
            not_found += 1

    total_need_fuzzy = sum(len(v) for v in need_fuzzy_by_stringid.values())
    logger.info(f"Exact matches: {len(matched)}, need fuzzy: {total_need_fuzzy} "
                f"across {len(need_fuzzy_by_stringid)} unique StringIDs")

    # Phase 2: Exact matches complete
    if progress_callback:
        progress_callback(f"[Phase 2/4] Exact matches: {len(matched)}, need fuzzy: {total_need_fuzzy}")

    if not need_fuzzy_by_stringid:
        # Phase 4: Complete (no fuzzy needed)
        if progress_callback:
            progress_callback(f"[Phase 4/4] COMPLETE: {len(matched)} matched, {not_found} not found")
            if len(corrections) > 0:
                progress_callback(f"  - Match rate: {len(matched)/len(corrections)*100:.1f}%")
        return matched, not_found

    # Process each StringID group: encode pool ONCE, then batch match all queries
    processed = 0
    group_count = 0
    total_groups = len(need_fuzzy_by_stringid)

    if progress_callback:
        progress_callback(f"[Phase 3/4] Fuzzy matching {total_groups} StringID groups...")

    for string_id, corr_group in need_fuzzy_by_stringid.items():
        pool = stringid_to_entries[string_id]
        group_count += 1

        if processed % 100 == 0 and processed > 0:
            logger.info(f"Fuzzy matching: {processed}/{total_need_fuzzy} processed")

        # Log every 10 rows OR first 5 groups for visibility
        if progress_callback and (processed % 10 == 0 or group_count <= 5):
            truncated_id = string_id[:25] + "..." if len(string_id) > 25 else string_id
            progress_callback(f"[{group_count}/{total_groups}] {truncated_id}: pool={len(pool)}, queries={len(corr_group)}")

        # Encode pool once for this StringID
        pool_texts = [e.get("str_origin", "") for e in pool]

        # Batch encode all queries for this StringID
        query_texts = [c.get("str_origin", "").strip() for c in corr_group]

        # Encode pool and queries, normalize for cosine similarity
        pool_embeddings = fuzzy_model.encode(pool_texts, show_progress_bar=False, convert_to_numpy=True)
        pool_embeddings = np.ascontiguousarray(pool_embeddings, dtype=np.float32)
        faiss_lib.normalize_L2(pool_embeddings)

        query_embeddings = fuzzy_model.encode(query_texts, show_progress_bar=False, convert_to_numpy=True)
        query_embeddings = np.ascontiguousarray(query_embeddings, dtype=np.float32)
        faiss_lib.normalize_L2(query_embeddings)

        # OPTIMIZATION: Use numpy for small pools, FAISS for large pools
        # Already normalized, so dot product = cosine similarity
        FAISS_THRESHOLD = 100

        if len(pool) < FAISS_THRESHOLD:
            # Direct numpy: scores matrix is (num_queries x pool_size)
            scores = query_embeddings @ pool_embeddings.T
            best_scores = scores.max(axis=1)  # Best score per query
        else:
            # FAISS batched search for large pools
            dim = pool_embeddings.shape[1]
            pool_index = faiss_lib.IndexFlatIP(dim)
            pool_index.add(pool_embeddings)
            distances, _ = pool_index.search(query_embeddings, 1)  # ALL queries at once
            best_scores = distances[:, 0]  # Flatten to 1D

        # Process results
        group_matched = 0
        group_not_found = 0
        for qi, c in enumerate(corr_group):
            if best_scores[qi] >= fuzzy_threshold:
                matched.append(c)
                group_matched += 1
            else:
                not_found += 1
                group_not_found += 1
            processed += 1

        # Log group results
        if progress_callback and (processed % 10 == 0 or group_count <= 5):
            progress_callback(f"  -> matched={group_matched}, not_found={group_not_found}")

    logger.info(f"Fuzzy matching complete: {len(matched)} matched, {not_found} not found")

    # Phase 4: Final summary
    if progress_callback:
        progress_callback(f"[Phase 4/4] COMPLETE: {len(matched)} matched, {not_found} not found")
        if len(corrections) > 0:
            progress_callback(f"  - Match rate: {len(matched)/len(corrections)*100:.1f}%")

    return matched, not_found


def find_stringid_from_text(
    text: str,
    reverse_lookup: Dict[str, Dict[str, str]]
) -> Optional[Tuple[str, str]]:
    """
    Find StringID by searching all languages for the text.

    Args:
        text: Text to search for
        reverse_lookup: Dict from build_reverse_lookup()

    Returns:
        Tuple of (StringID, detected_lang_code) or None if not found
    """
    for lang_code, text_to_id in reverse_lookup.items():
        if text in text_to_id:
            return (text_to_id[text], lang_code)
    return None


def format_multiple_matches(translations: List[str]) -> str:
    """
    Format multiple matches as numbered list.

    Args:
        translations: List of translation strings

    Returns:
        Single value if one match, numbered list if multiple
    """
    translations = [t for t in translations if t and t.strip()]
    if not translations:
        return ""
    if len(translations) == 1:
        return translations[0]
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(translations))


def filter_by_categories(
    string_ids: List[str],
    stringid_to_category: Dict[str, str],
    include_categories: Optional[Set[str]] = None,
    exclude_categories: Optional[Set[str]] = None,
) -> List[str]:
    """
    Filter StringIDs by category inclusion/exclusion.

    Args:
        string_ids: List of StringIDs to filter
        stringid_to_category: Dict mapping StringID to category
        include_categories: If set, only include these categories
        exclude_categories: If set, exclude these categories

    Returns:
        Filtered list of StringIDs
    """
    result = []
    for string_id in string_ids:
        category = stringid_to_category.get(string_id, "Uncategorized")

        if include_categories and category not in include_categories:
            continue
        if exclude_categories and category in exclude_categories:
            continue

        result.append(string_id)

    return result
