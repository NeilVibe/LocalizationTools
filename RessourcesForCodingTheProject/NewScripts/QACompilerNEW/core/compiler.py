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
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# =============================================================================
# GRANULAR DEBUG LOGGING
# =============================================================================

_COMPILER_LOG_FILE = Path(__file__).parent.parent / "COMPILER_DEBUG.log"
_COMPILER_LOG_ENABLED = False  # Set to True for verbose logging
_COMPILER_LOG_LINES = []  # Buffer for batch writing


def _compiler_log(msg: str, level: str = "INFO"):
    """Add message to compiler log buffer."""
    if not _COMPILER_LOG_ENABLED:
        return
    timestamp = datetime.now().strftime("%H:%M:%S")
    _COMPILER_LOG_LINES.append(f"[{timestamp}] [{level}] {msg}")


def _compiler_log_flush(header: str = None):
    """Flush log buffer to file."""
    global _COMPILER_LOG_LINES
    if not _COMPILER_LOG_LINES:
        return
    try:
        mode = "a" if _COMPILER_LOG_FILE.exists() else "w"
        with open(_COMPILER_LOG_FILE, mode, encoding="utf-8") as f:
            if header:
                f.write(f"\n{'='*60}\n{header}\n{'='*60}\n")
            f.write("\n".join(_COMPILER_LOG_LINES) + "\n")
        _COMPILER_LOG_LINES = []
    except Exception as e:
        print(f"[COMPILER LOG ERROR] {e}")


def _compiler_log_clear():
    """Clear log file for fresh run."""
    global _COMPILER_LOG_LINES
    _COMPILER_LOG_LINES = []
    try:
        with open(_COMPILER_LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"=== COMPILER DEBUG LOG === {datetime.now().isoformat()}\n\n")
    except:
        pass


# =============================================================================
# SCRIPT DEBUG LOGGING (for investigating Script manager status issue)
# =============================================================================

_SCRIPT_DEBUG_FILE = Path(__file__).parent.parent / "SCRIPT_DEBUG.log"
_SCRIPT_DEBUG_LINES = []


