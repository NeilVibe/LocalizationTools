"""
Submit Datasheet Module
=======================
Generate MasterSubmitDatasheet_EN.xlsx and MasterSubmitDatasheet_CN.xlsx
containing non-Script category (Item, Character, Skill, Quest, etc.) ISSUE rows.

Output columns:
- StrOrigin (Korean text directly from QA file SourceText column)
- Correction (MEMO/COMMENT from QA - tester's correction)
- StringID (directly from QA file STRINGID column)

No EXPORT mapping needed — all data comes directly from QA files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.excel_ops import safe_load_workbook, build_column_map


# SourceText column names in priority order (uppercased for col_map lookup)
_SOURCE_TEXT_CANDIDATES = [
    "SOURCETEXT (KR)",
    "ORIGINAL (KR)",
    "ORIGINAL",
    "KOREAN",
]


@dataclass
class DatasheetIssueRow:
    """Represents a single ISSUE row for MasterSubmitDatasheet."""
    source_text: str      # Korean from SourceText column
    correction: str       # Tester's fix from MEMO/COMMENT
    stringid: str         # STRINGID from QA file
    category: str         # Category name (Item, Quest, etc.)
    username: str = ""    # Tester who made the correction


@dataclass
class DatasheetConflictRow:
    """Represents a conflict where multiple testers corrected the same StringID differently."""
    stringid: str
    source_text: str
    category: str
    corrections: List[Tuple[str, str]] = field(default_factory=list)  # (username, correction) pairs


def _find_source_text_col(col_map: Dict[str, int]) -> int | None:
    """Find the SourceText column using priority-ordered candidates."""
    for candidate in _SOURCE_TEXT_CANDIDATES:
        col = col_map.get(candidate)
        if col is not None:
            return col
    return None


def collect_datasheet_issue_rows(
    qa_folders: List[Dict],
) -> Tuple[List[DatasheetIssueRow], List[DatasheetConflictRow]]:
    """
    Collect ISSUE rows from non-Script QA folders.

    For each QA file:
    1. Find STATUS, STRINGID, SourceText, MEMO/COMMENT columns
    2. Filter rows where STATUS = "ISSUE"
    3. Dedup by StringID (lowercase) — detect conflicts
    4. Return unique rows (last one wins) + conflict list

    Args:
        qa_folders: List of folder dicts with {xlsx_path, username, category, ...}

    Returns:
        Tuple of (List[DatasheetIssueRow], List[DatasheetConflictRow])
    """
    # Track all corrections per StringID: {stringid_lower: [(username, correction, source_text, category, original_sid), ...]}
    sid_corrections: Dict[str, List[Tuple[str, str, str, str, str]]] = {}

    files_processed = 0

    print(f"  Collecting ISSUE rows from {len(qa_folders)} non-Script QA files...")

    for qf in qa_folders:
        xlsx_path = qf.get("xlsx_path")
        username = qf.get("username", "unknown")
        category = qf.get("category", "unknown")

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

                col_map = build_column_map(ws)
                if not col_map:
                    continue

                # Find required columns
                status_col = col_map.get("STATUS")
                stringid_col = col_map.get("STRINGID")
                source_col = _find_source_text_col(col_map)

                # Comment: try MEMO first, then COMMENT, then COMMENT_{username}
                memo_col = col_map.get("MEMO")
                comment_col = col_map.get("COMMENT")

                comment_user_cols = []
                if not memo_col and not comment_col:
                    for key, col in col_map.items():
                        if key.startswith("COMMENT_") and not key.startswith("MANAGER_COMMENT_"):
                            comment_user_cols.append(col)

                if not status_col or not stringid_col or not source_col:
                    continue

                # Convert to 0-based indices
                status_idx = status_col - 1
                stringid_idx = stringid_col - 1
                source_idx = source_col - 1
                memo_idx = (memo_col - 1) if memo_col else None
                comment_idx = (comment_col - 1) if comment_col else None
                comment_user_idxs = [(c - 1) for c in comment_user_cols]

                for row_tuple in ws.iter_rows(min_row=2, values_only=True):
                    if not row_tuple or len(row_tuple) <= status_idx:
                        continue

                    status_val = row_tuple[status_idx]
                    if not status_val:
                        continue

                    status_str = str(status_val).strip().upper()
                    if status_str != "ISSUE":
                        continue

                    # Get StringID
                    stringid = ""
                    if stringid_idx < len(row_tuple) and row_tuple[stringid_idx]:
                        stringid = str(row_tuple[stringid_idx]).strip()
                    if not stringid:
                        continue

                    # Get SourceText
                    source_text = ""
                    if source_idx < len(row_tuple) and row_tuple[source_idx]:
                        source_text = str(row_tuple[source_idx]).strip()

                    # Get correction — MEMO > COMMENT > COMMENT_{user}
                    memo = ""
                    if memo_idx is not None and memo_idx < len(row_tuple) and row_tuple[memo_idx]:
                        memo = str(row_tuple[memo_idx]).strip()
                    if not memo and comment_idx is not None and comment_idx < len(row_tuple) and row_tuple[comment_idx]:
                        memo = str(row_tuple[comment_idx]).strip()
                    if not memo and comment_user_idxs:
                        for cidx in comment_user_idxs:
                            if cidx < len(row_tuple) and row_tuple[cidx]:
                                memo = str(row_tuple[cidx]).strip()
                                if memo:
                                    break

                    if not memo:
                        continue

                    sid_key = stringid.lower()
                    if sid_key not in sid_corrections:
                        sid_corrections[sid_key] = []
                    sid_corrections[sid_key].append((username, memo, source_text, category, stringid))

        except Exception as e:
            import traceback
            print(f"    WARNING: Error reading {xlsx_path.name}: {e}")
            traceback.print_exc()
        finally:
            if wb:
                wb.close()

    # Build final lists
    issue_rows: List[DatasheetIssueRow] = []
    conflict_rows: List[DatasheetConflictRow] = []

    for sid_key, corrections in sid_corrections.items():
        # Detect unique corrections
        unique_memos: Dict[str, str] = {}
        for username, memo, source_text, category, original_sid in corrections:
            if memo not in unique_memos:
                unique_memos[memo] = username

        if len(unique_memos) > 1:
            first = corrections[0]
            conflict_rows.append(DatasheetConflictRow(
                stringid=first[4],  # original_sid from first entry
                source_text=first[2],
                category=first[3],
                corrections=[(username, memo) for username, memo, _, _, _ in corrections],
            ))

        # Last correction wins
        last = corrections[-1]
        issue_rows.append(DatasheetIssueRow(
            source_text=last[2],
            correction=last[1],
            stringid=last[4],
            category=last[3],
            username=last[0],
        ))

    print(f"  Found {len(issue_rows)} unique ISSUE rows from {files_processed} files")
    if conflict_rows:
        print(f"  CONFLICTS: {len(conflict_rows)} StringIDs have multiple different corrections")

    return issue_rows, conflict_rows


def generate_master_submit_datasheet(
    issue_rows: List[DatasheetIssueRow],
    output_path: Path,
    lang_label: str,
) -> bool:
    """
    Generate Excel file using xlsxwriter.

    Columns: StrOrigin | Correction | StringID
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
        output_path.parent.mkdir(parents=True, exist_ok=True)

        workbook = xlsxwriter.Workbook(str(output_path))
        worksheet = workbook.add_worksheet("SubmitDatasheet")

        headers = ["StrOrigin", "Correction", "StringID"]

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

        stringid_format = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'border': 1,
            'num_format': '@',
        })

        # Column widths
        worksheet.set_column(0, 0, 50)  # StrOrigin
        worksheet.set_column(1, 1, 50)  # Correction
        worksheet.set_column(2, 2, 45)  # StringID

        # Header row
        for col_idx, header in enumerate(headers):
            worksheet.write(0, col_idx, header, header_format)

        # Data rows
        for row_idx, row in enumerate(issue_rows, start=1):
            worksheet.write(row_idx, 0, row.source_text, cell_format)
            worksheet.write(row_idx, 1, row.correction, cell_format)
            worksheet.write(row_idx, 2, row.stringid, stringid_format)

        workbook.close()
        print(f"    Generated {output_path.name} with {len(issue_rows)} rows")
        return True

    except Exception as e:
        print(f"    ERROR generating {output_path.name}: {e}")
        return False


