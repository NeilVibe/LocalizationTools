#!/usr/bin/env python3
"""
QA Compiler Suite v2.0 - Main Entry Point
==========================================

Unified tool for:
1. Generating LQA datasheets from XML game sources
2. Transferring tester work between folder structures
3. Building master files with progress tracking

Usage:
    # GUI mode (default)
    python main.py

    # CLI mode - Generate datasheets
    python main.py --generate quest knowledge item
    python main.py --generate all              # Generate all categories
    python main.py -g quest -g item            # Multiple -g flags

    # CLI mode - Compile QA files
    python main.py --transfer                  # Transfer QA files
    python main.py --build                     # Build master files
    python main.py --all                       # Full pipeline (transfer + build)

    # Utilities
    python main.py --list                      # List available categories
    python main.py --version                   # Show version info
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List

# Ensure package imports work
sys.path.insert(0, str(Path(__file__).parent))

from config import CATEGORIES, ensure_folders_exist, DATASHEET_OUTPUT, LANGUAGE_FOLDER, VOICE_RECORDING_SHEET_FOLDER

# =============================================================================
# VERSION INFO
# =============================================================================

VERSION = "2.0.0"
BANNER = f"""
╔══════════════════════════════════════════════════════════════════╗
║           QA COMPILER SUITE v{VERSION}                              ║
║    LQA Datasheet Generation & QA File Compilation                ║
╚══════════════════════════════════════════════════════════════════╝
"""


# =============================================================================
# UTILITIES
# =============================================================================

def print_banner():
    """Print the application banner."""
    print(BANNER)


def print_separator(char="─", length=70):
    """Print a separator line."""
    print(char * length)


def print_section(title: str):
    """Print a section header."""
    print()
    print_separator("═")
    print(f"  {title}")
    print_separator("═")


def print_success(msg: str):
    """Print success message."""
    print(f"✓ {msg}")


def print_error(msg: str):
    """Print error message."""
    print(f"✗ ERROR: {msg}")


def print_info(msg: str):
    """Print info message."""
    print(f"• {msg}")


# =============================================================================
# CLI HANDLERS
# =============================================================================

def cli_list_categories():
    """List all available categories."""
    print_section("Available Categories")
    print()
    print("The following categories can be used with --generate:")
    print()

    for i, cat in enumerate(CATEGORIES, 1):
        desc = {
            "Quest": "Main/Faction/Daily/Challenge/Minigame quests",
            "Knowledge": "Knowledge entries with hierarchical groups",
            "Item": "Items with descriptions and group organization",
            "Region": "Faction/Region exploration data",
            "System": "Skill + Help combined (category clustering)",
            "Character": "NPC/Monster character info",
            "Skill": "Player skills with knowledge linking",
            "Help": "GameAdvice/Help system entries",
            "Gimmick": "Interactive gimmick objects",
        }.get(cat, "")
        print(f"  {i}. {cat:12} - {desc}")

    print()
    print("Usage examples:")
    print("  python main.py --generate quest knowledge")
    print("  python main.py --generate all")
    print()


def cli_generate(categories: List[str]) -> bool:
    """Generate datasheets for specified categories."""
    print_section("Generate Datasheets")

    # Handle "all" keyword
    if "all" in [c.lower() for c in categories]:
        categories = CATEGORIES.copy()
        print_info("Generating ALL categories")

    print_info(f"Categories: {', '.join(categories)}")
    print_info(f"Output: {DATASHEET_OUTPUT}")
    print()

    start_time = time.time()

    try:
        from generators import generate_datasheets
        results = generate_datasheets(categories)

        elapsed = time.time() - start_time

        print()
        print_separator()
        print("Generation Results:")
        print_separator()

        if results.get("categories_processed"):
            print_success(f"Processed: {', '.join(results['categories_processed'])}")

        print_success(f"Files created: {results.get('files_created', 0)}")
        print_info(f"Time elapsed: {elapsed:.1f}s")

        if results.get("errors"):
            print()
            print_error("Errors encountered:")
            for err in results["errors"]:
                print(f"  - {err}")
            return False

        # Run coverage analysis if we have Korean strings collected
        korean_strings = results.get("korean_strings", {})
        if korean_strings:
            try:
                from tracker.coverage import run_coverage_analysis
                print()
                print_section("Language Data Coverage Analysis")
                run_coverage_analysis(
                    LANGUAGE_FOLDER,
                    VOICE_RECORDING_SHEET_FOLDER,
                    korean_strings,
                )
            except Exception as e:
                print_info(f"Coverage analysis skipped: {e}")

        print()
        print_success("Generation complete!")
        return True

    except ImportError as e:
        print_error(f"Generator modules not available: {e}")
        return False
    except Exception as e:
        print_error(f"Generation failed: {e}")
        return False


def cli_transfer() -> bool:
    """Transfer QA files from OLD/NEW to QAfolder."""
    print_section("Transfer QA Files")

    print_info("Source: QAfolderOLD + QAfolderNEW")
    print_info("Target: QAfolder")
    print()

    start_time = time.time()

    try:
        from core.transfer import transfer_qa_files
        success = transfer_qa_files()

        elapsed = time.time() - start_time
        print()
        print_info(f"Time elapsed: {elapsed:.1f}s")

        if success:
            print_success("Transfer complete!")
        else:
            print_error("Transfer failed - check console output above")

        return success

    except ImportError:
        # Fallback to original compile_qa
        try:
            print_info("Using fallback to original compile_qa module...")
            sys.path.insert(0, str(Path(__file__).parent.parent / "QAExcelCompiler"))
            from compile_qa import transfer_qa_files
            success = transfer_qa_files()

            if success:
                print_success("Transfer complete (via fallback)!")
            return success
        except Exception as e:
            print_error(f"Transfer failed: {e}")
            return False
    except Exception as e:
        print_error(f"Transfer failed: {e}")
        return False


def cli_build() -> bool:
    """Build master files from QAfolder."""
    print_section("Build Master Files")

    print_info("Source: QAfolder")
    print_info("Target: Masterfolder_EN / Masterfolder_CN")
    print()

    start_time = time.time()

    try:
        from core.compiler import run_compiler
        run_compiler()

        elapsed = time.time() - start_time
        print()
        print_info(f"Time elapsed: {elapsed:.1f}s")
        print_success("Build complete!")
        return True

    except ImportError:
        # Fallback to original compile_qa
        try:
            print_info("Using fallback to original compile_qa module...")
            sys.path.insert(0, str(Path(__file__).parent.parent / "QAExcelCompiler"))
            from compile_qa import main as compile_main
            compile_main()

            print_success("Build complete (via fallback)!")
            return True
        except Exception as e:
            print_error(f"Build failed: {e}")
            return False
    except Exception as e:
        print_error(f"Build failed: {e}")
        return False


def cli_full_pipeline() -> bool:
    """Run full pipeline: transfer + build."""
    print_banner()
    print("Running full compilation pipeline...")
    print()

    success = True

    # Step 1: Transfer
    if not cli_transfer():
        success = False

    # Step 2: Build (continue even if transfer had issues)
    if not cli_build():
        success = False

    print()
    print_separator("═")
    if success:
        print_success("Full pipeline completed successfully!")
    else:
        print_error("Pipeline completed with errors - check output above")
    print_separator("═")

    return success


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="QA Compiler Suite v2.0 - LQA Datasheet generation and QA file compilation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python main.py                          Launch GUI
  python main.py --list                   Show available categories
  python main.py --generate quest item    Generate Quest and Item datasheets
  python main.py --generate all           Generate all datasheets
  python main.py --transfer               Transfer QA files to QAfolder
  python main.py --build                  Build master files
  python main.py --all                    Full pipeline (transfer + build)

Available categories: {', '.join(CATEGORIES)}

Output folders:
  Datasheets: ./GeneratedDatasheets/
  Masters:    ./Masterfolder_EN/ and ./Masterfolder_CN/
        """
    )

    parser.add_argument(
        "--generate", "-g",
        nargs="+",
        action="extend",
        metavar="CATEGORY",
        help=f"Generate datasheets for categories. Use 'all' for all categories."
    )

    parser.add_argument(
        "--transfer", "-t",
        action="store_true",
        help="Transfer QA files from QAfolderOLD + QAfolderNEW to QAfolder"
    )

    parser.add_argument(
        "--build", "-b",
        action="store_true",
        help="Build master files from QAfolder to Masterfolder_EN/CN"
    )

    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run full pipeline: transfer + build"
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available categories for generation"
    )

    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version information"
    )

    parser.add_argument(
        "--gui",
        action="store_true",
        help="Force GUI mode even with other arguments"
    )

    parser.add_argument(
        "--update-tracker", "-u",
        action="store_true",
        help="Update tracker from QAFolderForTracker (without rebuilding masters)"
    )

    args = parser.parse_args()

    # Ensure folders exist
    ensure_folders_exist()

    # Version info
    if args.version:
        print(f"QA Compiler Suite v{VERSION}")
        print("LQA Datasheet Generation & QA File Compilation Tool")
        return

    # List categories
    if args.list:
        cli_list_categories()
        return

    # Force GUI mode
    if args.gui:
        from gui.app import run_gui
        run_gui()
        return

    # Update tracker only (no rebuild)
    if args.update_tracker:
        print_banner()
        try:
            from core.tracker_update import update_tracker_only
            success, message, entries = update_tracker_only()
            sys.exit(0 if success else 1)
        except ImportError as e:
            print_error(f"Tracker update module not available: {e}")
            sys.exit(1)
        except Exception as e:
            print_error(f"Tracker update failed: {e}")
            sys.exit(1)

    # If no arguments, launch GUI
    if not any([args.generate, args.transfer, args.build, args.all]):
        try:
            from gui.app import run_gui
            run_gui()
        except ImportError as e:
            print_error(f"GUI not available: {e}")
            print_info("Use --help to see CLI options")
            sys.exit(1)
        return

    # CLI mode
    print_banner()
    success = True

    # Generate datasheets
    if args.generate:
        # Validate categories (unless "all")
        if "all" not in [c.lower() for c in args.generate]:
            valid_lower = [c.lower() for c in CATEGORIES]
            invalid = [c for c in args.generate if c.lower() not in valid_lower]
            if invalid:
                print_error(f"Invalid categories: {', '.join(invalid)}")
                print_info(f"Available: {', '.join(CATEGORIES)}")
                print_info("Use 'all' to generate all categories")
                sys.exit(1)

        if not cli_generate(args.generate):
            success = False

    # Full pipeline takes precedence over individual transfer/build
    if args.all:
        if not cli_full_pipeline():
            success = False
    else:
        # Transfer QA files
        if args.transfer:
            if not cli_transfer():
                success = False

        # Build master files
        if args.build:
            if not cli_build():
                success = False

    # Final status
    print()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
