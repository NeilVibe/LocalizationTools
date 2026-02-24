"""
NEW Region Datasheet Generator
================================
Row-per-text region datasheet with up to 6 rows per entity:
  EntityName -> EntityDesc -> KnowledgeName -> KnowledgeDesc -> Knowledge2Name -> Knowledge2Desc

Each text gets its OWN row (unlike region.py which uses depth-based indentation).

Key features:
- FactionGroup -> Faction -> FactionNode hierarchy preserved via DataType labels
- Knowledge data rows (Pass 1: KnowledgeKey, Pass 2: name match from KnowledgeInfo)
- One sheet per FactionGroup (tab = GroupName)
- Standalone Factions sheet (not inside any FactionGroup)
- Shop data sheet (ShopGroup -> Stage)
- Alternating fills per entity for visual grouping
- 8-column layout matching NewItem format
"""

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from config import RESOURCE_FOLDER, LANGUAGE_FOLDER, DATASHEET_OUTPUT
from generators.base import (
    get_logger,
    parse_xml_file,
    iter_xml_files,
    load_language_tables,
    normalize_placeholders,
    autofit_worksheet,
    THIN_BORDER,
    resolve_translation,
    get_export_index,
    get_ordered_export_index,
    StringIdConsumer,
    add_status_dropdown,
)
from generators.newitem import _find_knowledge_key, load_knowledge_data

log = get_logger("NewRegionGenerator")

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
# DATA STRUCTURE
# =============================================================================

@dataclass
class RegionEntity:
    """A single region entity (group, faction, or node)."""
    strkey: str
    name_kor: str
    desc_kor: str               # FactionNode.Desc (empty for groups/factions)
    entity_type: str            # "FactionGroup", "Faction", "FactionNode"
    node_type: str              # FactionNode.Type (Main, Sub, etc.) -- empty for group/faction
    depth: int                  # Hierarchy depth
    knowledge_key: str
    knowledge_name_kor: str     # Pass 1
    knowledge_desc_kor: str     # Pass 1
    knowledge2_name_kor: str    # Pass 2
    knowledge2_desc_kor: str    # Pass 2
    source_file: str
    knowledge_source_file: str = ""
    knowledge2_source_file: str = ""
    group_name: str = ""        # For sheet organization


@dataclass
class ShopStageEntity:
    """A single shop stage entity."""
    strkey: str
    name_kor: str
    desc_kor: str
    knowledge_key: str
    knowledge_name_kor: str
    knowledge_desc_kor: str
    knowledge2_name_kor: str
    knowledge2_desc_kor: str
    source_file: str
    knowledge_source_file: str = ""
    knowledge2_source_file: str = ""
    parent_group_name: str = ""


@dataclass
class ShopGroupEntity:
    """A shop group containing stages."""
    name: str
    group: str
    source_file: str
    stages: List[ShopStageEntity] = field(default_factory=list)


# =============================================================================
# STYLING
# =============================================================================

_header_font = Font(bold=True, color="FFFFFF")
_header_fill = PatternFill("solid", fgColor="4F81BD")
_bold_font = Font(bold=True)
_fill_a = PatternFill("solid", fgColor="E2EFDA")  # Light green
_fill_b = PatternFill("solid", fgColor="FCE4D6")  # Light orange


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _sanitize_sheet_title(name: str) -> str:
    """Sanitize name for use as Excel sheet title (max 31 chars, no special)."""
    if not name:
        return "Unknown"
    clean = re.sub(r"[\\/*?:\[\]]", "_", name)
    clean = clean.strip()
    if len(clean) > 31:
        clean = clean[:31]
    return clean if clean else "Unknown"


