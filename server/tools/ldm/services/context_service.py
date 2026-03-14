"""
Context Service -- Entity context resolution combining glossary detection + mapdata lookups.

Combines GlossaryService entity detection with MapDataService media lookups to
provide rich entity context (character metadata, location images, audio samples)
for any translation string.

Phase 5.1: Contextual Intelligence & QA Engine (Plan 03)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from loguru import logger

from server.tools.ldm.services.glossary_service import (
    get_glossary_service,
    DetectedEntity,
    EntityInfo,
)
from server.tools.ldm.services.mapdata_service import (
    get_mapdata_service,
    ImageContext,
    AudioContext,
)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class CharacterContext:
    """Rich context for a character entity."""
    name: str
    entity_type: str
    strkey: str
    knowledge_key: str
    source_file: str
    image: Optional[ImageContext] = None
    audio: Optional[AudioContext] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "strkey": self.strkey,
            "knowledge_key": self.knowledge_key,
            "source_file": self.source_file,
            "image": self.image.to_dict() if self.image else None,
            "audio": self.audio.to_dict() if self.audio else None,
            "metadata": self.metadata,
        }


@dataclass
class LocationContext:
    """Rich context for a location/region entity."""
    name: str
    entity_type: str
    strkey: str
    knowledge_key: str
    source_file: str
    image: Optional[ImageContext] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "strkey": self.strkey,
            "knowledge_key": self.knowledge_key,
            "source_file": self.source_file,
            "image": self.image.to_dict() if self.image else None,
            "metadata": self.metadata,
        }


@dataclass
class EntityContext:
    """Combined entity context for a string."""
    entities: List[Union[CharacterContext, LocationContext]] = field(default_factory=list)
    detected_in_text: List[DetectedEntity] = field(default_factory=list)
    string_id_context: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "detected_in_text": [
                {"term": d.term, "start": d.start, "end": d.end, "type": d.entity.type}
                for d in self.detected_in_text
            ],
            "string_id_context": self.string_id_context,
        }


# =============================================================================
# ContextService
# =============================================================================


class ContextService:
    """Service for resolving rich entity context from text and string IDs.

    Combines GlossaryService (AC entity detection) with MapDataService
    (image/audio lookups) to provide complete entity context for translators.
    """

    def resolve_context(self, text: str) -> EntityContext:
        """Resolve entity context from text using glossary detection + media lookups.

        Args:
            text: Source text to scan for entities.

        Returns:
            EntityContext with detected entities and their media context.
        """
        glossary_svc = get_glossary_service()
        detected = glossary_svc.detect_entities(text)

        entities: List[Union[CharacterContext, LocationContext]] = []
        for det in detected:
            entity_ctx = self._resolve_entity_media(det.entity)
            entities.append(entity_ctx)

        return EntityContext(
            entities=entities,
            detected_in_text=detected,
        )

    def resolve_context_for_row(self, string_id: str, source_text: str) -> EntityContext:
        """Resolve context combining StringID-direct lookups with text detection.

        Args:
            string_id: The row's StringID for direct media lookup.
            source_text: Source text for entity detection.

        Returns:
            EntityContext with both direct StringID media and detected entities.
        """
        # First: entity detection from text
        result = self.resolve_context(source_text)

        # Second: direct StringID media lookup
        mapdata_svc = get_mapdata_service()
        direct_image = mapdata_svc.get_image_context(string_id)
        direct_audio = mapdata_svc.get_audio_context(string_id)

        result.string_id_context = {
            "image": direct_image.to_dict() if direct_image else None,
            "audio": direct_audio.to_dict() if direct_audio else None,
        }

        return result

    def _resolve_entity_media(self, entity_info: EntityInfo) -> Union[CharacterContext, LocationContext]:
        """Resolve image/audio for an entity using StrKey then KnowledgeKey fallback.

        CTX-03: Indirect audio matches via same character KnowledgeKey.
        CTX-04: Indirect image matches when direct StrKey returns None.

        Args:
            entity_info: Entity metadata from glossary detection.

        Returns:
            CharacterContext or LocationContext with resolved media.
        """
        mapdata_svc = get_mapdata_service()

        # Image lookup: try StrKey first, then KnowledgeKey (CTX-04)
        image = mapdata_svc.get_image_context(entity_info.strkey) if entity_info.strkey else None
        if image is None and entity_info.knowledge_key:
            image = mapdata_svc.get_image_context(entity_info.knowledge_key)

        if entity_info.type == "character":
            # Audio lookup: try StrKey first, then KnowledgeKey (CTX-03)
            audio = mapdata_svc.get_audio_context(entity_info.strkey) if entity_info.strkey else None
            if audio is None and entity_info.knowledge_key:
                audio = mapdata_svc.get_audio_context(entity_info.knowledge_key)

            return CharacterContext(
                name=entity_info.name,
                entity_type=entity_info.type,
                strkey=entity_info.strkey,
                knowledge_key=entity_info.knowledge_key,
                source_file=entity_info.source_file,
                image=image,
                audio=audio,
            )
        else:
            # Location/region/item -- no audio
            return LocationContext(
                name=entity_info.name,
                entity_type=entity_info.type,
                strkey=entity_info.strkey,
                knowledge_key=entity_info.knowledge_key,
                source_file=entity_info.source_file,
                image=image,
            )

    def get_status(self) -> dict:
        """Return service health info combining glossary and mapdata status."""
        glossary_svc = get_glossary_service()
        mapdata_svc = get_mapdata_service()

        return {
            "glossary": glossary_svc.get_status(),
            "mapdata": mapdata_svc.get_status(),
        }


# =============================================================================
# Singleton
# =============================================================================

_service_instance: Optional[ContextService] = None


def get_context_service() -> ContextService:
    """Get or create the singleton ContextService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ContextService()
    return _service_instance
