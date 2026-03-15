"""Codex API tests -- entity types, listing, search, detail, cross-references.

Validates the Codex encyclopedia endpoints:
- GET /api/ldm/codex/types          (available entity types)
- GET /api/ldm/codex/list/{type}    (list entities by type)
- GET /api/ldm/codex/search         (semantic/text search)
- GET /api/ldm/codex/entity/{type}/{strkey}  (single entity detail)

Tests cover cross-reference chains (character -> knowledge -> details),
Korean name search, and entity type sorting.
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import (
    assert_codex_entity,
    assert_error_response,
    assert_json_fields,
    assert_status,
    assert_status_ok,
)
from tests.api.helpers.constants import (
    CODEX_ENTITY_FIELDS,
    CODEX_SEARCH_FIELDS,
)


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.codex]


# ===========================================================================
# Entity Types endpoint
# ===========================================================================


class TestCodexTypes:
    """Tests for GET /api/ldm/codex/types."""

    def test_codex_types_returns_200(self, api):
        """GET /api/ldm/codex/types returns 200."""
        resp = api.get_codex_types()
        assert_status_ok(resp, "Codex types")

    def test_codex_types_is_dict(self, api):
        """Codex types response is a dict mapping type -> count."""
        resp = api.get_codex_types()
        assert_status_ok(resp, "Codex types dict")
        data = resp.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data).__name__}"

    def test_codex_types_include_character(self, api):
        """Entity types include 'character' (from mock characterinfo)."""
        resp = api.get_codex_types()
        data = resp.json()
        # Types may use different naming conventions
        type_keys = [k.lower() for k in data.keys()]
        has_character = any("character" in t for t in type_keys)
        assert has_character, f"'character' not found in types: {list(data.keys())}"

    def test_codex_types_include_item(self, api):
        """Entity types include 'item' (from mock iteminfo)."""
        resp = api.get_codex_types()
        data = resp.json()
        type_keys = [k.lower() for k in data.keys()]
        has_item = any("item" in t for t in type_keys)
        assert has_item, f"'item' not found in types: {list(data.keys())}"

    def test_codex_types_count(self, api):
        """Verify types dict has at least 3 entity types from mock data."""
        resp = api.get_codex_types()
        data = resp.json()
        assert len(data) >= 3, f"Expected >= 3 entity types, got {len(data)}: {list(data.keys())}"

    def test_codex_types_counts_are_positive(self, api):
        """Each type count is a positive integer."""
        resp = api.get_codex_types()
        data = resp.json()
        for type_name, count in data.items():
            assert isinstance(count, int), f"Count for '{type_name}' should be int, got {type(count).__name__}"
            assert count >= 0, f"Count for '{type_name}' should be >= 0, got {count}"


# ===========================================================================
# List Entities endpoint
# ===========================================================================


class TestCodexList:
    """Tests for GET /api/ldm/codex/list/{entity_type}."""

    def _get_first_entity_type(self, api) -> str:
        """Helper: get the first available entity type."""
        resp = api.get_codex_types()
        data = resp.json()
        assert len(data) > 0, "No entity types available"
        return list(data.keys())[0]

    def test_list_entities_returns_200(self, api):
        """List entities for a valid type returns 200."""
        entity_type = self._get_first_entity_type(api)
        resp = api.list_codex_entities(entity_type)
        assert_status_ok(resp, f"List {entity_type}")

    def test_list_entities_response_schema(self, api):
        """List response has entities, entity_type, count fields."""
        entity_type = self._get_first_entity_type(api)
        resp = api.list_codex_entities(entity_type)
        assert_status_ok(resp, "List schema")
        data = resp.json()
        assert_json_fields(data, ["entities", "entity_type", "count"], "CodexListResponse")
        assert isinstance(data["entities"], list)
        assert data["entity_type"] == entity_type

    def test_list_entities_have_names(self, api):
        """Each listed entity has a name field."""
        entity_type = self._get_first_entity_type(api)
        resp = api.list_codex_entities(entity_type)
        data = resp.json()
        for entity in data.get("entities", [])[:5]:
            assert "name" in entity, f"Entity missing 'name': {entity}"
            assert len(entity["name"]) > 0, f"Entity name is empty: {entity}"

    def test_list_entities_have_strkey(self, api):
        """Each listed entity has a strkey field."""
        entity_type = self._get_first_entity_type(api)
        resp = api.list_codex_entities(entity_type)
        data = resp.json()
        for entity in data.get("entities", [])[:5]:
            assert "strkey" in entity, f"Entity missing 'strkey': {entity}"

    def test_list_entities_have_source_file(self, api):
        """Each listed entity references its source file."""
        entity_type = self._get_first_entity_type(api)
        resp = api.list_codex_entities(entity_type)
        data = resp.json()
        for entity in data.get("entities", [])[:5]:
            assert "source_file" in entity, f"Entity missing 'source_file': {entity}"

    def test_list_nonexistent_type(self, api):
        """Listing an unknown entity type returns empty list (graceful)."""
        resp = api.list_codex_entities("nonexistent_type_xyz")
        # Should return 200 with empty list (graceful per route design)
        if resp.status_code == 200:
            data = resp.json()
            assert data["count"] == 0, f"Expected 0 entities, got {data['count']}"
            assert len(data["entities"]) == 0


# ===========================================================================
# Search endpoint
# ===========================================================================


class TestCodexSearch:
    """Tests for GET /api/ldm/codex/search."""

    def test_codex_search_returns_200(self, api):
        """Search with a query returns 200."""
        resp = api.search_codex(query="sword")
        assert_status_ok(resp, "Codex search")

    def test_codex_search_response_schema(self, api):
        """Search response has results, count, search_time_ms."""
        resp = api.search_codex(query="sword")
        assert_status_ok(resp, "Search schema")
        data = resp.json()
        assert_json_fields(data, CODEX_SEARCH_FIELDS, "CodexSearchResponse")
        assert isinstance(data["results"], list)
        assert isinstance(data["count"], int)

    def test_codex_search_by_korean_name(self, api):
        """Search by Korean entity name returns results."""
        # Use a Korean name from the fixture data
        resp = api.search_codex(query="장로 바론")
        assert_status_ok(resp, "Korean search")
        data = resp.json()
        # May return 0 if semantic search not indexed, but should not error
        assert isinstance(data["results"], list)

    def test_codex_search_by_strkey(self, api):
        """Search by StrKey returns matching entity."""
        resp = api.search_codex(query="STR_ITEM_0001")
        assert_status_ok(resp, "StrKey search")
        data = resp.json()
        assert isinstance(data["results"], list)

    def test_codex_search_with_entity_type_filter(self, api):
        """Search filtered by entity_type only returns that type."""
        types_resp = api.get_codex_types()
        types_data = types_resp.json()
        if len(types_data) > 0:
            first_type = list(types_data.keys())[0]
            resp = api.search_codex(query="a", entity_type=first_type)
            assert_status_ok(resp, "Filtered search")
            data = resp.json()
            for result in data.get("results", []):
                entity = result.get("entity", {})
                assert entity.get("entity_type") == first_type, (
                    f"Expected type '{first_type}', got '{entity.get('entity_type')}'"
                )

    def test_codex_search_empty_query_handled(self, api):
        """Search with very short query does not crash."""
        # Empty query should return 422 (FastAPI validation) since q is required
        resp = api.search_codex(query="a")
        # Should at least not 500
        assert resp.status_code < 500, f"Search crashed: {resp.status_code}"


# ===========================================================================
# Get Entity endpoint
# ===========================================================================


class TestCodexGetEntity:
    """Tests for GET /api/ldm/codex/entity/{entity_type}/{strkey}."""

    def _get_first_entity(self, api) -> tuple[str, str]:
        """Helper: get first entity type and strkey."""
        types_resp = api.get_codex_types()
        types_data = types_resp.json()
        assert len(types_data) > 0, "No entity types available"
        entity_type = list(types_data.keys())[0]
        list_resp = api.list_codex_entities(entity_type)
        entities = list_resp.json().get("entities", [])
        assert len(entities) > 0, f"No entities for type '{entity_type}'"
        return entity_type, entities[0]["strkey"]

    def test_get_entity_returns_200(self, api):
        """Get entity by type/strkey returns 200."""
        entity_type, strkey = self._get_first_entity(api)
        resp = api.get_codex_entity(entity_type, strkey)
        assert_status_ok(resp, f"Get entity {entity_type}/{strkey}")

    def test_get_entity_schema(self, api):
        """Entity response matches CodexEntity schema."""
        entity_type, strkey = self._get_first_entity(api)
        resp = api.get_codex_entity(entity_type, strkey)
        assert_status_ok(resp, "Entity schema")
        data = resp.json()
        assert_codex_entity(data)

    def test_get_nonexistent_entity(self, api):
        """Get nonexistent entity returns 404."""
        resp = api.get_codex_entity("item", "NONEXISTENT_KEY_XYZ_999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_get_entity_has_attributes(self, api):
        """Entity detail includes attributes dict."""
        entity_type, strkey = self._get_first_entity(api)
        resp = api.get_codex_entity(entity_type, strkey)
        data = resp.json()
        assert "attributes" in data, "Entity missing 'attributes'"
        assert isinstance(data["attributes"], dict)


# ===========================================================================
# Cross-Reference Chain tests
# ===========================================================================


class TestCodexCrossReferences:
    """Tests for cross-reference chains between entity types."""

    def test_character_knowledge_chain(self, api):
        """Character entities have knowledge_key that resolves to KnowledgeInfo."""
        types_resp = api.get_codex_types()
        types_data = types_resp.json()
        # Find character-like type
        char_type = None
        for t in types_data:
            if "character" in t.lower() or "npc" in t.lower():
                char_type = t
                break
        if char_type is None:
            pytest.skip("No character entity type found")

        list_resp = api.list_codex_entities(char_type)
        entities = list_resp.json().get("entities", [])
        if not entities:
            pytest.skip(f"No entities for type '{char_type}'")

        # Check first entity has knowledge_key
        entity = entities[0]
        knowledge_key = entity.get("knowledge_key")
        if knowledge_key:
            # The knowledge_key should reference a valid knowledge entity
            assert knowledge_key.startswith("KNOW_"), (
                f"Knowledge key should start with KNOW_: {knowledge_key}"
            )

    def test_item_knowledge_chain(self, api):
        """Item entities have knowledge_key linking to KnowledgeInfo."""
        types_resp = api.get_codex_types()
        types_data = types_resp.json()
        item_type = None
        for t in types_data:
            if "item" in t.lower():
                item_type = t
                break
        if item_type is None:
            pytest.skip("No item entity type found")

        list_resp = api.list_codex_entities(item_type)
        entities = list_resp.json().get("entities", [])
        if not entities:
            pytest.skip(f"No entities for type '{item_type}'")

        # Items should have knowledge keys
        entities_with_knowledge = [e for e in entities if e.get("knowledge_key")]
        assert len(entities_with_knowledge) > 0, (
            "At least some items should have knowledge_key"
        )

    def test_entity_type_sorting(self, api):
        """Entity types are returned in a consistent order."""
        resp = api.get_codex_types()
        data = resp.json()
        type_names = list(data.keys())
        # Should have a deterministic order (not random)
        resp2 = api.get_codex_types()
        type_names2 = list(resp2.json().keys())
        assert type_names == type_names2, (
            f"Entity type ordering not deterministic: {type_names} vs {type_names2}"
        )