def _resolve_knowledge(
    elem,
    knowledge_map: Dict[str, Tuple[str, str, str]],
    knowledge_name_index: Dict[str, List[Tuple[str, str, str]]],
    entity_name: str,
) -> Tuple[str, str, str, str, str, str, str]:
    """Resolve knowledge data for an element via Pass 1 and Pass 2.

    Pass 1: KnowledgeKey/RewardKnowledgeKey direct lookup in knowledge_map
    Pass 2: EntityName == KnowledgeInfo.Name in knowledge_name_index (skip if same strkey as Pass 1)

    Returns:
        (knowledge_key, kn_name, kn_desc, kn_src, kn2_name, kn2_desc, kn2_src)
    """
    knowledge_key = _find_knowledge_key(elem)

    # Pass 1: Direct key lookup
    kn_name = ""
    kn_desc = ""
    kn_src = ""
    pass1_strkey = ""
    if knowledge_key and knowledge_key in knowledge_map:
        kn_name, kn_desc, kn_src = knowledge_map[knowledge_key]
        pass1_strkey = knowledge_key

    # Pass 2: Identical name match (EntityName == KnowledgeInfo.Name)
    kn2_name = ""
    kn2_desc = ""
    kn2_src = ""
    if entity_name and entity_name in knowledge_name_index:
        for kn_strkey, k_desc, k_src in knowledge_name_index[entity_name]:
            if kn_strkey != pass1_strkey:
                kn2_name = entity_name
                kn2_desc = k_desc
                kn2_src = k_src
                break

    return knowledge_key, kn_name, kn_desc, kn_src, kn2_name, kn2_desc, kn2_src


# =============================================================================
# FACTION PARSING
# =============================================================================

def _parse_faction_node_recursive(
    elem,
    knowledge_map: Dict[str, Tuple[str, str, str]],
    knowledge_name_index: Dict[str, List[Tuple[str, str, str]]],
    global_seen: Set[str],
    depth: int,
    source_file: str,
    group_name: str,
    entities: List[RegionEntity],
) -> None:
    """Parse a FactionNode element and all its nested children into entities list."""
    strkey = elem.get("StrKey") or ""
    name = elem.get("Name") or ""
    desc = elem.get("Desc") or ""
    node_type = elem.get("Type") or ""

    if not name:
        # Still recurse children even if this node has no name
        for child in elem:
            if child.tag == "FactionNode":
                _parse_faction_node_recursive(
                    child, knowledge_map, knowledge_name_index,
                    global_seen, depth + 1, source_file, group_name, entities,
                )
        return

    # Duplicate check
    if strkey:
        if strkey in global_seen:
            return
        global_seen.add(strkey)

    # Resolve knowledge
    kn_key, kn_name, kn_desc, kn_src, kn2_name, kn2_desc, kn2_src = _resolve_knowledge(
        elem, knowledge_map, knowledge_name_index, name,
    )

    # Collect Korean strings
    _collect_korean_string(name)
    _collect_korean_string(desc)
    _collect_korean_string(kn_name)
    _collect_korean_string(kn_desc)
    _collect_korean_string(kn2_name)
    _collect_korean_string(kn2_desc)

    entities.append(RegionEntity(
        strkey=strkey,
        name_kor=name,
        desc_kor=desc,
        entity_type="FactionNode",
        node_type=node_type,
        depth=depth,
        knowledge_key=kn_key,
        knowledge_name_kor=kn_name,
        knowledge_desc_kor=kn_desc,
        knowledge2_name_kor=kn2_name,
        knowledge2_desc_kor=kn2_desc,
        source_file=source_file,
        knowledge_source_file=kn_src,
        knowledge2_source_file=kn2_src,
        group_name=group_name,
    ))

    # Parse nested FactionNode children
    for child in elem:
        if child.tag == "FactionNode":
            _parse_faction_node_recursive(
                child, knowledge_map, knowledge_name_index,
                global_seen, depth + 1, source_file, group_name, entities,
            )


