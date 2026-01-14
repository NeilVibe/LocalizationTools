"""
Item Datasheet Generator
========================
Extracts Item data from StaticInfo XMLs with proper hierarchy:
  ItemGroupInfo → ItemInfo

Key features:
- ItemGroupInfo hierarchy with parent-child relationships
- ItemDesc from KnowledgeKey lookup with fallback to ItemInfo.ItemDesc
- Depth-based clustering for group organization
- Monster item extraction to separate folder
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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

log = get_logger("ItemGenerator")

# Clustering settings
MERGE_UP_THRESHOLD = 50       # Groups with < this many items merge into parent
MIN_FOLDER_DEPTH = 1          # Minimum folder depth

# Special folder keys
OTHERS_KEY = "OTHERS"
MONSTER_ITEM_KEY = "MONSTER_ITEM"
MONSTER_SUBSTRING = "mon_"

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ItemData:
    """Complete data for a single item."""
    strkey: str
    item_name: str       # KOR original
    item_desc: str       # KOR original
    group_key: str
    group_name_kor: str  # KOR original


# Row format
PrimaryRow = Tuple[
    int, str,           # depth, group_key
    str, str, str,      # group_name (KOR, ENG, LOC)
    str, str,           # item_key, item_num
    str, str, str,      # item_name (KOR, ENG, LOC)
    str, str, str,      # item_desc (KOR, ENG, LOC)
    str, bool           # stringid, is_group
]

# =============================================================================
# STYLING
# =============================================================================

_depth_fill = {
    0: PatternFill("solid", fgColor="FFD966"),  # YELLOW
    1: PatternFill("solid", fgColor="D9E1F2"),  # BLUE
    2: PatternFill("solid", fgColor="E2EFDA"),  # GREEN
}
_item_fill = PatternFill("solid", fgColor="FCE4D6")
_header_font = Font(bold=True, color="FFFFFF")
_header_fill = PatternFill("solid", fgColor="4F81BD")
_bold_font = Font(bold=True)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calc_depth(node: str, parent_of: Dict[str, str]) -> int:
    """Calculate depth of a node in the hierarchy."""
    d = 0
    visited: Set[str] = set()
    while node in parent_of and parent_of[node]:
        if node in visited:
            break
        visited.add(node)
        node = parent_of[node]
        d += 1
    return d


def build_children_map(parent_of: Dict[str, str]) -> Dict[str, List[str]]:
    """Build reverse mapping: parent -> children."""
    children: Dict[str, List[str]] = {}
    for child, parent in parent_of.items():
        children.setdefault(parent, []).append(child)
    return children


def sanitize_filename(name: str) -> str:
    """Sanitize name for use as filename."""
    if not name:
        return "UNKNOWN"
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
    clean = clean.replace(' ', '_')
    clean = re.sub(r'_+', '_', clean)
    clean = clean.strip('_')
    if len(clean) > 50:
        clean = clean[:50]
    return clean if clean else "UNKNOWN"


def get_display_name(
    group_key: str,
    group_names: Dict[str, str],
    eng_tbl: Dict[str, Tuple[str, str]],
) -> str:
    """Get display name: ENG preferred, else raw group_key."""
    if group_key == OTHERS_KEY:
        return "Others"
    if group_key == MONSTER_ITEM_KEY:
        return "Monster_Item"

    kor_name = group_names.get(group_key, "")
    if kor_name:
        normalized = normalize_placeholders(kor_name)
        eng_name = eng_tbl.get(normalized, ("", ""))[0]
        if eng_name and is_good_translation(eng_name):
            return sanitize_filename(eng_name)

    if group_key.lower().startswith("itemgroup_"):
        fallback = group_key[10:]
    else:
        fallback = group_key

    return sanitize_filename(fallback)


# =============================================================================
# KNOWLEDGE DESCRIPTIONS
# =============================================================================

def load_knowledge_descriptions(folder: Path) -> Dict[str, str]:
    """Load KnowledgeKey -> Desc mapping from knowledge files."""
    log.info("Loading knowledge descriptions...")
    knowledge_map: Dict[str, str] = {}

    if not folder.exists():
        log.warning("Knowledge folder does not exist: %s", folder)
        return knowledge_map

    file_count = 0
    for path in iter_xml_files(folder):
        root = parse_xml_file(path)
        if root is None:
            continue
        file_count += 1

        for el in root.iter("KnowledgeInfo"):
            strkey = el.get("StrKey") or ""
            desc = el.get("Desc") or ""

            if strkey and strkey not in knowledge_map:
                knowledge_map[strkey] = desc

    log.info("Knowledge descriptions loaded: %d entries from %d files",
             len(knowledge_map), file_count)
    return knowledge_map


# =============================================================================
# MASTER ITEM GROUP PARSING
# =============================================================================

def parse_master_groups(path: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Parse ItemGroupInfo master file."""
    log.info("Parsing ItemGroupInfo master: %s", path)
    root = parse_xml_file(path)
    if root is None:
        log.error("Cannot parse ItemGroupInfo master file")
        return {}, {}

    group_name: Dict[str, str] = {}
    parent_of: Dict[str, str] = {}

    for el in root.iter("ItemGroupInfo"):
        sk = el.get("StrKey") or ""
        name = el.get("GroupName") or ""
        if sk:
            if sk not in group_name:
                group_name[sk] = name
            p = el.getparent()
            if p is not None and p.tag == "ItemGroupInfo":
                parent_key = p.get("StrKey") or ""
                if parent_key and sk not in parent_of:
                    parent_of[sk] = parent_key

    for el in root.iter("ChildGroupInfo"):
        child = el.get("StrKey") or ""
        name = el.get("GroupName") or ""
        p = el.getparent()
        if child:
            if name and child not in group_name:
                group_name[child] = name
            if p is not None and p.tag == "ItemGroupInfo":
                parent_key = p.get("StrKey") or ""
                if parent_key and child not in parent_of:
                    parent_of[child] = parent_key

    log.info("Groups parsed: %d  |  parent links: %d", len(group_name), len(parent_of))
    return group_name, parent_of


