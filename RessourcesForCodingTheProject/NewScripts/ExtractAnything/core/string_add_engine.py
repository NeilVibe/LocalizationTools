"""String Add engine – add LocStr nodes from source to target by StringID+StrOrigin diff."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from lxml import etree

import config
from . import xml_parser
from .text_utils import normalize_text, normalize_nospace

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Key extraction (reuses string_eraser pattern)
# ---------------------------------------------------------------------------

def _make_keys(sid: str, so: str) -> tuple[tuple, tuple]:
    """Return (exact_key, nospace_key) for a StringID + StrOrigin pair."""
    nt = normalize_text(so)
    return (sid.lower(), nt), (sid.lower(), normalize_nospace(nt))


def _collect_target_keys_from_root(root) -> tuple[set[tuple], set[tuple]]:
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
# Add logic
# ---------------------------------------------------------------------------

def add_for_file_pair(
    source_path: Path,
    target_path: Path,
    *,
    log_fn=None,
) -> list[dict]:
    """Diff one source/target file pair and add missing entries to target.

    Single parse path: target is parsed once with ``parse_tree_from_file``,
    keys are collected from that same tree, and missing entries are appended
    to the same root — no dual-parse mismatch.

    Returns report entries.
    """
    source_entries = _collect_source_entries(source_path)
    if not source_entries:
        return []

    # Single parse of target — same tree used for key collection AND writing
    try:
        tree, root = xml_parser.parse_tree_from_file(target_path)
    except Exception as exc:
        if log_fn:
            log_fn(f"  Cannot parse {target_path.name}: {exc}", "warning")
        return []

    target_keys, target_nospace = _collect_target_keys_from_root(root)

    # Diff with source dedup
    missing: list[dict] = []
    seen: set[tuple] = set()
    for entry in source_entries:
        if entry["key"] in target_keys or entry["nospace_key"] in target_nospace:
            continue
        if entry["key"] in seen:
            continue
        seen.add(entry["key"])
        missing.append(entry)

    if not missing:
        return []

    # Append to the already-parsed tree
    report: list[dict] = []
    for entry in missing:
        raw = entry["raw_attribs"]
        etree.SubElement(root, "LocStr", **{k: str(v) for k, v in raw.items()})
        report.append({"string_id": entry["string_id"], "status": "ADDED"})

    # Backup before write
    bak_path = target_path.with_suffix(target_path.suffix + ".bak")
    try:
        shutil.copy2(target_path, bak_path)
        logger.info("Backup created: %s", bak_path.name)
    except Exception as exc:
        logger.error("CANNOT create backup of %s: %s — aborting write", target_path.name, exc)
        if log_fn:
            log_fn(f"  SKIPPED {target_path.name}: backup failed", "error")
        return []

    xml_parser.write_xml_tree(tree, target_path)
    return report


# ---------------------------------------------------------------------------
# Folder-level operation
# ---------------------------------------------------------------------------

def add_folder(
    source_folder: Path,
    target_folder: Path,
    *,
    log_fn=None,
    progress_fn=None,
) -> tuple[int, list[dict]]:
    """Match source/target XMLs by filename, add missing entries.

    Returns ``(total_added, full_report)``.
    """
    # Collect source XML files
    source_files = sorted(
        f for f in source_folder.rglob("*.xml")
        if f.is_file() and not f.name.startswith("~$")
    )

    if not source_files:
        if log_fn:
            log_fn("No XML files in source folder.", "warning")
        return 0, []

    if log_fn:
        log_fn(f"Found {len(source_files)} source XML file(s).")

    # Build target file index by filename (case-insensitive)
    target_files = sorted(
        f for f in target_folder.rglob("*.xml")
        if f.is_file() and not f.name.startswith("~$")
    )
    target_index: dict[str, Path] = {f.name.lower(): f for f in target_files}

    if not target_files:
        if log_fn:
            log_fn("No XML files in target folder.", "warning")
        return 0, []

    total = len(source_files)
    full_report: list[dict] = []
    total_added = 0
    skipped = 0

    for i, src_path in enumerate(source_files, 1):
        if progress_fn:
            progress_fn(i * 100 // total)

        tgt_path = target_index.get(src_path.name.lower())
        if tgt_path is None:
            skipped += 1
            if log_fn:
                log_fn(f"  {src_path.name}: no matching target file — skipped", "warning")
            continue

        file_report = add_for_file_pair(src_path, tgt_path, log_fn=log_fn)
        if file_report:
            added = sum(1 for r in file_report if r["status"] == "ADDED")
            total_added += added
            full_report.extend(file_report)
            if log_fn:
                log_fn(f"  {src_path.name}: {added} entries added")
        else:
            if log_fn:
                log_fn(f"  {src_path.name}: 0 missing (target already complete)")

    if skipped and log_fn:
        log_fn(f"{skipped} source file(s) had no matching target file.", "warning")

    return total_added, full_report


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
