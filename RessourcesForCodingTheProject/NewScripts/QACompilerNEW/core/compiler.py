"""
Compiler Module
===============
Main compilation orchestration: QAfolder -> Masterfolder_EN/CN + Tracker

Handles:
- Discovery of QA folders
- Language-based routing (EN/CN)
- Category processing with clustering
- Master file generation
- Progress tracker updates
"""

from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    CATEGORIES, CATEGORY_TO_MASTER, TRANSLATION_COLS, SCRIPT_TYPE_CATEGORIES,
    SCRIPT_COLS,
    MASTER_FOLDER_EN, MASTER_FOLDER_CN,
    IMAGES_FOLDER_EN, IMAGES_FOLDER_CN,
    TRACKER_PATH,
    load_tester_mapping, ensure_folders_exist,
    get_target_master_category
)
from core.discovery import discover_qa_folders, group_folders_by_language
from core.excel_ops import (
    safe_load_workbook, ensure_master_folders,
    get_or_create_master, copy_images_with_unique_names,
    find_column_by_header, sort_worksheet_az
)
from core.processing import (
    process_sheet, update_status_sheet,
    hide_empty_comment_rows, autofit_rows_with_wordwrap,
    count_words_english, count_chars_chinese
)


# Valid manager status values
VALID_MANAGER_STATUS = {"FIXED", "REPORTED", "CHECKING", "NON-ISSUE", "NON ISSUE"}

# Valid tester status values (rows with these are "done")
# NOTE: Script-type categories (Sequencer/Dialog) use "NON-ISSUE" (with hyphen)
# while other categories use "NO ISSUE" (with space). Accept both.
VALID_TESTER_STATUS = {"ISSUE", "NO ISSUE", "NON-ISSUE", "BLOCKED", "KOREAN"}


# =============================================================================
# FIXED SCREENSHOTS COLLECTION
# =============================================================================

def collect_fixed_screenshots(master_folder: Path) -> set:
    """
    Collect all screenshot filenames where STATUS_{User} = FIXED.

    Used to skip copying these images during rebuild (optimization).

    Args:
        master_folder: Master folder to scan (EN or CN)

    Returns:
        Set of screenshot filenames that are FIXED
    """
    fixed_screenshots = set()

    for master_file in master_folder.glob("Master_*.xlsx"):
        try:
            wb = safe_load_workbook(master_file)

            for sheet_name in wb.sheetnames:
                if sheet_name == "STATUS":
                    continue

                ws = wb[sheet_name]

                # Find all SCREENSHOT_{User} and STATUS_{User} columns
                screenshot_cols = {}  # username -> col
                status_cols = {}      # username -> col

                for col in range(1, ws.max_column + 1):
                    header = ws.cell(row=1, column=col).value
                    if header:
                        header_str = str(header)
                        if header_str.startswith("SCREENSHOT_"):
                            username = header_str.replace("SCREENSHOT_", "")
                            screenshot_cols[username] = col
                        elif header_str.startswith("STATUS_"):
                            username = header_str.replace("STATUS_", "")
                            status_cols[username] = col

                # Collect screenshots where status is FIXED
                for row in range(2, ws.max_row + 1):
                    for username in screenshot_cols:
                        screenshot_col = screenshot_cols[username]
                        status_col = status_cols.get(username)

                        screenshot_val = ws.cell(row=row, column=screenshot_col).value
                        if screenshot_val and status_col:
                            status_val = ws.cell(row=row, column=status_col).value
                            if status_val and str(status_val).strip().upper() == "FIXED":
                                # Add the screenshot filename
                                fixed_screenshots.add(str(screenshot_val).strip())

            wb.close()

        except Exception as e:
            print(f"  WARN: Error reading {master_file.name} for fixed screenshots: {e}")

    return fixed_screenshots


# =============================================================================
# MANAGER STATUS COLLECTION
# =============================================================================

def extract_comment_text(full_comment) -> str:
    """
    Extract the actual comment text from formatted comment.

    Comment format: "comment text\n---\nstringid:\n10001\n(updated: ...)"
    Returns: Just the comment text before "---"
    """
    if not full_comment:
        return ""
    comment_str = str(full_comment).strip()
    if "---" in comment_str:
        return comment_str.split("---")[0].strip()
    return comment_str


