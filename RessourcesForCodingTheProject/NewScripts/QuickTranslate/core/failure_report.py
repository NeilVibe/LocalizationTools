"""
Failure Report Generator - Generate failure reports in XML and Excel formats.

Creates structured reports of LocStr entries that failed to merge:
- XML format: FAILED_TO_MERGE.xml grouped by source file
- Excel format: Multi-sheet workbook with summary, breakdown by reason/file, details

Uses xlsxwriter for reliable Excel generation (NOT openpyxl).
"""

import logging
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

# Try lxml first (more robust), fallback to standard library
try:
    from lxml import etree
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as etree
    USING_LXML = False

# Try xlsxwriter for Excel reports
try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# Word-level diff (ported from VRSManager strorigin_analysis.py)
# =============================================================================

def _get_strorigin_from_attribs(attribs: Dict) -> str:
    """Extract StrOrigin value from raw XML attributes dict, trying all case variants."""
    for key in ('StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN'):
        val = attribs.get(key)
        if val is not None:
            return val
    return ""


def extract_differences(text1: str, text2: str, max_length: int = 2000) -> str:
    """
    Extract WORD-LEVEL differences between two texts using difflib.

    Shows exactly what changed in WinMerge style with automatic chunking:
    - [old words→new words] for replacements (consecutive words grouped)
    - [-deleted words] for deletions
    - [+added words] for additions
    - [SPACING] when texts differ only by whitespace

    Args:
        text1: Previous text (old StrOrigin from correction source)
        text2: Current text (new StrOrigin from target XML)
        max_length: Maximum length for diff output (truncate if longer)

    Returns:
        Diff string showing changes, or empty string if no changes
    """
    if not text1 or not text2:
        return ""

    # Detect spacing-only differences before word-level split normalizes them away
    if text1 != text2 and text1.split() == text2.split():
        return "[SPACING ONLY]"

    words1 = text1.split()
    words2 = text2.split()

    matcher = SequenceMatcher(None, words1, words2)
    changes = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            old_words = ' '.join(words1[i1:i2])
            new_words = ' '.join(words2[j1:j2])
            changes.append(f"[{old_words}\u2192{new_words}]")
        elif tag == 'delete':
            deleted_words = ' '.join(words1[i1:i2])
            changes.append(f"[-{deleted_words}]")
        elif tag == 'insert':
            added_words = ' '.join(words2[j1:j2])
            changes.append(f"[+{added_words}]")

    if not changes:
        return ""

    diff_str = ' '.join(changes)

    if len(diff_str) > max_length:
        diff_str = diff_str[:max_length - 3] + "..."

    return diff_str


# =============================================================================
# Failure Reason Categories (for Excel reports)
# =============================================================================

FAILURE_REASONS = {
    "NOT_FOUND": "StringID not found in target",
    "STRORIGIN_MISMATCH": "StrOrigin mismatch",
    "DESCORIGIN_MISMATCH": "DescOrigin mismatch (StrOrigin matches but DescOrigin differs)",
    "SKIPPED_EMPTY_STRORIGIN": "StringID exists but StrOrigin empty in target (skipped)",
    "SKIPPED_TRANSLATED": "Already translated (skipped)",
    "SKIPPED_NON_SCRIPT": "Not a SCRIPT category (skipped)",
    "SKIPPED_SCRIPT": "SCRIPT category — use StringID-Only (skipped)",
    "SKIPPED_EXCLUDED": "Excluded subfolder (skipped)",
    "SKIPPED_NO_TRANSLATION": "Correction is 'no translation' (skipped)",
    "SKIPPED_DUPLICATE_STRORIGIN": "Duplicate StrOrigin in corrections (skipped)",
    "PARSE_ERROR": "Failed to parse correction",
    "WRITE_ERROR": "Failed to write to target file",
    "OTHER": "Other/Unknown error",
}

# StrOrigin-only overrides for mode-sensitive labels
_FAILURE_REASONS_STRORIGIN = {
    "NOT_FOUND": "StrOrigin text not found in target",
}


def _get_failure_reason(key: str, match_mode: str = "") -> str:
    """Get failure reason label, adapting to match mode."""
    if match_mode.startswith("strorigin_only") and key in _FAILURE_REASONS_STRORIGIN:
        return _FAILURE_REASONS_STRORIGIN[key]
    if match_mode.startswith("strorigin_descorigin"):
        if key == "NOT_FOUND":
            return "StrOrigin + DescOrigin combo not found in target"
        if key == "DESCORIGIN_MISMATCH":
            return FAILURE_REASONS[key]
    return FAILURE_REASONS.get(key, key)


def _classify_failure_reason(detail: Dict) -> str:
    """
    Classify a detail entry into a failure reason category.

    Args:
        detail: A detail dict from merge results with 'status' key

    Returns:
        Failure reason key from FAILURE_REASONS
    """
    status = detail.get("status", "").upper()

    if "SKIPPED_EMPTY_STRORIGIN" in status:
        return "SKIPPED_EMPTY_STRORIGIN"
    elif "NOT_FOUND" in status:
        return "NOT_FOUND"
    elif "DESCORIGIN_MISMATCH" in status:
        return "DESCORIGIN_MISMATCH"
    elif "MISMATCH" in status:
        return "STRORIGIN_MISMATCH"
    elif "SKIPPED_TRANSLATED" in status:
        return "SKIPPED_TRANSLATED"
    elif "SKIPPED_NON_SCRIPT" in status:
        return "SKIPPED_NON_SCRIPT"
    elif "SKIPPED_SCRIPT" in status:
        return "SKIPPED_SCRIPT"
    elif "SKIPPED_EXCLUDED" in status:
        return "SKIPPED_EXCLUDED"
    elif "SKIPPED_NO_TRANSLATION" in status:
        return "SKIPPED_NO_TRANSLATION"
    elif "SKIPPED_DUPLICATE_STRORIGIN" in status:
        return "SKIPPED_DUPLICATE_STRORIGIN"
    elif "ERROR" in status:
        return "PARSE_ERROR"
    else:
        return "OTHER"


def _is_failure(detail: Dict) -> bool:
    """Check if a detail entry represents a failure (not a success).

    SKIPPED_TRANSLATED is by design (untranslated-only scope), not a failure.
    """
    status = detail.get("status", "").upper()
    # Strip RECOVERED_ prefix — these come from the EventName recovery pass
    # in xml_transfer.py and represent successful recoveries, not failures.
    if status.startswith("RECOVERED_"):
        status = status[len("RECOVERED_"):]
    # Success / by-design statuses
    if status in ("UPDATED", "UNCHANGED", "SKIPPED_TRANSLATED", "SKIPPED_NO_TRANSLATION",
                  "SKIPPED_NON_SCRIPT", "SKIPPED_SCRIPT", "SKIPPED_EXCLUDED",
                  "SKIPPED_DUPLICATE_STRORIGIN"):
        return False
    # Match level suffixes are success
    if status.startswith("UPDATED (") or status.startswith("UNCHANGED ("):
        return False
    return True


def check_xlsxwriter_available() -> bool:
    """Check if xlsxwriter is available for Excel report generation."""
    return XLSXWRITER_AVAILABLE


