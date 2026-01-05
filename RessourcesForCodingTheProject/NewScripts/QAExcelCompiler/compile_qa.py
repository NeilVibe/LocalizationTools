#!/usr/bin/env python3
"""
QA Excel Compiler (Robust Version with Image Compilation)
==========================================================
Compiles QA tester Excel files into master sheets with image consolidation.

Works with ANY Excel structure - finds columns dynamically.

Usage:
    python3 compile_qa.py

Input:  QAfolder/{Username}_{Category}/
        - One .xlsx file per folder
        - Images referenced in SCREENSHOT column

Output: Masterfolder/Master_{Category}.xlsx
        Masterfolder/Images/{Username}_{Category}_{original}.png

Categories: Quest, Knowledge, Item, Node, System

Comment Handling:
- REPLACE mode: New comments replace old (no append/concatenation)
- Timestamp: Uses file's last modified time (not current time)
- Format: comment text\\n---\\nstringid:\\n<value>\\n(updated: YYMMDD HHMM)
- Duplicate check: Splits on '---' delimiter to compare original comment text
"""

import os
import shutil
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
IMAGES_FOLDER = MASTER_FOLDER / "Images"
CATEGORIES = ["Quest", "Knowledge", "Item", "Node", "System"]

# Supported image extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

# Valid STATUS values (only these count as "filled")
VALID_STATUS = ["ISSUE", "NO ISSUE", "BLOCKED"]

# === TRACKER CONFIGURATION ===
TRACKER_FILENAME = "LQA_UserProgress_Tracker.xlsx"

TRACKER_STYLES = {
    "title_color": "FFD700",       # Gold
    "header_color": "87CEEB",      # Light blue
    "subheader_color": "D3D3D3",   # Light gray
    "alt_row_color": "F5F5F5",     # Alternating gray
    "total_row_color": "E6E6E6",   # Total row gray
    "border_color": "000000",      # Black
}

CHART_COLORS = ["4472C4", "ED7D31", "70AD47", "FFC000", "5B9BD5", "A5A5A5"]


def discover_qa_folders():
    """
    Find all QA folders and parse their metadata.

    Folder format: {Username}_{Category}/
    Each folder contains: one .xlsx file + images

    Returns: List of dicts with {folder_path, xlsx_path, username, category, images}
    """
    results = []

    if not QA_FOLDER.exists():
        print(f"ERROR: QAfolder not found: {QA_FOLDER}")
        return results

    for folder in QA_FOLDER.iterdir():
        if not folder.is_dir():
            continue

        # Skip hidden/temp folders
        if folder.name.startswith('.') or folder.name.startswith('~'):
            continue

        # Parse folder name: {Username}_{Category}
        parts = folder.name.split("_")
        if len(parts) < 2:
            print(f"WARN: Invalid folder name format: {folder.name} (expected: Username_Category)")
            continue

        username = parts[0]
        category = "_".join(parts[1:])  # Handle categories with underscores (though unlikely)

        if category not in CATEGORIES:
            print(f"WARN: Unknown category '{category}' in folder {folder.name}")
            continue

        # Find xlsx file (must be exactly 1)
        xlsx_files = list(folder.glob("*.xlsx"))
        xlsx_files = [f for f in xlsx_files if not f.name.startswith("~$")]

        if len(xlsx_files) == 0:
            print(f"WARN: No xlsx in folder: {folder.name}")
            continue
        if len(xlsx_files) > 1:
            print(f"WARN: Multiple xlsx in folder: {folder.name}, using first: {xlsx_files[0].name}")

        xlsx_path = xlsx_files[0]

        # Find images
        images = [f for f in folder.iterdir()
                  if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]

        results.append({
            "folder_path": folder,
            "xlsx_path": xlsx_path,
            "username": username,
            "category": category,
            "images": images
        })

    return results


def ensure_master_folder():
    """Create Masterfolder and Images subfolder if they don't exist."""
    MASTER_FOLDER.mkdir(exist_ok=True)
    IMAGES_FOLDER.mkdir(exist_ok=True)


def copy_images_with_unique_names(qa_folder_info):
    """
    Copy images from QA folder to Images/ with unique names.

    Naming: {Username}_{Category}_{original_filename}

    Args:
        qa_folder_info: Dict with {folder_path, username, category, images}

    Returns: Dict mapping original_name -> new_name
    """
    username = qa_folder_info["username"]
    category = qa_folder_info["category"]
    images = qa_folder_info["images"]

    image_mapping = {}

    for img_path in images:
        original_name = img_path.name
        new_name = f"{username}_{category}_{original_name}"

        dest_path = IMAGES_FOLDER / new_name

        # Copy image (overwrite if same user re-submits)
        shutil.copy2(img_path, dest_path)

        image_mapping[original_name] = new_name

    if image_mapping:
        print(f"    Copied {len(image_mapping)} images to Images/")

    return image_mapping


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

    # Set column width for readability (only width, preserve hidden state of other columns)
    col_letter = get_column_letter(new_col)
    ws.column_dimensions[col_letter].width = 35
    # Explicitly ensure this new column is visible (don't inherit hidden state)
    ws.column_dimensions[col_letter].hidden = False

    print(f"    Created column: {col_name} at {get_column_letter(new_col)} (styled)")
    return new_col


