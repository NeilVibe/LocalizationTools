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
import sys
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation


# === CONFIGURATION ===
# Handle PyInstaller frozen state - exe unpacks to temp dir, need exe's actual location
if getattr(sys, 'frozen', False):
    # Running as compiled executable (.exe)
    SCRIPT_DIR = Path(sys.executable).parent
else:
    # Running as normal Python script
    SCRIPT_DIR = Path(__file__).parent
QA_FOLDER = SCRIPT_DIR / "QAfolder"

# Language-separated Master folders
MASTER_FOLDER_EN = SCRIPT_DIR / "Masterfolder_EN"
MASTER_FOLDER_CN = SCRIPT_DIR / "Masterfolder_CN"
IMAGES_FOLDER_EN = MASTER_FOLDER_EN / "Images"
IMAGES_FOLDER_CN = MASTER_FOLDER_CN / "Images"

# Tester→Language mapping file
TESTER_MAPPING_FILE = SCRIPT_DIR / "languageTOtester_list.txt"

# Progress Tracker at root level (combines all)
TRACKER_PATH = SCRIPT_DIR / "LQA_Tester_ProgressTracker.xlsx"

CATEGORIES = ["Quest", "Knowledge", "Item", "Region", "System", "Character"]

# Supported image extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

# Valid STATUS values (only these count as "filled")
VALID_STATUS = ["ISSUE", "NO ISSUE", "BLOCKED"]

# Valid MANAGER STATUS values (for manager workflow)
VALID_MANAGER_STATUS = ["FIXED", "REPORTED", "CHECKING", "NON-ISSUE"]

# === TRACKER CONFIGURATION ===
TRACKER_FILENAME = "LQA_Tester_ProgressTracker.xlsx"

TRACKER_STYLES = {
    "title_color": "FFD700",       # Gold
    "header_color": "87CEEB",      # Light blue
    "subheader_color": "D3D3D3",   # Light gray
    "alt_row_color": "F5F5F5",     # Alternating gray
    "total_row_color": "E6E6E6",   # Total row gray
    "border_color": "000000",      # Black
}

CHART_COLORS = ["4472C4", "ED7D31", "70AD47", "FFC000", "5B9BD5", "A5A5A5"]

# Characters that trigger Excel formula interpretation
EXCEL_FORMULA_CHARS = ('=', '+', '@')


def sanitize_for_excel(value):
    """
    Prevent Excel formula injection from user content.

    Excel interprets cells starting with =, +, @ as formulas.
    Prepending a single quote (') tells Excel to treat it as text.
    The quote is invisible in the cell but prevents formula parsing.

    Args:
        value: Cell value to sanitize

    Returns:
        Sanitized value safe for Excel
    """
    if not value:
        return value
    text = str(value)
    if text and text[0] in EXCEL_FORMULA_CHARS:
        return "'" + text  # Excel's native escape - invisible in cell
    return text


def load_tester_mapping():
    """
    Load tester→language mapping from languageTOtester_list.txt.

    File format:
        ENG
        김동헌
        황하연
        ...

        ZHO-CN
        김춘애
        최문석
        ...

    Returns: Dict {tester_name: "EN" or "CN"}
    """
    mapping = {}
    current_lang = None

    if not TESTER_MAPPING_FILE.exists():
        print(f"WARNING: Mapping file not found: {TESTER_MAPPING_FILE}")
        return mapping

    with open(TESTER_MAPPING_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line == "ENG":
                current_lang = "EN"
            elif line == "ZHO-CN":
                current_lang = "CN"
            elif current_lang:
                mapping[line] = current_lang

    print(f"  Loaded {len(mapping)} tester→language mappings")
    return mapping


def get_master_folder(username, tester_mapping):
    """Get the correct master folder based on tester's language."""
    lang = tester_mapping.get(username, "EN")  # Default to EN if not found
    if lang == "CN":
        return MASTER_FOLDER_CN, IMAGES_FOLDER_CN
    return MASTER_FOLDER_EN, IMAGES_FOLDER_EN


def ensure_master_folders():
    """Create both EN and CN master folders if they don't exist."""
    MASTER_FOLDER_EN.mkdir(exist_ok=True)
    MASTER_FOLDER_CN.mkdir(exist_ok=True)
    IMAGES_FOLDER_EN.mkdir(exist_ok=True)
    IMAGES_FOLDER_CN.mkdir(exist_ok=True)


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


def copy_images_with_unique_names(qa_folder_info, images_folder):
    """
    Copy images from QA folder to Images/ with original names.

    Args:
        qa_folder_info: Dict with {folder_path, username, category, images}
        images_folder: Target Images folder (EN or CN)

    Returns: Dict mapping original_name -> original_name
    """
    images = qa_folder_info["images"]

    image_mapping = {}

    for img_path in images:
        original_name = img_path.name
        # Keep original name - hyperlink depends on it
        dest_path = images_folder / original_name

        # Copy image (overwrite if exists - same image from different users)
        shutil.copy2(img_path, dest_path)

        image_mapping[original_name] = original_name  # Same name

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


def get_or_create_master(category, master_folder, template_file=None):
    """
    Load existing master file or create from template.

    CLEAN START: When creating new master, DELETE STATUS/COMMENT/SCREENSHOT
    columns entirely (not just clear values). Master starts clean with only
    data columns, then COMMENT_{User} columns are added at MAX_COLUMN + 1.

    Args:
        category: Category name (Quest, Knowledge, etc.)
        master_folder: Target Master folder (EN or CN)
        template_file: Path to first QA file to use as template

    Returns: openpyxl Workbook, master_path
    """
    master_path = master_folder / f"Master_{category}.xlsx"

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


def get_or_create_user_status_column(ws, username, after_comment_col):
    """
    Find or create STATUS_{username} column immediately after COMMENT_{username}.

    This is for MANAGER workflow - managers mark FIXED/REPORTED/CHECKING.
    Adds a dropdown list (data validation) so managers can only select valid values.

    Args:
        ws: Worksheet
        username: User identifier
        after_comment_col: Column index of COMMENT_{username} (status goes right after)

    Returns: Column index (1-based)
    """
    col_name = f"STATUS_{username}"

    # Check if column already exists
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header and str(header).strip() == col_name:
            # Ensure dropdown validation is up-to-date (might be old formula without NON-ISSUE)
            col_letter = get_column_letter(col)
            # Remove any existing validation for this column
            to_remove = []
            for existing_dv in ws.data_validations.dataValidation:
                if col_letter in str(existing_dv.sqref):
                    to_remove.append(existing_dv)
            for dv in to_remove:
                ws.data_validations.dataValidation.remove(dv)
            # Add fresh validation with current options (includes NON-ISSUE)
            dv = DataValidation(
                type="list",
                formula1='"FIXED,REPORTED,CHECKING,NON-ISSUE"',
                allow_blank=True,
                showDropDown=False,
                showErrorMessage=True,
                errorTitle="Invalid Status",
                error="Please select: FIXED, REPORTED, CHECKING, or NON-ISSUE"
            )
            # Use actual row count + buffer instead of hardcoded 1000
            last_row = max(ws.max_row, 10) + 50  # Buffer for future rows
            dv.add(f"{col_letter}2:{col_letter}{last_row}")
            ws.add_data_validation(dv)
            return col

    # Add new column at max_column + 1
    new_col = ws.max_column + 1

    cell = ws.cell(row=1, column=new_col)
    cell.value = col_name

    # Light green background for manager STATUS columns (distinct from tester columns)
    cell.fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
    # Bold font
    cell.font = Font(bold=True, color="000000")
    # Center alignment
    cell.alignment = Alignment(horizontal='center', vertical='center')
    # Nice border (green tint)
    cell.border = Border(
        left=Side(style='medium', color='228B22'),
        right=Side(style='medium', color='228B22'),
        top=Side(style='medium', color='228B22'),
        bottom=Side(style='medium', color='228B22')
    )

    # Set column width
    col_letter = get_column_letter(new_col)
    ws.column_dimensions[col_letter].width = 15
    ws.column_dimensions[col_letter].hidden = False

    # Add dropdown data validation for FIXED/REPORTED/CHECKING/NON-ISSUE
    # Use actual row count + buffer instead of hardcoded 1000 (prevents Excel repair warnings)
    last_row = max(ws.max_row, 10) + 50  # Buffer for future rows
    dv = DataValidation(
        type="list",
        formula1='"FIXED,REPORTED,CHECKING,NON-ISSUE"',
        allow_blank=True,
        showDropDown=False,  # False = show dropdown arrow, True = hide it (confusing API)
        showErrorMessage=True,
        errorTitle="Invalid Status",
        error="Please select: FIXED, REPORTED, CHECKING, or NON-ISSUE",
        promptTitle="Manager Status",
        prompt="Select status: FIXED, REPORTED, CHECKING, or NON-ISSUE"
    )
    dv.add(f"{col_letter}2:{col_letter}{last_row}")
    ws.add_data_validation(dv)

    print(f"    Created column: {col_name} at {get_column_letter(new_col)} (manager status - dropdown)")
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


def sort_worksheet_az(ws, sort_column=1):
    """
    Sort worksheet rows A-Z by specified column.

    Used for EN Item category to match tester's A-Z sorted files.
    Preserves header row (row 1), sorts data rows (row 2+).

    Args:
        ws: Worksheet to sort
        sort_column: Column index to sort by (1-based, default=1 for column A)
    """
    from copy import copy

    # Get all data rows (skip header)
    data_rows = []
    for row in range(2, ws.max_row + 1):
        row_data = []
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row=row, column=col)
            row_data.append({
                'value': cell.value,
                'font': copy(cell.font) if cell.font else None,
                'fill': copy(cell.fill) if cell.fill else None,
                'border': copy(cell.border) if cell.border else None,
                'alignment': copy(cell.alignment) if cell.alignment else None,
                'hyperlink': cell.hyperlink.target if cell.hyperlink else None
            })
        # Store sort key (first column value) and row data
        sort_key = ws.cell(row=row, column=sort_column).value
        sort_key = str(sort_key).lower() if sort_key else ""
        data_rows.append((sort_key, row_data))

    # Sort by first column (A-Z)
    data_rows.sort(key=lambda x: x[0])

    # Write back sorted data
    for new_row_idx, (sort_key, row_data) in enumerate(data_rows, start=2):
        for col_idx, cell_data in enumerate(row_data, start=1):
            cell = ws.cell(row=new_row_idx, column=col_idx)
            cell.value = cell_data['value']
            if cell_data['font']:
                cell.font = cell_data['font']
            if cell_data['fill']:
                cell.fill = cell_data['fill']
            if cell_data['border']:
                cell.border = cell_data['border']
            if cell_data['alignment']:
                cell.alignment = cell_data['alignment']
            if cell_data['hyperlink']:
                cell.hyperlink = cell_data['hyperlink']


