"""
Excel Operations Module
=======================
Workbook loading, saving, and manipulation utilities.
"""

import os
import re
import shutil
import zipfile
import tempfile
from copy import copy
from pathlib import Path
from typing import Optional, List, Dict, Tuple

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    MASTER_FOLDER_EN, MASTER_FOLDER_CN,
    IMAGES_FOLDER_EN, IMAGES_FOLDER_CN,
    CATEGORY_TO_MASTER, STATUS_OPTIONS, MANAGER_STATUS_OPTIONS,
    TRACKER_STYLES, get_target_master_category
)


# =============================================================================
# WORKBOOK LOADING
# =============================================================================

def repair_excel_filters(filepath: Path) -> Optional[Path]:
    """
    Repair Excel file by stripping corrupted auto-filter XML.

    Excel files are ZIP archives. This extracts, removes autoFilter
    elements from worksheet XML, and repacks to a temp file.

    Args:
        filepath: Path to corrupted Excel file

    Returns:
        Path to repaired temp file, or None if repair failed
    """
    try:
        # Create temp file for repaired Excel
        temp_fd, temp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(temp_fd)

        with zipfile.ZipFile(filepath, 'r') as zip_in:
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                for item in zip_in.namelist():
                    data = zip_in.read(item)

                    # Strip autoFilter from worksheet XML files
                    if item.startswith('xl/worksheets/') and item.endswith('.xml'):
                        content = data.decode('utf-8')
                        # Remove autoFilter elements (including corrupted ones)
                        content = re.sub(r'<autoFilter[^>]*>.*?</autoFilter>', '', content, flags=re.DOTALL)
                        content = re.sub(r'<autoFilter[^/]*/>', '', content)
                        data = content.encode('utf-8')

                    zip_out.writestr(item, data)

        return Path(temp_path)
    except Exception as e:
        print(f"    Repair failed: {e}")
        return None


def safe_load_workbook(filepath: Path, **kwargs) -> Workbook:
    """
    Safely load an Excel workbook, handling common corruption issues.

    ROBUST: Auto-repairs corrupted auto-filters by stripping them from XML.

    Args:
        filepath: Path to the Excel file
        **kwargs: Additional arguments passed to openpyxl.load_workbook

    Returns:
        Workbook object

    Raises:
        Exception for unrecoverable errors
    """
    try:
        return openpyxl.load_workbook(filepath, **kwargs)
    except ValueError as e:
        error_msg = str(e)

        # Handle corrupted filter values - AUTO REPAIR
        if "numerical or a string containing a wildcard" in error_msg or "could not read worksheets" in error_msg:
            print(f"    WARNING: Corrupted filters detected, auto-repairing...")

            repaired_path = repair_excel_filters(filepath)
            if repaired_path:
                try:
                    wb = openpyxl.load_workbook(repaired_path, **kwargs)
                    try:
                        os.unlink(repaired_path)
                    except:
                        pass
                    print(f"    SUCCESS: File repaired and loaded (filters stripped)")
                    return wb
                except Exception as repair_error:
                    print(f"    Repair load failed: {repair_error}")
                    try:
                        os.unlink(repaired_path)
                    except:
                        pass

            print(f"    ERROR: Auto-repair failed for '{filepath.name}'")
            print(f"           Manual fix: Open in Excel → Data → Clear → Save")
            raise ValueError(f"Corrupted Excel file: {filepath.name}. Auto-repair failed.")

        raise
    except Exception as e:
        print(f"    ERROR loading '{filepath}': {e}")
        raise


# =============================================================================
# COLUMN OPERATIONS
# =============================================================================

