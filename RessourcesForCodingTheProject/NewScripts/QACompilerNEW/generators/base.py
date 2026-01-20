"""
Generators Base Module
======================
Shared functionality for all datasheet generators.

Contains:
- XML parsing and sanitization
- Language table loading (with duplicate handling)
- Korean detection
- Placeholder normalization
- Excel autofit
- Common styles
- EXPORT-based duplicate translation resolution
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Iterator, Set
from dataclasses import dataclass

from lxml import etree as ET
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from config import DEPTH_COLORS, STATUS_OPTIONS, EXPORT_FOLDER

# =============================================================================
# LOGGING
# =============================================================================

def get_logger(name: str) -> logging.Logger:
    """Create a logger with console output."""
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)

    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)-8s  %(message)s"))
        handler.setLevel(logging.INFO)
        log.addHandler(handler)

    log.propagate = False
    return log


# =============================================================================
# TEXT NORMALIZATION
# =============================================================================

_placeholder_suffix_re = re.compile(r'\{([^#}]+)#[^}]+\}')
_whitespace_re = re.compile(r'\s+', flags=re.UNICODE)


def normalize_placeholders(text: str) -> str:
    """
    Normalize text for matching:
    1) Remove '#...' suffix inside {...} placeholders
    2) Collapse all whitespace to single space
    3) Trim leading/trailing spaces
    """
    if not text:
        return ""
    text = _placeholder_suffix_re.sub(r'{\1}', text)
    text = _whitespace_re.sub(' ', text).strip()
    return text


# =============================================================================
# KOREAN DETECTION
# =============================================================================

_korean_re = re.compile(r'[\uAC00-\uD7AF]')


def contains_korean(text: str) -> bool:
    """Check if text contains Korean characters."""
    return bool(_korean_re.search(text)) if text else False


def is_good_translation(text: str) -> bool:
    """Check if translation is valid (non-empty and no Korean)."""
    return bool(text) and not contains_korean(text)


# =============================================================================
# EXPORT STRINGID INDEX (for duplicate translation resolution)
# =============================================================================

_EXPORT_INDEX: Optional[Dict[str, Set[str]]] = None  # Module-level cache


def build_export_stringid_index(export_folder: Path) -> Dict[str, Set[str]]:
    """
    Scan EXPORT folder and build: normalized_filename → {stringid_1, stringid_2, ...}

    This allows us to determine which StringIDs belong to which source data file.
    For example, skillinfo_pc.staticinfo.loc.xml contains StringIDs from skillinfo_pc.staticinfo.xml.

    Args:
        export_folder: Path to EXPORT folder containing .loc.xml files

    Returns:
        Dict mapping normalized filename (without .loc.xml) to set of StringIDs
        Example: {"skillinfo_pc.staticinfo": {"1001", "1002", "1003"}}
    """
    index: Dict[str, Set[str]] = {}

    if not export_folder.exists():
        return index

    # Scan all .loc.xml files recursively
    for path in export_folder.rglob("*.loc.xml"):
        if not path.is_file():
            continue

        # Normalize filename: remove .loc.xml to get base name
        # "skillinfo_pc.staticinfo.loc.xml" → "skillinfo_pc.staticinfo"
        filename_key = path.name.lower().replace(".loc.xml", "")

        try:
            # Parse the file to extract StringIDs
            tree = ET.parse(str(path))
            root = tree.getroot()

            stringids: Set[str] = set()
            for loc_str in root.iter("LocStr"):
                sid = loc_str.get("StringId")
                if sid:
                    stringids.add(sid)

            if stringids:
                # Merge if multiple files have same base name (different folders)
                if filename_key in index:
                    index[filename_key].update(stringids)
                else:
                    index[filename_key] = stringids

        except ET.XMLSyntaxError:
            # Skip malformed files
            continue
        except Exception:
            # Skip files that can't be read
            continue

    return index


def get_export_index() -> Dict[str, Set[str]]:
    """
    Lazy-load and cache EXPORT index.

    Returns:
        Dict mapping normalized filename to set of StringIDs
    """
    global _EXPORT_INDEX
    if _EXPORT_INDEX is None:
        print("  Building EXPORT StringID index...")
        _EXPORT_INDEX = build_export_stringid_index(EXPORT_FOLDER)
        print(f"  Indexed {len(_EXPORT_INDEX)} EXPORT files")
    return _EXPORT_INDEX


def get_export_key(data_filename: str) -> str:
    """
    Convert data filename to export lookup key.

    Args:
        data_filename: e.g., "skillinfo_pc.staticinfo.xml"

    Returns:
        Normalized key: e.g., "skillinfo_pc.staticinfo"
    """
    return data_filename.lower().replace(".xml", "").replace(".loc", "")


def resolve_translation(
    korean_text: str,
    lang_table: Dict[str, List[Tuple[str, str]]],
    data_filename: str = "",
    export_index: Optional[Dict[str, Set[str]]] = None
) -> Tuple[str, str]:
    """
    Resolve correct translation using EXPORT mapping for duplicate disambiguation.

    When the same Korean text appears in multiple files with different translations,
    this function uses the EXPORT folder to find which StringID belongs to the
    current data file, returning the context-appropriate translation.

    Algorithm:
    1. Normalize Korean text
    2. Get all (translation, stringid) pairs for this text
    3. If only one → use it
    4. If multiple → find StringID that exists in matching EXPORT file
    5. Fallback → first good translation (no Korean)

    Args:
        korean_text: The Korean source text to translate
        lang_table: Language table with ALL translations stored as lists
                    {normalized_korean: [(translation, stringid), ...]}
        data_filename: Source data file name (e.g., "skillinfo_pc.staticinfo.xml")
        export_index: Optional pre-loaded EXPORT index (uses global cache if None)

    Returns:
        Tuple of (translation, stringid). Returns ("", "") if not found.
    """
    if not korean_text:
        return ("", "")

    normalized = normalize_placeholders(korean_text)
    if not normalized:
        return ("", "")

    # Get all translation candidates
    candidates = lang_table.get(normalized)
    if not candidates:
        return ("", "")

    # If only one candidate, return it
    if len(candidates) == 1:
        return candidates[0]

    # Multiple candidates - try to disambiguate using EXPORT
    if data_filename:
        if export_index is None:
            export_index = get_export_index()

        export_key = get_export_key(data_filename)
        export_stringids = export_index.get(export_key, set())

        if export_stringids:
            # Find candidate whose StringID is in this EXPORT file
            for translation, stringid in candidates:
                if stringid in export_stringids:
                    print(f"    [DUPLICATE] Korean '{korean_text[:30]}...' has {len(candidates)} translations")
                    print(f"    [RESOLVED] Using StringID {stringid} (matched {data_filename})")
                    return (translation, stringid)

    # Fallback: prefer good translation (no Korean)
    for translation, stringid in candidates:
        if is_good_translation(translation):
            return (translation, stringid)

    # Last resort: return first candidate
    return candidates[0]


# =============================================================================
# XML SANITIZATION (EXACT COPY FROM MONOLITH)
# =============================================================================

_bad_entity_re = re.compile(r'&(?!lt;|gt;|amp;|apos;|quot;)')


def _fix_bad_entities(txt: str) -> str:
    return _bad_entity_re.sub("&amp;", txt)


def _preprocess_newlines(raw: str) -> str:
    def repl(m: re.Match) -> str:
        inner = m.group(1).replace("\n", "&lt;br/&gt;").replace("\r\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"
    return re.sub(r"<seg>(.*?)</seg>", repl, raw, flags=re.DOTALL)


def sanitize_xml(raw: str) -> str:
    raw = _fix_bad_entities(raw)
    raw = _preprocess_newlines(raw)
    raw = re.sub(r'="([^"]*<[^"]*)"',
                 lambda m: '="' + m.group(1).replace("<", "&lt;") + '"', raw)
    raw = re.sub(r'="([^"]*&[^ltgapoqu][^"]*)"',
                 lambda m: '="' + m.group(1).replace("&", "&amp;") + '"', raw)
    # Tag stack repair for malformed XML
    tag_open  = re.compile(r"<([A-Za-z0-9_]+)(\s[^>]*)?>")
    tag_close = re.compile(r"</([A-Za-z0-9_]+)>")
    stack: List[str] = []
    out:   List[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        mo = tag_open.match(stripped)
        if mo:
            stack.append(mo.group(1)); out.append(line); continue
        mc = tag_close.match(stripped)
        if mc:
            if stack and stack[-1] == mc.group(1):
                stack.pop(); out.append(line)
            else:
                out.append(stack and f"</{stack.pop()}>" or line)
            continue
        if stripped.startswith("</>"):
            out.append(stack and line.replace("</>", f"</{stack.pop()}>") or line)
            continue
        out.append(line)
    while stack:
        out.append(f"</{stack.pop()}>")
    return "\n".join(out)


def parse_xml_file(path: Path) -> Optional[ET._Element]:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None
    cleaned = sanitize_xml(raw)
    wrapped = f"<ROOT>\n{cleaned}\n</ROOT>"
    try:
        return ET.fromstring(
            wrapped.encode("utf-8"),
            parser=ET.XMLParser(huge_tree=True)
        )
    except ET.XMLSyntaxError:
        try:
            return ET.fromstring(
                wrapped.encode("utf-8"),
                parser=ET.XMLParser(recover=True, huge_tree=True)
            )
        except ET.XMLSyntaxError:
            return None


def iter_xml_files(
    root: Path,
    suffixes: Tuple[str, ...] = (".xml", ".seqc")
) -> Iterator[Path]:
    """Recursively iterate over XML files in a folder."""
    if not root.exists():
        return
    for dp, _, files in os.walk(root):
        for fn in files:
            low = fn.lower()
            if any(low.endswith(suf) for suf in suffixes):
                yield Path(dp) / fn


# =============================================================================
# LANGUAGE TABLE LOADING
# =============================================================================

def load_language_tables(folder: Path) -> Dict[str, Dict[str, List[Tuple[str, str]]]]:
    """
    Load all non-Korean language tables with normalized placeholder keys.

    Stores ALL translations for each Korean text to support duplicate resolution.
    When the same Korean text appears in multiple files with different context-specific
    translations, we preserve all of them for later disambiguation using EXPORT mapping.

    Args:
        folder: Path to language data folder

    Returns:
        {lang_code: {normalized_korean: [(translation, stringid), ...]}}

    Note: The list preserves all translations for a given Korean text.
          Good translations (no Korean) are sorted to the front.
    """
    tables: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}

    for path in iter_xml_files(folder):
        stem = path.stem.lower()
        if not stem.startswith("languagedata_"):
            continue
        if stem.endswith("kor"):
            continue

        lang = stem.split("_", 1)[1]
        root_el = parse_xml_file(path)
        if root_el is None:
            continue

        tbl: Dict[str, List[Tuple[str, str]]] = {}

        for loc in root_el.iter("LocStr"):
            origin = loc.get("StrOrigin") or ""
            tr = loc.get("Str") or ""
            sid = loc.get("StringId") or ""

            if not origin:
                continue

            normalized_origin = normalize_placeholders(origin)

            # Store ALL translations for this Korean text
            if normalized_origin not in tbl:
                tbl[normalized_origin] = []

            # Add this translation (avoid exact duplicates)
            entry = (tr, sid)
            if entry not in tbl[normalized_origin]:
                tbl[normalized_origin].append(entry)

        # Sort each list: good translations first, then bad ones
        for key in tbl:
            tbl[key].sort(key=lambda x: (0 if is_good_translation(x[0]) else 1))

        tables[lang] = tbl

    return tables


def get_first_translation(
    lang_table: Dict[str, List[Tuple[str, str]]],
    korean_text: str
) -> Tuple[str, str]:
    """
    Simple lookup that returns the first (best) translation.

    This provides backward compatibility for code that doesn't need
    context-aware duplicate resolution.

    Args:
        lang_table: Language table {normalized_korean: [(translation, stringid), ...]}
        korean_text: Korean text to translate

    Returns:
        (translation, stringid) or ("", "") if not found
    """
    normalized = normalize_placeholders(korean_text)
    candidates = lang_table.get(normalized, [])
    return candidates[0] if candidates else ("", "")


# =============================================================================
# EXCEL STYLES
# =============================================================================

# Border style
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

# Header style
HEADER_FILL = PatternFill(start_color="ADD8E6", end_color="ADD8E6", fill_type="solid")
HEADER_FONT = Font(bold=True)
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=True)

# Depth-based styles
def get_depth_fill(depth: int) -> PatternFill:
    """Get fill color for a given depth level."""
    colors = DEPTH_COLORS
    color = colors[min(depth, len(colors) - 1)]
    return PatternFill(start_color=color, end_color=color, fill_type="solid")


def get_depth_font(depth: int) -> Font:
    """Get font for a given depth level."""
    return Font(bold=(depth == 0))


# =============================================================================
# EXCEL AUTOFIT
# =============================================================================

def autofit_worksheet(
    ws,
    min_width: int = 10,
    max_width: int = 80,
    row_height_per_line: float = 15.0,
    min_row_height: float = 20.0
) -> None:
    """
    Auto-fit column widths and row heights based on cell content.

    Args:
        ws: Worksheet to autofit
        min_width: Minimum column width
        max_width: Maximum column width
        row_height_per_line: Height per line of wrapped text
        min_row_height: Minimum row height
    """
    # Calculate optimal column widths
    col_widths: Dict[str, float] = {}

    for row in ws.iter_rows():
        for cell in row:
            if cell.value:
                col_letter = get_column_letter(cell.column)
                content_len = len(str(cell.value))
                width = min(max(content_len * 1.1 + 2, min_width), max_width)
                col_widths[col_letter] = max(col_widths.get(col_letter, min_width), width)

    # Apply column widths
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    # Calculate optimal row heights (considering text wrap)
    for row_idx, row in enumerate(ws.iter_rows(), start=1):
        max_lines = 1
        for cell in row:
            if cell.value:
                col_letter = get_column_letter(cell.column)
                col_width = col_widths.get(col_letter, min_width)
                text = str(cell.value)
                # Estimate lines needed
                chars_per_line = max(int(col_width / 1.1), 1)
                lines = max(1, len(text) // chars_per_line + text.count('\n') + 1)
                max_lines = max(max_lines, lines)

        height = max(min_row_height, max_lines * row_height_per_line)
        ws.row_dimensions[row_idx].height = height


# =============================================================================
# EXCEL HELPERS
# =============================================================================

def add_status_dropdown(ws, col: int, start_row: int = 2, end_row: int = 10000) -> None:
    """Add STATUS dropdown validation to a column."""
    dv = DataValidation(
        type="list",
        formula1=f'"{",".join(STATUS_OPTIONS)}"',
        allow_blank=True
    )
    dv.error = "Please select from the list"
    dv.errorTitle = "Invalid Status"
    ws.add_data_validation(dv)

    for row in range(start_row, min(end_row, ws.max_row + 1)):
        dv.add(ws.cell(row=row, column=col))


def create_header_row(ws, headers: List[str], row: int = 1) -> None:
    """Create a styled header row."""
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER


# =============================================================================
# ROW DATA STRUCTURE
# =============================================================================

@dataclass
class RowItem:
    """Represents a row of data for the Excel output."""
    depth: int           # Indentation level (0 = parent)
    text: str            # Korean original text
    needs_translation: bool = True  # Whether this row needs translation
    strkey: str = ""     # String key for reference


def emit_rows_to_worksheet(
    ws,
    rows: List[RowItem],
    lang_table: Dict[str, List[Tuple[str, str]]],
    lang_code: str,
    include_translation_col: bool = True,
    data_filename: str = "",
    export_index: Optional[Dict[str, Set[str]]] = None
) -> None:
    """
    Write rows to a worksheet with translations.

    Args:
        ws: Target worksheet
        rows: List of RowItem to write
        lang_table: Language table {normalized_korean: [(translation, stringid), ...]}
        lang_code: Language code (e.g., "eng", "fre")
        include_translation_col: Whether to include Translation column (False for ENG)
        data_filename: Source data file for context-aware duplicate resolution
        export_index: Optional pre-loaded EXPORT index (uses global cache if None)
    """
    # Headers
    if include_translation_col:
        headers = ["Original (KR)", "English (ENG)", "Translation (LOC)", "STATUS", "COMMENT", "STRINGID", "SCREENSHOT"]
    else:
        headers = ["Original (KR)", "English (ENG)", "STATUS", "COMMENT", "STRINGID", "SCREENSHOT"]

    create_header_row(ws, headers)

    # Get English table for ENG column
    # (Assume lang_table includes 'eng' key from parent)

    current_row = 2
    for item in rows:
        # Use context-aware resolution if data_filename is provided
        if data_filename:
            translation, stringid = resolve_translation(
                item.text, lang_table, data_filename, export_index
            )
        else:
            # Fallback to simple first-translation lookup
            translation, stringid = get_first_translation(lang_table, item.text)

        # Write cells
        col = 1

        # Original (KR)
        cell = ws.cell(row=current_row, column=col, value=item.text)
        cell.fill = get_depth_fill(item.depth)
        cell.font = get_depth_font(item.depth)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = THIN_BORDER
        col += 1

        # English (ENG) - for now use translation if lang_code is eng
        eng_text = translation if lang_code == "eng" else ""
        cell = ws.cell(row=current_row, column=col, value=eng_text)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = THIN_BORDER
        col += 1

        # Translation (LOC) - skip for ENG workbook
        if include_translation_col:
            cell = ws.cell(row=current_row, column=col, value=translation if lang_code != "eng" else "")
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = THIN_BORDER
            col += 1

        # STATUS
        cell = ws.cell(row=current_row, column=col, value="")
        cell.border = THIN_BORDER
        col += 1

        # COMMENT
        cell = ws.cell(row=current_row, column=col, value="")
        cell.border = THIN_BORDER
        col += 1

        # STRINGID (as text to prevent scientific notation)
        cell = ws.cell(row=current_row, column=col, value=stringid)
        cell.number_format = '@'
        cell.border = THIN_BORDER
        col += 1

        # SCREENSHOT
        cell = ws.cell(row=current_row, column=col, value="")
        cell.border = THIN_BORDER

        current_row += 1

    # Add STATUS dropdown
    status_col = 4 if include_translation_col else 3
    add_status_dropdown(ws, status_col, start_row=2, end_row=current_row)
