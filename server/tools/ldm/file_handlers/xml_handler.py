"""
LDM XML File Handler

Parses XML localization files with LocStr elements via XMLParsingEngine (lxml).
- StringId attribute: String identifier (case-variant lookup)
- StrOrigin attribute: Source text (Korean/Original)
- Str attribute: Target text (Translation)
- All other attributes: Preserved in extra_data for full reconstruction

Dual UI mode:
- Translator files (LocStr nodes): Parsed into source/target rows for CAT tool
- Game Dev files (non-LocStr): Parsed into flat structural rows for grid display

Returns tuple of (rows, metadata) for database insertion and file reconstruction.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from lxml import etree
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


def _format_attributes(elem: etree._Element, max_attrs: int = 3) -> str:
    """Format first N attributes as 'key=value, key=value'. Adds '...' if truncated."""
    attribs = list(elem.attrib.items())
    if not attribs:
        return ""
    formatted = [f"{k}={v}" for k, v in attribs[:max_attrs]]
    result = ", ".join(formatted)
    if len(attribs) > max_attrs:
        result += ", ..."
    return result


def _get_depth(elem: etree._Element, root: etree._Element) -> int:
    """Count ancestors from elem up to (but not including) root."""
    depth = 0
    parent = elem.getparent()
    while parent is not None and parent is not root:
        depth += 1
        parent = parent.getparent()
    # Add 1 for the step from root to first child
    if elem is not root:
        depth += 1
    return depth


def parse_gamedev_nodes(root: etree._Element, max_depth: int = 3) -> List[Dict]:
    """
    Parse non-LocStr XML into flat rows for Game Dev grid display.

    Iterates all elements (skipping root, comments, PIs), creating a row per element
    with structural data in extra_data.

    Args:
        root: lxml root element
        max_depth: Maximum depth to traverse (default 3)

    Returns:
        List of row dicts with: row_num, string_id, source, target, status, extra_data
    """
    rows: List[Dict] = []
    row_num = 0

    for elem in root.iter():
        # Skip the root element itself
        if elem is root:
            continue

        # Skip comments and processing instructions (lxml types)
        if isinstance(elem, (etree._Comment, etree._ProcessingInstruction)):
            continue

        depth = _get_depth(elem, root)

        # Respect max_depth
        if depth > max_depth:
            continue

        row_num += 1

        # Build extra_data with structural information
        extra_data = {
            "node_name": elem.tag,
            "attributes": dict(elem.attrib) if elem.attrib else {},
            "values": (elem.text.strip() if elem.text and elem.text.strip() else None),
            "children_count": len(list(elem)),  # Direct children only
            "depth": depth,
        }

        rows.append({
            "row_num": row_num,
            "string_id": None,
            "source": elem.tag,
            "target": _format_attributes(elem),
            "status": "pending",
            "extra_data": extra_data,
        })

    return rows


def parse_xml_file(file_content: bytes, filename: str) -> Tuple[List[Dict], Dict]:
    """
    Parse XML file content and extract rows.

    Detects file type:
    - "translator": LocStr elements found (CAT tool mode)
    - "gamedev": No LocStr elements (Game Dev grid mode)

    Preserves ALL data for full file reconstruction:
    - Core attributes (StringId, StrOrigin, Str) stored in dedicated columns
    - All other attributes stored in extra_data for reconstruction

    Args:
        file_content: Raw file bytes
        filename: Original filename (for logging)

    Returns:
        Tuple of (rows, metadata):
        - rows: List of row dicts with keys: row_num, string_id, source, target, extra_data
        - metadata: Dict with encoding, xml_declaration, root_element, file_type, etc.
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

        # Determine file type based on LocStr presence
        if loc_elements:
            file_type = "translator"
            element_tag = loc_elements[0].tag
        else:
            # Try String tag and generic StringId lookup before declaring gamedev
            loc_elements = list(root.iter('String'))
            if loc_elements:
                file_type = "translator"
                element_tag = 'String'
            else:
                loc_elements = [
                    el for el in root.iter()
                    if get_attr(el, STRINGID_ATTRS) is not None
                ]
                if loc_elements:
                    file_type = "translator"
                    element_tag = loc_elements[0].tag
                else:
                    file_type = "gamedev"
                    element_tag = None

        # Parse based on file type
        if file_type == "gamedev":
            rows = parse_gamedev_nodes(root)
            element_tag = rows[0]["source"] if rows else None
            row_count = len(rows)
        else:
            # Translator mode: existing LocStr parsing logic
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
            row_count = row_num

        # Build file-level metadata
        metadata = {
            "encoding": detected_encoding,
            "xml_declaration": xml_declaration,
            "root_element": root_tag,
            "root_attributes": root_attribs,
            "element_tag": element_tag,
            "element_count": row_count,
            "format_version": "1.0",
            "file_type": file_type,
        }

        logger.info(f"Parsed {filename}: {len(rows)} rows, type={file_type}, root=<{root_tag}>, encoding={detected_encoding}")

    except Exception as e:
        logger.error(f"Failed to parse XML file {filename}: {e}")

    return rows, metadata


def get_source_language() -> str:
    """Return the source language for XML files."""
    return "KR"  # Korean is source


def get_file_format() -> str:
    """Return the file format identifier."""
    return "XML"
