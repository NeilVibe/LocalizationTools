"""
Excel Writer Utility

Writes QuickCheck output files (LineCheck, TermCheck, Glossary) as clean Excel.
Uses xlsxwriter (write-only, reliable).
"""
from __future__ import annotations

import logging
from typing import List, Tuple

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared colour palette
# ---------------------------------------------------------------------------
COL_HEADER_BG = "#4472C4"   # Blue
COL_HEADER_FG = "#FFFFFF"   # White
COL_GROUP_BG  = "#D6E4F0"   # Light blue — term/source group header rows
COL_ALT_BG    = "#F5F9FF"   # Very light blue — alternating rows
COL_WHITE     = "#FFFFFF"
COL_DARK_TEXT = "#1A1A1A"
FG_SID        = "#555599"   # Muted purple — StringID cells


def _require_xlsxwriter() -> None:
    if xlsxwriter is None:
        raise ImportError(
            "xlsxwriter is required for Excel output. Install with: pip install xlsxwriter"
        )


# ---------------------------------------------------------------------------
# LineCheck Excel
# ---------------------------------------------------------------------------

def write_line_check_excel(
    results: list,          # List[LineCheckResult]
    output_path: str,
    lang_code: str = "",
) -> bool:
    """
    Write LINE CHECK results to Excel.

    Columns: Source (KR) | Translation 1 | SID 1 | Translation 2 | SID 2 | ...
    One row per inconsistency group. Max 8 translation columns (each with a SID column).
    """
    _require_xlsxwriter()

    wb = None
    try:
        wb = xlsxwriter.Workbook(output_path)
        ws = wb.add_worksheet(f"LineCheck {lang_code}" if lang_code else "LineCheck")

        fmt_header = wb.add_format({
            "bold": True, "bg_color": COL_HEADER_BG, "font_color": COL_HEADER_FG,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })
        fmt_source = wb.add_format({
            "bold": True, "bg_color": COL_GROUP_BG, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })
        fmt_trans = wb.add_format({
            "bg_color": COL_WHITE, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })
        fmt_trans_alt = wb.add_format({
            "bg_color": COL_ALT_BG, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })
        fmt_sid = wb.add_format({
            "bg_color": COL_WHITE, "font_color": FG_SID,
            "border": 1, "valign": "vcenter",
        })
        fmt_sid_alt = wb.add_format({
            "bg_color": COL_ALT_BG, "font_color": FG_SID,
            "border": 1, "valign": "vcenter",
        })
        fmt_summary = wb.add_format({"italic": True, "font_color": "#666666"})

        max_trans = min(max((len(r.translations) for r in results), default=2), 8)

        # Header: Source | Trans 1 | SID 1 | Trans 2 | SID 2 | ...
        ws.set_row(0, 20)
        ws.write(0, 0, "Source (KR)", fmt_header)
        for i in range(max_trans):
            ws.write(0, 1 + i * 2,     f"Translation {i + 1}", fmt_header)
            ws.write(0, 1 + i * 2 + 1, f"StringID {i + 1}",    fmt_header)

        ws.set_column(0, 0, 30)
        for i in range(max_trans):
            ws.set_column(1 + i * 2,     1 + i * 2,     35)   # Translation col
            ws.set_column(1 + i * 2 + 1, 1 + i * 2 + 1, 20)   # StringID col

        row = 1
        for idx, result in enumerate(results):
            fmt_t   = fmt_trans   if idx % 2 == 0 else fmt_trans_alt
            fmt_s   = fmt_sid     if idx % 2 == 0 else fmt_sid_alt
            ws.write(row, 0, result.source, fmt_source)
            for i, trans in enumerate(result.translations[:max_trans]):
                sid = result.string_ids[i] if i < len(result.string_ids) else ""
                ws.write(row, 1 + i * 2,     trans, fmt_t)
                ws.write(row, 1 + i * 2 + 1, sid,   fmt_s)
            row += 1

        ws.set_row(row + 1, 16)
        ws.write(row + 1, 0, f"Total: {len(results)} inconsistencies", fmt_summary)

        wb.close()
        wb = None   # mark closed so finally doesn't double-close
        return True

    except Exception as e:
        logger.error("Failed to write LineCheck Excel %s: %s", output_path, e)
        return False

    finally:
        if wb is not None:
            try:
                wb.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# TermCheck Excel
# ---------------------------------------------------------------------------

