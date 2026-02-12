"""
Pre-Submission Quality Checks.

Korean detection and pattern code mismatch checking for languagedata XML files.
Scans Source folder, groups by language, writes per-language result XMLs.

Output format: pure LocStr elements in <root>, same format as source XML.
"""

import logging
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from .xml_parser import parse_xml_file, iter_locstr_elements
from .korean_detection import is_korean_text
from .source_scanner import scan_source_for_languages

logger = logging.getLogger(__name__)

# Attribute name variations (case-insensitive handling)
_STR_ATTRS = ['Str', 'str', 'STR']
_STRORIGIN_ATTRS = ['StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN']
_STRINGID_ATTRS = ['StringId', 'StringID', 'stringid', 'STRINGID', 'Stringid', 'stringId']


def _get_attr(elem, attr_names: list) -> str:
    """Get attribute value trying multiple case variations. Returns '' if not found."""
    for name in attr_names:
        val = elem.get(name)
        if val is not None:
            return val
    return ""


def should_skip_locstr(elem, skip_staticinfo_knowledge: bool = True) -> bool:
    """
    Return True if LocStr should be skipped (staticinfo:knowledge filter).

    When skip_staticinfo_knowledge is True (default), any LocStr where Str OR
    StrOrigin contains 'staticinfo:knowledge' (case insensitive) is skipped
    because pattern codes in those entries cause false positives.

    This filter is for Pattern Check ONLY.
    Korean Check never calls this function (Korean = always scan everything).
    Quality Check currently uses this too, but may be removed in the future
    so that only Pattern Check has the toggle.
    """
    if not skip_staticinfo_knowledge:
        return False
    str_text = _get_attr(elem, _STR_ATTRS)
    strorigin_text = _get_attr(elem, _STRORIGIN_ATTRS)
    return ("staticinfo:knowledge" in str_text.lower()
            or "staticinfo:knowledge" in strorigin_text.lower())


def extract_code_patterns(text: str) -> Set[str]:
    """Extract {code} patterns from text."""
    return set(re.findall(r'\{.*?\}', text))


def normalize_staticinfo_pattern(code: str) -> str:
    """
    Normalize staticinfo patterns by stripping variable parts after #.

    {Staticinfo:Knowledge#123} -> {Staticinfo:Knowledge#}

    Ported from checkpatternerror.py battle-tested logic.
    """
    if re.search(r'\{[^{}]*Staticinfo:[^{}]*#', code, re.I):
        return code.split('#', 1)[0] + '#}'
    return code


def normalize_pattern_set(raw_set: Set[str]) -> Set[str]:
    """Normalize all patterns in a set."""
    return {normalize_staticinfo_pattern(p) for p in raw_set}


# Regex to find any <br...> tag variant (we then check if it's exactly <br/>)
_BR_TAG_RE = re.compile(r'<br\s*/?\s*>', re.IGNORECASE)


def _has_wrong_newlines(text: str) -> bool:
    """
    Check if text contains wrong newline representations.

    The only correct newline format in XML language data is <br/>.
    Flags: actual newline chars, literal \\n text, wrong <br> variants,
    Unicode line/paragraph separators.
    """
    if not text:
        return False

    # Actual newline / carriage return characters (from &#10; / &#13; in XML)
    if '\n' in text or '\r' in text:
        return True

    # Literal \n or \r as text (backslash + letter — someone typed it)
    if '\\n' in text or '\\r' in text:
        return True

    # Unicode line separator / paragraph separator
    if '\u2028' in text or '\u2029' in text:
        return True

    # Wrong <br> variants (not exactly <br/>)
    for m in _BR_TAG_RE.finditer(text):
        if m.group() != '<br/>':
            return True

    return False


