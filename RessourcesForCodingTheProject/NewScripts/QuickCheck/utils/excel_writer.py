"""
Excel Writer Utility

Writes QuickCheck output files (LineCheck, TermCheck, Glossary, LangCheck) as clean Excel.
Uses xlsxwriter (write-only, reliable).
"""
from __future__ import annotations

import logging
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.lang_check import LangIssue

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
        fmt_status = wb.add_format({
            "bold": True, "bg_color": "#FFE0E0", "font_color": "#CC0000",
            "border": 1, "align": "center", "valign": "vcenter",
        })
        fmt_comment = wb.add_format({
            "bg_color": COL_WHITE, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })
        fmt_summary = wb.add_format({"italic": True, "font_color": "#666666"})

        max_trans = min(max((len(r.translations) for r in results), default=2), 8)
        # Column layout: Source | Trans1 | SID1 | Trans2 | SID2 | ... | Status | Comment
        status_col  = 1 + max_trans * 2
        comment_col = 2 + max_trans * 2

        # Header
        ws.set_row(0, 20)
        ws.write(0, 0, "Source (KR)", fmt_header)
        for i in range(max_trans):
            ws.write(0, 1 + i * 2,     f"Translation {i + 1}", fmt_header)
            ws.write(0, 1 + i * 2 + 1, f"StringID {i + 1}",    fmt_header)
        ws.write(0, status_col,  "Status",  fmt_header)
        ws.write(0, comment_col, "Comment", fmt_header)

        ws.set_column(0, 0, 30)
        for i in range(max_trans):
            ws.set_column(1 + i * 2,     1 + i * 2,     35)
            ws.set_column(1 + i * 2 + 1, 1 + i * 2 + 1, 20)
        ws.set_column(status_col,  status_col,  14)
        ws.set_column(comment_col, comment_col, 40)

        row = 1
        for idx, result in enumerate(results):
            fmt_t = fmt_trans if idx % 2 == 0 else fmt_trans_alt
            fmt_s = fmt_sid   if idx % 2 == 0 else fmt_sid_alt
            ws.write(row, 0, result.source, fmt_source)
            for i, trans in enumerate(result.translations[:max_trans]):
                sid = result.string_ids[i] if i < len(result.string_ids) else ""
                ws.write(row, 1 + i * 2,     trans, fmt_t)
                ws.write(row, 1 + i * 2 + 1, sid,   fmt_s)
            ws.write(row, status_col,  "", fmt_status)
            ws.write(row, comment_col, "", fmt_comment)
            row += 1

        if row > 1:
            ws.data_validation(1, status_col, row - 1, status_col, {
                "validate": "list",
                "source":   ["ISSUE", "NO ISSUE", "FIXED"],
            })

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
    has_metadata: bool = False,
) -> bool:
    """
    Write TERM CHECK results to Excel.

    Without metadata:
      Term (KR) | Expected Translation | Source Text | Translation Found | StringID | Status | Comment
    With metadata:
      Term (KR) | Expected Translation | Source Text | Translation Found | StringID | Category | FileName | Status | Comment
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
        fmt_sid = wb.add_format({
            "bg_color": COL_WHITE, "font_color": FG_SID,
            "border": 1, "valign": "vcenter",
        })
        fmt_sid_alt = wb.add_format({
            "bg_color": COL_ALT_BG, "font_color": FG_SID,
            "border": 1, "valign": "vcenter",
        })
        fmt_summary = wb.add_format({"italic": True, "font_color": "#666666"})

        fmt_status = wb.add_format({
            "bold": True, "bg_color": "#FFE0E0", "font_color": "#CC0000",
            "border": 1, "align": "center", "valign": "vcenter",
        })
        fmt_comment = wb.add_format({
            "bg_color": COL_WHITE, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })

        if has_metadata:
            headers = ["Term (KR)", "Expected Translation", "Source Text",
                        "Translation Found", "StringID", "Category", "FileName",
                        "Status", "Comment"]
            widths = [22, 22, 45, 45, 20, 15, 20, 14, 40]
            col_status = 7
            col_comment = 8
        else:
            headers = ["Term (KR)", "Expected Translation", "Source Text",
                        "Translation Found", "StringID", "Status", "Comment"]
            widths = [22, 22, 45, 45, 20, 14, 40]
            col_status = 5
            col_comment = 6

        ws.set_row(0, 22)
        for i, h in enumerate(headers):
            ws.write(0, i, h, fmt_header)
            ws.set_column(i, i, widths[i])

        row = 1
        for result in results:
            for issue_idx, issue in enumerate(result.issues):
                fmt = fmt_issue if issue_idx % 2 == 0 else fmt_issue_alt
                fs  = fmt_sid   if issue_idx % 2 == 0 else fmt_sid_alt
                row_fmt = fmt_term_row if issue_idx == 0 else fmt
                ws.write(row, 0, result.term, row_fmt)
                ws.write(row, 1, result.reference_translation, row_fmt)
                ws.write(row, 2, issue.source_text, fmt)
                ws.write(row, 3, issue.translation_text, fmt)
                ws.write(row, 4, issue.string_id,  fs)
                if has_metadata:
                    ws.write(row, 5, issue.category,  fs)
                    ws.write(row, 6, issue.file_name, fs)
                ws.write(row, col_status,  "", fmt_status)
                ws.write(row, col_comment, "", fmt_comment)
                row += 1

        if row > 1:
            ws.data_validation(1, col_status, row - 1, col_status, {
                "validate": "list",
                "source":   ["ISSUE", "NO ISSUE", "FIXED"],
            })

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


# ---------------------------------------------------------------------------
# LangCheck Excel
# ---------------------------------------------------------------------------

def write_lang_check_excel(
    issues: List[LangIssue],
    output_path: str,
    lang_code: str = "",
) -> bool:
    """
    Write LANG CHECK results to Excel.

    Columns: StringId | StrOrigin | Str | Expected | Detected | Confidence | Method | Details | Status | Comment
    """
    _require_xlsxwriter()

    wb = None
    try:
        title = f"LangCheck {lang_code}" if lang_code else "LangCheck"
        wb = xlsxwriter.Workbook(output_path)
        ws = wb.add_worksheet(title[:31])

        fmt_header = wb.add_format({
            "bold": True, "bg_color": COL_HEADER_BG, "font_color": COL_HEADER_FG,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })
        fmt_row = wb.add_format({
            "bg_color": COL_WHITE, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })
        fmt_row_alt = wb.add_format({
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
        fmt_conf = wb.add_format({
            "bg_color": COL_WHITE, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter", "num_format": "0.00",
        })
        fmt_conf_alt = wb.add_format({
            "bg_color": COL_ALT_BG, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter", "num_format": "0.00",
        })
        fmt_method = wb.add_format({
            "bold": True, "bg_color": COL_GROUP_BG, "font_color": COL_DARK_TEXT,
            "border": 1, "align": "center", "valign": "vcenter",
        })
        fmt_status = wb.add_format({
            "bold": True, "bg_color": "#FFE0E0", "font_color": "#CC0000",
            "border": 1, "align": "center", "valign": "vcenter",
        })
        fmt_comment = wb.add_format({
            "bg_color": COL_WHITE, "font_color": COL_DARK_TEXT,
            "border": 1, "valign": "vcenter", "text_wrap": True,
        })
        fmt_summary = wb.add_format({"italic": True, "font_color": "#666666"})

        headers = ["StringId", "StrOrigin", "Str", "Expected", "Detected",
                    "Confidence", "Method", "Details", "Status", "Comment"]
        widths = [20, 50, 60, 10, 10, 10, 10, 45, 14, 40]

        ws.set_row(0, 22)
        for i, h in enumerate(headers):
            ws.write(0, i, h, fmt_header)
            ws.set_column(i, i, widths[i])

        for idx, issue in enumerate(issues):
            row = idx + 1
            alt = idx % 2 == 1
            f_r = fmt_row_alt if alt else fmt_row
            f_s = fmt_sid_alt if alt else fmt_sid
            f_c = fmt_conf_alt if alt else fmt_conf

            ws.write(row, 0, issue.string_id, f_s)
            ws.write(row, 1, issue.str_origin, f_r)
            ws.write(row, 2, issue.str_text, f_r)
            ws.write(row, 3, issue.expected_lang, f_r)
            ws.write(row, 4, issue.detected_lang, f_r)
            ws.write(row, 5, issue.confidence, f_c)
            ws.write(row, 6, issue.detection_method, fmt_method)
            ws.write(row, 7, issue.details, f_r)
            ws.write(row, 8, "", fmt_status)
            ws.write(row, 9, "", fmt_comment)

        data_rows = len(issues)
        if data_rows > 0:
            ws.data_validation(1, 8, data_rows, 8, {
                "validate": "list",
                "source": ["ISSUE", "NO ISSUE", "FIXED"],
            })
            ws.autofilter(0, 0, data_rows, len(headers) - 1)
            ws.freeze_panes(1, 0)

        script_count = sum(1 for i in issues if i.detection_method == "Script")
        stat_count = sum(1 for i in issues if i.detection_method == "Statistical")
        ws.write(data_rows + 2, 0,
                 f"Total: {data_rows} issues ({script_count} script, {stat_count} statistical)",
                 fmt_summary)

        wb.close()
        wb = None
        return True

    except Exception as e:
        logger.error("Failed to write LangCheck Excel %s: %s", output_path, e)
        return False

    finally:
        if wb is not None:
            try:
                wb.close()
            except Exception:
                pass