def generate_failed_merge_xml(
    failed_entries: List[Dict],
    output_path: Path,
    timestamp: Optional[datetime] = None,
) -> Path:
    """
    Generate a FAILED_TO_MERGE.xml file from a list of failed LocStr entries.

    The output XML groups entries by source file and includes:
    - Timestamp and total count in root element
    - Per-file grouping with language code and failed count
    - Each failed LocStr with StringId, StrOrigin, Str, and FailReason

    Args:
        failed_entries: List of dicts, each containing:
            - string_id: The StringID of the failed entry
            - str_origin: The Korean source text (StrOrigin)
            - str: The translation text (Str) that failed to merge
            - fail_reason: Human-readable reason for failure
            - source_file: Source filename (e.g., "itemequip_weapon.loc.xml")
            - language: Language code (e.g., "FRE", "GER")
            Optional:
            - category: Category name (e.g., "System", "Dialog")
            - subfolder: Subfolder path
        output_path: Path where FAILED_TO_MERGE.xml will be written
        timestamp: Optional timestamp (defaults to now)

    Returns:
        Path to the generated XML file

    Example output:
        <?xml version="1.0" encoding="utf-8"?>
        <FailedMerges timestamp="2026-02-05T14:30:00" total="45">
          <SourceFile name="itemequip_weapon.loc.xml" language="FRE" failed="12">
            <LocStr StringId="UI_001" StrOrigin="확인" Str="OK"
                    FailReason="StringID not found in target"/>
            ...
          </SourceFile>
        </FailedMerges>
    """
    if timestamp is None:
        timestamp = datetime.now()

    # Group entries by source file
    by_source = defaultdict(list)
    for entry in failed_entries:
        source_file = entry.get("source_file", "unknown.xml")
        by_source[source_file].append(entry)

    total_failed = len(failed_entries)
    timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S")

    if USING_LXML:
        # lxml: create with proper encoding handling
        root = etree.Element(
            "FailedMerges",
            timestamp=timestamp_str,
            total=str(total_failed),
        )

        for source_file, entries in sorted(by_source.items()):
            # Determine language (take from first entry, should be same for all in file)
            language = entries[0].get("language", "UNK") if entries else "UNK"

            source_elem = etree.SubElement(
                root,
                "SourceFile",
                name=source_file,
                language=language.upper(),
                failed=str(len(entries)),
            )

            for entry in entries:
                # Build attributes dict, handling None values
                attribs = {
                    "StringId": str(entry.get("string_id", "")),
                    "StrOrigin": str(entry.get("str_origin", "")),
                    "Str": str(entry.get("str", "")),
                    "FailReason": str(entry.get("fail_reason", "Unknown reason")),
                }

                # Add optional attributes if present
                if entry.get("category"):
                    attribs["Category"] = str(entry["category"])
                if entry.get("subfolder"):
                    attribs["Subfolder"] = str(entry["subfolder"])

                etree.SubElement(source_elem, "LocStr", **attribs)

        # Write with proper encoding and declaration
        tree = etree.ElementTree(root)
        tree.write(
            str(output_path),
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )

    else:
        # Standard library ElementTree
        root = etree.Element("FailedMerges")
        root.set("timestamp", timestamp_str)
        root.set("total", str(total_failed))

        for source_file, entries in sorted(by_source.items()):
            language = entries[0].get("language", "UNK") if entries else "UNK"

            source_elem = etree.SubElement(root, "SourceFile")
            source_elem.set("name", source_file)
            source_elem.set("language", language.upper())
            source_elem.set("failed", str(len(entries)))

            for entry in entries:
                loc_elem = etree.SubElement(source_elem, "LocStr")
                loc_elem.set("StringId", str(entry.get("string_id", "")))
                loc_elem.set("StrOrigin", str(entry.get("str_origin", "")))
                loc_elem.set("Str", str(entry.get("str", "")))
                loc_elem.set("FailReason", str(entry.get("fail_reason", "Unknown reason")))

                if entry.get("category"):
                    loc_elem.set("Category", str(entry["category"]))
                if entry.get("subfolder"):
                    loc_elem.set("Subfolder", str(entry["subfolder"]))

        # Write with declaration
        tree = etree.ElementTree(root)
        with open(output_path, "wb") as f:
            f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
            tree.write(f, encoding="utf-8", xml_declaration=False)

    logger.info(f"Generated failure report: {output_path} ({total_failed} entries)")
    return output_path


def generate_failed_merge_xml_per_language(
    failed_entries: List[Dict],
    output_folder: Path,
    timestamp: Optional[datetime] = None,
    preserve_all_attribs: bool = False,
) -> Dict[str, Path]:
    """
    Generate separate XML files for each language with failed LocStr elements.

    Creates CLEAN XML files - just <root> with <LocStr> elements inside.
    By default outputs only StringId, StrOrigin, Str (core attributes).
    Set preserve_all_attribs=True for full raw LocStr (e.g. NewStrOrigin reports).

    Args:
        failed_entries: List of failed entry dicts with 'language' key
        output_folder: Folder where XML files will be written
        timestamp: Optional timestamp (defaults to now)
        preserve_all_attribs: If True, dump all raw_attribs. If False, only core keys.

    Returns:
        Dict mapping language code to output file path
    """
    if timestamp is None:
        timestamp = datetime.now()

    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

    # Group entries by language
    by_language = defaultdict(list)
    for entry in failed_entries:
        lang = entry.get("language", "UNK").upper()
        by_language[lang].append(entry)

    output_files = {}

    # Core attributes for clean failure reports
    _CORE_KEYS = {"StringId", "StrOrigin", "Str"}

    for lang, entries in sorted(by_language.items()):
        output_path = output_folder / f"FAILED_{lang}_{timestamp_str}.xml"

        if USING_LXML:
            root = etree.Element("root")

            for entry in entries:
                raw = entry.get("raw_attribs", {})
                if raw:
                    if preserve_all_attribs:
                        attribs = {k: str(v) for k, v in raw.items()}
                    else:
                        attribs = {k: str(v) for k, v in raw.items() if k in _CORE_KEYS}
                    etree.SubElement(root, "LocStr", **attribs)
                else:
                    etree.SubElement(root, "LocStr",
                        StringId=str(entry.get("string_id", "")),
                        StrOrigin=str(entry.get("str_origin", "")),
                        Str=str(entry.get("str", "")),
                    )

            tree = etree.ElementTree(root)
            tree.write(
                str(output_path),
                encoding="utf-8",
                xml_declaration=True,
                pretty_print=True,
            )

        else:
            root = etree.Element("root")

            for entry in entries:
                loc_elem = etree.SubElement(root, "LocStr")
                raw = entry.get("raw_attribs", {})
                if raw:
                    if preserve_all_attribs:
                        for k, v in raw.items():
                            loc_elem.set(k, str(v))
                    else:
                        for k, v in raw.items():
                            if k in _CORE_KEYS:
                                loc_elem.set(k, str(v))
                else:
                    loc_elem.set("StringId", str(entry.get("string_id", "")))
                    loc_elem.set("StrOrigin", str(entry.get("str_origin", "")))
                    loc_elem.set("Str", str(entry.get("str", "")))

            tree = etree.ElementTree(root)
            with open(output_path, "wb") as f:
                f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
                tree.write(f, encoding="utf-8", xml_declaration=False)

        output_files[lang] = output_path
        logger.info(f"Generated {lang} failed strings: {output_path.name} ({len(entries)} entries)")

    return output_files


def extract_failed_from_transfer_results(
    results: Dict,
    source_file_name: str = "unknown.xml",
    language: str = "UNK",
) -> List[Dict]:
    """
    Extract failed entries from merge results.

    Converts the 'details' list from merge results into the format
    expected by generate_failed_merge_xml.

    Args:
        results: Results dict from merge_corrections_to_xml or similar
        source_file_name: Name of the source file being processed
        language: Language code for the entries

    Returns:
        List of failed entry dicts ready for generate_failed_merge_xml
    """
    failed_entries = []
    mm = results.get("match_mode", "")

    details = results.get("details", [])
    for detail in details:
        if not _is_failure(detail):
            continue
        status = detail.get("status", "")
        if "NOT_FOUND" in status or "MISMATCH" in status or "SKIPPED" in status:
            fail_reason = _status_to_reason(status, mm)

            failed_entries.append({
                "string_id": detail.get("string_id", ""),
                "str_origin": detail.get("old", ""),
                "str": detail.get("new", ""),
                "fail_reason": fail_reason,
                "source_file": source_file_name,
                "language": language,
                "raw_attribs": detail.get("raw_attribs", {}),  # EXACT original attributes
            })

    return failed_entries


def extract_failed_from_folder_results(
    results: Dict,
) -> List[Dict]:
    """
    Extract all failed entries from transfer_folder_to_folder results.

    Iterates through per-file results and aggregates all failures.
    Language is extracted from TARGET filename (languagedata_XXX.xml pattern),
    which is always correct and reliable.

    Args:
        results: Results dict from transfer_folder_to_folder

    Returns:
        List of failed entry dicts ready for generate_failed_merge_xml
    """
    all_failed = []
    mm = results.get("match_mode", "")

    file_results = results.get("file_results", {})
    for source_file, fresult in file_results.items():
        # Extract language from TARGET filename (always languagedata_XXX.xml format)
        # This is more reliable than extracting from source filename which can vary
        target_file = fresult.get("target", "")
        language = _extract_language_from_filename(target_file) if target_file else "UNK"

        details = fresult.get("details", [])
        for detail in details:
            if not _is_failure(detail):
                continue
            status = detail.get("status", "")
            if "NOT_FOUND" in status or "MISMATCH" in status or "SKIPPED" in status:
                fail_reason = _status_to_reason(status, mm)

                all_failed.append({
                    "string_id": detail.get("string_id", ""),
                    "str_origin": detail.get("old", ""),  # FULL StrOrigin
                    "str": detail.get("new", ""),  # Corrected text (translation)
                    "fail_reason": fail_reason,
                    "source_file": source_file,
                    "language": language,
                    "raw_attribs": detail.get("raw_attribs", {}),  # EXACT original attributes
                })

    return all_failed


