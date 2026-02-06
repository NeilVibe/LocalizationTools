"""
Missing Translation Finder.

Find Korean strings in TARGET that are MISSING from SOURCE by (StrOrigin, StringId) key.
Based on missingtranslationfromlanguagedata.py script.

Logic:
1. Scan TARGET and collect ALL LocStr where Str contains Korean characters
2. Compare those TARGET-Korean keys against SOURCE keys:
   - If key exists in SOURCE => HIT => discard
   - If key does NOT exist in SOURCE => MISS => keep
3. Optional post-filter: exclude StringIDs from specific export paths
4. Output: Per-language XML files + Summary Report (Excel)
"""

import logging
import os
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Try lxml first (more robust), fallback to standard library
try:
    from lxml import etree as LET
    HAS_LXML = True
except ImportError:
    LET = None
    HAS_LXML = False

from xml.etree import ElementTree as ET

from .xml_parser import sanitize_xml_content


# Korean character ranges (Hangul syllables + Jamo)
KOREAN_RE = re.compile(r'[\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F]')


def has_korean(text: str) -> bool:
    """Check if text contains any Korean characters."""
    return bool(text and KOREAN_RE.search(text))


def safe_get_attr(elem: ET.Element, name: str) -> str:
    """Safely get attribute value, return empty string if None."""
    v = elem.get(name)
    return v.strip() if v is not None else ""


def _get_attr_case_insensitive(elem: ET.Element, names: List[str]) -> str:
    """Get attribute value with case-insensitive name lookup."""
    for name in names:
        v = elem.get(name)
        if v is not None:
            return v.strip()
    return ""


def _iter_locstr_elements(root) -> list:
    """Iterate LocStr elements with case-insensitive tag matching."""
    locstr_tags = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']
    elements = []
    for tag in locstr_tags:
        elements.extend(root.iter(tag))
    return elements


def count_korean_words(text: str) -> int:
    """
    Count Korean words in text.
    Korean doesn't use spaces between words, so we count Korean character sequences.
    """
    if not text:
        return 0
    # Count Korean character sequences as words
    korean_sequences = re.findall(r'[\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F]+', text)
    return len(korean_sequences)


def count_korean_chars(text: str) -> int:
    """Count Korean characters in text."""
    if not text:
        return 0
    return len(KOREAN_RE.findall(text))


@dataclass
class MissingEntry:
    """A single missing translation entry."""
    string_id: str
    str_origin: str
    str_value: str  # Korean text
    source_file: str  # Which target file it came from
    elem: ET.Element
    korean_chars: int = 0
    korean_words: int = 0


@dataclass
class LanguageMissingReport:
    """Missing translation report for a single language."""
    language: str
    target_file: str
    entries: List[MissingEntry] = field(default_factory=list)
    korean_strings: int = 0  # Total Korean strings found in target
    hits: int = 0  # Found in source
    misses: int = 0  # Missing from source (need translation)
    total_korean_chars: int = 0
    total_korean_words: int = 0


@dataclass
class MissingTranslationReport:
    """Complete missing translation report."""
    source_path: str
    target_path: str
    mode: str
    timestamp: str
    by_language: Dict[str, LanguageMissingReport] = field(default_factory=dict)
    total_source_keys: int = 0
    total_target_korean: int = 0
    total_hits: int = 0
    total_misses: int = 0
    total_korean_chars: int = 0
    total_korean_words: int = 0


def _parse_xml_file(xml_path: Path) -> Optional[ET.Element]:
    """
    Parse XML file with sanitization.

    Args:
        xml_path: Path to XML file

    Returns:
        Root element or None if parsing fails
    """
    try:
        content = xml_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            content = xml_path.read_text(encoding='latin-1')
        except Exception:
            return None

    content = sanitize_xml_content(content)

    # Wrap in root element if needed
    if not content.strip().startswith('<?xml') and not content.strip().startswith('<root'):
        content = f"<root>\n{content}\n</root>"

    try:
        if HAS_LXML:
            return LET.fromstring(
                content.encode("utf-8"),
                parser=LET.XMLParser(recover=True, huge_tree=True)
            )
        else:
            return ET.fromstring(content)
    except Exception:
        return None


def iter_locstr_from_file(xml_path: Path):
    """
    Yields (key, element) for each LocStr in a file.
    key = (StrOrigin, StringId)

    Args:
        xml_path: Path to XML file

    Yields:
        Tuple of ((str_origin, string_id), element)
    """
    root = _parse_xml_file(xml_path)
    if root is None:
        return

    for loc in _iter_locstr_elements(root):
        so = _get_attr_case_insensitive(loc, ['StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN'])
        sid = _get_attr_case_insensitive(loc, ['StringId', 'StringID', 'stringid', 'STRINGID'])
        key = (so, sid)
        yield key, loc


def collect_source_keys_from_file(source_file: Path) -> Set[Tuple[str, str]]:
    """
    Returns set of (StrOrigin, StringId) present in source.

    Args:
        source_file: Path to source XML file

    Returns:
        Set of (StrOrigin, StringId) tuples
    """
    s = set()
    for key, _loc in iter_locstr_from_file(source_file):
        s.add(key)
    return s


def collect_source_keys_from_folder(source_folder: Path) -> Set[Tuple[str, str]]:
    """
    Returns set of (StrOrigin, StringId) present in source folder.

    Args:
        source_folder: Path to source folder

    Returns:
        Set of (StrOrigin, StringId) tuples
    """
    s = set()
    for root_dir, _, files in os.walk(source_folder):
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue
            fp = Path(root_dir) / fn
            for key, _loc in iter_locstr_from_file(fp):
                s.add(key)
    return s


def _detect_language_from_filename(filename: str) -> str:
    """
    Detect language code from filename like languagedata_FRE.xml.

    Args:
        filename: File name

    Returns:
        Language code (e.g., "FRE") or "UNK"
    """
    name = Path(filename).stem.lower()
    if name.startswith("languagedata_"):
        lang = name[13:].upper()
        if lang:
            return lang
    return "UNK"


def collect_target_korean_per_language(
    target_folder: Path,
    progress_cb: Optional[Callable[[str, int], None]] = None
) -> Dict[str, Dict[Tuple[str, str], MissingEntry]]:
    """
    Collect Korean entries from each languagedata file in target folder.

    Args:
        target_folder: Path to target folder (LOC folder with languagedata_*.xml files)
        progress_cb: Optional progress callback

    Returns:
        Dict: language_code -> {(str_origin, string_id) -> MissingEntry}
    """
    result = {}

    # Find all languagedata files
    lang_files = list(target_folder.glob("languagedata_*.xml"))
    total = len(lang_files)

    for i, xml_file in enumerate(lang_files, 1):
        lang = _detect_language_from_filename(xml_file.name)

        if progress_cb:
            pct = int(20 + 30 * (i / max(total, 1)))
            progress_cb(f"Scanning {xml_file.name} ({lang})...", pct)

        entries = {}
        for key, loc in iter_locstr_from_file(xml_file):
            if key in entries:
                continue
            str_val = _get_attr_case_insensitive(loc, ['Str', 'str', 'STR'])
            if has_korean(str_val):
                entries[key] = MissingEntry(
                    string_id=key[1],
                    str_origin=key[0],
                    str_value=str_val,
                    source_file=str(xml_file),
                    elem=loc,
                    korean_chars=count_korean_chars(str_val),
                    korean_words=count_korean_words(str_val),
                )

        if entries:
            result[lang] = entries

    return result


def count_total_locstr_per_language(target_folder: Path) -> Dict[str, int]:
    """
    Count ALL LocStr elements per language file (not just Korean).

    Args:
        target_folder: Path to target folder (LOC folder with languagedata_*.xml files)

    Returns:
        Dict mapping language code to total LocStr count: {lang_code: total_count}
    """
    result = {}
    lang_files = list(target_folder.glob("languagedata_*.xml"))

    for xml_file in lang_files:
        lang = _detect_language_from_filename(xml_file.name)
        root = _parse_xml_file(xml_file)
        if root is None:
            continue
        count = len(_iter_locstr_elements(root))
        result[lang] = count

    return result


