"""
Failure Report Generator - Generate failure reports in XML and Excel formats.

Creates structured reports of LocStr entries that failed to merge:
- XML format: FAILED_TO_MERGE.xml grouped by source file
- Excel format: Multi-sheet workbook with summary, breakdown by reason/file, details

Uses xlsxwriter for reliable Excel generation (NOT openpyxl).
"""

import logging
from datetime import datetime
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
# Failure Reason Categories (for Excel reports)
# =============================================================================

FAILURE_REASONS = {
    "NOT_FOUND": "StringID not found in target",
    "STRORIGIN_MISMATCH": "StrOrigin mismatch",
    "SKIPPED_TRANSLATED": "Already translated (skipped)",
    "SKIPPED_NON_SCRIPT": "Not a SCRIPT category (skipped)",
    "SKIPPED_EXCLUDED": "Excluded subfolder (skipped)",
    "PARSE_ERROR": "Failed to parse correction",
    "WRITE_ERROR": "Failed to write to target file",
    "OTHER": "Other/Unknown error",
}


def _classify_failure_reason(detail: Dict) -> str:
    """
    Classify a detail entry into a failure reason category.

    Args:
        detail: A detail dict from merge results with 'status' key

    Returns:
        Failure reason key from FAILURE_REASONS
    """
    status = detail.get("status", "").upper()

    if "NOT_FOUND" in status:
        return "NOT_FOUND"
    elif "MISMATCH" in status:
        return "STRORIGIN_MISMATCH"
    elif "SKIPPED_TRANSLATED" in status:
        return "SKIPPED_TRANSLATED"
    elif "SKIPPED_NON_SCRIPT" in status:
        return "SKIPPED_NON_SCRIPT"
    elif "SKIPPED_EXCLUDED" in status:
        return "SKIPPED_EXCLUDED"
    elif "ERROR" in status:
        return "PARSE_ERROR"
    else:
        return "OTHER"


def _is_failure(detail: Dict) -> bool:
    """Check if a detail entry represents a failure (not a success)."""
    status = detail.get("status", "").upper()
    # Success statuses
    if status in ("UPDATED", "UNCHANGED"):
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


