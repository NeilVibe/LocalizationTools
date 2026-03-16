"""Tests for GameDataIndexer -- multi-tier index builder for gamedata entities.

TDD RED: These tests define the expected behavior of GameDataIndexer.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from server.tools.ldm.schemas.gamedata import TreeNode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_tree_node(tag: str, attrs: dict, children=None, node_id="node_0", parent_id=None):
    """Helper to create a TreeNode with defaults."""
    from server.tools.ldm.services.gamedata_browse_service import EDITABLE_ATTRS
    editable = EDITABLE_ATTRS.get(tag, [])
    return TreeNode(
        node_id=node_id,
        tag=tag,
        attributes=attrs,
        children=children or [],
        parent_id=parent_id,
        editable_attrs=editable,
    )


@pytest.fixture
def indexer():
    """Fresh GameDataIndexer instance."""
    from server.tools.ldm.indexing.gamedata_indexer import GameDataIndexer
    return GameDataIndexer()


# ---------------------------------------------------------------------------
# extract_entities_from_tree
# ---------------------------------------------------------------------------

class TestExtractEntities:
    """Tests for entity extraction from TreeNode hierarchy."""

    def test_extract_item_with_name_and_desc(self, indexer):
        """ItemInfo with name + desc -> entity with both fields."""
        node = _make_tree_node("ItemInfo", {
            "ItemName": "Blade of Dawn",
            "ItemDesc": "A legendary sword",
            "Key": "ITEM_001",
        })
        entities = indexer.extract_entities_from_tree([node])
        assert len(entities) == 1
        assert entities[0]["entity_name"] == "Blade of Dawn"
        assert entities[0]["entity_desc"] == "A legendary sword"
        assert entities[0]["node_id"] == "node_0"
        assert entities[0]["tag"] == "ItemInfo"

    def test_extract_character_no_desc(self, indexer):
        """CharacterInfo has no desc in EDITABLE_ATTRS -> entity_desc is empty."""
        node = _make_tree_node("CharacterInfo", {
            "CharacterName": "Elder Varon",
        })
        entities = indexer.extract_entities_from_tree([node])
        assert len(entities) == 1
        assert entities[0]["entity_name"] == "Elder Varon"
        assert entities[0]["entity_desc"] == ""

    def test_extract_node_waypoint_empty(self, indexer):
        """NodeWaypointInfo has no editable attrs -> no entities extracted."""
        node = _make_tree_node("NodeWaypointInfo", {"WaypointId": "WP_001"})
        entities = indexer.extract_entities_from_tree([node])
        assert len(entities) == 0

    def test_extract_recursive_children(self, indexer):
        """Recursion walks children: root + 2 children each with 1 child = 4 entities."""
        grandchild_1 = _make_tree_node("ItemInfo", {"ItemName": "GC1", "ItemDesc": "d1"}, node_id="gc1")
        grandchild_2 = _make_tree_node("ItemInfo", {"ItemName": "GC2", "ItemDesc": "d2"}, node_id="gc2")
        child_1 = _make_tree_node("ItemInfo", {"ItemName": "C1", "ItemDesc": "d"}, children=[grandchild_1], node_id="c1")
        child_2 = _make_tree_node("ItemInfo", {"ItemName": "C2", "ItemDesc": "d"}, children=[grandchild_2], node_id="c2")
        root = _make_tree_node("ItemInfo", {"ItemName": "Root", "ItemDesc": "d"}, children=[child_1, child_2], node_id="root")
        # Total: root(1) + child_1(1) + child_2(1) + gc1(1) + gc2(1) = 5
        # But plan says "root with 2 children each having 1 child = 4 total"
        # That is: 2 children + 2 grandchildren = 4 (root might not be counted if it's just a container)
        # Actually plan says 4, so root is NOT extracted if it's a generic container
        # Let's make root a non-editable tag
        root = TreeNode(
            node_id="root", tag="LanguageData", attributes={},
            children=[child_1, child_2], editable_attrs=[],
        )
        entities = indexer.extract_entities_from_tree([root])
        assert len(entities) == 4  # c1, c2, gc1, gc2


# ---------------------------------------------------------------------------
# build_indexes
# ---------------------------------------------------------------------------

class TestBuildIndexes:
    """Tests for index building from extracted entities."""

    def _make_entities(self, count=10):
        """Create a list of entity dicts."""
        entities = []
        for i in range(count):
            entities.append({
                "entity_name": f"Entity {i}",
                "entity_desc": f"Description for entity {i}",
                "node_id": f"node_{i}",
                "tag": "ItemInfo",
                "file_path": f"/path/to/file_{i}.xml",
                "attributes": {"Key": f"KEY_{i}", "StrKey": f"str_key_{i}", "ItemName": f"Entity {i}"},
            })
        return entities

    @patch("server.tools.ldm.indexing.gamedata_indexer.get_embedding_engine")
    def test_build_produces_all_index_keys(self, mock_get_engine, indexer):
        """build_indexes returns dict with all expected keys."""
        # Mock embedding engine
        mock_engine = MagicMock()
        mock_engine.is_loaded = True
        mock_engine.name = "test"
        mock_engine.dimension = 256
        mock_engine.encode.return_value = np.random.randn(10, 256).astype(np.float32)
        mock_get_engine.return_value = mock_engine

        entities = self._make_entities(10)
        result = indexer.build_indexes(entities)

        assert indexer.is_ready
        indexes = indexer.indexes
        assert "whole_lookup" in indexes
        assert "line_lookup" in indexes
        assert "ac_automaton" in indexes
        assert "whole_index" in indexes
        assert "whole_mapping" in indexes
        assert "line_index" in indexes
        assert "line_mapping" in indexes
        assert "metadata" in indexes

    @patch("server.tools.ldm.indexing.gamedata_indexer.get_embedding_engine")
    def test_build_br_tag_split(self, mock_get_engine, indexer):
        """Desc with br-tags splits into separate line_lookup entries."""
        mock_engine = MagicMock()
        mock_engine.is_loaded = True
        mock_engine.name = "test"
        mock_engine.dimension = 256
        mock_engine.encode.return_value = np.random.randn(5, 256).astype(np.float32)
        mock_get_engine.return_value = mock_engine

        entities = [{
            "entity_name": "Test Item",
            "entity_desc": "First line<br/>Second line",
            "node_id": "n1",
            "tag": "ItemInfo",
            "file_path": "/test.xml",
            "attributes": {"ItemName": "Test Item"},
        }]
        indexer.build_indexes(entities)
        line_lookup = indexer.indexes["line_lookup"]
        # Both lines should be in lookup
        from server.tools.ldm.indexing.utils import normalize_for_hash
        assert normalize_for_hash("First line") in line_lookup
        assert normalize_for_hash("Second line") in line_lookup

    @patch("server.tools.ldm.indexing.gamedata_indexer.get_embedding_engine")
    def test_build_does_not_split_on_newline(self, mock_get_engine, indexer):
        """br-tags are the split delimiter, NOT literal \\n in XML text."""
        mock_engine = MagicMock()
        mock_engine.is_loaded = True
        mock_engine.name = "test"
        mock_engine.dimension = 256
        mock_engine.encode.return_value = np.random.randn(5, 256).astype(np.float32)
        mock_get_engine.return_value = mock_engine

        # This desc has br-tags, verify it splits correctly
        entities = [{
            "entity_name": "Item",
            "entity_desc": "Line A<br/>Line B<br/>Line C",
            "node_id": "n1",
            "tag": "ItemInfo",
            "file_path": "/test.xml",
            "attributes": {"ItemName": "Item"},
        }]
        indexer.build_indexes(entities)
        line_lookup = indexer.indexes["line_lookup"]
        from server.tools.ldm.indexing.utils import normalize_for_hash
        assert normalize_for_hash("Line A") in line_lookup
        assert normalize_for_hash("Line B") in line_lookup
        assert normalize_for_hash("Line C") in line_lookup

    @patch("server.tools.ldm.indexing.gamedata_indexer.get_embedding_engine")
    def test_whole_lookup_maps_normalized_name(self, mock_get_engine, indexer):
        """whole_lookup contains normalized entity name -> entity data with node_id, tag, entity_name."""
        mock_engine = MagicMock()
        mock_engine.is_loaded = True
        mock_engine.name = "test"
        mock_engine.dimension = 256
        mock_engine.encode.return_value = np.random.randn(2, 256).astype(np.float32)
        mock_get_engine.return_value = mock_engine

        entities = [{
            "entity_name": "Blade of Dawn",
            "entity_desc": "A sword",
            "node_id": "n1",
            "tag": "ItemInfo",
            "file_path": "/test.xml",
            "attributes": {"ItemName": "Blade of Dawn"},
        }]
        indexer.build_indexes(entities)
        whole_lookup = indexer.indexes["whole_lookup"]

        from server.tools.ldm.indexing.utils import normalize_for_hash
        key = normalize_for_hash("Blade of Dawn")
        assert key in whole_lookup
        match = whole_lookup[key]
        assert match["node_id"] == "n1"
        assert match["tag"] == "ItemInfo"
        assert match["entity_name"] == "Blade of Dawn"

    @patch("server.tools.ldm.indexing.gamedata_indexer.get_embedding_engine")
    def test_whole_lookup_indexes_key_and_strkey(self, mock_get_engine, indexer):
        """whole_lookup also contains entries for Key and StrKey attributes (IDX-01)."""
        mock_engine = MagicMock()
        mock_engine.is_loaded = True
        mock_engine.name = "test"
        mock_engine.dimension = 256
        mock_engine.encode.return_value = np.random.randn(2, 256).astype(np.float32)
        mock_get_engine.return_value = mock_engine

        entities = [{
            "entity_name": "Blade",
            "entity_desc": "",
            "node_id": "n1",
            "tag": "ItemInfo",
            "file_path": "/test.xml",
            "attributes": {"Key": "ITEM_001", "StrKey": "str_item_001", "ItemName": "Blade"},
        }]
        indexer.build_indexes(entities)
        whole_lookup = indexer.indexes["whole_lookup"]

        from server.tools.ldm.indexing.utils import normalize_for_hash
        # 3 separate entries: name, Key, StrKey
        assert normalize_for_hash("Blade") in whole_lookup
        assert normalize_for_hash("ITEM_001") in whole_lookup
        assert normalize_for_hash("str_item_001") in whole_lookup

    @patch("server.tools.ldm.indexing.gamedata_indexer.get_embedding_engine")
    def test_ac_automaton_contains_entity_names(self, mock_get_engine, indexer):
        """AC automaton has all entity names added."""
        mock_engine = MagicMock()
        mock_engine.is_loaded = True
        mock_engine.name = "test"
        mock_engine.dimension = 256
        mock_engine.encode.return_value = np.random.randn(3, 256).astype(np.float32)
        mock_get_engine.return_value = mock_engine

        entities = [
            {"entity_name": "Blade of Dawn", "entity_desc": "", "node_id": "n1", "tag": "ItemInfo", "file_path": "/t.xml", "attributes": {}},
            {"entity_name": "Elder Varon", "entity_desc": "", "node_id": "n2", "tag": "CharacterInfo", "file_path": "/t.xml", "attributes": {}},
        ]
        indexer.build_indexes(entities)
        ac = indexer.indexes["ac_automaton"]
        import ahocorasick
        assert isinstance(ac, ahocorasick.Automaton)
        # Verify the names are in the automaton
        assert len(list(ac.iter("Blade of Dawn and Elder Varon"))) >= 2

    @patch("server.tools.ldm.indexing.gamedata_indexer.get_embedding_engine")
    def test_build_metadata(self, mock_get_engine, indexer):
        """build_indexes returns metadata with entity_count, build_time_ms, lookup counts."""
        mock_engine = MagicMock()
        mock_engine.is_loaded = True
        mock_engine.name = "test"
        mock_engine.dimension = 256
        mock_engine.encode.return_value = np.random.randn(3, 256).astype(np.float32)
        mock_get_engine.return_value = mock_engine

        entities = [
            {"entity_name": f"E{i}", "entity_desc": f"D{i}", "node_id": f"n{i}", "tag": "ItemInfo", "file_path": "/t.xml", "attributes": {}}
            for i in range(3)
        ]
        result = indexer.build_indexes(entities)
        metadata = indexer.indexes["metadata"]

        assert metadata["entity_count"] == 3
        assert "build_time_ms" in metadata
        assert "whole_lookup_count" in metadata
        assert "line_lookup_count" in metadata


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class TestSchemas:
    """Test that Pydantic schemas exist and validate."""

    def test_index_build_request(self):
        from server.tools.ldm.schemas.gamedata import IndexBuildRequest
        req = IndexBuildRequest(path="/some/folder")
        assert req.path == "/some/folder"

    def test_index_search_request(self):
        from server.tools.ldm.schemas.gamedata import IndexSearchRequest
        req = IndexSearchRequest(query="Blade of Dawn")
        assert req.query == "Blade of Dawn"
        assert req.top_k == 5
        assert req.threshold == 0.92

    def test_index_search_response(self):
        from server.tools.ldm.schemas.gamedata import IndexSearchResponse, IndexSearchResult
        result = IndexSearchResult(
            entity_name="Blade", entity_desc="A sword", node_id="n1",
            tag="ItemInfo", file_path="/t.xml", score=1.0, match_type="perfect_whole",
        )
        resp = IndexSearchResponse(tier=1, tier_name="perfect_whole", results=[result], perfect_match=True)
        assert resp.tier == 1
        assert len(resp.results) == 1

    def test_index_status_response(self):
        from server.tools.ldm.schemas.gamedata import IndexStatusResponse
        status = IndexStatusResponse(
            ready=True, entity_count=100, build_time_ms=500,
            ac_terms_count=80, whole_lookup_count=120, line_lookup_count=200,
        )
        assert status.ready is True

    def test_index_build_response(self):
        from server.tools.ldm.schemas.gamedata import IndexBuildResponse
        resp = IndexBuildResponse(
            entity_count=100, whole_lookup_count=120, line_lookup_count=200,
            whole_embeddings_count=100, line_embeddings_count=150,
            ac_terms_count=80, build_time_ms=500, status="ready",
        )
        assert resp.status == "ready"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_gamedata_indexer_returns_same_instance(self):
        from server.tools.ldm.indexing.gamedata_indexer import get_gamedata_indexer
        a = get_gamedata_indexer()
        b = get_gamedata_indexer()
        assert a is b
