"""
Skill Datasheet Generator
=========================
Extracts SkillInfo entries and links them to KnowledgeInfo for detailed descriptions.

Structure:
- SkillInfo: Key, StrKey, SkillName, SkillDesc, LearnKnowledgeKey, MaxLevel
- KnowledgeInfo: Linked via LearnKnowledgeKey, contains Name, Desc, nested children

Priority Rule:
- When multiple SkillInfo share the same LearnKnowledgeKey, the one with highest MaxLevel wins
- Losers use their own SkillDesc instead of the linked KnowledgeInfo

Output:
- ONE Excel sheet with all skills
- Indentation: SkillName (depth 0) -> Knowledge Name/Title (depth 1) -> Desc (depth 2)
"""

import re
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
    autofit_worksheet,
    THIN_BORDER,
)

log = get_logger("SkillGenerator")

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class KnowledgeNode:
    """KnowledgeInfo node - can be parent or child."""
    strkey: str
    name: str
    desc: str
    parent_key: str = ""     # Reference to parent KnowledgeInfo
    unlock_level: int = 0    # Level at which this unlocks
    children: List["KnowledgeNode"] = field(default_factory=list)


@dataclass
class SkillItem:
    """Single SkillInfo entry."""
    key: str
    strkey: str
    skill_name: str
    skill_desc: str
    learn_knowledge_key: str
    max_level: int
    # Will be filled after knowledge linking
    knowledge: Optional[KnowledgeNode] = None
    use_own_desc: bool = False  # True if lost priority for knowledge key


# =============================================================================
# STYLING
# =============================================================================

_depth0_fill = PatternFill("solid", fgColor="FFD700")  # Gold for skill names
_depth0_font = Font(bold=True, size=12)

_depth1_fill = PatternFill("solid", fgColor="B4C6E7")  # Light blue for knowledge names
_depth1_font = Font(bold=True, size=11)

_depth2_fill = PatternFill("solid", fgColor="E2EFDA")  # Light green for descriptions
_depth2_font = Font(size=10)

_depth3_fill = PatternFill("solid", fgColor="FCE4D6")  # Light orange for sub-skills
_depth3_font = Font(bold=True, size=10)

_depth4_fill = PatternFill("solid", fgColor="DDEBF7")  # Light blue for sub-skill desc
_depth4_font = Font(size=10)

_header_font = Font(bold=True, color="FFFFFF", size=11)
_header_fill = PatternFill("solid", fgColor="4F81BD")


def _get_style_for_depth(depth: int) -> Tuple[PatternFill, Font]:
    """Get style for a given depth level."""
    if depth == 0:
        return _depth0_fill, _depth0_font
    elif depth == 1:
        return _depth1_fill, _depth1_font
    elif depth == 2:
        return _depth2_fill, _depth2_font
    elif depth == 3:
        return _depth3_fill, _depth3_font
    else:
        return _depth4_fill, _depth4_font


# =============================================================================
# EXTRACTION
# =============================================================================

# Regex to parse KnowledgeList like "Knowledge_UnArmedMastery_I(2)"
_knowledge_list_re = re.compile(r'^([A-Za-z0-9_]+)\((\d+)\)$')


