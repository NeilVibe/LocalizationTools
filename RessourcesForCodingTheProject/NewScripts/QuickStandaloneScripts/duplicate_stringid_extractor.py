#!/usr/bin/env python3
"""
Duplicate StringID Extractor — QSS
===================================
File dialog → select XML → extracts only LocStr entries with duplicate
StringIDs → saves output XML automatically in the script's folder.

Follows ExtractAnything XML patterns:
  - lxml-first with stdlib fallback
  - Case-insensitive tag/attribute matching
  - 5-step XML sanitization pipeline
  - <br/> preservation
  - stdlib logging (NO loguru — PyInstaller safe)
"""
from __future__ import annotations

import logging
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from tkinter import Tk, filedialog

# ---------------------------------------------------------------------------
# Logging — stdlib only (loguru breaks PyInstaller)
# ---------------------------------------------------------------------------
logger = logging.getLogger("DuplicateStringIDExtractor")
logger.setLevel(logging.DEBUG)
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(_sh)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
VERSION = "1.0"
SCRIPT_DIR = Path(__file__).resolve().parent

LOCSTR_TAGS = ["LocStr", "locstr", "LOCSTR", "LOCStr", "Locstr"]
STRINGID_ATTRS = ("StringId", "StringID", "stringid", "STRINGID", "Stringid", "stringId")

# ---------------------------------------------------------------------------
# lxml-first import
# ---------------------------------------------------------------------------
try:
    from lxml import etree  # type: ignore[import-untyped]
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as etree  # type: ignore[assignment,no-redef]
    USING_LXML = False

# ---------------------------------------------------------------------------
# XML sanitisation (5-step, ExtractAnything pattern)
# ---------------------------------------------------------------------------
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_BAD_AMP = re.compile(r"&(?!(?:amp|lt|gt|apos|quot|#\d+|#x[0-9a-fA-F]+);)")
_SEG_RE = re.compile(r"<seg>(.*?)</seg>", re.DOTALL)
_ATTR_WITH_LT = re.compile(r'="([^"]*<[^"]*)"')


def _seg_newline_to_br(m: re.Match) -> str:
    inner = m.group(1).replace("\n", "&lt;br/&gt;")
    return f"<seg>{inner}</seg>"


def sanitize_xml(raw: str) -> str:
    txt = _CONTROL_CHARS_RE.sub("", raw)
    txt = _BAD_AMP.sub("&amp;", txt)
    txt = _SEG_RE.sub(_seg_newline_to_br, txt)

    def _fix_attr_lt(m: re.Match) -> str:
        val = m.group(1)
        safe = re.sub(r"<(?![bB][rR]\s*/?>)", "&lt;", val)
        return f'="{safe}"'

    txt = _ATTR_WITH_LT.sub(_fix_attr_lt, txt)
    return txt


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

def read_xml_raw(path: Path) -> str | None:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, OSError):
            continue
    return None


def parse_root(raw: str):
    clean = sanitize_xml(raw)
    try:
        if USING_LXML:
            parser = etree.XMLParser(
                resolve_entities=False, load_dtd=False, no_network=True,
                recover=True, huge_tree=True,
            )
            return etree.fromstring(clean.encode("utf-8"), parser)
        else:
            return etree.fromstring(clean)
    except Exception as exc:
        logger.error("XML parse failed: %s", exc)
        return None


def iter_locstr(root) -> list:
    elements: list = []
    for tag in LOCSTR_TAGS:
        elements.extend(root.iter(tag))
    return elements


def get_attr(elem, variants: tuple) -> tuple[str | None, str | None]:
    for name in variants:
        val = elem.get(name)
        if val is not None:
            return name, val
    return None, None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def extract_duplicates(xml_path: Path) -> Path | None:
    """Parse XML, find duplicate StringIDs, write output. Returns output path or None."""
    raw = read_xml_raw(xml_path)
    if raw is None:
        logger.error("Cannot read: %s", xml_path)
        return None

    root = parse_root(raw)
    if root is None:
        logger.error("Cannot parse: %s", xml_path)
        return None

    elements = iter_locstr(root)
    logger.info("Total LocStr elements: %d", len(elements))

    # Pass 1 — count StringIDs
    sid_counter: Counter = Counter()
    entry_data: list[dict] = []

    for elem in elements:
        _, sid = get_attr(elem, STRINGID_ATTRS)
        if not sid:
            continue
        sid_lower = sid.strip().lower()
        sid_counter[sid_lower] += 1
        entry_data.append({
            "sid_lower": sid_lower,
            "attribs": dict(elem.attrib),
        })

    # Pass 2 — keep only duplicates
    dup_sids = {sid for sid, count in sid_counter.items() if count >= 2}
    dup_entries = [e for e in entry_data if e["sid_lower"] in dup_sids]

    logger.info("Unique StringIDs: %d", len(sid_counter))
    logger.info("Duplicate StringIDs: %d", len(dup_sids))
    logger.info("Entries to extract: %d", len(dup_entries))

    if not dup_entries:
        logger.info("No duplicates found.")
        return None

    # Write output
    out_root = etree.Element("LanguageData")
    for i, entry in enumerate(dup_entries):
        attribs = {k: str(v) for k, v in entry["attribs"].items()}
        child = etree.SubElement(out_root, "LocStr", **attribs)
        child.text = None
        child.tail = "\n  " if i < len(dup_entries) - 1 else "\n"

    if len(out_root) > 0:
        out_root.text = "\n  "

    out_name = f"{xml_path.stem}_duplicates.xml"
    out_path = SCRIPT_DIR / out_name

    if USING_LXML:
        tree = etree.ElementTree(out_root)
        tree.write(str(out_path), encoding="utf-8", xml_declaration=True, pretty_print=True)
    else:
        tree = etree.ElementTree(out_root)
        etree.indent(tree, space="  ")
        tree.write(str(out_path), encoding="utf-8", xml_declaration=True)

    logger.info("Output: %s (%d entries)", out_path, len(dup_entries))
    return out_path


# ---------------------------------------------------------------------------
# Main — file dialog → extract → done
# ---------------------------------------------------------------------------

def main() -> None:
    root = Tk()
    root.withdraw()

    xml_path = filedialog.askopenfilename(
        title="Select XML File",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
    )
    root.destroy()

    if not xml_path:
        logger.info("No file selected.")
        return

    path = Path(xml_path)
    logger.info("Selected: %s", path.name)

    result = extract_duplicates(path)
    if result:
        logger.info("DONE — saved to: %s", result)
    else:
        logger.info("DONE — no duplicates found.")


if __name__ == "__main__":
    main()
