#!/usr/bin/env python3
"""
Drive Path Replacer - Helper script for build_exe.bat

Replaces F:\ with the selected drive letter in config files.
Usage: python drive_replacer.py <drive_letter>
Example: python drive_replacer.py D
"""

import sys
import os

def replace_drive(filepath: str, new_drive: str):
    """Replace F:\\ with new_drive:\\ in a file, preserving encoding."""
    try:
        # Read with UTF-8
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace F:\ with new drive
        old_path = 'F:\\'
        new_path = f'{new_drive}:\\'
        new_content = content.replace(old_path, new_path)

        # Also replace F:/ (forward slash variant)
        old_path_fwd = 'F:/'
        new_path_fwd = f'{new_drive}:/'
        new_content = new_content.replace(old_path_fwd, new_path_fwd)

        # Write back with UTF-8
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_content)

        print(f"  Updated: {filepath}")
        return True

    except Exception as e:
        print(f"  ERROR updating {filepath}: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python drive_replacer.py <drive_letter>")
        print("Example: python drive_replacer.py D")
        sys.exit(1)

    drive_letter = sys.argv[1].upper()

    if len(drive_letter) != 1 or not drive_letter.isalpha():
        print(f"ERROR: Invalid drive letter: {drive_letter}")
        sys.exit(1)

    if drive_letter == 'F':
        print("Drive is already F, no changes needed.")
        sys.exit(0)

    print(f"Replacing F:\\ with {drive_letter}:\\ in config files...")

    # Files to update
    files_to_update = [
        'config.py',
        'system_localizer.py'
    ]

    success = True
    for filepath in files_to_update:
        if os.path.exists(filepath):
            if not replace_drive(filepath, drive_letter):
                success = False
        else:
            print(f"  SKIP: {filepath} not found")

    if success:
        print("Done!")
    else:
        print("Some files failed to update.")
        sys.exit(1)


if __name__ == '__main__':
    main()