def extract_skill_data(folder: Path) -> Tuple[List[SkillItem], Dict[str, KnowledgeNode]]:
    """
    Scan StaticInfo folder for SkillInfo and KnowledgeInfo elements.

    Knowledge parent-child relationships are determined by LevelData.KnowledgeList.

    Returns:
    - List of SkillItem
    - Dict of KnowledgeNode by StrKey (with children attached)
    """
    skills: List[SkillItem] = []
    knowledge_map: Dict[str, KnowledgeNode] = {}
    seen_skill_keys: Set[str] = set()

    log.info("Scanning for Skill/Knowledge data in: %s", folder)

    # First pass: collect all KnowledgeInfo
    for path in sorted(iter_xml_files(folder)):
        root_el = parse_xml_file(path)
        if root_el is None:
            continue

        for kn_el in root_el.iter("KnowledgeInfo"):
            strkey = kn_el.get("StrKey") or ""
            name = kn_el.get("Name") or ""
            desc = kn_el.get("Desc") or ""

            if not strkey or strkey in knowledge_map:
                continue
            if not name and not desc:
                continue

            # Check for parent reference in LevelData
            parent_key = ""
            unlock_level = 0
            for level_data in kn_el.findall("LevelData"):
                knowledge_list = level_data.get("KnowledgeList") or ""
                if knowledge_list:
                    match = _knowledge_list_re.match(knowledge_list)
                    if match:
                        parent_key = match.group(1)
                        unlock_level = int(match.group(2))
                        break

            knowledge_map[strkey] = KnowledgeNode(
                strkey=strkey,
                name=name,
                desc=desc,
                parent_key=parent_key,
                unlock_level=unlock_level,
            )

    log.info("Found %d KnowledgeInfo entries", len(knowledge_map))

    # Build parent-child relationships
    for kn in knowledge_map.values():
        if kn.parent_key and kn.parent_key in knowledge_map:
            parent = knowledge_map[kn.parent_key]
            parent.children.append(kn)

    # Sort children by unlock_level
    for kn in knowledge_map.values():
        kn.children.sort(key=lambda c: c.unlock_level)

    # Second pass: collect SkillInfo from ONLY skillinfo_pc.staticinfo.xml
    skill_file = folder / "skillinfo" / "skillinfo_pc.staticinfo.xml"
    if not skill_file.exists():
        log.error("Skill file not found: %s", skill_file)
        return skills, knowledge_map

    log.info("Reading skills from: %s", skill_file.name)
    root_el = parse_xml_file(skill_file)
    if root_el is not None:
        for skill_el in root_el.iter("SkillInfo"):
            key = skill_el.get("Key") or ""
            strkey = skill_el.get("StrKey") or ""
            skill_name = skill_el.get("SkillName") or ""
            skill_desc = skill_el.get("SkillDesc") or ""
            learn_knowledge_key = skill_el.get("LearnKnowledgeKey") or ""
            max_level_str = skill_el.get("MaxLevel") or "1"

            try:
                max_level = int(max_level_str)
            except ValueError:
                max_level = 1

            if strkey and strkey in seen_skill_keys:
                continue
            if strkey:
                seen_skill_keys.add(strkey)

            if not skill_name and not skill_desc:
                continue

            skills.append(SkillItem(
                key=key,
                strkey=strkey,
                skill_name=skill_name,
                skill_desc=skill_desc,
                learn_knowledge_key=learn_knowledge_key,
                max_level=max_level,
            ))

    log.info("Found %d SkillInfo entries", len(skills))

    # Third pass: resolve LearnKnowledgeKey priority
    knowledge_key_to_skills: Dict[str, List[SkillItem]] = {}
    for skill in skills:
        if skill.learn_knowledge_key:
            if skill.learn_knowledge_key not in knowledge_key_to_skills:
                knowledge_key_to_skills[skill.learn_knowledge_key] = []
            knowledge_key_to_skills[skill.learn_knowledge_key].append(skill)

    # Resolve priorities
    for kn_key, skill_list in knowledge_key_to_skills.items():
        if len(skill_list) > 1:
            skill_list.sort(key=lambda s: s.max_level, reverse=True)
            for loser in skill_list[1:]:
                loser.use_own_desc = True

    # Link knowledge to skills
    linked_count = 0
    for skill in skills:
        if skill.learn_knowledge_key and not skill.use_own_desc:
            if skill.learn_knowledge_key in knowledge_map:
                skill.knowledge = knowledge_map[skill.learn_knowledge_key]
                linked_count += 1

    log.info("Linked %d skills to KnowledgeInfo", linked_count)

    return skills, knowledge_map


# =============================================================================
# ROW GENERATION
# =============================================================================

# (depth, text)
RowItem = Tuple[int, str]


