"""
LDM XML File Handler

Parses XML localization files with LocStr elements:
- StringId attribute: String identifier
- StrOrigin attribute: Source text (Korean/Original)
- Str attribute: Target text (Translation)

Returns list of row dicts ready for database insertion.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict
from loguru import logger

# Factor Power: Use centralized text utils
from server.utils.text_utils import normalize_text


def parse_xml_file(file_content: bytes, filename: str) -> List[Dict]:
    """
    Parse XML file content and extract rows.

    XML Format expected:
    <Root>
      <LocStr StringId="xxx" StrOrigin="Korean text" Str="Translation" />
      ...
    </Root>

    Args:
        file_content: Raw file bytes
        filename: Original filename (for logging)

    Returns:
        List of row dicts with keys: row_num, string_id, source, target
    """
    rows = []

    try:
        # Decode with multiple fallbacks
        text_content = None
        for encoding in ['utf-8', 'utf-16', 'cp1252', 'iso-8859-1']:
            try:
                text_content = file_content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text_content is None:
            logger.error(f"Could not decode file {filename}")
            return rows

        # Parse XML
        root = ET.fromstring(text_content)

        row_num = 0
        for loc in root.findall('.//LocStr'):
            row_num += 1

            # Extract attributes
            string_id = loc.get('StringId', '') or ''
            source = normalize_text(loc.get('StrOrigin', '') or '')
            target = normalize_text(loc.get('Str', '') or '')

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

    except ET.ParseError as e:
        logger.error(f"XML parse error in {filename}: {e}")
    except Exception as e:
        logger.error(f"Failed to parse XML file {filename}: {e}")

    return rows


def get_source_language() -> str:
    """Return the source language for XML files."""
    return "KR"  # Korean is source


def get_file_format() -> str:
    """Return the file format identifier."""
    return "XML"
