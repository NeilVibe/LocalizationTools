"""
XLSTransfer Tool - AI-Powered Translation Transfer

A comprehensive tool for transferring translations between Excel files using
Korean BERT embeddings and FAISS similarity search.

Modules:
    - config: Tool-specific configuration
    - core: Text processing and utility functions
    - embeddings: Model loading, embedding generation, FAISS operations
    - translation: Translation matching and similarity search
    - excel_utils: Excel file operations

Key Features:
    - Semantic similarity matching using Korean BERT
    - FAISS-powered fast similarity search
    - Split and whole text matching modes
    - Game code pattern preservation
    - Newline adaptation
    - Excel file combining and transfer operations
"""

__version__ = "0.3.0"
__author__ = "Neil"

# Import configuration
from server.tools.xlstransfer import config

# Import core utilities
from server.tools.xlstransfer.core import (
    clean_text,
    excel_column_to_index,
    index_to_excel_column,
    convert_cell_value,
    analyze_code_patterns,
    extract_code_blocks,
    simple_number_replace,
    find_code_patterns_in_text,
    strip_codes_from_text,
    count_newlines,
    normalize_newlines
)

# Import embedding functions
from server.tools.xlstransfer.embeddings import (
    load_model,
    get_model,
    generate_embeddings,
    create_faiss_index,
    create_translation_dictionary,
    save_dictionary,
    load_dictionary,
    check_dictionary_exists,
    process_excel_for_dictionary
)

# Import translation functions
from server.tools.xlstransfer.translation import (
    find_best_match,
    process_batch,
    translate_text_multi_mode,
    get_match_statistics,
    filter_by_threshold,
    get_low_confidence_matches,
    TranslationProgress
)

# Import Excel utilities
from server.tools.xlstransfer.excel_utils import (
    read_excel_columns,
    get_sheet_names,
    write_translations_to_excel,
    check_newline_mismatches,
    combine_excel_files,
    auto_adapt_newlines,
    simple_excel_transfer,
    validate_excel_file
)

# Define what's available when using "from server.tools.xlstransfer import *"
__all__ = [
    # Config
    'config',

    # Core utilities (11 functions)
    'clean_text',
    'excel_column_to_index',
    'index_to_excel_column',
    'convert_cell_value',
    'analyze_code_patterns',
    'extract_code_blocks',
    'simple_number_replace',
    'find_code_patterns_in_text',
    'strip_codes_from_text',
    'count_newlines',
    'normalize_newlines',

    # Embedding functions (9 functions)
    'load_model',
    'get_model',
    'generate_embeddings',
    'create_faiss_index',
    'create_translation_dictionary',
    'save_dictionary',
    'load_dictionary',
    'check_dictionary_exists',
    'process_excel_for_dictionary',

    # Translation functions (7 functions + 1 class)
    'find_best_match',
    'process_batch',
    'translate_text_multi_mode',
    'get_match_statistics',
    'filter_by_threshold',
    'get_low_confidence_matches',
    'TranslationProgress',

    # Excel utilities (8 functions)
    'read_excel_columns',
    'get_sheet_names',
    'write_translations_to_excel',
    'check_newline_mismatches',
    'combine_excel_files',
    'auto_adapt_newlines',
    'simple_excel_transfer',
    'validate_excel_file',
]
