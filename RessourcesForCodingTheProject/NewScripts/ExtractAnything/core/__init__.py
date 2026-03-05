"""ExtractAnything core – shared parsing, I/O, and engine modules."""

from __future__ import annotations

from .xml_parser import (
    sanitize_xml,
    read_xml_raw,
    parse_root_from_string,
    parse_root_from_file,
    parse_tree_from_string,
    parse_tree_from_file,
    iter_locstr,
    get_attr,
    get_attr_value,
    write_xml_tree,
    USING_LXML,
)
from .text_utils import (
    normalize_text, normalize_nospace, visible_char_count,
    normalize_newlines, has_wrong_newlines, convert_linebreaks_for_xml, br_to_newline,
)
from .language_utils import discover_valid_codes, extract_language_from_filename
from .export_index import ExportIndex, build_export_index
from .input_parser import parse_input_file, parse_input_folder
from .xml_writer import write_locstr_xml
from .excel_writer import write_extraction_excel, write_blacklist_excel
from .excel_reader import read_entries_from_excel, read_blacklist_from_excel

__all__ = [
    "sanitize_xml", "read_xml_raw", "parse_root_from_string", "parse_root_from_file",
    "parse_tree_from_string", "parse_tree_from_file", "iter_locstr", "get_attr",
    "get_attr_value", "write_xml_tree", "USING_LXML",
    "normalize_text", "normalize_nospace", "visible_char_count",
    "normalize_newlines", "has_wrong_newlines", "convert_linebreaks_for_xml", "br_to_newline",
    "discover_valid_codes", "extract_language_from_filename",
    "ExportIndex", "build_export_index",
    "parse_input_file", "parse_input_folder",
    "write_locstr_xml",
    "write_extraction_excel", "write_blacklist_excel",
    "read_entries_from_excel", "read_blacklist_from_excel",
]
