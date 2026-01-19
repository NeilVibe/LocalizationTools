"""
Tracker Data Module
===================
Core tracker operations: create/load tracker, update _DAILY_DATA sheet.
"""

import openpyxl
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TRACKER_PATH
from core.excel_ops import safe_load_workbook


# =============================================================================
# TRACKER INITIALIZATION
# =============================================================================

def get_or_create_tracker(tracker_path: Path = None) -> Tuple[openpyxl.Workbook, Path]:
    """
    Load existing tracker or create new one with sheets.

    Args:
        tracker_path: Optional custom tracker path (defaults to TRACKER_PATH)

    Returns:
        Tuple of (workbook, path)
    """
    if tracker_path is None:
        tracker_path = TRACKER_PATH

    if tracker_path.exists():
        wb = safe_load_workbook(tracker_path)
    else:
        wb = openpyxl.Workbook()
        # Remove default sheet
        default_sheet = wb.active
        # Create sheets in order
        wb.create_sheet("DAILY", 0)
        wb.create_sheet("TOTAL", 1)
        wb.create_sheet("_DAILY_DATA", 2)
        # Remove default sheet
        wb.remove(default_sheet)
        # Hide data sheet
        wb["_DAILY_DATA"].sheet_state = 'hidden'

    return wb, tracker_path


# =============================================================================
# _DAILY_DATA SHEET OPERATIONS
# =============================================================================

# Schema for _DAILY_DATA sheet
DAILY_DATA_HEADERS = [
    "Date",        # 1
    "User",        # 2
    "Category",    # 3
    "TotalRows",   # 4
    "Done",        # 5
    "Issues",      # 6
    "NoIssue",     # 7
    "Blocked",     # 8
    "Fixed",       # 9
    "Reported",    # 10
    "Checking",    # 11
    "NonIssue",    # 12
    "WordCount",   # 13
    "Korean",      # 14
]


