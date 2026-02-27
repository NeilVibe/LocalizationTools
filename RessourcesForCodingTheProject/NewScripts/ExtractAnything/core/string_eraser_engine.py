"""String Eraser engine – remove LocStr nodes from XML by StringID+StrOrigin match."""

import logging
import shutil
from pathlib import Path

from .. import config
from . import xml_parser
from .text_utils import normalize_text, normalize_nospace

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source key loading
# ---------------------------------------------------------------------------

def load_source_keys_from_xml(xml_path: Path) -> tuple[set[tuple], set[tuple]]:
    """Load (StringID, StrOrigin) keys from a single XML file."""
    keys: set[tuple] = set()
    nospace_keys: set[tuple] = set()

    raw = xml_parser.read_xml_raw(xml_path)
    if raw is None:
        return keys, nospace_keys

    root = xml_parser.parse_root_from_string(raw)
    for elem in xml_parser.iter_locstr(root):
        _, sid = xml_parser.get_attr(elem, config.STRINGID_ATTRS)
        if not sid:
            continue
        _, so = xml_parser.get_attr(elem, config.STRORIGIN_ATTRS)
        so = so or ""

        nt = normalize_text(so)
        keys.add((sid.lower(), nt))
        nospace_keys.add((sid.lower(), normalize_nospace(nt)))

    return keys, nospace_keys


def load_source_keys(source_folder: Path) -> tuple[set[tuple], set[tuple]]:
    """Recursively load erase keys from all XML/Excel in *source_folder*."""
    from .excel_reader import read_erase_keys_from_excel

    keys: set[tuple] = set()
    nospace_keys: set[tuple] = set()

    for fpath in sorted(source_folder.rglob("*")):
        if not fpath.is_file():
            continue
        if fpath.name.startswith("~$"):
            continue
        suffix = fpath.suffix.lower()

        if suffix == ".xml":
            k, nk = load_source_keys_from_xml(fpath)
            keys.update(k)
            nospace_keys.update(nk)
        elif suffix in (".xlsx", ".xls"):
            k, nk = read_erase_keys_from_excel(fpath)
            keys.update(k)
            nospace_keys.update(nk)

    logger.info("Loaded %d erase keys (%d nospace variants)", len(keys), len(nospace_keys))
    return keys, nospace_keys


# ---------------------------------------------------------------------------
# Erase logic
# ---------------------------------------------------------------------------

def erase_from_xml(
    target_path: Path,
    keys: set[tuple],
    nospace_keys: set[tuple],
    *,
    log_fn=None,
) -> list[dict]:
    """Remove matching LocStr nodes from *target_path* in-place.

    Uses 2-step cascade match: exact normalised → nospace normalised.
    Returns a report list of ``{string_id, status, old_value}``.
    """
    # Parse as tree for in-place modification
    try:
        tree, root = xml_parser.parse_tree_from_file(target_path)
    except Exception as exc:
        if log_fn:
            log_fn(f"  Cannot parse {target_path.name}: {exc}", "warning")
        return []

    report: list[dict] = []
    to_remove: list = []

    for elem in xml_parser.iter_locstr(root):
        _, sid = xml_parser.get_attr(elem, config.STRINGID_ATTRS)
        if not sid:
            continue
        _, so = xml_parser.get_attr(elem, config.STRORIGIN_ATTRS)
        so = so or ""

        nt = normalize_text(so)
        key = (sid.lower(), nt)
        key_nospace = (sid.lower(), normalize_nospace(nt))

        if key not in keys and key_nospace not in nospace_keys:
            continue

        # Matched — collect for removal
        str_name, str_val = xml_parser.get_attr(elem, config.STR_ATTRS)

        if str_val is None or str_val.strip() == "":
            report.append({"string_id": sid, "status": "ALREADY_EMPTY", "old_value": ""})
            continue

        if xml_parser.USING_LXML:
            to_remove.append(elem)
            report.append({"string_id": sid, "status": "ERASED", "old_value": str_val[:60]})
        elif str_name:
            elem.set(str_name, "")
            report.append({"string_id": sid, "status": "ERASED", "old_value": str_val[:60]})
        else:
            report.append({"string_id": sid, "status": "NO_STR_ATTR", "old_value": ""})

    # Remove elements (lxml only — must be done after iteration)
    for elem in to_remove:
        parent = elem.getparent()
        if parent is not None:
            parent.remove(elem)

    if not report:
        return report

    # Backup before destructive write — abort if backup fails
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


def erase_folder(
    source_folder: Path,
    target_folder: Path,
    *,
    log_fn=None,
    progress_fn=None,
) -> tuple[int, list[dict]]:
    """Erase matching entries from all XML in *target_folder*.

    Returns ``(total_erased, full_report)``.
    """
    if log_fn:
        log_fn("Loading erase keys...", "header")
    keys, nospace_keys = load_source_keys(source_folder)

    if not keys:
        if log_fn:
            log_fn("No erase keys found.", "warning")
        return 0, []

    if log_fn:
        log_fn(f"Loaded {len(keys)} erase keys. Scanning target folder...")

    xml_files = sorted(target_folder.rglob("*.xml"))
    total = len(xml_files)
    if not xml_files:
        if log_fn:
            log_fn("No XML files in target folder.", "warning")
        return 0, []

    full_report: list[dict] = []
    total_erased = 0

    for i, xml_path in enumerate(xml_files, 1):
        if progress_fn:
            progress_fn(i * 100 // total)

        file_report = erase_from_xml(xml_path, keys, nospace_keys, log_fn=log_fn)
        if file_report:
            erased = sum(1 for r in file_report if r["status"] == "ERASED")
            total_erased += erased
            full_report.extend(file_report)
            if log_fn:
                log_fn(f"  {xml_path.name}: {erased} erased")

    return total_erased, full_report


def write_erase_report(report: list[dict], output_dir: Path) -> Path:
    """Write a plain-text erase report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"erase_report_{ts}.txt"

    lines = [f"Erase Report – {ts}", "=" * 60, ""]
    for r in report:
        lines.append(f"  {r['string_id']:40s} {r['status']:15s} {r['old_value']}")
    lines.append("")
    lines.append(f"Total: {len(report)} entries processed")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report written → %s", report_path)
    return report_path
