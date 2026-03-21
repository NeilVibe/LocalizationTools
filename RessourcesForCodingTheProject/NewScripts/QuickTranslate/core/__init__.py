"""
QuickTranslate Core Module.

Public exports for XML parsing, Korean detection, indexing, matching, and I/O.
"""

from .text_utils import normalize_text, normalize_for_matching, normalize_nospace
from .xml_parser import sanitize_xml_content, parse_xml_file, iter_locstr_elements, DESC_ATTRS, DESCORIGIN_ATTRS
from .korean_detection import KOREAN_REGEX, is_korean_text
from .indexing import build_sequencer_strorigin_index, scan_folder_for_entries_with_context
from .language_loader import (
    discover_language_files,
    build_translation_lookup,
    build_stringid_to_category,
    build_stringid_to_subfolder,
    build_stringid_to_filepath,
)
from .matching import format_multiple_matches
from .excel_io import (
    detect_excel_columns,
    read_corrections_from_excel,
    # Excel target merge (for TRANSFER mode)
    merge_corrections_to_excel,
)
from .xml_io import parse_corrections_from_xml
from .xml_transfer import (
    merge_corrections_to_xml,
    merge_corrections_stringid_only,
    transfer_folder_to_folder,
    format_transfer_report,
)
from .postprocess import run_all_postprocess, run_preprocess_excel
try:
    from .fuzzy_matching import (
        check_model_available,
        load_model as load_fuzzy_model,
        build_faiss_index,
        find_matches_fuzzy,
        build_index_from_folder,
        get_cached_index_info,
        clear_cache as clear_fuzzy_cache,
    )
except ImportError:
    # ML dependencies (numpy, faiss, model2vec) not installed
    # Fuzzy matching unavailable - other modes still work
    pass
from .source_scanner import (
    SourceScanResult,
    scan_source_for_languages,
    ValidationResult,
    # Target scanner (flexible target detection)
    TargetScanResult,
    scan_target_for_languages,
    # Transfer Plan (full tree table)
    TransferPlan,
    LanguageTransferPlan,
    FileMapping,
    generate_transfer_plan,
    format_transfer_plan,
)
from .failure_report import (
    generate_failed_merge_xml_per_language,
    extract_failed_from_folder_results,
    extract_mismatch_target_entries,
    # Excel failure reports
    generate_failure_report_excel,
    generate_fuzzy_report_excel,
    check_xlsxwriter_available,
    # Duplicate StrOrigin report
    generate_duplicate_strorigin_excel,
)
from .missing_translation_finder import (
    find_missing_with_options,
    MissingTranslationReport,
    LanguageMissingReport,
    MissingEntry,
)
from .category_mapper import build_stringid_category_index
from .checker import (
    run_korean_check,
    run_pattern_check,
    should_skip_locstr,
    iter_source_xml_files,
)
from .quality_checker import run_quality_check
from .tmx_tools import (
    clean_segment,
    clean_tmx_string,
    postprocess_tmx_string,
    combine_xmls_to_tmx,
    batch_tmx_from_folders,
    clean_and_convert_to_excel,
)
from .eventname_resolver import (
    get_eventname_mapping,
    resolve_eventnames_in_corrections,
    generate_missing_eventname_report,
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
    "DESC_ATTRS",
    "DESCORIGIN_ATTRS",
    # korean_detection
    "KOREAN_REGEX",
    "is_korean_text",
    # indexing
    "build_sequencer_strorigin_index",
    "scan_folder_for_entries_with_context",
    # language_loader
    "discover_language_files",
    "build_translation_lookup",
    "build_stringid_to_category",
    "build_stringid_to_subfolder",
    "build_stringid_to_filepath",
    # matching
    "format_multiple_matches",
    # excel_io
    "detect_excel_columns",
    "read_corrections_from_excel",
    "merge_corrections_to_excel",
    # xml_io
    "parse_corrections_from_xml",
    # xml_transfer
    "merge_corrections_to_xml",
    "merge_corrections_stringid_only",
    "transfer_folder_to_folder",
    "format_transfer_report",
    # postprocess
    "run_all_postprocess",
    "run_preprocess_excel",
    # fuzzy_matching
    "check_model_available",
    "load_fuzzy_model",
    "build_faiss_index",
    "find_matches_fuzzy",
    "build_index_from_folder",
    "get_cached_index_info",
    "clear_fuzzy_cache",
    # source_scanner
    "SourceScanResult",
    "scan_source_for_languages",
    "ValidationResult",
    "TargetScanResult",
    "scan_target_for_languages",
    "TransferPlan",
    "LanguageTransferPlan",
    "FileMapping",
    "generate_transfer_plan",
    "format_transfer_plan",
    # failure_report
    "generate_failed_merge_xml_per_language",
    "extract_failed_from_folder_results",
    "extract_mismatch_target_entries",
    "generate_failure_report_excel",
    "generate_fuzzy_report_excel",
    "check_xlsxwriter_available",
    "generate_duplicate_strorigin_excel",
    # missing_translation_finder
    "find_missing_with_options",
    "MissingTranslationReport",
    "LanguageMissingReport",
    "MissingEntry",
    # category_mapper
    "build_stringid_category_index",
    # checker
    "run_korean_check",
    "run_pattern_check",
    "should_skip_locstr",
    "iter_source_xml_files",
    # quality_checker
    "run_quality_check",
    # eventname_resolver
    "get_eventname_mapping",
    "resolve_eventnames_in_corrections",
    "generate_missing_eventname_report",
    # tmx_tools
    "clean_segment",
    "clean_tmx_string",
    "postprocess_tmx_string",
    "combine_xmls_to_tmx",
    "batch_tmx_from_folders",
    "clean_and_convert_to_excel",
]
