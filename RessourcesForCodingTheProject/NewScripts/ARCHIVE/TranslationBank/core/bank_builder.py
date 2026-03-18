"""
Bank Builder Module
===================
Build translation banks from XML files with 3-level indexing.
"""

import json
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from .xml_parser import parse_xml, iter_xml_files
from .unique_key import generate_level1_key, generate_level2_key, generate_level3_key

log = logging.getLogger(__name__)

# Import config for attribute names
try:
    from config import LOCSTR_ELEMENT, ATTR_STRING_ID, ATTR_STR_ORIGIN, ATTR_STR
except ImportError:
    LOCSTR_ELEMENT = "LocStr"
    ATTR_STRING_ID = "StringId"
    ATTR_STR_ORIGIN = "StrOrigin"
    ATTR_STR = "Str"


def _extract_entries_from_file(
    xml_path: Path,
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[Dict[str, Any]]:
    """
    Extract all LocStr entries from a single XML file.

    Returns list of entries with:
    - string_id, str_origin, str_translated
    - filename, position
    - prev_context, next_context (for Level 3 keys)
    """
    entries = []

    root = parse_xml(xml_path)
    if root is None:
        log.warning("Could not parse: %s", xml_path.name)
        return entries

    filename = xml_path.name

    # Collect all LocStr elements first
    all_locstrs = list(root.iter(LOCSTR_ELEMENT))

    for i, elem in enumerate(all_locstrs):
        string_id = elem.get(ATTR_STRING_ID, "")
        str_origin = elem.get(ATTR_STR_ORIGIN, "")
        str_translated = elem.get(ATTR_STR, "")

        # Skip entries without translation
        if not str_translated or not str_translated.strip():
            continue

        # Skip entries without origin (nothing to match on)
        if not str_origin or not str_origin.strip():
            continue

        # Get adjacent contexts for Level 3
        prev_origin = None
        prev_id = None
        next_origin = None
        next_id = None

        if i > 0:
            prev_elem = all_locstrs[i - 1]
            prev_origin = prev_elem.get(ATTR_STR_ORIGIN, "")
            prev_id = prev_elem.get(ATTR_STRING_ID, "")

        if i < len(all_locstrs) - 1:
            next_elem = all_locstrs[i + 1]
            next_origin = next_elem.get(ATTR_STR_ORIGIN, "")
            next_id = next_elem.get(ATTR_STRING_ID, "")

        entry = {
            "string_id": string_id,
            "str_origin": str_origin,
            "str_translated": str_translated,
            "filename": filename,
            "position": i,
            "prev_context": f"{prev_origin or ''}|{prev_id or ''}",
            "next_context": f"{next_origin or ''}|{next_id or ''}",
        }
        entries.append(entry)

    return entries


def build_bank(
    source_path: Path,
    recursive: bool = True,
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> Dict[str, Any]:
    """
    Build a translation bank from source XML file(s).

    Args:
        source_path: Single XML file or folder containing XML files
        recursive: If True, search subfolders (only for folder mode)
        progress_callback: Optional callback(message, current, total)

    Returns:
        Bank dictionary with metadata, entries, and indices
    """
    bank = {
        "metadata": {
            "created": datetime.now().isoformat(),
            "source_path": str(source_path),
            "entry_count": 0,
        },
        "entries": [],
        "indices": {
            "level1": {},  # hash -> entry_index
            "level2": {},  # string_id -> [entry_indices]
            "level3": {},  # hash -> entry_index
        }
    }

    # Collect files to process
    if source_path.is_file():
        xml_files = [source_path]
    else:
        xml_files = list(iter_xml_files(source_path, recursive=recursive))

    total_files = len(xml_files)
    log.info("Building bank from %d XML file(s)...", total_files)

    if progress_callback:
        progress_callback("Scanning files...", 0, total_files)

    # Process each file
    for file_idx, xml_path in enumerate(xml_files):
        if progress_callback:
            progress_callback(f"Processing: {xml_path.name}", file_idx + 1, total_files)

        file_entries = _extract_entries_from_file(xml_path)

        for entry in file_entries:
            entry_idx = len(bank["entries"])
            bank["entries"].append(entry)

            # Build Level 1 index (StrOrigin + StringId)
            level1_key = generate_level1_key(
                entry["str_origin"],
                entry["string_id"]
            )
            # Level 1 should be unique, but handle collisions by keeping first
            if level1_key not in bank["indices"]["level1"]:
                bank["indices"]["level1"][level1_key] = entry_idx

            # Build Level 2 index (StringId only) - may have multiple
            level2_key = generate_level2_key(entry["string_id"])
            if level2_key:
                if level2_key not in bank["indices"]["level2"]:
                    bank["indices"]["level2"][level2_key] = []
                bank["indices"]["level2"][level2_key].append(entry_idx)

            # Build Level 3 index (context-aware)
            # Parse prev/next context
            prev_parts = entry["prev_context"].split("|", 1)
            prev_origin = prev_parts[0] if prev_parts else ""
            prev_id = prev_parts[1] if len(prev_parts) > 1 else ""

            next_parts = entry["next_context"].split("|", 1)
            next_origin = next_parts[0] if next_parts else ""
            next_id = next_parts[1] if len(next_parts) > 1 else ""

            level3_key = generate_level3_key(
                entry["str_origin"],
                entry["filename"],
                prev_origin, prev_id,
                next_origin, next_id
            )
            if level3_key not in bank["indices"]["level3"]:
                bank["indices"]["level3"][level3_key] = entry_idx

    bank["metadata"]["entry_count"] = len(bank["entries"])

    log.info("Bank built: %d entries from %d files", len(bank["entries"]), total_files)
    log.info("  Level 1 keys: %d", len(bank["indices"]["level1"]))
    log.info("  Level 2 keys: %d", len(bank["indices"]["level2"]))
    log.info("  Level 3 keys: %d", len(bank["indices"]["level3"]))

    return bank


def save_bank(bank: Dict[str, Any], output_path: Path) -> bool:
    """
    Save bank to file (PKL or JSON based on extension).

    PKL is default for 150k+ entries (fast load/save).
    JSON available for debugging (human-readable).

    Args:
        bank: Bank dictionary
        output_path: Path to output file (.pkl or .json)

    Returns:
        True if successful
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix.lower() == ".json":
            # JSON format (slower but human-readable)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(bank, f, ensure_ascii=False, indent=2)
            log.info("Bank saved (JSON): %s (%d entries)", output_path, bank["metadata"]["entry_count"])
        else:
            # PKL format (fast, default for large banks)
            with open(output_path, "wb") as f:
                pickle.dump(bank, f, protocol=pickle.HIGHEST_PROTOCOL)
            log.info("Bank saved (PKL): %s (%d entries)", output_path, bank["metadata"]["entry_count"])

        return True

    except Exception:
        log.exception("Failed to save bank: %s", output_path)
        return False


def load_bank(bank_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load bank from file (PKL or JSON based on extension).

    Args:
        bank_path: Path to bank file (.pkl or .json)

    Returns:
        Bank dictionary or None if failed
    """
    try:
        if bank_path.suffix.lower() == ".json":
            # JSON format
            with open(bank_path, "r", encoding="utf-8") as f:
                bank = json.load(f)
            log.info("Bank loaded (JSON): %s (%d entries)", bank_path.name, bank["metadata"]["entry_count"])
        else:
            # PKL format
            with open(bank_path, "rb") as f:
                bank = pickle.load(f)
            log.info("Bank loaded (PKL): %s (%d entries)", bank_path.name, bank["metadata"]["entry_count"])

        return bank

    except Exception:
        log.exception("Failed to load bank: %s", bank_path)
        return None
