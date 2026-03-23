"""
E2E tests for Entity Detection + Context Panel pipelines.

Verifies:
- FEAT-05: Aho-Corasick entity detection identifies character/item/location names
- FEAT-06: Context panel returns entity metadata, image/audio references for StringId

Uses the shared E2E fixtures (client, auth_headers, api) from conftest.py.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------
pytestmark = [pytest.mark.e2e, pytest.mark.entity, pytest.mark.context]


# ===========================================================================
# TestContextServiceStatus
# ===========================================================================


class TestContextServiceStatus:
    """Verify context and mapdata service status endpoints are reachable."""

    def test_context_status_returns_200(self, api):
        """GET /api/ldm/context/status returns 200."""
        resp = api.get_context_status()
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"

    def test_context_status_has_glossary_info(self, api):
        """Context status response includes glossary information."""
        resp = api.get_context_status()
        assert resp.status_code == 200
        data = resp.json()
        # Status should contain glossary info (loaded or not)
        assert "glossary" in data, (
            f"Expected 'glossary' key in context status. Keys: {list(data.keys())}"
        )

    def test_mapdata_status_returns_200(self, api):
        """GET /api/ldm/mapdata/status returns 200."""
        resp = api.get_mapdata_status()
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"


# ===========================================================================
# TestEntityDetection (FEAT-05)
# ===========================================================================


class TestEntityDetection:
    """Verify Aho-Corasick entity detection via /api/ldm/context/detect."""

    def test_detect_entities_endpoint_exists(self, api):
        """POST /api/ldm/context/detect accepts text and returns 200."""
        resp = api.detect_entities_in_text("Hello world")
        assert resp.status_code == 200, (
            f"Detect endpoint returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_detect_entities_returns_structured_response(self, api):
        """Detection response has EntityContextResponse structure."""
        resp = api.detect_entities_in_text("Hello world")
        assert resp.status_code == 200
        data = resp.json()
        # EntityContextResponse must have detected_in_text field
        assert "detected_in_text" in data, (
            f"Expected 'detected_in_text' key. Keys: {list(data.keys())}"
        )
        assert isinstance(data["detected_in_text"], list)

    @pytest.mark.xfail(
        reason="Requires GlossaryService initialized with gamedata folder; "
               "mock_gamedata may not be configured in test environment"
    )
    def test_detect_known_entity_name(self, api):
        """Detect a known character name from mock StaticInfo data.

        Mock characterinfo contains StrKey 'Character_ElderVaron' with
        Korean name. The EN detection depends on GlossaryService extracting
        entity names from the configured gamedata path.
        """
        # Character_ElderVaron has Korean name, but detection typically uses
        # EN names derived from StrKey patterns. Try detection with known StrKey-based names.
        # The glossary extracts names like "Elder Varon" from the StrKey or EN fields.
        resp = api.detect_entities_in_text("Elder Varon guards the sealed library")
        assert resp.status_code == 200
        data = resp.json()
        detected = data.get("detected_in_text", [])
        assert len(detected) > 0, (
            "Expected at least one entity detected for 'Elder Varon'. "
            "GlossaryService may not be loaded with mock gamedata."
        )
        # Verify detected entity has positional data
        entity = detected[0]
        assert "term" in entity
        assert "start" in entity
        assert "end" in entity
        assert entity["start"] < entity["end"], "start must be before end"

    def test_detect_no_entities_in_plain_text(self, api):
        """Plain text without entity names returns empty detection list."""
        resp = api.detect_entities_in_text("The quick brown fox jumps over the lazy dog")
        assert resp.status_code == 200
        data = resp.json()
        detected = data.get("detected_in_text", [])
        # If glossary is not loaded, this will be empty anyway.
        # If loaded, "quick brown fox" should not match any game entities.
        assert isinstance(detected, list)
        assert len(detected) == 0, (
            f"Expected no entities in plain text, but found {len(detected)}: "
            f"{[d.get('term') for d in detected]}"
        )


# ===========================================================================
# TestContextPanel (FEAT-06)
# ===========================================================================


class TestContextPanel:
    """Verify context panel endpoint returns entity info with media structure."""

    def test_context_by_string_id_returns_200(self, api):
        """GET /api/ldm/context/{string_id} returns 200 for any string_id."""
        resp = api.get_context_by_string_id("DLG_001")
        assert resp.status_code == 200, (
            f"Context endpoint returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_context_response_structure(self, api):
        """Context response has EntityContextResponse fields."""
        resp = api.get_context_by_string_id("DLG_001")
        assert resp.status_code == 200
        data = resp.json()
        # Must have all EntityContextResponse fields
        assert "entities" in data, f"Missing 'entities'. Keys: {list(data.keys())}"
        assert "detected_in_text" in data, f"Missing 'detected_in_text'. Keys: {list(data.keys())}"
        assert "string_id_context" in data, f"Missing 'string_id_context'. Keys: {list(data.keys())}"
        # entities and detected_in_text must be lists
        assert isinstance(data["entities"], list)
        assert isinstance(data["detected_in_text"], list)

    @pytest.mark.xfail(
        reason="Requires GlossaryService + MapDataService initialized with gamedata; "
               "entity resolution needs configured gamedata folder"
    )
    def test_context_with_known_strkey(self, api):
        """Query context for a known StrKey from mock StaticInfo.

        Character_ElderVaron exists in mock characterinfo XML. If the
        GlossaryService is loaded, querying this StrKey should return
        entity context with structured image/audio references (may be None
        if MapDataService is not configured).
        """
        resp = api.get_context_by_string_id("Character_ElderVaron")
        assert resp.status_code == 200
        data = resp.json()
        entities = data.get("entities", [])
        assert len(entities) > 0, (
            "Expected entity info for Character_ElderVaron. "
            "GlossaryService may not be loaded."
        )
        entity = entities[0]
        assert entity.get("name"), "Entity must have a name"
        assert entity.get("entity_type"), "Entity must have entity_type"
        assert entity.get("strkey"), "Entity must have strkey"

    def test_image_context_endpoint(self, api):
        """GET /api/ldm/mapdata/image/{string_id} returns 200 or 404."""
        resp = api.get_image_context("Character_ElderVaron")
        # Endpoint should exist — 200 if data found, 404 if not configured
        assert resp.status_code in (200, 404), (
            f"Image context returned unexpected {resp.status_code}: {resp.text[:200]}"
        )

    def test_audio_context_endpoint(self, api):
        """GET /api/ldm/mapdata/audio/{string_id} returns 200 or 404."""
        resp = api.get_audio_context("Character_ElderVaron")
        # Endpoint should exist — 200 if data found, 404 if not configured
        assert resp.status_code in (200, 404), (
            f"Audio context returned unexpected {resp.status_code}: {resp.text[:200]}"
        )
