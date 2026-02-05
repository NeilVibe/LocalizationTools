"""
Configuration for Language XML to Categorized Excel Converter.

Paths, constants, and configuration for the exporter.
Now integrated with utils/language_utils for language classification.

Paths can be configured via settings.json (created by installer).
"""

from pathlib import Path
import sys
import json
import logging

logger = logging.getLogger(__name__)

# Detect if running as PyInstaller bundle
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent

# =============================================================================
# Settings Loading (from installer-generated settings.json)
# =============================================================================

def _load_settings() -> dict:
    """
    Load runtime settings from settings.json if it exists.

    The installer creates this file with the user's selected drive letter.
    Falls back to defaults if file doesn't exist or is invalid.
    """
    settings_path = SCRIPT_DIR / "settings.json"

    print(f"[DEBUG CONFIG] SCRIPT_DIR = {SCRIPT_DIR}")
    print(f"[DEBUG CONFIG] Looking for settings at: {settings_path}")
    print(f"[DEBUG CONFIG] settings.json exists? {settings_path.exists()}")

    if settings_path.exists():
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            print(f"[DEBUG CONFIG] Loaded settings.json successfully!")
            print(f"[DEBUG CONFIG] Settings content: {json.dumps(settings, indent=2)}")
            logger.info(f"Loaded settings from {settings_path}")
            return settings
        except (json.JSONDecodeError, IOError) as e:
            print(f"[DEBUG CONFIG] ERROR loading settings.json: {e}")
            logger.warning(f"Failed to load settings.json: {e}")
    else:
        print(f"[DEBUG CONFIG] settings.json NOT FOUND - using defaults")

    return {}

# Load settings at module level
_SETTINGS = _load_settings()

# =============================================================================
# Perforce Paths (Source Data)
# =============================================================================

# Get paths from settings.json if available, otherwise use F: drive defaults
_loc = _SETTINGS.get("loc_folder")
_export = _SETTINGS.get("export_folder")
_vrs = _SETTINGS.get("vrs_folder")

print(f"[DEBUG CONFIG] _loc from settings = {_loc}")
print(f"[DEBUG CONFIG] _export from settings = {_export}")
print(f"[DEBUG CONFIG] _vrs from settings = {_vrs}")

# LOC folder: Contains languagedata_*.xml files
LOC_FOLDER = Path(_loc) if _loc else Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")

# EXPORT folder: Contains categorized .loc.xml files
EXPORT_FOLDER = Path(_export) if _export else Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")

