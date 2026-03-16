"""GameData Browse Service -- folder scanning and XML metadata extraction.

Phase 18: Game Dev Grid -- provides folder tree browsing and dynamic column
detection for the Game Dev Grid file explorer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger
from lxml import etree

from server.tools.ldm.schemas.gamedata import (
    ColumnHint,
    FileColumnsResponse,
    FileNode,
    FolderNode,
)


# Attributes that are editable per entity type (from research)
EDITABLE_ATTRS = {
    "ItemInfo": ["ItemName", "ItemDesc"],
    "CharacterInfo": ["CharacterName"],
    "SkillInfo": ["SkillName", "SkillDesc"],
    "GimmickGroupInfo": ["GimmickName"],
    "GimmickInfo": ["GimmickName"],
    "KnowledgeInfo": ["Name", "Desc"],
    "FactionGroup": ["GroupName"],
    "QuestInfo": ["QuestName", "QuestDesc"],
    "RegionInfo": ["RegionName", "RegionDesc"],
    "SceneObjectData": ["ObjectName", "ObjectDesc", "AliasName"],
    "SealDataInfo": ["SealName", "Desc"],
    "SkillTreeInfo": ["UIPageName"],
    "NodeWaypointInfo": [],
}


class GameDataBrowseService:
    """Scans gamedata directories and detects XML entity columns."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir).resolve()

    def _validate_path(self, path: str) -> Path:
        """Resolve path and ensure it is within the allowed base directory."""
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(self.base_dir):
            raise ValueError(
                f"Path {path} is outside allowed base directory {self.base_dir}"
            )
        return resolved

    def _count_entities(self, xml_path: Path) -> int:
        """Quick entity count via lxml -- number of direct children of root."""
        try:
            tree = etree.parse(str(xml_path))
            return len(tree.getroot())
        except Exception:
            logger.warning(f"[GameDataBrowse] Failed to parse XML: {xml_path}")
            return 0

    def scan_folder(
        self, root_path: str, max_depth: int = 4, _current_depth: int = 0
    ) -> FolderNode:
        """Recursively scan directory, return FolderNode tree.

        Only includes .xml files. Validates path is within allowed base.
        """
        resolved = self._validate_path(root_path)

        folders: list[FolderNode] = []
        files: list[FileNode] = []

        if not resolved.is_dir():
            logger.warning(f"[GameDataBrowse] Not a directory: {resolved}")
            return FolderNode(name=resolved.name, path=str(resolved))

        for entry in sorted(resolved.iterdir()):
            if entry.is_dir() and _current_depth < max_depth:
                child = self.scan_folder(
                    str(entry),
                    max_depth=max_depth,
                    _current_depth=_current_depth + 1,
                )
                folders.append(child)
            elif entry.is_file() and entry.suffix.lower() == ".xml":
                entity_count = self._count_entities(entry)
                files.append(
                    FileNode(
                        name=entry.name,
                        path=str(entry),
                        size=entry.stat().st_size,
                        entity_count=entity_count,
                    )
                )

        return FolderNode(
            name=resolved.name,
            path=str(resolved),
            folders=folders,
            files=files,
        )

    def detect_columns(self, xml_path: str) -> FileColumnsResponse:
        """Parse first entity element, return column hints.

        Marks attributes in EDITABLE_ATTRS[entity_tag] as editable=True.
        """
        resolved = self._validate_path(xml_path)

        try:
            tree = etree.parse(str(resolved))
        except etree.XMLSyntaxError as exc:
            logger.warning(f"[GameDataBrowse] Malformed XML, cannot detect columns: {resolved}: {exc}")
            return FileColumnsResponse(columns=[], editable_attrs=[])

        root = tree.getroot()

        if len(root) == 0:
            return FileColumnsResponse(columns=[], editable_attrs=[])

        first_entity = root[0]
        entity_tag = first_entity.tag
        editable_set = set(EDITABLE_ATTRS.get(entity_tag, []))

        columns: list[ColumnHint] = []
        for attr_name in first_entity.attrib:
            columns.append(
                ColumnHint(
                    key=attr_name,
                    label=attr_name,
                    editable=attr_name in editable_set,
                )
            )

        editable_attrs = [c.key for c in columns if c.editable]

        logger.debug(
            f"[GameDataBrowse] Detected {len(columns)} columns for "
            f"{entity_tag} ({len(editable_attrs)} editable)"
        )

        return FileColumnsResponse(columns=columns, editable_attrs=editable_attrs)
