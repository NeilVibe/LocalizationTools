"""
Configuration for Language XML to Categorized Excel Converter.

Paths, constants, and configuration for the exporter.
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

# =============================================================================
# Output Configuration
# =============================================================================

# Output folder for generated Excel files
OUTPUT_FOLDER = SCRIPT_DIR / "GeneratedExcel"

# =============================================================================
# Language Configuration
# =============================================================================

# Asian languages that do NOT get an English column
# These languages don't need English reference (culturally distinct translation)
ASIAN_LANGUAGES = {"zho-cn", "zho-tw", "jpn"}

# Language display names for Excel file naming
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
