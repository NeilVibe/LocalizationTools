"""
QA Folder Discovery Module
==========================
Detects and parses QA folder structures.
"""

from pathlib import Path
from typing import List, Dict, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import QA_FOLDER, QA_FOLDER_OLD, QA_FOLDER_NEW, CATEGORIES

# Supported image extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}


def discover_qa_folders(base_folder: Path = None) -> List[Dict]:
    """
    Find all QA folders and parse their metadata.

    Folder format: {Username}_{Category}/
    Each folder contains: one .xlsx file + images

    Args:
        base_folder: Folder to scan (defaults to QA_FOLDER)

    Returns:
        List of dicts with {folder_path, xlsx_path, username, category, images}
    """
    if base_folder is None:
        base_folder = QA_FOLDER

    results = []

    if not base_folder.exists():
        print(f"ERROR: Folder not found: {base_folder}")
        return results

    for folder in base_folder.iterdir():
        if not folder.is_dir():
            continue

        # Skip hidden/temp folders
        if folder.name.startswith('.') or folder.name.startswith('~'):
            continue

        # Parse folder name: {Username}_{Category}
        parts = folder.name.split("_")
        if len(parts) < 2:
            print(f"WARN: Invalid folder name format: {folder.name} (expected: Username_Category)")
            continue

        username = parts[0]
        category = "_".join(parts[1:])  # Handle categories with underscores

        if category not in CATEGORIES:
            print(f"WARN: Unknown category '{category}' in folder {folder.name}")
            continue

        # Find xlsx file (pick most recent if multiple)
        xlsx_files = list(folder.glob("*.xlsx"))
        xlsx_files = [f for f in xlsx_files if not f.name.startswith("~$")]

        if len(xlsx_files) == 0:
            print(f"WARN: No xlsx in folder: {folder.name}")
            continue

        if len(xlsx_files) > 1:
            # Sort by modification time (most recent first) and pick the newest
            xlsx_files_sorted = sorted(xlsx_files, key=lambda x: x.stat().st_mtime, reverse=True)
            xlsx_path = xlsx_files_sorted[0]
            print(f"  INFO: Multiple xlsx in {folder.name} ({len(xlsx_files)} files), using most recent: {xlsx_path.name}")
        else:
            xlsx_path = xlsx_files[0]

        # Find images
        images = [f for f in folder.iterdir()
                  if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]

        results.append({
            "folder_path": folder,
            "xlsx_path": xlsx_path,
            "username": username,
            "category": category,
            "images": images
        })

    return results


def discover_qa_folders_in(base_folder: Path) -> List[Dict]:
    """
    Discover QA folders in a given base folder.

    Uses rsplit to handle usernames with underscores.

    Args:
        base_folder: Folder to scan

    Returns:
        List of dicts with {username, category, xlsx_path, folder_path, images}
    """
    folders = []
    if not base_folder.exists():
        return folders

    for folder in base_folder.iterdir():
        if not folder.is_dir():
            continue

        # Skip hidden/temp folders
        if folder.name.startswith('.') or folder.name.startswith('~'):
            continue

        # Parse folder name: {Username}_{Category}
        folder_name = folder.name
        if "_" not in folder_name:
            continue

        parts = folder_name.rsplit("_", 1)
        if len(parts) != 2:
            continue

        username, category = parts
        if category not in CATEGORIES:
            continue

        # Find xlsx file (skip temp files starting with ~)
        xlsx_files = [f for f in folder.glob("*.xlsx") if not f.name.startswith("~")]
        if not xlsx_files:
            continue

        # Use the most recent xlsx file (by modification time)
        if len(xlsx_files) > 1:
            xlsx_path = max(xlsx_files, key=lambda x: x.stat().st_mtime)
            print(f"  INFO: Multiple xlsx in {folder.name} ({len(xlsx_files)} files), using most recent: {xlsx_path.name}")
        else:
            xlsx_path = xlsx_files[0]

        # Collect images
        images = [f for f in folder.iterdir()
                  if f.suffix.lower() in IMAGE_EXTENSIONS]

        folders.append({
            "username": username,
            "category": category,
            "xlsx_path": xlsx_path,
            "folder_path": folder,
            "images": images,
        })

    return folders


def discover_old_folders() -> List[Dict]:
    """Discover QA folders in QAfolderOLD."""
    return discover_qa_folders_in(QA_FOLDER_OLD)


def discover_new_folders() -> List[Dict]:
    """Discover QA folders in QAfolderNEW."""
    return discover_qa_folders_in(QA_FOLDER_NEW)


def group_folders_by_category(folders: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group discovered folders by category.

    Args:
        folders: List of folder dicts from discover_qa_folders

    Returns:
        Dict mapping category -> list of folder dicts
    """
    from collections import defaultdict
    grouped = defaultdict(list)
    for folder in folders:
        grouped[folder["category"]].append(folder)
    return dict(grouped)


def group_folders_by_language(folders: List[Dict], tester_mapping: Dict[str, str]) -> tuple:
    """
    Group discovered folders by tester language (EN/CN).

    Args:
        folders: List of folder dicts
        tester_mapping: Dict mapping tester name -> "EN" or "CN"

    Returns:
        Tuple of (en_folders_by_category, cn_folders_by_category)
    """
    from collections import defaultdict

    by_category_en = defaultdict(list)
    by_category_cn = defaultdict(list)

    print("\nRouting testers by language:")
    for qf in folders:
        username = qf["username"].strip()
        lang = tester_mapping.get(username, "EN")  # Default to EN
        in_mapping = username in tester_mapping
        print(f"  {username} ({qf['category']}) -> {lang}{'' if in_mapping else ' (not in mapping, default)'}")

        if lang == "CN":
            by_category_cn[qf["category"]].append(qf)
        else:
            by_category_en[qf["category"]].append(qf)

    return dict(by_category_en), dict(by_category_cn)