# =============================================================================
# RESOURCE SCAN
# =============================================================================

def scan_resource_folder(
    folder: Path,
    knowledge_desc_map: Dict[str, str]
) -> Tuple[Dict[str, List[Tuple[str, str, str]]], Dict[str, str]]:
    """Scan resource folder for items."""
    log.info("Scanning resource folder for items: %s", folder)
    group_items: Dict[str, List[Tuple[str, str, str]]] = {}
    scanned_group_names: Dict[str, str] = {}

    for path in iter_xml_files(folder):
        root = parse_xml_file(path)
        if root is None:
            continue

        for g_el in root.iter("ItemGroupInfo"):
            g_key = g_el.get("StrKey") or ""
            g_name = g_el.get("GroupName") or ""
            if not g_key:
                continue
            if g_name and g_key not in scanned_group_names:
                scanned_group_names[g_key] = g_name

            bucket = group_items.setdefault(g_key, [])
            for item in g_el.iter("ItemInfo"):
                ik = item.get("StrKey") or ""
                name = item.get("ItemName") or ""

                knowledge_key = item.get("KnowledgeKey") or ""
                item_desc_attr = item.get("ItemDesc") or ""

                if knowledge_key:
                    desc = knowledge_desc_map.get(knowledge_key, "")
                    if not desc:
                        desc = item_desc_attr
                else:
                    desc = item_desc_attr

                if ik:
                    bucket.append((ik, name, desc))

    total_items = sum(len(v) for v in group_items.values())
    log.info("Group-item mapping built: Groups=%d  Total items=%d", len(group_items), total_items)
    return group_items, scanned_group_names


# =============================================================================
# BUILD ITEM DATA
# =============================================================================

def build_item_data(
    group_items: Dict[str, List[Tuple[str, str, str]]],
    group_names: Dict[str, str],
) -> Dict[str, ItemData]:
    """Build complete item data mapping."""
    items: Dict[str, ItemData] = {}
    for gk, lst in group_items.items():
        kor = group_names.get(gk, "")
        for ik, iname, idesc in lst:
            items[ik] = ItemData(
                strkey=ik,
                item_name=iname,
                item_desc=idesc,
                group_key=gk,
                group_name_kor=kor,
            )
    log.info("Built data for %d items", len(items))
    return items


