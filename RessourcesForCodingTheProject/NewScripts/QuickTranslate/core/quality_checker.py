"""
Quality Checker: Wrong Script Detection + AI Hallucination Detection.

Scans languagedata XML files in Source folder and produces per-language
Excel reports with two tabs: "Language Issues" and "AI Hallucination".

Reuses helpers from checker.py (no code duplication).
"""

import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .checker import (
    _get_attr,
    _STR_ATTRS,
    _STRORIGIN_ATTRS,
    _STRINGID_ATTRS,
    should_skip_locstr,
    iter_source_xml_files,
)
from .xml_parser import parse_xml_file, iter_locstr_elements

logger = logging.getLogger(__name__)

# ============================================================================
# Data classes
# ============================================================================

@dataclass
class ScriptIssue:
    string_id: str
    str_text: str
    wrong_chars: str          # comma-separated wrong characters
    script_names: str         # e.g. "Cyrillic"

@dataclass
class HallucinationIssue:
    string_id: str
    strorigin: str
    str_text: str
    issue_type: str           # "AI Phrase", "Length Ratio", "Forward Slash"
    details: str

@dataclass
class QualityReport:
    language: str
    script_issues: List[ScriptIssue] = field(default_factory=list)
    hallucination_issues: List[HallucinationIssue] = field(default_factory=list)

# ============================================================================
# Script group definitions
# ============================================================================

# Language code -> script group mapping
_LANG_TO_GROUP = {
    "ENG": "latin",
    "FRE": "latin",
    "GER": "latin",
    "ITA": "latin",
    "POL": "latin",
    "POR-BR": "latin",
    "SPA-ES": "latin",
    "SPA-MX": "latin",
    "TUR": "latin",
    "RUS": "cyrillic_latin",
    "JPN": "japanese",
    "ZHO-CN": "chinese",
    "ZHO-TW": "chinese",
    # KOR is skipped (handled by Check Korean)
}

# Language code -> phrase bank key mapping
_LANG_TO_PHRASE_KEY = {
    "ENG": "en",
    "FRE": "fr",
    "GER": "de",
    "ITA": "it",
    "POL": "pl",
    "POR-BR": "pt",
    "SPA-ES": "es",
    "SPA-MX": "es",
    "TUR": "tr",
    "RUS": "ru",
    "JPN": "ja",
    "ZHO-CN": "zh-cn",
    "ZHO-TW": "zh-tw",
    "KOR": "ko",
}

# CJK languages (use char count for length ratio instead of word count)
_CJK_LANGUAGES = {"JPN", "ZHO-CN", "ZHO-TW", "KOR"}

# ============================================================================
# Unicode classification helpers
# ============================================================================

def _is_latin(code: int) -> bool:
    return ((0x0041 <= code <= 0x024F)
            or (0x1E00 <= code <= 0x1EFF)
            or (0xFF21 <= code <= 0xFF3A)   # Fullwidth A-Z
            or (0xFF41 <= code <= 0xFF5A))  # Fullwidth a-z

def _is_cyrillic(code: int) -> bool:
    return ((0x0400 <= code <= 0x052F)
            or (0x2DE0 <= code <= 0x2DFF)
            or (0xA640 <= code <= 0xA69F))

def _is_cjk(code: int) -> bool:
    return ((0x4E00 <= code <= 0x9FFF)
            or (0x3400 <= code <= 0x4DBF)
            or (0x20000 <= code <= 0x2EBEF)
            or (0xF900 <= code <= 0xFAFF))

def _is_hiragana(code: int) -> bool:
    return 0x3040 <= code <= 0x309F

def _is_katakana(code: int) -> bool:
    return (0x30A0 <= code <= 0x30FF) or (0x31F0 <= code <= 0x31FF)

def _is_hangul(code: int) -> bool:
    return ((0xAC00 <= code <= 0xD7AF)     # Precomposed syllables
            or (0x1100 <= code <= 0x11FF)   # Hangul Jamo
            or (0x3130 <= code <= 0x318F)   # Compatibility Jamo
            or (0xA960 <= code <= 0xA97F)   # Jamo Extended-A
            or (0xD7B0 <= code <= 0xD7FF))  # Jamo Extended-B

