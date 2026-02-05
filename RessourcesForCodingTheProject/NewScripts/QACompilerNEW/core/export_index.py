"""
Export Index Module
===================
Build and cache SoundEventName -> (StringId, StrOrigin) mapping from EXPORT folder.

Used by MasterSubmitScript generator to map EventName from QA files
to StringId and Korean text from EXPORT files.
"""

from pathlib import Path
from typing import Dict, Optional
from lxml import etree as ET

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import EXPORT_FOLDER


# Module-level cache
_SOUNDEVENT_MAPPING: Optional[Dict[str, Dict[str, str]]] = None


def build_soundevent_mapping(export_folder: Path) -> Dict[str, Dict[str, str]]:
    """
    Scan Dialog/ + Sequencer/ subfolders for .loc.xml files.
    Extract LocStr elements with SoundEventName, StringId, StrOrigin.

    Args:
        export_folder: Path to EXPORT folder

    Returns:
        {soundeventname_lowercase: {"stringid": X, "strorigin": Y}}
    """
    mapping: Dict[str, Dict[str, str]] = {}

    if not export_folder.exists():
        print(f"  WARNING: EXPORT folder not found: {export_folder}")
        return mapping

    # Scan Dialog/ and Sequencer/ subfolders
    subfolders = ["Dialog", "Sequencer"]
    files_scanned = 0
    entries_found = 0

    for subfolder_name in subfolders:
        # Case-insensitive folder matching
        subfolder = None
        for item in export_folder.iterdir():
            if item.is_dir() and item.name.lower() == subfolder_name.lower():
                subfolder = item
                break

        if not subfolder:
            continue

        # Scan all .loc.xml files recursively
        for xml_path in subfolder.rglob("*.loc.xml"):
            if not xml_path.is_file():
                continue

            files_scanned += 1
            try:
                tree = ET.parse(str(xml_path))
                root = tree.getroot()

                # Find all LocStr elements
                for elem in root.iter("LocStr"):
                    # Case-insensitive attribute access
                    string_id = (
                        elem.get("StringId") or elem.get("StringID") or
                        elem.get("stringid") or elem.get("STRINGID")
                    )
                    sound_event = (
                        elem.get("SoundEventName") or elem.get("Soundeventname") or
                        elem.get("soundeventname") or elem.get("SOUNDEVENTNAME") or
                        elem.get("EventName") or elem.get("eventname") or elem.get("EVENTNAME")
                    )
                    str_origin = (
                        elem.get("StrOrigin") or elem.get("Strorigin") or
                        elem.get("strorigin") or elem.get("STRORIGIN")
                    )

                    if sound_event and string_id:
                        key = sound_event.strip().lower()
                        mapping[key] = {
                            "stringid": string_id.strip(),
                            "strorigin": str_origin.strip() if str_origin else ""
                        }
                        entries_found += 1

            except ET.XMLSyntaxError:
                continue
            except Exception:
                continue

    print(f"  EXPORT index: scanned {files_scanned} files, found {entries_found} SoundEventName entries")
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
