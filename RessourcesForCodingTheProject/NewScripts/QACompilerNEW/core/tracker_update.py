"""
Tracker Update Module
=====================
Update tracker from TrackerUpdateFolder without rebuilding master files.

Use case: Retroactively add missing days to the progress tracker.

Folder Structure:
    TrackerUpdateFolder/
    ├── QAfolder/              # Tester QA files
    │   └── Username_Category/
    │       └── file.xlsx
    ├── Masterfolder_EN/       # English master files (for manager stats)
    │   └── Master_Quest.xlsx
    └── Masterfolder_CN/       # Chinese master files (for manager stats)
        └── Master_Quest.xlsx

Workflow:
1. Copy QA files and Master files to TrackerUpdateFolder/
2. Set file dates via GUI (or use existing mtime)
3. Run: python main.py --update-tracker
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    TRACKER_UPDATE_FOLDER, TRACKER_UPDATE_QA,
    TRACKER_UPDATE_MASTER_EN, TRACKER_UPDATE_MASTER_CN,
    CATEGORIES, TRANSLATION_COLS,
    load_tester_mapping
)
from core.discovery import IMAGE_EXTENSIONS
from core.excel_ops import safe_load_workbook, find_column_by_header
from core.processing import count_words_english, count_chars_chinese


# Valid manager status values
VALID_MANAGER_STATUS = {"FIXED", "REPORTED", "CHECKING", "NON-ISSUE", "NON ISSUE"}


# =============================================================================
# QA FOLDER DISCOVERY (Tester Stats)
# =============================================================================

def discover_tracker_qa_folders() -> List[Dict]:
    """
    Discover QA folders in TrackerUpdateFolder/QAfolder, enriched with file_date from mtime.

    Returns:
        List of dicts with {username, category, xlsx_path, folder_path, file_date, images}
    """
    folders = []
    base_folder = TRACKER_UPDATE_QA

    if not base_folder.exists():
        print(f"  Creating folder: {base_folder}")
        base_folder.mkdir(parents=True, exist_ok=True)
        return folders

    for folder in base_folder.iterdir():
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
# TESTER STAT COUNTING
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


def count_qa_folder_stats(folder: Dict, tester_mapping: Dict) -> Dict:
    """
    Count all stats for a QA folder.

    Args:
        folder: Folder dict from discover_tracker_qa_folders()
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
# MANAGER STAT AGGREGATION
# =============================================================================

