#!/usr/bin/env python3
"""
QA Excel Compiler
=================
Compiles QA tester Excel files into master sheets.

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

# Column indices (1-based for openpyxl)
COL_STATUS = 5      # E
COL_COMMENT = 6     # F
COL_SCREENSHOT = 7  # G

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


def get_or_create_master(category, template_file=None):
    """
    Load existing master file or create from template.

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

        # Clear STATUS, COMMENT, SCREENSHOT columns (keep structure)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in range(2, ws.max_row + 1):
                ws.cell(row=row, column=COL_STATUS).value = None
                ws.cell(row=row, column=COL_COMMENT).value = None
                ws.cell(row=row, column=COL_SCREENSHOT).value = None

        return wb, master_path
    else:
        print(f"  ERROR: No template file for {category}")
        return None, master_path


def get_comment_column(ws, username):
    """
    Find or create COMMENT_{username} column.

    Args:
        ws: Worksheet
        username: User identifier

    Returns: Column index (1-based)
    """
    col_name = f"COMMENT_{username}"

    # Check if column already exists
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header == col_name:
            return col

    # Find last COMMENT_ column or use position after base COMMENT column
    last_col = COL_COMMENT
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header and str(header).startswith("COMMENT_"):
            last_col = col

    # Insert new column after last comment column
    new_col = last_col + 1
    ws.insert_cols(new_col)
    ws.cell(row=1, column=new_col).value = col_name

    print(f"    Created column: {col_name} at {get_column_letter(new_col)}")
    return new_col


def format_comment(new_comment, existing_comment=None):
    """
    Format comment with datetime, append to existing if present.

    Format: "comment text" (date: YYMMDD HHMM)

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
    formatted = f'"{new_text}" (date: {timestamp})'

    if existing_comment and str(existing_comment).strip():
        # New on top, old below
        return f"{formatted}\n\n{existing_comment}"
    else:
        return formatted


def process_sheet(master_ws, qa_ws, username):
    """
    Process a single sheet: copy COMMENT from QA to master, collect STATUS stats.

    Returns: Dict with {comments: n, stats: {issue: n, no_issue: n, blocked: n, total: n}}
    """
    # Get or create user's COMMENT column only (no STATUS column per user)
    comment_col = get_comment_column(master_ws, username)

    result = {
        "comments": 0,
        "stats": {"issue": 0, "no_issue": 0, "blocked": 0, "total": 0}
    }
    max_row = min(master_ws.max_row, qa_ws.max_row)

    for row in range(2, max_row + 1):  # Skip header
        result["stats"]["total"] += 1

        # Get QA STATUS (for stats only, not copied to master)
        qa_status = qa_ws.cell(row=row, column=COL_STATUS).value
        if qa_status:
            status_upper = str(qa_status).strip().upper()
            if status_upper == "ISSUE":
                result["stats"]["issue"] += 1
            elif status_upper == "NO ISSUE":
                result["stats"]["no_issue"] += 1
            elif status_upper == "BLOCKED":
                result["stats"]["blocked"] += 1

        # Get QA COMMENT
        qa_comment = qa_ws.cell(row=row, column=COL_COMMENT).value
        if qa_comment and str(qa_comment).strip():
            # Get existing comment in master
            existing = master_ws.cell(row=row, column=comment_col).value

            # Format and update (appends if different)
            new_value = format_comment(qa_comment, existing)
            master_ws.cell(row=row, column=comment_col).value = new_value
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

            print(f"    {sheet_name}: {result['comments']} comments, {stats['issue']} issues, {stats['no_issue']} OK, {stats['blocked']} blocked")

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
    print("QA Excel Compiler")
    print("="*60)

    # Ensure folders exist
    ensure_master_folder()

    # Discover QA files
    qa_files = discover_qa_files()

    if not qa_files:
        print("\nNo valid QA files found in QAfolder/")
        print("Expected format: Username_Category.xlsx")
        print(f"Valid categories: {', '.join(CATEGORIES)}")
        return

    print(f"\nFound {len(qa_files)} QA file(s)")

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
