"""
Sequencer and Folder Indexing.

Build StringID -> StrOrigin mappings from XML files.
Includes context-aware scanning for Quadruple Fallback matching.
"""

import hashlib
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .xml_parser import parse_xml_file
from .text_utils import normalize_for_matching


def _get_attribute_case_insensitive(elem, attr_names: list) -> Optional[str]:
    """Get attribute value trying multiple case variations."""
    for name in attr_names:
        val = elem.get(name)
        if val is not None:
            return val
    return None


def _iter_locstr_case_insensitive(root):
    """Iterate LocStr elements with case-insensitive tag matching."""
    locstr_tags = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']
    for tag in locstr_tags:
        yield from root.iter(tag)


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
            for elem in _iter_locstr_case_insensitive(root):
                string_id = (_get_attribute_case_insensitive(
                    elem, ['StringId', 'StringID', 'stringid', 'STRINGID']
                ) or '').strip()
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
            for elem in _iter_locstr_case_insensitive(root):
                string_id = (_get_attribute_case_insensitive(
                    elem, ['StringId', 'StringID', 'stringid', 'STRINGID']
                ) or '').strip()
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
            for elem in _iter_locstr_case_insensitive(root):
                string_id = (_get_attribute_case_insensitive(
                    elem, ['StringId', 'StringID', 'stringid', 'STRINGID']
                ) or '').strip()
                str_origin = _get_attribute_case_insensitive(
                    elem, ['StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN']
                ) or ''
                str_value = _get_attribute_case_insensitive(
                    elem, ['Str', 'str', 'STR']
                ) or ''

                if string_id:
                    # Normalize StrOrigin for matching (same as xml_transfer.py)
                    normalized = normalize_for_matching(str_origin)
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


def _compute_adjacency_hash(before: str, after: str) -> str:
    """
    Compute 8-char hex hash of adjacent StrOrigin values.

    Args:
        before: Normalized StrOrigin of previous entry (empty if first)
        after: Normalized StrOrigin of next entry (empty if last)

    Returns:
        8-character hex string
    """
    raw = f"{before}|{after}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]


def scan_folder_for_entries_with_context(
    folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Tuple[List[dict], Dict[tuple, List[dict]], Dict[tuple, List[dict]], Dict[tuple, List[dict]], Dict[str, List[dict]]]:
    """
    Scan folder for XML files and extract entries with adjacency context.

    Builds four index levels for Quadruple Fallback matching:
    - Level 1 (Triple):   (normalized_origin, file_relpath, adjacency_hash) -> entries
    - Level 2A (Double A): (normalized_origin, file_relpath) -> entries
    - Level 2B (Double B): (normalized_origin, adjacency_hash) -> entries
    - Level 3 (Single):   normalized_origin -> entries

    Adjacent entries are the immediate neighbors (N=1) within the same file.

    Args:
        folder: Path to folder to scan
        progress_callback: Optional callback for progress updates

    Returns:
        Tuple of (all_entries, level1_index, level2a_index, level2b_index, level3_index)
    """
    if not folder.exists():
        return [], {}, {}, {}, {}

    all_entries = []
    xml_files = list(folder.rglob("*.xml"))
    total = len(xml_files)

    # First pass: collect raw entries per file, preserving order
    file_entries = {}  # xml_file -> list of entry dicts in document order

    for i, xml_file in enumerate(xml_files):
        if progress_callback:
            progress_callback(f"Scanning with context... {i+1}/{total}")

        try:
            root = parse_xml_file(xml_file)
            entries_in_file = []

            for elem in _iter_locstr_case_insensitive(root):
                string_id = (_get_attribute_case_insensitive(
                    elem, ['StringId', 'StringID', 'stringid', 'STRINGID']
                ) or '').strip()
                str_origin = _get_attribute_case_insensitive(
                    elem, ['StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN']
                ) or ''
                str_value = _get_attribute_case_insensitive(
                    elem, ['Str', 'str', 'STR']
                ) or ''

                if string_id:
                    # Compute relative path from folder root
                    try:
                        file_relpath = str(xml_file.relative_to(folder))
                    except ValueError:
                        file_relpath = xml_file.name

                    entries_in_file.append({
                        "string_id": string_id,
                        "str_origin": str_origin,
                        "str_value": str_value,
                        "source_file": str(xml_file),
                        "filename": xml_file.name,
                        "file_relpath": file_relpath,
                    })

            if entries_in_file:
                file_entries[xml_file] = entries_in_file

        except Exception:
            continue

    # Second pass: enrich with adjacency context and build indexes
    level1_index = {}   # (norm_origin, file_relpath, adj_hash) -> [entries]
    level2a_index = {}  # (norm_origin, file_relpath) -> [entries]
    level2b_index = {}  # (norm_origin, adj_hash) -> [entries]
    level3_index = {}   # norm_origin -> [entries]

    for xml_file, entries_in_file in file_entries.items():
        n = len(entries_in_file)

        for idx, entry in enumerate(entries_in_file):
            norm_origin = normalize_for_matching(entry["str_origin"])

            # Get adjacent StrOrigin values (N=1 neighbors)
            before_origin = ""
            after_origin = ""

            if idx > 0:
                before_origin = normalize_for_matching(
                    entries_in_file[idx - 1]["str_origin"]
                )
            if idx < n - 1:
                after_origin = normalize_for_matching(
                    entries_in_file[idx + 1]["str_origin"]
                )

            adj_hash = _compute_adjacency_hash(before_origin, after_origin)

            # Enrich entry with context
            entry["adjacent_before"] = before_origin
            entry["adjacent_after"] = after_origin
            entry["adjacency_hash"] = adj_hash
            entry["norm_origin"] = norm_origin

            all_entries.append(entry)

            # Build Level 1 key: (norm_origin, file_relpath, adj_hash)
            key1 = (norm_origin, entry["file_relpath"], adj_hash)
            level1_index.setdefault(key1, []).append(entry)

            # Build Level 2A key: (norm_origin, file_relpath)
            key2a = (norm_origin, entry["file_relpath"])
            level2a_index.setdefault(key2a, []).append(entry)

            # Build Level 2B key: (norm_origin, adj_hash)
            key2b = (norm_origin, adj_hash)
            level2b_index.setdefault(key2b, []).append(entry)

            # Build Level 3 key: norm_origin
            level3_index.setdefault(norm_origin, []).append(entry)

    return all_entries, level1_index, level2a_index, level2b_index, level3_index