def _script_debug_log(msg: str):
    """Add message to Script debug log."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    _SCRIPT_DEBUG_LINES.append(f"[{timestamp}] {msg}")


def _script_debug_flush():
    """Flush Script debug log to file."""
    global _SCRIPT_DEBUG_LINES
    if not _SCRIPT_DEBUG_LINES:
        return
    try:
        mode = "a" if _SCRIPT_DEBUG_FILE.exists() else "w"
        with open(_SCRIPT_DEBUG_FILE, mode, encoding="utf-8") as f:
            f.write("\n".join(_SCRIPT_DEBUG_LINES) + "\n")
        _SCRIPT_DEBUG_LINES = []
    except Exception as e:
        print(f"[SCRIPT DEBUG ERROR] {e}")


def _script_debug_clear():
    """Clear Script debug log for fresh run."""
    global _SCRIPT_DEBUG_LINES
    _SCRIPT_DEBUG_LINES = []
    try:
        with open(_SCRIPT_DEBUG_FILE, "w", encoding="utf-8") as f:
            f.write(f"=== SCRIPT DEBUG LOG === {datetime.now().isoformat()}\n")
            f.write(f"Investigating why Script manager status is empty\n\n")
    except:
        pass


from config import (
    CATEGORIES, CATEGORY_TO_MASTER, TRANSLATION_COLS, SCRIPT_TYPE_CATEGORIES,
    SCRIPT_COLS, FACE_TYPE_CATEGORIES,
    MASTER_FOLDER_EN, MASTER_FOLDER_CN,
    IMAGES_FOLDER_EN, IMAGES_FOLDER_CN,
    TRACKER_PATH,
    load_tester_mapping, ensure_folders_exist,
    get_target_master_category,
    WORKER_GROUPS, MAX_PARALLEL_WORKERS
)
from core.discovery import discover_qa_folders, group_folders_by_language
from core.excel_ops import (
    safe_load_workbook, ensure_master_folders,
    get_or_create_master, copy_images_with_unique_names,
    find_column_by_header, sort_worksheet_az, build_column_map
)
from core.processing import (
    process_sheet, update_status_sheet,
    hide_empty_comment_rows, autofit_rows_with_wordwrap,
    count_words_english, count_chars_chinese
)
from core.matching import (
    build_master_index, clone_with_fresh_consumed, clear_master_index_cache
)


# Valid manager status values
VALID_MANAGER_STATUS = {"FIXED", "REPORTED", "CHECKING", "NON-ISSUE", "NON ISSUE"}

# Valid tester status values (rows with these are "done")
# NOTE: Script-type categories (Sequencer/Dialog) use "NON-ISSUE" (with hyphen)
# while other categories use "NO ISSUE" (with space). Accept both.
VALID_TESTER_STATUS = {"ISSUE", "NO ISSUE", "NON-ISSUE", "NON ISSUE", "BLOCKED", "KOREAN"}


# =============================================================================
# COMMENT TEXT EXTRACTION
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


# =============================================================================
# CONSOLIDATED MASTER DATA COLLECTION (Phase A optimization)
# =============================================================================
# Replaces 3 separate functions that each opened all master files independently:
#   - collect_fixed_screenshots()  -> fixed_screenshots set
#   - collect_manager_status()     -> manager_status dict
#   - collect_manager_stats_for_tracker() -> manager_stats dict
# Now: ONE pass per master file with read_only=True for all 3 data structures.

def collect_all_master_data(tester_mapping: Dict = None):
    """
    Single-pass collection of ALL master file data for compilation.

    Opens each master file ONCE with read_only=True, extracting:
    1. manager_status (EN/CN) - for preserving manager status during rebuild
    2. fixed_screenshots (EN/CN) - for skipping FIXED images during copy
    3. manager_stats - for tracker (FIXED/REPORTED/CHECKING/NON-ISSUE counts)

    Args:
        tester_mapping: Dict mapping tester names to language codes (EN/CN).
                        If None, loaded from file.

    Returns:
        Tuple of (manager_status_en, manager_status_cn,
                  fixed_screenshots_en, fixed_screenshots_cn,
                  manager_stats)
    """
    if tester_mapping is None:
        tester_mapping = load_tester_mapping()

    manager_status_en = {}
    manager_status_cn = {}
    fixed_screenshots_en = set()
    fixed_screenshots_cn = set()
    manager_stats = defaultdict(lambda: defaultdict(
        lambda: {"fixed": 0, "reported": 0, "checking": 0, "nonissue": 0, "lang": "EN"}
    ))

    # LOG FILE for manager stats debug
    log_path = Path(__file__).parent.parent / "MANAGER_STATS_DEBUG.log"
    L = []

    def log(msg, indent=0):
        L.append("  " * indent + msg)

    log(f"{'='*80}")
    log(f"CONSOLIDATED MASTER DATA COLLECTION (Phase A optimization)")
    log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{'='*80}")
    log("")
    log(f"[CONFIG] MASTER_FOLDER_EN: {MASTER_FOLDER_EN}")
    log(f"[CONFIG] MASTER_FOLDER_CN: {MASTER_FOLDER_CN}")
    log(f"[CONFIG] Tester mapping: {len(tester_mapping)} entries")
    log("")

    for master_folder in [MASTER_FOLDER_EN, MASTER_FOLDER_CN]:
        is_en = "EN" in str(master_folder)
        folder_label = "EN" if is_en else "CN"
        manager_status = manager_status_en if is_en else manager_status_cn
        fixed_screenshots = fixed_screenshots_en if is_en else fixed_screenshots_cn
        processed_masters = set()  # Avoid re-scanning clustered categories

        print(f"  [{folder_label}] Scanning master folder: {master_folder}")
        log(f"{'='*80}")
        log(f"PROCESSING FOLDER: {master_folder} [{folder_label}]")
        log(f"{'='*80}")

        if not master_folder.exists():
            print(f"  [{folder_label}] Folder does not exist - skipping")
            log(f"Folder does not exist - skipping")
            continue

        for category in CATEGORIES:
            target_category = get_target_master_category(category)
            master_path = master_folder / f"Master_{target_category}.xlsx"

            if master_path in processed_masters:
                # Already scanned this master (e.g., Sequencer+Dialog both -> Master_Script)
                # But still need to register the category in manager_status
                if master_path.exists() and category not in manager_status:
                    # Copy sheet data from the target_category that already has it
                    source_cat = target_category
                    if source_cat in manager_status:
                        manager_status[category] = manager_status[source_cat]
                continue

            if not master_path.exists():
                continue

            processed_masters.add(master_path)

            try:
                # read_only=True is 3-5x faster per open (Phase A optimization)
                print(f"    Opening: {master_path.name}...", end="", flush=True)
                wb = safe_load_workbook(master_path, read_only=True, data_only=True)
                print(f" {len(wb.sheetnames)} sheets")
                try:
                    log(f"")
                    log(f"{'~'*60}")
                    log(f"MASTER FILE: {master_path.name} [{folder_label}]")
                    log(f"{'~'*60}")
                    log(f"Sheets: {wb.sheetnames}")

                    # Initialize manager_status for ALL categories that map to this master
                    categories_for_master = [category]
                    for cat in CATEGORIES:
                        if cat != category and get_target_master_category(cat) == target_category:
                            categories_for_master.append(cat)

                    for cat in categories_for_master:
                        if cat not in manager_status:
                            manager_status[cat] = {}

                    sheets_processed = 0
                    total_rows_scanned = 0
                    for sheet_name in wb.sheetnames:
                        if sheet_name == "STATUS":
                            continue

                        ws = wb[sheet_name]

                        # In read_only mode, max_row/max_column can be None for empty sheets
                        if ws.max_row is None or ws.max_row < 2:
                            continue
                        if ws.max_column is None or ws.max_column < 1:
                            continue

                        # Initialize sheet in manager_status for all categories
                        for cat in categories_for_master:
                            if sheet_name not in manager_status[cat]:
                                manager_status[cat][sheet_name] = {}

                        # === HEADER SCAN via iter_rows (streaming, not random access) ===
                        stringid_col = None
                        comment_cols = {}          # username -> 0-based idx
                        status_cols = {}           # username -> 0-based idx (STATUS_{User} = manager status)
                        manager_comment_cols = {}  # username -> 0-based idx
                        screenshot_cols = {}       # username -> 0-based idx
                        tester_status_cols = {}    # username -> 0-based idx

                        # Read header row as tuple (single streaming read, not cell-by-cell)
                        header_iter = ws.iter_rows(min_row=1, max_row=1, max_col=ws.max_column, values_only=True)
                        header_tuple = next(header_iter, None)
                        if not header_tuple:
                            continue

                        stringid_idx = None  # 0-based index
                        for col_idx, header_val in enumerate(header_tuple):
                            if not header_val:
                                continue
                            header_str = str(header_val)
                            header_upper = header_str.upper()

                            if header_upper.startswith("STATUS_") and not header_upper.startswith("TESTER_STATUS_"):
                                status_cols[header_str[7:]] = col_idx
                            elif header_upper.startswith("COMMENT_"):
                                comment_cols[header_str[8:]] = col_idx
                            elif header_upper.startswith("MANAGER_COMMENT_"):
                                manager_comment_cols[header_str[16:]] = col_idx
                            elif header_upper.startswith("SCREENSHOT_"):
                                screenshot_cols[header_str[11:]] = col_idx
                            elif header_upper.startswith("TESTER_STATUS_"):
                                tester_status_cols[header_str[14:]] = col_idx
                            elif header_upper == "STRINGID":
                                stringid_idx = col_idx
                            elif header_upper == "EVENTNAME" and stringid_idx is None:
                                stringid_idx = col_idx

                        # DEBUG: Script category logging
                        is_script_cat = category.lower() in ("sequencer", "dialog")
                        if is_script_cat:
                            _script_debug_log(f"")
                            _script_debug_log(f"{'='*60}")
                            _script_debug_log(f"[COLLECT] {category}/{sheet_name}")
                            _script_debug_log(f"{'='*60}")
                            _script_debug_log(f"  STATUS_ columns: {list(status_cols.items())}")
                            _script_debug_log(f"  COMMENT_ columns: {list(comment_cols.items())}")
                            _script_debug_log(f"  STRINGID/EventName idx: {stringid_idx}")

                        if not status_cols:
                            if is_script_cat:
                                _script_debug_log(f"  [SKIP] No STATUS_ columns found")
                            continue

                        log(f"  [{sheet_name}] STATUS cols: {list(status_cols.keys())}")

                        # === SINGLE-PASS ROW SCAN via iter_rows (streaming tuples) ===
                        # CRITICAL: iter_rows is O(n) streaming vs ws.cell() which is O(n²) in read_only mode
                        script_debug_rows_stored = 0
                        script_debug_rows_skipped = 0
                        row_count = 0

                        for row_tuple in ws.iter_rows(min_row=2, max_col=ws.max_column, values_only=True):
                            row_count += 1
                            for username, status_idx in status_cols.items():
                                status_value = row_tuple[status_idx] if status_idx < len(row_tuple) else None
                                status_str = str(status_value).strip() if status_value else ""
                                status_upper = status_str.upper()

                                # Get manager comment for this user (tuple index)
                                mc_idx = manager_comment_cols.get(username)
                                mc_value = row_tuple[mc_idx] if mc_idx is not None and mc_idx < len(row_tuple) else None

                                has_status = status_upper in VALID_MANAGER_STATUS
                                has_manager_comment = mc_value and str(mc_value).strip()

                                # --- DATA 1: fixed_screenshots ---
                                if status_upper == "FIXED":
                                    sc_idx = screenshot_cols.get(username)
                                    if sc_idx is not None and sc_idx < len(row_tuple):
                                        sc_val = row_tuple[sc_idx]
                                        if sc_val and str(sc_val).strip():
                                            fixed_screenshots.add(str(sc_val).strip())

                                # --- DATA 2: manager_status ---
                                if has_status or has_manager_comment:
                                    # Get STRINGID (tuple index)
                                    stringid = ""
                                    if stringid_idx is not None and stringid_idx < len(row_tuple):
                                        sid_val = row_tuple[stringid_idx]
                                        if sid_val:
                                            stringid = str(sid_val).strip()

                                    # Get tester's comment text (tuple index)
                                    tester_comment_text = ""
                                    c_idx = comment_cols.get(username)
                                    if c_idx is not None and c_idx < len(row_tuple):
                                        full_comment = row_tuple[c_idx]
                                        tester_comment_text = extract_comment_text(full_comment)

                                    if tester_comment_text:
                                        script_debug_rows_stored += 1
                                        status_val_clean = status_upper if has_status else None
                                        mc_val_clean = str(mc_value).strip() if has_manager_comment else None
                                        user_entry = {"status": status_val_clean, "manager_comment": mc_val_clean}

                                        # Primary key + fallback key
                                        key = (stringid, tester_comment_text)
                                        fallback_key = ("", tester_comment_text)

                                        for cat in categories_for_master:
                                            sheet_dict = manager_status[cat][sheet_name]
                                            if key not in sheet_dict:
                                                sheet_dict[key] = {}
                                            sheet_dict[key][username] = user_entry

                                            if fallback_key not in sheet_dict:
                                                sheet_dict[fallback_key] = {}
                                            if username not in sheet_dict[fallback_key]:
                                                sheet_dict[fallback_key][username] = user_entry
                                    else:
                                        script_debug_rows_skipped += 1

                                # --- DATA 3: manager_stats (tracker counts) ---
                                # Reuse mc_value/comment from above (no duplicate cell read)
                                c_stats_idx = comment_cols.get(username)
                                comment_val = row_tuple[c_stats_idx] if c_stats_idx is not None and c_stats_idx < len(row_tuple) else None
                                comment_str_val = str(comment_val).strip() if comment_val else ""
                                has_comment = bool(comment_str_val)

                                if has_status or has_comment:
                                    if has_status:
                                        if status_upper == "FIXED":
                                            manager_stats[target_category][username]["fixed"] += 1
                                        elif status_upper == "REPORTED":
                                            manager_stats[target_category][username]["reported"] += 1
                                        elif status_upper == "CHECKING":
                                            manager_stats[target_category][username]["checking"] += 1
                                        elif status_upper in ("NON-ISSUE", "NON ISSUE"):
                                            manager_stats[target_category][username]["nonissue"] += 1

                                    manager_stats[target_category][username]["lang"] = tester_mapping.get(username, "EN")

                        # Debug logging for Script categories
                        if is_script_cat:
                            for cat in categories_for_master:
                                entries_count = len(manager_status[cat].get(sheet_name, {}))
                                _script_debug_log(f"  [SUMMARY] {cat}/{sheet_name}: {entries_count} keys stored, {script_debug_rows_skipped} skipped (no comment)")
                            _script_debug_flush()

                        log(f"    Stored {script_debug_rows_stored} manager_status entries, skipped {script_debug_rows_skipped}")
                        sheets_processed += 1
                        total_rows_scanned += row_count
                        print(f"      {sheet_name}: {row_count} rows, {script_debug_rows_stored} status entries")

                    print(f"    Done: {sheets_processed} sheets, {total_rows_scanned} rows scanned")

                finally:
                    wb.close()

            except Exception as e:
                import traceback as tb
                log(f"[ERROR] Failed to process {master_path}: {e}")
                log(f"[TRACEBACK] {tb.format_exc()}")
                print(f"\n  WARN: Error reading {master_path.name}: {e}")

    # Convert manager_stats defaultdicts to regular dicts
    manager_stats_result = {}
    for cat, users_dd in manager_stats.items():
        manager_stats_result[cat] = {}
        for user, stats_dd in users_dd.items():
            manager_stats_result[cat][user] = dict(stats_dd)

    # Log final summary
    log("")
    log(f"{'='*80}")
    log(f"FINAL SUMMARY")
    log(f"{'='*80}")
    log(f"manager_status_en categories: {list(manager_status_en.keys())}")
    log(f"manager_status_cn categories: {list(manager_status_cn.keys())}")
    log(f"fixed_screenshots_en: {len(fixed_screenshots_en)}")
    log(f"fixed_screenshots_cn: {len(fixed_screenshots_cn)}")
    log(f"manager_stats categories: {list(manager_stats_result.keys())}")
    for cat, users in manager_stats_result.items():
        log(f"  {cat}:")
        for user, stats in users.items():
            log(f"    {user}: F={stats['fixed']} R={stats['reported']} C={stats['checking']} N={stats['nonissue']} lang={stats['lang']}")
    log(f"{'='*80}")

    # Write log file
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(L))
        print(f"[LOG] Master data collection ({len(L)} lines): {log_path}")
    except Exception as e:
        print(f"[LOG ERROR] {e}")

    # Script debug summary
    for cat in ["Sequencer", "Dialog"]:
        if cat in manager_status_en:
            total_keys = sum(len(sd) for sd in manager_status_en[cat].values())
            _script_debug_log(f"[COLLECT TOTAL] {cat} EN: {total_keys} keys")
        if cat in manager_status_cn:
            total_keys = sum(len(sd) for sd in manager_status_cn[cat].values())
            _script_debug_log(f"[COLLECT TOTAL] {cat} CN: {total_keys} keys")
    _script_debug_flush()

    return (manager_status_en, manager_status_cn,
            fixed_screenshots_en, fixed_screenshots_cn,
            manager_stats_result)


# =============================================================================
# SCRIPT-TYPE PREPROCESSING (Sequencer/Dialog optimization)
# =============================================================================

def preprocess_script_category(
    qa_folders: List[Dict],
    is_english: bool = True
) -> Dict:
    """
    Preprocess Script-type category files to build global universe of rows WITH status.

    Phase B enhancement: Also stores full_row data and sheet headers so that
    build_master_from_universe() can create the master workbook directly in memory
    without needing create_filtered_script_template().

    Args:
        qa_folders: List of folder dicts from discovery (all for this category)
        is_english: Whether these are English files

    Returns:
        Dict with:
            - "rows": {(eventname, text): row_data} - all unique rows with status
            - "row_count": int - total rows with status
            - "source_files": int - number of files scanned
            - "errors": List of error messages encountered
            - "headers": {sheet_name: [header1, header2, ...]} - per-sheet headers
            - "num_columns": {sheet_name: int} - column count per sheet
    """
    import traceback
    # SCRIPT_COLS already imported from config at module level

    universe = {}  # (eventname, text) -> row_data
    headers = {}   # sheet_name -> [header values]
    num_columns = {}  # sheet_name -> int
    source_files = 0
    errors = []  # Track errors for debugging

    print(f"  [PREPROCESS] Scanning {len(qa_folders)} QA files for rows with STATUS...")

    if not qa_folders:
        print(f"    [WARN] No QA folders provided")
        return {"rows": {}, "row_count": 0, "source_files": 0, "errors": ["No QA folders provided"],
                "headers": {}, "num_columns": {}}

    for qf_idx, qf in enumerate(qa_folders, 1):
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

            # read_only=True is 3-5x faster for large files
            print(f"    [{qf_idx}/{len(qa_folders)}] {username}...", end="", flush=True)
            wb = safe_load_workbook(xlsx_path, read_only=True, data_only=True)

            for sheet_name in wb.sheetnames:
                if sheet_name == "STATUS":
                    continue

                try:
                    ws = wb[sheet_name]

                    # Check for empty sheet
                    if ws.max_row is None or ws.max_row < 2:
                        continue
                    if ws.max_column is None or ws.max_column < 1:
                        continue

                    # Find columns by NAME using streaming header scan (not ws.cell!)
                    # In read_only mode, ws.cell() re-parses XML; build_column_map uses iter_rows
                    col_map = build_column_map(ws)

                    status_col = col_map.get("STATUS")
                    # Translation: try "Text" first, then "Translation"
                    text_col = col_map.get("TEXT") or col_map.get("TRANSLATION")
                    # Unique ID: try "EventName" first, then "STRINGID"
                    eventname_col = col_map.get("EVENTNAME") or col_map.get("STRINGID")
                    # Comment: try "MEMO" first, then "COMMENT"
                    memo_col = col_map.get("MEMO") or col_map.get("COMMENT")

                    if not status_col or not text_col or not eventname_col:
                        # Not a script sheet - skip silently
                        continue

                    total_cols = ws.max_column

                    # Collect sheet structure from first file encountered per sheet
                    # (Phase B: needed for build_master_from_universe)
                    # Use iter_rows for streaming header read (not ws.cell!)
                    if sheet_name not in headers:
                        header_iter = ws.iter_rows(min_row=1, max_row=1, max_col=total_cols, values_only=True)
                        header_tuple = next(header_iter, None)
                        headers[sheet_name] = list(header_tuple) if header_tuple else []
                        num_columns[sheet_name] = total_cols

                    # Scan rows using iter_rows for batch reading (Phase C3)
                    status_idx = status_col - 1
                    eventname_idx = eventname_col - 1
                    text_idx = text_col - 1

                    for row_idx, row_tuple in enumerate(
                        ws.iter_rows(min_row=2, max_col=total_cols, values_only=True),
                        start=2
                    ):
                        try:
                            # Pad row_tuple if shorter than total_cols (can happen with sparse data)
                            if len(row_tuple) <= status_idx:
                                continue

                            status_val = row_tuple[status_idx]
                            if not status_val:
                                continue

                            status_str = str(status_val).strip()
                            if not status_str:
                                continue

                            # This row has a status value - add to universe
                            eventname = str(row_tuple[eventname_idx] or "").strip() if eventname_idx < len(row_tuple) else ""
                            text = str(row_tuple[text_idx] or "").strip() if text_idx < len(row_tuple) else ""

                            if not eventname and not text:
                                continue

                            key = (eventname, text)

                            # Store row data with full_row (Phase B: for direct master building)
                            # Convert tuple to list for storage
                            full_row = list(row_tuple)

                            if key not in universe:
                                universe[key] = {
                                    "eventname": eventname,
                                    "text": text,
                                    "sheet": sheet_name,
                                    "sources": [(username, xlsx_path, sheet_name, row_idx)],
                                    "full_row": full_row,
                                }
                            else:
                                # Track additional sources for debugging
                                universe[key]["sources"].append((username, xlsx_path, sheet_name, row_idx))

                        except Exception as row_err:
                            err_msg = f"Error reading row {row_idx} in {xlsx_path.name}/{sheet_name}: {row_err}"
                            errors.append(err_msg)

                except Exception as sheet_err:
                    err_msg = f"Error processing sheet '{sheet_name}' in {xlsx_path.name}: {sheet_err}"
                    errors.append(err_msg)
                    print(f"    [WARN] {err_msg}")

            file_rows = sum(1 for _ in universe.values() if any(s[0] == username for s in _.get("sources", [])))
            print(f" {len(wb.sheetnames)} sheets")
            wb.close()

        except Exception as e:
            err_msg = f"Error preprocessing {xlsx_path.name}: {type(e).__name__}: {e}"
            errors.append(err_msg)
            print(f"\n    [ERROR] {err_msg}")
            traceback.print_exc()

    print(f"  [PREPROCESS] Found {len(universe)} unique rows with STATUS from {source_files} files")
    if errors:
        print(f"  [PREPROCESS] Encountered {len(errors)} error(s) during preprocessing")

    return {
        "rows": universe,
        "row_count": len(universe),
        "source_files": source_files,
        "errors": errors,
        "headers": headers,
        "num_columns": num_columns,
    }


def build_master_from_universe(
    category: str,
    universe: Dict,
    master_folder: Path
):
    """
    Build master workbook directly from universe data (Phase B optimization).

    Creates the master workbook in memory from preprocessed data, eliminating
    the create_filtered_script_template() bottleneck which:
    - Opened template in FULL mode
    - Scanned ALL 10K rows to build index
    - Opened source files AGAIN
    - Wrote temp file to disk
    - Temp file immediately re-loaded by get_or_create_master()

    This function replaces that entire pipeline with direct in-memory construction.

    Args:
        category: Category name (e.g., "Sequencer")
        universe: Dict from preprocess_script_category() with "rows", "headers", etc.
        master_folder: Target Master folder (EN or CN)

    Returns:
        Tuple of (Workbook, master_path) - same interface as get_or_create_master()
    """
    from openpyxl import Workbook as NewWorkbook

    target_category = get_target_master_category(category)
    master_path = master_folder / f"Master_{target_category}.xlsx"

    # Delete old master if it exists (rebuild mode)
    if master_path.exists():
        print(f"  Deleting old master: {master_path.name} (rebuilding fresh)")
        master_path.unlink()

    wb = NewWorkbook()
    # Remove default "Sheet"
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    rows_data = universe.get("rows", {})
    sheet_headers = universe.get("headers", {})
    sheet_num_cols = universe.get("num_columns", {})

    # Columns to DELETE from master (same as get_or_create_master):
    # STATUS, COMMENT, SCREENSHOT, STRINGID
    # These are tester columns that get replaced by user-specific columns
    COLS_TO_SKIP = {"STATUS", "COMMENT", "SCREENSHOT", "STRINGID"}

    # Group rows by sheet name
    rows_by_sheet = {}
    for key, data in rows_data.items():
        sheet = data.get("sheet", "Script")
        if sheet not in rows_by_sheet:
            rows_by_sheet[sheet] = []
        rows_by_sheet[sheet].append(data)

    # Build each sheet
    total_rows_written = 0
    for sheet_name in sheet_headers:
        raw_headers = sheet_headers[sheet_name]
        n_cols = sheet_num_cols.get(sheet_name, len(raw_headers))

        # Determine which column indices to KEEP (skip STATUS/COMMENT/SCREENSHOT/STRINGID)
        cols_to_keep = []  # list of (original_0based_idx, header_value)
        for idx, header_val in enumerate(raw_headers):
            header_upper = str(header_val).strip().upper() if header_val else ""
            if header_upper not in COLS_TO_SKIP:
                cols_to_keep.append((idx, header_val))

        if not cols_to_keep:
            continue

        ws = wb.create_sheet(sheet_name)

        # Write filtered headers
        for new_col, (orig_idx, header_val) in enumerate(cols_to_keep, 1):
            ws.cell(row=1, column=new_col, value=header_val)

        # Write data rows for this sheet
        sheet_rows = rows_by_sheet.get(sheet_name, [])
        dst_row = 2
        for row_data in sheet_rows:
            full_row = row_data.get("full_row")
            if full_row:
                for new_col, (orig_idx, _) in enumerate(cols_to_keep, 1):
                    if orig_idx < len(full_row):
                        ws.cell(row=dst_row, column=new_col, value=full_row[orig_idx])
                dst_row += 1
                total_rows_written += 1

    print(f"  [BUILD] Created master with {total_rows_written} rows across {len(rows_by_sheet)} sheets (in-memory)")

    # Clear AutoFilter on all sheets (safety measure)
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        if ws.auto_filter.ref:
            ws.auto_filter.ref = None

    return wb, master_path


def build_prefiltered_rows(universe: Dict, xlsx_path: Path, sheet_name: str, username: str) -> Optional[List[int]]:
    """
    Extract prefiltered row numbers from universe for a specific user/file/sheet.

    Phase C2 optimization: Avoids re-scanning STATUS column in process_sheet()
    by providing row numbers already known from preprocessing.

    Args:
        universe: Dict from preprocess_script_category()
        xlsx_path: Path to the QA file
        sheet_name: Sheet name to filter for
        username: Username to filter for

    Returns:
        Sorted list of row numbers, or None if not available
    """
    rows_data = universe.get("rows", {})
    if not rows_data:
        return None

    row_numbers = []
    xlsx_str = str(xlsx_path)

    for key, data in rows_data.items():
        for src_user, src_path, src_sheet, src_row in data.get("sources", []):
            if src_user == username and str(src_path) == xlsx_str and src_sheet == sheet_name:
                row_numbers.append(src_row)

    if not row_numbers:
        return None

    return sorted(set(row_numbers))


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
    fixed_screenshots: set = None,
    accumulated_users: set = None,
    accumulated_stats: Dict = None,
    deferred_save: bool = False
) -> Tuple[List[Dict], set, Dict, Optional[object], Optional[Path]]:
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
        accumulated_users: Set of users accumulated across categories sharing same master
        accumulated_stats: Dict of user stats accumulated across categories sharing same master
        deferred_save: If True, skip autofit/save and return workbook for caller to finalize

    Returns:
        Tuple of (daily_entries, accumulated_users, accumulated_stats, master_wb, master_path)
        - daily_entries: List of daily_entry dicts for tracker
        - accumulated_users: Updated set of all users for this master
        - accumulated_stats: Updated dict of user stats for this master
        - master_wb: The master workbook (None if deferred_save=False, i.e., already saved)
        - master_path: Path to master file
    """
    if manager_status is None:
        manager_status = {}
    if fixed_screenshots is None:
        fixed_screenshots = set()
    if accumulated_users is None:
        accumulated_users = set()
    if accumulated_stats is None:
        accumulated_stats = defaultdict(lambda: {"total": 0, "issue": 0, "no_issue": 0, "blocked": 0, "korean": 0})

    target_master = get_target_master_category(category)
    cluster_info = f" -> Master_{target_master}" if target_master != category else ""

    # SCRIPT DEBUG: Log when processing Script-type categories
    is_script_category = category.lower() in SCRIPT_TYPE_CATEGORIES
    if is_script_category:
        _script_debug_log(f"")
        _script_debug_log(f"{'='*60}")
        _script_debug_log(f"[PROCESS_CATEGORY] {category} [{lang_label}]")
        _script_debug_log(f"{'='*60}")
        _script_debug_log(f"  target_master: {target_master}")
        _script_debug_log(f"  qa_folders count: {len(qa_folders)}")
        for qf in qa_folders:
            _script_debug_log(f"    - {qf.get('username')}: {qf.get('xlsx_path')}")
        _script_debug_flush()

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

    # Use unified template-based master creation for ALL categories
    # This preserves ALL template rows (including REPORTED issues that may not have
    # STATUS in current QA files). The old Script-specific "universe" method that
    # rebuilt from scratch was causing data loss when testers cleared STATUS.
    #
    # NOTE: Script-type categories (Sequencer/Dialog) previously used a separate
    # preprocess_script_category() + build_master_from_universe() pipeline that
    # only kept rows WITH STATUS. This optimization caused REPORTED rows to be lost
    # when testers removed STATUS from their QA files. Now all categories use the
    # unified method which preserves data integrity while still being fast.
    print(f"  Template: {template_user} (most recent file)")
    master_wb, master_path = get_or_create_master(
        category, master_folder, template_xlsx,
        rebuild=rebuild,
        is_english=is_english
    )

    if master_wb is None:
        return daily_entries, accumulated_users, dict(accumulated_stats) if accumulated_stats else {}, None, None

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

    # Track stats - use accumulated data if provided (for clustered categories)
    all_users = accumulated_users
    user_stats = accumulated_stats
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

    # ==========================================================================
    # PERFORMANCE OPTIMIZATION: Build master indexes ONCE per sheet
    # ==========================================================================
    # Instead of rebuilding the index for each user (O(users × rows)),
    # build once and clone with fresh consumed set (O(rows) + O(users))
    # This gives 10x speedup for 10 users on same master sheet.
    master_indexes = {}  # sheet_name -> master_index
    for sheet_name in master_wb.sheetnames:
        if sheet_name == "STATUS":
            continue
        master_ws = master_wb[sheet_name]
        if master_ws.max_row and master_ws.max_row > 1:
            master_indexes[sheet_name] = build_master_index(master_ws, category, is_english)
    print(f"  Pre-built {len(master_indexes)} master indexes for O(1) matching")

    # Process each QA folder
    for qf in qa_folders:
        username = qf["username"]
        xlsx_path = qf["xlsx_path"]
        all_users.add(username)

        # Ensure user exists in user_stats (may be a regular dict from previous category)
        # This handles the case where accumulated_stats was converted from defaultdict to dict
        if username not in user_stats:
            user_stats[username] = {"total": 0, "issue": 0, "no_issue": 0, "blocked": 0, "korean": 0}

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
        # NOTE: All categories use standard mode (not read_only) because process_sheet()
        # and word-counting use ws.cell() random access which is O(n²) in read_only mode.
        # The 3-5x faster open from read_only is negligible vs the catastrophic per-row slowdown.
        print(f"    Loading workbook...", end="", flush=True)
        qa_wb = safe_load_workbook(xlsx_path)
        print(f" {len(qa_wb.sheetnames)} sheets")

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
            # NOTE: prefiltered_rows optimization removed - all categories now scan
            # all rows for STATUS, which is slightly slower but preserves data integrity
            # Uses content-based matching for robust row matching
            qa_rows = qa_ws.max_row - 1 if qa_ws.max_row and qa_ws.max_row > 1 else 0
            print(f"      {sheet_name}: {qa_rows} rows...", end="", flush=True)

            # OPTIMIZATION: Use pre-built index with fresh consumed set for each user
            # This avoids rebuilding the index for each user (10x speedup for 10 users)
            user_index = None
            if sheet_name in master_indexes:
                user_index = clone_with_fresh_consumed(master_indexes[sheet_name])

            result = process_sheet(
                master_ws, qa_ws, username, category,
                is_english=is_english,
                image_mapping=image_mapping,
                xlsx_path=xlsx_path,
                manager_status=sheet_manager_status,
                master_index=user_index
            )

            # Accumulate stats from result["stats"]
            # Defensive check: ensure user exists in user_stats (fixes KeyError for clustered categories)
            if username not in user_stats:
                user_stats[username] = {"total": 0, "issue": 0, "no_issue": 0, "blocked": 0, "korean": 0}
            stats = result.get("stats", {})
            for key in ["issue", "no_issue", "blocked", "korean"]:
                user_stats[username][key] += stats.get(key, 0)
            user_stats[username]["total"] += stats.get("total", 0)
            total_screenshots += result.get("screenshots", 0)

            # Log match stats for debugging (content-based matching)
            match_stats = result.get("match_stats", {})
            manager_restored = result.get("manager_restored", 0)
            matched = match_stats.get("exact", 0) + match_stats.get("fallback", 0)
            print(f" matched={matched}, issues={stats.get('issue', 0)}")
            if match_stats.get("unmatched", 0) > 0:
                print(f"        [WARN] {match_stats['exact']} exact, {match_stats['fallback']} fallback, {match_stats['unmatched']} UNMATCHED")
            elif match_stats.get("fallback", 0) > 0:
                print(f"        {match_stats['exact']} exact, {match_stats['fallback']} fallback")
            # Log manager status restoration
            if manager_restored > 0:
                print(f"      [MANAGER] {sheet_name}: Restored {manager_restored} manager status entries")

            # Count words (EN) or characters (CN) from translation column
            # ONLY count rows where STATUS is filled (DONE rows)
            qa_status_col = find_column_by_header(qa_ws, "STATUS")

            # Script-type: find "Text" or "Translation" by NAME (no position fallback!)
            # Other categories: use position-based from config
            if is_script_category:
                trans_col = find_column_by_header(qa_ws, "Text")
                if not trans_col:
                    trans_col = find_column_by_header(qa_ws, "Translation")
                if not trans_col:
                    # Skip word counting for this sheet - no Text/Translation column found
                    print(f"      {sheet_name}: SKIPPED word counting (no Text/Translation column)")
                    continue  # BUG FIX: This continue was missing, causing TypeError with None trans_col
            else:
                trans_col = trans_col_default

            wc_label = "words" if is_english else "chars"
            wc_before = user_wordcount[username]
            for row in range(2, qa_ws.max_row + 1):
                if qa_status_col:
                    status_val = qa_ws.cell(row, qa_status_col).value
                    # Accept all variants: "NO ISSUE", "NON-ISSUE", "NON ISSUE"
                    if not status_val or str(status_val).strip().upper() not in ["ISSUE", "NO ISSUE", "NON-ISSUE", "NON ISSUE", "BLOCKED", "KOREAN"]:
                        continue  # Skip rows not marked as done
                cell_value = qa_ws.cell(row, trans_col).value
                if is_english:
                    user_wordcount[username] += count_words_english(cell_value)
                else:
                    user_wordcount[username] += count_chars_chinese(cell_value)
            wc_added = user_wordcount[username] - wc_before
            if wc_added > 0:
                print(f"      {sheet_name}: {wc_added} {wc_label} counted")

        qa_wb.close()

    # Create daily entry for tracker
    for username in all_users:
        # Defensive check: ensure user exists (fixes potential KeyError for accumulated users)
        if username not in user_stats:
            user_stats[username] = {"total": 0, "issue": 0, "no_issue": 0, "blocked": 0, "korean": 0}
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

        # SCRIPT DEBUG: Detailed logging for Script-type categories
        if is_script_category:
            _script_debug_log(f"")
            _script_debug_log(f"[DAILY_ENTRY CREATED] {category}/{username}")
            _script_debug_log(f"  date: {file_mod_date}")
            _script_debug_log(f"  category: {category} (lookup will use: {target_master})")
            _script_debug_log(f"  total_rows: {stats['total']}")
            _script_debug_log(f"  done: {entry['done']} (issue={stats['issue']} + no_issue={stats['no_issue']} + blocked={stats['blocked']} + korean={stats['korean']})")
            _script_debug_log(f"  issues: {stats['issue']} <-- THIS IS THE TESTER ISSUE COUNT")
            _script_debug_log(f"  word_count: {user_wordcount[username]}")
            _script_debug_flush()

    # NOTE: STATUS sheet update is DEFERRED - caller will call update_status_sheet()
    # after all categories sharing this master have been processed. This prevents
    # clustered categories (e.g., Sequencer + Dialog -> Master_Script) from
    # overwriting each other's users in the STATUS sheet.

    if deferred_save:
        # DEFERRED SAVE: Return workbook for caller to finalize (autofit + save)
        # This enables running autofit ONCE per master after ALL categories processed
        print(f"\n  [DEFERRED] Skipping autofit/save - will be done in final pass")
        if total_images > 0:
            print(f"  Images: {total_images} copied to Images/, {total_screenshots} hyperlinks updated")
        return daily_entries, all_users, dict(user_stats), master_wb, master_path
    else:
        # IMMEDIATE SAVE: Apply word wrap and autofit FIRST (before hiding)
        # This way all columns get proper widths, even if hidden later
        # Bonus: if user unhides a column in Excel, it already looks good
        print(f"\n  Formatting: autofit columns and row heights...")
        autofit_rows_with_wordwrap(master_wb)

        # THEN hide empty rows/sheets/columns (focus on issues)
        print(f"  Optimizing: hiding empty rows/sheets/columns...")
        hidden_rows, hidden_sheets, hidden_columns = hide_empty_comment_rows(master_wb)

        # Save master
        print(f"  Saving master file...", end="", flush=True)
        master_wb.save(master_path)
        print(f" done")
        print(f"\n  Saved: {master_path}")
        if hidden_sheets:
            print(f"  Hidden sheets (no comments): {', '.join(hidden_sheets)}")
        if hidden_columns > 0:
            print(f"  Hidden: {hidden_columns} empty user columns (unhide in Excel if needed)")
        if hidden_rows > 0:
            print(f"  Hidden: {hidden_rows} rows with no comments (unhide in Excel if needed)")
        if total_images > 0:
            print(f"  Images: {total_images} copied to Images/, {total_screenshots} hyperlinks updated")

        return daily_entries, all_users, dict(user_stats), None, master_path


