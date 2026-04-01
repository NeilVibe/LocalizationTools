"""
Configuration for Language XML to Categorized Excel Converter.

Paths, constants, and configuration for the exporter.
Now integrated with utils/language_utils for language classification.

Paths can be configured via settings.json (created by installer).
"""
from __future__ import annotations

# Version - auto-injected by CI pipeline
VERSION = "1.0.0"

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

    if settings_path.exists():
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            logger.info(f"Loaded settings from {settings_path}")
            return settings
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load settings.json: {e}")
    return {}

# Load settings at module level
_SETTINGS = _load_settings()

# =============================================================================
# Branch & Drive Configuration
# =============================================================================

KNOWN_BRANCHES = ["mainline", "cd_beta", "cd_alpha", "cd_lambda"]

_DRIVE_LETTER = _SETTINGS.get('drive_letter', 'F')
_BRANCH = _SETTINGS.get('branch', 'mainline')


def _apply_drive_letter(path_str: str, drive_letter: str) -> str:
    """Replace F: drive prefix with configured drive letter."""
    if path_str.startswith("F:") or path_str.startswith("f:"):
        return f"{drive_letter.upper()}:{path_str[2:]}"
    return path_str


def _apply_branch(path_str: str, branch: str) -> str:
    """Replace 'mainline' in path with configured branch."""
    return path_str.replace("mainline", branch)


def _build_path(template: str) -> Path:
    """Build a Path from template, applying drive letter and branch."""
    return Path(_apply_branch(_apply_drive_letter(template, _DRIVE_LETTER), _BRANCH))


def _save_settings(settings_dict: dict):
    """Save only essential keys to settings.json.

    Computed paths (loc_folder, export_folder, vrs_folder) are rebuilt
    dynamically from drive_letter + branch at runtime, so persisting
    them is redundant and confusing.  Only the keys that the installer
    or user explicitly sets are written back.
    """
    _ESSENTIAL_KEYS = {"drive_letter", "branch", "description"}
    trimmed = {k: v for k, v in settings_dict.items() if k in _ESSENTIAL_KEYS}

    settings_file = SCRIPT_DIR / "settings.json"
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(trimmed, f, indent=2)
        logger.info(f"Saved settings to {settings_file}")
    except Exception as e:
        logger.error(f"Failed to save settings.json: {e}")


