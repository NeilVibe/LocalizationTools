"""
Configuration for Language XML to Categorized Excel Converter.

Paths, constants, and configuration for the exporter.
Now integrated with utils/language_utils for language classification.
"""

from pathlib import Path
import sys

# Detect if running as PyInstaller bundle
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent

# =============================================================================
# Perforce Paths (Source Data)
# =============================================================================

# LOC folder: Contains languagedata_*.xml files
LOC_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")

# EXPORT folder: Contains categorized .loc.xml files
EXPORT_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")

# VoiceRecordingSheet folder: Contains Excel files with EventName ordering
# Used to order STORY strings (Sequencer, Dialog) in chronological story order
VOICE_RECORDING_FOLDER = Path(r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__")

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

# Column headers for Excel output
COLUMN_HEADERS_EU = ["StrOrigin", "Str", "StringID", "English", "Category"]
COLUMN_HEADERS_ASIAN = ["StrOrigin", "Str", "StringID", "Category"]

# Column widths (approximate)
COLUMN_WIDTHS = {
    "StrOrigin": 40,
    "Str": 40,
    "StringID": 15,
    "English": 40,
    "Category": 20,
}


def ensure_output_folder():
    """Create output folder if it doesn't exist."""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    return OUTPUT_FOLDER
