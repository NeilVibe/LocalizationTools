"""
QA Compiler Suite - Configuration
==================================
Central configuration for all modules.

All paths, constants, categories, and mappings in one place.
"""

# Version - auto-injected by CI pipeline
VERSION = "2.0.0"

import sys
import json
from pathlib import Path

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

# Detect if running as PyInstaller executable
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent


# =============================================================================
# RUNTIME SETTINGS (loaded from settings.json)
# =============================================================================

def _load_settings() -> dict:
    """Load runtime settings from settings.json next to the executable.

    Settings file format:
    {
        "drive_letter": "D",  // Drive letter without colon (default: "F")
        "version": "1.0"
    }

    Returns:
        Dict with settings, or empty dict if file not found/invalid.
    """
    settings_file = SCRIPT_DIR / "settings.json"

    if not settings_file.exists():
        return {}

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        # Validate drive_letter if present
        if 'drive_letter' in settings:
            drive = settings['drive_letter']
            if not isinstance(drive, str) or len(drive) != 1 or not drive.isalpha():
                print(f"  WARNING: Invalid drive_letter in settings.json: '{drive}'. Using default F:")
                del settings['drive_letter']

        return settings
    except json.JSONDecodeError as e:
        print(f"  WARNING: Invalid JSON in settings.json: {e}. Using defaults.")
        return {}
    except Exception as e:
        print(f"  WARNING: Error reading settings.json: {e}. Using defaults.")
        return {}


def _apply_drive_letter(path_str: str, drive_letter: str) -> str:
    """Replace the default F: drive with the configured drive letter.

    Args:
        path_str: Path string potentially starting with F:
        drive_letter: Single letter drive (e.g., "D")

    Returns:
        Path string with drive letter replaced.
    """
    if path_str.startswith("F:") or path_str.startswith("f:"):
        return f"{drive_letter.upper()}:{path_str[2:]}"
    return path_str


# Load settings at module import time
_SETTINGS = _load_settings()
_DRIVE_LETTER = _SETTINGS.get('drive_letter', 'F')

# Log drive letter if non-default
if _DRIVE_LETTER != 'F':
    print(f"  Using custom drive letter: {_DRIVE_LETTER}:")

# QA Folder paths
QA_FOLDER = SCRIPT_DIR / "QAfolder"
QA_FOLDER_OLD = SCRIPT_DIR / "QAfolderOLD"
QA_FOLDER_NEW = SCRIPT_DIR / "QAfolderNEW"

# Tracker Update Folder (for retroactive tracker updates)
TRACKER_UPDATE_FOLDER = SCRIPT_DIR / "TrackerUpdateFolder"
TRACKER_UPDATE_QA = TRACKER_UPDATE_FOLDER / "QAfolder"
TRACKER_UPDATE_MASTER_EN = TRACKER_UPDATE_FOLDER / "Masterfolder_EN"
TRACKER_UPDATE_MASTER_CN = TRACKER_UPDATE_FOLDER / "Masterfolder_CN"

# Output paths (EN/CN separation)
MASTER_FOLDER_EN = SCRIPT_DIR / "Masterfolder_EN"
MASTER_FOLDER_CN = SCRIPT_DIR / "Masterfolder_CN"
IMAGES_FOLDER_EN = MASTER_FOLDER_EN / "Images"
IMAGES_FOLDER_CN = MASTER_FOLDER_CN / "Images"

# Progress tracker
TRACKER_PATH = SCRIPT_DIR / "LQA_Tester_ProgressTracker.xlsx"

# Tester mapping files
TESTER_MAPPING_FILE = SCRIPT_DIR / "languageTOtester_list.txt"
TESTER_TYPE_FILE = SCRIPT_DIR / "TesterType.txt"

# =============================================================================
# GENERATOR PATHS (for datasheet generators)
# =============================================================================