def collect_manager_status(master_folder: Path) -> Dict:
    """
    Read existing Master files and collect all STATUS_{User} and MANAGER_COMMENT_{User} values.

    KEYED BY (STRINGID, TESTER_COMMENT_TEXT) - Manager status is paired with tester's comment.

    Dict Structure:
        {
            category: {
                sheet_name: {
                    (stringid, tester_comment_text): {
                        username: {
                            "status": "FIXED",
                            "manager_comment": "Fixed in build 5"
                        }
                    }
                }
            }
        }

    Matching Logic:
        - Primary key: (stringid, tester_comment_text) - exact match
        - Fallback key: ("", tester_comment_text) - when STRINGID changes but comment same

    Args:
        master_folder: Which Master folder to scan (EN or CN)

    Returns:
        Dict with manager status keyed by (stringid, tester_comment_text)
    """
    manager_status = {}

    for category in CATEGORIES:
        target_category = get_target_master_category(category)
        master_path = master_folder / f"Master_{target_category}.xlsx"
        if not master_path.exists():
            continue

        try:
            wb = safe_load_workbook(master_path)
            if category not in manager_status:
                manager_status[category] = {}

            for sheet_name in wb.sheetnames:
                if sheet_name == "STATUS":
                    continue

                ws = wb[sheet_name]
                manager_status[category][sheet_name] = {}

                # Find STRINGID column (or EventName for Script-type categories)
                stringid_col = find_column_by_header(ws, "STRINGID")
                if not stringid_col:
                    # Script-type categories use EventName instead of STRINGID
                    stringid_col = find_column_by_header(ws, "EventName")

                # Find all COMMENT_{User}, STATUS_{User}, MANAGER_COMMENT_{User} columns
                comment_cols = {}          # username -> col (TESTER's comment)
                status_cols = {}           # username -> col (MANAGER's status)
                manager_comment_cols = {}  # username -> col (MANAGER's comment)

                for col in range(1, ws.max_column + 1):
                    header = ws.cell(row=1, column=col).value
                    if header:
                        header_str = str(header)
                        if header_str.startswith("COMMENT_"):
                            username = header_str.replace("COMMENT_", "")
                            comment_cols[username] = col
                        elif header_str.startswith("STATUS_") and not header_str.startswith("TESTER_STATUS_"):
                            username = header_str.replace("STATUS_", "")
                            status_cols[username] = col
                        elif header_str.startswith("MANAGER_COMMENT_"):
                            username = header_str.replace("MANAGER_COMMENT_", "")
                            manager_comment_cols[username] = col

                if not status_cols:
                    continue

                # Collect manager status, keyed by (stringid, tester_comment_text)
                for row in range(2, ws.max_row + 1):
                    for username, status_col in status_cols.items():
                        status_value = ws.cell(row=row, column=status_col).value
                        manager_comment_col = manager_comment_cols.get(username)
                        manager_comment_value = None
                        if manager_comment_col:
                            manager_comment_value = ws.cell(row=row, column=manager_comment_col).value

                        # Only store if there's a manager status or manager comment
                        has_status = status_value and str(status_value).strip().upper() in VALID_MANAGER_STATUS
                        has_manager_comment = manager_comment_value and str(manager_comment_value).strip()

                        if has_status or has_manager_comment:
                            # Get STRINGID for this row (from Master - reliable!)
                            stringid = ""
                            if stringid_col:
                                stringid_val = ws.cell(row=row, column=stringid_col).value
                                if stringid_val:
                                    stringid = str(stringid_val).strip()

                            # Get TESTER's comment text (this is what manager reviewed)
                            tester_comment_text = ""
                            comment_col = comment_cols.get(username)
                            if comment_col:
                                full_comment = ws.cell(row=row, column=comment_col).value
                                tester_comment_text = extract_comment_text(full_comment)

                            # Need tester comment to match (manager status is response to tester comment)
                            if tester_comment_text:
                                # Primary key: (stringid, tester_comment_text)
                                key = (stringid, tester_comment_text)
                                if key not in manager_status[category][sheet_name]:
                                    manager_status[category][sheet_name][key] = {}
                                manager_status[category][sheet_name][key][username] = {
                                    "status": str(status_value).strip().upper() if has_status else None,
                                    "manager_comment": str(manager_comment_value).strip() if has_manager_comment else None
                                }

                                # Fallback key: ("", tester_comment_text) - for when STRINGID changes
                                fallback_key = ("", tester_comment_text)
                                if fallback_key not in manager_status[category][sheet_name]:
                                    manager_status[category][sheet_name][fallback_key] = {}
                                if username not in manager_status[category][sheet_name][fallback_key]:
                                    manager_status[category][sheet_name][fallback_key][username] = {
                                        "status": str(status_value).strip().upper() if has_status else None,
                                        "manager_comment": str(manager_comment_value).strip() if has_manager_comment else None
                                    }

            wb.close()

        except Exception as e:
            print(f"  WARN: Error reading {master_path.name} for preprocess: {e}")

    return manager_status


