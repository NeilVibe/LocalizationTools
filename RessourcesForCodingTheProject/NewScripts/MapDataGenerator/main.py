#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MapDataGenerator - Crimson Desert Map/Region Data Visualization Tool

A GUI tool for visualizing Crimson Desert map/region data with:
- Multi-language search (13 languages)
- DDS image display via UITextureName
- Multi-step linkage resolution
- Matplotlib-based map visualization

Usage:
    python main.py              # Launch GUI
    python main.py --help       # Show help
    python main.py --version    # Show version
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging() -> None:
    """Setup logging configuration."""
    from config import get_log_dir

    log_dir = get_log_dir()
    log_file = log_dir / f"mapdatagenerator_{datetime.now():%Y%m%d_%H%M%S}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    logging.info("Log file: %s", log_file)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    from config import VERSION

    parser = argparse.ArgumentParser(
        description="MapDataGenerator - Crimson Desert Map/Region Data Visualization Tool"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"MapDataGenerator {VERSION}"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    # Handle PyInstaller splash screen
    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass

    # Parse arguments
    args = parse_args()

    # Setup logging
    setup_logging()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    log = logging.getLogger(__name__)
    log.info("Starting MapDataGenerator...")

    try:
        # Import and run application
        from gui.app import MapDataGeneratorApp

        app = MapDataGeneratorApp()
        app.run()

        return 0

    except Exception as e:
        log.exception("Application error: %s", e)

        # Show error dialog if possible
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "MapDataGenerator Error",
                f"An error occurred:\n\n{str(e)}\n\nCheck logs for details."
            )
        except Exception:
            pass

        return 1


if __name__ == "__main__":
    sys.exit(main())
