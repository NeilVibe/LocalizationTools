"""GameData Index Builder -- multi-tier indexing for gamedata entities.

Adapted from TMIndexer (indexer.py). Key differences:
- In-memory only (no disk persistence, no DB tracking)
- Two-field extraction (name+desc) from TreeNode.attributes via EDITABLE_ATTRS
- br-tag splitting for line tiers (not \\n)
- Aho-Corasick automaton for entity detection (Tier 0)
- Global storage (not per-tm_id)

Phase 29: Multi-Tier Indexing (Plan 01)
"""

from __future__ import annotations

import time
import numpy as np
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

try:
    import ahocorasick
    AC_AVAILABLE = True
except ImportError:
    ahocorasick = None  # type: ignore
    AC_AVAILABLE = False
    logger.warning("ahocorasick not available - entity detection disabled")

try:
    import faiss  # noqa: F401
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss not available - embedding indexes disabled")

from server.tools.shared import FAISSManager, get_embedding_engine, get_current_engine_name
from server.tools.ldm.indexing.utils import (
    normalize_for_hash,
    normalize_for_embedding,
    normalize_newlines_universal,
)
from server.tools.ldm.services.gamedata_browse_service import EDITABLE_ATTRS
from server.tools.ldm.schemas.gamedata import TreeNode, FolderTreeDataResponse


