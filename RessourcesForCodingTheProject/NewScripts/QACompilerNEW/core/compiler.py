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
# MANAGER STATUS COLLECTION
# =============================================================================

def extract_comment_text(comment_value) -> str:
    """
    Extract just the comment text, removing timestamps and separators.

    Example: "2024-01-15 | This is a comment" -> "This is a comment"
    """
    if not comment_value:
        return ""

    text = str(comment_value).strip()

    # Remove timestamp prefix if present (format: "YYYY-MM-DD | ...")
    if " | " in text:
        parts = text.split(" | ", 1)
        if len(parts) > 1 and len(parts[0]) == 10:
            text = parts[1]

    return text.strip()


def collect_manager_status(master_folder: Path) -> Dict:
    """
    Read existing Master files and collect all STATUS_{User} values.

    KEYED BY COMMENT TEXT for matching after rebuild.

    Args:
        master_folder: Which Master folder to scan (EN or CN)

    Returns:
        {category: {sheet_name: {comment_text: {user: status}}}}
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

                # Find all COMMENT_{User} and STATUS_{User} columns
                comment_cols = {}  # username -> col
                status_cols = {}   # username -> col
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

                if not status_cols:
                    continue

                # Collect values per row, keyed by comment text
                for row in range(2, ws.max_row + 1):
                    for username, status_col in status_cols.items():
                        status_value = ws.cell(row=row, column=status_col).value
                        if status_value and str(status_value).strip().upper() in VALID_MANAGER_STATUS:
                            comment_col = comment_cols.get(username)
                            if comment_col:
                                full_comment = ws.cell(row=row, column=comment_col).value
                                comment_text = extract_comment_text(full_comment)
                                if comment_text:
                                    if comment_text not in manager_status[category][sheet_name]:
                                        manager_status[category][sheet_name][comment_text] = {}
                                    manager_status[category][sheet_name][comment_text][username] = \
                                        str(status_value).strip().upper()

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
    rebuild: bool = True
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

    Returns:
        List of daily_entry dicts for tracker
    """
    if manager_status is None:
        manager_status = {}

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
    if category == "Item" and lang_label == "EN":
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
        image_mapping = copy_images_with_unique_names(qf, images_folder)
        total_images += len(image_mapping)

        # Load QA workbook
        qa_wb = safe_load_workbook(xlsx_path)

        # EN Item category: Sort QA workbook sheets A-Z for consistent matching
        if category == "Item" and lang_label == "EN":
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

            # Ensure sheet exists in master
            if sheet_name not in master_wb.sheetnames:
                master_wb.create_sheet(sheet_name)

            master_ws = master_wb[sheet_name]

            # Get manager status for this sheet
            sheet_manager_status = manager_status.get(sheet_name, {})

            # Process the sheet (creates user columns internally)
            result = process_sheet(
                master_ws, qa_ws, username, category,
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

    # Post-process: Hide rows/sheets/columns with no comments (focus on issues)
    hidden_rows, hidden_sheets, hidden_columns = hide_empty_comment_rows(master_wb)

    # Apply word wrap and autofit row heights
    autofit_rows_with_wordwrap(master_wb)

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
                category_manager_status, rebuild=rebuild
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
                category_manager_status, rebuild=rebuild
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