def _parse_faction(
    elem,
    knowledge_map: Dict[str, Tuple[str, str, str]],
    knowledge_name_index: Dict[str, List[Tuple[str, str, str]]],
    global_seen: Set[str],
    depth: int,
    source_file: str,
    group_name: str,
    entities: List[RegionEntity],
) -> None:
    """Parse a Faction element and all its FactionNode children."""
    strkey = elem.get("StrKey") or ""
    name = elem.get("Name") or ""

    if not name:
        return

    # Duplicate check (no strkey check for Factions without StrKey)
    if strkey:
        if strkey in global_seen:
            return
        global_seen.add(strkey)

    # Resolve knowledge
    kn_key, kn_name, kn_desc, kn_src, kn2_name, kn2_desc, kn2_src = _resolve_knowledge(
        elem, knowledge_map, knowledge_name_index, name,
    )

    # Collect Korean strings
    _collect_korean_string(name)
    _collect_korean_string(kn_name)
    _collect_korean_string(kn_desc)
    _collect_korean_string(kn2_name)
    _collect_korean_string(kn2_desc)

    entities.append(RegionEntity(
        strkey=strkey,
        name_kor=name,
        desc_kor="",  # Factions have no Desc
        entity_type="Faction",
        node_type="",
        depth=depth,
        knowledge_key=kn_key,
        knowledge_name_kor=kn_name,
        knowledge_desc_kor=kn_desc,
        knowledge2_name_kor=kn2_name,
        knowledge2_desc_kor=kn2_desc,
        source_file=source_file,
        knowledge_source_file=kn_src,
        knowledge2_source_file=kn2_src,
        group_name=group_name,
    ))

    # Parse FactionNode children
    for child in elem:
        if child.tag == "FactionNode":
            _parse_faction_node_recursive(
                child, knowledge_map, knowledge_name_index,
                global_seen, depth + 1, source_file, group_name, entities,
            )


def parse_all_faction_data(
    folder: Path,
    knowledge_map: Dict[str, Tuple[str, str, str]],
    knowledge_name_index: Dict[str, List[Tuple[str, str, str]]],
    global_seen: Set[str],
) -> Tuple[Dict[str, List[RegionEntity]], List[RegionEntity]]:
    """Parse all faction data from XML files.

    Returns:
        (group_entities, standalone_entities) where:
        - group_entities: {GroupName: [RegionEntity, ...]} for each FactionGroup
        - standalone_entities: [RegionEntity, ...] for Factions not in any FactionGroup
    """
    log.info("Parsing FactionGroup -> Faction -> FactionNode hierarchy...")

    group_entities: Dict[str, List[RegionEntity]] = OrderedDict()
    standalone_entities: List[RegionEntity] = []

    total_groups = 0
    total_factions = 0
    total_nodes = 0

    for path in sorted(iter_xml_files(folder)):
        root_el = parse_xml_file(path)
        if root_el is None:
            continue
        source_file = path.name

        # Track which Faction StrKeys are inside FactionGroups (for standalone detection)
        factions_in_groups: Set[str] = set()

        # Parse FactionGroups
        for fg_elem in root_el.iter("FactionGroup"):
            fg_strkey = fg_elem.get("StrKey") or ""
            fg_group_name = fg_elem.get("GroupName") or ""

            if not fg_group_name:
                continue

            # Duplicate check for FactionGroup itself
            if fg_strkey:
                if fg_strkey in global_seen:
                    continue
                global_seen.add(fg_strkey)

            # Resolve knowledge for the FactionGroup
            kn_key, kn_name, kn_desc, kn_src, kn2_name, kn2_desc, kn2_src = _resolve_knowledge(
                fg_elem, knowledge_map, knowledge_name_index, fg_group_name,
            )

            # Collect Korean strings
            _collect_korean_string(fg_group_name)
            _collect_korean_string(kn_name)
            _collect_korean_string(kn_desc)
            _collect_korean_string(kn2_name)
            _collect_korean_string(kn2_desc)

            entities: List[RegionEntity] = []

            # Add FactionGroup entity itself
            entities.append(RegionEntity(
                strkey=fg_strkey,
                name_kor=fg_group_name,
                desc_kor="",
                entity_type="FactionGroup",
                node_type="",
                depth=0,
                knowledge_key=kn_key,
                knowledge_name_kor=kn_name,
                knowledge_desc_kor=kn_desc,
                knowledge2_name_kor=kn2_name,
                knowledge2_desc_kor=kn2_desc,
                source_file=source_file,
                knowledge_source_file=kn_src,
                knowledge2_source_file=kn2_src,
                group_name=fg_group_name,
            ))
            total_groups += 1

            # Parse child Factions
            for faction_elem in fg_elem:
                if faction_elem.tag == "Faction":
                    faction_sk = faction_elem.get("StrKey") or ""
                    if faction_sk:
                        factions_in_groups.add(faction_sk)
                    _parse_faction(
                        faction_elem, knowledge_map, knowledge_name_index,
                        global_seen, 1, source_file, fg_group_name, entities,
                    )

            if entities:
                # Merge into existing group if same GroupName already parsed from another file
                if fg_group_name in group_entities:
                    group_entities[fg_group_name].extend(entities)
                else:
                    group_entities[fg_group_name] = entities

        # Parse standalone Factions (direct children of root, not in any FactionGroup)
        for child in root_el:
            if child.tag == "Faction":
                child_sk = child.get("StrKey") or ""
                if child_sk and child_sk in factions_in_groups:
                    continue
                standalone: List[RegionEntity] = []
                _parse_faction(
                    child, knowledge_map, knowledge_name_index,
                    global_seen, 0, source_file, "Standalone", standalone,
                )
                standalone_entities.extend(standalone)

    # Count totals
    for entities in group_entities.values():
        for e in entities:
            if e.entity_type == "Faction":
                total_factions += 1
            elif e.entity_type == "FactionNode":
                total_nodes += 1
    for e in standalone_entities:
        if e.entity_type == "Faction":
            total_factions += 1
        elif e.entity_type == "FactionNode":
            total_nodes += 1

    log.info("  -> %d FactionGroups, %d Factions, %d FactionNodes, %d standalone entities",
             total_groups, total_factions, total_nodes, len(standalone_entities))

    return group_entities, standalone_entities


