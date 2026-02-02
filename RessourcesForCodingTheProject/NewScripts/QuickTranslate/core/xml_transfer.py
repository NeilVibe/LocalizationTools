"""
XML Transfer - Merge corrections to target XML files.

Ported from LanguageDataExporter's locdev_merger.py.
Writes corrections back to XML files using STRICT or StringID-only matching.
"""

import html
import os
import re
import stat
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Try lxml first (more robust), fallback to standard library
try:
    from lxml import etree
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as etree
    USING_LXML = False

from openpyxl import load_workbook

import config
from .text_utils import normalize_text, normalize_nospace

logger = logging.getLogger(__name__)

# Import from config (single source of truth)
SCRIPT_CATEGORIES = config.SCRIPT_CATEGORIES
SCRIPT_EXCLUDE_SUBFOLDERS = config.SCRIPT_EXCLUDE_SUBFOLDERS


def merge_corrections_to_xml(
    xml_path: Path,
    corrections: List[Dict],
    dry_run: bool = False,
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
        sid = c["string_id"]
        origin_norm = normalize_text(c.get("str_origin", ""))
        origin_nospace = normalize_nospace(origin_norm)
        category = c.get("category", "Uncategorized")

        correction_lookup[(sid, origin_norm)] = (c["corrected"], category, i)
        correction_lookup_nospace[(sid, origin_nospace)] = (c["corrected"], category, i)

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

        for loc in all_elements:
            # Case-insensitive attribute access
            sid = (loc.get("StringId") or loc.get("StringID") or
                   loc.get("stringid") or loc.get("STRINGID") or
                   loc.get("Stringid") or loc.get("stringId") or "").strip()
            orig_raw = (loc.get("StrOrigin") or loc.get("Strorigin") or
                        loc.get("strorigin") or loc.get("STRORIGIN") or "")
            orig = normalize_text(orig_raw)
            orig_nospace = normalize_nospace(orig)
            key = (sid, orig)
            key_nospace = (sid, orig_nospace)

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

                if new_str != old_str:
                    if not dry_run:
                        loc.set("Str", new_str)
                    result["updated"] += 1
                    result["by_category"][category]["updated"] += 1
                    changed = True
                    result["details"].append({
                        "string_id": sid,
                        "status": "UPDATED",
                        "old": old_str[:50] + "..." if len(old_str) > 50 else old_str,
                        "new": new_str[:50] + "..." if len(new_str) > 50 else new_str,
                    })
                    logger.debug(f"Updated StringId={sid}: '{old_str}' -> '{new_str}'")
                else:
                    result["details"].append({
                        "string_id": sid,
                        "status": "UNCHANGED",
                        "old": old_str[:50] + "..." if len(old_str) > 50 else old_str,
                        "new": "(same)",
                    })

        # Count corrections that didn't match
        for i, c in enumerate(corrections):
            if not correction_matched[i]:
                category = c.get("category", "Uncategorized")
                result["by_category"][category]["not_found"] += 1
                result["details"].append({
                    "string_id": c["string_id"],
                    "status": "NOT_FOUND",
                    "old": "",
                    "new": c["corrected"][:50] + "..." if len(c["corrected"]) > 50 else c["corrected"],
                })

        result["not_found"] = len(corrections) - result["matched"]

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
        "not_found": 0,
        "errors": [],
        "by_category": {},
        "details": [],
    }

    if not corrections:
        return result

    # Filter corrections to SCRIPT TYPE only (and not in excluded subfolders)
    script_corrections = []

    for c in corrections:
        sid = c["string_id"]
        category = stringid_to_category.get(sid, "Uncategorized")
        subfolder = stringid_to_subfolder.get(sid, "") if stringid_to_subfolder else ""

        # Check if in SCRIPT categories (Dialog/Sequencer)
        if category not in SCRIPT_CATEGORIES:
            result["skipped_non_script"] += 1
            result["details"].append({
                "string_id": sid,
                "status": "SKIPPED_NON_SCRIPT",
                "old": f"Category: {category}",
                "new": c["corrected"][:50] + "..." if len(c["corrected"]) > 50 else c["corrected"],
            })
            logger.debug(f"Skipped non-SCRIPT StringID={sid} (category={category})")
            continue

        # Check if subfolder is in exclusion list
        if subfolder in SCRIPT_EXCLUDE_SUBFOLDERS:
            result["skipped_excluded"] += 1
            result["details"].append({
                "string_id": sid,
                "status": "SKIPPED_EXCLUDED",
                "old": f"Subfolder: {subfolder}",
                "new": c["corrected"][:50] + "..." if len(c["corrected"]) > 50 else c["corrected"],
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

    # Build StringID-only lookup
    correction_lookup = {}
    correction_matched = {}

    for c in script_corrections:
        sid = c["string_id"]
        correction_lookup[sid] = c["corrected"]
        correction_matched[sid] = False

        # Initialize category stats
        category = c.get("category", "Uncategorized")
        if category not in result["by_category"]:
            result["by_category"][category] = {"matched": 0, "updated": 0, "not_found": 0}

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

            # StringID-only matching
            if sid in correction_lookup:
                new_str = correction_lookup[sid]
                correction_matched[sid] = True

                category = stringid_to_category.get(sid, "Uncategorized")

                result["matched"] += 1
                if category in result["by_category"]:
                    result["by_category"][category]["matched"] += 1

                old_str = (loc.get("Str") or loc.get("str") or
                           loc.get("STR") or "")

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
                        "old": old_str[:50] + "..." if len(old_str) > 50 else old_str,
                        "new": new_str[:50] + "..." if len(new_str) > 50 else new_str,
                    })
                    logger.debug(f"Updated StringId={sid}: '{old_str}' -> '{new_str}'")
                else:
                    result["details"].append({
                        "string_id": sid,
                        "status": "UNCHANGED",
                        "old": old_str[:50] + "..." if len(old_str) > 50 else old_str,
                        "new": "(same)",
                    })

        # Count unmatched corrections
        for sid, matched in correction_matched.items():
            if not matched:
                category = stringid_to_category.get(sid, "Uncategorized")
                result["not_found"] += 1
                if category in result["by_category"]:
                    result["by_category"][category]["not_found"] += 1
                result["details"].append({
                    "string_id": sid,
                    "status": "NOT_FOUND",
                    "old": "",
                    "new": correction_lookup[sid][:50] + "..." if len(correction_lookup[sid]) > 50 else correction_lookup[sid],
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


def transfer_folder_to_folder(
    source_folder: Path,
    target_folder: Path,
    stringid_to_category: Optional[Dict[str, str]] = None,
    stringid_to_subfolder: Optional[Dict[str, str]] = None,
    match_mode: str = "strict",
    dry_run: bool = False,
    progress_callback=None,
) -> Dict:
    """
    Transfer corrections from source folder to target folder.

    Matches files by name pattern: languagedata_*.xml

    Args:
        source_folder: Folder containing correction XML/Excel files
        target_folder: Folder containing target XML files to update
        stringid_to_category: Category mapping (required for stringid_only mode)
        stringid_to_subfolder: Subfolder mapping (for exclusion filtering)
        match_mode: "strict" or "stringid_only"
        dry_run: If True, don't write changes
        progress_callback: Optional callback for progress updates

    Returns:
        Dict with overall results
    """
    from .xml_io import parse_folder_xml_files
    from .excel_io import read_corrections_from_excel

    results = {
        "files_processed": 0,
        "total_corrections": 0,
        "total_matched": 0,
        "total_updated": 0,
        "total_not_found": 0,
        "total_skipped": 0,
        "total_skipped_excluded": 0,
        "errors": [],
        "file_results": {},
    }

    if not source_folder.exists():
        results["errors"].append(f"Source folder not found: {source_folder}")
        return results

    if not target_folder.exists():
        results["errors"].append(f"Target folder not found: {target_folder}")
        return results

    # Find source files
    xml_files = list(source_folder.glob("*.xml"))
    excel_files = list(source_folder.glob("*.xlsx"))
    excel_files.extend(source_folder.glob("*.xls"))

    all_sources = xml_files + excel_files
    total = len(all_sources)

    if total == 0:
        results["errors"].append(f"No XML or Excel files found in {source_folder}")
        return results

    for i, source_file in enumerate(all_sources):
        if progress_callback:
            progress_callback(f"Processing {source_file.name}... ({i+1}/{total})")

        # Parse corrections from source
        if source_file.suffix.lower() == ".xml":
            from .xml_io import parse_corrections_from_xml
            corrections = parse_corrections_from_xml(source_file)
        else:
            corrections = read_corrections_from_excel(source_file)

        if not corrections:
            logger.info(f"No corrections found in {source_file.name}")
            continue

        # Extract language code from filename
        name = source_file.stem.lower()
        lang_code = None
        if name.startswith("languagedata_"):
            lang_code = name[13:]
        elif "_" in name:
            lang_code = name.split("_")[-1]

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
            # Try to find any matching XML
            target_xmls = list(target_folder.glob("*.xml"))
            if len(target_xmls) == 1:
                target_xml = target_xmls[0]
            elif lang_code:
                results["errors"].append(f"No target XML found for {source_file.name}")
                continue

        if not target_xml:
            results["errors"].append(f"No target XML found for {source_file.name}")
            continue

        # Apply corrections
        if match_mode == "stringid_only" and stringid_to_category:
            file_result = merge_corrections_stringid_only(
                target_xml, corrections, stringid_to_category, stringid_to_subfolder, dry_run
            )
            results["total_skipped"] += file_result.get("skipped_non_script", 0)
            results["total_skipped_excluded"] += file_result.get("skipped_excluded", 0)
        else:
            file_result = merge_corrections_to_xml(target_xml, corrections, dry_run)

        # Aggregate results
        results["files_processed"] += 1
        results["total_corrections"] += len(corrections)
        results["total_matched"] += file_result["matched"]
        results["total_updated"] += file_result["updated"]
        results["total_not_found"] += file_result["not_found"]
        results["errors"].extend(file_result["errors"])

        results["file_results"][source_file.name] = {
            "target": target_xml.name,
            "corrections": len(corrections),
            **file_result,
        }

    return results


def transfer_file_to_file(
    source_file: Path,
    target_file: Path,
    stringid_to_category: Optional[Dict[str, str]] = None,
    stringid_to_subfolder: Optional[Dict[str, str]] = None,
    match_mode: str = "strict",
    dry_run: bool = False,
) -> Dict:
    """
    Transfer corrections from single source file to single target file.

    Args:
        source_file: Excel or XML file with corrections
        target_file: Target XML file to update
        stringid_to_category: Category mapping (required for stringid_only mode)
        stringid_to_subfolder: Subfolder mapping (for exclusion filtering)
        match_mode: "strict" or "stringid_only"
        dry_run: If True, don't write changes

    Returns:
        Dict with results
    """
    from .xml_io import parse_corrections_from_xml
    from .excel_io import read_corrections_from_excel

    # Parse corrections from source
    if source_file.suffix.lower() == ".xml":
        corrections = parse_corrections_from_xml(source_file)
    else:
        corrections = read_corrections_from_excel(source_file)

    if not corrections:
        return {
            "matched": 0,
            "updated": 0,
            "not_found": 0,
            "errors": ["No corrections found in source file"],
            "details": [],
        }

    # Apply corrections
    if match_mode == "stringid_only" and stringid_to_category:
        result = merge_corrections_stringid_only(
            target_file, corrections, stringid_to_category, stringid_to_subfolder, dry_run
        )
    else:
        result = merge_corrections_to_xml(target_file, corrections, dry_run)

    result["corrections_count"] = len(corrections)
    return result


def format_transfer_report(results: Dict, mode: str = "folder") -> str:
    """
    Format transfer results as a human-readable report.

    Args:
        results: Results from transfer_folder_to_folder or transfer_file_to_file
        mode: "folder" or "file"

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

    lines.append("")
    lines.append(TL + H * (width - 2) + TR)
    title = "QUICKTRANSLATE TRANSFER REPORT"
    lines.append(V + title.center(width - 2) + V)
    lines.append(LT + H * (width - 2) + RT)

    if mode == "folder":
        lines.append(V + f" Files Processed: {results.get('files_processed', 0)}".ljust(width - 2) + V)
        lines.append(V + f" Total Corrections: {results.get('total_corrections', 0)}".ljust(width - 2) + V)
        lines.append(V + f" Matched: {results.get('total_matched', 0)}".ljust(width - 2) + V)
        lines.append(V + f" Updated: {results.get('total_updated', 0)}".ljust(width - 2) + V)
        lines.append(V + f" Not Found: {results.get('total_not_found', 0)}".ljust(width - 2) + V)
        if results.get('total_skipped', 0) > 0:
            lines.append(V + f" Skipped (non-SCRIPT): {results.get('total_skipped', 0)}".ljust(width - 2) + V)

        # Per-file breakdown
        file_results = results.get("file_results", {})
        if file_results:
            lines.append(LT + H * (width - 2) + RT)
            lines.append(V + " PER-FILE BREAKDOWN:".ljust(width - 2) + V)
            for fname, fresult in file_results.items():
                target = fresult.get("target", "?")
                matched = fresult.get("matched", 0)
                updated = fresult.get("updated", 0)
                lines.append(V + f"   {fname} -> {target}".ljust(width - 2) + V)
                lines.append(V + f"     Matched: {matched}, Updated: {updated}".ljust(width - 2) + V)

    else:
        # Single file mode
        lines.append(V + f" Corrections: {results.get('corrections_count', 0)}".ljust(width - 2) + V)
        lines.append(V + f" Matched: {results.get('matched', 0)}".ljust(width - 2) + V)
        lines.append(V + f" Updated: {results.get('updated', 0)}".ljust(width - 2) + V)
        lines.append(V + f" Not Found: {results.get('not_found', 0)}".ljust(width - 2) + V)
        if results.get('skipped_non_script', 0) > 0:
            lines.append(V + f" Skipped (non-SCRIPT): {results.get('skipped_non_script', 0)}".ljust(width - 2) + V)

    # Success rate
    total = results.get('total_corrections', results.get('corrections_count', 0))
    matched = results.get('total_matched', results.get('matched', 0))
    rate = (matched / total * 100) if total > 0 else 0.0

    lines.append(LT + H * (width - 2) + RT)
    rate_str = f" SUCCESS RATE: {rate:.1f}%"
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
            lines.append(f"  × {error}")
        if len(errors) > 5:
            lines.append(f"  ... and {len(errors) - 5} more errors")

    lines.append("")
    lines.append("Legend: ● ≥95% success  ◐ ≥80% success  ○ <80% success")
    lines.append("")

    return "\n".join(lines)