def extract_mismatch_target_entries(results: Dict) -> List[Dict]:
    """
    Extract raw target LocStr entries for STRORIGIN_MISMATCH failures.

    When a TRANSFER fails because the StrOrigin changed in the target,
    this extracts the TARGET's current LocStr (with all its attributes)
    so the user gets a ready-made XML of "new strings that need review."

    Args:
        results: Results dict from transfer_folder_to_folder

    Returns:
        List of entry dicts with 'raw_attribs' from the TARGET XML,
        grouped-ready for generate_failed_merge_xml_per_language.
    """
    entries = []

    file_results = results.get("file_results", {})
    for _source_file, fresult in file_results.items():
        target_file = fresult.get("target", "")
        language = _extract_language_from_filename(target_file) if target_file else "UNK"

        for detail in fresult.get("details", []):
            if detail.get("status") not in ("STRORIGIN_MISMATCH", "DESCORIGIN_MISMATCH"):
                continue

            target_attribs = detail.get("target_raw_attribs", {})
            if not target_attribs:
                continue

            entries.append({
                "string_id": detail.get("string_id", ""),
                "str_origin": _get_strorigin_from_attribs(target_attribs),
                "str": target_attribs.get("Str", target_attribs.get("str", "")),
                "language": language,
                "raw_attribs": target_attribs,  # FULL target LocStr as-is
            })

    return entries


def _status_to_reason(status: str, match_mode: str = "") -> str:
    """Convert a status code to a human-readable failure reason."""
    status_upper = status.upper()
    is_strorigin = match_mode.startswith("strorigin_only")

    # Check MISMATCH first (before NOT_FOUND since it's more specific)
    if "DESCORIGIN_MISMATCH" in status_upper:
        return "DescOrigin mismatch (StrOrigin matches but DescOrigin differs)"
    if "STRORIGIN_MISMATCH" in status_upper or "MISMATCH" in status_upper:
        return "StrOrigin mismatch (StringID exists but source text differs)"

    if "NOT_FOUND" in status_upper:
        if match_mode.startswith("strorigin_descorigin"):
            return "StrOrigin + DescOrigin combo not found in target"
        if is_strorigin:
            return "StrOrigin text not found in target"
        if "L1" in status_upper:
            return "StringID not found in target (L1 exact match failed)"
        elif "L2A" in status_upper:
            return "StringID not found in target (L2A file match failed)"
        elif "L2B" in status_upper:
            return "StringID not found in target (L2B StrOrigin match failed)"
        elif "L3" in status_upper:
            return "StringID not found in target (L3 StringID-only failed)"
        else:
            return "StringID not found in target"

    elif "SKIPPED_EMPTY_STRORIGIN" in status_upper:
        return "Skipped: StringID exists but StrOrigin empty in target"

    elif "SKIPPED_NON_SCRIPT" in status_upper:
        return "Skipped: non-SCRIPT category (only Dialog/Sequencer allowed)"

    elif "SKIPPED_SCRIPT" in status_upper:
        return "Skipped: SCRIPT category (Dialog/Sequencer) — use StringID-Only mode"

    elif "SKIPPED_EXCLUDED" in status_upper:
        return "Skipped: excluded subfolder"

    elif "SKIPPED_TRANSLATED" in status_upper:
        return "Skipped: already translated (not Korean)"

    elif "SKIPPED" in status_upper:
        return "Skipped: unknown reason"

    else:
        return f"Failed: {status}"


def _extract_language_from_filename(filename: str) -> str:
    """Extract language code from filename like 'languagedata_fre.xml' or 'languagedata_zho-cn.xml'."""
    name = Path(filename).stem.lower()

    # Pattern: languagedata_XXX or languagedata_XXX-YY (with hyphen for variants like zho-cn)
    if name.startswith("languagedata_"):
        lang = name[13:].upper()
        # Allow hyphenated codes like ZHO-CN, ZHO-TW
        if lang and (2 <= len(lang.replace("-", "")) <= 6):
            return lang
    elif "_" in name:
        # Try last part after underscore
        parts = name.split("_")
        last = parts[-1]
        # Allow 2-6 chars base length, plus optional hyphen+variant
        base_len = len(last.replace("-", ""))
        if 2 <= base_len <= 6:
            return last.upper()

    return "UNK"


def format_failure_summary(failed_entries: List[Dict]) -> str:
    """
    Format a text summary of failures for logging.

    Args:
        failed_entries: List of failed entry dicts

    Returns:
        Multi-line summary string
    """
    if not failed_entries:
        return "No failures to report."

    lines = []
    lines.append(f"FAILURE SUMMARY: {len(failed_entries)} entries failed to merge")
    lines.append("-" * 60)

    # Group by source file
    by_source = defaultdict(list)
    for entry in failed_entries:
        source_file = entry.get("source_file", "unknown.xml")
        by_source[source_file].append(entry)

    for source_file, entries in sorted(by_source.items()):
        language = entries[0].get("language", "UNK") if entries else "UNK"
        lines.append(f"  {source_file} ({language}): {len(entries)} failures")

        # Group by failure reason
        by_reason = defaultdict(int)
        for entry in entries:
            reason = entry.get("fail_reason", "Unknown")
            by_reason[reason] += 1

        for reason, count in sorted(by_reason.items(), key=lambda x: -x[1]):
            lines.append(f"    - {reason}: {count}")

    lines.append("-" * 60)
    return "\n".join(lines)


# =============================================================================
# Excel Report Generator (using xlsxwriter)
# =============================================================================