def _is_allowed_char(code: int, group: str) -> bool:
    """Check if a Unicode code point is allowed for the given script group."""
    # Hangul is NEVER flagged (separate Check Korean handles it)
    if _is_hangul(code):
        return True

    if group == "latin":
        return _is_latin(code)
    elif group == "cyrillic_latin":
        return _is_latin(code) or _is_cyrillic(code)
    elif group == "japanese":
        return _is_latin(code) or _is_hiragana(code) or _is_katakana(code) or _is_cjk(code)
    elif group == "chinese":
        return _is_latin(code) or _is_cjk(code)
    return True  # Unknown group: allow everything


def _classify_script(code: int) -> str:
    """Classify a Unicode code point into a human-readable script name."""
    if _is_latin(code):
        return "Latin"
    if _is_cyrillic(code):
        return "Cyrillic"
    if _is_cjk(code):
        return "CJK"
    if _is_hiragana(code):
        return "Hiragana"
    if _is_katakana(code):
        return "Katakana"
    if _is_hangul(code):
        return "Hangul"
    # Arabic
    if 0x0600 <= code <= 0x06FF:
        return "Arabic"
    # Thai
    if 0x0E00 <= code <= 0x0E7F:
        return "Thai"
    # Devanagari
    if 0x0900 <= code <= 0x097F:
        return "Devanagari"
    # Greek
    if 0x0370 <= code <= 0x03FF:
        return "Greek"
    return "Other"


# Regex to strip {code} patterns and <br/> markup
_CODE_PATTERN = re.compile(r'\{[^{}]*\}')
_MARKUP_PATTERN = re.compile(r'<[^>]+>')


def _strip_codes_and_markup(text: str) -> str:
    """Strip {code} patterns and XML/HTML markup from text."""
    text = _CODE_PATTERN.sub('', text)
    text = _MARKUP_PATTERN.sub('', text)
    return text


# ============================================================================
# Wrong Script Detection
# ============================================================================

def check_wrong_script_in_file(xml_path: Path, script_group: str) -> List[ScriptIssue]:
    """
    Scan one XML file for characters from the wrong Unicode script.

    Only alphabetic characters are checked. {code} patterns and markup stripped first.
    """
    issues = []
    try:
        root = parse_xml_file(xml_path)
        for elem in iter_locstr_elements(root):
            if should_skip_locstr(elem):
                continue

            str_text = _get_attr(elem, _STR_ATTRS).strip()
            if not str_text:
                continue

            string_id = _get_attr(elem, _STRINGID_ATTRS)
            cleaned = _strip_codes_and_markup(str_text)

            wrong_chars = []
            script_names = set()
            for ch in cleaned:
                if not ch.isalpha():
                    continue
                code = ord(ch)
                if not _is_allowed_char(code, script_group):
                    wrong_chars.append(ch)
                    script_names.add(_classify_script(code))

            if wrong_chars:
                # Deduplicate chars for display
                seen = set()
                unique_chars = []
                for c in wrong_chars:
                    if c not in seen:
                        seen.add(c)
                        unique_chars.append(c)

                issues.append(ScriptIssue(
                    string_id=string_id,
                    str_text=str_text,
                    wrong_chars=', '.join(unique_chars),
                    script_names=', '.join(sorted(script_names)),
                ))
    except Exception as e:
        logger.warning(f"Failed to parse {xml_path.name} for script check: {e}")

    return issues


# ============================================================================
# AI Hallucination Detection
# ============================================================================

