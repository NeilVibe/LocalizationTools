"""Unified EXPORT index – category, subfolder, and voiced SIDs in one pass."""

import logging
from pathlib import Path

import config
from . import xml_parser

logger = logging.getLogger(__name__)


class ExportIndex:
    """Cached index built from the EXPORT folder."""

    __slots__ = ("category_map", "subfolder_map", "voiced_sids", "path_map", "is_built")

    def __init__(self) -> None:
        self.category_map: dict[str, str] = {}    # sid_lower → category
        self.subfolder_map: dict[str, str] = {}   # sid_lower → subfolder
        self.voiced_sids: set[str] = set()         # sid_lower with SoundEventName
        self.path_map: dict[str, str] = {}        # sid_lower → relative file path
        self.is_built: bool = False

    def invalidate(self) -> None:
        self.category_map.clear()
        self.subfolder_map.clear()
        self.voiced_sids.clear()
        self.path_map.clear()
        self.is_built = False


def build_export_index(
    export_folder: Path,
    progress_fn=None,
) -> ExportIndex:
    """Scan all ``*.loc.xml`` in *export_folder* and build the index.

    Single pass: each file yields category (from folder name), subfolder,
    and voiced SID detection.

    *progress_fn* is called with ``(current, total)`` for UI updates.
    """
    index = ExportIndex()

    if not export_folder or not export_folder.is_dir():
        logger.warning("EXPORT folder not set or missing: %s", export_folder)
        return index

    xml_files = sorted(export_folder.rglob("*.loc.xml"))
    total = len(xml_files)
    if total == 0:
        logger.warning("No .loc.xml files found in %s", export_folder)
        return index

    logger.info("Building EXPORT index from %d files …", total)

    for i, xml_path in enumerate(xml_files, 1):
        if progress_fn and i % max(1, total // 40) == 0:
            progress_fn(i, total)

        # Category = first directory component under export_folder
        try:
            rel = xml_path.relative_to(export_folder)
        except ValueError:
            continue
        category = rel.parts[0] if len(rel.parts) > 1 else ""
        subfolder = rel.parts[1] if len(rel.parts) > 2 else (
            rel.parts[0] if len(rel.parts) > 1 else ""
        )

        try:
            root = xml_parser.parse_root_from_file(xml_path)
        except Exception as exc:
            logger.debug("Skipping %s: %s", xml_path.name, exc)
            continue

        # Scan ALL elements (not just LocStr) for voiced detection
        for elem in root.iter():
            _, sid = xml_parser.get_attr(elem, config.STRINGID_ATTRS)
            if not sid:
                continue
            sid_lower = sid.lower()

            # Voiced detection (any element with SoundEventName + StringID)
            _, snd = xml_parser.get_attr(elem, config.SOUNDEVENT_ATTRS)
            if snd:
                index.voiced_sids.add(sid_lower)

        # Category + subfolder + path mapping (LocStr elements only)
        rel_str = str(rel).replace("\\", "/")
        for elem in xml_parser.iter_locstr(root):
            _, sid = xml_parser.get_attr(elem, config.STRINGID_ATTRS)
            if not sid:
                continue
            sid_lower = sid.lower()
            if category:
                index.category_map[sid_lower] = category
            if subfolder:
                index.subfolder_map[sid_lower] = subfolder
            index.path_map.setdefault(sid_lower, rel_str)

    if progress_fn:
        progress_fn(total, total)

    index.is_built = True
    logger.info(
        "EXPORT index: %d categories, %d subfolders, %d voiced SIDs, %d path mappings",
        len(index.category_map), len(index.subfolder_map),
        len(index.voiced_sids), len(index.path_map),
    )
    return index
