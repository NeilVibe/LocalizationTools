"""
Bank Transfer Module
====================
Transfer translations from bank to target XML files using 3-level fallback.
"""

import json
import logging
import pickle
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

from lxml import etree as ET

from .xml_parser import parse_xml, iter_xml_files, sanitize_xml
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


@dataclass
class TransferStats:
    """Statistics for a transfer operation."""
    total_entries: int = 0
    hit_level1: int = 0
    hit_level2: int = 0
    hit_level3: int = 0
    miss: int = 0
    files_processed: int = 0
    files_modified: int = 0

    @property
    def total_hits(self) -> int:
        return self.hit_level1 + self.hit_level2 + self.hit_level3

    @property
    def hit_rate(self) -> float:
        if self.total_entries == 0:
            return 0.0
        return self.total_hits / self.total_entries * 100

    def to_report(self, bank_path: str, target_path: str) -> str:
        """Generate formatted report."""
        lines = [
            "",
            "=" * 70,
            "              TRANSLATION BANK TRANSFER REPORT",
            "=" * 70,
            "",
            f"Bank:   {bank_path}",
            f"Target: {target_path}",
            "",
            "-" * 70,
            "                     MATCH SUMMARY",
            "-" * 70,
            f"Total Target Entries:     {self.total_entries:>10,}",
            "-" * 70,
        ]

        if self.total_entries > 0:
            hit_pct = self.total_hits / self.total_entries * 100
            l1_pct = self.hit_level1 / self.total_entries * 100
            l2_pct = self.hit_level2 / self.total_entries * 100
            l3_pct = self.hit_level3 / self.total_entries * 100
            miss_pct = self.miss / self.total_entries * 100

            lines.extend([
                f"HIT  (Total):             {self.total_hits:>10,}    ({hit_pct:>5.1f}%)",
                f"  Level 1 (StrOrigin+ID): {self.hit_level1:>10,}    ({l1_pct:>5.1f}%)",
                f"  Level 2 (ID only):      {self.hit_level2:>10,}    ({l2_pct:>5.1f}%)",
                f"  Level 3 (Context):      {self.hit_level3:>10,}    ({l3_pct:>5.1f}%)",
                "-" * 70,
                f"MISS:                     {self.miss:>10,}    ({miss_pct:>5.1f}%)",
            ])
        else:
            lines.append("No entries processed.")

        lines.extend([
            "=" * 70,
            "",
            f"Files processed: {self.files_processed}",
            f"Files modified:  {self.files_modified}",
            "",
        ])

        return "\n".join(lines)


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
            with open(bank_path, "r", encoding="utf-8") as f:
                bank = json.load(f)
            log.info("Bank loaded (JSON): %s (%d entries)", bank_path.name, bank["metadata"]["entry_count"])
        else:
            with open(bank_path, "rb") as f:
                bank = pickle.load(f)
            log.info("Bank loaded (PKL): %s (%d entries)", bank_path.name, bank["metadata"]["entry_count"])

        return bank

    except Exception:
        log.exception("Failed to load bank: %s", bank_path)
        return None


def _lookup_translation(
    bank: Dict[str, Any],
    str_origin: str,
    string_id: str,
    filename: str,
    prev_origin: str,
    prev_id: str,
    next_origin: str,
    next_id: str
) -> tuple[Optional[str], int]:
    """
    Look up translation using 3-level fallback.

    Returns:
        (translation, level) where level is 1, 2, 3, or 0 for miss
    """
    entries = bank["entries"]
    indices = bank["indices"]

    # Level 1: StrOrigin + StringId
    level1_key = generate_level1_key(str_origin, string_id)
    if level1_key in indices["level1"]:
        entry_idx = indices["level1"][level1_key]
        return entries[entry_idx]["str_translated"], 1

    # Level 2: StringId only
    level2_key = generate_level2_key(string_id)
    if level2_key and level2_key in indices["level2"]:
        entry_indices = indices["level2"][level2_key]
        if entry_indices:
            # If multiple matches, prefer one with matching origin
            for idx in entry_indices:
                if entries[idx]["str_origin"].strip() == str_origin.strip():
                    return entries[idx]["str_translated"], 2
            # Otherwise return first match
            return entries[entry_indices[0]]["str_translated"], 2

    # Level 3: Context-aware
    level3_key = generate_level3_key(
        str_origin, filename,
        prev_origin, prev_id,
        next_origin, next_id
    )
    if level3_key in indices["level3"]:
        entry_idx = indices["level3"][level3_key]
        return entries[entry_idx]["str_translated"], 3

    # Miss
    return None, 0


