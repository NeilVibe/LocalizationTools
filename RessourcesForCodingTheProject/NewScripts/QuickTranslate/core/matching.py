"""
Matching Algorithms.

All matching algorithms for QuickTranslate:
- Substring match (original, lookup only)
- StringID-only (SCRIPT strings)
- Strict (StringID + StrOrigin, with optional fuzzy StrOrigin)
- Quadruple fallback (StrOrigin + filename + adjacency cascade)
- Special key match (legacy)
- Reverse lookup (text -> StringID)
"""

import hashlib
import logging
from typing import Dict, List, Optional, Set, Tuple

import config
from .text_utils import normalize_for_matching

logger = logging.getLogger(__name__)

# SCRIPT categories - imported from config for single source of truth
SCRIPT_CATEGORIES = config.SCRIPT_CATEGORIES


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
) -> Tuple[List[Dict], int]:
    """
    Filter corrections to SCRIPT-only and match by StringID.

    For SCRIPT strings from export/Dialog/ and export/Sequencer/ folders,
    StrOrigin is just the raw KOR text, so StringID is sufficient for matching.

    Args:
        corrections: List of correction dicts with "string_id" key
        stringid_to_category: Dict mapping StringID to category (folder) name

    Returns:
        Tuple of (script_corrections, skipped_count)
    """
    script_corrections = []
    skipped = 0

    for c in corrections:
        string_id = c.get("string_id", "")
        category = stringid_to_category.get(string_id, "Uncategorized")

        if category in SCRIPT_CATEGORIES:
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


def _compute_adjacency_hash(before: str, after: str) -> str:
    """Compute 8-char hex hash of adjacent StrOrigin values."""
    raw = f"{before}|{after}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]


def find_matches_quadruple_fallback(
    corrections: List[Dict],
    level1_index: Dict[tuple, List[dict]],
    level2a_index: Dict[tuple, List[dict]],
    level2b_index: Dict[tuple, List[dict]],
    level3_index: Dict[str, List[dict]],
    source_has_context: bool = True,
    use_fuzzy: bool = False,
    fuzzy_model=None,
    fuzzy_threshold: float = 0.85,
    fuzzy_texts: Optional[List[str]] = None,
    fuzzy_entries: Optional[List[dict]] = None,
    fuzzy_index=None,
) -> Tuple[List[Dict], int, Dict[str, int]]:
    """
    Match corrections using 4-level quadruple fallback cascade.

    Tries each level in order for every correction:
    - L1  (HIGH confidence):        StrOrigin + file_relpath + adjacency_hash
    - L2A (MEDIUM-HIGH confidence): StrOrigin + file_relpath
    - L2B (MEDIUM confidence):      StrOrigin + adjacency_hash
    - L3  (LOW confidence):         StrOrigin only

    When source lacks file/adjacency context (e.g. Excel source),
    goes straight to L3.

    When use_fuzzy=True, StrOrigin comparison uses SBERT similarity instead
    of exact matching. For each correction's str_origin, FAISS is searched
    for top-K candidates above threshold, then those candidates are filtered
    through the level criteria (file_relpath, adjacency_hash).

    Args:
        corrections: List of correction dicts with str_origin (and optionally
                     file_relpath, adjacent_before, adjacent_after)
        level1_index: Dict keyed by (norm_origin, file_relpath, adj_hash)
        level2a_index: Dict keyed by (norm_origin, file_relpath)
        level2b_index: Dict keyed by (norm_origin, adj_hash)
        level3_index: Dict keyed by norm_origin
        source_has_context: Whether corrections have file/adjacency info
        use_fuzzy: If True, use SBERT similarity instead of exact matching
        fuzzy_model: Loaded SentenceTransformer model (required if use_fuzzy)
        fuzzy_threshold: Minimum similarity score for fuzzy matching
        fuzzy_texts: Target StrOrigin texts for FAISS (required if use_fuzzy)
        fuzzy_entries: Target entry dicts for FAISS (required if use_fuzzy)
        fuzzy_index: Pre-built FAISS index (required if use_fuzzy)

    Returns:
        Tuple of (matched_corrections, not_found_count, level_counts)
        Each matched correction gets 'match_level' and 'matched_entry' added.
        level_counts: {"L1": N, "L2A": N, "L2B": N, "L3": N}
    """
    if use_fuzzy:
        return _quadruple_fallback_fuzzy(
            corrections, source_has_context,
            fuzzy_model, fuzzy_threshold, fuzzy_texts, fuzzy_entries, fuzzy_index,
        )

    matched = []
    not_found = 0
    level_counts = {"L1": 0, "L2A": 0, "L2B": 0, "L3": 0}

    for c in corrections:
        str_origin = c.get("str_origin", "").strip()
        if not str_origin:
            not_found += 1
            continue

        norm_origin = normalize_for_matching(str_origin)
        match_entry = None
        match_level = None

        if source_has_context:
            file_relpath = c.get("file_relpath", "")
            adj_before = c.get("adjacent_before", "")
            adj_after = c.get("adjacent_after", "")
            adj_hash = None

            if adj_before or adj_after:
                adj_hash = _compute_adjacency_hash(adj_before, adj_after)

            # Try L1: StrOrigin + file_relpath + adjacency_hash
            if file_relpath and adj_hash:
                key1 = (norm_origin, file_relpath, adj_hash)
                entries = level1_index.get(key1, [])
                if entries:
                    match_entry = entries[0]
                    match_level = "L1"

            # Try L2A: StrOrigin + file_relpath
            if match_entry is None and file_relpath:
                key2a = (norm_origin, file_relpath)
                entries = level2a_index.get(key2a, [])
                if entries:
                    match_entry = entries[0]
                    match_level = "L2A"

            # Try L2B: StrOrigin + adjacency_hash
            if match_entry is None and adj_hash:
                key2b = (norm_origin, adj_hash)
                entries = level2b_index.get(key2b, [])
                if entries:
                    match_entry = entries[0]
                    match_level = "L2B"

        # Try L3: StrOrigin only (always available)
        if match_entry is None:
            entries = level3_index.get(norm_origin, [])
            if entries:
                match_entry = entries[0]
                match_level = "L3"

        if match_entry is not None:
            enriched = {
                **c,
                "match_level": match_level,
                "matched_string_id": match_entry["string_id"],
                "matched_str_origin": match_entry["str_origin"],
                "matched_source_file": match_entry.get("source_file", ""),
            }
            matched.append(enriched)
            level_counts[match_level] += 1
        else:
            not_found += 1

    return matched, not_found, level_counts


