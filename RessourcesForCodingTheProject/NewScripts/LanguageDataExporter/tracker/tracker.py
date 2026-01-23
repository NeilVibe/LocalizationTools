"""
Main Correction Tracker class.

Orchestrates data collection, storage, and report generation.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable

from openpyxl import Workbook, load_workbook

from .data import WeeklyDataManager, get_week_start
from .weekly import build_weekly_sheet
from .total import build_total_sheet

logger = logging.getLogger(__name__)


class CorrectionTracker:
    """
    Main tracker class for correction progress.

    Usage:
        tracker = CorrectionTracker(tracker_path, categories)
        tracker.update_from_stats(correction_stats)
        tracker.rebuild_report()
    """

    def __init__(self, tracker_path: Path, categories: List[str]):
        """
        Initialize tracker.

        Args:
            tracker_path: Path to Correction_ProgressTracker.xlsx
            categories: List of category names for reports
        """
        self.tracker_path = tracker_path
        self.categories = categories
        self.data_manager = WeeklyDataManager(tracker_path)

    def update_from_stats(
        self,
        correction_stats: Dict[str, Dict[str, Dict]],
        file_mod_times: Optional[Dict[str, datetime]] = None
    ) -> int:
        """
        Update tracker data from correction statistics.

        Args:
            correction_stats: Dict[lang, Dict[category, Dict]] with:
                - corrected: count
                - pending: count
                - kr_words: count
            file_mod_times: Optional dict of {lang: modification_datetime}
                          If not provided, uses current time

        Returns:
            Number of records written
        """
        if not correction_stats:
            logger.warning("No correction stats provided")
            return 0

        # Build records for _WEEKLY_DATA
        records = []
        now = datetime.now()

        for lang, cat_data in correction_stats.items():
            # Determine week start from file mod time or current date
            if file_mod_times and lang in file_mod_times:
                week_start = get_week_start(file_mod_times[lang])
            else:
                week_start = get_week_start(now)

            for category, stats in cat_data.items():
                records.append({
                    "WeekStart": week_start,
                    "Language": lang,
                    "Category": category,
                    "Corrected": stats.get("corrected", 0),
                    "Pending": stats.get("pending", 0),
                    "KRWords": stats.get("kr_words", 0),
                })

        # Write to _WEEKLY_DATA with REPLACE mode
        return self.data_manager.write_data(records)

    def rebuild_report(self) -> bool:
        """
        Rebuild WEEKLY and TOTAL sheets from _WEEKLY_DATA.

        Returns:
            True if successful
        """
        try:
            # Load or create workbook
            if self.tracker_path.exists():
                wb = load_workbook(self.tracker_path)
            else:
                wb = Workbook()
                wb.remove(wb.active)

            # Get data for reports
            weekly_summary = self.data_manager.get_weekly_summary()
            latest_data = self.data_manager.get_latest_week_data()

            # Build sheets
            build_weekly_sheet(wb, weekly_summary)
            build_total_sheet(wb, latest_data, self.categories)

            # Ensure _WEEKLY_DATA exists (for new files)
            self.data_manager._get_or_create_data_sheet(wb)

            # Save
            wb.save(self.tracker_path)

            logger.info(f"Rebuilt tracker report: {self.tracker_path}")
            return True

        except Exception as e:
            logger.error(f"Error rebuilding tracker report: {e}")
            return False

    def update_and_rebuild(
        self,
        correction_stats: Dict[str, Dict[str, Dict]],
        file_mod_times: Optional[Dict[str, datetime]] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> bool:
        """
        Combined update and rebuild operation.

        Args:
            correction_stats: Stats from collect_correction_stats()
            file_mod_times: Optional file modification times
            progress_callback: Optional progress callback

        Returns:
            True if successful
        """
        try:
            if progress_callback:
                progress_callback(10, "Updating tracker data...")

            written = self.update_from_stats(correction_stats, file_mod_times)

            if progress_callback:
                progress_callback(50, f"Wrote {written} records, rebuilding report...")

            success = self.rebuild_report()

            if progress_callback:
                status = "Tracker updated" if success else "Tracker update failed"
                progress_callback(100, status)

            return success

        except Exception as e:
            logger.error(f"Error in update_and_rebuild: {e}")
            if progress_callback:
                progress_callback(100, f"Error: {e}")
            return False

    def get_summary_text(self) -> str:
        """
        Get a text summary of current tracker state.

        Returns:
            Multi-line summary string
        """
        latest = self.data_manager.get_latest_week_data()
        if not latest:
            return "No data in tracker yet."

        lines = ["=== CORRECTION PROGRESS SUMMARY ===", ""]

        for lang in sorted(latest.keys()):
            cat_data = latest[lang]
            total_corrected = sum(c.get("Corrected", 0) for c in cat_data.values())
            total_pending = sum(c.get("Pending", 0) for c in cat_data.values())
            total = total_corrected + total_pending
            pct = (total_corrected / total * 100) if total > 0 else 0

            lines.append(f"{lang}: {total_corrected:,}/{total:,} ({pct:.1f}% complete)")

        return "\n".join(lines)
