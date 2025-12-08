"""
LDM TXT/TSV File Handler

Parses tab-delimited localization files:
- Columns 0-4: StringID components
- Column 5: Source text (Korean/Original)
- Column 6: Target text (Translation)

Returns list of row dicts ready for database insertion.
"""

import pandas as pd
import csv
import re
from typing import List, Dict, Optional
from loguru import logger


def normalize_text(text: str) -> str:
    """
    Normalize text for storage.

    - Remove unmatched quotes
    - Normalize Unicode whitespace
    - Normalize apostrophes
    - Strip whitespace
    """
    if not isinstance(text, str):
        return ""

    # Handle unmatched quotation marks
    balanced_indices = set()
    quote_indices = [i for i, char in enumerate(text) if char == '"']

    for i in range(0, len(quote_indices) - 1, 2):
        balanced_indices.add(quote_indices[i])
        balanced_indices.add(quote_indices[i + 1])

    result = []
    for i, char in enumerate(text):
        if char == '"' and i not in balanced_indices:
            continue
        result.append(char)

    text = ''.join(result)

    # Normalize Unicode whitespace
    text = re.sub(r'[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000\uFEFF]+', ' ', text)
    text = re.sub(r'[\u200B-\u200F\u202A-\u202E]+', '', text)

    # Normalize apostrophes
    text = re.sub(r'[\u2019\u2018\u02BC\u2032\u0060\u00B4]', "'", text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def parse_txt_file(file_content: bytes, filename: str) -> List[Dict]:
    """
    Parse TXT/TSV file content and extract rows.

    Args:
        file_content: Raw file bytes
        filename: Original filename (for logging)

    Returns:
        List of row dicts with keys: row_num, string_id, source, target
    """
    rows = []

    try:
        # Decode with multiple fallbacks
        for encoding in ['utf-8', 'utf-16', 'cp1252', 'iso-8859-1']:
            try:
                text_content = file_content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            logger.error(f"Could not decode file {filename}")
            return rows

        # Parse as TSV
        lines = text_content.splitlines()

        row_num = 0
        for line in lines:
            if not line.strip():
                continue

            parts = line.split('\t')

            # Need at least 7 columns (0-6)
            if len(parts) < 7:
                logger.debug(f"Skipping line with {len(parts)} columns (need 7)")
                continue

            row_num += 1

            # Build StringID from columns 0-4
            string_id_parts = [str(p).strip() for p in parts[0:5]]
            string_id = " ".join(string_id_parts)

            # Column 5 = Source (Korean), Column 6 = Target (Translation)
            source = normalize_text(parts[5]) if len(parts) > 5 else ""
            target = normalize_text(parts[6]) if len(parts) > 6 else ""

            # Skip if both source and target are empty
            if not source and not target:
                continue

            rows.append({
                "row_num": row_num,
                "string_id": string_id if string_id.strip() else None,
                "source": source if source else None,
                "target": target if target else None,
                "status": "translated" if target else "pending"
            })

        logger.info(f"Parsed {filename}: {len(rows)} rows extracted")

    except Exception as e:
        logger.error(f"Failed to parse TXT file {filename}: {e}")

    return rows


def get_source_language() -> str:
    """Return the source language for TXT files."""
    return "KR"  # Korean is source


def get_file_format() -> str:
    """Return the file format identifier."""
    return "TXT"
