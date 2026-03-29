"""GameData Edit Service -- XML attribute update with br-tag preservation.

Phase 18: Game Dev Grid -- provides save-back for inline edits in the
Game Dev Grid, preserving <br/> tags correctly through lxml round-trip.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from lxml import etree


class GameDataEditService:
    """Updates XML entity attributes and writes back to disk."""

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

    def update_entity_attribute(
        self,
        xml_path: str,
        entity_index: int,
        attr_name: str,
        new_value: str,
    ) -> bool:
        """Update a specific attribute on a specific entity in an XML file.

        CRITICAL br-tag handling: Pass user's text (containing <br/>) directly
        to element.set(). lxml auto-escapes to &lt;br/&gt; on disk. On re-read,
        lxml returns <br/> in the string. Do NOT pre-escape.

        Args:
            xml_path: Path to the XML file.
            entity_index: Zero-based index of the entity under root.
            attr_name: Name of the attribute to update.
            new_value: New value for the attribute.

        Returns:
            True on success, False on invalid index.
        """
        resolved = self._validate_path(xml_path)

        # NOTE: Intentionally NOT using sanitize_and_parse() here.
        # Edit service must preserve exact XML structure for write-back fidelity.
        # sanitize_and_parse() wraps in <ROOT> and normalizes, which would corrupt
        # the file on tree.write(). Same reason MDG's edit path uses raw parsing.
        try:
            tree = etree.parse(str(resolved))
        except etree.XMLSyntaxError:
            # Fallback: try recovery mode (like MDG)
            try:
                parser = etree.XMLParser(recover=True, huge_tree=True)
                tree = etree.parse(str(resolved), parser=parser)
            except Exception as exc:
                raise ValueError(f"Malformed XML in {resolved.name}: {exc}") from exc

        root = tree.getroot()
        entities = list(root)

        if entity_index < 0 or entity_index >= len(entities):
            logger.warning(
                f"[GameDataEdit] Invalid entity index {entity_index} "
                f"(file has {len(entities)} entities): {resolved}"
            )
            return False

        entity = entities[entity_index]
        old_value = entity.get(attr_name, "<missing>")
        entity.set(attr_name, new_value)

        try:
            tree.write(str(resolved), encoding="UTF-8", xml_declaration=True)
        except OSError as exc:
            raise ValueError(f"Failed to write XML {resolved.name}: {exc}") from exc

        logger.info(
            f"[GameDataEdit] Updated {entity.tag}[{entity_index}].{attr_name}: "
            f"'{old_value}' -> '{new_value}' in {resolved.name}"
        )

        return True
