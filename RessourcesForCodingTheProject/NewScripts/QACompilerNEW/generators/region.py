"""
Region Datasheet Generator
==========================
Extracts Region/Faction data from StaticInfo XMLs with proper hierarchy:
  FactionGroup → Faction → FactionNode (nested)

Structure:
- ONE Excel sheet per FactionGroup (using GroupName as tab name)
- Each sheet contains Factions as major sections
- FactionNodes nested under their parent Factions
- Proper indentation showing hierarchy depth

Key features:
- FactionNode.Name comes from KnowledgeInfo lookup (KnowledgeKey → StrKey match)
- FactionNode.Desc used directly as description
- Standalone 세력 없음 (Empty Faction) factions → separate sheet
- Shop data parsing (separate sheet)
"""

import re
from collections import OrderedDict
from dataclasses import dataclass, field
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

log = get_logger("RegionGenerator")

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


# Empty Faction identifier (Korean)
EMPTY_FACTION_NAME = "세력 없음"

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FactionNodeData:
    """A single FactionNode with nested children."""
    strkey: str
    name: str              # Display name (from KnowledgeInfo.Name lookup)
    original_name: str     # Original Name attribute (fallback)
    description: str       # From FactionNode.Desc
    knowledge_key: str
    node_type: str         # Main, Sub, etc.
    children: List["FactionNodeData"] = field(default_factory=list)


@dataclass
class FactionData:
    """A Faction containing multiple FactionNodes."""
    strkey: str
    name: str              # Faction Name attribute
    knowledge_key: str
    nodes: List[FactionNodeData] = field(default_factory=list)


@dataclass
class FactionGroupData:
    """A FactionGroup (top-level, becomes sheet tab)."""
    strkey: str
    group_name: str        # GroupName attribute - used as sheet tab name
    knowledge_key: str
    factions: List[FactionData] = field(default_factory=list)


@dataclass
class ShopStage:
    """A single shop stage."""
    strkey: str
    name: str
    description: str
    category: str = ""
    npc_key: str = ""


@dataclass
class ShopGroup:
    """A shop group."""
    tag_name: str
    name: str
    group: str
    stages: List[ShopStage] = field(default_factory=list)


# =============================================================================
# STYLING
# =============================================================================

STYLES = {
    "Faction": {
        "fill": PatternFill("solid", fgColor="4472C4"),  # Dark blue
        "font": Font(bold=True, size=12, color="FFFFFF"),
    },
    "FactionNode_Main": {
        "fill": PatternFill("solid", fgColor="5B9BD5"),  # Medium blue
        "font": Font(bold=True, size=11, color="FFFFFF"),
    },
    "FactionNode_Sub": {
        "fill": PatternFill("solid", fgColor="B4C6E7"),  # Light blue
        "font": Font(bold=True),
    },
    "FactionNode": {
        "fill": PatternFill("solid", fgColor="D6DCE4"),  # Very light blue
        "font": Font(),
    },
    "Description": {
        "fill": PatternFill("solid", fgColor="F5F5F5"),  # Light gray
        "font": Font(),
    },
    "ShopGroup": {
        "fill": PatternFill("solid", fgColor="00B0B0"),  # Teal
        "font": Font(bold=True, size=12, color="FFFFFF"),
    },
    "ShopStage": {
        "fill": PatternFill("solid", fgColor="E0F7FA"),  # Light cyan
        "font": Font(bold=True),
    },
}

_header_font = Font(bold=True, color="FFFFFF", size=11)
_header_fill = PatternFill("solid", fgColor="4F81BD")
_default_font = Font()
_default_fill = PatternFill("solid", fgColor="FFFFFF")


def get_style(style_type: str) -> Tuple[PatternFill, Font]:
    """Get style for a row type."""
    style = STYLES.get(style_type, {})
    return (
        style.get("fill", _default_fill),
        style.get("font", _default_font),
    )


# =============================================================================
# KNOWLEDGE NAME LOOKUP
# =============================================================================

