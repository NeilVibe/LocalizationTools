"""
Matching Module
===============
Shared content-based row matching logic for QA files.

Used by:
- transfer.py: Transfer data from OLD to NEW structure
- processing.py: Match QA rows to Master rows during build

Matching Strategy by Category:
- Standard (Quest, Knowledge, etc.): STRINGID + Translation, fallback to Translation only
- Item: ItemName + ItemDesc + STRINGID, fallback to ItemName + ItemDesc
- Contents: INSTRUCTIONS column (no fallback needed, unique identifier)
- Script (Sequencer/Dialog): Translation + EventName, fallback to EventName only
"""

from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TRANSLATION_COLS, ITEM_DESC_COLS, SCRIPT_COLS, SCRIPT_TYPE_CATEGORIES
from core.excel_ops import find_column_by_header


# =============================================================================
# GRANULAR DEBUG LOGGING
# =============================================================================

_MATCH_LOG_FILE = Path(__file__).parent.parent / "MATCHING_DEBUG.log"
_MATCH_LOG_ENABLED = True  # Set to False to disable verbose logging
_MATCH_LOG_LINES = []  # Buffer for batch writing


def _match_log(msg: str, level: str = "INFO"):
    """Add message to match log buffer."""
    if not _MATCH_LOG_ENABLED:
        return
    timestamp = datetime.now().strftime("%H:%M:%S")
    _MATCH_LOG_LINES.append(f"[{timestamp}] [{level}] {msg}")


def _match_log_flush(header: str = None):
    """Flush log buffer to file."""
    global _MATCH_LOG_LINES
    if not _MATCH_LOG_LINES:
        return
    try:
        mode = "a" if _MATCH_LOG_FILE.exists() else "w"
        with open(_MATCH_LOG_FILE, mode, encoding="utf-8") as f:
            if header:
                f.write(f"\n{'='*60}\n{header}\n{'='*60}\n")
            f.write("\n".join(_MATCH_LOG_LINES) + "\n")
        _MATCH_LOG_LINES = []
    except Exception as e:
        print(f"[MATCH LOG ERROR] {e}")


def _match_log_clear():
    """Clear log file for fresh run."""
    global _MATCH_LOG_LINES
    _MATCH_LOG_LINES = []
    try:
        with open(_MATCH_LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"=== MATCHING DEBUG LOG === {datetime.now().isoformat()}\n\n")
    except:
        pass


# =============================================================================
# STRINGID NORMALIZATION
# =============================================================================

def sanitize_stringid_for_match(value) -> str:
    """
    Normalize STRINGID for comparison.

    Handles:
    - None values
    - INT vs STRING type mismatch
    - Scientific notation (e.g., "1.23E+15")
    - Leading/trailing whitespace
    """
    if value is None:
        return ""
    s = str(value).strip()
    # Handle scientific notation
    if 'e' in s.lower():
        try:
            s = str(int(float(s)))
        except (ValueError, OverflowError):
            pass
    return s


# =============================================================================
# COLUMN DETECTION
# =============================================================================

def get_translation_column(category: str, is_english: bool) -> int:
    """
    Get translation column index based on category and language.

    NOTE: For Script-type categories (Sequencer/Dialog), use get_translation_column_by_name()
    instead, which finds the "Text" column by header name.

    Args:
        category: Category name
        is_english: True for English files

    Returns:
        Column index (1-based)
    """
    cols = TRANSLATION_COLS.get(category, {"eng": 2, "other": 3})
    return cols["eng"] if is_english else cols["other"]


def get_translation_column_by_name(ws, category: str) -> int:
    """
    Get translation column index by searching for column header name.

    For Script-type categories (Sequencer/Dialog), finds "Text" or "Translation" column.
    NO position-based fallback for Script categories.

    Args:
        ws: Worksheet to search
        category: Category name

    Returns:
        Column index (1-based), or None if not found
    """
    category_lower = category.lower()

    if category_lower in SCRIPT_TYPE_CATEGORIES:
        # Script-type: try "Text" first, then "Translation" (case-insensitive)
        text_col = find_column_by_header(ws, "Text")
        if text_col:
            return text_col
        # Fallback to "Translation"
        trans_col = find_column_by_header(ws, "Translation")
        return trans_col

    # Other categories: not implemented (use position-based)
    return None


