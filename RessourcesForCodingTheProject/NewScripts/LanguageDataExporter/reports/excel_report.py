"""
Excel Report Writer for Word Count Reports.

Generates styled Excel reports with:
- Sheet per language with category breakdown
- Summary sheet with all languages
- Color-coded headers and totals
- Category colors matching wordcount6.py style
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

from .report_generator import WordCountReport, LanguageReport

logger = logging.getLogger(__name__)

# Import CATEGORY_COLORS from config
try:
    from config import CATEGORY_COLORS
except ImportError:
    # Fallback colors matching wordcount6.py
    CATEGORY_COLORS = {
        "Sequencer": "FFE599",       # light-orange
        "AIDialog": "C6EFCE",        # light-green
        "QuestDialog": "C6EFCE",     # light-green
        "NarrationDialog": "C6EFCE", # light-green
        "Item": "D9D2E9",            # light-purple
        "Quest": "D9D2E9",           # light-purple
        "Character": "F8CBAD",       # light-red/peach
        "Gimmick": "D9D2E9",         # light-purple
        "Skill": "D9D2E9",           # light-purple
        "Knowledge": "D9D2E9",       # light-purple
        "Faction": "D9D2E9",         # light-purple
        "UI": "A9D08E",              # light-teal/green
        "Region": "F8CBAD",          # light-red/peach
        "System_Misc": "D9D9D9",     # light-grey
        "Uncategorized": "DDD9C4",   # light-brown
    }


def _get_category_fill(category: str) -> PatternFill:
    """Get PatternFill for a category based on CATEGORY_COLORS."""
    color = CATEGORY_COLORS.get(category, "FFFFFF")
    return PatternFill(start_color=color, end_color=color, fill_type="solid")

# =============================================================================
# STYLING CONSTANTS
# =============================================================================

# Header styling
HEADER_FONT = Font(bold=True, size=11, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")

# Category headers
CATEGORY_FONT = Font(bold=True, size=10)
CATEGORY_FILL = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")

# Total row styling
TOTAL_FONT = Font(bold=True, size=11)
TOTAL_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

# Data cells
DATA_ALIGNMENT = Alignment(horizontal="right", vertical="center")
CATEGORY_ALIGNMENT = Alignment(horizontal="left", vertical="center")

# Borders
THIN_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

# Untranslated highlighting
UNTRANSLATED_FILL = PatternFill(start_color="FFE0E0", end_color="FFE0E0", fill_type="solid")


class ExcelReportWriter:
    """
    Writes word count reports to styled Excel files.

    Features:
    - Individual sheets per language
    - Summary sheet comparing all languages
    - Color-coded headers, totals, and untranslated counts
    """

    def __init__(self, output_path: Path):
        """
        Initialize Excel report writer.

        Args:
            output_path: Path to output Excel file
        """
        self.output_path = output_path

    def write_report(self, report: WordCountReport) -> bool:
        """
        Write complete word count report to Excel.

        Args:
            report: WordCountReport with all languages

        Returns:
            True if successful, False otherwise
        """
        try:
            wb = Workbook()

            # Remove default sheet
            default_sheet = wb.active
            wb.remove(default_sheet)

            # Create summary sheet first
            self._write_summary_sheet(wb, report)

            # Create sheet for each language
            for lang_code in sorted(report.languages.keys()):
                lang_report = report.languages[lang_code]
                self._write_language_sheet(wb, lang_report, report.get_sorted_categories())

            # Ensure output directory exists
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save workbook
            wb.save(self.output_path)

            logger.info(f"Generated word count report: {self.output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Error writing Excel report: {e}")
            return False

    def _write_summary_sheet(self, wb: Workbook, report: WordCountReport):
        """Write summary sheet with all languages."""
        ws = wb.create_sheet("Summary")

        # Headers
        headers = ["Category", "Strings"] + [
            report.languages[lc].display_name
            for lc in sorted(report.languages.keys())
        ]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = HEADER_ALIGNMENT
            cell.border = THIN_BORDER

        # Data rows
        categories = report.get_sorted_categories()
        row = 2

        for category in categories:
            # Apply category color to entire row
            cat_fill = _get_category_fill(category)

            ws.cell(row=row, column=1, value=category).alignment = CATEGORY_ALIGNMENT
            ws.cell(row=row, column=1).border = THIN_BORDER
            ws.cell(row=row, column=1).fill = cat_fill

            # Get string count from first language
            first_lang = next(iter(report.languages.values()))
            cat_count = first_lang.word_count.categories.get(category)
            strings = cat_count.total_strings if cat_count else 0
            ws.cell(row=row, column=2, value=strings).alignment = DATA_ALIGNMENT
            ws.cell(row=row, column=2).border = THIN_BORDER
            ws.cell(row=row, column=2).fill = cat_fill

            # Language counts
            for col_idx, lang_code in enumerate(sorted(report.languages.keys()), 3):
                lang_report = report.languages[lang_code]
                cat_count = lang_report.word_count.categories.get(category)
                count = cat_count.translation_count if cat_count else 0

                cell = ws.cell(row=row, column=col_idx, value=count)
                cell.alignment = DATA_ALIGNMENT
                cell.border = THIN_BORDER
                cell.number_format = "#,##0"
                cell.fill = cat_fill

            row += 1

        # Total row
        ws.cell(row=row, column=1, value="TOTAL").font = TOTAL_FONT
        ws.cell(row=row, column=1).fill = TOTAL_FILL
        ws.cell(row=row, column=1).border = THIN_BORDER

        ws.cell(row=row, column=2, value=report.total_strings).font = TOTAL_FONT
        ws.cell(row=row, column=2).fill = TOTAL_FILL
        ws.cell(row=row, column=2).border = THIN_BORDER
        ws.cell(row=row, column=2).alignment = DATA_ALIGNMENT

        for col_idx, lang_code in enumerate(sorted(report.languages.keys()), 3):
            lang_report = report.languages[lang_code]
            total = lang_report.word_count.total_translation_count

            cell = ws.cell(row=row, column=col_idx, value=total)
            cell.font = TOTAL_FONT
            cell.fill = TOTAL_FILL
            cell.border = THIN_BORDER
            cell.alignment = DATA_ALIGNMENT
            cell.number_format = "#,##0"

        # Column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 12
        for idx in range(3, len(headers) + 1):
            ws.column_dimensions[get_column_letter(idx)].width = 12

        # Freeze header
        ws.freeze_panes = 'A2'

    def _write_language_sheet(
        self,
        wb: Workbook,
        lang_report: LanguageReport,
        all_categories: List[str]
    ):
        """Write individual language sheet."""
        ws = wb.create_sheet(lang_report.display_name)

        # Headers
        count_label = lang_report.count_type
        headers = ["Category", "Strings", f"Korean Words", f"Translation {count_label}", "Untranslated"]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = HEADER_ALIGNMENT
            cell.border = THIN_BORDER

        # Data rows
        row = 2
        word_count = lang_report.word_count

        for category in all_categories:
            cat_count = word_count.categories.get(category)
            cat_fill = _get_category_fill(category)

            if cat_count:
                ws.cell(row=row, column=1, value=category).alignment = CATEGORY_ALIGNMENT
                ws.cell(row=row, column=2, value=cat_count.total_strings).alignment = DATA_ALIGNMENT
                ws.cell(row=row, column=3, value=cat_count.korean_words).alignment = DATA_ALIGNMENT
                ws.cell(row=row, column=4, value=cat_count.translation_count).alignment = DATA_ALIGNMENT
                ws.cell(row=row, column=5, value=cat_count.untranslated).alignment = DATA_ALIGNMENT

                # Highlight untranslated if > 0 (overrides category color)
                if cat_count.untranslated > 0:
                    ws.cell(row=row, column=5).fill = UNTRANSLATED_FILL
            else:
                ws.cell(row=row, column=1, value=category).alignment = CATEGORY_ALIGNMENT
                for col in range(2, 6):
                    ws.cell(row=row, column=col, value=0).alignment = DATA_ALIGNMENT

            # Apply borders and category colors
            for col in range(1, 6):
                cell = ws.cell(row=row, column=col)
                cell.border = THIN_BORDER
                # Apply category color (except untranslated column if highlighted)
                if col != 5 or (cat_count and cat_count.untranslated == 0) or not cat_count:
                    cell.fill = cat_fill
                if col > 1:
                    cell.number_format = "#,##0"

            row += 1

        # Total row
        ws.cell(row=row, column=1, value="TOTAL").font = TOTAL_FONT
        ws.cell(row=row, column=1).fill = TOTAL_FILL

        totals = [
            word_count.total_strings,
            word_count.total_korean_words,
            word_count.total_translation_count,
            word_count.total_untranslated
        ]

        for col, total in enumerate(totals, 2):
            cell = ws.cell(row=row, column=col, value=total)
            cell.font = TOTAL_FONT
            cell.fill = TOTAL_FILL
            cell.alignment = DATA_ALIGNMENT
            cell.number_format = "#,##0"

            if col == 5 and total > 0:
                cell.fill = UNTRANSLATED_FILL

        # Apply borders to total row
        for col in range(1, 6):
            ws.cell(row=row, column=col).border = THIN_BORDER

        # Column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 12
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 20
        ws.column_dimensions['E'].width = 15

        # Freeze header
        ws.freeze_panes = 'A2'