def build_knowledge_name_lookup(folder: Path) -> Dict[str, str]:
    """
    Build lookup: KnowledgeInfo.StrKey → KnowledgeInfo.Name

    Used to get correct display names for FactionNodes via their KnowledgeKey.
    """
    log.info("Building Knowledge Name lookup...")

    name_lookup: Dict[str, str] = {}
    duplicates = 0

    for path in sorted(iter_xml_files(folder)):
        root_el = parse_xml_file(path)
        if root_el is None:
            continue

        for ki in root_el.iter("KnowledgeInfo"):
            strkey = ki.get("StrKey") or ""
            name = ki.get("Name") or ""

            if not strkey or not name:
                continue

            if strkey in name_lookup:
                duplicates += 1
                continue

            name_lookup[strkey] = name

    log.info("  → %d entries (%d duplicates ignored)", len(name_lookup), duplicates)
    return name_lookup


# =============================================================================
# FACTION PARSING
# =============================================================================

def parse_faction_node_recursive(
    elem,
    knowledge_lookup: Dict[str, str],
    global_seen: Set[str],
    depth: int = 0
) -> Optional[FactionNodeData]:
    """Parse a FactionNode element and all its nested FactionNode children."""
    strkey = elem.get("StrKey") or ""
    original_name = elem.get("Name") or ""
    knowledge_key = elem.get("KnowledgeKey") or ""
    description = elem.get("Desc") or ""
    node_type = elem.get("Type") or ""

    # Resolve display name via KnowledgeInfo lookup
    if knowledge_key and knowledge_key in knowledge_lookup:
        display_name = knowledge_lookup[knowledge_key]
    else:
        display_name = original_name

    if not display_name:
        return None

    # Duplicate check
    if strkey:
        if strkey in global_seen:
            return None
        global_seen.add(strkey)

    # Collect Korean strings for coverage tracking
    _collect_korean_string(display_name)
    _collect_korean_string(description)

    node = FactionNodeData(
        strkey=strkey,
        name=display_name,
        original_name=original_name,
        description=description,
        knowledge_key=knowledge_key,
        node_type=node_type,
    )

    # Parse nested FactionNodes
    for child_elem in elem:
        if child_elem.tag == "FactionNode":
            child_node = parse_faction_node_recursive(
                child_elem, knowledge_lookup, global_seen, depth + 1
            )
            if child_node:
                node.children.append(child_node)

    return node


def parse_faction_element(
    elem,
    knowledge_lookup: Dict[str, str],
    global_seen: Set[str]
) -> Optional[FactionData]:
    """Parse a Faction element and all its FactionNode children."""
    strkey = elem.get("StrKey") or ""
    name = elem.get("Name") or ""
    knowledge_key = elem.get("KnowledgeKey") or ""

    if not name:
        return None

    # Collect Korean string for coverage tracking
    _collect_korean_string(name)

    faction = FactionData(
        strkey=strkey,
        name=name,
        knowledge_key=knowledge_key,
    )

    # Parse direct FactionNode children
    for child_elem in elem:
        if child_elem.tag == "FactionNode":
            node = parse_faction_node_recursive(child_elem, knowledge_lookup, global_seen)
            if node:
                faction.nodes.append(node)

    return faction


def parse_faction_group_element(
    elem,
    knowledge_lookup: Dict[str, str],
    global_seen: Set[str]
) -> Optional[FactionGroupData]:
    """Parse a FactionGroup element and all its Faction children."""
    strkey = elem.get("StrKey") or ""
    group_name = elem.get("GroupName") or ""
    knowledge_key = elem.get("KnowledgeKey") or ""

    if not group_name:
        return None

    # Collect Korean string for coverage tracking
    _collect_korean_string(group_name)

    faction_group = FactionGroupData(
        strkey=strkey,
        group_name=group_name,
        knowledge_key=knowledge_key,
    )

    # Parse Faction children
    for child_elem in elem:
        if child_elem.tag == "Faction":
            faction = parse_faction_element(child_elem, knowledge_lookup, global_seen)
            if faction:
                faction_group.factions.append(faction)

    return faction_group


