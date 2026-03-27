"""
Unify Translations Module

Reads a reference Excel (TMX Clean output) and a LineCheck Excel (QuickCheck output),
matches by StrOrigin, and produces a merge-ready Excel with unified corrections.

Reference: StrOrigin | Correction | StringID | ... | ChangeDate
LineCheck:  Source (KR) | [Category] | Translation 1 | SID 1 | Translation 2 | SID 2 | ...
Output:     StrOrigin | Correction | StringID | Category
"""
from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


def _normalize(text: str) -> str:
    """Normalize text for matching — collapse whitespace, strip."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text).strip())


@dataclass
class UnifyResult:
    """Single row in the unified output."""
    str_origin: str
    correction: str
    string_id: str
    category: str


def read_reference_excel(
    path: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Tuple[str, str]]:
    """
    Read reference Excel (TMX Clean output).

    Returns: {normalized_StrOrigin: (Correction, ChangeDate)}
    If duplicate StrOrigin, keeps the one with latest ChangeDate.
    """
    if openpyxl is None:
        raise ImportError("openpyxl is required")

    if progress_callback:
        progress_callback("Reading reference file...")

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()

    if not rows:
        raise ValueError(f"Reference file is empty: {os.path.basename(path)}")

    # Detect columns by header
    header = [str(c).strip().lower() if c else "" for c in rows[0]]
    str_origin_idx = None
    correction_idx = None
    changedate_idx = None

    for i, h in enumerate(header):
        if h == "strorigin":
            str_origin_idx = i
        elif h == "correction":
            correction_idx = i
        elif h == "changedate":
            changedate_idx = i

    # Validation
    missing = []
    if str_origin_idx is None:
        missing.append("StrOrigin")
    if correction_idx is None:
        missing.append("Correction")
    if missing:
        raise ValueError(f"Reference file missing headers: {', '.join(missing)}")

    # Build lookup
    lookup: Dict[str, Tuple[str, str]] = {}
    for row in rows[1:]:
        if not row or len(row) <= max(str_origin_idx, correction_idx):
            continue

        str_origin_val = str(row[str_origin_idx] or "").strip()
        correction_val = str(row[correction_idx] or "").strip()
        changedate_val = ""
        if changedate_idx is not None and len(row) > changedate_idx:
            changedate_val = str(row[changedate_idx] or "").strip()

        if not str_origin_val or not correction_val:
            continue

        key = _normalize(str_origin_val)

        if key in lookup:
            # Keep latest ChangeDate
            existing_date = lookup[key][1]
            if changedate_val > existing_date:
                lookup[key] = (correction_val, changedate_val)
        else:
            lookup[key] = (correction_val, changedate_val)

    if progress_callback:
        progress_callback(f"Reference: {len(lookup)} unique StrOrigin entries loaded")

    return lookup


def read_linecheck_excel(
    path: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[dict]:
    """
    Read LineCheck Excel output.

    Returns list of dicts:
        {'source': str, 'category': str, 'translations': [(translation, string_id), ...]}
    """
    if openpyxl is None:
        raise ImportError("openpyxl is required")

    if progress_callback:
        progress_callback("Reading LineCheck file...")

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()

    if not rows:
        raise ValueError(f"LineCheck file is empty: {os.path.basename(path)}")

    # Parse header to find columns dynamically
    header = [str(c).strip() if c else "" for c in rows[0]]
    header_lower = [h.lower() for h in header]

    # Find Source column
    source_idx = None
    for i, h in enumerate(header_lower):
        if h.startswith("source"):
            source_idx = i
            break

    if source_idx is None:
        raise ValueError("LineCheck file missing 'Source (KR)' header")

    # Find Category column (optional)
    category_idx = None
    for i, h in enumerate(header_lower):
        if h == "category":
            category_idx = i
            break

    # Find Translation N / StringID N pairs
    trans_pairs: List[Tuple[int, int]] = []  # [(trans_col, sid_col), ...]
    for i, h in enumerate(header):
        if h.startswith("Translation "):
            # Next column should be StringID N
            if i + 1 < len(header) and header[i + 1].startswith("StringID "):
                trans_pairs.append((i, i + 1))

    if not trans_pairs:
        raise ValueError("LineCheck file missing Translation/StringID column pairs")

    # Parse data rows
    results = []
    for row in rows[1:]:
        if not row:
            continue

        source = str(row[source_idx] or "").strip() if len(row) > source_idx else ""
        if not source:
            continue

        # Skip summary rows
        if source.lower().startswith("total:"):
            continue

        category = ""
        if category_idx is not None and len(row) > category_idx:
            category = str(row[category_idx] or "").strip()

        translations = []
        for trans_col, sid_col in trans_pairs:
            trans_val = str(row[trans_col] or "").strip() if len(row) > trans_col else ""
            sid_val = str(row[sid_col] or "").strip() if len(row) > sid_col else ""
            if trans_val and sid_val:
                translations.append((trans_val, sid_val))

        if translations:
            results.append({
                'source': source,
                'category': category,
                'translations': translations,
            })

    if progress_callback:
        progress_callback(f"LineCheck: {len(results)} inconsistency groups loaded")

    return results


def unify(
    reference: Dict[str, Tuple[str, str]],
    linecheck_groups: List[dict],
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[List[UnifyResult], int, int]:
    """
    Match LineCheck groups against reference to produce unified corrections.

    Returns: (results, matched_count, unmatched_count)
    """
    results: List[UnifyResult] = []
    matched = 0
    unmatched = 0

    for group in linecheck_groups:
        source = group['source']
        category = group['category']
        translations = group['translations']
        key = _normalize(source)

        if key not in reference:
            unmatched += 1
            if progress_callback:
                progress_callback(f"  NO REFERENCE: {source[:50]}...")
            continue

        correction, _ = reference[key]
        matched += 1

        # Output ALL StringIDs in this group with the correct translation
        for trans_val, sid_val in translations:
            results.append(UnifyResult(
                str_origin=source,
                correction=correction,
                string_id=sid_val,
                category=category,
            ))

    if progress_callback:
        progress_callback(f"Matched: {matched}, No reference: {unmatched}, Output rows: {len(results)}")

    return results, matched, unmatched


def write_unified_excel(
    results: List[UnifyResult],
    output_path: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> bool:
    """Write unified results to merge-ready Excel."""
    if xlsxwriter is None:
        raise ImportError("xlsxwriter is required")

    if progress_callback:
        progress_callback(f"Writing {len(results)} rows to {os.path.basename(output_path)}...")

    try:
        wb = xlsxwriter.Workbook(output_path)
        ws = wb.add_worksheet('Unified')

        hdr_fmt = wb.add_format({
            'bold': True, 'bg_color': '#4472C4', 'font_color': 'white',
            'border': 1, 'valign': 'vcenter', 'text_wrap': True,
        })
        cell_fmt = wb.add_format({
            'border': 1, 'valign': 'vcenter', 'text_wrap': True,
        })
        sid_fmt = wb.add_format({
            'border': 1, 'valign': 'vcenter', 'num_format': '@',
        })

        headers = ['StrOrigin', 'Correction', 'StringID', 'Category']
        widths = [50, 50, 22, 15]

        for col, h in enumerate(headers):
            ws.write(0, col, h, hdr_fmt)
            ws.set_column(col, col, widths[col])

        for idx, r in enumerate(results, 1):
            ws.write(idx, 0, r.str_origin, cell_fmt)
            ws.write(idx, 1, r.correction, cell_fmt)
            ws.write_string(idx, 2, str(r.string_id), sid_fmt)
            ws.write(idx, 3, r.category, cell_fmt)

        data_rows = len(results)
        if data_rows > 0:
            ws.autofilter(0, 0, data_rows, len(headers) - 1)
            ws.freeze_panes(1, 0)

        wb.close()

        if progress_callback:
            progress_callback(f"Saved: {os.path.basename(output_path)} ({data_rows} rows)")

        return True

    except Exception as e:
        logger.error("Failed to write unified Excel %s: %s", output_path, e)
        if progress_callback:
            progress_callback(f"ERROR writing output: {e}")
        return False


def run_unify(
    reference_path: str,
    linecheck_path: str,
    output_path: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Optional[str]:
    """
    Full pipeline: read reference + linecheck, match, write output.

    Returns output path on success, None on failure.
    """
    if output_path is None:
        base = os.path.splitext(linecheck_path)[0]
        output_path = f"{base}_Unified.xlsx"

    try:
        reference = read_reference_excel(reference_path, progress_callback)
        linecheck_groups = read_linecheck_excel(linecheck_path, progress_callback)
        results, matched, unmatched = unify(reference, linecheck_groups, progress_callback)

        if not results:
            if progress_callback:
                progress_callback("No matches found — nothing to output.")
            return None

        ok = write_unified_excel(results, output_path, progress_callback)
        if ok:
            return output_path
        return None

    except Exception as e:
        logger.exception("Unify pipeline failed")
        if progress_callback:
            progress_callback(f"ERROR: {e}")
        return None