def _get_export_depth2(rel_path: str) -> str:
    """
    Extract EXPORT depth-2 category from relative path.

    Examples:
        'Dialog/AIDialog/file.loc.xml' -> 'Dialog/AIDialog'
        'Sequencer/file.loc.xml' -> 'Sequencer'
        'System/Item/file.loc.xml' -> 'System/Item'

    Args:
        rel_path: Relative path under EXPORT root

    Returns:
        Depth-2 path string
    """
    parts = rel_path.replace("\\", "/").split("/")
    # Take first 2 directory parts (exclude filename)
    dir_parts = [p for p in parts[:-1] if p]  # Exclude the filename
    if len(dir_parts) >= 2:
        return f"{dir_parts[0]}/{dir_parts[1]}"
    elif len(dir_parts) == 1:
        return dir_parts[0]
    else:
        return "None"


def build_export_stringid_index(
    export_root: Path,
    progress_cb: Optional[Callable[[str, int], None]] = None
) -> Dict[str, str]:
    """
    Build index: StringId -> relative path under export_root.

    Args:
        export_root: Path to export folder
        progress_cb: Optional callback(message, percent)

    Returns:
        Dict mapping StringId to relative file path
    """
    idx = {}

    if not export_root.exists():
        return idx

    xml_files = list(export_root.rglob("*.xml"))
    total = max(len(xml_files), 1)

    for i, fp in enumerate(xml_files, 1):
        if progress_cb and (i == 1 or i % 200 == 0 or i == total):
            pct = int(5 + 15 * (i / total))
            progress_cb(f"Indexing EXPORT ({i}/{total})...", pct)

        root = _parse_xml_file(fp)
        if root is None:
            continue

        try:
            rel = fp.relative_to(export_root)
            rel_norm = str(rel).replace("\\", "/")
        except ValueError:
            continue

        for loc in _iter_locstr_elements(root):
            sid = _get_attr_case_insensitive(loc, ['StringId', 'StringID', 'stringid', 'STRINGID'])
            if sid and sid not in idx:
                idx[sid] = rel_norm

    return idx


def is_filtered_by_export_location(
    string_id: str,
    export_index: Dict[str, str],
    filter_prefixes: Tuple[str, ...]
) -> bool:
    """
    Check if StringId is located under filtered paths in export.

    Args:
        string_id: The StringId to check
        export_index: StringId -> file path mapping
        filter_prefixes: Tuple of path prefixes to filter (lowercased, normalized)

    Returns:
        True if StringId should be filtered out
    """
    if not string_id or not filter_prefixes:
        return False
    rel = export_index.get(string_id)
    if not rel:
        return False
    rel_dir = os.path.dirname(rel)
    rel_dir_norm = rel_dir.replace("\\", "/").lower()
    return any(rel_dir_norm.startswith(pref) for pref in filter_prefixes)