def _load_phrase_bank(json_path: Path) -> dict:
    """Load AI hallucination phrase bank from JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load phrase bank from {json_path}: {e}")
        return {}


def _word_count(text: str) -> int:
    """Count words in text (split on whitespace)."""
    return len(text.split())


def check_hallucination_in_file(
    xml_path: Path,
    lang_code: str,
    phrase_bank: dict,
) -> List[HallucinationIssue]:
    """
    Scan one XML file for AI hallucination indicators.

    Checks:
    1. AI phrase matches (case-insensitive) from phrase bank
    2. Extreme length ratio (Str >> StrOrigin)
    3. Forward slash artifacts (/ in Str but not in StrOrigin)
    """
    issues = []
    is_cjk = lang_code in _CJK_LANGUAGES

    # Build phrase list: language-specific + always English
    phrase_key = _LANG_TO_PHRASE_KEY.get(lang_code)
    check_phrases = list(phrase_bank.get("en", []))
    if phrase_key and phrase_key != "en":
        check_phrases.extend(phrase_bank.get(phrase_key, []))

    try:
        root = parse_xml_file(xml_path)
        for elem in iter_locstr_elements(root):
            if should_skip_locstr(elem):
                continue

            str_text = _get_attr(elem, _STR_ATTRS).strip()
            strorigin_text = _get_attr(elem, _STRORIGIN_ATTRS).strip()
            string_id = _get_attr(elem, _STRINGID_ATTRS)

            if not str_text:
                continue

            str_lower = str_text.lower()

            # 1. AI phrase check
            for phrase in check_phrases:
                if phrase in str_lower:
                    issues.append(HallucinationIssue(
                        string_id=string_id,
                        strorigin=strorigin_text,
                        str_text=str_text,
                        issue_type="AI Phrase",
                        details=f'Matched: "{phrase}"',
                    ))
                    break  # One match per element is enough

            # 2. Extreme length ratio
            if strorigin_text:
                origin_cleaned = _strip_codes_and_markup(strorigin_text)
                str_cleaned = _strip_codes_and_markup(str_text)

                if is_cjk:
                    origin_len = len(origin_cleaned)
                    str_len = len(str_cleaned)
                    threshold = 5
                    unit = "char"
                else:
                    origin_len = _word_count(origin_cleaned)
                    str_len = _word_count(str_cleaned)
                    threshold = 10
                    unit = "word"

                if origin_len > 0 and origin_len < 20 and str_len > threshold * origin_len:
                    ratio = str_len / origin_len
                    issues.append(HallucinationIssue(
                        string_id=string_id,
                        strorigin=strorigin_text,
                        str_text=str_text,
                        issue_type="Length Ratio",
                        details=f"{unit.title()} ratio {str_len}/{origin_len} = {ratio:.1f}x (threshold: {threshold}x)",
                    ))

            # 3. Forward slash artifacts (strip {code} and markup like <br/>)
            str_no_codes = _strip_codes_and_markup(str_text)
            origin_no_codes = _strip_codes_and_markup(strorigin_text) if strorigin_text else ""
            if '/' in str_no_codes and '/' not in origin_no_codes:
                issues.append(HallucinationIssue(
                    string_id=string_id,
                    strorigin=strorigin_text,
                    str_text=str_text,
                    issue_type="Forward Slash",
                    details="'/' in Str but not in StrOrigin",
                ))

    except Exception as e:
        logger.warning(f"Failed to parse {xml_path.name} for hallucination check: {e}")

    return issues


# ============================================================================
# Excel output (xlsxwriter)
# ============================================================================

def _write_quality_excel(output_path: Path, report: QualityReport):
    """Write quality report to Excel with two tabs using xlsxwriter."""
    import xlsxwriter

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = xlsxwriter.Workbook(str(output_path))

    # Formats
    header_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#2E4057',
        'font_color': '#FFFFFF',
        'border': 1,
    })
    text_fmt = wb.add_format({'num_format': '@'})  # TEXT format for StringId
    wrap_fmt = wb.add_format({'text_wrap': True})

    # --- Tab 1: Language Issues (wrong script) ---
    ws1 = wb.add_worksheet("Language Issues")
    headers1 = ["StringId", "Str", "Wrong Characters Found", "Script Names"]
    for col, h in enumerate(headers1):
        ws1.write(0, col, h, header_fmt)

    for row, issue in enumerate(report.script_issues, start=1):
        ws1.write_string(row, 0, issue.string_id, text_fmt)
        ws1.write(row, 1, issue.str_text, wrap_fmt)
        ws1.write(row, 2, issue.wrong_chars)
        ws1.write(row, 3, issue.script_names)

    ws1.set_column(0, 0, 20)   # StringId
    ws1.set_column(1, 1, 60)   # Str
    ws1.set_column(2, 2, 30)   # Wrong Characters
    ws1.set_column(3, 3, 20)   # Script Names
    ws1.freeze_panes(1, 0)
    ws1.autofilter(0, 0, max(1, len(report.script_issues)), 3)

    # --- Tab 2: AI Hallucination ---
    ws2 = wb.add_worksheet("AI Hallucination")
    headers2 = ["StringId", "StrOrigin", "Str", "Issue Type", "Details"]
    for col, h in enumerate(headers2):
        ws2.write(0, col, h, header_fmt)

    for row, issue in enumerate(report.hallucination_issues, start=1):
        ws2.write_string(row, 0, issue.string_id, text_fmt)
        ws2.write(row, 1, issue.strorigin, wrap_fmt)
        ws2.write(row, 2, issue.str_text, wrap_fmt)
        ws2.write(row, 3, issue.issue_type)
        ws2.write(row, 4, issue.details, wrap_fmt)

    ws2.set_column(0, 0, 20)   # StringId
    ws2.set_column(1, 1, 50)   # StrOrigin
    ws2.set_column(2, 2, 60)   # Str
    ws2.set_column(3, 3, 15)   # Issue Type
    ws2.set_column(4, 4, 45)   # Details
    ws2.freeze_panes(1, 0)
    ws2.autofilter(0, 0, max(1, len(report.hallucination_issues)), 4)

    wb.close()


# ============================================================================
# Main runner
# ============================================================================

def _find_json_path() -> Path:
    """Find ai_hallucination_phrases.json, works both dev and PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Data files bundled via spec datas=[] go to _internal/ (sys._MEIPASS)
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent  # core/ -> QuickTranslate/

    json_path = base / "ai_hallucination_phrases.json"
    if json_path.exists():
        return json_path

    raise FileNotFoundError(
        f"ai_hallucination_phrases.json not found at {json_path}"
    )


