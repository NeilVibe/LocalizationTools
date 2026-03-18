"""String Add engine – add missing LocStr nodes from source to target folder."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from lxml import etree

import config
from . import xml_parser
from .text_utils import normalize_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------

def _make_key(sid: str, so: str) -> tuple:
    """Return exact key for a StringID + StrOrigin pair (space-sensitive)."""
    return (sid.lower(), normalize_text(so))


def _collect_keys_from_root(root) -> set[tuple]:
    """Collect all (StringID, StrOrigin) keys from a parsed root element."""
    keys: set[tuple] = set()

    for elem in xml_parser.iter_locstr(root):
        _, sid = xml_parser.get_attr(elem, config.STRINGID_ATTRS)
        if not sid:
            continue
        _, so = xml_parser.get_attr(elem, config.STRORIGIN_ATTRS)
        so = so or ""
        keys.add(_make_key(sid, so))

    return keys


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
        entries.append({
            "string_id": sid,
            "key": _make_key(sid, so),
            "raw_attribs": raw_attribs,
        })

    return entries


def _dedup_source_entries(entries: list[dict]) -> list[dict]:
    """Remove source-internal duplicates (exact key only, space-sensitive)."""
    deduped: list[dict] = []
    seen: set[tuple] = set()
    for entry in entries:
        if entry["key"] in seen:
            continue
        seen.add(entry["key"])
        deduped.append(entry)
    return deduped


# ---------------------------------------------------------------------------
# Core: add missing entries to a single target file
# ---------------------------------------------------------------------------

def _add_to_target(
    source_entries: list[dict],
    target_path: Path,
    *,
    log_fn=None,
) -> tuple[int, list[dict]]:
    """Diff *source_entries* vs *target_path* and append missing entries.

    *source_entries* must already be deduped (call ``_dedup_source_entries``).
    Returns ``(count_added, report)``.
    """
    try:
        tree, root = xml_parser.parse_tree_from_file(target_path)
    except Exception as exc:
        if log_fn:
            log_fn(f"  Cannot parse {target_path.name}: {exc}", "warning")
        return 0, []

    target_keys = _collect_keys_from_root(root)

    # Skip files with no existing LocStr (likely not a languagedata file)
    if not target_keys:
        return 0, []

    # Diff — exact match only (space-sensitive)
    missing: list[dict] = []
    for entry in source_entries:
        if entry["key"] in target_keys:
            continue
        missing.append(entry)

    if not missing:
        return 0, []

    # Detect indent from existing elements
    existing = list(root)
    if existing:
        sample_tail = existing[0].tail or ""
        indent = sample_tail.replace("\n", "") if "\n" in sample_tail else "    "
    else:
        indent = "    "
    child_tail = "\n" + indent
    closing_tail = "\n"

    if existing:
        existing[-1].tail = child_tail

    # Backup before write
    bak_path = target_path.with_suffix(target_path.suffix + ".bak")
    try:
        shutil.copy2(target_path, bak_path)
    except Exception as exc:
        logger.error("CANNOT create backup of %s: %s — aborting write", target_path.name, exc)
        if log_fn:
            log_fn(f"  SKIPPED {target_path.name}: backup failed", "error")
        return 0, []

    # Append missing entries
    report: list[dict] = []
    for i, entry in enumerate(missing):
        raw = entry["raw_attribs"]
        elem = etree.SubElement(root, "LocStr", **{k: str(v) for k, v in raw.items()})
        is_last = (i == len(missing) - 1)
        elem.tail = closing_tail if is_last else child_tail
        report.append({
            "string_id": entry["string_id"],
            "status": "ADDED",
            "target_file": target_path.name,
        })

    xml_parser.write_xml_tree(tree, target_path)
    return len(report), report


# ---------------------------------------------------------------------------
# Public: file-to-folder add
# ---------------------------------------------------------------------------

def add_missing_folder(
    source_path: Path,
    target_folder: Path,
    *,
    log_fn=None,
    progress_fn=None,
) -> tuple[int, list[dict]]:
    """Add missing entries from *source_path* to all XMLs in *target_folder*.

    Source is parsed once, then each target XML is processed individually.
    Returns ``(total_added, full_report)``.
    """
    if log_fn:
        log_fn(f"Source: {source_path.name}")
        log_fn(f"Target folder: {target_folder}")

    source_entries = _collect_source_entries(source_path)
    if not source_entries:
        if log_fn:
            log_fn("No LocStr entries found in source.", "warning")
        return 0, []

    source_entries = _dedup_source_entries(source_entries)
    if log_fn:
        log_fn(f"Source: {len(source_entries):,} unique LocStr entries")

    xml_files = sorted(target_folder.rglob("*.xml"))
    # Skip source file if it lives inside target folder
    xml_files = [
        f for f in xml_files
        if not _is_same_file(source_path, f)
    ]

    total = len(xml_files)
    if not xml_files:
        if log_fn:
            log_fn("No XML files in target folder.", "warning")
        return 0, []

    if log_fn:
        log_fn(f"Found {total} target XML files")

    full_report: list[dict] = []
    total_added = 0

    for i, xml_path in enumerate(xml_files, 1):
        if progress_fn:
            progress_fn(i * 100 // total)

        added, file_report = _add_to_target(
            source_entries, xml_path, log_fn=log_fn,
        )
        if file_report:
            total_added += added
            full_report.extend(file_report)
            if log_fn:
                log_fn(f"  {xml_path.name}: {added} added", "success")
        else:
            if log_fn:
                log_fn(f"  {xml_path.name}: nothing to add")

    return total_added, full_report


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_add_report(report: list[dict], output_dir: Path) -> Path:
    """Write a plain-text add report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"add_report_{ts}.txt"

    lines = [f"String Add Report – {ts}", "=" * 60, ""]
    for r in report:
        target = r.get("target_file", "")
        lines.append(f"  {r['string_id']:40s} {r['status']:10s} {target}")
    lines.append("")
    lines.append(f"Total: {len(report)} entries processed")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report written → %s", report_path)
    return report_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_same_file(a: Path, b: Path) -> bool:
    """Check if two paths point to the same file (handles symlinks, case)."""
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False
