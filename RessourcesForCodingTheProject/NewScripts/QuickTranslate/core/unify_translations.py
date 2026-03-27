"""
Unify Translations Module

Reads a reference Excel (TMX Clean output) and a LineCheck Excel (QuickCheck output),
matches by StrOrigin, and produces a merge-ready Excel with unified corrections.

Reference: StrOrigin | Correction | StringID | ... | ChangeDate
LineCheck:  Source (KR) | [Category] | Translation 1 | SID 1 | Translation 2 | SID 2 | ...
Output:     StrOrigin | Correction | StringID | Category
"""
from __future__ import annotations

import html
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


# Pre-compiled regex patterns for normalization (avoid re-compile per call)
_RE_UNICODE_WS = re.compile(r'[\u00A0\u1680\u180E\u2000-\u200A\u202F\u205F\u3000\uFEFF]+')
_RE_ZERO_WIDTH = re.compile(r'[\u200B-\u200F\u202A-\u202E]+')
_RE_APOSTROPHE = re.compile(r'[\u2019\u2018\u02BC\u2032\u0060\u00B4]')
_RE_WHITESPACE = re.compile(r'\s+')


def _normalize(text: str) -> str:
    """Normalize text for matching — unescape HTML, collapse whitespace, strip."""
    if not text:
        return ""
    text = html.unescape(str(text))
    text = _RE_UNICODE_WS.sub(' ', text)
    text = _RE_ZERO_WIDTH.sub('', text)
    text = _RE_APOSTROPHE.sub("'", text)
    return _RE_WHITESPACE.sub(' ', text.strip())


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

    file_size_mb = os.path.getsize(path) / (1024 * 1024)
    if progress_callback:
        progress_callback(f"[1/4] Reading reference file ({file_size_mb:.1f} MB)...")

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

    if progress_callback:
        progress_callback(f"  Headers found: {[str(c).strip() for c in rows[0] if c]}")

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
        raise ValueError(f"Reference file missing required headers: {', '.join(missing)}")

    if progress_callback:
        has_date = "YES" if changedate_idx is not None else "NO"
        progress_callback(f"  StrOrigin=col {str_origin_idx}, Correction=col {correction_idx}, ChangeDate={has_date}")

    # Build lookup
    lookup: Dict[str, Tuple[str, str]] = {}
    skipped_empty = 0
    dupes_updated = 0
    total_rows = len(rows) - 1

    for row in rows[1:]:
        if not row or len(row) <= max(str_origin_idx, correction_idx):
            skipped_empty += 1
            continue

        str_origin_val = str(row[str_origin_idx] or "").strip()
        correction_val = str(row[correction_idx] or "").strip()
        changedate_val = ""
        if changedate_idx is not None and len(row) > changedate_idx:
            changedate_val = str(row[changedate_idx] or "").strip()

        if not str_origin_val or not correction_val:
            skipped_empty += 1
            continue

        key = _normalize(str_origin_val)

        if key in lookup:
            existing_date = lookup[key][1]
            if changedate_val > existing_date:
                lookup[key] = (correction_val, changedate_val)
                dupes_updated += 1
        else:
            lookup[key] = (correction_val, changedate_val)

    if progress_callback:
        progress_callback(f"  Read {total_rows} rows → {len(lookup)} unique StrOrigin entries")
        if skipped_empty:
            progress_callback(f"  Skipped {skipped_empty} empty/incomplete rows")
        if dupes_updated:
            progress_callback(f"  {dupes_updated} duplicate StrOrigins resolved by ChangeDate")

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

    file_size_mb = os.path.getsize(path) / (1024 * 1024)
    if progress_callback:
        progress_callback(f"[2/4] Reading LineCheck file ({file_size_mb:.1f} MB)...")

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

    if progress_callback:
        progress_callback(f"  Headers found: {[h for h in header if h]}")

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
    trans_pairs: List[Tuple[int, int]] = []
    for i, h in enumerate(header):
        if h.startswith("Translation "):
            if i + 1 < len(header) and header[i + 1].startswith("StringID "):
                trans_pairs.append((i, i + 1))

    if not trans_pairs:
        raise ValueError("LineCheck file missing Translation/StringID column pairs")

    if progress_callback:
        has_cat = "YES" if category_idx is not None else "NO"
        progress_callback(f"  Source=col {source_idx}, Category={has_cat}, {len(trans_pairs)} translation pairs")

    # Parse data rows
    results = []
    total_string_ids = 0
    for row in rows[1:]:
        if not row:
            continue

        source = str(row[source_idx] or "").strip() if len(row) > source_idx else ""
        if not source:
            continue

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
            total_string_ids += len(translations)

    if progress_callback:
        progress_callback(f"  {len(results)} inconsistency groups, {total_string_ids} total StringIDs")

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
    if progress_callback:
        progress_callback("[3/4] Matching LineCheck groups against reference...")

    results: List[UnifyResult] = []
    matched = 0
    unmatched = 0
    total = len(linecheck_groups)

    for idx, group in enumerate(linecheck_groups):
        source = group['source']
        category = group['category']
        translations = group['translations']
        key = _normalize(source)

        if key not in reference:
            unmatched += 1
            continue

        correction, _ = reference[key]
        matched += 1

        for trans_val, sid_val in translations:
            results.append(UnifyResult(
                str_origin=source,
                correction=correction,
                string_id=sid_val,
                category=category,
            ))

        # Progress every 50 groups
        if progress_callback and (idx + 1) % 50 == 0:
            progress_callback(f"  Processed {idx + 1}/{total} groups...")

    if progress_callback:
        progress_callback(f"  Matched: {matched}/{total} groups")
        if unmatched:
            progress_callback(f"  No reference found: {unmatched} groups (skipped)")
        progress_callback(f"  Output: {len(results)} rows to write")

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
        progress_callback(f"[4/4] Writing {len(results)} rows to {os.path.basename(output_path)}...")

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
            # Count unique StrOrigins for summary
            unique_sources = len(set(r.str_origin for r in results))
            progress_callback(f"  Saved: {data_rows} rows ({unique_sources} unique sources)")

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

        if ok and progress_callback:
            progress_callback("-" * 40)
            progress_callback(f"DONE — Output: {os.path.basename(output_path)}")
            progress_callback(f"  Location: {output_path}")
            progress_callback(f"  Groups matched: {matched}, Skipped (no ref): {unmatched}")
            progress_callback(f"  Total correction rows: {len(results)}")

        if ok:
            return output_path
        return None

    except Exception as e:
        logger.exception("Unify pipeline failed")
        if progress_callback:
            progress_callback(f"ERROR: {e}")
        return None
