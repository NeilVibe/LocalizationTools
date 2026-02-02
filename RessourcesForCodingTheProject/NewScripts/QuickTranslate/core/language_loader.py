"""
Language File Discovery and Lookup Building.

Discover languagedata_*.xml files and build translation lookups.
"""

import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .xml_parser import parse_xml_file


def discover_language_files(loc_folder: Path) -> Dict[str, Path]:
    """
    Find all languagedata_*.xml files in the loc folder.

    Args:
        loc_folder: Path to loc folder containing language files

    Returns:
        Dict mapping language code (lowercase) to file path
    """
    if not loc_folder.exists():
        return {}

    lang_files = {}
    for xml_file in loc_folder.glob("languagedata_*.xml"):
        match = re.match(r'languagedata_(.+)\.xml', xml_file.name, re.IGNORECASE)
        if match:
            lang_code = match.group(1).lower()
            lang_files[lang_code] = xml_file

    return lang_files


def build_translation_lookup(
    lang_files: Dict[str, Path],
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Dict[str, str]]:
    """
    Parse all language files and build StringID -> translation lookup.

    Args:
        lang_files: Dict mapping language code to file path
        progress_callback: Optional callback for progress updates

    Returns:
        Dict mapping language code to {StringID: translation} dict
    """
    lookup = {}
    total = len(lang_files)

    for i, (lang_code, xml_path) in enumerate(lang_files.items()):
        if progress_callback:
            progress_callback(f"Loading {lang_code.upper()}... {i+1}/{total}")
        lookup[lang_code] = {}

        try:
            root = parse_xml_file(xml_path)
            for elem in root.iter('LocStr'):
                string_id = (elem.get('StringId') or elem.get('StringID') or
                            elem.get('stringid') or elem.get('STRINGID'))
                str_value = (elem.get('Str') or elem.get('str') or
                            elem.get('STR') or '')

                if string_id:
                    lookup[lang_code][string_id] = str_value
        except Exception:
            continue

    return lookup


def build_reverse_lookup(
    translation_lookup: Dict[str, Dict[str, str]]
) -> Dict[str, Dict[str, str]]:
    """
    Build reverse lookup: {lang_code: {translation_text: StringID}}.

    This allows finding StringID from any translation text.

    Args:
        translation_lookup: Dict from build_translation_lookup()

    Returns:
        Dict mapping language code to {text: StringID} dict
    """
    reverse = {}
    for lang_code, id_to_text in translation_lookup.items():
        reverse[lang_code] = {}
        for string_id, text in id_to_text.items():
            if text and text.strip():
                # Store text -> StringID (trimmed for matching)
                reverse[lang_code][text.strip()] = string_id
    return reverse


def build_stringid_to_category(
    export_folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, str]:
    """
    Build StringID -> Category mapping from export folder structure.

    Categories are determined by subfolder names (Sequencer, UI, Items, etc.)

    Args:
        export_folder: Path to export__ folder
        progress_callback: Optional callback for progress updates

    Returns:
        Dict mapping StringID to category name
    """
    if not export_folder.exists():
        return {}

    stringid_to_category = {}

    # Get all subfolders (categories)
    categories = [d for d in export_folder.iterdir() if d.is_dir()]

    for category_folder in categories:
        category_name = category_folder.name
        xml_files = list(category_folder.rglob("*.loc.xml"))

        if progress_callback:
            progress_callback(f"Indexing {category_name}...")

        for xml_file in xml_files:
            try:
                root = parse_xml_file(xml_file)
                for elem in root.iter('LocStr'):
                    string_id = (elem.get('StringId') or elem.get('StringID') or
                                elem.get('stringid') or elem.get('STRINGID'))
                    if string_id:
                        stringid_to_category[string_id] = category_name
            except Exception:
                continue

    return stringid_to_category
