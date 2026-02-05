"""
Excel Writer for categorized language data.

Generates Excel files with xlsxwriter, styled with headers and proper column widths.
STORY category strings are ordered by VoiceRecordingSheet EventName for
chronological story order.

Uses xlsxwriter instead of openpyxl for reliable cell protection.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

import xlsxwriter

if TYPE_CHECKING:
    from utils.vrs_ordering import VRSOrderer

# Import Korean detection for Text State column
try:
    from utils.language_utils import contains_korean
except ImportError:
    import re
    _KOREAN_REGEX = re.compile(r'[\uac00-\ud7a3]')
    def contains_korean(text):
        if not text or not isinstance(text, str):
            return False
        return bool(_KOREAN_REGEX.search(text))

logger = logging.getLogger(__name__)

# Import STORY_CATEGORIES from config
try:
    from config import STORY_CATEGORIES
except ImportError:
    STORY_CATEGORIES = ["Sequencer", "AIDialog", "QuestDialog", "NarrationDialog"]

# Column widths
DEFAULT_WIDTHS = {
    "StrOrigin": 45,
    "ENG": 45,
    "Str": 45,
    "Correction": 45,
    "Text State": 12,
    "MEMO1": 30,
    "MEMO2": 30,
    "MEMO3": 30,
    "Category": 20,
    "StringID": 15,
}


def _sort_entries_for_output(
    entries: List[Dict],
    category_index: Dict[str, str],
    default_category: str,
    vrs_orderer: Optional["VRSOrderer"] = None,
    stringid_to_soundevent: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """
    Sort entries for Excel output.

    - STORY categories (Sequencer, AIDialog, QuestDialog, NarrationDialog)
      are sorted by VoiceRecordingSheet EventName for chronological story order
    - Other categories are grouped together alphabetically

    Args:
        entries: Raw language entries
        category_index: {StringID: Category} mapping
        default_category: Fallback category
        vrs_orderer: VRSOrderer for story ordering
        stringid_to_soundevent: {StringID: SoundEventName} mapping

    Returns:
        Sorted list of entries
    """
    if not vrs_orderer or not vrs_orderer.loaded or not stringid_to_soundevent:
        # No VRS ordering available - just sort by category name
        return sorted(entries, key=lambda e: category_index.get(e.get("string_id", ""), default_category))

    # Separate STORY and non-STORY entries
    story_entries = []
    other_entries = []

    for entry in entries:
        string_id = entry.get("string_id", "")
        category = category_index.get(string_id, default_category)

        if category in STORY_CATEGORIES:
            story_entries.append(entry)
        else:
            other_entries.append(entry)

    # Sort STORY entries by VRS order (chronological story order)
    def story_sort_key(entry):
        string_id = entry.get("string_id", "")
        category = category_index.get(string_id, default_category)
        sound_event = stringid_to_soundevent.get(string_id, "")
        vrs_position = vrs_orderer.get_position(sound_event)
        # Sort by: category order, then VRS position
        cat_order = STORY_CATEGORIES.index(category) if category in STORY_CATEGORIES else 999
        return (cat_order, vrs_position)

    sorted_story = sorted(story_entries, key=story_sort_key)

    # Sort other entries by category name
    sorted_other = sorted(other_entries, key=lambda e: category_index.get(e.get("string_id", ""), default_category))

    # STORY entries first, then other categories
    return sorted_story + sorted_other


def write_language_excel(
    lang_code: str,
    lang_data: List[Dict],
    eng_lookup: Dict[str, str],
    category_index: Dict[str, str],
    output_path: Path,
    include_english: bool = True,
    default_category: str = "Uncategorized",
    vrs_orderer: Optional["VRSOrderer"] = None,
    stringid_to_soundevent: Optional[Dict[str, str]] = None,
    excluded_categories: Optional[set] = None,
    protect_sheet: bool = True,
) -> bool:
    """
    Write Excel file for one language using xlsxwriter.

    STORY category strings (Sequencer, AIDialog, QuestDialog, NarrationDialog)
    are sorted by VoiceRecordingSheet EventName for chronological story order.

    Args:
        lang_code: Language code (e.g., "eng", "fre")
        lang_data: List of dicts with str_origin, str, string_id
        eng_lookup: {StringID: English translation} for cross-reference
        category_index: {StringID: Category} mapping
        output_path: Path to output Excel file
        include_english: Whether to include English column
        default_category: Category for unmapped StringIDs
        vrs_orderer: VRSOrderer for story ordering (optional)
        stringid_to_soundevent: {StringID: SoundEventName} mapping (optional)
        excluded_categories: Set of category names to exclude (optional)
        protect_sheet: If True, only Correction column is editable (default: True)

    Returns:
        True if successful, False otherwise

    Column structure:
    - European: StrOrigin | ENG | Str | Correction | Text State | MEMO1 | MEMO2 | MEMO3 | Category | StringID
    - Asian:    StrOrigin | Str | Correction | Text State | MEMO1 | MEMO2 | MEMO3 | Category | StringID

    Text State column:
    - Auto-filled based on Korean detection in Str column
    - "KOREAN" = contains Korean characters (untranslated)
    - "TRANSLATED" = no Korean characters

    Sheet Protection:
    - When protect_sheet=True, only Correction and MEMO1/2/3 columns are EDITABLE
    - All other columns are locked/read-only (including Text State)
    - QA testers can modify Correction and add notes in MEMO columns
    """
    try:
        # Filter out excluded categories BEFORE processing
        if excluded_categories:
            original_count = len(lang_data)
            lang_data = [
                entry for entry in lang_data
                if category_index.get(entry.get('string_id', ''), default_category) not in excluded_categories
            ]
            filtered_count = original_count - len(lang_data)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} entries from excluded categories: {excluded_categories}")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create workbook with xlsxwriter
        workbook = xlsxwriter.Workbook(str(output_path))
        worksheet = workbook.add_worksheet(lang_code.upper())

        # Define headers based on language type
        # New columns: Text State (auto-filled), MEMO1/2/3 (editable)
        if include_english:
            headers = ["StrOrigin", "ENG", "Str", "Correction", "Text State", "MEMO1", "MEMO2", "MEMO3", "Category", "StringID"]
        else:
            headers = ["StrOrigin", "Str", "Correction", "Text State", "MEMO1", "MEMO2", "MEMO3", "Category", "StringID"]

        # Find Correction column index (0-based for xlsxwriter)
        correction_col_idx = headers.index("Correction") if "Correction" in headers else None

        # Find MEMO column indices (these are also editable)
        memo_col_indices = [headers.index(col) for col in ["MEMO1", "MEMO2", "MEMO3"] if col in headers]

        # Create formats
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'bg_color': '#DAEEF3',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'locked': True,
        })

        cell_format_locked = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'text_wrap': True,
            'border': 1,
            'locked': True,
        })

        cell_format_unlocked = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'text_wrap': True,
            'border': 1,
            'locked': False,  # This column is editable
        })

        # String format for StringID (prevent scientific notation)
        string_format_locked = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'border': 1,
            'locked': True,
            'num_format': '@',  # Text format
        })

        # Set column widths
        for col_idx, header in enumerate(headers):
            width = DEFAULT_WIDTHS.get(header, 20)
            worksheet.set_column(col_idx, col_idx, width)

        # Write header row
        for col_idx, header in enumerate(headers):
            worksheet.write(0, col_idx, header, header_format)

        # Sort data: STORY categories by VRS order, others alphabetically by category
        sorted_data = _sort_entries_for_output(
            lang_data,
            category_index,
            default_category,
            vrs_orderer,
            stringid_to_soundevent,
        )

        # Write data rows
        row_num = 1  # Start from row 1 (0 is header)
        for entry in sorted_data:
            string_id = entry.get('string_id', '')
            str_origin = entry.get('str_origin', '')
            str_value = entry.get('str', '')

            # Get category
            category = category_index.get(string_id, default_category)

            # Get English translation if needed
            english = eng_lookup.get(string_id, '') if include_english else None

            # Determine Text State based on Korean content in Str column
            # KOREAN = contains Korean characters (untranslated)
            # TRANSLATED = no Korean characters
            text_state = "KOREAN" if contains_korean(str_value) else "TRANSLATED"

            # Build row data (Correction + MEMO columns empty, to be filled during LQA)
            if include_english:
                row_data = [str_origin, english, str_value, "", text_state, "", "", "", category, string_id]
            else:
                row_data = [str_origin, str_value, "", text_state, "", "", "", category, string_id]

            # Write cells with appropriate format
            for col_idx, value in enumerate(row_data):
                # Determine format based on column
                if col_idx == correction_col_idx or col_idx in memo_col_indices:
                    # Correction and MEMO columns - UNLOCKED (editable)
                    fmt = cell_format_unlocked
                elif headers[col_idx] == "StringID":
                    # StringID - use string format to prevent scientific notation
                    fmt = string_format_locked
                else:
                    # All other columns - LOCKED (including Text State)
                    fmt = cell_format_locked

                worksheet.write(row_num, col_idx, value, fmt)

            row_num += 1

        # Freeze header row
        worksheet.freeze_panes(1, 0)

        # Add auto-filter
        if row_num > 1:
            worksheet.autofilter(0, 0, row_num - 1, len(headers) - 1)

        # Protect sheet - only cells with locked=False can be edited
        if protect_sheet:
            worksheet.protect('', {
                'format_cells': True,
                'format_columns': True,
                'format_rows': True,
                'insert_columns': False,
                'insert_rows': False,
                'insert_hyperlinks': False,
                'delete_columns': False,
                'delete_rows': False,
                'select_locked_cells': True,
                'sort': True,
                'autofilter': True,
                'pivot_tables': False,
                'select_unlocked_cells': True,
            })
            logger.info(f"Sheet protection enabled - editable columns: Correction (col {correction_col_idx}), MEMO1/2/3 (cols {memo_col_indices})")

        workbook.close()

        logger.info(f"Generated {output_path.name} with {row_num - 1} rows")
        return True

    except Exception as e:
        logger.error(f"Error writing Excel for {lang_code}: {e}")
        return False


def write_summary_excel(
    language_stats: Dict[str, Dict],
    category_stats: Dict[str, int],
    output_path: Path
) -> bool:
    """
    Write a summary Excel file with statistics.

    Args:
        language_stats: {lang_code: {"rows": N, "file": "path"}}
        category_stats: {category: count}
        output_path: Path to output Excel file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        workbook = xlsxwriter.Workbook(str(output_path))

        # Header format
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'bg_color': '#DAEEF3',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
        })

        cell_format = workbook.add_format({
            'border': 1,
        })

        # Languages sheet
        ws_lang = workbook.add_worksheet("Languages")

        headers = ["Language", "Rows", "File"]
        ws_lang.set_column(0, 0, 15)
        ws_lang.set_column(1, 1, 10)
        ws_lang.set_column(2, 2, 40)

        for col, header in enumerate(headers):
            ws_lang.write(0, col, header, header_format)

        row = 1
        for lang, stats in sorted(language_stats.items()):
            ws_lang.write(row, 0, lang.upper(), cell_format)
            ws_lang.write(row, 1, stats.get("rows", 0), cell_format)
            ws_lang.write(row, 2, stats.get("file", ""), cell_format)
            row += 1

        # Categories sheet
        ws_cat = workbook.add_worksheet("Categories")

        headers = ["Category", "StringIDs"]
        ws_cat.set_column(0, 0, 25)
        ws_cat.set_column(1, 1, 15)

        for col, header in enumerate(headers):
            ws_cat.write(0, col, header, header_format)

        row = 1
        for category, count in sorted(category_stats.items(), key=lambda x: -x[1]):
            ws_cat.write(row, 0, category, cell_format)
            ws_cat.write(row, 1, count, cell_format)
            row += 1

        workbook.close()

        logger.info(f"Generated summary: {output_path.name}")
        return True

    except Exception as e:
        logger.error(f"Error writing summary Excel: {e}")
        return False
