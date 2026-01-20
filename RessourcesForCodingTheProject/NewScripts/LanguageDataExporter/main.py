#!/usr/bin/env python3
"""
Language XML to Categorized Excel Converter

Converts languagedata_*.xml files into categorized Excel sheets
with EXPORT-based category assignment.

Usage:
    python main.py                    # Convert all languages
    python main.py --lang eng         # Convert specific language
    python main.py --lang eng,fre     # Convert multiple languages
    python main.py --dry-run          # Show what would be generated
    python main.py --list-categories  # List discovered categories
"""

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    LOC_FOLDER,
    EXPORT_FOLDER,
    OUTPUT_FOLDER,
    CLUSTER_CONFIG,
    ASIAN_LANGUAGES,
    LANGUAGE_NAMES,
    DEFAULT_CATEGORY,
    ensure_output_folder,
)
from exporter import (
    parse_language_file,
    discover_language_files,
    build_stringid_category_index,
    load_cluster_config,
    write_language_excel,
)
from exporter.excel_writer import write_summary_excel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def validate_paths() -> bool:
    """Validate that required paths exist."""
    errors = []

    if not LOC_FOLDER.exists():
        errors.append(f"LOC folder not found: {LOC_FOLDER}")

    if not EXPORT_FOLDER.exists():
        errors.append(f"EXPORT folder not found: {EXPORT_FOLDER}")

    if errors:
        for error in errors:
            logger.error(error)
        return False

    return True


def get_language_display_name(lang_code: str) -> str:
    """Get display name for language code."""
    return LANGUAGE_NAMES.get(lang_code.lower(), lang_code.upper())


def process_languages(
    languages: Optional[List[str]] = None,
    dry_run: bool = False
) -> Dict[str, Dict]:
    """
    Process language files and generate Excel outputs.

    Args:
        languages: Specific languages to process (None = all)
        dry_run: If True, don't write files

    Returns:
        Dictionary of language stats
    """
    # 1. Load category cluster config
    logger.info(f"Loading category config from {CLUSTER_CONFIG}")
    config = load_cluster_config(CLUSTER_CONFIG)
    clusters = config.get("clusters", {})
    default_category = config.get("default_category", DEFAULT_CATEGORY)

    # 2. Build StringID → Category index from EXPORT
    logger.info(f"Scanning EXPORT folder: {EXPORT_FOLDER}")
    category_index = build_stringid_category_index(
        EXPORT_FOLDER,
        clusters,
        default_category
    )

    if not category_index:
        logger.warning("No StringID → Category mappings found. Check EXPORT folder.")

    # Count categories
    category_stats = Counter(category_index.values())
    logger.info(f"Category distribution: {dict(category_stats)}")

    # 3. Discover all language files
    logger.info(f"Discovering language files in {LOC_FOLDER}")
    lang_files = discover_language_files(LOC_FOLDER)

    if not lang_files:
        logger.error("No language files found!")
        return {}

    # Filter to specific languages if requested
    if languages:
        lang_set = {lang.lower() for lang in languages}
        lang_files = {k: v for k, v in lang_files.items() if k.lower() in lang_set}

        if not lang_files:
            logger.error(f"Requested languages not found: {languages}")
            return {}

    logger.info(f"Processing {len(lang_files)} language(s): {list(lang_files.keys())}")

    # 4. Parse English first (for cross-reference)
    eng_lookup: Dict[str, str] = {}
    if "eng" in lang_files:
        logger.info("Parsing English for cross-reference...")
        eng_data = parse_language_file(lang_files["eng"])
        eng_lookup = {row["string_id"]: row["str"] for row in eng_data}
        logger.info(f"English lookup table: {len(eng_lookup)} entries")

    # 5. Ensure output folder exists
    if not dry_run:
        output_folder = ensure_output_folder()
        logger.info(f"Output folder: {output_folder}")

    # 6. Process each language
    language_stats: Dict[str, Dict] = {}

    for lang_code, lang_path in sorted(lang_files.items()):
        logger.info(f"Processing {lang_code.upper()}...")

        # Parse language file
        lang_data = parse_language_file(lang_path)

        if not lang_data:
            logger.warning(f"No data in {lang_code}, skipping")
            continue

        # Determine if English column should be included
        include_english = lang_code.lower() not in ASIAN_LANGUAGES

        # Build output path
        display_name = get_language_display_name(lang_code)
        output_path = OUTPUT_FOLDER / f"LanguageData_{display_name}.xlsx"

        # Record stats
        language_stats[lang_code] = {
            "rows": len(lang_data),
            "file": str(output_path.name),
            "include_english": include_english,
        }

        if dry_run:
            logger.info(f"  [DRY RUN] Would generate: {output_path.name} ({len(lang_data)} rows)")
            continue

        # Write Excel
        success = write_language_excel(
            lang_code=lang_code,
            lang_data=lang_data,
            eng_lookup=eng_lookup,
            category_index=category_index,
            output_path=output_path,
            include_english=include_english,
            default_category=default_category,
        )

        if success:
            logger.info(f"  Generated: {output_path.name}")
        else:
            logger.error(f"  Failed: {output_path.name}")

    # 7. Write summary
    if not dry_run and language_stats:
        summary_path = OUTPUT_FOLDER / "_Summary.xlsx"
        write_summary_excel(language_stats, dict(category_stats), summary_path)

    return language_stats


def list_categories():
    """List all discovered categories from EXPORT folder."""
    logger.info(f"Scanning EXPORT folder: {EXPORT_FOLDER}")

    config = load_cluster_config(CLUSTER_CONFIG)
    clusters = config.get("clusters", {})
    default_category = config.get("default_category", DEFAULT_CATEGORY)

    category_index = build_stringid_category_index(
        EXPORT_FOLDER,
        clusters,
        default_category
    )

    # Count by category
    category_stats = Counter(category_index.values())

    print("\nCategory Distribution:")
    print("-" * 40)
    for category, count in sorted(category_stats.items(), key=lambda x: -x[1]):
        print(f"  {category:20} : {count:>6} StringIDs")
    print("-" * 40)
    print(f"  {'TOTAL':20} : {sum(category_stats.values()):>6} StringIDs")


def main():
    parser = argparse.ArgumentParser(
        description="Convert language XML files to categorized Excel sheets"
    )

    parser.add_argument(
        "--lang",
        type=str,
        help="Specific language(s) to process (comma-separated, e.g., 'eng,fre')"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Custom output folder path"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files"
    )

    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List discovered categories from EXPORT folder"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Override output folder if specified
    global OUTPUT_FOLDER
    if args.output:
        OUTPUT_FOLDER = Path(args.output)

    # Validate paths
    if not validate_paths():
        sys.exit(1)

    # List categories mode
    if args.list_categories:
        list_categories()
        sys.exit(0)

    # Parse language filter
    languages = None
    if args.lang:
        languages = [lang.strip() for lang in args.lang.split(',')]

    # Process languages
    stats = process_languages(languages=languages, dry_run=args.dry_run)

    # Summary
    if stats:
        print(f"\n{'=' * 50}")
        print(f"Generated {len(stats)} Excel file(s) in {OUTPUT_FOLDER}")
        total_rows = sum(s.get("rows", 0) for s in stats.values())
        print(f"Total rows: {total_rows:,}")
        print(f"{'=' * 50}")
    else:
        print("\nNo files generated.")
        sys.exit(1)


if __name__ == "__main__":
    main()
