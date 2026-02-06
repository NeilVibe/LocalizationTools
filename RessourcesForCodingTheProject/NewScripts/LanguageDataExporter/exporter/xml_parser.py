"""
XML Parser for language data files.

Parses languagedata_*.xml files and extracts LocStr elements.
Uses lxml for robust parsing with recovery mode for malformed XML.

IMPORTANT: Attribute names are case-sensitive!
- StringId (not StringID)
- StrOrigin
- Str
- SoundEventName
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Try lxml first (more robust), fallback to standard library
try:
    from lxml import etree as ET
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as ET
    USING_LXML = False

logger = logging.getLogger(__name__)


# =============================================================================
# XML SANITIZATION (from QACompiler - battle-tested)
# =============================================================================

_bad_entity_re = re.compile(r'&(?!lt;|gt;|amp;|apos;|quot;)')


def _fix_bad_entities(txt: str) -> str:
    """Fix unescaped ampersands."""
    return _bad_entity_re.sub("&amp;", txt)


def _preprocess_newlines(raw: str) -> str:
    """Handle newlines in seg elements."""
    def repl(m: re.Match) -> str:
        inner = m.group(1).replace("\n", "&lt;br/&gt;").replace("\r\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"
    return re.sub(r"<seg>(.*?)</seg>", repl, raw, flags=re.DOTALL)


def sanitize_xml_content(raw: str) -> str:
    """
    Sanitize XML content to handle common issues.

    Uses QACompiler's battle-tested sanitization:
    - Fix unescaped ampersands
    - Handle newlines in segments
    - Fix < and & in attribute values
    - Tag stack repair for malformed XML
    - Remove invalid control characters
    """
    # Remove invalid XML characters (control chars except tab, newline, carriage return)
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)

    # Fix entities
    raw = _fix_bad_entities(raw)
    raw = _preprocess_newlines(raw)

    # Fix < and & in attribute values
    raw = re.sub(r'="([^"]*<[^"]*)"',
                 lambda m: '="' + m.group(1).replace("<", "&lt;") + '"', raw)
    raw = re.sub(r'="([^"]*&[^ltgapoqu][^"]*)"',
                 lambda m: '="' + m.group(1).replace("&", "&amp;") + '"', raw)

    # Tag stack repair for malformed XML
    tag_open = re.compile(r"<([A-Za-z0-9_]+)(\s[^>]*)?>")
    tag_close = re.compile(r"</([A-Za-z0-9_]+)>")
    stack: List[str] = []
    out: List[str] = []

    for line in raw.splitlines():
        stripped = line.strip()
        mo = tag_open.match(stripped)
        if mo:
            stack.append(mo.group(1))
            out.append(line)
            continue
        mc = tag_close.match(stripped)
        if mc:
            if stack and stack[-1] == mc.group(1):
                stack.pop()
                out.append(line)
            else:
                out.append(stack and f"</{stack.pop()}>" or line)
            continue
        if stripped.startswith("</>"):
            out.append(stack and line.replace("</>", f"</{stack.pop()}>") or line)
            continue
        out.append(line)

    while stack:
        out.append(f"</{stack.pop()}>")

    return "\n".join(out)


def parse_language_file(xml_path: Path) -> List[Dict]:
    """
    Parse languagedata_*.xml and extract LocStr elements.

    Args:
        xml_path: Path to the language XML file

    Returns:
        List of dictionaries with:
        - str_origin: Original Korean text
        - str: Translated text
        - string_id: The StringId

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

        # Parse XML (with lxml recovery mode if available)
        if USING_LXML:
            # Wrap in root for safety
            wrapped = f"<ROOT>\n{content}\n</ROOT>"
            try:
                root = ET.fromstring(
                    wrapped.encode("utf-8"),
                    parser=ET.XMLParser(huge_tree=True)
                )
            except ET.XMLSyntaxError:
                # Try recovery mode
                root = ET.fromstring(
                    wrapped.encode("utf-8"),
                    parser=ET.XMLParser(recover=True, huge_tree=True)
                )
        else:
            root = ET.fromstring(content)

        entries = []

        # Find all LocStr elements (try different tag casings)
        loc_str_elements = list(root.iter('LocStr'))
        if not loc_str_elements:
            loc_str_elements = list(root.iter('locstr'))
        if not loc_str_elements:
            loc_str_elements = list(root.iter('LOCSTR'))

        for loc_str in loc_str_elements:
            # Try all case variations for attributes
            string_id = (loc_str.get('StringId') or loc_str.get('StringID') or
                        loc_str.get('stringid') or loc_str.get('STRINGID') or '')
            str_origin = (loc_str.get('StrOrigin') or loc_str.get('Strorigin') or
                         loc_str.get('strorigin') or loc_str.get('STRORIGIN') or '')
            str_value = (loc_str.get('Str') or loc_str.get('str') or
                        loc_str.get('STR') or '')

            if string_id:  # Only include if we have a StringId
                entries.append({
                    'str_origin': str_origin,
                    'str': str_value,
                    'string_id': string_id,
                })

        logger.info(f"Parsed {len(entries)} entries from {xml_path.name}")
        return entries

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
    Parse an EXPORT .loc.xml file and extract all StringIds.

    Args:
        xml_path: Path to the .loc.xml file

    Returns:
        List of StringIds found in the file
    """
    if not xml_path.exists():
        logger.warning(f"EXPORT file not found: {xml_path}")
        return []

    try:
        # Read and sanitize content
        content = xml_path.read_text(encoding='utf-8')
        content = sanitize_xml_content(content)

        # Parse XML (with lxml recovery mode if available)
        if USING_LXML:
            wrapped = f"<ROOT>\n{content}\n</ROOT>"
            try:
                root = ET.fromstring(
                    wrapped.encode("utf-8"),
                    parser=ET.XMLParser(huge_tree=True)
                )
            except ET.XMLSyntaxError:
                root = ET.fromstring(
                    wrapped.encode("utf-8"),
                    parser=ET.XMLParser(recover=True, huge_tree=True)
                )
        else:
            root = ET.fromstring(content)

        string_ids = []

        # Find all LocStr elements (try different tag casings)
        loc_str_elements = list(root.iter('LocStr'))
        if not loc_str_elements:
            loc_str_elements = list(root.iter('locstr'))
        if not loc_str_elements:
            loc_str_elements = list(root.iter('LOCSTR'))

        # Try all case variations for StringId attribute
        for elem in loc_str_elements:
            string_id = (elem.get('StringId') or elem.get('StringID') or
                        elem.get('stringid') or elem.get('STRINGID'))
            if string_id:
                string_ids.append(string_id)

        return string_ids

    except Exception as e:
        logger.warning(f"Error parsing EXPORT file {xml_path}: {e}")
        return []


def parse_export_with_soundevent(xml_path: Path) -> List[Dict]:
    """
    Parse an EXPORT .loc.xml file and extract StringId with SoundEventName.

    Used for VoiceRecordingSheet ordering of STORY strings.

    Args:
        xml_path: Path to the .loc.xml file

    Returns:
        List of dicts with {"string_id", "sound_event"} for entries that have SoundEventName
    """
    if not xml_path.exists():
        logger.warning(f"EXPORT file not found: {xml_path}")
        return []

    try:
        content = xml_path.read_text(encoding='utf-8')
        content = sanitize_xml_content(content)

        # Parse XML (with lxml recovery mode if available)
        if USING_LXML:
            wrapped = f"<ROOT>\n{content}\n</ROOT>"
            try:
                root = ET.fromstring(
                    wrapped.encode("utf-8"),
                    parser=ET.XMLParser(huge_tree=True)
                )
            except ET.XMLSyntaxError:
                root = ET.fromstring(
                    wrapped.encode("utf-8"),
                    parser=ET.XMLParser(recover=True, huge_tree=True)
                )
        else:
            root = ET.fromstring(content)

        results = []

        # Find all LocStr elements (try different tag casings)
        loc_str_elements = list(root.iter('LocStr'))
        if not loc_str_elements:
            loc_str_elements = list(root.iter('locstr'))
        if not loc_str_elements:
            loc_str_elements = list(root.iter('LOCSTR'))

        # Find LocStr elements with both StringId and SoundEventName
        for elem in loc_str_elements:
            # Try all case variations
            string_id = (elem.get('StringId') or elem.get('StringID') or
                        elem.get('stringid') or elem.get('STRINGID'))
            sound_event = (elem.get('SoundEventName') or elem.get('Soundeventname') or
                          elem.get('soundeventname') or elem.get('SOUNDEVENTNAME') or
                          elem.get('EventName') or elem.get('eventname') or elem.get('EVENTNAME'))

            if string_id and sound_event:
                results.append({
                    'string_id': string_id.strip(),
                    'sound_event': sound_event.strip(),
                })

        return results

    except Exception as e:
        logger.warning(f"Error parsing EXPORT file {xml_path}: {e}")
        return []


def _find_folder_case_insensitive(parent: Path, name: str) -> Optional[Path]:
    """
    Find a folder by name, case-insensitively.

    Args:
        parent: Parent directory to search in
        name: Folder name to find (case-insensitive)

    Returns:
        Path to folder if found, None otherwise
    """
    if not parent.exists():
        return None

    name_lower = name.lower()
    try:
        for item in parent.iterdir():
            if item.is_dir() and item.name.lower() == name_lower:
                return item
    except PermissionError:
        pass

    return None


def build_stringid_soundevent_map(export_folder: Path) -> Dict[str, str]:
    """
    Build a mapping of StringID to SoundEventName from EXPORT folder.

    Only includes entries that have a SoundEventName (voiced lines).
    Uses case-insensitive folder matching for cross-platform compatibility.

    Args:
        export_folder: Path to EXPORT folder

    Returns:
        {StringID: SoundEventName} mapping
    """
    if not export_folder.exists():
        logger.error(f"EXPORT folder not found: {export_folder}")
        return {}

    stringid_to_soundevent: Dict[str, str] = {}

    # Only scan Dialog and Sequencer folders (STORY content)
    # Use case-insensitive matching for cross-platform compatibility
    story_folder_names = ["Dialog", "Sequencer"]

    for folder_name in story_folder_names:
        # Find folder case-insensitively
        folder_path = _find_folder_case_insensitive(export_folder, folder_name)
        if folder_path is None:
            logger.debug(f"STORY folder not found: {folder_name}")
            continue

        for xml_file in folder_path.rglob("*.loc.xml"):
            entries = parse_export_with_soundevent(xml_file)
            for entry in entries:
                sid = entry['string_id']
                snd = entry['sound_event']
                if sid not in stringid_to_soundevent:
                    stringid_to_soundevent[sid] = snd

    logger.info(f"Built {len(stringid_to_soundevent)} StringID → SoundEventName mappings")
    return stringid_to_soundevent
