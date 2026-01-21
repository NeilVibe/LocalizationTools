"""
Tier Classifier for Two-Tier Clustering System.

Classifies EXPORT folder paths into tiers:
- STORY: Dialog and Sequencer folders (fine-grained separation)
- GAME_DATA: Everything else (keyword-based clustering)
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Tier(Enum):
    """Classification tiers for EXPORT content."""
    STORY = "STORY"        # Dialog + Sequencer (fine-grained)
    GAME_DATA = "GAME_DATA"  # System, World, None, Platform (keyword-based)


# Top-level folders that belong to STORY tier
STORY_FOLDERS = {
    "dialog",
    "sequencer",
}

# Top-level folders that belong to GAME_DATA tier
GAME_DATA_FOLDERS = {
    "system",
    "world",
    "none",
    "platform",
}


class TierClassifier:
    """
    Classifies file paths into tiers based on top-level folder.

    The two-tier system allows different clustering strategies:
    - STORY tier: More fine-grained categories (Dialog_Quest, Seq_Memory, etc.)
    - GAME_DATA tier: Keyword-based clustering (Item, Quest, Character, etc.)
    """

    def __init__(self, export_folder: Path):
        """
        Initialize tier classifier.

        Args:
            export_folder: Root EXPORT folder path
        """
        self.export_folder = export_folder

    def get_tier(self, file_path: Path) -> Tier:
        """
        Get tier for a file based on its top-level folder.

        Args:
            file_path: Path to the file (absolute or relative to EXPORT)

        Returns:
            Tier enum value
        """
        top_level = self._get_top_level_folder(file_path)

        if top_level is None:
            return Tier.GAME_DATA  # Files in root

        top_lower = top_level.lower()

        if top_lower in STORY_FOLDERS:
            return Tier.STORY
        return Tier.GAME_DATA

    def is_dialog(self, file_path: Path) -> bool:
        """Check if file is in Dialog folder."""
        top_level = self._get_top_level_folder(file_path)
        return top_level is not None and top_level.lower() == "dialog"

    def is_sequencer(self, file_path: Path) -> bool:
        """Check if file is in Sequencer folder."""
        top_level = self._get_top_level_folder(file_path)
        return top_level is not None and top_level.lower() == "sequencer"

    def _get_top_level_folder(self, file_path: Path) -> Optional[str]:
        """
        Get the top-level folder name from a file path.

        Args:
            file_path: Absolute path or path relative to EXPORT

        Returns:
            Top-level folder name, or None if file is in EXPORT root
        """
        try:
            # Handle both absolute and relative paths
            if file_path.is_absolute():
                relative = file_path.relative_to(self.export_folder)
            else:
                relative = file_path

            parts = relative.parts

            # Need at least folder + filename
            if len(parts) < 2:
                return None

            return parts[0]

        except ValueError:
            logger.warning(f"Path not under EXPORT folder: {file_path}")
            return None

    def get_relative_path(self, file_path: Path) -> Path:
        """
        Get path relative to EXPORT folder.

        Args:
            file_path: Absolute path

        Returns:
            Path relative to EXPORT folder
        """
        try:
            return file_path.relative_to(self.export_folder)
        except ValueError:
            return file_path
