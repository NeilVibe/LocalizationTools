"""
Populate QAfolderNEW Helper
============================
Auto-populates QAfolderNEW with fresh datasheets based on QAfolderOLD structure.

This helper:
1. Checks if generated datasheets exist and are fresh (< MAX_AGE_HOURS)
2. Creates folders matching QAfolderOLD structure ({Username}_{Category})
3. Copies correct language sheets (ENG/ZHO-CN) per tester mapping

Usage:
    from core.populate_new import populate_qa_folder_new
    success, message = populate_qa_folder_new()
"""

import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    QA_FOLDER_OLD, QA_FOLDER_NEW, DATASHEET_OUTPUT,
    CATEGORIES, load_tester_mapping
)
from core.discovery import discover_qa_folders_in


# =============================================================================
# CONFIGURATION
# =============================================================================

# Maximum age for generated datasheets (in hours)
MAX_AGE_HOURS = 10

# Mapping of category to generated sheet patterns and folder names
# Format: category -> (folder_name, file_patterns_ENG, file_patterns_CN)
DATASHEET_LOCATIONS = {
    "Quest": {
        "folder": "QuestData_Map_All",
        "eng_pattern": "Quest_LQA_ENG*.xlsx",
        "cn_pattern": "Quest_LQA_ZHO-CN*.xlsx",
    },
    "Knowledge": {
        "folder": "Knowledge_LQA_All",
        "eng_pattern": "Knowledge_LQA_ENG*.xlsx",
        "cn_pattern": "Knowledge_LQA_ZHO-CN*.xlsx",
    },
    "Item": {
        "folder": "ItemData_Map_All/Item_Sorted_LQA",  # Sorted version (not Full)
        "eng_pattern": "ITEM_WORKING_LQA_ENG*.xlsx",
        "cn_pattern": "ITEM_WORKING_LQA_ZHO-CN*.xlsx",
    },
    "Region": {
        "folder": "Region_LQA_v3",
        "eng_pattern": "Region_LQA_ENG*.xlsx",
        "cn_pattern": "Region_LQA_ZHO-CN*.xlsx",
    },
    "Character": {
        "folder": "Character_LQA_All",
        "eng_pattern": "Character_LQA_ENG*.xlsx",
        "cn_pattern": "Character_LQA_ZHO-CN*.xlsx",
    },
    "Skill": {
        "folder": "Skill_LQA_All",
        "eng_pattern": "LQA_Skill_ENG*.xlsx",
        "cn_pattern": "LQA_Skill_ZHO-CN*.xlsx",
    },
    "Help": {
        "folder": "GameAdvice_LQA_All",
        "eng_pattern": "LQA_GameAdvice_ENG*.xlsx",
        "cn_pattern": "LQA_GameAdvice_ZHO-CN*.xlsx",
    },
    "Gimmick": {
        "folder": "Gimmick_LQA_Output",
        "eng_pattern": "Gimmick_LQA_ENG*.xlsx",
        "cn_pattern": "Gimmick_LQA_ZHO-CN*.xlsx",
    },
    "System": {
        # System is special - manually created, no auto-generated sheets
        "folder": None,
        "eng_pattern": None,
        "cn_pattern": None,
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def find_latest_datasheet(category: str, is_english: bool) -> Optional[Path]:
    """
    Find the latest generated datasheet for a category and language.

    Args:
        category: Category name (Quest, Knowledge, etc.)
        is_english: True for ENG, False for ZHO-CN

    Returns:
        Path to the most recent matching file, or None if not found
    """
    if category not in DATASHEET_LOCATIONS:
        return None

    config = DATASHEET_LOCATIONS[category]
    if config["folder"] is None:
        return None

    folder = DATASHEET_OUTPUT / config["folder"]
    if not folder.exists():
        return None

    pattern = config["eng_pattern"] if is_english else config["cn_pattern"]
    if not pattern:
        return None

    # Find all matching files
    matches = list(folder.glob(pattern))
    if not matches:
        return None

    # Return the most recently modified
    return max(matches, key=lambda p: p.stat().st_mtime)


def check_datasheet_freshness(max_age_hours: int = MAX_AGE_HOURS) -> Tuple[bool, Dict[str, str]]:
    """
    Check if generated datasheets exist and are fresh enough.

    Args:
        max_age_hours: Maximum acceptable age in hours

    Returns:
        Tuple of (all_fresh, status_dict)
        - all_fresh: True if all required sheets are fresh
        - status_dict: {category: status_message}
    """
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    status = {}
    all_fresh = True

    for category in CATEGORIES:
        if category == "System":
            status[category] = "Manual (skip)"
            continue

        config = DATASHEET_LOCATIONS.get(category)
        if not config or not config["folder"]:
            status[category] = "Not configured"
            all_fresh = False
            continue

        # Check ENG file (primary check)
        eng_file = find_latest_datasheet(category, is_english=True)

        if eng_file is None:
            status[category] = "Not found"
            all_fresh = False
            continue

        # Check age
        file_mtime = datetime.fromtimestamp(eng_file.stat().st_mtime)
        age_hours = (datetime.now() - file_mtime).total_seconds() / 3600

        if file_mtime < cutoff_time:
            status[category] = f"Stale ({age_hours:.1f}h old)"
            all_fresh = False
        else:
            status[category] = f"Fresh ({age_hours:.1f}h old)"

    return all_fresh, status


def populate_qa_folder_new(
    force: bool = False,
    max_age_hours: int = MAX_AGE_HOURS
) -> Tuple[bool, str]:
    """
    Auto-populate QAfolderNEW with fresh datasheets based on QAfolderOLD structure.

    STRICT MODE (all-or-nothing):
    - If ANY datasheet is missing or outdated -> STOP, don't do anything
    - Only proceeds when ALL required sheets are present AND fresh
    - This prevents partial updates that could cause data loss

    This function:
    1. Checks if ALL generated datasheets exist and are fresh
    2. Discovers folders in QAfolderOLD
    3. Creates matching folders in QAfolderNEW
    4. Copies the correct language sheet for each tester

    Args:
        force: If True, skip freshness check and populate anyway (DANGEROUS)
        max_age_hours: Maximum acceptable age for datasheets (default: 10 hours)

    Returns:
        Tuple of (success, message)
    """
    print()
    print("=" * 60)
    print("Auto-Populate QAfolderNEW (STRICT MODE)")
    print("=" * 60)
    print()
    print("STRICT MODE: ALL datasheets must be present AND fresh.")
    print("             If ANY is missing or outdated -> STOP immediately.")
    print()

    # Step 1: STRICT freshness check (unless forced - which is dangerous)
    if not force:
        print("[1/4] Checking ALL datasheets (strict mode)...")
        print(f"      Max age: {max_age_hours} hours")
        print()

        all_fresh, status = check_datasheet_freshness(max_age_hours)

        # Show status for ALL categories
        missing_or_stale = []
        for category, status_msg in sorted(status.items()):
            if "Fresh" in status_msg or "skip" in status_msg:
                marker = "[OK]"
            else:
                marker = "[!!]"
                if category != "System":  # System is manual, don't count it
                    missing_or_stale.append(f"{category}: {status_msg}")
            print(f"  {marker} {category}: {status_msg}")

        # STRICT: If ANY is bad, stop immediately
        if not all_fresh:
            print()
            print("=" * 60)
            print("STOPPED: Cannot proceed with missing or stale datasheets!")
            print("=" * 60)
            print()
            print("The following datasheets need attention:")
            for item in missing_or_stale:
                print(f"  - {item}")
            print()
            print("ACTION REQUIRED:")
            print("  1. Run 'Generate Datasheets' (select ALL categories)")
            print("  2. Wait for generation to complete")
            print("  3. Try 'Transfer' again")
            print()
            return False, (
                f"STRICT MODE: {len(missing_or_stale)} datasheet(s) missing or stale.\n"
                f"Run 'Generate Datasheets' first, then try again."
            )

        print()
        print("[OK] All datasheets are present and fresh!")
    else:
        print("[1/4] Freshness check SKIPPED (force=True)")
        print("      WARNING: This may cause issues if datasheets are stale!")
        print()

    # Step 2: Discover OLD folders
    print("\n[2/4] Discovering QAfolderOLD structure...")

    if not QA_FOLDER_OLD.exists():
        return False, f"QAfolderOLD not found at {QA_FOLDER_OLD}"

    old_folders = discover_qa_folders_in(QA_FOLDER_OLD)
    if not old_folders:
        return False, "No valid folders found in QAfolderOLD"

    print(f"  Found {len(old_folders)} folder(s) to populate")
    for f in old_folders:
        print(f"    - {f['username']}_{f['category']}")

    # Step 3: Load tester mapping
    print("\n[3/4] Loading tester->language mapping...")
    tester_mapping = load_tester_mapping()

    # Step 4: Create folders and copy sheets
    print("\n[4/4] Populating QAfolderNEW...")

    # Clear QAfolderNEW first (clean slate)
    if QA_FOLDER_NEW.exists():
        for item in QA_FOLDER_NEW.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            elif item.name not in [".gitkeep", "README.txt"]:
                item.unlink()
    QA_FOLDER_NEW.mkdir(parents=True, exist_ok=True)

    success_count = 0
    skip_count = 0
    errors = []

    for old_folder in old_folders:
        username = old_folder["username"]
        category = old_folder["category"]
        folder_name = f"{username}_{category}"

        # Determine language
        is_english = tester_mapping.get(username, "EN") == "EN"
        lang_code = "ENG" if is_english else "ZHO-CN"

        # Skip System category (manual)
        if category == "System":
            print(f"  [SKIP] {folder_name}: System is manual")
            skip_count += 1
            continue

        # Find source datasheet
        source_file = find_latest_datasheet(category, is_english)

        if source_file is None:
            errors.append(f"{folder_name}: No {lang_code} datasheet found for {category}")
            print(f"  [FAIL] {folder_name}: No {lang_code} datasheet")
            continue

        # Create destination folder
        dest_folder = QA_FOLDER_NEW / folder_name
        dest_folder.mkdir(parents=True, exist_ok=True)

        # Copy the datasheet
        dest_file = dest_folder / source_file.name
        shutil.copy2(source_file, dest_file)

        print(f"  [OK] {folder_name}: {source_file.name}")
        success_count += 1

    # Summary
    print()
    print("=" * 60)
    print("POPULATE SUMMARY")
    print("=" * 60)
    print(f"  Populated: {success_count}")
    print(f"  Skipped:   {skip_count} (System)")
    print(f"  Failed:    {len(errors)}")

    if errors:
        print()
        print("Errors:")
        for err in errors:
            print(f"  - {err}")

    if success_count == 0 and len(errors) > 0:
        return False, "Failed to populate any folders"

    print()
    print(f"QAfolderNEW populated at: {QA_FOLDER_NEW}")
    print("You can now run 'Transfer QA Files' to merge OLD data with NEW sheets.")

    return True, f"Successfully populated {success_count} folder(s)"


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """CLI entry point for populate_new."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-populate QAfolderNEW with fresh datasheets"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip freshness check and populate anyway"
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=MAX_AGE_HOURS,
        help=f"Maximum age for datasheets in hours (default: {MAX_AGE_HOURS})"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check freshness, don't populate"
    )

    args = parser.parse_args()

    if args.check_only:
        print("Checking datasheet freshness...")
        all_fresh, status = check_datasheet_freshness(args.max_age)

        for category, status_msg in sorted(status.items()):
            marker = "[OK]" if "Fresh" in status_msg or "skip" in status_msg else "[!!]"
            print(f"  {marker} {category}: {status_msg}")

        if all_fresh:
            print("\nAll datasheets are fresh!")
            sys.exit(0)
        else:
            print("\nSome datasheets are stale or missing.")
            sys.exit(1)
    else:
        success, message = populate_qa_folder_new(
            force=args.force,
            max_age_hours=args.max_age
        )

        if success:
            print(f"\n{message}")
            sys.exit(0)
        else:
            print(f"\nERROR: {message}")
            sys.exit(1)


if __name__ == "__main__":
    main()
