"""
Transfer Module
===============
Transfer QA files from QAfolderOLD + QAfolderNEW to QAfolder.

Handles:
- Row matching (STRINGID + Translation, or Translation only)
- Item-specific matching (ItemName + ItemDesc)
- Data transfer (STATUS, COMMENT, SCREENSHOT)
- Duplicate translation detection
"""

import shutil
from pathlib import Path
from typing import Dict, Tuple, Optional, List
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    QA_FOLDER, QA_FOLDER_OLD, QA_FOLDER_NEW,
    TRANSLATION_COLS, ITEM_DESC_COLS, CATEGORIES,
    load_tester_mapping
)
from core.discovery import discover_qa_folders_in
from core.excel_ops import safe_load_workbook, find_column_by_header


# =============================================================================
# STRINGID NORMALIZATION
# =============================================================================

def sanitize_stringid_for_match(value) -> str:
    """
    Normalize STRINGID for comparison during transfer.

    Handles:
    - None values
    - INT vs STRING type mismatch
    - Scientific notation (e.g., "1.23E+15")
    - Leading/trailing whitespace
    """
    if value is None:
        return ""
    s = str(value).strip()
    # Handle scientific notation
    if 'e' in s.lower():
        try:
            s = str(int(float(s)))
        except (ValueError, OverflowError):
            pass
    return s


# =============================================================================
# LANGUAGE DETECTION
# =============================================================================

def is_english_file(xlsx_path: Path) -> bool:
    """Detect if file is English based on filename."""
    name = str(xlsx_path).upper()
    # Check for explicit language markers
    if "_ENG" in name or "_EN." in name or "ENG_" in name:
        return True
    # Check for non-English markers
    non_eng = ["_FRE", "_ZHO", "_JPN", "_DEU", "_SPA", "_ITA", "_POR", "_RUS", "_KOR"]
    for marker in non_eng:
        if marker in name:
            return False
    # Default to English if no markers found
    return True


def get_translation_column(category: str, is_english: bool) -> int:
    """Get translation column index based on category and language."""
    cols = TRANSLATION_COLS.get(category, {"eng": 2, "other": 3})
    return cols["eng"] if is_english else cols["other"]


# =============================================================================
# ROW MATCHING
# =============================================================================

def find_file_in_folder(filename: str, folder_path: Path) -> Optional[str]:
    """
    Find a file in a folder by name (case-insensitive).

    Returns filename (not full path) if found, None otherwise.
    """
    if not folder_path or not folder_path.exists():
        return None

    filename_lower = filename.lower()
    for f in folder_path.iterdir():
        if f.is_file() and f.name.lower() == filename_lower:
            return f.name  # Return filename only, not full path
    return None


def find_matching_row_for_transfer(
    old_row_data: Dict,
    new_ws,
    category: str,
    is_english: bool
) -> Tuple[Optional[int], Optional[str]]:
    """
    Find matching row in NEW file for OLD row data.

    Uses 2-step cascade:
    1. STRINGID + Translation match (exact)
    2. Translation only match (fallback)

    Args:
        old_row_data: dict with {stringid, translation, row_num}
        new_ws: New worksheet to search in
        category: Category name for column detection
        is_english: Whether file is English

    Returns:
        Tuple of (new_row_num, match_type) or (None, None)
        match_type: "stringid+trans" or "trans_only"
    """
    old_stringid = sanitize_stringid_for_match(old_row_data.get("stringid"))
    old_trans = str(old_row_data.get("translation", "")).strip()

    if not old_trans:
        return None, None

    trans_col = get_translation_column(category, is_english)
    stringid_col = find_column_by_header(new_ws, "STRINGID")

    # Step 1: Try STRINGID + Translation match
    if old_stringid and stringid_col:
        for row in range(2, new_ws.max_row + 1):
            new_stringid = sanitize_stringid_for_match(new_ws.cell(row, stringid_col).value)
            new_trans = str(new_ws.cell(row, trans_col).value or "").strip()

            if new_stringid == old_stringid and new_trans == old_trans:
                return row, "stringid+trans"

    # Step 2: Fall back to Translation only
    for row in range(2, new_ws.max_row + 1):
        new_trans = str(new_ws.cell(row, trans_col).value or "").strip()
        if new_trans == old_trans:
            return row, "trans_only"

    return None, None