def find_matching_row_item_fallback(master_ws, qa_ws, qa_row, start_row=2):
    """
    Item category fallback: Match by 4+ of first 6 columns.

    Used when STRINGID is not available for Item category.
    Compares first 6 columns between QA row and master rows.
    If 4 or more values match, it's considered a match.

    Args:
        master_ws: Master worksheet
        qa_ws: QA worksheet
        qa_row: Row number in QA worksheet
        start_row: Start searching from this row in master

    Returns: Row number or None
    """
    # Get first 6 column values from QA row
    qa_values = []
    for col in range(1, 7):  # Columns 1-6
        val = qa_ws.cell(row=qa_row, column=col).value
        if val is not None:
            qa_values.append((col, str(val).strip()))
        else:
            qa_values.append((col, None))

    # Search master for matching row
    for master_row in range(start_row, master_ws.max_row + 1):
        matches = 0
        for col, qa_val in qa_values:
            master_val = master_ws.cell(row=master_row, column=col).value
            if master_val is not None:
                master_val = str(master_val).strip()
            else:
                master_val = None

            # Both None or both equal = match
            if qa_val == master_val:
                matches += 1
            elif qa_val and master_val and qa_val == master_val:
                matches += 1

        # 4+ matches out of 6 = found
        if matches >= 4:
            return master_row

    return None


def process_sheet(master_ws, qa_ws, username, category, image_mapping=None, xlsx_path=None, manager_status=None):
    """
    Process a single sheet: copy COMMENT and SCREENSHOT from QA to master, collect STATUS stats.

    ROBUST VERSION:
    - Finds COMMENT/STATUS/STRINGID/SCREENSHOT columns dynamically by header name
    - Uses MAX_COLUMN + 1 for user comment and screenshot columns
    - Creates columns in order: COMMENT_{User} → STATUS_{User} → SCREENSHOT_{User}
    - Falls back to 2+ cell matching if row counts differ
    - Applies beautiful styling to comment cells (blue fill + bold)
    - Transfers screenshots with hyperlink path transformation
    - Uses file modification time for comment timestamps
    - Preserves manager STATUS values (FIXED/REPORTED/CHECKING) from preprocess

    Args:
        master_ws: Master worksheet
        qa_ws: QA worksheet
        username: User identifier
        category: Category name
        image_mapping: Dict mapping original_name -> new_name (for hyperlink transformation)
        xlsx_path: Path to QA xlsx file (for file modification time)
        manager_status: Dict of {row: {user: status}} for this sheet (from preprocess)

    Returns: Dict with {comments: n, screenshots: n, stats: {...}, fallback_used: n}
    """
    if image_mapping is None:
        image_mapping = {}
    if manager_status is None:
        manager_status = {}

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

    # Find or create user columns in master in correct order:
    # COMMENT_{username} → STATUS_{username} → SCREENSHOT_{username}
    master_comment_col = get_or_create_user_comment_column(master_ws, username)
    master_user_status_col = get_or_create_user_status_column(master_ws, username, master_comment_col)
    master_screenshot_col = get_or_create_user_screenshot_column(master_ws, username, master_user_status_col)

    # Build exclude set for master row matching
    master_orig_status_col = find_column_by_header(master_ws, "STATUS")
    master_orig_comment_col = find_column_by_header(master_ws, "COMMENT")
    master_orig_screenshot_col = find_column_by_header(master_ws, "SCREENSHOT")

    master_exclude_cols = set()
    if master_orig_status_col:
        master_exclude_cols.add(master_orig_status_col)
    if master_orig_comment_col:
        master_exclude_cols.add(master_orig_comment_col)
    if master_orig_screenshot_col:
        master_exclude_cols.add(master_orig_screenshot_col)
    # Also exclude all COMMENT_*, STATUS_*, and SCREENSHOT_* columns
    for col in range(1, master_ws.max_column + 1):
        header = master_ws.cell(row=1, column=col).value
        if header and (str(header).startswith("COMMENT_") or str(header).startswith("STATUS_") or str(header).startswith("SCREENSHOT_")):
            master_exclude_cols.add(col)

    result = {
        "comments": 0,
        "screenshots": 0,
        "stats": {"issue": 0, "no_issue": 0, "blocked": 0, "total": 0},
        "fallback_used": 0,
        "stringid_matched": 0,
        "item_fallback_used": 0
    }

    # Determine if we need fallback matching
    use_fallback = (master_ws.max_row != qa_ws.max_row)
    if use_fallback:
        print(f"      Row count differs (master:{master_ws.max_row}, qa:{qa_ws.max_row}), using fallback matching")

    for qa_row in range(2, qa_ws.max_row + 1):  # Skip header
        result["stats"]["total"] += 1

        # Determine master row - simple index matching for all categories
        master_row = None

        if use_fallback:
            qa_sig = get_row_signature(qa_ws, qa_row, qa_exclude_cols)
            master_row = find_matching_row_fallback(master_ws, qa_sig, master_exclude_cols)
            if master_row is None:
                # No match found, skip this row
                continue
            result["fallback_used"] += 1
        else:
            master_row = qa_row  # Direct index matching

        # Refresh base data columns from QA to master
        # Copy ALL columns EXCEPT: STATUS, COMMENT, SCREENSHOT, and user-specific columns
        for col in range(1, qa_ws.max_column + 1):
            # Skip columns we handle specially
            if col in qa_exclude_cols:
                continue
            # Skip user-specific columns (COMMENT_{User}, SCREENSHOT_{User}, STATUS_{User})
            header = qa_ws.cell(row=1, column=col).value
            if header:
                header_str = str(header)
                if header_str.startswith("COMMENT_") or header_str.startswith("SCREENSHOT_") or header_str.startswith("STATUS_"):
                    continue
            # Copy value from QA to master (refresh base data)
            qa_value = qa_ws.cell(row=qa_row, column=col).value
            master_ws.cell(row=master_row, column=col).value = qa_value

        # Get QA STATUS (for stats AND to filter which comments to compile)
        is_issue = False
        if qa_status_col:
            qa_status = qa_ws.cell(row=qa_row, column=qa_status_col).value
            if qa_status:
                status_upper = str(qa_status).strip().upper()
                if status_upper == "ISSUE":
                    result["stats"]["issue"] += 1
                    is_issue = True
                elif status_upper == "NO ISSUE":
                    result["stats"]["no_issue"] += 1
                elif status_upper == "BLOCKED":
                    result["stats"]["blocked"] += 1

        # Get QA COMMENT and STRINGID, copy to master with styling
        # ONLY compile comments where STATUS = ISSUE (for Actual Issues % calculation)
        if qa_comment_col and is_issue:
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
                    cell.value = sanitize_for_excel(new_value)  # Prevent Excel formula injection

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

                    # Transform to new path - ALWAYS use Images/ prefix
                    if original_name in image_mapping:
                        new_name = image_mapping[original_name]
                        new_screenshot_value = new_name
                        new_screenshot_target = f"Images/{new_name}"
                    else:
                        # Image not found in mapping - still use Images/ prefix
                        # This handles case where image wasn't in QA folder
                        new_screenshot_value = original_name
                        new_screenshot_target = f"Images/{original_name}"
                        is_warning = True
                else:
                    # No hyperlink, just copy value (might be just text)
                    original_name = str(screenshot_value).strip()
                    if original_name in image_mapping:
                        new_name = image_mapping[original_name]
                        new_screenshot_value = new_name
                        new_screenshot_target = f"Images/{new_name}"
                    else:
                        # No mapping - still use Images/ prefix
                        new_screenshot_value = original_name
                        new_screenshot_target = f"Images/{original_name}"
                        is_warning = True

                # Check if hyperlink needs updating (value OR hyperlink different)
                existing_hyperlink = master_screenshot_cell.hyperlink.target if master_screenshot_cell.hyperlink else None
                needs_update = (new_screenshot_value != existing_screenshot) or (new_screenshot_target != existing_hyperlink)

                if needs_update:
                    master_screenshot_cell.value = sanitize_for_excel(new_screenshot_value)  # Prevent Excel formula injection
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

        # Restore manager STATUS_{username} value from preprocess
        if manager_status and master_row in manager_status:
            row_statuses = manager_status[master_row]
            if username in row_statuses:
                status_value = row_statuses[username]
                status_cell = master_ws.cell(row=master_row, column=master_user_status_col)
                # Only restore if currently empty (preserve manual edits)
                if not status_cell.value:
                    status_cell.value = status_value
                    # Style based on status value
                    status_cell.alignment = Alignment(horizontal='center', vertical='center')
                    if status_value == "FIXED":
                        status_cell.font = Font(bold=True, color="228B22")  # Forest green
                    elif status_value == "REPORTED":
                        status_cell.font = Font(bold=True, color="FF8C00")  # Dark orange
                    elif status_value == "CHECKING":
                        status_cell.font = Font(bold=True, color="0000FF")  # Blue

    return result


