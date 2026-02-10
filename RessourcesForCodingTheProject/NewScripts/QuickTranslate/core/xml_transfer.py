"""
XML Transfer - Merge corrections to target XML files.

Ported from LanguageDataExporter's locdev_merger.py.
Writes corrections back to XML files using STRICT or StringID-only matching.
"""

import os
import stat
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Try lxml first (more robust), fallback to standard library
try:
    from lxml import etree
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as etree
    USING_LXML = False

import config
from .text_utils import normalize_text, normalize_nospace, normalize_for_matching
from .korean_detection import is_korean_text
from .source_scanner import scan_source_for_languages

logger = logging.getLogger(__name__)

# Import from config (single source of truth)
SCRIPT_CATEGORIES = config.SCRIPT_CATEGORIES
SCRIPT_EXCLUDE_SUBFOLDERS = config.SCRIPT_EXCLUDE_SUBFOLDERS


def cleanup_empty_strorigin(xml_path: Path, dry_run: bool = False) -> int:
    """
    Post-process: clear Str on any element where StrOrigin is empty.

    Golden rule: if StrOrigin is empty, Str MUST be empty too.

    Args:
        xml_path: Path to XML file to clean up
        dry_run: If True, count but don't write

    Returns:
        Number of entries cleaned (Str cleared)
    """
    try:
        if USING_LXML:
            parser = etree.XMLParser(
                resolve_entities=False, load_dtd=False,
                no_network=True, recover=True,
            )
            tree = etree.parse(str(xml_path), parser)
            root = tree.getroot()
        else:
            tree = etree.parse(str(xml_path))
            root = tree.getroot()

        cleaned = 0
        locstr_tags = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']
        all_elements = []
        for tag in locstr_tags:
            all_elements.extend(root.iter(tag))

        for loc in all_elements:
            origin = (loc.get("StrOrigin") or loc.get("Strorigin") or
                      loc.get("strorigin") or loc.get("STRORIGIN") or "").strip()
            str_val = (loc.get("Str") or loc.get("str") or
                       loc.get("STR") or "").strip()

            if not origin and str_val:
                if not dry_run:
                    loc.set("Str", "")
                cleaned += 1

        if cleaned > 0 and not dry_run:
            try:
                current_mode = os.stat(xml_path).st_mode
                if not current_mode & stat.S_IWRITE:
                    os.chmod(xml_path, current_mode | stat.S_IWRITE)
            except Exception:
                pass

            if USING_LXML:
                tree.write(str(xml_path), encoding="utf-8", xml_declaration=False, pretty_print=True)
            else:
                tree.write(str(xml_path), encoding="utf-8", xml_declaration=False)
            logger.info(f"Cleaned {cleaned} entries with empty StrOrigin in {xml_path.name}")

        return cleaned
    except Exception as e:
        logger.error(f"Error cleaning empty StrOrigin in {xml_path}: {e}")
        return 0


def _convert_linebreaks_for_xml(txt: str) -> str:
    """
    Convert Excel linebreaks to XML linebreak format.

    Excel uses \\n (Alt+Enter) for line breaks in cells.
    The project's XML format uses <br/> for linebreaks
    (which lxml escapes to &lt;br/&gt; in attributes automatically).

    Also handles the case where Excel already contains &lt;br/&gt;
    (from XML copy-paste) — unescapes first to prevent double-escaping
    (&lt;br/&gt; → &amp;lt;br/&amp;gt;).

    Ported from LanguageDataExporter's locdev_merger.py.

    Args:
        txt: Text that may contain Excel linebreaks

    Returns:
        Text with linebreaks normalized to <br/> for XML storage
    """
    if not txt:
        return txt
    # Unescape HTML-escaped linebreak tags (prevents double-escaping by lxml)
    txt = txt.replace('&lt;br/&gt;', '<br/>')
    txt = txt.replace('&lt;br /&gt;', '<br/>')
    # Replace actual newlines (from Excel Alt+Enter)
    txt = txt.replace('\n', '<br/>')
    # Replace escaped newlines (\\n literal string, rare but handle for robustness)
    txt = txt.replace('\\n', '<br/>')
    return txt


def merge_corrections_to_xml(
    xml_path: Path,
    corrections: List[Dict],
    dry_run: bool = False,
    only_untranslated: bool = False,
) -> Dict:
    """
    Merge corrections into a target XML file.

    Uses STRICT matching: (StringID, normalized_StrOrigin) tuple key.
    Both must match for the correction to be applied.

    Args:
        xml_path: Path to target XML file
        corrections: List of correction dicts with string_id, str_origin, corrected
        dry_run: If True, don't write changes, just return stats

    Returns:
        Dict with stats: matched, updated, not_found, errors, by_category
    """
    result = {
        "matched": 0,
        "updated": 0,
        "not_found": 0,
        "strorigin_mismatch": 0,  # StringID exists but StrOrigin differs
        "skipped_translated": 0,
        "errors": [],
        "by_category": {},
        "details": [],  # List of {string_id, status, old, new}
    }

    if not corrections:
        return result

    # Build lookup: (StringID, normalized_StrOrigin) -> (corrected_text, category, index)
    correction_lookup = {}
    correction_lookup_nospace = {}  # Fallback for whitespace variations
    correction_matched = [False] * len(corrections)

    for i, c in enumerate(corrections):
        sid_lower = c["string_id"].lower()
        origin_norm = normalize_text(c.get("str_origin", ""))
        origin_nospace = normalize_nospace(origin_norm)
        category = c.get("category", "Uncategorized")

        correction_lookup[(sid_lower, origin_norm)] = (c["corrected"], category, i)
        correction_lookup_nospace[(sid_lower, origin_nospace)] = (c["corrected"], category, i)

    # Initialize category stats
    categories_seen = set(c.get("category", "Uncategorized") for c in corrections)
    for cat in categories_seen:
        result["by_category"][cat] = {"matched": 0, "updated": 0, "not_found": 0}

    try:
        if USING_LXML:
            # Parse XML with recovery mode
            parser = etree.XMLParser(
                resolve_entities=False,
                load_dtd=False,
                no_network=True,
                recover=True,
            )
            tree = etree.parse(str(xml_path), parser)
            root = tree.getroot()
        else:
            tree = etree.parse(str(xml_path))
            root = tree.getroot()

        changed = False

        # Case-insensitive LocStr tag search - collect ALL variants
        locstr_tags = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']
        all_elements = []
        for tag in locstr_tags:
            all_elements.extend(root.iter(tag))
        # No break - collect all tag case variants

        # Build set of all StringIDs in target for diagnostic purposes
        # (to distinguish "StringID not found" vs "StrOrigin mismatch")
        target_stringids = set()
        for loc in all_elements:
            tsid = (loc.get("StringId") or loc.get("StringID") or
                    loc.get("stringid") or loc.get("STRINGID") or
                    loc.get("Stringid") or loc.get("stringId") or "").strip()
            if tsid:
                target_stringids.add(tsid.lower())

        for loc in all_elements:
            # Case-insensitive attribute access
            sid = (loc.get("StringId") or loc.get("StringID") or
                   loc.get("stringid") or loc.get("STRINGID") or
                   loc.get("Stringid") or loc.get("stringId") or "").strip()
            orig_raw = (loc.get("StrOrigin") or loc.get("Strorigin") or
                        loc.get("strorigin") or loc.get("STRORIGIN") or "")
            orig = normalize_text(orig_raw)

            # Golden rule: empty StrOrigin = never write Str
            if not orig.strip():
                continue

            orig_nospace = normalize_nospace(orig)
            sid_lower = sid.lower()
            key = (sid_lower, orig)
            key_nospace = (sid_lower, orig_nospace)

            # Try exact match first, then nospace fallback
            match_data = None
            if key in correction_lookup:
                match_data = correction_lookup[key]
            elif key_nospace in correction_lookup_nospace:
                match_data = correction_lookup_nospace[key_nospace]
                logger.debug(f"Matched via nospace fallback: StringId={sid}")

            if match_data is not None:
                new_str, category, idx = match_data
                correction_matched[idx] = True
                result["matched"] += 1
                result["by_category"][category]["matched"] += 1

                # Get old value (case-insensitive)
                old_str = (loc.get("Str") or loc.get("str") or
                           loc.get("STR") or "")

                # Skip already-translated entries if only_untranslated mode
                if only_untranslated and old_str and not is_korean_text(old_str):
                    result["skipped_translated"] += 1
                    # Preserve original correction data for failure reports
                    orig_correction = corrections[idx]
                    result["details"].append({
                        "string_id": sid,
                        "status": "SKIPPED_TRANSLATED",
                        "old": orig_correction.get("str_origin", ""),
                        "new": orig_correction.get("corrected", ""),
                        "raw_attribs": orig_correction.get("raw_attribs", {}),
                    })
                    continue

                # Convert Excel linebreaks to XML format before comparison/write
                new_str = _convert_linebreaks_for_xml(new_str)

                if new_str != old_str:
                    if not dry_run:
                        loc.set("Str", new_str)
                    result["updated"] += 1
                    result["by_category"][category]["updated"] += 1
                    changed = True
                    result["details"].append({
                        "string_id": sid,
                        "status": "UPDATED",
                        "old": old_str,
                        "new": new_str,
                    })
                    logger.debug(f"Updated StringId={sid}: '{old_str}' -> '{new_str}'")
                else:
                    result["details"].append({
                        "string_id": sid,
                        "status": "UNCHANGED",
                        "old": old_str,
                        "new": "(same)",
                    })

        # Count corrections that didn't match - store FULL data for failure reports
        # Distinguish between "StringID not found" vs "StrOrigin mismatch"
        for i, c in enumerate(corrections):
            if not correction_matched[i]:
                category = c.get("category", "Uncategorized")
                result["by_category"][category]["not_found"] += 1

                # Check if StringID exists but StrOrigin differs
                sid = c["string_id"]
                if sid.lower() in target_stringids:
                    status = "STRORIGIN_MISMATCH"
                    result["strorigin_mismatch"] += 1
                else:
                    status = "NOT_FOUND"
                    result["not_found"] += 1

                result["details"].append({
                    "string_id": sid,
                    "status": status,
                    "old": c.get("str_origin", ""),
                    "new": c["corrected"],
                    "raw_attribs": c.get("raw_attribs", {}),  # ALL original attributes
                })

        if changed and not dry_run:
            # Make file writable if read-only
            try:
                current_mode = os.stat(xml_path).st_mode
                if not current_mode & stat.S_IWRITE:
                    os.chmod(xml_path, current_mode | stat.S_IWRITE)
                    logger.debug(f"Made {xml_path.name} writable")
            except Exception as e:
                logger.warning(f"Could not make {xml_path.name} writable: {e}")

            if USING_LXML:
                tree.write(str(xml_path), encoding="utf-8", xml_declaration=False, pretty_print=True)
            else:
                tree.write(str(xml_path), encoding="utf-8", xml_declaration=False)
            logger.info(f"Saved {xml_path.name}: {result['updated']} entries updated")

    except Exception as e:
        result["errors"].append(str(e))
        logger.error(f"Error merging to {xml_path}: {e}")

    return result