class GameDataIndexer:
    """In-memory multi-tier index builder for gamedata entities.

    Adapted from TMIndexer. Key differences:
    - In-memory only (no disk persistence, no DB tracking)
    - Two-field extraction (name+desc) from TreeNode.attributes via EDITABLE_ATTRS
    - br-tag splitting for line tiers (not \\n)
    - Aho-Corasick automaton for Tier 0
    - Global storage (not per-tm_id)
    """

    def __init__(self):
        self._engine = None  # Lazy-loaded EmbeddingEngine
        self._indexes: Optional[Dict[str, Any]] = None
        self._ready = False
        self._metadata: Dict[str, Any] = {}

    @property
    def is_ready(self) -> bool:
        """Whether indexes are built and ready for search."""
        return self._ready

    @property
    def indexes(self) -> Optional[Dict[str, Any]]:
        """The built index data dict."""
        return self._indexes

    # =========================================================================
    # Entity Extraction
    # =========================================================================

    def extract_entities_from_tree(
        self, roots: List[TreeNode], file_path: str = ""
    ) -> List[Dict[str, Any]]:
        """Walk TreeNode hierarchy, extract entity_name + entity_desc using EDITABLE_ATTRS.

        For each node: check tag in EDITABLE_ATTRS. If present and has attrs:
        - entity_name = attributes[EDITABLE_ATTRS[tag][0]] (first attr)
        - entity_desc = attributes[EDITABLE_ATTRS[tag][1]] if len > 1 else ""

        Recurse into node.children.

        Returns list of dicts: {entity_name, entity_desc, node_id, tag, file_path, attributes}
        """
        entities: List[Dict[str, Any]] = []
        self._walk_tree(roots, entities, file_path)
        return entities

    def _walk_tree(
        self, nodes: List[TreeNode], entities: List[Dict[str, Any]], file_path: str
    ) -> None:
        """Recursive tree walker."""
        for node in nodes:
            editable = EDITABLE_ATTRS.get(node.tag, None)
            if editable is not None and len(editable) > 0:
                # Extract name from first editable attr
                entity_name = str(node.attributes.get(editable[0], ""))
                # Extract desc from second editable attr (if exists)
                entity_desc = str(node.attributes.get(editable[1], "")) if len(editable) > 1 else ""

                if entity_name:  # Only index entities with a name
                    entities.append({
                        "entity_name": entity_name,
                        "entity_desc": entity_desc,
                        "node_id": node.node_id,
                        "tag": node.tag,
                        "file_path": file_path,
                        "attributes": dict(node.attributes),
                    })

            # Recurse into children
            if node.children:
                self._walk_tree(node.children, entities, file_path)

    # =========================================================================
    # Main Index Building
    # =========================================================================

    def build_indexes(
        self,
        entities: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> Dict[str, Any]:
        """Build all index tiers from extracted entities.

        Pipeline:
        1. _build_whole_lookup(entities) -> whole_lookup dict
        2. _build_line_lookup(entities) -> line_lookup dict (br-tag split)
        3. _build_whole_embeddings(entities) -> FAISS HNSW index + mapping
        4. _build_line_embeddings(entities) -> FAISS HNSW index + mapping
        5. _build_ac_automaton(entities) -> ahocorasick.Automaton

        Store all in self._indexes dict. Set self._ready = True.
        Return metadata dict.
        """
        start_time = time.time()

        logger.info(f"[GameDataIndexer] Building indexes for {len(entities)} entities")

        if progress_callback:
            progress_callback("Building hash indexes", 0, 5)

        # Tier 1: whole hash lookup
        whole_lookup = self._build_whole_lookup(entities)

        # Tier 3: line hash lookup
        line_lookup = self._build_line_lookup(entities)

        if progress_callback:
            progress_callback("Building embeddings", 1, 5)

        # Tier 2: whole FAISS embeddings
        whole_result = self._build_whole_embeddings(entities)

        if progress_callback:
            progress_callback("Building line embeddings", 2, 5)

        # Tier 4: line FAISS embeddings
        line_result = self._build_line_embeddings(entities)

        if progress_callback:
            progress_callback("Building AC automaton", 3, 5)

        # Tier 0: Aho-Corasick automaton
        ac_automaton = self._build_ac_automaton(entities)

        elapsed_ms = int((time.time() - start_time) * 1000)

        metadata = {
            "entity_count": len(entities),
            "whole_lookup_count": len(whole_lookup),
            "line_lookup_count": len(line_lookup),
            "whole_embeddings_count": whole_result.get("count", 0),
            "line_embeddings_count": line_result.get("count", 0),
            "ac_terms_count": whole_result.get("ac_terms", 0) if ac_automaton is None else len(set(
                e["entity_name"] for e in entities if e.get("entity_name")
            )),
            "build_time_ms": elapsed_ms,
        }

        self._indexes = {
            "whole_lookup": whole_lookup,
            "line_lookup": line_lookup,
            "whole_index": whole_result.get("index"),
            "whole_mapping": whole_result.get("mapping", []),
            "whole_embeddings": whole_result.get("embeddings"),
            "line_index": line_result.get("index"),
            "line_mapping": line_result.get("mapping", []),
            "line_embeddings": line_result.get("embeddings"),
            "ac_automaton": ac_automaton,
            "metadata": metadata,
        }

        self._ready = True
        self._metadata = metadata

        if progress_callback:
            progress_callback("Complete", 5, 5)

        logger.success(
            f"[GameDataIndexer] Index build complete: {len(entities)} entities, "
            f"{len(whole_lookup)} whole keys, {len(line_lookup)} line keys, "
            f"{elapsed_ms}ms"
        )

        return metadata

    def build_from_folder_tree(self, folder_data: FolderTreeDataResponse) -> Dict[str, Any]:
        """Convenience: extract entities from FolderTreeDataResponse, then build_indexes.

        Iterates folder_data.files, for each file iterates file.roots.
        Passes file.file_path to each extracted entity dict.
        """
        all_entities: List[Dict[str, Any]] = []

        for file_data in folder_data.files:
            entities = self.extract_entities_from_tree(
                file_data.roots, file_path=file_data.file_path
            )
            all_entities.extend(entities)

        logger.info(
            f"[GameDataIndexer] Extracted {len(all_entities)} entities "
            f"from {len(folder_data.files)} files"
        )

        return self.build_indexes(all_entities)

    # =========================================================================
    # Hash Index Builders (Tier 1 & 3)
    # =========================================================================

    def _build_whole_lookup(self, entities: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Hashtable: normalized key -> entity data.

        Adapted from TMIndexer._build_whole_lookup.

        For EACH entity, add UP TO 3 entries:
        1. normalize_for_hash(entity_name) -> entity data (always, if non-empty)
        2. normalize_for_hash(attributes.get("Key")) -> entity data (if Key exists)
        3. normalize_for_hash(attributes.get("StrKey")) -> entity data (if StrKey exists)

        This satisfies IDX-01: lookup by Key, StrKey, or exact name.
        """
        logger.info("[GameDataIndexer] Building whole_lookup...")
        lookup: Dict[str, Dict[str, Any]] = {}

        for entity in entities:
            entity_data = {
                "entity_name": entity["entity_name"],
                "entity_desc": entity.get("entity_desc", ""),
                "node_id": entity["node_id"],
                "tag": entity["tag"],
                "file_path": entity.get("file_path", ""),
            }

            # 1. Index by entity name
            name = entity["entity_name"]
            if name:
                normalized = normalize_for_hash(name)
                if normalized and normalized not in lookup:
                    lookup[normalized] = entity_data

            # 2. Index by Key attribute
            attrs = entity.get("attributes", {})
            key_val = attrs.get("Key", "")
            if key_val:
                normalized_key = normalize_for_hash(key_val)
                if normalized_key and normalized_key not in lookup:
                    lookup[normalized_key] = entity_data

            # 3. Index by StrKey attribute
            strkey_val = attrs.get("StrKey", "")
            if strkey_val:
                normalized_strkey = normalize_for_hash(strkey_val)
                if normalized_strkey and normalized_strkey not in lookup:
                    lookup[normalized_strkey] = entity_data

        logger.info(f"[GameDataIndexer] Built whole_lookup: {len(lookup):,} entries")
        return lookup

    def _build_line_lookup(self, entities: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Hashtable: normalized desc line -> entity data.

        Adapted from TMIndexer._build_line_lookup.
        CRITICAL: Split entity_desc by '<br/>' via normalize_newlines_universal first,
        then split by '\\n'.
        """
        logger.info("[GameDataIndexer] Building line_lookup...")
        lookup: Dict[str, Dict[str, Any]] = {}

        for entity in entities:
            desc = entity.get("entity_desc", "")
            if not desc:
                continue

            # Use normalize_newlines_universal to convert <br/> -> \n, then split
            normalized_desc = normalize_newlines_universal(desc)
            lines = normalized_desc.split("\n")

            for i, line in enumerate(lines):
                if not line.strip():
                    continue

                normalized_line = normalize_for_hash(line)
                if not normalized_line:
                    continue

                if normalized_line not in lookup:
                    lookup[normalized_line] = {
                        "entity_name": entity["entity_name"],
                        "entity_desc": entity.get("entity_desc", ""),
                        "node_id": entity["node_id"],
                        "tag": entity["tag"],
                        "file_path": entity.get("file_path", ""),
                        "line_num": i,
                        "source_line": line,
                        "total_lines": len(lines),
                    }

        logger.info(f"[GameDataIndexer] Built line_lookup: {len(lookup):,} entries")
        return lookup

    # =========================================================================
    # Embedding Index Builders (Tier 2 & 4)
    # =========================================================================

    def _ensure_model_loaded(self):
        """Load the embedding engine if not already loaded."""
        if not FAISS_AVAILABLE:
            raise RuntimeError("faiss not available - embedding indexes disabled")

        if self._engine is None or not self._engine.is_loaded:
            engine_name = get_current_engine_name()
            logger.info(f"[GameDataIndexer] Loading embedding engine: {engine_name}")
            self._engine = get_embedding_engine(engine_name)
            self._engine.load()
            logger.success(f"[GameDataIndexer] Embedding engine loaded: {self._engine.name}")

    def _build_whole_embeddings(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """FAISS HNSW index on concatenated (entity_name + " " + entity_desc).

        Adapted from TMIndexer._build_whole_embeddings.
        Uses in-memory index (no disk persistence).
        """
        logger.info("[GameDataIndexer] Building whole-text embeddings...")

        texts = []
        mapping = []

        for entity in entities:
            name = entity["entity_name"]
            desc = entity.get("entity_desc", "")
            combined = f"{name} {desc}".strip() if desc else name

            normalized = normalize_for_embedding(combined)
            if normalized:
                texts.append(normalized)
                mapping.append({
                    "entity_name": entity["entity_name"],
                    "entity_desc": entity.get("entity_desc", ""),
                    "node_id": entity["node_id"],
                    "tag": entity["tag"],
                    "file_path": entity.get("file_path", ""),
                })

        if not texts:
            logger.warning("[GameDataIndexer] No texts to embed for whole embeddings")
            return {"count": 0, "dim": 0, "index": None, "mapping": [], "embeddings": None}

        self._ensure_model_loaded()

        logger.info(f"[GameDataIndexer] Encoding {len(texts):,} whole texts...")
        embeddings = self._engine.encode(texts, normalize=True, show_progress=False)
        embeddings = np.array(embeddings, dtype=np.float32)

        dim = embeddings.shape[1]
        # Build in-memory FAISS index (no path = no disk save)
        index = FAISSManager.build_index(embeddings, path=None, normalize=True)

        logger.info(f"[GameDataIndexer] Built whole embeddings: {len(texts):,} entries, dim={dim}")
        return {"count": len(texts), "dim": dim, "index": index, "mapping": mapping, "embeddings": embeddings}

    def _build_line_embeddings(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """FAISS HNSW per desc line after br-tag split.

        Same br-tag split logic as _build_line_lookup.
        """
        logger.info("[GameDataIndexer] Building line embeddings...")

        texts = []
        mapping = []

        for entity in entities:
            desc = entity.get("entity_desc", "")
            if not desc:
                continue

            normalized_desc = normalize_newlines_universal(desc)
            lines = normalized_desc.split("\n")

            for i, line in enumerate(lines):
                if not line.strip():
                    continue

                normalized = normalize_for_embedding(line)
                if not normalized or len(normalized) < 3:
                    continue

                texts.append(normalized)
                mapping.append({
                    "entity_name": entity["entity_name"],
                    "entity_desc": entity.get("entity_desc", ""),
                    "node_id": entity["node_id"],
                    "tag": entity["tag"],
                    "file_path": entity.get("file_path", ""),
                    "line_num": i,
                    "source_line": line,
                })

        if not texts:
            logger.warning("[GameDataIndexer] No texts to embed for line embeddings")
            return {"count": 0, "dim": 0, "index": None, "mapping": [], "embeddings": None}

        self._ensure_model_loaded()

        logger.info(f"[GameDataIndexer] Encoding {len(texts):,} lines...")
        embeddings = self._engine.encode(texts, normalize=True, show_progress=False)
        embeddings = np.array(embeddings, dtype=np.float32)

        dim = embeddings.shape[1]
        index = FAISSManager.build_index(embeddings, path=None, normalize=True)

        logger.info(f"[GameDataIndexer] Built line embeddings: {len(texts):,} lines, dim={dim}")
        return {"count": len(texts), "dim": dim, "index": index, "mapping": mapping, "embeddings": embeddings}

    # =========================================================================
    # Aho-Corasick Automaton (Tier 0)
    # =========================================================================

    def _build_ac_automaton(self, entities: List[Dict[str, Any]]) -> Any:
        """Build Aho-Corasick automaton from all entity_name values.

        Pattern from GlossaryService.build_from_entity_names:
        - Create ahocorasick.Automaton()
        - For each entity: automaton.add_word(entity_name, (idx, entity_name))
        - automaton.make_automaton()
        - Use frozenset dedup to skip duplicate names.
        """
        if not AC_AVAILABLE:
            logger.warning("[GameDataIndexer] ahocorasick not available, skipping AC automaton")
            return None

        logger.info("[GameDataIndexer] Building AC automaton...")
        automaton = ahocorasick.Automaton()
        seen_names: set = set()
        idx = 0

        for entity in entities:
            name = entity.get("entity_name", "")
            if not name or name in seen_names:
                continue

            seen_names.add(name)
            automaton.add_word(name, (idx, name, entity["node_id"], entity["tag"]))
            idx += 1

        if idx == 0:
            logger.warning("[GameDataIndexer] No terms for AC automaton, returning None")
            return None

        automaton.make_automaton()
        logger.info(f"[GameDataIndexer] Built AC automaton with {idx} terms")
        return automaton

    # =========================================================================
    # Status & Management
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Return index status: ready, entity_count, build_time_ms, tier counts."""
        if not self._ready or not self._metadata:
            return {
                "ready": False,
                "entity_count": 0,
                "build_time_ms": 0,
                "ac_terms_count": 0,
                "whole_lookup_count": 0,
                "line_lookup_count": 0,
            }

        return {
            "ready": True,
            "entity_count": self._metadata.get("entity_count", 0),
            "build_time_ms": self._metadata.get("build_time_ms", 0),
            "ac_terms_count": self._metadata.get("ac_terms_count", 0),
            "whole_lookup_count": self._metadata.get("whole_lookup_count", 0),
            "line_lookup_count": self._metadata.get("line_lookup_count", 0),
        }

    def clear(self):
        """Reset all indexes. Called before rebuild on new folder load."""
        self._indexes = None
        self._ready = False
        self._metadata = {}
        logger.info("[GameDataIndexer] Indexes cleared")


# =============================================================================
# Singleton
# =============================================================================

_indexer_instance: Optional[GameDataIndexer] = None


def get_gamedata_indexer() -> GameDataIndexer:
    """Get or create the singleton GameDataIndexer instance."""
    global _indexer_instance
    if _indexer_instance is None:
        _indexer_instance = GameDataIndexer()
    return _indexer_instance