def hide_empty_comment_rows(wb, context_rows=1, debug=False):
    """
    Post-process: Hide rows/sheets/columns where ALL COMMENT_{User} columns are empty.

    This allows focusing on issues right away while preserving all data.
    Rows are hidden (not deleted) so they can be unhidden in Excel if needed.

    Features:
    - Sheet hiding: Sheets with NO comments at all are hidden entirely
    - Column hiding: COMMENT_{User} columns with no data in a sheet are hidden
      (also hides paired SCREENSHOT_{User} and STATUS_{User} columns)
    - Row hiding: Rows with no comments are hidden (with context rows kept visible)

    Args:
        wb: Master workbook
        context_rows: Number of rows above/below visible rows to keep visible (default: 1)
        debug: If True, print debug info about what's being detected

    Returns: Tuple of (rows_hidden, sheets_hidden)
    """
    hidden_rows = 0
    hidden_sheets = []
    hidden_columns_total = 0

    # === PHASE 0: RESET all sheets to visible first (fixes re-run UNHIDE bug) ===
    # Previously hidden sheets that now have content must be shown
    for sheet_name in wb.sheetnames:
        if sheet_name == "STATUS":
            continue
        wb[sheet_name].sheet_state = 'visible'
        if debug:
            print(f"    [DEBUG] Reset sheet '{sheet_name}' to visible")

    for sheet_name in wb.sheetnames:
        if sheet_name == "STATUS":
            continue

        ws = wb[sheet_name]

        # CRITICAL: Clear any AutoFilter from QA files before applying our logic
        # Testers may have filters/sorting applied - we want clean output
        if ws.auto_filter.ref:
            ws.auto_filter.ref = None
            if debug:
                print(f"    [DEBUG] Cleared AutoFilter from sheet: {sheet_name}")

        # Find all COMMENT_{User} columns
        comment_cols = []
        for col in range(1, ws.max_column + 1):
            header = ws.cell(row=1, column=col).value
            if header and str(header).startswith("COMMENT_"):
                comment_cols.append(col)
                if debug:
                    print(f"    [DEBUG] Found comment column: {header} at col {col}")

        if not comment_cols:
            if debug:
                print(f"    [DEBUG] No COMMENT_ columns found in {sheet_name}")
            continue

        # === RESET all COMMENT_*, SCREENSHOT_*, STATUS_* columns to visible first ===
        # Fixes re-run UNHIDE bug: previously hidden columns that now have content must be shown
        for col in comment_cols:
            header = ws.cell(row=1, column=col).value
            username = str(header).replace("COMMENT_", "") if header else ""
            col_letter = get_column_letter(col)
            ws.column_dimensions[col_letter].hidden = False

            # Also unhide paired SCREENSHOT_{User} and STATUS_{User} columns
            for search_col in range(1, ws.max_column + 1):
                search_header = ws.cell(row=1, column=search_col).value
                if search_header:
                    if str(search_header) == f"SCREENSHOT_{username}" or str(search_header) == f"STATUS_{username}":
                        search_col_letter = get_column_letter(search_col)
                        ws.column_dimensions[search_col_letter].hidden = False
            if debug:
                print(f"    [DEBUG] Reset column group for user '{username}' to visible")

        # First pass: Find rows that have comments AND track which columns have comments
        rows_with_comments = set()
        cols_with_comments = set()  # Track which COMMENT_ columns have data

        for row in range(2, ws.max_row + 1):
            for col in comment_cols:
                value = ws.cell(row=row, column=col).value
                # Check for any content (not just whitespace)
                if value is not None and str(value).strip():
                    rows_with_comments.add(row)
                    cols_with_comments.add(col)
                    if debug and row <= 10:  # Only debug first 10 rows
                        print(f"    [DEBUG] Row {row} has comment in col {col}: {repr(str(value)[:30])}")

        # If NO comments in entire sheet, hide the sheet tab
        if not rows_with_comments:
            if debug:
                print(f"    [DEBUG] Sheet '{sheet_name}' has {len(comment_cols)} COMMENT_ columns but ALL are empty - HIDING SHEET")
            ws.sheet_state = 'hidden'
            hidden_sheets.append(sheet_name)
            continue
        else:
            if debug:
                print(f"    [DEBUG] Sheet '{sheet_name}' has {len(rows_with_comments)} rows with comments - keeping visible")

        # Column hiding: Hide COMMENT_{User} columns that are entirely empty in this sheet
        # Also hide paired SCREENSHOT_{User} and STATUS_{User} columns
        hidden_cols_this_sheet = 0
        for col in comment_cols:
            if col not in cols_with_comments:
                # This COMMENT_ column is empty in this sheet - hide it
                header = ws.cell(row=1, column=col).value
                username = str(header).replace("COMMENT_", "") if header else ""

                # Hide the COMMENT_{User} column
                col_letter = ws.cell(row=1, column=col).column_letter
                ws.column_dimensions[col_letter].hidden = True
                hidden_cols_this_sheet += 1

                # Find and hide paired SCREENSHOT_{User} and STATUS_{User} columns
                for search_col in range(1, ws.max_column + 1):
                    search_header = ws.cell(row=1, column=search_col).value
                    if search_header:
                        if str(search_header) == f"SCREENSHOT_{username}":
                            search_col_letter = ws.cell(row=1, column=search_col).column_letter
                            ws.column_dimensions[search_col_letter].hidden = True
                            hidden_cols_this_sheet += 1
                        elif str(search_header) == f"STATUS_{username}":
                            search_col_letter = ws.cell(row=1, column=search_col).column_letter
                            ws.column_dimensions[search_col_letter].hidden = True
                            hidden_cols_this_sheet += 1

                if debug:
                    print(f"    [DEBUG] Hidden empty column group for user: {username}")

        hidden_columns_total += hidden_cols_this_sheet

        # Second pass: Build set of rows to keep visible (comments + context)
        rows_to_show = set(rows_with_comments)
        for row in rows_with_comments:
            # Add context rows above
            for offset in range(1, context_rows + 1):
                if row - offset >= 2:  # Don't include header
                    rows_to_show.add(row - offset)
            # Add context rows below
            for offset in range(1, context_rows + 1):
                if row + offset <= ws.max_row:
                    rows_to_show.add(row + offset)

        # Third pass: First UNHIDE all rows (clear any tester hiding), then hide our target rows
        for row in range(2, ws.max_row + 1):
            # Reset: unhide all rows first
            ws.row_dimensions[row].hidden = False

        # Fourth pass: Hide rows not in the show set
        for row in range(2, ws.max_row + 1):
            if row not in rows_to_show:
                ws.row_dimensions[row].hidden = True
                hidden_rows += 1

    return hidden_rows, hidden_sheets, hidden_columns_total


