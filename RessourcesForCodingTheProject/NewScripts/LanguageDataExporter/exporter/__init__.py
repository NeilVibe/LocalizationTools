"""
Exporter package for Language XML to Categorized Excel Converter.

Modules:
- xml_parser: Parse languagedata_*.xml files
- category_mapper: Build StringID → Category from EXPORT folder (two-tier clustering)
- excel_writer: Generate Excel files with openpyxl
- submit_preparer: Prepare files for LQA submission
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
    collect_correction_stats,
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
    "collect_correction_stats",
]
