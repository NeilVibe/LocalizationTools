"""
Pre-Submission Quality Checks.

Korean detection and pattern code mismatch checking for languagedata XML files.
Scans Source folder, groups by language, writes per-language result XMLs.

Output format: pure LocStr elements in <root>, same format as source XML.
"""

import logging
import re
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from lxml import etree as ET

from .xml_parser import (
    parse_xml_file, iter_locstr_elements,
    get_attr as _get_attr,
    STRINGID_ATTRS as _STRINGID_ATTRS,
    STRORIGIN_ATTRS as _STRORIGIN_ATTRS,
    STR_ATTRS as _STR_ATTRS,
    DESC_ATTRS as _DESC_ATTRS,
)
from .korean_detection import is_korean_text
from .source_scanner import scan_source_for_languages
from .text_utils import is_formula_text, is_text_integrity_issue

logger = logging.getLogger(__name__)


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


def _has_unbalanced_brackets(text: str) -> bool:
    """
    Check if curly brackets in Str are properly paired and nested.

    Uses a stack approach: '{' pushes, '}' pops. Catches:
    - Missing closing bracket: {code without }
    - Missing opening bracket: } without {
    - Wrong nesting: }text{

    Only checks Str (translation) — StrOrigin is assumed correct.
    """
    if not text:
        return False
    depth = 0
    for ch in text:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth < 0:
                return True  # closing without opening
    return depth != 0  # unclosed opening brackets


# Regex to extract self-closing LocStr elements from raw XML text
_LOCSTR_RE = re.compile(r'<LocStr\b[^>]*/\s*>', re.DOTALL | re.IGNORECASE)
# Regex to extract StringId from raw (possibly broken) LocStr text
_RAW_STRINGID_RE = re.compile(r'StringId\s*=\s*"([^"]*?)"', re.IGNORECASE)

# Detect premature close: <LocStr ...> where tag closes with > instead of />
# followed by orphaned attributes (word="...") that should have been inside.
# LocStr is ALWAYS self-closing in game XML, so <LocStr ...> is always broken.
# [^/]> ensures the > is NOT preceded by / (i.e. not self-closing).
_PREMATURE_CLOSE_RE = re.compile(
    r'<LocStr\b[^>]*[^/]>(?:\s*\w+\s*=\s*"[^"]*")*\s*/>',
    re.DOTALL | re.IGNORECASE
)

# Detect "naked close": <LocStr attrs> where tag ends with > but NOT />
# LocStr is ALWAYS self-closing in game XML, so this is always broken.
# Requires at least one attr="val" pair to avoid false positives on bare <LocStr>.
_NAKED_CLOSE_RE = re.compile(
    r'<LocStr\b(?:\s+\w+\s*=\s*"[^"]*")+\s*>',
    re.DOTALL | re.IGNORECASE
)


def check_broken_xml_in_file(xml_path: Path) -> List[Tuple[str, str, str]]:
    """
    Detect malformed LocStr elements by strict-parsing each one individually.

    Three detection passes:
      1. Self-closing LocStr (<LocStr .../>) — extract and strict-parse each one.
         Catches: garbled attributes, bad escaping, missing quotes, etc.
      2. Premature close (<LocStr ...> attr="..."/>) — the tag closes with >
         instead of />, leaving attributes orphaned outside the element.
         Catches: the specific corruption where > appears mid-tag.
      3. Naked close (<LocStr attrs>) — tag ends with > instead of /> with
         NO following orphaned attributes. The simplest broken case.

    Args:
        xml_path: Path to XML file

    Returns:
        List of (string_id, raw_fragment, filename) tuples for each broken LocStr.
    """
    broken = []
    try:
        raw = xml_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.warning("Failed to read %s: %s", xml_path.name, e)
        return broken

    filename = xml_path.name

    # Track positions already reported (avoid duplicate reports)
    reported_positions = set()

    # Pass 1: Self-closing LocStr fragments — strict XML parse test
    for m in _LOCSTR_RE.finditer(raw):
        fragment = m.group()
        test_xml = f'<r>{fragment}</r>'
        try:
            ET.fromstring(test_xml.encode('utf-8'))
        except ET.XMLSyntaxError:
            sid_match = _RAW_STRINGID_RE.search(fragment)
            sid = sid_match.group(1) if sid_match else '(unknown)'
            broken.append((sid, fragment, filename))
            reported_positions.add(m.start())

    # Pass 2: Premature close — <LocStr ...> followed by orphaned attributes
    for m in _PREMATURE_CLOSE_RE.finditer(raw):
        if m.start() in reported_positions:
            continue  # Already caught by Pass 1
        fragment = m.group()
        sid_match = _RAW_STRINGID_RE.search(fragment)
        sid = sid_match.group(1) if sid_match else '(unknown)'
        broken.append((sid, fragment, filename))
        reported_positions.add(m.start())

    # Pass 3: Naked close — <LocStr attrs> with NO following orphaned attrs
    # Catches the simplest broken case that Pass 2 misses.
    for m in _NAKED_CLOSE_RE.finditer(raw):
        if m.start() in reported_positions:
            continue  # Already caught by Pass 1 or 2
        fragment = m.group()
        sid_match = _RAW_STRINGID_RE.search(fragment)
        sid = sid_match.group(1) if sid_match else '(unknown)'
        broken.append((sid, fragment, filename))
        reported_positions.add(m.start())

    return broken


