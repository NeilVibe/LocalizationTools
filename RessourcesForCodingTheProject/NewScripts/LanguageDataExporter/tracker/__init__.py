"""
Correction Progress Tracker module.

Tracks LQA merge results with:
- WEEKLY sheet: Week-over-week merge results per language (Corrections, Success, Fail)
- TOTAL sheet: Summary per language with Success %
- _WEEKLY_DATA sheet: Raw data storage (hidden)

Structure follows QACompiler tracker pattern.
"""

from .data import (
    WeeklyDataManager,
    get_week_start,
)
from .weekly import build_weekly_sheet
from .total import build_total_sheet
from .tracker import CorrectionTracker

__all__ = [
    "WeeklyDataManager",
    "get_week_start",
    "build_weekly_sheet",
    "build_total_sheet",
    "CorrectionTracker",
]