def merge_corrections_strorigin_only(
    xml_path: Path,
    corrections: List[Dict],
    dry_run: bool = False,
    only_untranslated: bool = True,
) -> Dict:
    """
    Merge corrections into a target XML using StrOrigin-only matching.

    SAFETY: only_untranslated defaults to True. Without StringID verification,
    overwriting existing translations is too dangerous. Only fills untranslated entries.

    Single XML parse, pure dict lookup by normalized StrOrigin.
    Applies each correction to ALL target entries with matching StrOrigin
    (fan-out to duplicates).

    Args:
        xml_path: Path to target XML file
        corrections: List of correction dicts with str_origin, corrected
        dry_run: If True, don't write changes
        only_untranslated: If True, skip entries that already have non-Korean Str

    Returns:
        Dict with stats: matched, updated, not_found, errors, details
    """
    result = {
        "matched": 0,
        "updated": 0,
        "not_found": 0,
        "skipped_translated": 0,
        "unique_corrections": 0,
        "unique_matched": 0,
        "duplicate_sources": 0,
        "errors": [],
        "details": [],
    }

    if not corrections:
        return result

    # Build lookup: normalized_StrOrigin -> (corrected_text, index)
    # Multiple corrections with the same StrOrigin: last one wins
    correction_lookup = {}
    correction_lookup_nospace = {}
    correction_matched = [False] * len(corrections)
    conflicting = 0

    skipped_empty = 0
    for i, c in enumerate(corrections):
        origin_norm = normalize_for_matching(c.get("str_origin", ""))

        # Guard: skip corrections with empty StrOrigin (would false-match any empty target)
        if not origin_norm:
            skipped_empty += 1
            logger.warning(
                f"Skipping correction #{i} with empty StrOrigin "
                f"(StringID={c.get('string_id', '?')})"
            )
            continue

        origin_nospace = normalize_nospace(origin_norm)

        if origin_norm in correction_lookup:
            old_c_idx = correction_lookup[origin_norm][1]
            old_corrected = corrections[old_c_idx].get("corrected", "")
            if old_corrected != c.get("corrected", ""):
                conflicting += 1
                logger.debug(
                    f"Duplicate StrOrigin '{origin_norm[:50]}': overwriting "
                    f"'{old_corrected[:40]}' with '{c.get('corrected', '')[:40]}'"
                )

        correction_lookup[origin_norm] = (c["corrected"], i)
        correction_lookup_nospace[origin_nospace] = (c["corrected"], i)

    if skipped_empty:
        logger.warning(f"Skipped {skipped_empty} corrections with empty StrOrigin")

    result["unique_corrections"] = len(correction_lookup)
    result["duplicate_sources"] = conflicting
    if conflicting > 0:
        logger.info(
            f"{len(corrections)} source rows -> {len(correction_lookup)} unique StrOrigin values "
            f"({conflicting} had multiple translations, using latest)"
        )

    try:
        if USING_LXML:
            parser = etree.XMLParser(
                resolve_entities=False, load_dtd=False,
                no_network=True, recover=True,
            )
            tree = etree.parse(str(xml_path), parser)
            root = tree.getroot()
        else:
            tree = etree.parse(str(xml_path))
            root = tree.getroot()

        changed = False

        locstr_tags = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']
        all_elements = []
        for tag in locstr_tags:
            all_elements.extend(root.iter(tag))

        for loc in all_elements:
            sid = (loc.get("StringId") or loc.get("StringID") or
                   loc.get("stringid") or loc.get("STRINGID") or
                   loc.get("Stringid") or loc.get("stringId") or "").strip()
            orig_raw = (loc.get("StrOrigin") or loc.get("Strorigin") or
                        loc.get("strorigin") or loc.get("STRORIGIN") or "")
            orig = normalize_for_matching(orig_raw)

            # Golden rule: empty StrOrigin = never write Str
            if not orig.strip():
                continue

            orig_nospace = normalize_nospace(orig)

            # Try exact match first, then nospace fallback
            match_data = None
            if orig in correction_lookup:
                match_data = correction_lookup[orig]
            elif orig_nospace in correction_lookup_nospace:
                match_data = correction_lookup_nospace[orig_nospace]

            if match_data is not None:
                new_str, idx = match_data
                correction_matched[idx] = True
                result["matched"] += 1

                old_str = (loc.get("Str") or loc.get("str") or
                           loc.get("STR") or "")

                if only_untranslated and old_str and not is_korean_text(old_str):
                    result["skipped_translated"] += 1
                    orig_correction = corrections[idx]
                    result["details"].append({
                        "string_id": sid,
                        "status": "SKIPPED_TRANSLATED",
                        "old": orig_correction.get("str_origin", ""),
                        "new": orig_correction.get("corrected", ""),
                        "raw_attribs": orig_correction.get("raw_attribs", {}),
                    })
                    continue

                new_str = _convert_linebreaks_for_xml(new_str)

                if new_str != old_str:
                    if not dry_run:
                        loc.set("Str", new_str)
                    result["updated"] += 1
                    changed = True
                    result["details"].append({
                        "string_id": sid,
                        "status": "UPDATED",
                        "old": old_str,
                        "new": new_str,
                    })
                else:
                    result["details"].append({
                        "string_id": sid,
                        "status": "UNCHANGED",
                        "old": old_str,
                        "new": "(same)",
                    })

        # Build set of StrOrigins that actually matched in target
        matched_origins = set()
        for i, matched in enumerate(correction_matched):
            if matched:
                matched_origins.add(
                    normalize_for_matching(corrections[i].get("str_origin", ""))
                )

        # Count NOT_FOUND vs DUPLICATE (source entries whose StrOrigin was
        # already handled by another correction with the same StrOrigin)
        result["unique_matched"] = len(matched_origins)
        result["duplicates_in_source"] = 0

        for i, c in enumerate(corrections):
            if not correction_matched[i]:
                origin_norm = normalize_for_matching(c.get("str_origin", ""))
                # Skip empty StrOrigin (already logged as skipped_empty above)
                if not origin_norm:
                    continue
                if origin_norm in matched_origins:
                    # StrOrigin WAS matched — this is a source duplicate, not a failure
                    result["duplicates_in_source"] += 1
                else:
                    # StrOrigin truly not found in target
                    result["not_found"] += 1
                    result["details"].append({
                        "string_id": c.get("string_id", ""),
                        "status": "NOT_FOUND",
                        "old": c.get("str_origin", ""),
                        "new": c["corrected"],
                        "raw_attribs": c.get("raw_attribs", {}),
                    })

        if changed and not dry_run:
            try:
                current_mode = os.stat(xml_path).st_mode
                if not current_mode & stat.S_IWRITE:
                    os.chmod(xml_path, current_mode | stat.S_IWRITE)
            except Exception as e:
                logger.warning(f"Could not make {xml_path.name} writable: {e}")

            if USING_LXML:
                tree.write(str(xml_path), encoding="utf-8", xml_declaration=False, pretty_print=True)
            else:
                tree.write(str(xml_path), encoding="utf-8", xml_declaration=False)
            logger.info(f"Saved {xml_path.name}: {result['updated']} entries updated (StrOrigin-only)")

    except Exception as e:
        result["errors"].append(str(e))
        logger.error(f"Error merging (StrOrigin-only) to {xml_path}: {e}")

    return result