def aggregate_transfer_results(results: Dict, mode: str = "folder") -> Dict:
    """
    Aggregate transfer results into structures suitable for Excel report.

    Args:
        results: Results from transfer_folder_to_folder or transfer_file_to_file
        mode: "folder" or "file"

    Returns:
        Dict with aggregated data for each sheet
    """
    mm = results.get("match_mode", "")
    aggregated = {
        "match_mode": mm,
        "summary": {},
        "by_reason": defaultdict(lambda: {"count": 0, "examples": []}),
        "by_file": [],
        "detailed_failures": [],
    }

    if mode == "folder":
        # Folder mode - multiple files
        total_corrections = results.get("total_corrections", 0)
        total_matched = results.get("total_matched", 0)
        total_updated = results.get("total_updated", 0)
        total_not_found = results.get("total_not_found", 0)
        total_strorigin_mismatch = results.get("total_strorigin_mismatch", 0)
        total_skipped = results.get("total_skipped", 0)
        total_skipped_translated = results.get("total_skipped_translated", 0)
        total_skipped_excluded = results.get("total_skipped_excluded", 0)
        files_processed = results.get("files_processed", 0)

        total_unchanged = max(0, total_matched - total_updated - total_skipped_translated)
        total_success = total_updated
        # SKIPPED_TRANSLATED is by design (untranslated-only scope), not a failure
        total_failures = (total_not_found + total_strorigin_mismatch + total_skipped +
                         total_skipped_excluded)

        # Count Korean words from StrOrigin in details (success vs failure)
        kr_words_success = 0
        kr_words_failed = 0
        kr_words_total = 0

        for _sname, file_result in results.get("file_results", {}).items():
            for detail in file_result.get("details", []):
                str_origin = detail.get("old", "") or ""
                word_count = len(str_origin.split()) if str_origin.strip() else 0
                kr_words_total += word_count
                if _is_failure(detail):
                    kr_words_failed += word_count
                else:
                    kr_words_success += word_count

        aggregated["summary"] = {
            "files_processed": files_processed,
            "total_corrections": total_corrections,
            "total_success": total_success,
            "total_failures": total_failures,
            "unchanged": total_unchanged,
            "success_rate": (total_success / total_corrections * 100) if total_corrections > 0 else 0,
            "failure_rate": (total_failures / total_corrections * 100) if total_corrections > 0 else 0,
            "matched": total_matched,
            "updated": total_updated,
            "not_found": total_not_found,
            "strorigin_mismatch": total_strorigin_mismatch,
            "skipped_non_script": total_skipped,
            "skipped_translated": total_skipped_translated,
            "skipped_excluded": total_skipped_excluded,
            "errors": results.get("errors", []),
            "kr_words_total": kr_words_total,
            "kr_words_success": kr_words_success,
            "kr_words_failed": kr_words_failed,
        }

        # Process per-file results
        for source_name, file_result in results.get("file_results", {}).items():
            target_name = file_result.get("target", "")
            corrections = file_result.get("corrections", 0)
            matched = file_result.get("matched", 0)
            updated = file_result.get("updated", 0)
            not_found = file_result.get("not_found", 0)

            # Count failures for this file
            failed = corrections - matched
            success_rate = (updated / corrections * 100) if corrections > 0 else 0

            # Extract language from filename
            lang = ""
            if "_" in source_name:
                # Try languagedata_XXX.xml pattern
                parts = source_name.replace(".xml", "").replace(".xlsx", "").split("_")
                if len(parts) >= 2:
                    lang = parts[-1].upper()

            aggregated["by_file"].append({
                "source_file": source_name,
                "language": lang,
                "target_file": target_name,
                "attempted": corrections,
                "failed": failed,
                "success_rate": success_rate,
            })

            # Process details for failure reasons and detailed list
            for detail in file_result.get("details", []):
                if _is_failure(detail):
                    reason = _classify_failure_reason(detail)
                    aggregated["by_reason"][reason]["count"] += 1

                    # Store example (first few per reason)
                    if len(aggregated["by_reason"][reason]["examples"]) < 3:
                        aggregated["by_reason"][reason]["examples"].append({
                            "string_id": detail.get("string_id", ""),
                            "source_file": source_name,
                        })

                    # Add to detailed failures
                    lang = _extract_language_from_filename(target_name)
                    # Defensive: extract target_strorigin from raw attribs if missing
                    _tso = detail.get("target_strorigin", "")
                    if not _tso:
                        _raw = detail.get("target_raw_attribs", {})
                        _tso = (
                            _raw.get("StrOrigin") or _raw.get("Strorigin") or
                            _raw.get("strorigin") or _raw.get("STRORIGIN") or ""
                        )
                    aggregated["detailed_failures"].append({
                        "source_file": source_name,
                        "string_id": detail.get("string_id", ""),
                        "str_origin": detail.get("old", ""),
                        "correction": detail.get("new", ""),
                        "reason": _get_failure_reason(reason, mm),
                        "target_file": target_name,
                        "target_strorigin": _tso,
                        "target_raw_attribs": detail.get("target_raw_attribs", {}),
                        "language": lang,
                    })

    else:
        # File mode - single file
        corrections_count = results.get("corrections_count", 0)
        matched = results.get("matched", 0)
        updated = results.get("updated", 0)
        not_found = results.get("not_found", 0)
        strorigin_mismatch = results.get("strorigin_mismatch", 0)
        skipped_non_script = results.get("skipped_non_script", 0)
        skipped_script = results.get("skipped_script", 0)
        skipped_translated = results.get("skipped_translated", 0)
        skipped_excluded = results.get("skipped_excluded", 0)

        unchanged = max(0, matched - updated - skipped_translated)
        total_success = updated
        # SKIPPED_TRANSLATED is by design (untranslated-only scope), not a failure
        total_failures = (not_found + strorigin_mismatch + skipped_non_script +
                        skipped_script + skipped_excluded)

        # Count Korean words from StrOrigin in details
        kr_words_success = 0
        kr_words_failed = 0
        kr_words_total = 0
        for detail in results.get("details", []):
            str_origin = detail.get("old", "") or ""
            word_count = len(str_origin.split()) if str_origin.strip() else 0
            kr_words_total += word_count
            if _is_failure(detail):
                kr_words_failed += word_count
            else:
                kr_words_success += word_count

        aggregated["summary"] = {
            "files_processed": 1,
            "total_corrections": corrections_count,
            "total_success": total_success,
            "total_failures": total_failures,
            "unchanged": unchanged,
            "success_rate": (total_success / corrections_count * 100) if corrections_count > 0 else 0,
            "failure_rate": (total_failures / corrections_count * 100) if corrections_count > 0 else 0,
            "matched": matched,
            "updated": updated,
            "not_found": not_found,
            "strorigin_mismatch": strorigin_mismatch,
            "skipped_non_script": skipped_non_script,
            "skipped_script": skipped_script,
            "skipped_translated": skipped_translated,
            "skipped_excluded": skipped_excluded,
            "errors": results.get("errors", []),
            "kr_words_total": kr_words_total,
            "kr_words_success": kr_words_success,
            "kr_words_failed": kr_words_failed,
        }

        # Single file entry
        aggregated["by_file"].append({
            "source_file": "Source file",
            "language": "",
            "target_file": "Target file",
            "attempted": corrections_count,
            "failed": total_failures,
            "success_rate": aggregated["summary"]["success_rate"],
        })

        # Process details
        for detail in results.get("details", []):
            if _is_failure(detail):
                reason = _classify_failure_reason(detail)
                aggregated["by_reason"][reason]["count"] += 1

                if len(aggregated["by_reason"][reason]["examples"]) < 3:
                    aggregated["by_reason"][reason]["examples"].append({
                        "string_id": detail.get("string_id", ""),
                        "source_file": "Source file",
                    })

                # Defensive: extract target_strorigin from raw attribs if missing
                _tso = detail.get("target_strorigin", "")
                if not _tso:
                    _raw = detail.get("target_raw_attribs", {})
                    _tso = (
                        _raw.get("StrOrigin") or _raw.get("Strorigin") or
                        _raw.get("strorigin") or _raw.get("STRORIGIN") or ""
                    )
                aggregated["detailed_failures"].append({
                    "source_file": "Source file",
                    "string_id": detail.get("string_id", ""),
                    "str_origin": detail.get("old", ""),
                    "correction": detail.get("new", ""),
                    "reason": _get_failure_reason(reason, mm),
                    "target_file": "Target file",
                    "target_strorigin": _tso,
                    "target_raw_attribs": detail.get("target_raw_attribs", {}),
                    "language": "ALL",
                })

    return aggregated


def _create_excel_formats(workbook) -> Dict:
    """Create reusable cell formats for the Excel workbook."""
    formats = {}

    # Title format (large, bold, centered)
    formats["title"] = workbook.add_format({
        "bold": True,
        "font_size": 16,
        "font_color": "#2E4057",
        "align": "center",
        "valign": "vcenter",
        "bottom": 2,
        "bottom_color": "#2E4057",
    })

    # Subtitle format
    formats["subtitle"] = workbook.add_format({
        "bold": True,
        "font_size": 11,
        "font_color": "#666666",
        "align": "left",
        "valign": "vcenter",
    })

    # Header format (bold, dark background)
    formats["header"] = workbook.add_format({
        "bold": True,
        "font_size": 11,
        "font_color": "#FFFFFF",
        "bg_color": "#2E4057",
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#1A2634",
        "text_wrap": True,
    })

    # Section header (bold, light background)
    formats["section_header"] = workbook.add_format({
        "bold": True,
        "font_size": 12,
        "font_color": "#2E4057",
        "bg_color": "#E8EEF4",
        "align": "left",
        "valign": "vcenter",
        "top": 2,
        "top_color": "#2E4057",
        "bottom": 1,
        "bottom_color": "#CCCCCC",
    })

    # Normal cell (even row)
    formats["cell_even"] = workbook.add_format({
        "font_size": 10,
        "align": "left",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#DDDDDD",
        "bg_color": "#FFFFFF",
        "text_wrap": True,
    })

    # Normal cell (odd row)
    formats["cell_odd"] = workbook.add_format({
        "font_size": 10,
        "align": "left",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#DDDDDD",
        "bg_color": "#F8F9FA",
        "text_wrap": True,
    })

    # Text cell (even row) - forces TEXT format for StringID columns
    formats["text_even"] = workbook.add_format({
        "font_size": 10,
        "align": "left",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#DDDDDD",
        "bg_color": "#FFFFFF",
        "num_format": "@",  # TEXT format
    })

    # Text cell (odd row) - forces TEXT format for StringID columns
    formats["text_odd"] = workbook.add_format({
        "font_size": 10,
        "align": "left",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#DDDDDD",
        "bg_color": "#F8F9FA",
        "num_format": "@",  # TEXT format
    })

    # Number cell (even row)
    formats["number_even"] = workbook.add_format({
        "font_size": 10,
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#DDDDDD",
        "bg_color": "#FFFFFF",
        "num_format": "#,##0",
    })

    # Number cell (odd row)
    formats["number_odd"] = workbook.add_format({
        "font_size": 10,
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#DDDDDD",
        "bg_color": "#F8F9FA",
        "num_format": "#,##0",
    })

    # Percentage cell (even row)
    formats["percent_even"] = workbook.add_format({
        "font_size": 10,
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#DDDDDD",
        "bg_color": "#FFFFFF",
        "num_format": "0.0%",
    })

    # Percentage cell (odd row)
    formats["percent_odd"] = workbook.add_format({
        "font_size": 10,
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#DDDDDD",
        "bg_color": "#F8F9FA",
        "num_format": "0.0%",
    })

    # Success formats (green)
    formats["success_number"] = workbook.add_format({
        "font_size": 11,
        "font_color": "#155724",
        "bold": True,
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#C3E6CB",
        "bg_color": "#D4EDDA",
        "num_format": "#,##0",
    })

    formats["success_percent"] = workbook.add_format({
        "font_size": 11,
        "font_color": "#155724",
        "bold": True,
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#C3E6CB",
        "bg_color": "#D4EDDA",
        "num_format": "0.0%",
    })

    # Failure formats (red)
    formats["failure_number"] = workbook.add_format({
        "font_size": 11,
        "font_color": "#721C24",
        "bold": True,
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#F5C6CB",
        "bg_color": "#F8D7DA",
        "num_format": "#,##0",
    })

    formats["failure_percent"] = workbook.add_format({
        "font_size": 11,
        "font_color": "#721C24",
        "bold": True,
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#F5C6CB",
        "bg_color": "#F8D7DA",
        "num_format": "0.0%",
    })

    # Warning formats (yellow/orange)
    formats["warning_number"] = workbook.add_format({
        "font_size": 10,
        "font_color": "#856404",
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#FFEEBA",
        "bg_color": "#FFF3CD",
        "num_format": "#,##0",
    })

    # Label format (bold, left aligned)
    formats["label"] = workbook.add_format({
        "bold": True,
        "font_size": 10,
        "align": "left",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#DDDDDD",
        "bg_color": "#F0F0F0",
    })

    # Value format
    formats["value"] = workbook.add_format({
        "font_size": 10,
        "align": "left",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#DDDDDD",
        "bg_color": "#FFFFFF",
    })

    # Timestamp format
    formats["timestamp"] = workbook.add_format({
        "font_size": 9,
        "font_color": "#888888",
        "italic": True,
        "align": "left",
    })

    # Indented label (sub-item in hierarchy)
    formats["indent_label"] = workbook.add_format({
        "font_size": 10,
        "align": "left",
        "valign": "vcenter",
        "indent": 2,
        "border": 1,
        "border_color": "#DDDDDD",
        "bg_color": "#F5F5F5",
    })

    # Bold total row
    formats["total_label"] = workbook.add_format({
        "bold": True,
        "font_size": 11,
        "align": "left",
        "valign": "vcenter",
        "border": 2,
        "border_color": "#2E4057",
        "bg_color": "#E8EEF4",
    })

    formats["total_number"] = workbook.add_format({
        "bold": True,
        "font_size": 11,
        "align": "center",
        "valign": "vcenter",
        "border": 2,
        "border_color": "#2E4057",
        "bg_color": "#E8EEF4",
        "num_format": "#,##0",
    })

    formats["total_percent"] = workbook.add_format({
        "bold": True,
        "font_size": 11,
        "align": "center",
        "valign": "vcenter",
        "border": 2,
        "border_color": "#2E4057",
        "bg_color": "#E8EEF4",
        "num_format": "0.0%",
    })

    return formats


