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
from datetime import datetime
from typing import Dict, Set, Tuple, Optional, List
from dataclasses import dataclass, field

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from lxml import etree as ET

from generators.base import normalize_placeholders, parse_xml_file, get_logger
from config import EXPORT_LOOKAT_FOLDER, EXPORT_QUEST_FOLDER

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
# LOAD ADDITIONAL STRINGS FROM EXPORT FOLDERS
# =============================================================================

def load_export_string_ids(export_folder: Path) -> Set[str]:
    """
    Load StringIds from export XML files.

    These are strings inherently tested but not in the Excel datasheets.
    We collect StringIds to later map them to LOC ENG for word counts.

    Args:
        export_folder: Path to export subfolder (e.g., System/LookAt)

    Returns:
        Set of StringIds found in export XML files
    """
    log.info("Loading StringIds from export folder: %s", export_folder)

    string_ids: Set[str] = set()

    if not export_folder.exists():
        log.warning("Export folder not found: %s", export_folder)
        return string_ids

    # Find all XML files in the folder
    xml_files = list(export_folder.rglob("*.xml"))
    if not xml_files:
        log.warning("No XML files found in %s", export_folder)
        return string_ids

    for xml_file in xml_files:
        try:
            root = parse_xml_file(xml_file)
            if root is None:
                continue

            for loc in root.iter("LocStr"):
                sid = loc.get("StringId")
                if sid:
                    string_ids.add(sid)

        except Exception as e:
            log.error("Failed to parse %s: %s", xml_file.name, e)

    log.info("Loaded %d StringIds from export folder", len(string_ids))
    return string_ids