def merge_corrections_stringid_only(
    xml_path: Path,
    corrections: List[Dict],
    stringid_to_category: Dict[str, str],
    stringid_to_subfolder: Optional[Dict[str, str]] = None,
    dry_run: bool = False,
    only_untranslated: bool = False,
) -> Dict:
    """
    Merge corrections using StringID-ONLY matching.
    ONLY applies to SCRIPT TYPE strings (Dialog/Sequencer).

    This is useful when source text changed but StringID is still valid.
    Non-SCRIPT strings are skipped for safety.

    Args:
        xml_path: Path to target XML file
        corrections: List of correction dicts with string_id, corrected
        stringid_to_category: Pre-built StringID->Category mapping
        stringid_to_subfolder: Pre-built StringID->Subfolder mapping (for exclusions)
        dry_run: If True, don't write changes

    Returns:
        Dict with: matched, updated, skipped_non_script, skipped_excluded, not_found, errors
    """
    result = {
        "matched": 0,
        "updated": 0,
        "skipped_non_script": 0,
        "skipped_excluded": 0,
        "skipped_translated": 0,
        "not_found": 0,
        "errors": [],
        "by_category": {},
        "details": [],
    }

    if not corrections:
        return result

    # Build case-insensitive lookup versions of category/subfolder mappings
    # so StringIDs from any source (Excel, EventName resolver, XML) always match
    ci_category = {k.lower(): v for k, v in stringid_to_category.items()}
    ci_subfolder = {k.lower(): v for k, v in stringid_to_subfolder.items()} if stringid_to_subfolder else {}

    # Filter corrections to SCRIPT TYPE only (and not in excluded subfolders)
    script_corrections = []

    for c in corrections:
        sid = c["string_id"]
        sid_lower = sid.lower()
        category = ci_category.get(sid_lower, "Uncategorized")
        subfolder = ci_subfolder.get(sid_lower, "")

        # Check if in SCRIPT categories (Dialog/Sequencer)
        if category not in SCRIPT_CATEGORIES:
            result["skipped_non_script"] += 1
            result["details"].append({
                "string_id": sid,
                "status": "SKIPPED_NON_SCRIPT",
                "old": f"Category: {category}",
                "new": c["corrected"],
            })
            logger.debug(f"Skipped non-SCRIPT StringID={sid} (category={category})")
            continue

        # Check if subfolder is in exclusion list (case-insensitive)
        if subfolder.lower() in {s.lower() for s in SCRIPT_EXCLUDE_SUBFOLDERS}:
            result["skipped_excluded"] += 1
            result["details"].append({
                "string_id": sid,
                "status": "SKIPPED_EXCLUDED",
                "old": f"Subfolder: {subfolder}",
                "new": c["corrected"],
            })
            logger.debug(f"Skipped excluded subfolder StringID={sid} (subfolder={subfolder})")
            continue

        script_corrections.append({
            **c,
            "category": category,
        })

    if not script_corrections:
        logger.info(f"No SCRIPT corrections to apply to {xml_path.name}")
        return result

    # Build StringID-only lookup - store full correction for failure reports
    correction_lookup = {}
    correction_matched = {}
    duplicate_stringids = 0

    for c in script_corrections:
        sid_lower = c["string_id"].lower()

        if sid_lower in correction_lookup:
            old_corrected = correction_lookup[sid_lower].get("corrected", "")
            if old_corrected != c.get("corrected", ""):
                duplicate_stringids += 1
                logger.debug(
                    f"Duplicate StringID '{c['string_id']}': overwriting "
                    f"'{old_corrected[:40]}' with '{c.get('corrected', '')[:40]}'"
                )

        correction_lookup[sid_lower] = c  # Store FULL correction dict (lowercase key)
        correction_matched[sid_lower] = False

        # Initialize category stats
        category = c.get("category", "Uncategorized")
        if category not in result["by_category"]:
            result["by_category"][category] = {"matched": 0, "updated": 0, "not_found": 0}

    result["duplicate_sources"] = duplicate_stringids
    if duplicate_stringids > 0:
        logger.info(
            f"{len(script_corrections)} SCRIPT corrections -> {len(correction_lookup)} unique StringIDs "
            f"({duplicate_stringids} had conflicting translations, using latest)"
        )

    try:
        if USING_LXML:
            parser = etree.XMLParser(
                resolve_entities=False,
                load_dtd=False,
                no_network=True,
                recover=True,
            )
            tree = etree.parse(str(xml_path), parser)
            root = tree.getroot()
        else:
            tree = etree.parse(str(xml_path))
            root = tree.getroot()

        changed = False

        # Case-insensitive LocStr tag search - collect ALL variants
        locstr_tags = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']
        all_elements = []
        for tag in locstr_tags:
            all_elements.extend(root.iter(tag))
        # No break - collect all tag case variants

        for loc in all_elements:
            sid = (loc.get("StringId") or loc.get("StringID") or
                   loc.get("stringid") or loc.get("STRINGID") or
                   loc.get("Stringid") or loc.get("stringId") or "").strip()

            # Golden rule: empty StrOrigin = never write Str
            target_origin = (loc.get("StrOrigin") or loc.get("Strorigin") or
                             loc.get("strorigin") or loc.get("STRORIGIN") or "").strip()
            if not target_origin:
                continue

            # StringID-only matching (case-insensitive)
            sid_lower = sid.lower()
            if sid_lower in correction_lookup:
                new_str = correction_lookup[sid_lower]["corrected"]
                correction_matched[sid_lower] = True

                category = ci_category.get(sid_lower, "Uncategorized")

                result["matched"] += 1
                if category in result["by_category"]:
                    result["by_category"][category]["matched"] += 1

                old_str = (loc.get("Str") or loc.get("str") or
                           loc.get("STR") or "")

                # Skip already-translated entries if only_untranslated mode
                if only_untranslated and old_str and not is_korean_text(old_str):
                    result["skipped_translated"] += 1
                    # Preserve original correction data for failure reports
                    orig_correction = correction_lookup[sid_lower]
                    result["details"].append({
                        "string_id": sid,
                        "status": "SKIPPED_TRANSLATED",
                        "old": orig_correction.get("str_origin", ""),
                        "new": orig_correction.get("corrected", ""),
                        "raw_attribs": orig_correction.get("raw_attribs", {}),
                    })
                    continue

                # Convert Excel linebreaks to XML format before comparison/write
                new_str = _convert_linebreaks_for_xml(new_str)

                if new_str != old_str:
                    if not dry_run:
                        loc.set("Str", new_str)
                    result["updated"] += 1
                    if category in result["by_category"]:
                        result["by_category"][category]["updated"] += 1
                    changed = True
                    result["details"].append({
                        "string_id": sid,
                        "status": "UPDATED",
                        "old": old_str,
                        "new": new_str,
                    })
                    logger.debug(f"Updated StringId={sid}: '{old_str}' -> '{new_str}'")
                else:
                    result["details"].append({
                        "string_id": sid,
                        "status": "UNCHANGED",
                        "old": old_str,
                        "new": "(same)",
                    })

        # Count unmatched corrections - store FULL data for failure reports
        for sid_key, matched in correction_matched.items():
            if not matched:
                category = ci_category.get(sid_key, "Uncategorized")
                result["not_found"] += 1
                if category in result["by_category"]:
                    result["by_category"][category]["not_found"] += 1
                c = correction_lookup[sid_key]
                result["details"].append({
                    "string_id": sid,
                    "status": "NOT_FOUND",
                    "old": c.get("str_origin", ""),
                    "new": c["corrected"],
                    "raw_attribs": c.get("raw_attribs", {}),  # ALL original attributes
                })

        if changed and not dry_run:
            try:
                current_mode = os.stat(xml_path).st_mode
                if not current_mode & stat.S_IWRITE:
                    os.chmod(xml_path, current_mode | stat.S_IWRITE)
                    logger.debug(f"Made {xml_path.name} writable")
            except Exception as e:
                logger.warning(f"Could not make {xml_path.name} writable: {e}")

            if USING_LXML:
                tree.write(str(xml_path), encoding="utf-8", xml_declaration=False, pretty_print=True)
            else:
                tree.write(str(xml_path), encoding="utf-8", xml_declaration=False)
            logger.info(f"Saved {xml_path.name}: {result['updated']} entries updated (StringID-only)")

    except Exception as e:
        result["errors"].append(str(e))
        logger.error(f"Error merging to {xml_path}: {e}")

    return result