# Default paths - can be overridden via GUI or config file
# Drive letter is configurable via settings.json
RESOURCE_FOLDER = Path(_apply_drive_letter(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo", _DRIVE_LETTER))
LANGUAGE_FOLDER = Path(_apply_drive_letter(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc", _DRIVE_LETTER))
EXPORT_FOLDER = Path(_apply_drive_letter(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__", _DRIVE_LETTER))

# Additional export paths for coverage (strings inherently tested but not in Excel)
EXPORT_LOOKAT_FOLDER = EXPORT_FOLDER / "System" / "LookAt"   # Additional for Item
EXPORT_QUEST_FOLDER = EXPORT_FOLDER / "System" / "Quest"     # Additional for Quest

# Output folder for generated datasheets
DATASHEET_OUTPUT = SCRIPT_DIR / "GeneratedDatasheets"

# =============================================================================
# QUEST GENERATOR PATHS
# =============================================================================

# Quest-specific paths (drive letter configurable via settings.json)
QUESTGROUPINFO_FILE = Path(_apply_drive_letter(
    r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\questgroupinfo.staticinfo.xml",
    _DRIVE_LETTER
))
SCENARIO_FOLDER = Path(_apply_drive_letter(
    r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\scenario",
    _DRIVE_LETTER
))
FACTION_QUEST_FOLDER = Path(_apply_drive_letter(
    r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\quest\faction",
    _DRIVE_LETTER
))
CHALLENGE_FOLDER = Path(_apply_drive_letter(
    r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\Challenge",
    _DRIVE_LETTER
))
MINIGAME_FILE = Path(_apply_drive_letter(
    r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\contents\contents_minigame.staticinfo.xml",
    _DRIVE_LETTER
))
STRINGKEYTABLE_FILE = Path(_apply_drive_letter(
    r"F:\perforce\cd\mainline\resource\editordata\StaticInfo__\StaticInfo_StringKeyTable.xml",
    _DRIVE_LETTER
))
SEQUENCER_FOLDER = Path(_apply_drive_letter(
    r"F:\perforce\cd\mainline\resource\sequencer\stageseq",
    _DRIVE_LETTER
))
FACTIONINFO_FOLDER = Path(_apply_drive_letter(
    r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo",
    _DRIVE_LETTER
))

# Teleport reference file (optional - falls back gracefully if not found)
TELEPORT_SOURCE_FILE = SCRIPT_DIR / "Quest_LQA_ENG_1231_seon_final_final.xlsx"

# =============================================================================
# VOICE RECORDING SHEET PATH (for Quest coverage calculation)
# =============================================================================

VOICE_RECORDING_SHEET_FOLDER = Path(_apply_drive_letter(
    r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__",
    _DRIVE_LETTER
))

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
    "Contents",
    "Sequencer",  # → Master_Script.xlsx
    "Dialog",     # → Master_Script.xlsx
    "Face",       # Facial animation QA (custom processing)
]

# Category clustering: Multiple categories can merge into one master file
# Key = input category from folder name, Value = target master file category
CATEGORY_TO_MASTER = {
    "Skill": "System",      # Skill -> Master_System.xlsx
    "Help": "System",       # Help (GameAdvice) -> Master_System.xlsx
    "Gimmick": "Item",      # Gimmick -> Master_Item.xlsx
    "Sequencer": "Script",  # Sequencer -> Master_Script.xlsx
    "Dialog": "Script",     # Dialog -> Master_Script.xlsx
    # All others map to themselves (Quest->Quest, Knowledge->Knowledge, etc.)
}

# =============================================================================
# WORKER GROUPS FOR PARALLEL PROCESSING
# =============================================================================
# Categories are grouped for parallel execution. Categories in the same group
# share a master file and MUST be processed sequentially. Different groups
# CAN run in parallel since they write to different master files.
#
# Performance: With 6 workers, independent groups run concurrently.
# Expected speedup: ~2-3x on typical datasets.

WORKER_GROUPS = {
    "quest":      ["Quest"],
    "knowledge":  ["Knowledge"],
    "region":     ["Region"],
    "character":  ["Character"],
    "contents":   ["Contents"],
    "face":       ["Face"],
    "item":       ["Item", "Gimmick"],       # Must serialize (shared Master_Item.xlsx)
    "system":     ["Skill", "Help"],         # Must serialize (shared Master_System.xlsx)
    "script":     ["Sequencer", "Dialog"],   # Must serialize (shared Master_Script.xlsx)
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
    "System": {"eng": 1, "other": 1},  # CONTENT column (single column for all languages)
    "Skill": {"eng": 2, "other": 3},
    "Help": {"eng": 2, "other": 3},
    "Gimmick": {"eng": 2, "other": 3},
    "Contents": {"eng": 2, "other": 2},  # INSTRUCTIONS column (matching key, no localization)
    "Sequencer": {"eng": 2, "other": 3},  # Text column → Master_Script
    "Dialog": {"eng": 2, "other": 3},     # Text column → Master_Script
}

# =============================================================================
# SCRIPT-TYPE CATEGORIES (Sequencer, Dialog)
# =============================================================================
# Script-type categories are special:
# - ALL columns detected BY NAME (not position) using find_column_by_header()
# - Unique matching: Primary = (Text, EventName), Fallback = EventName ONLY
# - MEMO column maps to COMMENT (no separate COMMENT column)
# - NO SCREENSHOT column
# - Preprocessing optimization: Only rows with STATUS are processed

SCRIPT_COLS = {
    "translation": "Text",       # Primary: "Text", Fallback: "Translation" (no position fallback!)
    "stringid": "EventName",     # Primary: "EventName", Fallback: "STRINGID"
    "status": "STATUS",          # Column NAME for tester status
    "comment": "MEMO",           # Primary: "MEMO", Fallback: "COMMENT"
    # NO SCREENSHOT for Script-type
}

# Categories that use Script-type logic (preprocessing + name-based columns)
SCRIPT_TYPE_CATEGORIES = {"sequencer", "dialog"}

# =============================================================================
# FACE CATEGORY (Facial animation QA)
# =============================================================================
# Face category is special:
# - No standard master file (no Master_Face.xlsx template)
# - STATUS values: NO ISSUE, MISMATCH, MISSING (not ISSUE/NO ISSUE/BLOCKED/KOREAN)
# - Output: MasterMismatch_{lang}.xlsx, MasterMissing_{lang}.xlsx, MasterConflict_{lang}.xlsx
# - Separate tracker tab: "Facial" with custom schema

FACE_COLS = {
    "eventname": "EventName",
    "text": "Text",
    "group": "Group",
    "status": "STATUS",
}

FACE_STATUS_OPTIONS = ["NO ISSUE", "MISMATCH", "MISSING"]

# Categories that use Face-type logic (custom processing, no master file)
FACE_TYPE_CATEGORIES = {"face"}

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
    "border_color": "808080",      # Dark gray borders (more visible)
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
# NOTE: Accept all variants: "NO ISSUE", "NON-ISSUE", "NON ISSUE"
STATUS_OPTIONS = ["ISSUE", "NO ISSUE", "NON-ISSUE", "NON ISSUE", "BLOCKED", "KOREAN"]

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
        # Tracker Update folders
        TRACKER_UPDATE_FOLDER,
        TRACKER_UPDATE_QA,
        TRACKER_UPDATE_MASTER_EN,
        TRACKER_UPDATE_MASTER_CN,
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)


def load_tester_mapping() -> dict:
    """Load tester -> language mapping from file.

    File format (section-based):
        ENG
        김동헌
        황하연
        ...

        ZHO-CN
        김춘애
        최문석
        ...

    Returns:
        Dict mapping tester names to language codes (EN/CN)
    """
    mapping = {}
    current_lang = None

    if not TESTER_MAPPING_FILE.exists():
        print(f"  WARNING: Mapping file not found: {TESTER_MAPPING_FILE}")
        print(f"           All testers will default to EN.")
        return mapping

    with open(TESTER_MAPPING_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line == "ENG":
                current_lang = "EN"
            elif line == "ZHO-CN":
                current_lang = "CN"
            elif current_lang:
                mapping[line] = current_lang

    print(f"  Loaded {len(mapping)} tester->language mappings")
    return mapping


def load_tester_type_mapping() -> dict:
    """Load tester -> type mapping from file.

    File format (section-based):
        Text
        김민영
        황하연
        ...

        Gameplay
        김춘애
        최문석
        ...

    Returns:
        Dict mapping tester names to type ("Text" or "Gameplay")
    """
    mapping = {}
    current_type = None

    if not TESTER_TYPE_FILE.exists():
        print(f"  WARNING: Tester type file not found: {TESTER_TYPE_FILE}")
        print(f"           All testers will default to 'Unknown'.")
        return mapping

    with open(TESTER_TYPE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line == "Text":
                current_type = "Text"
            elif line == "Gameplay":
                current_type = "Gameplay"
            elif current_type:
                mapping[line] = current_type

    print(f"  Loaded {len(mapping)} tester->type mappings")
    return mapping


def get_runtime_settings() -> dict:
    """Get the current runtime settings for debugging/inspection.

    Returns:
        Dict containing:
        - settings_file: Path to settings.json
        - settings_exists: Whether settings.json was found
        - drive_letter: Currently configured drive letter
        - loaded_settings: Raw settings dict from file (or empty)
    """
    return {
        'settings_file': str(SCRIPT_DIR / "settings.json"),
        'settings_exists': (SCRIPT_DIR / "settings.json").exists(),
        'drive_letter': _DRIVE_LETTER,
        'loaded_settings': _SETTINGS.copy(),
    }


def create_default_settings_file() -> bool:
    """Create a default settings.json file with F: drive.

    Useful for users who want to customize the drive letter.

    Returns:
        True if file was created, False if it already exists.
    """
    settings_file = SCRIPT_DIR / "settings.json"

    if settings_file.exists():
        return False

    default_settings = {
        "drive_letter": "F",
        "version": "1.0"
    }

    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, indent=2)
        return True
    except Exception as e:
        print(f"  ERROR: Failed to create settings.json: {e}")
        return False