def get_item_desc_column(is_english: bool) -> int:
    """
    Get ItemDesc column index for Item category.

    Args:
        is_english: True for English files

    Returns:
        Column index (1-based)
    """
    return ITEM_DESC_COLS["eng"] if is_english else ITEM_DESC_COLS["other"]


# =============================================================================
# ROW DATA EXTRACTION
# =============================================================================

def extract_qa_row_data(qa_ws, row: int, category: str, is_english: bool, column_cache: Dict = None) -> Dict:
    """
    Extract matching key data from a QA worksheet row.

    Args:
        qa_ws: QA worksheet
        row: Row number (1-based)
        category: Category name
        is_english: Whether file is English
        column_cache: Optional dict from build_column_map() for O(1) header lookups.
                      When None (default), falls back to find_column_by_header() per call.

    Returns:
        Dict with extracted data for matching
    """
    # Use cache for O(1) column lookup, or fall back to linear scan
    if column_cache is not None:
        stringid_col = column_cache.get("STRINGID")
    else:
        stringid_col = find_column_by_header(qa_ws, "STRINGID")
    stringid = sanitize_stringid_for_match(qa_ws.cell(row, stringid_col).value) if stringid_col else ""

    category_lower = category.lower()

    if category_lower == "contents":
        # Contents: use INSTRUCTIONS column (always col 2)
        instructions = str(qa_ws.cell(row, 2).value or "").strip()
        return {
            "instructions": instructions,
            "stringid": stringid,
            "row": row,
        }

    elif category_lower == "item":
        # Item: use ItemName + ItemDesc
        name_col = get_translation_column(category, is_english)
        desc_col = get_item_desc_column(is_english)
        item_name = str(qa_ws.cell(row, name_col).value or "").strip()
        item_desc = str(qa_ws.cell(row, desc_col).value or "").strip()
        return {
            "item_name": item_name,
            "item_desc": item_desc,
            "stringid": stringid,
            "row": row,
        }

    elif category_lower in SCRIPT_TYPE_CATEGORIES:
        # Sequencer/Dialog: use Translation (Text or Translation) + EventName
        # EventName is PRIMARY identifier - try EventName first, then STRINGID
        # Use NAME-based detection ONLY (no position fallback!)

        # Translation column: try "Text" first, then "Translation"
        if column_cache is not None:
            trans_col = column_cache.get("TEXT") or column_cache.get("TRANSLATION")
        else:
            trans_col = get_translation_column_by_name(qa_ws, category)
        translation = str(qa_ws.cell(row, trans_col).value or "").strip() if trans_col else ""

        # EventName column: primary identifier for Script
        if column_cache is not None:
            eventname_col = column_cache.get("EVENTNAME")
        else:
            eventname_col = find_column_by_header(qa_ws, "EventName")
        eventname = ""
        if eventname_col:
            eventname = str(qa_ws.cell(row, eventname_col).value or "").strip()

        # For Script: EventName is primary, STRINGID is fallback
        if eventname:
            stringid = eventname
        # stringid already set from STRINGID column lookup above (fallback)

        return {
            "translation": translation,
            "eventname": eventname,
            "stringid": stringid,
            "row": row,
        }

    else:
        # Standard: use Translation
        trans_col = get_translation_column(category, is_english)
        translation = str(qa_ws.cell(row, trans_col).value or "").strip()
        return {
            "translation": translation,
            "stringid": stringid,
            "row": row,
        }


# =============================================================================
# MASTER INDEX BUILDING
# =============================================================================

