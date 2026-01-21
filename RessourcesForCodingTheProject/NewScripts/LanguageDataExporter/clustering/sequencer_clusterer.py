"""
Sequencer Clusterer - Classifies Sequencer folder content by filename patterns.

Sequencer categories are determined by filename prefix patterns:
- cd_seq_quest_* → Seq_Quest (551 files)
- cd_seq_memory_* → Seq_Memory (228 files)
- cd_seq_node_* → Seq_Node (197 files)
- cd_seq_faction_* → Seq_Faction (116 files)
- cd_boss_* → Seq_Boss (28 files)
- *bossencounter* → Seq_BossEncounter (36 files)
- cd_seq_onetimequest_* → Seq_OneTimeQuest (17 files)
- cd_minigame_* → Seq_Minigame (16 files)
- other cd_seq_* → Seq_Other
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# Sequencer filename patterns and their categories
# Order matters - more specific patterns first
# Each tuple: (pattern_type, pattern, category)
# pattern_type: "prefix" (startswith) or "contains" (in filename)
SEQUENCER_PATTERNS: List[Tuple[str, str, str]] = [
    ("prefix", "cd_seq_quest_", "Seq_Quest"),
    ("prefix", "cd_seq_memory_", "Seq_Memory"),
    ("prefix", "cd_seq_node_", "Seq_Node"),
    ("prefix", "cd_seq_faction_", "Seq_Faction"),
    ("prefix", "cd_seq_onetimequest_", "Seq_OneTimeQuest"),
    ("prefix", "cd_boss_", "Seq_Boss"),
    ("contains", "bossencounter", "Seq_BossEncounter"),
    ("prefix", "cd_minigame_", "Seq_Minigame"),
    # Generic fallback for other cd_seq_ files
    ("prefix", "cd_seq_", "Seq_Other"),
]

# Default category for files that don't match any pattern
DEFAULT_SEQUENCER_CATEGORY = "Seq_Other"


class SequencerClusterer:
    """
    Classifies Sequencer folder content based on filename patterns.

    The Sequencer folder contains files for different game sequences:
    - Quest sequences (cd_seq_quest_*)
    - Memory sequences (cd_seq_memory_*)
    - Node sequences (cd_seq_node_*)
    - Faction sequences (cd_seq_faction_*)
    - Boss sequences (cd_boss_*)
    - Boss encounters (*bossencounter*)
    - Minigame sequences (cd_minigame_*)
    """

    def __init__(self, export_folder: Path):
        """
        Initialize sequencer clusterer.

        Args:
            export_folder: Root EXPORT folder path
        """
        self.export_folder = export_folder
        self.sequencer_folder = export_folder / "Sequencer"

    def get_category(self, file_path: Path) -> str:
        """
        Get category for a sequencer file based on its filename.

        Args:
            file_path: Path to the file

        Returns:
            Sequencer category (e.g., "Seq_Quest", "Seq_Memory")
        """
        filename = file_path.name.lower()

        # Strip extension for matching
        if filename.endswith(".loc.xml"):
            filename = filename[:-8]  # Remove .loc.xml
        elif filename.endswith(".xml"):
            filename = filename[:-4]  # Remove .xml

        # Check patterns in order (most specific first)
        for pattern_type, pattern, category in SEQUENCER_PATTERNS:
            if pattern_type == "prefix":
                if filename.startswith(pattern):
                    return category
            elif pattern_type == "contains":
                if pattern in filename:
                    return category

        return DEFAULT_SEQUENCER_CATEGORY

    def get_pattern_info(self) -> List[Dict]:
        """
        Get information about all sequencer patterns.

        Returns:
            List of dicts with pattern, category, and type info
        """
        return [
            {
                "type": ptype,
                "pattern": pattern,
                "category": category,
            }
            for ptype, pattern, category in SEQUENCER_PATTERNS
        ]

    def scan_sequencer_files(self) -> Dict[str, int]:
        """
        Scan Sequencer folder and count files by category.

        Returns:
            Dict mapping category to file count
        """
        category_counts: Dict[str, int] = {}

        if not self.sequencer_folder.exists():
            logger.warning(f"Sequencer folder not found: {self.sequencer_folder}")
            return category_counts

        for xml_file in self.sequencer_folder.rglob("*.loc.xml"):
            category = self.get_category(xml_file)
            category_counts[category] = category_counts.get(category, 0) + 1

        return category_counts

    def analyze_patterns(self) -> Dict[str, List[str]]:
        """
        Analyze sequencer files and group by category.

        Returns:
            Dict mapping category to list of example filenames
        """
        category_files: Dict[str, List[str]] = {}

        if not self.sequencer_folder.exists():
            return category_files

        for xml_file in self.sequencer_folder.rglob("*.loc.xml"):
            category = self.get_category(xml_file)
            if category not in category_files:
                category_files[category] = []
            category_files[category].append(xml_file.name)

        return category_files
