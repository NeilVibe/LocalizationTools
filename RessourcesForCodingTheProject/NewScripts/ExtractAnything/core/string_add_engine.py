"""String Add engine – add missing LocStr nodes from source to target (file-to-file)."""

from __future__ import annotations

import logging
from pathlib import Path

from lxml import etree

import config
from . import xml_parser
from .text_utils import normalize_text, normalize_nospace

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------

def _make_keys(sid: str, so: str) -> tuple[tuple, tuple]:
    """Return (exact_key, nospace_key) for a StringID + StrOrigin pair."""
    nt = normalize_text(so)
    return (sid.lower(), nt), (sid.lower(), normalize_nospace(nt))


def _collect_keys_from_root(root) -> tuple[set[tuple], set[tuple]]:
    """Collect all (StringID, StrOrigin) keys from a parsed root element."""
    keys: set[tuple] = set()
    nospace_keys: set[tuple] = set()

    for elem in xml_parser.iter_locstr(root):
        _, sid = xml_parser.get_attr(elem, config.STRINGID_ATTRS)
        if not sid:
            continue
        _, so = xml_parser.get_attr(elem, config.STRORIGIN_ATTRS)
        so = so or ""
        k, nk = _make_keys(sid, so)
        keys.add(k)
        nospace_keys.add(nk)

    return keys, nospace_keys


def _collect_source_entries(source_path: Path) -> list[dict]:
    """Parse source XML and return entries with raw_attribs preserved."""
    raw = xml_parser.read_xml_raw(source_path)
    if raw is None:
        return []

    root = xml_parser.parse_root_from_string(raw)
    entries: list[dict] = []

    for elem in xml_parser.iter_locstr(root):
        _, sid = xml_parser.get_attr(elem, config.STRINGID_ATTRS)
        if not sid:
            continue
        _, so = xml_parser.get_attr(elem, config.STRORIGIN_ATTRS)
        so = so or ""
        raw_attribs = dict(elem.attrib)
        k, nk = _make_keys(sid, so)
        entries.append({
            "string_id": sid,
            "key": k,
            "nospace_key": nk,
            "raw_attribs": raw_attribs,
        })

    return entries


# ---------------------------------------------------------------------------
# Core: file-to-file add
# ---------------------------------------------------------------------------

def add_missing(
    source_path: Path,
    target_path: Path,
    *,
    log_fn=None,
) -> tuple[int, list[dict]]:
    """Diff source vs target and add missing entries to target in-place.

    Single parse path: target is parsed once, keys collected from that
    same tree, missing entries appended, then written back.

    Returns ``(total_added, report)``.
    """
    if log_fn:
        log_fn(f"Source: {source_path.name}")
        log_fn(f"Target: {target_path.name}")

    source_entries = _collect_source_entries(source_path)
    if not source_entries:
        if log_fn:
            log_fn("No LocStr entries found in source.", "warning")
        return 0, []

    if log_fn:
        log_fn(f"Source: {len(source_entries):,} LocStr entries")

    # Single parse of target
    try:
        tree, root = xml_parser.parse_tree_from_file(target_path)
    except Exception as exc:
        if log_fn:
            log_fn(f"Cannot parse target: {exc}", "error")
        return 0, []

    target_keys, target_nospace = _collect_keys_from_root(root)
    if log_fn:
        log_fn(f"Target: {len(target_keys):,} existing entries")

    # Diff with source dedup (both exact and nospace keys)
    missing: list[dict] = []
    seen: set[tuple] = set()
    seen_nospace: set[tuple] = set()
    for entry in source_entries:
        if entry["key"] in target_keys or entry["nospace_key"] in target_nospace:
            continue
        if entry["key"] in seen or entry["nospace_key"] in seen_nospace:
            continue
        seen.add(entry["key"])
        seen_nospace.add(entry["nospace_key"])
        missing.append(entry)

    if not missing:
        if log_fn:
            log_fn("No missing entries — target already has everything.", "success")
        return 0, []

    if log_fn:
        log_fn(f"Found {len(missing):,} entries to add")

    # Detect indent from existing elements (tail = "\n    " → indent = "    ")
    existing = list(root)
    if existing:
        sample_tail = existing[0].tail or ""
        # tail is typically "\n" + indent (e.g. "\n    ")
        indent = sample_tail.replace("\n", "") if "\n" in sample_tail else "    "
    else:
        indent = "    "
    child_tail = "\n" + indent   # between LocStr elements
    closing_tail = "\n"          # before closing root tag

    # Fix the last existing element's tail so new elements stack below it
    if existing:
        existing[-1].tail = child_tail

    # Append new LocStr elements with proper stacking
    report: list[dict] = []
    for i, entry in enumerate(missing):
        raw = entry["raw_attribs"]
        elem = etree.SubElement(root, "LocStr", **{k: str(v) for k, v in raw.items()})
        is_last = (i == len(missing) - 1)
        elem.tail = closing_tail if is_last else child_tail
        report.append({"string_id": entry["string_id"], "status": "ADDED"})

    xml_parser.write_xml_tree(tree, target_path)

    return len(report), report


def write_add_report(report: list[dict], output_dir: Path) -> Path:
    """Write a plain-text add report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"add_report_{ts}.txt"

    lines = [f"String Add Report – {ts}", "=" * 60, ""]
    for r in report:
        lines.append(f"  {r['string_id']:40s} {r['status']}")
    lines.append("")
    lines.append(f"Total: {len(report)} entries processed")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report written → %s", report_path)
    return report_path