def find_column_by_header(ws, header_name: str, case_insensitive: bool = True) -> Optional[int]:
    """
    Find column index by header name.

    Args:
        ws: Worksheet
        header_name: Header to search for
        case_insensitive: Match case-insensitively

    Returns:
        Column index (1-based) or None if not found
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


def build_column_map(ws) -> Dict[str, int]:
    """
    Build a dict mapping header names to column indices (1-based).

    Scans row 1 once and returns {HEADER_UPPER: col_index}.
    First occurrence wins (matches find_column_by_header behavior).
    Keys are uppercased for case-insensitive matching.

    Args:
        ws: Worksheet

    Returns:
        Dict mapping uppercase header name to column index
    """
    col_map = {}
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header:
            key = str(header).strip().upper()
            if key not in col_map:
                col_map[key] = col
    return col_map


def find_column_by_prefix(ws, prefix: str) -> Optional[int]:
    """
    Find column index by header prefix.

    Args:
        ws: Worksheet
        prefix: Header prefix to match

    Returns:
        Column index (1-based) or None if not found
    """
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header and str(header).upper().startswith(prefix.upper()):
            return col
    return None


# =============================================================================
# MASTER FILE OPERATIONS
# =============================================================================

def get_or_create_master(
    category: str,
    master_folder: Path,
    template_file: Path = None,
    rebuild: bool = True
) -> Tuple[Optional[Workbook], Path]:
    """
    Get or create master workbook for a category.

    Args:
        category: Category name (Quest, Knowledge, etc.)
        master_folder: Target Master folder (EN or CN)
        template_file: Path to first QA file to use as template
        rebuild: If True, delete old and create fresh. If False, append to existing.

    Returns:
        Tuple of (Workbook, master_path)
    """
    target_category = get_target_master_category(category)
    master_path = master_folder / f"Master_{target_category}.xlsx"

    # If not rebuilding and master exists, load it and add new sheets
    if not rebuild and master_path.exists():
        print(f"  Loading existing master: {master_path.name} (appending {category} sheets)")
        wb = safe_load_workbook(master_path)

        # Copy sheets from template that don't exist in master yet
        if template_file:
            template_wb = safe_load_workbook(template_file)
            sheets_added = []

            for sheet_name in template_wb.sheetnames:
                if sheet_name == "STATUS":
                    continue
                if sheet_name not in wb.sheetnames:
                    # Copy sheet from template to master
                    source_ws = template_wb[sheet_name]
                    target_ws = wb.create_sheet(sheet_name)

                    # Copy all cells
                    for row in source_ws.iter_rows():
                        for cell in row:
                            new_cell = target_ws.cell(row=cell.row, column=cell.column, value=cell.value)
                            if cell.has_style:
                                new_cell.font = copy(cell.font)
                                new_cell.border = copy(cell.border)
                                new_cell.fill = copy(cell.fill)
                                new_cell.number_format = cell.number_format
                                new_cell.alignment = copy(cell.alignment)

                    # Copy column widths
                    for col_letter, col_dim in source_ws.column_dimensions.items():
                        target_ws.column_dimensions[col_letter].width = col_dim.width

                    # Copy row heights
                    for row_num, row_dim in source_ws.row_dimensions.items():
                        target_ws.row_dimensions[row_num].height = row_dim.height

                    # Clean the new sheet (delete tester columns)
                    # MEMO is Script category's equivalent of COMMENT
                    cols_to_delete = []
                    for h in ["STATUS", "COMMENT", "MEMO", "SCREENSHOT", "STRINGID"]:
                        col = find_column_by_header(target_ws, h)
                        if col:
                            cols_to_delete.append(col)
                    cols_to_delete.sort(reverse=True)
                    for col in cols_to_delete:
                        target_ws.delete_cols(col)

                    sheets_added.append(sheet_name)

            template_wb.close()

            if sheets_added:
                print(f"    Added {len(sheets_added)} new sheets from {category}: {', '.join(sheets_added)}")

        return wb, master_path

    # Rebuild mode: delete old master and create fresh
    if rebuild and master_path.exists():
        print(f"  Deleting old master: {master_path.name} (rebuilding fresh)")
        master_path.unlink()

    if template_file:
        print(f"  Creating new master from: {template_file.name}")
        wb = safe_load_workbook(template_file)

        # Delete tester columns (MEMO is Script category's equivalent of COMMENT)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]

            # Clear AutoFilter
            if ws.auto_filter.ref:
                ws.auto_filter.ref = None

            cols_to_delete = []
            for h in ["STATUS", "COMMENT", "MEMO", "SCREENSHOT", "STRINGID"]:
                col = find_column_by_header(ws, h)
                if col:
                    cols_to_delete.append(col)

            cols_to_delete.sort(reverse=True)
            for col in cols_to_delete:
                ws.delete_cols(col)
                print(f"    Deleted column {col} from {sheet_name}")

        print(f"    Master cleaned: tester columns removed")
        return wb, master_path
    else:
        print(f"  ERROR: No template file for {category}")
        return None, master_path


# =============================================================================
# FOLDER OPERATIONS
# =============================================================================

def ensure_master_folders():
    """Create both EN and CN master folders if they don't exist."""
    MASTER_FOLDER_EN.mkdir(exist_ok=True)
    MASTER_FOLDER_CN.mkdir(exist_ok=True)
    IMAGES_FOLDER_EN.mkdir(exist_ok=True)
    IMAGES_FOLDER_CN.mkdir(exist_ok=True)


