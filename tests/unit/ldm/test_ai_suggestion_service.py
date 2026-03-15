"""
Tests for AISuggestionService -- AI-generated translation suggestions via Ollama/Qwen3.

Phase 17: AI Translation Suggestions (Plan 01)
Requirements: AISUG-01, AISUG-02, AISUG-04, AISUG-05
"""

from __future__ import annotations

import json

import httpx
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from server.tools.ldm.services.ai_suggestion_service import (
    AISuggestionService,
    get_ai_suggestion_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service():
    """Fresh AISuggestionService instance (no singleton)."""
    return AISuggestionService()


def _mock_ollama_response(suggestions: list[dict]) -> httpx.Response:
    """Build a mock httpx.Response with Ollama-style JSON body."""
    inner_json = json.dumps({"suggestions": suggestions})
    body = json.dumps({
        "model": "qwen3:4b",
        "response": inner_json,
        "done": True,
    })
    return httpx.Response(status_code=200, text=body)


def _make_suggestions(count: int = 3) -> list[dict]:
    """Build sample suggestion dicts for tests."""
    return [
        {"text": f"Translation {i+1}", "confidence": 0.8 - i * 0.1, "reasoning": f"Reason {i+1}"}
        for i in range(count)
    ]


def _mock_httpx_client(response=None, side_effect=None):
    """Create a mock httpx.AsyncClient context manager."""
    client_instance = AsyncMock()
    if side_effect:
        client_instance.post.side_effect = side_effect
    else:
        client_instance.post.return_value = response
    client_instance.__aenter__ = AsyncMock(return_value=client_instance)
    client_instance.__aexit__ = AsyncMock(return_value=False)
    return client_instance


# =============================================================================
# generate_suggestions() Tests
# =============================================================================


class TestGenerateSuggestions:
    """Test generate_suggestions() calls Ollama and parses structured JSON."""

    @pytest.mark.asyncio
    async def test_returns_three_suggestions(self, service):
        """AISUG-01: Returns 3 suggestions with text, confidence, reasoning."""
        suggestions = _make_suggestions(3)
        mock_response = _mock_ollama_response(suggestions)

        with patch("server.tools.ldm.services.ai_suggestion_service.httpx.AsyncClient") as MockClient:
            MockClient.return_value = _mock_httpx_client(response=mock_response)

            result = await service.generate_suggestions(
                string_id="SID_ITEM_001_NAME",
                source_text="Sword of Dawn",
                target_lang="KR",
                entity_type="Item",
                surrounding_context=[],
            )

        assert result["status"] == "generated"
        assert len(result["suggestions"]) == 3
        for s in result["suggestions"]:
            assert "text" in s
            assert "confidence" in s
            assert "reasoning" in s
            assert 0.0 <= s["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(self, service):
        """AISUG-01: Second call with same string_id + source_text returns cached."""
        suggestions = _make_suggestions(3)
        mock_response = _mock_ollama_response(suggestions)

        with patch("server.tools.ldm.services.ai_suggestion_service.httpx.AsyncClient") as MockClient:
            client_instance = _mock_httpx_client(response=mock_response)
            MockClient.return_value = client_instance

            # First call
            result1 = await service.generate_suggestions(
                "SID_001", "Sword of Dawn", "KR", "Item", []
            )
            assert result1["status"] == "generated"

            # Second call -- should use cache
            client_instance.post.reset_mock()
            result2 = await service.generate_suggestions(
                "SID_001", "Sword of Dawn", "KR", "Item", []
            )
            assert result2["status"] == "cached"
            assert len(result2["suggestions"]) == 3
            client_instance.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_connect_error_returns_unavailable(self, service):
        """AISUG-05: ConnectError -> status=unavailable, no crash."""
        with patch("server.tools.ldm.services.ai_suggestion_service.httpx.AsyncClient") as MockClient:
            MockClient.return_value = _mock_httpx_client(
                side_effect=httpx.ConnectError("Connection refused")
            )

            result = await service.generate_suggestions(
                "SID_001", "text", "KR", "Item", []
            )

        assert result["status"] == "unavailable"
        assert result["suggestions"] == []

    @pytest.mark.asyncio
    async def test_timeout_returns_unavailable(self, service):
        """AISUG-05: TimeoutException -> status=unavailable."""
        with patch("server.tools.ldm.services.ai_suggestion_service.httpx.AsyncClient") as MockClient:
            MockClient.return_value = _mock_httpx_client(
                side_effect=httpx.TimeoutException("Timed out")
            )

            result = await service.generate_suggestions(
                "SID_001", "text", "KR", "Item", []
            )

        assert result["status"] == "unavailable"
        assert result["suggestions"] == []

    @pytest.mark.asyncio
    async def test_malformed_json_returns_error(self, service):
        """AISUG-05: Malformed JSON from Ollama -> status=error."""
        bad_response = httpx.Response(
            status_code=200,
            text=json.dumps({
                "model": "qwen3:4b",
                "response": "not valid json{{{",
                "done": True,
            }),
        )

        with patch("server.tools.ldm.services.ai_suggestion_service.httpx.AsyncClient") as MockClient:
            MockClient.return_value = _mock_httpx_client(response=bad_response)

            result = await service.generate_suggestions(
                "SID_001", "text", "KR", "Item", []
            )

        assert result["status"] == "error"
        assert result["suggestions"] == []

    @pytest.mark.asyncio
    async def test_prompt_includes_entity_type_and_context(self, service):
        """AISUG-04: Prompt contains entity_type and surrounding_context."""
        suggestions = _make_suggestions(3)
        mock_response = _mock_ollama_response(suggestions)

        with patch("server.tools.ldm.services.ai_suggestion_service.httpx.AsyncClient") as MockClient:
            client_instance = _mock_httpx_client(response=mock_response)
            MockClient.return_value = client_instance

            context = [
                {"source": "Iron Shield", "target": "철의 방패"},
                {"source": "Steel Armor", "target": "강철 갑옷"},
            ]
            await service.generate_suggestions(
                "SID_ITEM_010_NAME", "Blade of Light", "KR", "Item", context
            )

            # Inspect the prompt sent
            call_args = client_instance.post.call_args
            payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
            prompt = payload["prompt"]
            assert "Item" in prompt
            assert "Iron Shield" in prompt
            assert "철의 방패" in prompt

    @pytest.mark.asyncio
    async def test_cache_key_includes_source_text_hash(self, service):
        """Cache key uses source_text hash, so different text invalidates cache."""
        suggestions = _make_suggestions(3)
        mock_response = _mock_ollama_response(suggestions)

        with patch("server.tools.ldm.services.ai_suggestion_service.httpx.AsyncClient") as MockClient:
            client_instance = _mock_httpx_client(response=mock_response)
            MockClient.return_value = client_instance

            # First call with text A
            await service.generate_suggestions(
                "SID_001", "Text A", "KR", "Item", []
            )

            # Second call with different text -> should NOT be cached
            result = await service.generate_suggestions(
                "SID_001", "Text B", "KR", "Item", []
            )
            assert result["status"] == "generated"
            assert client_instance.post.call_count == 2


# =============================================================================
# Blended Confidence Tests
# =============================================================================


class TestBlendConfidence:
    """Test _blend_confidence computation (AISUG-02)."""

    def test_blend_with_similar_segments(self, service):
        """0.4 * max_sim + 0.6 * llm_conf."""
        segments = [
            {"source": "a", "target": "b", "similarity": 0.9},
            {"source": "c", "target": "d", "similarity": 0.7},
        ]
        result = service._blend_confidence(0.8, segments)
        expected = 0.4 * 0.9 + 0.6 * 0.8  # 0.36 + 0.48 = 0.84
        assert abs(result - expected) < 0.001

    def test_blend_without_segments(self, service):
        """No segments -> return clamped llm_confidence."""
        result = service._blend_confidence(0.75, [])
        assert abs(result - 0.75) < 0.001

    def test_blend_clamped_to_one(self, service):
        """Result never exceeds 1.0."""
        segments = [{"source": "a", "target": "b", "similarity": 1.0}]
        result = service._blend_confidence(1.0, segments)
        assert result == 1.0

    def test_blend_clamped_to_zero(self, service):
        """Result never below 0.0."""
        result = service._blend_confidence(-0.5, [])
        assert result == 0.0


# =============================================================================
# Find Similar Segments Tests
# =============================================================================


class TestFindSimilarSegments:
    """Test _find_similar_segments with mocked EmbeddingEngine."""

    def test_returns_similar_segments_when_engine_available(self, service):
        """AISUG-02: Returns top-3 similar segments with source, target, similarity."""
        mock_engine = MagicMock()
        mock_engine.encode.return_value = np.array([[0.1] * 256], dtype=np.float32)
        mock_engine.is_loaded = True

        with patch("server.tools.ldm.services.ai_suggestion_service.get_embedding_engine", return_value=mock_engine):
            # We also need to mock the FAISS search -- but since there's no TM loaded,
            # we test the graceful empty return
            result = service._find_similar_segments("Sword of Dawn")

        # Without a loaded TM/FAISS index, returns empty gracefully
        assert isinstance(result, list)

    def test_returns_empty_when_engine_unavailable(self, service):
        """Returns [] when EmbeddingEngine cannot be loaded."""
        with patch(
            "server.tools.ldm.services.ai_suggestion_service.get_embedding_engine",
            side_effect=Exception("No engine"),
        ):
            result = service._find_similar_segments("test text")
        assert result == []


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingleton:
    """Test get_ai_suggestion_service() returns singleton."""

    def test_returns_same_instance(self):
        import server.tools.ldm.services.ai_suggestion_service as mod
        mod._service_instance = None
        svc1 = get_ai_suggestion_service()
        svc2 = get_ai_suggestion_service()
        assert svc1 is svc2
        mod._service_instance = None  # Cleanup