def parse_all_faction_groups(
    folder: Path,
    knowledge_lookup: Dict[str, str],
    global_seen: Set[str]
) -> List[FactionGroupData]:
    """Parse all FactionGroup elements from all XML files."""
    log.info("Parsing FactionGroup → Faction → FactionNode hierarchy...")

    faction_groups: List[FactionGroupData] = []
    seen_group_strkeys: Set[str] = set()

    total_factions = 0
    total_nodes = 0

    for path in sorted(iter_xml_files(folder)):
        root_el = parse_xml_file(path)
        if root_el is None:
            continue

        for fg_elem in root_el.iter("FactionGroup"):
            strkey = fg_elem.get("StrKey") or ""

            # Skip duplicate FactionGroups
            if strkey and strkey in seen_group_strkeys:
                continue
            if strkey:
                seen_group_strkeys.add(strkey)

            fg = parse_faction_group_element(fg_elem, knowledge_lookup, global_seen)
            if fg and fg.factions:
                faction_groups.append(fg)

                for faction in fg.factions:
                    total_factions += 1
                    total_nodes += count_nodes_recursive(faction.nodes)

    log.info("  → %d FactionGroups, %d Factions, %d FactionNodes",
             len(faction_groups), total_factions, total_nodes)

    return faction_groups


def count_nodes_recursive(nodes: List[FactionNodeData]) -> int:
    """Count total nodes including nested children."""
    count = len(nodes)
    for node in nodes:
        count += count_nodes_recursive(node.children)
    return count


def parse_standalone_factions(
    folder: Path,
    knowledge_lookup: Dict[str, str],
    global_seen: Set[str],
) -> List[FactionData]:
    """Parse Faction elements that are NOT inside any FactionGroup."""
    log.info("Parsing standalone Factions (not in any FactionGroup)...")

    standalone_factions: List[FactionData] = []
    seen_faction_strkeys: Set[str] = set()

    for path in sorted(iter_xml_files(folder)):
        root_el = parse_xml_file(path)
        if root_el is None:
            continue

        # Collect all Faction StrKeys that ARE inside FactionGroups
        factions_in_groups: Set[str] = set()
        for fg_elem in root_el.iter("FactionGroup"):
            for faction_elem in fg_elem.iter("Faction"):
                sk = faction_elem.get("StrKey") or ""
                if sk:
                    factions_in_groups.add(sk)

        # Find Factions that are direct children of ROOT
        for child in root_el:
            if child.tag == "Faction":
                strkey = child.get("StrKey") or ""

                if strkey and strkey in seen_faction_strkeys:
                    continue
                if strkey and strkey in factions_in_groups:
                    continue

                if strkey:
                    seen_faction_strkeys.add(strkey)

                faction = parse_faction_element(child, knowledge_lookup, global_seen)
                if faction and faction.nodes:
                    standalone_factions.append(faction)

    total_nodes = sum(count_nodes_recursive(f.nodes) for f in standalone_factions)
    log.info("  → %d standalone Factions, %d total nodes",
             len(standalone_factions), total_nodes)

    return standalone_factions


# =============================================================================
# SHOP PARSING
# =============================================================================

def parse_shop_file(shop_path: Path, global_seen: Set[str]) -> List[ShopGroup]:
    """Parse shop file for shop stage data."""
    if not shop_path.exists():
        log.warning("Shop file not found: %s", shop_path)
        return []

    log.info("Parsing shop file: %s", shop_path)

    root_el = parse_xml_file(shop_path)
    if root_el is None:
        log.error("Failed to parse shop file")
        return []

    merged_groups: OrderedDict[str, ShopGroup] = OrderedDict()

    for child in root_el:
        if not isinstance(child.tag, str):
            continue

        name = child.get("Name") or ""
        group = child.get("Group") or ""

        if not name:
            continue

        new_stages: List[ShopStage] = []
        for stage_el in child.iter("Stage"):
            strkey = stage_el.get("StrKey") or ""
            stage_name = stage_el.get("Name") or ""
            desc = stage_el.get("Desc") or ""
            category = stage_el.get("Category") or ""
            npc_key = stage_el.get("NPCShopCharacterKey") or ""

            if not stage_name:
                continue

            if strkey:
                if strkey in global_seen:
                    continue
                global_seen.add(strkey)

            stage = ShopStage(
                strkey=strkey,
                name=stage_name,
                description=desc,
                category=category,
                npc_key=npc_key,
            )
            new_stages.append(stage)

        if not new_stages:
            continue

        if name in merged_groups:
            merged_groups[name].stages.extend(new_stages)
        else:
            merged_groups[name] = ShopGroup(
                tag_name=child.tag,
                name=name,
                group=group,
                stages=new_stages,
            )

    shop_groups = list(merged_groups.values())
    log.info("  → %d groups, %d stages",
             len(shop_groups), sum(len(g.stages) for g in shop_groups))

    return shop_groups


