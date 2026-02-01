"""
LOCDEV Merger - Merge corrections from Excel back to LOCDEV XML files.

QA testers return Excel files with corrections in "Correction" column.
This module reads ONLY rows with corrections and merges them into LOCDEV
languagedata XML files using STRICT matching: StrOrigin + StringID must BOTH match.

Also tracks SUCCESS/FAIL for each correction to update the Progress Tracker.
"""

import html
import os
import re
import stat
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from lxml import etree

from openpyxl import load_workbook

logger = logging.getLogger(__name__)


def normalize_text(txt: Optional[str]) -> str:
    """
    Normalize text for consistent matching.

    Ensures TMX/Excel and XML text are IDENTICAL for matching:
    1. Unescape HTML entities (&lt; -> <, &amp; -> &, etc.)
    2. Strip leading/trailing whitespace
    3. Collapse all internal whitespace (spaces, tabs, newlines) to single space
    4. Remove &desc; markers (legacy description prefix)

    This is the same normalization used in translatexmlstable7.py and tmxtransfer11.py.

    Args:
        txt: Text to normalize

    Returns:
        Normalized text string
    """
    if not txt:
        return ""
    # Unescape HTML entities
    txt = html.unescape(str(txt))
    # Collapse all whitespace to single space and strip
    txt = re.sub(r'\s+', ' ', txt.strip())
    # Remove &desc; markers (case-insensitive)
    if txt.lower().startswith("&desc;"):
        txt = txt[6:].lstrip()
    elif txt.lower().startswith("&amp;desc;"):
        txt = txt[10:].lstrip()
    return txt


def normalize_nospace(txt: str) -> str:
    """
    Remove ALL whitespace from text for fallback matching.

    Used when exact match fails but text differs only in whitespace placement.
    Same pattern as translatexmlstable7.py nospace fallback.

    Args:
        txt: Already normalized text

    Returns:
        Text with all whitespace removed
    """
    return re.sub(r'\s+', '', txt)


