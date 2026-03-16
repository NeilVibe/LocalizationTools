"""Diff engine – compare XML/Excel sources, category filtering, folder diff, revert."""

from __future__ import annotations

import logging
import shutil
from collections import OrderedDict
from pathlib import Path

import config
from . import xml_parser, input_parser
from .text_utils import extract_differences, has_letter_change
from .xml_writer import write_locstr_xml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_key(entry: dict, mode: str) -> str | tuple:
    """Build a comparison key for an entry based on the mode."""
    sid = entry["string_id"]
    so = entry["str_origin"]
    sv = entry["str_value"]

    if mode == "StrOrigin + StringID":
        return (so.lower(), sid.lower())
    if mode == "StrOrigin + StringID + Str":
        return (so.lower(), sid.lower(), sv.lower())
    if mode == "StringID + Str":
        return (sid.lower(), sv.lower())
    # "Full (all attributes)" – keyed by SID; attrs compared separately
    return sid.lower()


def _entries_to_ordered(entries: list[dict]) -> OrderedDict:
    """Build SID-keyed OrderedDict (for Full mode). Last-wins on dupe SID."""
    od: OrderedDict = OrderedDict()
    for e in entries:
        od[e["string_id"].lower()] = e
    return od


# ---------------------------------------------------------------------------
# Post-filter: non-letter-only changes
# ---------------------------------------------------------------------------

def _filter_nonletter_changes(
    source_entries: list[dict],
    extracted: list[dict],
    log_fn=None,
) -> list[dict]:
    """Remove entries whose Str diff contains NO letter changes.

    Builds a SID→entry map from *source_entries*, then for each extracted
    entry checks whether the Str difference involves at least one letter
    (or a ``<br/>`` structural change).  Pure-punctuation / symbol diffs
    are dropped.
    """
    src_map: dict[str, dict] = {}
    for e in source_entries:
        src_map[e["string_id"].lower()] = e

    kept: list[dict] = []
    filtered_count = 0
    for e in extracted:
        sid_lower = e["string_id"].lower()
        src_e = src_map.get(sid_lower)
        if src_e is None:
            # ADD — no source to compare, always keep
            kept.append(e)
            continue
        old_str = src_e.get("str_value", "")
        new_str = e.get("str_value", "")
        if old_str == new_str:
            # Str unchanged — change is in other attributes, keep it
            kept.append(e)
            continue
        if has_letter_change(old_str, new_str):
            kept.append(e)
        else:
            filtered_count += 1
            logger.debug(
                "Filtered non-letter-only change: SID=%s old=%r new=%r",
                e["string_id"], old_str, new_str,
            )

    if filtered_count and log_fn:
        log_fn(f"Filtered {filtered_count:,} non-letter-only change(s)", "info")
    return kept


# ---------------------------------------------------------------------------
# File-level diff
# ---------------------------------------------------------------------------

def diff_file(
    source_entries: list[dict],
    target_entries: list[dict],
    *,
    mode: str = "Full (all attributes)",
    category_filter: str = "All (no filter)",
    category_map: dict[str, str] | None = None,
    filter_nonletter: bool = False,
    log_fn=None,
) -> list[dict]:
    """Compare *source* and *target* entries, return extracted entries.

    For Full mode: returns ADDs (in target, not in source) and EDITs
    (same SID, different attributes).

    For keyed modes: returns target entries whose key is not in source.
    """
    # Apply category filter to target
    if category_filter != "All (no filter)" and category_map:
        target_entries = _filter_by_category(target_entries, category_filter, category_map)

    if mode == "Full (all attributes)":
        result = _diff_full(source_entries, target_entries)
    elif mode == "StrOrigin Diff":
        result = _diff_strorigin(source_entries, target_entries)
    else:
        # Key-based modes
        source_keys = {_build_key(e, mode) for e in source_entries}
        result = [e for e in target_entries if _build_key(e, mode) not in source_keys]

    if filter_nonletter:
        result = _filter_nonletter_changes(source_entries, result, log_fn=log_fn)
    return result


