#!/usr/bin/env python3
"""
Translation Bank - Main Entry Point
====================================
A translation transfer tool that preserves translations when StringId or StrOrigin
changes in XML localization files.

Uses a 3-level unique key system:
- Level 1: StrOrigin + StringId (most reliable)
- Level 2: StringId only (when StrOrigin changed)
- Level 3: Context-aware (when both changed, uses adjacent entries)

Usage:
    python main.py          # Launch GUI
    python main.py --cli    # CLI mode (TODO)
"""

import sys
from pathlib import Path


def main():
    """Main entry point."""
    # Check for CLI mode
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        print("CLI mode not yet implemented. Use GUI mode.")
        print("Usage: python main.py")
        return 1

    # Launch GUI
    try:
        from gui.app import run_gui
        run_gui()
        return 0
    except ImportError as e:
        print(f"Error: Could not import GUI module: {e}")
        print("Make sure you're running from the TranslationBank directory.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