def update_daily_data_sheet(
    wb: openpyxl.Workbook,
    daily_entries: List[Dict],
    manager_stats: Dict = None,
    manager_dates: Dict = None
) -> None:
    """
    Update hidden _DAILY_DATA sheet with new entries including manager stats.

    Args:
        wb: Tracker workbook
        daily_entries: List of dicts with:
            {date, user, category, total_rows, done, issues, no_issue, blocked,
             word_count, korean}
        manager_stats: Optional dict of:
            {category: {user: {fixed, reported, checking, nonissue}}}
        manager_dates: Optional dict of:
            {(category, user): file_date} - dates from master file mtime

    Mode: REPLACE - same (date, user, category) overwrites existing row
    """
    if manager_stats is None:
        manager_stats = {}
    if manager_dates is None:
        manager_dates = {}

    ws = wb["_DAILY_DATA"]

    # Ensure headers exist (14 columns total)
    if ws.cell(1, 1).value != "Date" or ws.max_column < 14:
        for col, header in enumerate(DAILY_DATA_HEADERS, 1):
            ws.cell(1, col, header)

    # Build index of existing rows: (date, user, category) -> row_number
    existing = {}
    for row in range(2, ws.max_row + 1):
        key = (
            ws.cell(row, 1).value,  # Date
            ws.cell(row, 2).value,  # User
            ws.cell(row, 3).value   # Category
        )
        if key[0] is not None:  # Only index non-empty rows
            existing[key] = row

    # Update or insert entries from daily_entries (tester stats)
    for entry in daily_entries:
        key = (entry["date"], entry["user"], entry["category"])

        if key in existing:
            row = existing[key]
        else:
            row = ws.max_row + 1
            existing[key] = row

        # Get manager stats for this user/category
        category = entry["category"]
        user = entry["user"]
        user_manager_stats = manager_stats.get(category, {}).get(
            user,
            {"fixed": 0, "reported": 0, "checking": 0, "nonissue": 0}
        )

        # Write row data according to schema
        ws.cell(row, 1, entry["date"])
        ws.cell(row, 2, entry["user"])
        ws.cell(row, 3, entry["category"])
        ws.cell(row, 4, entry.get("total_rows", 0))      # TotalRows
        ws.cell(row, 5, entry["done"])                   # Done
        ws.cell(row, 6, entry["issues"])                 # Issues
        ws.cell(row, 7, entry["no_issue"])               # NoIssue
        ws.cell(row, 8, entry["blocked"])                # Blocked
        ws.cell(row, 9, user_manager_stats["fixed"])     # Fixed
        ws.cell(row, 10, user_manager_stats["reported"]) # Reported
        ws.cell(row, 11, user_manager_stats["checking"]) # Checking
        ws.cell(row, 12, user_manager_stats["nonissue"]) # NonIssue
        ws.cell(row, 13, entry.get("word_count", 0))     # WordCount
        ws.cell(row, 14, entry.get("korean", 0))         # Korean

    # Also update/create rows for manager stats
    # This handles the case where we're only updating manager stats (no QA folders)
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    print("\n" + "="*70)
    print("GRANULAR DEBUG: update_daily_data_sheet() - MANAGER STATS SECTION")
    print("="*70)

    print(f"\n[STEP 1] INPUTS RECEIVED:")
    print(f"  - manager_stats type: {type(manager_stats)}")
    print(f"  - manager_stats is None: {manager_stats is None}")
    print(f"  - manager_stats length: {len(manager_stats) if manager_stats else 0}")
    if manager_stats:
        print(f"  - Categories in manager_stats: {list(manager_stats.keys())}")
        for cat, users in manager_stats.items():
            print(f"    - {cat}: {len(users)} users -> {list(users.keys())[:3]}...")

    print(f"\n[STEP 2] WORKSHEET STATE BEFORE WRITE:")
    print(f"  - ws.max_row = {ws.max_row}")
    print(f"  - ws.max_column = {ws.max_column}")
    print(f"  - Header row (row 1): {[ws.cell(1, c).value for c in range(1, 15)]}")
    if ws.max_row >= 2:
        print(f"  - Row 2 sample: {[ws.cell(2, c).value for c in range(1, 15)]}")

    # Build index of existing rows: (user, category) -> {row, date}
    # This is needed because max_row may not update correctly after cell writes
    existing_user_cat = {}
    actual_max_row = ws.max_row  # Start from current sheet max row

    print(f"\n[STEP 3] BUILDING EXISTING ROW INDEX:")
    print(f"  - Starting actual_max_row = {actual_max_row}")
    print(f"  - Scanning rows 2 to {ws.max_row + 1}...")

    for row in range(2, ws.max_row + 1):
        row_user = ws.cell(row, 2).value
        row_category = ws.cell(row, 3).value
        row_date = ws.cell(row, 1).value
        if row_user and row_category:
            key = (row_user, row_category)
            # Keep the latest date row for each user/category combo
            if key not in existing_user_cat or str(row_date) > str(existing_user_cat[key]["date"]):
                existing_user_cat[key] = {"row": row, "date": row_date}
                print(f"    - Indexed row {row}: user={row_user}, cat={row_category}, date={row_date}")
            actual_max_row = max(actual_max_row, row)

    print(f"  - Final existing_user_cat count: {len(existing_user_cat)}")
    print(f"  - Final actual_max_row: {actual_max_row}")

    print(f"\n[STEP 4] WRITING MANAGER STATS TO EXCEL:")
    rows_created = 0
    rows_updated = 0

    for category, users in manager_stats.items():
        print(f"\n  Processing category: {category} ({len(users)} users)")
        for user, stats in users.items():
            # Get the date from manager_dates (file mtime), fallback to today
            file_date = manager_dates.get((category, user), today)

            print(f"    User: {user}")
            print(f"      - stats type: {type(stats)}")
            print(f"      - stats keys: {list(stats.keys()) if isinstance(stats, dict) else 'NOT A DICT'}")
            print(f"      - stats['fixed']: {stats.get('fixed', 'KEY NOT FOUND')}")
            print(f"      - stats['reported']: {stats.get('reported', 'KEY NOT FOUND')}")
            print(f"      - file_date: {file_date}")

            key = (user, category)
            if key in existing_user_cat:
                # Update existing row's manager stats
                found_row = existing_user_cat[key]["row"]
                print(f"      -> UPDATING existing row {found_row}")
                ws.cell(found_row, 9, stats["fixed"])      # Fixed
                ws.cell(found_row, 10, stats["reported"])  # Reported
                ws.cell(found_row, 11, stats["checking"])  # Checking
                ws.cell(found_row, 12, stats["nonissue"])  # NonIssue
                rows_updated += 1
            else:
                # No existing row - create new row with manager stats only
                actual_max_row += 1  # Increment our tracked max row
                new_row = actual_max_row
                print(f"      -> CREATING new row {new_row}")
                ws.cell(new_row, 1, file_date)             # Date (from file mtime, not today!)
                ws.cell(new_row, 2, user)                  # User
                ws.cell(new_row, 3, category)              # Category
                ws.cell(new_row, 4, 0)                     # TotalRows
                ws.cell(new_row, 5, 0)                     # Done
                ws.cell(new_row, 6, 0)                     # Issues
                ws.cell(new_row, 7, 0)                     # NoIssue
                ws.cell(new_row, 8, 0)                     # Blocked
                ws.cell(new_row, 9, stats["fixed"])        # Fixed
                ws.cell(new_row, 10, stats["reported"])    # Reported
                ws.cell(new_row, 11, stats["checking"])    # Checking
                ws.cell(new_row, 12, stats["nonissue"])    # NonIssue
                ws.cell(new_row, 13, 0)                    # WordCount
                ws.cell(new_row, 14, 0)                    # Korean
                # Add to index so duplicates in same batch don't overwrite
                existing_user_cat[key] = {"row": new_row, "date": file_date}
                rows_created += 1

                # VERIFY the write
                print(f"      -> VERIFY row {new_row}: Date={ws.cell(new_row, 1).value}, User={ws.cell(new_row, 2).value}, Fixed={ws.cell(new_row, 9).value}")

    print(f"\n[STEP 5] WRITE SUMMARY:")
    print(f"  - Rows updated: {rows_updated}")
    print(f"  - Rows created: {rows_created}")
    print(f"  - Final actual_max_row: {actual_max_row}")
    print(f"  - ws.max_row after writes: {ws.max_row}")

    print(f"\n[STEP 6] SAMPLE OF WRITTEN DATA:")
    for r in range(2, min(actual_max_row + 1, 7)):  # Show first 5 data rows
        print(f"  Row {r}: {[ws.cell(r, c).value for c in range(1, 15)]}")

    print("="*70 + "\n")


