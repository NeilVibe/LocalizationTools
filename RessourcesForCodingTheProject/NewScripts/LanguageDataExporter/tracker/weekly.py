"""
WEEKLY sheet builder for Correction Progress Tracker.

Shows week-over-week progress per language with:
- Language, Week, Corrected, Pending, % Done, KR Words
"""

import logging
from typing import Dict, List

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

WEEKLY_SHEET_NAME = "WEEKLY"

# Column configuration
WEEKLY_HEADERS = ["Language", "Week", "Corrected", "Pending", "% Done", "KR Words"]
WEEKLY_WIDTHS = [12, 12, 12, 12, 10, 12]

# Styling
HEADER_FONT = Font(bold=True, size=11)
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT_WHITE = Font(bold=True, size=11, color="FFFFFF")
TITLE_FONT = Font(bold=True, size=14)
THIN_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)


def build_weekly_sheet(wb: Workbook, weekly_data: List[Dict]) -> None:
    """
    Build the WEEKLY sheet with week-over-week progress.

    Args:
        wb: Workbook to add sheet to
        weekly_data: List of dicts from WeeklyDataManager.get_weekly_summary()
    """
    # Create or get sheet
    if WEEKLY_SHEET_NAME in wb.sheetnames:
        del wb[WEEKLY_SHEET_NAME]

    ws = wb.create_sheet(WEEKLY_SHEET_NAME, 0)  # First position

    # Title
    ws.merge_cells('A1:F1')
    title_cell = ws.cell(row=1, column=1, value="WEEKLY CORRECTION PROGRESS")
    title_cell.font = TITLE_FONT
    title_cell.alignment = Alignment(horizontal="center")

    # Headers (row 3)
    header_row = 3
    for col, header in enumerate(WEEKLY_HEADERS, 1):
        cell = ws.cell(row=header_row, column=col, value=header)
        cell.font = HEADER_FONT_WHITE
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER

    # Set column widths
    for col, width in enumerate(WEEKLY_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(col)].width = width

    # Data rows
    if not weekly_data:
        ws.cell(row=4, column=1, value="No data yet. Run 'Prepare For Submit' to collect data.")
        return

    data_row = header_row + 1
    for record in weekly_data:
        ws.cell(row=data_row, column=1, value=record["Language"])
        ws.cell(row=data_row, column=2, value=record["WeekStart"])
        ws.cell(row=data_row, column=3, value=record["Corrected"])
        ws.cell(row=data_row, column=4, value=record["Pending"])

        # % Done with formatting
        pct_cell = ws.cell(row=data_row, column=5, value=record["PercentDone"] / 100)
        pct_cell.number_format = '0.0%'

        ws.cell(row=data_row, column=6, value=record["KRWords"])

        # Apply borders
        for col in range(1, 7):
            ws.cell(row=data_row, column=col).border = THIN_BORDER
            ws.cell(row=data_row, column=col).alignment = Alignment(horizontal="center")

        data_row += 1

    # Freeze header
    ws.freeze_panes = 'A4'

    logger.info(f"Built WEEKLY sheet with {len(weekly_data)} records")