def _write_summary_sheet(
    workbook,
    data: Dict,
    formats: Dict,
    source_name: str,
    target_name: str
):
    """Write the Summary sheet — ONE unified table with full hierarchy."""
    sheet = workbook.add_worksheet("Summary")
    summary = data["summary"]
    mm = data.get("match_mode", "")
    is_strorigin = mm.startswith("strorigin_only")
    is_strorigin_descorigin = mm.startswith("strorigin_descorigin")

    total = summary["total_corrections"] or 1  # avoid /0
    total_failures = summary["total_failures"] or 1

    # Set column widths
    sheet.set_column("A:A", 48)
    sheet.set_column("B:B", 20)
    sheet.set_column("C:C", 18)

    row = 0

    # Title
    sheet.merge_range(row, 0, row, 2, "TRANSFER REPORT", formats["title"])
    row += 1

    # Timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.write(row, 0, f"Generated: {timestamp}", formats["timestamp"])
    row += 1
    if source_name:
        sheet.write(row, 0, f"Source: {source_name}    Target: {target_name or 'LOC'}", formats["timestamp"])
        row += 1
    sheet.write(row, 0, f"Source Files Processed: {summary['files_processed']}", formats["timestamp"])
    row += 2

    # ===================================================================
    # TABLE 1: LOCSTR STRING BREAKDOWN (one unified table)
    # ===================================================================
    sheet.merge_range(row, 0, row, 2, "LOCSTR STRING BREAKDOWN", formats["section_header"])
    row += 1

    # Table headers
    sheet.write(row, 0, "", formats["header"])
    sheet.write(row, 1, "LocStr Strings", formats["header"])
    sheet.write(row, 2, "% of Total", formats["header"])
    row += 1

    # TOTAL row (bold, top of table)
    sheet.write(row, 0, "TOTAL LOCSTR STRINGS IN SOURCE", formats["total_label"])
    sheet.write(row, 1, summary["total_corrections"], formats["total_number"])
    sheet.write(row, 2, 1.0, formats["total_percent"])
    row += 1

    # Success
    sheet.write(row, 0, "Strings Updated Successfully", formats["indent_label"])
    sheet.write(row, 1, summary["total_success"], formats["success_number"])
    sheet.write(row, 2, summary["success_rate"] / 100, formats["success_percent"])
    row += 1

    # Unchanged
    unchanged = summary.get("unchanged", 0)
    if unchanged > 0:
        unchanged_rate = unchanged / summary["total_corrections"] if summary["total_corrections"] > 0 else 0
        sheet.write(row, 0, "Strings Unchanged (already correct)", formats["indent_label"])
        sheet.write(row, 1, unchanged, formats["number_even"])
        sheet.write(row, 2, unchanged_rate, formats["percent_even"])
        row += 1

    # Failed (subtotal)
    sheet.write(row, 0, "Strings Failed (total)", formats["indent_label"])
    sheet.write(row, 1, summary["total_failures"], formats["failure_number"])
    sheet.write(row, 2, summary["failure_rate"] / 100, formats["failure_percent"])
    row += 1

    # Failed breakdown — each reason indented further, showing % of total AND % of failed
    if is_strorigin_descorigin:
        not_found_label = "StrOrigin + DescOrigin Combo Not Found"
    elif is_strorigin:
        not_found_label = "StrOrigin Not Found in Target"
    else:
        not_found_label = "StringID Not Found in Target"

    mismatch_label = (
        "DescOrigin Mismatch (StrOrigin matches, DescOrigin differs)"
        if is_strorigin_descorigin
        else "StrOrigin Mismatch (ID exists, text differs)"
    )

    breakdown_items = [
        (not_found_label, summary.get("not_found", 0)),
        (mismatch_label, summary.get("strorigin_mismatch", 0)),
        ("Skipped: Not a SCRIPT category", summary.get("skipped_non_script", 0)),
        ("Skipped: SCRIPT category (use StringID-Only)", summary.get("skipped_script", 0)),
        ("Skipped: Already Translated (non-Korean)", summary.get("skipped_translated", 0)),
        ("Skipped: Excluded Subfolder", summary.get("skipped_excluded", 0)),
    ]

    for i, (label, count) in enumerate(breakdown_items):
        if count > 0:
            fmt_cell = formats["cell_even"] if i % 2 == 0 else formats["cell_odd"]
            fmt_num = formats["number_even"] if i % 2 == 0 else formats["number_odd"]
            fmt_pct = formats["percent_even"] if i % 2 == 0 else formats["percent_odd"]

            sheet.write(row, 0, f"      {label}", fmt_cell)
            sheet.write(row, 1, count, fmt_num)
            sheet.write(row, 2, count / total, fmt_pct)
            row += 1

    row += 2

    # ===================================================================
    # TABLE 2: KOREAN WORD COUNT BREAKDOWN (same unified style)
    # ===================================================================
    kr_words_total = summary.get("kr_words_total", 0)
    if kr_words_total > 0:
        kr_words_success = summary.get("kr_words_success", 0)
        kr_words_failed = summary.get("kr_words_failed", 0)

        sheet.merge_range(row, 0, row, 2, "KOREAN WORD COUNT (from StrOrigin)", formats["section_header"])
        row += 1

        sheet.write(row, 0, "", formats["header"])
        sheet.write(row, 1, "Korean Words", formats["header"])
        sheet.write(row, 2, "% of Total", formats["header"])
        row += 1

        # Total words row
        sheet.write(row, 0, "TOTAL KOREAN WORDS", formats["total_label"])
        sheet.write(row, 1, kr_words_total, formats["total_number"])
        sheet.write(row, 2, 1.0, formats["total_percent"])
        row += 1

        sheet.write(row, 0, "Words in Succeeded Strings", formats["indent_label"])
        sheet.write(row, 1, kr_words_success, formats["success_number"])
        sheet.write(row, 2, kr_words_success / kr_words_total, formats["success_percent"])
        row += 1

        sheet.write(row, 0, "Words in Failed Strings", formats["indent_label"])
        sheet.write(row, 1, kr_words_failed, formats["failure_number"])
        sheet.write(row, 2, kr_words_failed / kr_words_total, formats["failure_percent"])
        row += 2

    # ===================================================================
    # ERRORS (if any)
    # ===================================================================
    errors = summary.get("errors", [])
    if errors:
        sheet.merge_range(row, 0, row, 2, "ERRORS", formats["section_header"])
        row += 1

        for i, error in enumerate(errors[:10]):
            fmt = formats["cell_even"] if i % 2 == 0 else formats["cell_odd"]
            sheet.merge_range(row, 0, row, 2, error, fmt)
            row += 1

        if len(errors) > 10:
            sheet.write(row, 0, f"... and {len(errors) - 10} more errors", formats["timestamp"])