def _write_broken_xml_report(output_path: Path, entries: List[Tuple[str, str, str]]):
    """
    Write broken XML report as plain text (broken XML can't be embedded in XML).

    Each entry is a (string_id, raw_fragment, filename) tuple.
    """
    lines = ["Broken XML Report", "=" * 60, ""]
    for sid, raw, fname in entries:
        lines.append(f"File:     {fname}")
        lines.append(f"StringId: {sid}")
        lines.append(f"Raw:      {raw}")
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('\n'.join(lines), encoding='utf-8')


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


def check_formula_text_in_file(xml_path: Path) -> list:
    """
    Scan one XML file for formula-like text in Str and Desc values.

    Catches Excel formulas (=VLOOKUP, +SUM, etc.), error values (#REF!, #N/A),
    and openpyxl repr leaks that may have been written into XML previously.

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
            desc_text = _get_attr(elem, _DESC_ATTRS).strip()

            if str_text and is_formula_text(str_text):
                findings.append(elem)
                continue
            if desc_text and is_formula_text(desc_text):
                findings.append(elem)
    except Exception as e:
        logger.warning(f"Failed to parse {xml_path.name}: {e}")

    return findings


def check_text_integrity_in_file(xml_path: Path) -> list:
    """
    Scan one XML file for text integrity issues in Str and Desc values.

    Catches broken <br/> tags, encoding artifacts, control characters,
    and zero-width/invisible characters.

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
            desc_text = _get_attr(elem, _DESC_ATTRS).strip()

            if str_text and is_text_integrity_issue(str_text):
                findings.append(elem)
                continue
            if desc_text and is_text_integrity_issue(desc_text):
                findings.append(elem)
    except Exception as e:
        logger.warning(f"Failed to parse {xml_path.name}: {e}")

    return findings


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
) -> Tuple[list, list, list, list]:
    """
    Scan one XML file for pattern code mismatches, wrong newlines,
    unbalanced brackets, and empty Str with StrOrigin.

    Compares normalized {code} pattern sets. If they differ, it's a pattern error.
    Also checks for wrong newline representations (only <br/> is correct).
    Also checks for unbalanced curly brackets in Str (missing { or }).
    Also flags entries where Str is empty but StrOrigin exists (untranslated).

    Args:
        xml_path: Path to XML file
        skip_staticinfo_knowledge: If True, skip entries containing 'staticinfo:knowledge'

    Returns:
        Tuple of (pattern_errors, newline_errors, bracket_errors, empty_str_errors).
    """
    pattern_errors = []
    newline_errors = []
    bracket_errors = []
    empty_str_errors = []
    try:
        root = parse_xml_file(xml_path)
        for elem in iter_locstr_elements(root):
            str_text = _get_attr(elem, _STR_ATTRS).strip()
            if not str_text:
                # Empty Str check runs on ALL entries (no staticinfo skip) —
                # an untranslated entry is always worth flagging.
                strorigin_for_empty = _get_attr(elem, _STRORIGIN_ATTRS).strip()
                if strorigin_for_empty:
                    empty_str_errors.append(elem)
                continue

            # Bracket check runs on ALL entries — unbalanced brackets are
            # always critical, even in staticinfo:knowledge entries.
            if _has_unbalanced_brackets(str_text):
                bracket_errors.append(elem)

            # Pattern and newline checks respect the staticinfo skip filter
            if should_skip_locstr(elem, skip_staticinfo_knowledge):
                continue

            strorigin_text = _get_attr(elem, _STRORIGIN_ATTRS).strip()
            if not strorigin_text:
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

    return pattern_errors, newline_errors, bracket_errors, empty_str_errors


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
    cancel_event: Optional[threading.Event] = None,
) -> Dict[str, int]:
    """
    Run Korean character check on all languages in Source folder.

    Scans all languagedata XML files, finds Korean in Str values,
    writes per-language result XMLs to output_folder/Korean/.

    Args:
        source_folder: Path to Source folder with language subfolders
        output_folder: Path to CheckResults folder
        progress_callback: Optional callback for progress updates
        cancel_event: Optional threading.Event to support cancellation

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
        if cancel_event and cancel_event.is_set():
            raise InterruptedError("Operation cancelled by user")
        xml_files = xml_by_lang[lang]
        if progress_callback:
            progress_callback(f"Checking Korean... ({i + 1}/{len(languages)} languages: {lang})")

        all_findings = []
        for xml_path in xml_files:
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Operation cancelled by user")
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
    cancel_event: Optional[threading.Event] = None,
) -> Dict[str, Tuple[int, int, int, int, int, int, int]]:
    """
    Run pattern mismatch + newline + bracket + broken XML + empty Str check.

    Compares {code} patterns between StrOrigin and Str for each LocStr.
    Also detects wrong newline representations (only <br/> is correct).
    Also detects unbalanced curly brackets in Str (critical errors).
    Also detects malformed/broken LocStr elements at raw text level (critical).
    Also detects entries where Str is empty but StrOrigin exists (untranslated).
    Also detects formula-like text in Str/Desc (leaked Excel formulas/errors).

    Writes per-language result XMLs to:
    - output_folder/PatternErrors/pattern_errors_{LANG}.xml  (all issues combined)
    - output_folder/MissingBrackets/MissingBrackets_{LANG}.xml  (critical bracket issues only)
    - output_folder/BrokenXML/BrokenXML_{LANG}.txt  (critical broken XML report)
    - output_folder/EmptyStr/EmptyStr_{LANG}.xml  (empty Str with StrOrigin)
    - output_folder/FormulaText/FormulaText_{LANG}.xml  (formula-like text in Str/Desc)

    Args:
        source_folder: Path to Source folder with language subfolders
        output_folder: Path to CheckResults folder
        progress_callback: Optional callback for progress updates
        skip_staticinfo_knowledge: If True, skip entries containing 'staticinfo:knowledge'
        cancel_event: Optional threading.Event to support cancellation

    Returns:
        Summary dict: {"FRE": (pattern, newline, bracket, broken_xml, empty_str, formula_text, integrity), ...}
    """
    xml_by_lang = iter_source_xml_files(source_folder)
    if not xml_by_lang:
        if progress_callback:
            progress_callback("No XML files found in Source folder")
        return {}

    pattern_dir = output_folder / "PatternErrors"
    pattern_dir.mkdir(parents=True, exist_ok=True)
    bracket_dir = output_folder / "MissingBrackets"
    bracket_dir.mkdir(parents=True, exist_ok=True)
    broken_dir = output_folder / "BrokenXML"
    broken_dir.mkdir(parents=True, exist_ok=True)
    empty_dir = output_folder / "EmptyStr"
    empty_dir.mkdir(parents=True, exist_ok=True)
    formula_dir = output_folder / "FormulaText"
    formula_dir.mkdir(parents=True, exist_ok=True)
    integrity_dir = output_folder / "TextIntegrity"
    integrity_dir.mkdir(parents=True, exist_ok=True)

    languages = sorted(xml_by_lang.keys())
    summary = {}

    for i, lang in enumerate(languages):
        if cancel_event and cancel_event.is_set():
            raise InterruptedError("Operation cancelled by user")
        xml_files = xml_by_lang[lang]
        if progress_callback:
            progress_callback(f"Checking patterns... ({i + 1}/{len(languages)} languages: {lang})")

        all_pattern_errors = []
        all_newline_errors = []
        all_bracket_errors = []
        all_broken_xml = []
        all_empty_str = []
        all_formula_text = []
        all_integrity = []
        for xml_path in xml_files:
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Operation cancelled by user")
            p_errors, n_errors, b_errors, e_errors = check_patterns_in_file(xml_path, skip_staticinfo_knowledge)
            all_pattern_errors.extend(p_errors)
            all_newline_errors.extend(n_errors)
            all_bracket_errors.extend(b_errors)
            all_empty_str.extend(e_errors)

            # Broken XML check — raw text level, always runs on ALL entries
            broken = check_broken_xml_in_file(xml_path)
            all_broken_xml.extend(broken)

            # Formula text check — catches leaked Excel formulas/errors in Str/Desc
            formula = check_formula_text_in_file(xml_path)
            all_formula_text.extend(formula)

            # Text integrity check — broken linebreaks, encoding artifacts, bad chars
            integrity = check_text_integrity_in_file(xml_path)
            all_integrity.extend(integrity)

        summary[lang] = (len(all_pattern_errors), len(all_newline_errors),
                         len(all_bracket_errors), len(all_broken_xml),
                         len(all_empty_str), len(all_formula_text),
                         len(all_integrity))

        # Combine all error lists for main XML output (deduplicate by element identity)
        seen = set()
        combined = []
        for elem in all_pattern_errors + all_newline_errors + all_bracket_errors + all_empty_str + all_formula_text + all_integrity:
            eid = id(elem)
            if eid not in seen:
                seen.add(eid)
                combined.append(elem)

        if combined:
            out_path = pattern_dir / f"pattern_errors_{lang}.xml"
            _write_results_xml(out_path, combined)
            p_count = len(all_pattern_errors)
            n_count = len(all_newline_errors)
            b_count = len(all_bracket_errors)
            e_count = len(all_empty_str)
            f_count = len(all_formula_text)
            i_count = len(all_integrity)
            logger.info(f"Pattern check {lang}: {p_count} pattern + {n_count} newline + {b_count} bracket + {e_count} empty + {f_count} formula + {i_count} integrity errors in {len(xml_files)} files -> {out_path.name}")
        else:
            logger.info(f"Pattern check {lang}: clean ({len(xml_files)} files)")

        # Write separate critical bracket file
        if all_bracket_errors:
            bracket_path = bracket_dir / f"MissingBrackets_{lang}.xml"
            _write_results_xml(bracket_path, all_bracket_errors)
            logger.info(f"Bracket check {lang}: {len(all_bracket_errors)} CRITICAL entries -> {bracket_path.name}")

        # Write separate critical broken XML report
        if all_broken_xml:
            broken_path = broken_dir / f"BrokenXML_{lang}.txt"
            _write_broken_xml_report(broken_path, all_broken_xml)
            logger.info(f"Broken XML {lang}: {len(all_broken_xml)} CRITICAL entries -> {broken_path.name}")

        # Write separate empty Str file
        if all_empty_str:
            empty_path = empty_dir / f"EmptyStr_{lang}.xml"
            _write_results_xml(empty_path, all_empty_str)
            logger.info(f"Empty Str {lang}: {len(all_empty_str)} entries -> {empty_path.name}")

        # Write separate formula text file
        if all_formula_text:
            formula_path = formula_dir / f"FormulaText_{lang}.xml"
            _write_results_xml(formula_path, all_formula_text)
            logger.info(f"Formula text {lang}: {len(all_formula_text)} CRITICAL entries -> {formula_path.name}")

        # Write separate text integrity file
        if all_integrity:
            integrity_path = integrity_dir / f"TextIntegrity_{lang}.xml"
            _write_results_xml(integrity_path, all_integrity)
            logger.info(f"Text integrity {lang}: {len(all_integrity)} CRITICAL entries -> {integrity_path.name}")

    return summary
