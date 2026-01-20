"""
Excel Writer for categorized language data.

Generates Excel files with openpyxl, styled with headers and proper column widths.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

# Excel styling constants
HEADER_FONT = Font(bold=True, size=11)
HEADER_FILL = PatternFill(start_color="DAEEF3", end_color="DAEEF3", fill_type="solid")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")
CELL_ALIGNMENT = Alignment(horizontal="left", vertical="top", wrap_text=True)
THIN_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

# Column widths
DEFAULT_WIDTHS = {
    "StrOrigin": 45,
    "Str": 45,
    "StringID": 15,
    "English": 45,
    "Category": 20,
}


def _apply_header_style(ws, row: int = 1):
    """Apply styling to header row."""
    for cell in ws[row]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER


def _set_column_widths(ws, headers: List[str]):
    """Set column widths based on header names."""
    for idx, header in enumerate(headers, 1):
        col_letter = get_column_letter(idx)
        width = DEFAULT_WIDTHS.get(header, 20)
        ws.column_dimensions[col_letter].width = width


def write_language_excel(
    lang_code: str,
    lang_data: List[Dict],
    eng_lookup: Dict[str, str],
    category_index: Dict[str, str],
    output_path: Path,
    include_english: bool = True,
    default_category: str = "Uncategorized"
) -> bool:
    """
    Write Excel file for one language.

    Args:
        lang_code: Language code (e.g., "eng", "fre")
        lang_data: List of dicts with str_origin, str, string_id
        eng_lookup: {StringID: English translation} for cross-reference
        category_index: {StringID: Category} mapping
        output_path: Path to output Excel file
        include_english: Whether to include English column
        default_category: Category for unmapped StringIDs

    Returns:
        True if successful, False otherwise

    Column structure:
    - European: StrOrigin | Str | StringID | English | Category
    - Asian:    StrOrigin | Str | StringID | Category
    """
    try:
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = lang_code.upper()

        # Define headers based on language type
        if include_english:
            headers = ["StrOrigin", "Str", "StringID", "English", "Category"]
        else:
            headers = ["StrOrigin", "Str", "StringID", "Category"]

        # Write header row
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

        # Apply header styling
        _apply_header_style(ws)
        _set_column_widths(ws, headers)

        # Write data rows
        row_num = 2
        for entry in lang_data:
            string_id = entry.get('string_id', '')
            str_origin = entry.get('str_origin', '')
            str_value = entry.get('str', '')

            # Get category
            category = category_index.get(string_id, default_category)

            # Get English translation if needed
            english = eng_lookup.get(string_id, '') if include_english else None

            # Build row data
            if include_english:
                row_data = [str_origin, str_value, string_id, english, category]
            else:
                row_data = [str_origin, str_value, string_id, category]

            # Write cells
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_num, column=col, value=value)
                cell.alignment = CELL_ALIGNMENT
                cell.border = THIN_BORDER

            row_num += 1

        # Freeze header row
        ws.freeze_panes = 'A2'

        # Add auto-filter
        ws.auto_filter.ref = ws.dimensions

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save workbook
        wb.save(output_path)

        logger.info(f"Generated {output_path.name} with {row_num - 2} rows")
        return True

    except Exception as e:
        logger.error(f"Error writing Excel for {lang_code}: {e}")
        return False


def write_summary_excel(
    language_stats: Dict[str, Dict],
    category_stats: Dict[str, int],
    output_path: Path
) -> bool:
    """
    Write a summary Excel file with statistics.

    Args:
        language_stats: {lang_code: {"rows": N, "file": "path"}}
        category_stats: {category: count}
        output_path: Path to output Excel file

    Returns:
        True if successful, False otherwise
    """
    try:
        wb = Workbook()

        # Languages sheet
        ws_lang = wb.active
        ws_lang.title = "Languages"

        headers = ["Language", "Rows", "File"]
        for col, header in enumerate(headers, 1):
            ws_lang.cell(row=1, column=col, value=header)
        _apply_header_style(ws_lang)

        row = 2
        for lang, stats in sorted(language_stats.items()):
            ws_lang.cell(row=row, column=1, value=lang.upper())
            ws_lang.cell(row=row, column=2, value=stats.get("rows", 0))
            ws_lang.cell(row=row, column=3, value=stats.get("file", ""))
            row += 1

        # Categories sheet
        ws_cat = wb.create_sheet("Categories")

        headers = ["Category", "StringIDs"]
        for col, header in enumerate(headers, 1):
            ws_cat.cell(row=1, column=col, value=header)
        _apply_header_style(ws_cat)

        row = 2
        for category, count in sorted(category_stats.items(), key=lambda x: -x[1]):
            ws_cat.cell(row=row, column=1, value=category)
            ws_cat.cell(row=row, column=2, value=count)
            row += 1

        # Set column widths
        ws_lang.column_dimensions['A'].width = 15
        ws_lang.column_dimensions['B'].width = 10
        ws_lang.column_dimensions['C'].width = 40

        ws_cat.column_dimensions['A'].width = 25
        ws_cat.column_dimensions['B'].width = 15

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_path)

        logger.info(f"Generated summary: {output_path.name}")
        return True

    except Exception as e:
        logger.error(f"Error writing summary Excel: {e}")
        return False