# =============================================================================
# MAIN COMPILER
# =============================================================================

def run_compiler():
    """
    Main compiler entry point.

    Discovers QA folders, routes by language, processes categories,
    and updates the progress tracker.
    """
    # Clear Script debug log for fresh run
    _script_debug_clear()
    _script_debug_log("=== STARTING FULL COMPILATION ===")
    _script_debug_flush()

    # Clear master index cache for fresh run
    clear_master_index_cache()

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

    # Preprocess: Collect ALL master data in single pass (Phase A optimization)
    # Opens each master file ONCE with read_only=True instead of 3 separate passes
    print("\nCollecting master data (manager status + fixed screenshots + tracker stats)...")
    (manager_status_en, manager_status_cn,
     fixed_screenshots_en, fixed_screenshots_cn,
     manager_stats) = collect_all_master_data(tester_mapping)

    total_en = sum(sum(len(statuses) for statuses in sheets.values()) for sheets in manager_status_en.values())
    total_cn = sum(sum(len(statuses) for statuses in sheets.values()) for sheets in manager_status_cn.values())
    if total_en > 0 or total_cn > 0:
        print(f"  Found {total_en} EN + {total_cn} CN manager status entries to preserve")
    else:
        print("  No existing manager status entries found")

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

    # ==========================================================================
    # EARLY OUTPUT: Generate MasterSubmitScript FIRST (quick - just ISSUE rows)
    # ==========================================================================
    # This runs BEFORE heavy Master file processing so output is available early
    print("\n" + "=" * 60)
    print("STEP 1: Generating MasterSubmitScript (Quick Output)")
    print("=" * 60)

    from core.export_index import get_soundevent_mapping
    from core.submit_script import collect_issue_rows, generate_master_submit_script, generate_conflict_file

    export_mapping = get_soundevent_mapping()
    print(f"  EXPORT mapping: {len(export_mapping)} EventName entries loaded")

    # EN: Combine Sequencer + Dialog folders
    en_script_folders = []
    for cat in ["Sequencer", "Dialog"]:
        if cat in by_category_en:
            en_script_folders.extend(by_category_en[cat])

    if en_script_folders:
        print(f"\n[EN] Collecting from {len(en_script_folders)} Script files...")
        en_issues, en_conflicts = collect_issue_rows(en_script_folders, export_mapping)
        if en_issues:
            generate_master_submit_script(
                en_issues,
                MASTER_FOLDER_EN / "MasterSubmitScript_EN.xlsx",
                "EN"
            )
        else:
            print("    No ISSUE rows found for EN")
        if en_conflicts:
            generate_conflict_file(
                en_conflicts,
                MASTER_FOLDER_EN / "MasterSubmitScript_Conflicts_EN.xlsx",
                "EN"
            )
    else:
        print("\n[EN] No Script category files to process")

    # CN: Same pattern
    cn_script_folders = []
    for cat in ["Sequencer", "Dialog"]:
        if cat in by_category_cn:
            cn_script_folders.extend(by_category_cn[cat])

    if cn_script_folders:
        print(f"\n[CN] Collecting from {len(cn_script_folders)} Script files...")
        cn_issues, cn_conflicts = collect_issue_rows(cn_script_folders, export_mapping)
        if cn_issues:
            generate_master_submit_script(
                cn_issues,
                MASTER_FOLDER_CN / "MasterSubmitScript_CN.xlsx",
                "CN"
            )
        else:
            print("    No ISSUE rows found for CN")
        if cn_conflicts:
            generate_conflict_file(
                cn_conflicts,
                MASTER_FOLDER_CN / "MasterSubmitScript_Conflicts_CN.xlsx",
                "CN"
            )
    else:
        print("\n[CN] No Script category files to process")

    # ==========================================================================
    # STEP 2: Process Master Files (Heavy Processing)
    # ==========================================================================
    print("\n" + "=" * 60)
    print("STEP 2: Building Master Files (WORKER GROUP PARALLELISM)")
    print("=" * 60)

    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    # Thread-safe result collection
    results_lock = threading.Lock()

    def process_worker_group(group_name, categories, lang_label, by_category,
                             master_folder, images_folder, manager_status,
                             fixed_screenshots, tester_mapping_ref):
        """
        Process a worker group (categories sharing same master file).
        Categories within the group are processed SEQUENTIALLY (shared master).
        Returns (group_name, lang, daily_entries, master_status_data).
        """
        from core.face_processor import process_face_category

        daily_entries = []
        processed_masters = set()
        master_status_data = {}

        # Filter to categories that exist in this language
        active_categories = [c for c in categories if c in by_category]
        if not active_categories:
            return (group_name, lang_label, [], {})

        for category in active_categories:
            # Face category: custom processing pipeline
            if category.lower() in FACE_TYPE_CATEGORIES:
                entries = process_face_category(
                    by_category[category], master_folder, lang_label, tester_mapping_ref
                )
                daily_entries.extend(entries)
                continue

            target_master = get_target_master_category(category)
            rebuild = target_master not in processed_masters
            processed_masters.add(target_master)

            # Get or initialize accumulated data for this master
            if target_master not in master_status_data:
                master_status_data[target_master] = {
                    "users": set(),
                    "stats": defaultdict(lambda: {"total": 0, "issue": 0, "no_issue": 0, "blocked": 0, "korean": 0}),
                    "workbook": None,
                    "path": None,
                }
            data = master_status_data[target_master]
            acc_users = data["users"]
            acc_stats = data["stats"]

            category_manager_status = manager_status.get(category, {})
            entries, acc_users, acc_stats, master_wb, master_path = process_category(
                category, by_category[category],
                master_folder, images_folder, lang_label,
                category_manager_status, rebuild=rebuild,
                fixed_screenshots=fixed_screenshots,
                accumulated_users=acc_users,
                accumulated_stats=acc_stats,
                deferred_save=True
            )
            daily_entries.extend(entries)
            master_status_data[target_master]["users"] = acc_users
            master_status_data[target_master]["stats"] = acc_stats
            if master_wb is not None:
                master_status_data[target_master]["workbook"] = master_wb
                master_status_data[target_master]["path"] = master_path

        return (group_name, lang_label, daily_entries, master_status_data)

    # ==========================================================================
    # PARALLEL PROCESSING: Worker groups across EN + CN (up to MAX_PARALLEL_WORKERS)
    # ==========================================================================
    print(f"\n[PARALLEL] Worker group parallelism enabled")
    print(f"  Max workers: {MAX_PARALLEL_WORKERS}")
    print(f"  Worker groups: {len(WORKER_GROUPS)} per language")

    all_daily_entries = []
    master_status_data_en = {}
    master_status_data_cn = {}

    # Submit all worker groups for both languages
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS, thread_name_prefix="wg") as executor:
        futures = []

        # Submit EN worker groups
        for group_name, categories in WORKER_GROUPS.items():
            if any(c in by_category_en for c in categories):
                future = executor.submit(
                    process_worker_group,
                    group_name, categories, "EN", by_category_en,
                    MASTER_FOLDER_EN, IMAGES_FOLDER_EN,
                    manager_status_en, fixed_screenshots_en, tester_mapping
                )
                futures.append(future)

        # Submit CN worker groups
        for group_name, categories in WORKER_GROUPS.items():
            if any(c in by_category_cn for c in categories):
                future = executor.submit(
                    process_worker_group,
                    group_name, categories, "CN", by_category_cn,
                    MASTER_FOLDER_CN, IMAGES_FOLDER_CN,
                    manager_status_cn, fixed_screenshots_cn, tester_mapping
                )
                futures.append(future)

        print(f"  Submitted {len(futures)} worker tasks")

        # Collect results as they complete
        completed = 0
        for future in as_completed(futures):
            try:
                group_name, lang, entries, master_data = future.result()
                completed += 1

                with results_lock:
                    all_daily_entries.extend(entries)
                    if lang == "EN":
                        master_status_data_en.update(master_data)
                    else:
                        master_status_data_cn.update(master_data)

                if entries:
                    print(f"  [{lang}/{group_name}] Completed: {len(entries)} entries ({completed}/{len(futures)})")
            except Exception as e:
                print(f"  [ERROR] Worker failed: {e}")
                raise

    print(f"\n  All {len(futures)} workers completed")

    # ==========================================================================
    # FINAL PASS: STATUS sheet + autofit + hide + save (PARALLEL)
    # ==========================================================================
    # This is the DEFERRED SAVE optimization: instead of autofit+save after each
    # category, we do it once per master after ALL categories are processed.
    # Now also parallelized for additional speedup.
    print("\n" + "=" * 60)
    print("FINAL PASS: STATUS + autofit + save (PARALLEL)")
    print("=" * 60)

    def finalize_master(target_master, data, lang_label):
        """Finalize and save a single master file. Thread-safe."""
        users = data["users"]
        stats = data["stats"]
        wb = data["workbook"]
        path = data["path"]

        if wb is None or path is None:
            return None

        # 1. Update STATUS sheet
        if users:
            update_status_sheet(wb, users, dict(stats))

        # 2. Autofit
        autofit_rows_with_wordwrap(wb)

        # 3. Hide empty rows/sheets/columns
        hidden_rows, hidden_sheets, hidden_columns = hide_empty_comment_rows(wb)

        # 4. Save
        wb.save(path)

        return {
            "lang": lang_label,
            "master": target_master,
            "users": len(users),
            "hidden_rows": hidden_rows,
            "hidden_sheets": hidden_sheets,
            "hidden_columns": hidden_columns,
        }

    # Parallel finalize + save
    finalize_futures = []
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS, thread_name_prefix="save") as executor:
        for target_master, data in master_status_data_en.items():
            future = executor.submit(finalize_master, target_master, data, "EN")
            finalize_futures.append(future)

        for target_master, data in master_status_data_cn.items():
            future = executor.submit(finalize_master, target_master, data, "CN")
            finalize_futures.append(future)

        print(f"  Finalizing {len(finalize_futures)} master files in parallel...")

        for future in as_completed(finalize_futures):
            result = future.result()
            if result:
                lang = result["lang"]
                master = result["master"]
                users = result["users"]
                hidden_rows = result["hidden_rows"]
                hidden_cols = result["hidden_columns"]
                print(f"  [{lang}] Master_{master}: {users} users, {hidden_rows} rows hidden, saved")

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

        # manager_stats already collected by collect_all_master_data() above
        print("  Loading tracker workbook...")
        tracker_wb, tracker_path = get_or_create_tracker()

        # Separate Face entries (different schema) from standard entries
        standard_entries = [e for e in all_daily_entries if e.get("category") != "Face"]
        face_entries = [e for e in all_daily_entries if e.get("category") == "Face"]
        print(f"  Entries: {len(standard_entries)} standard, {len(face_entries)} face")

        # Update standard tracker tabs
        if standard_entries:
            print("  Writing daily data...")
            update_daily_data_sheet(tracker_wb, standard_entries, manager_stats)
        print("  Building DAILY sheet...")
        build_daily_sheet(tracker_wb)
        print("  Building TOTAL sheet...")
        build_total_sheet(tracker_wb)

        # Update Facial tracker tab (if Face entries exist)
        if face_entries:
            from tracker.facial import update_facial_data_sheet, build_facial_sheet
            print("  Writing facial data...")
            update_facial_data_sheet(tracker_wb, face_entries)
            print("  Building Facial sheet...")
            build_facial_sheet(tracker_wb)

        # Remove deprecated GRAPHS sheet
        if "GRAPHS" in tracker_wb.sheetnames:
            del tracker_wb["GRAPHS"]

        print("  Saving tracker...", end="", flush=True)
        tracker_wb.save(tracker_path)
        print(" done")

        print(f"  Saved: {tracker_path}")
        sheets_info = "DAILY (with stats), TOTAL (with rankings)"
        if face_entries:
            sheets_info += ", Facial (face animation)"
        print(f"  Sheets: {sheets_info}")

    print("\n" + "=" * 60)
    print("Compilation complete!")
    print(f"Output EN: {MASTER_FOLDER_EN}")
    print(f"Output CN: {MASTER_FOLDER_CN}")
    if all_daily_entries:
        print(f"Tracker: {TRACKER_PATH}")
    print("=" * 60)