def autofit_rows_with_wordwrap(wb, default_row_height=15, chars_per_line=50):
    """
    Apply word wrap to all cells and autofit row heights based on content.

    Args:
        wb: Workbook
        default_row_height: Default height for single-line rows
        chars_per_line: Estimated characters per line (for height calculation)
    """
    for sheet_name in wb.sheetnames:
        if sheet_name == "STATUS":
            continue

        ws = wb[sheet_name]

        for row in range(1, ws.max_row + 1):
            max_lines = 1  # Track max lines needed for this row

            for col in range(1, ws.max_column + 1):
                cell = ws.cell(row=row, column=col)

                # Apply word wrap to all cells
                cell.alignment = Alignment(wrap_text=True, vertical='top')

                # Calculate lines needed based on content
                if cell.value:
                    content = str(cell.value)
                    # Count explicit line breaks
                    explicit_lines = content.count('\n') + 1
                    # Estimate wrapped lines based on length
                    longest_line = max(len(line) for line in content.split('\n')) if content else 0
                    wrapped_lines = max(1, (longest_line // chars_per_line) + 1)
                    # Total lines needed
                    total_lines = explicit_lines + wrapped_lines - 1
                    max_lines = max(max_lines, total_lines)

            # Set row height based on content (15 points per line is standard)
            calculated_height = max_lines * default_row_height
            # Cap at reasonable max (300 points)
            ws.row_dimensions[row].height = min(calculated_height, 300)


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
# MANAGER STATUS PREPROCESS FUNCTIONS
# =============================================================================

def collect_manager_status(master_folder):
    """
    Read existing Master files and collect all STATUS_{User} values.

    This is the PREPROCESS step - runs before compilation to preserve
    manager-entered status values (FIXED/REPORTED/CHECKING).

    Args:
        master_folder: Which Master folder to scan (EN or CN)

    Returns: Dict structure
    {
        "Quest": {
            "Sheet1": {
                row_number: {
                    "John": "FIXED",
                    "Alice": "REPORTED"
                }
            }
        }
    }
    """
    manager_status = {}

    for category in CATEGORIES:
        master_path = master_folder / f"Master_{category}.xlsx"
        if not master_path.exists():
            continue

        try:
            wb = openpyxl.load_workbook(master_path)
            manager_status[category] = {}

            for sheet_name in wb.sheetnames:
                if sheet_name == "STATUS":
                    continue

                ws = wb[sheet_name]
                manager_status[category][sheet_name] = {}

                # Find all STATUS_{User} columns
                status_cols = {}
                for col in range(1, ws.max_column + 1):
                    header = ws.cell(row=1, column=col).value
                    if header and str(header).startswith("STATUS_"):
                        username = str(header).replace("STATUS_", "")
                        status_cols[username] = col

                if not status_cols:
                    continue

                # Collect values per row
                for row in range(2, ws.max_row + 1):
                    row_status = {}
                    for username, col in status_cols.items():
                        value = ws.cell(row=row, column=col).value
                        if value and str(value).strip().upper() in VALID_MANAGER_STATUS:
                            row_status[username] = str(value).strip().upper()

                    if row_status:
                        manager_status[category][sheet_name][row] = row_status

            wb.close()

        except Exception as e:
            print(f"  WARN: Error reading {master_path.name} for preprocess: {e}")

    return manager_status


def collect_manager_stats_for_tracker():
    """
    Read all Master files (EN + CN) and count FIXED/REPORTED/CHECKING/NON-ISSUE per user per category.

    Returns: Dict structure
    {
        "Quest": {
            "John": {"fixed": 5, "reported": 2, "checking": 1, "nonissue": 0, "lang": "EN"},
            "Alice": {"fixed": 3, "reported": 1, "checking": 0, "nonissue": 2, "lang": "CN"}
        }
    }
    """
    manager_stats = defaultdict(lambda: defaultdict(lambda: {"fixed": 0, "reported": 0, "checking": 0, "nonissue": 0, "lang": "EN"}))

    # Load tester mapping to get language
    tester_mapping = load_tester_mapping()

    # Scan both EN and CN folders
    for master_folder in [MASTER_FOLDER_EN, MASTER_FOLDER_CN]:
        for category in CATEGORIES:
            master_path = master_folder / f"Master_{category}.xlsx"
            if not master_path.exists():
                continue

            try:
                wb = openpyxl.load_workbook(master_path)

                for sheet_name in wb.sheetnames:
                    if sheet_name == "STATUS":
                        continue

                    ws = wb[sheet_name]

                    # Find all STATUS_{User} columns
                    status_cols = {}
                    for col in range(1, ws.max_column + 1):
                        header = ws.cell(row=1, column=col).value
                        if header and str(header).startswith("STATUS_"):
                            username = str(header).replace("STATUS_", "")
                            status_cols[username] = col

                    if not status_cols:
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
                                elif status_upper == "NON-ISSUE":
                                    manager_stats[category][username]["nonissue"] += 1
                            # Set language from mapping
                            manager_stats[category][username]["lang"] = tester_mapping.get(username, "EN")

                wb.close()

            except Exception as e:
                print(f"  WARN: Error reading {master_path.name} for manager stats: {e}")

    return manager_stats


# =============================================================================
# TRACKER FUNCTIONS - LQA User Progress Tracker
# =============================================================================

def get_or_create_tracker():
    """
    Load existing tracker or create new one with sheets.

    Returns: (workbook, path)
    """
    tracker_path = TRACKER_PATH  # Root level

    if tracker_path.exists():
        wb = openpyxl.load_workbook(tracker_path)
    else:
        wb = openpyxl.Workbook()
        # Remove default sheet
        default_sheet = wb.active
        # Create sheets in order (no GRAPHS - charts embedded in DAILY/TOTAL)
        wb.create_sheet("DAILY", 0)
        wb.create_sheet("TOTAL", 1)
        wb.create_sheet("_DAILY_DATA", 2)
        # Remove default sheet
        wb.remove(default_sheet)
        # Hide data sheet
        wb["_DAILY_DATA"].sheet_state = 'hidden'

    return wb, tracker_path


def update_daily_data_sheet(wb, daily_entries, manager_stats=None):
    """
    Update hidden _DAILY_DATA sheet with new entries including manager stats.

    Args:
        wb: Tracker workbook
        daily_entries: List of dicts with {date, user, category, total_rows, done, issues, no_issue, blocked}
        manager_stats: Dict of {category: {user: {fixed, reported, checking}}} from manager status

    Mode: REPLACE - same (date, user, category) overwrites existing row
    """
    if manager_stats is None:
        manager_stats = {}

    ws = wb["_DAILY_DATA"]

    # Ensure headers exist (now includes TotalRows, Fixed, Reported, Checking, NonIssue)
    # Schema: Date, User, Category, TotalRows, Done, Issues, NoIssue, Blocked, Fixed, Reported, Checking, NonIssue
    if ws.cell(1, 1).value != "Date" or ws.max_column < 12:
        headers = ["Date", "User", "Category", "TotalRows", "Done", "Issues", "NoIssue", "Blocked", "Fixed", "Reported", "Checking", "NonIssue"]
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

        # Get manager stats for this user/category
        category = entry["category"]
        user = entry["user"]
        user_manager_stats = manager_stats.get(category, {}).get(user, {"fixed": 0, "reported": 0, "checking": 0, "nonissue": 0})

        # Schema: Date, User, Category, TotalRows, Done, Issues, NoIssue, Blocked, Fixed, Reported, Checking, NonIssue
        ws.cell(row, 1, entry["date"])
        ws.cell(row, 2, entry["user"])
        ws.cell(row, 3, entry["category"])
        ws.cell(row, 4, entry.get("total_rows", 0))  # TotalRows (universe)
        ws.cell(row, 5, entry["done"])               # Done (completed)
        ws.cell(row, 6, entry["issues"])
        ws.cell(row, 7, entry["no_issue"])
        ws.cell(row, 8, entry["blocked"])
        ws.cell(row, 9, user_manager_stats["fixed"])
        ws.cell(row, 10, user_manager_stats["reported"])
        ws.cell(row, 11, user_manager_stats["checking"])
        ws.cell(row, 12, user_manager_stats["nonissue"])


def build_daily_sheet(wb):
    """
    Build DAILY sheet from _DAILY_DATA.

    Aggregates by (date, user) - combines all categories.
    Includes both Tester Stats (Done, Issues) and Manager Stats (Fixed, Reported, Checking, Pending).
    """
    # Delete and recreate sheet to handle merged cells properly
    if "DAILY" in wb.sheetnames:
        del wb["DAILY"]
    ws = wb.create_sheet("DAILY", 0)

    data_ws = wb["_DAILY_DATA"]

    # Read raw data and aggregate by (date, user)
    # Now includes manager stats: fixed, reported, checking, nonissue + total_rows for completion %
    daily_data = defaultdict(lambda: defaultdict(lambda: {
        "total_rows": 0, "done": 0, "issues": 0, "fixed": 0, "reported": 0, "checking": 0, "nonissue": 0
    }))
    users = set()

    # Schema: Date(1), User(2), Category(3), TotalRows(4), Done(5), Issues(6), NoIssue(7), Blocked(8), Fixed(9), Reported(10), Checking(11), NonIssue(12)
    for row in range(2, data_ws.max_row + 1):
        date = data_ws.cell(row, 1).value
        user = data_ws.cell(row, 2).value
        total_rows = data_ws.cell(row, 4).value or 0  # Column 4: TotalRows
        done = data_ws.cell(row, 5).value or 0        # Column 5 now
        issues = data_ws.cell(row, 6).value or 0      # Column 6 now
        fixed = data_ws.cell(row, 9).value or 0       # Column 9 now
        reported = data_ws.cell(row, 10).value or 0   # Column 10 now
        checking = data_ws.cell(row, 11).value or 0   # Column 11 now
        nonissue = data_ws.cell(row, 12).value or 0   # Column 12: NON-ISSUE count

        if date and user:
            daily_data[date][user]["total_rows"] += total_rows
            daily_data[date][user]["done"] += done
            daily_data[date][user]["issues"] += issues
            daily_data[date][user]["fixed"] += fixed
            daily_data[date][user]["reported"] += reported
            daily_data[date][user]["checking"] += checking
            daily_data[date][user]["nonissue"] += nonissue
            users.add(user)

    if not users:
        ws.cell(1, 1, "No data yet")
        return

    users = sorted(users)
    dates = sorted(daily_data.keys())

    # === Calculate DAILY DELTAS from cumulative values ===
    # Each date's data is cumulative - to get daily work, subtract previous day's cumulative
    # daily_delta[date][user] = cumulative[date][user] - cumulative[prev_date][user]
    daily_delta = defaultdict(lambda: defaultdict(lambda: {
        "total_rows": 0, "done": 0, "issues": 0, "fixed": 0, "reported": 0, "checking": 0, "nonissue": 0
    }))

    for i, date in enumerate(dates):
        for user in users:
            current = daily_data[date].get(user, {"total_rows": 0, "done": 0, "issues": 0, "fixed": 0, "reported": 0, "checking": 0, "nonissue": 0})

            if i == 0:
                # First date: delta = cumulative (no previous)
                prev = {"total_rows": 0, "done": 0, "issues": 0, "fixed": 0, "reported": 0, "checking": 0, "nonissue": 0}
            else:
                prev_date = dates[i - 1]
                prev = daily_data[prev_date].get(user, {"total_rows": 0, "done": 0, "issues": 0, "fixed": 0, "reported": 0, "checking": 0, "nonissue": 0})

            # Calculate delta (ensure non-negative)
            daily_delta[date][user]["total_rows"] = current["total_rows"]  # total_rows is universe size, not cumulative
            daily_delta[date][user]["done"] = max(0, current["done"] - prev["done"])
            daily_delta[date][user]["issues"] = max(0, current["issues"] - prev["issues"])
            daily_delta[date][user]["fixed"] = max(0, current["fixed"] - prev["fixed"])
            daily_delta[date][user]["reported"] = max(0, current["reported"] - prev["reported"])
            daily_delta[date][user]["checking"] = max(0, current["checking"] - prev["checking"])
            daily_delta[date][user]["nonissue"] = max(0, current["nonissue"] - prev["nonissue"])

    # Styles
    title_fill = PatternFill(start_color=TRACKER_STYLES["title_color"], end_color=TRACKER_STYLES["title_color"], fill_type="solid")
    header_fill = PatternFill(start_color=TRACKER_STYLES["header_color"], end_color=TRACKER_STYLES["header_color"], fill_type="solid")
    manager_header_fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")  # Light green for manager
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

    # Layout: Date | Tester Stats (Done, Issues, Comp %, Actual Issues per user) | Manager Stats (Fixed, Reported, Checking, Pending)
    # title_cols = Date(1) + Users*4 (tester) + 4 (manager stats)
    tester_cols_per_user = 4  # Done, Issues, Comp %, Actual Issues
    tester_cols = len(users) * tester_cols_per_user
    manager_cols = 4  # Fixed, Reported, Checking, Pending
    title_cols = 1 + tester_cols + manager_cols

    # Row 1: Title
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=title_cols)
    title_cell = ws.cell(1, 1, "DAILY PROGRESS")
    title_cell.fill = title_fill
    title_cell.font = Font(bold=True, size=14)
    title_cell.alignment = center

    # Row 2: Section headers (Tester Stats | Manager Stats)
    ws.cell(3, 1, "")  # Date column header placeholder

    # Tester Stats section header
    if tester_cols > 0:
        tester_start = 2
        tester_end = 1 + tester_cols
        ws.merge_cells(start_row=2, start_column=tester_start, end_row=2, end_column=tester_end)
        tester_section = ws.cell(2, tester_start, "Tester Stats")
        tester_section.fill = header_fill
        tester_section.font = bold
        tester_section.alignment = center

    # Manager Stats section header
    manager_start = 2 + tester_cols
    manager_end = manager_start + manager_cols - 1
    ws.merge_cells(start_row=2, start_column=manager_start, end_row=2, end_column=manager_end)
    manager_section = ws.cell(2, manager_start, "Manager Stats")
    manager_section.fill = manager_header_fill
    manager_section.font = bold
    manager_section.alignment = center

    # Row 3: User names (merged across Done+Issues+Comp%+Actual Issues) for tester section
    col = 2
    for user in users:
        ws.merge_cells(start_row=3, start_column=col, end_row=3, end_column=col + 3)
        cell = ws.cell(3, col, user)
        cell.fill = header_fill
        cell.font = bold
        cell.alignment = center
        for offset in range(1, 4):  # Merged cell styling
            ws.cell(3, col + offset).fill = header_fill
        col += tester_cols_per_user

    # Manager stats headers in row 3
    for i, label in enumerate(["Fixed", "Reported", "Checking", "Pending"]):
        cell = ws.cell(3, manager_start + i, label)
        cell.fill = manager_header_fill
        cell.font = bold
        cell.alignment = center
        cell.border = border

    # Row 4: Sub-headers (Date, Done, Issues, Comp %, Actual Issues per user)
    date_cell = ws.cell(4, 1, "Date")
    date_cell.fill = subheader_fill
    date_cell.font = bold
    date_cell.alignment = center
    date_cell.border = border

    col = 2
    for user in users:
        for label in ["Done", "Issues", "Comp %", "Actual Issues"]:
            cell = ws.cell(4, col, label)
            cell.fill = subheader_fill
            cell.font = bold
            cell.alignment = center
            cell.border = border
            col += 1

    # Manager sub-headers row 4 (empty as labels are in row 3)
    for i in range(manager_cols):
        cell = ws.cell(4, manager_start + i)
        cell.fill = subheader_fill
        cell.border = border

    # Row 5+: Data rows
    user_totals = {user: {"total_rows": 0, "done": 0, "issues": 0, "nonissue": 0} for user in users}
    manager_totals = {"fixed": 0, "reported": 0, "checking": 0, "pending": 0}
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

        # Aggregate manager stats across all users for this date
        day_fixed = 0
        day_reported = 0
        day_checking = 0
        day_issues = 0

        col = 2
        for user in users:
            # Use DELTA values for daily display (not cumulative)
            user_data = daily_delta[date].get(user, {"total_rows": 0, "done": 0, "issues": 0, "fixed": 0, "reported": 0, "checking": 0, "nonissue": 0})
            total_rows_val = user_data["total_rows"]
            done_val = user_data["done"]
            issues_val = user_data["issues"]
            nonissue_val = user_data["nonissue"]

            # Aggregate for manager stats (also use delta values)
            day_fixed += user_data["fixed"]
            day_reported += user_data["reported"]
            day_checking += user_data["checking"]
            day_issues += issues_val

            # Track totals per user
            user_totals[user]["total_rows"] += total_rows_val
            user_totals[user]["done"] += done_val
            user_totals[user]["issues"] += issues_val
            user_totals[user]["nonissue"] += nonissue_val

            # Calculate completion % and actual issues % for this user on this day
            comp_pct = round(done_val / total_rows_val * 100, 1) if total_rows_val > 0 else 0
            # Clamp to 0-100% to prevent negative values from delta calculation
            actual_pct = max(0, min(100, round((issues_val - nonissue_val) / issues_val * 100, 1))) if issues_val > 0 else 0

            # Display value or "--" for zero/no data
            done_display = done_val if done_val > 0 else "--"
            issues_display = issues_val if issues_val > 0 else "--"
            comp_display = f"{comp_pct}%" if total_rows_val > 0 else "--"
            actual_display = f"{actual_pct}%" if issues_val > 0 else "--"

            # Write 4 cells per user: Done, Issues, Comp %, Actual Issues
            for i, (val, fill_alt) in enumerate([
                (done_display, True), (issues_display, True), (comp_display, True), (actual_display, True)
            ]):
                cell = ws.cell(data_row, col + i, val)
                cell.alignment = center
                cell.border = border
                if idx % 2 == 1:
                    cell.fill = alt_fill

            col += tester_cols_per_user

        # Manager stats for this day (aggregated across all users)
        day_pending = day_issues - day_fixed - day_reported - day_checking
        if day_pending < 0:
            day_pending = 0

        manager_totals["fixed"] += day_fixed
        manager_totals["reported"] += day_reported
        manager_totals["checking"] += day_checking
        manager_totals["pending"] += day_pending

        manager_values = [day_fixed, day_reported, day_checking, day_pending]
        for i, val in enumerate(manager_values):
            display_val = val if val > 0 else "--"
            cell = ws.cell(data_row, manager_start + i, display_val)
            cell.alignment = center
            cell.border = border
            if idx % 2 == 1:
                cell.fill = alt_fill

        data_row += 1

    # TOTAL row
    total_cell = ws.cell(data_row, 1, "TOTAL")
    total_cell.fill = total_fill
    total_cell.font = bold
    total_cell.alignment = center
    total_cell.border = border

    col = 2
    for user in users:
        user_total_rows = user_totals[user]["total_rows"]
        user_done = user_totals[user]["done"]
        user_issues = user_totals[user]["issues"]
        user_nonissue = user_totals[user]["nonissue"]
        user_comp_pct = round(user_done / user_total_rows * 100, 1) if user_total_rows > 0 else 0
        # Clamp to 0-100% to prevent negative values
        user_actual_pct = max(0, min(100, round((user_issues - user_nonissue) / user_issues * 100, 1))) if user_issues > 0 else 0

        # Write 4 cells per user: Done, Issues, Comp %, Actual Issues
        for val in [user_done, user_issues, f"{user_comp_pct}%", f"{user_actual_pct}%"]:
            cell = ws.cell(data_row, col, val)
            cell.fill = total_fill
            cell.font = bold
            cell.alignment = center
            cell.border = border
            col += 1

    # Manager totals
    manager_total_values = [manager_totals["fixed"], manager_totals["reported"], manager_totals["checking"], manager_totals["pending"]]
    for i, val in enumerate(manager_total_values):
        cell = ws.cell(data_row, manager_start + i, val)
        cell.fill = total_fill
        cell.font = bold
        cell.alignment = center
        cell.border = border

    # Set column widths with auto-sizing + padding
    PADDING = 2  # Small padding for edge cases
    ws.column_dimensions['A'].width = len("Date") + PADDING + 2  # Date column

    # Tester columns - auto-width based on header length
    col = 2
    for user in users:
        headers = ["Done", "Issues", "Comp %", "Actual Issues"]
        for header in headers:
            col_letter = get_column_letter(col)
            ws.column_dimensions[col_letter].width = len(header) + PADDING
            col += 1

    # Manager columns
    manager_headers = ["Fixed", "Reported", "Checking", "Pending"]
    for i, header in enumerate(manager_headers):
        col_letter = get_column_letter(manager_start + i)
        ws.column_dimensions[col_letter].width = len(header) + PADDING

    # === Add clustered bar chart: Daily Done by User (time-series) ===
    if len(dates) > 0 and len(users) > 0:
        from openpyxl.chart import BarChart, Reference
        from openpyxl.chart.series import DataPoint
        from openpyxl.drawing.fill import PatternFillProperties, ColorChoice

        # Unique colors for each user (vibrant, distinct)
        USER_COLORS = ["4472C4", "ED7D31", "70AD47", "FFC000", "5B9BD5", "7030A0", "C00000", "00B0F0"]

        # Build data table for clustered chart (below main table)
        # Format: Date | User1 | User2 | User3 | ...
        chart_data_row = data_row + 3

        # Header row: Date + User names
        ws.cell(chart_data_row, 1, "Date")
        for i, user in enumerate(users):
            cell = ws.cell(chart_data_row, 2 + i, user)
            cell.font = bold
            cell.alignment = center

        # Data rows: one row per date with Done values per user
        for row_idx, date in enumerate(dates):
            # Format date as MM/DD
            if isinstance(date, str) and len(date) >= 10:
                display_date = date[5:7] + "/" + date[8:10]
            else:
                display_date = str(date)

            ws.cell(chart_data_row + 1 + row_idx, 1, display_date)

            for col_idx, user in enumerate(users):
                # Use DELTA values for chart (not cumulative)
                user_day_data = daily_delta[date].get(user, {"done": 0})
                done_val = user_day_data["done"]
                ws.cell(chart_data_row + 1 + row_idx, 2 + col_idx, done_val if done_val > 0 else 0)

        num_dates = len(dates)
        num_users = len(users)

        # --- Chart 1: Daily Done by Tester ---
        chart1 = BarChart()
        chart1.type = "col"  # Vertical bars (columns)
        chart1.grouping = "clustered"  # Bars side by side per category
        chart1.title = "Daily Progress: Done by Tester"
        chart1.style = 10

        # Dynamic width based on number of dates (expands horizontally)
        chart1.width = max(15, 6 + num_dates * 2)  # Min 15, grows with dates
        chart1.height = 10

        # Data reference: each user column is a series
        data_ref = Reference(
            ws,
            min_col=2,
            max_col=1 + num_users,
            min_row=chart_data_row,
            max_row=chart_data_row + num_dates
        )

        # Categories reference: dates in column 1
        cats_ref = Reference(
            ws,
            min_col=1,
            min_row=chart_data_row + 1,
            max_row=chart_data_row + num_dates
        )

        chart1.add_data(data_ref, titles_from_data=True)
        chart1.set_categories(cats_ref)

        # Apply unique colors to each user's series
        for i, series in enumerate(chart1.series):
            color = USER_COLORS[i % len(USER_COLORS)]
            series.graphicalProperties.solidFill = color

        # Chart formatting
        chart1.legend.position = "b"  # Legend at bottom
        chart1.y_axis.title = "Done"
        chart1.x_axis.title = "Date"
        chart1.x_axis.tickLblPos = "low"  # Labels below axis

        # Place chart 1 below data table
        chart1_row = chart_data_row + num_dates + 3
        ws.add_chart(chart1, f"A{chart1_row}")

        # --- Chart 2: Actual Issues % by Tester ---
        # Build data table for Actual Issues % (below first chart's data)
        chart2_data_row = chart1_row + 15  # Leave space for chart1

        # Header row: Date + User names
        ws.cell(chart2_data_row, 1, "Date")
        for i, user in enumerate(users):
            cell = ws.cell(chart2_data_row, 2 + i, user)
            cell.font = bold
            cell.alignment = center

        # Data rows: Actual Issues % per user per date
        for row_idx, date in enumerate(dates):
            # Format date as MM/DD
            if isinstance(date, str) and len(date) >= 10:
                display_date = date[5:7] + "/" + date[8:10]
            else:
                display_date = str(date)

            ws.cell(chart2_data_row + 1 + row_idx, 1, display_date)

            for col_idx, user in enumerate(users):
                # Use DELTA values for chart (not cumulative)
                user_day_data = daily_delta[date].get(user, {"issues": 0, "nonissue": 0})
                issues = user_day_data.get("issues", 0)
                nonissue = user_day_data.get("nonissue", 0)
                # Clamp to 0-100% to prevent negative values
                actual_pct = max(0, min(100, round((issues - nonissue) / issues * 100, 1))) if issues > 0 else 0
                ws.cell(chart2_data_row + 1 + row_idx, 2 + col_idx, actual_pct)

        # Create chart 2
        chart2 = BarChart()
        chart2.type = "col"
        chart2.grouping = "clustered"
        chart2.title = "Daily Progress: Actual Issues % by Tester"
        chart2.style = 10

        chart2.width = max(15, 6 + num_dates * 2)  # Same dynamic width as chart1
        chart2.height = 10

        data2_ref = Reference(
            ws,
            min_col=2,
            max_col=1 + num_users,
            min_row=chart2_data_row,
            max_row=chart2_data_row + num_dates
        )

        cats2_ref = Reference(
            ws,
            min_col=1,
            min_row=chart2_data_row + 1,
            max_row=chart2_data_row + num_dates
        )

        chart2.add_data(data2_ref, titles_from_data=True)
        chart2.set_categories(cats2_ref)

        # Apply same colors as chart1
        for i, series in enumerate(chart2.series):
            color = USER_COLORS[i % len(USER_COLORS)]
            series.graphicalProperties.solidFill = color

        chart2.legend.position = "b"
        chart2.y_axis.title = "Actual Issues %"
        chart2.x_axis.title = "Date"
        chart2.x_axis.tickLblPos = "low"

        # Place chart 2 below chart 1
        chart2_row = chart2_data_row + num_dates + 3
        ws.add_chart(chart2, f"A{chart2_row}")


def build_total_sheet(wb):
    """
    Build TOTAL sheet from _DAILY_DATA.

    Aggregates by user across all dates and categories.
    Includes both tester stats and manager stats (Fixed, Reported, Checking, Pending).
    Separates EN and CN testers into distinct sections.
    """
    # Delete and recreate sheet to handle merged cells properly
    if "TOTAL" in wb.sheetnames:
        del wb["TOTAL"]
    ws = wb.create_sheet("TOTAL", 1)

    data_ws = wb["_DAILY_DATA"]

    # Load tester mapping to separate EN/CN
    tester_mapping = load_tester_mapping()

    # Read raw data and aggregate by user (now includes manager stats + total_rows + nonissue)
    user_data = defaultdict(lambda: {
        "total_rows": 0, "done": 0, "issues": 0, "no_issue": 0, "blocked": 0,
        "fixed": 0, "reported": 0, "checking": 0, "nonissue": 0
    })

    # Schema: Date(1), User(2), Category(3), TotalRows(4), Done(5), Issues(6), NoIssue(7), Blocked(8), Fixed(9), Reported(10), Checking(11), NonIssue(12)
    for row in range(2, data_ws.max_row + 1):
        user = data_ws.cell(row, 2).value
        total_rows = data_ws.cell(row, 4).value or 0  # TotalRows (universe)
        done = data_ws.cell(row, 5).value or 0        # Done (completed)
        issues = data_ws.cell(row, 6).value or 0
        no_issue = data_ws.cell(row, 7).value or 0
        blocked = data_ws.cell(row, 8).value or 0
        fixed = data_ws.cell(row, 9).value or 0
        reported = data_ws.cell(row, 10).value or 0
        checking = data_ws.cell(row, 11).value or 0
        nonissue = data_ws.cell(row, 12).value or 0   # Manager NON-ISSUE count

        if user:
            user_data[user]["total_rows"] += total_rows
            user_data[user]["done"] += done
            user_data[user]["issues"] += issues
            user_data[user]["no_issue"] += no_issue
            user_data[user]["blocked"] += blocked
            user_data[user]["fixed"] += fixed
            user_data[user]["reported"] += reported
            user_data[user]["checking"] += checking
            user_data[user]["nonissue"] += nonissue

    if not user_data:
        ws.cell(1, 1, "No data yet")
        return

    # Separate users by language
    en_users = sorted([u for u in user_data.keys() if tester_mapping.get(u, "EN") == "EN"])
    cn_users = sorted([u for u in user_data.keys() if tester_mapping.get(u) == "CN"])
    all_users = sorted(user_data.keys())

    # Styles
    title_fill = PatternFill(start_color=TRACKER_STYLES["title_color"], end_color=TRACKER_STYLES["title_color"], fill_type="solid")
    en_title_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")  # Blue for EN
    cn_title_fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")  # Red for CN
    header_fill = PatternFill(start_color=TRACKER_STYLES["header_color"], end_color=TRACKER_STYLES["header_color"], fill_type="solid")
    manager_header_fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")  # Light green
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
    white_bold = Font(bold=True, color="FFFFFF")

    # Total columns: 7 tester + 4 manager = 11
    tester_headers = ["User", "Comp %", "Actual Issues", "Total", "Issues", "No Issue", "Blocked"]
    manager_headers = ["Fixed", "Reported", "Checking", "Pending"]
    total_cols = len(tester_headers) + len(manager_headers)

    def build_section(ws, start_row, section_title, section_fill, users_list, user_data):
        """Build a section (EN or CN) with title, headers, data rows, and subtotal."""
        if not users_list:
            return start_row  # No data for this section

        current_row = start_row

        # Section Title
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=total_cols)
        title_cell = ws.cell(current_row, 1, section_title)
        title_cell.fill = section_fill
        title_cell.font = white_bold
        title_cell.alignment = center
        current_row += 1

        # Headers
        for col, header in enumerate(tester_headers, 1):
            cell = ws.cell(current_row, col, header)
            cell.fill = header_fill
            cell.font = bold
            cell.alignment = center
            cell.border = border

        manager_start_col = len(tester_headers) + 1
        for col, header in enumerate(manager_headers, manager_start_col):
            cell = ws.cell(current_row, col, header)
            cell.fill = manager_header_fill
            cell.font = bold
            cell.alignment = center
            cell.border = border
        current_row += 1

        # Data rows
        section_total = {
            "total_rows": 0, "done": 0, "issues": 0, "no_issue": 0, "blocked": 0,
            "fixed": 0, "reported": 0, "checking": 0, "pending": 0, "nonissue": 0
        }

        for idx, user in enumerate(users_list):
            data = user_data[user]
            total_rows = data["total_rows"]
            done = data["done"]
            issues = data["issues"]
            no_issue = data["no_issue"]
            blocked = data["blocked"]
            fixed = data["fixed"]
            reported = data["reported"]
            checking = data["checking"]
            nonissue = data["nonissue"]
            pending = issues - fixed - reported - checking
            if pending < 0:
                pending = 0

            completion_pct = round(done / total_rows * 100, 1) if total_rows > 0 else 0
            # Clamp to 0-100% to prevent negative values
            actual_pct = max(0, min(100, round((issues - nonissue) / issues * 100, 1))) if issues > 0 else 0

            # Accumulate section totals
            section_total["total_rows"] += total_rows
            section_total["done"] += done
            section_total["issues"] += issues
            section_total["no_issue"] += no_issue
            section_total["blocked"] += blocked
            section_total["fixed"] += fixed
            section_total["reported"] += reported
            section_total["checking"] += checking
            section_total["pending"] += pending
            section_total["nonissue"] += nonissue

            row_data = [user, f"{completion_pct}%", f"{actual_pct}%", done, issues, no_issue, blocked, fixed, reported, checking, pending]

            for col, value in enumerate(row_data, 1):
                cell = ws.cell(current_row, col, value)
                cell.alignment = center
                cell.border = border
                if idx % 2 == 1:
                    cell.fill = alt_fill
            current_row += 1

        # Section subtotal row
        st = section_total
        st_completion = round(st["done"] / st["total_rows"] * 100, 1) if st["total_rows"] > 0 else 0
        # Clamp to 0-100% to prevent negative values
        st_actual_pct = max(0, min(100, round((st["issues"] - st["nonissue"]) / st["issues"] * 100, 1))) if st["issues"] > 0 else 0
        subtotal_data = [
            "SUBTOTAL", f"{st_completion}%", f"{st_actual_pct}%", st["done"], st["issues"], st["no_issue"], st["blocked"],
            st["fixed"], st["reported"], st["checking"], st["pending"]
        ]

        for col, value in enumerate(subtotal_data, 1):
            cell = ws.cell(current_row, col, value)
            cell.fill = total_fill
            cell.font = bold
            cell.alignment = center
            cell.border = border
        current_row += 1

        return current_row, section_total

    # Build EN section
    current_row = 1
    en_total = None
    if en_users:
        current_row, en_total = build_section(ws, current_row, "EN TESTER STATS", en_title_fill, en_users, user_data)
        current_row += 1  # Empty row between sections

    # Build CN section
    cn_total = None
    if cn_users:
        current_row, cn_total = build_section(ws, current_row, "CN TESTER STATS", cn_title_fill, cn_users, user_data)
        current_row += 1  # Empty row before grand total

    # Grand total row (combines EN + CN)
    grand_total = {
        "total_rows": 0, "done": 0, "issues": 0, "no_issue": 0, "blocked": 0,
        "fixed": 0, "reported": 0, "checking": 0, "pending": 0, "nonissue": 0
    }
    for t in [en_total, cn_total]:
        if t:
            for key in grand_total:
                grand_total[key] += t[key]

    if grand_total["total_rows"] > 0:
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=total_cols)
        gt_title = ws.cell(current_row, 1, "GRAND TOTAL (ALL LANGUAGES)")
        gt_title.fill = title_fill
        gt_title.font = Font(bold=True, size=12)
        gt_title.alignment = center
        current_row += 1

        gt = grand_total
        gt_completion = round(gt["done"] / gt["total_rows"] * 100, 1) if gt["total_rows"] > 0 else 0
        # Clamp to 0-100% to prevent negative values
        gt_actual_pct = max(0, min(100, round((gt["issues"] - gt["nonissue"]) / gt["issues"] * 100, 1))) if gt["issues"] > 0 else 0
        total_row_data = [
            "TOTAL", f"{gt_completion}%", f"{gt_actual_pct}%", gt["done"], gt["issues"], gt["no_issue"], gt["blocked"],
            gt["fixed"], gt["reported"], gt["checking"], gt["pending"]
        ]

        for col, value in enumerate(total_row_data, 1):
            cell = ws.cell(current_row, col, value)
            cell.fill = total_fill
            cell.font = bold
            cell.alignment = center
            cell.border = border
        current_row += 1

    # Set column widths with auto-sizing + padding
    PADDING = 2
    all_headers = tester_headers + manager_headers
    for col, header in enumerate(all_headers, 1):
        col_letter = get_column_letter(col)
        ws.column_dimensions[col_letter].width = len(header) + PADDING

    # === Add two clustered bar charts (same style as DAILY) ===
    if len(all_users) > 0:
        from openpyxl.chart import BarChart, Reference

        # Unique colors for each user
        USER_COLORS = ["4472C4", "ED7D31", "70AD47", "FFC000", "5B9BD5", "7030A0", "C00000", "00B0F0"]

        num_users = len(all_users)

        # Build data table for Chart 1: Done by Tester
        chart1_data_row = current_row + 2

        # Header row: Tester | Done value (single series, testers as categories)
        ws.cell(chart1_data_row, 1, "Tester")
        ws.cell(chart1_data_row, 2, "Done")
        for i, user in enumerate(all_users):
            ws.cell(chart1_data_row + 1 + i, 1, user)
            done = user_data[user]["done"]
            ws.cell(chart1_data_row + 1 + i, 2, done)

        # --- Chart 1: Total Done by Tester (clustered bar, vertical) ---
        chart1 = BarChart()
        chart1.type = "col"  # Vertical bars (columns) - same as DAILY
        chart1.grouping = "clustered"
        chart1.title = "Total Progress: Done by Tester"
        chart1.style = 10

        # Dynamic width based on number of users (expands horizontally)
        chart1.width = max(15, 6 + num_users * 2)
        chart1.height = 10

        data1_ref = Reference(ws, min_col=2, min_row=chart1_data_row, max_row=chart1_data_row + num_users)
        cats1_ref = Reference(ws, min_col=1, min_row=chart1_data_row + 1, max_row=chart1_data_row + num_users)
        chart1.add_data(data1_ref, titles_from_data=True)
        chart1.set_categories(cats1_ref)
        chart1.legend = None

        # Apply unique color per bar (each user gets their color)
        if chart1.series:
            for i, pt in enumerate(range(num_users)):
                color = USER_COLORS[i % len(USER_COLORS)]
                # For single series with multiple categories, color each point
                from openpyxl.chart.series import DataPoint
                from openpyxl.drawing.fill import PatternFillProperties, ColorChoice
                point = DataPoint(idx=i)
                point.graphicalProperties.solidFill = color
                chart1.series[0].data_points.append(point)

        chart1.y_axis.title = "Done"
        chart1.x_axis.title = "Tester"
        chart1.x_axis.tickLblPos = "low"

        # Place chart 1 below data table
        chart1_row = chart1_data_row + num_users + 3
        ws.add_chart(chart1, f"A{chart1_row}")

        # --- Chart 2: Actual Issues % by Tester ---
        chart2_data_row = chart1_row + 15  # Leave space for chart1

        ws.cell(chart2_data_row, 1, "Tester")
        ws.cell(chart2_data_row, 2, "Actual Issues %")
        for i, user in enumerate(all_users):
            ws.cell(chart2_data_row + 1 + i, 1, user)
            issues = user_data[user]["issues"]
            nonissue = user_data[user]["nonissue"]
            # Clamp to 0-100% to prevent negative values
            actual_pct = max(0, min(100, round((issues - nonissue) / issues * 100, 1))) if issues > 0 else 0
            ws.cell(chart2_data_row + 1 + i, 2, actual_pct)

        chart2 = BarChart()
        chart2.type = "col"
        chart2.grouping = "clustered"
        chart2.title = "Total Progress: Actual Issues % by Tester"
        chart2.style = 10

        chart2.width = max(15, 6 + num_users * 2)
        chart2.height = 10

        data2_ref = Reference(ws, min_col=2, min_row=chart2_data_row, max_row=chart2_data_row + num_users)
        cats2_ref = Reference(ws, min_col=1, min_row=chart2_data_row + 1, max_row=chart2_data_row + num_users)
        chart2.add_data(data2_ref, titles_from_data=True)
        chart2.set_categories(cats2_ref)
        chart2.legend = None

        # Apply unique color per bar
        if chart2.series:
            for i in range(num_users):
                color = USER_COLORS[i % len(USER_COLORS)]
                from openpyxl.chart.series import DataPoint
                point = DataPoint(idx=i)
                point.graphicalProperties.solidFill = color
                chart2.series[0].data_points.append(point)

        chart2.y_axis.title = "Actual Issues %"
        chart2.x_axis.title = "Tester"
        chart2.x_axis.tickLblPos = "low"

        # Place chart 2 below chart 1
        chart2_row = chart2_data_row + num_users + 3
        ws.add_chart(chart2, f"A{chart2_row}")


