"""
Exporter package for Language XML to Categorized Excel Converter.

Modules:
- xml_parser: Parse languagedata_*.xml files
- category_mapper: Build StringID → Category from EXPORT folder (two-tier clustering)
- excel_writer: Generate Excel files with openpyxl
- submit_preparer: Prepare files for LQA submission
- locdev_merger: Merge corrections back to LOCDEV XML files
"""

from .xml_parser import parse_language_file, discover_language_files
from .category_mapper import (
    build_stringid_category_index,
    load_cluster_config,
    analyze_categories,
    TwoTierCategoryMapper,
)
from .excel_writer import write_language_excel
from .submit_preparer import (
    discover_submit_files,
    create_backup,
    prepare_file_for_submit,
    prepare_all_for_submit,
)
from .locdev_merger import (
    normalize_text,
    parse_corrections_from_excel,
    merge_corrections_to_locdev,
    merge_all_corrections,
    print_merge_report,
    # StringID-only matching for SCRIPT strings
    SCRIPT_CATEGORIES,
    merge_corrections_stringid_only_script,
    merge_all_corrections_stringid_only_script,
    print_stringid_only_report,
)
from .pattern_analyzer import (
    extract_code_patterns,
    cluster_patterns,
    analyze_patterns,
    generate_pattern_report,
)

__all__ = [
    "parse_language_file",
    "discover_language_files",
    "build_stringid_category_index",
    "load_cluster_config",
    "analyze_categories",
    "TwoTierCategoryMapper",
    "write_language_excel",
    "discover_submit_files",
    "create_backup",
    "prepare_file_for_submit",
    "prepare_all_for_submit",
    # LOCDEV merger
    "normalize_text",
    "parse_corrections_from_excel",
    "merge_corrections_to_locdev",
    "merge_all_corrections",
    "print_merge_report",
    # StringID-only matching
    "SCRIPT_CATEGORIES",
    "merge_corrections_stringid_only_script",
    "merge_all_corrections_stringid_only_script",
    "print_stringid_only_report",
    # Pattern analyzer
    "extract_code_patterns",
    "cluster_patterns",
    "analyze_patterns",
    "generate_pattern_report",
]
