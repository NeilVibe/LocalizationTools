"""
XML/TXT Parser Module

Parses XML and TXT/TSV files to extract LocStr entries with StringID support.
"""

import os
import csv
from typing import List, Dict, Optional, Tuple, Callable, Any
from dataclasses import dataclass

try:
    from lxml import etree
except ImportError:
    etree = None

import pandas as pd

try:
    from utils.language_utils import normalize_text, tokenize
except ImportError:
    from ..utils.language_utils import normalize_text, tokenize


@dataclass
class LocStrEntry:
    """Represents a single LocStr entry from the localization files."""
    string_id: str
    str_origin: str  # Korean/source text
    str: str  # Translation
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


def parse_txt_file(
    file_path: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[LocStrEntry]:
    """
    Parse a TXT/TSV file and extract LocStr-equivalent entries.

    Expected format: Tab-separated with at least 7 columns
    - Columns 0-4: StringID components (joined with space)
    - Column 5: Korean/source text (StrOrigin)
    - Column 6: Translation (Str)

    Args:
        file_path: Path to the TXT/TSV file
        progress_callback: Optional callback for progress updates

    Returns:
        List of LocStrEntry objects
    """
    entries = []

    try:
        df = pd.read_csv(
            file_path,
            delimiter="\t",
            header=None,
            dtype=str,
            quoting=csv.QUOTE_NONE,
            quotechar=None,
            escapechar=None,
            na_values=[''],
            keep_default_na=False
        )

        if len(df.columns) < 7:
            if progress_callback:
                progress_callback(f"Warning: {file_path} has only {len(df.columns)} columns, expected at least 7")
            return entries

        for _, row in df.iterrows():
            # Build StringID from first 5 columns
            string_id = " ".join(str(x).strip() if pd.notna(x) else '' for x in row[0:5])
            str_origin = normalize_text(str(row[5]) if pd.notna(row[5]) else "")
            str_val = normalize_text(str(row[6]) if pd.notna(row[6]) else "")

            if str_origin or str_val:
                entries.append(LocStrEntry(
                    string_id=string_id,
                    str_origin=str_origin,
                    str=str_val,
                    file_path=file_path
                ))

    except Exception as e:
        if progress_callback:
            progress_callback(f"Error reading {file_path}: {e}")

    return entries


def parse_file(
    file_path: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[LocStrEntry]:
    """
    Parse a file (auto-detect format) and extract LocStr entries.

    Args:
        file_path: Path to the file
        progress_callback: Optional callback for progress updates

    Returns:
        List of LocStrEntry objects
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.xml':
        return parse_xml_file(file_path, progress_callback)
    elif ext in ('.txt', '.tsv'):
        return parse_txt_file(file_path, progress_callback)
    else:
        if progress_callback:
            progress_callback(f"Skipping unsupported file type: {file_path}")
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


def parse_folder(
    folder_path: str,
    recursive: bool = True,
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> List[LocStrEntry]:
    """
    Parse all supported files in a folder.

    Args:
        folder_path: Path to the folder
        recursive: Whether to search recursively
        progress_callback: Optional callback(message, current, total)

    Returns:
        Combined list of LocStrEntry objects
    """
    file_paths = []

    if recursive:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.xml', '.txt', '.tsv')):
                    file_paths.append(os.path.join(root, file))
    else:
        for file in os.listdir(folder_path):
            if file.lower().endswith(('.xml', '.txt', '.tsv')):
                file_paths.append(os.path.join(folder_path, file))

    return parse_multiple_files(file_paths, progress_callback)


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
