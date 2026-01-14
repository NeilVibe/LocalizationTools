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
    korean_word_count: int = 0
    translation_word_count: int = 0
    sub_categories: List["CategoryCoverage"] = field(default_factory=list)


@dataclass
class CoverageReport:
    """Complete coverage report."""
    categories: List[CategoryCoverage] = field(default_factory=list)
    total_master_strings: int = 0
    total_master_korean_words: int = 0
    total_master_translation_words: int = 0
    total_covered_strings: int = 0
    total_covered_korean_words: int = 0
    total_covered_translation_words: int = 0


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

def load_master_language_data(language_folder: Path) -> Tuple[Set[str], int, Dict[str, str], int]:
    """
    Load all StrOrigin values and their translations from language data file.

    Args:
        language_folder: Path to stringtable/loc folder

    Returns:
        Tuple of (set of normalized StrOrigin strings, korean word count,
                  dict of korean->translation, translation word count)
    """
    log.info("Loading master language data from: %s", language_folder)

    master_strings: Set[str] = set()
    translations: Dict[str, str] = {}

    if not language_folder.exists():
        log.error("Language folder not found: %s", language_folder)
        return master_strings, 0, translations, 0

    # Find the first languagedata_*.xml file (prefer eng)
    lang_files = sorted(language_folder.glob("languagedata_*.xml"))
    if not lang_files:
        log.error("No language data files found")
        return master_strings, 0, translations, 0

    # Prefer English if available, otherwise use first
    target_file = None
    for f in lang_files:
        if "eng" in f.stem.lower():
            target_file = f
            break
    if target_file is None:
        target_file = lang_files[0]

    log.info("Using language file: %s", target_file.name)

    # Parse and extract StrOrigin values and translations
    root = parse_xml_file(target_file)
    if root is None:
        log.error("Failed to parse language file")
        return master_strings, 0, translations, 0

    for loc in root.iter("LocStr"):
        origin = loc.get("StrOrigin") or ""
        translation = loc.get("StrValue") or ""
        if origin:
            normalized = normalize_placeholders(origin)
            if normalized:
                master_strings.add(normalized)
                if translation:
                    translations[normalized] = translation

    korean_words = count_words_in_set(master_strings)
    translation_words = sum(count_korean_words(t) for t in translations.values())
    log.info("Loaded %d unique StrOrigin strings (%d KR words, %d TR words)",
             len(master_strings), korean_words, translation_words)

    return master_strings, korean_words, translations, translation_words


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
# LOAD FROM EXISTING GENERATED DATASHEETS
# =============================================================================

# Map folder names to category names (EXACT names from generators)
FOLDER_TO_CATEGORY = {
    "Character_LQA_All": "Character",
    "QuestData_Map_All": "Quest",
    "ItemData_Map_All": "Item",
    "Knowledge_LQA_All": "Knowledge",
    "Skill_LQA_All": "Skill",
    "Region_LQA_v3": "Region",
    "Gimmick_LQA_Output": "Gimmick",
    "GameAdvice_LQA_All": "Help",
}


def load_korean_strings_from_datasheets(datasheet_folder: Path) -> Dict[str, Set[str]]:
    """
    Load Korean strings from existing generated datasheet Excel files.

    Scans GeneratedDatasheets folder for category subfolders and reads
    column A (Original KR) from each Excel file.

    Args:
        datasheet_folder: Path to GeneratedDatasheets folder

    Returns:
        Dict mapping category name to set of Korean strings
    """
    log.info("Loading Korean strings from existing datasheets: %s", datasheet_folder)

    category_strings: Dict[str, Set[str]] = {}

    if not datasheet_folder.exists():
        log.error("Datasheet folder not found: %s", datasheet_folder)
        return category_strings

    # Scan for category subfolders
    for subfolder in sorted(datasheet_folder.iterdir()):
        if not subfolder.is_dir():
            continue

        folder_name = subfolder.name
        category = FOLDER_TO_CATEGORY.get(folder_name)

        if not category:
            # Try to extract category from folder name pattern
            if "_LQA_" in folder_name:
                category = folder_name.split("_LQA_")[0]
            else:
                continue

        log.info("  Scanning %s -> %s", folder_name, category)

        korean_strings: Set[str] = set()

        # Find Excel files (prefer ENG version for consistency)
        excel_files = list(subfolder.glob("*_ENG.xlsx"))
        if not excel_files:
            excel_files = list(subfolder.glob("*.xlsx"))

        if not excel_files:
            log.warning("    No Excel files found in %s", folder_name)
            continue

        # Use first file found
        excel_file = excel_files[0]
        log.info("    Reading: %s", excel_file.name)

        try:
            wb = load_workbook(excel_file, read_only=True, data_only=True)

            for sheet in wb.worksheets:
                # Read column A (Original KR) starting from row 2
                for row in sheet.iter_rows(min_row=2, max_col=1, values_only=True):
                    if row and row[0]:
                        text = str(row[0]).strip()
                        if text:
                            normalized = normalize_placeholders(text)
                            if normalized:
                                korean_strings.add(normalized)

            wb.close()

        except Exception as e:
            log.error("    Failed to read %s: %s", excel_file.name, e)
            continue

        if korean_strings:
            category_strings[category] = korean_strings
            log.info("    Loaded %d Korean strings for %s", len(korean_strings), category)

    log.info("Loaded %d categories from existing datasheets", len(category_strings))
    return category_strings


