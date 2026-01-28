"""Core functionality for QuickSearch."""

from .xml_parser import parse_xml_file, parse_txt_file, parse_multiple_files
from .preprocessing import preprocess_for_consistency_check
from .line_check import run_line_check
from .term_check import run_term_check
from .glossary import extract_glossary, glossary_filter
from .dictionary import create_dictionary, load_dictionary, save_dictionary
from .search import search_one_line, search_multi_line

__all__ = [
    'parse_xml_file',
    'parse_txt_file',
    'parse_multiple_files',
    'preprocess_for_consistency_check',
    'run_line_check',
    'run_term_check',
    'extract_glossary',
    'glossary_filter',
    'create_dictionary',
    'load_dictionary',
    'save_dictionary',
    'search_one_line',
    'search_multi_line',
]
