#!/usr/bin/env python3
"""
QA Excel Compiler (Robust Version)
===================================
Compiles QA tester Excel files into master sheets.

Works with ANY Excel structure - finds columns dynamically.

Usage:
    python3 compile_qa.py

Input:  QAfolder/{Username}_{Category}.xlsx
Output: Masterfolder/Master_{Category}.xlsx

Categories: Quest, Knowledge, Item, Node, System
"""

import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side


# === CONFIGURATION ===
SCRIPT_DIR = Path(__file__).parent
QA_FOLDER = SCRIPT_DIR / "QAfolder"
MASTER_FOLDER = SCRIPT_DIR / "Masterfolder"
CATEGORIES = ["Quest", "Knowledge", "Item", "Node", "System"]

# Valid STATUS values (only these count as "filled")
VALID_STATUS = ["ISSUE", "NO ISSUE", "BLOCKED"]


def discover_qa_files():
    """
    Find all QA Excel files and parse their metadata.

    Returns: List of dicts with {filepath, username, category}
    """
    files = []

    if not QA_FOLDER.exists():
        print(f"ERROR: QAfolder not found: {QA_FOLDER}")
        return files

    for f in QA_FOLDER.glob("*.xlsx"):
        # Skip temp files
        if f.name.startswith("~$"):
            continue

        # Parse: Username_Category.xlsx
        parts = f.stem.split("_")
        if len(parts) >= 2:
            username = parts[0]
            category = parts[1]

            if category in CATEGORIES:
                files.append({
                    "filepath": f,
                    "username": username,
                    "category": category
                })
            else:
                print(f"WARN: Unknown category '{category}' in {f.name}")
        else:
            print(f"WARN: Invalid filename format: {f.name} (expected: Username_Category.xlsx)")

    return files


def ensure_master_folder():
    """Create Masterfolder if it doesn't exist."""
    MASTER_FOLDER.mkdir(exist_ok=True)


def find_column_by_header(ws, header_name, case_insensitive=True):
    """
    Find column index by header name.

    Args:
        ws: Worksheet
        header_name: Header to search for
        case_insensitive: Match case-insensitively

    Returns: Column index (1-based) or None if not found
    """
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header:
            header_str = str(header).strip()
            if case_insensitive:
                if header_str.upper() == header_name.upper():
                    return col
            else:
                if header_str == header_name:
                    return col
    return None


def get_or_create_master(category, template_file=None):
    """
    Load existing master file or create from template.

    CLEAN START: When creating new master, DELETE STATUS/COMMENT/SCREENSHOT
    columns entirely (not just clear values). Master starts clean with only
    data columns, then COMMENT_{User} columns are added at MAX_COLUMN + 1.

    Args:
        category: Category name (Quest, Knowledge, etc.)
        template_file: Path to first QA file to use as template

    Returns: openpyxl Workbook
    """
    master_path = MASTER_FOLDER / f"Master_{category}.xlsx"

    if master_path.exists():
        print(f"  Loading existing: {master_path.name}")
        return openpyxl.load_workbook(master_path), master_path
    elif template_file:
        print(f"  Creating new master from: {template_file.name}")
        wb = openpyxl.load_workbook(template_file)

        # DELETE STATUS, COMMENT, SCREENSHOT, STRINGID columns entirely (CLEAN START)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]

            # Find columns to delete (must delete from right to left to preserve indices)
            cols_to_delete = []

            status_col = find_column_by_header(ws, "STATUS")
            comment_col = find_column_by_header(ws, "COMMENT")
            screenshot_col = find_column_by_header(ws, "SCREENSHOT")
            stringid_col = find_column_by_header(ws, "STRINGID")

            if status_col:
                cols_to_delete.append(status_col)
            if comment_col:
                cols_to_delete.append(comment_col)
            if screenshot_col:
                cols_to_delete.append(screenshot_col)
            if stringid_col:
                cols_to_delete.append(stringid_col)

            # Sort descending (delete from right to left)
            cols_to_delete.sort(reverse=True)

            for col in cols_to_delete:
                ws.delete_cols(col)
                print(f"    Deleted column {col} from {sheet_name}")

        print(f"    Master cleaned: STATUS/COMMENT/SCREENSHOT/STRINGID removed")
        return wb, master_path
    else:
        print(f"  ERROR: No template file for {category}")
        return None, master_path