# =============================================================================
# SHOP PARSING
# =============================================================================

def parse_shop_data(
    shop_path: Path,
    knowledge_map: Dict[str, Tuple[str, str, str]],
    knowledge_name_index: Dict[str, List[Tuple[str, str, str]]],
    global_seen: Set[str],
) -> List[ShopGroupEntity]:
    """Parse shop file for shop stage data with knowledge linking."""
    if not shop_path.exists():
        log.warning("Shop file not found: %s", shop_path)
        return []

    log.info("Parsing shop file: %s", shop_path)

    root_el = parse_xml_file(shop_path)
    if root_el is None:
        log.error("Failed to parse shop file")
        return []

    source_file = shop_path.name
    merged_groups: OrderedDict[str, ShopGroupEntity] = OrderedDict()

    for child in root_el:
        if not isinstance(child.tag, str):
            continue

        group_name = child.get("Name") or ""
        group_val = child.get("Group") or ""

        if not group_name:
            continue

        new_stages: List[ShopStageEntity] = []
        for stage_el in child.iter("Stage"):
            strkey = stage_el.get("StrKey") or ""
            stage_name = stage_el.get("Name") or ""
            desc = stage_el.get("Desc") or ""

            if not stage_name:
                continue

            if strkey:
                if strkey in global_seen:
                    continue
                global_seen.add(strkey)

            # Resolve knowledge for stage
            kn_key, kn_name, kn_desc, kn_src, kn2_name, kn2_desc, kn2_src = _resolve_knowledge(
                stage_el, knowledge_map, knowledge_name_index, stage_name,
            )

            # Collect Korean strings
            _collect_korean_string(stage_name)
            _collect_korean_string(desc)
            _collect_korean_string(kn_name)
            _collect_korean_string(kn_desc)
            _collect_korean_string(kn2_name)
            _collect_korean_string(kn2_desc)

            new_stages.append(ShopStageEntity(
                strkey=strkey,
                name_kor=stage_name,
                desc_kor=desc,
                knowledge_key=kn_key,
                knowledge_name_kor=kn_name,
                knowledge_desc_kor=kn_desc,
                knowledge2_name_kor=kn2_name,
                knowledge2_desc_kor=kn2_desc,
                source_file=source_file,
                knowledge_source_file=kn_src,
                knowledge2_source_file=kn2_src,
                parent_group_name=group_name,
            ))

        if not new_stages:
            continue

        if group_name in merged_groups:
            merged_groups[group_name].stages.extend(new_stages)
        else:
            merged_groups[group_name] = ShopGroupEntity(
                name=group_name,
                group=group_val,
                source_file=source_file,
                stages=new_stages,
            )

    shop_groups = list(merged_groups.values())
    total_stages = sum(len(g.stages) for g in shop_groups)
    log.info("  -> %d shop groups, %d stages", len(shop_groups), total_stages)

    # Collect shop group names too
    for sg in shop_groups:
        _collect_korean_string(sg.name)

    return shop_groups


# =============================================================================
# EXCEL WRITER (row-per-text format)
# =============================================================================