def _rebuild_paths():
    """Rebuild all path globals from current _DRIVE_LETTER and _BRANCH."""
    global LOC_FOLDER, EXPORT_FOLDER, VOICE_RECORDING_FOLDER
    global AUDIO_FOLDER_EN, AUDIO_FOLDER_KR, AUDIO_FOLDER_ZH, LANG_TO_AUDIO_FOLDER
    global STATICINFO_FOLDER, STATICINFO_QUEST_FOLDER, STATICINFO_DIALOG_FOLDER
    LOC_FOLDER = _build_path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")
    EXPORT_FOLDER = _build_path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")
    STATICINFO_FOLDER = _build_path(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo")
    STATICINFO_QUEST_FOLDER = _build_path(r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest")
    STATICINFO_DIALOG_FOLDER = _build_path(r"F:\perforce\cd\mainline\resource\GameData\staticinfo_dialog")
    VOICE_RECORDING_FOLDER = _build_path(r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__")
    AUDIO_FOLDER_EN = _build_path(r"F:\perforce\cd\mainline\resource\sound\windows\English(US)")
    AUDIO_FOLDER_KR = _build_path(r"F:\perforce\cd\mainline\resource\sound\windows\Korean")
    AUDIO_FOLDER_ZH = _build_path(r"F:\perforce\cd\mainline\resource\sound\windows\Chinese(PRC)")
    LANG_TO_AUDIO_FOLDER = {
        "eng": AUDIO_FOLDER_EN,
        "kor": AUDIO_FOLDER_KR,
        "zho-cn": AUDIO_FOLDER_ZH,
    }


def update_branch(new_branch: str):
    """Update all paths to use new branch. Called from GUI."""
    global _BRANCH

    _BRANCH = new_branch
    _rebuild_paths()

    _SETTINGS['branch'] = new_branch
    _save_settings(_SETTINGS)

    logger.info(f"Branch updated to: {new_branch}")


def get_branch() -> str:
    """Get the current branch name."""
    return _BRANCH


def update_drive(new_drive: str):
    """Update all paths to use new drive letter. Called from GUI."""
    global _DRIVE_LETTER

    # Sanitize: strip whitespace/colon, take first char only, must be alpha
    clean = new_drive.strip().rstrip(':').upper()
    if not clean or not clean[0].isalpha():
        logger.warning(f"Invalid drive letter ignored: {new_drive!r}")
        return
    _DRIVE_LETTER = clean[0]
    _rebuild_paths()

    _SETTINGS['drive_letter'] = _DRIVE_LETTER
    _save_settings(_SETTINGS)

    logger.info(f"Drive updated to: {_DRIVE_LETTER}")


def get_drive() -> str:
    """Get the current drive letter."""
    return _DRIVE_LETTER


# =============================================================================
# Perforce Paths (Source Data)
# =============================================================================

# LOC folder: Contains languagedata_*.xml files
LOC_FOLDER = _build_path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")

# EXPORT folder: Contains categorized .loc.xml files
EXPORT_FOLDER = _build_path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")

# GameData StaticInfo folders: Contains game data XMLs with Name/Desc attributes
# Used for glossary extraction (reverse lookup Korean → Name vs Desc)
STATICINFO_FOLDER = _build_path(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo")
STATICINFO_QUEST_FOLDER = _build_path(r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest")
STATICINFO_DIALOG_FOLDER = _build_path(r"F:\perforce\cd\mainline\resource\GameData\staticinfo_dialog")

# VoiceRecordingSheet folder: Contains Excel files with EventName ordering
# Used to order STORY strings (Sequencer, Dialog) in chronological story order
VOICE_RECORDING_FOLDER = _build_path(r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__")

# Audio folders: Contains .wem files for HasAudio detection
# Same paths as MapDataGenerator (battle-tested)
AUDIO_FOLDER_EN = _build_path(r"F:\perforce\cd\mainline\resource\sound\windows\English(US)")
AUDIO_FOLDER_KR = _build_path(r"F:\perforce\cd\mainline\resource\sound\windows\Korean")
AUDIO_FOLDER_ZH = _build_path(r"F:\perforce\cd\mainline\resource\sound\windows\Chinese(PRC)")

# Language code -> audio folder mapping
LANG_TO_AUDIO_FOLDER = {
    "eng": AUDIO_FOLDER_EN,
    "kor": AUDIO_FOLDER_KR,
    "zho-cn": AUDIO_FOLDER_ZH,
}

# =============================================================================
# Output Configuration
# =============================================================================

# Output folder for generated Excel files
OUTPUT_FOLDER = SCRIPT_DIR / "GeneratedExcel"

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

    # Official suffixes from LOC folder: ENG, FRE, GER, ITA, JPN, KOR, POL, POR-BR, RUS, SPA-ES, SPA-MX, TUR, ZHO-CN, ZHO-TW
    LANGUAGE_NAMES = {
        "eng": "ENG",
        "fre": "FRE",
        "ger": "GER",
        "ita": "ITA",
        "jpn": "JPN",
        "kor": "KOR",
        "pol": "POL",
        "por-br": "POR-BR",
        "rus": "RUS",
        "spa-es": "SPA-ES",
        "spa-mx": "SPA-MX",
        "tur": "TUR",
        "zho-cn": "ZHO-CN",
        "zho-tw": "ZHO-TW",
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

# Categories to EXCLUDE in "No Script" mode (script/dialog content)
DIALOG_SEQUENCER_EXCLUSION = {"Sequencer", "AIDialog", "QuestDialog", "NarrationDialog"}

# Categories to EXCLUDE in "Non-Script+NarrationDialog" mode
# Same as No Script but KEEPS NarrationDialog
NOSCRIPT_PLUS_NARRATION_EXCLUSION = {"Sequencer", "AIDialog", "QuestDialog"}

# Inverse exclusion: everything that ISN'T script/dialog (for "Script Only" export)
GAMEDATA_EXCLUSION = {
    "Item", "Quest", "Character", "Gimmick", "Skill",
    "Knowledge", "Faction", "UI", "Region", "System_Misc", "Uncategorized"
}

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
# STATUS: dropdown validation (ISSUE / NO ISSUE)
# COMMENT: free-text QA notes
COLUMN_HEADERS_EU = ["StrOrigin", "ENG", "Str", "Correction", "Text State", "STATUS", "COMMENT", "Category", "FileName", "StringID", "DescOrigin", "Desc"]
COLUMN_HEADERS_ASIAN = ["StrOrigin", "Str", "Correction", "Text State", "STATUS", "COMMENT", "Category", "FileName", "StringID", "DescOrigin", "Desc"]

# Script Only column headers: no MEMO1/MEMO2, adds EventName + HasAudio
COLUMN_HEADERS_SCRIPT_EU = ["StrOrigin", "ENG", "Str", "Correction", "Text State", "STATUS", "COMMENT", "Category", "FileName", "StringID", "EventName", "HasAudio", "DescOrigin", "Desc"]
COLUMN_HEADERS_SCRIPT_ASIAN = ["StrOrigin", "Str", "Correction", "Text State", "STATUS", "COMMENT", "Category", "FileName", "StringID", "EventName", "HasAudio", "DescOrigin", "Desc"]

# Column widths (approximate)
COLUMN_WIDTHS = {
    "StrOrigin": 40,
    "ENG": 40,
    "Str": 40,
    "Correction": 40,
    "Text State": 12,
    "STATUS": 14,
    "COMMENT": 30,
    "Category": 20,
    "FileName": 25,
    "StringID": 15,
    "EventName": 35,
    "HasAudio": 12,
    "DescOrigin": 40,
    "Desc": 40,
}


def get_audio_folder(lang_code: str) -> Path:
    """Get the audio folder for a language. Falls back to English."""
    return LANG_TO_AUDIO_FOLDER.get(lang_code.lower(), AUDIO_FOLDER_EN)


def ensure_output_folder():
    """Create output folder if it doesn't exist."""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    return OUTPUT_FOLDER