def get_or_create_user_comment_column(ws, username):
    """
    Find or create COMMENT_{username} column using MAX_COLUMN + 1.

    ROBUST: Always adds new columns at the far right (max_column + 1).
    Works with ANY Excel structure.

    BEAUTIFUL: Adds color, bold, and border formatting to header.

    Args:
        ws: Worksheet
        username: User identifier

    Returns: Column index (1-based)
    """
    col_name = f"COMMENT_{username}"

    # Check if column already exists
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header and str(header).strip() == col_name:
            return col

    # MAX_COLUMN + 1: Add new column at the far right
    new_col = ws.max_column + 1
    cell = ws.cell(row=1, column=new_col)
    cell.value = col_name

    # Beautiful formatting for COMMENT_{User} header
    # Light blue background
    cell.fill = PatternFill(start_color="87CEEB", end_color="87CEEB", fill_type="solid")
    # Bold font
    cell.font = Font(bold=True, color="000000")
    # Center alignment
    cell.alignment = Alignment(horizontal='center', vertical='center')
    # Nice border
    cell.border = Border(
        left=Side(style='medium', color='4472C4'),
        right=Side(style='medium', color='4472C4'),
        top=Side(style='medium', color='4472C4'),
        bottom=Side(style='medium', color='4472C4')
    )

    # Set column width for readability
    ws.column_dimensions[get_column_letter(new_col)].width = 35

    print(f"    Created column: {col_name} at {get_column_letter(new_col)} (styled)")
    return new_col


def format_comment(new_comment, string_id=None, existing_comment=None):
    """
    Format comment with StringID and datetime, append to existing if present.

    Format: "comment text" (stringid: 12345 // date: YYMMDD HHMM)

    Duplicate check: If the exact comment text already exists (ignoring date),
    we skip to avoid duplicating on re-runs.
    """
    if not new_comment or str(new_comment).strip() == "":
        return existing_comment

    new_text = str(new_comment).strip()

    # Check if this exact comment already exists (avoid duplicates on re-run)
    if existing_comment:
        existing_str = str(existing_comment)
        # Extract comment texts (between quotes) from existing
        if f'"{new_text}"' in existing_str:
            # Comment already exists, skip
            return existing_comment

    timestamp = datetime.now().strftime("%y%m%d %H%M")

    # Build metadata string with stringid (if available) and date
    if string_id and str(string_id).strip():
        metadata = f"stringid: {str(string_id).strip()} // date: {timestamp}"
    else:
        metadata = f"date: {timestamp}"

    formatted = f'"{new_text}" ({metadata})'

    if existing_comment and str(existing_comment).strip():
        # New on top, old below
        return f"{formatted}\n\n{existing_comment}"
    else:
        return formatted


def get_row_signature(ws, row, exclude_cols=None):
    """
    Get a signature for a row based on non-empty cells (excluding specified columns).
    Used for fallback row matching.

    Args:
        ws: Worksheet
        row: Row number
        exclude_cols: Set of column indices to exclude (STATUS, COMMENT, SCREENSHOT)

    Returns: Tuple of (col_index, value) for non-empty cells
    """
    if exclude_cols is None:
        exclude_cols = set()

    signature = []
    for col in range(1, ws.max_column + 1):
        if col in exclude_cols:
            continue
        val = ws.cell(row=row, column=col).value
        if val and str(val).strip():
            signature.append((col, str(val).strip()))

    return tuple(signature)


def find_matching_row_fallback(master_ws, qa_signature, exclude_cols, start_row=2):
    """
    Find a row in master that matches QA row by 2+ cell matching.

    Args:
        master_ws: Master worksheet
        qa_signature: Signature from QA row
        exclude_cols: Columns to exclude from matching
        start_row: Start searching from this row

    Returns: Row number or None
    """
    if len(qa_signature) < 2:
        return None  # Need at least 2 cells to match

    for row in range(start_row, master_ws.max_row + 1):
        master_sig = get_row_signature(master_ws, row, exclude_cols)

        # Count matching cells
        matches = 0
        for (col, val) in qa_signature:
            if (col, val) in master_sig:
                matches += 1

        # 2+ cell match = found
        if matches >= 2:
            return row

    return None


