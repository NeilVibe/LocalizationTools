"""
Correction Progress Tracker module.

Tracks LQA correction progress with:
- WEEKLY sheet: Week-over-week progress per language
- TOTAL sheet: Summary tables (per-language, per-category)
- _WEEKLY_DATA sheet: Raw data storage (hidden)

Structure follows QACompiler tracker pattern.
"""

from .data import (
    WeeklyDataManager,
    get_week_start,
    contains_korean,
    is_corrected,
)
from .weekly import build_weekly_sheet
from .total import build_total_sheet
from .tracker import CorrectionTracker

__all__ = [
    "WeeklyDataManager",
    "get_week_start",
    "contains_korean",
    "is_corrected",
    "build_weekly_sheet",
    "build_total_sheet",
    "CorrectionTracker",
]