# build_graphs_sheet removed - charts now embedded in DAILY/TOTAL




def process_category(category, qa_folders, master_folder, images_folder, lang_label, manager_status=None):
    """
    Process all QA folders for one category.

    Args:
        category: Category name (Quest, Knowledge, etc.)
        qa_folders: List of dicts with {folder_path, xlsx_path, username, category, images}
        master_folder: Target Master folder (EN or CN)
        images_folder: Target Images folder (EN or CN)
        lang_label: Language label for display ("EN" or "CN")
        manager_status: Dict of {sheet_name: {row: {user: status}}} from preprocess (optional)

    Returns:
        List of daily_entry dicts for tracker
    """
    if manager_status is None:
        manager_status = {}
    print(f"\n{'='*50}")
    print(f"Processing: {category} [{lang_label}] ({len(qa_folders)} folders)")
    print(f"{'='*50}")

    daily_entries = []  # NEW: Collect entries for tracker

    # Get or create master (in correct language folder)
    first_xlsx = qa_folders[0]["xlsx_path"]
    master_wb, master_path = get_or_create_master(category, master_folder, first_xlsx)

    if master_wb is None:
        return daily_entries

    # For EN Item category: Sort master A-Z by ItemName(ENG) column to match tester's sorted files
    # CN Item uses original indexing (no sorting)
    if category.lower() == "item" and lang_label == "EN":
        print("  [Item EN] Sorting master sheets A-Z by ItemName(ENG) column...")
        for sheet_name in master_wb.sheetnames:
            if sheet_name != "STATUS":
                ws = master_wb[sheet_name]
                # Find ItemName(ENG) column
                sort_col = find_column_by_header(ws, "ItemName(ENG)")
                if sort_col:
                    sort_worksheet_az(ws, sort_column=sort_col)
                    print(f"    Sorted {sheet_name} by column {sort_col} (ItemName(ENG))")
                else:
                    print(f"    WARNING: ItemName(ENG) column not found in {sheet_name}, skipping sort")

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

        # Copy images to correct language folder
        image_mapping = copy_images_with_unique_names(qf, images_folder)
        total_images += len(image_mapping)

        # Load xlsx
        qa_wb = openpyxl.load_workbook(xlsx_path)

        # For EN Item category: Sort input A-Z to match master ordering
        # This ensures consistent row alignment regardless of tester's file order
        if category.lower() == "item" and lang_label == "EN":
            for sheet_name in qa_wb.sheetnames:
                if sheet_name != "STATUS":
                    qa_ws = qa_wb[sheet_name]
                    sort_col = find_column_by_header(qa_ws, "ItemName(ENG)")
                    if sort_col:
                        sort_worksheet_az(qa_ws, sort_column=sort_col)

        for sheet_name in qa_wb.sheetnames:
            # Skip STATUS sheets
            if sheet_name == "STATUS":
                continue

            # Check if sheet exists in master
            if sheet_name not in master_wb.sheetnames:
                print(f"    WARN: Sheet '{sheet_name}' not in master, skipping")
                continue

            # Process sheet with image mapping for hyperlink transformation + xlsx_path for mod time
            # Also pass manager_status for this sheet to preserve manager entries
            sheet_manager_status = manager_status.get(sheet_name, {})
            result = process_sheet(master_wb[sheet_name], qa_wb[sheet_name], username, category, image_mapping, xlsx_path, sheet_manager_status)
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
            "lang": lang_label,  # EN or CN for tracker separation
            "total_rows": user_stats[username]["total"],  # Total universe of rows
            "done": user_stats[username]["issue"] + user_stats[username]["no_issue"] + user_stats[username]["blocked"],
            "issues": user_stats[username]["issue"],
            "no_issue": user_stats[username]["no_issue"],
            "blocked": user_stats[username]["blocked"]
        })

    # Update STATUS sheet (first tab, with stats)
    update_status_sheet(master_wb, all_users, user_stats)

    # Post-process: Hide rows/sheets/columns with no comments (focus on issues)
    hidden_rows, hidden_sheets, hidden_columns = hide_empty_comment_rows(master_wb)

    # Apply word wrap and autofit row heights
    autofit_rows_with_wordwrap(master_wb)

    # Save master
    master_wb.save(master_path)
    print(f"\n  Saved: {master_path}")
    if hidden_sheets:
        print(f"  Hidden sheets (no comments): {', '.join(hidden_sheets)}")
    if hidden_columns > 0:
        print(f"  Hidden: {hidden_columns} empty user columns (unhide in Excel if needed)")
    if hidden_rows > 0:
        print(f"  Hidden: {hidden_rows} rows with no comments (unhide in Excel if needed)")
    if total_images > 0:
        print(f"  Images: {total_images} copied to Images/, {total_screenshots} hyperlinks updated")

    return daily_entries  # NEW: Return entries for tracker