def generate_datasheet_conflict_file(
    conflict_rows: List[DatasheetConflictRow],
    output_path: Path,
    lang_label: str,
) -> bool:
    """
    Generate Excel file showing conflicts (same StringID, different corrections).

    Columns: STRINGID | SourceText | Category | USER | CORRECTION
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

        headers = ["STRINGID", "SourceText", "Category", "USER", "CORRECTION"]

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'bg_color': '#FFCCCC',
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

        # Column widths
        worksheet.set_column(0, 0, 45)  # STRINGID
        worksheet.set_column(1, 1, 50)  # SourceText
        worksheet.set_column(2, 2, 20)  # Category
        worksheet.set_column(3, 3, 15)  # USER
        worksheet.set_column(4, 4, 50)  # CORRECTION

        for col_idx, header in enumerate(headers):
            worksheet.write(0, col_idx, header, header_format)

        row_idx = 1
        for conflict in conflict_rows:
            for username, memo in conflict.corrections:
                worksheet.write(row_idx, 0, conflict.stringid, stringid_format)
                worksheet.write(row_idx, 1, conflict.source_text, cell_format)
                worksheet.write(row_idx, 2, conflict.category, cell_format)
                worksheet.write(row_idx, 3, username, cell_format)
                worksheet.write(row_idx, 4, memo, cell_format)
                row_idx += 1

        workbook.close()
        print(f"    Generated {output_path.name} with {len(conflict_rows)} conflicts ({row_idx - 1} rows)")
        return True

    except Exception as e:
        print(f"    ERROR generating {output_path.name}: {e}")
        return False