# =============================================================================
# ROW GENERATION
# =============================================================================

def build_rows_for_language(
    code: str,
    group_names: Dict[str, str],
    parent_of: Dict[str, str],
    group_items: Dict[str, List[Tuple[str, str, str]]],
    lang_tbl: Dict[str, Tuple[str, str]],
    eng_tbl: Dict[str, Tuple[str, str]],
) -> List[PrimaryRow]:
    """Build rows for a specific language."""
    log.info("Building rows for %s", code.upper())

    def t(tbl: Dict[str, Tuple[str, str]], text: str) -> str:
        if not text:
            return ""
        return tbl.get(normalize_placeholders(text), ("", ""))[0]

    rows: List[PrimaryRow] = []
    children_of = build_children_map(parent_of)
    all_groups = set(group_items)
    master_roots = sorted(g for g in group_names if g not in parent_of)
    seen: Set[str] = set()

    def recurse(gk: str):
        if gk in seen:
            return
        seen.add(gk)
        depth = calc_depth(gk, parent_of)
        kor = group_names.get(gk, "")
        eng = t(eng_tbl, kor)
        loc = t(lang_tbl, kor)
        rows.append((depth, gk, kor, eng, loc,
                     "", "", "", "", "", "", "", "", "", True))

        for ik, iname, idesc in sorted(group_items.get(gk, []), key=lambda x: x[0]):
            ieng = t(eng_tbl, iname)
            iloc = t(lang_tbl, iname)
            deng = t(eng_tbl, idesc)
            dloc = t(lang_tbl, idesc)
            sid = lang_tbl.get(normalize_placeholders(iname), ("", ""))[1]
            rows.append((depth+1, gk, kor, eng, loc,
                         ik, "", iname, ieng, iloc, idesc, deng, dloc, sid, False))

        for child in sorted(children_of.get(gk, [])):
            recurse(child)

    for root in master_roots:
        recurse(root)
    for orphan in sorted(all_groups - seen):
        recurse(orphan)

    log.info("Total rows for %s: %d", code.upper(), len(rows))
    return rows


# =============================================================================
# EXCEL WRITER
# =============================================================================

def write_primary_sheet(
    wb: Workbook,
    lang_code: str,
    rows: List[PrimaryRow],
) -> None:
    """Create the primary LQA sheet for one language."""
    title = lang_code.upper()
    ws = wb.create_sheet(title=title[:31])

    # Build headers
    headers = [
        "Depth", "GroupKey",
        "GroupName(KOR)", "GroupName(ENG)",
        "ItemKey", "ItemName(KOR)", "ItemName(ENG)",
    ]
    if lang_code != "eng":
        headers.append(f"ItemName({title})")

    headers += ["ItemDesc(KOR)", "ItemDesc(ENG)"]
    if lang_code != "eng":
        headers.append(f"ItemDesc({title})")

    headers += ["StringID", "DebugCommand", "STATUS", "COMMENT", "STRINGID", "SCREENSHOT"]

    # Write header row
    for col, txt in enumerate(headers, start=1):
        cell = ws.cell(1, col, txt)
        cell.font = _header_font
        cell.fill = _header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    # Write data rows
    is_eng = lang_code.lower() == "eng"
    r = 2

    for row in rows:
        (
            depth, gk, gkor, geng, gloc,
            ik, num, nkor, neng, nloc,
            dkor, deng, dloc, sid, is_group
        ) = row

        vals = [depth, gk, gkor, geng]
        vals += [ik, nkor, neng]
        if lang_code != "eng":
            vals.append(nloc)
        vals += [dkor, deng]
        if lang_code != "eng":
            vals.append(dloc)
        vals += [sid, f"/create item {ik}" if not is_group else ""]
        vals += ["", "", sid, ""]

        for cidx, val in enumerate(vals, start=1):
            c = ws.cell(r, cidx, val)
            c.alignment = Alignment(
                indent=(depth if cidx == 1 else 0),
                wrap_text=True,
                vertical="top",
            )
            c.border = THIN_BORDER
            if is_group:
                c.fill = _depth_fill.get(depth, _depth_fill[2])
                if cidx in (3, 4):
                    c.font = _bold_font
            else:
                c.fill = _item_fill
        r += 1

    # Sheet cosmetics
    last_col_letter = get_column_letter(len(headers))
    ws.auto_filter.ref = f"A1:{last_col_letter}{r-1}"
    ws.freeze_panes = "A2"

    # Hide depth column
    ws.column_dimensions["A"].hidden = True

    # Add STATUS drop-down
    status_col_idx = headers.index("STATUS") + 1
    col_letter = get_column_letter(status_col_idx)
    dv = DataValidation(
        type="list",
        formula1=f'"{",".join(STATUS_OPTIONS)}"',
        allow_blank=True,
    )
    dv.add(f"{col_letter}2:{col_letter}{ws.max_row}")
    ws.add_data_validation(dv)

    # Auto-fit
    autofit_worksheet(ws)


