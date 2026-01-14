"""
Language Data Coverage Tracker
==============================
Calculates coverage of language data by generated QA datasheets.

Features:
- Loads master language data (StrOrigin from languagedata_*.xml)
- Consumes Korean strings from each generator category
- Calculates word counts (Korean whitespace-separated tokens)
- Generates terminal report
"""

import re
from pathlib import Path
from typing import Dict, Set, Tuple, Optional, List
from dataclasses import dataclass, field

from openpyxl import load_workbook
from lxml import etree as ET

from generators.base import normalize_placeholders, parse_xml_file, get_logger

log = get_logger("CoverageTracker")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class CategoryCoverage:
    """Coverage statistics for a single category."""
    name: str
    unique_strings: int = 0
    word_count: int = 0
    sub_categories: List["CategoryCoverage"] = field(default_factory=list)


@dataclass
class CoverageReport:
    """Complete coverage report."""
    categories: List[CategoryCoverage] = field(default_factory=list)
    total_master_strings: int = 0
    total_master_words: int = 0
    total_covered_strings: int = 0
    total_covered_words: int = 0


# =============================================================================
# KOREAN WORD COUNT CALCULATION
# =============================================================================

def count_korean_words(text: str) -> int:
    """
    Count words in Korean text.

    Korean uses spaces between word-phrases (어절).
    We use whitespace-separated token count.
    """
    if not text:
        return 0

    # Split by whitespace
    tokens = text.split()
    if tokens:
        return len(tokens)

    # If no whitespace (single word), count as 1
    return 1 if text.strip() else 0


def count_words_in_set(strings: Set[str]) -> int:
    """Count total words in a set of strings."""
    return sum(count_korean_words(s) for s in strings)


# =============================================================================
# MASTER LANGUAGE DATA LOADING
# =============================================================================

def load_master_language_data(language_folder: Path) -> Tuple[Set[str], int]:
    """
    Load all StrOrigin values from the first language data file.

    Args:
        language_folder: Path to stringtable/loc folder

    Returns:
        Tuple of (set of normalized StrOrigin strings, total word count)
    """
    log.info("Loading master language data from: %s", language_folder)

    master_strings: Set[str] = set()

    if not language_folder.exists():
        log.error("Language folder not found: %s", language_folder)
        return master_strings, 0

    # Find the first languagedata_*.xml file (prefer eng)
    lang_files = sorted(language_folder.glob("languagedata_*.xml"))
    if not lang_files:
        log.error("No language data files found")
        return master_strings, 0

    # Prefer English if available, otherwise use first
    target_file = None
    for f in lang_files:
        if "eng" in f.stem.lower():
            target_file = f
            break
    if target_file is None:
        target_file = lang_files[0]

    log.info("Using language file: %s", target_file.name)

    # Parse and extract StrOrigin values
    root = parse_xml_file(target_file)
    if root is None:
        log.error("Failed to parse language file")
        return master_strings, 0

    for loc in root.iter("LocStr"):
        origin = loc.get("StrOrigin") or ""
        if origin:
            normalized = normalize_placeholders(origin)
            if normalized:
                master_strings.add(normalized)

    total_words = count_words_in_set(master_strings)
    log.info("Loaded %d unique StrOrigin strings (%d words)",
             len(master_strings), total_words)

    return master_strings, total_words


# =============================================================================
# VOICE RECORDING SHEET LOADING
# =============================================================================

