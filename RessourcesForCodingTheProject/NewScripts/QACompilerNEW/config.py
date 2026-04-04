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
        "drive_letter": "D",  // Drive letter without colon (default: "D")
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
                print(f"  WARNING: Invalid drive_letter in settings.json: '{drive}'. Using default D:")
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
_DRIVE_LETTER = _SETTINGS.get('drive_letter', 'D')

# Log drive letter if non-default
if _DRIVE_LETTER != 'D':
    print(f"  Using custom drive letter: {_DRIVE_LETTER}:")

# Branch configuration (e.g., mainline, cd_beta, cd_lambda)
KNOWN_BRANCHES = ["cd_beta", "mainline", "cd_alpha", "cd_delta", "cd_lambda"]
KNOWN_DRIVES = ["C", "D", "E", "F", "G"]
_BRANCH = _SETTINGS.get('branch', 'cd_beta')

if _BRANCH != 'cd_beta':
    print(f"  Using custom branch: {_BRANCH}")


def _apply_branch(path_str: str, branch: str) -> str:
    """Replace 'mainline' in a path with the configured branch name."""
    return path_str.replace("mainline", branch)


def _build_path(template: str) -> Path:
    """Build a Path from a template, applying current drive letter and branch."""
    return Path(_apply_branch(_apply_drive_letter(template, _DRIVE_LETTER), _BRANCH))


# =============================================================================
# PATH TEMPLATES (raw strings with F: and mainline as placeholders)
# =============================================================================

_PATH_TEMPLATES = {
    "RESOURCE_FOLDER": r"F:\perforce\cd\mainline\resource\GameData\StaticInfo",
    "LANGUAGE_FOLDER": r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc",
    "EXPORT_FOLDER": r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__",
    "QUESTGROUPINFO_FILE": r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\questgroupinfo.staticinfo.xml",
    "SCENARIO_FOLDER": r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\main",
    "FACTION_QUEST_FOLDER": r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\faction",
    "CHALLENGE_FOLDER": r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\Challenge",
    "MINIGAME_FILE": r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\contents\contents_minigame.staticinfo.xml",
    "STRINGKEYTABLE_FILE": r"F:\perforce\cd\mainline\resource\editordata\StaticInfo__\StaticInfo_StringKeyTable.xml",
    "SEQUENCER_FOLDER": r"F:\perforce\cd\mainline\resource\sequencer\stageseq",
    "FACTIONINFO_FOLDER": r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo",
    "VOICE_RECORDING_SHEET_FOLDER": r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__",
    "INPUTMAP_FILE": r"F:\perforce\cd\mainline\resource\UI\inputmap.xml",
}


def _rebuild_paths():
    """Rebuild ALL Perforce-dependent globals from templates using current drive/branch."""
    global RESOURCE_FOLDER, LANGUAGE_FOLDER, EXPORT_FOLDER
    global EXPORT_LOOKAT_FOLDER, EXPORT_QUEST_FOLDER
    global QUESTGROUPINFO_FILE, SCENARIO_FOLDER, FACTION_QUEST_FOLDER
    global CHALLENGE_FOLDER, MINIGAME_FILE, STRINGKEYTABLE_FILE
    global SEQUENCER_FOLDER, FACTIONINFO_FOLDER, VOICE_RECORDING_SHEET_FOLDER
    global INPUTMAP_FILE

    RESOURCE_FOLDER = _build_path(_PATH_TEMPLATES["RESOURCE_FOLDER"])
    LANGUAGE_FOLDER = _build_path(_PATH_TEMPLATES["LANGUAGE_FOLDER"])
    EXPORT_FOLDER = _build_path(_PATH_TEMPLATES["EXPORT_FOLDER"])
    EXPORT_LOOKAT_FOLDER = EXPORT_FOLDER / "System" / "LookAt"
    EXPORT_QUEST_FOLDER = EXPORT_FOLDER / "System" / "Quest"
    QUESTGROUPINFO_FILE = _build_path(_PATH_TEMPLATES["QUESTGROUPINFO_FILE"])
    SCENARIO_FOLDER = _build_path(_PATH_TEMPLATES["SCENARIO_FOLDER"])
    FACTION_QUEST_FOLDER = _build_path(_PATH_TEMPLATES["FACTION_QUEST_FOLDER"])
    CHALLENGE_FOLDER = _build_path(_PATH_TEMPLATES["CHALLENGE_FOLDER"])
    MINIGAME_FILE = _build_path(_PATH_TEMPLATES["MINIGAME_FILE"])
    STRINGKEYTABLE_FILE = _build_path(_PATH_TEMPLATES["STRINGKEYTABLE_FILE"])
    SEQUENCER_FOLDER = _build_path(_PATH_TEMPLATES["SEQUENCER_FOLDER"])
    FACTIONINFO_FOLDER = _build_path(_PATH_TEMPLATES["FACTIONINFO_FOLDER"])
    VOICE_RECORDING_SHEET_FOLDER = _build_path(_PATH_TEMPLATES["VOICE_RECORDING_SHEET_FOLDER"])
    INPUTMAP_FILE = _build_path(_PATH_TEMPLATES["INPUTMAP_FILE"])


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
# All Perforce-dependent paths are built by _rebuild_paths() from templates.
# Call _rebuild_paths() after changing _DRIVE_LETTER or _BRANCH.

# Declare globals (populated by _rebuild_paths below)
RESOURCE_FOLDER = None
LANGUAGE_FOLDER = None
EXPORT_FOLDER = None
EXPORT_LOOKAT_FOLDER = None
EXPORT_QUEST_FOLDER = None
QUESTGROUPINFO_FILE = None
SCENARIO_FOLDER = None
FACTION_QUEST_FOLDER = None
CHALLENGE_FOLDER = None
MINIGAME_FILE = None
STRINGKEYTABLE_FILE = None
SEQUENCER_FOLDER = None
FACTIONINFO_FOLDER = None
VOICE_RECORDING_SHEET_FOLDER = None
INPUTMAP_FILE = None

