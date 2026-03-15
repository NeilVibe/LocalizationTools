"""Codex Service -- entity registry, cross-ref resolution, FAISS search.

Phase 19: Game World Codex -- scans StaticInfo XML files, builds an entity
registry with 6 entity types, resolves KnowledgeKey cross-references, and
provides semantic search via FAISS + Model2Vec.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from loguru import logger
from lxml import etree

from server.tools.ldm.schemas.codex import (
    CodexEntity,
    CodexListResponse,
    CodexSearchResponse,
    CodexSearchResult,
)
from server.tools.shared.embedding_engine import get_embedding_engine
from server.tools.shared.faiss_manager import FAISSManager


# =============================================================================
# Entity type detection mapping
# =============================================================================

# Maps XML child tag -> (entity_type, name_attr, knowledge_key_attr)
ENTITY_TAG_MAP: Dict[str, tuple] = {
    "CharacterInfo": ("character", "CharacterName", "KnowledgeKey"),
    "ItemInfo": ("item", "ItemName", "KnowledgeKey"),
    "SkillInfo": ("skill", "SkillName", "LearnKnowledgeKey"),
    "GimmickGroupInfo": ("gimmick", "GimmickName", None),
    "KnowledgeInfo": ("knowledge", "Name", None),
    "FactionNode": ("region", None, "KnowledgeKey"),
}

# Attributes to skip when building the attributes dict (they're top-level fields)
_SKIP_ATTRS = {"StrKey", "CharacterName", "ItemName", "SkillName", "GimmickName",
               "Name", "KnowledgeKey", "LearnKnowledgeKey", "AliasName"}


class CodexService:
    """Entity registry with cross-reference resolution and FAISS semantic search."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir).resolve()
        # Registry: {entity_type: {strkey: CodexEntity}}
        self._registry: Dict[str, Dict[str, CodexEntity]] = {}
        self._faiss_index = None
        self._index_keys: List[tuple] = []  # [(entity_type, strkey), ...]
        self._initialized = False

    # =========================================================================
    # Initialization
    # =========================================================================

    def initialize(self) -> None:
        """Full initialization: scan, cross-ref, index. Lazy-called on first request."""
        if self._initialized:
            return

        logger.info("[Codex] Initializing entity registry...")
        t0 = time.time()

        self._scan_entities()
        self._resolve_cross_refs()
        self._find_related_entities()

        try:
            self._build_search_index()
        except Exception as e:
            logger.warning(f"[Codex] FAISS index build failed (search unavailable): {e}")

        elapsed = time.time() - t0
        total = sum(len(v) for v in self._registry.values())
        logger.info(f"[Codex] Initialized: {total} entities in {elapsed:.2f}s")
        self._initialized = True

    # =========================================================================
    # Entity scanning
    # =========================================================================

    def _scan_entities(self) -> None:
        """Scan all StaticInfo XML files and build entity registry."""
        self._registry = {
            "character": {},
            "item": {},
            "skill": {},
            "gimmick": {},
            "knowledge": {},
            "region": {},
        }

        xml_files = list(self.base_dir.rglob("*.xml"))
        if not xml_files:
            xml_files = list(self.base_dir.rglob("*.staticinfo.xml"))

        for xml_path in xml_files:
            try:
                self._parse_xml_file(xml_path)
            except Exception as e:
                logger.warning(f"[Codex] Failed to parse {xml_path}: {e}")

        for etype, entities in self._registry.items():
            logger.debug(f"[Codex] Scanned {len(entities)} {etype} entities")

    def _parse_xml_file(self, xml_path: Path) -> None:
        """Parse a single XML file and add entities to registry."""
        tree = etree.parse(str(xml_path))
        root = tree.getroot()
        source_file = str(xml_path)

        for child in root:
            tag = child.tag

            if tag in ENTITY_TAG_MAP:
                self._extract_entity(child, tag, source_file)
            else:
                # Check nested structures (e.g., FactionGroup -> Faction -> FactionNode)
                self._scan_nested(child, source_file)

    def _scan_nested(self, element, source_file: str) -> None:
        """Recursively scan nested XML elements for entity tags."""
        for child in element:
            tag = child.tag
            if tag in ENTITY_TAG_MAP:
                self._extract_entity(child, tag, source_file)
            else:
                self._scan_nested(child, source_file)

    def _extract_entity(self, element, tag: str, source_file: str) -> None:
        """Extract a single entity from an XML element."""
        entity_type, name_attr, knowledge_key_attr = ENTITY_TAG_MAP[tag]

        strkey = element.get("StrKey")
        if not strkey:
            return

        # Get entity name
        name = ""
        if name_attr:
            name = element.get(name_attr, "")
        elif tag == "FactionNode":
            # Region entities get name from AliasName or KnowledgeKey lookup later
            name = element.get("AliasName", strkey)

        # Get knowledge key
        knowledge_key = None
        if knowledge_key_attr:
            knowledge_key = element.get(knowledge_key_attr)

        # Build attributes dict (all other XML attributes)
        attributes: Dict[str, str] = {}
        for attr_name, attr_val in element.attrib.items():
            if attr_name not in _SKIP_ATTRS:
                attributes[attr_name] = attr_val

        # Handle gimmick: extract SealData Desc from nested element
        description = None
        if tag == "KnowledgeInfo":
            description = element.get("Desc")
            # Knowledge entities: name is from Name attr, image from UITextureName
            # These are self-contained, no further cross-ref needed
        elif tag == "GimmickGroupInfo":
            # Gimmick: parse nested GimmickInfo/SealData
            for gimmick_info in element.iter("GimmickInfo"):
                # Update strkey to inner GimmickInfo if available
                inner_strkey = gimmick_info.get("StrKey")
                if inner_strkey:
                    strkey = inner_strkey
                for seal in gimmick_info.iter("SealData"):
                    description = seal.get("Desc")

        image_texture = element.get("UITextureName")

        entity = CodexEntity(
            entity_type=entity_type,
            strkey=strkey,
            name=name,
            description=description,
            knowledge_key=knowledge_key,
            image_texture=image_texture,
            audio_key=strkey,  # audio is keyed by StrKey
            source_file=source_file,
            attributes=attributes,
            related_entities=[],
        )

        self._registry[entity_type][strkey] = entity

    # =========================================================================
    # Cross-reference resolution
    # =========================================================================

    def _resolve_cross_refs(self) -> None:
        """Resolve KnowledgeKey cross-references to attach descriptions and images."""
        # Build knowledge map: StrKey -> KnowledgeInfo entity
        knowledge_map: Dict[str, CodexEntity] = {}
        for entity in self._registry.get("knowledge", {}).values():
            knowledge_map[entity.strkey] = entity

        # Resolve for all non-knowledge entity types
        for etype in ["character", "item", "skill", "region", "gimmick"]:
            for entity in self._registry.get(etype, {}).values():
                if entity.knowledge_key and entity.knowledge_key in knowledge_map:
                    know = knowledge_map[entity.knowledge_key]
                    if entity.description is None:
                        entity.description = know.description
                    if entity.image_texture is None:
                        entity.image_texture = know.image_texture

    # =========================================================================
    # Related entities
    # =========================================================================

    def _find_related_entities(self) -> None:
        """Find related entities by shared source file or knowledge key prefix."""
        # Group entities by source file
        by_file: Dict[str, List[tuple]] = {}
        for etype, entities in self._registry.items():
            for strkey, entity in entities.items():
                by_file.setdefault(entity.source_file, []).append((etype, strkey))

        # Entities in the same file are related
        for file_path, entity_keys in by_file.items():
            if len(entity_keys) <= 1:
                continue
            for etype, strkey in entity_keys:
                entity = self._registry[etype][strkey]
                related = [f"{t}/{k}" for t, k in entity_keys
                           if not (t == etype and k == strkey)]
                entity.related_entities = related[:10]  # Cap at 10

    # =========================================================================
    # FAISS search index
    # =========================================================================

    def _build_search_index(self) -> None:
        """Build FAISS index from entity names + descriptions."""
        texts = []
        keys = []

        for etype, entities in self._registry.items():
            for strkey, entity in entities.items():
                text_parts = [entity.name]
                if entity.description:
                    text_parts.append(entity.description)
                texts.append(" ".join(text_parts))
                keys.append((etype, strkey))

        if not texts:
            logger.warning("[Codex] No entities to index")
            return

        engine = get_embedding_engine()
        if not engine.is_loaded:
            engine.load()

        embeddings = engine.encode(texts, normalize=True)
        embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)

        self._faiss_index = FAISSManager.build_index(embeddings, normalize=False)
        self._index_keys = keys

        logger.info(f"[Codex] FAISS index built: {len(texts)} entities, dim={embeddings.shape[1]}")

    # =========================================================================
    # Public API
    # =========================================================================

    def search(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 20,
    ) -> CodexSearchResponse:
        """Semantic search across all entity types."""
        if not self._initialized:
            self.initialize()

        t0 = time.time()

        if self._faiss_index is None or not self._index_keys:
            return CodexSearchResponse(
                results=[], count=0, search_time_ms=0.0
            )

        engine = get_embedding_engine()
        query_vec = engine.encode(query, normalize=True)

        distances, indices = FAISSManager.search(
            self._faiss_index, query_vec, k=min(limit * 3, len(self._index_keys)),
            normalize=False,
        )

        results: List[CodexSearchResult] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._index_keys):
                continue

            etype, strkey = self._index_keys[idx]

            if entity_type and etype != entity_type:
                continue

            entity = self._registry.get(etype, {}).get(strkey)
            if entity is None:
                continue

            results.append(CodexSearchResult(
                entity=entity,
                similarity=float(dist),
                match_type="semantic",
            ))

            if len(results) >= limit:
                break

        elapsed_ms = (time.time() - t0) * 1000

        return CodexSearchResponse(
            results=results,
            count=len(results),
            search_time_ms=round(elapsed_ms, 2),
        )

    def get_entity(
        self, entity_type: str, strkey: str
    ) -> Optional[CodexEntity]:
        """Direct registry lookup for a single entity."""
        if not self._initialized:
            self.initialize()

        return self._registry.get(entity_type, {}).get(strkey)

    def list_entities(self, entity_type: str) -> CodexListResponse:
        """Return all entities of a given type."""
        if not self._initialized:
            self.initialize()

        entities = list(self._registry.get(entity_type, {}).values())
        return CodexListResponse(
            entities=entities,
            entity_type=entity_type,
            count=len(entities),
        )

    def get_entity_types(self) -> Dict[str, int]:
        """Return dict of entity_type -> count."""
        if not self._initialized:
            self.initialize()

        return {
            etype: len(entities)
            for etype, entities in self._registry.items()
            if len(entities) > 0
        }
