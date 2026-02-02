"""
Sequencer and Folder Indexing.

Build StringID -> StrOrigin mappings from XML files.
"""

from pathlib import Path
from typing import Callable, Dict, Optional

from .xml_parser import parse_xml_file


def _get_attribute_case_insensitive(elem, attr_names: list) -> Optional[str]:
    """Get attribute value trying multiple case variations."""
    for name in attr_names:
        val = elem.get(name)
        if val is not None:
            return val
    return None


def build_sequencer_strorigin_index(
    sequencer_folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, str]:
    """
    Scan Sequencer/*.loc.xml files and build StringID->StrOrigin mapping.

    Args:
        sequencer_folder: Path to Sequencer folder
        progress_callback: Optional callback for progress updates

    Returns:
        Dict mapping StringID to StrOrigin
    """
    if not sequencer_folder.exists():
        return {}

    index = {}
    xml_files = list(sequencer_folder.rglob("*.loc.xml"))
    total = len(xml_files)

    for i, xml_file in enumerate(xml_files):
        if progress_callback:
            progress_callback(f"Indexing Sequencer... {i+1}/{total}")
        try:
            root = parse_xml_file(xml_file)
            for elem in root.iter('LocStr'):
                string_id = _get_attribute_case_insensitive(
                    elem, ['StringId', 'StringID', 'stringid', 'STRINGID']
                )
                str_origin = _get_attribute_case_insensitive(
                    elem, ['StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN']
                ) or ''

                if string_id and str_origin:
                    index[string_id] = str_origin
        except Exception:
            continue

    return index


def scan_folder_for_strings(
    folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, str]:
    """
    Recursively scan folder for XML files and extract StringID -> StrOrigin mapping.

    Scans ALL .xml files (not just .loc.xml) to maximize coverage.

    Args:
        folder: Path to folder to scan
        progress_callback: Optional callback for progress updates

    Returns:
        Dict mapping StringID to StrOrigin
    """
    if not folder.exists():
        return {}

    string_map = {}
    xml_files = list(folder.rglob("*.xml"))
    total = len(xml_files)

    for i, xml_file in enumerate(xml_files):
        if progress_callback:
            progress_callback(f"Scanning folder... {i+1}/{total}")
        try:
            root = parse_xml_file(xml_file)
            for elem in root.iter('LocStr'):
                string_id = _get_attribute_case_insensitive(
                    elem, ['StringId', 'StringID', 'stringid', 'STRINGID']
                )
                str_origin = _get_attribute_case_insensitive(
                    elem, ['StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN']
                ) or ''

                if string_id and str_origin:
                    string_map[string_id] = str_origin
        except Exception:
            continue

    return string_map


def scan_folder_for_entries(
    folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[tuple, dict]:
    """
    Scan folder for XML files and extract full entry data.

    Returns dict keyed by (StringID, normalized_StrOrigin) tuple.

    Args:
        folder: Path to folder to scan
        progress_callback: Optional callback for progress updates

    Returns:
        Dict mapping (StringID, StrOrigin) tuple to entry dict
    """
    if not folder.exists():
        return {}

    entries = {}
    xml_files = list(folder.rglob("*.xml"))
    total = len(xml_files)

    for i, xml_file in enumerate(xml_files):
        if progress_callback:
            progress_callback(f"Scanning folder... {i+1}/{total}")
        try:
            root = parse_xml_file(xml_file)
            for elem in root.iter('LocStr'):
                string_id = _get_attribute_case_insensitive(
                    elem, ['StringId', 'StringID', 'stringid', 'STRINGID']
                )
                str_origin = _get_attribute_case_insensitive(
                    elem, ['StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN']
                ) or ''
                str_value = _get_attribute_case_insensitive(
                    elem, ['Str', 'str', 'STR']
                ) or ''

                if string_id:
                    # Normalize StrOrigin for matching
                    normalized = str_origin.strip().lower()
                    key = (string_id, normalized)
                    entries[key] = {
                        "string_id": string_id,
                        "str_origin": str_origin,
                        "str_value": str_value,
                        "source_file": str(xml_file),
                    }
        except Exception:
            continue

    return entries