def _detect_column_indices(ws) -> Dict[str, int]:
    """
    Detect column indices from header row (CASE INSENSITIVE).

    Returns dict mapping LOWERCASE column name to 1-based index.
    This ensures headers like "StringID", "STRINGID", "stringid" all work.
    """
    indices = {}
    first_row = list(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    if first_row and first_row[0]:
        for col, header in enumerate(first_row[0], 1):
            if header:
                # Store lowercase key for case-insensitive lookup
                indices[str(header).strip().lower()] = col
    return indices


def parse_corrections_from_excel(excel_path: Path) -> List[Dict]:
    """
    Parse corrections from an Excel file.

    Only extracts rows where the Correction column has a non-empty value.

    Args:
        excel_path: Path to the Excel file

    Returns:
        List of dicts with keys: string_id, str_origin, corrected
    """
    corrections = []

    try:
        wb = load_workbook(excel_path, read_only=True, data_only=True)
        ws = wb.active

        col_indices = _detect_column_indices(ws)

        # Use lowercase keys for case-insensitive matching
        str_origin_col = col_indices.get("strorigin")
        correction_col = col_indices.get("correction")
        stringid_col = col_indices.get("stringid")

        if not all([str_origin_col, correction_col, stringid_col]):
            logger.warning(
                f"Missing required columns in {excel_path.name}. "
                f"Found: {list(col_indices.keys())}"
            )
            wb.close()
            return corrections

        for row in ws.iter_rows(min_row=2, values_only=True):
            # Access by 0-based index (subtract 1 from column number)
            str_origin = row[str_origin_col - 1] if str_origin_col <= len(row) else None
            correction = row[correction_col - 1] if correction_col <= len(row) else None
            string_id = row[stringid_col - 1] if stringid_col <= len(row) else None

            # Only process rows with a correction value
            if correction and str(correction).strip() and string_id:
                corrections.append({
                    "string_id": str(string_id).strip(),
                    "str_origin": str(str_origin or "").strip(),
                    "corrected": str(correction).strip(),
                })

        wb.close()
        logger.info(f"Parsed {len(corrections)} corrections from {excel_path.name}")

    except Exception as e:
        logger.error(f"Error parsing corrections from {excel_path}: {e}")

    return corrections


def merge_corrections_to_locdev(
    xml_path: Path,
    corrections: List[Dict],
    dry_run: bool = False,
) -> Dict:
    """
    Merge corrections into a LOCDEV XML file.

    Uses STRICT matching: (StringID, normalized_StrOrigin) tuple key.
    Both must match for the correction to be applied.

    Args:
        xml_path: Path to the LOCDEV XML file
        corrections: List of correction dicts from parse_corrections_from_excel
        dry_run: If True, don't write changes, just return what would change

    Returns:
        Dict with statistics: {
            "matched": int,
            "updated": int,
            "not_found": int,
            "errors": List[str]
        }
    """
    result = {
        "matched": 0,
        "updated": 0,
        "not_found": 0,
        "errors": [],
    }

    if not corrections:
        return result

    # Build lookup: (StringID, normalized_StrOrigin) -> corrected_text
    correction_lookup = {}
    correction_lookup_nospace = {}  # Fallback for whitespace variations

    for c in corrections:
        sid = c["string_id"]
        origin_norm = normalize_text(c["str_origin"])
        origin_nospace = normalize_nospace(origin_norm)

        correction_lookup[(sid, origin_norm)] = c["corrected"]
        correction_lookup_nospace[(sid, origin_nospace)] = c["corrected"]

    try:
        # Parse XML with recovery mode
        parser = etree.XMLParser(
            resolve_entities=False,
            load_dtd=False,
            no_network=True,
            recover=True,
        )
        tree = etree.parse(str(xml_path), parser)
        root = tree.getroot()

        changed = False

        for loc in root.iter("LocStr"):
            sid = loc.get("StringId", "").strip()
            orig = normalize_text(loc.get("StrOrigin", ""))
            orig_nospace = normalize_nospace(orig)
            key = (sid, orig)
            key_nospace = (sid, orig_nospace)

            # Try exact match first, then nospace fallback
            new_str = None
            if key in correction_lookup:
                new_str = correction_lookup[key]
            elif key_nospace in correction_lookup_nospace:
                new_str = correction_lookup_nospace[key_nospace]
                logger.debug(f"Matched via nospace fallback: StringId={sid}")

            if new_str is not None:
                result["matched"] += 1
                old_str = loc.get("Str", "")

                if new_str != old_str:
                    if not dry_run:
                        loc.set("Str", new_str)
                    result["updated"] += 1
                    changed = True
                    logger.debug(f"Updated StringId={sid}: '{old_str}' -> '{new_str}'")

        # Count corrections that didn't match any XML entry
        result["not_found"] = len(corrections) - result["matched"]

        if changed and not dry_run:
            # Make file writable if read-only (LOC folder files are often read-only)
            try:
                current_mode = os.stat(xml_path).st_mode
                if not current_mode & stat.S_IWRITE:
                    os.chmod(xml_path, current_mode | stat.S_IWRITE)
                    logger.debug(f"Made {xml_path.name} writable")
            except Exception as e:
                logger.warning(f"Could not make {xml_path.name} writable: {e}")

            tree.write(str(xml_path), encoding="utf-8", xml_declaration=False, pretty_print=True)
            logger.info(f"Saved {xml_path.name}: {result['updated']} entries updated")

    except Exception as e:
        result["errors"].append(str(e))
        logger.error(f"Error merging to {xml_path}: {e}")

    return result


def get_file_mod_time(file_path: Path) -> Optional[datetime]:
    """
    Get the modification time of a file.

    Args:
        file_path: Path to the file

    Returns:
        datetime of last modification, or None if file doesn't exist
    """
    try:
        if file_path.exists():
            mtime = os.path.getmtime(file_path)
            return datetime.fromtimestamp(mtime)
    except Exception as e:
        logger.warning(f"Could not get mod time for {file_path}: {e}")
    return None


def merge_all_corrections(
    submit_folder: Path,
    locdev_folder: Path,
    dry_run: bool = False,
) -> Dict:
    """
    Process all Excel files in ToSubmit folder and merge corrections to LOCDEV.

    Matches Excel files to LOCDEV XML files by language code:
    - languagedata_FRE.xlsx -> languagedata_fre.xml (or languagedata_FRE.xml)
    - LanguageData_GER.xlsx -> languagedata_ger.xml

    Args:
        submit_folder: Path to ToSubmit folder containing Excel files
        locdev_folder: Path to LOCDEV folder containing XML files
        dry_run: If True, don't write changes, just report what would change

    Returns:
        Dict with overall results: {
            "files_processed": int,
            "total_corrections": int,  # Total rows with Correction values
            "total_success": int,      # Successfully merged (matched + updated)
            "total_fail": int,         # Failed to match in LOCDEV
            "errors": List[str],
            "file_results": Dict[str, Dict],  # Per-language results
            "file_mod_times": Dict[str, datetime],  # Per-language file mod times
        }
    """
    results = {
        "files_processed": 0,
        "total_corrections": 0,
        "total_success": 0,
        "total_fail": 0,
        "errors": [],
        "file_results": {},
        "file_mod_times": {},
    }

    if not submit_folder.exists():
        results["errors"].append(f"ToSubmit folder not found: {submit_folder}")
        return results

    if not locdev_folder.exists():
        results["errors"].append(f"LOCDEV folder not found: {locdev_folder}")
        return results

    # Find all Excel files
    excel_files = list(submit_folder.glob("languagedata_*.xlsx"))
    excel_files.extend(submit_folder.glob("LanguageData_*.xlsx"))

    # Remove duplicates (case-insensitive)
    seen = set()
    unique_files = []
    for f in excel_files:
        if f.name.lower() not in seen:
            seen.add(f.name.lower())
            unique_files.append(f)

    for excel_path in unique_files:
        # Extract language code from filename
        name = excel_path.stem  # e.g., "languagedata_FRE" or "LanguageData_GER"
        if name.lower().startswith("languagedata_"):
            lang_code = name[13:]  # After "languagedata_"
        else:
            continue

        # Get file modification time for weekly tracking
        file_mod_time = get_file_mod_time(excel_path)
        if file_mod_time:
            results["file_mod_times"][lang_code] = file_mod_time

        # Find corresponding LOCDEV XML file
        xml_candidates = [
            locdev_folder / f"languagedata_{lang_code.lower()}.xml",
            locdev_folder / f"languagedata_{lang_code.upper()}.xml",
            locdev_folder / f"languagedata_{lang_code}.xml",
        ]

        xml_path = None
        for candidate in xml_candidates:
            if candidate.exists():
                xml_path = candidate
                break

        if not xml_path:
            results["errors"].append(f"No LOCDEV XML found for {excel_path.name}")
            continue

        # Parse corrections from Excel
        corrections = parse_corrections_from_excel(excel_path)

        if not corrections:
            logger.info(f"No corrections found in {excel_path.name}")
            results["file_results"][lang_code] = {
                "corrections": 0,
                "success": 0,
                "fail": 0,
                "matched": 0,
                "updated": 0,
                "not_found": 0,
                "errors": ["No corrections found"],
            }
            continue

        # Merge corrections to LOCDEV
        file_result = merge_corrections_to_locdev(xml_path, corrections, dry_run)

        # Calculate success/fail counts
        # Success = corrections that matched in LOCDEV (whether updated or already same)
        # Fail = corrections that did NOT match in LOCDEV
        corrections_count = len(corrections)
        success_count = file_result["matched"]
        fail_count = file_result["not_found"]

        # Add to file result
        file_result["corrections"] = corrections_count
        file_result["success"] = success_count
        file_result["fail"] = fail_count

        results["file_results"][lang_code] = file_result

        results["files_processed"] += 1
        results["total_corrections"] += corrections_count
        results["total_success"] += success_count
        results["total_fail"] += fail_count
        results["errors"].extend(file_result["errors"])

        logger.info(
            f"Processed {lang_code}: corrections={corrections_count}, "
            f"success={success_count}, fail={fail_count}"
        )

    return results


def print_merge_report(results: Dict) -> None:
    """
    Print a formatted terminal report of merge results.

    Args:
        results: The dict returned by merge_all_corrections()
    """
    # Box drawing characters for nice borders
    H = "═"  # Horizontal
    V = "║"  # Vertical
    TL = "╔"  # Top-left
    TR = "╗"  # Top-right
    BL = "╚"  # Bottom-left
    BR = "╝"  # Bottom-right
    LT = "╠"  # Left-T
    RT = "╣"  # Right-T
    TT = "╦"  # Top-T
    BT = "╩"  # Bottom-T
    X = "╬"   # Cross

    width = 72

    print()
    print(TL + H * (width - 2) + TR)
    title = "LOCDEV MERGE REPORT"
    print(V + title.center(width - 2) + V)
    print(LT + H * (width - 2) + RT)

    # Column widths
    lang_w = 14
    corr_w = 14
    succ_w = 12
    fail_w = 10
    rate_w = 12

    # Header
    header = f"{V} {'LANGUAGE':<{lang_w}} {'CORRECTIONS':>{corr_w}} {'SUCCESS':>{succ_w}} {'FAIL':>{fail_w}} {'RATE':>{rate_w}} {V}"
    print(header)
    print(LT + H * (width - 2) + RT)

    # Per-language rows
    file_results = results.get("file_results", {})
    for lang_code in sorted(file_results.keys()):
        file_result = file_results[lang_code]
        corrections = file_result.get("corrections", 0)
        success = file_result.get("success", 0)
        fail = file_result.get("fail", 0)
        rate = (success / corrections * 100) if corrections > 0 else 0.0

        # Color indicators
        if rate >= 95:
            status = "●"  # Green indicator
        elif rate >= 80:
            status = "◐"  # Half indicator
        else:
            status = "○"  # Empty indicator

        row = f"{V} {lang_code.upper():<{lang_w}} {corrections:>{corr_w},} {success:>{succ_w},} {fail:>{fail_w},} {rate:>{rate_w - 2}.1f}% {status} {V}"
        print(row)

    # Separator before totals
    print(LT + H * (width - 2) + RT)

    # Totals
    total_corr = results.get("total_corrections", 0)
    total_succ = results.get("total_success", 0)
    total_fail = results.get("total_fail", 0)
    total_rate = (total_succ / total_corr * 100) if total_corr > 0 else 0.0

    total_row = f"{V} {'TOTAL':<{lang_w}} {total_corr:>{corr_w},} {total_succ:>{succ_w},} {total_fail:>{fail_w},} {total_rate:>{rate_w - 2}.1f}%   {V}"
    print(total_row)
    print(BL + H * (width - 2) + BR)

    # Errors section (if any)
    errors = results.get("errors", [])
    if errors:
        print()
        print("ERRORS:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"  × {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")

    # Legend
    print()
    print("Legend: ● ≥95% success  ◐ ≥80% success  ○ <80% success")
    print()
