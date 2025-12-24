"""
KR Similar Core Module

Provides text normalization and utility functions for Korean similarity search.
Extracted from KRSIMILAR0124.py source script.

NOTE: Core functions are now centralized in server/utils/:
      - normalize_text -> server/utils/text_utils.py
      - adapt_structure -> server/utils/code_patterns.py
      Re-exported here for backwards compatibility.
"""

from typing import Optional

import pandas as pd

# Factor Power: Use centralized utils
from server.utils.text_utils import normalize_korean_text as normalize_text
from server.utils.code_patterns import adapt_structure


class KRSimilarCore:
    """
    Core class for KR Similar functionality.

    Provides text normalization and structure adaptation utilities
    used by the embeddings and searcher modules.
    """

    def __init__(self):
        """Initialize KRSimilarCore."""
        pass

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize text for embedding generation."""
        return normalize_text(text)

    @staticmethod
    def adapt_structure(kr_text: str, translation: str) -> str:
        """Adapt translation to match Korean text structure."""
        return adapt_structure(kr_text, translation)

    @staticmethod
    def parse_language_file(file_path: str, kr_column: int = 5, trans_column: int = 6) -> pd.DataFrame:
        """
        Parse a tab-separated language data file.

        Expected format:
        - Tab-separated values
        - Korean text in column 5 (0-indexed)
        - Translation in column 6 (0-indexed)

        Args:
            file_path: Path to the language data file
            kr_column: Column index for Korean text (default: 5)
            trans_column: Column index for translation (default: 6)

        Returns:
            DataFrame with 'Korean' and 'Translation' columns
        """
        try:
            data = pd.read_csv(
                file_path,
                delimiter="\t",
                header=None,
                usecols=[kr_column, trans_column],
                on_bad_lines='skip'
            )
            data.columns = ['Korean', 'Translation']
            return data
        except Exception as e:
            raise ValueError(f"Failed to parse language file: {str(e)}")

    @staticmethod
    def process_split_data(data: pd.DataFrame) -> pd.DataFrame:
        """
        Split multi-line entries into individual lines.

        Used for creating split embeddings where each line
        is embedded separately.

        Args:
            data: DataFrame with 'Korean' and 'Translation' columns

        Returns:
            DataFrame with split lines
        """
        split_data = []

        for idx, row in data.iterrows():
            kr_text = str(row['Korean']) if pd.notna(row['Korean']) else ''
            trans_text = str(row['Translation']) if pd.notna(row['Translation']) else ''

            kr_lines = kr_text.split('\\n')
            trans_lines = trans_text.split('\\n')

            if len(kr_lines) == len(trans_lines):
                for kr_line, trans_line in zip(kr_lines, trans_lines):
                    if kr_line.strip():
                        split_data.append({
                            'Korean': kr_line.strip(),
                            'Translation': trans_line.strip()
                        })

        return pd.DataFrame(split_data)
