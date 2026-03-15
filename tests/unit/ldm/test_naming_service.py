"""
Tests for NamingCoherenceService -- entity naming similarity + AI suggestions.

Phase 21: AI Naming Coherence + Placeholders (Plan 01)
Requirements: AINAME-01, AINAME-02, AINAME-03, AINAME-05
"""

from __future__ import annotations

import json

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from server.tools.ldm.services.naming_coherence_service import (
    NamingCoherenceService,
    get_naming_coherence_service,
)
from server.tools.ldm.schemas.naming import (
    NamingSimilarItem,
    NamingSuggestionItem,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service():
    """Fresh NamingCoherenceService instance (no singleton)."""
    return NamingCoherenceService()


def _mock_codex_search_results(count: int = 3) -> MagicMock:
    """Build a mock CodexSearchResponse with entity results."""
    results = []
    names = ["Eldric the Wise", "Eldara of the North", "Eldwin Stormbreaker"]
    strkeys = ["CHR_ELDRIC", "CHR_ELDARA", "CHR_ELDWIN"]
    for i in range(count):
        result = MagicMock()
        result.entity = MagicMock()
        result.entity.name = names[i] if i < len(names) else f"Entity {i}"
        result.entity.strkey = strkeys[i] if i < len(strkeys) else f"KEY_{i}"
        result.entity.entity_type = "character"
        result.similarity = 0.95 - i * 0.1
        results.append(result)

    response = MagicMock()
    response.results = results
    return response


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
    """Build sample naming suggestion dicts."""
    return [
        {"name": f"Eldric Variant {i+1}", "confidence": 0.9 - i * 0.1, "reasoning": f"Pattern {i+1}"}
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
# find_similar_names() Tests
# =============================================================================


class TestFindSimilarNames:
    """Test find_similar_names() delegates to CodexService.search()."""

    def test_returns_ranked_results(self, service):
        """AINAME-01: Returns names sorted by similarity with entity_type and strkey."""
        mock_response = _mock_codex_search_results(3)

        with patch(
            "server.tools.ldm.services.naming_coherence_service._get_codex_service",
            return_value=MagicMock(search=MagicMock(return_value=mock_response)),
        ):
            result = service.find_similar_names("Eldric", entity_type="character", limit=10)

        assert len(result) == 3
        assert result[0]["name"] == "Eldric the Wise"
        assert result[0]["strkey"] == "CHR_ELDRIC"
        assert result[0]["entity_type"] == "character"
        assert result[0]["similarity"] == pytest.approx(0.95)
        # Verify sorted by similarity descending
        assert result[0]["similarity"] >= result[1]["similarity"] >= result[2]["similarity"]

    def test_filters_by_entity_type(self, service):
        """AINAME-01: entity_type param is passed through to CodexService.search()."""
        mock_codex = MagicMock()
        mock_codex.search.return_value = _mock_codex_search_results(0)
        mock_codex.search.return_value.results = []

        with patch(
            "server.tools.ldm.services.naming_coherence_service._get_codex_service",
            return_value=mock_codex,
        ):
            service.find_similar_names("Eldric", entity_type="item", limit=5)

        mock_codex.search.assert_called_once_with(query="Eldric", entity_type="item", limit=5)

    def test_empty_index(self, service):
        """AINAME-01: Empty index returns empty list without crash."""
        mock_response = MagicMock()
        mock_response.results = []

        with patch(
            "server.tools.ldm.services.naming_coherence_service._get_codex_service",
            return_value=MagicMock(search=MagicMock(return_value=mock_response)),
        ):
            result = service.find_similar_names("NonExistent", entity_type="character")

        assert result == []


# =============================================================================
# suggest_names() Tests
# =============================================================================


class TestSuggestNames:
    """Test suggest_names() generates AI naming suggestions via Ollama."""

    @pytest.mark.asyncio
    async def test_returns_structured_response(self, service):
        """AINAME-02: Returns NamingSuggestionResponse shape with name/confidence/reasoning."""
        suggestions = _make_suggestions(3)
        mock_response = _mock_ollama_response(suggestions)

        with patch(
            "server.tools.ldm.services.naming_coherence_service.httpx.AsyncClient"
        ) as MockClient:
            MockClient.return_value = _mock_httpx_client(response=mock_response)

            result = await service.suggest_names(
                name="Eldric",
                entity_type="character",
                similar_names=[],
            )

        assert result["status"] == "ok"
        assert len(result["suggestions"]) == 3
        for s in result["suggestions"]:
            assert "name" in s
            assert "confidence" in s
            assert "reasoning" in s

    @pytest.mark.asyncio
    async def test_caching(self, service):
        """AINAME-03: Second call with same (entity_type, name) returns cached."""
        suggestions = _make_suggestions(3)
        mock_response = _mock_ollama_response(suggestions)

        with patch(
            "server.tools.ldm.services.naming_coherence_service.httpx.AsyncClient"
        ) as MockClient:
            client_instance = _mock_httpx_client(response=mock_response)
            MockClient.return_value = client_instance

            # First call
            result1 = await service.suggest_names("Eldric", "character", [])
            assert result1["status"] == "ok"

            # Second call -- should use cache
            client_instance.post.reset_mock()
            result2 = await service.suggest_names("Eldric", "character", [])
            assert result2["status"] == "cached"
            assert len(result2["suggestions"]) == 3
            client_instance.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_ollama_unavailable(self, service):
        """AINAME-05: ConnectError -> status=unavailable, empty suggestions."""
        with patch(
            "server.tools.ldm.services.naming_coherence_service.httpx.AsyncClient"
        ) as MockClient:
            MockClient.return_value = _mock_httpx_client(
                side_effect=httpx.ConnectError("Connection refused")
            )

            result = await service.suggest_names("Eldric", "character", [])

        assert result["status"] == "unavailable"
        assert result["suggestions"] == []

    @pytest.mark.asyncio
    async def test_prompt_includes_similar_names(self, service):
        """AINAME-02: Prompt contains similar entity names for pattern context."""
        suggestions = _make_suggestions(3)
        mock_response = _mock_ollama_response(suggestions)

        similar = [
            {"name": "Eldara of the North", "strkey": "CHR_ELDARA", "similarity": 0.85, "entity_type": "character"},
        ]

        with patch(
            "server.tools.ldm.services.naming_coherence_service.httpx.AsyncClient"
        ) as MockClient:
            client_instance = _mock_httpx_client(response=mock_response)
            MockClient.return_value = client_instance

            await service.suggest_names("Eldric", "character", similar)

            # Inspect the prompt
            call_args = client_instance.post.call_args
            payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
            prompt = payload["prompt"]
            assert "Eldara of the North" in prompt
            assert "character" in prompt


# =============================================================================
# Status + Singleton Tests
# =============================================================================


class TestGetStatus:
    """Test get_status() returns service info."""

    def test_status_dict(self, service):
        """Returns dict with available, cache_size, model fields."""
        status = service.get_status()
        assert "available" in status
        assert "cache_size" in status
        assert "model" in status
        assert status["model"] == "qwen3:4b"
        assert status["cache_size"] == 0


class TestSingleton:
    """Test get_naming_coherence_service() returns singleton."""

    def test_returns_same_instance(self):
        import server.tools.ldm.services.naming_coherence_service as mod
        mod._naming_service = None
        svc1 = get_naming_coherence_service()
        svc2 = get_naming_coherence_service()
        assert svc1 is svc2
        mod._naming_service = None  # Cleanup
