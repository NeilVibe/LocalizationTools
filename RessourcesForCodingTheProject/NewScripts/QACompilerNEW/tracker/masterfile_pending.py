"""
Masterfile Pending Issue Reader
===============================
Given Masterfolder_EN and Masterfolder_CN paths, extract per-tester per-category
status counts from TESTER_STATUS_{user} + STATUS_{user} column pairs.

Single responsibility: read masterfiles -> return structured counts.
"""
from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import logging
from openpyxl import load_workbook

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

# Master filename -> category mapping (reverse of CATEGORY_TO_MASTER)
# Master_Script.xlsx contains Sequencer + Dialog sheets -> category "Script"
# Master_System.xlsx contains System + Help sheets -> category "System"
# Master_Item.xlsx contains Item + Gimmick sheets -> category "Item"
# All others: Master_Quest.xlsx -> "Quest", etc.
_MASTER_FILE_TO_CATEGORY = {
    "master_script": "Script",
    "master_system": "System",
    "master_item": "Item",
    "master_quest": "Quest",
    "master_knowledge": "Knowledge",
    "master_region": "Region",
    "master_character": "Character",
    "master_skill": "Skill",
    "master_itemknowledgecluster": "ItemKnowledgeCluster",
    "master_face": "Face",
    "master_contents": "Contents",
}

_TESTER_STATUS_PREFIX = "TESTER_STATUS_"
_STATUS_PREFIX = "STATUS_"

# Sheets to skip
_SKIP_SHEETS = {"STATUS"}


def _extract_category_from_filename(filename: str) -> Optional[str]:
    """Extract category from Master_XXX.xlsx filename."""
    stem = Path(filename).stem.lower()
    return _MASTER_FILE_TO_CATEGORY.get(stem)


def _discover_latest_masterfiles(folder: Path) -> Dict[str, Path]:
    """
    Recursively find Master_*.xlsx files, group by category,
    keep only the latest mtime per category.

    Returns: {category: path}
    """
    if not folder.exists():
        return {}

    candidates: Dict[str, List[Tuple[float, Path]]] = defaultdict(list)

    for path in folder.rglob("Master_*.xlsx"):
        # Skip temp files
        if path.name.startswith("~"):
            continue

        category = _extract_category_from_filename(path.name)
        if category is None:
            logger.debug(f"Skipping unrecognized masterfile: {path.name}")
            continue

        mtime = path.stat().st_mtime
        candidates[category].append((mtime, path))

    # Keep latest per category
    result = {}
    for category, entries in candidates.items():
        entries.sort(key=lambda x: x[0], reverse=True)
        result[category] = entries[0][1]

    return result


def _classify_status(raw_status: Optional[str]) -> str:
    """
    Classify a manager STATUS_{user} value.

    Returns one of: 'pending', 'fixed', 'reported', 'checking', 'nonissue'
    """
    if raw_status is None or str(raw_status).strip() == "":
        return "pending"

    normalized = str(raw_status).strip().upper()

    if normalized == "FIXED":
        return "fixed"
    if normalized == "REPORTED":
        return "reported"
    if normalized == "CHECKING":
        return "checking"
    if normalized in ("NON-ISSUE", "NON ISSUE"):
        return "nonissue"

    # Unknown status -> treat as pending
    return "pending"


def _empty_counts() -> Dict[str, int]:
    """Return a fresh zero-initialized status count dict."""
    return {
        "active_issues": 0,
        "pending": 0,
        "fixed": 0,
        "reported": 0,
        "checking": 0,
        "nonissue": 0,
    }