# =============================================================================
# ROW GENERATION
# =============================================================================

# Row format: (depth, text, style_type)
RowItem = Tuple[int, str, str]


def emit_faction_node_rows(node: FactionNodeData, depth: int) -> List[RowItem]:
    """Generate rows for a FactionNode and its children."""
    rows: List[RowItem] = []

    style = f"FactionNode_{node.node_type}" if node.node_type else "FactionNode"
    rows.append((depth, node.name, style))

    if node.description:
        rows.append((depth + 1, node.description, "Description"))

    for child in node.children:
        rows.extend(emit_faction_node_rows(child, depth + 1))

    return rows


def emit_faction_rows(faction: FactionData, depth: int = 0) -> List[RowItem]:
    """Generate rows for a Faction and all its FactionNodes."""
    rows: List[RowItem] = []

    rows.append((depth, faction.name, "Faction"))

    for node in faction.nodes:
        rows.extend(emit_faction_node_rows(node, depth + 1))

    return rows


def emit_faction_group_rows(fg: FactionGroupData) -> List[RowItem]:
    """Generate all rows for a FactionGroup."""
    rows: List[RowItem] = []

    for faction in fg.factions:
        rows.extend(emit_faction_rows(faction, 0))

    return rows


def emit_standalone_faction_rows(standalone_factions: List[FactionData]) -> List[RowItem]:
    """Generate rows for standalone Factions."""
    rows: List[RowItem] = []

    for faction in standalone_factions:
        rows.append((0, faction.name, "Faction"))
        for node in faction.nodes:
            rows.extend(emit_faction_node_rows(node, 1))

    return rows


def emit_shop_rows(shop_groups: List[ShopGroup]) -> List[RowItem]:
    """Generate rows for Shop data."""
    rows: List[RowItem] = []

    for group in shop_groups:
        rows.append((0, group.name, "ShopGroup"))
        for stage in group.stages:
            rows.append((1, stage.name, "ShopStage"))
            if stage.description:
                rows.append((2, stage.description, "Description"))

    return rows


# =============================================================================
# EXCEL WRITER
# =============================================================================

def get_translated_tab_name(
    korean_name: str,
    eng_tbl: Dict[str, Tuple[str, str]],
    lang_tbl: Optional[Dict[str, Tuple[str, str]]],
    lang_code: str,
    fallback: str = "Sheet"
) -> str:
    """Get translated sheet tab name."""
    normalized = normalize_placeholders(korean_name)
    is_eng = lang_code.lower() == "eng"

    if is_eng:
        trans, _ = eng_tbl.get(normalized, ("", ""))
        title = trans.strip() if trans else korean_name.strip()
    else:
        if lang_tbl:
            trans, _ = lang_tbl.get(normalized, ("", ""))
            if trans and is_good_translation(trans):
                title = trans.strip()
            else:
                trans_eng, _ = eng_tbl.get(normalized, ("", ""))
                title = trans_eng.strip() if trans_eng else korean_name.strip()
        else:
            trans_eng, _ = eng_tbl.get(normalized, ("", ""))
            title = trans_eng.strip() if trans_eng else korean_name.strip()

    if not title:
        title = fallback

    # Sanitize for Excel
    title = title[:31]
    title = re.sub(r"[\\/*?:\[\]]", "_", title)

    return title