def _quadruple_fallback_fuzzy(
    corrections: List[Dict],
    source_has_context: bool,
    model,
    threshold: float,
    texts: List[str],
    entries: List[dict],
    index,
) -> Tuple[List[Dict], int, Dict[str, int]]:
    """
    Quadruple Fallback with SBERT fuzzy StrOrigin matching.

    Instead of exact StrOrigin lookup via index keys, this encodes each
    correction's str_origin with the SBERT model, searches FAISS for the
    top-K candidates above threshold, then filters those candidates through
    the level criteria (file_relpath, adjacency_hash).

    The cascade becomes:
    1. Get FAISS candidates above threshold for this correction's str_origin
    2. Among those candidates: any with matching file_relpath AND adj_hash? -> L1
    3. Among those candidates: any with matching file_relpath? -> L2A
    4. Among those candidates: any with matching adj_hash? -> L2B
    5. Among those candidates: take best score match -> L3

    Args:
        corrections: List of correction dicts
        source_has_context: Whether corrections have file/adjacency info
        model: Loaded SentenceTransformer model
        threshold: Minimum similarity score
        texts: Target StrOrigin texts (parallel to entries)
        entries: Target entry dicts (parallel to texts)
        index: Pre-built FAISS index

    Returns:
        Tuple of (matched_corrections, not_found_count, level_counts)
    """
    import numpy as np
    import faiss as faiss_lib

    matched = []
    not_found = 0
    level_counts = {"L1": 0, "L2A": 0, "L2B": 0, "L3": 0}

    k = 10  # Search top-K candidates per query
    total = len(corrections)

    for ci, c in enumerate(corrections):
        str_origin = c.get("str_origin", "").strip()
        if not str_origin:
            not_found += 1
            continue

        if ci % 100 == 0:
            logger.info(f"Fuzzy quadruple fallback: {ci+1}/{total}")

        # Encode query and search FAISS
        query_embedding = model.encode([str_origin], convert_to_numpy=True)
        query_embedding = np.ascontiguousarray(query_embedding, dtype=np.float32)
        faiss_lib.normalize_L2(query_embedding)

        distances, indices_arr = index.search(query_embedding, k)

        # Collect candidates above threshold, sorted by score (descending)
        candidates = []
        for score, idx in zip(distances[0], indices_arr[0]):
            if idx < 0 or idx >= len(entries):
                continue
            if score >= threshold:
                candidates.append((entries[idx], float(score)))

        if not candidates:
            not_found += 1
            continue

        match_entry = None
        match_level = None

        if source_has_context:
            file_relpath = c.get("file_relpath", "")
            adj_before = c.get("adjacent_before", "")
            adj_after = c.get("adjacent_after", "")
            adj_hash = None
            if adj_before or adj_after:
                adj_hash = _compute_adjacency_hash(adj_before, adj_after)

            # L1: candidate with matching file_relpath AND adj_hash
            if file_relpath and adj_hash:
                for entry, score in candidates:
                    cand_adj_hash = entry.get("adjacency_hash", "")
                    cand_relpath = entry.get("file_relpath", "")
                    if cand_relpath == file_relpath and cand_adj_hash == adj_hash:
                        match_entry = entry
                        match_level = "L1"
                        break

            # L2A: candidate with matching file_relpath
            if match_entry is None and file_relpath:
                for entry, score in candidates:
                    cand_relpath = entry.get("file_relpath", "")
                    if cand_relpath == file_relpath:
                        match_entry = entry
                        match_level = "L2A"
                        break

            # L2B: candidate with matching adj_hash
            if match_entry is None and adj_hash:
                for entry, score in candidates:
                    cand_adj_hash = entry.get("adjacency_hash", "")
                    if cand_adj_hash == adj_hash:
                        match_entry = entry
                        match_level = "L2B"
                        break

        # L3: best score candidate (first in list, already sorted)
        if match_entry is None:
            match_entry = candidates[0][0]
            match_level = "L3"

        enriched = {
            **c,
            "match_level": match_level,
            "matched_string_id": match_entry["string_id"],
            "matched_str_origin": match_entry["str_origin"],
            "matched_source_file": match_entry.get("source_file", ""),
        }
        matched.append(enriched)
        level_counts[match_level] += 1

    return matched, not_found, level_counts