def _write_entity_rows(
    ws,
    entity_type_label: str,
    name_kor: str,
    desc_kor: str,
    knowledge_name_kor: str,
    knowledge_desc_kor: str,
    knowledge2_name_kor: str,
    knowledge2_desc_kor: str,
    source_file: str,
    knowledge_source_file: str,
    knowledge2_source_file: str,
    lang_tbl: Dict[str, List[Tuple[str, str]]],
    export_index: Dict[str, Set[str]],
    consumer: Optional[StringIdConsumer],
    current_fill: PatternFill,
    excel_row: int,
) -> int:
    """Write up to 6 rows for a single entity. Returns next excel_row."""

    def _write_row(data_type: str, kor_text: str, src_file: str, row: int) -> int:
        """Write a single data row and return next row number."""
        trans, sid = resolve_translation(kor_text, lang_tbl, src_file, export_index, consumer=consumer)
        vals = [data_type, src_file, kor_text, trans, "", "", "", sid]
        for ci, val in enumerate(vals, 1):
            cell = ws.cell(row, ci, val)
            cell.fill = current_fill
            cell.border = THIN_BORDER
            if ci == 5:  # STATUS
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        # STRINGID as text format (prevent scientific notation)
        ws.cell(row, 8).number_format = '@'
        return row + 1

    # 1. Entity Name (always output)
    excel_row = _write_row(entity_type_label, name_kor, source_file, excel_row)

    # 2. Entity Desc (FactionNode only, skip if empty)
    if desc_kor:
        excel_row = _write_row(entity_type_label, desc_kor, source_file, excel_row)

    # 3. KnowledgeData -- Name (Pass 1, skip if empty)
    if knowledge_name_kor:
        excel_row = _write_row("KnowledgeData", knowledge_name_kor, knowledge_source_file, excel_row)

    # 4. KnowledgeData -- Desc (Pass 1, skip if empty)
    if knowledge_desc_kor:
        excel_row = _write_row("KnowledgeData", knowledge_desc_kor, knowledge_source_file, excel_row)

    # 5. KnowledgeData2 -- Name (Pass 2, skip if empty)
    if knowledge2_name_kor:
        excel_row = _write_row("KnowledgeData2", knowledge2_name_kor, knowledge2_source_file, excel_row)

    # 6. KnowledgeData2 -- Desc (Pass 2, skip if empty)
    if knowledge2_desc_kor:
        excel_row = _write_row("KnowledgeData2", knowledge2_desc_kor, knowledge2_source_file, excel_row)

    return excel_row