def process_sheet(master_ws, qa_ws, username):
    """
    Process a single sheet: copy COMMENT from QA to master, collect STATUS stats.

    ROBUST VERSION:
    - Finds COMMENT/STATUS/STRINGID columns dynamically by header name
    - Uses MAX_COLUMN + 1 for user comment columns
    - Falls back to 2+ cell matching if row counts differ
    - Applies beautiful styling to comment cells (blue fill + bold)

    Returns: Dict with {comments: n, stats: {issue: n, no_issue: n, blocked: n, total: n}}
    """
    # Find columns dynamically in QA worksheet
    qa_status_col = find_column_by_header(qa_ws, "STATUS")
    qa_comment_col = find_column_by_header(qa_ws, "COMMENT")
    qa_screenshot_col = find_column_by_header(qa_ws, "SCREENSHOT")
    qa_stringid_col = find_column_by_header(qa_ws, "STRINGID")

    # Build exclude set for row signature matching
    qa_exclude_cols = set()
    if qa_status_col:
        qa_exclude_cols.add(qa_status_col)
    if qa_comment_col:
        qa_exclude_cols.add(qa_comment_col)
    if qa_screenshot_col:
        qa_exclude_cols.add(qa_screenshot_col)
    if qa_stringid_col:
        qa_exclude_cols.add(qa_stringid_col)

    # Find or create COMMENT_{username} in master (MAX_COLUMN + 1)
    master_comment_col = get_or_create_user_comment_column(master_ws, username)

    # Build exclude set for master row matching
    master_status_col = find_column_by_header(master_ws, "STATUS")
    master_orig_comment_col = find_column_by_header(master_ws, "COMMENT")
    master_screenshot_col = find_column_by_header(master_ws, "SCREENSHOT")

    master_exclude_cols = set()
    if master_status_col:
        master_exclude_cols.add(master_status_col)
    if master_orig_comment_col:
        master_exclude_cols.add(master_orig_comment_col)
    if master_screenshot_col:
        master_exclude_cols.add(master_screenshot_col)
    # Also exclude all COMMENT_* columns
    for col in range(1, master_ws.max_column + 1):
        header = master_ws.cell(row=1, column=col).value
        if header and str(header).startswith("COMMENT_"):
            master_exclude_cols.add(col)

    result = {
        "comments": 0,
        "stats": {"issue": 0, "no_issue": 0, "blocked": 0, "total": 0},
        "fallback_used": 0
    }

    # Determine if we need fallback matching
    use_fallback = (master_ws.max_row != qa_ws.max_row)
    if use_fallback:
        print(f"      Row count differs (master:{master_ws.max_row}, qa:{qa_ws.max_row}), using fallback matching")

    for qa_row in range(2, qa_ws.max_row + 1):  # Skip header
        result["stats"]["total"] += 1

        # Determine master row (index match or fallback)
        if use_fallback:
            qa_sig = get_row_signature(qa_ws, qa_row, qa_exclude_cols)
            master_row = find_matching_row_fallback(master_ws, qa_sig, master_exclude_cols)
            if master_row is None:
                # No match found, skip this row
                continue
            result["fallback_used"] += 1
        else:
            master_row = qa_row  # Direct index matching

        # Get QA STATUS (for stats only, not copied to master)
        if qa_status_col:
            qa_status = qa_ws.cell(row=qa_row, column=qa_status_col).value
            if qa_status:
                status_upper = str(qa_status).strip().upper()
                if status_upper == "ISSUE":
                    result["stats"]["issue"] += 1
                elif status_upper == "NO ISSUE":
                    result["stats"]["no_issue"] += 1
                elif status_upper == "BLOCKED":
                    result["stats"]["blocked"] += 1

        # Get QA COMMENT and STRINGID, copy to master with styling
        if qa_comment_col:
            qa_comment = qa_ws.cell(row=qa_row, column=qa_comment_col).value
            if qa_comment and str(qa_comment).strip():
                # Get StringID if available
                string_id = None
                if qa_stringid_col:
                    string_id = qa_ws.cell(row=qa_row, column=qa_stringid_col).value

                # Get existing comment in master
                existing = master_ws.cell(row=master_row, column=master_comment_col).value

                # Format and update (appends if different, includes stringid)
                new_value = format_comment(qa_comment, string_id, existing)

                # ONLY write if there's actually new content (preserve team's custom formatting!)
                if new_value != existing:
                    cell = master_ws.cell(row=master_row, column=master_comment_col)
                    cell.value = new_value

                    # Apply styling: light blue fill + bold for visibility
                    cell.fill = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(wrap_text=True, vertical='top')
                    cell.border = Border(
                        left=Side(style='thin', color='87CEEB'),
                        right=Side(style='thin', color='87CEEB'),
                        top=Side(style='thin', color='87CEEB'),
                        bottom=Side(style='thin', color='87CEEB')
                    )

                    result["comments"] += 1

    return result