# =============================================================================
# COVERAGE CALCULATION
# =============================================================================

def calculate_coverage(
    master_strings: Set[str],
    master_korean_words: int,
    master_translation_words: int,
    translations: Dict[str, str],
    category_strings: Dict[str, Set[str]],
    voice_sheet_strings: Optional[Set[str]] = None,
) -> CoverageReport:
    """
    Calculate coverage using the consume technique.

    Each Korean string is consumed once (no double counting).
    Categories are processed in a defined order.

    Args:
        master_strings: Set of all normalized StrOrigin from language data
        master_korean_words: Total Korean word count in master data
        master_translation_words: Total translation word count in master data
        translations: Dict mapping Korean text to translation text
        category_strings: Dict mapping category name to set of Korean strings
        voice_sheet_strings: Optional set of strings from VoiceRecordingSheet

    Returns:
        CoverageReport with per-category and total statistics
    """
    log.info("Calculating coverage with consume technique...")

    report = CoverageReport(
        total_master_strings=len(master_strings),
        total_master_korean_words=master_korean_words,
        total_master_translation_words=master_translation_words,
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

        korean_words = count_words_in_set(consumed)
        translation_words = sum(count_korean_words(translations.get(s, "")) for s in consumed)

        cat_coverage = CategoryCoverage(
            name=category_name,
            unique_strings=len(consumed),
            korean_word_count=korean_words,
            translation_word_count=translation_words,
        )

        # Special handling for Quest: add voice sheet as sub-category
        if category_name == "Quest" and voice_sheet_strings:
            voice_consumed = voice_sheet_strings & remaining
            remaining -= voice_consumed
            voice_korean_words = count_words_in_set(voice_consumed)
            voice_translation_words = sum(count_korean_words(translations.get(s, "")) for s in voice_consumed)

            voice_coverage = CategoryCoverage(
                name="Voice Sheet",
                unique_strings=len(voice_consumed),
                korean_word_count=voice_korean_words,
                translation_word_count=voice_translation_words,
            )
            cat_coverage.sub_categories.append(voice_coverage)

            # Add to totals
            report.total_covered_strings += len(voice_consumed)
            report.total_covered_korean_words += voice_korean_words
            report.total_covered_translation_words += voice_translation_words

        report.categories.append(cat_coverage)
        report.total_covered_strings += len(consumed)
        report.total_covered_korean_words += korean_words
        report.total_covered_translation_words += translation_words

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
    print(f"{'Category':<20} {'Unique Strings':>15} {'Korean Words':>15} {'% Coverage':>12}")
    print("-" * width)

    # Per-category stats
    for cat in report.categories:
        pct = (cat.unique_strings / report.total_master_strings * 100) if report.total_master_strings > 0 else 0
        print(f"{cat.name:<20} {cat.unique_strings:>15,} {cat.korean_word_count:>15,} {pct:>11.1f}%")

        # Sub-categories (indented)
        for sub in cat.sub_categories:
            sub_pct = (sub.unique_strings / report.total_master_strings * 100) if report.total_master_strings > 0 else 0
            print(f"  {'└─ ' + sub.name:<17} {sub.unique_strings:>15,} {sub.korean_word_count:>15,} {sub_pct:>11.1f}%")

    print()
    print("=" * width)

    # Total coverage
    string_pct = (report.total_covered_strings / report.total_master_strings * 100) if report.total_master_strings > 0 else 0
    kr_word_pct = (report.total_covered_korean_words / report.total_master_korean_words * 100) if report.total_master_korean_words > 0 else 0

    print(f"TOTAL COVERAGE:  {report.total_covered_strings:,} / {report.total_master_strings:,} strings ({string_pct:.1f}%)")
    print(f"                 {report.total_covered_korean_words:,} / {report.total_master_korean_words:,} Korean words ({kr_word_pct:.1f}%)")
    print("=" * width)
    print()

    # === ADDITIONAL TABLE: Word Counts (Korean vs Translation) ===
    print()
    print("=" * width)
    print("                    WORD COUNT BY CATEGORY")
    print("=" * width)
    print()
    print(f"{'Category':<20} {'Korean Words':>18} {'Translation Words':>18}")
    print("-" * width)

    total_kr = 0
    total_tr = 0

    for cat in report.categories:
        print(f"{cat.name:<20} {cat.korean_word_count:>18,} {cat.translation_word_count:>18,}")
        total_kr += cat.korean_word_count
        total_tr += cat.translation_word_count

        # Sub-categories (indented)
        for sub in cat.sub_categories:
            print(f"  {'└─ ' + sub.name:<17} {sub.korean_word_count:>18,} {sub.translation_word_count:>18,}")
            total_kr += sub.korean_word_count
            total_tr += sub.translation_word_count

    print("-" * width)
    print(f"{'TOTAL':<20} {total_kr:>18,} {total_tr:>18,}")
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
    # 1. Load master language data (now includes translations)
    master_strings, korean_words, translations, translation_words = load_master_language_data(language_folder)

    if not master_strings:
        log.error("No master language data loaded - cannot calculate coverage")
        return CoverageReport()

    # 2. Load voice recording sheet
    voice_strings = load_voice_recording_sheet(voice_sheet_folder)

    # 3. Calculate coverage
    report = calculate_coverage(
        master_strings,
        korean_words,
        translation_words,
        translations,
        category_strings,
        voice_strings,
    )

    # 4. Print report
    print_coverage_report(report)

    return report