def write_newregion_excel(
    group_entities: Dict[str, List[RegionEntity]],
    standalone_entities: List[RegionEntity],
    shop_groups: List[ShopGroupEntity],
    lang_tbl: Dict[str, List[Tuple[str, str]]],
    lang_code: str,
    export_index: Dict[str, Set[str]],
    output_path: Path,
) -> None:
    """Write NewRegion Excel with one row per text field.

    8 columns: DataType | Filename | SourceText (KR) | Translation | STATUS | COMMENT | SCREENSHOT | STRINGID
    """
    wb = Workbook()
    wb.remove(wb.active)
    code = lang_code.upper()

    headers = [
        "DataType",
        "Filename",
        "SourceText (KR)",
        f"Translation ({code})",
        "STATUS",
        "COMMENT",
        "SCREENSHOT",
        "STRINGID",
    ]

    # Order-based StringID consumer (fresh per language write pass)
    ordered_idx = get_ordered_export_index()
    consumer = StringIdConsumer(ordered_idx)

    used_titles: Set[str] = set()

    def _get_unique_title(base: str) -> str:
        """Get unique sheet title, handling duplicates."""
        title = _sanitize_sheet_title(base)
        if title not in used_titles:
            used_titles.add(title)
            return title
        cnt = 1
        while True:
            candidate = f"{title[:28]}_{cnt}"
            if candidate not in used_titles:
                used_titles.add(candidate)
                return candidate
            cnt += 1

    def _write_header(ws) -> None:
        """Write header row to worksheet."""
        for col_idx, txt in enumerate(headers, 1):
            cell = ws.cell(1, col_idx, txt)
            cell.font = _header_font
            cell.fill = _header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = THIN_BORDER

    def _finalize_sheet(ws, excel_row: int) -> None:
        """Apply cosmetics: auto-filter, freeze panes, status dropdown, autofit."""
        if excel_row > 2:
            ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{excel_row - 1}"
        ws.freeze_panes = "A2"
        add_status_dropdown(ws, col=5)
        autofit_worksheet(ws)

    # --- FactionGroup sheets ---
    for group_name, entities in group_entities.items():
        if not entities:
            continue

        title = _get_unique_title(group_name)
        ws = wb.create_sheet(title)
        _write_header(ws)

        excel_row = 2
        current_fill = _fill_a
        last_strkey = None

        for entity in entities:
            # Alternate fill per entity for visual grouping
            entity_id = entity.strkey or entity.name_kor
            if last_strkey is not None and entity_id != last_strkey:
                current_fill = _fill_b if current_fill == _fill_a else _fill_a
            last_strkey = entity_id

            # Determine DataType label based on entity_type
            if entity.entity_type == "FactionGroup":
                label = "FactionGroupData"
            elif entity.entity_type == "Faction":
                label = "FactionData"
            else:
                label = "FactionNodeData"

            excel_row = _write_entity_rows(
                ws, label,
                entity.name_kor, entity.desc_kor,
                entity.knowledge_name_kor, entity.knowledge_desc_kor,
                entity.knowledge2_name_kor, entity.knowledge2_desc_kor,
                entity.source_file, entity.knowledge_source_file, entity.knowledge2_source_file,
                lang_tbl, export_index, consumer, current_fill, excel_row,
            )

        _finalize_sheet(ws, excel_row)
        log.info("  Sheet '%s': %d rows", title, excel_row - 2)

    # --- Standalone Factions sheet ---
    if standalone_entities:
        title = _get_unique_title("Standalone")
        ws = wb.create_sheet(title)
        _write_header(ws)

        excel_row = 2
        current_fill = _fill_a
        last_strkey = None

        for entity in standalone_entities:
            entity_id = entity.strkey or entity.name_kor
            if last_strkey is not None and entity_id != last_strkey:
                current_fill = _fill_b if current_fill == _fill_a else _fill_a
            last_strkey = entity_id

            if entity.entity_type == "Faction":
                label = "FactionData"
            else:
                label = "FactionNodeData"

            excel_row = _write_entity_rows(
                ws, label,
                entity.name_kor, entity.desc_kor,
                entity.knowledge_name_kor, entity.knowledge_desc_kor,
                entity.knowledge2_name_kor, entity.knowledge2_desc_kor,
                entity.source_file, entity.knowledge_source_file, entity.knowledge2_source_file,
                lang_tbl, export_index, consumer, current_fill, excel_row,
            )

        _finalize_sheet(ws, excel_row)
        log.info("  Sheet '%s': %d rows", title, excel_row - 2)

    # --- Shop sheet ---
    if shop_groups:
        title = _get_unique_title("Shop")
        ws = wb.create_sheet(title)
        _write_header(ws)

        excel_row = 2
        current_fill = _fill_a
        last_entity_id = None

        for shop_group in shop_groups:
            # Write ShopGroup name row
            group_id = f"shopgroup_{shop_group.name}"
            if last_entity_id is not None and group_id != last_entity_id:
                current_fill = _fill_b if current_fill == _fill_a else _fill_a
            last_entity_id = group_id

            # ShopGroup name row (single row, no knowledge)
            trans, sid = resolve_translation(
                shop_group.name, lang_tbl, shop_group.source_file, export_index, consumer=consumer,
            )
            vals = ["ShopGroupData", shop_group.source_file, shop_group.name, trans, "", "", "", sid]
            for ci, val in enumerate(vals, 1):
                cell = ws.cell(excel_row, ci, val)
                cell.fill = current_fill
                cell.border = THIN_BORDER
                if ci == 5:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            ws.cell(excel_row, 8).number_format = '@'
            excel_row += 1

            # Write stages
            for stage in shop_group.stages:
                stage_id = stage.strkey or stage.name_kor
                if last_entity_id is not None and stage_id != last_entity_id:
                    current_fill = _fill_b if current_fill == _fill_a else _fill_a
                last_entity_id = stage_id

                excel_row = _write_entity_rows(
                    ws, "ShopStageData",
                    stage.name_kor, stage.desc_kor,
                    stage.knowledge_name_kor, stage.knowledge_desc_kor,
                    stage.knowledge2_name_kor, stage.knowledge2_desc_kor,
                    stage.source_file, stage.knowledge_source_file, stage.knowledge2_source_file,
                    lang_tbl, export_index, consumer, current_fill, excel_row,
                )

        _finalize_sheet(ws, excel_row)
        log.info("  Sheet 'Shop': %d rows", excel_row - 2)

    # Save workbook
    if wb.worksheets:
        wb.save(output_path)
        log.info("NewRegion Excel saved: %s (%d sheets)", output_path.name, len(wb.worksheets))
    else:
        log.warning("No sheets generated for %s", output_path.name)


