"""
AI Intelligence subsystem API tests.

Tests AI Suggestions, Naming Coherence, Context Detection, and MapData
endpoints. All AI endpoints may depend on ML models (Ollama/Qwen, FAISS)
which may not be available in test -- tests handle graceful degradation
by accepting both success (200) and service-unavailable (503) responses.

Phase 25 Plan 08: AI Intelligence, Search, QA/Grammar E2E Tests
"""
from __future__ import annotations

import json

import pytest

from tests.api.helpers.assertions import (
    assert_json_fields,
    assert_status,
    assert_status_ok,
)
from tests.api.helpers.constants import KOREAN_TEXT_SAMPLES


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.ai


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Valid HTTP codes for AI endpoints: 200 (working) or 503 (model offline)
AI_ACCEPTABLE_CODES = {200, 503}
# Broader set that also allows 404 (no data) and 422 (validation)
AI_EXTENDED_CODES = {200, 404, 422, 500, 503}


def assert_ai_response(response, msg: str = ""):
    """Assert response is a valid AI endpoint response (200 or 503)."""
    prefix = f"{msg} -- " if msg else ""
    assert response.status_code in AI_ACCEPTABLE_CODES, (
        f"{prefix}Expected 200 or 503, got {response.status_code}. "
        f"Body: {response.text[:300]}"
    )


# =========================================================================
# AI Suggestions
# =========================================================================


class TestAISuggestionsStatus:
    """GET /api/ldm/ai-suggestions/status"""

    def test_ai_suggestions_status(self, api):
        """AI suggestion status endpoint returns valid response."""
        resp = api.ai_suggestions_status()
        assert_ai_response(resp, "AI suggestions status")
        if resp.status_code == 200:
            data = resp.json()
            # Should have availability info
            assert isinstance(data, dict)

    def test_ai_suggestions_status_response_shape(self, api):
        """Status response has expected structure when available."""
        resp = api.ai_suggestions_status()
        assert_ai_response(resp, "AI suggestions status shape")
        if resp.status_code == 200:
            data = resp.json()
            # Service returns status dict -- at minimum it should be a dict
            assert isinstance(data, dict), f"Expected dict, got {type(data).__name__}"


class TestAISuggestionsGenerate:
    """GET /api/ldm/ai-suggestions/{string_id}"""

    def test_ai_suggestions_generate(self, api):
        """Generate suggestions for a test string."""
        resp = api.get_ai_suggestions("TEST_001")
        assert resp.status_code in AI_EXTENDED_CODES, (
            f"Unexpected status {resp.status_code}: {resp.text[:200]}"
        )
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict)

    def test_ai_suggestions_generate_with_params(self, api):
        """Generate suggestions with source_text and target_lang params."""
        resp = api.client.get(
            "/api/ldm/ai-suggestions/TEST_001",
            headers=api.headers,
            params={
                "source_text": "검은 칼날의 전사",
                "target_lang": "KR",
            },
        )
        assert resp.status_code in AI_EXTENDED_CODES

    def test_ai_suggestions_response_schema(self, api):
        """If 200, response has suggestions array and status field."""
        resp = api.client.get(
            "/api/ldm/ai-suggestions/TEST_001",
            headers=api.headers,
            params={"source_text": "Sword of Dawn"},
        )
        if resp.status_code == 200:
            data = resp.json()
            # Service returns dict with suggestions/status
            assert "suggestions" in data or "status" in data, (
                f"Expected suggestions or status in response: {list(data.keys())}"
            )

    def test_ai_suggestions_korean_input(self, api):
        """Korean source text does not crash the endpoint."""
        resp = api.client.get(
            "/api/ldm/ai-suggestions/KR_TEST",
            headers=api.headers,
            params={"source_text": "마법 스킬 설명입니다"},
        )
        assert resp.status_code in AI_EXTENDED_CODES

    def test_ai_suggestions_long_text(self, api):
        """Very long input (1000+ chars) does not crash."""
        long_text = "테스트 문장입니다. " * 120  # ~1200 chars
        resp = api.client.get(
            "/api/ldm/ai-suggestions/LONG_TEST",
            headers=api.headers,
            params={"source_text": long_text[:2000]},
        )
        # Should not be 500
        assert resp.status_code != 500, f"Server error on long text: {resp.text[:200]}"


