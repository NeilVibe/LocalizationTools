"""
Gimmick Datasheet Generator
===========================
Extracts Gimmick data from StaticInfo XMLs with proper hierarchy:
  GimmickAttributeGroup (GimmickName) → GimmickInfo (StrKey, GimmickName) → DropItem (Key)

FILTER: Only includes gimmicks that have ALL of:
  - GimmickInfo with StrKey
  - GimmickInfo with GimmickName (not empty)
  - DropItem with Key

Output per-language Excel files with:
  Sheet 1: GimmickDropItem – Hierarchical view with Group→Gimmick→Item
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lxml import etree as ET
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
    is_good_translation,
    autofit_worksheet,
    THIN_BORDER,
)

log = get_logger("GimmickGenerator")

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ItemData:
    """Item info for DropItem lookups."""
    strkey: str
    item_name: str       # KOR
    item_desc: str       # KOR


@dataclass
class GimmickEntry:
    """
    A valid gimmick entry with all required fields.
    Organized by: AttributeGroup (group_name) → GimmickInfo → DropItems
    """
    # From GimmickAttributeGroup
    group_name_kor: str          # GimmickName on AttributeGroup (group level)

    # From GimmickInfo
    gimmick_strkey: str          # StrKey
    gimmick_name_kor: str        # GimmickName on GimmickInfo

    # From DropItem(s)
    drop_item_keys: List[str] = field(default_factory=list)

    # For ordering (file + element order)
    source_file: str = ""
    order_index: int = 0


# =============================================================================
# STYLING
# =============================================================================

_depth_fill = {
    0: PatternFill("solid", fgColor="FFD966"),  # YELLOW - group
    1: PatternFill("solid", fgColor="D9E1F2"),  # BLUE - gimmick
    2: PatternFill("solid", fgColor="E2EFDA"),  # GREEN - item
}
_header_font = Font(bold=True, color="FFFFFF")
_header_fill = PatternFill("solid", fgColor="4F81BD")
_bold_font = Font(bold=True)


# =============================================================================
# ITEM INDEXING
# =============================================================================

def index_iteminfo(static_folder: Path) -> Dict[str, ItemData]:
    """Index all ItemInfo entries from StaticInfo."""
    log.info("Indexing ItemInfo from StaticInfo...")
    items: Dict[str, ItemData] = {}
    file_count = 0

    for xml in iter_xml_files(static_folder):
        root = parse_xml_file(xml)
        if root is None:
            continue
        file_count += 1

        for item in root.iter("ItemInfo"):
            key = item.get("StrKey")
            name = item.get("ItemName") or ""
            desc = item.get("ItemDesc") or ""
            if key and key not in items:
                items[key] = ItemData(strkey=key, item_name=name, item_desc=desc)

    log.info("Indexed %d ItemInfo entries from %d files", len(items), file_count)
    return items


# =============================================================================
# GIMMICK EXTRACTION
# =============================================================================

def find_parent_attribute_group(el: ET._Element) -> Tuple[str, Optional[ET._Element]]:
    """
    Walk up from GimmickInfo to find nearest GimmickAttributeGroup with GimmickName.
    Returns (group_name, group_element) or ("", None).
    """
    parent = el.getparent()
    while parent is not None:
        if parent.tag == "GimmickAttributeGroup":
            gname = parent.get("GimmickName") or ""
            if gname:
                return gname, parent
        parent = parent.getparent()
    return "", None


def index_gimmicks(static_folder: Path) -> List[GimmickEntry]:
    """
    Index gimmicks with the required structure.

    FILTER: Only include when ALL are present:
      - GimmickInfo with StrKey
      - GimmickInfo with GimmickName (not empty)
      - DropItem with Key

    Returns list of GimmickEntry in document order.
    """
    log.info("Indexing Gimmicks from StaticInfo...")
    entries: List[GimmickEntry] = []

    file_count = 0
    gimmick_count = 0
    skipped_no_name = 0
    skipped_no_drop = 0

    for xml in sorted(iter_xml_files(static_folder)):
        root = parse_xml_file(xml)
        if root is None:
            continue
        file_count += 1

        # Find all GimmickInfo elements
        for idx, gim_el in enumerate(root.iter("GimmickInfo")):
            strkey = gim_el.get("StrKey") or ""
            gim_name = gim_el.get("GimmickName") or ""

            if not strkey:
                continue

            # FILTER: Must have GimmickName
            if not gim_name:
                skipped_no_name += 1
                continue

            # Collect DropItem keys
            drop_keys: List[str] = []
            for drop_el in gim_el.findall(".//DropItem"):
                dk = drop_el.get("Key")
                if dk:
                    drop_keys.append(dk)

            # FILTER: Must have at least one DropItem
            if not drop_keys:
                skipped_no_drop += 1
                continue

            # Find parent GimmickAttributeGroup with GimmickName
            group_name, _ = find_parent_attribute_group(gim_el)

            entry = GimmickEntry(
                group_name_kor=group_name,
                gimmick_strkey=strkey,
                gimmick_name_kor=gim_name,
                drop_item_keys=drop_keys,
                source_file=xml.name,
                order_index=idx,
            )
            entries.append(entry)
            gimmick_count += 1

    log.info(
        "Indexed %d valid gimmicks from %d files (skipped: %d no name, %d no dropitem)",
        gimmick_count, file_count, skipped_no_name, skipped_no_drop
    )
    return entries


# =============================================================================
# TRANSLATION HELPERS
# =============================================================================

def translate(
    lang_tbl: Dict[str, Tuple[str, str]],
    kor_text: str,
    fallback_to_kor: bool = True,
) -> str:
    """Translate Korean text using language table."""
    if not kor_text:
        return ""
    norm = normalize_placeholders(kor_text)
    result = lang_tbl.get(norm, ("", ""))[0]
    if result and is_good_translation(result):
        return result
    return kor_text if fallback_to_kor else ""


def get_string_id(lang_tbl: Dict[str, Tuple[str, str]], kor_text: str) -> str:
    """Get StringID for Korean text from language table."""
    if not kor_text:
        return ""
    norm = normalize_placeholders(kor_text)
    return lang_tbl.get(norm, ("", ""))[1]


# =============================================================================
# EXCEL WRITER
# =============================================================================

def write_dropitem_sheet(
    wb: Workbook,
    lang_code: str,
    entries: List[GimmickEntry],
    items: Dict[str, ItemData],
    lang_tbl: Dict[str, Tuple[str, str]],
    eng_tbl: Dict[str, Tuple[str, str]],
) -> None:
    """
    Sheet 1: GimmickDropItem with STATUS column
    Hierarchical view: Group → Gimmick → Item
    """
    code = lang_code.upper()
    ws = wb.create_sheet(title="GimmickDropItem")

    # Build headers
    headers = [
        "Depth",
        "Type",
        "GroupName(KOR)",
        f"GroupName({code})" if lang_code != "eng" else "GroupName(ENG)",
        "GimmickKey",
        "GimmickName(KOR)",
        f"GimmickName({code})" if lang_code != "eng" else "GimmickName(ENG)",
        "ItemKey",
        "ItemName(KOR)",
        f"ItemName({code})" if lang_code != "eng" else "ItemName(ENG)",
        "ItemDesc(KOR)",
        f"ItemDesc({code})" if lang_code != "eng" else "ItemDesc(ENG)",
        "Command",
        "StringID",
        "STATUS",
    ]

    # Write headers
    for col, txt in enumerate(headers, start=1):
        cell = ws.cell(1, col, txt)
        cell.font = _header_font
        cell.fill = _header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    # Hidden columns
    hidden_cols = {"Depth", "GroupName(KOR)", "GimmickName(KOR)", "ItemName(KOR)", "ItemDesc(KOR)"}
    for idx, h in enumerate(headers, 1):
        if h in hidden_cols:
            ws.column_dimensions[get_column_letter(idx)].hidden = True

    # Build hierarchical rows
    rows_data: List[Tuple[List, int, str]] = []
    last_group = None
    last_gimmick = None

    for entry in entries:
        if entry.group_name_kor and entry.group_name_kor != last_group:
            group_loc = translate(lang_tbl if lang_code != "eng" else eng_tbl, entry.group_name_kor)
            row = [0, "Group", entry.group_name_kor, group_loc, "", "", "", "", "", "", "", "", "", "", ""]
            rows_data.append((row, 0, "Group"))
            last_group = entry.group_name_kor
            last_gimmick = None

        if entry.gimmick_strkey != last_gimmick:
            gim_loc = translate(lang_tbl if lang_code != "eng" else eng_tbl, entry.gimmick_name_kor)
            row = [1, "Gimmick", entry.group_name_kor, translate(lang_tbl if lang_code != "eng" else eng_tbl, entry.group_name_kor),
                   entry.gimmick_strkey, entry.gimmick_name_kor, gim_loc, "", "", "", "", "", "", "", ""]
            rows_data.append((row, 1, "Gimmick"))
            last_gimmick = entry.gimmick_strkey

        for item_key in entry.drop_item_keys:
            itm = items.get(item_key)
            item_kor = itm.item_name if itm else ""
            item_desc_kor = itm.item_desc if itm else ""
            item_loc = translate(lang_tbl if lang_code != "eng" else eng_tbl, item_kor)
            desc_loc = translate(lang_tbl if lang_code != "eng" else eng_tbl, item_desc_kor)
            cmd = f"/create item {item_key}"
            sid = get_string_id(lang_tbl, item_kor) or get_string_id(eng_tbl, item_kor)

            row = [2, "Item", entry.group_name_kor, translate(lang_tbl if lang_code != "eng" else eng_tbl, entry.group_name_kor),
                   entry.gimmick_strkey, entry.gimmick_name_kor, translate(lang_tbl if lang_code != "eng" else eng_tbl, entry.gimmick_name_kor),
                   item_key, item_kor, item_loc, item_desc_kor, desc_loc, cmd, sid, ""]
            rows_data.append((row, 2, "Item"))

    # Write rows
    for r_idx, (row, depth, row_type) in enumerate(rows_data, start=2):
        fill = _depth_fill.get(depth, _depth_fill[2])
        for c_idx, val in enumerate(row, start=1):
            cell = ws.cell(r_idx, c_idx, val)
            cell.fill = fill
            cell.border = THIN_BORDER
            if row_type in ("Group", "Gimmick"):
                cell.font = _bold_font
            cell.alignment = Alignment(
                horizontal="left" if c_idx > 1 else "center",
                vertical="top",
                wrap_text=True,
                indent=depth if c_idx == 2 else 0
            )

    # Add STATUS validation
    status_col_idx = headers.index("STATUS") + 1
    dv = DataValidation(
        type="list",
        formula1=f'"{",".join(STATUS_OPTIONS)}"',
        allow_blank=True,
        showErrorMessage=True,
    )
    col_letter = get_column_letter(status_col_idx)
    rng = f"{col_letter}2:{col_letter}{ws.max_row}"
    dv.add(rng)
    ws.add_data_validation(dv)

    # Force StringID column to text format
    stringid_col_idx = headers.index("StringID") + 1
    for row in range(2, ws.max_row + 1):
        ws.cell(row, stringid_col_idx).number_format = '@'

    # Finalize
    last_col = get_column_letter(len(headers))
    ws.auto_filter.ref = f"A1:{last_col}{len(rows_data)+1}"
    ws.freeze_panes = "A2"

    # Column widths
    width_map = {
        "Depth": 8, "Type": 10, "GroupName(KOR)": 20, f"GroupName({code})": 25, "GroupName(ENG)": 25,
        "GimmickKey": 40, "GimmickName(KOR)": 20, f"GimmickName({code})": 25, "GimmickName(ENG)": 25,
        "ItemKey": 30, "ItemName(KOR)": 20, f"ItemName({code})": 25, "ItemName(ENG)": 25,
        "ItemDesc(KOR)": 25, f"ItemDesc({code})": 35, "ItemDesc(ENG)": 35,
        "Command": 35, "StringID": 15, "STATUS": 15
    }
    for idx, h in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(idx)].width = width_map.get(h, 20)

    # Auto-fit columns and rows
    autofit_worksheet(ws)

    log.info("  Sheet GimmickDropItem: %d rows", len(rows_data))


# =============================================================================
# MAIN GENERATOR FUNCTION
# =============================================================================

def generate_gimmick_datasheets() -> Dict:
    """
    Generate Gimmick datasheets for all languages.

    Returns:
        Dict with results: {
            "category": "Gimmick",
            "files_created": N,
            "errors": [...]
        }
    """
    result = {
        "category": "Gimmick",
        "files_created": 0,
        "errors": [],
    }

    log.info("=" * 70)
    log.info("Gimmick Datasheet Generator")
    log.info("=" * 70)

    # Ensure output folder exists
    DATASHEET_OUTPUT.mkdir(parents=True, exist_ok=True)
    output_folder = DATASHEET_OUTPUT / "Gimmick_LQA"
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
        # 1. Load language tables
        lang_tables = load_language_tables(LANGUAGE_FOLDER)
        eng_tbl = lang_tables.get("eng", {})

        if not eng_tbl:
            log.warning("English language table not found!")

        # 2. Index items
        items = index_iteminfo(RESOURCE_FOLDER)

        # 3. Index gimmicks
        entries = index_gimmicks(RESOURCE_FOLDER)

        if not entries:
            result["errors"].append("No valid gimmick entries found!")
            log.warning("No valid gimmick entries found!")
            return result

        # 4. Generate workbooks for each language
        log.info("Processing languages...")
        total = len(lang_tables)

        for idx, (code, tbl) in enumerate(lang_tables.items(), 1):
            log.info("(%d/%d) Language %s", idx, total, code.upper())

            wb = Workbook()
            wb.remove(wb.active)

            # Sheet 1: Hierarchical DropItem view
            write_dropitem_sheet(wb, code, entries, items, tbl, eng_tbl)

            # Save
            out_path = output_folder / f"Gimmick_LQA_{code.upper()}.xlsx"
            wb.save(out_path)
            log.info("  Saved: %s", out_path.name)
            result["files_created"] += 1

        log.info("=" * 70)
        log.info("Done! Output folder: %s", output_folder)
        log.info("=" * 70)

    except Exception as e:
        result["errors"].append(f"Generator error: {e}")
        log.exception("Error in Gimmick generator: %s", e)

    return result


# Allow standalone execution for testing
if __name__ == "__main__":
    result = generate_gimmick_datasheets()
    print(f"\nResult: {result}")
