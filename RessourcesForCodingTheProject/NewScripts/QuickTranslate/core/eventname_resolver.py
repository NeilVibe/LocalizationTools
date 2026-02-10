"""
EventName to StringID Resolution.

Resolves EventNames (audio event identifiers like Quest_Complete_001) to StringIDs
by scanning the export__ folder where XML elements have both SoundEventName and StringId attributes.

Ported from QACompilerNEW/eventname_to_stringid.py with adaptations:
- logger instead of print()
- Uses config.EXPORT_FOLDER
- Module-level cache (same pattern as source_scanner._cached_valid_codes)
- xlsxwriter for missing report
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

try:
    from lxml import etree
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as etree
    USING_LXML = False

logger = logging.getLogger(__name__)

# Module-level cache (same pattern as source_scanner._cached_valid_codes)
_cached_mapping: Optional[Dict[str, Dict[str, str]]] = None
_cached_folder: Optional[str] = None


def clear_cache():
    """Clear cached EventName mapping. Call when export folder changes in settings."""
    global _cached_mapping, _cached_folder
    _cached_mapping = None
    _cached_folder = None
    logger.debug("EventName mapping cache cleared")


def _robust_parse_xml(path: Path):
    """Parse XML ignoring BOM/DTD/encoding issues. Ported from eventname_to_stringid.py."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()

        content = re.sub(r'^<\?xml[^>]*\?>\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'<!DOCTYPE[^>]*>\s*', '', content, flags=re.MULTILINE)

        if USING_LXML:
            parser = etree.XMLParser(resolve_entities=False, load_dtd=False,
                                     no_network=True, recover=True)
            root = etree.fromstring(content.encode("utf-8"), parser=parser)
        else:
            root = etree.fromstring(content.encode("utf-8"))
        return root
    except Exception as e:
        logger.warning(f"Failed to parse XML {path.name}: {e}")
        return None


def build_eventname_mapping(
    export_folder: Path,
    progress_callback: Optional[Callable] = None,
) -> Dict[str, Dict[str, str]]:
    """
    Scan ALL XML files in export folder recursively.
    Look for SoundEventName/EventName + StringId + StrOrigin ATTRIBUTES on any element.

    Returns:
        {eventname_lowercase: {"stringid": X, "strorigin": Y}}
    """
    mapping = {}

    if not export_folder.exists():
        logger.error(f"Export folder not found: {export_folder}")
        return mapping

    xml_files = list(export_folder.rglob("*.xml"))
    logger.info(f"EventName resolver: scanning {len(xml_files)} XML files in {export_folder}")

    if progress_callback:
        progress_callback(f"Building EventName mapping from {len(xml_files)} XML files...")

    for idx, xml_path in enumerate(xml_files, 1):
        if idx % 500 == 0:
            logger.debug(f"  EventName scan: processed {idx}/{len(xml_files)} files...")
            if progress_callback:
                progress_callback(f"EventName scan: {idx}/{len(xml_files)} files...")

        root = _robust_parse_xml(xml_path)
        if root is None:
            continue

        for node in root.iter():
            # Case-insensitive attribute access for SoundEventName/EventName
            se = (node.get("SoundEventName") or node.get("soundeventname") or
                  node.get("EventName") or node.get("eventname") or "").strip()
            sid = (node.get("StringId") or node.get("StringID") or
                   node.get("stringid") or "").strip()
            strorigin = (node.get("StrOrigin") or node.get("Strorigin") or
                         node.get("strorigin") or "").strip()

            if se and sid:
                mapping[se.lower()] = {"stringid": sid, "strorigin": strorigin}

    logger.info(f"EventName resolver: found {len(mapping)} EventName -> StringID mappings")
    return mapping


def get_eventname_mapping(
    export_folder: Path,
    force_rebuild: bool = False,
    progress_callback: Optional[Callable] = None,
) -> Dict[str, Dict[str, str]]:
    """
    Cached wrapper around build_eventname_mapping.
    Builds once, reuses until export folder changes or force_rebuild is True.
    """
    global _cached_mapping, _cached_folder

    folder_str = str(export_folder)

    if not force_rebuild and _cached_mapping is not None and _cached_folder == folder_str:
        logger.debug(f"EventName mapping cache hit: {len(_cached_mapping)} entries")
        return _cached_mapping

    _cached_mapping = build_eventname_mapping(export_folder, progress_callback)
    _cached_folder = folder_str
    return _cached_mapping


def generate_stringid_from_dialogvoice(eventname: str, dialogvoice: str) -> str:
    """
    Step 1: Generate StringID from EventName + DialogVoice (tmxtransfer11 algorithm).

    Algorithm:
    - If dialogvoice is non-empty and found inside eventname: remove it, strip leading '_'
    - If dialogvoice is empty but eventname exists: use eventname, strip leading '_'
    - Otherwise: return empty (fail)

    Args:
        eventname: The audio event identifier (e.g. "john_conversation_greeting_001")
        dialogvoice: The dialog voice prefix (e.g. "john_conversation")

    Returns:
        Generated StringID or empty string on failure
    """
    event = eventname.lower().strip()
    dialog = dialogvoice.lower().strip() if dialogvoice else ""

    if dialog and event and dialog in event:
        # Remove DialogVoice prefix from EventName
        diff = event.replace(dialog, "", 1)
        if diff.startswith("_"):
            diff = diff[1:]
        return diff
    elif not dialog and event:
        # No DialogVoice — use EventName as-is, strip leading underscore
        return event[1:] if event.startswith("_") else event
    else:
        return ""


def extract_stringid_from_dialog_keyword(eventname: str) -> str:
    """
    Step 2: Extract StringID via aidialog/questdialog keyword (findeventname8 algorithm).

    Algorithm:
    - Search for "aidialog" in eventname (case-insensitive)
    - If not found, search for "questdialog"
    - If found: return substring from keyword to end (lowercase)
    - If neither found: return empty (fail)

    Args:
        eventname: The audio event identifier

    Returns:
        Extracted StringID or empty string on failure
    """
    lower = eventname.lower().strip()

    idx = lower.find("aidialog")
    if idx == -1:
        idx = lower.find("questdialog")

    if idx != -1:
        return lower[idx:]
    return ""


def resolve_eventnames_in_corrections(
    corrections: List[Dict],
    mapping: Dict[str, Dict[str, str]],
) -> Tuple[List[Dict], List[Dict]]:
    """
    Replace _source_eventname -> string_id in correction dicts.

    For each correction with a _source_eventname key:
    - Look up the eventname in the mapping
    - If found: set string_id (and optionally str_origin if empty)
    - If not found: add to missing list

    Args:
        corrections: List of correction dicts (may have _source_eventname key)
        mapping: EventName mapping from get_eventname_mapping()

    Returns:
        (resolved_corrections, missing_corrections)
        - resolved: all corrections with string_id populated
        - missing: corrections where eventname couldn't be resolved
    """
    resolved = []
    missing = []
    step_counts = {"dialogvoice": 0, "keyword": 0, "export": 0}

    for c in corrections:
        eventname = c.get("_source_eventname")

        if not eventname:
            # No eventname — already has string_id from normal flow
            resolved.append(c)
            continue

        # Step 1: DialogVoice generation (tmxtransfer11 algorithm)
        # Only attempt when the Excel had a DialogVoice column (_source_dialogvoice key present)
        has_dialogvoice_col = "_source_dialogvoice" in c
        dialogvoice = c.get("_source_dialogvoice", "")
        generated = generate_stringid_from_dialogvoice(eventname, dialogvoice) if has_dialogvoice_col else ""
        if generated:
            new_c = dict(c)
            new_c["string_id"] = generated
            new_c.pop("_source_eventname", None)
            new_c.pop("_source_dialogvoice", None)
            resolved.append(new_c)
            step_counts["dialogvoice"] += 1
            logger.debug(f"Step 1 (DialogVoice): '{eventname}' -> '{generated}'")
            continue

        # Step 2: aidialog/questdialog keyword extraction (findeventname8 algorithm)
        extracted = extract_stringid_from_dialog_keyword(eventname)
        if extracted:
            new_c = dict(c)
            new_c["string_id"] = extracted
            new_c.pop("_source_eventname", None)
            new_c.pop("_source_dialogvoice", None)
            resolved.append(new_c)
            step_counts["keyword"] += 1
            logger.debug(f"Step 2 (Keyword): '{eventname}' -> '{extracted}'")
            continue

        # Step 3: Export folder lookup (existing logic)
        data = mapping.get(eventname.lower())
        if data:
            new_c = dict(c)
            new_c["string_id"] = data["stringid"]
            if not new_c.get("str_origin") and data.get("strorigin"):
                new_c["str_origin"] = data["strorigin"]
            new_c.pop("_source_eventname", None)
            new_c.pop("_source_dialogvoice", None)
            resolved.append(new_c)
            step_counts["export"] += 1
            logger.debug(f"Step 3 (Export): '{eventname}' -> '{data['stringid']}'")
        else:
            missing.append(c)
            logger.debug(f"Unresolved EventName (all 3 steps failed): '{eventname}'")

    logger.info(
        f"EventName resolution: {len(resolved)} resolved, {len(missing)} missing "
        f"(out of {len(corrections)} total corrections) — "
        f"Step1-DialogVoice: {step_counts['dialogvoice']}, "
        f"Step2-Keyword: {step_counts['keyword']}, "
        f"Step3-Export: {step_counts['export']}"
    )
    return resolved, missing


def generate_missing_eventname_report(
    missing: List[Dict],
    output_path: Path,
) -> bool:
    """
    Generate an Excel report of unresolved EventNames using xlsxwriter.

    Args:
        missing: List of correction dicts with unresolved _source_eventname
        output_path: Path to write the report Excel

    Returns:
        True if report was generated, False if xlsxwriter not available or no data
    """
    if not missing:
        return False

    try:
        import xlsxwriter
    except ImportError:
        logger.warning("xlsxwriter not available — cannot generate missing EventName report")
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb = xlsxwriter.Workbook(str(output_path))
    ws = wb.add_worksheet("Missing EventNames")

    # Header format: dark blue background, white text
    header_fmt = wb.add_format({
        'bold': True,
        'font_color': '#FFFFFF',
        'bg_color': '#2E4057',
        'border': 1,
    })
    cell_fmt = wb.add_format({'border': 1, 'text_wrap': True})
    status_fmt = wb.add_format({
        'border': 1,
        'font_color': '#CC0000',
        'bold': True,
    })

    # Headers
    headers = ["EventName", "Correction Text", "Source File", "Status"]
    for col, header in enumerate(headers):
        ws.write(0, col, header, header_fmt)

    # Data rows
    for row, c in enumerate(missing, 1):
        eventname = c.get("_source_eventname", "")
        correction = c.get("corrected", "")
        source = c.get("_source_file", "")
        ws.write(row, 0, eventname, cell_fmt)
        ws.write(row, 1, correction, cell_fmt)
        ws.write(row, 2, source, cell_fmt)
        ws.write(row, 3, "MISSING", status_fmt)

    # Column widths
    ws.set_column(0, 0, 45)  # EventName
    ws.set_column(1, 1, 50)  # Correction Text
    ws.set_column(2, 2, 35)  # Source File
    ws.set_column(3, 3, 12)  # Status

    # Auto-filter and freeze top row
    ws.autofilter(0, 0, len(missing), len(headers) - 1)
    ws.freeze_panes(1, 0)

    wb.close()
    logger.info(f"Missing EventName report: {output_path} ({len(missing)} entries)")
    return True