def _write_reason_sheet(workbook, data: Dict, formats: Dict):
    """Write the Failure by Reason sheet — full context table."""
    sheet = workbook.add_worksheet("Failure by Reason")

    summary = data["summary"]
    total_strings = summary.get("total_corrections", 0) or 1
    total_failed = sum(v["count"] for v in data["by_reason"].values()) or 1
    total_success = summary.get("total_success", 0)

    # Set column widths
    sheet.set_column("A:A", 48)
    sheet.set_column("B:B", 20)
    sheet.set_column("C:C", 18)
    sheet.set_column("D:D", 18)

    row = 0

    # Title
    sheet.merge_range(row, 0, row, 3, "LOCSTR STRINGS BY REASON", formats["title"])
    row += 2

    # Headers
    sheet.write(row, 0, "", formats["header"])
    sheet.write(row, 1, "LocStr Strings", formats["header"])
    sheet.write(row, 2, "% of Total", formats["header"])
    sheet.write(row, 3, "% of Failed", formats["header"])
    row += 1

    # TOTAL row
    sheet.write(row, 0, "TOTAL LOCSTR STRINGS", formats["total_label"])
    sheet.write(row, 1, total_strings, formats["total_number"])
    sheet.write(row, 2, 1.0, formats["total_percent"])
    sheet.write(row, 3, "", formats["total_label"])
    row += 1

    # Success row
    sheet.write(row, 0, "Strings Succeeded", formats["indent_label"])
    sheet.write(row, 1, total_success, formats["success_number"])
    sheet.write(row, 2, total_success / total_strings, formats["success_percent"])
    sheet.write(row, 3, "", formats["cell_even"])
    row += 1

    # Failed subtotal
    sheet.write(row, 0, "Strings Failed (breakdown below)", formats["indent_label"])
    sheet.write(row, 1, total_failed, formats["failure_number"])
    sheet.write(row, 2, total_failed / total_strings, formats["failure_percent"])
    sheet.write(row, 3, 1.0, formats["failure_percent"])
    row += 1

    # Sort by count (descending)
    sorted_reasons = sorted(
        data["by_reason"].items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )

    for i, (reason_key, reason_data) in enumerate(sorted_reasons):
        count = reason_data["count"]
        if count == 0:
            continue

        reason_label = _get_failure_reason(reason_key, data.get("match_mode", ""))

        fmt_cell = formats["cell_even"] if i % 2 == 0 else formats["cell_odd"]
        fmt_num = formats["number_even"] if i % 2 == 0 else formats["number_odd"]
        fmt_pct = formats["percent_even"] if i % 2 == 0 else formats["percent_odd"]

        sheet.write(row, 0, f"      {reason_label}", fmt_cell)
        sheet.write(row, 1, count, fmt_num)
        sheet.write(row, 2, count / total_strings, fmt_pct)
        sheet.write(row, 3, count / total_failed, fmt_pct)
        row += 1


def _write_file_sheet(workbook, data: Dict, formats: Dict):
    """Write the Failure by File sheet."""
    sheet = workbook.add_worksheet("Results by File")

    # Set column widths
    sheet.set_column("A:A", 30)  # Source File
    sheet.set_column("B:B", 12)  # Language
    sheet.set_column("C:C", 30)  # Target
    sheet.set_column("D:D", 22)  # Total LocStr Strings
    sheet.set_column("E:E", 22)  # Strings Succeeded
    sheet.set_column("F:F", 22)  # Strings Failed
    sheet.set_column("G:G", 15)  # Success Rate

    row = 0

    # Title
    sheet.merge_range(row, 0, row, 6, "RESULTS BY SOURCE FILE", formats["title"])
    row += 2

    # Headers
    headers = [
        "Source File", "Language", "Target File",
        "Total LocStr Strings", "Strings Succeeded", "Strings Failed", "Success Rate"
    ]
    for col, header in enumerate(headers):
        sheet.write(row, col, header, formats["header"])
    row += 1
    header_row = row - 1

    # Data rows
    for i, file_data in enumerate(data["by_file"]):
        # Alternate row colors
        fmt_cell = formats["cell_even"] if i % 2 == 0 else formats["cell_odd"]
        fmt_num = formats["number_even"] if i % 2 == 0 else formats["number_odd"]

        attempted = file_data["attempted"]
        failed = file_data["failed"]
        succeeded = max(0, attempted - failed)

        sheet.write(row, 0, file_data["source_file"], fmt_cell)
        sheet.write(row, 1, file_data["language"], fmt_cell)
        sheet.write(row, 2, file_data["target_file"], fmt_cell)
        sheet.write(row, 3, attempted, fmt_num)
        sheet.write(row, 4, succeeded, formats["success_number"] if succeeded > 0 else fmt_num)
        sheet.write(row, 5, failed, formats["failure_number"] if failed > 0 else fmt_num)

        # Color-code success rate
        success_rate = file_data["success_rate"]
        if success_rate >= 95:
            sheet.write(row, 6, success_rate / 100, formats["success_percent"])
        elif success_rate >= 80:
            sheet.write(row, 6, success_rate / 100, formats["percent_even"] if i % 2 == 0 else formats["percent_odd"])
        else:
            sheet.write(row, 6, success_rate / 100, formats["failure_percent"])

        row += 1

    # Add autofilter
    if data["by_file"]:
        sheet.autofilter(header_row, 0, row - 1, 6)


def _write_detailed_sheet(workbook, data: Dict, formats: Dict):
    """Write per-language Detailed Failures sheets (Details_FRE, Details_ENG, etc.)."""
    all_failures = data["detailed_failures"]
    if not all_failures:
        return

    # Group failures by language
    by_language = defaultdict(list)
    for failure in all_failures:
        lang = failure.get("language", "ALL")
        by_language[lang].append(failure)

    # Create one sheet per language, sorted alphabetically
    for lang in sorted(by_language.keys()):
        failures = by_language[lang]

        # Sheet name: "Details_FRE", "Details_ENG", etc. (max 31 chars for Excel)
        sheet_name = f"Details_{lang}"[:31]
        sheet = workbook.add_worksheet(sheet_name)

        # Set column widths
        sheet.set_column("A:A", 25)  # StringID
        sheet.set_column("B:B", 40)  # StrOrigin
        sheet.set_column("C:C", 40)  # Correction
        sheet.set_column("D:D", 30)  # Reason
        sheet.set_column("E:E", 40)  # New StrOrigin
        sheet.set_column("F:F", 45)  # StrOrigin Diff

        row = 0

        # Title
        sheet.merge_range(row, 0, row, 5, f"DETAILED FAILURES — {lang}", formats["title"])
        row += 1

        # Count info
        sheet.write(row, 0, f"Failures: {len(failures)}", formats["timestamp"])
        row += 2

        # Headers (no Source File / Target — redundant per-language)
        headers = ["StringID", "StrOrigin", "Correction", "Reason",
                   "New StrOrigin", "StrOrigin Diff"]
        for col, header in enumerate(headers):
            sheet.write(row, col, header, formats["header"])
        row += 1
        header_row = row - 1

        for i, failure in enumerate(failures):
            fmt_cell = formats["cell_even"] if i % 2 == 0 else formats["cell_odd"]
            fmt_text = formats["text_even"] if i % 2 == 0 else formats["text_odd"]

            sheet.write_string(row, 0, str(failure.get("string_id", "")), fmt_text)
            sheet.write(row, 1, failure.get("str_origin", ""), fmt_cell)
            sheet.write(row, 2, failure.get("correction", ""), fmt_cell)
            sheet.write(row, 3, failure.get("reason", ""), fmt_cell)

            target_strorigin = failure.get("target_strorigin", "")
            # Defensive fallback: extract from raw attribs if target_strorigin is empty
            if not target_strorigin:
                raw = failure.get("target_raw_attribs", {})
                target_strorigin = (
                    raw.get("StrOrigin") or raw.get("Strorigin") or
                    raw.get("strorigin") or raw.get("STRORIGIN") or ""
                )
            sheet.write(row, 4, target_strorigin, fmt_cell)
            if target_strorigin:
                diff = extract_differences(failure.get("str_origin", ""), target_strorigin)
                sheet.write(row, 5, diff, fmt_cell)
            else:
                sheet.write(row, 5, "", fmt_cell)

            row += 1

        # Autofilter + freeze
        if failures:
            sheet.autofilter(header_row, 0, row - 1, 5)
        sheet.freeze_panes(header_row + 1, 0)


def generate_failure_report_excel(
    results: Dict,
    output_path: Path,
    mode: str = "folder",
    source_name: str = "",
    target_name: str = "",
) -> Tuple[bool, str]:
    """
    Generate a detailed Excel failure report for transfer operations.

    Creates a 4-sheet workbook with:
    - Summary: Overview, totals, success/failure rates
    - Failure by Reason: Breakdown by failure category
    - Failure by File: Per-file statistics
    - Detailed Failures: Individual failure entries

    Args:
        results: Results from transfer_folder_to_folder or transfer_file_to_file
        output_path: Path for output Excel file
        mode: "folder" or "file"
        source_name: Name of source file/folder (for report header)
        target_name: Name of target file/folder (for report header)

    Returns:
        Tuple of (success: bool, message: str)
    """
    if not XLSXWRITER_AVAILABLE:
        return False, "xlsxwriter not installed. Run: pip install xlsxwriter"

    try:
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Aggregate data
        data = aggregate_transfer_results(results, mode)

        # Create workbook
        workbook = xlsxwriter.Workbook(str(output_path))

        # Define formats
        formats = _create_excel_formats(workbook)

        # Write sheets
        _write_summary_sheet(workbook, data, formats, source_name, target_name)
        _write_reason_sheet(workbook, data, formats)
        _write_file_sheet(workbook, data, formats)
        _write_detailed_sheet(workbook, data, formats)

        workbook.close()

        logger.info(f"Excel failure report saved to: {output_path}")
        return True, f"Report saved: {output_path}"

    except Exception as e:
        logger.error(f"Failed to generate Excel failure report: {e}")
        return False, f"Failed to generate report: {e}"


