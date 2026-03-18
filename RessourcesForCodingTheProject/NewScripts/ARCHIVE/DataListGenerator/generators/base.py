"""
Base Generator for DataListGenerator
=====================================
Abstract base class for all data generators.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

from openpyxl.styles import PatternFill

from utils.excel_writer import write_data_list_excel


@dataclass
class DataEntry:
    """A generic data entry (faction, skill, etc.)."""
    name: str
    entry_type: str
    source_file: str


class BaseGenerator(ABC):
    """Abstract base class for data list generators."""

    # Subclasses must define these
    name: str = "Base"  # Display name (e.g., "Faction", "Skill")
    output_filename: str = "DataList.xlsx"  # Output file name
    sheet_name: str = "Data List"  # Excel sheet name
    headers: List[str] = ["Name", "Type", "Source File"]  # Column headers

    def __init__(self, xml_folder: Path):
        """Initialize generator with source folder.

        Args:
            xml_folder: Path to folder containing XML files to parse
        """
        self.xml_folder = xml_folder
        self.type_colors: Dict[str, PatternFill] = {}

    @abstractmethod
    def extract(self) -> List[DataEntry]:
        """Extract data entries from XML files.

        Returns:
            List of DataEntry objects
        """
        pass

    def generate_excel(self, entries: List[DataEntry], output_path: Path) -> None:
        """Generate Excel file from extracted entries.

        Args:
            entries: List of DataEntry objects
            output_path: Path to save the Excel file
        """
        write_data_list_excel(
            entries=entries,
            output_path=output_path,
            sheet_name=self.sheet_name,
            headers=self.headers,
            type_colors=self.type_colors
        )

    def run(self, output_folder: Path) -> List[DataEntry]:
        """Execute the full generation pipeline.

        Args:
            output_folder: Folder to save output file

        Returns:
            List of extracted DataEntry objects
        """
        print(f"\n{'='*50}")
        print(f"Generating {self.name} List")
        print(f"{'='*50}")

        # Check folder exists
        if not self.xml_folder.exists():
            print(f"ERROR: Folder not found: {self.xml_folder}")
            return []

        # Extract data
        print(f"Parsing XML files from {self.xml_folder}...")
        entries = self.extract()

        if not entries:
            print(f"WARNING: No {self.name.lower()} entries found!")
            return []

        # Count by type
        type_counts: Dict[str, int] = {}
        for entry in entries:
            type_counts[entry.entry_type] = type_counts.get(entry.entry_type, 0) + 1

        print(f"Extracted {len(entries)} unique {self.name.lower()} entries:")
        for entry_type, count in sorted(type_counts.items()):
            print(f"  - {entry_type}: {count}")

        # Generate Excel
        output_path = output_folder / self.output_filename
        self.generate_excel(entries, output_path)

        return entries
