"""
QuickTranslate Core Module.

Public exports for XML parsing, Korean detection, indexing, matching, and I/O.
"""

from .text_utils import normalize_text, normalize_for_matching, normalize_nospace
from .xml_parser import sanitize_xml_content, parse_xml_file, iter_locstr_elements
from .korean_detection import KOREAN_REGEX, is_korean_text
from .indexing import build_sequencer_strorigin_index, scan_folder_for_strings, scan_folder_for_entries
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
    merge_corrections_stringid_only,
    transfer_folder_to_folder,
    transfer_file_to_file,
    format_transfer_report,
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
    "merge_corrections_stringid_only",
    "transfer_folder_to_folder",
    "transfer_file_to_file",
    "format_transfer_report",
]
