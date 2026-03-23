# server/services/merge package
#
# Self-contained merge engine internalized from QuickTranslate core.
# All imports are relative -- no sys.path or sys.modules manipulation needed.
from __future__ import annotations

from .text_utils import normalize_text, normalize_for_matching, normalize_nospace
from .xml_parser import (
    sanitize_xml_content,
    parse_xml_file,
    iter_locstr_elements,
    DESC_ATTRS,
    DESCORIGIN_ATTRS,
)
from .korean_detection import KOREAN_REGEX, is_korean_text
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
from .source_scanner import (
    SourceScanResult,
    scan_source_for_languages,
    scan_target_for_languages,
    TargetScanResult,
    ValidationResult,
    TransferPlan,
    LanguageTransferPlan,
    FileMapping,
    generate_transfer_plan,
    format_transfer_plan,
)
from .eventname_resolver import (
    get_eventname_mapping,
    resolve_eventnames_in_corrections,
    generate_missing_eventname_report,
)
from .tmx_tools import (
    clean_segment,
    clean_tmx_string,
    postprocess_tmx_string,
    combine_xmls_to_tmx,
    batch_tmx_from_folders,
    clean_and_convert_to_excel,
    convert_to_memoq_tmx,
    SUFFIX_TO_BCP47,
)
from ._config import configure, get_config, reconfigure

__all__ = [
    # _config
    "configure",
    "get_config",
    "reconfigure",
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
    # source_scanner
    "SourceScanResult",
    "scan_source_for_languages",
    "scan_target_for_languages",
    "TargetScanResult",
    "ValidationResult",
    "TransferPlan",
    "LanguageTransferPlan",
    "FileMapping",
    "generate_transfer_plan",
    "format_transfer_plan",
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
    "convert_to_memoq_tmx",
    "SUFFIX_TO_BCP47",
]