def find_matching_row_for_item_transfer(
    old_row_data: Dict,
    new_ws,
    is_english: bool
) -> Tuple[Optional[int], Optional[str]]:
    """
    Item-specific matching: requires BOTH ItemName AND ItemDesc to match.

    Uses 2-step cascade:
    1. ItemName + ItemDesc + STRINGID (all 3 must match)
    2. ItemName + ItemDesc (both must match, no STRINGID required)

    Args:
        old_row_data: dict with {item_name, item_desc, stringid, row_num}
        new_ws: New worksheet to search in
        is_english: Whether file is English

    Returns:
        Tuple of (new_row_num, match_type) or (None, None)
        match_type: "name+desc+stringid" or "name+desc"
    """
    old_stringid = sanitize_stringid_for_match(old_row_data.get("stringid"))
    old_item_name = str(old_row_data.get("item_name", "")).strip()
    old_item_desc = str(old_row_data.get("item_desc", "")).strip()

    # Need at least ItemName to match
    if not old_item_name:
        return None, None

    name_col = TRANSLATION_COLS["Item"]["eng"] if is_english else TRANSLATION_COLS["Item"]["other"]
    desc_col = ITEM_DESC_COLS["eng"] if is_english else ITEM_DESC_COLS["other"]
    stringid_col = find_column_by_header(new_ws, "STRINGID")

    # Step 1: Try ItemName + ItemDesc + STRINGID match
    if old_stringid and stringid_col:
        for row in range(2, new_ws.max_row + 1):
            new_stringid = sanitize_stringid_for_match(new_ws.cell(row, stringid_col).value)
            new_name = str(new_ws.cell(row, name_col).value or "").strip()
            new_desc = str(new_ws.cell(row, desc_col).value or "").strip()

            if new_stringid == old_stringid and new_name == old_item_name and new_desc == old_item_desc:
                return row, "name+desc+stringid"

    # Step 2: Fall back to ItemName + ItemDesc only
    for row in range(2, new_ws.max_row + 1):
        new_name = str(new_ws.cell(row, name_col).value or "").strip()
        new_desc = str(new_ws.cell(row, desc_col).value or "").strip()

        if new_name == old_item_name and new_desc == old_item_desc:
            return row, "name+desc"

    return None, None


# =============================================================================
# SHEET TRANSFER
# =============================================================================

