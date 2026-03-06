"""
XML Transfer - Merge corrections to target XML files.

Ported from LanguageDataExporter's locdev_merger.py.
Writes corrections back to XML files using STRICT or StringID-only matching.
"""

import os
import re
import stat
import logging
from collections import Counter, defaultdict
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
from .xml_parser import get_attr, STRINGID_ATTRS, STRORIGIN_ATTRS, STR_ATTRS, DESC_ATTRS, DESCORIGIN_ATTRS, LOCSTR_TAGS
from .source_scanner import scan_source_for_languages, scan_target_for_languages, TargetScanResult
from .postprocess import run_all_postprocess

logger = logging.getLogger(__name__)

# Import from config (single source of truth)
SCRIPT_CATEGORIES = config.SCRIPT_CATEGORIES
SCRIPT_EXCLUDE_SUBFOLDERS = config.SCRIPT_EXCLUDE_SUBFOLDERS

# ─── Pre-filter: raw-bytes regex for fast StringID/StrOrigin scanning ────
_STRINGID_RE = re.compile(rb'stringid\s*=\s*"([^"]*)"', re.IGNORECASE)
_STRORIGIN_RE = re.compile(rb'strorigin\s*=\s*"([^"]*)"', re.IGNORECASE)


def _quick_scan_stringids(filepath: Path) -> Optional[set]:
    """Scan raw bytes for all StringID values. Returns lowercase set, or None on error (fail-safe)."""
    try:
        data = filepath.read_bytes()
        return {m.group(1).decode("utf-8", errors="replace").lower()
                for m in _STRINGID_RE.finditer(data)}
    except Exception:
        return None


def _quick_scan_strorigins(filepath: Path) -> Optional[set]:
    """Scan raw bytes for all StrOrigin values, normalized. Returns set, or None on error (fail-safe)."""
    try:
        data = filepath.read_bytes()
        origins = set()
        for m in _STRORIGIN_RE.finditer(data):
            raw = m.group(1).decode("utf-8", errors="replace")
            # normalize_for_matching handles html.unescape + whitespace + lowercase
            origins.add(normalize_for_matching(raw))
        return origins
    except Exception:
        return None


def _build_correction_lookups(corrections, match_mode):
    """
    Build correction lookup dicts ONCE for reuse across all target files.

    Returns (correction_lookup, correction_lookup_nospace) tuple.
    correction_matched is NOT included — must be built per-file since different
    files match different corrections.

    Args:
        corrections: List of correction dicts (already filtered/preprocessed)
        match_mode: One of "strict", "strorigin_only", "stringid_only", "fuzzy"
    """
    if match_mode == "strict":
        # (StringID, normalized_StrOrigin) -> list of (corrected_text, category, index)
        correction_lookup = defaultdict(list)
        correction_lookup_nospace = defaultdict(list)
        for i, c in enumerate(corrections):
            sid_lower = c["string_id"].lower()
            origin_norm = normalize_text(c.get("str_origin", ""))
            origin_nospace = normalize_nospace(origin_norm)
            category = c.get("category", "Uncategorized")
            correction_lookup[(sid_lower, origin_norm)].append((c["corrected"], category, i))
            correction_lookup_nospace[(sid_lower, origin_nospace)].append((c["corrected"], category, i))
        return correction_lookup, correction_lookup_nospace

    elif match_mode == "strorigin_only":
        # normalized_StrOrigin -> (corrected_text, index)
        correction_lookup = {}
        correction_lookup_nospace = {}
        for i, c in enumerate(corrections):
            origin_norm = normalize_for_matching(c.get("str_origin", ""))
            if not origin_norm:
                continue
            origin_nospace = normalize_nospace(origin_norm)
            correction_lookup[origin_norm] = (c["corrected"], i)
            correction_lookup_nospace[origin_nospace] = (c["corrected"], i)
        return correction_lookup, correction_lookup_nospace

    elif match_mode == "stringid_only":
        # sid.lower() -> full correction dict
        correction_lookup = {}
        for c in corrections:
            sid_lower = c["string_id"].lower()
            correction_lookup[sid_lower] = c
        return correction_lookup, None

    elif match_mode == "strorigin_descorigin":
        # (normalized_StrOrigin, normalized_DescOrigin) -> list of (corrected_text, category, index)
        # Uses normalize_for_matching (case-insensitive) since this mode matches by text content
        correction_lookup = defaultdict(list)
        correction_lookup_nospace = defaultdict(list)
        for i, c in enumerate(corrections):
            origin_norm = normalize_for_matching(c.get("str_origin", ""))
            if not origin_norm:
                continue
            desc_norm = normalize_for_matching(c.get("desc_origin", ""))
            if not desc_norm:
                continue
            origin_nospace = normalize_nospace(origin_norm)
            desc_nospace = normalize_nospace(desc_norm)
            category = c.get("category", "Uncategorized")
            correction_lookup[(origin_norm, desc_norm)].append((c["corrected"], category, i))
            correction_lookup_nospace[(origin_nospace, desc_nospace)].append((c["corrected"], category, i))
        return correction_lookup, correction_lookup_nospace

    elif match_mode == "fuzzy":
        # fuzzy_target_string_id.lower() -> full correction dict
        correction_lookup = {}
        for c in corrections:
            target_sid = c.get("fuzzy_target_string_id", "")
            if target_sid:
                correction_lookup[target_sid.lower()] = c
        return correction_lookup, None

    return None, None


def _preprocess_stringid_only(corrections, stringid_to_category, stringid_to_subfolder=None):
    """
    Pre-process corrections for StringID-only mode: category filter + EventName resolution + subfolder exclusion.

    Extracted from merge_corrections_stringid_only so it can run ONCE for folder mode.

    Args:
        corrections: Raw correction dicts
        stringid_to_category: StringID -> Category mapping
        stringid_to_subfolder: Optional StringID -> Subfolder mapping

    Returns:
        (script_corrections, preprocess_stats) where script_corrections is the filtered list
        and preprocess_stats has counts for skipped_non_script, skipped_excluded, etc.
    """
    stats = {
        "skipped_non_script": 0,
        "skipped_excluded": 0,
        "eventname_resolved": 0,
        "details": [],
    }

    ci_category = {k.lower(): v for k, v in stringid_to_category.items()}
    ci_subfolder = {k.lower(): v for k, v in stringid_to_subfolder.items()} if stringid_to_subfolder else {}

    script_corrections = []
    _en_resolver_loaded = False
    _en_mapping = None
    _en_extract_fn = None

    def _try_resolve_as_eventname(eventname_str):
        nonlocal _en_resolver_loaded, _en_mapping, _en_extract_fn
        if not _en_resolver_loaded:
            _en_resolver_loaded = True
            try:
                from .eventname_resolver import (
                    get_eventname_mapping,
                    extract_stringid_from_dialog_keyword,
                )
                _en_mapping = get_eventname_mapping(config.EXPORT_FOLDER)
                _en_extract_fn = extract_stringid_from_dialog_keyword
            except Exception:
                _en_mapping = None
        if not _en_mapping:
            return None
        extracted = _en_extract_fn(eventname_str)
        if extracted and extracted.lower() != eventname_str.lower():
            return extracted
        data = _en_mapping.get(eventname_str.lower())
        if data:
            return data["stringid"]
        return None

    for c in corrections:
        sid = c["string_id"]
        sid_lower = sid.lower()
        category = ci_category.get(sid_lower, "Uncategorized")
        subfolder = ci_subfolder.get(sid_lower, "")

        if category not in SCRIPT_CATEGORIES:
            resolved_sid = _try_resolve_as_eventname(sid)
            if resolved_sid:
                resolved_lower = resolved_sid.lower()
                resolved_category = ci_category.get(resolved_lower, "Uncategorized")
                if resolved_category in SCRIPT_CATEGORIES:
                    stats["eventname_resolved"] += 1
                    logger.debug(f"EventName '{sid}' resolved to SCRIPT StringID '{resolved_sid}' (category={resolved_category})")
                    sid = resolved_sid
                    sid_lower = resolved_lower
                    category = resolved_category
                    subfolder = ci_subfolder.get(resolved_lower, "")
                    c = dict(c)
                    c["string_id"] = resolved_sid
                else:
                    stats["skipped_non_script"] += 1
                    stats["details"].append({
                        "string_id": sid,
                        "status": "SKIPPED_NON_SCRIPT",
                        "old": f"Category: {resolved_category} (resolved from EventName)",
                        "new": c["corrected"],
                    })
                    logger.debug(f"Skipped non-SCRIPT EventName={sid} -> StringID={resolved_sid} (category={resolved_category})")
                    continue
            else:
                stats["skipped_non_script"] += 1
                stats["details"].append({
                    "string_id": sid,
                    "status": "SKIPPED_NON_SCRIPT",
                    "old": f"Category: {category}",
                    "new": c["corrected"],
                })
                logger.debug(f"Skipped non-SCRIPT StringID={sid} (category={category})")
                continue

        if subfolder.lower() in {s.lower() for s in SCRIPT_EXCLUDE_SUBFOLDERS}:
            stats["skipped_excluded"] += 1
            stats["details"].append({
                "string_id": sid,
                "status": "SKIPPED_EXCLUDED",
                "old": f"Subfolder: {subfolder}",
                "new": c["corrected"],
            })
            logger.debug(f"Skipped excluded subfolder StringID={sid} (subfolder={subfolder})")
            continue

        script_corrections.append({**c, "category": category})

    if stats["eventname_resolved"]:
        logger.info(f"EventName resolution: {stats['eventname_resolved']} EventNames resolved to SCRIPT StringIDs")

    return script_corrections, stats


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


def _try_write_desc(loc, correction, dry_run=False):
    """
    Write Desc to LocStr if correction has desc_corrected and target has DescOrigin.

    Desc transfer conditions:
    1. Correction has non-empty desc_corrected
    2. Target LocStr has non-empty DescOrigin
    3. The new Desc value differs from the current one

    Returns True if Desc was written (or would be in dry_run).
    """
    desc_corrected = correction.get("desc_corrected", "")
    if not desc_corrected:
        return False
    # Target must have non-empty DescOrigin
    target_descorigin = get_attr(loc, DESCORIGIN_ATTRS).strip()
    if not target_descorigin:
        return False
    old_desc = get_attr(loc, DESC_ATTRS)
    new_desc = _convert_linebreaks_for_xml(desc_corrected)
    if new_desc != old_desc:
        if not dry_run:
            loc.set("Desc", new_desc)
        return True
    return False


