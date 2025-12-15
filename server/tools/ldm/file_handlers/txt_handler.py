"""
LDM TXT/TSV File Handler

Parses tab-delimited localization files:
- Columns 0-4: StringID components
- Column 5: Source text (Korean/Original)
- Column 6: Target text (Translation)
- Columns 7+: Extra columns (preserved for full reconstruction)

Returns list of row dicts ready for database insertion.
Also returns file-level metadata for full file reconstruction.
"""

import csv
from typing import List, Dict, Optional, Tuple
from loguru import logger

# Factor Power: Use centralized text utils
from server.utils.text_utils import normalize_text


# Module-level state for file metadata (used by get_file_metadata)
_file_metadata: Dict = {}


def parse_txt_file(file_content: bytes, filename: str) -> List[Dict]:
    """
    Parse TXT/TSV file content and extract rows.

    Preserves ALL data for full file reconstruction:
    - Standard columns 0-6 are parsed normally
    - Extra columns (7+) stored in extra_data for reconstruction

    Args:
        file_content: Raw file bytes
        filename: Original filename (for logging)

    Returns:
        List of row dicts with keys: row_num, string_id, source, target, extra_data
    """
    global _file_metadata
    rows = []
    detected_encoding = None
    max_columns = 0

    try:
        # Decode with multiple fallbacks
        for encoding in ['utf-8', 'utf-16', 'cp1252', 'iso-8859-1']:
            try:
                text_content = file_content.decode(encoding)
                detected_encoding = encoding
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
            max_columns = max(max_columns, len(parts))

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

            # Capture extra columns (7+) for full reconstruction
            extra_data = None
            if len(parts) > 7:
                extra_cols = {}
                for i, val in enumerate(parts[7:], start=7):
                    extra_cols[f"col{i}"] = val
                extra_data = extra_cols

            rows.append({
                "row_num": row_num,
                "string_id": string_id if string_id.strip() else None,
                "source": source if source else None,
                "target": target if target else None,
                "status": "translated" if target else "pending",
                "extra_data": extra_data
            })

        # Store file-level metadata for reconstruction
        _file_metadata = {
            "encoding": detected_encoding,
            "total_columns": max_columns,
            "line_count": len(lines),
            "format_version": "1.0"
        }

        logger.info(f"Parsed {filename}: {len(rows)} rows, {max_columns} columns, encoding={detected_encoding}")

    except Exception as e:
        logger.error(f"Failed to parse TXT file {filename}: {e}")

    return rows


def get_file_metadata() -> Dict:
    """
    Get file-level metadata for full reconstruction.

    Returns dict with:
    - encoding: Detected file encoding
    - total_columns: Maximum column count in file
    - line_count: Total lines in original file
    """
    global _file_metadata
    return _file_metadata.copy()


def get_source_language() -> str:
    """Return the source language for TXT files."""
    return "KR"  # Korean is source


def get_file_format() -> str:
    """Return the file format identifier."""
    return "TXT"
