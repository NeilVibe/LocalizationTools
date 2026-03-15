"""
LDM XML File Handler

Parses XML localization files with LocStr elements via XMLParsingEngine (lxml).
- StringId attribute: String identifier (case-variant lookup)
- StrOrigin attribute: Source text (Korean/Original)
- Str attribute: Target text (Translation)
- All other attributes: Preserved in extra_data for full reconstruction

Returns tuple of (rows, metadata) for database insertion and file reconstruction.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from loguru import logger

from server.tools.ldm.services.xml_parsing import (
    get_xml_parsing_engine,
    get_attr,
    iter_locstr_elements,
    STRINGID_ATTRS,
    STRORIGIN_ATTRS,
    STR_ATTRS,
)
from server.utils.text_utils import normalize_text


# Core attributes that are stored in dedicated columns (case-insensitive matching)
CORE_ATTRIBUTES = {'stringid', 'strorigin', 'str'}


def parse_xml_file(file_content: bytes, filename: str) -> Tuple[List[Dict], Dict]:
    """
    Parse XML file content and extract rows.

    Preserves ALL data for full file reconstruction:
    - Core attributes (StringId, StrOrigin, Str) stored in dedicated columns
    - All other attributes stored in extra_data for reconstruction

    Args:
        file_content: Raw file bytes
        filename: Original filename (for logging)

    Returns:
        Tuple of (rows, metadata):
        - rows: List of row dicts with keys: row_num, string_id, source, target, extra_data
        - metadata: Dict with encoding, xml_declaration, root_element, etc.
    """
    rows: List[Dict] = []
    metadata: Dict = {}

    engine = get_xml_parsing_engine()

    try:
        root, detected_encoding = engine.parse_bytes(file_content, filename)

        if root is None:
            logger.error(f"Could not parse XML file {filename}")
            return rows, metadata

        # Extract XML declaration from raw bytes for metadata
        xml_declaration = None
        try:
            text_start = file_content[:200].decode('utf-8', errors='ignore')
            decl_match = re.match(r'(<\?xml[^?]*\?>)', text_start)
            if decl_match:
                xml_declaration = decl_match.group(1)
        except Exception:
            pass

        # Store root element info
        root_tag = root.tag
        root_attribs = dict(root.attrib) if root.attrib else None

        # Find LocStr elements using case-variant matching
        loc_elements = list(iter_locstr_elements(root))
        element_tag = loc_elements[0].tag if loc_elements else 'LocStr'

        # If no LocStr variants found, try String tag and generic StringId lookup
        if not loc_elements:
            loc_elements = list(root.iter('String'))
            element_tag = 'String'
        if not loc_elements:
            loc_elements = [
                el for el in root.iter()
                if get_attr(el, STRINGID_ATTRS) is not None
            ]
            if loc_elements:
                element_tag = loc_elements[0].tag

        row_num = 0
        for loc in loc_elements:
            row_num += 1

            # Case-variant attribute lookup via XMLParsingEngine helpers
            string_id = get_attr(loc, STRINGID_ATTRS) or ''
            source = normalize_text(get_attr(loc, STRORIGIN_ATTRS) or '')
            target = normalize_text(get_attr(loc, STR_ATTRS) or '')

            # Skip if both source and target are empty
            if not source and not target:
                continue

            # Capture ALL other attributes (excluding core ones)
            extra_attribs = {}
            for key, val in loc.attrib.items():
                if key.lower() not in CORE_ATTRIBUTES:
                    extra_attribs[key] = val

            extra_data = extra_attribs if extra_attribs else None

            rows.append({
                "row_num": row_num,
                "string_id": string_id if string_id.strip() else None,
                "source": source if source else None,
                "target": target if target else None,
                "status": "translated" if target else "pending",
                "extra_data": extra_data
            })

        # Build file-level metadata
        metadata = {
            "encoding": detected_encoding,
            "xml_declaration": xml_declaration,
            "root_element": root_tag,
            "root_attributes": root_attribs,
            "element_tag": element_tag,
            "element_count": row_num,
            "format_version": "1.0"
        }

        logger.info(f"Parsed {filename}: {len(rows)} rows, root=<{root_tag}>, encoding={detected_encoding}")

    except Exception as e:
        logger.error(f"Failed to parse XML file {filename}: {e}")

    return rows, metadata


def get_source_language() -> str:
    """Return the source language for XML files."""
    return "KR"  # Korean is source


def get_file_format() -> str:
    """Return the file format identifier."""
    return "XML"
