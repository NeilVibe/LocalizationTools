"""XML output – LocStr builder with <br/> preservation."""

import logging
import re
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_SENTINEL = "\x00BR\x00"


def xml_escape_attr(value: str) -> str:
    """Escape an attribute value for XML, preserving ``<br/>`` tags."""
    value = _BR_RE.sub(_SENTINEL, value)
    value = (
        value
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    value = value.replace(_SENTINEL, "<br/>")
    return value


def build_locstr_line(entry: dict, *, attr_order: Sequence[str] | None = None) -> str:
    """Build a single ``<LocStr ... />`` line from an entry dict.

    *entry* must have ``string_id``, ``str_origin``, ``str_value``.
    Additional attributes come from ``raw_attribs`` if present.
    """
    sid = entry.get("string_id", "")
    so = entry.get("str_origin", "")
    sv = entry.get("str_value", "")
    raw = entry.get("raw_attribs", {})

    # Build ordered attributes: StringID, StrOrigin, Str, then remaining
    parts = [f'StringID="{xml_escape_attr(sid)}"']
    if so:
        parts.append(f'StrOrigin="{xml_escape_attr(so)}"')
    if sv:
        parts.append(f'Str="{xml_escape_attr(sv)}"')

    # Remaining raw attribs (skip already-written ones)
    skip = {"StringID", "StringId", "stringid", "STRINGID", "Stringid", "stringId",
            "StrOrigin", "Strorigin", "strorigin", "STRORIGIN",
            "Str", "str", "STR"}
    if attr_order:
        for k in attr_order:
            if k in raw and k not in skip:
                parts.append(f'{k}="{xml_escape_attr(str(raw[k]))}"')
                skip.add(k)
    for k, v in raw.items():
        if k not in skip:
            parts.append(f'{k}="{xml_escape_attr(str(v))}"')

    return "  <LocStr " + " ".join(parts) + " />"


def write_locstr_xml(
    out_path: Path,
    entries: Sequence[dict],
    *,
    sort_key=None,
    dedup_by_sid: bool = False,
    xml_declaration: bool = True,
) -> int:
    """Write a list of entry dicts to an XML file.

    Returns the number of LocStr elements written.
    """
    if sort_key:
        entries = sorted(entries, key=sort_key)

    seen: set[str] = set()
    lines: list[str] = []

    if xml_declaration:
        lines.append('<?xml version="1.0" encoding="utf-8"?>')
    lines.append("<root>")

    count = 0
    for entry in entries:
        if dedup_by_sid:
            key = entry.get("string_id", "").lower()
            if key in seen:
                continue
            seen.add(key)
        lines.append(build_locstr_line(entry))
        count += 1

    lines.append("</root>")
    lines.append("")  # trailing newline

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote %d LocStr → %s", count, out_path.name)
    return count