def collect_manager_stats_for_tracker() -> Dict:
    """
    Read all Master files (EN + CN) and count FIXED/REPORTED/CHECKING/NON-ISSUE per user per category.

    IMPORTANT: Uses sheet_name as category (not outer loop category) to avoid
    triple-counting for clustered categories like Skill/Help/System → Master_System.xlsx.

    Returns:
        {category: {user: {fixed, reported, checking, nonissue, lang}}}
    """
    print("\n" + "="*60)
    print("[COLLECT_MANAGER_STATS] Starting collection from Master files...")
    print("="*60)

    tester_mapping = load_tester_mapping()
    manager_stats = defaultdict(lambda: defaultdict(
        lambda: {"fixed": 0, "reported": 0, "checking": 0, "nonissue": 0, "lang": "EN"}
    ))

    # Scan both EN and CN folders
    for master_folder in [MASTER_FOLDER_EN, MASTER_FOLDER_CN]:
        print(f"\n[SCAN] Folder: {master_folder}")
        # Track processed master files to avoid re-reading (clustered categories share masters)
        processed_masters = set()

        for category in CATEGORIES:
            target_category = get_target_master_category(category)
            master_path = master_folder / f"Master_{target_category}.xlsx"

            # Skip if already processed or doesn't exist
            if master_path in processed_masters:
                continue
            if not master_path.exists():
                print(f"  [SKIP] {master_path.name} - does not exist")
                continue

            processed_masters.add(master_path)
            print(f"\n  [READ] {master_path.name}")

            try:
                wb = safe_load_workbook(master_path)

                for sheet_name in wb.sheetnames:
                    if sheet_name == "STATUS":
                        continue

                    ws = wb[sheet_name]

                    # Find all STATUS_{User} columns
                    status_cols = {}
                    all_headers = []
                    for col in range(1, ws.max_column + 1):
                        header = ws.cell(row=1, column=col).value
                        if header:
                            all_headers.append(str(header))
                            if str(header).startswith("STATUS_"):
                                username = str(header).replace("STATUS_", "")
                                status_cols[username] = col

                    if not status_cols:
                        # Show headers to debug why no STATUS_ columns found
                        status_like = [h for h in all_headers if "STATUS" in h.upper()]
                        print(f"    [SHEET] {sheet_name}: NO STATUS_ columns (headers with STATUS: {status_like[:5]})")
                        continue

                    print(f"    [SHEET] {sheet_name}: Found STATUS_ columns for users: {list(status_cols.keys())}")

                    # Count status values per user
                    # USE SHEET_NAME AS CATEGORY (not outer loop category!)
                    # Master_System.xlsx has sheets "Skill", "Help", "System" → use those
                    # Master_Script.xlsx has sheets "Sequencer", "Dialog" → use those
                    sheet_counts = defaultdict(lambda: {"fixed": 0, "reported": 0, "checking": 0, "nonissue": 0})
                    for row in range(2, ws.max_row + 1):
                        for username, col in status_cols.items():
                            value = ws.cell(row=row, column=col).value
                            if value:
                                status_upper = str(value).strip().upper()
                                if status_upper == "FIXED":
                                    manager_stats[sheet_name][username]["fixed"] += 1
                                    sheet_counts[username]["fixed"] += 1
                                elif status_upper == "REPORTED":
                                    manager_stats[sheet_name][username]["reported"] += 1
                                    sheet_counts[username]["reported"] += 1
                                elif status_upper == "CHECKING":
                                    manager_stats[sheet_name][username]["checking"] += 1
                                    sheet_counts[username]["checking"] += 1
                                elif status_upper in ("NON-ISSUE", "NON ISSUE"):
                                    manager_stats[sheet_name][username]["nonissue"] += 1
                                    sheet_counts[username]["nonissue"] += 1
                            manager_stats[sheet_name][username]["lang"] = tester_mapping.get(username, "EN")

                    # Print counts for this sheet
                    for username, counts in sheet_counts.items():
                        total = counts["fixed"] + counts["reported"] + counts["checking"] + counts["nonissue"]
                        if total > 0:
                            print(f"      [{username}] fixed={counts['fixed']}, reported={counts['reported']}, checking={counts['checking']}, nonissue={counts['nonissue']}")

                wb.close()

            except Exception as e:
                print(f"  WARN: Error reading {master_path.name} for manager stats: {e}")

    # Summary
    result = dict(manager_stats)
    print(f"\n[COLLECT_MANAGER_STATS] SUMMARY:")
    print(f"  Categories found: {list(result.keys())}")
    total_users = 0
    total_stats = {"fixed": 0, "reported": 0, "checking": 0, "nonissue": 0}
    for cat, users in result.items():
        total_users += len(users)
        for user, stats in users.items():
            total_stats["fixed"] += stats["fixed"]
            total_stats["reported"] += stats["reported"]
            total_stats["checking"] += stats["checking"]
            total_stats["nonissue"] += stats["nonissue"]
    print(f"  Total users: {total_users}")
    print(f"  Total stats: fixed={total_stats['fixed']}, reported={total_stats['reported']}, checking={total_stats['checking']}, nonissue={total_stats['nonissue']}")
    print("="*60 + "\n")

    return result


# =============================================================================
# SCRIPT-TYPE PREPROCESSING (Sequencer/Dialog optimization)
# =============================================================================

def preprocess_script_category(
    qa_folders: List[Dict],
    is_english: bool = True
) -> Dict:
    """
    Preprocess Script-type category files to build global universe of rows WITH status.

    This optimization scans ALL QA files and collects only rows that have been checked
    (have a STATUS value). This dramatically speeds up processing for large files
    like Sequencer/Dialog which can have thousands of unchecked rows.

    Args:
        qa_folders: List of folder dicts from discovery (all for this category)
        is_english: Whether these are English files

    Returns:
        Dict with:
            - "rows": {(eventname, text): row_data} - all unique rows with status
            - "row_count": int - total rows with status
            - "source_files": int - number of files scanned
            - "errors": List of error messages encountered
    """
    import traceback
    # SCRIPT_COLS already imported from config at module level

    universe = {}  # (eventname, text) -> row_data
    source_files = 0
    errors = []  # Track errors for debugging

    print(f"  [PREPROCESS] Scanning {len(qa_folders)} QA files for rows with STATUS...")

    if not qa_folders:
        print(f"    [WARN] No QA folders provided")
        return {"rows": {}, "row_count": 0, "source_files": 0, "errors": ["No QA folders provided"]}

    for qf in qa_folders:
        xlsx_path = qf.get("xlsx_path")
        username = qf.get("username", "unknown")

        if xlsx_path is None:
            errors.append(f"Missing xlsx_path for user {username}")
            continue

        source_files += 1

        try:
            # Validate file exists
            if not xlsx_path.exists():
                errors.append(f"File not found: {xlsx_path}")
                print(f"    [WARN] File not found: {xlsx_path}")
                continue

            wb = safe_load_workbook(xlsx_path)

            for sheet_name in wb.sheetnames:
                if sheet_name == "STATUS":
                    continue

                try:
                    ws = wb[sheet_name]

                    # Check for empty sheet
                    if ws.max_row is None or ws.max_row < 2:
                        continue

                    # Find columns by NAME (not position!)
                    status_col = find_column_by_header(ws, SCRIPT_COLS.get("status", "STATUS"))
                    text_col = find_column_by_header(ws, SCRIPT_COLS.get("translation", "Text"))
                    eventname_col = find_column_by_header(ws, SCRIPT_COLS.get("stringid", "EventName"))
                    memo_col = find_column_by_header(ws, SCRIPT_COLS.get("comment", "MEMO"))

                    if not status_col or not text_col or not eventname_col:
                        # Not a script sheet - skip silently
                        continue

                    # Scan rows for those with STATUS
                    # SIMPLE APPROACH: If STATUS has ANY value (not empty), include the row
                    # Don't be overly strict about what the status value is - if a tester
                    # touched the row (put anything in STATUS), we want to process it.
                    for row in range(2, ws.max_row + 1):
                        try:
                            status_val = ws.cell(row=row, column=status_col).value
                            if not status_val:
                                continue

                            # Just check if STATUS has any non-empty value
                            status_str = str(status_val).strip()
                            if not status_str:
                                continue

                            # This row has a status value - add to universe
                            eventname = str(ws.cell(row=row, column=eventname_col).value or "").strip()
                            text = str(ws.cell(row=row, column=text_col).value or "").strip()

                            if not eventname and not text:
                                continue

                            key = (eventname, text)

                            # Store row data (first occurrence wins, but track all sources)
                            if key not in universe:
                                universe[key] = {
                                    "eventname": eventname,
                                    "text": text,
                                    "sheet": sheet_name,
                                    "sources": [(username, xlsx_path, sheet_name, row)],
                                }
                            else:
                                # Track additional sources for debugging
                                universe[key]["sources"].append((username, xlsx_path, sheet_name, row))

                        except Exception as row_err:
                            err_msg = f"Error reading row {row} in {xlsx_path.name}/{sheet_name}: {row_err}"
                            errors.append(err_msg)
                            # Continue processing other rows

                except Exception as sheet_err:
                    err_msg = f"Error processing sheet '{sheet_name}' in {xlsx_path.name}: {sheet_err}"
                    errors.append(err_msg)
                    print(f"    [WARN] {err_msg}")
                    # Continue with other sheets

            wb.close()

        except Exception as e:
            err_msg = f"Error preprocessing {xlsx_path.name}: {type(e).__name__}: {e}"
            errors.append(err_msg)
            print(f"    [ERROR] {err_msg}")
            traceback.print_exc()
            # Continue with other files

    print(f"  [PREPROCESS] Found {len(universe)} unique rows with STATUS from {source_files} files")
    if errors:
        print(f"  [PREPROCESS] Encountered {len(errors)} error(s) during preprocessing")

    return {
        "rows": universe,
        "row_count": len(universe),
        "source_files": source_files,
        "errors": errors,
    }