def build_master_index(master_ws, category: str, is_english: bool) -> Dict:
    """
    Build O(1) lookup index for master worksheet.

    This enables efficient content-based matching during compilation.

    Args:
        master_ws: Master worksheet
        category: Category name
        is_english: Whether file is English

    Returns:
        Dict with:
            - "primary": {key: row_num} for exact match
            - "fallback": {key: [row_nums]} for fallback match
            - "consumed": set() to track used rows (prevent duplicates)

    The index structure varies by category:
    - Standard: primary=(stringid, trans), fallback=trans
    - Item: primary=(name, desc, stringid), fallback=(name, desc)
    - Contents: primary=instructions (no fallback)
    - Script: primary=(translation, eventname), fallback=eventname
    """
    category_lower = category.lower()
    stringid_col = find_column_by_header(master_ws, "STRINGID")

    # GRANULAR DEBUG: Log index building start
    _match_log(f"BUILD INDEX: category={category}, is_english={is_english}, max_row={master_ws.max_row}")
    _match_log(f"  STRINGID column found: {stringid_col}")

    index = {
        "primary": {},
        "fallback": defaultdict(list),
        "consumed": set(),
    }

    if category_lower == "contents":
        # Contents: index by INSTRUCTIONS (col 2)
        for row in range(2, master_ws.max_row + 1):
            instructions = str(master_ws.cell(row, 2).value or "").strip()
            if instructions and instructions not in index["primary"]:
                index["primary"][instructions] = row

    elif category_lower == "item":
        # Item: index by (ItemName, ItemDesc, STRINGID) and (ItemName, ItemDesc)
        name_col = get_translation_column(category, is_english)
        desc_col = get_item_desc_column(is_english)

        for row in range(2, master_ws.max_row + 1):
            stringid = sanitize_stringid_for_match(master_ws.cell(row, stringid_col).value) if stringid_col else ""
            item_name = str(master_ws.cell(row, name_col).value or "").strip()
            item_desc = str(master_ws.cell(row, desc_col).value or "").strip()

            if item_name:
                # Primary: name + desc + stringid
                if stringid:
                    key = (item_name, item_desc, stringid)
                    if key not in index["primary"]:
                        index["primary"][key] = row

                # Fallback: name + desc only
                fallback_key = (item_name, item_desc)
                index["fallback"][fallback_key].append(row)

    elif category_lower in SCRIPT_TYPE_CATEGORIES:
        # Sequencer/Dialog: index by (Translation, EventName) with EventName-only fallback
        # DIFFERENT from standard: Fallback is EventName ONLY, not Translation only
        # Use NAME-based detection ONLY (no position fallback!)
        trans_col = get_translation_column_by_name(master_ws, category)
        eventname_col = find_column_by_header(master_ws, "EventName")

        for row in range(2, master_ws.max_row + 1):
            # For Script: EventName is primary, STRINGID is fallback
            eventname = ""
            if eventname_col:
                eventname = str(master_ws.cell(row, eventname_col).value or "").strip()
            stringid = eventname if eventname else (sanitize_stringid_for_match(master_ws.cell(row, stringid_col).value) if stringid_col else "")
            translation = str(master_ws.cell(row, trans_col).value or "").strip() if trans_col else ""

            # Primary: translation + eventname (both must match)
            if translation and eventname:
                key = (translation, eventname)
                if key not in index["primary"]:
                    index["primary"][key] = row

            # Fallback: EventName ONLY (NOT translation only!)
            if eventname:
                index["fallback"][eventname].append(row)

    else:
        # Standard: index by (STRINGID, Translation) and Translation only
        trans_col = get_translation_column(category, is_english)

        for row in range(2, master_ws.max_row + 1):
            stringid = sanitize_stringid_for_match(master_ws.cell(row, stringid_col).value) if stringid_col else ""
            translation = str(master_ws.cell(row, trans_col).value or "").strip()

            if translation:
                # Primary: stringid + trans
                if stringid:
                    key = (stringid, translation)
                    if key not in index["primary"]:
                        index["primary"][key] = row

                # Fallback: trans only
                index["fallback"][translation].append(row)

    # GRANULAR DEBUG: Log index summary
    _match_log(f"  INDEX BUILT: primary_keys={len(index['primary'])}, fallback_keys={len(index['fallback'])}")
    if len(index['primary']) == 0:
        _match_log(f"  WARNING: No primary keys indexed! Matching will fail.", "WARN")
    # Sample first 3 primary keys for debugging
    sample_keys = list(index['primary'].keys())[:3]
    _match_log(f"  Sample primary keys: {sample_keys}")
    _match_log_flush(f"INDEX: {category}")

    return index


