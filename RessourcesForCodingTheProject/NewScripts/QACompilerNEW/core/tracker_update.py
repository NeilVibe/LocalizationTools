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


# =============================================================================
# GRANULAR DEBUG LOGGING
# =============================================================================

_TRACKER_LOG_FILE = Path(__file__).parent.parent / "TRACKER_UPDATE_DEBUG.log"
_TRACKER_LOG_ENABLED = True  # Set to False to disable verbose logging
_TRACKER_LOG_LINES = []  # Buffer for batch writing


def _tracker_log(msg: str, level: str = "INFO"):
    """Add message to tracker log buffer."""
    if not _TRACKER_LOG_ENABLED:
        return
    timestamp = datetime.now().strftime("%H:%M:%S")
    _TRACKER_LOG_LINES.append(f"[{timestamp}] [{level}] {msg}")


def _tracker_log_flush(header: str = None):
    """Flush log buffer to file."""
    global _TRACKER_LOG_LINES
    if not _TRACKER_LOG_LINES:
        return
    try:
        mode = "a" if _TRACKER_LOG_FILE.exists() else "w"
        with open(_TRACKER_LOG_FILE, mode, encoding="utf-8") as f:
            if header:
                f.write(f"\n{'='*60}\n{header}\n{'='*60}\n")
            f.write("\n".join(_TRACKER_LOG_LINES) + "\n")
        _TRACKER_LOG_LINES = []
    except Exception as e:
        print(f"[TRACKER LOG ERROR] {e}")


def _tracker_log_clear():
    """Clear log file for fresh run."""
    global _TRACKER_LOG_LINES
    _TRACKER_LOG_LINES = []
    try:
        with open(_TRACKER_LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"=== TRACKER UPDATE DEBUG LOG === {datetime.now().isoformat()}\n\n")
    except:
        pass


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

    _tracker_log(f"DISCOVER: Scanning {base_folder}")

    if not base_folder.exists():
        _tracker_log(f"DISCOVER: Creating folder (did not exist)", "WARN")
        print(f"  Creating folder: {base_folder}")
        base_folder.mkdir(parents=True, exist_ok=True)
        _tracker_log_flush("DISCOVER QA FOLDERS")
        return folders

    for folder in base_folder.iterdir():
        if not folder.is_dir():
            continue

        # Skip hidden/temp folders
        if folder.name.startswith('.') or folder.name.startswith('~'):
            _tracker_log(f"  SKIP: {folder.name} (hidden/temp)")
            continue

        # Parse folder name: {Username}_{Category}
        folder_name = folder.name
        if "_" not in folder_name:
            _tracker_log(f"  SKIP: {folder_name} (no underscore)", "WARN")
            print(f"  WARN: Invalid folder name format: {folder_name}")
            continue

        parts = folder_name.rsplit("_", 1)
        if len(parts) != 2:
            _tracker_log(f"  SKIP: {folder_name} (bad split)", "WARN")
            print(f"  WARN: Invalid folder name format: {folder_name}")
            continue

        username, category = parts
        if category not in CATEGORIES:
            _tracker_log(f"  SKIP: {folder_name} (unknown category '{category}')", "WARN")
            print(f"  WARN: Unknown category '{category}' in folder {folder_name}")
            continue

        # Find xlsx file (skip temp files starting with ~)
        xlsx_files = [f for f in folder.glob("*.xlsx") if not f.name.startswith("~")]
        if not xlsx_files:
            _tracker_log(f"  SKIP: {folder_name} (no xlsx)", "WARN")
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

        _tracker_log(f"  FOUND: {username}_{category} date={file_date} xlsx={xlsx_path.name} images={len(images)}")

        folders.append({
            "username": username,
            "category": category,
            "xlsx_path": xlsx_path,
            "folder_path": folder,
            "file_date": file_date,
            "images": images,
        })

    _tracker_log(f"DISCOVER: Found {len(folders)} valid QA folders")
    _tracker_log_flush("DISCOVER QA FOLDERS")
    return folders


# =============================================================================
# TESTER STAT COUNTING
# =============================================================================

