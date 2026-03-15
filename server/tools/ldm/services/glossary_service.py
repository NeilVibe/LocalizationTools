"""
Glossary Service -- Entity extraction from game data + Aho-Corasick automaton.

Extracts character, item, location, and skill names from staticinfo XML files.
Builds an Aho-Corasick automaton for O(n) real-time entity detection in text.
Maps detected entities to their datapoint info (StrKey, KnowledgeKey, source file).

Phase 5.1: Contextual Intelligence & QA Engine (Plan 01)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ahocorasick
from loguru import logger

from server.utils.qa_helpers import is_isolated, is_sentence, has_punctuation


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class EntityInfo:
    """Metadata for a game entity (character, item, region, skill)."""
    type: str
    name: str
    strkey: str
    knowledge_key: str
    source_file: str
    datapoint_paths: Dict[str, str] = field(default_factory=dict)


@dataclass
class DetectedEntity:
    """An entity detected in text via AC automaton scan."""
    term: str
    start: int
    end: int
    entity: EntityInfo


@dataclass
class GlossaryEntry:
    """A glossary term with source/target pair and entity info."""
    source: str
    target: str
    entity_info: Optional[EntityInfo] = None


# =============================================================================
# GlossaryService
# =============================================================================


class GlossaryService:
    """Service for glossary extraction and Aho-Corasick entity detection.

    Singleton pattern following MapDataService. Extracts entity names from
    game data XML files, builds an AC automaton for O(n) multi-pattern
    matching, and maps detected entities to their datapoint metadata.
    """

    def __init__(self):
        self._automaton: Optional[ahocorasick.Automaton] = None
        self._entity_index: Dict[str, EntityInfo] = {}
        self._loaded: bool = False

    # -------------------------------------------------------------------------
    # AC Automaton Building
    # -------------------------------------------------------------------------

    def build_from_entity_names(self, entities: List[Tuple[str, EntityInfo]]) -> None:
        """Build AC automaton from list of (name, EntityInfo) tuples.

        Args:
            entities: List of (entity_name, EntityInfo) pairs.
        """
        self._automaton = ahocorasick.Automaton()
        self._entity_index = {}

        for idx, (name, info) in enumerate(entities):
            if not name:
                continue
            self._automaton.add_word(name, (idx, name))
            self._entity_index[name] = info

        if len(self._entity_index) > 0:
            self._automaton.make_automaton()
        self._loaded = True

        logger.info(
            f"[GLOSSARY] Built AC automaton with {len(self._entity_index)} entities"
        )

    # -------------------------------------------------------------------------
    # Entity Detection
    # -------------------------------------------------------------------------

    def detect_entities(self, text: str) -> List[DetectedEntity]:
        """Scan text for entities using AC automaton with word boundary check.

        Uses is_isolated() from qa_helpers to prevent false matches in
        compound words (especially Korean).

        Args:
            text: Text to scan for entity names.

        Returns:
            List of DetectedEntity with term, position, and entity info.
        """
        if not self._loaded or self._automaton is None:
            return []

        if len(self._entity_index) == 0:
            return []

        results = []
        for end_index, (pattern_id, original_term) in self._automaton.iter(text):
            start_index = end_index - len(original_term) + 1
            end_pos = end_index + 1

            # Word boundary check -- critical for Korean compound words
            if is_isolated(text, start_index, end_pos):
                entity_info = self._entity_index.get(original_term)
                if entity_info:
                    results.append(DetectedEntity(
                        term=original_term,
                        start=start_index,
                        end=end_pos,
                        entity=entity_info,
                    ))

        return results

    # -------------------------------------------------------------------------
    # XML Extraction Methods
    # -------------------------------------------------------------------------

    def extract_character_glossary(self, folder: Path) -> List[Tuple[str, EntityInfo]]:
        """Extract character names from characterinfo XML files.

        Parses characterinfo_*.staticinfo.xml or characterinfo_*.xml files
        and extracts CharacterName, StrKey, KnowledgeKey attributes.

        Args:
            folder: Path to folder containing characterinfo XML files.

        Returns:
            List of (character_name, EntityInfo) tuples.
        """
        entries = []
        patterns = ["characterinfo_*.staticinfo.xml", "characterinfo_*.xml"]
        files = set()
        for pattern in patterns:
            files.update(folder.rglob(pattern))

        for path in sorted(files):
            root = self._parse_xml(path)
            if root is None:
                continue
            for el in root.iter("CharacterInfo"):
                name = el.get("CharacterName") or ""
                strkey = el.get("StrKey") or ""
                knowledge_key = el.get("KnowledgeKey") or ""
                if name:
                    entries.append((name, EntityInfo(
                        type="character",
                        name=name,
                        strkey=strkey,
                        knowledge_key=knowledge_key,
                        source_file=path.name,
                    )))

        logger.debug(f"[GLOSSARY] Extracted {len(entries)} character entries from {folder}")
        return entries

    def extract_item_glossary(self, folder: Path) -> List[Tuple[str, EntityInfo]]:
        """Extract item names from iteminfo XML files.

        Args:
            folder: Path to folder containing iteminfo XML files.

        Returns:
            List of (item_name, EntityInfo) tuples.
        """
        entries = []
        patterns = ["iteminfo_*.staticinfo.xml", "iteminfo_*.xml"]
        files = set()
        for pattern in patterns:
            files.update(folder.rglob(pattern))

        for path in sorted(files):
            root = self._parse_xml(path)
            if root is None:
                continue
            for el in root.iter("ItemInfo"):
                name = el.get("ItemName") or ""
                strkey = el.get("StrKey") or ""
                if name:
                    entries.append((name, EntityInfo(
                        type="item",
                        name=name,
                        strkey=strkey,
                        knowledge_key="",
                        source_file=path.name,
                    )))

        logger.debug(f"[GLOSSARY] Extracted {len(entries)} item entries from {folder}")
        return entries

    def extract_region_glossary(self, folder: Path) -> List[Tuple[str, EntityInfo]]:
        """Extract region/location names from factioninfo XML files.

        Args:
            folder: Path to folder containing factioninfo/regioninfo XML files.

        Returns:
            List of (region_name, EntityInfo) tuples.
        """
        entries = []
        patterns = [
            "factioninfo_*.staticinfo.xml",
            "factioninfo_*.xml",
            "regioninfo_*.xml",
        ]
        files = set()
        for pattern in patterns:
            files.update(folder.rglob(pattern))

        for path in sorted(files):
            root = self._parse_xml(path)
            if root is None:
                continue
            for el in root.iter("FactionNodeData"):
                name = el.get("NodeName") or ""
                knowledge_key = el.get("KnowledgeKey") or ""
                if name:
                    entries.append((name, EntityInfo(
                        type="region",
                        name=name,
                        strkey="",
                        knowledge_key=knowledge_key,
                        source_file=path.name,
                    )))

        logger.debug(f"[GLOSSARY] Extracted {len(entries)} region entries from {folder}")
        return entries

    # -------------------------------------------------------------------------
    # Glossary Filter
    # -------------------------------------------------------------------------

    @staticmethod
    def glossary_filter(
        entities: List[Tuple[str, EntityInfo]],
        max_term_length: int = 25,
        filter_sentences: bool = True,
        min_occurrence: int = 2,
    ) -> List[Tuple[str, EntityInfo]]:
        """Filter glossary entries using QuickSearch proven defaults.

        Removes:
        - Terms longer than max_term_length
        - Sentences (ending with . ? !)
        - Terms with punctuation
        - Terms occurring fewer than min_occurrence times

        Args:
            entities: Raw entity list.
            max_term_length: Maximum term length.
            filter_sentences: Whether to filter sentence-like terms.
            min_occurrence: Minimum occurrence count.

        Returns:
            Filtered entity list.
        """
        # Filter empty names
        filtered = [(n, i) for n, i in entities if n]

        # Filter by length
        filtered = [(n, i) for n, i in filtered if len(n) <= max_term_length]

        # Filter sentences
        if filter_sentences:
            filtered = [(n, i) for n, i in filtered if not is_sentence(n)]

        # Filter punctuation
        filtered = [(n, i) for n, i in filtered if not has_punctuation(n)]

        # Filter by min occurrence
        if min_occurrence > 1:
            counts = Counter(n for n, _ in filtered)
            filtered = [(n, i) for n, i in filtered if counts[n] >= min_occurrence]

        return filtered

    # -------------------------------------------------------------------------
    # Initialize (Full Pipeline)
    # -------------------------------------------------------------------------

    def initialize(self, paths: dict) -> bool:
        """Initialize service from game data paths.

        Applies WSL path conversion to all folder paths, then calls all
        extract_* methods, applies glossary filter, and builds automaton.

        Args:
            paths: Dict with keys like 'character_folder', 'item_folder', etc.
                   Values can be Windows paths (auto-converted to WSL).

        Returns:
            True if initialization succeeded.
        """
        from server.tools.ldm.services.mapdata_service import convert_to_wsl_path

        all_entities: List[Tuple[str, EntityInfo]] = []

        character_folder = paths.get("character_folder")
        if character_folder:
            folder = Path(convert_to_wsl_path(character_folder))
            if folder.exists():
                all_entities.extend(self.extract_character_glossary(folder))

        item_folder = paths.get("item_folder")
        if item_folder:
            folder = Path(convert_to_wsl_path(item_folder))
            if folder.exists():
                all_entities.extend(self.extract_item_glossary(folder))

        region_folder = paths.get("region_folder") or paths.get("faction_folder")
        if region_folder:
            folder = Path(convert_to_wsl_path(region_folder))
            if folder.exists():
                all_entities.extend(self.extract_region_glossary(folder))

        logger.info(f"[GLOSSARY] Raw entities: {len(all_entities)}")

        # Apply filter with QuickSearch defaults
        filtered = self.glossary_filter(
            all_entities,
            max_term_length=25,
            filter_sentences=True,
            min_occurrence=2,
        )

        logger.info(f"[GLOSSARY] Filtered entities: {len(filtered)} (from {len(all_entities)} raw)")

        self.build_from_entity_names(filtered)
        return True

    # -------------------------------------------------------------------------
    # Glossary Terms Export
    # -------------------------------------------------------------------------

    def get_glossary_terms(self) -> List[GlossaryEntry]:
        """Return current glossary entries for Term Check usage.

        Returns:
            List of GlossaryEntry with source terms and entity info.
        """
        return [
            GlossaryEntry(source=name, target="", entity_info=info)
            for name, info in self._entity_index.items()
        ]

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return service status info."""
        counts_by_type: Dict[str, int] = {}
        for info in self._entity_index.values():
            counts_by_type[info.type] = counts_by_type.get(info.type, 0) + 1

        return {
            "loaded": self._loaded,
            "entity_count": len(self._entity_index),
            "counts_by_type": counts_by_type,
            "automaton_size": len(self._entity_index),
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _parse_xml(path: Path):
        """Parse XML file via centralized XMLParsingEngine.

        Delegates to XMLParsingEngine for sanitization, encoding detection,
        and recovery mode parsing. All XML parsing goes through the centralized
        sanitizer to handle malformed game data consistently.

        Args:
            path: Path to XML file.

        Returns:
            lxml Element root, or None on failure.
        """
        from server.tools.ldm.services.xml_parsing import get_xml_parsing_engine

        try:
            return get_xml_parsing_engine().parse_file(path)
        except Exception as e:
            logger.warning(f"[GLOSSARY] Failed to parse {path}: {e}")
            return None


# =============================================================================
# Singleton
# =============================================================================

_service_instance: Optional[GlossaryService] = None


def get_glossary_service() -> GlossaryService:
    """Get or create the singleton GlossaryService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = GlossaryService()
    return _service_instance