def extract_failed_from_transfer_results(
    results: Dict,
    source_file_name: str = "unknown.xml",
    language: str = "UNK",
) -> List[Dict]:
    """
    Extract failed entries from transfer_file_to_file or merge results.

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

    details = results.get("details", [])
    for detail in details:
        status = detail.get("status", "")

        # Only include failed/not found entries
        if "NOT_FOUND" in status or "SKIPPED" in status:
            fail_reason = _status_to_reason(status)

            failed_entries.append({
                "string_id": detail.get("string_id", ""),
                "str_origin": "",  # Not always available in details
                "str": detail.get("new", ""),
                "fail_reason": fail_reason,
                "source_file": source_file_name,
                "language": language,
            })

    return failed_entries


def extract_failed_from_folder_results(
    results: Dict,
) -> List[Dict]:
    """
    Extract all failed entries from transfer_folder_to_folder results.

    Iterates through per-file results and aggregates all failures.

    Args:
        results: Results dict from transfer_folder_to_folder

    Returns:
        List of failed entry dicts ready for generate_failed_merge_xml
    """
    all_failed = []

    file_results = results.get("file_results", {})
    for source_file, fresult in file_results.items():
        # Try to extract language from filename
        language = _extract_language_from_filename(source_file)

        details = fresult.get("details", [])
        for detail in details:
            status = detail.get("status", "")

            if "NOT_FOUND" in status or "SKIPPED" in status:
                fail_reason = _status_to_reason(status)

                all_failed.append({
                    "string_id": detail.get("string_id", ""),
                    "str_origin": detail.get("old", ""),
                    "str": detail.get("new", ""),
                    "fail_reason": fail_reason,
                    "source_file": source_file,
                    "language": language,
                })

    return all_failed


def _status_to_reason(status: str) -> str:
    """Convert a status code to a human-readable failure reason."""
    status_upper = status.upper()

    if "NOT_FOUND" in status_upper:
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

    elif "SKIPPED_NON_SCRIPT" in status_upper:
        return "Skipped: non-SCRIPT category (only Dialog/Sequencer allowed)"

    elif "SKIPPED_EXCLUDED" in status_upper:
        return "Skipped: excluded subfolder"

    elif "SKIPPED_TRANSLATED" in status_upper:
        return "Skipped: already translated (not Korean)"

    elif "SKIPPED" in status_upper:
        return "Skipped: unknown reason"

    else:
        return f"Failed: {status}"


def _extract_language_from_filename(filename: str) -> str:
    """Extract language code from filename like 'languagedata_fre.xml'."""
    name = Path(filename).stem.lower()

    # Pattern: languagedata_XXX or XXX_languagedata
    if name.startswith("languagedata_"):
        return name[13:].upper()
    elif "_" in name:
        # Try last part after underscore
        parts = name.split("_")
        last = parts[-1]
        if 2 <= len(last) <= 6:
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
    aggregated = {
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
        total_skipped = results.get("total_skipped", 0)
        total_skipped_translated = results.get("total_skipped_translated", 0)
        total_skipped_excluded = results.get("total_skipped_excluded", 0)
        files_processed = results.get("files_processed", 0)

        total_success = total_updated
        total_failures = (total_not_found + total_skipped +
                         total_skipped_translated + total_skipped_excluded)

        aggregated["summary"] = {
            "files_processed": files_processed,
            "total_corrections": total_corrections,
            "total_success": total_success,
            "total_failures": total_failures,
            "success_rate": (total_success / total_corrections * 100) if total_corrections > 0 else 0,
            "failure_rate": (total_failures / total_corrections * 100) if total_corrections > 0 else 0,
            "matched": total_matched,
            "updated": total_updated,
            "not_found": total_not_found,
            "skipped_non_script": total_skipped,
            "skipped_translated": total_skipped_translated,
            "skipped_excluded": total_skipped_excluded,
            "errors": results.get("errors", []),
        }

        # Process per-file results
        for source_name, file_result in results.get("file_results", {}).items():
            target_name = file_result.get("target", "")
            corrections = file_result.get("corrections", 0)
            matched = file_result.get("matched", 0)
            updated = file_result.get("updated", 0)
            not_found = file_result.get("not_found", 0)

            # Count failures for this file
            failed = corrections - updated
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
                    aggregated["detailed_failures"].append({
                        "source_file": source_name,
                        "string_id": detail.get("string_id", ""),
                        "str_origin": detail.get("old", ""),
                        "correction": detail.get("new", ""),
                        "reason": FAILURE_REASONS.get(reason, reason),
                        "target_file": target_name,
                    })

    else:
        # File mode - single file
        corrections_count = results.get("corrections_count", 0)
        matched = results.get("matched", 0)
        updated = results.get("updated", 0)
        not_found = results.get("not_found", 0)
        skipped_non_script = results.get("skipped_non_script", 0)
        skipped_translated = results.get("skipped_translated", 0)
        skipped_excluded = results.get("skipped_excluded", 0)

        total_success = updated
        total_failures = (not_found + skipped_non_script +
                        skipped_translated + skipped_excluded)

        aggregated["summary"] = {
            "files_processed": 1,
            "total_corrections": corrections_count,
            "total_success": total_success,
            "total_failures": total_failures,
            "success_rate": (total_success / corrections_count * 100) if corrections_count > 0 else 0,
            "failure_rate": (total_failures / corrections_count * 100) if corrections_count > 0 else 0,
            "matched": matched,
            "updated": updated,
            "not_found": not_found,
            "skipped_non_script": skipped_non_script,
            "skipped_translated": skipped_translated,
            "skipped_excluded": skipped_excluded,
            "errors": results.get("errors", []),
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

                aggregated["detailed_failures"].append({
                    "source_file": "Source file",
                    "string_id": detail.get("string_id", ""),
                    "str_origin": detail.get("old", ""),
                    "correction": detail.get("new", ""),
                    "reason": FAILURE_REASONS.get(reason, reason),
                    "target_file": "Target file",
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

    return formats


def _write_summary_sheet(
    workbook,
    data: Dict,
    formats: Dict,
    source_name: str,
    target_name: str
):
    """Write the Summary sheet."""
    sheet = workbook.add_worksheet("Summary")
    summary = data["summary"]

    # Set column widths
    sheet.set_column("A:A", 25)
    sheet.set_column("B:B", 20)
    sheet.set_column("C:C", 15)
    sheet.set_column("D:D", 15)

    row = 0

    # Title
    sheet.merge_range(row, 0, row, 3, "TRANSFER FAILURE REPORT", formats["title"])
    row += 1

    # Timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.write(row, 0, f"Generated: {timestamp}", formats["timestamp"])
    row += 2

    # Source/Target info
    if source_name:
        sheet.write(row, 0, "Source:", formats["label"])
        sheet.write(row, 1, source_name, formats["value"])
        row += 1
    if target_name:
        sheet.write(row, 0, "Target:", formats["label"])
        sheet.write(row, 1, target_name, formats["value"])
        row += 1

    row += 1

    # Summary section header
    sheet.merge_range(row, 0, row, 3, "OVERVIEW", formats["section_header"])
    row += 1

    # Files processed
    sheet.write(row, 0, "Files Processed", formats["label"])
    sheet.write(row, 1, summary["files_processed"], formats["number_even"])
    row += 1

    # Total corrections
    sheet.write(row, 0, "Total Corrections", formats["label"])
    sheet.write(row, 1, summary["total_corrections"], formats["number_odd"])
    row += 2

    # Success/Failure counts section
    sheet.merge_range(row, 0, row, 3, "RESULTS", formats["section_header"])
    row += 1

    # Headers
    sheet.write(row, 0, "", formats["header"])
    sheet.write(row, 1, "Count", formats["header"])
    sheet.write(row, 2, "Percentage", formats["header"])
    row += 1

    # Success row
    sheet.write(row, 0, "SUCCESS (Updated)", formats["label"])
    sheet.write(row, 1, summary["total_success"], formats["success_number"])
    sheet.write(row, 2, summary["success_rate"] / 100, formats["success_percent"])
    row += 1

    # Failure row
    sheet.write(row, 0, "FAILURE (Total)", formats["label"])
    sheet.write(row, 1, summary["total_failures"], formats["failure_number"])
    sheet.write(row, 2, summary["failure_rate"] / 100, formats["failure_percent"])
    row += 2

    # Breakdown section
    sheet.merge_range(row, 0, row, 3, "FAILURE BREAKDOWN", formats["section_header"])
    row += 1

    # Breakdown items
    breakdown_items = [
        ("StringID Not Found", summary.get("not_found", 0)),
        ("Skipped (Non-SCRIPT)", summary.get("skipped_non_script", 0)),
        ("Skipped (Already Translated)", summary.get("skipped_translated", 0)),
        ("Skipped (Excluded Subfolder)", summary.get("skipped_excluded", 0)),
    ]

    total_failures = summary["total_failures"] or 1  # Avoid division by zero

    for i, (label, count) in enumerate(breakdown_items):
        if count > 0:
            fmt_cell = formats["cell_even"] if i % 2 == 0 else formats["cell_odd"]
            fmt_num = formats["number_even"] if i % 2 == 0 else formats["number_odd"]
            fmt_pct = formats["percent_even"] if i % 2 == 0 else formats["percent_odd"]

            sheet.write(row, 0, label, fmt_cell)
            sheet.write(row, 1, count, fmt_num)
            sheet.write(row, 2, count / total_failures, fmt_pct)
            row += 1

    row += 1

    # Errors section (if any)
    errors = summary.get("errors", [])
    if errors:
        sheet.merge_range(row, 0, row, 3, "ERRORS", formats["section_header"])
        row += 1

        for i, error in enumerate(errors[:10]):  # Max 10 errors
            fmt = formats["cell_even"] if i % 2 == 0 else formats["cell_odd"]
            sheet.merge_range(row, 0, row, 3, error, fmt)
            row += 1

        if len(errors) > 10:
            sheet.write(row, 0, f"... and {len(errors) - 10} more errors", formats["timestamp"])


def _write_reason_sheet(workbook, data: Dict, formats: Dict):
    """Write the Failure by Reason sheet."""
    sheet = workbook.add_worksheet("Failure by Reason")

    # Set column widths
    sheet.set_column("A:A", 35)
    sheet.set_column("B:B", 12)
    sheet.set_column("C:C", 15)

    row = 0

    # Title
    sheet.merge_range(row, 0, row, 2, "FAILURES BY REASON", formats["title"])
    row += 2

    # Headers
    sheet.write(row, 0, "Failure Reason", formats["header"])
    sheet.write(row, 1, "Count", formats["header"])
    sheet.write(row, 2, "Percentage", formats["header"])
    row += 1

    # Calculate total failures for percentages
    total = sum(v["count"] for v in data["by_reason"].values()) or 1

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

        reason_label = FAILURE_REASONS.get(reason_key, reason_key)
        percentage = count / total

        # Alternate row colors
        fmt_cell = formats["cell_even"] if i % 2 == 0 else formats["cell_odd"]
        fmt_num = formats["number_even"] if i % 2 == 0 else formats["number_odd"]
        fmt_pct = formats["percent_even"] if i % 2 == 0 else formats["percent_odd"]

        sheet.write(row, 0, reason_label, fmt_cell)
        sheet.write(row, 1, count, fmt_num)
        sheet.write(row, 2, percentage, fmt_pct)
        row += 1

    # Total row
    if sorted_reasons:
        row += 1
        sheet.write(row, 0, "TOTAL", formats["label"])
        sheet.write(row, 1, total, formats["failure_number"])
        sheet.write(row, 2, 1.0, formats["failure_percent"])


def _write_file_sheet(workbook, data: Dict, formats: Dict):
    """Write the Failure by File sheet."""
    sheet = workbook.add_worksheet("Failure by File")

    # Set column widths
    sheet.set_column("A:A", 30)  # Source File
    sheet.set_column("B:B", 12)  # Language
    sheet.set_column("C:C", 30)  # Target
    sheet.set_column("D:D", 12)  # Attempted
    sheet.set_column("E:E", 10)  # Failed
    sheet.set_column("F:F", 15)  # Success Rate

    row = 0

    # Title
    sheet.merge_range(row, 0, row, 5, "FAILURES BY FILE", formats["title"])
    row += 2

    # Headers
    headers = ["Source File", "Language", "Target", "Attempted", "Failed", "Success Rate"]
    for col, header in enumerate(headers):
        sheet.write(row, col, header, formats["header"])
    row += 1
    header_row = row - 1

    # Data rows
    for i, file_data in enumerate(data["by_file"]):
        # Alternate row colors
        fmt_cell = formats["cell_even"] if i % 2 == 0 else formats["cell_odd"]
        fmt_num = formats["number_even"] if i % 2 == 0 else formats["number_odd"]

        sheet.write(row, 0, file_data["source_file"], fmt_cell)
        sheet.write(row, 1, file_data["language"], fmt_cell)
        sheet.write(row, 2, file_data["target_file"], fmt_cell)
        sheet.write(row, 3, file_data["attempted"], fmt_num)
        sheet.write(row, 4, file_data["failed"], fmt_num)

        # Color-code success rate
        success_rate = file_data["success_rate"]
        if success_rate >= 95:
            sheet.write(row, 5, success_rate / 100, formats["success_percent"])
        elif success_rate >= 80:
            sheet.write(row, 5, success_rate / 100, formats["percent_even"] if i % 2 == 0 else formats["percent_odd"])
        else:
            sheet.write(row, 5, success_rate / 100, formats["failure_percent"])

        row += 1

    # Add autofilter
    if data["by_file"]:
        sheet.autofilter(header_row, 0, row - 1, 5)


def _write_detailed_sheet(workbook, data: Dict, formats: Dict):
    """Write the Detailed Failures sheet."""
    sheet = workbook.add_worksheet("Detailed Failures")

    # Set column widths
    sheet.set_column("A:A", 25)  # Source File
    sheet.set_column("B:B", 25)  # StringID
    sheet.set_column("C:C", 40)  # StrOrigin
    sheet.set_column("D:D", 40)  # Correction
    sheet.set_column("E:E", 30)  # Reason
    sheet.set_column("F:F", 25)  # Target

    row = 0

    # Title
    sheet.merge_range(row, 0, row, 5, "DETAILED FAILURES", formats["title"])
    row += 1

    # Count info
    total_failures = len(data["detailed_failures"])
    sheet.write(row, 0, f"Total failures: {total_failures}", formats["timestamp"])
    row += 2

    # Headers
    headers = ["Source File", "StringID", "StrOrigin", "Correction", "Reason", "Target"]
    for col, header in enumerate(headers):
        sheet.write(row, col, header, formats["header"])
    row += 1
    header_row = row - 1

    # Data rows (limit to 10000 to avoid performance issues)
    max_rows = 10000
    failures_to_write = data["detailed_failures"][:max_rows]

    for i, failure in enumerate(failures_to_write):
        # Alternate row colors
        fmt_cell = formats["cell_even"] if i % 2 == 0 else formats["cell_odd"]
        fmt_text = formats["text_even"] if i % 2 == 0 else formats["text_odd"]

        sheet.write(row, 0, failure.get("source_file", ""), fmt_cell)
        sheet.write_string(row, 1, str(failure.get("string_id", "")), fmt_text)  # TEXT format
        sheet.write(row, 2, failure.get("str_origin", ""), fmt_cell)
        sheet.write(row, 3, failure.get("correction", ""), fmt_cell)
        sheet.write(row, 4, failure.get("reason", ""), fmt_cell)
        sheet.write(row, 5, failure.get("target_file", ""), fmt_cell)
        row += 1

    # Add note if truncated
    if total_failures > max_rows:
        row += 1
        sheet.write(row, 0, f"Note: Showing first {max_rows} of {total_failures} failures", formats["timestamp"])

    # Add autofilter
    if failures_to_write:
        sheet.autofilter(header_row, 0, row - 1, 5)

    # Freeze header row
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