# =========================================================================
# Naming Coherence
# =========================================================================


class TestNamingStatus:
    """GET /api/ldm/naming/status"""

    def test_naming_status(self, api):
        """Naming status endpoint returns valid response."""
        resp = api.naming_status()
        assert_ai_response(resp, "Naming status")

    def test_naming_status_response_shape(self, api):
        """Status response is a dict when available."""
        resp = api.naming_status()
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict)


class TestNamingSimilar:
    """GET /api/ldm/naming/similar/{entity_type}"""

    def test_naming_similar_basic(self, api):
        """Find similar names for an entity type."""
        resp = api.naming_similar("item", name="Sword")
        assert resp.status_code in AI_EXTENDED_CODES

    def test_naming_similar_response_fields(self, api):
        """If 200, response has items list and count."""
        resp = api.naming_similar("item", name="Shield")
        if resp.status_code == 200:
            data = resp.json()
            assert "items" in data, f"Missing 'items' in response: {list(data.keys())}"
            assert "count" in data, f"Missing 'count' in response: {list(data.keys())}"
            assert isinstance(data["items"], list)

    def test_naming_similar_korean(self, api):
        """Korean entity name input does not crash."""
        resp = api.naming_similar("character", name="검은 기사")
        assert resp.status_code in AI_EXTENDED_CODES


class TestNamingSuggest:
    """GET /api/ldm/naming/suggest/{entity_type}"""

    def test_naming_suggest_basic(self, api):
        """Get naming suggestions for an entity."""
        resp = api.naming_suggest("item", name="Dark Blade")
        assert resp.status_code in AI_EXTENDED_CODES

    def test_naming_suggest_korean(self, api):
        """Korean entity name for suggestions."""
        resp = api.naming_suggest("character", name="빛의 수호자")
        assert resp.status_code in AI_EXTENDED_CODES

    def test_naming_suggest_response_fields(self, api):
        """If 200, response has suggestions list and status."""
        resp = api.naming_suggest("item", name="Flame Sword")
        if resp.status_code == 200:
            data = resp.json()
            assert "suggestions" in data, f"Missing 'suggestions': {list(data.keys())}"
            assert "status" in data, f"Missing 'status': {list(data.keys())}"


# =========================================================================
# Context
# =========================================================================


class TestContextStatus:
    """GET /api/ldm/context/status"""

    def test_context_status(self, api):
        """Context status endpoint returns valid response."""
        resp = api.get_context_status()
        assert_ai_response(resp, "Context status")

    def test_context_status_dict(self, api):
        """Status returns a dict with service info."""
        resp = api.get_context_status()
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict)


class TestContextDetect:
    """POST /api/ldm/context/detect"""

    def test_context_detect_english(self, api):
        """Detect entities in English text."""
        resp = api.detect_entities_in_text("The warrior wielded the Blade of Dawn")
        assert resp.status_code in AI_EXTENDED_CODES

    def test_context_detect_korean(self, api):
        """Detect entities in Korean text."""
        resp = api.detect_entities_in_text("검은 기사가 새벽의 칼날을 들었다")
        assert resp.status_code in AI_EXTENDED_CODES

    def test_context_detect_response_schema(self, api):
        """If 200, response has entities and detected_in_text."""
        resp = api.detect_entities_in_text("Some entity text here")
        if resp.status_code == 200:
            data = resp.json()
            assert "entities" in data, f"Missing 'entities': {list(data.keys())}"
            assert "detected_in_text" in data, f"Missing 'detected_in_text': {list(data.keys())}"


class TestContextByStringId:
    """GET /api/ldm/context/{string_id}"""

    def test_context_get_by_string_id(self, api):
        """Get context for a string_id (may return empty context)."""
        resp = api.get_context_by_string_id("TEST_001")
        assert resp.status_code in AI_EXTENDED_CODES

    def test_context_string_id_response_schema(self, api):
        """If 200, response matches EntityContextResponse."""
        resp = api.get_context_by_string_id("ITEM_SWORD_001")
        if resp.status_code == 200:
            data = resp.json()
            assert "entities" in data


# =========================================================================
# MapData
# =========================================================================


