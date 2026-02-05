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

import os
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field

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

    for loc in root.findall(".//LocStr"):
        so = safe_get_attr(loc, "StrOrigin")
        sid = safe_get_attr(loc, "StringId")
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
            str_val = safe_get_attr(loc, "Str")
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

        for loc in root.findall(".//LocStr"):
            sid = safe_get_attr(loc, "StringId")
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
    Write summary report to Excel file.

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

    # Formats
    header_fmt = wb.add_format({
        'bold': True, 'bg_color': '#4472C4', 'font_color': 'white',
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    total_fmt = wb.add_format({
        'bold': True, 'bg_color': '#FFC000', 'border': 1,
        'align': 'right', 'num_format': '#,##0'
    })
    num_fmt = wb.add_format({'num_format': '#,##0', 'align': 'right'})
    text_fmt = wb.add_format({'text_wrap': True, 'valign': 'top'})

    # === SUMMARY SHEET ===
    ws = wb.add_worksheet("Summary")
    ws.set_column('A:A', 18)
    ws.set_column('B:B', 15)
    ws.set_column('C:C', 15)
    ws.set_column('D:D', 15)
    ws.set_column('E:E', 15)
    ws.set_column('F:F', 45)

    # Headers
    headers = ["Language", "Missing Strings", "Korean Chars", "Korean Words", "Hits", "Target File"]
    for col, h in enumerate(headers):
        ws.write(0, col, h, header_fmt)

    # Data rows
    row = 1
    sorted_langs = sorted(report.by_language.keys())
    for lang in sorted_langs:
        lang_report = report.by_language[lang]
        ws.write(row, 0, lang)
        ws.write(row, 1, lang_report.misses, num_fmt)
        ws.write(row, 2, lang_report.total_korean_chars, num_fmt)
        ws.write(row, 3, lang_report.total_korean_words, num_fmt)
        ws.write(row, 4, lang_report.hits, num_fmt)
        ws.write(row, 5, Path(lang_report.target_file).name, text_fmt)
        row += 1

    # Totals row
    ws.write(row, 0, "TOTAL", total_fmt)
    ws.write(row, 1, report.total_misses, total_fmt)
    ws.write(row, 2, report.total_korean_chars, total_fmt)
    ws.write(row, 3, report.total_korean_words, total_fmt)
    ws.write(row, 4, report.total_hits, total_fmt)
    ws.write(row, 5, "", total_fmt)

    # === INFO SHEET ===
    ws_info = wb.add_worksheet("Info")
    ws_info.set_column('A:A', 25)
    ws_info.set_column('B:B', 80)

    info_header = wb.add_format({'bold': True, 'bg_color': '#5B9BD5', 'font_color': 'white'})
    ws_info.write(0, 0, "Field", info_header)
    ws_info.write(0, 1, "Value", info_header)

    info_data = [
        ("Report Generated", report.timestamp),
        ("Source Path", report.source_path),
        ("Target Path", report.target_path),
        ("Mode", report.mode),
        ("Languages Found", len(report.by_language)),
        ("Total Source Keys", report.total_source_keys),
        ("Total Target Korean", report.total_target_korean),
        ("Total Hits", report.total_hits),
        ("Total Misses", report.total_misses),
        ("Total Korean Chars", report.total_korean_chars),
        ("Total Korean Words", report.total_korean_words),
    ]
    for i, (field, value) in enumerate(info_data, 1):
        ws_info.write(i, 0, field)
        ws_info.write(i, 1, str(value) if not isinstance(value, int) else value, num_fmt if isinstance(value, int) else None)

    # === PER-LANGUAGE DETAIL SHEETS (first 1000 entries per language) ===
    for lang in sorted_langs:
        lang_report = report.by_language[lang]
        if not lang_report.entries:
            continue

        # Excel sheet names limited to 31 chars
        sheet_name = f"{lang[:28]}"
        ws_lang = wb.add_worksheet(sheet_name)
        ws_lang.set_column('A:A', 20)  # StringId
        ws_lang.set_column('B:B', 50)  # StrOrigin
        ws_lang.set_column('C:C', 50)  # Korean Text
        ws_lang.set_column('D:D', 12)  # Korean Chars
        ws_lang.set_column('E:E', 12)  # Korean Words

        # Headers
        detail_headers = ["StringId", "StrOrigin", "Korean Text (Str)", "Korean Chars", "Korean Words"]
        for col, h in enumerate(detail_headers):
            ws_lang.write(0, col, h, header_fmt)

        # Data (limit to 1000 for Excel performance)
        for i, entry in enumerate(lang_report.entries[:1000], 1):
            ws_lang.write(i, 0, entry.string_id)
            ws_lang.write(i, 1, entry.str_origin[:200], text_fmt)
            ws_lang.write(i, 2, entry.str_value[:200], text_fmt)
            ws_lang.write(i, 3, entry.korean_chars, num_fmt)
            ws_lang.write(i, 4, entry.korean_words, num_fmt)

        if len(lang_report.entries) > 1000:
            ws_lang.write(1001, 0, f"... and {len(lang_report.entries) - 1000} more entries (see XML file)")

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
    lines.append("=" * 70)
    lines.append("MISSING TRANSLATION REPORT")
    lines.append("=" * 70)
    lines.append(f"Generated: {report.timestamp}")
    lines.append(f"Source: {report.source_path}")
    lines.append(f"Target: {report.target_path}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append("-" * 70)
    lines.append(f"  Source keys (StrOrigin, StringId):  {report.total_source_keys:,}")
    lines.append(f"  Target Korean entries:              {report.total_target_korean:,}")
    lines.append(f"  Total HITS (found in source):       {report.total_hits:,}")
    lines.append(f"  Total MISSES (need translation):    {report.total_misses:,}")
    lines.append(f"  Total Korean characters:            {report.total_korean_chars:,}")
    lines.append(f"  Total Korean words/sequences:       {report.total_korean_words:,}")
    lines.append("")
    lines.append("PER-LANGUAGE BREAKDOWN")
    lines.append("-" * 70)
    lines.append(f"{'Language':<10} {'Missing':>10} {'KR Chars':>12} {'KR Words':>12} {'Hits':>10}")
    lines.append("-" * 70)

    for lang in sorted(report.by_language.keys()):
        lr = report.by_language[lang]
        lines.append(f"{lang:<10} {lr.misses:>10,} {lr.total_korean_chars:>12,} {lr.total_korean_words:>12,} {lr.hits:>10,}")

    lines.append("-" * 70)
    lines.append(f"{'TOTAL':<10} {report.total_misses:>10,} {report.total_korean_chars:>12,} {report.total_korean_words:>12,} {report.total_hits:>10,}")
    lines.append("=" * 70)

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
            str_val = safe_get_attr(loc, "Str")
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