def aggregate_manager_stats(tester_mapping: Dict) -> Tuple[Dict, Dict]:
    """
    Aggregate manager stats from TrackerUpdateFolder master files.

    Logic:
    1. Scan Master_*.xlsx files directly
    2. Extract category from filename (Master_System.xlsx → "System")
    3. Find users via COMMENT_{User} or STATUS_{User} columns
    4. Store stats under that master file's category

    This avoids duplicate counting when multiple categories map to same master.

    Returns:
        Tuple of:
        - manager_stats: {category: {user: {fixed, reported, checking, nonissue, lang}}}
        - manager_dates: {(category, user): file_date}
    """
    manager_stats = defaultdict(lambda: defaultdict(
        lambda: {"fixed": 0, "reported": 0, "checking": 0, "nonissue": 0, "lang": "EN"}
    ))
    manager_dates = {}

    # Scan both EN and CN folders
    for master_folder in [TRACKER_UPDATE_MASTER_EN, TRACKER_UPDATE_MASTER_CN]:
        print(f"  Checking folder: {master_folder}")
        if not master_folder.exists():
            print(f"    Folder does not exist, creating...")
            master_folder.mkdir(parents=True, exist_ok=True)
            continue

        # List all xlsx files for debug
        all_xlsx = list(master_folder.glob("*.xlsx"))
        print(f"    Found {len(all_xlsx)} xlsx files: {[f.name for f in all_xlsx]}")

        # Scan actual master files (not iterate over CATEGORIES)
        for master_path in master_folder.glob("Master_*.xlsx"):
            if master_path.name.startswith("~"):
                continue

            # Extract category from filename: Master_System.xlsx → "System"
            category = master_path.stem.replace("Master_", "")

            # Get file date from mtime
            file_mtime = master_path.stat().st_mtime
            file_date = datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d")

            print(f"    Reading {master_path.name} → category={category}")

            try:
                wb = safe_load_workbook(master_path)

                for sheet_name in wb.sheetnames:
                    if sheet_name == "STATUS":
                        continue

                    ws = wb[sheet_name]

                    # Find STATUS_{User} columns for counting manager stats
                    # Note: STATUS_{User} is manager status (FIXED/REPORTED/etc)
                    #       TESTER_STATUS_{User} is tester's original status (hidden)
                    status_cols = {}

                    for col in range(1, ws.max_column + 1):
                        header = ws.cell(row=1, column=col).value
                        if not header:
                            continue
                        header_str = str(header).strip()

                        # Find STATUS_{User} columns (not TESTER_STATUS_{User})
                        if header_str.startswith("STATUS_"):
                            username = header_str.replace("STATUS_", "")
                            status_cols[username] = col

                    print(f"      Sheet '{sheet_name}': found STATUS_ columns for {list(status_cols.keys())}")

                    if not status_cols:
                        print(f"      Sheet '{sheet_name}': no STATUS_ columns found, skipping")
                        continue

                    # Count status values per user
                    for row in range(2, ws.max_row + 1):
                        for username, col in status_cols.items():
                            value = ws.cell(row=row, column=col).value
                            if value:
                                status_upper = str(value).strip().upper()
                                if status_upper == "FIXED":
                                    manager_stats[category][username]["fixed"] += 1
                                elif status_upper == "REPORTED":
                                    manager_stats[category][username]["reported"] += 1
                                elif status_upper == "CHECKING":
                                    manager_stats[category][username]["checking"] += 1
                                elif status_upper in ("NON-ISSUE", "NON ISSUE"):
                                    manager_stats[category][username]["nonissue"] += 1

                    # Set lang and date for all users found in this file
                    for username in status_cols.keys():
                        manager_stats[category][username]["lang"] = tester_mapping.get(username, "EN")
                        manager_dates[(category, username)] = file_date

                wb.close()

            except Exception as e:
                print(f"  WARN: Error reading {master_path.name} for manager stats: {e}")

    # Convert nested defaultdicts to regular dicts
    result_stats = {}
    for category, users in manager_stats.items():
        result_stats[category] = dict(users)

    return result_stats, manager_dates


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def update_tracker_only() -> Tuple[bool, str, List[Dict]]:
    """
    Main entry point for tracker-only update.

    1. Discover QA folders in TrackerUpdateFolder/QAfolder
    2. Discover Master files in TrackerUpdateFolder/Masterfolder_EN and CN
    3. Count tester stats from QA files
    4. Count manager stats from Master files
    5. Update _DAILY_DATA sheet
    6. Rebuild DAILY and TOTAL sheets
    7. Save tracker

    Returns:
        Tuple of (success, message, entries)
    """
    print()
    print("=" * 60)
    print("Update Tracker from TrackerUpdateFolder")
    print("=" * 60)
    print()
    print("This mode updates the progress tracker WITHOUT rebuilding master files.")
    print("Use it to retroactively add missing days to the tracker.")
    print()
    print("Folder structure:")
    print(f"  {TRACKER_UPDATE_FOLDER}/")
    print(f"  ├── QAfolder/           (tester QA files)")
    print(f"  ├── Masterfolder_EN/    (manager stats)")
    print(f"  └── Masterfolder_CN/    (manager stats)")
    print()

    # Discover QA folders
    print("Discovering QA folders...")
    qa_folders = discover_tracker_qa_folders()
    print(f"  Found {len(qa_folders)} QA folder(s)")

    # Check for master files
    has_master_files = (
        any(TRACKER_UPDATE_MASTER_EN.glob("Master_*.xlsx")) or
        any(TRACKER_UPDATE_MASTER_CN.glob("Master_*.xlsx"))
    )
    master_en_count = len(list(TRACKER_UPDATE_MASTER_EN.glob("Master_*.xlsx")))
    master_cn_count = len(list(TRACKER_UPDATE_MASTER_CN.glob("Master_*.xlsx")))
    print(f"\nMaster files: {master_en_count} EN, {master_cn_count} CN")

    if not qa_folders and not has_master_files:
        msg = "No QA folders or master files found in TrackerUpdateFolder"
        print(f"\n{msg}")
        return False, msg, []

    # Load tester mapping
    print("\nLoading tester->language mapping...")
    tester_mapping = load_tester_mapping()

    entries = []

    # Process QA folders (tester stats)
    if qa_folders:
        print("\nProcessing QA folders (tester stats)...")
        for folder in qa_folders:
            username = folder["username"]
            category = folder["category"]
            file_date = folder["file_date"]
            lang = tester_mapping.get(username, "EN")
            in_mapping = username in tester_mapping

            print(f"\n  {username}_{category} ({file_date})")
            print(f"    Language: {lang}{'' if in_mapping else ' (not in mapping, default)'}")

            entry = count_qa_folder_stats(folder, tester_mapping)
            entries.append(entry)

            print(f"    Total: {entry['total_rows']}, Done: {entry['done']}, Issues: {entry['issues']}")

    # Process master files (manager stats) - check if any master files exist
    manager_stats = {}
    manager_dates = {}
    has_master_files = (
        any(TRACKER_UPDATE_MASTER_EN.glob("Master_*.xlsx")) or
        any(TRACKER_UPDATE_MASTER_CN.glob("Master_*.xlsx"))
    )
    if has_master_files:
        print("\nProcessing master files (manager stats)...")
        print("  Using ORIGINAL category names (Skill, Help, Gimmick → mapped to master files)")
        manager_stats, manager_dates = aggregate_manager_stats(tester_mapping)

        for category, users in manager_stats.items():
            for username, stats in users.items():
                total = stats["fixed"] + stats["reported"] + stats["checking"] + stats["nonissue"]
                if total > 0:
                    date = manager_dates.get((category, username), "unknown")
                    print(f"  {username} ({category}, {date}): FIXED={stats['fixed']}, REPORTED={stats['reported']}, CHECKING={stats['checking']}, NON-ISSUE={stats['nonissue']}")

    # Update tracker
    print("\n" + "=" * 60)
    print("Updating Progress Tracker...")
    print("=" * 60)

    try:
        from tracker.data import get_or_create_tracker, update_daily_data_sheet
        from tracker.daily import build_daily_sheet
        from tracker.total import build_total_sheet

        print("\n[TRACKER DEBUG] STEP A: Loading/Creating Tracker")
        tracker_wb, tracker_path = get_or_create_tracker()
        print(f"  - Tracker path: {tracker_path}")
        print(f"  - Tracker exists: {tracker_path.exists()}")
        print(f"  - Sheets in workbook: {tracker_wb.sheetnames}")

        # Check _DAILY_DATA sheet state BEFORE update
        dd_ws = tracker_wb["_DAILY_DATA"]
        print(f"  - _DAILY_DATA max_row BEFORE: {dd_ws.max_row}")
        print(f"  - _DAILY_DATA max_column BEFORE: {dd_ws.max_column}")

        print("\n[TRACKER DEBUG] STEP B: Calling update_daily_data_sheet()")
        print(f"  - entries count: {len(entries)}")
        print(f"  - manager_stats count: {len(manager_stats)}")
        print(f"  - manager_stats categories: {list(manager_stats.keys())}")
        for cat, users in manager_stats.items():
            print(f"    - {cat}: {len(users)} users")
            for u, s in list(users.items())[:2]:  # Show first 2 users per category
                print(f"      - {u}: fixed={s.get('fixed')}, reported={s.get('reported')}")

        # Update _DAILY_DATA with tester stats AND manager stats
        # Pass manager_dates so new rows use file mtime, not today's date
        update_daily_data_sheet(tracker_wb, entries, manager_stats, manager_dates)

        # Check _DAILY_DATA sheet state AFTER update
        print("\n[TRACKER DEBUG] STEP C: After update_daily_data_sheet()")
        print(f"  - _DAILY_DATA max_row AFTER: {dd_ws.max_row}")
        print(f"  - _DAILY_DATA max_column AFTER: {dd_ws.max_column}")
        print(f"  - Sample rows from _DAILY_DATA:")
        for r in range(1, min(dd_ws.max_row + 1, 8)):
            row_data = [dd_ws.cell(r, c).value for c in range(1, 15)]
            print(f"    Row {r}: {row_data}")

        print("\n[TRACKER DEBUG] STEP D: Rebuilding visible sheets")
        # Rebuild visible sheets
        build_daily_sheet(tracker_wb)
        build_total_sheet(tracker_wb)

        # Remove deprecated GRAPHS sheet if present
        if "GRAPHS" in tracker_wb.sheetnames:
            del tracker_wb["GRAPHS"]

        print("\n[TRACKER DEBUG] STEP E: Saving workbook")
        print(f"  - Saving to: {tracker_path}")
        tracker_wb.save(tracker_path)
        print(f"  - Save complete!")

        # VERIFY: Reload and check
        print("\n[TRACKER DEBUG] STEP F: VERIFICATION - Reloading saved file")
        from core.excel_ops import safe_load_workbook
        verify_wb = safe_load_workbook(tracker_path)
        verify_ws = verify_wb["_DAILY_DATA"]
        print(f"  - Reloaded _DAILY_DATA max_row: {verify_ws.max_row}")
        print(f"  - Reloaded sample rows:")
        for r in range(1, min(verify_ws.max_row + 1, 8)):
            row_data = [verify_ws.cell(r, c).value for c in range(1, 15)]
            print(f"    Row {r}: {row_data}")
        verify_wb.close()

        print(f"\n  Saved: {tracker_path}")
        if entries:
            print(f"  Updated {len(entries)} tester entries from {len(set(e['date'] for e in entries))} unique date(s)")
        if manager_stats:
            total_users = sum(len(users) for users in manager_stats.values())
            print(f"  Updated manager stats for {total_users} user(s)")

    except Exception as e:
        msg = f"Failed to update tracker: {e}"
        print(f"\nERROR: {msg}")
        import traceback
        traceback.print_exc()
        return False, msg, entries

    # Summary
    print("\n" + "=" * 60)
    print("Tracker Update Complete!")
    print("=" * 60)

    # Group by date for summary
    if entries:
        by_date = defaultdict(list)
        for entry in entries:
            by_date[entry["date"]].append(entry)

        print("\nTester stats by date:")
        for date in sorted(by_date.keys()):
            date_entries = by_date[date]
            total_done = sum(e["done"] for e in date_entries)
            total_issues = sum(e["issues"] for e in date_entries)
            users = [e["user"] for e in date_entries]
            print(f"  {date}: {len(users)} user(s), {total_done} done, {total_issues} issues")

    msg = f"Successfully updated tracker"
    if entries:
        msg += f" with {len(entries)} tester entries"
    if manager_stats:
        msg += f" and manager stats"
    return True, msg, entries