def get_master_folder(username: str, tester_mapping: Dict[str, str]) -> Tuple[Path, Path]:
    """Get the correct master folder based on tester's language."""
    lang = tester_mapping.get(username, "EN")
    if lang == "CN":
        return MASTER_FOLDER_CN, IMAGES_FOLDER_CN
    return MASTER_FOLDER_EN, IMAGES_FOLDER_EN


# =============================================================================
# IMAGE OPERATIONS
# =============================================================================

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}


def copy_images_with_unique_names(
    qa_folder_info: Dict,
    images_folder: Path,
    skip_images: set = None
) -> Dict[str, str]:
    """
    Copy images from QA folder to Images/ with original names.

    Optimization: Skip images in skip_images set (e.g., FIXED screenshots).

    Args:
        qa_folder_info: Dict with {folder_path, username, category, images}
        images_folder: Target Images folder
        skip_images: Set of image filenames to skip (case-insensitive)

    Returns:
        Dict mapping original_name -> original_name
    """
    images = qa_folder_info["images"]
    image_mapping = {}
    skipped = 0

    # Normalize skip list for case-insensitive matching
    skip_set = {s.lower() for s in (skip_images or set())}

    for img_path in images:
        original_name = img_path.name

        # Skip FIXED images
        if original_name.lower() in skip_set:
            skipped += 1
            continue

        dest_path = images_folder / original_name
        shutil.copy2(img_path, dest_path)
        image_mapping[original_name] = original_name

    if image_mapping or skipped:
        msg = f"    Copied {len(image_mapping)} images to Images/"
        if skipped:
            msg += f" (skipped {skipped} FIXED)"
        print(msg)

    return image_mapping


# =============================================================================
# STYLING HELPERS
# =============================================================================

# Standard border
THIN_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

# Header styles
HEADER_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
HEADER_FONT = Font(bold=True)
HEADER_ALIGNMENT = Alignment(horizontal='center', vertical='center')


def style_header_cell(cell):
    """Apply standard header styling to a cell."""
    cell.fill = HEADER_FILL
    cell.font = HEADER_FONT
    cell.alignment = HEADER_ALIGNMENT
    cell.border = THIN_BORDER


def add_status_dropdown(ws, col: int, start_row: int = 2, end_row: int = None):
    """Add STATUS dropdown validation to a column."""
    if end_row is None:
        end_row = ws.max_row

    dv = DataValidation(
        type="list",
        formula1=f'"{",".join(STATUS_OPTIONS)}"',
        allow_blank=True
    )
    dv.error = "Please select from the list"
    dv.errorTitle = "Invalid Status"
    ws.add_data_validation(dv)

    for row in range(start_row, end_row + 1):
        dv.add(ws.cell(row=row, column=col))


def add_manager_dropdown(ws, col: int, start_row: int = 2, end_row: int = None):
    """Add manager status dropdown validation to a column."""
    if end_row is None:
        end_row = ws.max_row

    dv = DataValidation(
        type="list",
        formula1=f'"{",".join(MANAGER_STATUS_OPTIONS)}"',
        allow_blank=True
    )
    dv.error = "Please select from the list"
    dv.errorTitle = "Invalid Status"
    ws.add_data_validation(dv)

    for row in range(start_row, end_row + 1):
        dv.add(ws.cell(row=row, column=col))


# =============================================================================
# WORKSHEET SORTING
# =============================================================================

def sort_worksheet_az(ws, sort_column: int = 1):
    """
    Sort worksheet rows A-Z by specified column.

    Used for EN Item category to match tester's A-Z sorted files.
    Preserves header row (row 1), sorts data rows (row 2+).

    Args:
        ws: Worksheet to sort
        sort_column: Column index to sort by (1-based, default=1 for column A)
    """
    # CRITICAL: Clear any AutoFilter before sorting (testers may have filters applied)
    if ws.auto_filter.ref:
        ws.auto_filter.ref = None

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
        # Store sort key (specified column value) and row data
        sort_key = ws.cell(row=row, column=sort_column).value
        sort_key = str(sort_key).lower() if sort_key else ""
        data_rows.append((sort_key, row_data))

    # Sort by specified column (A-Z)
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
