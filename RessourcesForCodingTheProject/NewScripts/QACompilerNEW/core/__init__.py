"""
Core Package
============
Compiler core modules.

- discovery.py: QA folder detection
- excel_ops.py: Workbook operations
- processing.py: Sheet processing
- transfer.py: File transfer operations
- compiler.py: Main compilation orchestration
"""

from core.discovery import (
    discover_qa_folders,
    discover_qa_folders_in,
    group_folders_by_category,
    group_folders_by_language,
)

from core.excel_ops import (
    safe_load_workbook,
    repair_excel_filters,
    find_column_by_header,
    get_or_create_master,
    ensure_master_folders,
    copy_images_with_unique_names,
)

from core.transfer import transfer_qa_files

from core.compiler import run_compiler

__all__ = [
    # Discovery
    "discover_qa_folders",
    "discover_qa_folders_in",
    "group_folders_by_category",
    "group_folders_by_language",
    # Excel operations
    "safe_load_workbook",
    "repair_excel_filters",
    "find_column_by_header",
    "get_or_create_master",
    "ensure_master_folders",
    "copy_images_with_unique_names",
    # Transfer
    "transfer_qa_files",
    # Compiler
    "run_compiler",
]
