"""
TextBatchProcessor - Batch text file processing for localization workflows

Simple tool for common text file operations:
- Find and replace patterns
- Extract unique strings
- Combine multiple files
- Word count statistics
- Split files by delimiter
"""

from client.tools.text_batch_processor.core import (
    find_and_replace,
    extract_unique_strings,
    combine_files,
    get_word_count_stats,
    split_by_delimiter
)

__all__ = [
    'find_and_replace',
    'extract_unique_strings',
    'combine_files',
    'get_word_count_stats',
    'split_by_delimiter'
]
