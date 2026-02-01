#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MapDataGenerator - Three-Mode Data Visualization Tool

A GUI tool with IMAGE-FIRST architecture for visualizing:
- MAP mode: FactionNodes with map visualization
- CHARACTER mode: CharacterInfo with large image display
- ITEM mode: KnowledgeInfo items with large image display

Features:
- Image-first filtering (only entries with valid DDS files)
- Lazy language loading (English/Korean first, others on-demand)
- Large image display (512x512+)
- Multi-language search (13 languages)
- Matplotlib-based map visualization (MAP mode)

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

# Ensure package imports work in PyInstaller frozen executables
sys.path.insert(0, str(Path(__file__).parent))


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
        description="MapDataGenerator - Map/Region Data Visualization Tool"
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
