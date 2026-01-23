"""
Skill Generator for DataListGenerator
======================================
Extracts skill names from skillinfo XML files.
"""

from pathlib import Path
from typing import List, Set

from openpyxl.styles import PatternFill

from generators.base import BaseGenerator, DataEntry
from utils.xml_parser import iter_xml_files, parse_xml_file


class SkillGenerator(BaseGenerator):
    """Generator for skill names from skillinfo XML files.

    Extracts SkillName attribute from SkillInfo elements:
    <SkillInfo Key="..." StrKey="..." SkillName="파이어볼" SkillDesc="..." />
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
        """Extract skill names from all XML files in the folder."""
        entries: List[DataEntry] = []
        seen_names: Set[str] = set()

        xml_files = iter_xml_files(self.xml_folder)

        if not xml_files:
            print(f"  No XML files found in {self.xml_folder}")
            return entries

        print(f"  Found {len(xml_files)} XML files to parse...")

        for path in xml_files:
            root = parse_xml_file(path)
            if root is None:
                continue

            source_file = path.name

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

        return entries