def get_or_create_user_screenshot_column(ws, username, after_comment_col):
    """
    Find or create SCREENSHOT_{username} column immediately after COMMENT_{username}.

    Args:
        ws: Worksheet
        username: User identifier
        after_comment_col: Column index of COMMENT_{username} (screenshot goes right after)

    Returns: Column index (1-based)
    """
    col_name = f"SCREENSHOT_{username}"

    # Check if column already exists
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header and str(header).strip() == col_name:
            return col

    # Insert new column right after COMMENT_{username}
    new_col = after_comment_col + 1

    # If there's already data after the comment column, we need to insert
    # Actually, since we're using MAX_COLUMN + 1 for COMMENT, SCREENSHOT should be MAX_COLUMN + 1 now
    # But to be safe, let's just use max_column + 1 for screenshot too
    new_col = ws.max_column + 1

    cell = ws.cell(row=1, column=new_col)
    cell.value = col_name

    # Light blue background for screenshot columns (matching COMMENT style)
    cell.fill = PatternFill(start_color="87CEEB", end_color="87CEEB", fill_type="solid")
    # Bold font
    cell.font = Font(bold=True, color="000000")
    # Center alignment
    cell.alignment = Alignment(horizontal='center', vertical='center')
    # Nice border (matching COMMENT style)
    cell.border = Border(
        left=Side(style='medium', color='4472C4'),
        right=Side(style='medium', color='4472C4'),
        top=Side(style='medium', color='4472C4'),
        bottom=Side(style='medium', color='4472C4')
    )

    # Set column width
    col_letter = get_column_letter(new_col)
    ws.column_dimensions[col_letter].width = 40
    ws.column_dimensions[col_letter].hidden = False

    print(f"    Created column: {col_name} at {get_column_letter(new_col)} (styled)")
    return new_col


def format_comment(new_comment, string_id=None, existing_comment=None, file_mod_time=None):
    """
    Format comment with StringID and file modification time.

    Format (with stringid):
        <comment text>
        ---
        stringid:
        <stringid value>
        (updated: YYMMDD HHMM)

    Format (without stringid):
        <comment text>
        ---
        (updated: YYMMDD HHMM)

    REPLACE MODE: If comment text differs, REPLACE entirely (no append).
    DUPLICATE CHECK: Split on '---' delimiter to extract original comment for comparison.
    """
    if not new_comment or str(new_comment).strip() == "":
        return existing_comment  # Return existing if no new comment

    new_text = str(new_comment).strip()

    # Check if this exact comment text already exists (avoid re-update on re-run)
    if existing_comment:
        existing_str = str(existing_comment)
        # Split on --- delimiter to extract original comment
        if "\n---\n" in existing_str:
            existing_original = existing_str.split("\n---\n")[0].strip()
            if existing_original == new_text:
                return existing_comment  # Duplicate, skip

    # Format timestamp from file modification time (or fallback to now)
    if file_mod_time:
        timestamp = file_mod_time.strftime("%y%m%d %H%M")
    else:
        timestamp = datetime.now().strftime("%y%m%d %H%M")

    # Build formatted comment: text + delimiter + metadata
    if string_id and str(string_id).strip():
        # With stringid: comment -> --- -> stringid: -> value -> (updated)
        return f"{new_text}\n---\nstringid:\n{str(string_id).strip()}\n(updated: {timestamp})"
    else:
        # Without stringid: comment -> --- -> (updated)
        return f"{new_text}\n---\n(updated: {timestamp})"


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


