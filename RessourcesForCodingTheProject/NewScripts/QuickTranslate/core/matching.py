"""
Matching Algorithms.

All matching algorithms for QuickTranslate:
- Substring match (original)
- StringID-only (SCRIPT strings)
- Strict (StringID + StrOrigin)
- Special key match
- Reverse lookup (text -> StringID)
"""

from typing import Dict, List, Optional, Set, Tuple

import config
from .text_utils import normalize_for_matching

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
