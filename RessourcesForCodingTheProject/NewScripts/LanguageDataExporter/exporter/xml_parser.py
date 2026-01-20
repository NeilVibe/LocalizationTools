"""
XML Parser for language data files.

Parses languagedata_*.xml files and extracts LocStr elements.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


def sanitize_xml_content(content: str) -> str:
    """
    Sanitize XML content to handle common issues.

    Handles:
    - Unescaped ampersands
    - Invalid XML characters
    - Malformed CDATA sections
    """
    # Replace unescaped ampersands (but not already-escaped ones)
    content = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', content)

    # Remove invalid XML characters (control chars except tab, newline, carriage return)
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)

    return content


def parse_language_file(xml_path: Path) -> List[Dict]:
    """
    Parse languagedata_*.xml and extract LocStr elements.

    Args:
        xml_path: Path to the language XML file

    Returns:
        List of dictionaries with:
        - str_origin: Original Korean text
        - str: Translated text
        - string_id: The StringID

    Example return:
        [
            {"str_origin": "몬스터", "str": "Monster", "string_id": "1001"},
            {"str_origin": "철검", "str": "Iron Sword", "string_id": "2001"},
        ]
    """
    if not xml_path.exists():
        logger.error(f"Language file not found: {xml_path}")
        return []

    try:
        # Read and sanitize content
        content = xml_path.read_text(encoding='utf-8')
        content = sanitize_xml_content(content)

        # Parse XML
        root = ET.fromstring(content)

        entries = []

        # Find all LocStr elements
        # Structure: <LocStrTable><LocStr StringID="..." StrOrigin="..." Str="..."/></LocStrTable>
        for loc_str in root.iter('LocStr'):
            string_id = loc_str.get('StringID', '')
            str_origin = loc_str.get('StrOrigin', '')
            str_value = loc_str.get('Str', '')

            if string_id:  # Only include if we have a StringID
                entries.append({
                    'str_origin': str_origin,
                    'str': str_value,
                    'string_id': string_id,
                })

        logger.info(f"Parsed {len(entries)} entries from {xml_path.name}")
        return entries

    except ET.ParseError as e:
        logger.error(f"XML parse error in {xml_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error parsing {xml_path}: {e}")
        return []


def discover_language_files(loc_folder: Path) -> Dict[str, Path]:
    """
    Find all languagedata_*.xml files in the LOC folder.

    Args:
        loc_folder: Path to the LOC folder

    Returns:
        Dictionary mapping language code to file path:
        {"eng": Path(...), "fre": Path(...), "zho-cn": Path(...)}
    """
    if not loc_folder.exists():
        logger.error(f"LOC folder not found: {loc_folder}")
        return {}

    lang_files = {}

    # Pattern: languagedata_XXX.xml or languagedata_XXX-YY.xml
    for xml_file in loc_folder.glob("languagedata_*.xml"):
        # Extract language code from filename
        # languagedata_eng.xml -> eng
        # languagedata_zho-cn.xml -> zho-cn
        match = re.match(r'languagedata_(.+)\.xml', xml_file.name, re.IGNORECASE)
        if match:
            lang_code = match.group(1).lower()
            lang_files[lang_code] = xml_file
            logger.debug(f"Found language file: {lang_code} -> {xml_file}")

    logger.info(f"Discovered {len(lang_files)} language files in {loc_folder}")
    return lang_files


def parse_export_file(xml_path: Path) -> List[str]:
    """
    Parse an EXPORT .loc.xml file and extract all StringIDs.

    Args:
        xml_path: Path to the .loc.xml file

    Returns:
        List of StringIDs found in the file
    """
    if not xml_path.exists():
        logger.warning(f"EXPORT file not found: {xml_path}")
        return []

    try:
        # Read and sanitize content
        content = xml_path.read_text(encoding='utf-8')
        content = sanitize_xml_content(content)

        # Parse XML
        root = ET.fromstring(content)

        string_ids = []

        # Find all elements with StringID attribute
        for elem in root.iter():
            string_id = elem.get('StringID')
            if string_id:
                string_ids.append(string_id)

        return string_ids

    except ET.ParseError as e:
        logger.warning(f"XML parse error in EXPORT file {xml_path}: {e}")
        return []
    except Exception as e:
        logger.warning(f"Error parsing EXPORT file {xml_path}: {e}")
        return []