def find_matching_row_in_master(
    qa_row_data: Dict,
    master_index: Dict,
    category: str,
    log_failures: bool = True
) -> Tuple[Optional[int], Optional[str]]:
    """
    Find matching master row using 2-step cascade.

    Args:
        qa_row_data: Dict from extract_qa_row_data()
        master_index: Dict from build_master_index()
        category: Category name
        log_failures: If True, log detailed info for unmatched rows

    Returns:
        Tuple of (row_num, match_type) or (None, None) if no match
        match_type: "exact" (primary match) or "fallback"
    """
    category_lower = category.lower()
    consumed = master_index["consumed"]
    qa_row_num = qa_row_data.get("row", "?")

    if category_lower == "contents":
        # Contents: match by INSTRUCTIONS
        instructions = qa_row_data.get("instructions", "")
        if instructions and instructions in master_index["primary"]:
            row = master_index["primary"][instructions]
            if row not in consumed:
                consumed.add(row)
                return row, "exact"
        if log_failures:
            _match_log(f"UNMATCHED QA row {qa_row_num}: instructions='{instructions[:50]}...' not in index", "MISS")
        return None, None

    elif category_lower == "item":
        # Item: try name + desc + stringid first
        item_name = qa_row_data.get("item_name", "")
        item_desc = qa_row_data.get("item_desc", "")
        stringid = qa_row_data.get("stringid", "")

        # Primary: name + desc + stringid
        if stringid and item_name:
            key = (item_name, item_desc, stringid)
            if key in master_index["primary"]:
                row = master_index["primary"][key]
                if row not in consumed:
                    consumed.add(row)
                    return row, "exact"

        # Fallback: name + desc only
        if item_name:
            key = (item_name, item_desc)
            if key in master_index["fallback"]:
                for row in master_index["fallback"][key]:
                    if row not in consumed:
                        consumed.add(row)
                        return row, "fallback"

        if log_failures:
            _match_log(f"UNMATCHED QA row {qa_row_num}: item_name='{item_name[:30] if item_name else ''}', item_desc='{item_desc[:30] if item_desc else ''}', stringid='{stringid}'", "MISS")
        return None, None

    elif category_lower in SCRIPT_TYPE_CATEGORIES:
        # Sequencer/Dialog: try translation + eventname first, then EventName ONLY fallback
        translation = qa_row_data.get("translation", "")
        eventname = qa_row_data.get("eventname", "")
        stringid = qa_row_data.get("stringid", "")
        # Use EventName as fallback key if available
        if not eventname and stringid:
            eventname = stringid

        # Primary: translation + eventname (both must match)
        if translation and eventname:
            key = (translation, eventname)
            if key in master_index["primary"]:
                row = master_index["primary"][key]
                if row not in consumed:
                    consumed.add(row)
                    return row, "exact"

        # Fallback: EventName ONLY (NOT translation only!)
        if eventname and eventname in master_index["fallback"]:
            for row in master_index["fallback"][eventname]:
                if row not in consumed:
                    consumed.add(row)
                    return row, "fallback"

        if log_failures:
            _match_log(f"UNMATCHED QA row {qa_row_num}: eventname='{eventname}', translation='{translation[:40] if translation else ''}...'", "MISS")
        return None, None

    else:
        # Standard: try stringid + trans first
        translation = qa_row_data.get("translation", "")
        stringid = qa_row_data.get("stringid", "")

        # Primary: stringid + trans
        if stringid and translation:
            key = (stringid, translation)
            if key in master_index["primary"]:
                row = master_index["primary"][key]
                if row not in consumed:
                    consumed.add(row)
                    return row, "exact"

        # Fallback: trans only
        if translation and translation in master_index["fallback"]:
            for row in master_index["fallback"][translation]:
                if row not in consumed:
                    consumed.add(row)
                    return row, "fallback"

        if log_failures:
            _match_log(f"UNMATCHED QA row {qa_row_num}: stringid='{stringid}', translation='{translation[:40] if translation else ''}...'", "MISS")
        return None, None


# =============================================================================
# LEGACY FUNCTIONS (for transfer.py compatibility)
# =============================================================================