def write_sheet_content(
    sheet,
    rows: List[RowItem],
    is_eng: bool,
    eng_tbl: Dict[str, Tuple[str, str]],
    lang_tbl: Optional[Dict[str, Tuple[str, str]]],
    lang_code: str
) -> None:
    """Write rows to a sheet with proper formatting."""

    # Headers
    headers = []
    headers.append(sheet.cell(1, 1, "Original (KR)"))
    headers.append(sheet.cell(1, 2, "English (ENG)"))
    if not is_eng:
        headers.append(sheet.cell(1, 3, f"Translation ({lang_code.upper()})"))

    extra_headers = ["STATUS", "COMMENT", "STRINGID", "SCREENSHOT"]
    start_col = len(headers) + 1
    for idx, name in enumerate(extra_headers, start=start_col):
        headers.append(sheet.cell(1, idx, name))

    for c in headers:
        c.font = _header_font
        c.fill = _header_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = THIN_BORDER
    sheet.row_dimensions[1].height = 25

    # Data rows with deduplication
    seen_keys = set()
    r_idx = 2

    for (depth, text, style_type) in rows:
        fill, font = get_style(style_type)
        normalized = normalize_placeholders(text)

        trans_eng, sid_eng = eng_tbl.get(normalized, ("", ""))
        trans_other = sid_other = ""
        if not is_eng and lang_tbl:
            trans_other, sid_other = lang_tbl.get(normalized, ("", ""))

        # Deduplication: skip if (Korean, Translation, STRINGID) already seen
        trans = trans_eng if is_eng else trans_other
        sid = sid_eng if is_eng else sid_other
        dedup_key = (text, trans, sid)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        # Original
        c_orig = sheet.cell(r_idx, 1, text)
        c_orig.fill = fill
        c_orig.font = font
        c_orig.alignment = Alignment(indent=depth, wrap_text=True, vertical="center")
        c_orig.border = THIN_BORDER

        # English
        c_eng = sheet.cell(r_idx, 2, trans_eng)
        c_eng.fill = fill
        c_eng.font = font
        c_eng.alignment = Alignment(indent=depth, wrap_text=True, vertical="center")
        c_eng.border = THIN_BORDER

        # Target language
        col_offset = 2
        if not is_eng:
            c_other = sheet.cell(r_idx, 3, trans_other)
            c_other.fill = fill
            c_other.font = font
            c_other.alignment = Alignment(indent=depth, wrap_text=True, vertical="center")
            c_other.border = THIN_BORDER
            col_offset = 3

        # Extra columns
        c_status = sheet.cell(r_idx, col_offset + 1, "")
        c_status.fill = fill
        c_status.alignment = Alignment(horizontal="center", vertical="center")
        c_status.border = THIN_BORDER

        c_comment = sheet.cell(r_idx, col_offset + 2, "")
        c_comment.fill = fill
        c_comment.border = THIN_BORDER

        c_stringid = sheet.cell(r_idx, col_offset + 3, sid_other if not is_eng else sid_eng)
        c_stringid.fill = fill
        c_stringid.font = Font(bold=True)
        c_stringid.border = THIN_BORDER
        c_stringid.number_format = '@'

        c_screenshot = sheet.cell(r_idx, col_offset + 4, "")
        c_screenshot.fill = fill
        c_screenshot.border = THIN_BORDER

        r_idx += 1

    last_row = r_idx - 1

    # Column widths
    widths = [40, 80] + ([] if is_eng else [80]) + [15, 70, 25, 25]
    for idx, w in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(idx)].width = w

    # Hide English column for non-English workbooks
    if not is_eng:
        sheet.column_dimensions["B"].hidden = True

    # Status dropdown
    status_col = 3 if is_eng else 4
    dv = DataValidation(
        type="list",
        formula1=f'"{",".join(STATUS_OPTIONS)}"',
        allow_blank=True,
    )
    col_letter = get_column_letter(status_col)
    dv.add(f"{col_letter}2:{col_letter}{last_row}")
    sheet.add_data_validation(dv)

    # Auto-fit
    autofit_worksheet(sheet)