def write_term_check_excel(
    results: list,          # List[TermCheckResult]
    output_path: str,
    lang_code: str = "",
    match_mode: str = "",
) -> bool:
    """
    Write TERM CHECK results to Excel.

    Columns: Term (KR) | Expected Translation | Source Text | Translation Found | StringID
    One row per issue. Term/expected repeated on each row for easy filtering.
    """
    _require_xlsxwriter()

    wb = None
    try:
        title = f"TermCheck {lang_code}" if lang_code else "TermCheck"
        wb = xlsxwriter.Workbook(output_path)
        ws = wb.add_worksheet(title[:31])

        fmt_header = wb.add_format({
            "bold": True, "bg_color": COL_HEADER_BG, "font_color": COL_HEADER_FG,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })
        fmt_term_row = wb.add_format({
            "bold": True, "bg_color": COL_GROUP_BG, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })
        fmt_issue = wb.add_format({
            "bg_color": COL_WHITE, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })
        fmt_issue_alt = wb.add_format({
            "bg_color": COL_ALT_BG, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })
        fmt_summary = wb.add_format({"italic": True, "font_color": "#666666"})

        ws.set_row(0, 22)
        for i, h in enumerate(["Term (KR)", "Expected Translation", "Source Text", "Translation Found", "StringID"]):
            ws.write(0, i, h, fmt_header)

        ws.set_column(0, 0, 22)
        ws.set_column(1, 1, 22)
        ws.set_column(2, 2, 45)
        ws.set_column(3, 3, 45)
        ws.set_column(4, 4, 20)

        row = 1
        for result in results:
            for issue_idx, issue in enumerate(result.issues):
                fmt = fmt_issue if issue_idx % 2 == 0 else fmt_issue_alt
                row_fmt = fmt_term_row if issue_idx == 0 else fmt
                ws.write(row, 0, result.term, row_fmt)
                ws.write(row, 1, result.reference_translation, row_fmt)
                ws.write(row, 2, issue.source_text, fmt)
                ws.write(row, 3, issue.translation_text, fmt)
                ws.write(row, 4, issue.string_id, fmt)
                row += 1

        total_issues = sum(r.issue_count for r in results)
        label = f"Total: {len(results)} terms with issues, {total_issues} individual issues"
        if match_mode:
            label += f" (mode: {match_mode})"
        ws.write(row + 1, 0, label, fmt_summary)

        wb.close()
        wb = None
        return True

    except Exception as e:
        logger.error("Failed to write TermCheck Excel %s: %s", output_path, e)
        return False

    finally:
        if wb is not None:
            try:
                wb.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Glossary Excel
# ---------------------------------------------------------------------------

def write_glossary_excel(
    glossary: List[Tuple[str, str, int]],   # [(source, translation, count), ...]
    output_path: str,
    lang_code: str = "",
) -> bool:
    """
    Write extracted glossary to Excel.

    Columns: # | Source (KR) | Translation | Occurrences
    Sorted by occurrence count descending, then source length ascending.
    """
    _require_xlsxwriter()

    wb = None
    try:
        title = f"Glossary {lang_code}" if lang_code else "Glossary"
        wb = xlsxwriter.Workbook(output_path)
        ws = wb.add_worksheet(title[:31])

        fmt_header = wb.add_format({
            "bold": True, "bg_color": COL_HEADER_BG, "font_color": COL_HEADER_FG,
            "border": 1, "align": "center", "valign": "vcenter",
        })
        fmt_num = wb.add_format({
            "bg_color": COL_WHITE, "font_color": "#888888",
            "border": 1, "align": "right", "valign": "vcenter",
        })
        fmt_source = wb.add_format({
            "bold": True, "bg_color": COL_WHITE, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter",
        })
        fmt_trans = wb.add_format({
            "bg_color": COL_WHITE, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter",
        })
        fmt_count = wb.add_format({
            "bg_color": COL_WHITE, "font_color": "#555599",
            "border": 1, "align": "right", "valign": "vcenter", "bold": True,
        })
        fmt_num_alt = wb.add_format({
            "bg_color": COL_ALT_BG, "font_color": "#888888",
            "border": 1, "align": "right", "valign": "vcenter",
        })
        fmt_source_alt = wb.add_format({
            "bold": True, "bg_color": COL_ALT_BG, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter",
        })
        fmt_trans_alt = wb.add_format({
            "bg_color": COL_ALT_BG, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter",
        })
        fmt_count_alt = wb.add_format({
            "bg_color": COL_ALT_BG, "font_color": "#555599",
            "border": 1, "align": "right", "valign": "vcenter", "bold": True,
        })
        fmt_summary = wb.add_format({"italic": True, "font_color": "#666666"})

        ws.set_row(0, 22)
        for i, h in enumerate(["#", "Source (KR)", "Translation", "Occurrences"]):
            ws.write(0, i, h, fmt_header)

        ws.set_column(0, 0, 6)
        ws.set_column(1, 1, 25)
        ws.set_column(2, 2, 35)
        ws.set_column(3, 3, 14)

        sorted_glossary = sorted(glossary, key=lambda x: (-x[2], len(x[0])))

        for idx, (source, translation, count) in enumerate(sorted_glossary):
            data_row = idx + 1
            alt = idx % 2 == 1
            ws.write(data_row, 0, idx + 1,      fmt_num_alt    if alt else fmt_num)
            ws.write(data_row, 1, source,        fmt_source_alt if alt else fmt_source)
            ws.write(data_row, 2, translation,   fmt_trans_alt  if alt else fmt_trans)
            ws.write(data_row, 3, count,         fmt_count_alt  if alt else fmt_count)

        ws.write(len(sorted_glossary) + 2, 0,
                 f"Total: {len(sorted_glossary)} glossary terms", fmt_summary)

        wb.close()
        wb = None
        return True

    except Exception as e:
        logger.error("Failed to write Glossary Excel %s: %s", output_path, e)
        return False

    finally:
        if wb is not None:
            try:
                wb.close()
            except Exception:
                pass
