# Origin: QuickTranslate/core/xml_io.py
from __future__ import annotations
"""
XML Input Parsing.

Parse corrections from XML files for transfer mode.
"""

import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .xml_parser import (
    parse_xml_file, iter_locstr_elements,
    get_attr, STRINGID_ATTRS, STRORIGIN_ATTRS, STR_ATTRS,
    DESC_ATTRS, DESCORIGIN_ATTRS,
)
from .korean_detection import is_korean_text
from .text_utils import is_formula_text, is_text_integrity_issue

logger = logging.getLogger(__name__)


def parse_corrections_from_xml(
    xml_path: Path,
    formula_report: Optional[list] = None,
    integrity_report: Optional[list] = None,
    no_translation_report: Optional[list] = None,
    ellipsis_report: Optional[list] = None,
) -> List[Dict]:
    """
    Parse corrections from XML file (LocStr elements).

    Args:
        xml_path: Path to XML file
        formula_report: Optional list to collect formula/error detections.
            Each entry is a dict with keys: string_id, column, reason, value.
        integrity_report: Optional list to collect text integrity detections
            (broken linebreaks, encoding artifacts, bad chars).
            Same dict format as formula_report.
        no_translation_report: Optional list to collect "no translation" skips.
            Each entry is a dict with keys: string_id, column.

    Returns:
        List of correction dicts with keys: string_id, str_origin, corrected, raw_attribs
    """
    corrections = []

    try:
        root = parse_xml_file(xml_path)
        for elem in iter_locstr_elements(root):
            string_id = get_attr(elem, STRINGID_ATTRS).strip()
            str_origin = get_attr(elem, STRORIGIN_ATTRS).strip()
            str_value = get_attr(elem, STR_ATTRS).strip()

            if string_id and str_value:
                # Skip entries where Str is still Korean (untranslated).
                # These are NOT corrections -- including them would overwrite
                # real translations in the lookup (last-wins) with Korean text.
                if is_korean_text(str_value):
                    continue

                # Skip "no translation" entries -- these are NOT corrections.
                # Transferring them would overwrite real translations, then
                # postprocess would replace with StrOrigin (Korean).
                _norm = ' '.join(str_value.split()).lower()
                if _norm == 'no translation':
                    logger.debug("Skipping 'no translation' source entry: StringID=%s", string_id)
                    if no_translation_report is not None:
                        no_translation_report.append({
                            'string_id': string_id,
                            'column': 'Str',
                        })
                    continue

                # Formula/garbage text check on Str (correction value)
                bad_str = is_formula_text(str_value)
                if bad_str:
                    if formula_report is not None:
                        formula_report.append({
                            'string_id': string_id,
                            'column': 'Str',
                            'reason': bad_str,
                            'value': str_value[:60],
                        })
                    logger.debug("Skipping formula-like Str in XML: StringID=%s reason=%s", string_id, bad_str)
                    continue

                # Text integrity check on Str (broken linebreaks, encoding, bad chars)
                bad_integrity = is_text_integrity_issue(str_value, from_xml=True, source_text=str_origin)
                if bad_integrity:
                    if integrity_report is not None:
                        integrity_report.append({
                            'string_id': string_id,
                            'column': 'Str',
                            'reason': bad_integrity,
                            'value': str_value[:60],
                        })
                    # Warnings (lone brackets matching source) still transfer -- only skip blocking issues
                    if not bad_integrity.startswith('Warning:'):
                        logger.debug("Skipping integrity-issue Str in XML: StringID=%s reason=%s", string_id, bad_integrity)
                        continue

                # Store ALL original attributes for exact preservation in failure reports
                raw_attribs = dict(elem.attrib)

                # Extract Desc/DescOrigin (voice direction descriptions)
                desc_origin = get_attr(elem, DESCORIGIN_ATTRS).strip()
                desc_value = get_attr(elem, DESC_ATTRS).strip()

                entry = {
                    "string_id": string_id,
                    "str_origin": str_origin,
                    "corrected": str_value,
                    "raw_attribs": raw_attribs,  # ALL original attributes
                }

                if desc_origin:
                    entry["desc_origin"] = desc_origin
                if desc_value and not is_korean_text(desc_value) and ' '.join(desc_value.split()).lower() != 'no translation':
                    # Formula/garbage text check on Desc
                    bad_desc = is_formula_text(desc_value)
                    if bad_desc:
                        if formula_report is not None:
                            formula_report.append({
                                'string_id': string_id,
                                'column': 'Desc',
                                'reason': bad_desc,
                                'value': desc_value[:60],
                            })
                        logger.debug("Neutralizing formula-like Desc in XML: StringID=%s reason=%s", string_id, bad_desc)
                    else:
                        # Text integrity check on Desc
                        bad_desc_integrity = is_text_integrity_issue(desc_value, from_xml=True, source_text=desc_origin)
                        if bad_desc_integrity:
                            if integrity_report is not None:
                                integrity_report.append({
                                    'string_id': string_id,
                                    'column': 'Desc',
                                    'reason': bad_desc_integrity,
                                    'value': desc_value[:60],
                                })
                            # Warnings (lone brackets matching source) still transfer
                            if bad_desc_integrity.startswith('Warning:'):
                                entry["desc_corrected"] = desc_value
                            else:
                                logger.debug("Neutralizing integrity-issue Desc in XML: StringID=%s reason=%s", string_id, bad_desc_integrity)
                        else:
                            entry["desc_corrected"] = desc_value

                # NOTE: Ellipsis detection removed -- postprocess Step 7 auto-fixes
                # Unicode ellipsis (…) to three dots for non-CJK languages.

                corrections.append(entry)
    except Exception as e:
        logger.warning(f"Failed to parse XML file {xml_path}: {e}")

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
