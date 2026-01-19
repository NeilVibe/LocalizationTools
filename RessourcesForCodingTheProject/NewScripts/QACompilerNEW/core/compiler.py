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
    CATEGORIES, CATEGORY_TO_MASTER, TRANSLATION_COLS,
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

    KEYED BY COMMENT TEXT for matching after rebuild.

    Args:
        master_folder: Which Master folder to scan (EN or CN)

    Returns:
        {category: {sheet_name: {comment_text: {user: {"status": val, "manager_comment": val}}}}}
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

                # Find all COMMENT_{User}, STATUS_{User}, and MANAGER_COMMENT_{User} columns
                comment_cols = {}          # username -> col (tester comment)
                status_cols = {}           # username -> col (manager status)
                manager_comment_cols = {}  # username -> col (manager comment)
                for col in range(1, ws.max_column + 1):
                    header = ws.cell(row=1, column=col).value
                    if header:
                        header_str = str(header)
                        if header_str.startswith("COMMENT_"):
                            username = header_str.replace("COMMENT_", "")
                            comment_cols[username] = col
                        elif header_str.startswith("STATUS_"):
                            username = header_str.replace("STATUS_", "")
                            status_cols[username] = col
                        elif header_str.startswith("MANAGER_COMMENT_"):
                            username = header_str.replace("MANAGER_COMMENT_", "")
                            manager_comment_cols[username] = col

                if not status_cols:
                    continue

                # Collect values per row, keyed by comment text
                for row in range(2, ws.max_row + 1):
                    for username, status_col in status_cols.items():
                        status_value = ws.cell(row=row, column=status_col).value
                        manager_comment_col = manager_comment_cols.get(username)
                        manager_comment_value = None
                        if manager_comment_col:
                            manager_comment_value = ws.cell(row=row, column=manager_comment_col).value

                        # Only store if there's a status or manager comment
                        has_status = status_value and str(status_value).strip().upper() in VALID_MANAGER_STATUS
                        has_manager_comment = manager_comment_value and str(manager_comment_value).strip()

                        if has_status or has_manager_comment:
                            comment_col = comment_cols.get(username)
                            if comment_col:
                                full_comment = ws.cell(row=row, column=comment_col).value
                                comment_text = extract_comment_text(full_comment)
                                if comment_text:
                                    if comment_text not in manager_status[category][sheet_name]:
                                        manager_status[category][sheet_name][comment_text] = {}
                                    manager_status[category][sheet_name][comment_text][username] = {
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

    Returns:
        {category: {user: {fixed, reported, checking, nonissue, lang}}}
    """
    tester_mapping = load_tester_mapping()
    manager_stats = defaultdict(lambda: defaultdict(
        lambda: {"fixed": 0, "reported": 0, "checking": 0, "nonissue": 0, "lang": "EN"}
    ))

    # Scan both EN and CN folders
    for master_folder in [MASTER_FOLDER_EN, MASTER_FOLDER_CN]:
        for category in CATEGORIES:
            target_category = get_target_master_category(category)
            master_path = master_folder / f"Master_{target_category}.xlsx"
            if not master_path.exists():
                continue

            try:
                wb = safe_load_workbook(master_path)

                for sheet_name in wb.sheetnames:
                    if sheet_name == "STATUS":
                        continue

                    ws = wb[sheet_name]

                    # Find all STATUS_{User} columns
                    status_cols = {}
                    for col in range(1, ws.max_column + 1):
                        header = ws.cell(row=1, column=col).value
                        if header and str(header).startswith("STATUS_"):
                            username = str(header).replace("STATUS_", "")
                            status_cols[username] = col

                    if not status_cols:
                        continue

                    # Count status values per user
                    for row in range(2, ws.max_row + 1):
                        for username, col in status_cols.items():
                            value = ws.cell(row=row, column=col).value
                            if value:
                                status_upper = str(value).strip().upper()
                                if status_upper == "FIXED":
                                    manager_stats[category][username]["fixed"] += 1
                                elif status_upper == "REPORTED":
                                    manager_stats[category][username]["reported"] += 1
                                elif status_upper == "CHECKING":
                                    manager_stats[category][username]["checking"] += 1
                                elif status_upper in ("NON-ISSUE", "NON ISSUE"):
                                    manager_stats[category][username]["nonissue"] += 1
                            manager_stats[category][username]["lang"] = tester_mapping.get(username, "EN")

                wb.close()

            except Exception as e:
                print(f"  WARN: Error reading {master_path.name} for manager stats: {e}")

    return dict(manager_stats)


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

    # Get or create master
    first_xlsx = qa_folders[0]["xlsx_path"]
    master_wb, master_path = get_or_create_master(category, master_folder, first_xlsx, rebuild=rebuild)

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

    # Determine if EN or CN for word counting
    is_english = (lang_label == "EN")
    trans_col_key = "eng" if is_english else "other"
    trans_col = TRANSLATION_COLS.get(category, {"eng": 2, "other": 3}).get(trans_col_key, 2)

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
            if match_stats.get("unmatched", 0) > 0:
                print(f"      [WARN] {sheet_name}: {match_stats['exact']} exact, {match_stats['fallback']} fallback, {match_stats['unmatched']} UNMATCHED")
            elif match_stats.get("fallback", 0) > 0:
                print(f"      {sheet_name}: {match_stats['exact']} exact, {match_stats['fallback']} fallback")

            # Count words (EN) or characters (CN) from translation column
            # ONLY count rows where STATUS is filled (DONE rows)
            qa_status_col = find_column_by_header(qa_ws, "STATUS")
            for row in range(2, qa_ws.max_row + 1):
                if qa_status_col:
                    status_val = qa_ws.cell(row, qa_status_col).value
                    if not status_val or str(status_val).strip().upper() not in ["ISSUE", "NO ISSUE", "BLOCKED", "KOREAN"]:
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