# VoiceRecordingSheet folder: Contains Excel files with EventName ordering
# Used to order STORY strings (Sequencer, Dialog) in chronological story order
VOICE_RECORDING_FOLDER = Path(_vrs) if _vrs else Path(r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__")

# LOCDEV folder: Contains dev languagedata XML files for merging corrections back
_locdev = _SETTINGS.get("locdev_folder")
LOCDEV_FOLDER = Path(_locdev) if _locdev else Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\locdev__")

print(f"[DEBUG CONFIG] === FINAL PATHS ===")
print(f"[DEBUG CONFIG] LOC_FOLDER = {LOC_FOLDER}")
print(f"[DEBUG CONFIG] LOC_FOLDER exists? {LOC_FOLDER.exists()}")
print(f"[DEBUG CONFIG] EXPORT_FOLDER = {EXPORT_FOLDER}")
print(f"[DEBUG CONFIG] EXPORT_FOLDER exists? {EXPORT_FOLDER.exists()}")
print(f"[DEBUG CONFIG] VOICE_RECORDING_FOLDER = {VOICE_RECORDING_FOLDER}")
print(f"[DEBUG CONFIG] VOICE_RECORDING_FOLDER exists? {VOICE_RECORDING_FOLDER.exists()}")

# =============================================================================
# Output Configuration
# =============================================================================

# Output folder for generated Excel files
OUTPUT_FOLDER = SCRIPT_DIR / "GeneratedExcel"

# ToSubmit folder for files prepared for LQA submission
TOSUBMIT_FOLDER = SCRIPT_DIR / "ToSubmit"
SUBMIT_FILE_PATTERN = "languagedata_*.xlsx"

# =============================================================================
# Language Configuration (imported from utils for consistency)
# =============================================================================

try:
    from utils.language_utils import (
        WORD_COUNT_LANGUAGES,
        CHAR_COUNT_LANGUAGES,
        ENGLISH_COLUMN_LANGUAGES,
        NO_ENGLISH_COLUMN_LANGUAGES,
        LANGUAGE_NAMES,
        should_include_english_column,
    )

    # Asian languages that do NOT get an English column
    ASIAN_LANGUAGES = NO_ENGLISH_COLUMN_LANGUAGES

except ImportError:
    # Fallback if utils not available
    ASIAN_LANGUAGES = {"zho-cn", "zho-tw", "jpn"}

    LANGUAGE_NAMES = {
        "eng": "ENG",
        "fre": "FRE",
        "ger": "GER",
        "spa": "SPA",
        "por": "POR",
        "ita": "ITA",
        "rus": "RUS",
        "tur": "TUR",
        "pol": "POL",
        "zho-cn": "ZHO-CN",
        "zho-tw": "ZHO-TW",
        "jpn": "JPN",
        "kor": "KOR",
        "tha": "THA",
        "vie": "VIE",
        "ind": "IND",
        "msa": "MSA",
    }

# =============================================================================
# Category Configuration
# =============================================================================

# Path to category cluster configuration
CLUSTER_CONFIG = SCRIPT_DIR / "category_clusters.json"

# Default category for StringIDs not found in EXPORT
DEFAULT_CATEGORY = "Uncategorized"

# =============================================================================
# Category Configuration
# =============================================================================

# STORY categories (ordered by VoiceRecordingSheet EventName)
# These are ordered chronologically by story appearance
STORY_CATEGORIES = ["Sequencer", "AIDialog", "QuestDialog", "NarrationDialog"]

# Categories to EXCLUDE for ENG and ZHO-CN exports (voiced/story content)
# These languages get voiceover, so Dialog/Sequencer strings are handled separately
DIALOG_SEQUENCER_EXCLUSION = {"Sequencer", "AIDialog", "QuestDialog", "NarrationDialog"}

# Languages that have DIALOG/SEQUENCER exclusion (voiced languages)
LANGUAGES_WITH_DIALOG_EXCLUSION = {"eng", "zho-cn"}

# GAME_DATA categories (keyword-based, no special ordering)
GAMEDATA_CATEGORIES = [
    "Item", "Quest", "Character", "Gimmick", "Skill",
    "Knowledge", "Faction", "UI", "Region", "System_Misc"
]

# Folder mappings
STORY_FOLDERS = ["Dialog", "Sequencer"]
GAMEDATA_FOLDERS = ["System", "World", "None", "Platform"]

# =============================================================================
# Category Colors (from wordcount6.py style)
# =============================================================================

CATEGORY_COLORS = {
    # STORY categories
    "Sequencer": "FFE599",       # light-orange
    "AIDialog": "C6EFCE",        # light-green
    "QuestDialog": "C6EFCE",     # light-green
    "NarrationDialog": "C6EFCE", # light-green
    # GAME_DATA categories
    "Item": "D9D2E9",            # light-purple
    "Quest": "D9D2E9",           # light-purple
    "Character": "F8CBAD",       # light-red/peach
    "Gimmick": "D9D2E9",         # light-purple
    "Skill": "D9D2E9",           # light-purple
    "Knowledge": "D9D2E9",       # light-purple
    "Faction": "D9D2E9",         # light-purple
    "UI": "A9D08E",              # light-teal/green
    "Region": "F8CBAD",          # light-red/peach
    "System_Misc": "D9D9D9",     # light-grey
    "Uncategorized": "DDD9C4",   # light-brown
}

# =============================================================================
# XML Configuration
# =============================================================================

# Language data file pattern
LANGUAGE_FILE_PATTERN = "languagedata_*.xml"

# EXPORT file extension
EXPORT_FILE_EXTENSION = ".loc.xml"

# =============================================================================
# Excel Configuration
# =============================================================================

# Column headers for Excel output (new order with Correction column, StringID at end)
# Text State: auto-filled (KOREAN/TRANSLATED based on Korean detection)
# MEMO1/2/3: editable memo columns for QA notes
COLUMN_HEADERS_EU = ["StrOrigin", "ENG", "Str", "Correction", "Text State", "MEMO1", "MEMO2", "MEMO3", "Category", "StringID"]
COLUMN_HEADERS_ASIAN = ["StrOrigin", "Str", "Correction", "Text State", "MEMO1", "MEMO2", "MEMO3", "Category", "StringID"]

# Column widths (approximate)
COLUMN_WIDTHS = {
    "StrOrigin": 40,
    "ENG": 40,
    "Str": 40,
    "Correction": 40,
    "Text State": 12,
    "MEMO1": 30,
    "MEMO2": 30,
    "MEMO3": 30,
    "Category": 20,
    "StringID": 15,
}


# =============================================================================
# Tracker Configuration
# =============================================================================

# Correction Progress Tracker file
TRACKER_PATH = SCRIPT_DIR / "Correction_ProgressTracker.xlsx"

# Categories to track (all STORY + GAMEDATA categories)
TRACKER_CATEGORIES = [
    "Sequencer", "AIDialog", "QuestDialog", "NarrationDialog",
    "Item", "Quest", "Character", "Gimmick", "Skill",
    "Knowledge", "Faction", "UI", "Region", "System_Misc"
]


def ensure_output_folder():
    """Create output folder if it doesn't exist."""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    return OUTPUT_FOLDER


def ensure_tosubmit_folder():
    """Create ToSubmit folder if it doesn't exist."""
    TOSUBMIT_FOLDER.mkdir(parents=True, exist_ok=True)
    return TOSUBMIT_FOLDER
