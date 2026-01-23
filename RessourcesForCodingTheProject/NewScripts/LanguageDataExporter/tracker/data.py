"""
Weekly Data Manager for Correction Progress Tracker.

Handles _WEEKLY_DATA sheet with REPLACE mode to prevent duplicates.
Key = (week_start, language, category) - same key overwrites existing row.
"""

import re
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

logger = logging.getLogger(__name__)

# _WEEKLY_DATA schema
DATA_SHEET_NAME = "_WEEKLY_DATA"
DATA_HEADERS = [
    "WeekStart",      # Monday date (YYYY-MM-DD)
    "Language",       # Language code (ENG, FRE, etc.)
    "Category",       # Category name
    "Corrected",      # Count of corrected strings
    "Pending",        # Count of pending strings
    "KRWords",        # Korean word count
    "Timestamp",      # When this record was written
]


def get_week_start(date: datetime) -> str:
    """
    Convert date to week start (Monday) in YYYY-MM-DD format.

    Args:
        date: Any datetime

    Returns:
        String date of that week's Monday (YYYY-MM-DD)
    """
    monday = date - timedelta(days=date.weekday())
    return monday.strftime("%Y-%m-%d")


def contains_korean(text: str) -> bool:
    """Check if text contains Korean characters (Hangul)."""
    if not text:
        return False
    korean_pattern = re.compile(r'[\uAC00-\uD7AF]')
    return bool(korean_pattern.search(str(text)))


def is_corrected(str_origin: str, str_value: str) -> bool:
    """
    Determine if a string has been corrected.

    Corrected = Str differs from StrOrigin AND has no Korean.

    Args:
        str_origin: Original Korean string
        str_value: Current translated string

    Returns:
        True if the string appears to be corrected
    """
    if not str_value or str_value == str_origin:
        return False
    return not contains_korean(str_value)