def generate_failure_report_from_transfer(
    results: Dict,
    output_folder: Path,
    mode: str = "folder",
    source_name: str = "",
    target_name: str = "",
    filename_prefix: str = "FailureReport",
    format: str = "excel",
) -> Tuple[bool, str, Optional[Path]]:
    """
    Generate a failure report with automatic filename.

    Args:
        results: Results from transfer operation
        output_folder: Folder to save report in
        mode: "folder" or "file"
        source_name: Source name for header
        target_name: Target name for header
        filename_prefix: Prefix for filename
        format: "excel" or "xml"

    Returns:
        Tuple of (success, message, output_path or None)
    """
    # Generate timestamp-based filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "excel":
        filename = f"{filename_prefix}_{timestamp}.xlsx"
        output_path = Path(output_folder) / filename

        success, message = generate_failure_report_excel(
            results, output_path, mode, source_name, target_name
        )
    else:
        # XML format
        filename = f"{filename_prefix}_{timestamp}.xml"
        output_path = Path(output_folder) / filename

        # Extract failed entries for XML format
        if mode == "folder":
            failed_entries = extract_failed_from_folder_results(results)
        else:
            failed_entries = extract_failed_from_transfer_results(results, source_name)

        try:
            generate_failed_merge_xml(failed_entries, output_path)
            success, message = True, f"Report saved: {output_path}"
        except Exception as e:
            success, message = False, f"Failed to generate report: {e}"

    if success:
        return True, message, output_path
    else:
        return False, message, None


def _write_duplicate_sheet(
    workbook: "xlsxwriter.Workbook",
    sheet_name: str,
    entries: List[Dict],
) -> None:
    """Write a single sheet of duplicate StrOrigin entries."""
    ws = workbook.add_worksheet(sheet_name)
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
    ws.write(0, 0, "StrOrigin", header_fmt)
    ws.write(0, 1, "Correction", header_fmt)
    ws.write(0, 2, "StringID", header_fmt)

    for row_idx, entry in enumerate(entries, 1):
        ws.write(row_idx, 0, entry.get("old", ""))
        ws.write(row_idx, 1, entry.get("new", ""))
        ws.write_string(row_idx, 2, str(entry.get("string_id", "")))

    ws.set_column(0, 0, 60)   # StrOrigin
    ws.set_column(1, 1, 60)   # Correction
    ws.set_column(2, 2, 30)   # StringID
    ws.autofilter(0, 0, len(entries), 2)
    ws.freeze_panes(1, 0)


def generate_duplicate_strorigin_excel(
    duplicate_entries: List[Dict],
    output_folder: Path,
) -> List[Path]:
    """Generate per-language Excel files for skipped duplicate StrOrigin corrections.

    One file per language. Columns: StrOrigin / Correction / StringID.
    User deletes unwanted rows and re-submits via normal Excel transfer.

    Args:
        duplicate_entries: List of detail dicts with status SKIPPED_DUPLICATE_STRORIGIN
        output_folder: Directory to write the report into

    Returns:
        List of Paths to generated Excel files (empty list if nothing to write)
    """
    if not XLSXWRITER_AVAILABLE or not duplicate_entries:
        return []

    output_folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Group by language
    by_lang: Dict[str, List[Dict]] = {}
    for entry in duplicate_entries:
        lang = entry.get("language", "UNKNOWN")
        by_lang.setdefault(lang, []).append(entry)

    output_paths: List[Path] = []
    for lang, entries in sorted(by_lang.items()):
        # Sort by StrOrigin so duplicate groups are visually adjacent
        entries = sorted(entries, key=lambda e: e.get("old", ""))

        output_path = output_folder / f"KROnly_DuplicateStrings_{lang}_{timestamp}.xlsx"
        try:
            workbook = xlsxwriter.Workbook(str(output_path))
            _write_duplicate_sheet(workbook, "Duplicates", entries)
            workbook.close()
            logger.info(f"Duplicate StrOrigin report [{lang}]: {output_path.name} ({len(entries)} entries)")
            output_paths.append(output_path)
        except Exception as e:
            logger.error(f"Failed to generate duplicate StrOrigin report [{lang}]: {e}")

    return output_paths


# =============================================================================
# Fuzzy Match Report
# =============================================================================

# Score band definitions: (lower_bound, upper_bound, label, bg_color, font_color)
_FUZZY_BANDS = [
    (0.95, 1.01, "95-100%", "#1B5E20", "#FFFFFF"),
    (0.90, 0.95, "90-95%",  "#2E7D32", "#FFFFFF"),
    (0.85, 0.90, "85-90%",  "#4CAF50", "#FFFFFF"),
    (0.80, 0.85, "80-85%",  "#FFF176", "#5D4037"),
    (0.75, 0.80, "75-80%",  "#FFB74D", "#4E342E"),
    (0.70, 0.75, "70-75%",  "#EF5350", "#FFFFFF"),
]
_FUZZY_UNMATCHED_BG = "#BDBDBD"
_FUZZY_UNMATCHED_FG = "#424242"


def _get_band_index(score: float) -> int:
    """Return the index into _FUZZY_BANDS for a given score, or -1 if below all bands."""
    for i, (lo, hi, *_) in enumerate(_FUZZY_BANDS):
        if lo <= score < hi:
            return i
    return -1