def write_workbook(
    faction_groups: List[FactionGroupData],
    standalone_factions: List[FactionData],
    shop_groups: List[ShopGroup],
    eng_tbl: Dict[str, Tuple[str, str]],
    lang_tbl: Optional[Dict[str, Tuple[str, str]]],
    lang_code: str,
    out_path: Path,
) -> None:
    """Generate Excel workbook for a language."""
    wb = Workbook()
    wb.remove(wb.active)

    is_eng = lang_code.lower() == "eng"
    used_titles: Set[str] = set()

    def get_unique_title(base: str) -> str:
        title = base
        counter = 1
        while title in used_titles:
            title = f"{base[:28]}_{counter}"
            counter += 1
        used_titles.add(title)
        return title

    # FactionGroup sheets
    for fg in faction_groups:
        rows = emit_faction_group_rows(fg)
        if not rows:
            continue

        title = get_translated_tab_name(fg.group_name, eng_tbl, lang_tbl, lang_code, "Group")
        title = get_unique_title(title)

        sheet = wb.create_sheet(title=title)
        write_sheet_content(sheet, rows, is_eng, eng_tbl, lang_tbl, lang_code)

        log.info("    Sheet '%s': %d rows", title, len(rows))

    # Standalone Faction sheet
    if standalone_factions:
        rows = emit_standalone_faction_rows(standalone_factions)
        if rows:
            title = get_translated_tab_name(EMPTY_FACTION_NAME, eng_tbl, lang_tbl, lang_code, "No Faction")
            title = get_unique_title(title)

            sheet = wb.create_sheet(title=title)
            write_sheet_content(sheet, rows, is_eng, eng_tbl, lang_tbl, lang_code)

            log.info("    Sheet '%s': %d rows", title, len(rows))

    # Shop sheet
    if shop_groups:
        rows = emit_shop_rows(shop_groups)
        if rows:
            sheet = wb.create_sheet(title="Shop")
            write_sheet_content(sheet, rows, is_eng, eng_tbl, lang_tbl, lang_code)
            log.info("    Sheet 'Shop': %d rows", len(rows))

    # Save
    if wb.worksheets:
        wb.save(out_path)
        log.info("  → Saved: %s (%d sheets)", out_path.name, len(wb.worksheets))


# =============================================================================
# MAIN GENERATOR FUNCTION
# =============================================================================

def generate_region_datasheets() -> Dict:
    """
    Generate Region datasheets for all languages.

    Returns:
        Dict with results: {
            "category": "Region",
            "files_created": N,
            "errors": [...]
        }
    """
    result = {
        "category": "Region",
        "files_created": 0,
        "errors": [],
    }

    # Reset Korean string collection
    reset_korean_collection()

    log.info("=" * 70)
    log.info("Region Datasheet Generator")
    log.info("=" * 70)

    # Ensure output folder exists
    DATASHEET_OUTPUT.mkdir(parents=True, exist_ok=True)
    output_folder = DATASHEET_OUTPUT / "Region_LQA"
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
        # Global duplicate tracking
        global_seen: Set[str] = set()

        # 1. Knowledge lookup
        knowledge_lookup = build_knowledge_name_lookup(RESOURCE_FOLDER)

        # 2. Parse FactionGroup hierarchy
        faction_groups = parse_all_faction_groups(RESOURCE_FOLDER, knowledge_lookup, global_seen)

        # 3. Parse Standalone Factions
        standalone_factions = parse_standalone_factions(RESOURCE_FOLDER, knowledge_lookup, global_seen)

        # 4. Parse Shop data (if file exists)
        shop_file = RESOURCE_FOLDER.parent / "staticinfo_quest" / "funcnpc" / "shop_world.staticinfo.xml"
        shop_groups = parse_shop_file(shop_file, global_seen)

        # 5. Load language tables
        lang_tables = load_language_tables(LANGUAGE_FOLDER)

        if not lang_tables:
            result["errors"].append("No language tables found!")
            log.warning("No language tables found!")
            return result

        eng_tbl = lang_tables.get("eng", {})

        # 6. Generate workbooks
        log.info("Generating Excel workbooks...")
        total = len(lang_tables)

        for idx, (code, tbl) in enumerate(lang_tables.items(), 1):
            log.info("(%d/%d) Generating: %s", idx, total, code.upper())
            out_path = output_folder / f"Region_LQA_{code.upper()}.xlsx"

            if code.lower() == "eng":
                write_workbook(faction_groups, standalone_factions, shop_groups, eng_tbl, None, code, out_path)
            else:
                write_workbook(faction_groups, standalone_factions, shop_groups, eng_tbl, tbl, code, out_path)
            result["files_created"] += 1

        log.info("=" * 70)
        log.info("Done! Output folder: %s", output_folder)
        log.info("=" * 70)

    except Exception as e:
        result["errors"].append(f"Generator error: {e}")
        log.exception("Error in Region generator: %s", e)

    return result


# Allow standalone execution for testing
if __name__ == "__main__":
    result = generate_region_datasheets()
    print(f"\nResult: {result}")
