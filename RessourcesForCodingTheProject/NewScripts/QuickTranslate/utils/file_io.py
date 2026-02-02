"""
File I/O Utilities.

General file operations for QuickTranslate.
"""

from pathlib import Path
from typing import List


def read_text_file_lines(file_path: Path) -> List[str]:
    """
    Read text file and return trimmed non-empty lines.

    Args:
        file_path: Path to text file

    Returns:
        List of trimmed non-empty lines
    """
    lines = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
    return lines
