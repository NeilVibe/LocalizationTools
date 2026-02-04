#!/usr/bin/env python3
"""
QuickTranslate - Find translations for Korean text by matching StrOrigin.

Entry point for QuickTranslate application.

Features:
    - Multiple match types: Substring, StringID-only, Strict, Special Key
    - Multiple input modes: File (single) or Folder (recursive)
    - Multiple formats: Excel (.xlsx) or XML (.xml)
    - Branch selection: mainline or cd_lambda
    - StringID lookup
    - Reverse lookup (any language -> all languages)
    - ToSubmit folder integration

Usage:
    python main.py          # Launch GUI
    python main.py --help   # Show help
"""

import argparse
import logging
import sys
from pathlib import Path

# PyInstaller compatibility - ensure we can find our modules
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_DIR = Path(sys.executable).parent
    sys.path.insert(0, str(BASE_DIR))
else:
    # Running as script
    BASE_DIR = Path(__file__).parent
    sys.path.insert(0, str(BASE_DIR))

# Handle PyInstaller splash screen
try:
    import pyi_splash  # noqa: F401
    pyi_splash.close()
except ImportError:
    pass

# Setup logging
def setup_logging(verbose: bool = False):
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('QuickTranslate')


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='QuickTranslate - Find translations for Korean text',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                  # Launch GUI
    python main.py --verbose        # Launch GUI with verbose logging

For GUI usage:
    1. Select format (Excel or XML)
    2. Select mode (File or Folder)
    3. Select match type
    4. Choose source file/folder
    5. Click Generate
        """
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='QuickTranslate 2.0.0'
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.verbose)
    logger.info("Starting QuickTranslate...")

    # Import and run GUI
    try:
        from gui import QuickTranslateApp
        if QuickTranslateApp is None:
            logger.error("GUI not available (tkinter not installed)")
            print("ERROR: tkinter not available.")
            print("  - Windows: Reinstall Python with 'tcl/tk' checkbox enabled")
            print("  - Linux:   sudo apt install python3-tk")
            sys.exit(1)

        import tkinter as tk
        root = tk.Tk()
        app = QuickTranslateApp(root)
        logger.info("GUI initialized successfully")
        root.mainloop()

    except ImportError as e:
        logger.error(f"Import error: {e}")
        print(f"ERROR: Missing dependency: {e}")
        print(f"  Module: {e.name}" if hasattr(e, 'name') else "")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