def merge_corrections_fuzzy(
    xml_path: Path,
    corrections: List[Dict],
    dry_run: bool = False,
    only_untranslated: bool = False,
) -> Dict:
    """
    Merge corrections using fuzzy-matched StringIDs.

    Each correction must have 'fuzzy_target_string_id' from fuzzy matching.
    Uses that StringID to find and update entries in the target XML.

    Args:
        xml_path: Path to target XML file
        corrections: List of correction dicts with fuzzy_target_string_id and corrected
        dry_run: If True, don't write changes

    Returns:
        Dict with stats: matched, updated, not_found, errors, details
    """
    result = {
        "matched": 0,
        "updated": 0,
        "not_found": 0,
        "skipped_translated": 0,
        "errors": [],
        "details": [],
    }

    if not corrections:
        return result

    # Build lookup: fuzzy_target_string_id -> full correction dict
    correction_lookup = {}
    correction_matched = {}

    for c in corrections:
        target_sid = c.get("fuzzy_target_string_id", "")
        if target_sid:
            correction_lookup[target_sid.lower()] = c  # Store FULL correction dict (lowercase key)
            correction_matched[target_sid.lower()] = False

    if not correction_lookup:
        result["errors"].append("No corrections with fuzzy_target_string_id found")
        return result

    try:
        if USING_LXML:
            parser = etree.XMLParser(
                resolve_entities=False, load_dtd=False,
                no_network=True, recover=True,
            )
            tree = etree.parse(str(xml_path), parser)
            root = tree.getroot()
        else:
            tree = etree.parse(str(xml_path))
            root = tree.getroot()

        changed = False

        locstr_tags = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']
        all_elements = []
        for tag in locstr_tags:
            all_elements.extend(root.iter(tag))

        for loc in all_elements:
            # Golden rule: empty StrOrigin = never write Str
            target_origin = (loc.get("StrOrigin") or loc.get("Strorigin") or
                             loc.get("strorigin") or loc.get("STRORIGIN") or "").strip()
            if not target_origin:
                continue

            sid = (loc.get("StringId") or loc.get("StringID") or
                   loc.get("stringid") or loc.get("STRINGID") or
                   loc.get("Stringid") or loc.get("stringId") or "").strip()

            sid_lower = sid.lower()
            if sid_lower in correction_lookup:
                c = correction_lookup[sid_lower]
                new_str = c["corrected"]
                correction_matched[sid_lower] = True
                result["matched"] += 1

                old_str = (loc.get("Str") or loc.get("str") or
                           loc.get("STR") or "")

                # Skip already-translated entries if only_untranslated mode
                if only_untranslated and old_str and not is_korean_text(old_str):
                    result["skipped_translated"] += 1
                    # Preserve original correction data for failure reports
                    result["details"].append({
                        "string_id": sid,
                        "status": "SKIPPED_TRANSLATED (fuzzy)",
                        "old": c.get("str_origin", ""),
                        "new": c.get("corrected", ""),
                        "raw_attribs": c.get("raw_attribs", {}),
                    })
                    continue

                # Convert Excel linebreaks to XML format before comparison/write
                new_str = _convert_linebreaks_for_xml(new_str)

                if new_str != old_str:
                    if not dry_run:
                        loc.set("Str", new_str)
                    result["updated"] += 1
                    changed = True
                    result["details"].append({
                        "string_id": sid,
                        "status": "UPDATED (fuzzy)",
                        "old": old_str,
                        "new": new_str,
                    })
                    logger.debug(f"Updated (fuzzy) StringId={sid}: '{old_str}' -> '{new_str}'")
                else:
                    result["details"].append({
                        "string_id": sid,
                        "status": "UNCHANGED (fuzzy)",
                        "old": old_str,
                        "new": "(same)",
                    })

        # Count unmatched - store FULL data for failure reports
        for sid, was_matched in correction_matched.items():
            if not was_matched:
                result["not_found"] += 1
                c = correction_lookup[sid]
                result["details"].append({
                    "string_id": sid,
                    "status": "NOT_FOUND",
                    "old": c.get("str_origin", ""),
                    "new": c["corrected"],
                    "raw_attribs": c.get("raw_attribs", {}),  # ALL original attributes
                })

        if changed and not dry_run:
            try:
                current_mode = os.stat(xml_path).st_mode
                if not current_mode & stat.S_IWRITE:
                    os.chmod(xml_path, current_mode | stat.S_IWRITE)
            except Exception as e:
                logger.warning(f"Could not make {xml_path.name} writable: {e}")

            if USING_LXML:
                tree.write(str(xml_path), encoding="utf-8", xml_declaration=False, pretty_print=True)
            else:
                tree.write(str(xml_path), encoding="utf-8", xml_declaration=False)
            logger.info(f"Saved {xml_path.name}: {result['updated']} entries updated (fuzzy)")

    except Exception as e:
        result["errors"].append(str(e))
        logger.error(f"Error merging (fuzzy) to {xml_path}: {e}")

    return result


def _prematch_fuzzy(
    corrections: List[Dict],
    fuzzy_model,
    fuzzy_index,
    fuzzy_texts: List[str],
    fuzzy_entries: List[dict],
    threshold: float = None,
    progress_callback=None,
) -> List[Dict]:
    """
    Pre-match corrections using FAISS fuzzy search.

    This is the ORIGINAL fuzzy pre-match logic restored:
    - Each correction's StrOrigin is encoded by SBERT
    - Searched against the full FAISS index for best semantic match
    - Returns enriched corrections with fuzzy_target_string_id

    Args:
        corrections: Unconsumed corrections from Step 1 (perfect match)
        fuzzy_model: Loaded SentenceTransformer model
        fuzzy_index: Built FAISS index
        fuzzy_texts: StrOrigin texts in the FAISS index
        fuzzy_entries: Entry dicts corresponding to index vectors
        threshold: Similarity threshold (0.0-1.0)
        progress_callback: Optional callback

    Returns:
        List of enriched correction dicts with fuzzy_target_string_id
    """
    from .fuzzy_matching import find_matches_fuzzy

    if threshold is None:
        threshold = config.FUZZY_THRESHOLD_DEFAULT

    try:
        matched, unmatched, stats = find_matches_fuzzy(
            corrections, fuzzy_texts, fuzzy_entries,
            fuzzy_model, fuzzy_index, threshold, progress_callback,
        )
        return matched
    except Exception as e:
        logger.error(f"FAISS fuzzy pre-match failed: {e}")
        return []