# =============================================================================
# MAIN GENERATOR FUNCTION
# =============================================================================

def generate_newregion_datasheets() -> Dict:
    """
    Generate NewRegion datasheets for all languages.

    Pipeline:
    1. Load language tables
    2. Load knowledge data (Name + Desc + source_file for Pass 1 + Pass 2)
    3. Parse FactionGroup -> Faction -> FactionNode hierarchy
    4. Parse standalone Factions (not in any FactionGroup)
    5. Parse Shop data
    6. Get EXPORT index (for StringID disambiguation)
    7. For each language: write row-per-text Excel

    Returns:
        Dict with results: {
            "category": "NewRegion",
            "files_created": N,
            "errors": [...]
        }
    """
    result: Dict = {
        "category": "NewRegion",
        "files_created": 0,
        "errors": [],
    }

    # Reset Korean string collection
    reset_korean_collection()

    log.info("=" * 70)
    log.info("NEW Region Datasheet Generator")
    log.info("=" * 70)

    # Ensure output folder exists
    DATASHEET_OUTPUT.mkdir(parents=True, exist_ok=True)
    output_folder = DATASHEET_OUTPUT / "NewRegionData_Map_All"
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

        # 1. Load language tables
        lang_tables = load_language_tables(LANGUAGE_FOLDER)

        if not lang_tables:
            result["errors"].append("No language tables found!")
            log.warning("No language tables found!")
            return result

        # 2. Load knowledge data (map + name index for Pass 2)
        knowledge_folder = RESOURCE_FOLDER / "knowledgeinfo"
        knowledge_map, knowledge_name_index = load_knowledge_data(knowledge_folder)

        # 3+4. Parse all faction data (groups + standalone)
        group_entities, standalone_entities = parse_all_faction_data(
            RESOURCE_FOLDER, knowledge_map, knowledge_name_index, global_seen,
        )

        # 5. Parse Shop data
        shop_file = RESOURCE_FOLDER.parent / "staticinfo_quest" / "funcnpc" / "shop_world.staticinfo.xml"
        shop_groups = parse_shop_data(shop_file, knowledge_map, knowledge_name_index, global_seen)

        # Check if we have any data at all
        total_entities = sum(len(e) for e in group_entities.values()) + len(standalone_entities)
        total_shop_stages = sum(len(g.stages) for g in shop_groups)
        if total_entities == 0 and total_shop_stages == 0:
            result["errors"].append("No region/faction/shop data found!")
            log.warning("No region/faction/shop data found!")
            return result

        # 6. Get EXPORT index
        export_index = get_export_index()

        # 7. Generate Excel per language
        log.info("Generating Excel workbooks...")
        total = len(lang_tables)

        for idx, (code, tbl) in enumerate(lang_tables.items(), 1):
            log.info("(%d/%d) Language %s", idx, total, code.upper())
            excel_path = output_folder / f"NewRegion_LQA_{code.upper()}.xlsx"
            write_newregion_excel(
                group_entities, standalone_entities, shop_groups,
                tbl, code, export_index, excel_path,
            )
            result["files_created"] += 1

        log.info("=" * 70)
        log.info("Done! Output folder: %s", output_folder)
        log.info("=" * 70)

    except Exception as e:
        result["errors"].append(f"Generator error: {e}")
        log.exception("Error in NewRegion generator: %s", e)

    return result


# Allow standalone execution for testing
if __name__ == "__main__":
    result = generate_newregion_datasheets()
    print(f"\nResult: {result}")
