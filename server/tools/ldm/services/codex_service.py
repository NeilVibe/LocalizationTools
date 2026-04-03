"""Codex Service -- entity registry, cross-ref resolution, FAISS search.

Phase 19: Game World Codex -- scans StaticInfo XML files, builds an entity
registry with 6 entity types, resolves KnowledgeKey cross-references, and
provides semantic search via FAISS + Model2Vec.

Phase 45: MegaIndex migration -- _registry now populated from MegaIndex
instead of independent XML scanning. One parse to rule them all.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger

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
    "RegionInfo": ("region", "RegionName", "KnowledgeKey"),
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
        self._key_to_strkey: Dict[str, str] = {}  # Key attr -> StrKey mapping
        self._initialized = False

    # =========================================================================
    # Initialization
    # =========================================================================

    def initialize(self) -> None:
        """Full initialization: populate from MegaIndex, cross-ref, index."""
        if self._initialized:
            return

        logger.info("[Codex] Initializing entity registry from MegaIndex...")
        t0 = time.time()

        # Trigger MegaIndex build if not already built.
        # Guard against RuntimeError if a background rebuild is in progress.
        from server.tools.ldm.services.mega_index import get_mega_index
        mega = get_mega_index()
        if not mega._built:
            try:
                mega.build()
            except RuntimeError:
                logger.warning("[CODEX] MegaIndex build already in progress — using current state")

        self._populate_from_mega_index()
        self._resolve_cross_refs()
        self._find_related_entities()

        try:
            self._build_search_index()
        except Exception as e:
            logger.warning(f"[Codex] FAISS index build failed (search unavailable): {e}")

        elapsed = time.time() - t0
        total = sum(len(v) for v in self._registry.values())
        logger.info(f"[Codex] Initialized: {total} entities in {elapsed:.2f}s (via MegaIndex)")
        self._initialized = True

    # =========================================================================
    # MegaIndex population (replaces _scan_entities)
    # =========================================================================

    def _populate_from_mega_index(self) -> None:
        """Convert MegaIndex frozen dataclasses to CodexEntity Pydantic models."""
        from server.tools.ldm.services.mega_index import get_mega_index
        mega = get_mega_index()

        self._registry = {
            "character": {},
            "item": {},
            "skill": {},
            "gimmick": {},
            "knowledge": {},
            "region": {},
        }

        # Knowledge entries
        for strkey, e in mega.knowledge_by_strkey.items():
            attrs: Dict[str, str] = {}
            if e.group_key:
                attrs["GroupKey"] = e.group_key
            self._registry["knowledge"][strkey] = CodexEntity(
                entity_type="knowledge",
                strkey=e.strkey,
                name=e.name,
                description=e.desc or None,
                knowledge_key=None,
                image_texture=e.ui_texture_name or None,
                audio_key=e.strkey,
                source_file=e.source_file,
                attributes=attrs,
                related_entities=[],
            )

        # Character entries
        for strkey, e in mega.character_by_strkey.items():
            attrs = {}
            if e.use_macro:
                attrs["UseMacro"] = e.use_macro
            if e.age:
                attrs["Age"] = e.age
            if e.job:
                attrs["Job"] = e.job
            if e.ui_icon_path:
                attrs["UIIconPath"] = e.ui_icon_path
            self._registry["character"][strkey] = CodexEntity(
                entity_type="character",
                strkey=e.strkey,
                name=e.name,
                description=e.desc or None,
                knowledge_key=e.knowledge_key or None,
                image_texture=None,
                audio_key=e.strkey,
                source_file=e.source_file,
                attributes=attrs,
                related_entities=[],
            )

        # Item entries
        for strkey, e in mega.item_by_strkey.items():
            attrs = {}
            if e.group_key:
                attrs["GroupKey"] = e.group_key
            self._registry["item"][strkey] = CodexEntity(
                entity_type="item",
                strkey=e.strkey,
                name=e.name,
                description=e.desc or None,
                knowledge_key=e.knowledge_key or None,
                image_texture=None,
                audio_key=e.strkey,
                source_file=e.source_file,
                attributes=attrs,
                related_entities=[],
            )

        # Region entries
        for strkey, e in mega.region_by_strkey.items():
            attrs = {}
            if e.world_position is not None:
                attrs["WorldPosition"] = f"{e.world_position[0]},{e.world_position[1]},{e.world_position[2]}"
            if e.node_type:
                attrs["NodeType"] = e.node_type
            if e.parent_strkey:
                attrs["ParentStrKey"] = e.parent_strkey
            self._registry["region"][strkey] = CodexEntity(
                entity_type="region",
                strkey=e.strkey,
                name=e.display_name or e.name,
                description=e.desc or None,
                knowledge_key=e.knowledge_key or None,
                image_texture=None,
                audio_key=e.strkey,
                source_file=e.source_file,
                attributes=attrs,
                related_entities=[],
            )

        # Skill entries
        for strkey, e in mega.skill_by_strkey.items():
            self._registry["skill"][strkey] = CodexEntity(
                entity_type="skill",
                strkey=e.strkey,
                name=e.name,
                description=e.desc or None,
                knowledge_key=e.learn_knowledge_key or None,
                image_texture=None,
                audio_key=e.strkey,
                source_file=e.source_file,
                attributes={},
                related_entities=[],
            )

        # Gimmick entries
        for strkey, e in mega.gimmick_by_strkey.items():
            desc = e.desc or None
            if e.seal_desc and desc:
                desc = f"{desc} | {e.seal_desc}"
            elif e.seal_desc:
                desc = e.seal_desc
            self._registry["gimmick"][strkey] = CodexEntity(
                entity_type="gimmick",
                strkey=e.strkey,
                name=e.name,
                description=desc,
                knowledge_key=None,
                image_texture=None,
                audio_key=e.strkey,
                source_file=e.source_file,
                attributes={},
                related_entities=[],
            )

        for etype, entities in self._registry.items():
            logger.debug(f"[Codex] Populated {len(entities)} {etype} entities from MegaIndex")

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
                    # BUG 4: Enrich name if it still equals strkey (no proper name found)
                    if entity.name == entity.strkey and know.name:
                        entity.name = know.name

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

        # BUG 3: Empty/whitespace query returns garbage from zero vector
        if not query or not query.strip():
            return CodexSearchResponse(
                results=[], count=0, search_time_ms=0.0
            )

        # BUG 1: Normalize entity_type to lowercase for case-insensitive matching
        if entity_type:
            entity_type = entity_type.lower()

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

        # BUG 1: Normalize entity_type to lowercase
        entity_type = entity_type.lower()

        registry = self._registry.get(entity_type, {})

        # BUG 2: Case-insensitive StrKey lookup
        entity = registry.get(strkey)
        if entity is not None:
            return entity

        # Fallback: case-insensitive search
        strkey_lower = strkey.lower()
        for key, ent in registry.items():
            if key.lower() == strkey_lower:
                return ent

        return None

    def list_entities(
        self,
        entity_type: str,
        offset: int = 0,
        limit: int | None = None,
    ) -> CodexListResponse:
        """Return entities of a given type, optionally paginated with offset/limit."""
        if not self._initialized:
            self.initialize()

        # BUG 1: Normalize entity_type to lowercase
        entity_type = entity_type.lower()

        entities = list(self._registry.get(entity_type, {}).values())
        total = len(entities)

        if limit is not None:
            page = entities[offset:offset + limit]
            has_more = (offset + len(page)) < total
        else:
            page = entities
            has_more = False

        return CodexListResponse(
            entities=page,
            entity_type=entity_type,
            count=len(page),
            total=total,
            has_more=has_more,
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

    def get_relationships(self) -> Dict[str, Any]:
        """Extract entity relationships from cross-references for graph visualization.

        Scans all entities for attributes ending in 'Key' or 'Id' that reference
        other entities. Returns nodes + links for D3 force graph.
        """
        if not self._initialized:
            self.initialize()

        nodes: List[Dict[str, Any]] = []
        links: List[Dict[str, Any]] = []
        seen_links: set = set()  # (source_strkey, target_strkey, rel_type) dedup
        entity_index: Dict[str, int] = {}  # strkey -> node index

        # Build node list from all non-knowledge entities
        for etype in ["character", "item", "skill", "region", "gimmick"]:
            for strkey, entity in self._registry.get(etype, {}).items():
                entity_index[strkey] = len(nodes)
                # Prefer Korean name from attributes, then entity.name, then strkey
                display_name = (
                    entity.attributes.get("NameKR")
                    or entity.name
                    or strkey
                )
                nodes.append({
                    "id": strkey,
                    "name": display_name,
                    "entity_type": etype,
                    "has_image": bool(entity.ai_image_url or entity.image_texture),
                    "image_url": f"/api/ldm/codex/image/{strkey}" if entity.ai_image_url else None,
                })

        # Collect unique FactionKey values and create synthetic faction nodes
        faction_keys = set()
        for etype in ["character", "item", "skill", "region", "gimmick"]:
            for strkey, entity in self._registry.get(etype, {}).items():
                fk = entity.attributes.get("FactionKey")
                if fk and fk not in entity_index:
                    faction_keys.add(fk)
        for fk in sorted(faction_keys):
            entity_index[fk] = len(nodes)
            nodes.append({
                "id": fk,
                "name": fk.replace("Region_", "").replace("_", " "),
                "entity_type": "faction",
                "has_image": False,
                "image_url": None,
            })

        # Relationship type classification based on attribute name
        REL_TYPE_MAP = {
            "ItemKey": "owns",
            "RewardKey": "owns",
            "SkillKey": "knows",
            "RequireSkillKey": "knows",
            "LearnKnowledgeKey": "knows",
            "KnowledgeKey": "knows",
            "FactionKey": "member_of",
            "RegionKey": "located_in",
            "CharacterKey": "enemy_of",
            "TargetKey": "enemy_of",
        }

        # Scan entities for cross-ref attributes
        for etype in ["character", "item", "skill", "region", "gimmick"]:
            for strkey, entity in self._registry.get(etype, {}).items():
                if strkey not in entity_index:
                    continue
                for attr_name, attr_value in entity.attributes.items():
                    if not attr_value:
                        continue
                    # Check if this attribute is a cross-ref
                    rel_type = REL_TYPE_MAP.get(attr_name)
                    if rel_type is None:
                        continue
                    # Find target in registry
                    target_strkey = str(attr_value)
                    if target_strkey not in entity_index:
                        # Try Key -> StrKey fallback for CharacterKey refs
                        resolved = self._key_to_strkey.get(target_strkey)
                        if resolved and resolved in entity_index:
                            target_strkey = resolved
                        else:
                            continue
                    # Dedup
                    link_key = (strkey, target_strkey, rel_type)
                    if link_key in seen_links:
                        continue
                    seen_links.add(link_key)
                    links.append({
                        "source": strkey,
                        "target": target_strkey,
                        "rel_type": rel_type,
                    })

        # Direct KnowledgeKey links (stripped from attributes by _SKIP_ATTRS)
        for etype in ["character", "item", "skill", "region"]:
            for strkey, entity in self._registry.get(etype, {}).items():
                if strkey not in entity_index or not entity.knowledge_key:
                    continue
                target = entity.knowledge_key
                if target not in entity_index:
                    target = self._key_to_strkey.get(target, target)
                if target not in entity_index:
                    continue
                link_key = (strkey, target, "knows")
                if link_key not in seen_links:
                    seen_links.add(link_key)
                    links.append({"source": strkey, "target": target, "rel_type": "knows"})

        # Add related_entities links (from same-file grouping)
        for etype in ["character", "item", "skill", "region", "gimmick"]:
            for strkey, entity in self._registry.get(etype, {}).items():
                if strkey not in entity_index:
                    continue
                for related_ref in (entity.related_entities or []):
                    # related_ref format: "type/strkey"
                    parts = related_ref.split("/", 1)
                    if len(parts) == 2:
                        target_strkey = parts[1]
                        if target_strkey in entity_index:
                            # Skip related link if ANY typed link exists for this pair
                            has_typed = any(
                                (strkey, target_strkey, rt) in seen_links
                                for rt in REL_TYPE_MAP.values()
                            )
                            if has_typed:
                                continue
                            link_key = (strkey, target_strkey, "related")
                            if link_key not in seen_links:
                                seen_links.add(link_key)
                                links.append({
                                    "source": strkey,
                                    "target": target_strkey,
                                    "rel_type": "related",
                                })

        logger.info(f"[Codex] Relationships extracted: {len(nodes)} nodes, {len(links)} links")
        return {"nodes": nodes, "links": links}
