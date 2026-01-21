#!/usr/bin/env python3
"""
Drive Path Replacer - Helper script for build_exe.bat

Creates settings.json with the selected drive letter.
This file is read by config.py at runtime to override the default F: drive.

Usage: python drive_replacer.py <drive_letter> [output_path]
Example: python drive_replacer.py D
Example: python drive_replacer.py D dist/QACompiler/settings.json

Note: This script NO LONGER modifies config.py directly.
      config.py now reads the drive letter from settings.json at runtime.
"""

import sys
import os
import json


def create_settings_file(output_path: str, drive_letter: str) -> bool:
    """Create settings.json with the specified drive letter.

    Args:
        output_path: Path to write settings.json
        drive_letter: Single letter drive (e.g., "D")

    Returns:
        True if successful, False otherwise.
    """
    settings = {
        "drive_letter": drive_letter.upper(),
        "version": "1.0"
    }

    try:
        # Ensure parent directory exists
        parent_dir = os.path.dirname(output_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)

        print(f"  Created: {output_path}")
        print(f"  Drive letter: {drive_letter}:")
        return True

    except Exception as e:
        print(f"  ERROR creating {output_path}: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python drive_replacer.py <drive_letter> [output_path]")
        print("Example: python drive_replacer.py D")
        print("Example: python drive_replacer.py D dist/QACompiler/settings.json")
        print()
        print("Creates settings.json with the specified drive letter.")
        print("config.py reads this file at runtime to determine the drive.")
        sys.exit(1)

    drive_letter = sys.argv[1].upper()

    if len(drive_letter) != 1 or not drive_letter.isalpha():
        print(f"ERROR: Invalid drive letter: {drive_letter}")
        sys.exit(1)

    # Default output path is settings.json in current directory
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        output_path = "settings.json"

    print(f"Creating settings.json with drive letter: {drive_letter}:")

    if create_settings_file(output_path, drive_letter):
        print("Done!")
    else:
        print("Failed to create settings file.")
        sys.exit(1)


if __name__ == '__main__':
    main()