def _diff_full(source_entries: list[dict], target_entries: list[dict]) -> list[dict]:
    """Full attribute comparison: detect ADDs and EDITs.

    When either side has empty ``raw_attribs`` (Excel entries), falls back
    to comparing ``str_origin`` + ``str_value`` instead.
    """
    src = _entries_to_ordered(source_entries)
    extracted = []

    for e in target_entries:
        sid_lower = e["string_id"].lower()
        if sid_lower not in src:
            e["_diff_type"] = "ADD"
            extracted.append(e)
        else:
            src_e = src[sid_lower]
            tgt_attribs = e.get("raw_attribs") or {}
            src_attribs = src_e.get("raw_attribs") or {}

            if not tgt_attribs or not src_attribs:
                # Excel entry on one or both sides — no XML attributes to
                # compare, so fall back to content-level comparison.
                # Defense-in-depth: skip if both content fields are empty
                # on either side (indicates missing columns — should have
                # been blocked by GUI validation).
                if not e["str_origin"] and not e["str_value"]:
                    logger.warning("Skipping entry %s: target str_origin and str_value both empty", e["string_id"])
                    continue
                if not src_e["str_origin"] and not src_e["str_value"]:
                    logger.warning("Skipping entry %s: source str_origin and str_value both empty", e["string_id"])
                    continue
                if (e["str_origin"].lower() != src_e["str_origin"].lower()
                        or e["str_value"].lower() != src_e["str_value"].lower()):
                    e["_diff_type"] = "EDIT"
                    extracted.append(e)
            elif tgt_attribs != src_attribs:
                e["_diff_type"] = "EDIT"
                extracted.append(e)

    return extracted


def _diff_strorigin(source_entries: list[dict], target_entries: list[dict]) -> list[dict]:
    """StrOrigin Diff: find entries where same StringID has different StrOrigin.

    Returns target entries enriched with ``_old_strorigin`` and ``_strorigin_diff``.
    """
    src_map: dict[str, dict] = {}
    for e in source_entries:
        src_map[e["string_id"].lower()] = e

    extracted = []
    for e in target_entries:
        sid_lower = e["string_id"].lower()
        if sid_lower not in src_map:
            continue
        src_e = src_map[sid_lower]
        old_so = src_e["str_origin"]
        new_so = e["str_origin"]
        if old_so.lower() == new_so.lower():
            continue
        e["_old_strorigin"] = old_so
        e["_strorigin_diff"] = extract_differences(old_so, new_so)
        extracted.append(e)

    return extracted


def _filter_by_category(
    entries: list[dict],
    cat_filter: str,
    category_map: dict[str, str],
) -> list[dict]:
    """Filter entries by category using the EXPORT index."""
    filtered = []
    for e in entries:
        sid_lower = e["string_id"].lower()
        cat = category_map.get(sid_lower, "")
        if cat_filter == "SCRIPT only":
            if cat in config.SCRIPT_CATEGORIES:
                filtered.append(e)
        elif cat_filter == "NON-SCRIPT only":
            if cat and cat not in config.SCRIPT_CATEGORIES:
                filtered.append(e)
        else:
            filtered.append(e)
    return filtered


# ---------------------------------------------------------------------------
# Folder-level diff
# ---------------------------------------------------------------------------

def diff_folder(
    source_folder: Path,
    target_folder: Path,
    *,
    mode: str = "Full (all attributes)",
    category_filter: str = "All (no filter)",
    category_map: dict[str, str] | None = None,
    filter_nonletter: bool = False,
    valid_codes: set[str] | None = None,
    log_fn=None,
    progress_fn=None,
) -> dict[str, list[dict]]:
    """Diff per-language across two folders.

    Returns ``{LANG: [extracted_entries]}``.
    """
    from .language_utils import discover_valid_codes as _disc

    if valid_codes is None:
        loc = config.LOC_FOLDER
        if loc:
            valid_codes = set(_disc(loc).keys())

    if log_fn:
        log_fn("Parsing source folder...")
    src_prog = (lambda v: progress_fn(v * 0.4)) if progress_fn else None
    source_by_lang = input_parser.parse_input_folder(
        source_folder, valid_codes=valid_codes,
        log_fn=log_fn,
        progress_fn=src_prog,
    )

    if log_fn:
        log_fn("Parsing target folder...")
    tgt_prog = (lambda v: progress_fn(40 + v * 0.4)) if progress_fn else None
    target_by_lang = input_parser.parse_input_folder(
        target_folder, valid_codes=valid_codes,
        log_fn=log_fn,
        progress_fn=tgt_prog,
    )

    # Info note when Full mode encounters Excel entries (no raw_attribs).
    # Columns were pre-validated — this is informational, not a warning.
    if mode == "Full (all attributes)" and log_fn:
        all_entries = [e for lang_entries in list(source_by_lang.values()) + list(target_by_lang.values())
                       for e in lang_entries]
        excel_count = sum(1 for e in all_entries if not e.get("raw_attribs"))
        if excel_count:
            log_fn(
                f"Note: {excel_count:,} entries from Excel (columns pre-validated) — "
                f"Full mode uses StrOrigin + Str comparison for these.",
                "info",
            )

    result: dict[str, list[dict]] = {}

    all_langs = sorted(set(source_by_lang) | set(target_by_lang))
    total_langs = len(all_langs)
    for i, lang in enumerate(all_langs, 1):
        if progress_fn:
            progress_fn(80 + (i * 20 / max(total_langs, 1)))

        src = source_by_lang.get(lang, [])
        tgt = target_by_lang.get(lang, [])
        if not tgt:
            continue
        extracted = diff_file(src, tgt, mode=mode, category_filter=category_filter,
                              category_map=category_map, filter_nonletter=filter_nonletter,
                              log_fn=log_fn)
        if extracted:
            result[lang] = extracted
            if log_fn:
                log_fn(f"  {lang}: {len(extracted):,} differences found")

    return result