# =============================================================================
# MAIN GENERATOR FUNCTION
# =============================================================================

def generate_item_datasheets() -> Dict:
    """
    Generate Item datasheets for all languages.

    Returns:
        Dict with results: {
            "category": "Item",
            "files_created": N,
            "errors": [...]
        }
    """
    result = {
        "category": "Item",
        "files_created": 0,
        "errors": [],
    }

    log.info("=" * 70)
    log.info("Item Datasheet Generator")
    log.info("=" * 70)

    # Ensure output folder exists
    DATASHEET_OUTPUT.mkdir(parents=True, exist_ok=True)
    output_folder = DATASHEET_OUTPUT / "Item_LQA"
    output_folder.mkdir(exist_ok=True)

    # Check paths
    item_folder = RESOURCE_FOLDER / "iteminfo"
    if not item_folder.exists():
        item_folder = RESOURCE_FOLDER  # Fallback

    knowledge_folder = RESOURCE_FOLDER / "knowledgeinfo"

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

        if not lang_tables:
            result["errors"].append("No language tables found!")
            log.warning("No language tables found!")
            return result

        # 2. Load knowledge descriptions
        knowledge_desc_map = load_knowledge_descriptions(knowledge_folder)

        # 3. Parse master groups
        itemgroupinfo_file = item_folder / "itemgroupinfo.staticinfo.xml"
        if itemgroupinfo_file.exists():
            master_names, parent_of = parse_master_groups(itemgroupinfo_file)
        else:
            master_names, parent_of = {}, {}
            log.warning("ItemGroupInfo master file not found")

        # 4. Scan resource folder
        group_items, scanned_names = scan_resource_folder(item_folder, knowledge_desc_map)

        all_names = {**scanned_names, **master_names}
        all_names[OTHERS_KEY] = "Others"
        all_names[MONSTER_ITEM_KEY] = "Monster_Item"

        # 5. Build item data
        items = build_item_data(group_items, all_names)

        if not items:
            result["errors"].append("No item data found!")
            log.warning("No item data found!")
            return result

        # 6. Generate workbooks
        log.info("Processing languages...")
        total = len(lang_tables)

        for idx, (code, tbl) in enumerate(lang_tables.items(), 1):
            log.info("(%d/%d) Language %s", idx, total, code.upper())

            rows = build_rows_for_language(code, all_names, parent_of,
                                           group_items, tbl, eng_tbl)

            wb = Workbook()
            wb.remove(wb.active)
            write_primary_sheet(wb, code, rows)
            wb.save(output_folder / f"Item_LQA_{code.upper()}.xlsx")
            result["files_created"] += 1

        log.info("=" * 70)
        log.info("Done! Output folder: %s", output_folder)
        log.info("=" * 70)

    except Exception as e:
        result["errors"].append(f"Generator error: {e}")
        log.exception("Error in Item generator: %s", e)

    return result


# Allow standalone execution for testing
if __name__ == "__main__":
    result = generate_item_datasheets()
    print(f"\nResult: {result}")
