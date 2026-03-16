"""Write Excel reports using xlsxwriter."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import xlsxwriter

from .text_utils import br_to_newline

logger = logging.getLogger(__name__)

# Columns whose values may contain <br/> and need text_wrap in Excel
_MULTILINE_KEYS = {"str_origin", "str_value", "old_value", "correction", "_old_strorigin", "_strorigin_diff", "_old_str", "_str_diff"}


def write_extraction_excel(
    out_path: Path,
    entries: Sequence[dict],
    *,
    columns: list[tuple[str, str, int]],
    sheet_name: str = "Extraction",
    header_bg: str = "#2E4057",
    header_fg: str = "#FFFFFF",
    sort_key=None,
    extra_formats: dict[str, dict] | None = None,
) -> int:
    """Write entries to an xlsx file.

    Parameters
    ----------
    columns : list of (dict_key, header_label, col_width)
        Columns to write. *dict_key* is the key in each entry dict.
    sort_key : callable, optional
        Sort function applied to *entries* before writing.
    extra_formats : {dict_key: format_props}
        Per-column format overrides (e.g. bold, font_color).

    Returns the number of rows written (excluding header).
    """
    if sort_key:
        entries = sorted(entries, key=sort_key)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb = xlsxwriter.Workbook(str(out_path))
    ws = wb.add_worksheet(sheet_name)

    # Header format
    hdr_fmt = wb.add_format({
        "bold": True,
        "bg_color": header_bg,
        "font_color": header_fg,
        "border": 1,
    })

    # Text-wrap format for columns that may contain newlines
    wrap_fmt = wb.add_format({"text_wrap": True})

    # Per-column body formats
    col_fmts: dict[int, xlsxwriter.format.Format | None] = {}
    for ci, (key, _, _) in enumerate(columns):
        if extra_formats and key in extra_formats:
            props = dict(extra_formats[key])
            if key in _MULTILINE_KEYS:
                props["text_wrap"] = True
            col_fmts[ci] = wb.add_format(props)
        elif key in _MULTILINE_KEYS:
            col_fmts[ci] = wrap_fmt
        else:
            col_fmts[ci] = None

    # Write header + set widths
    for ci, (_, label, width) in enumerate(columns):
        ws.write(0, ci, label, hdr_fmt)
        ws.set_column(ci, ci, width)

    # Write data (convert <br/> → \n for human-readable Excel)
    row = 1
    for entry in entries:
        for ci, (key, _, _) in enumerate(columns):
            val = entry.get(key, "")
            if key in _MULTILINE_KEYS and isinstance(val, str):
                val = br_to_newline(val)
            fmt = col_fmts[ci]
            if fmt:
                ws.write(row, ci, val, fmt)
            else:
                ws.write(row, ci, val)
        row += 1

    ws.autofilter(0, 0, max(row - 1, 0), len(columns) - 1)
    ws.freeze_panes(1, 0)
    wb.close()

    count = row - 1
    logger.info("Wrote %d rows → %s", count, out_path.name)
    return count


def write_blacklist_excel(
    out_path: Path,
    matches: Sequence[dict],
) -> int:
    """Write blacklist match results.

    Each *match* dict has: ``string_id``, ``str_origin``, ``str_value``,
    ``matched_term``.
    """
    return write_extraction_excel(
        out_path,
        matches,
        columns=[
            ("string_id", "StringID", 35),
            ("str_origin", "StrOrigin", 45),
            ("str_value", "Str", 60),
            ("matched_term", "Matched Term", 25),
        ],
        sheet_name="Blacklist Matches",
        header_bg="#8B0000",
        sort_key=lambda e: (e.get("matched_term", "").lower(), e.get("string_id", "").lower()),
        extra_formats={
            "matched_term": {"bold": True, "font_color": "#8B0000"},
        },
    )
