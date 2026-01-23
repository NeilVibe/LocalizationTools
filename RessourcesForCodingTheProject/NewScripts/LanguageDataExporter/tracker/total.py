"""
TOTAL sheet builder for Correction Progress Tracker.

Contains two tables:
1. Per-Language Summary (STRING count)
2. Per-Category/Per-Language % Done (with Korean word count)
"""

import logging
from typing import Dict, List, Set

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

TOTAL_SHEET_NAME = "TOTAL"

# Styling
HEADER_FONT = Font(bold=True, size=11)
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT_WHITE = Font(bold=True, size=11, color="FFFFFF")
TITLE_FONT = Font(bold=True, size=14)
SECTION_FONT = Font(bold=True, size=12)
THIN_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)


def build_total_sheet(
    wb: Workbook,
    latest_data: Dict[str, Dict[str, Dict]],
    categories: List[str]
) -> None:
    """
    Build the TOTAL sheet with summary tables.

    Args:
        wb: Workbook to add sheet to
        latest_data: Dict[language, Dict[category, Dict]] from get_latest_week_data()
        categories: List of category names to include in per-category table
    """
    # Create or get sheet
    if TOTAL_SHEET_NAME in wb.sheetnames:
        del wb[TOTAL_SHEET_NAME]

    ws = wb.create_sheet(TOTAL_SHEET_NAME, 1)  # Second position

    if not latest_data:
        ws.cell(row=1, column=1, value="No data yet. Run 'Prepare For Submit' to collect data.")
        return

    # Get sorted language list
    languages = sorted(latest_data.keys())

    # =========================================================================
    # Table 1: Per-Language Summary
    # =========================================================================
    _build_language_summary_table(ws, latest_data, languages, start_row=1)

    # =========================================================================
    # Table 2: Per-Category/Per-Language % Done
    # =========================================================================
    # Calculate start row (after table 1 + gap)
    table2_start = len(languages) + 7
    _build_category_table(ws, latest_data, languages, categories, start_row=table2_start)

    # Set column widths
    ws.column_dimensions['A'].width = 15  # Category/Language column

    logger.info(f"Built TOTAL sheet with {len(languages)} languages, {len(categories)} categories")


def _build_language_summary_table(
    ws,
    data: Dict[str, Dict[str, Dict]],
    languages: List[str],
    start_row: int
) -> int:
    """
    Build Table 1: Per-Language Summary.

    | Language | Corrected | Pending | Total | % Complete | Korean Words |
    """
    # Section title
    ws.cell(row=start_row, column=1, value="PER-LANGUAGE SUMMARY")
    ws.cell(row=start_row, column=1).font = TITLE_FONT

    # Headers (row + 2)
    header_row = start_row + 2
    headers = ["Language", "Corrected", "Pending", "Total", "% Complete", "Korean Words"]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col, value=header)
        cell.font = HEADER_FONT_WHITE
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER

    # Data rows
    data_row = header_row + 1
    for lang in languages:
        lang_data = data.get(lang, {})

        # Aggregate across all categories
        total_corrected = sum(cat.get("Corrected", 0) for cat in lang_data.values())
        total_pending = sum(cat.get("Pending", 0) for cat in lang_data.values())
        total_kr_words = sum(cat.get("KRWords", 0) for cat in lang_data.values())
        total = total_corrected + total_pending
        pct_complete = (total_corrected / total) if total > 0 else 0

        ws.cell(row=data_row, column=1, value=lang)
        ws.cell(row=data_row, column=2, value=total_corrected)
        ws.cell(row=data_row, column=3, value=total_pending)
        ws.cell(row=data_row, column=4, value=total)

        pct_cell = ws.cell(row=data_row, column=5, value=pct_complete)
        pct_cell.number_format = '0.0%'

        ws.cell(row=data_row, column=6, value=total_kr_words)

        # Apply borders and alignment
        for col in range(1, 7):
            ws.cell(row=data_row, column=col).border = THIN_BORDER
            ws.cell(row=data_row, column=col).alignment = Alignment(horizontal="center")

        data_row += 1

    return data_row


def _build_category_table(
    ws,
    data: Dict[str, Dict[str, Dict]],
    languages: List[str],
    categories: List[str],
    start_row: int
) -> int:
    """
    Build Table 2: Per-Category/Per-Language % Done.

    | Category | ENG | FRE | GER | ... | Total KR Words |
    """
    # Section title
    ws.cell(row=start_row, column=1, value="PER-CATEGORY COMPLETION")
    ws.cell(row=start_row, column=1).font = TITLE_FONT

    # Headers: Category + each language + Total KR Words
    header_row = start_row + 2
    headers = ["Category"] + languages + ["Total KR Words"]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col, value=header)
        cell.font = HEADER_FONT_WHITE
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER

        # Set width for language columns
        if col > 1 and col < len(headers):
            ws.column_dimensions[get_column_letter(col)].width = 8
        elif col == len(headers):
            ws.column_dimensions[get_column_letter(col)].width = 14

    # Collect all categories that have data
    all_cats_with_data: Set[str] = set()
    for lang_data in data.values():
        all_cats_with_data.update(lang_data.keys())

    # Use predefined categories order, plus any extras
    ordered_categories = [c for c in categories if c in all_cats_with_data]
    extra_cats = sorted(all_cats_with_data - set(categories))
    ordered_categories.extend(extra_cats)

    # Data rows
    data_row = header_row + 1
    for category in ordered_categories:
        ws.cell(row=data_row, column=1, value=category)
        ws.cell(row=data_row, column=1).border = THIN_BORDER

        total_kr_words = 0

        for col_idx, lang in enumerate(languages, 2):
            lang_data = data.get(lang, {})
            cat_data = lang_data.get(category, {})

            corrected = cat_data.get("Corrected", 0)
            pending = cat_data.get("Pending", 0)
            kr_words = cat_data.get("KRWords", 0)
            total = corrected + pending
            pct = (corrected / total) if total > 0 else 0

            total_kr_words += kr_words

            if total > 0:
                pct_cell = ws.cell(row=data_row, column=col_idx, value=pct)
                pct_cell.number_format = '0.0%'
            else:
                ws.cell(row=data_row, column=col_idx, value="-")

            ws.cell(row=data_row, column=col_idx).border = THIN_BORDER
            ws.cell(row=data_row, column=col_idx).alignment = Alignment(horizontal="center")

        # Total KR Words column
        kr_col = len(languages) + 2
        ws.cell(row=data_row, column=kr_col, value=total_kr_words)
        ws.cell(row=data_row, column=kr_col).border = THIN_BORDER
        ws.cell(row=data_row, column=kr_col).alignment = Alignment(horizontal="center")

        data_row += 1

    return data_row
