"""
Korean MISS String Extractor.

Extract Korean strings from target XML that do NOT exist in source XML.
Used to identify untranslated or missing localization entries.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Try lxml first (more robust), fallback to standard library
try:
    from lxml import etree as ET
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as ET
    USING_LXML = False

from .xml_parser import sanitize_xml_content, iter_locstr_elements
from .text_utils import normalize_text


# Korean character ranges:
# - Hangul Syllables: AC00-D7AF (most common)
# - Hangul Jamo: 1100-11FF (consonants/vowels)
# - Hangul Compatibility Jamo: 3130-318F (compatibility)
KOREAN_FULL_REGEX = re.compile(r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]')


def contains_korean(text: str) -> bool:
    """
    Check if text contains any Korean characters.

    Covers full Korean Unicode ranges:
    - Hangul Syllables (AC00-D7AF)
    - Hangul Jamo (1100-11FF)
    - Hangul Compatibility Jamo (3130-318F)

    Args:
        text: Text to check

    Returns:
        True if text contains Korean characters
    """
    if not text:
        return False
    return bool(KOREAN_FULL_REGEX.search(text))


def normalize_strorigin(text: str) -> str:
    """
    Normalize StrOrigin text for comparison.

    Strips leading/trailing whitespace and collapses multiple spaces.

    Args:
        text: StrOrigin text to normalize

    Returns:
        Normalized text string
    """
    if not text:
        return ""
    # Strip and collapse whitespace
    return re.sub(r'\s+', ' ', text.strip())


def _parse_xml_to_root(xml_path: Path) -> Optional[ET.Element]:
    """
    Parse XML file with sanitization.

    Args:
        xml_path: Path to XML file

    Returns:
        Root element or None if parsing fails
    """
    try:
        content = xml_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # Try with latin-1 fallback
        content = xml_path.read_text(encoding='latin-1')

    content = sanitize_xml_content(content)

    if USING_LXML:
        wrapped = f"<ROOT>\n{content}\n</ROOT>"
        try:
            return ET.fromstring(
                wrapped.encode("utf-8"),
                parser=ET.XMLParser(huge_tree=True)
            )
        except ET.XMLSyntaxError:
            # Try recovery mode
            try:
                return ET.fromstring(
                    wrapped.encode("utf-8"),
                    parser=ET.XMLParser(recover=True, huge_tree=True)
                )
            except Exception:
                return None
    else:
        try:
            return ET.fromstring(content)
        except ET.ParseError:
            return None


def _build_source_lookup(root: ET.Element) -> Set[Tuple[str, str]]:
    """
    Build lookup set of (StringID, normalized_StrOrigin) from source XML.

    Args:
        root: Root element of source XML

    Returns:
        Set of (StringID, normalized_StrOrigin) tuples
    """
    lookup: Set[Tuple[str, str]] = set()

    for elem in iter_locstr_elements(root):
        string_id = elem.get('StringID', '') or elem.get('stringid', '') or ''
        str_origin = elem.get('StrOrigin', '') or elem.get('strorigin', '') or ''

        if string_id:
            normalized_origin = normalize_strorigin(str_origin)
            lookup.add((string_id, normalized_origin))

    return lookup


def _collect_korean_locstr(root: ET.Element) -> List[ET.Element]:
    """
    Collect all LocStr elements where Str attribute contains Korean.

    Args:
        root: Root element of target XML

    Returns:
        List of LocStr elements with Korean text
    """
    korean_elements: List[ET.Element] = []

    for elem in iter_locstr_elements(root):
        str_value = elem.get('Str', '') or elem.get('str', '') or ''

        if contains_korean(str_value):
            korean_elements.append(elem)

    return korean_elements


def _filter_by_excluded_paths(
    elements: List[ET.Element],
    excluded_paths: Optional[List[str]]
) -> Tuple[List[ET.Element], int]:
    """
    Filter out elements whose File attribute starts with excluded paths.

    Args:
        elements: List of LocStr elements
        excluded_paths: List of path prefixes to exclude (e.g., "System/MultiChange")

    Returns:
        Tuple of (filtered elements, count of filtered out)
    """
    if not excluded_paths:
        return elements, 0

    filtered: List[ET.Element] = []
    filtered_count = 0

    for elem in elements:
        file_attr = elem.get('File', '') or elem.get('file', '') or ''
        # Normalize path separators and lowercase for case-insensitive matching
        file_attr_normalized = file_attr.replace('\\', '/').lower()

        excluded = False
        for exc_path in excluded_paths:
            exc_path_normalized = exc_path.replace('\\', '/').lower()
            if file_attr_normalized.startswith(exc_path_normalized):
                excluded = True
                filtered_count += 1
                break

        if not excluded:
            filtered.append(elem)

    return filtered, filtered_count


def _write_output_xml(elements: List[ET.Element], output_path: Path) -> None:
    """
    Write LocStr elements to output XML file.

    Args:
        elements: List of LocStr elements to write
        output_path: Path for output file
    """
    # Build XML content
    lines = ['<?xml version="1.0" encoding="utf-8"?>']
    lines.append('<LocStrList>')

    for elem in elements:
        # Reconstruct LocStr element as string
        attribs = []
        for key, value in elem.attrib.items():
            # Escape special characters in attribute values
            escaped_value = (value
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
            )
            attribs.append(f'{key}="{escaped_value}"')

        attrib_str = ' '.join(attribs)
        lines.append(f'  <LocStr {attrib_str} />')

    lines.append('</LocStrList>')

    # Write to file
    output_path.write_text('\n'.join(lines), encoding='utf-8')


def extract_korean_misses(
    source_file: str,
    target_file: str,
    output_file: str,
    excluded_paths: Optional[List[str]] = None
) -> Dict:
    """
    Extract Korean strings from target that do NOT exist in source.

    Logic:
    1. Parse target file, collect all LocStr nodes with Korean in Str attribute
    2. Parse source file, build (StringID, StrOrigin) lookup
    3. Find HITS: Korean LocStr from target that match source lookup
    4. Collect MISSES: Korean LocStr that did NOT match
    5. Filter by excluded paths
    6. Write remaining MISS nodes to output file

    Args:
        source_file: Path to source XML file
        target_file: Path to target XML file (contains Korean strings to check)
        output_file: Path for output XML file (will contain MISS strings)
        excluded_paths: List of path prefixes to exclude from results
            (e.g., ["System/MultiChange", "System/Gimmick"])

    Returns:
        Dict with statistics:
        {
            "total_target_korean": int,  # Korean strings in target
            "hits": int,                  # Matched with source
            "misses_before_filter": int,  # Misses before path filter
            "filtered_out": int,          # Removed by path filter
            "final_misses": int,          # Written to output
            "excluded_paths_used": list   # Paths that were filtered
        }

    Raises:
        FileNotFoundError: If source or target file doesn't exist
        ValueError: If XML parsing fails
    """
    source_path = Path(source_file)
    target_path = Path(target_file)
    output_path = Path(output_file)

    # Validate input files exist
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_file}")
    if not target_path.exists():
        raise FileNotFoundError(f"Target file not found: {target_file}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse target XML
    target_root = _parse_xml_to_root(target_path)
    if target_root is None:
        raise ValueError(f"Failed to parse target XML: {target_file}")

    # Parse source XML
    source_root = _parse_xml_to_root(source_path)
    if source_root is None:
        raise ValueError(f"Failed to parse source XML: {source_file}")

    # Build source lookup
    source_lookup = _build_source_lookup(source_root)

    # Collect Korean LocStr from target
    korean_elements = _collect_korean_locstr(target_root)
    total_target_korean = len(korean_elements)

    # Find HITS and MISSES
    hits = 0
    misses: List[ET.Element] = []

    for elem in korean_elements:
        string_id = elem.get('StringID', '') or elem.get('stringid', '') or ''
        str_origin = elem.get('StrOrigin', '') or elem.get('strorigin', '') or ''

        normalized_origin = normalize_strorigin(str_origin)
        key = (string_id, normalized_origin)

        if key in source_lookup:
            hits += 1
        else:
            misses.append(elem)

    misses_before_filter = len(misses)

    # Filter by excluded paths
    excluded_paths_list = excluded_paths if excluded_paths else []
    filtered_misses, filtered_out = _filter_by_excluded_paths(misses, excluded_paths_list)

    final_misses = len(filtered_misses)

    # Write output XML
    _write_output_xml(filtered_misses, output_path)

    return {
        "total_target_korean": total_target_korean,
        "hits": hits,
        "misses_before_filter": misses_before_filter,
        "filtered_out": filtered_out,
        "final_misses": final_misses,
        "excluded_paths_used": excluded_paths_list,
    }