def transfer_sheet_data(
    old_ws,
    new_ws,
    category: str,
    is_english: bool,
    old_folder_path: Path = None
) -> Dict:
    """
    Transfer data from OLD sheet to NEW sheet.

    Transfers: COMMENT, STATUS, SCREENSHOT (with hyperlinks).

    Args:
        old_ws: OLD worksheet
        new_ws: NEW worksheet (modified in place)
        category: Category name
        is_english: Whether file is English
        old_folder_path: Path to old folder for hyperlink fixing

    Returns:
        Stats dict with counts
    """
    stats = {
        "total": 0,
        "stringid_match": 0,
        "trans_only": 0,
        "unmatched": 0,
        "name_desc_stringid_match": 0,
        "name_desc_match": 0,
    }

    # Find columns
    old_comment_col = find_column_by_header(old_ws, "COMMENT")
    old_status_col = find_column_by_header(old_ws, "STATUS")
    old_screenshot_col = find_column_by_header(old_ws, "SCREENSHOT")
    old_stringid_col = find_column_by_header(old_ws, "STRINGID")

    new_comment_col = find_column_by_header(new_ws, "COMMENT")
    new_status_col = find_column_by_header(new_ws, "STATUS")
    new_screenshot_col = find_column_by_header(new_ws, "SCREENSHOT")

    # Get translation column for matching
    old_trans_col = get_translation_column(category, is_english)

    # Item category needs ItemDesc column too
    is_item_category = category.lower() == "item"
    old_desc_col = None
    if is_item_category:
        old_desc_col = ITEM_DESC_COLS["eng"] if is_english else ITEM_DESC_COLS["other"]

    # Process each row with data
    for old_row in range(2, old_ws.max_row + 1):
        old_comment = old_ws.cell(old_row, old_comment_col).value if old_comment_col else None
        old_status = old_ws.cell(old_row, old_status_col).value if old_status_col else None
        old_screenshot = old_ws.cell(old_row, old_screenshot_col).value if old_screenshot_col else None
        old_screenshot_hyperlink = old_ws.cell(old_row, old_screenshot_col).hyperlink if old_screenshot_col else None

        # Skip rows with no data to transfer
        if not any([old_comment, old_status, old_screenshot]):
            continue

        stats["total"] += 1

        # Build old row data for matching
        old_row_data = {
            "stringid": old_ws.cell(old_row, old_stringid_col).value if old_stringid_col else None,
            "translation": old_ws.cell(old_row, old_trans_col).value,
            "row_num": old_row,
        }

        # For Item category, add ItemName and ItemDesc
        if is_item_category:
            old_row_data["item_name"] = old_ws.cell(old_row, old_trans_col).value
            old_row_data["item_desc"] = old_ws.cell(old_row, old_desc_col).value if old_desc_col else ""

        # Find matching row in NEW file
        if is_item_category:
            new_row, match_type = find_matching_row_for_item_transfer(old_row_data, new_ws, is_english)
        else:
            new_row, match_type = find_matching_row_for_transfer(old_row_data, new_ws, category, is_english)

        if new_row is None:
            stats["unmatched"] += 1
            continue

        # Track match type
        if match_type == "stringid+trans":
            stats["stringid_match"] += 1
        elif match_type == "trans_only":
            stats["trans_only"] += 1
        elif match_type == "name+desc+stringid":
            stats["name_desc_stringid_match"] += 1
        elif match_type == "name+desc":
            stats["name_desc_match"] += 1

        # Transfer data
        if new_comment_col and old_comment:
            new_ws.cell(new_row, new_comment_col, old_comment)
        if new_status_col and old_status:
            new_ws.cell(new_row, new_status_col, old_status)
        if new_screenshot_col and old_screenshot:
            new_cell = new_ws.cell(new_row, new_screenshot_col, old_screenshot)
            # Transfer hyperlink
            if old_screenshot_hyperlink:
                new_cell.hyperlink = old_screenshot_hyperlink.target
            elif old_folder_path:
                # AUTO-FIX: Try to find file in old folder
                filename = str(old_screenshot).strip()
                actual_file = find_file_in_folder(filename, old_folder_path)
                if actual_file:
                    new_cell.hyperlink = actual_file

    return stats


# =============================================================================
# DUPLICATE DETECTION
# =============================================================================

def detect_duplicate_translations(old_wb, category: str, is_english: bool) -> Dict:
    """
    Detect translations that appear multiple times with DIFFERENT comments.

    This helps identify potential data loss during transfer where we take
    the first match but other comments might be lost.

    Args:
        old_wb: OLD workbook
        category: Category name
        is_english: Whether file is English

    Returns:
        dict: {sheet_name: [(translation, [comment1, comment2, ...]), ...]}
    """
    duplicates = {}

    for sheet_name in old_wb.sheetnames:
        old_ws = old_wb[sheet_name]
        trans_col = get_translation_column(category, is_english)
        comment_col = find_column_by_header(old_ws, "COMMENT")

        if not comment_col:
            continue

        # Group comments by translation
        trans_to_comments = {}
        for row in range(2, old_ws.max_row + 1):
            trans = str(old_ws.cell(row, trans_col).value or "").strip()
            comment = str(old_ws.cell(row, comment_col).value or "").strip()

            if not trans or not comment:
                continue

            if trans not in trans_to_comments:
                trans_to_comments[trans] = set()
            trans_to_comments[trans].add(comment)

        # Find translations with multiple different comments
        sheet_duplicates = []
        for trans, comments in trans_to_comments.items():
            if len(comments) > 1:
                sheet_duplicates.append((trans, sorted(comments)))

        if sheet_duplicates:
            duplicates[sheet_name] = sheet_duplicates

    return duplicates