def read_daily_data(wb: openpyxl.Workbook) -> Dict:
    """
    Read all data from _DAILY_DATA sheet.

    Returns:
        Dict with structure: raw_data[date][user][category] = {
            total_rows, done, issues, no_issue, blocked, korean,
            fixed, reported, checking, nonissue, word_count
        }
    """
    from collections import defaultdict

    ws = wb["_DAILY_DATA"]

    # Structure: raw_data[date][user][category] = {...stats...}
    raw_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
        "total_rows": 0, "done": 0, "issues": 0, "no_issue": 0, "blocked": 0, "korean": 0,
        "fixed": 0, "reported": 0, "checking": 0, "nonissue": 0, "word_count": 0
    })))
    users = set()
    categories = set()

    for row in range(2, ws.max_row + 1):
        date = ws.cell(row, 1).value
        user = ws.cell(row, 2).value
        category = ws.cell(row, 3).value or "Unknown"
        total_rows = ws.cell(row, 4).value or 0
        done = ws.cell(row, 5).value or 0
        issues = ws.cell(row, 6).value or 0
        no_issue = ws.cell(row, 7).value or 0
        blocked = ws.cell(row, 8).value or 0
        fixed = ws.cell(row, 9).value or 0
        reported = ws.cell(row, 10).value or 0
        checking = ws.cell(row, 11).value or 0
        nonissue = ws.cell(row, 12).value or 0
        word_count = ws.cell(row, 13).value or 0
        korean = ws.cell(row, 14).value or 0

        if date and user:
            # Store per-category data
            raw_data[date][user][category]["total_rows"] = total_rows
            raw_data[date][user][category]["done"] = done
            raw_data[date][user][category]["issues"] = issues
            raw_data[date][user][category]["no_issue"] = no_issue
            raw_data[date][user][category]["blocked"] = blocked
            raw_data[date][user][category]["korean"] = korean
            raw_data[date][user][category]["fixed"] = fixed
            raw_data[date][user][category]["reported"] = reported
            raw_data[date][user][category]["checking"] = checking
            raw_data[date][user][category]["nonissue"] = nonissue
            raw_data[date][user][category]["word_count"] = word_count
            users.add(user)
            categories.add(category)

    return {
        "raw_data": dict(raw_data),
        "users": users,
        "categories": categories,
        "dates": sorted(raw_data.keys())
    }


