"""
LOCDEV Merger - Merge corrections from Excel back to LOCDEV XML files.

QA testers return Excel files with corrections in "Correction" column.
This module reads ONLY rows with corrections and merges them into LOCDEV
languagedata XML files using STRICT matching: StrOrigin + StringID must BOTH match.
"""

import html
import re
import logging
from pathlib import Path
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

    This is the same normalization used in translatexmlstable7.py.

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
    return txt


def _detect_column_indices(ws) -> Dict[str, int]:
    """
    Detect column indices from header row.

    Returns dict mapping column name to 1-based index.
    """
    indices = {}
    first_row = list(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    if first_row and first_row[0]:
        for col, header in enumerate(first_row[0], 1):
            if header:
                indices[str(header).strip()] = col
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

        str_origin_col = col_indices.get("StrOrigin")
        correction_col = col_indices.get("Correction")
        stringid_col = col_indices.get("StringID")

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
    correction_lookup = {
        (c["string_id"], normalize_text(c["str_origin"])): c["corrected"]
        for c in corrections
    }

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
            key = (sid, orig)

            if key in correction_lookup:
                result["matched"] += 1
                new_str = correction_lookup[key]
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
            tree.write(str(xml_path), encoding="utf-8", xml_declaration=False, pretty_print=True)
            logger.info(f"Saved {xml_path.name}: {result['updated']} entries updated")

    except Exception as e:
        result["errors"].append(str(e))
        logger.error(f"Error merging to {xml_path}: {e}")

    return result


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
            "total_matched": int,
            "total_updated": int,
            "total_not_found": int,
            "errors": List[str],
            "file_results": Dict[str, Dict]
        }
    """
    results = {
        "files_processed": 0,
        "total_matched": 0,
        "total_updated": 0,
        "total_not_found": 0,
        "errors": [],
        "file_results": {},
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
                "matched": 0,
                "updated": 0,
                "not_found": 0,
                "errors": ["No corrections found"],
            }
            continue

        # Merge corrections to LOCDEV
        file_result = merge_corrections_to_locdev(xml_path, corrections, dry_run)
        results["file_results"][lang_code] = file_result

        results["files_processed"] += 1
        results["total_matched"] += file_result["matched"]
        results["total_updated"] += file_result["updated"]
        results["total_not_found"] += file_result["not_found"]
        results["errors"].extend(file_result["errors"])

        logger.info(
            f"Processed {lang_code}: matched={file_result['matched']}, "
            f"updated={file_result['updated']}, not_found={file_result['not_found']}"
        )

    return results
