#!/usr/bin/env python3
"""
Drive Replacer for LanguageDataExporter.

Updates settings.json with the correct drive letter for Perforce paths.
Used during build process or manual configuration.

Usage:
    python drive_replacer.py D                    # Creates settings.json with D: drive
    python drive_replacer.py D settings.json     # Specify output path
"""

import json
import sys
from pathlib import Path


def create_settings(drive_letter: str, output_path: Path = None) -> bool:
    """
    Create settings.json with specified drive letter.

    Args:
        drive_letter: Single letter (A-Z)
        output_path: Path to settings.json (default: ./settings.json)

    Returns:
        True if successful
    """
    # Validate drive letter
    drive = drive_letter.upper().strip()
    if len(drive) != 1 or not drive.isalpha():
        print(f"Error: Invalid drive letter '{drive_letter}'. Must be A-Z.")
        return False

    # Default output path
    if output_path is None:
        output_path = Path(__file__).parent / "settings.json"
    else:
        output_path = Path(output_path)

    # Build settings
    settings = {
        "drive_letter": drive,
        "loc_folder": f"{drive}:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc",
        "export_folder": f"{drive}:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__",
        "vrs_folder": f"{drive}:\\perforce\\cd\\mainline\\resource\\editordata\\VoiceRecordingSheet__",
        "description": "Runtime configuration - edit paths if needed"
    }

    # Write settings
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        print(f"Created {output_path} with drive {drive}:")
        return True
    except Exception as e:
        print(f"Error writing settings: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    drive_letter = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    success = create_settings(drive_letter, output_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
