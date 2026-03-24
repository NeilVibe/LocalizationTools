"""Tests for CodexService -- entity registry, cross-refs, FAISS search.

Phase 19: Game World Codex (Plan 01, Task 1)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# =============================================================================
# Fixtures
# =============================================================================

MOCK_GAMEDATA = Path(__file__).resolve().parents[2] / "fixtures" / "mock_gamedata"


@pytest.fixture
def codex_service():
    """Create a CodexService pointing at mock_gamedata."""
    from server.tools.ldm.services.codex_service import CodexService

    svc = CodexService(base_dir=MOCK_GAMEDATA / "StaticInfo")
    return svc


@pytest.fixture
def mock_embedding_engine():
    """Mock embedding engine that returns deterministic 256-dim vectors."""
    engine = MagicMock()
    engine.dimension = 256
    engine.is_loaded = True

    def _encode(texts, normalize=True, show_progress=False):
        """Return deterministic vectors based on text hash."""
        if isinstance(texts, str):
            texts = [texts]
        vecs = np.random.RandomState(42).randn(len(texts), 256).astype(np.float32)
        # Normalize
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return vecs / norms

    engine.encode = _encode
    engine.load = MagicMock()
    return engine


# =============================================================================
# Entity scanning tests
# =============================================================================


@pytest.mark.skip(reason="_scan_entities was replaced by MegaIndex population — method no longer exists")
class TestScanEntities:
    """Tests for _scan_entities method (DEPRECATED — method removed, replaced by MegaIndex)."""

    def test_scan_finds_all_entity_types(self, codex_service):
        """_scan_entities parses mock_gamedata and finds all 6 entity types."""
        codex_service._scan_entities()

        types_found = set(codex_service._registry.keys())
        # At minimum we expect character, item, skill, gimmick, knowledge, region
        assert "character" in types_found
        assert "item" in types_found
        assert "skill" in types_found
        assert "gimmick" in types_found
        assert "knowledge" in types_found
        assert "region" in types_found

    def test_scan_correct_entity_counts(self, codex_service):
        """_scan_entities produces non-zero counts for each entity type."""
        codex_service._scan_entities()

        for etype in ["character", "item", "skill", "gimmick", "knowledge", "region"]:
            assert len(codex_service._registry[etype]) > 0, f"No {etype} entities found"

    def test_entity_attributes_populated(self, codex_service):
        """Entity attributes dict contains type-specific fields."""
        codex_service._scan_entities()

        # Check item has Grade attribute
        item_entities = codex_service._registry["item"]
        some_item = list(item_entities.values())[0]
        assert "Grade" in some_item.attributes or "ItemType" in some_item.attributes

        # Check character has Race/Job
        char_entities = codex_service._registry["character"]
        some_char = list(char_entities.values())[0]
        assert "Race" in some_char.attributes or "Job" in some_char.attributes

    def test_entity_strkey_populated(self, codex_service):
        """Every entity has a non-empty strkey."""
        codex_service._scan_entities()

        for etype, entities in codex_service._registry.items():
            for strkey, entity in entities.items():
                assert entity.strkey, f"Empty strkey for {etype} entity"
                assert entity.strkey == strkey

    def test_entity_source_file_populated(self, codex_service):
        """Every entity has a source_file path."""
        codex_service._scan_entities()

        for etype, entities in codex_service._registry.items():
            for entity in entities.values():
                assert entity.source_file, f"Empty source_file for {etype}/{entity.strkey}"

    def test_audio_key_set_to_strkey(self, codex_service):
        """audio_key is set to entity strkey for all entities."""
        codex_service._scan_entities()

        for etype, entities in codex_service._registry.items():
            for entity in entities.values():
                assert entity.audio_key == entity.strkey


# =============================================================================
# Cross-reference tests
# =============================================================================


class TestCrossRefs:
    """Tests for _resolve_cross_refs method."""

    def test_cross_ref_populates_description(self, codex_service):
        """_resolve_cross_refs attaches description from KnowledgeInfo."""
        codex_service._scan_entities()
        codex_service._resolve_cross_refs()

        # Characters with KnowledgeKey should have descriptions
        chars = codex_service._registry["character"]
        chars_with_desc = [e for e in chars.values() if e.description is not None]
        assert len(chars_with_desc) > 0, "No characters got descriptions from cross-refs"

    def test_cross_ref_populates_image_texture(self, codex_service):
        """_resolve_cross_refs attaches image_texture from KnowledgeInfo."""
        codex_service._scan_entities()
        codex_service._resolve_cross_refs()

        # Items with KnowledgeKey should have image_texture
        items = codex_service._registry["item"]
        items_with_img = [e for e in items.values() if e.image_texture is not None]
        assert len(items_with_img) > 0, "No items got image_texture from cross-refs"

    def test_entity_without_knowledge_key_graceful(self, codex_service):
        """Entities without KnowledgeKey have None description/image gracefully."""
        codex_service._scan_entities()
        codex_service._resolve_cross_refs()

        # Knowledge entities themselves don't have KnowledgeKey cross-refs
        knowledge_entities = codex_service._registry["knowledge"]
        for entity in knowledge_entities.values():
            # Knowledge entities get their own description from their Desc attribute
            # but don't cross-ref further -- just ensure no crash
            assert entity.strkey is not None


# =============================================================================
# FAISS search tests
# =============================================================================


class TestSearch:
    """Tests for FAISS search integration."""

    def test_build_search_index(self, codex_service, mock_embedding_engine):
        """_build_search_index creates FAISS index with correct entity count."""
        with patch("server.tools.ldm.services.codex_service.get_embedding_engine",
                   return_value=mock_embedding_engine):
            codex_service._scan_entities()
            codex_service._resolve_cross_refs()
            codex_service._build_search_index()

        assert codex_service._faiss_index is not None
        assert codex_service._faiss_index.ntotal > 0
        # Index should have as many vectors as total entities
        total_entities = sum(len(v) for v in codex_service._registry.values())
        assert codex_service._faiss_index.ntotal == total_entities

    def test_search_returns_results(self, codex_service, mock_embedding_engine):
        """search() returns ranked results with similarity scores."""
        with patch("server.tools.ldm.services.codex_service.get_embedding_engine",
                   return_value=mock_embedding_engine):
            codex_service._scan_entities()
            codex_service._resolve_cross_refs()
            codex_service._build_search_index()
            codex_service._initialized = True

            response = codex_service.search("sword", limit=5)

        assert response.count > 0
        assert len(response.results) <= 5
        assert response.search_time_ms >= 0
        # Results should have similarity scores
        for result in response.results:
            assert isinstance(result.similarity, float)

    def test_search_with_type_filter(self, codex_service, mock_embedding_engine):
        """search() with entity_type filter returns only entities of that type."""
        with patch("server.tools.ldm.services.codex_service.get_embedding_engine",
                   return_value=mock_embedding_engine):
            codex_service._scan_entities()
            codex_service._resolve_cross_refs()
            codex_service._build_search_index()
            codex_service._initialized = True

            response = codex_service.search("sword", entity_type="item", limit=20)

        for result in response.results:
            assert result.entity.entity_type == "item"


# =============================================================================
# get_entity / list_entities tests
# =============================================================================


class TestEntityAccess:
    """Tests for get_entity and list_entities."""

    def test_get_entity_found(self, codex_service):
        """get_entity returns entity with resolved cross-refs."""
        codex_service._scan_entities()
        codex_service._resolve_cross_refs()
        codex_service._initialized = True

        # Get a known character
        chars = codex_service._registry["character"]
        first_strkey = list(chars.keys())[0]

        entity = codex_service.get_entity("character", first_strkey)
        assert entity is not None
        assert entity.entity_type == "character"
        assert entity.strkey == first_strkey

    def test_get_entity_not_found(self, codex_service):
        """get_entity returns None for nonexistent entity."""
        codex_service._scan_entities()
        codex_service._initialized = True

        entity = codex_service.get_entity("item", "NONEXISTENT_KEY")
        assert entity is None

    def test_list_entities_returns_all_of_type(self, codex_service):
        """list_entities returns all entities of a given type."""
        codex_service._scan_entities()
        codex_service._resolve_cross_refs()
        codex_service._initialized = True

        response = codex_service.list_entities("character")
        assert response.entity_type == "character"
        assert response.count == len(codex_service._registry["character"])
        assert len(response.entities) == response.count

    def test_list_entities_unknown_type(self, codex_service):
        """list_entities for unknown type returns empty list."""
        codex_service._scan_entities()
        codex_service._initialized = True

        response = codex_service.list_entities("dragon")
        assert response.entity_type == "dragon"
        assert response.count == 0
        assert response.entities == []
