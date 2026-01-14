"""
QA Compiler Suite - Configuration
==================================
Central configuration for all modules.

All paths, constants, categories, and mappings in one place.
"""

import sys
from pathlib import Path

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

# Detect if running as PyInstaller executable
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent

# QA Folder paths
QA_FOLDER = SCRIPT_DIR / "QAfolder"
QA_FOLDER_OLD = SCRIPT_DIR / "QAfolderOLD"
QA_FOLDER_NEW = SCRIPT_DIR / "QAfolderNEW"

# Output paths (EN/CN separation)
MASTER_FOLDER_EN = SCRIPT_DIR / "Masterfolder_EN"
MASTER_FOLDER_CN = SCRIPT_DIR / "Masterfolder_CN"
IMAGES_FOLDER_EN = MASTER_FOLDER_EN / "Images"
IMAGES_FOLDER_CN = MASTER_FOLDER_CN / "Images"

# Progress tracker
TRACKER_PATH = SCRIPT_DIR / "LQA_Tester_ProgressTracker.xlsx"

# Tester mapping file
TESTER_MAPPING_FILE = SCRIPT_DIR / "languageTOtester_list.txt"

# =============================================================================
# GENERATOR PATHS (for datasheet generators)
# =============================================================================

# Default paths - can be overridden via GUI or config file
RESOURCE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo")
LANGUAGE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")
EXPORT_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")

# Additional export paths for coverage (strings inherently tested but not in Excel)
EXPORT_LOOKAT_FOLDER = EXPORT_FOLDER / "System" / "LookAt"   # Additional for Item
EXPORT_QUEST_FOLDER = EXPORT_FOLDER / "System" / "Quest"     # Additional for Quest

# Output folder for generated datasheets
DATASHEET_OUTPUT = SCRIPT_DIR / "GeneratedDatasheets"

# =============================================================================
# QUEST GENERATOR PATHS
# =============================================================================

# Quest-specific paths
QUESTGROUPINFO_FILE = Path(
    r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\questgroupinfo.staticinfo.xml"
)
SCENARIO_FOLDER = Path(
    r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\scenario"
)
FACTION_QUEST_FOLDER = Path(
    r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\quest\faction"
)
CHALLENGE_FOLDER = Path(
    r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\Challenge"
)
MINIGAME_FILE = Path(
    r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\contents\contents_minigame.staticinfo.xml"
)
STRINGKEYTABLE_FILE = Path(
    r"F:\perforce\cd\mainline\resource\editordata\StaticInfo__\StaticInfo_StringKeyTable.xml"
)
SEQUENCER_FOLDER = Path(
    r"F:\perforce\cd\mainline\resource\sequencer\stageseq"
)
FACTIONINFO_FOLDER = Path(
    r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo"
)

# Teleport reference file (optional - falls back gracefully if not found)
TELEPORT_SOURCE_FILE = SCRIPT_DIR / "Quest_LQA_ENG_1231_seon_final_final.xlsx"

# =============================================================================
# VOICE RECORDING SHEET PATH (for Quest coverage calculation)
# =============================================================================

VOICE_RECORDING_SHEET_FOLDER = Path(
    r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__"
)

# =============================================================================
# CATEGORIES
# =============================================================================

# All supported categories
CATEGORIES = [
    "Quest",
    "Knowledge",
    "Item",
    "Region",
    "System",
    "Character",
    "Skill",
    "Help",
    "Gimmick",
]

# Category clustering: Multiple categories can merge into one master file
# Key = input category from folder name, Value = target master file category
CATEGORY_TO_MASTER = {
    "Skill": "System",   # Skill -> Master_System.xlsx
    "Help": "System",    # Help (GameAdvice) -> Master_System.xlsx
    "Gimmick": "Item",   # Gimmick -> Master_Item.xlsx
    # All others map to themselves (Quest->Quest, Knowledge->Knowledge, etc.)
}

# =============================================================================
# COLUMN POSITIONS BY CATEGORY
# =============================================================================

# Translation column positions (for row matching during transfer)
TRANSLATION_COLS = {
    "Quest": {"eng": 2, "other": 3},
    "Knowledge": {"eng": 2, "other": 3},
    "Character": {"eng": 2, "other": 3},
    "Region": {"eng": 2, "other": 3},
    "Item": {"eng": 5, "other": 7},  # ItemName column
    "System": {"eng": 2, "other": 3},
    "Skill": {"eng": 2, "other": 3},
    "Help": {"eng": 2, "other": 3},
    "Gimmick": {"eng": 2, "other": 3},
}

# Item description columns (for stricter Item matching)
ITEM_DESC_COLS = {
    "eng": 6,   # ItemDesc(ENG)
    "other": 8  # ItemDesc(LOC)
}

# =============================================================================
# TRACKER STYLES
# =============================================================================

TRACKER_STYLES = {
    "header_color": "4472C4",      # Blue header
    "subheader_color": "D9E2F3",   # Light blue subheader
    "alt_row_color": "F2F2F2",     # Alternating row color
    "border_color": "B4B4B4",      # Gray borders
    "total_row_color": "FFF2CC",   # Yellow for totals
    "title_color": "70AD47",       # Green for section titles
}

# =============================================================================
# EXCEL STYLING
# =============================================================================

# Colors for depth-based indentation in generators
DEPTH_COLORS = [
    "FFD700",  # Gold (depth 0 - parent)
    "ADD8E6",  # Light Blue (depth 1)
    "90EE90",  # Light Green (depth 2)
    "FFB6C1",  # Light Pink (depth 3)
    "DDA0DD",  # Plum (depth 4+)
]

# Status dropdown options
STATUS_OPTIONS = ["ISSUE", "NO ISSUE", "BLOCKED", "KOREAN"]

# Manager status options
MANAGER_STATUS_OPTIONS = ["FIXED", "REPORTED", "CHECKING", "NON ISSUE"]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_target_master_category(category: str) -> str:
    """Get the target master file category for a given input category.

    Uses CATEGORY_TO_MASTER for clustering (e.g., Skill -> System).
    Categories not in the mapping go to their own master.
    """
    return CATEGORY_TO_MASTER.get(category, category)


def ensure_folders_exist():
    """Create all required folders if they don't exist."""
    folders = [
        QA_FOLDER,
        MASTER_FOLDER_EN,
        MASTER_FOLDER_CN,
        IMAGES_FOLDER_EN,
        IMAGES_FOLDER_CN,
        DATASHEET_OUTPUT,
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)


def load_tester_mapping() -> dict:
    """Load tester -> language mapping from file.

    File format: one entry per line, "TesterName=LANG" (e.g., "John=EN")

    Returns:
        Dict mapping tester names to language codes (EN/CN)
    """
    mapping = {}
    if TESTER_MAPPING_FILE.exists():
        with open(TESTER_MAPPING_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        name, lang = parts[0].strip(), parts[1].strip().upper()
                        if lang in ('EN', 'CN'):
                            mapping[name] = lang
        print(f"  Loaded {len(mapping)} tester->language mappings")
    return mapping