def _escape_attr_value(value: str) -> str:
    """Escape attribute value for XML output."""
    return (value
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def _elem_to_locstr_line(elem) -> str:
    """Reconstruct a LocStr element as an XML string from its attributes."""
    attribs = []
    for key, value in elem.attrib.items():
        attribs.append(f'{key}="{_escape_attr_value(value)}"')
    attrib_str = ' '.join(attribs)
    return f'  <LocStr {attrib_str} />'


def check_korean_in_file(xml_path: Path) -> list:
    """
    Scan one XML file for Korean characters in Str values.

    Args:
        xml_path: Path to XML file

    Returns:
        List of matching LocStr elements (lxml elements with original attributes).
    """
    findings = []
    try:
        root = parse_xml_file(xml_path)
        for elem in iter_locstr_elements(root):
            str_text = _get_attr(elem, _STR_ATTRS).strip()
            if not str_text:
                continue

            if is_korean_text(str_text):
                findings.append(elem)
    except Exception as e:
        logger.warning(f"Failed to parse {xml_path.name}: {e}")

    return findings


def check_patterns_in_file(
    xml_path: Path,
    skip_staticinfo_knowledge: bool = True,
) -> Tuple[list, list]:
    """
    Scan one XML file for pattern code mismatches AND wrong newlines.

    Compares normalized {code} pattern sets. If they differ, it's a pattern error.
    Also checks for wrong newline representations (only <br/> is correct).

    Args:
        xml_path: Path to XML file
        skip_staticinfo_knowledge: If True, skip entries containing 'staticinfo:knowledge'

    Returns:
        Tuple of (pattern_errors, newline_errors) — two lists of LocStr elements.
    """
    pattern_errors = []
    newline_errors = []
    try:
        root = parse_xml_file(xml_path)
        for elem in iter_locstr_elements(root):
            if should_skip_locstr(elem, skip_staticinfo_knowledge):
                continue

            strorigin_text = _get_attr(elem, _STRORIGIN_ATTRS).strip()
            str_text = _get_attr(elem, _STR_ATTRS).strip()

            if not strorigin_text or not str_text:
                continue

            # Pattern mismatch check
            origin_patterns = normalize_pattern_set(extract_code_patterns(strorigin_text))
            str_patterns = normalize_pattern_set(extract_code_patterns(str_text))

            if origin_patterns != str_patterns:
                pattern_errors.append(elem)

            # Wrong newline check
            if _has_wrong_newlines(str_text) or _has_wrong_newlines(strorigin_text):
                newline_errors.append(elem)
    except Exception as e:
        logger.warning(f"Failed to parse {xml_path.name}: {e}")

    return pattern_errors, newline_errors


def iter_source_xml_files(source_folder: Path) -> Dict[str, List[Path]]:
    """
    Discover all XML files in Source folder, grouped by language.

    Uses the existing source_scanner to detect language codes from
    folder/file naming conventions.

    Args:
        source_folder: Path to Source folder

    Returns:
        Dict mapping language code to list of XML file paths.
        Example: {"ENG": [path1, path2], "FRE": [path3], ...}
    """
    scan_result = scan_source_for_languages(source_folder)

    # Filter to XML files only
    xml_by_lang = {}
    for lang, files in scan_result.lang_files.items():
        xml_files = [f for f in files if f.suffix.lower() == ".xml"]
        if xml_files:
            xml_by_lang[lang] = xml_files

    return xml_by_lang


def _write_results_xml(output_path: Path, elements: list):
    """
    Write LocStr elements to XML file in pure source format.

    Output: <root> with LocStr elements preserving original attributes.
    Same format as missing_translation_finder and checkpatternerror.py.
    """
    lines = ['<?xml version="1.0" encoding="utf-8"?>']
    lines.append('<root>')

    for elem in elements:
        lines.append(_elem_to_locstr_line(elem))

    lines.append('</root>')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('\n'.join(lines), encoding='utf-8')


def run_korean_check(
    source_folder: Path,
    output_folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, int]:
    """
    Run Korean character check on all languages in Source folder.

    Scans all languagedata XML files, finds Korean in Str values,
    writes per-language result XMLs to output_folder/Korean/.

    Args:
        source_folder: Path to Source folder with language subfolders
        output_folder: Path to CheckResults folder
        progress_callback: Optional callback for progress updates

    Returns:
        Summary dict: {"FRE": 5, "GER": 0, ...} (finding counts per language)
    """
    xml_by_lang = iter_source_xml_files(source_folder)
    if not xml_by_lang:
        if progress_callback:
            progress_callback("No XML files found in Source folder")
        return {}

    korean_dir = output_folder / "Korean"
    korean_dir.mkdir(parents=True, exist_ok=True)

    languages = sorted(xml_by_lang.keys())
    summary = {}

    for i, lang in enumerate(languages):
        xml_files = xml_by_lang[lang]
        if progress_callback:
            progress_callback(f"Checking Korean... ({i + 1}/{len(languages)} languages: {lang})")

        all_findings = []
        for xml_path in xml_files:
            all_findings.extend(check_korean_in_file(xml_path))

        summary[lang] = len(all_findings)

        if all_findings:
            out_path = korean_dir / f"korean_findings_{lang}.xml"
            _write_results_xml(out_path, all_findings)
            logger.info(f"Korean check {lang}: {len(all_findings)} findings in {len(xml_files)} files -> {out_path.name}")
        else:
            logger.info(f"Korean check {lang}: clean ({len(xml_files)} files)")

    return summary


def run_pattern_check(
    source_folder: Path,
    output_folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None,
    skip_staticinfo_knowledge: bool = True,
) -> Dict[str, Tuple[int, int]]:
    """
    Run pattern mismatch + newline check on all languages in Source folder.

    Compares {code} patterns between StrOrigin and Str for each LocStr.
    Also detects wrong newline representations (only <br/> is correct).
    Writes per-language result XMLs to output_folder/PatternErrors/.

    Args:
        source_folder: Path to Source folder with language subfolders
        output_folder: Path to CheckResults folder
        progress_callback: Optional callback for progress updates
        skip_staticinfo_knowledge: If True, skip entries containing 'staticinfo:knowledge'

    Returns:
        Summary dict: {"FRE": (pattern_count, newline_count), ...}
    """
    xml_by_lang = iter_source_xml_files(source_folder)
    if not xml_by_lang:
        if progress_callback:
            progress_callback("No XML files found in Source folder")
        return {}

    pattern_dir = output_folder / "PatternErrors"
    pattern_dir.mkdir(parents=True, exist_ok=True)

    languages = sorted(xml_by_lang.keys())
    summary = {}

    for i, lang in enumerate(languages):
        xml_files = xml_by_lang[lang]
        if progress_callback:
            progress_callback(f"Checking patterns... ({i + 1}/{len(languages)} languages: {lang})")

        all_pattern_errors = []
        all_newline_errors = []
        for xml_path in xml_files:
            p_errors, n_errors = check_patterns_in_file(xml_path, skip_staticinfo_knowledge)
            all_pattern_errors.extend(p_errors)
            all_newline_errors.extend(n_errors)

        summary[lang] = (len(all_pattern_errors), len(all_newline_errors))

        # Combine both error lists for XML output (deduplicate by element identity)
        seen = set()
        combined = []
        for elem in all_pattern_errors + all_newline_errors:
            eid = id(elem)
            if eid not in seen:
                seen.add(eid)
                combined.append(elem)

        if combined:
            out_path = pattern_dir / f"pattern_errors_{lang}.xml"
            _write_results_xml(out_path, combined)
            p_count, n_count = len(all_pattern_errors), len(all_newline_errors)
            logger.info(f"Pattern check {lang}: {p_count} pattern + {n_count} newline errors in {len(xml_files)} files -> {out_path.name}")
        else:
            logger.info(f"Pattern check {lang}: clean ({len(xml_files)} files)")

    return summary