def write_output_xml(entries: List[MissingEntry], out_path: Path) -> None:
    """
    Write MissingEntry list to output XML file.

    Args:
        entries: List of MissingEntry objects
        out_path: Path for output file
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ['<?xml version="1.0" encoding="utf-8"?>']
    lines.append('<root>')

    for entry in entries:
        loc = entry.elem
        # Reconstruct LocStr element as string
        attribs = []
        for key, value in loc.attrib.items():
            # Escape special characters in attribute values
            escaped_value = (value
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
            )
            attribs.append(f'{key}="{escaped_value}"')

        attrib_str = ' '.join(attribs)
        lines.append(f'  <LocStr {attrib_str} />')

    lines.append('</root>')
    out_path.write_text('\n'.join(lines), encoding='utf-8')


def write_summary_report_excel(
    report: MissingTranslationReport,
    output_path: Path
) -> bool:
    """
    Write summary report to Excel file with professional table formatting.

    Args:
        report: MissingTranslationReport object
        output_path: Path for output Excel file

    Returns:
        True if successful, False if xlsxwriter not available
    """
    try:
        import xlsxwriter
    except ImportError:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb = xlsxwriter.Workbook(str(output_path))

    # === FORMATS ===
    # Header format - dark blue with white text, thick border
    header_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#2F5496',
        'font_color': 'white',
        'font_size': 11,
        'border': 2,
        'align': 'center',
        'valign': 'vcenter',
    })

    # Total row format - gold background
    total_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#FFC000',
        'border': 2,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '#,##0',
    })
    total_text_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#FFC000',
        'border': 2,
        'align': 'left',
        'valign': 'vcenter',
    })

    # Alternating row formats for data
    row_light = wb.add_format({
        'bg_color': '#FFFFFF',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
    })
    row_light_num = wb.add_format({
        'bg_color': '#FFFFFF',
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '#,##0',
    })
    row_dark = wb.add_format({
        'bg_color': '#D6DCE5',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
    })
    row_dark_num = wb.add_format({
        'bg_color': '#D6DCE5',
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '#,##0',
    })

    # Text wrap formats for long content
    text_wrap_light = wb.add_format({
        'bg_color': '#FFFFFF',
        'border': 1,
        'text_wrap': True,
        'valign': 'top',
    })
    text_wrap_dark = wb.add_format({
        'bg_color': '#D6DCE5',
        'border': 1,
        'text_wrap': True,
        'valign': 'top',
    })

    # Info sheet formats
    info_header = wb.add_format({
        'bold': True,
        'bg_color': '#2F5496',
        'font_color': 'white',
        'border': 2,
        'align': 'center',
        'valign': 'vcenter',
    })
    info_label = wb.add_format({
        'bold': True,
        'bg_color': '#D6DCE5',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
    })
    info_value = wb.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
    })
    info_value_num = wb.add_format({
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '#,##0',
    })

    sorted_langs = sorted(report.by_language.keys())

    # === SUMMARY SHEET ===
    ws = wb.add_worksheet("Summary")
    ws.set_column('A:A', 12)   # Language
    ws.set_column('B:B', 18)   # Missing Strings
    ws.set_column('C:C', 18)   # Korean Words
    ws.set_column('D:D', 40)   # Target File

    # Headers
    headers = ["Language", "Missing Strings", "Korean Words", "Target File"]
    for col, h in enumerate(headers):
        ws.write(0, col, h, header_fmt)

    # Data rows with alternating colors
    row = 1
    for lang in sorted_langs:
        lang_report = report.by_language[lang]
        is_dark = (row % 2 == 0)
        txt_fmt = row_dark if is_dark else row_light
        num_fmt = row_dark_num if is_dark else row_light_num

        ws.write(row, 0, lang, txt_fmt)
        ws.write(row, 1, lang_report.misses, num_fmt)
        ws.write(row, 2, lang_report.total_korean_words, num_fmt)
        ws.write(row, 3, Path(lang_report.target_file).name, txt_fmt)
        row += 1

    # Totals row
    ws.write(row, 0, "TOTAL", total_text_fmt)
    ws.write(row, 1, report.total_misses, total_fmt)
    ws.write(row, 2, report.total_korean_words, total_fmt)
    ws.write(row, 3, "", total_text_fmt)

    # Freeze header row
    ws.freeze_panes(1, 0)

    # === INFO SHEET ===
    ws_info = wb.add_worksheet("Info")
    ws_info.set_column('A:A', 25)
    ws_info.set_column('B:B', 80)

    ws_info.write(0, 0, "Field", info_header)
    ws_info.write(0, 1, "Value", info_header)

    info_data = [
        ("Report Generated", report.timestamp, False),
        ("Source Path", report.source_path, False),
        ("Target Path", report.target_path, False),
        ("Mode", report.mode, False),
        ("Languages Found", len(report.by_language), True),
        ("Total Source Keys", report.total_source_keys, True),
        ("Total Target Korean", report.total_target_korean, True),
        ("Total Hits", report.total_hits, True),
        ("Total Misses", report.total_misses, True),
        ("Total Korean Words", report.total_korean_words, True),
    ]
    for i, (field, value, is_num) in enumerate(info_data, 1):
        ws_info.write(i, 0, field, info_label)
        if is_num:
            ws_info.write(i, 1, value, info_value_num)
        else:
            ws_info.write(i, 1, str(value), info_value)

    ws_info.freeze_panes(1, 0)

    # === PER-LANGUAGE DETAIL SHEETS ===
    for lang in sorted_langs:
        lang_report = report.by_language[lang]
        if not lang_report.entries:
            continue

        # Excel sheet names limited to 31 chars
        sheet_name = f"{lang[:28]}"
        ws_lang = wb.add_worksheet(sheet_name)
        ws_lang.set_column('A:A', 22)  # StringId
        ws_lang.set_column('B:B', 55)  # StrOrigin
        ws_lang.set_column('C:C', 55)  # Korean Text
        ws_lang.set_column('D:D', 14)  # Korean Words

        # Headers
        detail_headers = ["StringId", "StrOrigin", "Korean Text (Str)", "Korean Words"]
        for col, h in enumerate(detail_headers):
            ws_lang.write(0, col, h, header_fmt)

        # Data rows with alternating colors (limit to 1000 for Excel performance)
        for i, entry in enumerate(lang_report.entries[:1000], 1):
            is_dark = (i % 2 == 0)
            txt_fmt = row_dark if is_dark else row_light
            num_fmt = row_dark_num if is_dark else row_light_num
            wrap_fmt = text_wrap_dark if is_dark else text_wrap_light

            ws_lang.write(i, 0, entry.string_id, txt_fmt)
            ws_lang.write(i, 1, entry.str_origin[:200], wrap_fmt)
            ws_lang.write(i, 2, entry.str_value[:200], wrap_fmt)
            ws_lang.write(i, 3, entry.korean_words, num_fmt)

        if len(lang_report.entries) > 1000:
            ws_lang.write(1001, 0, f"... and {len(lang_report.entries) - 1000} more entries (see XML file)")

        # Freeze header row
        ws_lang.freeze_panes(1, 0)

    wb.close()
    return True


def find_missing_translations_per_language(
    source_path: str,
    target_path: str,
    output_dir: str,
    export_folder: Optional[str] = None,
    filter_prefixes: Optional[List[str]] = None,
    progress_cb: Optional[Callable[[str, int], None]] = None
) -> MissingTranslationReport:
    """
    Find Korean strings in TARGET that are MISSING from SOURCE, per language.

    Generates:
    - One XML file per language: MISSING_<LANG>_<timestamp>.xml
    - One Excel summary report: MISSING_REPORT_<timestamp>.xlsx

    Args:
        source_path: Path to source file or folder
        target_path: Path to target folder (LOC folder with languagedata_*.xml)
        output_dir: Directory for output files
        export_folder: Optional path to export folder for filtering
        filter_prefixes: Optional list of path prefixes to filter out
        progress_cb: Optional callback(message, percent)

    Returns:
        MissingTranslationReport with all statistics
    """
    source = Path(source_path)
    target = Path(target_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    report = MissingTranslationReport(
        source_path=str(source),
        target_path=str(target),
        mode="folder" if source.is_dir() else "file",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    # Step 1: Collect SOURCE keys
    if progress_cb:
        progress_cb("Collecting SOURCE keys...", 5)

    if source.is_file():
        source_keys = collect_source_keys_from_file(source)
    else:
        source_keys = collect_source_keys_from_folder(source)

    report.total_source_keys = len(source_keys)

    # Step 2: Build export index if filtering enabled
    export_index = {}
    norm_prefixes = ()
    if export_folder and filter_prefixes:
        export_path = Path(export_folder)
        if export_path.exists():
            if progress_cb:
                progress_cb("Building EXPORT index...", 10)
            export_index = build_export_stringid_index(export_path, progress_cb)
            norm_prefixes = tuple(p.replace("\\", "/").lower() for p in filter_prefixes)

    # Step 3: Collect TARGET Korean entries per language
    if progress_cb:
        progress_cb("Scanning TARGET for Korean strings...", 20)

    per_lang_korean = collect_target_korean_per_language(target, progress_cb)

    # Step 4: Find misses for each language
    if progress_cb:
        progress_cb("Finding MISSING translations...", 55)

    total_langs = len(per_lang_korean)
    for idx, (lang, korean_entries) in enumerate(per_lang_korean.items(), 1):
        if progress_cb:
            pct = 55 + int(35 * (idx / max(total_langs, 1)))
            progress_cb(f"Processing {lang}...", pct)

        # Detect target file from first entry
        target_file = ""
        if korean_entries:
            first_entry = next(iter(korean_entries.values()))
            target_file = first_entry.source_file

        lang_report = LanguageMissingReport(
            language=lang,
            target_file=target_file,
            korean_strings=len(korean_entries),
        )

        # Find misses
        for key, entry in korean_entries.items():
            if key in source_keys:
                lang_report.hits += 1
            else:
                # Optional export filter
                if norm_prefixes and is_filtered_by_export_location(
                    entry.string_id, export_index, norm_prefixes
                ):
                    continue  # Filtered out

                lang_report.entries.append(entry)
                lang_report.total_korean_chars += entry.korean_chars
                lang_report.total_korean_words += entry.korean_words

        lang_report.misses = len(lang_report.entries)

        # Write per-language XML
        if lang_report.entries:
            xml_path = out_dir / f"MISSING_{lang}_{timestamp}.xml"
            write_output_xml(lang_report.entries, xml_path)

        report.by_language[lang] = lang_report
        report.total_target_korean += lang_report.korean_strings
        report.total_hits += lang_report.hits
        report.total_misses += lang_report.misses
        report.total_korean_chars += lang_report.total_korean_chars
        report.total_korean_words += lang_report.total_korean_words

    # Step 5: Write Excel summary
    if progress_cb:
        progress_cb("Writing summary report...", 95)

    excel_path = out_dir / f"MISSING_REPORT_{timestamp}.xlsx"
    write_summary_report_excel(report, excel_path)

    if progress_cb:
        progress_cb("Done.", 100)

    return report


def format_report_summary(report: MissingTranslationReport) -> str:
    """
    Format report as human-readable summary.

    Args:
        report: MissingTranslationReport object

    Returns:
        Formatted string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("MISSING TRANSLATION REPORT")
    lines.append("=" * 60)
    lines.append(f"Generated: {report.timestamp}")
    lines.append(f"Source: {report.source_path}")
    lines.append(f"Target: {report.target_path}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append("-" * 60)
    lines.append(f"  Source keys (StrOrigin, StringId):  {report.total_source_keys:,}")
    lines.append(f"  Target Korean entries:              {report.total_target_korean:,}")
    lines.append(f"  Total HITS (found in source):       {report.total_hits:,}")
    lines.append(f"  Total MISSES (need translation):    {report.total_misses:,}")
    lines.append(f"  Total Korean words:                 {report.total_korean_words:,}")
    lines.append("")
    lines.append("PER-LANGUAGE BREAKDOWN")
    lines.append("-" * 60)
    lines.append(f"{'Language':<10} {'Missing':>12} {'KR Words':>14} {'Hits':>12}")
    lines.append("-" * 60)

    for lang in sorted(report.by_language.keys()):
        lr = report.by_language[lang]
        lines.append(f"{lang:<10} {lr.misses:>12,} {lr.total_korean_words:>14,} {lr.hits:>12,}")

    lines.append("-" * 60)
    lines.append(f"{'TOTAL':<10} {report.total_misses:>12,} {report.total_korean_words:>14,} {report.total_hits:>12,}")
    lines.append("=" * 60)

    return "\n".join(lines)


# Keep simple single-output version for backwards compatibility
def find_missing_translations(
    source_path: str,
    target_path: str,
    output_path: str,
    mode: str = "auto",
    export_folder: Optional[str] = None,
    filter_prefixes: Optional[List[str]] = None,
    progress_cb: Optional[Callable[[str, int], None]] = None
) -> Dict:
    """
    Find Korean strings in TARGET that are MISSING from SOURCE (single output file).

    For per-language output, use find_missing_translations_per_language() instead.

    Args:
        source_path: Path to source file or folder
        target_path: Path to target file or folder
        output_path: Path for output XML file
        mode: "file", "folder", or "auto" (detect from paths)
        export_folder: Optional path to export folder for filtering
        filter_prefixes: Optional list of path prefixes to filter out
        progress_cb: Optional callback(message, percent)

    Returns:
        Dict with statistics
    """
    source = Path(source_path)
    target = Path(target_path)
    output = Path(output_path)

    # Auto-detect mode
    if mode == "auto":
        mode = "folder" if source.is_dir() and target.is_dir() else "file"

    if mode not in ("file", "folder"):
        raise ValueError("mode must be 'file', 'folder', or 'auto'")

    # Validate paths
    if mode == "file":
        if not source.is_file():
            raise FileNotFoundError(f"Source file not found: {source}")
        if not target.is_file():
            raise FileNotFoundError(f"Target file not found: {target}")
    else:
        if not source.is_dir():
            raise FileNotFoundError(f"Source folder not found: {source}")
        if not target.is_dir():
            raise FileNotFoundError(f"Target folder not found: {target}")

    # Step 1: Collect SOURCE keys
    if progress_cb:
        progress_cb("Collecting SOURCE keys...", 5)

    if mode == "file":
        source_keys = collect_source_keys_from_file(source)
    else:
        source_keys = collect_source_keys_from_folder(source)

    # Step 2: Collect TARGET Korean strings
    if progress_cb:
        progress_cb(f"SOURCE keys: {len(source_keys)}. Collecting TARGET Korean...", 25)

    all_korean = {}
    if mode == "file":
        for key, loc in iter_locstr_from_file(target):
            if key in all_korean:
                continue
            str_val = _get_attr_case_insensitive(loc, ['Str', 'str', 'STR'])
            if has_korean(str_val):
                all_korean[key] = MissingEntry(
                    string_id=key[1],
                    str_origin=key[0],
                    str_value=str_val,
                    source_file=str(target),
                    elem=loc,
                    korean_chars=count_korean_chars(str_val),
                    korean_words=count_korean_words(str_val),
                )
    else:
        per_lang = collect_target_korean_per_language(target, progress_cb)
        for lang_entries in per_lang.values():
            all_korean.update(lang_entries)

    # Step 3: Find MISSES (not in source)
    if progress_cb:
        progress_cb(f"TARGET Korean: {len(all_korean)}. Finding MISSES...", 50)

    kept = []
    hits = 0

    for key, entry in all_korean.items():
        if key in source_keys:
            hits += 1
        else:
            kept.append(entry)

    kept_before_filter = len(kept)

    # Step 4: Optional export filter
    filtered_out = 0
    if export_folder and filter_prefixes:
        export_path = Path(export_folder)
        if export_path.exists():
            if progress_cb:
                progress_cb("Building EXPORT index for filtering...", 78)

            export_index = build_export_stringid_index(export_path, progress_cb)

            # Normalize filter prefixes
            norm_prefixes = tuple(
                p.replace("\\", "/").lower() for p in filter_prefixes
            )

            if progress_cb:
                progress_cb("Filtering by export location...", 88)

            kept2 = []
            for entry in kept:
                if is_filtered_by_export_location(entry.string_id, export_index, norm_prefixes):
                    filtered_out += 1
                else:
                    kept2.append(entry)
            kept = kept2

    # Step 5: Write output
    if progress_cb:
        progress_cb("Writing output XML...", 95)

    write_output_xml(kept, output)

    if progress_cb:
        progress_cb("Done.", 100)

    return {
        "source_keys": len(source_keys),
        "target_korean_keys": len(all_korean),
        "hits": hits,
        "kept_missing_before_filter": kept_before_filter,
        "filtered_out": filtered_out,
        "final_misses": len(kept),
        "output_file": str(output),
    }


# =============================================================================
# Category colors and sort order (matches LanguageDataExporter)
# =============================================================================

CATEGORY_COLORS = {
    "Sequencer": "#FFE599",
    "AIDialog": "#C6EFCE",
    "QuestDialog": "#C6EFCE",
    "NarrationDialog": "#C6EFCE",
    "Item": "#D9D2E9",
    "Quest": "#D9D2E9",
    "Character": "#F8CBAD",
    "Gimmick": "#D9D2E9",
    "Skill": "#D9D2E9",
    "Knowledge": "#D9D2E9",
    "Faction": "#D9D2E9",
    "UI": "#A9D08E",
    "Region": "#F8CBAD",
    "System_Misc": "#D9D9D9",
    "Uncategorized": "#DDD9C4",
}

# STORY first, then GAME_DATA alphabetically, Uncategorized last
CATEGORY_SORT_ORDER = [
    "Sequencer", "AIDialog", "QuestDialog", "NarrationDialog",
    "Character", "Faction", "Gimmick", "Item", "Knowledge",
    "Quest", "Region", "Skill", "System_Misc", "UI",
    "Uncategorized",
]


def _category_sort_key(category: str) -> tuple:
    """Sort key for category ordering."""
    try:
        return (0, CATEGORY_SORT_ORDER.index(category))
    except ValueError:
        return (1, category)


@dataclass
class MissingEntryWithCategory:
    """A missing translation entry with category info."""
    string_id: str
    str_origin: str
    translation: str  # The Str value from target (Korean text)
    category: str
    source_file: str
    elem: Optional[ET.Element] = None  # Original LocStr element for XML reconstruction


@dataclass
class LanguageSummary:
    """Summary metrics for a single language."""
    language: str
    total_strings: int = 0       # All LocStr entries
    korean_strings: int = 0      # Entries with Korean Str
    translated_strings: int = 0  # total - korean
    missing_strings: int = 0     # MISS from analysis
    hit_strings: int = 0         # HIT from analysis
    total_kr_words: int = 0      # Korean words in all Korean entries
    missing_kr_words: int = 0    # Korean words in MISS entries
    hit_kr_words: int = 0        # total_kr_words - missing_kr_words
    coverage_pct: float = 0.0    # translated / total * 100


@dataclass
class CategoryBreakdown:
    """Metrics for one EXPORT depth-2 category within a language."""
    depth2_path: str
    total_strings: int = 0
    korean_strings: int = 0
    missing_strings: int = 0
    hit_strings: int = 0
    total_kr_words: int = 0
    missing_kr_words: int = 0
    hit_kr_words: int = 0


def _collect_source_strorigins(source_folder: Path) -> Set[str]:
    """Collect set of normalized StrOrigin texts from source folder."""
    origins = set()
    for root_dir, _, files in os.walk(source_folder):
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue
            fp = Path(root_dir) / fn
            for key, _loc in iter_locstr_from_file(fp):
                so = key[0].strip()
                if so:
                    origins.add(so)
    return origins


def _collect_source_strorigins_from_file(source_file: Path) -> Set[str]:
    """Collect set of StrOrigin texts from single source file."""
    origins = set()
    for key, _loc in iter_locstr_from_file(source_file):
        so = key[0].strip()
        if so:
            origins.add(so)
    return origins


def _write_missing_excel_with_categories(
    entries: List[MissingEntryWithCategory],
    output_path: Path,
    language: str,
) -> bool:
    """
    Write per-language Excel file with StrOrigin, Translation, StringID, Category columns.

    Rows sorted by category. Category column color-coded.
    """
    try:
        import xlsxwriter
    except ImportError:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb = xlsxwriter.Workbook(str(output_path))

    # Header format
    header_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#2F5496',
        'font_color': 'white',
        'font_size': 11,
        'border': 2,
        'align': 'center',
        'valign': 'vcenter',
    })

    # Base row format
    base_fmt = {
        'border': 1,
        'valign': 'vcenter',
        'text_wrap': True,
    }

    # Build category-specific formats
    cat_formats = {}
    for cat, color in CATEGORY_COLORS.items():
        cat_formats[cat] = wb.add_format({**base_fmt, 'bg_color': color})

    default_cat_fmt = wb.add_format({**base_fmt, 'bg_color': '#DDD9C4'})
    text_fmt = wb.add_format({**base_fmt})

    ws = wb.add_worksheet("Missing Translations")
    ws.set_column('A:A', 55)  # StrOrigin
    ws.set_column('B:B', 55)  # Translation
    ws.set_column('C:C', 22)  # StringID
    ws.set_column('D:D', 18)  # Category

    # Headers
    for col, h in enumerate(["StrOrigin", "Translation", "StringID", "Category"]):
        ws.write(0, col, h, header_fmt)

    # Sort entries by category
    entries.sort(key=lambda e: _category_sort_key(e.category))

    # Write rows
    for i, entry in enumerate(entries, 1):
        ws.write(i, 0, entry.str_origin[:500], text_fmt)
        ws.write(i, 1, entry.translation[:500], text_fmt)
        ws.write(i, 2, entry.string_id, text_fmt)
        cat_fmt = cat_formats.get(entry.category, default_cat_fmt)
        ws.write(i, 3, entry.category, cat_fmt)

    # Auto-filter and freeze
    if entries:
        ws.autofilter(0, 0, len(entries), 3)
    ws.freeze_panes(1, 0)

    wb.close()
    return True


