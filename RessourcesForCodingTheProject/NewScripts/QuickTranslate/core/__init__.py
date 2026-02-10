"""
QuickTranslate Core Module.

Public exports for XML parsing, Korean detection, indexing, matching, and I/O.
"""

from .text_utils import normalize_text, normalize_for_matching, normalize_nospace
from .xml_parser import sanitize_xml_content, parse_xml_file, iter_locstr_elements
from .korean_detection import KOREAN_REGEX, is_korean_text
from .indexing import build_sequencer_strorigin_index, scan_folder_for_strings, scan_folder_for_entries, scan_folder_for_entries_with_context
from .language_loader import (
    discover_language_files,
    build_translation_lookup,
    build_reverse_lookup,
    build_stringid_to_category,
    build_stringid_to_subfolder,
)
from .matching import (
    find_matches,
    find_matches_with_stats,
    find_matches_stringid_only,
    find_matches_strict,
    find_matches_strict_fuzzy,
    find_matches_special_key,
    find_stringid_from_text,
    format_multiple_matches,
)
from .excel_io import (
    read_korean_input,
    read_corrections_from_excel,
    get_ordered_languages,
    write_output_excel,
    write_stringid_lookup_excel,
    write_folder_translation_excel,
    write_reverse_lookup_excel,
)
from .xml_io import parse_corrections_from_xml, parse_folder_xml_files, parse_tosubmit_xml
from .xml_transfer import (
    merge_corrections_to_xml,
    merge_corrections_strorigin_only,
    merge_corrections_stringid_only,
    merge_corrections_fuzzy,
    cleanup_empty_strorigin,
    transfer_folder_to_folder,
    transfer_file_to_file,
    format_transfer_report,
)
try:
    from .fuzzy_matching import (
        check_model_available,
        load_model as load_fuzzy_model,
        build_faiss_index,
        search_fuzzy,
        find_matches_fuzzy,
        build_index_from_folder,
        get_cached_index_info,
        clear_cache as clear_fuzzy_cache,
    )
except ImportError:
    # ML dependencies (numpy, faiss, sentence-transformers) not installed
    # Fuzzy matching unavailable - other modes still work
    pass
from .source_scanner import (
    SourceScanResult,
    scan_source_for_languages,
    extract_language_suffix,
    validate_source_structure,
    format_scan_result,
    ValidationResult,
    # Transfer Plan (full tree table)
    TransferPlan,
    LanguageTransferPlan,
    FileMapping,
    generate_transfer_plan,
    format_transfer_plan,
)
from .failure_report import (
    generate_failed_merge_xml,
    generate_failed_merge_xml_per_language,
    extract_failed_from_transfer_results,
    extract_failed_from_folder_results,
    format_failure_summary,
    # Excel failure reports
    generate_failure_report_excel,
    generate_failure_report_from_transfer,
    aggregate_transfer_results,
    check_xlsxwriter_available,
    FAILURE_REASONS,
)
from .missing_translation_finder import (
    find_missing_translations,
    find_missing_translations_per_language,
    find_missing_with_options,
    format_report_summary,
    MissingTranslationReport,
    LanguageMissingReport,
    MissingEntry,
)
from .category_mapper import (
    categorize_file,
    build_stringid_category_index,
)
from .checker import (
    run_korean_check,
    run_pattern_check,
    should_skip_locstr,
    iter_source_xml_files,
)
from .quality_checker import (
    run_quality_check,
)

__all__ = [
    # text_utils
    "normalize_text",
    "normalize_for_matching",
    "normalize_nospace",
    # xml_parser
    "sanitize_xml_content",
    "parse_xml_file",
    "iter_locstr_elements",
    # korean_detection
    "KOREAN_REGEX",
    "is_korean_text",
    # indexing
    "build_sequencer_strorigin_index",
    "scan_folder_for_strings",
    "scan_folder_for_entries",
    "scan_folder_for_entries_with_context",
    # language_loader
    "discover_language_files",
    "build_translation_lookup",
    "build_reverse_lookup",
    "build_stringid_to_category",
    "build_stringid_to_subfolder",
    # matching
    "find_matches",
    "find_matches_with_stats",
    "find_matches_stringid_only",
    "find_matches_strict",
    "find_matches_strict_fuzzy",
    "find_matches_special_key",
    "find_stringid_from_text",
    "format_multiple_matches",
    # excel_io
    "read_korean_input",
    "read_corrections_from_excel",
    "get_ordered_languages",
    "write_output_excel",
    "write_stringid_lookup_excel",
    "write_folder_translation_excel",
    "write_reverse_lookup_excel",
    # xml_io
    "parse_corrections_from_xml",
    "parse_folder_xml_files",
    "parse_tosubmit_xml",
    # xml_transfer
    "merge_corrections_to_xml",
    "merge_corrections_strorigin_only",
    "merge_corrections_stringid_only",
    "merge_corrections_fuzzy",
    "cleanup_empty_strorigin",
    "transfer_folder_to_folder",
    "transfer_file_to_file",
    "format_transfer_report",
    # fuzzy_matching
    "check_model_available",
    "load_fuzzy_model",
    "build_faiss_index",
    "search_fuzzy",
    "find_matches_fuzzy",
    "build_index_from_folder",
    "get_cached_index_info",
    "clear_fuzzy_cache",
    # source_scanner
    "SourceScanResult",
    "scan_source_for_languages",
    "extract_language_suffix",
    "validate_source_structure",
    "format_scan_result",
    "ValidationResult",
    # transfer_plan (full tree table)
    "TransferPlan",
    "LanguageTransferPlan",
    "FileMapping",
    "generate_transfer_plan",
    "format_transfer_plan",
    # failure_report (XML)
    "generate_failed_merge_xml",
    "generate_failed_merge_xml_per_language",
    "extract_failed_from_transfer_results",
    "extract_failed_from_folder_results",
    "format_failure_summary",
    # failure_report (Excel)
    "generate_failure_report_excel",
    "generate_failure_report_from_transfer",
    "aggregate_transfer_results",
    "check_xlsxwriter_available",
    "FAILURE_REASONS",
    # missing_translation_finder
    "find_missing_translations",
    "find_missing_translations_per_language",
    "find_missing_with_options",
    "format_report_summary",
    "MissingTranslationReport",
    "LanguageMissingReport",
    "MissingEntry",
    # category_mapper
    "categorize_file",
    "build_stringid_category_index",
    # checker
    "run_korean_check",
    "run_pattern_check",
    "should_skip_locstr",
    "iter_source_xml_files",
    # quality_checker
    "run_quality_check",
]