def run_quality_check(
    source_folder: Path,
    output_folder: Path,
    json_path: Optional[Path] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Tuple[int, int]]:
    """
    Run quality check (wrong script + AI hallucination) on all languages.

    Args:
        source_folder: Path to Source folder with language subfolders
        output_folder: Path to Presubmission Checks folder
        json_path: Optional path to ai_hallucination_phrases.json
        progress_callback: Optional callback for progress updates

    Returns:
        Summary dict: {"FRE": (3, 1), "GER": (0, 2), ...}
        Tuple is (script_issue_count, hallucination_issue_count).
    """
    xml_by_lang = iter_source_xml_files(source_folder)
    if not xml_by_lang:
        if progress_callback:
            progress_callback("No XML files found in Source folder")
        return {}

    # Load phrase bank
    if json_path is None:
        json_path = _find_json_path()
    phrase_bank = _load_phrase_bank(json_path)

    quality_dir = output_folder / "QualityReport"
    quality_dir.mkdir(parents=True, exist_ok=True)

    languages = sorted(xml_by_lang.keys())
    summary: Dict[str, Tuple[int, int]] = {}

    for i, lang in enumerate(languages):
        xml_files = xml_by_lang[lang]
        if progress_callback:
            progress_callback(
                f"Quality check... ({i + 1}/{len(languages)} languages: {lang})"
            )

        report = QualityReport(language=lang)
        script_group = _LANG_TO_GROUP.get(lang)

        for xml_path in xml_files:
            # Wrong script check (skip KOR and unknown groups)
            if script_group:
                report.script_issues.extend(
                    check_wrong_script_in_file(xml_path, script_group)
                )

            # AI hallucination check (all languages)
            report.hallucination_issues.extend(
                check_hallucination_in_file(xml_path, lang, phrase_bank)
            )

        script_count = len(report.script_issues)
        halluc_count = len(report.hallucination_issues)
        summary[lang] = (script_count, halluc_count)

        if script_count > 0 or halluc_count > 0:
            out_path = quality_dir / f"quality_report_{lang}.xlsx"
            _write_quality_excel(out_path, report)
            logger.info(
                f"Quality check {lang}: {script_count} script + {halluc_count} hallucination "
                f"issues in {len(xml_files)} files -> {out_path.name}"
            )
        else:
            logger.info(f"Quality check {lang}: clean ({len(xml_files)} files)")

    return summary