def transfer_folder_to_folder(
    source_folder: Path,
    target_folder: Path,
    stringid_to_category: Optional[Dict[str, str]] = None,
    stringid_to_subfolder: Optional[Dict[str, str]] = None,
    match_mode: str = "strict",
    dry_run: bool = False,
    progress_callback=None,
    threshold: float = None,
    only_untranslated: bool = False,
    # Pre-built fuzzy data (CRITICAL: avoid rebuilding full index!)
    fuzzy_model=None,
    fuzzy_index=None,
    fuzzy_texts: Optional[List[str]] = None,
    fuzzy_entries: Optional[List[dict]] = None,
    source_stringids: Optional[set] = None,
) -> Dict:
    """
    Transfer corrections from source folder to target folder.

    Matches files by name pattern: languagedata_*.xml

    For strict_fuzzy modes, indexes are built ONCE before the per-file
    loop and reused for every source file (avoids redundant rescans).

    Args:
        source_folder: Folder containing correction XML/Excel files
        target_folder: Folder containing target XML files to update
        stringid_to_category: Category mapping (required for stringid_only mode)
        stringid_to_subfolder: Subfolder mapping (for exclusion filtering)
        match_mode: "strict", "strict_fuzzy", "stringid_only",
                    "strorigin_only", or "strorigin_only_fuzzy"
        dry_run: If True, don't write changes
        progress_callback: Optional callback for progress updates
        threshold: Similarity threshold for fuzzy modes (defaults to config.FUZZY_THRESHOLD_DEFAULT)

    Returns:
        Dict with overall results
    """
    from .excel_io import read_corrections_from_excel

    results = {
        "files_processed": 0,
        "total_corrections": 0,
        "total_matched": 0,
        "total_updated": 0,
        "total_not_found": 0,
        "total_strorigin_mismatch": 0,  # StringID exists but StrOrigin differs
        "total_skipped": 0,
        "total_skipped_excluded": 0,
        "total_skipped_translated": 0,
        "errors": [],
        "file_results": {},
    }

    if not source_folder.exists():
        results["errors"].append(f"Source folder not found: {source_folder}")
        return results

    if not target_folder.exists():
        results["errors"].append(f"Target folder not found: {target_folder}")
        return results

    # Find source files using smart scanner (recursive, language-aware)
    # This matches what validation/tree display uses
    scan_result = scan_source_for_languages(source_folder)

    # Build file->language mapping (preserves language info from folder names)
    file_to_lang = {}  # {Path: lang_code}
    all_sources = []
    for lang, files in scan_result.lang_files.items():
        for f in files:
            file_to_lang[f] = lang
            all_sources.append(f)

    # Also add any unrecognized files (direct XML/Excel in source folder)
    for item in scan_result.unrecognized:
        if item.is_file() and item.suffix.lower() in (".xml", ".xlsx", ".xls"):
            all_sources.append(item)
            # For unrecognized, try to extract from filename
            file_to_lang[item] = None

    total = len(all_sources)

    if total == 0:
        results["errors"].append(f"No XML or Excel files found in {source_folder}")
        return results

    logger.info(f"Smart scanner found {total} files across {scan_result.language_count} languages")

    # ─── PRE-BUILD indexes ONCE before the per-file loop ───────────────
    # For strict_fuzzy modes, scanning the target folder and building
    # FAISS indexes is expensive.  Do it once, reuse for every source file.
    #
    # CRITICAL: If pre-built fuzzy data is passed (from GUI with filters),
    # USE IT instead of rebuilding from scratch!

    # Use pre-built fuzzy data if provided, otherwise initialize to None
    _fuzzy_model = fuzzy_model
    _fuzzy_texts = fuzzy_texts
    _fuzzy_entries = fuzzy_entries
    _fuzzy_index = fuzzy_index

    effective_threshold = threshold if threshold is not None else config.FUZZY_THRESHOLD_DEFAULT

    # Log whether we're using pre-built data
    if _fuzzy_entries is not None:
        logger.info(f"Using pre-built fuzzy data: {len(_fuzzy_entries):,} entries (filtered)")
    else:
        logger.info("No pre-built fuzzy data - will build from scratch if needed")

    # ─── CRITICAL: Extract ALL StringIDs from ALL source files FIRST ───
    # This filter ensures we don't load FULL languagedata (2.2M entries)!
    # Use pre-passed source_stringids if available, otherwise extract from source files.
    all_source_stringids = source_stringids  # May be None or pre-computed set from GUI
    if all_source_stringids is None and match_mode in ("strict_fuzzy", "strorigin_only_fuzzy"):
        from .xml_io import parse_corrections_from_xml
        from .excel_io import read_corrections_from_excel

        if progress_callback:
            progress_callback("Extracting StringIDs from all source files for filtering...")

        all_source_stringids = set()
        for src_file in all_sources:
            try:
                if src_file.suffix.lower() == ".xml":
                    corrs = parse_corrections_from_xml(src_file)
                else:
                    corrs = read_corrections_from_excel(src_file)
                for c in corrs:
                    sid = c.get("string_id", "")
                    if sid:
                        all_source_stringids.add(sid)
            except ValueError as e:
                logger.warning(f"Skipped {src_file.name} during StringID extraction: {e}")
                continue
            except Exception as e:
                logger.warning(f"Skipped {src_file.name} during StringID extraction: {e}")
                continue
        logger.info(f"Extracted {len(all_source_stringids):,} unique StringIDs from {len(all_sources)} source files")

    if match_mode in ("strict_fuzzy", "strorigin_only_fuzzy"):
        # 2-pass fuzzy: Step 1 = exact match, Step 2 = FAISS fuzzy on unconsumed
        # Needs model + FAISS index for Step 2
        if _fuzzy_entries is not None and _fuzzy_model is not None and _fuzzy_index is not None:
            logger.info(f"Using pre-built FAISS index for {match_mode}")
        else:
            from .fuzzy_matching import load_model, build_index_from_folder, build_faiss_index

            if progress_callback:
                progress_callback(f"Loading model and building FAISS index for {match_mode}...")
            try:
                _fuzzy_model = load_model(progress_callback)
                _fuzzy_texts, _fuzzy_entries = build_index_from_folder(
                    target_folder, progress_callback,
                    stringid_filter=all_source_stringids
                )
                if _fuzzy_texts:
                    _fuzzy_index = build_faiss_index(
                        _fuzzy_texts, _fuzzy_entries, _fuzzy_model, progress_callback
                    )
                else:
                    logger.warning(f"No StrOrigin values in target folder: {target_folder}")
            except Exception as e:
                results["errors"].append(f"Failed to build FAISS index for {match_mode}: {e}")
                logger.error(f"Failed to build FAISS index for {match_mode}: {e}")

    # ─── Phase 1: Parse ALL source files and group by target XML ─────
    # Instead of one pass per source file, concatenate ALL corrections
    # for the same target language into ONE dataset for a SINGLE pass.

    from .xml_io import parse_corrections_from_xml

    # {target_xml_path: {"corrections": [...], "source_files": [...]}}
    target_groups = {}

    for i, source_file in enumerate(all_sources):
        if progress_callback:
            progress_callback(f"Parsing {source_file.name}... ({i+1}/{total})")

        # Parse corrections from source
        try:
            if source_file.suffix.lower() == ".xml":
                corrections = parse_corrections_from_xml(source_file)
            else:
                corrections = read_corrections_from_excel(source_file)
        except ValueError as e:
            logger.error(f"SKIPPED {source_file.name}: {e}")
            results["errors"].append(f"SKIPPED {source_file.name}: {e}")
            continue

        if not corrections:
            logger.info(f"No corrections found in {source_file.name}")
            continue

        # Get language code from scanner mapping (folder-based detection)
        lang_code = file_to_lang.get(source_file)
        if not lang_code:
            name = source_file.stem.lower()
            if name.startswith("languagedata_"):
                lang_code = name[13:]
            elif "_" in name:
                last_part = name.split("_")[-1]
                if 2 <= len(last_part) <= 6 or "-" in last_part:
                    lang_code = last_part

        # Find target XML
        target_xml = None
        if lang_code:
            candidates = [
                target_folder / f"languagedata_{lang_code}.xml",
                target_folder / f"languagedata_{lang_code.upper()}.xml",
                target_folder / f"languagedata_{lang_code.lower()}.xml",
            ]
            for c in candidates:
                if c.exists():
                    target_xml = c
                    break

        if not target_xml:
            target_xmls = list(target_folder.glob("*.xml"))
            if len(target_xmls) == 1:
                target_xml = target_xmls[0]
            elif lang_code:
                results["errors"].append(f"No target XML found for {source_file.name}")
                continue

        if not target_xml:
            results["errors"].append(f"No target XML found for {source_file.name}")
            continue

        # Group corrections by target XML
        target_key = str(target_xml)
        if target_key not in target_groups:
            target_groups[target_key] = {
                "target_xml": target_xml,
                "corrections": [],
                "source_files": [],
            }
        target_groups[target_key]["corrections"].extend(corrections)
        target_groups[target_key]["source_files"].append(source_file.name)
        logger.info(f"Parsed {source_file.name}: {len(corrections)} corrections → {target_xml.name}")

    logger.info(f"Grouped {sum(len(g['corrections']) for g in target_groups.values()):,} corrections "
                f"across {len(target_groups)} target files")

    # ─── EventName Resolution (between parse and merge) ───────────────
    # If any correction has _source_eventname, resolve via export__ mapping
    all_have_eventnames = any(
        c.get("_source_eventname")
        for g in target_groups.values()
        for c in g["corrections"]
    )
    all_missing_eventnames = []

    if all_have_eventnames:
        from .eventname_resolver import get_eventname_mapping, resolve_eventnames_in_corrections

        if progress_callback:
            progress_callback("Resolving EventNames to StringIDs...")

        en_mapping = get_eventname_mapping(config.EXPORT_FOLDER, progress_callback=progress_callback)

        if en_mapping:
            for target_key, group in target_groups.items():
                # Tag corrections with source file info for the missing report
                for c in group["corrections"]:
                    if c.get("_source_eventname") and not c.get("_source_file"):
                        c["_source_file"] = ", ".join(group["source_files"])

                resolved, missing = resolve_eventnames_in_corrections(
                    group["corrections"], en_mapping
                )
                group["corrections"] = resolved
                all_missing_eventnames.extend(missing)

            total_en = sum(
                1 for g in target_groups.values()
                for c in g["corrections"]
            ) + len(all_missing_eventnames)
            logger.info(
                f"EventName resolution complete: "
                f"{total_en - len(all_missing_eventnames)} resolved, "
                f"{len(all_missing_eventnames)} missing"
            )
        else:
            logger.warning("EventName mapping is empty — export folder may not contain SoundEventName attributes")

    # ─── Phase 2: ONE pass per target XML with ALL corrections ────────

    for ti, (target_key, group) in enumerate(target_groups.items()):
        target_xml = group["target_xml"]
        corrections = group["corrections"]
        source_names = group["source_files"]

        if progress_callback:
            progress_callback(f"Transferring to {target_xml.name}... ({ti+1}/{len(target_groups)})")

        logger.info(f"═══ {target_xml.name}: {len(corrections):,} corrections from {len(source_names)} files ═══")

        # Apply corrections based on match mode — ONE pass with ALL corrections
        if match_mode == "stringid_only" and stringid_to_category:
            file_result = merge_corrections_stringid_only(
                target_xml, corrections, stringid_to_category,
                stringid_to_subfolder, dry_run,
                only_untranslated=only_untranslated,
            )
            results["total_skipped"] += file_result.get("skipped_non_script", 0)
            results["total_skipped_excluded"] += file_result.get("skipped_excluded", 0)

        elif match_mode == "strict_fuzzy":
            # ═══ TWO-STEP PROCESS (single pass with ALL corrections) ═══
            # Step 1: Perfect match (exact StringID + exact StrOrigin)
            file_result = merge_corrections_to_xml(
                target_xml, corrections, dry_run,
                only_untranslated=only_untranslated,
            )
            step1_matched = file_result["matched"]
            logger.info(f"Step 1 (perfect): {step1_matched}/{len(corrections)} matched")

            # Step 2: FAISS fuzzy on UNCONSUMED corrections only
            if _fuzzy_model and _fuzzy_index and _fuzzy_texts and _fuzzy_entries:
                unconsumed = []
                for detail in file_result["details"]:
                    if detail["status"] in ("STRORIGIN_MISMATCH", "NOT_FOUND"):
                        unconsumed.append({
                            "string_id": detail["string_id"],
                            "str_origin": detail.get("old", ""),
                            "corrected": detail.get("new", ""),
                            "raw_attribs": detail.get("raw_attribs", {}),
                            "_original_status": detail["status"],
                        })

                if unconsumed:
                    from .fuzzy_matching import find_matches_fuzzy
                    logger.info(f"Step 2: FAISS fuzzy on {len(unconsumed)} unconsumed corrections")

                    fuzzy_matched, fuzzy_unmatched, fuzzy_stats = find_matches_fuzzy(
                        unconsumed, _fuzzy_texts, _fuzzy_entries,
                        _fuzzy_model, _fuzzy_index, effective_threshold,
                    )

                    if fuzzy_matched:
                        fuzzy_result = merge_corrections_fuzzy(
                            target_xml, fuzzy_matched, dry_run,
                            only_untranslated=only_untranslated,
                        )
                        file_result["matched"] += fuzzy_result["matched"]
                        file_result["updated"] += fuzzy_result["updated"]

                        # Bug 2 fix: Count by original status, not blanket subtract
                        fuzzy_from_not_found = sum(
                            1 for m in fuzzy_matched
                            if m.get("_original_status") == "NOT_FOUND"
                        )
                        fuzzy_from_mismatch = sum(
                            1 for m in fuzzy_matched
                            if m.get("_original_status") == "STRORIGIN_MISMATCH"
                        )
                        file_result["not_found"] = max(0, file_result.get("not_found", 0) - fuzzy_from_not_found)
                        if "strorigin_mismatch" in file_result:
                            file_result["strorigin_mismatch"] = max(0, file_result["strorigin_mismatch"] - fuzzy_from_mismatch)

                        # Bug 1 fix: Remove stale Step1 failures resolved by fuzzy
                        resolved_sids = {m["string_id"] for m in fuzzy_matched}
                        file_result["details"] = [
                            d for d in file_result["details"]
                            if not (d["status"] in ("NOT_FOUND", "STRORIGIN_MISMATCH") and d["string_id"] in resolved_sids)
                        ]

                        file_result["details"].extend(fuzzy_result["details"])
                        logger.info(
                            f"Step 2 (FAISS fuzzy): {fuzzy_result['matched']} additional matches "
                            f"({fuzzy_result['updated']} updated, avg_score={fuzzy_stats['avg_score']:.3f})"
                        )
                    else:
                        logger.info(f"Step 2: No fuzzy matches found for {len(unconsumed)} unconsumed")
                else:
                    logger.info("Step 2: All corrections matched in Step 1 (perfect match)")

        elif match_mode == "strorigin_only":
            # SAFETY: Default untranslated-only (GUI warns if user picks "ALL")
            file_result = merge_corrections_strorigin_only(
                target_xml, corrections, dry_run,
                only_untranslated=only_untranslated,
            )
        elif match_mode == "strorigin_only_fuzzy":
            # ═══ TWO-STEP: Exact StrOrigin first, then SBERT fuzzy on leftovers ═══
            # SAFETY: Default untranslated-only (GUI warns if user picks "ALL")
            file_result = merge_corrections_strorigin_only(
                target_xml, corrections, dry_run,
                only_untranslated=only_untranslated,
            )
            step1_matched = file_result["matched"]
            logger.info(f"Step 1 (StrOrigin exact): {step1_matched}/{len(corrections)} matched")

            if _fuzzy_model and _fuzzy_index and _fuzzy_texts and _fuzzy_entries:
                unconsumed = []
                for detail in file_result["details"]:
                    if detail["status"] == "NOT_FOUND":
                        unconsumed.append({
                            "string_id": detail.get("string_id", ""),
                            "str_origin": detail.get("old", ""),
                            "corrected": detail.get("new", ""),
                            "raw_attribs": detail.get("raw_attribs", {}),
                            "_original_status": detail["status"],
                        })

                if unconsumed:
                    from .fuzzy_matching import find_matches_fuzzy
                    logger.info(f"Step 2: FAISS fuzzy on {len(unconsumed)} unconsumed corrections")

                    fuzzy_matched, fuzzy_unmatched, fuzzy_stats = find_matches_fuzzy(
                        unconsumed, _fuzzy_texts, _fuzzy_entries,
                        _fuzzy_model, _fuzzy_index, effective_threshold,
                    )

                    if fuzzy_matched:
                        fuzzy_result = merge_corrections_fuzzy(
                            target_xml, fuzzy_matched, dry_run,
                            only_untranslated=only_untranslated,
                        )
                        file_result["matched"] += fuzzy_result["matched"]
                        file_result["updated"] += fuzzy_result["updated"]

                        fuzzy_from_not_found = sum(
                            1 for m in fuzzy_matched
                            if m.get("_original_status") == "NOT_FOUND"
                        )
                        file_result["not_found"] = max(0, file_result.get("not_found", 0) - fuzzy_from_not_found)

                        resolved_sids = {m.get("string_id", "") for m in fuzzy_matched}
                        file_result["details"] = [
                            d for d in file_result["details"]
                            if not (d["status"] == "NOT_FOUND" and d.get("string_id", "") in resolved_sids)
                        ]

                        file_result["details"].extend(fuzzy_result["details"])
                        logger.info(
                            f"Step 2 (FAISS fuzzy): {fuzzy_result['matched']} additional matches "
                            f"({fuzzy_result['updated']} updated, avg_score={fuzzy_stats['avg_score']:.3f})"
                        )
                    else:
                        logger.info(f"Step 2: No fuzzy matches found for {len(unconsumed)} unconsumed")
                else:
                    logger.info("Step 2: All corrections matched in Step 1 (StrOrigin exact)")
        else:
            file_result = merge_corrections_to_xml(
                target_xml, corrections, dry_run,
                only_untranslated=only_untranslated,
            )

        # Post-process: enforce empty StrOrigin = empty Str
        if not dry_run:
            cleaned = cleanup_empty_strorigin(target_xml)
            if cleaned > 0:
                logger.info(f"Post-process: cleared Str on {cleaned} entries with empty StrOrigin in {target_xml.name}")

        # Aggregate results
        results["files_processed"] += len(source_names)
        results["total_corrections"] += len(corrections)
        results["total_matched"] += file_result["matched"]
        results["total_updated"] += file_result["updated"]
        results["total_not_found"] += file_result.get("not_found", 0)
        results["total_strorigin_mismatch"] += file_result.get("strorigin_mismatch", 0)
        results["total_skipped_translated"] += file_result.get("skipped_translated", 0)
        results["errors"].extend(file_result["errors"])

        # Store result keyed by target name (since sources are concatenated)
        source_label = ", ".join(source_names)
        results["file_results"][target_xml.name] = {
            "target": target_xml.name,
            "source_files": source_names,
            "corrections": len(corrections),
            **file_result,
        }

        # Log per-target result
        updated = file_result["updated"]
        not_found = file_result.get("not_found", 0)
        skipped_tr = file_result.get("skipped_translated", 0)
        logger.info(
            f"[{source_label}] -> {target_xml.name}: "
            f"{updated} updated, {skipped_tr} skipped, {not_found} not found"
        )

    # ─── Missing EventName report (after all transfers complete) ──────
    if all_missing_eventnames:
        from .eventname_resolver import generate_missing_eventname_report
        from datetime import datetime

        results["missing_eventnames_count"] = len(all_missing_eventnames)
        report_dir = config.get_failed_report_dir(
            source_folder.name if source_folder.is_dir() else source_folder.stem
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"MissingEventNames_{timestamp}.xlsx"

        if generate_missing_eventname_report(all_missing_eventnames, report_path):
            results["missing_eventname_report"] = str(report_path)
            logger.info(f"Missing EventName report: {report_path}")

    return results


def transfer_file_to_file(
    source_file: Path,
    target_file: Path,
    stringid_to_category: Optional[Dict[str, str]] = None,
    stringid_to_subfolder: Optional[Dict[str, str]] = None,
    match_mode: str = "strict",
    dry_run: bool = False,
    threshold: float = None,
    only_untranslated: bool = False,
    fuzzy_model=None,
    fuzzy_index=None,
    fuzzy_texts: Optional[List[str]] = None,
    fuzzy_entries: Optional[List[dict]] = None,
) -> Dict:
    """
    Transfer corrections from single source file to single target file.

    For file mode there is only one source file, so pre-building and matching
    happen in sequence (no loop optimization needed).

    Args:
        source_file: Excel or XML file with corrections
        target_file: Target XML file to update
        stringid_to_category: Category mapping (required for stringid_only mode)
        stringid_to_subfolder: Subfolder mapping (for exclusion filtering)
        match_mode: "strict", "strict_fuzzy", "stringid_only",
                    "strorigin_only", or "strorigin_only_fuzzy"
        dry_run: If True, don't write changes
        threshold: Similarity threshold for fuzzy modes (defaults to config.FUZZY_THRESHOLD_DEFAULT)
        fuzzy_model: Pre-loaded SBERT model (optional, avoids reload)
        fuzzy_index: Pre-built FAISS index (optional, for fuzzy modes)
        fuzzy_texts: Pre-extracted StrOrigin texts (optional)
        fuzzy_entries: Pre-extracted entry dicts (optional)

    Returns:
        Dict with results
    """
    from .xml_io import parse_corrections_from_xml
    from .excel_io import read_corrections_from_excel

    # Parse corrections from source
    try:
        if source_file.suffix.lower() == ".xml":
            corrections = parse_corrections_from_xml(source_file)
        else:
            corrections = read_corrections_from_excel(source_file)
    except ValueError as e:
        return {
            "matched": 0,
            "updated": 0,
            "not_found": 0,
            "errors": [f"Column error: {e}"],
            "details": [],
        }

    if not corrections:
        return {
            "matched": 0,
            "updated": 0,
            "not_found": 0,
            "errors": ["No corrections found in source file"],
            "details": [],
        }

    # ─── EventName Resolution ─────────────────────────────────────────
    missing_eventnames = []
    has_eventnames = any(c.get("_source_eventname") for c in corrections)

    if has_eventnames:
        from .eventname_resolver import get_eventname_mapping, resolve_eventnames_in_corrections

        en_mapping = get_eventname_mapping(config.EXPORT_FOLDER)
        if en_mapping:
            for c in corrections:
                if c.get("_source_eventname") and not c.get("_source_file"):
                    c["_source_file"] = source_file.name
            corrections, missing_eventnames = resolve_eventnames_in_corrections(
                corrections, en_mapping
            )
        else:
            logger.warning("EventName mapping is empty — cannot resolve EventNames")

    # Apply corrections based on match mode
    if match_mode == "stringid_only" and stringid_to_category:
        result = merge_corrections_stringid_only(
            target_file, corrections, stringid_to_category,
            stringid_to_subfolder, dry_run,
            only_untranslated=only_untranslated,
        )
    elif match_mode == "strict_fuzzy":
        # ═══ TWO-STEP PROCESS ═══
        # Step 1: Perfect match (exact StringID + exact StrOrigin)
        result = merge_corrections_to_xml(
            target_file, corrections, dry_run,
            only_untranslated=only_untranslated,
        )
        step1_matched = result["matched"]
        logger.info(f"Step 1 (perfect): {step1_matched}/{len(corrections)} matched")

        # Step 2: FAISS fuzzy on UNCONSUMED corrections only
        target_folder = target_file.parent

        # Build FAISS index if not pre-built
        _fm = fuzzy_model
        _fi = fuzzy_index
        _ft = fuzzy_texts
        _fe = fuzzy_entries
        if _fm is None or _fi is None:
            from .fuzzy_matching import load_model, build_index_from_folder, build_faiss_index
            try:
                correction_stringids = {c.get("string_id", "") for c in corrections if c.get("string_id")}
                logger.info(f"File-to-file strict_fuzzy: building FAISS for {len(correction_stringids):,} StringIDs")
                _fm = _fm or load_model()
                _ft, _fe = build_index_from_folder(
                    target_folder, stringid_filter=correction_stringids
                )
                if _ft:
                    _fi = build_faiss_index(_ft, _fe, _fm)
            except Exception as e:
                logger.error(f"Failed to build FAISS index: {e}")
                _fi = None

        if _fm and _fi and _ft and _fe:
            # Collect unconsumed corrections
            unconsumed = []
            for detail in result["details"]:
                if detail["status"] in ("STRORIGIN_MISMATCH", "NOT_FOUND"):
                    unconsumed.append({
                        "string_id": detail["string_id"],
                        "str_origin": detail.get("old", ""),
                        "corrected": detail.get("new", ""),
                        "raw_attribs": detail.get("raw_attribs", {}),
                        "_original_status": detail["status"],
                    })

            if unconsumed:
                from .fuzzy_matching import find_matches_fuzzy
                effective_threshold = threshold if threshold is not None else config.FUZZY_THRESHOLD_DEFAULT
                logger.info(f"Step 2: FAISS fuzzy on {len(unconsumed)} unconsumed corrections")

                fuzzy_matched, fuzzy_unmatched, fuzzy_stats = find_matches_fuzzy(
                    unconsumed, _ft, _fe, _fm, _fi, effective_threshold,
                )

                if fuzzy_matched:
                    fuzzy_result = merge_corrections_fuzzy(
                        target_file, fuzzy_matched, dry_run,
                        only_untranslated=only_untranslated,
                    )
                    result["matched"] += fuzzy_result["matched"]
                    result["updated"] += fuzzy_result["updated"]

                    # Bug 2 fix: Count by original status, not blanket subtract
                    fuzzy_from_not_found = sum(
                        1 for m in fuzzy_matched
                        if m.get("_original_status") == "NOT_FOUND"
                    )
                    fuzzy_from_mismatch = sum(
                        1 for m in fuzzy_matched
                        if m.get("_original_status") == "STRORIGIN_MISMATCH"
                    )
                    result["not_found"] = max(0, result.get("not_found", 0) - fuzzy_from_not_found)
                    if "strorigin_mismatch" in result:
                        result["strorigin_mismatch"] = max(0, result["strorigin_mismatch"] - fuzzy_from_mismatch)

                    # Bug 1 fix: Remove stale Step1 failures resolved by fuzzy
                    resolved_sids = {m["string_id"] for m in fuzzy_matched}
                    result["details"] = [
                        d for d in result["details"]
                        if not (d["status"] in ("NOT_FOUND", "STRORIGIN_MISMATCH") and d["string_id"] in resolved_sids)
                    ]

                    result["details"].extend(fuzzy_result["details"])
                    logger.info(
                        f"Step 2 (FAISS fuzzy): {fuzzy_result['matched']} additional matches "
                        f"({fuzzy_result['updated']} updated)"
                    )
    elif match_mode == "strorigin_only":
        # SAFETY: Default untranslated-only (GUI warns if user picks "ALL")
        result = merge_corrections_strorigin_only(
            target_file, corrections, dry_run,
            only_untranslated=only_untranslated,
        )
    elif match_mode == "strorigin_only_fuzzy":
        # ═══ TWO-STEP: Exact StrOrigin first, then SBERT fuzzy on leftovers ═══
        # SAFETY: Default untranslated-only (GUI warns if user picks "ALL")
        result = merge_corrections_strorigin_only(
            target_file, corrections, dry_run,
            only_untranslated=only_untranslated,
        )
        step1_matched = result["matched"]
        logger.info(f"Step 1 (StrOrigin exact): {step1_matched}/{len(corrections)} matched")

        # Build FAISS index if not pre-built
        target_folder = target_file.parent
        _fm = fuzzy_model
        _fi = fuzzy_index
        _ft = fuzzy_texts
        _fe = fuzzy_entries
        if _fm is None or _fi is None:
            from .fuzzy_matching import load_model, build_index_from_folder, build_faiss_index
            try:
                correction_stringids = {c.get("string_id", "") for c in corrections if c.get("string_id")}
                logger.info(f"File-to-file strorigin_only_fuzzy: building FAISS for {len(correction_stringids):,} StringIDs")
                _fm = _fm or load_model()
                _ft, _fe = build_index_from_folder(
                    target_folder, stringid_filter=correction_stringids
                )
                if _ft:
                    _fi = build_faiss_index(_ft, _fe, _fm)
            except Exception as e:
                logger.error(f"Failed to build FAISS index: {e}")
                _fi = None

        if _fm and _fi and _ft and _fe:
            unconsumed = []
            for detail in result["details"]:
                if detail["status"] == "NOT_FOUND":
                    unconsumed.append({
                        "string_id": detail.get("string_id", ""),
                        "str_origin": detail.get("old", ""),
                        "corrected": detail.get("new", ""),
                        "raw_attribs": detail.get("raw_attribs", {}),
                        "_original_status": detail["status"],
                    })

            if unconsumed:
                from .fuzzy_matching import find_matches_fuzzy
                effective_threshold = threshold if threshold is not None else config.FUZZY_THRESHOLD_DEFAULT
                logger.info(f"Step 2: FAISS fuzzy on {len(unconsumed)} unconsumed corrections")

                fuzzy_matched, fuzzy_unmatched, fuzzy_stats = find_matches_fuzzy(
                    unconsumed, _ft, _fe, _fm, _fi, effective_threshold,
                )

                if fuzzy_matched:
                    fuzzy_result = merge_corrections_fuzzy(
                        target_file, fuzzy_matched, dry_run,
                        only_untranslated=only_untranslated,
                    )
                    result["matched"] += fuzzy_result["matched"]
                    result["updated"] += fuzzy_result["updated"]

                    fuzzy_from_not_found = sum(
                        1 for m in fuzzy_matched
                        if m.get("_original_status") == "NOT_FOUND"
                    )
                    result["not_found"] = max(0, result.get("not_found", 0) - fuzzy_from_not_found)

                    resolved_sids = {m.get("string_id", "") for m in fuzzy_matched}
                    result["details"] = [
                        d for d in result["details"]
                        if not (d["status"] == "NOT_FOUND" and d.get("string_id", "") in resolved_sids)
                    ]

                    result["details"].extend(fuzzy_result["details"])
                    logger.info(
                        f"Step 2 (FAISS fuzzy): {fuzzy_result['matched']} additional matches "
                        f"({fuzzy_result['updated']} updated, avg_score={fuzzy_stats['avg_score']:.3f})"
                    )
    else:
        result = merge_corrections_to_xml(
            target_file, corrections, dry_run,
            only_untranslated=only_untranslated,
        )

    # Post-process: enforce empty StrOrigin = empty Str
    if not dry_run:
        cleaned = cleanup_empty_strorigin(target_file)
        if cleaned > 0:
            logger.info(f"Post-process: cleared Str on {cleaned} entries with empty StrOrigin in {target_file.name}")

    result["corrections_count"] = len(corrections)

    # ─── Missing EventName report ─────────────────────────────────────
    if missing_eventnames:
        from .eventname_resolver import generate_missing_eventname_report
        from datetime import datetime

        result["missing_eventnames_count"] = len(missing_eventnames)
        report_dir = config.get_failed_report_dir(source_file.stem)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"MissingEventNames_{timestamp}.xlsx"

        if generate_missing_eventname_report(missing_eventnames, report_path):
            result["missing_eventname_report"] = str(report_path)
            logger.info(f"Missing EventName report: {report_path}")

    return result


def format_transfer_report(results: Dict, mode: str = "folder", match_mode: str = "") -> str:
    """
    Format transfer results as a human-readable report.

    Args:
        results: Results from transfer_folder_to_folder or transfer_file_to_file
        mode: "folder" or "file"
        match_mode: The match mode used (e.g. "strorigin_only", "strict")

    Returns:
        Formatted report string
    """
    lines = []
    H = "═"
    V = "║"
    TL = "╔"
    TR = "╗"
    BL = "╚"
    BR = "╝"
    LT = "╠"
    RT = "╣"

    width = 72
    is_strorigin = match_mode.startswith("strorigin_only")

    lines.append("")
    lines.append(TL + H * (width - 2) + TR)
    title = "QUICKTRANSLATE TRANSFER REPORT"
    lines.append(V + title.center(width - 2) + V)
    if match_mode:
        mode_label = match_mode.upper().replace("_", " ")
        lines.append(V + f" Mode: {mode_label}".ljust(width - 2) + V)
    lines.append(LT + H * (width - 2) + RT)

    if mode == "folder":
        total_corrections = results.get('total_corrections', 0)
        total_updated = results.get('total_updated', 0)
        total_not_found = results.get('total_not_found', 0)
        total_skipped_translated = results.get('total_skipped_translated', 0)

        lines.append(V + f" Languages Processed: {len(results.get('file_results', {}))}".ljust(width - 2) + V)
        lines.append(V + f" Total Corrections: {total_corrections:,}".ljust(width - 2) + V)
        lines.append(V + f" Total Updated: {total_updated:,}".ljust(width - 2) + V)
        lines.append(V + f" Not Found: {total_not_found:,}".ljust(width - 2) + V)
        if total_skipped_translated > 0:
            lines.append(V + f" Skipped (already translated): {total_skipped_translated:,}".ljust(width - 2) + V)
        if results.get('total_skipped', 0) > 0:
            lines.append(V + f" Skipped (non-SCRIPT): {results.get('total_skipped', 0):,}".ljust(width - 2) + V)

        # Per-language breakdown
        file_results = results.get("file_results", {})
        if file_results:
            lines.append(LT + H * (width - 2) + RT)
            lines.append(V + " PER-LANGUAGE RESULTS:".ljust(width - 2) + V)
            lines.append(V + "".ljust(width - 2) + V)
            for fname, fresult in file_results.items():
                target = fresult.get("target", "?")
                updated = fresult.get("updated", 0)
                skipped = fresult.get("skipped_translated", 0)
                not_found = fresult.get("not_found", 0)
                matched = fresult.get("matched", 0)

                # Extract language name from filename (e.g. languagedata_eng.xml -> ENG)
                lang = target.replace("languagedata_", "").replace(".xml", "").replace(".loc", "").upper()

                parts = [f"{updated} updated"]
                if skipped > 0:
                    parts.append(f"{skipped} skipped")
                if not_found > 0:
                    parts.append(f"{not_found} not found")
                detail = " | ".join(parts)
                lines.append(V + f"   {lang}: {detail}".ljust(width - 2) + V)

    else:
        # Single file mode
        lines.append(V + f" Corrections: {results.get('corrections_count', 0)}".ljust(width - 2) + V)
        lines.append(V + f" Matched: {results.get('matched', 0)}".ljust(width - 2) + V)
        lines.append(V + f" Updated: {results.get('updated', 0)}".ljust(width - 2) + V)
        lines.append(V + f" Not Found: {results.get('not_found', 0)}".ljust(width - 2) + V)
        if results.get('skipped_non_script', 0) > 0:
            lines.append(V + f" Skipped (non-SCRIPT): {results.get('skipped_non_script', 0)}".ljust(width - 2) + V)
        if results.get('skipped_translated', 0) > 0:
            lines.append(V + f" Skipped (already translated): {results.get('skipped_translated', 0)}".ljust(width - 2) + V)

    # Success rate
    total_updated = results.get('total_updated', results.get('updated', 0))
    total = results.get('total_corrections', results.get('corrections_count', 0))
    matched = results.get('total_matched', results.get('matched', 0))
    rate = (matched / total * 100) if total > 0 else 0.0

    lines.append(LT + H * (width - 2) + RT)
    rate_str = f" COVERAGE: {rate:.1f}%"
    if rate >= 95:
        rate_str += " ●"
    elif rate >= 80:
        rate_str += " ◐"
    else:
        rate_str += " ○"
    lines.append(V + rate_str.ljust(width - 2) + V)
    lines.append(BL + H * (width - 2) + BR)

    # Errors
    errors = results.get("errors", [])
    if errors:
        lines.append("")
        lines.append("ERRORS:")
        for error in errors[:5]:
            lines.append(f"  x {error}")
        if len(errors) > 5:
            lines.append(f"  ... and {len(errors) - 5} more errors")

    lines.append("")
    lines.append("Legend: ● >=95% coverage  ◐ >=80% coverage  ○ <80% coverage")
    lines.append("")

    return "\n".join(lines)