def merge_corrections_to_xml(
    xml_path: Path,
    corrections: List[Dict],
    dry_run: bool = False,
    only_untranslated: bool = False,
    _prebuilt_lookup=None,
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

    # Build lookup: (StringID, normalized_StrOrigin) -> list of (corrected_text, category, index)
    correction_matched = [False] * len(corrections)

    if _prebuilt_lookup is not None:
        correction_lookup, correction_lookup_nospace = _prebuilt_lookup
    else:
        correction_lookup = defaultdict(list)
        correction_lookup_nospace = defaultdict(list)  # Fallback for whitespace variations
        for i, c in enumerate(corrections):
            sid_lower = c["string_id"].lower()
            origin_norm = normalize_text(c.get("str_origin", ""))
            origin_nospace = normalize_nospace(origin_norm)
            category = c.get("category", "Uncategorized")
            correction_lookup[(sid_lower, origin_norm)].append((c["corrected"], category, i))
            correction_lookup_nospace[(sid_lower, origin_nospace)].append((c["corrected"], category, i))

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

        if root is None:
            result["errors"].append(f"{xml_path.name}: empty or invalid XML (no root element)")
            logger.error(f"merge_corrections_to_xml: {xml_path} has no root element")
            return result

        changed = False

        # Case-insensitive LocStr tag search - collect ALL variants
        all_elements = []
        for tag in LOCSTR_TAGS:
            all_elements.extend(root.iter(tag))

        # Build set of all StringIDs in target for diagnostic purposes
        # (to distinguish "StringID not found" vs "StrOrigin mismatch")
        target_stringids = set()
        target_strorigin_map = {}  # sid.lower() → raw StrOrigin text
        target_raw_attribs_map = {}  # sid.lower() → dict of ALL attributes
        for loc in all_elements:
            tsid = get_attr(loc, STRINGID_ATTRS).strip()
            if tsid:
                target_stringids.add(tsid.lower())
                tso = get_attr(loc, STRORIGIN_ATTRS)
                if tsid.lower() not in target_strorigin_map:
                    target_strorigin_map[tsid.lower()] = tso
                    target_raw_attribs_map[tsid.lower()] = dict(loc.attrib)

        for loc in all_elements:
            # Case-insensitive attribute access
            sid = get_attr(loc, STRINGID_ATTRS).strip()
            orig_raw = get_attr(loc, STRORIGIN_ATTRS)
            orig = normalize_text(orig_raw)

            # Golden rule: empty StrOrigin = never write Str
            if not orig.strip():
                continue

            orig_nospace = normalize_nospace(orig)
            sid_lower = sid.lower()
            key = (sid_lower, orig)
            key_nospace = (sid_lower, orig_nospace)

            # Try exact match first, then nospace fallback
            match_entries = correction_lookup.get(key, [])
            if not match_entries:
                match_entries = correction_lookup_nospace.get(key_nospace, [])
                if match_entries:
                    logger.debug(f"Matched via nospace fallback: StringId={sid}")

            if match_entries:
                # Use last correction (last wins) but mark ALL as matched
                new_str, category, idx = match_entries[-1]
                for _, _, matched_idx in match_entries:
                    correction_matched[matched_idx] = True
                result["matched"] += 1
                result["by_category"][category]["matched"] += 1

                # Get old value (case-insensitive)
                old_str = get_attr(loc, STR_ATTRS)

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

                # Write Desc if correction has desc_corrected and target has DescOrigin
                orig_correction = corrections[idx]
                if _try_write_desc(loc, orig_correction, dry_run):
                    result["desc_updated"] = result.get("desc_updated", 0) + 1
                    changed = True

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

                detail_entry = {
                    "string_id": sid,
                    "status": status,
                    "old": c.get("str_origin", ""),
                    "new": c["corrected"],
                    "target_strorigin": target_strorigin_map.get(sid.lower(), "") if status == "STRORIGIN_MISMATCH" else "",
                    "raw_attribs": c.get("raw_attribs", {}),  # ALL original attributes from source
                    "_original_eventname": c.get("_original_eventname", ""),
                    "_original_dialogvoice": c.get("_original_dialogvoice", ""),
                }
                if status == "STRORIGIN_MISMATCH":
                    detail_entry["target_raw_attribs"] = target_raw_attribs_map.get(sid.lower(), {})
                result["details"].append(detail_entry)

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


def merge_corrections_stringid_only(
    xml_path: Path,
    corrections: List[Dict],
    stringid_to_category: Dict[str, str],
    stringid_to_subfolder: Optional[Dict[str, str]] = None,
    dry_run: bool = False,
    only_untranslated: bool = False,
    _prebuilt_lookup=None,
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
        "skipped_empty_strorigin": 0,
        "not_found": 0,
        "errors": [],
        "by_category": {},
        "details": [],
    }

    if not corrections:
        return result

    # Build case-insensitive category lookup (always needed for per-element matching)
    ci_category = {k.lower(): v for k, v in stringid_to_category.items()}

    if _prebuilt_lookup is not None:
        # Folder mode: preprocessing + lookup already done ONCE
        correction_lookup, _ = _prebuilt_lookup
        correction_matched = {sid: False for sid in correction_lookup}

        # Initialize category stats from pre-built lookup
        for sid_lower, c in correction_lookup.items():
            category = c.get("category", "Uncategorized")
            if category not in result["by_category"]:
                result["by_category"][category] = {"matched": 0, "updated": 0, "not_found": 0}
    else:
        # Single-file mode: do full preprocessing inline
        ci_subfolder = {k.lower(): v for k, v in stringid_to_subfolder.items()} if stringid_to_subfolder else {}

        # Filter corrections to SCRIPT TYPE only (and not in excluded subfolders)
        # Multi-pass: if StringID not in category index, try EventName resolution first
        script_corrections = []
        _eventname_resolved_count = 0

        # Lazy EventName resolver — only loaded if needed
        _en_resolver_loaded = False
        _en_mapping = None
        _en_extract_fn = None

        def _try_resolve_as_eventname(eventname_str):
            """Try to resolve a value as EventName → StringID via 3-step waterfall."""
            nonlocal _en_resolver_loaded, _en_mapping, _en_extract_fn
            if not _en_resolver_loaded:
                _en_resolver_loaded = True
                try:
                    from .eventname_resolver import (
                        get_eventname_mapping,
                        extract_stringid_from_dialog_keyword,
                    )
                    _en_mapping = get_eventname_mapping(config.EXPORT_FOLDER)
                    _en_extract_fn = extract_stringid_from_dialog_keyword
                except Exception:
                    _en_mapping = None
            if not _en_mapping:
                return None

            # Step 1: keyword extraction
            extracted = _en_extract_fn(eventname_str)
            if extracted and extracted.lower() != eventname_str.lower():
                return extracted

            # Step 2: export lookup
            data = _en_mapping.get(eventname_str.lower())
            if data:
                return data["stringid"]

            return None

        for c in corrections:
            sid = c["string_id"]
            sid_lower = sid.lower()
            category = ci_category.get(sid_lower, "Uncategorized")
            subfolder = ci_subfolder.get(sid_lower, "")

            # Check if in SCRIPT categories (Dialog/Sequencer)
            if category not in SCRIPT_CATEGORIES:
                # Multi-pass: before skipping, try resolving as EventName
                # The StringID might actually be an EventName that resolves to a SCRIPT StringID
                resolved_sid = _try_resolve_as_eventname(sid)
                if resolved_sid:
                    resolved_lower = resolved_sid.lower()
                    resolved_category = ci_category.get(resolved_lower, "Uncategorized")
                    if resolved_category in SCRIPT_CATEGORIES:
                        # EventName resolved to a SCRIPT StringID — use it
                        _eventname_resolved_count += 1
                        logger.debug(f"EventName '{sid}' resolved to SCRIPT StringID '{resolved_sid}' (category={resolved_category})")
                        sid = resolved_sid
                        sid_lower = resolved_lower
                        category = resolved_category
                        subfolder = ci_subfolder.get(resolved_lower, "")
                        # Update the correction's string_id for downstream matching
                        c = dict(c)
                        c["string_id"] = resolved_sid
                    else:
                        # Resolved but still not SCRIPT
                        result["skipped_non_script"] += 1
                        result["details"].append({
                            "string_id": sid,
                            "status": "SKIPPED_NON_SCRIPT",
                            "old": f"Category: {resolved_category} (resolved from EventName)",
                            "new": c["corrected"],
                        })
                        logger.debug(f"Skipped non-SCRIPT EventName={sid} -> StringID={resolved_sid} (category={resolved_category})")
                        continue
                else:
                    # Not resolvable as EventName either
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

        if _eventname_resolved_count:
            logger.info(f"EventName resolution: {_eventname_resolved_count} EventNames resolved to SCRIPT StringIDs")

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

        if root is None:
            result["errors"].append(f"{xml_path.name}: empty or invalid XML (no root element)")
            logger.error(f"merge_corrections_stringid_only: {xml_path} has no root element")
            return result

        changed = False

        # Case-insensitive LocStr tag search - collect ALL variants
        all_elements = []
        for tag in LOCSTR_TAGS:
            all_elements.extend(root.iter(tag))

        # First pass: collect ALL target StringIDs (even those with empty StrOrigin)
        # so we can distinguish "truly missing" from "exists but empty StrOrigin"
        target_stringids_all = set()
        for loc in all_elements:
            sid = get_attr(loc, STRINGID_ATTRS).strip()
            if sid:
                target_stringids_all.add(sid.lower())

        for loc in all_elements:
            sid = get_attr(loc, STRINGID_ATTRS).strip()

            # Golden rule: empty StrOrigin = never write Str
            target_origin = get_attr(loc, STRORIGIN_ATTRS).strip()
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

                old_str = get_attr(loc, STR_ATTRS)

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

                # Write Desc if correction has desc_corrected and target has DescOrigin
                if _try_write_desc(loc, correction_lookup[sid_lower], dry_run):
                    result["desc_updated"] = result.get("desc_updated", 0) + 1
                    changed = True

        # Count unmatched corrections - store FULL data for failure reports
        # Distinguish "truly missing" from "exists but StrOrigin is empty"
        for sid_key, matched in correction_matched.items():
            if not matched:
                category = ci_category.get(sid_key, "Uncategorized")
                c = correction_lookup[sid_key]

                if sid_key in target_stringids_all:
                    # StringID exists in target but was skipped (empty StrOrigin)
                    status = "SKIPPED_EMPTY_STRORIGIN"
                    result["skipped_empty_strorigin"] += 1
                else:
                    status = "NOT_FOUND"
                    result["not_found"] += 1

                if status == "NOT_FOUND" and category in result["by_category"]:
                    result["by_category"][category]["not_found"] += 1

                result["details"].append({
                    "string_id": c["string_id"],
                    "status": status,
                    "old": c.get("str_origin", ""),
                    "new": c["corrected"],
                    "raw_attribs": c.get("raw_attribs", {}),
                    "_original_eventname": c.get("_original_eventname", ""),
                    "_original_dialogvoice": c.get("_original_dialogvoice", ""),
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


def _recover_not_found_via_eventname(
    file_result: Dict,
    target_file: Path,
    export_mapping: Optional[Dict],
    dry_run: bool = False,
    only_untranslated: bool = True,
    log_callback=None,
    original_merge_mode: str = "strict",
    stringid_to_category: Optional[Dict] = None,
    stringid_to_subfolder: Optional[Dict] = None,
) -> Dict:
    """
    Recovery pass: re-resolve NOT_FOUND corrections via EventName waterfall.

    When an Excel correction sheet has bogus StringIDs (actually EventNames),
    they fail to match in the target XML and end up as NOT_FOUND. This function
    takes those NOT_FOUND entries, runs them through the 3-step EventName
    waterfall (DialogVoice strip → keyword extract → export lookup), and
    re-merges any that resolve to a valid StringID.

    Args:
        file_result: Result dict from a merge function (has "details", "not_found", etc.)
        target_file: Path to the target XML file for re-merge
        export_mapping: EventName→StringID mapping from get_eventname_mapping()
        dry_run: If True, don't write changes
        only_untranslated: If True, only fill untranslated entries
        log_callback: Optional GUI log callback
        original_merge_mode: "strict" or "stringid_only" — determines which merge function to use for re-merge
        stringid_to_category: Category mapping (required when original_merge_mode="stringid_only")
        stringid_to_subfolder: Subfolder mapping (optional, for stringid_only exclusions)

    Returns:
        Updated file_result dict with recovery stats
    """
    from .eventname_resolver import (
        generate_stringid_from_dialogvoice,
        extract_stringid_from_dialog_keyword,
    )

    if not export_mapping:
        export_mapping = {}

    # Extract NOT_FOUND entries that have recovery metadata
    candidates = []
    for detail in file_result.get("details", []):
        if detail.get("status") != "NOT_FOUND":
            continue
        orig_en = detail.get("_original_eventname", "")
        orig_dv = detail.get("_original_dialogvoice", "")
        failed_sid = detail.get("string_id", "")
        if not (orig_en or orig_dv or failed_sid):
            continue
        candidates.append(detail)

    if not candidates:
        return file_result

    # Run waterfall on each candidate to find a new StringID
    recovered_corrections = []
    step_counts = {"dialogvoice": 0, "keyword": 0, "export": 0}

    for detail in candidates:
        orig_en = detail.get("_original_eventname", "")
        orig_dv = detail.get("_original_dialogvoice", "")
        failed_sid = detail.get("string_id", "")
        new_sid = ""

        # Determine the eventname to use for the waterfall
        eventname = orig_en if orig_en else failed_sid

        if not eventname:
            continue

        # Step 1: DialogVoice strip (only if we have an original eventname)
        if orig_en:
            generated = generate_stringid_from_dialogvoice(eventname, orig_dv)
            if generated and generated.lower() != failed_sid.lower():
                new_sid = generated
                step_counts["dialogvoice"] += 1

        # Step 2: keyword extraction
        if not new_sid:
            extracted = extract_stringid_from_dialog_keyword(eventname)
            if extracted and extracted.lower() != failed_sid.lower():
                new_sid = extracted
                step_counts["keyword"] += 1

        # Step 3: export lookup
        if not new_sid:
            data = export_mapping.get(eventname.lower())
            if data:
                lookup_sid = data["stringid"]
                if lookup_sid.lower() != failed_sid.lower():
                    new_sid = lookup_sid
                    step_counts["export"] += 1

        if new_sid:
            recovered_corrections.append({
                "string_id": new_sid,
                "str_origin": detail.get("old", ""),
                "corrected": detail.get("new", ""),
                "_recovery_from": failed_sid,
            })

    if not recovered_corrections:
        logger.debug("EventName recovery: no candidates resolved")
        return file_result

    # Re-merge recovered corrections using the same merge mode as the original
    logger.info(
        f"EventName recovery: {len(recovered_corrections)} candidates to re-merge "
        f"(mode={original_merge_mode}, Step1: {step_counts['dialogvoice']}, "
        f"Step2: {step_counts['keyword']}, Step3: {step_counts['export']})"
    )

    if original_merge_mode == "stringid_only" and stringid_to_category:
        recovery_result = merge_corrections_stringid_only(
            target_file, recovered_corrections, stringid_to_category,
            stringid_to_subfolder or {}, dry_run,
            only_untranslated=only_untranslated,
        )
    else:
        recovery_result = merge_corrections_to_xml(
            target_file, recovered_corrections, dry_run,
            only_untranslated=only_untranslated,
        )

    recovery_matched = recovery_result["matched"]
    if recovery_matched == 0:
        logger.info("EventName recovery: resolved StringIDs but none matched in target XML")
        return file_result

    # Remove stale NOT_FOUND detail entries for recovered items
    # Only remove entries whose failed SID was successfully re-merged
    recovered_detail_sids = set()
    for rc in recovered_corrections:
        rc_sid = rc["string_id"]
        for rd in recovery_result["details"]:
            if rd.get("string_id", "").lower() == rc_sid.lower() and rd["status"] in ("UPDATED", "UNCHANGED"):
                recovered_detail_sids.add(rc["_recovery_from"].lower())

    file_result["details"] = [
        d for d in file_result["details"]
        if not (d["status"] == "NOT_FOUND" and d.get("string_id", "").lower() in recovered_detail_sids)
    ]

    # Update counters — decrement not_found by actual removals, not total matched
    actually_recovered = len(recovered_detail_sids)
    file_result["matched"] = file_result.get("matched", 0) + actually_recovered
    file_result["updated"] = file_result.get("updated", 0) + recovery_result.get("updated", 0)
    file_result["not_found"] = max(0, file_result.get("not_found", 0) - actually_recovered)

    # Add recovery detail entries
    for rd in recovery_result["details"]:
        if rd["status"] in ("UPDATED", "UNCHANGED"):
            rd["status"] = f"RECOVERED_{rd['status']}"
        file_result["details"].append(rd)

    # Store recovery stats
    file_result["eventname_recovery"] = {
        "candidates": len(candidates),
        "resolved": len(recovered_corrections),
        "matched": actually_recovered,
        "updated": recovery_result.get("updated", 0),
        "steps": step_counts,
    }

    logger.info(
        f"EventName recovery: {actually_recovered}/{len(candidates)} recovered "
        f"({recovery_result.get('updated', 0)} updated)"
    )
    if log_callback:
        log_callback(
            f"  EventName recovery: {actually_recovered} recovered "
            f"(DV:{step_counts['dialogvoice']} KW:{step_counts['keyword']} EX:{step_counts['export']})",
            'info',
        )

    return file_result


# ─── Fast Folder Merge (TMXTransfer11 pattern) ──────────────────────────────


def _fast_folder_merge(
    target_files: List[Path],
    corrections: List[Dict],
    correction_lookup,
    correction_lookup_nospace,
    match_mode: str,
    dry_run: bool,
    only_untranslated: bool,
    log_callback=None,
    progress_callback=None,
) -> Dict:
    """
    Merge ALL corrections into ALL target XML files in one tight loop.

    TMXTransfer11 pattern: parse → 1 match pass + 1 postprocess pass → write.
    No per-file details lists, no per-file correction_matched arrays.
    Global tracking of which corrections matched SOMEWHERE across all files.

    Args:
        target_files: List of XML file paths to process
        corrections: Full corrections list (for unmatched reporting)
        correction_lookup: Pre-built lookup dict (mode-specific)
        correction_lookup_nospace: Pre-built nospace fallback (strict/strorigin_only)
        match_mode: "strict" | "strorigin_only" | "stringid_only"
        dry_run: If True, don't write changes
        only_untranslated: If True, skip entries that already have non-Korean Str
        log_callback: Optional GUI log callback
        progress_callback: Optional progress callback

    Returns:
        Dict with: total_matched, total_updated, total_not_found,
                   total_strorigin_mismatch, total_skipped_translated,
                   total_desc_updated, errors, per_file, unmatched_details
    """
    from .postprocess import run_all_postprocess_on_tree

    result = {
        "total_matched": 0,
        "total_updated": 0,
        "total_not_found": 0,
        "total_strorigin_mismatch": 0,
        "total_skipped_translated": 0,
        "total_desc_updated": 0,
        "errors": [],
        "per_file": {},
        "unmatched_details": [],
    }

    if not target_files or not corrections:
        return result

    # ─── Phase A: Global state (once, before file loop) ──────────────

    if match_mode == "strict":
        # correction_lookup: (sid_lower, norm_orig) -> list of (corrected, category, index)
        # Track per correction index — use len(corrections) for robustness
        # (handles edge case where some corrections are filtered out of lookup)
        correction_matched = bytearray(len(corrections))

        # For STRORIGIN_MISMATCH diagnostics
        correction_sid_set = set()
        for key in correction_lookup:
            correction_sid_set.add(key[0])  # key = (sid_lower, norm_orig)
        target_sids_seen = set()
        target_attribs_cache = {}

    elif match_mode == "strorigin_only":
        # correction_lookup: norm_orig -> (corrected, index)
        correction_matched = bytearray(len(corrections))
        # Track matched origins for source-duplicate detection
        matched_origin_set = set()

    elif match_mode == "stringid_only":
        # correction_lookup: sid_lower -> full correction dict
        correction_matched = {sid: False for sid in correction_lookup}
        # For SKIPPED_EMPTY_STRORIGIN diagnostics
        target_stringids_all = set()

    elif match_mode == "strorigin_descorigin":
        # correction_lookup: (norm_orig, norm_desc) -> list of (corrected, category, index)
        correction_matched = bytearray(len(corrections))
        # For DESCORIGIN_MISMATCH diagnostics: track StrOrigins that were seen
        correction_origin_set = set()
        for key in correction_lookup:
            correction_origin_set.add(key[0])  # key = (norm_orig, norm_desc)
        target_origins_seen = set()
        target_attribs_cache_so = {}

    counters_matched = 0
    counters_updated = 0
    counters_skipped_translated = 0
    counters_desc_updated = 0

    # ─── Phase B: Tight file loop ────────────────────────────────────

    for fi, target_file in enumerate(target_files):
        if progress_callback:
            progress_callback(f"Processing {target_file.name} ({fi+1}/{len(target_files)})")

        try:
            if USING_LXML:
                parser = etree.XMLParser(
                    resolve_entities=False, load_dtd=False,
                    no_network=True, recover=True,
                )
                tree = etree.parse(str(target_file), parser)
                root = tree.getroot()
            else:
                tree = etree.parse(str(target_file))
                root = tree.getroot()
        except Exception as e:
            result["errors"].append(f"{target_file.name}: {e}")
            logger.error(f"Fast merge parse error: {target_file}: {e}")
            continue

        if root is None:
            result["errors"].append(f"{target_file.name}: empty or invalid XML (no root element)")
            logger.error(f"Fast merge: {target_file} has no root element, skipping")
            continue

        changed = False
        file_updated = 0
        file_matched = 0

        # Collect all LocStr elements once
        all_elements = []
        for tag in LOCSTR_TAGS:
            all_elements.extend(root.iter(tag))

        # ─── StringID-only: collect ALL target SIDs for empty-strorigin diagnostics
        if match_mode == "stringid_only":
            for loc in all_elements:
                sid = get_attr(loc, STRINGID_ATTRS).strip()
                if sid:
                    target_stringids_all.add(sid.lower())

        # ─── ONE match pass over all elements ────────────────────────
        for loc in all_elements:
            sid = get_attr(loc, STRINGID_ATTRS).strip()
            orig_raw = get_attr(loc, STRORIGIN_ATTRS)

            if match_mode == "strict":
                orig = normalize_text(orig_raw)
                if not orig.strip():
                    continue

                sid_lower = sid.lower()
                orig_nospace = normalize_nospace(orig)
                key = (sid_lower, orig)
                key_nospace = (sid_lower, orig_nospace)

                match_entries = correction_lookup.get(key, [])
                if not match_entries:
                    match_entries = correction_lookup_nospace.get(key_nospace, [])

                if match_entries:
                    new_str, category, idx = match_entries[-1]
                    for _, _, matched_idx in match_entries:
                        correction_matched[matched_idx] = 1
                    counters_matched += 1
                    file_matched += 1
                    target_sids_seen.add(sid_lower)  # track for STRORIGIN_MISMATCH

                    old_str = get_attr(loc, STR_ATTRS)

                    if only_untranslated and old_str and not is_korean_text(old_str):
                        counters_skipped_translated += 1
                        orig_correction = corrections[idx]
                        result["unmatched_details"].append({
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
                        counters_updated += 1
                        file_updated += 1
                        changed = True

                    # Desc transfer
                    orig_correction = corrections[idx]
                    if _try_write_desc(loc, orig_correction, dry_run):
                        counters_desc_updated += 1
                        changed = True
                else:
                    # Not matched — capture for STRORIGIN_MISMATCH diagnostics
                    if sid_lower in correction_sid_set:
                        target_sids_seen.add(sid_lower)
                        if sid_lower not in target_attribs_cache:
                            target_attribs_cache[sid_lower] = dict(loc.attrib)

            elif match_mode == "strorigin_only":
                orig = normalize_for_matching(orig_raw)
                if not orig.strip():
                    continue

                orig_nospace = normalize_nospace(orig)

                match_data = correction_lookup.get(orig)
                if match_data is None:
                    match_data = correction_lookup_nospace.get(orig_nospace)

                if match_data is not None:
                    new_str, idx = match_data
                    correction_matched[idx] = 1
                    matched_origin_set.add(normalize_for_matching(
                        corrections[idx].get("str_origin", "")
                    ))
                    counters_matched += 1
                    file_matched += 1

                    old_str = get_attr(loc, STR_ATTRS)

                    if only_untranslated and old_str and not is_korean_text(old_str):
                        counters_skipped_translated += 1
                        orig_correction = corrections[idx]
                        result["unmatched_details"].append({
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
                        counters_updated += 1
                        file_updated += 1
                        changed = True

            elif match_mode == "stringid_only":
                target_origin = get_attr(loc, STRORIGIN_ATTRS).strip()
                if not target_origin:
                    continue

                sid_lower = sid.lower()
                if sid_lower in correction_lookup:
                    c = correction_lookup[sid_lower]
                    correction_matched[sid_lower] = True
                    counters_matched += 1
                    file_matched += 1

                    new_str = c["corrected"]
                    old_str = get_attr(loc, STR_ATTRS)

                    if only_untranslated and old_str and not is_korean_text(old_str):
                        counters_skipped_translated += 1
                        result["unmatched_details"].append({
                            "string_id": sid,
                            "status": "SKIPPED_TRANSLATED",
                            "old": c.get("str_origin", ""),
                            "new": c.get("corrected", ""),
                            "raw_attribs": c.get("raw_attribs", {}),
                        })
                        continue

                    new_str = _convert_linebreaks_for_xml(new_str)
                    if new_str != old_str:
                        if not dry_run:
                            loc.set("Str", new_str)
                        counters_updated += 1
                        file_updated += 1
                        changed = True

                    # Desc transfer
                    if _try_write_desc(loc, c, dry_run):
                        counters_desc_updated += 1
                        changed = True

            elif match_mode == "strorigin_descorigin":
                orig = normalize_for_matching(orig_raw)
                if not orig.strip():
                    continue

                desc_raw = get_attr(loc, DESCORIGIN_ATTRS)
                desc = normalize_for_matching(desc_raw)
                if not desc:
                    continue
                orig_nospace = normalize_nospace(orig)
                desc_nospace = normalize_nospace(desc)
                key = (orig, desc)
                key_nospace = (orig_nospace, desc_nospace)

                match_entries = correction_lookup.get(key, [])
                if not match_entries:
                    match_entries = correction_lookup_nospace.get(key_nospace, [])

                if match_entries:
                    new_str, category, idx = match_entries[-1]
                    for _, _, matched_idx in match_entries:
                        correction_matched[matched_idx] = 1
                    counters_matched += 1
                    file_matched += 1
                    target_origins_seen.add(orig)  # orig already normalized

                    old_str = get_attr(loc, STR_ATTRS)

                    if only_untranslated and old_str and not is_korean_text(old_str):
                        counters_skipped_translated += 1
                        orig_correction = corrections[idx]
                        result["unmatched_details"].append({
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
                        counters_updated += 1
                        file_updated += 1
                        changed = True

                    # Desc transfer
                    orig_correction = corrections[idx]
                    if _try_write_desc(loc, orig_correction, dry_run):
                        counters_desc_updated += 1
                        changed = True
                else:
                    # Not matched — capture for DESCORIGIN_MISMATCH diagnostics
                    if orig in correction_origin_set:
                        target_origins_seen.add(orig)  # orig already normalized
                        if orig not in target_attribs_cache_so:
                            target_attribs_cache_so[orig] = dict(loc.attrib)

        # ─── Combined postprocess (ONE pass) ─────────────────────────
        pp = run_all_postprocess_on_tree(root)
        if pp["changed"]:
            changed = True

        # ─── Write if anything changed ───────────────────────────────
        if changed and not dry_run:
            try:
                current_mode = os.stat(target_file).st_mode
                if not current_mode & stat.S_IWRITE:
                    os.chmod(target_file, current_mode | stat.S_IWRITE)
            except Exception:
                pass

            if USING_LXML:
                tree.write(str(target_file), encoding="utf-8", xml_declaration=False, pretty_print=True)
            else:
                tree.write(str(target_file), encoding="utf-8", xml_declaration=False)

        if file_updated > 0:
            result["per_file"][target_file.name] = {"updated": file_updated, "matched": file_matched}

    # ─── Phase C: Compute unmatched ONCE (after all files) ───────────

    if match_mode == "strict":
        for i, c in enumerate(corrections):
            if not correction_matched[i]:
                sid = c["string_id"]
                sid_lower = sid.lower()
                if sid_lower in target_sids_seen:
                    status = "STRORIGIN_MISMATCH"
                    result["total_strorigin_mismatch"] += 1
                else:
                    status = "NOT_FOUND"
                    result["total_not_found"] += 1

                detail = {
                    "string_id": sid,
                    "status": status,
                    "old": c.get("str_origin", ""),
                    "new": c["corrected"],
                    "raw_attribs": c.get("raw_attribs", {}),
                    "_original_eventname": c.get("_original_eventname", ""),
                    "_original_dialogvoice": c.get("_original_dialogvoice", ""),
                }
                if status == "STRORIGIN_MISMATCH":
                    detail["target_raw_attribs"] = target_attribs_cache.get(sid_lower, {})
                    # Build target_strorigin from cached attribs
                    cached = target_attribs_cache.get(sid_lower, {})
                    detail["target_strorigin"] = cached.get("StrOrigin", cached.get("strorigin", ""))
                result["unmatched_details"].append(detail)

    elif match_mode == "strorigin_only":
        for i, c in enumerate(corrections):
            if not correction_matched[i]:
                origin_norm = normalize_for_matching(c.get("str_origin", ""))
                if not origin_norm:
                    continue
                if origin_norm in matched_origin_set:
                    continue  # source duplicate, not a failure
                result["total_not_found"] += 1
                result["unmatched_details"].append({
                    "string_id": c.get("string_id", ""),
                    "status": "NOT_FOUND",
                    "old": c.get("str_origin", ""),
                    "new": c["corrected"],
                    "raw_attribs": c.get("raw_attribs", {}),
                    "_original_eventname": c.get("_original_eventname", ""),
                    "_original_dialogvoice": c.get("_original_dialogvoice", ""),
                })

    elif match_mode == "stringid_only":
        for sid_key, matched in correction_matched.items():
            if not matched:
                c = correction_lookup[sid_key]
                if sid_key in target_stringids_all:
                    status = "SKIPPED_EMPTY_STRORIGIN"
                else:
                    status = "NOT_FOUND"
                    result["total_not_found"] += 1
                result["unmatched_details"].append({
                    "string_id": c["string_id"],
                    "status": status,
                    "old": c.get("str_origin", ""),
                    "new": c["corrected"],
                    "raw_attribs": c.get("raw_attribs", {}),
                    "_original_eventname": c.get("_original_eventname", ""),
                    "_original_dialogvoice": c.get("_original_dialogvoice", ""),
                })

    elif match_mode == "strorigin_descorigin":
        for i, c in enumerate(corrections):
            if not correction_matched[i]:
                origin_norm = normalize_for_matching(c.get("str_origin", ""))
                if not origin_norm:
                    continue
                desc_norm = normalize_for_matching(c.get("desc_origin", ""))
                if not desc_norm:
                    continue
                if origin_norm in target_origins_seen:
                    status = "DESCORIGIN_MISMATCH"
                    result["total_strorigin_mismatch"] += 1
                else:
                    status = "NOT_FOUND"
                    result["total_not_found"] += 1

                detail = {
                    "string_id": c.get("string_id", ""),
                    "status": status,
                    "old": c.get("str_origin", ""),
                    "new": c["corrected"],
                    "raw_attribs": c.get("raw_attribs", {}),
                    "_original_eventname": c.get("_original_eventname", ""),
                    "_original_dialogvoice": c.get("_original_dialogvoice", ""),
                }
                if status == "DESCORIGIN_MISMATCH":
                    detail["target_raw_attribs"] = target_attribs_cache_so.get(origin_norm, {})
                    cached = target_attribs_cache_so.get(origin_norm, {})
                    detail["target_descorigin"] = (
                        cached.get("DescOrigin") or cached.get("Descorigin") or
                        cached.get("descorigin") or cached.get("DESCORIGIN") or ""
                    )
                result["unmatched_details"].append(detail)

    result["total_matched"] = counters_matched
    result["total_updated"] = counters_updated
    result["total_skipped_translated"] = counters_skipped_translated
    result["total_desc_updated"] = counters_desc_updated

    logger.info(
        f"Fast merge complete: {len(target_files)} files, "
        f"{counters_matched} matched, {counters_updated} updated, "
        f"{result['total_not_found']} not found"
    )

    return result


def transfer_folder_to_folder(
    source_folder: Path,
    target_folder: Path,
    stringid_to_category: Optional[Dict[str, str]] = None,
    stringid_to_subfolder: Optional[Dict[str, str]] = None,
    match_mode: str = "strict",
    dry_run: bool = False,
    progress_callback=None,
    log_callback=None,
    threshold: float = None,
    only_untranslated: bool = False,
    # Pre-built fuzzy data (CRITICAL: avoid rebuilding full index!)
    fuzzy_model=None,
    fuzzy_index=None,
    fuzzy_texts: Optional[List[str]] = None,
    fuzzy_entries: Optional[List[dict]] = None,
    source_stringids: Optional[set] = None,
    # Pre-scanned target (flexible target support)
    target_scan: Optional[TargetScanResult] = None,
    # Unique-only filtering for strorigin_only modes
    unique_only: bool = False,
    # Non-Script Only filtering for strict modes
    strict_non_script_only: bool = False,
    # StringID-Only: match ALL categories (bypass SCRIPT filter)
    stringid_all_categories: bool = False,
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
                    "strorigin_only", "strorigin_only_fuzzy",
                    "strorigin_descorigin", or "strorigin_descorigin_fuzzy"
        dry_run: If True, don't write changes
        progress_callback: Optional callback for progress updates
        threshold: Similarity threshold for fuzzy modes (defaults to config.FUZZY_THRESHOLD_DEFAULT)

    Returns:
        Dict with overall results
    """
    from .excel_io import read_corrections_from_excel

    results = {
        "match_mode": match_mode,
        "files_processed": 0,
        "total_corrections": 0,
        "total_matched": 0,
        "total_updated": 0,
        "total_not_found": 0,
        "total_strorigin_mismatch": 0,  # StringID exists but StrOrigin differs
        "total_skipped": 0,
        "total_skipped_excluded": 0,
        "total_skipped_translated": 0,
        "total_skipped_empty_strorigin": 0,
        "total_skipped_duplicate_strorigin": 0,
        "total_skipped_script": 0,
        "total_desc_updated": 0,
        "prefilter_skipped": 0,
        "prefilter_total": 0,
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
    # NOTE: strorigin_only_fuzzy matches by StrOrigin text, NOT StringID.
    # Filtering the FAISS index by StringIDs would miss valid matches where
    # source and target have different StringIDs but matching StrOrigin text.
    if all_source_stringids is None and match_mode == "strict_fuzzy":
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
                        all_source_stringids.add(sid.lower())
            except ValueError as e:
                logger.warning(f"Skipped {src_file.name} during StringID extraction: {e}")
                continue
            except Exception as e:
                logger.warning(f"Skipped {src_file.name} during StringID extraction: {e}")
                continue
        logger.info(f"Extracted {len(all_source_stringids):,} unique StringIDs from {len(all_sources)} source files")

    if match_mode in ("strict_fuzzy", "strorigin_only_fuzzy", "strorigin_descorigin_fuzzy"):
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
                    stringid_filter=all_source_stringids,
                    only_untranslated=only_untranslated,
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

    # ─── Scan target folder for flexible language detection ──────────
    if target_scan is None:
        target_scan = scan_target_for_languages(target_folder)

    # Build target language → files lookup (case-insensitive)
    target_files_by_lang: Dict[str, List[Path]] = {}
    for lang_code, files in target_scan.lang_files.items():
        target_files_by_lang[lang_code.upper()] = files
        target_files_by_lang[lang_code.lower()] = files

    # ─── Phase 1: Parse ALL source files and group by LANGUAGE ────────
    # Group corrections by language code. Each language may have MULTIPLE
    # target files (XML and/or Excel) that ALL receive the corrections.

    from .xml_io import parse_corrections_from_xml

    # {lang_code_upper: {"corrections": [...], "source_files": [...], "target_files": [...]}}
    lang_groups = {}

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

        if not lang_code:
            results["errors"].append(f"No language detected for {source_file.name}")
            continue

        # Find target files for this language (flexible scanner)
        lang_upper = lang_code.upper()
        target_files = target_files_by_lang.get(lang_upper, [])

        if not target_files:
            # Backward compat: try hardcoded languagedata pattern as last resort
            for candidate in [
                target_folder / f"languagedata_{lang_code}.xml",
                target_folder / f"languagedata_{lang_upper}.xml",
                target_folder / f"languagedata_{lang_code.lower()}.xml",
            ]:
                if candidate.exists():
                    target_files = [candidate]
                    break

        if not target_files:
            results["errors"].append(f"No target files found for {source_file.name} (lang={lang_upper})")
            continue

        # Group corrections by language
        if lang_upper not in lang_groups:
            lang_groups[lang_upper] = {
                "corrections": [],
                "source_files": [],
                "target_files": target_files,
            }
        lang_groups[lang_upper]["corrections"].extend(corrections)
        lang_groups[lang_upper]["source_files"].append(source_file.name)
        target_names = ", ".join(f.name for f in target_files)
        logger.info(f"Parsed {source_file.name}: {len(corrections)} corrections → {target_names}")

    logger.info(f"Grouped {sum(len(g['corrections']) for g in lang_groups.values()):,} corrections "
                f"across {len(lang_groups)} languages")

    # ─── GLOBAL Unique-Only pre-filter (StrOrigin-Only modes) ─────────
    # Filter ONCE across ALL corrections per language BEFORE the per-file
    # loop. This ensures accurate counts and avoids N*duplicates inflation.
    if unique_only and match_mode in ("strorigin_only", "strorigin_only_fuzzy"):
        total_skipped_dup = 0
        total_dup_groups = 0
        all_duplicate_details = []  # Collect globally for reporting

        for lang_upper, group in lang_groups.items():
            corrections_list = group["corrections"]
            origin_counts = Counter()
            for c in corrections_list:
                norm = normalize_for_matching(c.get("str_origin", ""))
                if norm:
                    origin_counts[norm] += 1

            unique_corrections = []
            for c in corrections_list:
                norm = normalize_for_matching(c.get("str_origin", ""))
                if norm and origin_counts[norm] > 1:
                    all_duplicate_details.append({
                        "string_id": c.get("string_id", ""),
                        "status": "SKIPPED_DUPLICATE_STRORIGIN",
                        "old": c.get("str_origin", ""),
                        "new": c.get("corrected", ""),
                        "language": lang_upper,
                    })
                    continue
                unique_corrections.append(c)

            skipped_dup = len(corrections_list) - len(unique_corrections)
            dup_groups = sum(1 for cnt in origin_counts.values() if cnt > 1)
            if skipped_dup > 0:
                logger.info(
                    f"[{lang_upper}] Unique-only filter: skipped {skipped_dup} corrections "
                    f"({dup_groups} duplicate StrOrigin groups)"
                )
            total_skipped_dup += skipped_dup
            total_dup_groups += dup_groups
            group["corrections"] = unique_corrections

        if total_skipped_dup > 0:
            logger.info(
                f"Global unique-only filter: {total_skipped_dup} corrections skipped "
                f"({total_dup_groups} duplicate StrOrigin groups) -- exported to report"
            )
        results["total_skipped_duplicate_strorigin"] = total_skipped_dup
        results["_duplicate_strorigin_details"] = all_duplicate_details

    # ─── Non-Script pre-filter for Strict / StrOrigin+DescOrigin modes ──────
    # Skip SCRIPT corrections (Dialog/Sequencer) — handle via StringID-Only pass.
    if strict_non_script_only and stringid_to_category and match_mode in ("strict", "strict_fuzzy", "strorigin_descorigin", "strorigin_descorigin_fuzzy"):
        ci_cat = {k.lower(): v for k, v in stringid_to_category.items()}
        total_skipped_script = 0
        for lang_upper, group in lang_groups.items():
            original = group["corrections"]
            filtered = [c for c in original
                        if ci_cat.get(c.get("string_id", "").lower(), "") not in SCRIPT_CATEGORIES]
            skipped = len(original) - len(filtered)
            if skipped > 0 and log_callback:
                log_callback(f"[{lang_upper}] Non-Script filter: skipped {skipped} SCRIPT corrections", 'warning')
            total_skipped_script += skipped
            group["corrections"] = filtered
        if total_skipped_script > 0:
            logger.info(f"Non-Script filter total: {total_skipped_script} SCRIPT corrections removed")
        results["total_skipped_script"] = total_skipped_script

    # Convert lang_groups to target_groups format for the Phase 2 loop.
    # Each target file gets its own entry so the merge loop can process them independently.
    target_groups = {}
    for lang_upper, group in lang_groups.items():
        for target_file in group["target_files"]:
            target_key = str(target_file)
            if target_key not in target_groups:
                target_groups[target_key] = {
                    "target_file": target_file,
                    "corrections": group["corrections"],
                    "source_files": group["source_files"],
                    "language": lang_upper,
                }

    logger.info(f"Expanded to {len(target_groups)} target files for merge")

    # ─── Auto-detect EventNames in StringID column (3A.5) ──────────────
    # When no EventName column exists, StringID column may contain mixed
    # StringIDs and EventNames. For entries NOT in category index, stash
    # string_id as _source_eventname so the waterfall resolution can try.
    if stringid_to_category:
        ci_cat = {k.lower(): v for k, v in stringid_to_category.items()}
        auto_detected = 0
        for g in target_groups.values():
            for c in g["corrections"]:
                if c.get("_no_eventname_col") and not c.get("_source_eventname"):
                    sid = c.get("string_id", "")
                    if sid and sid.lower() not in ci_cat:
                        c["_source_eventname"] = sid
                        c["_original_eventname"] = sid
                        auto_detected += 1
        if auto_detected:
            logger.info(f"Auto-detected {auto_detected} potential EventNames in StringID column")

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

    # ─── Pre-filter: skip target files with zero matching corrections ─────
    # Raw-bytes regex scan (~2ms/file) avoids expensive XML parse+iterate
    # for the 98%+ of files that have no matching StringIDs/StrOrigins.
    prefilter_total = sum(
        1 for g in target_groups.values()
        if g["target_file"].suffix.lower() in (".xml",)
    )
    prefilter_skipped = 0

    if prefilter_total > 0:
        if progress_callback:
            progress_callback(f"Pre-filtering {prefilter_total} target files...")

        if match_mode in ("strict", "strict_fuzzy", "stringid_only"):
            # Collect all correction StringIDs (lowercase) across all groups
            correction_sids = set()
            for g in target_groups.values():
                for c in g["corrections"]:
                    sid = c.get("string_id", "")
                    if sid:
                        correction_sids.add(sid.lower())

            if correction_sids:
                keys_to_skip = []
                for target_key, group in target_groups.items():
                    tf = group["target_file"]
                    if tf.suffix.lower() != ".xml":
                        continue
                    file_sids = _quick_scan_stringids(tf)
                    if file_sids is None:
                        continue  # fail-safe: scan error → don't skip
                    if not file_sids.intersection(correction_sids):
                        keys_to_skip.append(target_key)
                for k in keys_to_skip:
                    logger.debug(f"Pre-filter skip: {target_groups[k]['target_file'].name}")
                    del target_groups[k]
                prefilter_skipped = len(keys_to_skip)

        elif match_mode in ("strorigin_only", "strorigin_only_fuzzy",
                            "strorigin_descorigin", "strorigin_descorigin_fuzzy"):
            # Collect all correction StrOrigins (normalized) across all groups
            correction_origins = set()
            for g in target_groups.values():
                for c in g["corrections"]:
                    origin = c.get("str_origin", "")
                    if origin:
                        correction_origins.add(normalize_for_matching(origin))

            if correction_origins:
                keys_to_skip = []
                for target_key, group in target_groups.items():
                    tf = group["target_file"]
                    if tf.suffix.lower() != ".xml":
                        continue
                    file_origins = _quick_scan_strorigins(tf)
                    if file_origins is None:
                        continue  # fail-safe: scan error → don't skip
                    if not file_origins.intersection(correction_origins):
                        keys_to_skip.append(target_key)
                for k in keys_to_skip:
                    logger.debug(f"Pre-filter skip: {target_groups[k]['target_file'].name}")
                    del target_groups[k]
                prefilter_skipped = len(keys_to_skip)

        if prefilter_skipped > 0:
            msg = f"Pre-filter: {prefilter_skipped}/{prefilter_total} target files skipped (zero matching corrections)"
            logger.info(msg)
            if log_callback:
                log_callback(msg, 'info')
        else:
            logger.info(f"Pre-filter: all {prefilter_total} target files have potential matches")

    results["prefilter_skipped"] = prefilter_skipped
    results["prefilter_total"] = prefilter_total

    # ─── Build correction lookups ONCE per language for reuse across target files ─
    # TMXTransfer11 pattern: build dict once, lean dict.get() in inner loop.
    # Multiple languages may have different corrections — cache by corrections list id.
    _base_mode = match_mode.replace("_fuzzy", "")  # strict_fuzzy → strict
    _lookup_cache = {}          # {id(corrections_list): (lookup, lookup_nospace)}
    _preprocess_stats_cache = {}  # {id(corrections_list): stats_dict}

    for _group in target_groups.values():
        _corr = _group["corrections"]
        _corr_id = id(_corr)
        if _corr_id in _lookup_cache or not _corr:
            continue

        if _base_mode == "strict":
            _lookup_cache[_corr_id] = _build_correction_lookups(_corr, "strict")
            logger.info(f"Built shared strict lookup: {len(_lookup_cache[_corr_id][0]):,} keys")

        elif _base_mode == "strorigin_only":
            _lookup_cache[_corr_id] = _build_correction_lookups(_corr, "strorigin_only")
            logger.info(f"Built shared strorigin_only lookup: {len(_lookup_cache[_corr_id][0]):,} keys")

        elif _base_mode == "strorigin_descorigin":
            _lookup_cache[_corr_id] = _build_correction_lookups(_corr, "strorigin_descorigin")
            logger.info(f"Built shared strorigin_descorigin lookup: {len(_lookup_cache[_corr_id][0]):,} keys")

        elif _base_mode == "stringid_only":
            if stringid_all_categories:
                # ALL categories: skip preprocessing, build lookup directly from all corrections
                _lookup_cache[_corr_id] = _build_correction_lookups(_corr, "stringid_only")
                _preprocess_stats_cache[_corr_id] = {
                    "skipped_non_script": 0, "skipped_excluded": 0,
                    "eventname_resolved": 0, "details": [],
                }
                logger.info(
                    f"Built shared stringid_only lookup (ALL CATEGORIES): "
                    f"{len(_lookup_cache[_corr_id][0]):,} keys"
                )
            elif stringid_to_category:
                _preprocessed, _pp_stats = _preprocess_stringid_only(
                    _corr, stringid_to_category, stringid_to_subfolder,
                )
                _preprocess_stats_cache[_corr_id] = _pp_stats
                if _preprocessed:
                    _lookup_cache[_corr_id] = _build_correction_lookups(_preprocessed, "stringid_only")
                    logger.info(
                        f"Built shared stringid_only lookup: {len(_lookup_cache[_corr_id][0]):,} keys "
                        f"(skipped {_pp_stats['skipped_non_script']} non-script, "
                        f"{_pp_stats['skipped_excluded']} excluded)"
                    )
                else:
                    _lookup_cache[_corr_id] = (None, None)

    # ─── Phase 2: Merge corrections to target files ─────────────────
    # ALL XML targets (including fuzzy modes) use fast folder merge (TMXTransfer11 pattern).
    # Excel targets use the per-file loop.

    from .excel_io import merge_corrections_to_excel

    # Lazy export mapping loader for EventName recovery (only built if needed)
    _recovery_mapping = None
    def _get_recovery_mapping():
        nonlocal _recovery_mapping
        if _recovery_mapping is None:
            from .eventname_resolver import get_eventname_mapping
            _recovery_mapping = get_eventname_mapping(config.EXPORT_FOLDER)
        return _recovery_mapping

    _preprocess_stats_counted = set()  # Track which correction lists had stats counted

    # ─── Phase 2A: Fast merge for non-fuzzy XML targets ──────────────
    # Groups all XML targets by correction list (one group per language),
    # runs _fast_folder_merge() once per group. 10x+ faster than per-file.

    _fast_merge_modes = {
        "strict", "strorigin_only", "stringid_only",
        "strict_fuzzy", "strorigin_only_fuzzy",
        "strorigin_descorigin", "strorigin_descorigin_fuzzy",
    }
    _remaining_targets = {}  # Targets that need per-file processing (Excel only)

    if match_mode in _fast_merge_modes:
        # Group XML targets by correction list ID (same corrections = same language)
        _fast_groups = {}  # {corr_id: {"corrections": [...], "xml_files": [...], ...}}

        for target_key, group in target_groups.items():
            target_file = group["target_file"]
            if target_file.suffix.lower() in (".xlsx", ".xls"):
                _remaining_targets[target_key] = group
                continue
            corr_id = id(group["corrections"])
            if corr_id not in _fast_groups:
                _fast_groups[corr_id] = {
                    "corrections": group["corrections"],
                    "xml_files": [],
                    "source_files": group["source_files"],
                    "language": group.get("language", ""),
                }
            _fast_groups[corr_id]["xml_files"].append(target_file)

        for corr_id, fg in _fast_groups.items():
            _cached = _lookup_cache.get(corr_id)
            if not _cached or _cached[0] is None:
                logger.warning(f"No lookup for fast merge group (lang={fg['language']}), skipping")
                continue

            lookup, lookup_nospace = _cached
            corrections = fg["corrections"]
            xml_files = fg["xml_files"]
            lang = fg["language"]
            source_names = fg["source_files"]

            # Handle stringid_only preprocess stats (skipped_non_script, etc.)
            if match_mode == "stringid_only":
                _pp_stats = _preprocess_stats_cache.get(corr_id)
                if _pp_stats and corr_id not in _preprocess_stats_counted:
                    results["total_skipped"] += _pp_stats.get("skipped_non_script", 0)
                    results["total_skipped_excluded"] += _pp_stats.get("skipped_excluded", 0)
                    _preprocess_stats_counted.add(corr_id)

            logger.info(f"═══ FAST MERGE [{lang}]: {len(corrections):,} corrections → {len(xml_files)} XML files ═══")
            if log_callback:
                log_callback(
                    f"── {lang} · {len(corrections):,} corrections → {len(xml_files)} XML files ──",
                    'header',
                )

            # Use base mode for fast merge (strict_fuzzy → strict, etc.)
            _fm_mode = _base_mode if match_mode.endswith("_fuzzy") else match_mode

            fast_result = _fast_folder_merge(
                xml_files, corrections,
                lookup, lookup_nospace,
                _fm_mode,
                dry_run, only_untranslated,
                log_callback, progress_callback,
            )

            # Aggregate fast_result into results
            results["files_processed"] += len(source_names)
            results["total_corrections"] += len(corrections)
            results["total_matched"] += fast_result["total_matched"]
            results["total_updated"] += fast_result["total_updated"]
            results["total_not_found"] += fast_result["total_not_found"]
            results["total_strorigin_mismatch"] += fast_result["total_strorigin_mismatch"]
            results["total_skipped_translated"] += fast_result["total_skipped_translated"]
            results["total_desc_updated"] += fast_result["total_desc_updated"]
            results["errors"].extend(fast_result["errors"])

            # Count SKIPPED_EMPTY_STRORIGIN from unmatched details (stringid_only)
            skipped_empty_so = sum(
                1 for d in fast_result["unmatched_details"]
                if d.get("status") == "SKIPPED_EMPTY_STRORIGIN"
            )
            results["total_skipped_empty_strorigin"] += skipped_empty_so

            # Build file_results entry for failure report compatibility.
            # Use first target file as the representative (language extraction works on any).
            representative_target = xml_files[0].name
            combined_details = list(fast_result["unmatched_details"])

            # Merge stringid_only preprocess details (SKIPPED_NON_SCRIPT, SKIPPED_EXCLUDED)
            if match_mode == "stringid_only":
                _pp_stats = _preprocess_stats_cache.get(corr_id)
                if _pp_stats:
                    combined_details.extend(_pp_stats.get("details", []))

            results["file_results"][representative_target] = {
                "target": representative_target,
                "source_files": source_names,
                "corrections": len(corrections),
                "matched": fast_result["total_matched"],
                "updated": fast_result["total_updated"],
                "not_found": fast_result["total_not_found"],
                "strorigin_mismatch": fast_result["total_strorigin_mismatch"],
                "skipped_translated": fast_result["total_skipped_translated"],
                "skipped_empty_strorigin": skipped_empty_so,
                "desc_updated": fast_result["total_desc_updated"],
                "errors": fast_result["errors"],
                "details": combined_details,
            }

            # EventName recovery on unmatched (strict and stringid_only only)
            if match_mode in ("strict", "strict_fuzzy", "stringid_only") and fast_result["total_not_found"] > 0:
                # Run EventName recovery on the synthetic file_result against all XML files
                # Use the first XML file as target (recovery re-parses per-file anyway)
                _fr_entry = results["file_results"][representative_target]
                for recovery_target in xml_files:
                    not_found_count = sum(
                        1 for d in _fr_entry["details"]
                        if d.get("status") == "NOT_FOUND"
                    )
                    if not_found_count == 0:
                        break
                    # When stringid_all_categories, use generic merge (no SCRIPT filter on recovery)
                    _recovery_mode = match_mode if match_mode == "stringid_only" and not stringid_all_categories else None
                    _fr_entry = _recover_not_found_via_eventname(
                        _fr_entry, recovery_target, _get_recovery_mapping(),
                        dry_run=dry_run, only_untranslated=only_untranslated,
                        log_callback=log_callback,
                        original_merge_mode=_recovery_mode,
                        stringid_to_category=stringid_to_category if _recovery_mode == "stringid_only" else None,
                        stringid_to_subfolder=stringid_to_subfolder if _recovery_mode == "stringid_only" else None,
                    )
                # Update results with recovery
                results["file_results"][representative_target] = _fr_entry
                recovery = _fr_entry.get("eventname_recovery", {})
                if recovery:
                    results.setdefault("total_eventname_recovered", 0)
                    results["total_eventname_recovered"] += recovery.get("matched", 0)
                    # Adjust not_found in results (recovery resolved some)
                    recovered_count = recovery.get("matched", 0)
                    results["total_not_found"] = max(0, results["total_not_found"] - recovered_count)

            # ─── Fuzzy Step 2: FAISS on unmatched → fast merge by StringID ───
            if match_mode.endswith("_fuzzy") and _fuzzy_model and _fuzzy_index and _fuzzy_texts and _fuzzy_entries:
                _fr_entry = results["file_results"][representative_target]
                if match_mode == "strict_fuzzy":
                    _fuzzy_statuses = {"NOT_FOUND", "STRORIGIN_MISMATCH"}
                elif match_mode == "strorigin_descorigin_fuzzy":
                    _fuzzy_statuses = {"NOT_FOUND", "DESCORIGIN_MISMATCH"}
                else:
                    _fuzzy_statuses = {"NOT_FOUND"}
                unconsumed = []
                for detail in _fr_entry["details"]:
                    if detail.get("status") in _fuzzy_statuses:
                        unconsumed.append({
                            "string_id": detail["string_id"],
                            "str_origin": detail.get("old", ""),
                            "corrected": detail.get("new", ""),
                            "raw_attribs": detail.get("raw_attribs", {}),
                            "_original_status": detail["status"],
                        })

                if unconsumed:
                    from .fuzzy_matching import find_matches_fuzzy
                    logger.info(f"[{lang}] Fuzzy Step 2: FAISS on {len(unconsumed)} unconsumed corrections")
                    if log_callback:
                        log_callback(f"  Fuzzy Step 2: {len(unconsumed)} unmatched → FAISS search", 'info')

                    fuzzy_matched, fuzzy_unmatched, fuzzy_stats = find_matches_fuzzy(
                        unconsumed, _fuzzy_texts, _fuzzy_entries,
                        _fuzzy_model, _fuzzy_index, effective_threshold,
                        progress_callback=progress_callback,
                        log_callback=log_callback,
                    )

                    if fuzzy_matched:
                        # Build lookup: fuzzy_target_string_id.lower() → correction dict
                        # Same structure as stringid_only (sid.lower() → dict), so _fast_folder_merge works
                        fuzzy_lookup, _ = _build_correction_lookups(fuzzy_matched, "fuzzy")

                        fuzzy_result = _fast_folder_merge(
                            xml_files, fuzzy_matched,
                            fuzzy_lookup, None,
                            "stringid_only",
                            dry_run, only_untranslated,
                            log_callback, progress_callback,
                        )

                        # Merge fuzzy results into totals
                        results["total_matched"] += fuzzy_result["total_matched"]
                        results["total_updated"] += fuzzy_result["total_updated"]

                        # Adjust Step 1 unmatched counts (fuzzy resolved some)
                        fuzzy_from_not_found = sum(
                            1 for m in fuzzy_matched if m.get("_original_status") == "NOT_FOUND"
                        )
                        fuzzy_from_mismatch = sum(
                            1 for m in fuzzy_matched if m.get("_original_status") in ("STRORIGIN_MISMATCH", "DESCORIGIN_MISMATCH")
                        )
                        results["total_not_found"] = max(0, results["total_not_found"] - fuzzy_from_not_found)
                        results["total_strorigin_mismatch"] = max(0, results["total_strorigin_mismatch"] - fuzzy_from_mismatch)

                        # Update file_results details: remove resolved, add fuzzy details
                        resolved_sids = {m.get("string_id", "") for m in fuzzy_matched}
                        _fr_entry["details"] = [
                            d for d in _fr_entry["details"]
                            if not (d.get("status") in _fuzzy_statuses and d.get("string_id", "") in resolved_sids)
                        ]
                        _fr_entry["details"].extend(fuzzy_result["unmatched_details"])

                        # Update file_results counters
                        _fr_entry["matched"] = _fr_entry.get("matched", 0) + fuzzy_result["total_matched"]
                        _fr_entry["updated"] = _fr_entry.get("updated", 0) + fuzzy_result["total_updated"]
                        _fr_entry["not_found"] = max(0, _fr_entry.get("not_found", 0) - fuzzy_from_not_found)
                        if "strorigin_mismatch" in _fr_entry:
                            _fr_entry["strorigin_mismatch"] = max(0, _fr_entry["strorigin_mismatch"] - fuzzy_from_mismatch)

                        logger.info(
                            f"[{lang}] Fuzzy Step 2: {fuzzy_result['total_matched']} additional matches "
                            f"({fuzzy_result['total_updated']} updated, avg_score={fuzzy_stats['avg_score']:.3f})"
                        )
                        if log_callback:
                            log_callback(
                                f"  Fuzzy Step 2: {fuzzy_result['total_matched']} recovered (avg: {fuzzy_stats['avg_score']:.2f})",
                                'info',
                            )
                    else:
                        logger.info(f"[{lang}] Fuzzy Step 2: No matches found for {len(unconsumed)} unconsumed")
                        if log_callback:
                            log_callback(f"  Fuzzy Step 2: 0 recovered from {len(unconsumed)} attempts", 'warning')
                else:
                    logger.info(f"[{lang}] Fuzzy Step 2: All corrections matched in Step 1!")
                    if log_callback:
                        log_callback("  Fuzzy Step 2: All matched in Step 1!", 'success')

            # Log summary
            f_updated = fast_result["total_updated"]
            f_matched = fast_result["total_matched"]
            f_not_found = fast_result["total_not_found"]
            f_skipped_tr = fast_result["total_skipped_translated"]
            f_strorigin_mm = fast_result["total_strorigin_mismatch"]
            f_unchanged = max(0, f_matched - f_updated - f_skipped_tr)
            logger.info(
                f"[{lang}] fast merge: "
                f"{f_updated} updated, {f_unchanged} already correct, {f_skipped_tr} skipped, {f_not_found} not found"
            )
            if log_callback:
                tag = 'success' if f_not_found == 0 and f_strorigin_mm == 0 else 'warning'
                parts = [f"{f_updated} updated", f"{f_unchanged} already correct"]
                if f_skipped_tr > 0:
                    parts.append(f"{f_skipped_tr} skipped")
                if f_not_found > 0:
                    parts.append(f"{f_not_found} not found")
                if f_strorigin_mm > 0 and match_mode in ("strict", "strict_fuzzy"):
                    parts.append(f"{f_strorigin_mm} origin mismatch")
                log_callback(f"  Result: {' · '.join(parts)}", tag)
    else:
        # Unknown mode: fall back to per-file processing for all targets
        logger.warning(f"match_mode '{match_mode}' not in fast merge modes, falling back to per-file processing")
        _remaining_targets = dict(target_groups)

    # ─── Phase 2B: Per-file loop for remaining targets (Excel only) ──
    for ti, (target_key, group) in enumerate(_remaining_targets.items()):
        target_file = group["target_file"]
        corrections = group["corrections"]
        source_names = group["source_files"]
        is_excel = target_file.suffix.lower() in (".xlsx", ".xls")

        # Resolve per-language shared lookup (None if not cached or empty corrections)
        _corr_id = id(corrections)
        _cached = _lookup_cache.get(_corr_id)
        _shared_lookup = _cached if _cached and _cached[0] is not None else None

        if progress_callback:
            progress_callback(f"Transferring to {target_file.name}... ({ti+1}/{len(_remaining_targets)})")

        logger.info(f"═══ {target_file.name}: {len(corrections):,} corrections from {len(source_names)} files ═══")

        # GUI per-language header
        if log_callback:
            lang_code = group.get("language", target_file.stem.replace("languagedata_", "").upper())
            log_callback(f"── {lang_code} ({ti+1}/{len(_remaining_targets)}) · {len(corrections):,} corrections → {target_file.name} ──", 'header')

        # ─── Dispatch based on target file type ───────────────────────
        if is_excel:
            # Excel target: use merge_corrections_to_excel()
            # Map transfer match_mode to base mode (fuzzy N/A for Excel targets)
            excel_mode = match_mode.replace("_fuzzy", "")  # strict_fuzzy -> strict
            if excel_mode != match_mode:
                logger.warning("Fuzzy mode not supported for Excel target %s, using '%s'", target_file.name, excel_mode)
            file_result = merge_corrections_to_excel(
                target_file, corrections,
                match_mode=excel_mode,
                dry_run=dry_run,
                only_untranslated=only_untranslated,
                stringid_to_category=stringid_to_category,
                stringid_to_subfolder=stringid_to_subfolder,
                stringid_all_categories=stringid_all_categories,
            )
            results["total_skipped"] += file_result.get("skipped_non_script", 0)
            results["total_skipped_excluded"] += file_result.get("skipped_excluded", 0)
        else:
            # Fallback: non-Excel target reaching Phase 2B (all XML should use Phase 2A fast merge)
            logger.warning(f"Unexpected non-Excel target in Phase 2B: {target_file.name} (mode={match_mode})")
            file_result = merge_corrections_to_xml(
                target_file, corrections, dry_run,
                only_untranslated=only_untranslated,
                _prebuilt_lookup=_shared_lookup,
            )
            if not dry_run:
                run_all_postprocess(target_file)

        # Aggregate results
        results["files_processed"] += len(source_names)
        results["total_corrections"] += len(corrections)
        results["total_matched"] += file_result["matched"]
        results["total_updated"] += file_result["updated"]
        results["total_not_found"] += file_result.get("not_found", 0)
        results["total_strorigin_mismatch"] += file_result.get("strorigin_mismatch", 0)
        results["total_skipped_translated"] += file_result.get("skipped_translated", 0)
        results["total_skipped_empty_strorigin"] += file_result.get("skipped_empty_strorigin", 0)
        results["total_desc_updated"] += file_result.get("desc_updated", 0)
        # NOTE: total_skipped_duplicate_strorigin is set by the global pre-filter above,
        # NOT aggregated per-file (the per-file merge no longer tracks this).
        results["errors"].extend(file_result["errors"])

        # Aggregate EventName recovery stats
        recovery = file_result.get("eventname_recovery", {})
        if recovery:
            results.setdefault("total_eventname_recovered", 0)
            results["total_eventname_recovered"] += recovery.get("matched", 0)

        # Store result keyed by target name
        source_label = ", ".join(source_names)
        results["file_results"][target_file.name] = {
            "target": target_file.name,
            "source_files": source_names,
            "corrections": len(corrections),
            **file_result,
        }

        # Log per-target result
        f_updated = file_result["updated"]
        f_matched = file_result.get("matched", 0)
        f_not_found = file_result.get("not_found", 0)
        f_skipped_tr = file_result.get("skipped_translated", 0)
        f_strorigin_mm = file_result.get("strorigin_mismatch", 0)
        f_unchanged = max(0, f_matched - f_updated - f_skipped_tr)
        logger.info(
            f"[{source_label}] -> {target_file.name}: "
            f"{f_updated} updated, {f_unchanged} already correct, {f_skipped_tr} skipped, {f_not_found} not found"
        )
        if log_callback:
            tag = 'success' if f_not_found == 0 and f_strorigin_mm == 0 else 'warning'
            parts = [f"{f_updated} updated", f"{f_unchanged} already correct"]
            if f_skipped_tr > 0:
                parts.append(f"{f_skipped_tr} skipped")
            if f_not_found > 0:
                parts.append(f"{f_not_found} not found")
            if f_strorigin_mm > 0 and not match_mode.startswith("strorigin_only"):
                parts.append(f"{f_strorigin_mm} origin mismatch")
            log_callback(f"  Result: {' · '.join(parts)}", tag)

    # ─── Fix total_corrections to reflect ORIGINAL count (before unique-only filter)
    # The per-file loop aggregated len(corrections) from the FILTERED list.
    # Add back skipped duplicates so the summary shows the true source count.
    skipped_dup = results.get("total_skipped_duplicate_strorigin", 0)
    if skipped_dup > 0:
        results["total_corrections"] += skipped_dup

    skipped_script = results.get("total_skipped_script", 0)
    if skipped_script > 0:
        results["total_corrections"] += skipped_script

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


# NOTE: transfer_file_to_file() removed — GUI only uses transfer_folder_to_folder()


def format_transfer_report(results: Dict, mode: str = "folder", match_mode: str = "") -> str:
    """
    Format transfer results as a human-readable report.

    Args:
        results: Results from transfer_folder_to_folder
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
    is_strorigin_descorigin = match_mode.startswith("strorigin_descorigin")
    if is_strorigin_descorigin:
        not_found_label = "(StrOrigin + DescOrigin combo not found)"
    elif is_strorigin:
        not_found_label = "(StrOrigin text not found in target)"
    else:
        not_found_label = "(StringID missing from target)"

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
        total_matched = results.get('total_matched', 0)
        total_updated = results.get('total_updated', 0)
        total_not_found = results.get('total_not_found', 0)
        total_strorigin_mismatch = results.get('total_strorigin_mismatch', 0)
        total_skipped_translated = results.get('total_skipped_translated', 0)
        total_unchanged = max(0, total_matched - total_updated - total_skipped_translated)

        lines.append(V + f" Languages Processed: {len(results.get('file_results', {}))}".ljust(width - 2) + V)
        lines.append(V + "".ljust(width - 2) + V)
        lines.append(V + f" Total Corrections: {total_corrections:,}".ljust(width - 2) + V)
        lines.append(V + f"   Updated:          {total_updated:,}  (value changed in target)".ljust(width - 2) + V)
        total_desc_updated = results.get('total_desc_updated', 0)
        if total_desc_updated > 0:
            lines.append(V + f"   Desc Updated:     {total_desc_updated:,}  (voice direction descriptions)".ljust(width - 2) + V)
        lines.append(V + f"   Already Correct:  {total_unchanged:,}  (target already had correct value)".ljust(width - 2) + V)
        if total_not_found > 0 or total_strorigin_mismatch > 0:
            lines.append(V + f"   Not Found:        {total_not_found:,}  {not_found_label}".ljust(width - 2) + V)
        if total_strorigin_mismatch > 0 and not is_strorigin:
            lines.append(V + f"   Origin Mismatch:  {total_strorigin_mismatch:,}  (StringID exists, StrOrigin differs)".ljust(width - 2) + V)
        if total_skipped_translated > 0:
            lines.append(V + f"   Skipped:          {total_skipped_translated:,}  (already translated)".ljust(width - 2) + V)
        if results.get('total_skipped_empty_strorigin', 0) > 0 and not is_strorigin:
            lines.append(V + f"   Empty StrOrigin:  {results['total_skipped_empty_strorigin']:,}  (StringID exists, StrOrigin empty in target)".ljust(width - 2) + V)
        if results.get('total_skipped', 0) > 0:
            skip_label = "SCRIPT — use StringID-Only" if "strorigin" in match_mode else "non-SCRIPT"
            lines.append(V + f"   Skipped:          {results.get('total_skipped', 0):,}  ({skip_label})".ljust(width - 2) + V)
        if results.get('total_skipped_duplicate_strorigin', 0) > 0:
            lines.append(V + f"   Dup. StrOrigin:   {results['total_skipped_duplicate_strorigin']:,}  (unique-only filter, see report)".ljust(width - 2) + V)
        if results.get('total_skipped_script', 0) > 0:
            lines.append(V + f"   Non-Script Skip:  {results['total_skipped_script']:,}  (Dialog/Sequencer filtered out)".ljust(width - 2) + V)
        if results.get('total_eventname_recovered', 0) > 0:
            lines.append(V + f"   EN Recovery:      {results['total_eventname_recovered']:,}  (EventName→StringID resolved)".ljust(width - 2) + V)

        # Per-language breakdown
        file_results = results.get("file_results", {})
        if file_results:
            lines.append(LT + H * (width - 2) + RT)
            lines.append(V + " PER-LANGUAGE BREAKDOWN:".ljust(width - 2) + V)
            lines.append(V + "".ljust(width - 2) + V)
            for fname, fresult in file_results.items():
                target = fresult.get("target", "?")
                f_updated = fresult.get("updated", 0)
                f_matched = fresult.get("matched", 0)
                f_skipped = fresult.get("skipped_translated", 0)
                f_not_found = fresult.get("not_found", 0)
                f_strorigin_mismatch = fresult.get("strorigin_mismatch", 0)
                f_unchanged = max(0, f_matched - f_updated - f_skipped)

                # Extract language name from filename (e.g. languagedata_eng.xml -> ENG)
                lang = target.replace("languagedata_", "").replace(".xml", "").replace(".loc", "").upper()

                parts = [f"{f_updated} updated"]
                if f_unchanged > 0:
                    parts.append(f"{f_unchanged} already correct")
                if f_skipped > 0:
                    parts.append(f"{f_skipped} skipped")
                if f_not_found > 0:
                    parts.append(f"{f_not_found} not found")
                if f_strorigin_mismatch > 0 and not is_strorigin:
                    parts.append(f"{f_strorigin_mismatch} origin mismatch")
                detail = " | ".join(parts)
                lines.append(V + f"   {lang}: {detail}".ljust(width - 2) + V)

    else:
        # Single file mode
        s_corrections = results.get('corrections_count', 0)
        s_matched = results.get('matched', 0)
        s_updated = results.get('updated', 0)
        s_not_found = results.get('not_found', 0)
        s_strorigin_mismatch = results.get('strorigin_mismatch', 0)
        s_skipped_translated = results.get('skipped_translated', 0)
        s_unchanged = max(0, s_matched - s_updated - s_skipped_translated)

        lines.append(V + f" Corrections: {s_corrections:,}".ljust(width - 2) + V)
        lines.append(V + f"   Updated:          {s_updated:,}  (value changed in target)".ljust(width - 2) + V)
        s_desc_updated = results.get('desc_updated', 0)
        if s_desc_updated > 0:
            lines.append(V + f"   Desc Updated:     {s_desc_updated:,}  (voice direction descriptions)".ljust(width - 2) + V)
        lines.append(V + f"   Already Correct:  {s_unchanged:,}  (target already had correct value)".ljust(width - 2) + V)
        if s_not_found > 0 or s_strorigin_mismatch > 0:
            lines.append(V + f"   Not Found:        {s_not_found:,}  {not_found_label}".ljust(width - 2) + V)
        if s_strorigin_mismatch > 0 and not is_strorigin:
            lines.append(V + f"   Origin Mismatch:  {s_strorigin_mismatch:,}  (StringID exists, StrOrigin differs)".ljust(width - 2) + V)
        if results.get('skipped_non_script', 0) > 0:
            lines.append(V + f"   Skipped:          {results.get('skipped_non_script', 0):,}  (non-SCRIPT)".ljust(width - 2) + V)
        if s_skipped_translated > 0:
            lines.append(V + f"   Skipped:          {s_skipped_translated:,}  (already translated)".ljust(width - 2) + V)
        recovery = results.get('eventname_recovery', {})
        if recovery.get('matched', 0) > 0:
            lines.append(V + f"   EN Recovery:      {recovery['matched']:,}  (EventName→StringID resolved)".ljust(width - 2) + V)

    # Success rate
    # Coverage is based on EFFECTIVE corrections (excluding duplicates that were
    # intentionally skipped by the unique-only filter — they never had a chance
    # to match, so including them would artificially deflate the rate).
    total = results.get('total_corrections', results.get('corrections_count', 0))
    dup_skipped = results.get('total_skipped_duplicate_strorigin', 0)
    script_skipped = results.get('total_skipped_script', 0)
    effective_total = total - dup_skipped - script_skipped
    matched = results.get('total_matched', results.get('matched', 0))
    rate = (matched / effective_total * 100) if effective_total > 0 else 0.0

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