def count_sheet_stats(qa_ws, category: str, is_english: bool, sheet_name: str = "") -> Dict:
    """
    Count stats from a QA worksheet without modifying anything.

    Args:
        qa_ws: QA worksheet
        category: Category name
        is_english: Whether file is English
        sheet_name: Sheet name for logging

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
        _tracker_log(f"    SHEET '{sheet_name}': No STATUS column found", "WARN")
        return stats

    # Get translation column for word counting
    trans_col_key = "eng" if is_english else "other"
    trans_col = TRANSLATION_COLS.get(category, {"eng": 2, "other": 3}).get(trans_col_key, 2)

    _tracker_log(f"    SHEET '{sheet_name}': max_row={qa_ws.max_row}, STATUS_col={status_col}, trans_col={trans_col}")

    # SCRIPT GRANULAR DEBUG
    is_script = category.lower() in ("sequencer", "dialog")
    if is_script:
        _tracker_log(f"    *** SCRIPT TESTER STATS DEBUG ***")

    # Process each row
    rows_with_status = []
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
            if is_script:
                rows_with_status.append((row, status_upper))

            if status_upper == "ISSUE":
                stats["issue"] += 1
            elif status_upper in ("NO ISSUE", "NON-ISSUE"):
                # Accept both "NO ISSUE" (standard) and "NON-ISSUE" (Script-type)
                stats["no_issue"] += 1
            elif status_upper == "BLOCKED":
                stats["blocked"] += 1
            elif status_upper == "KOREAN":
                stats["korean"] += 1

    # SCRIPT GRANULAR DEBUG: Show all rows with STATUS
    if is_script:
        if rows_with_status:
            _tracker_log(f"    FOUND {len(rows_with_status)} ROWS WITH STATUS:")
            for r, s in rows_with_status[:30]:  # Show first 30
                _tracker_log(f"      Row {r}: '{s}'")
            if len(rows_with_status) > 30:
                _tracker_log(f"      ... and {len(rows_with_status) - 30} more")
        else:
            _tracker_log(f"    *** NO STATUS VALUES FOUND! ***", "WARN")

            # Count words/chars for DONE rows
            # Accept both "NO ISSUE" (standard) and "NON-ISSUE" (Script-type)
            if status_upper in ["ISSUE", "NO ISSUE", "NON-ISSUE", "BLOCKED", "KOREAN"]:
                cell_value = qa_ws.cell(row, trans_col).value
                if is_english:
                    stats["word_count"] += count_words_english(cell_value)
                else:
                    stats["word_count"] += count_chars_chinese(cell_value)

    _tracker_log(f"    SHEET '{sheet_name}': total={stats['total']} issue={stats['issue']} no_issue={stats['no_issue']} blocked={stats['blocked']} korean={stats['korean']} words={stats['word_count']}")
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

    _tracker_log(f"COUNT FOLDER: {username}_{category} date={file_date} lang={lang}")
    _tracker_log(f"  File: {xlsx_path.name}")

    # Load workbook
    wb = safe_load_workbook(xlsx_path)
    _tracker_log(f"  Sheets: {wb.sheetnames}")

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
            _tracker_log(f"    SKIP: STATUS sheet")
            continue

        ws = wb[sheet_name]
        sheet_stats = count_sheet_stats(ws, category, is_english, sheet_name)

        for key in total_stats:
            total_stats[key] += sheet_stats[key]

    wb.close()

    # Build tracker entry
    done = total_stats["issue"] + total_stats["no_issue"] + total_stats["blocked"] + total_stats["korean"]

    _tracker_log(f"  TOTALS: total={total_stats['total']} done={done} issues={total_stats['issue']} words={total_stats['word_count']}")

    # SCRIPT GRANULAR DEBUG: Show the entry that will be written
    is_script = category.lower() in ("sequencer", "dialog")
    if is_script:
        _tracker_log(f"")
        _tracker_log(f"  *** SCRIPT ENTRY TO BE WRITTEN ***")
        _tracker_log(f"    date={file_date}, user={username}, category={category}")
        _tracker_log(f"    done={done}, issues={total_stats['issue']}, no_issue={total_stats['no_issue']}")
        _tracker_log(f"    blocked={total_stats['blocked']}, korean={total_stats['korean']}")
        _tracker_log(f"")

    _tracker_log_flush(f"QA FOLDER: {username}_{category}")

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
    """
    manager_stats = defaultdict(lambda: defaultdict(
        lambda: {"fixed": 0, "reported": 0, "checking": 0, "nonissue": 0, "lang": "EN"}
    ))
    manager_dates = {}

    _tracker_log("MANAGER STATS: Starting aggregation")

    for master_folder in [TRACKER_UPDATE_MASTER_EN, TRACKER_UPDATE_MASTER_CN]:
        if not master_folder.exists():
            _tracker_log(f"  Creating folder: {master_folder}")
            master_folder.mkdir(parents=True, exist_ok=True)
            continue

        folder_label = "EN" if "EN" in str(master_folder) else "CN"
        _tracker_log(f"SCAN FOLDER: {folder_label} ({master_folder})")

        for master_path in master_folder.glob("Master_*.xlsx"):
            if master_path.name.startswith("~"):
                _tracker_log(f"  SKIP: {master_path.name} (temp file)")
                continue

            # Extract target_category from filename (e.g., Master_Character.xlsx → "Character")
            target_category = master_path.stem.replace("Master_", "")
            file_mtime = master_path.stat().st_mtime
            file_date = datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d")

            _tracker_log(f"MASTER FILE: {target_category} [{folder_label}] date={file_date}")
            _tracker_log(f"  Path: {master_path}")

            try:
                wb = safe_load_workbook(master_path)
                _tracker_log(f"  Sheets: {wb.sheetnames}")

                for sheet_name in wb.sheetnames:
                    if sheet_name == "STATUS":
                        continue

                    # Use target_category (from filename) as key to match compiler.py
                    category = target_category
                    ws = wb[sheet_name]

                    status_cols = {}
                    for col in range(1, ws.max_column + 1):
                        header = ws.cell(row=1, column=col).value
                        if header:
                            header_str = str(header)
                            header_upper = header_str.upper()
                            if header_upper.startswith("STATUS_") and not header_upper.startswith("TESTER_STATUS_"):
                                status_cols[header_str[7:]] = col  # Skip "STATUS_" prefix

                    _tracker_log(f"  SHEET '{sheet_name}': rows={ws.max_row}, cols={ws.max_column}")

                    # SCRIPT GRANULAR DEBUG: Show ALL headers for Script category
                    is_script = target_category.upper() == "SCRIPT"
                    if is_script:
                        _tracker_log(f"")
                        _tracker_log(f"  *** SCRIPT CATEGORY DETAILED DEBUG ***")
                        _tracker_log(f"  ALL COLUMN HEADERS:")
                        for col in range(1, min(ws.max_column + 1, 30)):  # First 30 columns
                            h = ws.cell(row=1, column=col).value
                            _tracker_log(f"    Col {col}: '{h}'")

                    _tracker_log(f"    STATUS_ columns: {list(status_cols.keys()) if status_cols else 'NONE'}")

                    if not status_cols:
                        _tracker_log(f"    SKIP: No STATUS_ columns", "WARN")
                        continue

                    # SCRIPT GRANULAR DEBUG: Check EVERY row for values
                    if is_script:
                        _tracker_log(f"")
                        _tracker_log(f"  SCANNING ALL {ws.max_row - 1} ROWS FOR STATUS VALUES:")
                        rows_with_values = []
                        for r in range(2, ws.max_row + 1):
                            for username, col in status_cols.items():
                                v = ws.cell(row=r, column=col).value
                                if v and str(v).strip():
                                    rows_with_values.append((r, username, str(v).strip()))

                        if rows_with_values:
                            _tracker_log(f"  FOUND {len(rows_with_values)} ROWS WITH STATUS VALUES:")
                            for r, u, v in rows_with_values[:50]:  # Show first 50
                                _tracker_log(f"    Row {r}: {u} = '{v}'")
                            if len(rows_with_values) > 50:
                                _tracker_log(f"    ... and {len(rows_with_values) - 50} more")
                        else:
                            _tracker_log(f"  *** NO STATUS VALUES FOUND IN ANY ROW! ***", "WARN")
                            _tracker_log(f"  Checking raw cell values for first STATUS column...")
                            if status_cols:
                                first_user = list(status_cols.keys())[0]
                                first_col = status_cols[first_user]
                                _tracker_log(f"    Column {first_col} ({first_user}) first 20 rows:")
                                for r in range(2, min(22, ws.max_row + 1)):
                                    raw_val = ws.cell(row=r, column=first_col).value
                                    _tracker_log(f"      Row {r}: raw='{raw_val}' type={type(raw_val).__name__}")
                        _tracker_log(f"")

                    # Sample values for debugging (all categories)
                    sample_values = {}
                    for username, col in status_cols.items():
                        vals = []
                        for r in range(2, min(12, ws.max_row + 1)):  # First 10 data rows
                            v = ws.cell(row=r, column=col).value
                            if v:
                                vals.append(str(v).strip())
                        sample_values[username] = vals[:5] if vals else ["(empty)"]
                    _tracker_log(f"    Sample values: {sample_values}")

                    for row in range(2, ws.max_row + 1):
                        for username, col in status_cols.items():
                            value = ws.cell(row=row, column=col).value
                            if value:
                                v = str(value).strip().upper()
                                if v == "FIXED": manager_stats[category][username]["fixed"] += 1
                                elif v == "REPORTED": manager_stats[category][username]["reported"] += 1
                                elif v == "CHECKING": manager_stats[category][username]["checking"] += 1
                                elif v in ("NON-ISSUE", "NON ISSUE"): manager_stats[category][username]["nonissue"] += 1

                    for username in status_cols.keys():
                        manager_stats[category][username]["lang"] = tester_mapping.get(username, "EN")
                        manager_dates[(category, username)] = file_date

                    # Log per-sheet summary
                    for u in status_cols.keys():
                        s = manager_stats[category][u]
                        _tracker_log(f"    {category}/{u}: F={s['fixed']} R={s['reported']} C={s['checking']} N={s['nonissue']}")

                wb.close()
            except Exception as e:
                _tracker_log(f"  ERROR: {e}", "ERROR")

    # Convert nested defaultdicts to regular dicts
    result_stats = {}
    for category, users_dd in manager_stats.items():
        result_stats[category] = {}
        for user, stats_dd in users_dd.items():
            result_stats[category][user] = dict(stats_dd)

    # Summary
    total_f = sum(s["fixed"] for u in result_stats.values() for s in u.values())
    total_r = sum(s["reported"] for u in result_stats.values() for s in u.values())
    total_c = sum(s["checking"] for u in result_stats.values() for s in u.values())
    total_n = sum(s["nonissue"] for u in result_stats.values() for s in u.values())
    _tracker_log(f"MANAGER TOTALS: F={total_f} R={total_r} C={total_c} N={total_n}")
    _tracker_log_flush("MANAGER STATS AGGREGATION")

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
    # Clear log for fresh run
    _tracker_log_clear()
    _tracker_log("=" * 50)
    _tracker_log("UPDATE TRACKER ONLY - START")
    _tracker_log("=" * 50)

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
    _tracker_log(f"Master files found: EN={master_en_count}, CN={master_cn_count}")

    if not qa_folders and not has_master_files:
        msg = "No QA folders or master files found in TrackerUpdateFolder"
        _tracker_log(msg, "ERROR")
        _tracker_log_flush("UPDATE TRACKER - ABORTED")
        print(f"\n{msg}")
        return False, msg, []

    # Load tester mapping
    print("\nLoading tester->language mapping...")
    tester_mapping = load_tester_mapping()
    _tracker_log(f"Tester mapping loaded: {len(tester_mapping)} entries")

    entries = []

    # Process QA folders (tester stats)
    if qa_folders:
        _tracker_log(f"Processing {len(qa_folders)} QA folders...")
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

        # STEP A: Load tracker
        _tracker_log("STEP A: Loading/Creating Tracker")
        tracker_wb, tracker_path = get_or_create_tracker()
        _tracker_log(f"  Path: {tracker_path}")
        _tracker_log(f"  Sheets: {tracker_wb.sheetnames}")

        dd_ws = tracker_wb["_DAILY_DATA"]
        _tracker_log(f"  _DAILY_DATA BEFORE: rows={dd_ws.max_row}, cols={dd_ws.max_column}")

        # STEP B: Update _DAILY_DATA
        _tracker_log("STEP B: Calling update_daily_data_sheet()")
        _tracker_log(f"  entries={len(entries)}, manager_stats categories={list(manager_stats.keys())}")
        for cat, users in manager_stats.items():
            for u, s in users.items():
                _tracker_log(f"    {cat}/{u}: F={s.get('fixed')} R={s.get('reported')} C={s.get('checking')} N={s.get('nonissue')}")

        update_daily_data_sheet(tracker_wb, entries, manager_stats, manager_dates)

        # STEP C: Check state after update
        _tracker_log("STEP C: After update_daily_data_sheet()")
        _tracker_log(f"  _DAILY_DATA AFTER: rows={dd_ws.max_row}, cols={dd_ws.max_column}")
        # Log sample rows
        for r in range(1, min(dd_ws.max_row + 1, 8)):
            row_data = [dd_ws.cell(r, c).value for c in range(1, 15)]
            _tracker_log(f"  Row {r}: {row_data}")

        # STEP D: Rebuild visible sheets
        _tracker_log("STEP D: Rebuilding DAILY and TOTAL sheets")
        build_daily_sheet(tracker_wb)
        build_total_sheet(tracker_wb)

        if "GRAPHS" in tracker_wb.sheetnames:
            del tracker_wb["GRAPHS"]

        # STEP E: Save
        _tracker_log("STEP E: Saving workbook")
        _tracker_log(f"  Path: {tracker_path}")
        tracker_wb.save(tracker_path)
        _tracker_log("  Save complete!")

        # STEP F: Verify
        _tracker_log("STEP F: VERIFICATION - Reloading saved file")
        verify_wb = safe_load_workbook(tracker_path)
        verify_ws = verify_wb["_DAILY_DATA"]
        _tracker_log(f"  Reloaded _DAILY_DATA: rows={verify_ws.max_row}")
        for r in range(1, min(verify_ws.max_row + 1, 8)):
            row_data = [verify_ws.cell(r, c).value for c in range(1, 15)]
            _tracker_log(f"  Row {r}: {row_data}")
        verify_wb.close()

        _tracker_log_flush("TRACKER UPDATE COMPLETE")

        print(f"\n  Saved: {tracker_path}")
        if entries:
            print(f"  Updated {len(entries)} tester entries from {len(set(e['date'] for e in entries))} unique date(s)")
        if manager_stats:
            total_users = sum(len(users) for users in manager_stats.values())
            print(f"  Updated manager stats for {total_users} user(s)")

    except Exception as e:
        msg = f"Failed to update tracker: {e}"
        _tracker_log(f"ERROR: {msg}", "ERROR")
        _tracker_log_flush("TRACKER UPDATE FAILED")
        print(f"\nERROR: {msg}")
        import traceback
        traceback.print_exc()
        return False, msg, entries

    # Summary
    print("\n" + "=" * 60)
    print("Tracker Update Complete!")
    print("=" * 60)

    _tracker_log("=" * 50)
    _tracker_log("UPDATE TRACKER ONLY - COMPLETE")
    _tracker_log("=" * 50)

    # Group by date for summary
    if entries:
        by_date = defaultdict(list)
        for entry in entries:
            by_date[entry["date"]].append(entry)

        print("\nTester stats by date:")
        _tracker_log("SUMMARY BY DATE:")
        for date in sorted(by_date.keys()):
            date_entries = by_date[date]
            total_done = sum(e["done"] for e in date_entries)
            total_issues = sum(e["issues"] for e in date_entries)
            users = [e["user"] for e in date_entries]
            print(f"  {date}: {len(users)} user(s), {total_done} done, {total_issues} issues")
            _tracker_log(f"  {date}: users={users} done={total_done} issues={total_issues}")

    msg = f"Successfully updated tracker"
    if entries:
        msg += f" with {len(entries)} tester entries"
    if manager_stats:
        msg += f" and manager stats"

    _tracker_log(f"RESULT: {msg}")
    _tracker_log_flush("FINAL SUMMARY")

    return True, msg, entries