def map_string_ids_to_master(
    string_ids: Set[str],
    language_folder: Path,
) -> Tuple[Set[str], Dict[str, str]]:
    """
    Map StringIds from export to master language data (LOC ENG).

    Reads the LOC ENG file and finds matching StringIds to get Korean text.

    Args:
        string_ids: Set of StringIds to look up
        language_folder: Path to stringtable/loc folder

    Returns:
        Tuple of (set of Korean strings, dict of Korean->Translation)
    """
    log.info("Mapping %d StringIds to master language data", len(string_ids))

    korean_strings: Set[str] = set()
    translations: Dict[str, str] = {}

    if not language_folder.exists():
        log.error("Language folder not found: %s", language_folder)
        return korean_strings, translations

    # Find ENG language file
    lang_files = sorted(language_folder.glob("languagedata_*.xml"))
    target_file = None
    for f in lang_files:
        if "eng" in f.stem.lower():
            target_file = f
            break
    if target_file is None and lang_files:
        target_file = lang_files[0]

    if target_file is None:
        log.error("No language data file found")
        return korean_strings, translations

    log.info("Using language file: %s", target_file.name)

    # Parse and find matching StringIds
    root = parse_xml_file(target_file)
    if root is None:
        return korean_strings, translations

    for loc in root.iter("LocStr"):
        sid = loc.get("StringId")
        if sid and sid in string_ids:
            origin = loc.get("StrOrigin") or ""
            translation = loc.get("StrValue") or ""
            if origin:
                normalized = normalize_placeholders(origin)
                if normalized:
                    korean_strings.add(normalized)
                    if translation:
                        translations[normalized] = translation

    log.info("Mapped %d StringIds to Korean strings", len(korean_strings))
    return korean_strings, translations


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

        # Find Excel files RECURSIVELY (some generators have nested subfolders)
        # Prefer ENG version for consistency
        excel_files = list(subfolder.rglob("*_ENG.xlsx"))
        if not excel_files:
            excel_files = list(subfolder.rglob("*.xlsx"))

        if not excel_files:
            log.warning("    No Excel files found in %s", folder_name)
            continue

        # Use first file found
        excel_file = excel_files[0]
        log.info("    Reading: %s", excel_file.name)

        try:
            wb = load_workbook(excel_file, read_only=True, data_only=True)

            for sheet in wb.worksheets:
                # Find Korean columns from header row
                # Look for: "Original (KR)", "(KOR)", or column A as fallback
                korean_cols = []
                header_row = None
                for row in sheet.iter_rows(min_row=1, max_row=1, values_only=True):
                    header_row = row
                    break

                if header_row:
                    for idx, header in enumerate(header_row):
                        if header:
                            h = str(header).strip()
                            # Match Korean columns based on exact generator patterns:
                            # - Quest: "Original"
                            # - Character/Knowledge/Skill/Region/Help: "Original (KR)"
                            # - Item/Gimmick: columns ending with "(KOR)"
                            if h == "Original" or h == "Original (KR)" or "(KOR)" in h:
                                korean_cols.append(idx)

                # Fallback to column A if no Korean columns found
                if not korean_cols:
                    korean_cols = [0]

                # Read data from Korean columns
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if not row:
                        continue
                    for col_idx in korean_cols:
                        if col_idx < len(row) and row[col_idx]:
                            text = str(row[col_idx]).strip()
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
    item_additional_strings: Optional[Set[str]] = None,
    item_additional_translations: Optional[Dict[str, str]] = None,
    quest_additional_strings: Optional[Set[str]] = None,
    quest_additional_translations: Optional[Dict[str, str]] = None,
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
        item_additional_strings: Optional set of strings from export/System/LookAt
        item_additional_translations: Optional translations for LookAt strings
        quest_additional_strings: Optional set of strings from export/System/Quest
        quest_additional_translations: Optional translations for Quest export strings

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

        # Special handling for Quest: add voice sheet and System/Quest as sub-categories
        if category_name == "Quest":
            # Voice Sheet sub-category
            if voice_sheet_strings:
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

            # Additional: System/Quest export (inherent testing data)
            if quest_additional_strings:
                quest_add_consumed = quest_additional_strings & remaining
                remaining -= quest_add_consumed
                quest_add_korean_words = count_words_in_set(quest_add_consumed)
                quest_add_trans = quest_additional_translations or {}
                quest_add_translation_words = sum(count_korean_words(quest_add_trans.get(s, "")) for s in quest_add_consumed)

                quest_add_coverage = CategoryCoverage(
                    name="Additional (System/Quest)",
                    unique_strings=len(quest_add_consumed),
                    korean_word_count=quest_add_korean_words,
                    translation_word_count=quest_add_translation_words,
                )
                cat_coverage.sub_categories.append(quest_add_coverage)

                # Add to totals
                report.total_covered_strings += len(quest_add_consumed)
                report.total_covered_korean_words += quest_add_korean_words
                report.total_covered_translation_words += quest_add_translation_words

        # Special handling for Item: add LookAt as sub-category
        if category_name == "Item" and item_additional_strings:
            item_add_consumed = item_additional_strings & remaining
            remaining -= item_add_consumed
            item_add_korean_words = count_words_in_set(item_add_consumed)
            item_add_trans = item_additional_translations or {}
            item_add_translation_words = sum(count_korean_words(item_add_trans.get(s, "")) for s in item_add_consumed)

            item_add_coverage = CategoryCoverage(
                name="Additional (LookAt)",
                unique_strings=len(item_add_consumed),
                korean_word_count=item_add_korean_words,
                translation_word_count=item_add_translation_words,
            )
            cat_coverage.sub_categories.append(item_add_coverage)

            # Add to totals
            report.total_covered_strings += len(item_add_consumed)
            report.total_covered_korean_words += item_add_korean_words
            report.total_covered_translation_words += item_add_translation_words

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
    print(f"{'Category':<30} {'Korean Words':>18} {'Translation Words':>18}")
    print("-" * width)

    total_kr = 0
    total_tr = 0

    for cat in report.categories:
        # Calculate category total (main + all sub-categories)
        cat_total_kr = cat.korean_word_count
        cat_total_tr = cat.translation_word_count
        for sub in cat.sub_categories:
            cat_total_kr += sub.korean_word_count
            cat_total_tr += sub.translation_word_count

        # Show category with TOTAL if it has sub-categories
        if cat.sub_categories:
            print(f"{cat.name + ' (TOTAL)':<30} {cat_total_kr:>18,} {cat_total_tr:>18,}")
            # Show main category detail
            print(f"  {'├─ ' + cat.name + ' (main)':<27} {cat.korean_word_count:>18,} {cat.translation_word_count:>18,}")
            # Show sub-categories
            for i, sub in enumerate(cat.sub_categories):
                prefix = "└─" if i == len(cat.sub_categories) - 1 else "├─"
                print(f"  {prefix + ' ' + sub.name:<27} {sub.korean_word_count:>18,} {sub.translation_word_count:>18,}")
        else:
            # No sub-categories, just show the category
            print(f"{cat.name:<30} {cat.korean_word_count:>18,} {cat.translation_word_count:>18,}")

        total_kr += cat_total_kr
        total_tr += cat_total_tr

    print("-" * width)
    print(f"{'GRAND TOTAL':<30} {total_kr:>18,} {total_tr:>18,}")
    print("=" * width)
    print()


# =============================================================================
# EXCEL EXPORT
# =============================================================================

# Style definitions
HEADER_FILL = PatternFill("solid", fgColor="4472C4")
HEADER_FONT = Font(bold=True, color="FFFFFF")
TOTAL_FILL = PatternFill("solid", fgColor="FFF2CC")
SUBTOTAL_FILL = PatternFill("solid", fgColor="E2EFDA")
SUB_ITEM_FILL = PatternFill("solid", fgColor="F2F2F2")
THIN_BORDER = Border(
    left=Side(style='thin', color='B4B4B4'),
    right=Side(style='thin', color='B4B4B4'),
    top=Side(style='thin', color='B4B4B4'),
    bottom=Side(style='thin', color='B4B4B4')
)