# Build all paths with current drive/branch
_rebuild_paths()

# Output folder for generated datasheets
DATASHEET_OUTPUT = SCRIPT_DIR / "GeneratedDatasheets"

# Teleport reference file (optional - falls back gracefully if not found)
TELEPORT_SOURCE_FILE = SCRIPT_DIR / "Quest_LQA_ENG_1231_seon_final_final.xlsx"

# =============================================================================
# CATEGORIES
# =============================================================================

# All supported categories
CATEGORIES = [
    "Quest",
    "Knowledge",
    "Item",            # Row-per-text item datasheet (4-step pass)
    "ItemKnowledgeCluster",  # Mega item-knowledge cluster datasheet
    "Region",          # Region datasheet with DisplayName from RegionInfo
    "System",
    "Character",       # Row-per-text character datasheet with knowledge passes
    "Skill",           # Row-per-text skill datasheet (UIPosition ordered)
    "Help",
    "Gimmick",
    "Contents",
    "Sequencer",  # → Master_Script.xlsx
    "Dialog",     # → Master_Script.xlsx
    "Face",       # Facial animation QA (custom processing)
    "InputMap",   # Input binding reference (inputmap.xml)
]

# Category clustering: Multiple categories can merge into one master file
# Key = input category from folder name, Value = target master file category
CATEGORY_TO_MASTER = {
    "Help": "System",       # Help (GameAdvice) -> Master_System.xlsx
    "Gimmick": "Item",      # Gimmick -> Master_Item.xlsx
    "Sequencer": "Script",  # Sequencer -> Master_Script.xlsx
    "Dialog": "Script",     # Dialog -> Master_Script.xlsx
    # All others map to themselves (Quest->Quest, Knowledge->Knowledge, Skill->Skill, etc.)
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

# Maximum parallel workers for compilation (tune based on CPU preference)
# 6 = balanced (40-60% CPU), 8 = moderate (50-70%), 12 = aggressive (70-90%)
MAX_PARALLEL_WORKERS = 8

WORKER_GROUPS = {
    "quest":      ["Quest"],
    "knowledge":  ["Knowledge"],
    "region":     ["Region"],
    "character":  ["Character"],
    "contents":   ["Contents"],
    "face":       ["Face"],
    "item":       ["Item", "Gimmick"],       # Must serialize (shared Master_Item.xlsx)
    "itemknowledgecluster": ["ItemKnowledgeCluster"],  # Mega cluster (own master)
    "skill":        ["Skill"],                  # Row-per-text skill (UIPosition ordered)
    "system":     ["System", "Help"],          # Must serialize (shared Master_System.xlsx)
    "script":     ["Sequencer", "Dialog"],   # Must serialize (shared Master_Script.xlsx)
    "inputmap":   ["InputMap"],               # Input binding reference (standalone)
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
        테스터A
        황하연
        ...

        ZHO-CN
        테스터B
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
        테스터B
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


def _save_settings(settings_dict: dict):
    """Save essential settings to settings.json next to the executable/script."""
    settings_file = SCRIPT_DIR / "settings.json"
    # Only persist the keys that matter
    essential = {k: settings_dict[k] for k in ("drive_letter", "branch") if k in settings_dict}
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(essential, f, indent=2)
    except Exception as e:
        print(f"  ERROR: Failed to save settings.json: {e}")


def update_branch(new_branch: str):
    """Update all Perforce paths to use a new branch. Called from GUI."""
    global _BRANCH
    _BRANCH = new_branch
    _rebuild_paths()
    _SETTINGS['branch'] = new_branch
    _save_settings(_SETTINGS)
    print(f"  Branch updated to: {new_branch}")


def update_drive(new_drive: str):
    """Update all Perforce paths to use a new drive letter. Called from GUI."""
    global _DRIVE_LETTER
    clean = new_drive.strip().rstrip(':').upper()
    if not clean or not clean[0].isalpha():
        print(f"  WARNING: Invalid drive letter ignored: {new_drive!r}")
        return
    _DRIVE_LETTER = clean[0]
    _rebuild_paths()
    _SETTINGS['drive_letter'] = _DRIVE_LETTER
    _save_settings(_SETTINGS)
    print(f"  Drive updated to: {_DRIVE_LETTER}:")


def get_drive() -> str:
    """Get the current drive letter."""
    return _DRIVE_LETTER


def get_branch() -> str:
    """Get the current branch name."""
    return _BRANCH


def validate_paths() -> tuple:
    """Check if critical Perforce paths exist.

    Returns:
        (all_ok: bool, missing: list[str])
    """
    critical = {
        "RESOURCE_FOLDER": RESOURCE_FOLDER,
        "LANGUAGE_FOLDER": LANGUAGE_FOLDER,
        "EXPORT_FOLDER": EXPORT_FOLDER,
    }
    missing = [name for name, path in critical.items() if not path.exists()]
    return (len(missing) == 0, missing)


def create_default_settings_file() -> bool:
    """Create a default settings.json file with D: drive.

    Useful for users who want to customize the drive letter.

    Returns:
        True if file was created, False if it already exists.
    """
    settings_file = SCRIPT_DIR / "settings.json"

    if settings_file.exists():
        return False

    default_settings = {
        "drive_letter": "D",
        "branch": "cd_beta"
    }

    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, indent=2)
        return True
    except Exception as e:
        print(f"  ERROR: Failed to create settings.json: {e}")
        return False