def load_voice_recording_sheet(folder: Path) -> Set[str]:
    """
    Load StrOrigin values from the most recent VoiceRecordingSheet Excel file.

    Args:
        folder: Path to VoiceRecordingSheet__ folder

    Returns:
        Set of normalized StrOrigin strings
    """
    log.info("Loading VoiceRecordingSheet from: %s", folder)

    voice_strings: Set[str] = set()

    if not folder.exists():
        log.warning("VoiceRecordingSheet folder not found: %s", folder)
        return voice_strings

    # Find the most recent Excel file
    excel_files = sorted(folder.glob("*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not excel_files:
        log.warning("No Excel files found in VoiceRecordingSheet folder")
        return voice_strings

    target_file = excel_files[0]
    log.info("Using VoiceRecordingSheet: %s", target_file.name)

    try:
        wb = load_workbook(target_file, read_only=True, data_only=True)

        for sheet in wb.worksheets:
            # Find StrOrigin column in header row
            header_row = None
            for row in sheet.iter_rows(min_row=1, max_row=1, values_only=True):
                header_row = row
                break

            if header_row is None:
                continue

            str_origin_col = None
            for idx, header in enumerate(header_row):
                if header and "StrOrigin" in str(header):
                    str_origin_col = idx
                    break

            if str_origin_col is None:
                continue

            # Read StrOrigin values
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if len(row) > str_origin_col:
                    value = row[str_origin_col]
                    if value:
                        normalized = normalize_placeholders(str(value))
                        if normalized:
                            voice_strings.add(normalized)

        wb.close()

    except Exception as e:
        log.error("Failed to load VoiceRecordingSheet: %s", e)

    log.info("Loaded %d StrOrigin strings from VoiceRecordingSheet", len(voice_strings))
    return voice_strings


# =============================================================================
# COVERAGE CALCULATION
# =============================================================================

def calculate_coverage(
    master_strings: Set[str],
    master_word_count: int,
    category_strings: Dict[str, Set[str]],
    voice_sheet_strings: Optional[Set[str]] = None,
) -> CoverageReport:
    """
    Calculate coverage using the consume technique.

    Each Korean string is consumed once (no double counting).
    Categories are processed in a defined order.

    Args:
        master_strings: Set of all normalized StrOrigin from language data
        master_word_count: Total word count in master data
        category_strings: Dict mapping category name to set of Korean strings
        voice_sheet_strings: Optional set of strings from VoiceRecordingSheet

    Returns:
        CoverageReport with per-category and total statistics
    """
    log.info("Calculating coverage with consume technique...")

    report = CoverageReport(
        total_master_strings=len(master_strings),
        total_master_words=master_word_count,
    )

    # Create a working copy to consume from
    remaining = master_strings.copy()

    # Define processing order
    category_order = [
        "Character",
        "Quest",
        "Item",
        "Knowledge",
        "Skill",
        "Region",
        "Gimmick",
        "Help",
    ]

    for category_name in category_order:
        if category_name not in category_strings:
            continue

        cat_strings = category_strings[category_name]

        # Consume: intersection with remaining
        consumed = cat_strings & remaining
        remaining -= consumed

        word_count = count_words_in_set(consumed)

        cat_coverage = CategoryCoverage(
            name=category_name,
            unique_strings=len(consumed),
            word_count=word_count,
        )

        # Special handling for Quest: add voice sheet as sub-category
        if category_name == "Quest" and voice_sheet_strings:
            voice_consumed = voice_sheet_strings & remaining
            remaining -= voice_consumed
            voice_word_count = count_words_in_set(voice_consumed)

            voice_coverage = CategoryCoverage(
                name="Voice Sheet",
                unique_strings=len(voice_consumed),
                word_count=voice_word_count,
            )
            cat_coverage.sub_categories.append(voice_coverage)

            # Add to totals
            report.total_covered_strings += len(voice_consumed)
            report.total_covered_words += voice_word_count

        report.categories.append(cat_coverage)
        report.total_covered_strings += len(consumed)
        report.total_covered_words += word_count

    return report


# =============================================================================
# TERMINAL REPORT GENERATION
# =============================================================================

def print_coverage_report(report: CoverageReport) -> None:
    """
    Print formatted coverage report to terminal.

    Args:
        report: CoverageReport with all statistics
    """
    width = 75

    print()
    print("=" * width)
    print("                    LANGUAGE DATA COVERAGE REPORT")
    print("=" * width)
    print()

    # Header
    print(f"{'Category':<20} {'Unique Strings':>15} {'Words Covered':>15} {'% Coverage':>12}")
    print("-" * width)

    # Per-category stats
    for cat in report.categories:
        pct = (cat.unique_strings / report.total_master_strings * 100) if report.total_master_strings > 0 else 0
        print(f"{cat.name:<20} {cat.unique_strings:>15,} {cat.word_count:>15,} {pct:>11.1f}%")

        # Sub-categories (indented)
        for sub in cat.sub_categories:
            sub_pct = (sub.unique_strings / report.total_master_strings * 100) if report.total_master_strings > 0 else 0
            print(f"  {'└─ ' + sub.name:<17} {sub.unique_strings:>15,} {sub.word_count:>15,} {sub_pct:>11.1f}%")

    print()
    print("=" * width)

    # Total coverage
    string_pct = (report.total_covered_strings / report.total_master_strings * 100) if report.total_master_strings > 0 else 0
    word_pct = (report.total_covered_words / report.total_master_words * 100) if report.total_master_words > 0 else 0

    print(f"TOTAL COVERAGE:  {report.total_covered_strings:,} / {report.total_master_strings:,} strings ({string_pct:.1f}%)")
    print(f"                 {report.total_covered_words:,} / {report.total_master_words:,} words ({word_pct:.1f}%)")
    print("=" * width)
    print()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def run_coverage_analysis(
    language_folder: Path,
    voice_sheet_folder: Path,
    category_strings: Dict[str, Set[str]],
) -> CoverageReport:
    """
    Run complete coverage analysis and print report.

    Args:
        language_folder: Path to stringtable/loc folder
        voice_sheet_folder: Path to VoiceRecordingSheet__ folder
        category_strings: Dict mapping category name to set of Korean strings

    Returns:
        CoverageReport
    """
    # 1. Load master language data
    master_strings, master_word_count = load_master_language_data(language_folder)

    if not master_strings:
        log.error("No master language data loaded - cannot calculate coverage")
        return CoverageReport()

    # 2. Load voice recording sheet
    voice_strings = load_voice_recording_sheet(voice_sheet_folder)

    # 3. Calculate coverage
    report = calculate_coverage(
        master_strings,
        master_word_count,
        category_strings,
        voice_strings,
    )

    # 4. Print report
    print_coverage_report(report)

    return report
