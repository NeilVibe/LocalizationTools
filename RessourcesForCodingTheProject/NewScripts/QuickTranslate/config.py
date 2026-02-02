"""
Configuration for QuickTranslate.

Paths and constants for translation lookup.
Paths can be configured via settings.json (created on first run) or through the Settings UI.
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

# SCRIPT categories - folder names where StrOrigin = raw KOR text
# These map to export__/Dialog/ and export__/Sequencer/ folders
# Only these categories are transferred in StringID-Only mode
SCRIPT_CATEGORIES = {"Sequencer", "Dialog"}

# Subfolders to EXCLUDE from StringID-Only transfer
# These are subfolders within Dialog/ or Sequencer/ that should be skipped
SCRIPT_EXCLUDE_SUBFOLDERS = {"NarrationDialog"}

# Input modes
INPUT_MODES = ["folder", "file"]
FORMAT_MODES = ["excel", "xml"]

# Special Key fields - hardcoded for Special Key Match mode
SPECIAL_KEY_FIELDS = ["string_id", "category"]

# =============================================================================
# Settings Loading
# =============================================================================

def _get_settings_path() -> Path:
    """Get the path to settings.json."""
    return SCRIPT_DIR / "settings.json"


def _load_settings() -> dict:
    """
    Load runtime settings from settings.json if it exists.
    Falls back to F: drive defaults if file doesn't exist.
    """
    settings_path = _get_settings_path()

    if settings_path.exists():
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_settings(settings: dict) -> bool:
    """Save settings to settings.json. Returns True on success."""
    settings_path = _get_settings_path()
    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        return True
    except IOError as e:
        print(f"[CONFIG] Warning: Failed to save settings: {e}")
        return False


# Load settings at module level
_SETTINGS = _load_settings()

# =============================================================================
# Default Paths (can be overridden in settings.json)
# =============================================================================

DEFAULT_LOC_FOLDER = r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc"
DEFAULT_EXPORT_FOLDER = r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__"

# =============================================================================
# Perforce Paths (Source Data)
# =============================================================================

# Get paths from settings.json if available, otherwise use F: drive defaults
_loc = _SETTINGS.get("loc_folder")
_export = _SETTINGS.get("export_folder")

# LOC folder: Contains languagedata_*.xml files
LOC_FOLDER = Path(_loc) if _loc else Path(DEFAULT_LOC_FOLDER)

# EXPORT folder: Contains categorized .loc.xml files
EXPORT_FOLDER = Path(_export) if _export else Path(DEFAULT_EXPORT_FOLDER)

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


def get_settings() -> dict:
    """Get current settings as a dictionary."""
    return {
        "loc_folder": str(LOC_FOLDER),
        "export_folder": str(EXPORT_FOLDER),
    }


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


def reload_settings():
    """Reload settings from settings.json file."""
    global LOC_FOLDER, EXPORT_FOLDER, SEQUENCER_FOLDER, _SETTINGS

    _SETTINGS = _load_settings()

    _loc = _SETTINGS.get("loc_folder")
    _export = _SETTINGS.get("export_folder")

    LOC_FOLDER = Path(_loc) if _loc else Path(DEFAULT_LOC_FOLDER)
    EXPORT_FOLDER = Path(_export) if _export else Path(DEFAULT_EXPORT_FOLDER)
    SEQUENCER_FOLDER = EXPORT_FOLDER / "Sequencer"
