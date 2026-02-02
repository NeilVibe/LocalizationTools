"""
XML Input Parsing.

Parse corrections from XML files for transfer mode.
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional

from .xml_parser import parse_xml_file


def parse_corrections_from_xml(xml_path: Path) -> List[Dict]:
    """
    Parse corrections from XML file (LocStr elements).

    Args:
        xml_path: Path to XML file

    Returns:
        List of correction dicts with keys: string_id, str_origin, corrected
    """
    corrections = []

    try:
        root = parse_xml_file(xml_path)
        for elem in root.iter('LocStr'):
            string_id = (elem.get('StringId') or elem.get('StringID') or
                        elem.get('stringid') or elem.get('STRINGID') or '').strip()
            str_origin = (elem.get('StrOrigin') or elem.get('Strorigin') or
                         elem.get('strorigin') or elem.get('STRORIGIN') or '').strip()
            str_value = (elem.get('Str') or elem.get('str') or
                        elem.get('STR') or '').strip()

            if string_id and str_value:
                corrections.append({
                    "string_id": string_id,
                    "str_origin": str_origin,
                    "corrected": str_value,
                })
    except Exception:
        pass

    return corrections


def parse_folder_xml_files(
    folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[Dict]:
    """
    Recursively scan folder for XML files and extract corrections.

    Args:
        folder: Path to folder to scan
        progress_callback: Optional callback for progress updates

    Returns:
        List of all corrections from all XML files
    """
    if not folder.exists():
        return []

    all_corrections = []
    xml_files = list(folder.rglob("*.xml"))
    total = len(xml_files)

    for i, xml_file in enumerate(xml_files):
        if progress_callback:
            progress_callback(f"Parsing XML files... {i+1}/{total}")

        corrections = parse_corrections_from_xml(xml_file)
        for c in corrections:
            c["source_file"] = str(xml_file)
        all_corrections.extend(corrections)

    return all_corrections


def parse_tosubmit_xml(tosubmit_folder: Path) -> List[Dict]:
    """
    Parse corrections from ToSubmit folder structure.

    ToSubmit folder contains XML files organized by category.

    Args:
        tosubmit_folder: Path to ToSubmit folder

    Returns:
        List of corrections with source file info
    """
    if not tosubmit_folder.exists():
        return []

    return parse_folder_xml_files(tosubmit_folder)


def extract_stringids_from_xml(xml_path: Path) -> List[str]:
    """
    Extract just StringIDs from an XML file.

    Args:
        xml_path: Path to XML file

    Returns:
        List of StringIDs
    """
    string_ids = []

    try:
        root = parse_xml_file(xml_path)
        for elem in root.iter('LocStr'):
            string_id = (elem.get('StringId') or elem.get('StringID') or
                        elem.get('stringid') or elem.get('STRINGID') or '').strip()
            if string_id:
                string_ids.append(string_id)
    except Exception:
        pass

    return string_ids