def write_duplicate_translation_report(
    duplicates: Dict,
    output_folder: Path,
    username: str,
    category: str
) -> Optional[Path]:
    """Write a report file listing translations with different comments."""
    if not duplicates:
        return None

    report_path = output_folder / "DUPLICATE_TRANSLATION_REPORT.txt"
    total_count = sum(len(items) for items in duplicates.values())

    lines = [
        "=" * 70,
        "DUPLICATE TRANSLATION REPORT",
        "=" * 70,
        f"Tester: {username}",
        f"Category: {category}",
        f"Total duplicates: {total_count}",
        "",
        "These translations appear multiple times with DIFFERENT comments.",
        "During transfer, only the FIRST comment was kept.",
        "Review this list to ensure no important feedback was lost.",
        "",
        "-" * 70,
        "",
    ]

    for sheet_name, items in sorted(duplicates.items()):
        lines.append(f"Sheet: {sheet_name}")
        lines.append("-" * 40)

        for trans, comments in items:
            trans_display = trans[:80] + "..." if len(trans) > 80 else trans
            lines.append(f"\nTranslation: {trans_display}")
            lines.append("Comments:")
            for i, comment in enumerate(comments, 1):
                comment_display = comment[:100] + "..." if len(comment) > 100 else comment
                lines.append(f"  {i}. {comment_display}")

        lines.append("")

    lines.append("=" * 70)
    lines.append("End of report")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return report_path


# =============================================================================
# FOLDER TRANSFER
# =============================================================================

def transfer_folder_data(
    old_folder: Dict,
    new_folder: Dict,
    output_dir: Path,
    tester_mapping: Dict
) -> Dict:
    """
    Transfer all sheet data from OLD folder to NEW folder.

    Args:
        old_folder: dict with folder info
        new_folder: dict with folder info
        output_dir: Path to QAfolder (output)
        tester_mapping: dict {tester_name: "EN" or "CN"}

    Returns:
        dict: {(username, category): stats}
    """
    username = old_folder["username"]
    category = old_folder["category"]
    is_english = tester_mapping.get(username, "EN") == "EN"
    is_item_category = category.lower() == "item"

    # Load workbooks
    old_wb = safe_load_workbook(old_folder["xlsx_path"])
    new_wb = safe_load_workbook(new_folder["xlsx_path"])

    combined_stats = {
        "total": 0,
        "stringid_match": 0,
        "trans_only": 0,
        "unmatched": 0,
        "name_desc_stringid_match": 0,
        "name_desc_match": 0,
    }

    # Process each sheet
    for sheet_name in old_wb.sheetnames:
        if sheet_name not in new_wb.sheetnames:
            print(f"    WARN: Sheet '{sheet_name}' not in NEW file, skipping")
            continue

        old_ws = old_wb[sheet_name]
        new_ws = new_wb[sheet_name]

        sheet_stats = transfer_sheet_data(
            old_ws, new_ws, category, is_english, old_folder["folder_path"]
        )

        # Accumulate stats
        for key in combined_stats:
            combined_stats[key] += sheet_stats.get(key, 0)

        if sheet_stats["total"] > 0:
            if is_item_category:
                print(f"    Sheet '{sheet_name}': {sheet_stats['name_desc_stringid_match']}+{sheet_stats['name_desc_match']} transferred, {sheet_stats['unmatched']} unmatched")
            else:
                print(f"    Sheet '{sheet_name}': {sheet_stats['stringid_match']}+{sheet_stats['trans_only']} transferred, {sheet_stats['unmatched']} unmatched")

    # Create output folder
    output_folder = output_dir / f"{username}_{category}"
    output_folder.mkdir(parents=True, exist_ok=True)

    # Detect duplicates
    duplicates = detect_duplicate_translations(old_wb, category, is_english)
    if duplicates:
        report_path = write_duplicate_translation_report(duplicates, output_folder, username, category)
        if report_path:
            total_dups = sum(len(items) for items in duplicates.values())
            print(f"    WARNING: {total_dups} translations have different comments!")
            print(f"    Report: {report_path.name}")

    # Save the new workbook
    output_xlsx = output_folder / new_folder["xlsx_path"].name
    new_wb.save(output_xlsx)

    # Copy images
    for img in old_folder["images"]:
        dest = output_folder / img.name
        shutil.copy2(img, dest)

    old_wb.close()
    new_wb.close()

    return {(username, category): combined_stats}


# =============================================================================
# REPORT PRINTING
# =============================================================================

