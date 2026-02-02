"""
Configuration for QuickTranslate.

Paths and constants for translation lookup.
Paths can be configured via settings.json (created on first run).
"""

from pathlib import Path
import sys
import json

# Detect if running as PyInstaller bundle
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent

# =============================================================================
# Matching Modes
# =============================================================================

MATCHING_MODES = {
    "substring": "Substring Match (original)",
    "stringid_only": "StringID-Only (SCRIPT strings)",
    "strict": "StringID + StrOrigin (Strict)",
    "special_key": "Special Key Match",
}

# SCRIPT categories - strings where StrOrigin = raw KOR text
SCRIPT_CATEGORIES = {"Sequencer", "AIDialog", "QuestDialog", "NarrationDialog"}

# Input modes
INPUT_MODES = ["folder", "file"]
FORMAT_MODES = ["excel", "xml"]

# =============================================================================
# ToSubmit Integration
# =============================================================================

TOSUBMIT_FOLDER = SCRIPT_DIR / "ToSubmit"
TOSUBMIT_COLUMNS = ["StrOrigin", "Correction", "StringID"]

# =============================================================================
# Branch Configuration
# =============================================================================

BRANCHES = {
    "mainline": {
        "loc": Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc"),
        "export": Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__"),
    },
    "cd_lambda": {
        "loc": Path(r"F:\perforce\cd\cd_lambda\resource\GameData\stringtable\loc"),
        "export": Path(r"F:\perforce\cd\cd_lambda\resource\GameData\stringtable\export__"),
    },
}

# =============================================================================
# Settings Loading
# =============================================================================

def _load_settings() -> dict:
    """
    Load runtime settings from settings.json if it exists.
    Falls back to F: drive defaults if file doesn't exist.
    """
    settings_path = SCRIPT_DIR / "settings.json"

    if settings_path.exists():
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_settings(settings: dict):
    """Save settings to settings.json."""
    settings_path = SCRIPT_DIR / "settings.json"
    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except IOError:
        pass


# Load settings at module level
_SETTINGS = _load_settings()

# =============================================================================
# Perforce Paths (Source Data)
# =============================================================================

# Get paths from settings.json if available, otherwise use F: drive defaults
_loc = _SETTINGS.get("loc_folder")
_export = _SETTINGS.get("export_folder")

# LOC folder: Contains languagedata_*.xml files
LOC_FOLDER = Path(_loc) if _loc else Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")

# EXPORT folder: Contains categorized .loc.xml files
EXPORT_FOLDER = Path(_export) if _export else Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")

# SEQUENCER folder: Only source for StrOrigin matching
SEQUENCER_FOLDER = EXPORT_FOLDER / "Sequencer"

# =============================================================================
# Output Configuration
# =============================================================================

OUTPUT_FOLDER = SCRIPT_DIR / "Output"

# =============================================================================
# Language Configuration
# =============================================================================

# Preferred output order for languages
LANGUAGE_ORDER = [
    "kor",      # Korean (source)
    "eng",      # English
    "fre",      # French
    "ger",      # German
    "spa",      # Spanish
    "por",      # Portuguese
    "ita",      # Italian
    "rus",      # Russian
    "tur",      # Turkish
    "pol",      # Polish
    "zho-cn",   # Chinese Simplified
    "zho-tw",   # Chinese Traditional
    "jpn",      # Japanese
    "tha",      # Thai
    "vie",      # Vietnamese
    "ind",      # Indonesian
    "msa",      # Malay
]

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


def ensure_output_folder():
    """Create output folder if it doesn't exist."""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    return OUTPUT_FOLDER


def update_settings(loc_folder: str = None, export_folder: str = None):
    """Update and save settings."""
    global LOC_FOLDER, EXPORT_FOLDER, SEQUENCER_FOLDER, _SETTINGS

    if loc_folder:
        _SETTINGS["loc_folder"] = loc_folder
        LOC_FOLDER = Path(loc_folder)
    if export_folder:
        _SETTINGS["export_folder"] = export_folder
        EXPORT_FOLDER = Path(export_folder)
        SEQUENCER_FOLDER = EXPORT_FOLDER / "Sequencer"

    _save_settings(_SETTINGS)