def update_status_sheet(wb, users, user_stats):
    """
    Create/update STATUS sheet with completion tracking and detailed stats.

    Args:
        wb: Master workbook
        users: Set of usernames
        user_stats: {username: {total: n, issue: n, no_issue: n, blocked: n}}
    """
    # Create or clear STATUS sheet
    if "STATUS" in wb.sheetnames:
        del wb["STATUS"]

    ws = wb.create_sheet("STATUS", 0)  # Insert at position 0 (first tab)

    # Styles
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold/Yellow
    header_font = Font(bold=True)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    center = Alignment(horizontal='center')

    # Headers
    headers = ["User", "Completion %", "Total Rows", "ISSUE #", "NO ISSUE %", "BLOCKED %"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = center

    # Data rows
    for row_idx, user in enumerate(sorted(users), 2):
        stats = user_stats.get(user, {"total": 0, "issue": 0, "no_issue": 0, "blocked": 0})

        total = stats["total"]
        issue = stats["issue"]
        no_issue = stats["no_issue"]
        blocked = stats["blocked"]
        completed = issue + no_issue + blocked

        # Calculate percentages
        completion_pct = round(completed / total * 100, 1) if total > 0 else 0
        no_issue_pct = round(no_issue / total * 100, 1) if total > 0 else 0
        blocked_pct = round(blocked / total * 100, 1) if total > 0 else 0

        # Write data
        row_data = [
            user,
            f"{completion_pct}%",
            total,
            issue,  # Raw number for ISSUE
            f"{no_issue_pct}%",
            f"{blocked_pct}%"
        ]

        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.border = border
            if col > 1:
                cell.alignment = center

    # Adjust column widths
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 10
    ws.column_dimensions['E'].width = 14
    ws.column_dimensions['F'].width = 12

    print(f"  Updated STATUS sheet with {len(users)} users (first tab, yellow header)")


def process_category(category, qa_files):
    """
    Process all QA files for one category.
    """
    print(f"\n{'='*50}")
    print(f"Processing: {category} ({len(qa_files)} files)")
    print(f"{'='*50}")

    # Get or create master
    first_file = qa_files[0]["filepath"]
    master_wb, master_path = get_or_create_master(category, first_file)

    if master_wb is None:
        return

    # Track users and aggregated stats
    all_users = set()
    user_stats = defaultdict(lambda: {"total": 0, "issue": 0, "no_issue": 0, "blocked": 0})

    # Process each QA file
    for qf in qa_files:
        username = qf["username"]
        filepath = qf["filepath"]
        all_users.add(username)

        print(f"\n  File: {filepath.name}")

        qa_wb = openpyxl.load_workbook(filepath)

        for sheet_name in qa_wb.sheetnames:
            # Skip STATUS sheets
            if sheet_name == "STATUS":
                continue

            # Check if sheet exists in master
            if sheet_name not in master_wb.sheetnames:
                print(f"    WARN: Sheet '{sheet_name}' not in master, skipping")
                continue

            # Process sheet and collect stats
            result = process_sheet(master_wb[sheet_name], qa_wb[sheet_name], username)
            stats = result["stats"]

            fallback_info = f", fallback:{result['fallback_used']}" if result.get('fallback_used', 0) > 0 else ""
            print(f"    {sheet_name}: {result['comments']} comments, {stats['issue']} issues, {stats['no_issue']} OK, {stats['blocked']} blocked{fallback_info}")

            # Aggregate stats for this user across all sheets
            user_stats[username]["total"] += stats["total"]
            user_stats[username]["issue"] += stats["issue"]
            user_stats[username]["no_issue"] += stats["no_issue"]
            user_stats[username]["blocked"] += stats["blocked"]

        qa_wb.close()

    # Update STATUS sheet (first tab, with stats)
    update_status_sheet(master_wb, all_users, user_stats)

    # Save master
    master_wb.save(master_path)
    print(f"\n  Saved: {master_path}")


def main():
    """Main entry point."""
    print("="*60)
    print("QA Excel Compiler (Robust Version)")
    print("="*60)
    print("Features:")
    print("  - Dynamic column detection (finds STATUS/COMMENT by header)")
    print("  - MAX_COLUMN + 1 for user columns (works with ANY structure)")
    print("  - Fallback row matching (2+ cell match if row counts differ)")
    print()

    # Ensure folders exist
    ensure_master_folder()

    # Discover QA files
    qa_files = discover_qa_files()

    if not qa_files:
        print("\nNo valid QA files found in QAfolder/")
        print("Expected format: Username_Category.xlsx")
        print(f"Valid categories: {', '.join(CATEGORIES)}")
        return

    print(f"Found {len(qa_files)} QA file(s)")

    # Group by category
    by_category = defaultdict(list)
    for qf in qa_files:
        by_category[qf["category"]].append(qf)

    # Process each category
    for category in CATEGORIES:
        if category in by_category:
            process_category(category, by_category[category])
        else:
            print(f"\nSKIP: No files for category '{category}'")

    print("\n" + "="*60)
    print("Compilation complete!")
    print("="*60)


if __name__ == "__main__":
    main()