def print_transfer_report(stats: Dict):
    """Print formatted transfer report to terminal."""
    print()
    print("=" * 79)
    print("                              TRANSFER REPORT")
    print("=" * 79)
    print()
    print(f"{'Tester':<20}{'Category':<12}{'Total':>7}{'Exact':>10}{'Fallback':>10}{'Success %':>12}")
    print("-" * 79)

    grand_total = 0
    grand_exact = 0
    grand_fallback = 0

    for (tester, category), data in sorted(stats.items()):
        total = data["total"]
        is_item = category.lower() == "item"

        if is_item:
            exact = data.get("name_desc_stringid_match", 0)
            fallback = data.get("name_desc_match", 0)
        else:
            exact = data.get("stringid_match", 0)
            fallback = data.get("trans_only", 0)

        success = (exact + fallback) / total * 100 if total > 0 else 0
        print(f"{tester:<20}{category:<12}{total:>7}{exact:>10}{fallback:>10}{success:>11.1f}%")

        grand_total += total
        grand_exact += exact
        grand_fallback += fallback

    print("-" * 79)
    grand_success = (grand_exact + grand_fallback) / grand_total * 100 if grand_total > 0 else 0
    print(f"{'TOTAL':<20}{'':<12}{grand_total:>7}{grand_exact:>10}{grand_fallback:>10}{grand_success:>11.1f}%")
    print("=" * 79)
    print()
    print("Legend:")
    print("  Exact    = Strong match (STRINGID+Trans for most, ItemName+ItemDesc+STRINGID for Item)")
    print("  Fallback = Weaker match (Trans only for most, ItemName+ItemDesc for Item)")
    unmatched = grand_total - grand_exact - grand_fallback
    print(f"  Unmatched = {unmatched} rows (not transferred)")
    print()


# =============================================================================
# MAIN TRANSFER FUNCTION
# =============================================================================

def transfer_qa_files() -> bool:
    """
    Main transfer function: QAfolderOLD -> QAfolderNEW -> QAfolder

    Returns:
        bool: True if transfer completed successfully
    """
    print()
    print("=" * 60)
    print("QA File Transfer (OLD -> NEW structure)")
    print("=" * 60)

    # Check folders exist
    if not QA_FOLDER_OLD.exists():
        print(f"ERROR: QAfolderOLD not found at {QA_FOLDER_OLD}")
        print("Please create QAfolderOLD/ with your OLD QA files.")
        return False

    if not QA_FOLDER_NEW.exists():
        print(f"ERROR: QAfolderNEW not found at {QA_FOLDER_NEW}")
        print("Please create QAfolderNEW/ with your NEW (empty) QA files.")
        return False

    # Discover folders
    old_folders = discover_qa_folders_in(QA_FOLDER_OLD)
    new_folders = discover_qa_folders_in(QA_FOLDER_NEW)

    if not old_folders:
        print("ERROR: No valid QA folders found in QAfolderOLD/")
        return False

    if not new_folders:
        print("ERROR: No valid QA folders found in QAfolderNEW/")
        return False

    print(f"Found {len(old_folders)} OLD folder(s), {len(new_folders)} NEW folder(s)")

    # Load tester mapping
    print("\nLoading tester->language mapping...")
    tester_mapping = load_tester_mapping()

    # Build lookup for NEW folders
    new_lookup = {f"{f['username']}_{f['category']}": f for f in new_folders}

    # Transfer each OLD folder
    all_stats = {}

    for old_folder in old_folders:
        key = f"{old_folder['username']}_{old_folder['category']}"
        username = old_folder['username']
        lang = tester_mapping.get(username, "EN")
        in_mapping = username in tester_mapping
        print(f"\nTransferring: {key} -> {lang}{'' if in_mapping else ' (not in mapping, default)'}")

        if key not in new_lookup:
            print(f"  WARN: No matching NEW folder for {key}, skipping")
            continue

        new_folder = new_lookup[key]
        folder_stats = transfer_folder_data(old_folder, new_folder, QA_FOLDER, tester_mapping)
        all_stats.update(folder_stats)

    # Print report
    if all_stats:
        print_transfer_report(all_stats)

    print("Transfer complete!")
    print(f"Output: {QA_FOLDER}")
    print("You can now run 'Build Masterfiles' to compile.")

    return True