def process_sheet(master_ws, qa_ws, username, category, image_mapping=None, xlsx_path=None):
    """
    Process a single sheet: copy COMMENT and SCREENSHOT from QA to master, collect STATUS stats.

    ROBUST VERSION:
    - Finds COMMENT/STATUS/STRINGID/SCREENSHOT columns dynamically by header name
    - Uses MAX_COLUMN + 1 for user comment and screenshot columns
    - Falls back to 2+ cell matching if row counts differ
    - Applies beautiful styling to comment cells (blue fill + bold)
    - Transfers screenshots with hyperlink path transformation
    - Uses file modification time for comment timestamps

    Args:
        master_ws: Master worksheet
        qa_ws: QA worksheet
        username: User identifier
        category: Category name
        image_mapping: Dict mapping original_name -> new_name (for hyperlink transformation)
        xlsx_path: Path to QA xlsx file (for file modification time)

    Returns: Dict with {comments: n, screenshots: n, stats: {...}, fallback_used: n}
    """
    if image_mapping is None:
        image_mapping = {}

    # Get file modification time for timestamp
    file_mod_time = None
    if xlsx_path:
        file_mod_time = datetime.fromtimestamp(xlsx_path.stat().st_mtime)

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

    # Find or create SCREENSHOT_{username} in master (right after COMMENT_{username})
    master_screenshot_col = get_or_create_user_screenshot_column(master_ws, username, master_comment_col)

    # Build exclude set for master row matching
    master_status_col = find_column_by_header(master_ws, "STATUS")
    master_orig_comment_col = find_column_by_header(master_ws, "COMMENT")
    master_orig_screenshot_col = find_column_by_header(master_ws, "SCREENSHOT")

    master_exclude_cols = set()
    if master_status_col:
        master_exclude_cols.add(master_status_col)
    if master_orig_comment_col:
        master_exclude_cols.add(master_orig_comment_col)
    if master_orig_screenshot_col:
        master_exclude_cols.add(master_orig_screenshot_col)
    # Also exclude all COMMENT_* and SCREENSHOT_* columns
    for col in range(1, master_ws.max_column + 1):
        header = master_ws.cell(row=1, column=col).value
        if header and (str(header).startswith("COMMENT_") or str(header).startswith("SCREENSHOT_")):
            master_exclude_cols.add(col)

    result = {
        "comments": 0,
        "screenshots": 0,
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

                # Format and update (REPLACE mode, includes stringid + file mod time)
                new_value = format_comment(qa_comment, string_id, existing, file_mod_time)

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

        # Transfer SCREENSHOT to SCREENSHOT_{username} with hyperlink transformation
        if qa_screenshot_col:
            qa_screenshot_cell = qa_ws.cell(row=qa_row, column=qa_screenshot_col)
            screenshot_value = qa_screenshot_cell.value
            screenshot_hyperlink = qa_screenshot_cell.hyperlink

            if screenshot_value and str(screenshot_value).strip():
                master_screenshot_cell = master_ws.cell(row=master_row, column=master_screenshot_col)
                existing_screenshot = master_screenshot_cell.value

                # Determine the new value and hyperlink target
                new_screenshot_value = None
                new_screenshot_target = None
                is_warning = False  # Orange for missing images

                if screenshot_hyperlink and screenshot_hyperlink.target:
                    # Extract original filename from hyperlink target
                    original_target = screenshot_hyperlink.target
                    original_name = os.path.basename(original_target)

                    # Transform to new path if image was copied
                    if original_name in image_mapping:
                        new_name = image_mapping[original_name]
                        new_screenshot_value = new_name
                        new_screenshot_target = f"Images/{new_name}"
                    else:
                        # Image not found in mapping, preserve original
                        new_screenshot_value = screenshot_value
                        new_screenshot_target = original_target
                        is_warning = True
                else:
                    # No hyperlink, just copy value (might be just text)
                    original_name = str(screenshot_value).strip()
                    if original_name in image_mapping:
                        new_name = image_mapping[original_name]
                        new_screenshot_value = new_name
                        new_screenshot_target = f"Images/{new_name}"
                    else:
                        new_screenshot_value = screenshot_value

                # ONLY write if value changed (preserve team's custom formatting!)
                if new_screenshot_value != existing_screenshot:
                    master_screenshot_cell.value = new_screenshot_value
                    if new_screenshot_target:
                        master_screenshot_cell.hyperlink = new_screenshot_target

                    # Apply styling: blue fill + blue border (matching COMMENT style)
                    master_screenshot_cell.fill = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
                    master_screenshot_cell.alignment = Alignment(horizontal='left', vertical='center')
                    master_screenshot_cell.border = Border(
                        left=Side(style='thin', color='87CEEB'),
                        right=Side(style='thin', color='87CEEB'),
                        top=Side(style='thin', color='87CEEB'),
                        bottom=Side(style='thin', color='87CEEB')
                    )

                    # Hyperlink font: blue for valid, orange for warning
                    if new_screenshot_target:
                        if is_warning:
                            master_screenshot_cell.font = Font(color="FF6600", underline="single")  # Orange = warning
                        else:
                            master_screenshot_cell.font = Font(color="0000FF", underline="single")  # Blue = valid

                    result["screenshots"] += 1

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


# =============================================================================
# TRACKER FUNCTIONS - LQA User Progress Tracker
# =============================================================================

def get_or_create_tracker():
    """
    Load existing tracker or create new one with 4 sheets.

    Returns: (workbook, path)
    """
    tracker_path = MASTER_FOLDER / TRACKER_FILENAME

    if tracker_path.exists():
        wb = openpyxl.load_workbook(tracker_path)
    else:
        wb = openpyxl.Workbook()
        # Remove default sheet
        default_sheet = wb.active
        # Create sheets in order
        wb.create_sheet("DAILY", 0)
        wb.create_sheet("TOTAL", 1)
        wb.create_sheet("GRAPHS", 2)
        wb.create_sheet("_DAILY_DATA", 3)
        # Remove default sheet
        wb.remove(default_sheet)
        # Hide data sheet
        wb["_DAILY_DATA"].sheet_state = 'hidden'

    return wb, tracker_path


def update_daily_data_sheet(wb, daily_entries):
    """
    Update hidden _DAILY_DATA sheet with new entries.

    Args:
        wb: Tracker workbook
        daily_entries: List of dicts with {date, user, category, done, issues, no_issue, blocked}

    Mode: REPLACE - same (date, user, category) overwrites existing row
    """
    ws = wb["_DAILY_DATA"]

    # Ensure headers exist
    if ws.cell(1, 1).value != "Date":
        headers = ["Date", "User", "Category", "Done", "Issues", "NoIssue", "Blocked"]
        for col, header in enumerate(headers, 1):
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

    # Update or insert entries
    for entry in daily_entries:
        key = (entry["date"], entry["user"], entry["category"])

        if key in existing:
            row = existing[key]
        else:
            row = ws.max_row + 1
            existing[key] = row

        ws.cell(row, 1, entry["date"])
        ws.cell(row, 2, entry["user"])
        ws.cell(row, 3, entry["category"])
        ws.cell(row, 4, entry["done"])
        ws.cell(row, 5, entry["issues"])
        ws.cell(row, 6, entry["no_issue"])
        ws.cell(row, 7, entry["blocked"])


def build_daily_sheet(wb):
    """
    Build DAILY sheet from _DAILY_DATA.

    Aggregates by (date, user) - combines all categories.
    """
    # Delete and recreate sheet to handle merged cells properly
    if "DAILY" in wb.sheetnames:
        del wb["DAILY"]
    ws = wb.create_sheet("DAILY", 0)

    data_ws = wb["_DAILY_DATA"]

    # Read raw data and aggregate by (date, user)
    daily_data = defaultdict(lambda: defaultdict(lambda: {"done": 0, "issues": 0}))
    users = set()

    for row in range(2, data_ws.max_row + 1):
        date = data_ws.cell(row, 1).value
        user = data_ws.cell(row, 2).value
        done = data_ws.cell(row, 4).value or 0
        issues = data_ws.cell(row, 5).value or 0

        if date and user:
            daily_data[date][user]["done"] += done
            daily_data[date][user]["issues"] += issues
            users.add(user)

    if not users:
        ws.cell(1, 1, "No data yet")
        return

    users = sorted(users)
    dates = sorted(daily_data.keys())

    # Styles
    title_fill = PatternFill(start_color=TRACKER_STYLES["title_color"], end_color=TRACKER_STYLES["title_color"], fill_type="solid")
    header_fill = PatternFill(start_color=TRACKER_STYLES["header_color"], end_color=TRACKER_STYLES["header_color"], fill_type="solid")
    subheader_fill = PatternFill(start_color=TRACKER_STYLES["subheader_color"], end_color=TRACKER_STYLES["subheader_color"], fill_type="solid")
    alt_fill = PatternFill(start_color=TRACKER_STYLES["alt_row_color"], end_color=TRACKER_STYLES["alt_row_color"], fill_type="solid")
    total_fill = PatternFill(start_color=TRACKER_STYLES["total_row_color"], end_color=TRACKER_STYLES["total_row_color"], fill_type="solid")
    border = Border(
        left=Side(style='thin', color=TRACKER_STYLES["border_color"]),
        right=Side(style='thin', color=TRACKER_STYLES["border_color"]),
        top=Side(style='thin', color=TRACKER_STYLES["border_color"]),
        bottom=Side(style='thin', color=TRACKER_STYLES["border_color"])
    )
    center = Alignment(horizontal='center', vertical='center')
    bold = Font(bold=True)

    # Row 1: Title
    title_cols = 1 + len(users) * 2  # Date + (Done, Issues) per user
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=title_cols)
    title_cell = ws.cell(1, 1, "DAILY PROGRESS")
    title_cell.fill = title_fill
    title_cell.font = Font(bold=True, size=14)
    title_cell.alignment = center

    # Row 2: Empty

    # Row 3: User names (merged across Done+Issues)
    ws.cell(3, 1, "")  # Date column header placeholder
    col = 2
    for user in users:
        ws.merge_cells(start_row=3, start_column=col, end_row=3, end_column=col + 1)
        cell = ws.cell(3, col, user)
        cell.fill = header_fill
        cell.font = bold
        cell.alignment = center
        ws.cell(3, col + 1).fill = header_fill  # Merged cell styling
        col += 2

    # Row 4: Sub-headers (Date, Done, Issues, Done, Issues, ...)
    ws.cell(4, 1, "Date").fill = subheader_fill
    ws.cell(4, 1).font = bold
    ws.cell(4, 1).alignment = center
    ws.cell(4, 1).border = border
    col = 2
    for user in users:
        done_cell = ws.cell(4, col, "Done")
        done_cell.fill = subheader_fill
        done_cell.font = bold
        done_cell.alignment = center
        done_cell.border = border

        issues_cell = ws.cell(4, col + 1, "Issues")
        issues_cell.fill = subheader_fill
        issues_cell.font = bold
        issues_cell.alignment = center
        issues_cell.border = border
        col += 2

    # Row 5+: Data rows
    user_totals = {user: {"done": 0, "issues": 0} for user in users}
    data_row = 5
    for idx, date in enumerate(dates):
        # Date column - format as MM/DD
        if isinstance(date, str) and len(date) >= 10:
            display_date = date[5:7] + "/" + date[8:10]  # YYYY-MM-DD -> MM/DD
        else:
            display_date = str(date)

        date_cell = ws.cell(data_row, 1, display_date)
        date_cell.alignment = center
        date_cell.border = border
        if idx % 2 == 1:
            date_cell.fill = alt_fill

        col = 2
        for user in users:
            user_data = daily_data[date].get(user, {"done": 0, "issues": 0})
            done_val = user_data["done"]
            issues_val = user_data["issues"]

            # Track totals
            user_totals[user]["done"] += done_val
            user_totals[user]["issues"] += issues_val

            # Display value or "--" for zero
            done_display = done_val if done_val > 0 else "--"
            issues_display = issues_val if issues_val > 0 else "--"

            done_cell = ws.cell(data_row, col, done_display)
            done_cell.alignment = center
            done_cell.border = border
            if idx % 2 == 1:
                done_cell.fill = alt_fill

            issues_cell = ws.cell(data_row, col + 1, issues_display)
            issues_cell.alignment = center
            issues_cell.border = border
            if idx % 2 == 1:
                issues_cell.fill = alt_fill

            col += 2

        data_row += 1

    # TOTAL row
    total_cell = ws.cell(data_row, 1, "TOTAL")
    total_cell.fill = total_fill
    total_cell.font = bold
    total_cell.alignment = center
    total_cell.border = border

    col = 2
    for user in users:
        done_cell = ws.cell(data_row, col, user_totals[user]["done"])
        done_cell.fill = total_fill
        done_cell.font = bold
        done_cell.alignment = center
        done_cell.border = border

        issues_cell = ws.cell(data_row, col + 1, user_totals[user]["issues"])
        issues_cell.fill = total_fill
        issues_cell.font = bold
        issues_cell.alignment = center
        issues_cell.border = border
        col += 2

    # Set column widths
    ws.column_dimensions['A'].width = 12
    for i in range(len(users) * 2):
        col_letter = get_column_letter(2 + i)
        ws.column_dimensions[col_letter].width = 10


