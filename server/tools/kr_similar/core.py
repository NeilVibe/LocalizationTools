"""
KR Similar Core Module

Provides text normalization and utility functions for Korean similarity search.
Extracted from KRSIMILAR0124.py source script.
"""

import re
import pandas as pd
from typing import Optional


def normalize_text(text: str) -> str:
    """
    Normalize Korean text by removing code markers and formatting.

    Removes:
    - Code markers like {ChangeScene()}, {AudioVoice()}
    - Triangle markers (▶)
    - Scale/Color tags
    - Extra whitespace

    Args:
        text: Raw Korean text from language file

    Returns:
        Normalized text for embedding generation
    """
    if pd.isna(text) or not isinstance(text, str):
        return ''

    # Replace \n not followed by { or ▶ with space
    text = re.sub(r'\\n(?![\{▶])', ' ', text)

    # Remove triangles
    text = re.sub(r'▶', '', text)

    # Remove various tags
    text = re.sub(r'<Scale[^>]*>|</Scale>', '', text)
    text = re.sub(r'<color[^>]*>|</color>', '', text)
    text = re.sub(r'<PAColor[^>]*>|<PAOldColor>', '', text)
    text = re.sub(r'\{[^}]*\}', '', text)  # Remove content in curly braces
    text = re.sub(r'<Style:[^>]*>', '', text)  # Handle Style tags

    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def adapt_structure(kr_text: str, translation: str) -> str:
    """
    Adapt translation structure to match Korean text line structure.

    Used when auto-translating to maintain line breaks and formatting.

    Args:
        kr_text: Original Korean text with line breaks
        translation: Translation text to adapt

    Returns:
        Adapted translation matching Korean structure
    """
    kr_lines = kr_text.split('\\n')
    total_lines = len(kr_lines)
    non_empty_lines = sum(1 for line in kr_lines if line.strip())

    if not translation.strip():
        return '\\n'.join([''] * total_lines)

    ideal_length = len(translation) / non_empty_lines if non_empty_lines > 0 else len(translation)
    threshold = int(ideal_length * 1.5)  # 50% over ideal length

    end_punct_pattern = r'[.!?]|\.\.\.'
    all_punct_pattern = r'[.!?,;:]|\.\.\.'

    adapted_lines = []
    start = 0

    for line in kr_lines:
        if line.strip():
            if start >= len(translation):
                adapted_lines.append('')
                continue

            # Find phrase-ending punctuations within threshold
            matches = list(re.finditer(end_punct_pattern, translation[start:start + threshold]))

            if matches:
                # Find punctuation closest to ideal length
                closest_match = min(matches, key=lambda m: abs(m.end() - ideal_length))
                end = start + closest_match.end()
            else:
                # Fallback to any punctuation
                matches = list(re.finditer(all_punct_pattern, translation[start:start + threshold]))
                if matches:
                    closest_match = min(matches, key=lambda m: abs(m.end() - ideal_length))
                    end = start + closest_match.end()
                else:
                    # Break at closest word to ideal length
                    last_space = translation.rfind(' ', start + int(ideal_length) - 10, start + int(ideal_length) + 10)
                    if last_space != -1:
                        end = last_space + 1
                    else:
                        end = start + int(ideal_length)

            # Don't break in middle of ellipsis
            if translation[end-3:end] == '...':
                end += 1

            adapted_lines.append(translation[start:end].strip())
            start = end
        else:
            adapted_lines.append('')

    # Add remaining text to last non-empty line
    if start < len(translation):
        for i in range(len(adapted_lines) - 1, -1, -1):
            if adapted_lines[i]:
                adapted_lines[i] += ' ' + translation[start:].strip()
                break

    return '\\n'.join(adapted_lines)


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
