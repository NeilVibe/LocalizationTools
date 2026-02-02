"""
QuickTranslate Core Module.

Public exports for XML parsing, Korean detection, indexing, matching, and I/O.
"""

from .xml_parser import sanitize_xml_content, parse_xml_file
from .korean_detection import KOREAN_REGEX, is_korean_text
from .indexing import build_sequencer_strorigin_index, scan_folder_for_strings
from .language_loader import (
    discover_language_files,
    build_translation_lookup,
    build_reverse_lookup,
)
from .matching import (
    find_matches,
    find_matches_stringid_only,
    find_matches_strict,
    find_matches_special_key,
    find_stringid_from_text,
    format_multiple_matches,
    normalize_text,
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
from .xml_io import parse_corrections_from_xml, parse_folder_xml_files

__all__ = [
    # xml_parser
    "sanitize_xml_content",
    "parse_xml_file",
    # korean_detection
    "KOREAN_REGEX",
    "is_korean_text",
    # indexing
    "build_sequencer_strorigin_index",
    "scan_folder_for_strings",
    # language_loader
    "discover_language_files",
    "build_translation_lookup",
    "build_reverse_lookup",
    # matching
    "find_matches",
    "find_matches_stringid_only",
    "find_matches_strict",
    "find_matches_special_key",
    "find_stringid_from_text",
    "format_multiple_matches",
    "normalize_text",
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
]