def emit_knowledge_child_rows(child: KnowledgeNode, depth: int) -> List[RowItem]:
    """Emit rows for a knowledge child (sub-skill)."""
    rows: List[RowItem] = []

    if child.name:
        rows.append((depth, child.name))

    if child.desc:
        rows.append((depth + 1, child.desc))

    for nested in child.children:
        rows.extend(emit_knowledge_child_rows(nested, depth + 1))

    return rows


def emit_skill_rows(skill: SkillItem) -> List[RowItem]:
    """Generate rows for a single skill with proper nesting."""
    rows: List[RowItem] = []

    # Depth 0: SkillName (parent)
    if skill.skill_name:
        rows.append((0, skill.skill_name))

    if skill.knowledge and not skill.use_own_desc:
        kn = skill.knowledge

        # Depth 1: Parent Knowledge Desc
        if kn.desc:
            rows.append((1, kn.desc))
        elif skill.skill_desc:
            rows.append((1, skill.skill_desc))

        # Emit children (sub-skills)
        for child in kn.children:
            rows.extend(emit_knowledge_child_rows(child, 1))
    else:
        # No knowledge link or lost priority
        if skill.skill_desc:
            rows.append((1, skill.skill_desc))

    return rows


def emit_rows(skills: List[SkillItem]) -> List[RowItem]:
    """Generate all rows from skill list."""
    rows: List[RowItem] = []

    for skill in skills:
        rows.extend(emit_skill_rows(skill))

    # Postprocess: drop empty rows
    rows = [(d, t) for (d, t) in rows if t and t.strip()]

    return rows


# =============================================================================
# EXCEL WRITER
# =============================================================================