def build_total_sheet(wb):
    """
    Build TOTAL sheet from _DAILY_DATA.

    Aggregates by user across all dates and categories.
    """
    # Delete and recreate sheet to handle merged cells properly
    if "TOTAL" in wb.sheetnames:
        del wb["TOTAL"]
    ws = wb.create_sheet("TOTAL", 1)

    data_ws = wb["_DAILY_DATA"]

    # Read raw data and aggregate by user
    user_data = defaultdict(lambda: {"done": 0, "issues": 0, "no_issue": 0, "blocked": 0})

    for row in range(2, data_ws.max_row + 1):
        user = data_ws.cell(row, 2).value
        done = data_ws.cell(row, 4).value or 0
        issues = data_ws.cell(row, 5).value or 0
        no_issue = data_ws.cell(row, 6).value or 0
        blocked = data_ws.cell(row, 7).value or 0

        if user:
            user_data[user]["done"] += done
            user_data[user]["issues"] += issues
            user_data[user]["no_issue"] += no_issue
            user_data[user]["blocked"] += blocked

    if not user_data:
        ws.cell(1, 1, "No data yet")
        return

    users = sorted(user_data.keys())

    # Styles
    title_fill = PatternFill(start_color=TRACKER_STYLES["title_color"], end_color=TRACKER_STYLES["title_color"], fill_type="solid")
    header_fill = PatternFill(start_color=TRACKER_STYLES["header_color"], end_color=TRACKER_STYLES["header_color"], fill_type="solid")
    alt_fill = PatternFill(start_color=TRACKER_STYLES["alt_row_color"], end_color=TRACKER_STYLES["alt_row_color"], fill_type="solid")
    total_fill = PatternFill(start_color=TRACKER_STYLES["total_row_color"], end_color=TRACKER_STYLES["total_row_color"], fill_type="solid")
    border = Border(
        left=Side(style='thin', color=TRACKER_STYLES["border_color"]),
        right=Side(style='thin', color=TRACKER_STYLES["border_color"]),
        top=Side(style='thin', color=TRACKER_STYLES["border_color"]),
        bottom=Side(style='thin', color=TRACKER_STYLES["border_color"])
    )
    center = Alignment(horizontal='center', vertical='center')
    bold = Font(bold=True)

    # Row 1: Title
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
    title_cell = ws.cell(1, 1, "TOTAL SUMMARY")
    title_cell.fill = title_fill
    title_cell.font = Font(bold=True, size=14)
    title_cell.alignment = center

    # Row 2: Empty

    # Row 3: Headers
    headers = ["User", "Completion %", "Total", "Issues", "No Issue", "Blocked"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(3, col, header)
        cell.fill = header_fill
        cell.font = bold
        cell.alignment = center
        cell.border = border

    # Row 4+: Data rows
    grand_total = {"done": 0, "issues": 0, "no_issue": 0, "blocked": 0}
    data_row = 4
    for idx, user in enumerate(users):
        data = user_data[user]
        total = data["done"]
        issues = data["issues"]
        no_issue = data["no_issue"]
        blocked = data["blocked"]
        completion_pct = round((issues + no_issue + blocked) / total * 100, 1) if total > 0 else 0

        # Accumulate grand totals
        grand_total["done"] += total
        grand_total["issues"] += issues
        grand_total["no_issue"] += no_issue
        grand_total["blocked"] += blocked

        row_data = [user, f"{completion_pct}%", total, issues, no_issue, blocked]

        for col, value in enumerate(row_data, 1):
            cell = ws.cell(data_row, col, value)
            cell.alignment = center
            cell.border = border
            if idx % 2 == 1:
                cell.fill = alt_fill

        data_row += 1

    # TOTAL row
    gt = grand_total
    gt_completion = round((gt["issues"] + gt["no_issue"] + gt["blocked"]) / gt["done"] * 100, 1) if gt["done"] > 0 else 0
    total_row_data = ["TOTAL", f"{gt_completion}%", gt["done"], gt["issues"], gt["no_issue"], gt["blocked"]]

    for col, value in enumerate(total_row_data, 1):
        cell = ws.cell(data_row, col, value)
        cell.fill = total_fill
        cell.font = bold
        cell.alignment = center
        cell.border = border

    # Set column widths
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 10
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 10


def build_graphs_sheet(wb):
    """
    Build GRAPHS sheet with charts.

    Uses openpyxl.chart module.
    """
    from openpyxl.chart import BarChart, Reference
    from openpyxl.chart.series import DataPoint
    from openpyxl.chart.label import DataLabelList

    # Delete and recreate sheet to handle charts properly
    if "GRAPHS" in wb.sheetnames:
        del wb["GRAPHS"]
    ws = wb.create_sheet("GRAPHS", 2)

    daily_ws = wb["DAILY"]
    total_ws = wb["TOTAL"]

    # Check if we have data
    if daily_ws.cell(1, 1).value == "No data yet" or total_ws.cell(1, 1).value == "No data yet":
        ws.cell(1, 1, "No data available for charts")
        return

    # --- Chart 1: Daily Progress (Done per user per day) ---
    # Find data range in DAILY sheet
    # Row 4 has headers (Date, Done, Issues, Done, Issues, ...)
    # Row 5+ has data

    # Count users and dates
    daily_max_row = daily_ws.max_row
    daily_max_col = daily_ws.max_column

    if daily_max_row < 5 or daily_max_col < 2:
        ws.cell(1, 1, "Not enough data for charts")
        return

    # Build a mini data table for charting in GRAPHS sheet
    # Copy DAILY data for chart reference
    ws.cell(1, 1, "Daily Progress Chart Data")
    ws.cell(1, 1).font = Font(bold=True)

    # Copy headers and data from DAILY sheet (simplified: just Date and Done values)
    # We'll create a simpler structure for the chart

    # Get users from row 3 of DAILY
    users = []
    col = 2
    while col <= daily_max_col:
        user = daily_ws.cell(3, col).value
        if user:
            users.append(user)
        col += 2  # Skip Issues column

    if not users:
        ws.cell(2, 1, "No users found")
        return

    # Build chart data table in GRAPHS sheet
    # Row 3: Headers (Date, User1, User2, ...)
    ws.cell(3, 1, "Date")
    for i, user in enumerate(users):
        ws.cell(3, 2 + i, user)

    # Row 4+: Data (date, done values per user)
    chart_row = 4
    for daily_row in range(5, daily_max_row):  # Exclude TOTAL row
        date = daily_ws.cell(daily_row, 1).value
        if date == "TOTAL":
            break

        ws.cell(chart_row, 1, date)
        for i, user in enumerate(users):
            done_col = 2 + i * 2  # Done columns are at 2, 4, 6, ...
            done_val = daily_ws.cell(daily_row, done_col).value
            if done_val == "--":
                done_val = 0
            ws.cell(chart_row, 2 + i, done_val)
        chart_row += 1

    num_dates = chart_row - 4

    if num_dates > 0:
        # Create bar chart for daily progress
        chart1 = BarChart()
        chart1.type = "col"
        chart1.grouping = "clustered"
        chart1.title = "Daily Progress by User"
        chart1.y_axis.title = "Rows Completed"
        chart1.x_axis.title = "Date"

        # Data reference (user columns)
        data = Reference(ws, min_col=2, min_row=3, max_col=1 + len(users), max_row=3 + num_dates)
        # Categories (dates)
        cats = Reference(ws, min_col=1, min_row=4, max_row=3 + num_dates)

        chart1.add_data(data, titles_from_data=True)
        chart1.set_categories(cats)
        chart1.shape = 4
        chart1.width = 18
        chart1.height = 10

        # Apply colors to series
        for i, series in enumerate(chart1.series):
            color = CHART_COLORS[i % len(CHART_COLORS)]
            series.graphicalProperties.solidFill = color

        ws.add_chart(chart1, "A" + str(chart_row + 2))

    # --- Chart 2: User Completion Rate ---
    # Build data table for completion chart
    comp_start_row = chart_row + 15

    ws.cell(comp_start_row, 1, "User Completion Chart Data")
    ws.cell(comp_start_row, 1).font = Font(bold=True)

    ws.cell(comp_start_row + 2, 1, "User")
    ws.cell(comp_start_row + 2, 2, "Completion %")

    # Copy from TOTAL sheet
    total_data_row = 4
    comp_row = comp_start_row + 3
    while True:
        user = total_ws.cell(total_data_row, 1).value
        if not user or user == "TOTAL":
            break
        completion = total_ws.cell(total_data_row, 2).value
        # Convert "95.0%" to 95.0
        if isinstance(completion, str) and completion.endswith("%"):
            completion = float(completion.rstrip("%"))

        ws.cell(comp_row, 1, user)
        ws.cell(comp_row, 2, completion)
        comp_row += 1
        total_data_row += 1

    num_users = comp_row - (comp_start_row + 3)

    if num_users > 0:
        chart2 = BarChart()
        chart2.type = "bar"  # Horizontal bar
        chart2.title = "User Completion Rate"
        chart2.y_axis.title = "User"
        chart2.x_axis.title = "Completion %"

        data2 = Reference(ws, min_col=2, min_row=comp_start_row + 2, max_row=comp_start_row + 2 + num_users)
        cats2 = Reference(ws, min_col=1, min_row=comp_start_row + 3, max_row=comp_start_row + 2 + num_users)

        chart2.add_data(data2, titles_from_data=True)
        chart2.set_categories(cats2)
        chart2.width = 14
        chart2.height = 8

        # Color the bars
        if chart2.series:
            chart2.series[0].graphicalProperties.solidFill = CHART_COLORS[0]

        ws.add_chart(chart2, "A" + str(comp_start_row + 4 + num_users + 2))


def process_category(category, qa_folders):
    """
    Process all QA folders for one category.

    Args:
        category: Category name (Quest, Knowledge, etc.)
        qa_folders: List of dicts with {folder_path, xlsx_path, username, category, images}

    Returns:
        List of daily_entry dicts for tracker
    """
    print(f"\n{'='*50}")
    print(f"Processing: {category} ({len(qa_folders)} folders)")
    print(f"{'='*50}")

    daily_entries = []  # NEW: Collect entries for tracker

    # Get or create master
    first_xlsx = qa_folders[0]["xlsx_path"]
    master_wb, master_path = get_or_create_master(category, first_xlsx)

    if master_wb is None:
        return daily_entries

    # Track users and aggregated stats
    all_users = set()
    user_stats = defaultdict(lambda: {"total": 0, "issue": 0, "no_issue": 0, "blocked": 0})
    total_images = 0
    total_screenshots = 0

    # Process each QA folder
    for qf in qa_folders:
        username = qf["username"]
        xlsx_path = qf["xlsx_path"]
        folder_path = qf["folder_path"]
        all_users.add(username)

        print(f"\n  Folder: {folder_path.name}")

        # Get file modification date for tracker
        file_mod_time = datetime.fromtimestamp(xlsx_path.stat().st_mtime)
        file_mod_date = file_mod_time.strftime("%Y-%m-%d")

        # Copy images with unique names
        image_mapping = copy_images_with_unique_names(qf)
        total_images += len(image_mapping)

        # Load xlsx
        qa_wb = openpyxl.load_workbook(xlsx_path)

        for sheet_name in qa_wb.sheetnames:
            # Skip STATUS sheets
            if sheet_name == "STATUS":
                continue

            # Check if sheet exists in master
            if sheet_name not in master_wb.sheetnames:
                print(f"    WARN: Sheet '{sheet_name}' not in master, skipping")
                continue

            # Process sheet with image mapping for hyperlink transformation + xlsx_path for mod time
            result = process_sheet(master_wb[sheet_name], qa_wb[sheet_name], username, category, image_mapping, xlsx_path)
            stats = result["stats"]

            fallback_info = f", fallback:{result['fallback_used']}" if result.get('fallback_used', 0) > 0 else ""
            screenshot_info = f", screenshots:{result['screenshots']}" if result.get('screenshots', 0) > 0 else ""
            print(f"    {sheet_name}: {result['comments']} comments, {stats['issue']} issues, {stats['no_issue']} OK, {stats['blocked']} blocked{fallback_info}{screenshot_info}")

            total_screenshots += result.get('screenshots', 0)

            # Aggregate stats for this user across all sheets
            user_stats[username]["total"] += stats["total"]
            user_stats[username]["issue"] += stats["issue"]
            user_stats[username]["no_issue"] += stats["no_issue"]
            user_stats[username]["blocked"] += stats["blocked"]

        qa_wb.close()

        # NEW: Collect entry for tracker (after processing all sheets for this user)
        daily_entries.append({
            "date": file_mod_date,
            "user": username,
            "category": category,
            "done": user_stats[username]["issue"] + user_stats[username]["no_issue"] + user_stats[username]["blocked"],
            "issues": user_stats[username]["issue"],
            "no_issue": user_stats[username]["no_issue"],
            "blocked": user_stats[username]["blocked"]
        })

    # Update STATUS sheet (first tab, with stats)
    update_status_sheet(master_wb, all_users, user_stats)

    # Save master
    master_wb.save(master_path)
    print(f"\n  Saved: {master_path}")
    if total_images > 0:
        print(f"  Images: {total_images} copied to Images/, {total_screenshots} hyperlinks updated")

    return daily_entries  # NEW: Return entries for tracker


def main():
    """Main entry point."""
    print("="*60)
    print("QA Excel Compiler (with Image Compilation)")
    print("="*60)
    print("Features:")
    print("  - Folder-based input: QAfolder/{Username}_{Category}/")
    print("  - Dynamic column detection (finds STATUS/COMMENT/SCREENSHOT by header)")
    print("  - Paired COMMENT_{User} + SCREENSHOT_{User} columns")
    print("  - REPLACE mode: New comments replace old (no append)")
    print("  - Timestamp: Uses file's last modified time")
    print("  - Image consolidation to Masterfolder/Images/")
    print("  - Hyperlink transformation with unique naming")
    print("  - Fallback row matching (2+ cell match if row counts differ)")
    print()

    # Ensure folders exist
    ensure_master_folder()

    # Discover QA folders
    qa_folders = discover_qa_folders()

    if not qa_folders:
        print("\nNo valid QA folders found in QAfolder/")
        print("Expected format: QAfolder/{Username}_{Category}/")
        print("  - Each folder should contain one .xlsx file")
        print("  - Images should be in the same folder")
        print(f"Valid categories: {', '.join(CATEGORIES)}")
        return

    print(f"Found {len(qa_folders)} QA folder(s)")

    # Count total images
    total_images = sum(len(qf["images"]) for qf in qa_folders)
    if total_images > 0:
        print(f"Total images to process: {total_images}")

    # Group by category
    by_category = defaultdict(list)
    for qf in qa_folders:
        by_category[qf["category"]].append(qf)

    # Process each category and collect daily entries for tracker
    all_daily_entries = []
    for category in CATEGORIES:
        if category in by_category:
            entries = process_category(category, by_category[category])
            all_daily_entries.extend(entries)
        else:
            print(f"\nSKIP: No folders for category '{category}'")

    # Update LQA User Progress Tracker
    if all_daily_entries:
        print("\n" + "="*60)
        print("Updating LQA User Progress Tracker...")
        print("="*60)

        tracker_wb, tracker_path = get_or_create_tracker()
        update_daily_data_sheet(tracker_wb, all_daily_entries)
        build_daily_sheet(tracker_wb)
        build_total_sheet(tracker_wb)
        build_graphs_sheet(tracker_wb)
        tracker_wb.save(tracker_path)

        print(f"  Saved: {tracker_path}")
        print(f"  Sheets: DAILY, TOTAL, GRAPHS")

    print("\n" + "="*60)
    print("Compilation complete!")
    print(f"Output: {MASTER_FOLDER}")
    if total_images > 0:
        print(f"Images: {IMAGES_FOLDER}")
    if all_daily_entries:
        print(f"Tracker: {TRACKER_FILENAME}")
    print("="*60)


if __name__ == "__main__":
    main()
