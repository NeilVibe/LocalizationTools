"""
Dialog Clusterer - Classifies Dialog folder content by folder path.

Dialog categories are determined by the subfolder structure:
- Dialog/AIDialog → Dialog_AI
- Dialog/NarrationDialog → Dialog_Narration
- Dialog/QuestDialog → Dialog_Quest
- Dialog/StageCloseDialog → Dialog_StageClose
- Dialog/OtherFolder → Dialog_Other (fallback)
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Dialog subfolder to category mapping
# Keys are normalized (lowercase) for case-insensitive matching
DIALOG_FOLDER_CATEGORIES = {
    "aidialog": "Dialog_AI",
    "narrationdialog": "Dialog_Narration",
    "questdialog": "Dialog_Quest",
    "stageclosedialog": "Dialog_StageClose",
}

# Default category for unknown dialog subfolders
DEFAULT_DIALOG_CATEGORY = "Dialog_Other"


class DialogClusterer:
    """
    Classifies Dialog folder content based on subfolder structure.

    The Dialog folder contains subfolders for different dialog types:
    - AIDialog: NPC/AI conversations
    - NarrationDialog: Narration/story text
    - QuestDialog: Quest-related dialogs
    - StageCloseDialog: Stage completion dialogs
    """

    def __init__(self, export_folder: Path):
        """
        Initialize dialog clusterer.

        Args:
            export_folder: Root EXPORT folder path
        """
        self.export_folder = export_folder
        self.dialog_folder = export_folder / "Dialog"

    def get_category(self, file_path: Path) -> str:
        """
        Get category for a dialog file based on its subfolder.

        Args:
            file_path: Path to the file

        Returns:
            Dialog category (e.g., "Dialog_Quest", "Dialog_AI")
        """
        subfolder = self._get_dialog_subfolder(file_path)

        if subfolder is None:
            return DEFAULT_DIALOG_CATEGORY

        # Normalize for case-insensitive lookup
        subfolder_lower = subfolder.lower()

        return DIALOG_FOLDER_CATEGORIES.get(subfolder_lower, DEFAULT_DIALOG_CATEGORY)

    def _get_dialog_subfolder(self, file_path: Path) -> Optional[str]:
        """
        Get the dialog subfolder name.

        For path Dialog/QuestDialog/somefile.loc.xml, returns "QuestDialog"

        Args:
            file_path: Path to the file

        Returns:
            Subfolder name, or None if file is directly in Dialog root
        """
        try:
            # Get path relative to EXPORT folder
            if file_path.is_absolute():
                relative = file_path.relative_to(self.export_folder)
            else:
                relative = file_path

            parts = relative.parts

            # Expected: Dialog/SubFolder/file.xml (at least 3 parts)
            if len(parts) < 3:
                return None

            # First part should be Dialog, second is the subfolder
            if parts[0].lower() != "dialog":
                return None

            return parts[1]

        except ValueError:
            return None

    def get_all_categories(self) -> Dict[str, str]:
        """
        Get mapping of all known dialog categories.

        Returns:
            Dict mapping subfolder names to categories
        """
        return dict(DIALOG_FOLDER_CATEGORIES)

    def scan_dialog_folders(self) -> Dict[str, int]:
        """
        Scan Dialog folder and count files by category.

        Returns:
            Dict mapping category to file count
        """
        category_counts: Dict[str, int] = {}

        if not self.dialog_folder.exists():
            logger.warning(f"Dialog folder not found: {self.dialog_folder}")
            return category_counts

        for xml_file in self.dialog_folder.rglob("*.loc.xml"):
            category = self.get_category(xml_file)
            category_counts[category] = category_counts.get(category, 0) + 1

        return category_counts
