"""
Generators Base Module
======================
Shared functionality for all datasheet generators.

Contains:
- XML parsing and sanitization
- Language table loading
- Korean detection
- Placeholder normalization
- Excel autofit
- Common styles
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Iterator
from dataclasses import dataclass

from lxml import etree as ET
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from config import DEPTH_COLORS, STATUS_OPTIONS

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
# XML SANITIZATION
# =============================================================================

_bad_entity_re = re.compile(r"&(?!lt;|gt;|amp;|apos;|quot;)")


def _fix_entities(txt: str) -> str:
    """Replace unescaped ampersands with &amp;"""
    return _bad_entity_re.sub("&amp;", txt)


def _escape_newlines_in_seg(txt: str) -> str:
    """Escape newlines inside <seg> tags."""
    def repl(m: re.Match) -> str:
        seg = m.group(1).replace("\n", "&lt;br/&gt;").replace("\r", "")
        return f"<seg>{seg}</seg>"
    return re.sub(r"<seg>(.*?)</seg>", repl, txt, flags=re.DOTALL)


def sanitize_xml(raw: str) -> str:
    """
    Sanitize XML content for parsing:
    - Fix unescaped entities
    - Escape newlines in <seg> tags
    - Handle malformed attributes
    """
    raw = _fix_entities(raw)
    raw = _escape_newlines_in_seg(raw)

    # Fix < inside attribute values
    raw = re.sub(
        r'="([^"]*<[^"]*)"',
        lambda m: '="' + m.group(1).replace("<", "&lt;") + '"',
        raw
    )

    # Fix & inside attribute values
    raw = re.sub(
        r'="([^"]*&[^ltgapoqu][^"]*)"',
        lambda m: '="' + m.group(1).replace("&", "&amp;") + '"',
        raw
    )

    return raw


def parse_xml_file(path: Path) -> Optional[ET._Element]:
    """
    Parse an XML file with sanitization.

    Returns:
        Root element or None if parsing fails
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None

    raw = sanitize_xml(raw)

    try:
        return ET.fromstring(raw.encode("utf-8"))
    except ET.XMLSyntaxError:
        return None


def iter_xml_files(folder: Path, pattern: str = "*.xml") -> Iterator[Path]:
    """Recursively iterate over XML files in a folder."""
    if not folder.exists():
        return
    for path in folder.rglob(pattern):
        if path.is_file():
            yield path


# =============================================================================
# LANGUAGE TABLE LOADING
# =============================================================================

def load_language_tables(folder: Path) -> Dict[str, Dict[str, Tuple[str, str]]]:
    """
    Load all non-Korean language tables with normalized placeholder keys.

    Args:
        folder: Path to language data folder

    Returns:
        {lang_code: {normalized_korean: (translation, stringid)}}
    """
    tables: Dict[str, Dict[str, Tuple[str, str]]] = {}

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

        tbl: Dict[str, Tuple[str, str]] = {}

        for loc in root_el.iter("LocStr"):
            origin = loc.get("StrOrigin") or ""
            tr = loc.get("Str") or ""
            sid = loc.get("StringId") or ""

            if not origin:
                continue

            normalized_origin = normalize_placeholders(origin)

            # Prefer good translations (no Korean) over bad ones
            if normalized_origin in tbl:
                existing_tr, _ = tbl[normalized_origin]
                if is_good_translation(tr) and not is_good_translation(existing_tr):
                    tbl[normalized_origin] = (tr, sid)
            else:
                tbl[normalized_origin] = (tr, sid)

        tables[lang] = tbl

    return tables


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
    lang_table: Dict[str, Tuple[str, str]],
    lang_code: str,
    include_translation_col: bool = True
) -> None:
    """
    Write rows to a worksheet with translations.

    Args:
        ws: Target worksheet
        rows: List of RowItem to write
        lang_table: Language table {normalized_korean: (translation, stringid)}
        lang_code: Language code (e.g., "eng", "fre")
        include_translation_col: Whether to include Translation column (False for ENG)
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
        normalized = normalize_placeholders(item.text)

        # Lookup translation
        translation, stringid = lang_table.get(normalized, ("", ""))

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
