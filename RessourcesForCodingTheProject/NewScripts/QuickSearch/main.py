#!/usr/bin/env python3
"""
QuickSearch - Modular Localization Tool

A modular rewrite of QuickSearch with:
- ENG BASE / KR BASE selection for LINE CHECK and TERM CHECK
- Clean output (no verbose filename printing)
- Modular architecture like LanguageDataExporter/QACompiler

Usage:
    python main.py              # Launch GUI
    python main.py --help       # Show help

Author: Neil
Version: 1.0.0
"""

import argparse
import sys
import os

# Add parent directory to path for package imports when running as script
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="QuickSearch - Localization Search and Consistency Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                     # Launch GUI
    python main.py --version           # Show version

Modules:
    - Quick Search: Dictionary-based search with reference support
    - LINE CHECK: Find inconsistent translations (same source, different trans)
    - TERM CHECK: Find missing glossary terms (Aho-Corasick)
    - Glossary Extract: Create glossaries from localization files

New Features:
    - ENG BASE / KR BASE mode for LINE CHECK and TERM CHECK
    - Clean output without filename clutter
    - Modular architecture for maintainability
"""
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="QuickSearch 1.0.0"
    )

    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in CLI mode (not yet implemented)"
    )

    args = parser.parse_args()

    if args.cli:
        print("CLI mode not yet implemented. Launching GUI...")

    # Launch GUI
    try:
        # Try importing as package first
        from gui.app import QuickSearchApp
    except ImportError:
        # Fall back to relative import
        from QuickSearch.gui.app import QuickSearchApp

    print("QuickSearch v1.0.0 - Modular Localization Tool")
    print("Loading GUI...")

    app = QuickSearchApp()
    app.run()


if __name__ == "__main__":
    main()