def generate_fuzzy_report_excel(
    fuzzy_matched: List[Dict],
    fuzzy_unmatched: List[Dict],
    fuzzy_stats: Dict,
    output_path: Path,
) -> Path:
    """
    Generate a colorful Excel report showing fuzzy match quality distribution.

    Creates a 3-sheet workbook:
    - Summary: Score distribution by 5-point bands with visual bars
    - Matches: Every fuzzy match row, sorted by score desc, color-coded
    - Unmatched: Items below threshold with best available score

    Args:
        fuzzy_matched: List of matched correction dicts (with fuzzy_score, etc.)
        fuzzy_unmatched: List of unmatched correction dicts (with best_score, etc.)
        fuzzy_stats: Stats dict from find_matches_fuzzy
        output_path: Path for output Excel file

    Returns:
        Path to the generated report
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = xlsxwriter.Workbook(str(output_path))

    # --- Shared formats ---
    fmt_title = workbook.add_format({
        "bold": True, "font_size": 16, "font_color": "#2E4057",
        "align": "center", "valign": "vcenter", "bottom": 2, "bottom_color": "#2E4057",
    })
    fmt_header = workbook.add_format({
        "bold": True, "font_size": 11, "font_color": "#FFFFFF", "bg_color": "#2E4057",
        "align": "center", "valign": "vcenter", "border": 1, "text_wrap": True,
    })
    fmt_info_label = workbook.add_format({
        "bold": True, "font_size": 10, "align": "right", "valign": "vcenter",
    })
    fmt_info_value = workbook.add_format({
        "font_size": 10, "align": "left", "valign": "vcenter",
    })
    fmt_total_row = workbook.add_format({
        "bold": True, "font_size": 11, "border": 1, "bg_color": "#E8EEF4",
        "align": "center", "valign": "vcenter",
    })
    fmt_total_left = workbook.add_format({
        "bold": True, "font_size": 11, "border": 1, "bg_color": "#E8EEF4",
        "align": "left", "valign": "vcenter",
    })

    # Band formats (for Summary and Matches sheets)
    band_formats = []
    band_formats_score = []  # numeric score column (0.000 format)
    for _, _, _, bg, fg in _FUZZY_BANDS:
        band_formats.append(workbook.add_format({
            "font_size": 10, "font_color": fg, "bg_color": bg,
            "align": "center", "valign": "vcenter", "border": 1, "text_wrap": True,
        }))
        band_formats_score.append(workbook.add_format({
            "font_size": 10, "font_color": fg, "bg_color": bg,
            "align": "center", "valign": "vcenter", "border": 1,
            "num_format": "0.000",
        }))
    # Left-aligned variant for text columns
    band_formats_left = []
    for _, _, _, bg, fg in _FUZZY_BANDS:
        band_formats_left.append(workbook.add_format({
            "font_size": 10, "font_color": fg, "bg_color": bg,
            "align": "left", "valign": "vcenter", "border": 1, "text_wrap": True,
        }))

    fmt_unmatched = workbook.add_format({
        "font_size": 10, "font_color": _FUZZY_UNMATCHED_FG, "bg_color": _FUZZY_UNMATCHED_BG,
        "align": "center", "valign": "vcenter", "border": 1, "text_wrap": True,
    })
    fmt_unmatched_score = workbook.add_format({
        "font_size": 10, "font_color": _FUZZY_UNMATCHED_FG, "bg_color": _FUZZY_UNMATCHED_BG,
        "align": "center", "valign": "vcenter", "border": 1,
        "num_format": "0.000",
    })
    fmt_unmatched_left = workbook.add_format({
        "font_size": 10, "font_color": _FUZZY_UNMATCHED_FG, "bg_color": _FUZZY_UNMATCHED_BG,
        "align": "left", "valign": "vcenter", "border": 1, "text_wrap": True,
    })

    # --- Sheet 1: Summary ---
    ws_sum = workbook.add_worksheet("Summary")
    ws_sum.set_column("A:A", 22)
    ws_sum.set_column("B:B", 14)
    ws_sum.set_column("C:C", 12)
    ws_sum.set_column("D:D", 40)

    ws_sum.merge_range("A1:D1", "Fuzzy Match Report", fmt_title)
    row = 2

    stats = fuzzy_stats or {}

    # --- Transfer Overview (global context) ---
    fmt_section = workbook.add_format({
        "bold": True, "font_size": 12, "font_color": "#2E4057",
        "bg_color": "#E8EEF4", "bottom": 1, "bottom_color": "#CCCCCC",
    })
    fuzzy_recovered = stats.get("matched", len(fuzzy_matched))
    fuzzy_still_unmatched = stats.get("unmatched", len(fuzzy_unmatched))
    sent_to_fuzzy = fuzzy_recovered + fuzzy_still_unmatched

    # Transfer Overview — only when transfer context is available
    total_corrections = stats.get("transfer_total_corrections", 0)
    if total_corrections > 0 and "transfer_total_matched" in stats:
        total_transfer_matched = stats["transfer_total_matched"]
        total_transfer_updated = stats.get("transfer_total_updated", 0)
        exact_matched = max(0, total_transfer_matched - fuzzy_recovered)
        recovery_rate = (fuzzy_recovered / sent_to_fuzzy * 100) if sent_to_fuzzy > 0 else 0

        ws_sum.merge_range(row, 0, row, 3, "Transfer Overview", fmt_section)
        row += 1
        overview_items = [
            ("Total Corrections:", f"{total_corrections:,}"),
            ("Step 1 (Exact Match):", f"{exact_matched:,} matched"),
            ("Step 2 (Fuzzy):", f"{fuzzy_recovered:,} additional matches recovered"),
            ("Still Unmatched:", f"{fuzzy_still_unmatched:,}"),
            ("Fuzzy Recovery Rate:", f"{recovery_rate:.1f}% ({fuzzy_recovered} of {sent_to_fuzzy})"),
            ("Total Updated:", f"{total_transfer_updated:,} values written"),
        ]
        for label, value in overview_items:
            ws_sum.write(row, 0, label, fmt_info_label)
            ws_sum.write(row, 1, value, fmt_info_value)
            row += 1
        row += 1

    # --- Fuzzy Details ---
    ws_sum.merge_range(row, 0, row, 3, "Fuzzy Match Details", fmt_section)
    row += 1
    info_items = [
        ("Threshold:", f"{stats.get('threshold', 0):.0%}"),
        ("Fuzzy Matched:", f"{fuzzy_recovered:,}"),
        ("Fuzzy Unmatched:", f"{fuzzy_still_unmatched:,}"),
        ("Avg Score:", f"{stats.get('avg_score', 0):.3f}"),
        ("Min Score:", f"{stats.get('min_score', 0):.3f}"),
        ("Max Score:", f"{stats.get('max_score', 0):.3f}"),
        ("Fuzzy Elapsed:", f"{stats.get('elapsed_sec', 0):.1f}s"),
    ]
    for label, value in info_items:
        ws_sum.write(row, 0, label, fmt_info_label)
        ws_sum.write(row, 1, value, fmt_info_value)
        row += 1

    row += 1

    # Band distribution table
    ws_sum.write(row, 0, "Score Band", fmt_header)
    ws_sum.write(row, 1, "Count", fmt_header)
    ws_sum.write(row, 2, "% of Total", fmt_header)
    ws_sum.write(row, 3, "Visual Bar", fmt_header)
    row += 1

    # Count matches per band
    band_counts = [0] * len(_FUZZY_BANDS)
    for m in fuzzy_matched:
        score = m.get("fuzzy_score", 0)
        idx = _get_band_index(score)
        if idx >= 0:
            band_counts[idx] += 1

    total_matched = sum(band_counts)
    max_count = max(band_counts) if band_counts else 1

    for i, (lo, hi, label, bg, fg) in enumerate(_FUZZY_BANDS):
        count = band_counts[i]
        pct = (count / total_matched * 100) if total_matched > 0 else 0
        bar_len = int((count / max_count) * 30) if max_count > 0 else 0
        bar = "\u2588" * bar_len

        fmt_c = band_formats[i]
        fmt_l = band_formats_left[i]
        ws_sum.write(row, 0, label, fmt_c)
        ws_sum.write(row, 1, count, fmt_c)
        ws_sum.write(row, 2, f"{pct:.1f}%", fmt_c)
        ws_sum.write(row, 3, bar, fmt_l)
        row += 1

    # Total row
    ws_sum.write(row, 0, "Total", fmt_total_row)
    ws_sum.write(row, 1, total_matched, fmt_total_row)
    ws_sum.write(row, 2, "100%", fmt_total_row)
    ws_sum.write(row, 3, "", fmt_total_left)

    # --- Sheet 2: Matches ---
    ws_match = workbook.add_worksheet("Matches")
    match_cols = ["Score", "Source StringID", "Source StrOrigin", "Matched StrOrigin", "Correction", "Status", "Comment"]
    col_widths = [10, 25, 45, 45, 45, 12, 25]
    for ci, (col_name, width) in enumerate(zip(match_cols, col_widths)):
        ws_match.set_column(ci, ci, width)
        ws_match.write(0, ci, col_name, fmt_header)

    ws_match.freeze_panes(1, 0)
    ws_match.autofilter(0, 0, max(1, len(fuzzy_matched)), len(match_cols) - 1)

    # Sort by score descending
    sorted_matched = sorted(fuzzy_matched, key=lambda m: m.get("fuzzy_score", 0), reverse=True)

    for ri, m in enumerate(sorted_matched, start=1):
        score = m.get("fuzzy_score", 0)
        bi = _get_band_index(score)
        fmt_c = band_formats[bi] if bi >= 0 else fmt_unmatched
        fmt_s = band_formats_score[bi] if bi >= 0 else fmt_unmatched_score
        fmt_l = band_formats_left[bi] if bi >= 0 else fmt_unmatched_left

        ws_match.write_number(ri, 0, score, fmt_s)
        ws_match.write(ri, 1, m.get("string_id", ""), fmt_l)
        ws_match.write(ri, 2, m.get("str_origin", ""), fmt_l)
        ws_match.write(ri, 3, m.get("fuzzy_target_str_origin", ""), fmt_l)
        ws_match.write(ri, 4, m.get("corrected", ""), fmt_l)
        ws_match.write(ri, 5, "", fmt_c)  # Status — filled by user
        ws_match.write(ri, 6, "", fmt_l)  # Comment

    # Data validation for Status column
    if sorted_matched:
        ws_match.data_validation(1, 5, len(sorted_matched), 5, {
            "validate": "list",
            "source": ["ISSUE", "NO ISSUE", "FIXED"],
            "show_error": False,
        })

    # --- Sheet 3: Unmatched ---
    ws_unm = workbook.add_worksheet("Unmatched")
    unm_cols = ["Source StringID", "Source StrOrigin", "Best Score", "Best Match StrOrigin", "Correction"]
    unm_widths = [25, 45, 12, 45, 45]
    for ci, (col_name, width) in enumerate(zip(unm_cols, unm_widths)):
        ws_unm.set_column(ci, ci, width)
        ws_unm.write(0, ci, col_name, fmt_header)

    ws_unm.freeze_panes(1, 0)
    ws_unm.autofilter(0, 0, max(1, len(fuzzy_unmatched)), len(unm_cols) - 1)

    # Sort by best_score descending (closest to threshold first)
    sorted_unmatched = sorted(fuzzy_unmatched, key=lambda u: u.get("best_score", 0), reverse=True)

    for ri, u in enumerate(sorted_unmatched, start=1):
        best = u.get("best_score", 0)
        ws_unm.write(ri, 0, u.get("string_id", ""), fmt_unmatched_left)
        ws_unm.write(ri, 1, u.get("str_origin", ""), fmt_unmatched_left)
        if best > 0:
            ws_unm.write_number(ri, 2, best, fmt_unmatched_score)
        else:
            ws_unm.write(ri, 2, "", fmt_unmatched)
        ws_unm.write(ri, 3, u.get("best_match_str_origin", ""), fmt_unmatched_left)
        ws_unm.write(ri, 4, u.get("corrected", ""), fmt_unmatched_left)

    workbook.close()
    logger.info(f"Fuzzy report saved: {output_path} ({len(fuzzy_matched)} matched, {len(fuzzy_unmatched)} unmatched)")
    return output_path