def find_matches_strict_fuzzy(
    corrections: List[Dict],
    xml_entries: Dict[Tuple[str, str], dict],
    fuzzy_model,
    fuzzy_index,
    fuzzy_texts: List[str],
    fuzzy_entries: List[dict],
    fuzzy_threshold: float = 0.85,
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
    for entry in fuzzy_entries:
        sid = entry.get("string_id", "")
        if sid:
            stringid_to_entries[sid].append(entry)

    logger.info(f"Built StringID pool index: {len(stringid_to_entries)} unique StringIDs")

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

    if not need_fuzzy_by_stringid:
        return matched, not_found

    # Process each StringID group: encode pool ONCE, then batch match all queries
    processed = 0
    for string_id, corr_group in need_fuzzy_by_stringid.items():
        pool = stringid_to_entries[string_id]

        if processed % 100 == 0 and processed > 0:
            logger.info(f"Fuzzy matching: {processed}/{total_need_fuzzy} processed")

        # Encode pool once for this StringID
        pool_texts = [e.get("str_origin", "") for e in pool]

        # Batch encode all queries for this StringID
        query_texts = [c.get("str_origin", "").strip() for c in corr_group]

        # Standard FAISS workflow on the StringID pool (like KRSIMILAR):
        # 1. Encode pool texts
        # 2. Normalize with faiss.normalize_L2
        # 3. Build FAISS index from pool
        # 4. Encode queries, normalize
        # 5. Search the pool index

        # Encode pool
        pool_embeddings = fuzzy_model.encode(pool_texts, show_progress_bar=False, convert_to_numpy=True)
        pool_embeddings = np.ascontiguousarray(pool_embeddings, dtype=np.float32)
        faiss_lib.normalize_L2(pool_embeddings)

        # Build FAISS index for this StringID's pool
        dim = pool_embeddings.shape[1]
        pool_index = faiss_lib.IndexFlatIP(dim)
        pool_index.add(pool_embeddings)

        # Encode queries
        query_embeddings = fuzzy_model.encode(query_texts, show_progress_bar=False, convert_to_numpy=True)
        query_embeddings = np.ascontiguousarray(query_embeddings, dtype=np.float32)
        faiss_lib.normalize_L2(query_embeddings)

        # Search pool index for each query
        for qi, c in enumerate(corr_group):
            query_emb = query_embeddings[qi:qi+1]
            distances, indices_arr = pool_index.search(query_emb, 1)  # Get best match

            best_score = distances[0][0]
            if best_score >= fuzzy_threshold:
                matched.append(c)
            else:
                not_found += 1
            processed += 1

    logger.info(f"Fuzzy matching complete: {len(matched)} matched, {not_found} not found")
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