def compute_daily_deltas(raw_data: Dict, users: set, categories: set, dates: list) -> Dict:
    """
    Compute daily deltas per (user, category), then aggregate.

    This prevents cross-category contamination in delta calculation.
    The fix for the Quest delta bug.

    Args:
        raw_data: Dict from read_daily_data
        users: Set of all usernames
        categories: Set of all categories
        dates: Sorted list of all dates

    Returns:
        Dict: daily_delta[date][user] = {done, issues, no_issue, blocked, korean,
                                         fixed, reported, checking, nonissue, word_count}
    """
    from collections import defaultdict

    default_data = {
        "total_rows": 0, "done": 0, "issues": 0, "no_issue": 0, "blocked": 0, "korean": 0,
        "fixed": 0, "reported": 0, "checking": 0, "nonissue": 0, "word_count": 0
    }

    daily_delta = defaultdict(lambda: defaultdict(lambda: default_data.copy()))

    # For each (user, category), find dates where that combo has data and compute deltas
    for user in users:
        for category in categories:
            # Get all dates where this user+category has data
            user_cat_dates = sorted([
                d for d in dates
                if category in raw_data.get(d, {}).get(user, {})
            ])

            for i, date in enumerate(user_cat_dates):
                current = raw_data[date][user][category]

                if i == 0:
                    prev = default_data.copy()
                else:
                    prev_date = user_cat_dates[i - 1]
                    prev = raw_data[prev_date][user][category]

                # Calculate delta for this category (ensure non-negative)
                cat_delta_total_rows = current["total_rows"]  # total_rows is not cumulative
                cat_delta_done = max(0, current["done"] - prev["done"])
                cat_delta_issues = max(0, current["issues"] - prev["issues"])
                cat_delta_no_issue = max(0, current["no_issue"] - prev["no_issue"])
                cat_delta_blocked = max(0, current["blocked"] - prev["blocked"])
                cat_delta_korean = max(0, current["korean"] - prev["korean"])
                cat_delta_fixed = max(0, current["fixed"] - prev["fixed"])
                cat_delta_reported = max(0, current["reported"] - prev["reported"])
                cat_delta_checking = max(0, current["checking"] - prev["checking"])
                cat_delta_nonissue = max(0, current["nonissue"] - prev["nonissue"])
                cat_delta_word_count = max(0, current["word_count"] - prev["word_count"])

                # Aggregate this category's delta into the (date, user) totals
                daily_delta[date][user]["total_rows"] += cat_delta_total_rows
                daily_delta[date][user]["done"] += cat_delta_done
                daily_delta[date][user]["issues"] += cat_delta_issues
                daily_delta[date][user]["no_issue"] += cat_delta_no_issue
                daily_delta[date][user]["blocked"] += cat_delta_blocked
                daily_delta[date][user]["korean"] += cat_delta_korean
                daily_delta[date][user]["fixed"] += cat_delta_fixed
                daily_delta[date][user]["reported"] += cat_delta_reported
                daily_delta[date][user]["checking"] += cat_delta_checking
                daily_delta[date][user]["nonissue"] += cat_delta_nonissue
                daily_delta[date][user]["word_count"] += cat_delta_word_count

    return dict(daily_delta)
