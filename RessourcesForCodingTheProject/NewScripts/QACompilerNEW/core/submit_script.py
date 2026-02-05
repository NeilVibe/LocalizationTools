"""
Submit Script Module
====================
Generate MasterSubmitScript_EN.xlsx and MasterSubmitScript_CN.xlsx
containing Script category (Sequencer + Dialog) ISSUE rows.

Output columns:
- KOREAN (StrOrigin from EXPORT)
- FIXED TRANSLATION (MEMO/COMMENT from QA - tester's correction)
- STRINGID (mapped from EventName via EXPORT)
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SCRIPT_COLS
from core.excel_ops import safe_load_workbook, build_column_map


@dataclass
class IssueRow:
    """Represents a single ISSUE row for MasterSubmitScript."""
    korean: str           # StrOrigin from EXPORT
    fixed_translation: str  # MEMO/COMMENT from QA
    stringid: str         # StringId from EXPORT
    eventname: str        # Original EventName (for debugging)
    username: str = ""    # Tester who made the correction


@dataclass
class ConflictRow:
    """Represents a conflict where multiple testers corrected the same EventName differently."""
    eventname: str
    stringid: str
    korean: str
    corrections: List[tuple]  # List of (username, memo) pairs


def collect_issue_rows(
    qa_folders: List[Dict],
    export_mapping: Dict[str, Dict[str, str]]
) -> tuple:
    """
    Collect ISSUE rows from QA folders (Sequencer + Dialog combined).

    For each QA file:
    1. Find STATUS, MEMO/COMMENT, EventName columns
    2. Filter rows where STATUS = "ISSUE"
    3. Look up StringId and StrOrigin from export_mapping
    4. Detect conflicts (same EventName, different corrections)
    5. Return unique rows (last one wins) + conflict list

    Args:
        qa_folders: List of folder dicts with {xlsx_path, username, ...}
        export_mapping: {soundeventname_lowercase: {"stringid": X, "strorigin": Y}}

    Returns:
        Tuple of (List[IssueRow], List[ConflictRow])
        - IssueRow list: unique entries (last correction wins for conflicts)
        - ConflictRow list: entries where multiple users corrected differently
    """
    # Track all corrections per EventName: {eventname_lower: [(username, memo), ...]}
    eventname_corrections: Dict[str, List[tuple]] = {}
    # Track EXPORT data per EventName
    eventname_export: Dict[str, Dict[str, str]] = {}

    missing_eventnames = 0
    files_processed = 0

    print(f"  Collecting ISSUE rows from {len(qa_folders)} QA files...")

    for qf in qa_folders:
        xlsx_path = qf.get("xlsx_path")
        username = qf.get("username", "unknown")

        if xlsx_path is None or not xlsx_path.exists():
            continue

        files_processed += 1
        wb = None

        try:
            wb = safe_load_workbook(xlsx_path, read_only=True, data_only=True)

            for sheet_name in wb.sheetnames:
                if sheet_name == "STATUS":
                    continue

                ws = wb[sheet_name]

                # Check for empty sheet
                if ws.max_row is None or ws.max_row < 2:
                    continue
                if ws.max_column is None or ws.max_column < 1:
                    continue

                # Build column map for header lookup
                col_map = build_column_map(ws)

                # Find required columns by name
                status_col = col_map.get("STATUS")
                # Unique ID: try EventName first, then STRINGID
                eventname_col = col_map.get("EVENTNAME") or col_map.get("STRINGID")
                # Comment: try MEMO first, then COMMENT
                memo_col = col_map.get("MEMO")
                comment_col = col_map.get("COMMENT")

                if not status_col or not eventname_col:
                    continue

                # Convert to 0-based indices for tuple access
                status_idx = status_col - 1
                eventname_idx = eventname_col - 1
                memo_idx = (memo_col - 1) if memo_col else None
                comment_idx = (comment_col - 1) if comment_col else None

                # Scan rows for ISSUE status
                for row_tuple in ws.iter_rows(min_row=2, max_col=ws.max_column, values_only=True):
                    # Skip empty or too-short rows
                    if not row_tuple or len(row_tuple) <= status_idx:
                        continue

                    # Check STATUS
                    status_val = row_tuple[status_idx]
                    if not status_val:
                        continue

                    status_str = str(status_val).strip().upper()
                    if status_str != "ISSUE":
                        continue

                    # Get EventName
                    eventname = ""
                    if eventname_idx < len(row_tuple) and row_tuple[eventname_idx]:
                        eventname = str(row_tuple[eventname_idx]).strip()

                    if not eventname:
                        continue

                    # Get MEMO or COMMENT (tester's fix) - try MEMO first, fallback to COMMENT
                    memo = ""
                    if memo_idx is not None and memo_idx < len(row_tuple) and row_tuple[memo_idx]:
                        memo = str(row_tuple[memo_idx]).strip()
                    if not memo and comment_idx is not None and comment_idx < len(row_tuple) and row_tuple[comment_idx]:
                        memo = str(row_tuple[comment_idx]).strip()

                    # Skip rows without a fix (STATUS=ISSUE but no correction provided)
                    if not memo:
                        continue

                    eventname_key = eventname.lower()

                    # Track correction for this EventName
                    if eventname_key not in eventname_corrections:
                        eventname_corrections[eventname_key] = []
                    eventname_corrections[eventname_key].append((username, memo, eventname))

                    # Look up and cache EXPORT data
                    if eventname_key not in eventname_export:
                        export_data = export_mapping.get(eventname_key)
                        if export_data:
                            eventname_export[eventname_key] = export_data
                        else:
                            eventname_export[eventname_key] = {"stringid": "", "strorigin": ""}
                            missing_eventnames += 1

        except Exception as e:
            print(f"    WARNING: Error reading {xlsx_path.name}: {e}")
        finally:
            if wb:
                wb.close()

    # Build final lists: unique rows and conflicts
    issue_rows: List[IssueRow] = []
    conflict_rows: List[ConflictRow] = []

    for eventname_key, corrections in eventname_corrections.items():
        export_data = eventname_export.get(eventname_key, {})
        stringid = export_data.get("stringid", "")
        korean = export_data.get("strorigin", "")

        # Get unique memos for this EventName
        unique_memos = {}
        for username, memo, original_eventname in corrections:
            if memo not in unique_memos:
                unique_memos[memo] = (username, original_eventname)

        if len(unique_memos) > 1:
            # CONFLICT: Multiple different corrections for same EventName
            conflict_rows.append(ConflictRow(
                eventname=corrections[0][2],  # Use original case from first entry
                stringid=stringid,
                korean=korean,
                corrections=[(username, memo) for username, memo, _ in corrections]
            ))

        # Take the LAST correction (last one wins)
        last_username, last_memo, last_eventname = corrections[-1]
        issue_rows.append(IssueRow(
            korean=korean,
            fixed_translation=last_memo,
            stringid=stringid,
            eventname=last_eventname,
            username=last_username
        ))

    print(f"  Found {len(issue_rows)} unique ISSUE rows from {files_processed} files")
    if conflict_rows:
        print(f"  CONFLICTS: {len(conflict_rows)} EventNames have multiple different corrections")
    if missing_eventnames > 0:
        print(f"    WARNING: {missing_eventnames} EventNames not found in EXPORT mapping")

    return issue_rows, conflict_rows


def generate_master_submit_script(
    issue_rows: List[IssueRow],
    output_path: Path,
    lang_label: str
) -> bool:
    """
    Generate Excel file using xlsxwriter.

    Columns: KOREAN | FIXED TRANSLATION | STRINGID

    Args:
        issue_rows: List of IssueRow objects to write
        output_path: Path to output Excel file
        lang_label: Language label for logging ("EN" or "CN")

    Returns:
        True if successful, False otherwise
    """
    try:
        import xlsxwriter
    except ImportError:
        print("    ERROR: xlsxwriter not installed. Install with: pip install xlsxwriter")
        return False

    if not issue_rows:
        print(f"    No ISSUE rows to write for {lang_label}")
        return False

    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create workbook with xlsxwriter
        workbook = xlsxwriter.Workbook(str(output_path))
        worksheet = workbook.add_worksheet("SubmitScript")

        # Define headers
        headers = ["KOREAN", "FIXED TRANSLATION", "STRINGID"]

        # Create formats
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'bg_color': '#DAEEF3',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
        })

        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'text_wrap': True,
            'border': 1,
        })

        # String format for StringID (prevent scientific notation)
        stringid_format = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'border': 1,
            'num_format': '@',  # Text format
        })

        # Set column widths
        worksheet.set_column(0, 0, 50)  # KOREAN
        worksheet.set_column(1, 1, 50)  # FIXED TRANSLATION
        worksheet.set_column(2, 2, 45)  # STRINGID

        # Write header row
        for col_idx, header in enumerate(headers):
            worksheet.write(0, col_idx, header, header_format)

        # Write data rows
        for row_idx, issue_row in enumerate(issue_rows, start=1):
            worksheet.write(row_idx, 0, issue_row.korean, cell_format)
            worksheet.write(row_idx, 1, issue_row.fixed_translation, cell_format)
            worksheet.write(row_idx, 2, issue_row.stringid, stringid_format)

        workbook.close()
        print(f"    Generated {output_path.name} with {len(issue_rows)} rows")
        return True

    except Exception as e:
        print(f"    ERROR generating {output_path.name}: {e}")
        return False


def generate_conflict_file(
    conflict_rows: List[ConflictRow],
    output_path: Path,
    lang_label: str
) -> bool:
    """
    Generate Excel file showing conflicts (same EventName, different corrections).

    Columns: EVENTNAME | STRINGID | KOREAN | USER | CORRECTION

    Args:
        conflict_rows: List of ConflictRow objects
        output_path: Path to output Excel file
        lang_label: Language label for logging ("EN" or "CN")

    Returns:
        True if successful, False otherwise
    """
    try:
        import xlsxwriter
    except ImportError:
        print("    ERROR: xlsxwriter not installed")
        return False

    if not conflict_rows:
        print(f"    No conflicts to write for {lang_label}")
        return False

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        workbook = xlsxwriter.Workbook(str(output_path))
        worksheet = workbook.add_worksheet("Conflicts")

        headers = ["EVENTNAME", "STRINGID", "KOREAN", "USER", "CORRECTION"]

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'bg_color': '#FFCCCC',  # Light red for conflicts
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
        })

        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'text_wrap': True,
            'border': 1,
        })

        stringid_format = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'border': 1,
            'num_format': '@',
        })

        # Set column widths
        worksheet.set_column(0, 0, 35)  # EVENTNAME
        worksheet.set_column(1, 1, 40)  # STRINGID
        worksheet.set_column(2, 2, 50)  # KOREAN
        worksheet.set_column(3, 3, 15)  # USER
        worksheet.set_column(4, 4, 50)  # CORRECTION

        # Write headers
        for col_idx, header in enumerate(headers):
            worksheet.write(0, col_idx, header, header_format)

        # Write conflict rows (one row per user correction)
        row_idx = 1
        for conflict in conflict_rows:
            for username, memo in conflict.corrections:
                worksheet.write(row_idx, 0, conflict.eventname, cell_format)
                worksheet.write(row_idx, 1, conflict.stringid, stringid_format)
                worksheet.write(row_idx, 2, conflict.korean, cell_format)
                worksheet.write(row_idx, 3, username, cell_format)
                worksheet.write(row_idx, 4, memo, cell_format)
                row_idx += 1

        workbook.close()
        print(f"    Generated {output_path.name} with {len(conflict_rows)} conflicts ({row_idx - 1} rows)")
        return True

    except Exception as e:
        print(f"    ERROR generating {output_path.name}: {e}")
        return False
