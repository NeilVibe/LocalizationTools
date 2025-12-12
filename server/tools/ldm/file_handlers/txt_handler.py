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
from typing import List, Dict, Optional
from loguru import logger

# Factor Power: Use centralized text utils
from server.utils.text_utils import normalize_text


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