def find_matching_row_for_transfer(
    old_row_data: Dict,
    new_ws,
    category: str,
    is_english: bool
) -> Tuple[Optional[int], Optional[str]]:
    """
    Find matching row in NEW file for OLD row data.

    Uses 2-step cascade:
    1. STRINGID + Translation match (exact)
    2. Translation only match (fallback)

    Args:
        old_row_data: dict with {stringid, translation, row_num}
        new_ws: New worksheet to search in
        category: Category name for column detection
        is_english: Whether file is English

    Returns:
        Tuple of (new_row_num, match_type) or (None, None)
        match_type: "stringid+trans" or "trans_only"
    """
    old_stringid = sanitize_stringid_for_match(old_row_data.get("stringid"))
    old_trans = str(old_row_data.get("translation", "")).strip()

    if not old_trans:
        return None, None

    trans_col = get_translation_column(category, is_english)
    stringid_col = find_column_by_header(new_ws, "STRINGID")

    # Step 1: Try STRINGID + Translation match
    if old_stringid and stringid_col:
        for row in range(2, new_ws.max_row + 1):
            new_stringid = sanitize_stringid_for_match(new_ws.cell(row, stringid_col).value)
            new_trans = str(new_ws.cell(row, trans_col).value or "").strip()

            if new_stringid == old_stringid and new_trans == old_trans:
                return row, "stringid+trans"

    # Step 2: Fall back to Translation only
    for row in range(2, new_ws.max_row + 1):
        new_trans = str(new_ws.cell(row, trans_col).value or "").strip()
        if new_trans == old_trans:
            return row, "trans_only"

    return None, None


def find_matching_row_for_contents_transfer(
    old_row_data: Dict,
    new_ws
) -> Tuple[Optional[int], Optional[str]]:
    """
    Contents-specific matching: uses INSTRUCTIONS column (col 2) as unique identifier.

    Contents has no localization - just direct row matching by INSTRUCTIONS value.

    Args:
        old_row_data: dict with {instructions, row_num}
        new_ws: New worksheet to search in

    Returns:
        Tuple of (new_row_num, match_type) or (None, None)
        match_type: "instructions"
    """
    old_instructions = str(old_row_data.get("instructions", "")).strip()

    if not old_instructions:
        return None, None

    instructions_col = 2  # INSTRUCTIONS is always column 2 for Contents

    for row in range(2, new_ws.max_row + 1):
        new_instructions = str(new_ws.cell(row, instructions_col).value or "").strip()
        if new_instructions == old_instructions:
            return row, "instructions"

    return None, None


def find_matching_row_for_item_transfer(
    old_row_data: Dict,
    new_ws,
    is_english: bool
) -> Tuple[Optional[int], Optional[str]]:
    """
    Item-specific matching: requires BOTH ItemName AND ItemDesc to match.

    Uses 2-step cascade:
    1. ItemName + ItemDesc + STRINGID (all 3 must match)
    2. ItemName + ItemDesc (both must match, no STRINGID required)

    Args:
        old_row_data: dict with {item_name, item_desc, stringid, row_num}
        new_ws: New worksheet to search in
        is_english: Whether file is English

    Returns:
        Tuple of (new_row_num, match_type) or (None, None)
        match_type: "name+desc+stringid" or "name+desc"
    """
    old_stringid = sanitize_stringid_for_match(old_row_data.get("stringid"))
    old_item_name = str(old_row_data.get("item_name", "")).strip()
    old_item_desc = str(old_row_data.get("item_desc", "")).strip()

    # Need at least ItemName to match
    if not old_item_name:
        return None, None

    name_col = TRANSLATION_COLS["Item"]["eng"] if is_english else TRANSLATION_COLS["Item"]["other"]
    desc_col = ITEM_DESC_COLS["eng"] if is_english else ITEM_DESC_COLS["other"]
    stringid_col = find_column_by_header(new_ws, "STRINGID")

    # Step 1: Try ItemName + ItemDesc + STRINGID match
    if old_stringid and stringid_col:
        for row in range(2, new_ws.max_row + 1):
            new_stringid = sanitize_stringid_for_match(new_ws.cell(row, stringid_col).value)
            new_name = str(new_ws.cell(row, name_col).value or "").strip()
            new_desc = str(new_ws.cell(row, desc_col).value or "").strip()

            if new_stringid == old_stringid and new_name == old_item_name and new_desc == old_item_desc:
                return row, "name+desc+stringid"

    # Step 2: Fall back to ItemName + ItemDesc only
    for row in range(2, new_ws.max_row + 1):
        new_name = str(new_ws.cell(row, name_col).value or "").strip()
        new_desc = str(new_ws.cell(row, desc_col).value or "").strip()

        if new_name == old_item_name and new_desc == old_item_desc:
            return row, "name+desc"

    return None, None
