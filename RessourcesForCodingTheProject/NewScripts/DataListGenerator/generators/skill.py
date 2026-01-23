"""
Skill Generator for DataListGenerator
======================================
Extracts skill names from skillinfo_pc.staticinfo.xml ONLY.
"""

from pathlib import Path
from typing import List, Set

from openpyxl.styles import PatternFill

from generators.base import BaseGenerator, DataEntry
from utils.xml_parser import parse_xml_file


class SkillGenerator(BaseGenerator):
    """Generator for skill names from skillinfo_pc.staticinfo.xml.

    Extracts SkillName attribute from SkillInfo elements:
    <SkillInfo Key="..." StrKey="..." SkillName="파이어볼" SkillDesc="..." />

    ONLY reads from skillinfo_pc.staticinfo.xml (same as QACompiler).
    """

    name = "Skill"
    output_filename = "SkillList.xlsx"
    sheet_name = "Skill List"
    headers = ["Skill Name", "Type", "Source File"]

    def __init__(self, xml_folder: Path):
        super().__init__(xml_folder)
        self.type_colors = {
            "Skill": PatternFill(start_color="DDA0DD", end_color="DDA0DD", fill_type="solid"),  # Plum
        }

    def extract(self) -> List[DataEntry]:
        """Extract skill names from skillinfo_pc.staticinfo.xml ONLY."""
        entries: List[DataEntry] = []
        seen_names: Set[str] = set()

        # ONLY read from skillinfo_pc.staticinfo.xml (same as QACompiler)
        skill_file = self.xml_folder / "skillinfo_pc.staticinfo.xml"

        if not skill_file.exists():
            print(f"  ERROR: Skill file not found: {skill_file}")
            return entries

        print(f"  Reading from: {skill_file.name}")

        root = parse_xml_file(skill_file)
        if root is None:
            print(f"  ERROR: Failed to parse {skill_file.name}")
            return entries

        source_file = skill_file.name

        # Find all SkillInfo elements and extract SkillName
        for skill_elem in root.iter("SkillInfo"):
            skill_name = skill_elem.get("SkillName") or ""

            # Skip empty names or duplicates
            if not skill_name or skill_name in seen_names:
                continue

            # Skip placeholder names (often start with underscore or are just numbers)
            if skill_name.startswith("_") or skill_name.isdigit():
                continue

            entries.append(DataEntry(
                name=skill_name,
                entry_type="Skill",
                source_file=source_file
            ))
            seen_names.add(skill_name)

        print(f"  Found {len(entries)} unique skill names")
        return entries
