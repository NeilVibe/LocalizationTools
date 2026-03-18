"""
Translation Bank Configuration
==============================
Settings for drive letters, paths, and defaults.
"""

from pathlib import Path

# =============================================================================
# VERSION (Auto-updated by CI)
# =============================================================================

VERSION = "1.0.0"

# =============================================================================
# DRIVE LETTERS (modify based on your system)
# =============================================================================

# Primary data drive - where game data is located
DATA_DRIVE = "D:"

# Backup/alternate drive
BACKUP_DRIVE = "E:"

# =============================================================================
# DEFAULT PATHS
# =============================================================================

# Default source folder for creating banks (translated XML files)
DEFAULT_SOURCE_FOLDER = Path(f"{DATA_DRIVE}/LanguageData_Translated")

# Default output folder for banks
DEFAULT_BANK_OUTPUT = Path(f"{DATA_DRIVE}/TranslationBanks")

# Default target folder for transfer (new XML files needing translations)
DEFAULT_TARGET_FOLDER = Path(f"{DATA_DRIVE}/LanguageData_New")

# =============================================================================
# FILE PATTERNS
# =============================================================================

# XML file patterns to process
XML_PATTERNS = ["*.xml", "*.XML"]

# Bank file extension (.pkl for speed, .json for debugging)
BANK_EXTENSION = ".pkl"
BANK_EXTENSION_JSON = ".json"  # Alternative for human-readable output

# =============================================================================
# LOCSTR ELEMENT CONFIG
# =============================================================================

# Element name containing localization strings
LOCSTR_ELEMENT = "LocStr"

# Attribute names
ATTR_STRING_ID = "StringId"
ATTR_STR_ORIGIN = "StrOrigin"  # Korean original
ATTR_STR = "Str"               # Translation

# =============================================================================
# LOGGING
# =============================================================================

import logging

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.INFO


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        format=LOG_FORMAT,
        level=LOG_LEVEL,
    )
    return logging.getLogger("TranslationBank")


log = setup_logging()
