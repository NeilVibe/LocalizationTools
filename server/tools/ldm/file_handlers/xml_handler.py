"""
LDM XML File Handler

Parses XML localization files with LocStr elements:
- StringId attribute: String identifier
- StrOrigin attribute: Source text (Korean/Original)
- Str attribute: Target text (Translation)

Returns list of row dicts ready for database insertion.
"""

import xml.etree.ElementTree as ET
import re
from typing import List, Dict
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
