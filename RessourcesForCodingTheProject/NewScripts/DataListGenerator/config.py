"""
Configuration Module for DataListGenerator
==========================================
Handles settings loading, drive letter application, and path configuration.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any


# Detect if running as PyInstaller executable
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent


def load_settings() -> Dict[str, Any]:
    """Load runtime settings from settings.json.

    Settings file format:
    {
        "drive_letter": "F",
        "version": "3.0",
        "paths": {
            "factioninfo": "...",
            "skillinfo": "...",
            "loc_folder": "..."
        }
    }
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


def apply_drive_letter(path_str: str, drive_letter: str) -> str:
    """Replace the default F: drive with the configured drive letter."""
    if path_str.startswith("F:") or path_str.startswith("f:"):
        return f"{drive_letter.upper()}:{path_str[2:]}"
    return path_str


# Load settings at module import time
_SETTINGS = load_settings()
DRIVE_LETTER = _SETTINGS.get('drive_letter', 'F')

if DRIVE_LETTER != 'F':
    print(f"  Using custom drive letter: {DRIVE_LETTER}:")


# Path configurations
FACTIONINFO_FOLDER = Path(apply_drive_letter(
    _SETTINGS.get('paths', {}).get('factioninfo',
        r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo"),
    DRIVE_LETTER
))

SKILLINFO_FOLDER = Path(apply_drive_letter(
    _SETTINGS.get('paths', {}).get('skillinfo',
        r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\skillinfo"),
    DRIVE_LETTER
))

LOC_FOLDER = Path(apply_drive_letter(
    _SETTINGS.get('paths', {}).get('loc_folder',
        r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc"),
    DRIVE_LETTER
))

# Output folders
OUTPUT_FOLDER = SCRIPT_DIR / "Output"
TRANSLATIONS_FOLDER = OUTPUT_FOLDER / "Translations"
