"""
File Parser Module

Parses XML and Excel files to extract LocStr-equivalent entries.
Excel files: looks for StrOrigin+Str columns (case-insensitive headers), or
             falls back to col 0 = StrOrigin, col 1 = Str.
"""
from __future__ import annotations

import os
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass

try:
    from lxml import etree
except ImportError:
    etree = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

from utils.language_utils import normalize_text


@dataclass
class LocStrEntry:
    """Represents a single LocStr entry from the localization files."""
    string_id: str
    str_origin: str   # Korean/source text
    str: str          # Translation
    file_path: str

    def to_dict(self) -> Dict[str, str]:
        return {
            'string_id': self.string_id,
            'str_origin': self.str_origin,
            'str': self.str,
            'file_path': self.file_path
        }


def parse_xml_file(
    file_path: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[LocStrEntry]:
    """
    Parse an XML file and extract LocStr entries.

    Args:
        file_path: Path to the XML file
        progress_callback: Optional callback for progress updates

    Returns:
        List of LocStrEntry objects
    """
    if etree is None:
        raise ImportError("lxml is required for XML parsing")

    entries = []

    try:
        parser = etree.XMLParser(recover=True, resolve_entities=False)
        tree = etree.parse(file_path, parser)

        for locstr in tree.xpath('//LocStr'):
            string_id = locstr.get('StringId', '') or ''
            str_origin = normalize_text(locstr.get('StrOrigin', '') or '')
            str_val = normalize_text(locstr.get('Str', '') or '')

            if str_origin or str_val:
                entries.append(LocStrEntry(
                    string_id=string_id,
                    str_origin=str_origin,
                    str=str_val,
                    file_path=file_path
                ))

    except Exception as e:
        if progress_callback:
            progress_callback(f"Error parsing {file_path}: {e}")

    return entries


def parse_excel_file(
    file_path: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[LocStrEntry]:
    """
    Parse an Excel file and extract LocStr-equivalent entries.

    Column detection (case-insensitive):
    - Looks for 'StrOrigin' and 'Str' headers in row 1
    - Falls back to col 0 = StrOrigin, col 1 = Str if headers not found
    - Also reads 'StringId'/'StringID' if present

    Args:
        file_path: Path to the Excel (.xlsx/.xls) file
        progress_callback: Optional callback for progress updates

    Returns:
        List of LocStrEntry objects
    """
    if openpyxl is None:
        if progress_callback:
            progress_callback(f"openpyxl not available — skipping Excel file: {file_path}")
        return []

    entries = []

    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))
        wb.close()

        if not rows:
            return []

        # Detect column indices from header row
        header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]

        str_origin_idx = next(
            (i for i, h in enumerate(header) if h in ("strorigin", "str_origin")), None
        )
        str_idx = next(
            (i for i, h in enumerate(header) if h == "str"), None
        )
        stringid_idx = next(
            (i for i, h in enumerate(header) if h in ("stringid", "string_id")), None
        )

        # Fall back to positional if headers not found
        data_start = 1
        if str_origin_idx is None or str_idx is None:
            str_origin_idx = 0
            str_idx = 1
            stringid_idx = None
            data_start = 0  # No header row detected

        for row in rows[data_start:]:
            if not row or len(row) <= max(str_origin_idx, str_idx):
                continue

            str_origin_val = row[str_origin_idx]
            str_val = row[str_idx]
            string_id_val = row[stringid_idx] if stringid_idx is not None else ""

            str_origin = normalize_text(str(str_origin_val) if str_origin_val is not None else "")
            str_text = normalize_text(str(str_val) if str_val is not None else "")
            string_id = str(string_id_val).strip() if string_id_val is not None else ""

            if str_origin or str_text:
                entries.append(LocStrEntry(
                    string_id=string_id,
                    str_origin=str_origin,
                    str=str_text,
                    file_path=file_path
                ))

    except Exception as e:
        if progress_callback:
            progress_callback(f"Error reading Excel {file_path}: {e}")

    return entries


def parse_file(
    file_path: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[LocStrEntry]:
    """
    Parse a file (auto-detect format by extension).

    Args:
        file_path: Path to the file
        progress_callback: Optional callback for progress updates

    Returns:
        List of LocStrEntry objects
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".xml":
        return parse_xml_file(file_path, progress_callback)
    elif ext == ".xlsx":
        return parse_excel_file(file_path, progress_callback)
    return []


def parse_multiple_files(
    file_paths: List[str],
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> List[LocStrEntry]:
    """
    Parse multiple files and extract all LocStr entries.

    Args:
        file_paths: List of file paths
        progress_callback: Optional callback(message, current, total)

    Returns:
        Combined list of LocStrEntry objects
    """
    all_entries = []
    total = len(file_paths)

    for idx, file_path in enumerate(file_paths, start=1):
        if progress_callback:
            progress_callback(f"Reading {os.path.basename(file_path)}", idx, total)

        entries = parse_file(file_path)
        all_entries.extend(entries)

    return all_entries


def extract_pairs(entries: List[LocStrEntry]) -> List[Tuple[str, str]]:
    """
    Extract (StrOrigin, Str) pairs from LocStrEntry list.

    Args:
        entries: List of LocStrEntry objects

    Returns:
        List of (source, translation) tuples
    """
    return [(e.str_origin, e.str) for e in entries if e.str_origin and e.str]


def build_stringid_lookup(entries: List[LocStrEntry]) -> Dict[str, Tuple[str, str]]:
    """
    Build a lookup dictionary from StringID to (StrOrigin, Str).

    Args:
        entries: List of LocStrEntry objects

    Returns:
        Dictionary mapping StringID to (source, translation)
    """
    lookup = {}
    for entry in entries:
        if entry.string_id:
            lookup[entry.string_id] = (entry.str_origin, entry.str)
    return lookup