def style_header_row(ws, row: int, headers: List[str], widths: List[int] = None):
    """Apply header styling to a row."""
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row, col, header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = THIN_BORDER
        cell.alignment = Alignment(horizontal='center')
        if widths and col <= len(widths):
            ws.column_dimensions[cell.column_letter].width = widths[col - 1]


def export_coverage_to_excel(report: CoverageReport, output_folder: Path = None) -> Path:
    """
    Export coverage report to a clean Excel file.

    Creates multiple sheets:
    - Coverage Summary: Overall coverage statistics
    - Word Count by Category: Korean and Translation word counts

    Args:
        report: CoverageReport with all statistics
        output_folder: Optional output folder (defaults to current directory)

    Returns:
        Path to the generated Excel file
    """
    wb = Workbook()

    # =========================================================================
    # SHEET 1: Coverage Summary
    # =========================================================================
    ws1 = wb.active
    ws1.title = "Coverage Summary"

    # Title
    ws1.cell(1, 1, "LANGUAGE DATA COVERAGE REPORT").font = Font(bold=True, size=14)
    ws1.cell(2, 1, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    ws1.merge_cells('A1:D1')
    ws1.merge_cells('A2:D2')

    # Headers
    headers = ["Category", "Unique Strings", "Korean Words", "Coverage %"]
    widths = [30, 18, 18, 15]
    style_header_row(ws1, 4, headers, widths)

    row = 5
    for cat in report.categories:
        # Category row
        pct = (cat.unique_strings / report.total_master_strings * 100) if report.total_master_strings > 0 else 0
        ws1.cell(row, 1, cat.name).border = THIN_BORDER
        ws1.cell(row, 2, cat.unique_strings).border = THIN_BORDER
        ws1.cell(row, 3, cat.korean_word_count).border = THIN_BORDER
        ws1.cell(row, 4, f"{pct:.1f}%").border = THIN_BORDER
        ws1.cell(row, 2).number_format = '#,##0'
        ws1.cell(row, 3).number_format = '#,##0'
        row += 1

        # Sub-categories
        for sub in cat.sub_categories:
            sub_pct = (sub.unique_strings / report.total_master_strings * 100) if report.total_master_strings > 0 else 0
            cell = ws1.cell(row, 1, f"  └─ {sub.name}")
            cell.border = THIN_BORDER
            cell.fill = SUB_ITEM_FILL
            for col in [2, 3, 4]:
                ws1.cell(row, col).fill = SUB_ITEM_FILL
                ws1.cell(row, col).border = THIN_BORDER
            ws1.cell(row, 2, sub.unique_strings).number_format = '#,##0'
            ws1.cell(row, 3, sub.korean_word_count).number_format = '#,##0'
            ws1.cell(row, 4, f"{sub_pct:.1f}%")
            row += 1

    # Total row
    row += 1
    string_pct = (report.total_covered_strings / report.total_master_strings * 100) if report.total_master_strings > 0 else 0
    for col in range(1, 5):
        ws1.cell(row, col).fill = TOTAL_FILL
        ws1.cell(row, col).border = THIN_BORDER
        ws1.cell(row, col).font = Font(bold=True)
    ws1.cell(row, 1, "TOTAL COVERED")
    ws1.cell(row, 2, report.total_covered_strings).number_format = '#,##0'
    ws1.cell(row, 3, report.total_covered_korean_words).number_format = '#,##0'
    ws1.cell(row, 4, f"{string_pct:.1f}%")

    row += 1
    for col in range(1, 5):
        ws1.cell(row, col).fill = TOTAL_FILL
        ws1.cell(row, col).border = THIN_BORDER
        ws1.cell(row, col).font = Font(bold=True)
    ws1.cell(row, 1, "MASTER TOTAL")
    ws1.cell(row, 2, report.total_master_strings).number_format = '#,##0'
    ws1.cell(row, 3, report.total_master_korean_words).number_format = '#,##0'
    ws1.cell(row, 4, "100%")

    # =========================================================================
    # SHEET 2: Word Count by Category
    # =========================================================================
    ws2 = wb.create_sheet("Word Count by Category")

    # Title
    ws2.cell(1, 1, "WORD COUNT BY CATEGORY").font = Font(bold=True, size=14)
    ws2.cell(2, 1, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    ws2.merge_cells('A1:C1')
    ws2.merge_cells('A2:C2')

    # Headers
    headers = ["Category", "Korean Words", "Translation Words"]
    widths = [35, 20, 20]
    style_header_row(ws2, 4, headers, widths)

    row = 5
    grand_total_kr = 0
    grand_total_tr = 0

    for cat in report.categories:
        # Calculate category total (main + sub-categories)
        cat_total_kr = cat.korean_word_count
        cat_total_tr = cat.translation_word_count
        for sub in cat.sub_categories:
            cat_total_kr += sub.korean_word_count
            cat_total_tr += sub.translation_word_count

        if cat.sub_categories:
            # Category TOTAL row (highlighted)
            for col in range(1, 4):
                ws2.cell(row, col).fill = SUBTOTAL_FILL
                ws2.cell(row, col).border = THIN_BORDER
                ws2.cell(row, col).font = Font(bold=True)
            ws2.cell(row, 1, f"{cat.name} (TOTAL)")
            ws2.cell(row, 2, cat_total_kr).number_format = '#,##0'
            ws2.cell(row, 3, cat_total_tr).number_format = '#,##0'
            row += 1

            # Main category detail
            ws2.cell(row, 1, f"  ├─ {cat.name} (main)").border = THIN_BORDER
            ws2.cell(row, 1).fill = SUB_ITEM_FILL
            ws2.cell(row, 2, cat.korean_word_count).number_format = '#,##0'
            ws2.cell(row, 2).border = THIN_BORDER
            ws2.cell(row, 2).fill = SUB_ITEM_FILL
            ws2.cell(row, 3, cat.translation_word_count).number_format = '#,##0'
            ws2.cell(row, 3).border = THIN_BORDER
            ws2.cell(row, 3).fill = SUB_ITEM_FILL
            row += 1

            # Sub-categories
            for i, sub in enumerate(cat.sub_categories):
                prefix = "└─" if i == len(cat.sub_categories) - 1 else "├─"
                ws2.cell(row, 1, f"  {prefix} {sub.name}").border = THIN_BORDER
                ws2.cell(row, 1).fill = SUB_ITEM_FILL
                ws2.cell(row, 2, sub.korean_word_count).number_format = '#,##0'
                ws2.cell(row, 2).border = THIN_BORDER
                ws2.cell(row, 2).fill = SUB_ITEM_FILL
                ws2.cell(row, 3, sub.translation_word_count).number_format = '#,##0'
                ws2.cell(row, 3).border = THIN_BORDER
                ws2.cell(row, 3).fill = SUB_ITEM_FILL
                row += 1
        else:
            # Simple category (no sub-categories)
            ws2.cell(row, 1, cat.name).border = THIN_BORDER
            ws2.cell(row, 2, cat.korean_word_count).number_format = '#,##0'
            ws2.cell(row, 2).border = THIN_BORDER
            ws2.cell(row, 3, cat.translation_word_count).number_format = '#,##0'
            ws2.cell(row, 3).border = THIN_BORDER
            row += 1

        grand_total_kr += cat_total_kr
        grand_total_tr += cat_total_tr

    # Grand Total row
    row += 1
    for col in range(1, 4):
        ws2.cell(row, col).fill = TOTAL_FILL
        ws2.cell(row, col).border = THIN_BORDER
        ws2.cell(row, col).font = Font(bold=True)
    ws2.cell(row, 1, "GRAND TOTAL")
    ws2.cell(row, 2, grand_total_kr).number_format = '#,##0'
    ws2.cell(row, 3, grand_total_tr).number_format = '#,##0'

    # =========================================================================
    # Save workbook
    # =========================================================================
    if output_folder is None:
        output_folder = Path.cwd()
    output_folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_folder / f"Coverage_Report_{timestamp}.xlsx"
    wb.save(output_file)

    log.info("Excel report saved: %s", output_file)
    return output_file


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

    # 3. Load additional export data (inherent testing data not in Excel)
    # Item: LookAt folder
    lookat_string_ids = load_export_string_ids(EXPORT_LOOKAT_FOLDER)
    item_additional_strings, item_additional_translations = map_string_ids_to_master(
        lookat_string_ids, language_folder
    )

    # Quest: System/Quest folder
    quest_export_string_ids = load_export_string_ids(EXPORT_QUEST_FOLDER)
    quest_additional_strings, quest_additional_translations = map_string_ids_to_master(
        quest_export_string_ids, language_folder
    )

    # 4. Calculate coverage
    report = calculate_coverage(
        master_strings,
        korean_words,
        translation_words,
        translations,
        category_strings,
        voice_strings,
        item_additional_strings,
        item_additional_translations,
        quest_additional_strings,
        quest_additional_translations,
    )

    # 5. Print report to terminal
    print_coverage_report(report)

    # 6. Export to Excel
    excel_path = export_coverage_to_excel(report)
    print(f"\n📊 Excel report saved: {excel_path}\n")

    return report