def _read_master_statuses(
    master_path: Path, category: str
) -> Dict[str, Dict[str, int]]:
    """
    Read TESTER_STATUS_{user} + STATUS_{user} columns from all non-STATUS sheets.

    Returns: {username: {active_issues, pending, fixed, reported, checking, nonissue}}
    """
    result: Dict[str, Dict[str, int]] = {}

    try:
        wb = load_workbook(master_path, read_only=True, data_only=True)
    except Exception as exc:
        logger.warning(f"Failed to open {master_path}: {exc}")
        return result

    try:
        for ws in wb.worksheets:
            if ws.title in _SKIP_SHEETS:
                continue

            # Read headers from first row using iter_rows
            headers = []
            for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
                headers = [str(h) if h is not None else "" for h in row]
                break

            if not headers:
                continue

            # Find TESTER_STATUS_{user} and STATUS_{user} column pairs
            # Map: username -> (tester_status_idx, status_idx)
            user_columns: Dict[str, Tuple[int, Optional[int]]] = {}

            for idx, hdr in enumerate(headers):
                hdr_upper = hdr.upper()
                if hdr_upper.startswith(_TESTER_STATUS_PREFIX.upper()):
                    username = hdr[len(_TESTER_STATUS_PREFIX):].strip()
                    if username:
                        # Find matching STATUS_{username}
                        status_col_name = f"{_STATUS_PREFIX}{username}"
                        status_idx = None
                        for sidx, shdr in enumerate(headers):
                            if shdr.upper() == status_col_name.upper():
                                status_idx = sidx
                                break
                        user_columns[username] = (idx, status_idx)

            if not user_columns:
                continue

            # Process data rows
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not any(row):
                    continue

                for username, (ts_idx, s_idx) in user_columns.items():
                    # Check TESTER_STATUS value
                    tester_status = row[ts_idx] if ts_idx < len(row) else None
                    if tester_status is None:
                        continue
                    if str(tester_status).strip().upper() != "ISSUE":
                        continue

                    # This row is an active issue for this user
                    if username not in result:
                        result[username] = _empty_counts()

                    counts = result[username]
                    counts["active_issues"] += 1

                    # Get manager status
                    manager_status = None
                    if s_idx is not None and s_idx < len(row):
                        manager_status = row[s_idx]

                    classification = _classify_status(manager_status)

                    if classification == "checking":
                        # CHECKING = manager is reviewing but hasn't resolved.
                        # Counts as BOTH checking AND pending (pending = unresolved).
                        # NOTE: This means active_issues != pending + fixed + reported + checking + nonissue
                        # because checking rows are in both pending and checking.
                        counts["checking"] += 1
                        counts["pending"] += 1
                    else:
                        counts[classification] += 1

    finally:
        wb.close()

    return result


def build_pending_from_masterfiles(
    masterfolder_en: Path,
    masterfolder_cn: Path,
) -> Dict[str, Dict[str, Dict[str, int]]]:
    """
    Build pending issue counts from masterfiles in EN and CN folders.

    Returns:
        {username: {category: {active_issues, pending, fixed, reported, checking, nonissue}}}
    """
    # Discover latest masterfiles from both folders (dedup within each folder)
    en_masters = _discover_latest_masterfiles(masterfolder_en)
    cn_masters = _discover_latest_masterfiles(masterfolder_cn)

    # Collect all masterfiles to read: EN and CN are independent language folders
    # with different testers, so read BOTH. Dedup only within the same folder.
    masters_to_read: List[Tuple[str, Path]] = []
    for cat, path in en_masters.items():
        masters_to_read.append((cat, path))
    for cat, path in cn_masters.items():
        masters_to_read.append((cat, path))

    # Read statuses from each masterfile and merge
    result: Dict[str, Dict[str, Dict[str, int]]] = {}

    for category, master_path in masters_to_read:
        logger.debug(f"Reading {category} from {master_path}")
        user_counts = _read_master_statuses(master_path, category)

        for username, counts in user_counts.items():
            if username not in result:
                result[username] = {}
            if category in result[username]:
                # Merge counts additively (e.g., same tester in EN + CN)
                existing = result[username][category]
                for key in counts:
                    existing[key] += counts[key]
            else:
                result[username][category] = counts

    return result
