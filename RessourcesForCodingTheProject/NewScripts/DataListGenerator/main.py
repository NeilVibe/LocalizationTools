#!/usr/bin/env python3
"""
DataListGenerator - Main Entry Point
=====================================
A modular tool for generating data lists (Factions, Skills, etc.)
from game XML files with multi-language translation support.

Usage:
    python main.py           # Launch GUI
    python main.py --help    # Show help
"""

import argparse
import sys
from pathlib import Path

# Ensure package imports work when running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from DataListGenerator.config import OUTPUT_FOLDER, TRANSLATIONS_FOLDER
from DataListGenerator.gui import DataToolGUI


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DataListGenerator - Generate data lists from game XML files"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="DataListGenerator v3.0"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Data List Generator v3.0")
    print("=" * 60)

    # Ensure output folders exist
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    TRANSLATIONS_FOLDER.mkdir(parents=True, exist_ok=True)

    # Launch GUI
    app = DataToolGUI()
    app.run()


if __name__ == "__main__":
    main()
