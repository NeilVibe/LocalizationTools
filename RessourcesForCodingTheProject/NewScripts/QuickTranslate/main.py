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
import traceback
from pathlib import Path

# PyInstaller compatibility - ensure we can find our modules
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_DIR = Path(sys.executable).parent
    sys.path.insert(0, str(BASE_DIR))

    # Crash logging: write errors to file since console=False hides them
    _crash_log = BASE_DIR / "QuickTranslate_crash.log"
    try:
        sys.stderr = open(str(_crash_log), 'a', encoding='utf-8')
    except Exception:
        pass
else:
    # Running as script
    BASE_DIR = Path(__file__).parent
    sys.path.insert(0, str(BASE_DIR))


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

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        tb = traceback.format_exc()
        logger.exception(f"Fatal error: {e}")

        # Write to crash log
        try:
            with open(str(BASE_DIR / "QuickTranslate_crash.log"), 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n{error_msg}\n{tb}\n")
        except Exception:
            pass

        # Show error dialog (visible even with console=False)
        try:
            import tkinter as _tk
            from tkinter import messagebox as _mb
            _root = _tk.Tk()
            _root.withdraw()
            _mb.showerror(
                "QuickTranslate Error",
                f"Fatal error:\n\n{error_msg}\n\n"
                f"Details written to QuickTranslate_crash.log"
            )
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
