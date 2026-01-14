"""
Character Datasheet Generator
=============================
Extracts CharacterInfo nodes from staticinfo files and groups by filename pattern.

Tab Organization:
  characterinfo_npc.staticinfo        ]
  characterinfo_npc_shop.staticinfo   ] → NPC tab
  characterinfo_npc_unique.staticinfo ]

  characterinfo_monster.staticinfo        ] → MONSTER tab
  characterinfo_monster_unique.staticinfo ]

Output per-language Excel files with:
  - One sheet per group (NPC, MONSTER, etc.)
  - Columns: Original (KR) | English (ENG) | Translation | COMMAND | STATUS | COMMENT | STRINGID | SCREENSHOT
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from config import RESOURCE_FOLDER, LANGUAGE_FOLDER, DATASHEET_OUTPUT, STATUS_OPTIONS
from generators.base import (
    get_logger,
    parse_xml_file,
    iter_xml_files,
    load_language_tables,
    normalize_placeholders,
    autofit_worksheet,
    THIN_BORDER,
)

log = get_logger("CharacterGenerator")

# =============================================================================
# KOREAN STRING COLLECTION (for coverage tracking)
# =============================================================================

_collected_korean_strings: set = set()


def reset_korean_collection() -> None:
    """Reset the Korean string collection before a new run."""
    global _collected_korean_strings
    _collected_korean_strings = set()


def get_collected_korean_strings() -> set:
    """Return a copy of collected Korean strings."""
    return _collected_korean_strings.copy()


def _collect_korean_string(text: str) -> None:
    """Add a Korean string to the collection (normalized)."""
    if text:
        normalized = normalize_placeholders(text)
        if normalized:
            _collected_korean_strings.add(normalized)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class CharacterItem:
    """Single character entry."""
    strkey: str
    name: str  # CharacterName (Korean)
    source_file: str  # For debugging


# =============================================================================
# STYLING
# =============================================================================

_header_font = Font(bold=True, color="FFFFFF", size=11)
_header_fill = PatternFill("solid", fgColor="4F81BD")
_bold_font = Font(bold=True)

_row_fill_even = PatternFill("solid", fgColor="F2F2F2")
_row_fill_odd = PatternFill("solid", fgColor="FFFFFF")


# =============================================================================
# CHARACTER EXTRACTION
# =============================================================================

def iter_characterinfo_files(root: Path):
    """Find all characterinfo_*.staticinfo.xml files."""
    for path in iter_xml_files(root):
        fn = path.name.lower()
        if fn.startswith("characterinfo_") and fn.endswith(".staticinfo.xml"):
            yield path


def get_group_key(filename: str) -> str:
    """
    Extract group key from filename.

    characterinfo_npc.staticinfo.xml → npc
    characterinfo_npc_shop.staticinfo.xml → npc
    characterinfo_monster_unique.staticinfo.xml → monster
    """
    stem = filename.lower()
    if stem.startswith("characterinfo_"):
        stem = stem[len("characterinfo_"):]
    if stem.endswith(".staticinfo.xml"):
        stem = stem[:-len(".staticinfo.xml")]

    parts = stem.split("_")
    return parts[0] if parts else "unknown"


def extract_characters_from_file(path: Path) -> List[CharacterItem]:
    """Extract all CharacterInfo nodes from a file."""
    characters: List[CharacterItem] = []

    root_el = parse_xml_file(path)
    if root_el is None:
        return characters

    for node in root_el.iter("CharacterInfo"):
        strkey = node.get("StrKey") or ""
        name = node.get("CharacterName") or ""

        # Skip entries without both key and name
        if not strkey or not name:
            continue

        # Collect Korean string for coverage tracking
        _collect_korean_string(name)

        characters.append(CharacterItem(
            strkey=strkey,
            name=name,
            source_file=path.name
        ))

    return characters


def build_character_groups(folder: Path) -> Dict[str, List[CharacterItem]]:
    """
    Build character groups organized by filename pattern.

    Returns:
        Dict mapping group_key (e.g., 'npc', 'monster') to list of CharacterItems
    """
    groups: Dict[str, List[CharacterItem]] = defaultdict(list)
    seen_strkeys: set = set()  # Deduplication

    log.info("Scanning for characterinfo files...")

    file_count = 0
    for path in sorted(iter_characterinfo_files(folder)):
        file_count += 1
        group_key = get_group_key(path.name)

        characters = extract_characters_from_file(path)

        added = 0
        for char in characters:
            if char.strkey in seen_strkeys:
                continue
            seen_strkeys.add(char.strkey)
            groups[group_key].append(char)
            added += 1

        log.debug("  %s → %s: %d characters", path.name, group_key.upper(), added)

    log.info("Scanned %d files, found %d groups", file_count, len(groups))
    for key, items in sorted(groups.items()):
        log.info("  • %s: %d characters", key.upper(), len(items))

    return dict(groups)


# =============================================================================
# EXCEL WRITER
# =============================================================================

def write_workbook(
    groups: Dict[str, List[CharacterItem]],
    eng_tbl: Dict[str, Tuple[str, str]],
    lang_tbl: Optional[Dict[str, Tuple[str, str]]],
    lang_code: str,
    out_path: Path,
) -> None:
    """
    Write one workbook with one sheet per group.

    Columns:
      - Original (KR)
      - English (ENG)
      - Translation (OTHER) [skipped for ENG workbook]
      - COMMAND
      - STATUS
      - COMMENT
      - STRINGID
      - SCREENSHOT
    """
    wb = Workbook()
    wb.remove(wb.active)

    is_eng = lang_code.lower() == "eng"

    for group_key in sorted(groups.keys()):
        characters = groups[group_key]
        if not characters:
            continue

        title = group_key.upper()[:31]
        title = re.sub(r"[\\/*?:\[\]]", "_", title)
        sheet = wb.create_sheet(title=title)

        # Header row
        headers = []
        h1 = sheet.cell(1, 1, "Original (KR)")
        h2 = sheet.cell(1, 2, "English (ENG)")
        headers = [h1, h2]

        col_idx = 3
        if not is_eng:
            h3 = sheet.cell(1, col_idx, f"Translation ({lang_code.upper()})")
            headers.append(h3)
            col_idx += 1

        extra_headers = ["COMMAND", "STATUS", "COMMENT", "STRINGID", "SCREENSHOT"]
        for name in extra_headers:
            headers.append(sheet.cell(1, col_idx, name))
            col_idx += 1

        for c in headers:
            c.font = _header_font
            c.fill = _header_fill
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = THIN_BORDER
        sheet.row_dimensions[1].height = 25

        # Write data rows
        r_idx = 2

        for char in characters:
            fill = _row_fill_even if r_idx % 2 == 0 else _row_fill_odd
            normalized_name = normalize_placeholders(char.name)

            trans_eng, sid_eng = eng_tbl.get(normalized_name, ("", ""))
            trans_other, sid_other = ("", "")
            if not is_eng and lang_tbl is not None:
                trans_other, sid_other = lang_tbl.get(normalized_name, ("", ""))

            command = f"/create character {char.strkey}"

            col = 1
            c_orig = sheet.cell(r_idx, col, char.name)
            c_orig.fill = fill
            c_orig.border = THIN_BORDER
            c_orig.alignment = Alignment(vertical="center", wrap_text=True)
            col += 1

            c_eng = sheet.cell(r_idx, col, trans_eng)
            c_eng.fill = fill
            c_eng.border = THIN_BORDER
            c_eng.alignment = Alignment(vertical="center", wrap_text=True)
            col += 1

            if not is_eng:
                c_other = sheet.cell(r_idx, col, trans_other)
                c_other.fill = fill
                c_other.border = THIN_BORDER
                c_other.alignment = Alignment(vertical="center", wrap_text=True)
                col += 1

            c_command = sheet.cell(r_idx, col, command)
            c_command.fill = fill
            c_command.font = _bold_font
            c_command.border = THIN_BORDER
            c_command.alignment = Alignment(vertical="center", wrap_text=True)
            col += 1

            c_status = sheet.cell(r_idx, col, "")
            c_status.fill = fill
            c_status.border = THIN_BORDER
            c_status.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            col += 1

            c_comment = sheet.cell(r_idx, col, "")
            c_comment.fill = fill
            c_comment.border = THIN_BORDER
            c_comment.alignment = Alignment(vertical="center", wrap_text=True)
            col += 1

            c_stringid = sheet.cell(r_idx, col, sid_other if not is_eng else sid_eng)
            c_stringid.fill = fill
            c_stringid.font = _bold_font
            c_stringid.border = THIN_BORDER
            c_stringid.alignment = Alignment(vertical="center", wrap_text=True)
            c_stringid.number_format = '@'  # Text format
            col += 1

            c_screenshot = sheet.cell(r_idx, col, "")
            c_screenshot.fill = fill
            c_screenshot.border = THIN_BORDER
            c_screenshot.alignment = Alignment(vertical="center", wrap_text=True)

            r_idx += 1

        last_row = r_idx - 1

        # Column widths
        sheet.column_dimensions["A"].width = 30
        sheet.column_dimensions["B"].hidden = not is_eng
        sheet.column_dimensions["B"].width = 40
        if not is_eng:
            sheet.column_dimensions["C"].width = 40
            sheet.column_dimensions["D"].width = 50
            sheet.column_dimensions["E"].width = 11
            sheet.column_dimensions["F"].width = 50
            sheet.column_dimensions["G"].width = 25
            sheet.column_dimensions["H"].width = 20
        else:
            sheet.column_dimensions["C"].width = 50
            sheet.column_dimensions["D"].width = 11
            sheet.column_dimensions["E"].width = 50
            sheet.column_dimensions["F"].width = 25
            sheet.column_dimensions["G"].width = 20

        # Add strict STATUS validation
        status_col_idx = 5 if not is_eng else 4
        col_letter = get_column_letter(status_col_idx)
        dv = DataValidation(
            type="list",
            formula1=f'"{",".join(STATUS_OPTIONS)}"',
            allow_blank=True,
            showErrorMessage=True,
            errorStyle="stop",
            errorTitle="Invalid STATUS",
            error="Please select from the list."
        )
        rng = f"{col_letter}2:{col_letter}{last_row}"
        dv.add(rng)
        sheet.add_data_validation(dv)

        # Auto-fit columns and rows
        autofit_worksheet(sheet)

        actual_rows = last_row - 1
        log.info("  Sheet '%s': %d rows", title, actual_rows)

    if wb.worksheets:
        wb.save(out_path)
        log.info("→ Saved: %s (%d sheets)", out_path.name, len(wb.worksheets))


# =============================================================================
# MAIN GENERATOR FUNCTION
# =============================================================================

def generate_character_datasheets() -> Dict:
    """
    Generate Character datasheets for all languages.

    Returns:
        Dict with results: {
            "category": "Character",
            "files_created": N,
            "errors": [...]
        }
    """
    result = {
        "category": "Character",
        "files_created": 0,
        "errors": [],
    }

    # Reset Korean string collection
    reset_korean_collection()

    log.info("=" * 70)
    log.info("Character Datasheet Generator")
    log.info("=" * 70)

    # Ensure output folder exists
    DATASHEET_OUTPUT.mkdir(parents=True, exist_ok=True)
    output_folder = DATASHEET_OUTPUT / "Character_LQA"
    output_folder.mkdir(exist_ok=True)

    # Check paths
    if not RESOURCE_FOLDER.exists():
        result["errors"].append(f"Resource folder not found: {RESOURCE_FOLDER}")
        log.error("Resource folder not found: %s", RESOURCE_FOLDER)
        return result

    if not LANGUAGE_FOLDER.exists():
        result["errors"].append(f"Language folder not found: {LANGUAGE_FOLDER}")
        log.error("Language folder not found: %s", LANGUAGE_FOLDER)
        return result

    try:
        # 1. Build character groups from StaticInfo
        groups = build_character_groups(RESOURCE_FOLDER)

        if not groups:
            result["errors"].append("No character groups found!")
            log.warning("No character groups found!")
            return result

        # 2. Load language tables
        lang_tables = load_language_tables(LANGUAGE_FOLDER)

        if not lang_tables:
            result["errors"].append("No language tables found!")
            log.warning("No language tables found!")
            return result

        eng_tbl = lang_tables.get("eng", {})

        # 3. Generate workbooks
        log.info("Generating Excel workbooks...")
        total = len(lang_tables)

        for idx, (code, tbl) in enumerate(lang_tables.items(), 1):
            log.info("(%d/%d) Processing language: %s", idx, total, code.upper())
            out_xlsx = output_folder / f"Character_LQA_{code.upper()}.xlsx"
            if code.lower() == "eng":
                write_workbook(groups, eng_tbl, None, code, out_xlsx)
            else:
                write_workbook(groups, eng_tbl, tbl, code, out_xlsx)
            result["files_created"] += 1

        log.info("=" * 70)
        log.info("Done! Output folder: %s", output_folder)
        log.info("=" * 70)

    except Exception as e:
        result["errors"].append(f"Generator error: {e}")
        log.exception("Error in Character generator: %s", e)

    return result


# Allow standalone execution for testing
if __name__ == "__main__":
    result = generate_character_datasheets()
    print(f"\nResult: {result}")
