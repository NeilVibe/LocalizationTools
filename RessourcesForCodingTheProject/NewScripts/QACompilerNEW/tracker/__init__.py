"""
Tracker Package
===============
Progress tracker modules for QA Compiler.

- data.py: Core tracker operations (_DAILY_DATA sheet)
- daily.py: DAILY sheet builder
- total.py: TOTAL sheet builder with rankings
- coverage.py: Language data coverage analysis
- facial.py: Facial sheet builder (Face-specific QA tracking)
"""

from tracker.data import (
    get_or_create_tracker,
    update_daily_data_sheet,
    read_daily_data,
    compute_daily_deltas,
    DAILY_DATA_HEADERS,
)

from tracker.daily import build_daily_sheet

from tracker.total import build_total_sheet

from tracker.coverage import (
    run_coverage_analysis,
    calculate_coverage,
    load_master_language_data,
    load_voice_recording_sheet,
    CoverageReport,
    CategoryCoverage,
)

from tracker.facial import update_facial_data_sheet, build_facial_sheet

__all__ = [
    # Data operations
    "get_or_create_tracker",
    "update_daily_data_sheet",
    "read_daily_data",
    "compute_daily_deltas",
    "DAILY_DATA_HEADERS",
    # Sheet builders
    "build_daily_sheet",
    "build_total_sheet",
    # Coverage analysis
    "run_coverage_analysis",
    "calculate_coverage",
    "load_master_language_data",
    "load_voice_recording_sheet",
    "CoverageReport",
    "CategoryCoverage",
    # Facial tracking
    "update_facial_data_sheet",
    "build_facial_sheet",
]