def _write_locstr_xml(entries: List[MissingEntryWithCategory], out_path: Path) -> None:
    """
    Write MissingEntryWithCategory list to an XML file preserving LocStr attributes.

    Args:
        entries: List of entries with elem field
        out_path: Output XML file path
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ['<?xml version="1.0" encoding="utf-8"?>']
    lines.append('<root>')

    for entry in entries:
        if entry.elem is None:
            continue
        attribs = []
        for key, value in entry.elem.attrib.items():
            escaped_value = (value
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
            )
            attribs.append(f'{key}="{escaped_value}"')
        attrib_str = ' '.join(attribs)
        lines.append(f'  <LocStr {attrib_str} />')

    lines.append('</root>')
    out_path.write_text('\n'.join(lines), encoding='utf-8')


def _write_close_folders(
    missing_per_lang: Dict[str, List[MissingEntryWithCategory]],
    export_path_index: Dict[str, str],
    out_dir: Path,
) -> Dict[str, str]:
    """
    Write Close_{LANG} folders mirroring the EXPORT folder structure.

    For each language, groups missing entries by their EXPORT file path
    (looked up via StringID) and writes XML files preserving folder hierarchy.

    Args:
        missing_per_lang: {lang_code: [MissingEntryWithCategory, ...]}
        export_path_index: {StringID: "relative/path/to/file.loc.xml"}
        out_dir: Root output directory

    Returns:
        {lang_code: close_folder_path} mapping
    """
    close_folders = {}

    for lang, entries in missing_per_lang.items():
        if not entries:
            continue

        close_dir = out_dir / f"Close_{lang}"
        close_dir.mkdir(parents=True, exist_ok=True)
        close_folders[lang] = str(close_dir)

        # Group entries by their EXPORT file path
        by_export_path: Dict[str, List[MissingEntryWithCategory]] = {}
        unmapped_entries: List[MissingEntryWithCategory] = []

        for entry in entries:
            rel_path = export_path_index.get(entry.string_id)
            if rel_path:
                by_export_path.setdefault(rel_path, []).append(entry)
            else:
                unmapped_entries.append(entry)

        # Write XML files following EXPORT structure
        for rel_path, path_entries in by_export_path.items():
            xml_out = close_dir / rel_path
            _write_locstr_xml(path_entries, xml_out)

        # Write unmapped entries (StringID not found in EXPORT) to _unmapped.xml
        if unmapped_entries:
            _write_locstr_xml(unmapped_entries, close_dir / "_unmapped.xml")

    return close_folders


def _build_category_breakdowns(
    per_lang_korean: Dict[str, Dict],
    missing_per_lang: Dict[str, List[MissingEntryWithCategory]],
    export_path_index: Dict[str, str],
) -> Dict[str, Dict[str, CategoryBreakdown]]:
    """
    Build per-language, per-depth2 category breakdown.

    Args:
        per_lang_korean: {lang: {(str_origin, string_id): MissingEntry}}
        missing_per_lang: {lang: [MissingEntryWithCategory, ...]}
        export_path_index: {StringID: relative_path}

    Returns:
        {lang: {depth2_path: CategoryBreakdown}}
    """
    result: Dict[str, Dict[str, CategoryBreakdown]] = {}

    for lang, korean_entries in per_lang_korean.items():
        breakdowns: Dict[str, CategoryBreakdown] = {}

        # Count Korean entries per depth2 category
        for key, entry in korean_entries.items():
            rel_path = export_path_index.get(entry.string_id, "")
            depth2 = _get_export_depth2(rel_path) if rel_path else "None"

            if depth2 not in breakdowns:
                breakdowns[depth2] = CategoryBreakdown(depth2_path=depth2)

            bd = breakdowns[depth2]
            bd.korean_strings += 1
            bd.total_kr_words += entry.korean_words

        # Count missing entries per depth2 category
        for entry in missing_per_lang.get(lang, []):
            rel_path = export_path_index.get(entry.string_id, "")
            depth2 = _get_export_depth2(rel_path) if rel_path else "None"

            if depth2 not in breakdowns:
                breakdowns[depth2] = CategoryBreakdown(depth2_path=depth2)

            bd = breakdowns[depth2]
            bd.missing_strings += 1
            bd.missing_kr_words += count_korean_words(entry.translation)

        # Compute hit = korean - missing for each category
        for bd in breakdowns.values():
            bd.hit_strings = bd.korean_strings - bd.missing_strings
            bd.hit_kr_words = bd.total_kr_words - bd.missing_kr_words

        result[lang] = breakdowns

    return result


def _depth2_sort_key(depth2_path: str) -> tuple:
    """
    Sort key for depth-2 category ordering.
    Groups by parent folder, children alphabetical within each parent.
    "None" always last.

    Result order:
        Dialog/AIDialog
        Dialog/NarrationDialog
        Dialog/QuestDialog
        Dialog/StageCloseDialog
        Sequencer
        System/Character
        System/Faction
        ...
        World
        None
    """
    if depth2_path == "None":
        return (2, "", "")

    parts = depth2_path.split("/")
    parent = parts[0]
    child = parts[1] if len(parts) > 1 else ""

    # Parent folder sort: alphabetical (Dialog < Platform < Sequencer < System < World)
    return (0, parent, child)


def _write_master_summary_excel(
    summaries: Dict[str, LanguageSummary],
    breakdowns: Dict[str, Dict[str, CategoryBreakdown]],
    output_path: Path,
    match_mode: str,
    threshold: float,
) -> bool:
    """
    Write Master Summary Excel with Global Summary and Detailed Summary tabs.

    Args:
        summaries: {lang: LanguageSummary}
        breakdowns: {lang: {depth2_path: CategoryBreakdown}}
        output_path: Path for output Excel file
        match_mode: Match mode used
        threshold: Fuzzy threshold used

    Returns:
        True if successful
    """
    try:
        import xlsxwriter
    except ImportError:
        logger.error("xlsxwriter not available - cannot write master summary")
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = xlsxwriter.Workbook(str(output_path))

    # === FORMATS ===
    header_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#2F5496',
        'font_color': 'white',
        'font_size': 11,
        'border': 2,
        'align': 'center',
        'valign': 'vcenter',
    })

    # Number format with comma separators
    num_fmt = wb.add_format({
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '#,##0',
    })

    text_fmt = wb.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
    })

    # Coverage conditional formats
    coverage_green = wb.add_format({
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '0.0%',
        'bg_color': '#C6EFCE',
        'font_color': '#006100',
    })
    coverage_yellow = wb.add_format({
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '0.0%',
        'bg_color': '#FFEB9C',
        'font_color': '#9C6500',
    })
    coverage_red = wb.add_format({
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '0.0%',
        'bg_color': '#FFC7CE',
        'font_color': '#9C0006',
    })

    # Total row format
    total_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#FFC000',
        'border': 2,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '#,##0',
    })
    total_text_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#FFC000',
        'border': 2,
        'align': 'left',
        'valign': 'vcenter',
    })
    total_pct_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#FFC000',
        'border': 2,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '0.0%',
    })

    # Language header row in Detailed tab
    lang_header_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#A6A6A6',
        'font_color': 'white',
        'font_size': 11,
        'border': 2,
        'align': 'left',
        'valign': 'vcenter',
    })

    # Subtotal row in Detailed tab
    subtotal_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#D9E2F3',
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '#,##0',
    })
    subtotal_text_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#D9E2F3',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
    })

    # Base format for category-colored cells
    base_cat_props = {
        'border': 1,
        'valign': 'vcenter',
        'align': 'left',
    }

    # ================================================================
    # TAB 1: Global Summary
    # ================================================================
    ws1 = wb.add_worksheet("Global Summary")
    ws1.set_column('A:A', 12)   # Language
    ws1.set_column('B:B', 15)   # Total Strings
    ws1.set_column('C:C', 16)   # Korean Strings
    ws1.set_column('D:D', 18)   # Translated Strings
    ws1.set_column('E:E', 16)   # Missing Strings
    ws1.set_column('F:F', 13)   # Hit Strings
    ws1.set_column('G:G', 16)   # Total KR Words
    ws1.set_column('H:H', 18)   # Missing KR Words
    ws1.set_column('I:I', 14)   # Hit KR Words
    ws1.set_column('J:J', 13)   # Coverage %

    headers_tab1 = [
        "Language", "Total Strings", "Korean Strings", "Translated Strings",
        "Missing Strings", "Hit Strings", "Total KR Words",
        "Missing KR Words", "Hit KR Words", "Coverage %",
    ]
    for col, h in enumerate(headers_tab1):
        ws1.write(0, col, h, header_fmt)

    # Data rows
    row = 1
    sum_total = sum_korean = sum_translated = 0
    sum_missing = sum_hits = 0
    sum_kr_words = sum_miss_kr = sum_hit_kr = 0

    for lang in sorted(summaries.keys()):
        s = summaries[lang]
        ws1.write(row, 0, s.language, text_fmt)
        ws1.write(row, 1, s.total_strings, num_fmt)
        ws1.write(row, 2, s.korean_strings, num_fmt)
        ws1.write(row, 3, s.translated_strings, num_fmt)
        ws1.write(row, 4, s.missing_strings, num_fmt)
        ws1.write(row, 5, s.hit_strings, num_fmt)
        ws1.write(row, 6, s.total_kr_words, num_fmt)
        ws1.write(row, 7, s.missing_kr_words, num_fmt)
        ws1.write(row, 8, s.hit_kr_words, num_fmt)

        # Coverage % with conditional color
        pct_value = s.coverage_pct / 100.0  # Excel expects 0.0-1.0 for percentage
        if s.coverage_pct > 80:
            ws1.write(row, 9, pct_value, coverage_green)
        elif s.coverage_pct >= 50:
            ws1.write(row, 9, pct_value, coverage_yellow)
        else:
            ws1.write(row, 9, pct_value, coverage_red)

        sum_total += s.total_strings
        sum_korean += s.korean_strings
        sum_translated += s.translated_strings
        sum_missing += s.missing_strings
        sum_hits += s.hit_strings
        sum_kr_words += s.total_kr_words
        sum_miss_kr += s.missing_kr_words
        sum_hit_kr += s.hit_kr_words
        row += 1

    # TOTALS row
    ws1.write(row, 0, "TOTAL", total_text_fmt)
    ws1.write(row, 1, sum_total, total_fmt)
    ws1.write(row, 2, sum_korean, total_fmt)
    ws1.write(row, 3, sum_translated, total_fmt)
    ws1.write(row, 4, sum_missing, total_fmt)
    ws1.write(row, 5, sum_hits, total_fmt)
    ws1.write(row, 6, sum_kr_words, total_fmt)
    ws1.write(row, 7, sum_miss_kr, total_fmt)
    ws1.write(row, 8, sum_hit_kr, total_fmt)
    avg_coverage = (sum_translated / sum_total) if sum_total > 0 else 0.0
    ws1.write(row, 9, avg_coverage, total_pct_fmt)

    ws1.autofilter(0, 0, row - 1, len(headers_tab1) - 1)
    ws1.freeze_panes(1, 0)

    # ================================================================
    # TAB 2: Detailed Summary
    # ================================================================
    ws2 = wb.add_worksheet("Detailed Summary")
    ws2.set_column('A:A', 28)   # Category
    ws2.set_column('B:B', 16)   # Korean Strings
    ws2.set_column('C:C', 16)   # Missing Strings
    ws2.set_column('D:D', 13)   # Hit Strings
    ws2.set_column('E:E', 16)   # Total KR Words
    ws2.set_column('F:F', 18)   # Missing KR Words
    ws2.set_column('G:G', 14)   # Hit KR Words

    headers_tab2 = [
        "Category", "Korean Strings", "Missing Strings", "Hit Strings",
        "Total KR Words", "Missing KR Words", "Hit KR Words",
    ]
    for col, h in enumerate(headers_tab2):
        ws2.write(0, col, h, header_fmt)

    # Build category-colored formats for depth2 paths
    cat_fmt_cache = {}

    def _get_cat_format(depth2_path: str):
        """Get or create format for a depth2 category path."""
        if depth2_path in cat_fmt_cache:
            return cat_fmt_cache[depth2_path]

        # Extract leaf name for color lookup
        leaf = depth2_path.split("/")[-1] if "/" in depth2_path else depth2_path
        color = CATEGORY_COLORS.get(leaf, "#D9D9D9")

        fmt = wb.add_format({**base_cat_props, 'bg_color': color})
        cat_fmt_cache[depth2_path] = fmt
        return fmt

    row = 1
    for lang in sorted(breakdowns.keys()):
        lang_bds = breakdowns[lang]
        if not lang_bds:
            continue

        lang_summary = summaries.get(lang)
        lang_label = lang
        if lang_summary:
            lang_label = f"{lang} ({lang_summary.korean_strings:,} Korean / {lang_summary.total_strings:,} total)"

        # Language header row
        ws2.merge_range(row, 0, row, len(headers_tab2) - 1, lang_label, lang_header_fmt)
        row += 1

        # Sort categories
        sorted_cats = sorted(lang_bds.keys(), key=_depth2_sort_key)

        sub_korean = sub_missing = sub_hit = 0
        sub_kr_words = sub_miss_kr = sub_hit_kr = 0

        for depth2 in sorted_cats:
            bd = lang_bds[depth2]
            cat_fmt = _get_cat_format(depth2)

            ws2.write(row, 0, depth2, cat_fmt)
            ws2.write(row, 1, bd.korean_strings, num_fmt)
            ws2.write(row, 2, bd.missing_strings, num_fmt)
            ws2.write(row, 3, bd.hit_strings, num_fmt)
            ws2.write(row, 4, bd.total_kr_words, num_fmt)
            ws2.write(row, 5, bd.missing_kr_words, num_fmt)
            ws2.write(row, 6, bd.hit_kr_words, num_fmt)

            sub_korean += bd.korean_strings
            sub_missing += bd.missing_strings
            sub_hit += bd.hit_strings
            sub_kr_words += bd.total_kr_words
            sub_miss_kr += bd.missing_kr_words
            sub_hit_kr += bd.hit_kr_words
            row += 1

        # Subtotal row for this language
        ws2.write(row, 0, f"Subtotal {lang}", subtotal_text_fmt)
        ws2.write(row, 1, sub_korean, subtotal_fmt)
        ws2.write(row, 2, sub_missing, subtotal_fmt)
        ws2.write(row, 3, sub_hit, subtotal_fmt)
        ws2.write(row, 4, sub_kr_words, subtotal_fmt)
        ws2.write(row, 5, sub_miss_kr, subtotal_fmt)
        ws2.write(row, 6, sub_hit_kr, subtotal_fmt)
        row += 1

        # Blank row between languages
        row += 1

    last_data_row = max(row - 2, 0)
    ws2.autofilter(0, 0, last_data_row, len(headers_tab2) - 1)
    ws2.freeze_panes(1, 0)

    # ================================================================
    # TAB 3: Info
    # ================================================================
    ws3 = wb.add_worksheet("Info")
    ws3.set_column('A:A', 22)
    ws3.set_column('B:B', 50)

    info_header_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#2F5496',
        'font_color': 'white',
        'border': 2,
        'align': 'center',
        'valign': 'vcenter',
    })
    info_label_fmt = wb.add_format({
        'bold': True,
        'bg_color': '#D6DCE5',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
    })
    info_value_fmt = wb.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
    })

    ws3.write(0, 0, "Field", info_header_fmt)
    ws3.write(0, 1, "Value", info_header_fmt)

    mode_labels = {
        "stringid_kr_strict": "StringID + KR (Strict)",
        "stringid_kr_fuzzy": "StringID + KR (Fuzzy)",
        "kr_strict": "KR only (Strict)",
        "kr_fuzzy": "KR only (Fuzzy)",
    }

    info_data = [
        ("Report Type", "Master Summary"),
        ("Match Mode", mode_labels.get(match_mode, match_mode)),
        ("Threshold", f"{threshold:.2f}"),
        ("Languages", str(len(summaries))),
        ("Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ]
    for i, (field, value) in enumerate(info_data, 1):
        ws3.write(i, 0, field, info_label_fmt)
        ws3.write(i, 1, value, info_value_fmt)

    ws3.freeze_panes(1, 0)

    wb.close()
    logger.info(f"Master Summary Excel written: {output_path.name}")
    return True


def find_missing_with_options(
    source_path: str,
    target_path: str,
    output_dir: str,
    match_mode: str = "stringid_kr_strict",
    threshold: float = 0.85,
    export_folder: Optional[str] = None,
    progress_cb: Optional[Callable[[str, int], None]] = None,
    model=None,
) -> Dict:
    """
    Find missing translations with configurable match modes.

    Generates per-language Excel files with StrOrigin, Translation, StringID, Category.

    Args:
        source_path: Path to source file or folder
        target_path: Path to target folder (LOC folder with languagedata_*.xml)
        output_dir: Directory for output files
        match_mode: One of stringid_kr_strict, stringid_kr_fuzzy, kr_strict, kr_fuzzy
        threshold: Fuzzy similarity threshold (only for fuzzy modes)
        export_folder: Path to EXPORT folder for category mapping
        progress_cb: Optional callback(message, percent)
        model: Pre-loaded KR-SBERT model (required for fuzzy modes)

    Returns:
        Dict with statistics per language and output paths
    """
    source = Path(source_path)
    target = Path(target_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info("=" * 60)
    logger.info("FIND MISSING TRANSLATIONS - START")
    logger.info(f"  Match mode: {match_mode}")
    logger.info(f"  Threshold:  {threshold:.2f}")
    logger.info(f"  Source:     {source}")
    logger.info(f"  Target:     {target}")
    logger.info(f"  Output:     {out_dir}")
    logger.info(f"  EXPORT:     {export_folder or 'None'}")
    logger.info("=" * 60)

    # Step 1: Build category index AND export path index from EXPORT folder
    if progress_cb:
        progress_cb("Building EXPORT indexes...", 5)

    category_index: Dict[str, str] = {}
    export_path_index: Dict[str, str] = {}
    if export_folder:
        export_path = Path(export_folder)
        if export_path.exists():
            from .category_mapper import build_stringid_category_index
            category_index = build_stringid_category_index(export_path)
            export_path_index = build_export_stringid_index(export_path)

    logger.info(f"[Step 1] EXPORT indexes built: {len(category_index):,} categories, {len(export_path_index):,} paths")
    if progress_cb:
        progress_cb(f"EXPORT indexes: {len(category_index)} categories, {len(export_path_index)} paths", 15)

    # Step 2: Collect SOURCE keys based on match_mode
    if progress_cb:
        progress_cb("Collecting SOURCE keys...", 18)

    use_stringid = match_mode.startswith("stringid_kr")
    is_fuzzy = match_mode.endswith("_fuzzy")
    logger.info(f"[Step 2] Collecting SOURCE keys (use_stringid={use_stringid}, is_fuzzy={is_fuzzy})")

    if use_stringid:
        # (StrOrigin, StringId) composite keys
        if source.is_file():
            source_keys = collect_source_keys_from_file(source)
        else:
            source_keys = collect_source_keys_from_folder(source)
        logger.info(f"[Step 2] SOURCE composite keys collected: {len(source_keys):,}")
    else:
        # KR-only: just StrOrigin texts
        if source.is_file():
            source_origins = _collect_source_strorigins_from_file(source)
        else:
            source_origins = _collect_source_strorigins(source)
        logger.info(f"[Step 2] SOURCE StrOrigin texts collected: {len(source_origins):,}")

    # Step 3: Collect TARGET Korean entries per language
    logger.info("[Step 3] Scanning TARGET for Korean (untranslated) entries...")
    if progress_cb:
        progress_cb("Scanning TARGET for Korean strings...", 22)

    per_lang_korean = collect_target_korean_per_language(target, progress_cb)

    total_korean_all = sum(len(entries) for entries in per_lang_korean.values())
    logger.info(f"[Step 3] TARGET scan complete: {len(per_lang_korean)} languages, {total_korean_all:,} total Korean entries")
    for lang, entries in sorted(per_lang_korean.items()):
        logger.info(f"  {lang}: {len(entries):,} Korean entries")

    # Step 3b: Count total LocStr per language (for coverage calculation)
    if progress_cb:
        progress_cb("Counting total strings per language...", 52)
    total_locstr_per_lang = count_total_locstr_per_language(target)
    logger.info(f"[Step 3b] Total LocStr per language: {', '.join(f'{k}={v:,}' for k, v in sorted(total_locstr_per_lang.items()))}")

    # Step 4: For fuzzy modes, prepare embeddings
    source_embeddings = None
    source_group_embeddings = None  # For stringid_kr_fuzzy

    if is_fuzzy:
        import numpy as np
        logger.info("[Step 4] Preparing fuzzy embeddings with KR-SBERT...")

        if not use_stringid:
            # kr_fuzzy: encode ALL unique source StrOrigin texts
            if progress_cb:
                progress_cb("Encoding SOURCE texts with KR-SBERT...", 40)

            all_source_texts = list(source_origins)
            logger.info(f"[Step 4] kr_fuzzy: encoding {len(all_source_texts):,} unique SOURCE texts")

            # Batch encode
            batch_size = 100
            all_vecs = []
            for i in range(0, len(all_source_texts), batch_size):
                batch = all_source_texts[i:i + batch_size]
                vecs = model.encode(batch, show_progress_bar=False)
                all_vecs.append(vecs)
                done = min(i + batch_size, len(all_source_texts))
                if done % 500 == 0 or done == len(all_source_texts):
                    logger.info(f"  Encoding SOURCE: {done:,}/{len(all_source_texts):,}")
                if progress_cb:
                    pct = 40 + int(10 * done / max(len(all_source_texts), 1))
                    progress_cb(f"Encoding SOURCE ({done}/{len(all_source_texts)})...", pct)

            if all_vecs:
                source_embeddings = np.vstack(all_vecs).astype(np.float32)
                # L2 normalize for cosine similarity
                norms = np.linalg.norm(source_embeddings, axis=1, keepdims=True)
                norms[norms == 0] = 1
                source_embeddings = source_embeddings / norms
                logger.info(f"[Step 4] SOURCE embeddings ready: shape={source_embeddings.shape}")
            else:
                logger.warning("[Step 4] No SOURCE texts to encode - all entries will be MISS")

        elif use_stringid:
            # stringid_kr_fuzzy: group source by StringID
            if progress_cb:
                progress_cb("Grouping SOURCE by StringID for fuzzy...", 40)

            # Build StringID -> list of StrOrigin texts
            source_by_sid: Dict[str, List[str]] = {}
            for (so, sid) in source_keys:
                if so.strip():
                    source_by_sid.setdefault(sid, []).append(so)

            logger.info(f"[Step 4] stringid_kr_fuzzy: {len(source_by_sid):,} unique StringID groups from {len(source_keys):,} keys")

            # Pre-encode all unique texts grouped by StringID
            source_group_embeddings = {}
            total_sids = len(source_by_sid)
            total_texts_encoded = 0
            for idx, (sid, texts) in enumerate(source_by_sid.items()):
                vecs = model.encode(texts, show_progress_bar=False)
                vecs = vecs.astype(np.float32)
                norms = np.linalg.norm(vecs, axis=1, keepdims=True)
                norms[norms == 0] = 1
                vecs = vecs / norms
                source_group_embeddings[sid] = vecs
                total_texts_encoded += len(texts)
                if (idx + 1) % 500 == 0 or (idx + 1) == total_sids:
                    logger.info(f"  Encoding groups: {idx + 1:,}/{total_sids:,} ({total_texts_encoded:,} texts)")
                if progress_cb and (idx + 1) % 500 == 0:
                    pct = 40 + int(10 * (idx + 1) / max(total_sids, 1))
                    progress_cb(f"Encoding groups ({idx + 1}/{total_sids})...", pct)

            logger.info(f"[Step 4] Encoding complete: {len(source_group_embeddings):,} groups, {total_texts_encoded:,} total texts encoded")
    else:
        logger.info("[Step 4] Strict mode - no embeddings needed")

    # Step 5: Find misses per language
    logger.info("[Step 5] Finding MISSES per language...")
    results = {
        "match_mode": match_mode,
        "threshold": threshold,
        "languages": {},
        "output_files": [],
        "close_folders": {},
        "total_misses": 0,
        "total_hits": 0,
        "total_korean": 0,
    }

    # Collect all missing entries per language for Close folder output
    missing_per_lang: Dict[str, List[MissingEntryWithCategory]] = {}

    total_langs = len(per_lang_korean)
    for lang_idx, (lang, korean_entries) in enumerate(sorted(per_lang_korean.items()), 1):
        if progress_cb:
            pct = 55 + int(35 * lang_idx / max(total_langs, 1))
            progress_cb(f"Processing {lang}...", pct)

        logger.info(f"  [{lang_idx}/{total_langs}] Processing {lang}: {len(korean_entries):,} Korean entries")

        missing_entries: List[MissingEntryWithCategory] = []
        hits = 0
        sid_not_in_source = 0  # For fuzzy: StringID not found at all
        fuzzy_below_threshold = 0  # For fuzzy: below similarity threshold

        if not is_fuzzy:
            # === STRICT modes ===
            for key, entry in korean_entries.items():
                if use_stringid:
                    # stringid_kr_strict: exact (StrOrigin, StringID) match
                    if key in source_keys:
                        hits += 1
                        continue
                else:
                    # kr_strict: exact StrOrigin text match
                    if entry.str_origin.strip() in source_origins:
                        hits += 1
                        continue

                # MISS
                cat = category_index.get(entry.string_id, "Uncategorized")
                missing_entries.append(MissingEntryWithCategory(
                    string_id=entry.string_id,
                    str_origin=entry.str_origin,
                    translation=entry.str_value,
                    category=cat,
                    source_file=entry.source_file,
                    elem=entry.elem,
                ))

            logger.info(f"    STRICT: {hits:,} HIT, {len(missing_entries):,} MISS")

        else:
            # === FUZZY modes ===
            import numpy as np

            if use_stringid and source_group_embeddings is not None:
                # stringid_kr_fuzzy: compare within StringID groups
                total_entries = len(korean_entries)
                for entry_idx, (key, entry) in enumerate(korean_entries.items(), 1):
                    sid = entry.string_id
                    so = entry.str_origin.strip()

                    if sid not in source_group_embeddings:
                        # StringID not in source at all -> automatic MISS
                        sid_not_in_source += 1
                        cat = category_index.get(sid, "Uncategorized")
                        missing_entries.append(MissingEntryWithCategory(
                            string_id=sid,
                            str_origin=entry.str_origin,
                            translation=entry.str_value,
                            category=cat,
                            source_file=entry.source_file,
                            elem=entry.elem,
                        ))
                        continue

                    # Encode target text and compare against source group
                    target_vec = model.encode([so], show_progress_bar=False).astype(np.float32)
                    norm = np.linalg.norm(target_vec)
                    if norm > 0:
                        target_vec = target_vec / norm

                    group_vecs = source_group_embeddings[sid]
                    sims = (target_vec @ group_vecs.T).flatten()
                    max_sim = float(sims.max()) if len(sims) > 0 else 0.0

                    if max_sim >= threshold:
                        hits += 1
                    else:
                        fuzzy_below_threshold += 1
                        cat = category_index.get(sid, "Uncategorized")
                        missing_entries.append(MissingEntryWithCategory(
                            string_id=sid,
                            str_origin=entry.str_origin,
                            translation=entry.str_value,
                            category=cat,
                            source_file=entry.source_file,
                            elem=entry.elem,
                        ))

                    if entry_idx % 200 == 0 or entry_idx == total_entries:
                        logger.info(f"    Fuzzy matching: {entry_idx:,}/{total_entries:,} "
                                    f"(HIT={hits:,} SID_MISS={sid_not_in_source:,} BELOW_THRESH={fuzzy_below_threshold:,})")

                logger.info(f"    STRINGID_KR_FUZZY: {hits:,} HIT, {sid_not_in_source:,} StringID not in source, "
                            f"{fuzzy_below_threshold:,} below threshold ({threshold:.2f})")

            elif not use_stringid and source_embeddings is not None:
                # kr_fuzzy: batch similarity against all source texts
                target_texts = []
                target_entries_list = []
                for key, entry in korean_entries.items():
                    target_texts.append(entry.str_origin.strip())
                    target_entries_list.append(entry)

                logger.info(f"    KR_FUZZY: encoding {len(target_texts):,} target texts, comparing against {source_embeddings.shape[0]:,} source texts")

                batch_size = 100
                for i in range(0, len(target_texts), batch_size):
                    batch_texts = target_texts[i:i + batch_size]
                    batch_entries = target_entries_list[i:i + batch_size]

                    target_vecs = model.encode(batch_texts, show_progress_bar=False).astype(np.float32)
                    norms = np.linalg.norm(target_vecs, axis=1, keepdims=True)
                    norms[norms == 0] = 1
                    target_vecs = target_vecs / norms

                    # (batch, source_count) similarities
                    sims = target_vecs @ source_embeddings.T
                    max_sims = sims.max(axis=1)

                    for sim, entry in zip(max_sims, batch_entries):
                        if float(sim) >= threshold:
                            hits += 1
                        else:
                            cat = category_index.get(entry.string_id, "Uncategorized")
                            missing_entries.append(MissingEntryWithCategory(
                                string_id=entry.string_id,
                                str_origin=entry.str_origin,
                                translation=entry.str_value,
                                category=cat,
                                source_file=entry.source_file,
                                elem=entry.elem,
                            ))

                    done = min(i + batch_size, len(target_texts))
                    if done % 500 == 0 or done == len(target_texts):
                        logger.info(f"    Encoding+comparing: {done:,}/{len(target_texts):,} "
                                    f"(HIT={hits:,} MISS={len(missing_entries):,})")

                logger.info(f"    KR_FUZZY: {hits:,} HIT, {len(missing_entries):,} MISS (threshold={threshold:.2f})")

        # Write per-language Excel
        lang_result = {
            "korean_entries": len(korean_entries),
            "hits": hits,
            "misses": len(missing_entries),
        }

        if missing_entries:
            excel_path = out_dir / f"MISSING_{lang}_{timestamp}.xlsx"
            _write_missing_excel_with_categories(missing_entries, excel_path, lang)
            lang_result["output_file"] = str(excel_path)
            results["output_files"].append(str(excel_path))
            missing_per_lang[lang] = missing_entries
            logger.info(f"    Excel written: {excel_path.name} ({len(missing_entries):,} rows)")
        else:
            logger.info(f"    No missing entries for {lang} - no Excel generated")

        results["languages"][lang] = lang_result
        results["total_misses"] += len(missing_entries)
        results["total_hits"] += hits
        results["total_korean"] += len(korean_entries)

    # Step 6: Write Close_{LANG} folders mirroring EXPORT structure
    if export_path_index and missing_per_lang:
        logger.info(f"[Step 6] Writing Close folders for {len(missing_per_lang)} languages...")
        if progress_cb:
            progress_cb("Writing Close folders with EXPORT structure...", 93)

        close_folders = _write_close_folders(missing_per_lang, export_path_index, out_dir)
        results["close_folders"] = close_folders
        for lang, folder_path in close_folders.items():
            logger.info(f"  Close_{lang}/ written")
    else:
        logger.info("[Step 6] No Close folders needed (no export paths or no misses)")

    # Step 7: Write Master Summary Report
    logger.info("[Step 7] Building Master Summary Report...")
    if progress_cb:
        progress_cb("Writing Master Summary Report...", 96)

    # Build LanguageSummary for each language
    summaries = {}
    for lang in sorted(per_lang_korean.keys()):
        lr = results["languages"][lang]
        total = total_locstr_per_lang.get(lang, 0)
        korean = lr["korean_entries"]
        translated = total - korean

        total_kr_words = sum(e.korean_words for e in per_lang_korean[lang].values())
        missing_kr_words = sum(
            count_korean_words(e.translation) for e in missing_per_lang.get(lang, [])
        )

        summary = LanguageSummary(
            language=lang,
            total_strings=total,
            korean_strings=korean,
            translated_strings=translated,
            missing_strings=lr["misses"],
            hit_strings=lr["hits"],
            total_kr_words=total_kr_words,
            missing_kr_words=missing_kr_words,
        )
        summary.hit_kr_words = summary.total_kr_words - summary.missing_kr_words
        summary.coverage_pct = (translated / total * 100) if total > 0 else 0.0
        summaries[lang] = summary

    # Build per-category breakdowns
    breakdowns = _build_category_breakdowns(per_lang_korean, missing_per_lang, export_path_index)

    # Write Excel
    master_path = out_dir / f"MASTER_SUMMARY_{timestamp}.xlsx"
    _write_master_summary_excel(summaries, breakdowns, master_path, match_mode, threshold)
    results["master_summary"] = str(master_path)

    # Final summary
    logger.info("=" * 60)
    logger.info("FIND MISSING TRANSLATIONS - COMPLETE")
    logger.info(f"  Total Korean entries: {results['total_korean']:,}")
    logger.info(f"  Total HITS (matched):  {results['total_hits']:,}")
    logger.info(f"  Total MISSES:          {results['total_misses']:,}")
    logger.info(f"  Languages processed:   {len(results['languages'])}")
    logger.info(f"  Excel files:           {len(results['output_files'])}")
    logger.info(f"  Close folders:         {len(results.get('close_folders', {}))}")
    logger.info(f"  Master summary:        {master_path.name}")
    logger.info("=" * 60)

    if progress_cb:
        progress_cb("Done.", 100)

    return results


def generate_output_filename(source_path: str, target_path: str, output_dir: Optional[str] = None) -> str:
    """
    Generate automatic output filename.

    Args:
        source_path: Path to source
        target_path: Path to target
        output_dir: Optional output directory (defaults to script dir)

    Returns:
        Output file path string
    """
    source = Path(source_path)
    target = Path(target_path)

    src_name = source.stem if source.is_file() else source.name
    tgt_name = target.stem if target.is_file() else target.name
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = Path(__file__).parent.parent / "MissingTranslationReports"

    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir / f"{tgt_name}_MISSING_in_{src_name}_{ts}.xml")