def write_workbook(
    rows: List[RowItem],
    eng_tbl: Dict[str, Tuple[str, str]],
    lang_tbl: Optional[Dict[str, Tuple[str, str]]],
    lang_code: str,
    out_path: Path,
) -> None:
    """Write one workbook with ONE sheet (Skills)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Skills"

    is_eng = lang_code.lower() == "eng"

    # Header row
    headers: List = []
    h1 = ws.cell(1, 1, "Original (KR)")
    h2 = ws.cell(1, 2, "English (ENG)")
    headers.extend([h1, h2])

    if not is_eng:
        h3 = ws.cell(1, 3, f"Translation ({lang_code.upper()})")
        headers.append(h3)

    start_extra_col = len(headers) + 1
    extra_names = ["STATUS", "COMMENT", "STRINGID", "SCREENSHOT"]
    for idx, name in enumerate(extra_names, start=start_extra_col):
        headers.append(ws.cell(1, idx, name))

    for hcell in headers:
        hcell.font = _header_font
        hcell.fill = _header_fill
        hcell.alignment = Alignment(horizontal="center", vertical="center")
        hcell.border = THIN_BORDER
    ws.row_dimensions[1].height = 25

    # Column widths
    ws.column_dimensions["A"].width = 50
    ws.column_dimensions["B"].width = 50
    ws.column_dimensions["B"].hidden = not is_eng
    if not is_eng:
        ws.column_dimensions["C"].width = 50
        ws.column_dimensions["D"].width = 12
        ws.column_dimensions["E"].width = 40
        ws.column_dimensions["F"].width = 20
        ws.column_dimensions["G"].width = 20
    else:
        ws.column_dimensions["C"].width = 12
        ws.column_dimensions["D"].width = 40
        ws.column_dimensions["E"].width = 20
        ws.column_dimensions["F"].width = 20

    # Data validation for STATUS
    status_col = 4 if not is_eng else 3
    dv = DataValidation(
        type="list",
        formula1=f'"{",".join(STATUS_OPTIONS)}"',
        allow_blank=True,
    )
    dv.error = "Invalid status"
    dv.prompt = "Select status"
    ws.add_data_validation(dv)

    # Write data rows
    for row_idx, (depth, text) in enumerate(rows, start=2):
        normalized = normalize_placeholders(text)
        eng_tr, sid = eng_tbl.get(normalized, ("", ""))
        loc_tr = ""
        if lang_tbl:
            loc_tr, sid = lang_tbl.get(normalized, (loc_tr, sid))

        fill, font = _get_style_for_depth(depth)
        indent = depth

        # Column A: Original (KR)
        c1 = ws.cell(row_idx, 1, text)
        c1.fill = fill
        c1.font = font
        c1.alignment = Alignment(indent=indent, wrap_text=True, vertical="center")
        c1.border = THIN_BORDER

        # Column B: English (ENG)
        c2 = ws.cell(row_idx, 2, eng_tr)
        c2.fill = fill
        c2.font = font
        c2.alignment = Alignment(indent=indent, wrap_text=True, vertical="center")
        c2.border = THIN_BORDER

        col_offset = 2

        # Column C: Translation (if not ENG)
        if not is_eng:
            c3 = ws.cell(row_idx, 3, loc_tr)
            c3.fill = fill
            c3.font = font
            c3.alignment = Alignment(indent=indent, wrap_text=True, vertical="center")
            c3.border = THIN_BORDER
            col_offset = 3

        # STATUS, COMMENT, STRINGID, SCREENSHOT
        for extra_idx, val in enumerate(["", "", sid, ""], start=col_offset + 1):
            cell = ws.cell(row_idx, extra_idx, val)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center")
            if extra_idx == col_offset + 3:
                cell.number_format = '@'

        # Apply STATUS data validation
        dv.add(ws.cell(row_idx, status_col))

    # Auto-fit
    autofit_worksheet(ws)

    # Save
    wb.save(out_path)
    log.info("Saved: %s (%d rows)", out_path.name, len(rows))


# =============================================================================
# MAIN GENERATOR FUNCTION
# =============================================================================

def generate_skill_datasheets() -> Dict:
    """
    Generate Skill datasheets for all languages.

    Returns:
        Dict with results: {
            "category": "Skill",
            "files_created": N,
            "errors": [...]
        }
    """
    result = {
        "category": "Skill",
        "files_created": 0,
        "errors": [],
    }

    log.info("=" * 70)
    log.info("Skill Datasheet Generator")
    log.info("=" * 70)

    # Ensure output folder exists
    DATASHEET_OUTPUT.mkdir(parents=True, exist_ok=True)
    output_folder = DATASHEET_OUTPUT / "Skill_LQA"
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
        # 1. Extract Skill and Knowledge data
        skills, knowledge_map = extract_skill_data(RESOURCE_FOLDER)
        if not skills:
            result["errors"].append("No Skill data found!")
            log.warning("No Skill data found!")
            return result

        # 2. Generate rows
        rows = emit_rows(skills)
        log.info("Generated %d rows", len(rows))

        # 3. Load language tables
        lang_tables = load_language_tables(LANGUAGE_FOLDER)
        eng_tbl = lang_tables.get("eng", {})

        if not eng_tbl:
            log.warning("English language table not found!")

        # 4. Write workbooks (one per language)
        # Always write English
        write_workbook(
            rows, eng_tbl, None, "eng",
            output_folder / "Skill_LQA_ENG.xlsx"
        )
        result["files_created"] += 1

        # Write other languages
        for lang_code, lang_tbl in lang_tables.items():
            if lang_code.lower() == "eng":
                continue
            write_workbook(
                rows, eng_tbl, lang_tbl, lang_code,
                output_folder / f"Skill_LQA_{lang_code.upper()}.xlsx"
            )
            result["files_created"] += 1

        log.info("=" * 70)
        log.info("Done! Output folder: %s", output_folder)
        log.info("=" * 70)

    except Exception as e:
        result["errors"].append(f"Generator error: {e}")
        log.exception("Error in Skill generator: %s", e)

    return result


# Allow standalone execution for testing
if __name__ == "__main__":
    result = generate_skill_datasheets()
    print(f"\nResult: {result}")