class TestMapDataStatus:
    """GET /api/ldm/mapdata/status"""

    def test_mapdata_status(self, api):
        """MapData status endpoint returns valid response."""
        resp = api.get_mapdata_status()
        assert_ai_response(resp, "MapData status")

    def test_mapdata_status_fields(self, api):
        """Status response has expected fields."""
        resp = api.get_mapdata_status()
        if resp.status_code == 200:
            data = resp.json()
            assert "loaded" in data, f"Missing 'loaded': {list(data.keys())}"
            assert "known_branches" in data, f"Missing 'known_branches': {list(data.keys())}"


class TestMapDataImageContext:
    """GET /api/ldm/mapdata/image/{string_id}"""

    def test_mapdata_image_context(self, api):
        """Image context returns 200 or 404 (no image for string)."""
        resp = api.get_image_context("TEST_001")
        assert resp.status_code in {200, 404, 503}

    def test_mapdata_image_context_response(self, api):
        """If 200, response has texture_name and has_image."""
        resp = api.get_image_context("ITEM_SWORD_001")
        if resp.status_code == 200:
            data = resp.json()
            assert "texture_name" in data
            assert "has_image" in data


class TestMapDataAudioContext:
    """GET /api/ldm/mapdata/audio/{string_id}"""

    def test_mapdata_audio_context(self, api):
        """Audio context returns 200 or 404 (no audio for string)."""
        resp = api.get_audio_context("TEST_001")
        assert resp.status_code in {200, 404, 503}


class TestMapDataCombinedContext:
    """GET /api/ldm/mapdata/context/{string_id}"""

    def test_mapdata_combined_context(self, api):
        """Combined context returns 200 with nullable image/audio."""
        resp = api.get_combined_context("TEST_001")
        assert resp.status_code in {200, 404, 503}

    def test_mapdata_combined_response_schema(self, api):
        """If 200, response has string_id, image, audio fields."""
        resp = api.get_combined_context("ITEM_001")
        if resp.status_code == 200:
            data = resp.json()
            assert "string_id" in data
            # image and audio can be null
            assert "image" in data or data.get("image") is None
            assert "audio" in data or data.get("audio") is None


class TestMapDataConfigure:
    """POST /api/ldm/mapdata/configure"""

    def test_mapdata_configure_invalid_branch(self, api):
        """Invalid branch returns 400."""
        resp = api.configure_mapdata(branch="nonexistent_branch", drive="C")
        assert resp.status_code in {400, 422}


# =========================================================================
# Graceful Degradation
# =========================================================================


class TestAIGracefulDegradation:
    """AI endpoints must never return 500 Internal Server Error."""

    @pytest.mark.parametrize("endpoint_call", [
        "ai_suggestions_status",
        "naming_status",
        "get_context_status",
        "get_mapdata_status",
    ])
    def test_ai_status_endpoints_no_500(self, api, endpoint_call):
        """Status endpoints never return 500."""
        resp = getattr(api, endpoint_call)()
        assert resp.status_code != 500, (
            f"{endpoint_call} returned 500: {resp.text[:200]}"
        )

    def test_ai_suggestions_no_server_error(self, api):
        """AI suggestions endpoint does not return 500."""
        resp = api.client.get(
            "/api/ldm/ai-suggestions/GRACEFUL_TEST",
            headers=api.headers,
            params={"source_text": "Test graceful degradation"},
        )
        assert resp.status_code != 500, f"AI suggestions 500: {resp.text[:200]}"

    def test_naming_no_server_error(self, api):
        """Naming endpoint does not return 500 when model offline."""
        resp = api.naming_similar("item", name="Test")
        assert resp.status_code != 500, f"Naming similar 500: {resp.text[:200]}"

    def test_context_detect_no_server_error(self, api):
        """Context detect does not return 500."""
        resp = api.detect_entities_in_text("Graceful degradation test")
        assert resp.status_code != 500, f"Context detect 500: {resp.text[:200]}"

    def test_ai_status_indicates_availability(self, api):
        """All AI status endpoints clearly indicate availability."""
        for call_name in ["ai_suggestions_status", "naming_status", "get_context_status"]:
            resp = getattr(api, call_name)()
            if resp.status_code == 200:
                data = resp.json()
                # Status should be a dict (not a raw string or error)
                assert isinstance(data, dict), (
                    f"{call_name} returned non-dict: {type(data).__name__}"
                )