def _transfer_single_file(
    xml_path: Path,
    bank: Dict[str, Any],
    output_path: Path,
    stats: TransferStats
) -> bool:
    """
    Transfer translations to a single XML file.

    Uses regex-based replacement to preserve original formatting.

    Returns:
        True if file was modified
    """
    try:
        raw_content = xml_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        log.exception("Failed to read: %s", xml_path)
        return False

    # Parse for structure (to get adjacent contexts)
    root = parse_xml(xml_path)
    if root is None:
        log.warning("Could not parse: %s", xml_path.name)
        return False

    filename = xml_path.name
    all_locstrs = list(root.iter(LOCSTR_ELEMENT))

    modified = False
    new_content = raw_content

    for i, elem in enumerate(all_locstrs):
        string_id = elem.get(ATTR_STRING_ID, "")
        str_origin = elem.get(ATTR_STR_ORIGIN, "")
        current_translation = elem.get(ATTR_STR, "")

        # Skip if already has translation
        if current_translation and current_translation.strip():
            continue

        # Skip if no origin
        if not str_origin or not str_origin.strip():
            continue

        stats.total_entries += 1

        # Get adjacent contexts
        prev_origin = ""
        prev_id = ""
        next_origin = ""
        next_id = ""

        if i > 0:
            prev_elem = all_locstrs[i - 1]
            prev_origin = prev_elem.get(ATTR_STR_ORIGIN, "")
            prev_id = prev_elem.get(ATTR_STRING_ID, "")

        if i < len(all_locstrs) - 1:
            next_elem = all_locstrs[i + 1]
            next_origin = next_elem.get(ATTR_STR_ORIGIN, "")
            next_id = next_elem.get(ATTR_STRING_ID, "")

        # Look up translation
        translation, level = _lookup_translation(
            bank, str_origin, string_id, filename,
            prev_origin, prev_id, next_origin, next_id
        )

        if translation and level > 0:
            # Update stats
            if level == 1:
                stats.hit_level1 += 1
            elif level == 2:
                stats.hit_level2 += 1
            elif level == 3:
                stats.hit_level3 += 1

            # Build regex to find this specific LocStr element
            # Match by StringId and StrOrigin combination
            escaped_id = re.escape(string_id)
            escaped_origin = re.escape(str_origin)

            # Pattern to match LocStr with these attributes and empty/missing Str
            # This handles various attribute orderings
            pattern = (
                rf'(<{LOCSTR_ELEMENT}\s+'
                rf'[^>]*{ATTR_STRING_ID}\s*=\s*"{escaped_id}"'
                rf'[^>]*{ATTR_STR_ORIGIN}\s*=\s*"{escaped_origin}"'
                rf'[^>]*){ATTR_STR}\s*=\s*""([^>]*/?>)'
            )

            # Escape special chars in translation for replacement
            safe_translation = translation.replace("\\", "\\\\").replace('"', '&quot;')

            replacement = rf'\g<1>{ATTR_STR}="{safe_translation}"\g<2>'

            new_content_test = re.sub(pattern, replacement, new_content, count=1, flags=re.DOTALL)

            if new_content_test != new_content:
                new_content = new_content_test
                modified = True
            else:
                # Try alternate attribute order (StrOrigin before StringId)
                pattern_alt = (
                    rf'(<{LOCSTR_ELEMENT}\s+'
                    rf'[^>]*{ATTR_STR_ORIGIN}\s*=\s*"{escaped_origin}"'
                    rf'[^>]*{ATTR_STRING_ID}\s*=\s*"{escaped_id}"'
                    rf'[^>]*){ATTR_STR}\s*=\s*""([^>]*/?>)'
                )
                new_content_test = re.sub(pattern_alt, replacement, new_content, count=1, flags=re.DOTALL)
                if new_content_test != new_content:
                    new_content = new_content_test
                    modified = True

        else:
            stats.miss += 1

    # Write output if modified
    if modified:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(new_content, encoding="utf-8")
            stats.files_modified += 1
            return True
        except Exception:
            log.exception("Failed to write: %s", output_path)
            return False

    return False


def transfer_translations(
    bank_path: Path,
    target_path: Path,
    output_path: Optional[Path] = None,
    recursive: bool = True,
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> TransferStats:
    """
    Transfer translations from bank to target XML files.

    Args:
        bank_path: Path to bank JSON file
        target_path: Single XML file or folder
        output_path: Output location (if None, modifies in place)
        recursive: Search subfolders for folder mode
        progress_callback: Optional callback(message, current, total)

    Returns:
        TransferStats with results
    """
    stats = TransferStats()

    # Load bank
    bank = load_bank(bank_path)
    if bank is None:
        log.error("Failed to load bank: %s", bank_path)
        return stats

    # Collect target files
    if target_path.is_file():
        target_files = [target_path]
    else:
        target_files = list(iter_xml_files(target_path, recursive=recursive))

    total_files = len(target_files)
    log.info("Transferring to %d XML file(s)...", total_files)

    if progress_callback:
        progress_callback("Starting transfer...", 0, total_files)

    for file_idx, xml_path in enumerate(target_files):
        stats.files_processed += 1

        if progress_callback:
            progress_callback(f"Processing: {xml_path.name}", file_idx + 1, total_files)

        # Determine output path
        if output_path is None:
            file_output = xml_path  # In-place
        elif output_path.is_dir():
            # Preserve relative structure
            try:
                rel_path = xml_path.relative_to(target_path)
            except ValueError:
                rel_path = Path(xml_path.name)
            file_output = output_path / rel_path
        else:
            file_output = output_path

        _transfer_single_file(xml_path, bank, file_output, stats)

    # Log summary
    report = stats.to_report(str(bank_path), str(target_path))
    log.info(report)

    return stats