def _safe_get_color_rgb(color_obj) -> str:
    """
    Safely extract RGB color string from an openpyxl color object.

    Handles various color types:
    - RGB colors (string like "FFFFFF")
    - Indexed colors (integer)
    - None values
    - Theme colors

    Args:
        color_obj: An openpyxl Color object

    Returns:
        RGB string (e.g., "FFFFFF") or "FFFFFF" as fallback
    """
    if color_obj is None:
        return "FFFFFF"

    rgb = getattr(color_obj, 'rgb', None)

    # rgb can be None
    if rgb is None:
        return "FFFFFF"

    # rgb can be an integer (indexed color) - just use white
    if isinstance(rgb, int):
        return "FFFFFF"

    # rgb can be a string - validate it's a valid hex color
    if isinstance(rgb, str):
        # Some colors start with "00" for alpha channel
        if len(rgb) == 8:
            return rgb[2:]  # Strip alpha channel
        elif len(rgb) == 6:
            return rgb
        else:
            return "FFFFFF"

    # Unknown type - fallback
    return "FFFFFF"


def create_filtered_script_template(
    template_path: Path,
    universe: Dict,
    output_path: Path = None
) -> Path:
    """
    Create a filtered template workbook containing ONLY rows from the universe.

    This creates a temporary workbook that will be used as the master template,
    containing only rows that have been checked by at least one tester.

    IMPORTANT: Preserves FULL row data from source files (all columns), not just
    the columns used for matching. Uses the most recent file for column structure.

    Args:
        template_path: Path to a QA file to use as structure template
        universe: Dict from preprocess_script_category() with "rows" key
        output_path: Optional output path (default: temp file)

    Returns:
        Path to the filtered template workbook

    Raises:
        Exception: Re-raises any exception after printing full traceback
    """
    import traceback
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    # SCRIPT_COLS already imported from config at module level
    import tempfile

    try:
        # Load template for structure (column headers)
        print(f"  [FILTERED TEMPLATE] Loading template: {template_path.name}")
        template_wb = safe_load_workbook(template_path)
    except Exception as e:
        print(f"  [ERROR] Failed to load template workbook: {template_path}")
        print(f"  [ERROR] Exception: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

    try:
        # Create new filtered workbook
        filtered_wb = Workbook()
        # Remove default sheet
        if "Sheet" in filtered_wb.sheetnames:
            del filtered_wb["Sheet"]

        rows_data = universe.get("rows", {})

        if not rows_data:
            print(f"  [WARN] Universe is empty - no rows to filter")

        # Group rows by sheet name
        rows_by_sheet = {}
        for key, data in rows_data.items():
            sheet = data.get("sheet", "Script")
            if sheet not in rows_by_sheet:
                rows_by_sheet[sheet] = []
            rows_by_sheet[sheet].append(data)

        # Cache of loaded source workbooks (avoid reloading same file multiple times)
        source_wb_cache = {}

        def get_source_row_data(sources, sheet_name, num_cols):
            """
            Fetch full row data from source file.
            Returns list of cell values for all columns.
            """
            if not sources:
                return None

            # Use first source (username, xlsx_path, sheet_name, row)
            username, xlsx_path, src_sheet, src_row = sources[0]
            xlsx_path = Path(xlsx_path) if not isinstance(xlsx_path, Path) else xlsx_path

            # Load from cache or open new
            cache_key = str(xlsx_path)
            if cache_key not in source_wb_cache:
                try:
                    source_wb_cache[cache_key] = safe_load_workbook(xlsx_path)
                except Exception as e:
                    print(f"    WARN: Could not load source {xlsx_path.name}: {e}")
                    return None

            wb = source_wb_cache[cache_key]
            if src_sheet not in wb.sheetnames:
                return None

            ws = wb[src_sheet]
            # Get all cell values for this row
            row_values = []
            for col in range(1, num_cols + 1):
                row_values.append(ws.cell(row=src_row, column=col).value)
            return row_values

        # Process each sheet from template
        for sheet_name in template_wb.sheetnames:
            if sheet_name == "STATUS":
                continue

            try:
                template_ws = template_wb[sheet_name]
                num_cols = template_ws.max_column

                if num_cols == 0 or num_cols is None:
                    print(f"    [SKIP] Sheet '{sheet_name}' has no columns")
                    continue

                # Create filtered sheet
                filtered_ws = filtered_wb.create_sheet(sheet_name)

                # Copy header row (row 1) with all columns and styles
                # Use try/except for each cell to avoid one bad cell breaking the whole sheet
                for col in range(1, num_cols + 1):
                    try:
                        src_cell = template_ws.cell(row=1, column=col)
                        dst_cell = filtered_ws.cell(row=1, column=col)
                        dst_cell.value = src_cell.value

                        # Copy styles - but don't fail if styling fails
                        if src_cell.has_style:
                            try:
                                # Copy font (safe - most properties are simple types)
                                dst_cell.font = Font(
                                    bold=src_cell.font.bold if src_cell.font.bold else False,
                                    color=src_cell.font.color,
                                    size=src_cell.font.size if src_cell.font.size else 11
                                )
                            except Exception as font_err:
                                pass  # Font copy failed - not critical

                            try:
                                # Copy fill - this is where errors commonly occur
                                if src_cell.fill and src_cell.fill.patternType and src_cell.fill.patternType != 'none':
                                    start_rgb = _safe_get_color_rgb(src_cell.fill.start_color)
                                    end_rgb = _safe_get_color_rgb(src_cell.fill.end_color)
                                    dst_cell.fill = PatternFill(
                                        start_color=start_rgb,
                                        end_color=end_rgb,
                                        fill_type=src_cell.fill.fill_type if src_cell.fill.fill_type else "solid"
                                    )
                            except Exception as fill_err:
                                pass  # Fill copy failed - not critical

                            try:
                                # Copy alignment
                                dst_cell.alignment = Alignment(
                                    horizontal=src_cell.alignment.horizontal,
                                    vertical=src_cell.alignment.vertical,
                                    wrap_text=src_cell.alignment.wrap_text if src_cell.alignment.wrap_text else False
                                )
                            except Exception as align_err:
                                pass  # Alignment copy failed - not critical

                    except Exception as cell_err:
                        print(f"    [WARN] Error copying header cell {col} in sheet '{sheet_name}': {cell_err}")

                # Find column positions in template for matching
                text_col = find_column_by_header(template_ws, SCRIPT_COLS.get("translation", "Text"))
                eventname_col = find_column_by_header(template_ws, SCRIPT_COLS.get("stringid", "EventName"))

                if not text_col or not eventname_col:
                    print(f"    [SKIP] Sheet '{sheet_name}' missing required columns (Text or EventName)")
                    continue

                # Build index of rows in template (by key) for quick lookup
                template_rows = {}
                max_row = template_ws.max_row
                if max_row is None or max_row < 2:
                    print(f"    [SKIP] Sheet '{sheet_name}' has no data rows")
                    continue

                for row in range(2, max_row + 1):
                    try:
                        eventname = str(template_ws.cell(row=row, column=eventname_col).value or "").strip()
                        text = str(template_ws.cell(row=row, column=text_col).value or "").strip()
                        key = (eventname, text)
                        if key not in template_rows:
                            template_rows[key] = row
                    except Exception as row_err:
                        print(f"    [WARN] Error reading template row {row} in sheet '{sheet_name}': {row_err}")

                # Copy only rows that are in the universe
                sheet_rows = rows_by_sheet.get(sheet_name, [])
                dst_row = 2
                rows_from_template = 0
                rows_from_source = 0

                for row_data in sheet_rows:
                    try:
                        key = (row_data["eventname"], row_data["text"])

                        # Try to find row in template first (most efficient)
                        src_row = template_rows.get(key)
                        if src_row:
                            # Copy entire row from template (ALL columns)
                            for col in range(1, num_cols + 1):
                                src_cell = template_ws.cell(row=src_row, column=col)
                                dst_cell = filtered_ws.cell(row=dst_row, column=col)
                                dst_cell.value = src_cell.value
                            dst_row += 1
                            rows_from_template += 1
                        else:
                            # Row not in template - fetch from source file
                            source_values = get_source_row_data(row_data.get("sources"), sheet_name, num_cols)
                            if source_values:
                                for col, value in enumerate(source_values, 1):
                                    filtered_ws.cell(row=dst_row, column=col).value = value
                                rows_from_source += 1
                            else:
                                # Fallback: create minimal row with just key columns
                                filtered_ws.cell(row=dst_row, column=eventname_col).value = row_data["eventname"]
                                filtered_ws.cell(row=dst_row, column=text_col).value = row_data["text"]
                            dst_row += 1
                    except Exception as copy_err:
                        print(f"    [WARN] Error copying row data for key {row_data.get('eventname', '?')}: {copy_err}")
                        dst_row += 1  # Still increment to avoid getting stuck

                # Set column widths
                for col in range(1, num_cols + 1):
                    try:
                        col_letter = filtered_ws.cell(row=1, column=col).column_letter
                        filtered_ws.column_dimensions[col_letter].width = 20
                    except Exception:
                        pass  # Column width is not critical

                if rows_from_source > 0:
                    print(f"    Sheet '{sheet_name}': {rows_from_template} from template, {rows_from_source} from source files")

            except Exception as sheet_err:
                print(f"    [ERROR] Failed to process sheet '{sheet_name}': {sheet_err}")
                traceback.print_exc()
                # Continue with other sheets

        # Close cached source workbooks
        for wb in source_wb_cache.values():
            try:
                wb.close()
            except:
                pass

        template_wb.close()

        # Save to temp file or specified path
        if output_path is None:
            fd, temp_path = tempfile.mkstemp(suffix=".xlsx", prefix="filtered_script_")
            output_path = Path(temp_path)
            import os
            os.close(fd)

        try:
            filtered_wb.save(output_path)
            filtered_wb.close()
            print(f"  [PREPROCESS] Created filtered template with {len(rows_data)} rows: {output_path.name}")
        except Exception as save_err:
            print(f"  [ERROR] Failed to save filtered template: {save_err}")
            traceback.print_exc()
            raise

        return output_path

    except Exception as e:
        print(f"  [ERROR] create_filtered_script_template failed:")
        print(f"  [ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        raise


# =============================================================================
# CATEGORY PROCESSING
# =============================================================================

def process_category(
    category: str,
    qa_folders: List[Dict],
    master_folder: Path,
    images_folder: Path,
    lang_label: str,
    manager_status: Dict = None,
    rebuild: bool = True,
    fixed_screenshots: set = None
) -> List[Dict]:
    """
    Process all QA folders for one category.

    Args:
        category: Category name (Quest, Knowledge, etc.)
        qa_folders: List of folder dicts from discovery
        master_folder: Target Master folder (EN or CN)
        images_folder: Target Images folder
        lang_label: "EN" or "CN"
        manager_status: Pre-collected manager status to restore
        rebuild: If True, rebuild master. If False, append (for clustering)
        fixed_screenshots: Set of screenshot filenames to skip (FIXED optimization)

    Returns:
        List of daily_entry dicts for tracker
    """
    if manager_status is None:
        manager_status = {}
    if fixed_screenshots is None:
        fixed_screenshots = set()

    target_master = get_target_master_category(category)
    cluster_info = f" -> Master_{target_master}" if target_master != category else ""

    print(f"\n{'='*50}")
    print(f"Processing: {category} [{lang_label}] ({len(qa_folders)} folders){cluster_info}")
    print(f"{'='*50}")

    daily_entries = []

    # Determine if EN or CN for word counting
    is_english = (lang_label == "EN")

    # Get or create master (use most recent file as template for freshest structure)
    sorted_by_mtime = sorted(qa_folders, key=lambda x: x["xlsx_path"].stat().st_mtime, reverse=True)
    template_xlsx = sorted_by_mtime[0]["xlsx_path"]
    template_user = sorted_by_mtime[0]["username"]

    # OPTIMIZATION: For Script-type categories (Sequencer/Dialog), preprocess to filter
    # out rows without STATUS. This dramatically speeds up processing for large files.
    filtered_template_path = None
    if category.lower() in SCRIPT_TYPE_CATEGORIES:
        print(f"  [OPTIMIZATION] Script-type category detected - preprocessing...")
        universe = preprocess_script_category(qa_folders, is_english)

        if universe["row_count"] == 0:
            print(f"  [SKIP] No rows with STATUS found in any QA file")
            return daily_entries

        # Create filtered template containing only rows with STATUS
        filtered_template_path = create_filtered_script_template(
            template_xlsx, universe
        )
        template_xlsx = filtered_template_path
        print(f"  Template: FILTERED ({universe['row_count']} rows with STATUS)")
    else:
        print(f"  Template: {template_user} (most recent file)")

    master_wb, master_path = get_or_create_master(category, master_folder, template_xlsx, rebuild=rebuild)

    if master_wb is None:
        return daily_entries

    # EN Item category: Sort master sheets A-Z by ItemName(ENG) for consistent matching
    if category.lower() == "item" and lang_label == "EN":
        for sheet_name in master_wb.sheetnames:
            if sheet_name == "STATUS":
                continue
            ws = master_wb[sheet_name]
            sort_col = find_column_by_header(ws, "ItemName(ENG)")
            if sort_col:
                sort_worksheet_az(ws, sort_column=sort_col)
                print(f"    Sorted {sheet_name} by column {sort_col} (ItemName(ENG))")
            else:
                print(f"    WARNING: ItemName(ENG) column not found in {sheet_name}, skipping sort")

    # Track stats
    all_users = set()
    user_stats = defaultdict(lambda: {"total": 0, "issue": 0, "no_issue": 0, "blocked": 0, "korean": 0})
    user_wordcount = defaultdict(int)  # username -> word count (EN) or char count (CN)
    user_file_dates = {}  # username -> file modification date
    total_images = 0
    total_screenshots = 0

    # Get translation column for word counting (is_english already defined above)
    # For Script-type: will be found by NAME ("Text") per worksheet
    # For other categories: use position-based from config
    is_script_category = category.lower() in SCRIPT_TYPE_CATEGORIES
    trans_col_key = "eng" if is_english else "other"
    trans_col_default = TRANSLATION_COLS.get(category, {"eng": 2, "other": 3}).get(trans_col_key, 2)

    # Process each QA folder
    for qf in qa_folders:
        username = qf["username"]
        xlsx_path = qf["xlsx_path"]
        all_users.add(username)

        # Get file modification date for tracker
        file_mod_time = __import__('datetime').datetime.fromtimestamp(xlsx_path.stat().st_mtime)
        user_file_dates[username] = file_mod_time.strftime("%Y-%m-%d")

        print(f"\n  Processing: {username}")

        # Copy images FIRST to get mapping for screenshot links
        # Script-type categories (Sequencer/Dialog) have NO screenshots - skip image copying
        if category.lower() in SCRIPT_TYPE_CATEGORIES:
            image_mapping = {}
        else:
            image_mapping = copy_images_with_unique_names(qf, images_folder, skip_images=fixed_screenshots)
            total_images += len(image_mapping)

        # Load QA workbook
        qa_wb = safe_load_workbook(xlsx_path)

        # EN Item category: Sort QA workbook sheets A-Z for consistent matching
        if category.lower() == "item" and lang_label == "EN":
            for sheet_name in qa_wb.sheetnames:
                if sheet_name == "STATUS":
                    continue
                qa_ws = qa_wb[sheet_name]
                sort_col = find_column_by_header(qa_ws, "ItemName(ENG)")
                if sort_col:
                    sort_worksheet_az(qa_ws, sort_column=sort_col)

        # Process each sheet
        for sheet_name in qa_wb.sheetnames:
            if sheet_name == "STATUS":
                continue

            qa_ws = qa_wb[sheet_name]

            # Check if sheet exists in master
            if sheet_name not in master_wb.sheetnames:
                print(f"    WARN: Sheet '{sheet_name}' not in master, skipping")
                continue

            master_ws = master_wb[sheet_name]

            # Get manager status for this sheet
            sheet_manager_status = manager_status.get(sheet_name, {})

            # Process the sheet (creates user columns internally)
            # Uses content-based matching for robust row matching
            result = process_sheet(
                master_ws, qa_ws, username, category,
                is_english=is_english,
                image_mapping=image_mapping,
                xlsx_path=xlsx_path,
                manager_status=sheet_manager_status
            )

            # Accumulate stats from result["stats"]
            stats = result.get("stats", {})
            for key in ["issue", "no_issue", "blocked", "korean"]:
                user_stats[username][key] += stats.get(key, 0)
            user_stats[username]["total"] += stats.get("total", 0)
            total_screenshots += result.get("screenshots", 0)

            # Log match stats for debugging (content-based matching)
            match_stats = result.get("match_stats", {})
            manager_restored = result.get("manager_restored", 0)
            if match_stats.get("unmatched", 0) > 0:
                print(f"      [WARN] {sheet_name}: {match_stats['exact']} exact, {match_stats['fallback']} fallback, {match_stats['unmatched']} UNMATCHED")
            elif match_stats.get("fallback", 0) > 0:
                print(f"      {sheet_name}: {match_stats['exact']} exact, {match_stats['fallback']} fallback")
            # Log manager status restoration
            if manager_restored > 0:
                print(f"      [MANAGER] {sheet_name}: Restored {manager_restored} manager status entries")

            # Count words (EN) or characters (CN) from translation column
            # ONLY count rows where STATUS is filled (DONE rows)
            qa_status_col = find_column_by_header(qa_ws, "STATUS")

            # Script-type: find "Text" column by NAME (more robust)
            # Other categories: use position-based from config
            if is_script_category:
                trans_col = find_column_by_header(qa_ws, SCRIPT_COLS.get("translation", "Text"))
                if not trans_col:
                    trans_col = trans_col_default  # Fallback to position
            else:
                trans_col = trans_col_default

            for row in range(2, qa_ws.max_row + 1):
                if qa_status_col:
                    status_val = qa_ws.cell(row, qa_status_col).value
                    # Accept both "NO ISSUE" (standard) and "NON-ISSUE" (Script-type)
                    if not status_val or str(status_val).strip().upper() not in ["ISSUE", "NO ISSUE", "NON-ISSUE", "BLOCKED", "KOREAN"]:
                        continue  # Skip rows not marked as done
                cell_value = qa_ws.cell(row, trans_col).value
                if is_english:
                    user_wordcount[username] += count_words_english(cell_value)
                else:
                    user_wordcount[username] += count_chars_chinese(cell_value)

        qa_wb.close()

    # Create daily entry for tracker
    for username in all_users:
        stats = user_stats[username]
        file_mod_date = user_file_dates.get(username, __import__('datetime').datetime.now().strftime("%Y-%m-%d"))
        entry = {
            "date": file_mod_date,
            "user": username,
            "category": category,
            "lang": lang_label,
            "total_rows": stats["total"],
            "done": stats["issue"] + stats["no_issue"] + stats["blocked"] + stats["korean"],
            "issues": stats["issue"],
            "no_issue": stats["no_issue"],
            "blocked": stats["blocked"],
            "korean": stats["korean"],
            "word_count": user_wordcount[username],
        }
        print(f"    [DEBUG] daily_entry: {entry['date']} | {entry['user']} | {entry['category']} | done={entry['done']}, issues={entry['issues']}")
        daily_entries.append(entry)

    # Update STATUS sheet with user stats
    update_status_sheet(master_wb, all_users, dict(user_stats))

    # Apply word wrap and autofit FIRST (before hiding)
    # This way all columns get proper widths, even if hidden later
    # Bonus: if user unhides a column in Excel, it already looks good
    autofit_rows_with_wordwrap(master_wb)

    # THEN hide empty rows/sheets/columns (focus on issues)
    hidden_rows, hidden_sheets, hidden_columns = hide_empty_comment_rows(master_wb)

    # Save master
    master_wb.save(master_path)
    print(f"\n  Saved: {master_path}")
    if hidden_sheets:
        print(f"  Hidden sheets (no comments): {', '.join(hidden_sheets)}")
    if hidden_columns > 0:
        print(f"  Hidden: {hidden_columns} empty user columns (unhide in Excel if needed)")
    if hidden_rows > 0:
        print(f"  Hidden: {hidden_rows} rows with no comments (unhide in Excel if needed)")
    if total_images > 0:
        print(f"  Images: {total_images} copied to Images/, {total_screenshots} hyperlinks updated")

    # Cleanup: Remove filtered template temp file if it was created
    if filtered_template_path and filtered_template_path.exists():
        try:
            filtered_template_path.unlink()
            print(f"  [CLEANUP] Removed temp filtered template")
        except Exception as e:
            print(f"  [WARN] Could not remove temp file: {e}")

    return daily_entries


# =============================================================================
# MAIN COMPILER
# =============================================================================

def run_compiler():
    """
    Main compiler entry point.

    Discovers QA folders, routes by language, processes categories,
    and updates the progress tracker.
    """
    print("=" * 60)
    print("QA Excel Compiler (EN/CN Separation + Manager Status)")
    print("=" * 60)
    print("Features:")
    print("  - Folder-based input: QAfolder/{Username}_{Category}/")
    print("  - Language separation: Masterfolder_EN/ and Masterfolder_CN/")
    print("  - Auto-routing testers by language mapping")
    print("  - Manager workflow: STATUS_{User} for FIXED/REPORTED/CHECKING")
    print("  - Combined Progress Tracker at root level")
    print()

    # Load tester mapping
    print("Loading tester->language mapping...")
    tester_mapping = load_tester_mapping()

    # Ensure folders exist
    ensure_master_folders()

    # Preprocess: Collect manager status from existing Master files
    print("\nCollecting manager status from existing Master files...")
    manager_status_en = collect_manager_status(MASTER_FOLDER_EN)
    manager_status_cn = collect_manager_status(MASTER_FOLDER_CN)

    total_en = sum(sum(len(statuses) for statuses in sheets.values()) for sheets in manager_status_en.values())
    total_cn = sum(sum(len(statuses) for statuses in sheets.values()) for sheets in manager_status_cn.values())
    if total_en > 0 or total_cn > 0:
        print(f"  Found {total_en} EN + {total_cn} CN manager status entries to preserve")
    else:
        print("  No existing manager status entries found")

    # Collect FIXED screenshots to skip during image copy (optimization)
    print("\nCollecting FIXED screenshots to skip...")
    fixed_screenshots_en = collect_fixed_screenshots(MASTER_FOLDER_EN)
    fixed_screenshots_cn = collect_fixed_screenshots(MASTER_FOLDER_CN)
    total_fixed = len(fixed_screenshots_en) + len(fixed_screenshots_cn)
    if total_fixed > 0:
        print(f"  Found {len(fixed_screenshots_en)} EN + {len(fixed_screenshots_cn)} CN FIXED screenshots to skip")

    # Discover QA folders
    qa_folders = discover_qa_folders()

    if not qa_folders:
        print("\nNo valid QA folders found in QAfolder/")
        print("Expected format: QAfolder/{Username}_{Category}/")
        print("  - Each folder should contain one .xlsx file")
        print("  - Images should be in the same folder")
        print(f"Valid categories: {', '.join(CATEGORIES)}")
        return

    print(f"Found {len(qa_folders)} QA folder(s)")

    # Count images
    total_images = sum(len(qf["images"]) for qf in qa_folders)
    if total_images > 0:
        print(f"Total images to process: {total_images}")

    # Group by category AND language
    by_category_en, by_category_cn = group_folders_by_language(qa_folders, tester_mapping)

    # Process categories
    all_daily_entries = []

    # Track processed masters for clustering
    processed_masters_en = set()
    processed_masters_cn = set()

    # Process EN
    for category in CATEGORIES:
        if category in by_category_en:
            target_master = get_target_master_category(category)
            rebuild = target_master not in processed_masters_en
            processed_masters_en.add(target_master)

            category_manager_status = manager_status_en.get(category, {})
            entries = process_category(
                category, by_category_en[category],
                MASTER_FOLDER_EN, IMAGES_FOLDER_EN, "EN",
                category_manager_status, rebuild=rebuild,
                fixed_screenshots=fixed_screenshots_en
            )
            all_daily_entries.extend(entries)

    # Process CN
    for category in CATEGORIES:
        if category in by_category_cn:
            target_master = get_target_master_category(category)
            rebuild = target_master not in processed_masters_cn
            processed_masters_cn.add(target_master)

            category_manager_status = manager_status_cn.get(category, {})
            entries = process_category(
                category, by_category_cn[category],
                MASTER_FOLDER_CN, IMAGES_FOLDER_CN, "CN",
                category_manager_status, rebuild=rebuild,
                fixed_screenshots=fixed_screenshots_cn
            )
            all_daily_entries.extend(entries)

    # Show skipped categories
    for category in CATEGORIES:
        if category not in by_category_en and category not in by_category_cn:
            print(f"\nSKIP: No folders for category '{category}'")

    # Update Progress Tracker
    if all_daily_entries:
        print("\n" + "=" * 60)
        print("Updating LQA User Progress Tracker...")
        print("=" * 60)

        # Import tracker modules
        from tracker.data import get_or_create_tracker, update_daily_data_sheet
        from tracker.daily import build_daily_sheet
        from tracker.total import build_total_sheet

        # Collect manager stats for tracker
        manager_stats = collect_manager_stats_for_tracker()

        tracker_wb, tracker_path = get_or_create_tracker()
        update_daily_data_sheet(tracker_wb, all_daily_entries, manager_stats)
        build_daily_sheet(tracker_wb)
        build_total_sheet(tracker_wb)

        # Remove deprecated GRAPHS sheet
        if "GRAPHS" in tracker_wb.sheetnames:
            del tracker_wb["GRAPHS"]

        tracker_wb.save(tracker_path)

        print(f"  Saved: {tracker_path}")
        print(f"  Sheets: DAILY (with stats), TOTAL (with rankings)")

    print("\n" + "=" * 60)
    print("Compilation complete!")
    print(f"Output EN: {MASTER_FOLDER_EN}")
    print(f"Output CN: {MASTER_FOLDER_CN}")
    if all_daily_entries:
        print(f"Tracker: {TRACKER_PATH}")
    print("=" * 60)
