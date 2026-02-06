"""
Export Index Module
===================
Build and cache SoundEventName -> (StringId, StrOrigin) mapping from EXPORT folder.

Used by MasterSubmitScript generator to map EventName from QA files
to StringId and Korean text from EXPORT files.

Uses the same robust XML parsing as eventname_to_stringid.py:
- Strips BOM/DTD/encoding issues before parsing
- Uses recover=True parser for malformed XML
- Scans ALL elements (not just LocStr)
- Scans ALL .xml files recursively
"""

import re
from pathlib import Path
from typing import Dict, Optional
from lxml import etree

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import EXPORT_FOLDER


# Module-level cache
_SOUNDEVENT_MAPPING: Optional[Dict[str, Dict[str, str]]] = None


def _robust_parse_xml(path: Path):
    """Parse XML ignoring BOM/DTD/encoding issues (same as eventname_to_stringid.py)."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()

        content = re.sub(r'^<\?xml[^>]*\?>\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'<!DOCTYPE[^>]*>\s*', '', content, flags=re.MULTILINE)

        parser = etree.XMLParser(resolve_entities=False, load_dtd=False,
                                  no_network=True, recover=True)
        root = etree.fromstring(content.encode("utf-8"), parser=parser)
        return root
    except Exception:
        return None


def build_soundevent_mapping(export_folder: Path) -> Dict[str, Dict[str, str]]:
    """
    Scan ALL XML files in EXPORT folder recursively.
    Look for SoundEventName, StringId, and StrOrigin ATTRIBUTES on any element.

    Same logic as eventname_to_stringid.py standalone script.

    Args:
        export_folder: Path to EXPORT folder

    Returns:
        {soundeventname_lowercase: {"stringid": X, "strorigin": Y}}
    """
    mapping: Dict[str, Dict[str, str]] = {}

    if not export_folder.exists():
        print(f"  WARNING: EXPORT folder not found: {export_folder}")
        return mapping

    xml_files = list(export_folder.rglob("*.xml"))
    files_scanned = 0
    entries_found = 0

    print(f"  Scanning {len(xml_files)} XML files in EXPORT folder...")

    for idx, xml_path in enumerate(xml_files, 1):
        if idx % 500 == 0:
            print(f"    Processed {idx}/{len(xml_files)} files...")

        if not xml_path.is_file():
            continue

        files_scanned += 1
        root = _robust_parse_xml(xml_path)
        if root is None:
            continue

        # Iterate ALL elements, get ATTRIBUTES (same as standalone script)
        for node in root.iter():
            se = (node.get("SoundEventName") or node.get("soundeventname") or
                  node.get("EventName") or node.get("eventname") or "").strip()
            sid = (node.get("StringId") or node.get("StringID") or
                   node.get("stringid") or "").strip()
            strorigin = (node.get("StrOrigin") or node.get("Strorigin") or
                         node.get("strorigin") or "").strip()

            if se and sid:
                mapping[se.lower()] = {"stringid": sid, "strorigin": strorigin}
                entries_found += 1

    print(f"  EXPORT index: scanned {files_scanned} files, found {entries_found} entries, {len(mapping)} unique EventNames")
    return mapping


def clear_soundevent_cache() -> None:
    """Clear the cached SoundEventName mapping. Call if EXPORT folder contents changed."""
    global _SOUNDEVENT_MAPPING
    _SOUNDEVENT_MAPPING = None


def get_soundevent_mapping() -> Dict[str, Dict[str, str]]:
    """
    Lazy-load and cache the SoundEventName mapping.

    Returns:
        {soundeventname_lowercase: {"stringid": X, "strorigin": Y}}
    """
    global _SOUNDEVENT_MAPPING
    if _SOUNDEVENT_MAPPING is None:
        print("  Building EXPORT SoundEventName index...")
        _SOUNDEVENT_MAPPING = build_soundevent_mapping(EXPORT_FOLDER)
    return _SOUNDEVENT_MAPPING


def lookup_by_eventname(event_name: str) -> Optional[Dict[str, str]]:
    """
    Look up StringId and StrOrigin by EventName (case-insensitive).

    Args:
        event_name: EventName from QA file

    Returns:
        {"stringid": X, "strorigin": Y} or None if not found
    """
    if not event_name:
        return None

    mapping = get_soundevent_mapping()
    return mapping.get(event_name.strip().lower())