def main():
    """Main entry point."""
    print("="*60)
    print("QA Excel Compiler (EN/CN Separation + Manager Status)")
    print("="*60)
    print("Features:")
    print("  - Folder-based input: QAfolder/{Username}_{Category}/")
    print("  - Language separation: Masterfolder_EN/ and Masterfolder_CN/")
    print("  - Auto-routing testers by language mapping")
    print("  - Manager workflow: STATUS_{User} for FIXED/REPORTED/CHECKING")
    print("  - Manager status preservation on re-compile")
    print("  - Auto-hide rows with no comments (focus on issues)")
    print("  - Combined Progress Tracker at root level")
    print()

    # Load tester→language mapping
    print("Loading tester→language mapping...")
    tester_mapping = load_tester_mapping()

    # Ensure folders exist
    ensure_master_folders()

    # PREPROCESS: Collect manager status from existing Master files (both EN and CN)
    print("\nCollecting manager status from existing Master files...")
    manager_status_en = collect_manager_status(MASTER_FOLDER_EN)
    manager_status_cn = collect_manager_status(MASTER_FOLDER_CN)
    total_en = sum(sum(len(rows) for rows in sheets.values()) for sheets in manager_status_en.values())
    total_cn = sum(sum(len(rows) for rows in sheets.values()) for sheets in manager_status_cn.values())
    if total_en > 0 or total_cn > 0:
        print(f"  Found {total_en} EN + {total_cn} CN manager status entries to preserve")
    else:
        print("  No existing manager status entries found")

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

    # Group by category AND language
    by_category_en = defaultdict(list)
    by_category_cn = defaultdict(list)
    print("\nRouting testers by language:")
    for qf in qa_folders:
        username = qf["username"].strip()  # Strip whitespace for safety
        lang = tester_mapping.get(username, "EN")
        in_mapping = username in tester_mapping
        print(f"  {username} ({qf['category']}) -> {lang}{'' if in_mapping else ' (not in mapping, default)'}")
        if lang == "CN":
            by_category_cn[qf["category"]].append(qf)
        else:
            by_category_en[qf["category"]].append(qf)

    # Process each category for EN and CN
    all_daily_entries = []

    # Process EN
    for category in CATEGORIES:
        if category in by_category_en:
            category_manager_status = manager_status_en.get(category, {})
            entries = process_category(
                category, by_category_en[category],
                MASTER_FOLDER_EN, IMAGES_FOLDER_EN, "EN",
                category_manager_status
            )
            all_daily_entries.extend(entries)

    # Process CN
    for category in CATEGORIES:
        if category in by_category_cn:
            category_manager_status = manager_status_cn.get(category, {})
            entries = process_category(
                category, by_category_cn[category],
                MASTER_FOLDER_CN, IMAGES_FOLDER_CN, "CN",
                category_manager_status
            )
            all_daily_entries.extend(entries)

    # Show skipped categories
    for category in CATEGORIES:
        if category not in by_category_en and category not in by_category_cn:
            print(f"\nSKIP: No folders for category '{category}'")

    # Update LQA User Progress Tracker
    if all_daily_entries:
        print("\n" + "="*60)
        print("Updating LQA User Progress Tracker...")
        print("="*60)

        # Collect manager stats for tracker (FIXED/REPORTED/CHECKING counts)
        manager_stats = collect_manager_stats_for_tracker()

        tracker_wb, tracker_path = get_or_create_tracker()
        update_daily_data_sheet(tracker_wb, all_daily_entries, manager_stats)
        build_daily_sheet(tracker_wb)
        build_total_sheet(tracker_wb)

        # Remove GRAPHS sheet if it exists (deprecated)
        if "GRAPHS" in tracker_wb.sheetnames:
            del tracker_wb["GRAPHS"]

        tracker_wb.save(tracker_path)

        print(f"  Saved: {tracker_path}")
        print(f"  Sheets: DAILY (with chart), TOTAL (with chart)")

    print("\n" + "="*60)
    print("Compilation complete!")
    print(f"Output EN: {MASTER_FOLDER_EN}")
    print(f"Output CN: {MASTER_FOLDER_CN}")
    if all_daily_entries:
        print(f"Tracker: {TRACKER_PATH}")
    print("="*60)


if __name__ == "__main__":
    main()