# ---------------------------------------------------------------------------
# Revert
# ---------------------------------------------------------------------------

def revert_entries(
    before_entries: list[dict],
    after_entries: list[dict],
    current_path: Path,
    *,
    log_fn=None,
) -> tuple[int, int]:
    """Revert changes in *current_path* XML: remove ADDs, restore EDITs.

    Returns ``(removed_count, restored_count)``.
    """
    # Compute diff: what was added/edited in AFTER vs BEFORE
    adds, edits = _compute_revert_changes(before_entries, after_entries)

    if not adds and not edits:
        if log_fn:
            log_fn("No changes to revert.")
        return 0, 0

    # Parse current file for modification
    raw = xml_parser.read_xml_raw(current_path)
    if raw is None:
        if log_fn:
            log_fn(f"Cannot read {current_path.name}", "error")
        return 0, 0

    tree, root = xml_parser.parse_tree_from_string(raw)

    removed = 0
    restored = 0

    # Collect elements to remove/modify
    to_remove = []
    for elem in xml_parser.iter_locstr(root):
        _, sid = xml_parser.get_attr(elem, config.STRINGID_ATTRS)
        if not sid:
            continue
        sid_lower = sid.lower()

        if sid_lower in adds:
            to_remove.append(elem)
        elif sid_lower in edits:
            before_entry = edits[sid_lower]
            # Use raw_attribs to preserve original format (no normalization)
            raw = before_entry.get("raw_attribs") or {}
            str_name, _ = xml_parser.get_attr(elem, config.STR_ATTRS)
            if str_name:
                raw_val = xml_parser.get_attr_value(raw, config.STR_ATTRS)
                elem.set(str_name, raw_val if raw_val else before_entry.get("str_value", ""))
                restored += 1

    # Remove ADD elements
    for elem in to_remove:
        if xml_parser.USING_LXML:
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
                removed += 1
        else:
            # stdlib fallback: blank the Str attribute
            str_name, _ = xml_parser.get_attr(elem, config.STR_ATTRS)
            if str_name:
                elem.set(str_name, "")
                removed += 1

    # Backup before revert write — abort if backup fails
    bak_path = current_path.with_suffix(current_path.suffix + ".bak")
    try:
        shutil.copy2(current_path, bak_path)
        logger.info("Backup created: %s", bak_path.name)
    except Exception as exc:
        logger.error("CANNOT create backup of %s: %s — aborting write", current_path.name, exc)
        if log_fn:
            log_fn(f"  SKIPPED revert of {current_path.name}: backup failed", "error")
        return 0, 0

    xml_parser.write_xml_tree(tree, current_path)

    if log_fn:
        log_fn(f"Reverted: {removed} removed, {restored} restored in {current_path.name}")

    return removed, restored


def _compute_revert_changes(
    before_entries: list[dict],
    after_entries: list[dict],
) -> tuple[set[str], dict[str, dict]]:
    """Return (add_sids, {sid: before_entry for edits})."""
    before_map = {e["string_id"].lower(): e for e in before_entries}
    adds: set[str] = set()
    edits: dict[str, dict] = {}

    for e in after_entries:
        sid_lower = e["string_id"].lower()
        if sid_lower not in before_map:
            adds.add(sid_lower)
        else:
            be = before_map[sid_lower]
            tgt_attribs = e.get("raw_attribs") or {}
            src_attribs = be.get("raw_attribs") or {}

            if not tgt_attribs or not src_attribs:
                # Excel fallback: compare content fields.
                # Defense-in-depth: skip if both content fields are empty
                # on either side.
                if not e.get("str_origin") and not e.get("str_value"):
                    logger.warning("Skipping revert entry %s: after str_origin and str_value both empty", sid_lower)
                    continue
                if not be.get("str_origin") and not be.get("str_value"):
                    logger.warning("Skipping revert entry %s: before str_origin and str_value both empty", sid_lower)
                    continue
                if (e.get("str_origin", "").lower() != be.get("str_origin", "").lower()
                        or e.get("str_value", "").lower() != be.get("str_value", "").lower()):
                    edits[sid_lower] = be
            elif tgt_attribs != src_attribs:
                edits[sid_lower] = be

    return adds, edits
