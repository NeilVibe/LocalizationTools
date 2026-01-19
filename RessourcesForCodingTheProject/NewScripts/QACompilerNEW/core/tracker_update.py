"""
Tracker Update Module
=====================
Update tracker from QAFolderForTracker without rebuilding master files.

Use case: Retroactively add missing days to the progress tracker.

Workflow:
1. Copy QA files for the missing day to QAFolderForTracker/
2. Set file mtime to target date: touch -d "2025-01-18" QAFolderForTracker/*/*.xlsx
3. Run: python main.py --update-tracker
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    QA_FOLDER_FOR_TRACKER, CATEGORIES, TRANSLATION_COLS,
    load_tester_mapping
)
from core.discovery import IMAGE_EXTENSIONS
from core.excel_ops import safe_load_workbook, find_column_by_header
from core.processing import count_words_english, count_chars_chinese


# =============================================================================
# FOLDER DISCOVERY
# =============================================================================

def discover_tracker_folders() -> List[Dict]:
    """
    Discover QA folders in QAFolderForTracker, enriched with file_date from mtime.

    Returns:
        List of dicts with {username, category, xlsx_path, folder_path, file_date, images}
    """
    folders = []

    if not QA_FOLDER_FOR_TRACKER.exists():
        print(f"  Creating folder: {QA_FOLDER_FOR_TRACKER}")
        QA_FOLDER_FOR_TRACKER.mkdir(parents=True, exist_ok=True)
        return folders

    for folder in QA_FOLDER_FOR_TRACKER.iterdir():
        if not folder.is_dir():
            continue

        # Skip hidden/temp folders
        if folder.name.startswith('.') or folder.name.startswith('~'):
            continue

        # Parse folder name: {Username}_{Category}
        folder_name = folder.name
        if "_" not in folder_name:
            print(f"  WARN: Invalid folder name format: {folder_name}")
            continue

        parts = folder_name.rsplit("_", 1)
        if len(parts) != 2:
            print(f"  WARN: Invalid folder name format: {folder_name}")
            continue

        username, category = parts
        if category not in CATEGORIES:
            print(f"  WARN: Unknown category '{category}' in folder {folder_name}")
            continue

        # Find xlsx file (skip temp files starting with ~)
        xlsx_files = [f for f in folder.glob("*.xlsx") if not f.name.startswith("~")]
        if not xlsx_files:
            print(f"  WARN: No xlsx in folder: {folder_name}")
            continue

        # Use the largest xlsx file (likely the real one)
        xlsx_path = max(xlsx_files, key=lambda x: x.stat().st_size)

        # Get file date from mtime
        file_mtime = xlsx_path.stat().st_mtime
        file_date = datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d")

        # Collect images (for reference, not actually copying)
        images = [f for f in folder.iterdir()
                  if f.suffix.lower() in IMAGE_EXTENSIONS]

        folders.append({
            "username": username,
            "category": category,
            "xlsx_path": xlsx_path,
            "folder_path": folder,
            "file_date": file_date,
            "images": images,
        })

    return folders


# =============================================================================
# STAT COUNTING
# =============================================================================

def count_sheet_stats(qa_ws, category: str, is_english: bool) -> Dict:
    """
    Count stats from a QA worksheet without modifying anything.

    Args:
        qa_ws: QA worksheet
        category: Category name
        is_english: Whether file is English

    Returns:
        Dict with {total, issue, no_issue, blocked, korean, word_count}
    """
    stats = {
        "total": 0,
        "issue": 0,
        "no_issue": 0,
        "blocked": 0,
        "korean": 0,
        "word_count": 0,
    }

    # Find STATUS column
    status_col = find_column_by_header(qa_ws, "STATUS")
    if not status_col:
        return stats

    # Get translation column for word counting
    trans_col_key = "eng" if is_english else "other"
    trans_col = TRANSLATION_COLS.get(category, {"eng": 2, "other": 3}).get(trans_col_key, 2)

    # Process each row
    for row in range(2, qa_ws.max_row + 1):
        # Skip empty rows
        first_col_value = qa_ws.cell(row=row, column=1).value
        if first_col_value is None or str(first_col_value).strip() == "":
            continue

        stats["total"] += 1

        # Get STATUS value
        status_value = qa_ws.cell(row=row, column=status_col).value
        if status_value:
            status_upper = str(status_value).strip().upper()
            if status_upper == "ISSUE":
                stats["issue"] += 1
            elif status_upper == "NO ISSUE":
                stats["no_issue"] += 1
            elif status_upper == "BLOCKED":
                stats["blocked"] += 1
            elif status_upper == "KOREAN":
                stats["korean"] += 1

            # Count words/chars for DONE rows
            if status_upper in ["ISSUE", "NO ISSUE", "BLOCKED", "KOREAN"]:
                cell_value = qa_ws.cell(row, trans_col).value
                if is_english:
                    stats["word_count"] += count_words_english(cell_value)
                else:
                    stats["word_count"] += count_chars_chinese(cell_value)

    return stats


def count_folder_stats(folder: Dict, tester_mapping: Dict) -> Dict:
    """
    Count all stats for a QA folder.

    Args:
        folder: Folder dict from discover_tracker_folders()
        tester_mapping: Dict mapping tester name -> "EN" or "CN"

    Returns:
        Dict with tracker entry data
    """
    username = folder["username"]
    category = folder["category"]
    xlsx_path = folder["xlsx_path"]
    file_date = folder["file_date"]

    # Determine language
    lang = tester_mapping.get(username, "EN")
    is_english = (lang == "EN")

    # Load workbook
    wb = safe_load_workbook(xlsx_path)

    # Aggregate stats across all sheets
    total_stats = {
        "total": 0,
        "issue": 0,
        "no_issue": 0,
        "blocked": 0,
        "korean": 0,
        "word_count": 0,
    }

    for sheet_name in wb.sheetnames:
        if sheet_name == "STATUS":
            continue

        ws = wb[sheet_name]
        sheet_stats = count_sheet_stats(ws, category, is_english)

        for key in total_stats:
            total_stats[key] += sheet_stats[key]

    wb.close()

    # Build tracker entry
    done = total_stats["issue"] + total_stats["no_issue"] + total_stats["blocked"] + total_stats["korean"]

    return {
        "date": file_date,
        "user": username,
        "category": category,
        "lang": lang,
        "total_rows": total_stats["total"],
        "done": done,
        "issues": total_stats["issue"],
        "no_issue": total_stats["no_issue"],
        "blocked": total_stats["blocked"],
        "korean": total_stats["korean"],
        "word_count": total_stats["word_count"],
    }


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def update_tracker_only() -> Tuple[bool, str, List[Dict]]:
    """
    Main entry point for tracker-only update.

    1. Discover folders in QAFolderForTracker/
    2. For each: extract date from mtime, count stats
    3. Update _DAILY_DATA sheet
    4. Rebuild DAILY and TOTAL sheets
    5. Save tracker

    Returns:
        Tuple of (success, message, entries)
    """
    print()
    print("=" * 60)
    print("Update Tracker from QAFolderForTracker")
    print("=" * 60)
    print()
    print("This mode updates the progress tracker WITHOUT rebuilding master files.")
    print("Use it to retroactively add missing days to the tracker.")
    print()
    print("Instructions:")
    print("  1. Copy QA files for the missing day to QAFolderForTracker/")
    print("  2. Set file date: touch -d '2025-01-18' QAFolderForTracker/*/*.xlsx")
    print("  3. Run this command")
    print()

    # Discover folders
    print("Discovering folders in QAFolderForTracker...")
    folders = discover_tracker_folders()

    if not folders:
        msg = "No valid QA folders found in QAFolderForTracker/"
        print(f"\n{msg}")
        print(f"\nExpected format: QAFolderForTracker/{{Username}}_{{Category}}/")
        print(f"Valid categories: {', '.join(CATEGORIES)}")
        return False, msg, []

    print(f"  Found {len(folders)} folder(s)")

    # Load tester mapping
    print("\nLoading tester->language mapping...")
    tester_mapping = load_tester_mapping()

    # Process each folder and build tracker entries
    print("\nProcessing folders...")
    entries = []
    for folder in folders:
        username = folder["username"]
        category = folder["category"]
        file_date = folder["file_date"]
        lang = tester_mapping.get(username, "EN")
        in_mapping = username in tester_mapping

        print(f"\n  {username}_{category} ({file_date})")
        print(f"    Language: {lang}{'' if in_mapping else ' (not in mapping, default)'}")

        entry = count_folder_stats(folder, tester_mapping)
        entries.append(entry)

        print(f"    Total: {entry['total_rows']}, Done: {entry['done']}, Issues: {entry['issues']}")

    # Update tracker
    print("\n" + "=" * 60)
    print("Updating Progress Tracker...")
    print("=" * 60)

    try:
        from tracker.data import get_or_create_tracker, update_daily_data_sheet
        from tracker.daily import build_daily_sheet
        from tracker.total import build_total_sheet

        tracker_wb, tracker_path = get_or_create_tracker()

        # Update _DAILY_DATA (no manager stats in tracker-only mode)
        update_daily_data_sheet(tracker_wb, entries, manager_stats={})

        # Rebuild visible sheets
        build_daily_sheet(tracker_wb)
        build_total_sheet(tracker_wb)

        # Remove deprecated GRAPHS sheet if present
        if "GRAPHS" in tracker_wb.sheetnames:
            del tracker_wb["GRAPHS"]

        tracker_wb.save(tracker_path)

        print(f"\n  Saved: {tracker_path}")
        print(f"  Updated {len(entries)} entries from {len(set(e['date'] for e in entries))} unique date(s)")

    except Exception as e:
        msg = f"Failed to update tracker: {e}"
        print(f"\nERROR: {msg}")
        return False, msg, entries

    # Summary
    print("\n" + "=" * 60)
    print("Tracker Update Complete!")
    print("=" * 60)

    # Group by date for summary
    by_date = defaultdict(list)
    for entry in entries:
        by_date[entry["date"]].append(entry)

    print("\nSummary by date:")
    for date in sorted(by_date.keys()):
        date_entries = by_date[date]
        total_done = sum(e["done"] for e in date_entries)
        total_issues = sum(e["issues"] for e in date_entries)
        users = [e["user"] for e in date_entries]
        print(f"  {date}: {len(users)} user(s), {total_done} done, {total_issues} issues")

    msg = f"Successfully updated tracker with {len(entries)} entries"
    return True, msg, entries