class WeeklyDataManager:
    """
    Manages _WEEKLY_DATA sheet with REPLACE mode.

    Key: (week_start, language, category)
    Same key overwrites existing row instead of appending.
    """

    def __init__(self, tracker_path: Path):
        """
        Initialize with tracker file path.

        Args:
            tracker_path: Path to Correction_ProgressTracker.xlsx
        """
        self.tracker_path = tracker_path

    def _get_or_create_workbook(self) -> Workbook:
        """Load existing workbook or create new one."""
        if self.tracker_path.exists():
            return load_workbook(self.tracker_path)
        else:
            wb = Workbook()
            # Remove default sheet, we'll create our own
            wb.remove(wb.active)
            return wb

    def _get_or_create_data_sheet(self, wb: Workbook):
        """Get or create _WEEKLY_DATA sheet with headers."""
        if DATA_SHEET_NAME in wb.sheetnames:
            return wb[DATA_SHEET_NAME]

        # Create sheet at the end
        ws = wb.create_sheet(DATA_SHEET_NAME)

        # Write headers
        for col, header in enumerate(DATA_HEADERS, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)

        # Hide the sheet (raw data)
        ws.sheet_state = 'hidden'

        return ws

    def _build_key_index(self, ws) -> Dict[Tuple[str, str, str], int]:
        """
        Build index of existing rows by key.

        Returns:
            Dict mapping (week_start, language, category) to row number
        """
        index = {}
        for row in range(2, ws.max_row + 1):
            week_start = ws.cell(row=row, column=1).value
            language = ws.cell(row=row, column=2).value
            category = ws.cell(row=row, column=3).value
            if week_start and language and category:
                index[(str(week_start), str(language), str(category))] = row
        return index

    def write_data(self, records: List[Dict]) -> int:
        """
        Write records to _WEEKLY_DATA with REPLACE mode.

        Args:
            records: List of dicts with keys matching DATA_HEADERS

        Returns:
            Number of records written/updated
        """
        if not records:
            return 0

        wb = self._get_or_create_workbook()
        ws = self._get_or_create_data_sheet(wb)

        # Build key index for REPLACE mode
        key_index = self._build_key_index(ws)

        # Find next available row for new records
        next_row = ws.max_row + 1 if ws.max_row > 1 else 2

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        written = 0

        for record in records:
            week_start = str(record.get("WeekStart", ""))
            language = str(record.get("Language", ""))
            category = str(record.get("Category", ""))

            if not all([week_start, language, category]):
                continue

            key = (week_start, language, category)

            # REPLACE mode: use existing row or new row
            if key in key_index:
                row = key_index[key]
            else:
                row = next_row
                next_row += 1

            # Write record
            ws.cell(row=row, column=1, value=week_start)
            ws.cell(row=row, column=2, value=language)
            ws.cell(row=row, column=3, value=category)
            ws.cell(row=row, column=4, value=record.get("Corrected", 0))
            ws.cell(row=row, column=5, value=record.get("Pending", 0))
            ws.cell(row=row, column=6, value=record.get("KRWords", 0))
            ws.cell(row=row, column=7, value=timestamp)

            written += 1

        # Save and close workbook
        self.tracker_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(self.tracker_path)
        wb.close()

        logger.info(f"Wrote {written} records to {DATA_SHEET_NAME}")
        return written

    def read_all_data(self) -> List[Dict]:
        """
        Read all records from _WEEKLY_DATA.

        Returns:
            List of dicts with keys matching DATA_HEADERS
        """
        if not self.tracker_path.exists():
            return []

        wb = load_workbook(self.tracker_path, read_only=True)

        if DATA_SHEET_NAME not in wb.sheetnames:
            wb.close()
            return []

        ws = wb[DATA_SHEET_NAME]
        records = []

        for row in range(2, ws.max_row + 1):
            record = {
                "WeekStart": ws.cell(row=row, column=1).value,
                "Language": ws.cell(row=row, column=2).value,
                "Category": ws.cell(row=row, column=3).value,
                "Corrected": ws.cell(row=row, column=4).value or 0,
                "Pending": ws.cell(row=row, column=5).value or 0,
                "KRWords": ws.cell(row=row, column=6).value or 0,
                "Timestamp": ws.cell(row=row, column=7).value,
            }
            if record["WeekStart"] and record["Language"]:
                records.append(record)

        wb.close()
        return records

    def get_latest_week_data(self) -> Dict[str, Dict[str, Dict]]:
        """
        Get data for the most recent week only.

        Returns:
            Dict[language, Dict[category, Dict]] with latest week data
        """
        all_data = self.read_all_data()
        if not all_data:
            return {}

        # Find latest week
        weeks = set(r["WeekStart"] for r in all_data)
        if not weeks:
            return {}
        latest_week = max(weeks)

        # Filter to latest week
        result = {}
        for record in all_data:
            if record["WeekStart"] != latest_week:
                continue

            lang = record["Language"]
            cat = record["Category"]

            if lang not in result:
                result[lang] = {}

            result[lang][cat] = {
                "Corrected": record["Corrected"],
                "Pending": record["Pending"],
                "KRWords": record["KRWords"],
            }

        return result

    def get_weekly_summary(self) -> List[Dict]:
        """
        Get week-by-week summary aggregated by language.

        Returns:
            List of dicts with: WeekStart, Language, Corrected, Pending, PercentDone, KRWords
        """
        all_data = self.read_all_data()
        if not all_data:
            return []

        # Aggregate by (week, language)
        aggregated = {}
        for record in all_data:
            key = (record["WeekStart"], record["Language"])
            if key not in aggregated:
                aggregated[key] = {"Corrected": 0, "Pending": 0, "KRWords": 0}

            aggregated[key]["Corrected"] += record["Corrected"]
            aggregated[key]["Pending"] += record["Pending"]
            aggregated[key]["KRWords"] += record["KRWords"]

        # Build summary list
        summary = []
        for (week, lang), data in sorted(aggregated.items()):
            total = data["Corrected"] + data["Pending"]
            pct_done = (data["Corrected"] / total * 100) if total > 0 else 0

            summary.append({
                "WeekStart": week,
                "Language": lang,
                "Corrected": data["Corrected"],
                "Pending": data["Pending"],
                "PercentDone": round(pct_done, 1),
                "KRWords": data["KRWords"],
            })

        return summary
