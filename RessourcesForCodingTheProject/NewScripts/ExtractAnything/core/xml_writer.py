"""XML output – raw LocStr writer using lxml."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from lxml import etree

logger = logging.getLogger(__name__)


def write_locstr_xml(
    out_path: Path,
    entries: Sequence[dict],
    *,
    sort_key=None,
    dedup_by_sid: bool = False,
    xml_declaration: bool = True,
) -> int:
    """Write a list of entry dicts to an XML file.

    Uses ``raw_attribs`` from each entry – pure raw, no transformation.
    Returns the number of LocStr elements written.
    """
    if sort_key:
        entries = sorted(entries, key=sort_key)

    root = etree.Element("root")
    seen: set[str] = set()
    count = 0

    for entry in entries:
        if dedup_by_sid:
            key = entry.get("string_id", "").lower()
            if key in seen:
                continue
            seen.add(key)

        raw = entry.get("raw_attribs", {})
        if raw:
            etree.SubElement(root, "LocStr", **{k: str(v) for k, v in raw.items()})
        else:
            attrs = {}
            sid = entry.get("string_id", "")
            so = entry.get("str_origin", "")
            sv = entry.get("str_value", "")
            if sid:
                attrs["StringID"] = sid
            if so:
                attrs["StrOrigin"] = so
            if sv:
                attrs["Str"] = sv
            etree.SubElement(root, "LocStr", **attrs)
        count += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree = etree.ElementTree(root)
    tree.write(
        str(out_path),
        encoding="utf-8",
        xml_declaration=xml_declaration,
        pretty_print=True,
    )
    logger.info("Wrote %d LocStr → %s", count, out_path.name)
    return count
