"""
LDM XML File Handler

Parses XML localization files with LocStr elements:
- StringId attribute: String identifier
- StrOrigin attribute: Source text (Korean/Original)
- Str attribute: Target text (Translation)
- All other attributes: Preserved in extra_data for full reconstruction

Returns list of row dicts ready for database insertion.
Also returns file-level metadata for full file reconstruction.
"""

import xml.etree.ElementTree as ET
import re
from typing import List, Dict
from loguru import logger

# Factor Power: Use centralized text utils
from server.utils.text_utils import normalize_text


# Module-level state for file metadata
_file_metadata: Dict = {}


# Core attributes that are stored in dedicated columns (case-insensitive matching)
CORE_ATTRIBUTES = {'stringid', 'strorigin', 'str'}


def parse_xml_file(file_content: bytes, filename: str) -> List[Dict]:
    """
    Parse XML file content and extract rows.

    Preserves ALL data for full file reconstruction:
    - Core attributes (StringId, StrOrigin, Str) stored in dedicated columns
    - All other attributes stored in extra_data for reconstruction

    XML Format expected:
    <Root>
      <LocStr StringId="xxx" StrOrigin="Korean text" Str="Translation" OtherAttr="..." />
      ...
    </Root>

    Args:
        file_content: Raw file bytes
        filename: Original filename (for logging)

    Returns:
        List of row dicts with keys: row_num, string_id, source, target, extra_data
    """
    global _file_metadata
    rows = []
    detected_encoding = None

    try:
        # Decode with multiple fallbacks
        text_content = None
        for encoding in ['utf-8', 'utf-16', 'cp1252', 'iso-8859-1']:
            try:
                text_content = file_content.decode(encoding)
                detected_encoding = encoding
                break
            except UnicodeDecodeError:
                continue

        if text_content is None:
            logger.error(f"Could not decode file {filename}")
            return rows

        # Extract XML declaration if present
        xml_declaration = None
        decl_match = re.match(r'(<\?xml[^?]*\?>)', text_content)
        if decl_match:
            xml_declaration = decl_match.group(1)

        # Parse XML
        root = ET.fromstring(text_content)

        # Store root element info
        root_tag = root.tag
        root_attribs = dict(root.attrib) if root.attrib else None

        # Find the element tag used for localization strings
        # Try common patterns: LocStr, String, etc.
        loc_elements = root.findall('.//LocStr')
        element_tag = 'LocStr'
        if not loc_elements:
            loc_elements = root.findall('.//String')
            element_tag = 'String'
        if not loc_elements:
            # Try any element with StringId attribute
            loc_elements = [el for el in root.iter() if 'StringId' in el.attrib or 'stringid' in {k.lower() for k in el.attrib}]
            if loc_elements:
                element_tag = loc_elements[0].tag

        row_num = 0
        for loc in loc_elements:
            row_num += 1

            # Case-insensitive attribute lookup
            attribs = loc.attrib
            attrib_lower_map = {k.lower(): k for k in attribs}

            # Extract core attributes (case-insensitive)
            string_id_key = attrib_lower_map.get('stringid', 'StringId')
            strorigin_key = attrib_lower_map.get('strorigin', 'StrOrigin')
            str_key = attrib_lower_map.get('str', 'Str')

            string_id = attribs.get(string_id_key, '') or ''
            source = normalize_text(attribs.get(strorigin_key, '') or '')
            target = normalize_text(attribs.get(str_key, '') or '')

            # Skip if both source and target are empty
            if not source and not target:
                continue

            # Capture ALL other attributes (excluding core ones)
            extra_attribs = {}
            for key, val in attribs.items():
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

        # Store file-level metadata for reconstruction
        _file_metadata = {
            "encoding": detected_encoding,
            "xml_declaration": xml_declaration,
            "root_element": root_tag,
            "root_attributes": root_attribs,
            "element_tag": element_tag,
            "element_count": row_num,
            "format_version": "1.0"
        }

        logger.info(f"Parsed {filename}: {len(rows)} rows, root=<{root_tag}>, encoding={detected_encoding}")

    except ET.ParseError as e:
        logger.error(f"XML parse error in {filename}: {e}")
    except Exception as e:
        logger.error(f"Failed to parse XML file {filename}: {e}")

    return rows


def get_file_metadata() -> Dict:
    """
    Get file-level metadata for full reconstruction.

    Returns dict with:
    - encoding: Detected file encoding
    - xml_declaration: Original <?xml ...?> if present
    - root_element: Root element tag name
    - root_attributes: Root element attributes
    - element_tag: Tag name used for localization elements
    """
    global _file_metadata
    return _file_metadata.copy()


def get_source_language() -> str:
    """Return the source language for XML files."""
    return "KR"  # Korean is source


def get_file_format() -> str:
    """Return the file format identifier."""
    return "XML"
