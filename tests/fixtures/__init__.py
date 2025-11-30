"""
Test Fixtures - Mock Data for LocaNext Apps

Provides comprehensive mock data based on real language data file structures
for use in testing XLSTransfer, QuickSearch, KR Similar, and future apps.

Data Format (Tab-Separated):
- Column 0: Category ID (e.g., 39, 18)
- Column 1: File ID (e.g., 7924197, 8504)
- Column 2: String ID (e.g., 1824, 26)
- Column 3: Unknown (typically 0)
- Column 4: Unknown (typically sequence number)
- Column 5: Korean text (with code markers like {ChangeScene()}, {AudioVoice()})
- Column 6: Translation (English, French, etc.)
- Column 7+: Additional metadata (notes, etc.)
"""

import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent


def get_fixture_path(filename: str) -> str:
    """Get full path to a fixture file."""
    return str(FIXTURES_DIR / filename)


def get_sample_language_data() -> str:
    """Get path to sample language data file."""
    return get_fixture_path("sample_language_data.txt")


def get_sample_excel() -> str:
    """Get path to sample Excel file."""
    return get_fixture_path("sample_data.xlsx")
