"""
Tests for AISummaryService -- AI-generated contextual summaries via Ollama/Qwen3.

Phase 13: AI Summaries (Plan 01)
Requirements: AISUM-01, AISUM-02, AISUM-04, AISUM-05
"""

from __future__ import annotations

import json

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from server.tools.ldm.services.ai_summary_service import (
    AISummaryService,
    get_ai_summary_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service():
    """Fresh AISummaryService instance (no singleton)."""
    return AISummaryService()


def _mock_ollama_response(summary: str, entity_type: str = "character") -> httpx.Response:
    """Build a mock httpx.Response with Ollama-style JSON body."""
    inner_json = json.dumps({"summary": summary, "entity_type": entity_type})
    body = json.dumps({
        "model": "qwen3:8b",
        "response": inner_json,
        "done": True,
    })
    return httpx.Response(status_code=200, text=body)


# =============================================================================
# generate_summary() Tests
# =============================================================================


class TestGenerateSummary:
    """Test generate_summary() calls Ollama and parses structured JSON."""

    @pytest.mark.asyncio
    async def test_generate_summary_success(self, service):
        """AISUM-01: Mock httpx POST returning structured JSON -> ai_status='generated'."""
        mock_response = _mock_ollama_response("A legendary warrior who guards the northern gate.")

        with patch("server.tools.ldm.services.ai_summary_service.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_response
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await service.generate_summary(
                string_id="STR_NPC_001",
                entity_name="Varon",
                entity_type="character",
                source_text="The warrior named Varon guards the gate.",
            )

        assert result["ai_status"] == "generated"
        assert result["ai_summary"] == "A legendary warrior who guards the northern gate."

    @pytest.mark.asyncio
    async def test_cache_hit_skips_ollama(self, service):
        """AISUM-02: Second call with same string_id returns cached, no httpx call."""
        mock_response = _mock_ollama_response("Cached summary text.")

        with patch("server.tools.ldm.services.ai_summary_service.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_response
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            # First call
            result1 = await service.generate_summary("STR_001", "Varon", "character", "text")
            assert result1["ai_status"] == "generated"

            # Second call -- should NOT hit httpx
            client_instance.post.reset_mock()
            result2 = await service.generate_summary("STR_001", "Varon", "character", "text")
            assert result2["ai_status"] == "cached"
            assert result2["ai_summary"] == "Cached summary text."
            client_instance.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_ollama_unavailable_returns_badge(self, service):
        """AISUM-04: ConnectError -> ai_status='unavailable', no exception raised."""
        with patch("server.tools.ldm.services.ai_summary_service.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.side_effect = httpx.ConnectError("Connection refused")
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await service.generate_summary("STR_001", "Varon", "character", "text")

        assert result["ai_status"] == "unavailable"
        assert result["ai_summary"] is None

    @pytest.mark.asyncio
    async def test_ollama_timeout_returns_unavailable(self, service):
        """AISUM-04: TimeoutException -> ai_status='unavailable'."""
        with patch("server.tools.ldm.services.ai_summary_service.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.side_effect = httpx.TimeoutException("Timed out")
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await service.generate_summary("STR_001", "Varon", "character", "text")

        assert result["ai_status"] == "unavailable"
        assert result["ai_summary"] is None

    @pytest.mark.asyncio
    async def test_malformed_json_returns_error(self, service):
        """AISUM-05: Valid HTTP but invalid JSON response -> ai_status='error'."""
        bad_response = httpx.Response(
            status_code=200,
            text=json.dumps({"model": "qwen3:8b", "response": "not valid json{{{", "done": True}),
        )

        with patch("server.tools.ldm.services.ai_summary_service.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = bad_response
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await service.generate_summary("STR_001", "Varon", "character", "text")

        assert result["ai_status"] == "error"
        assert result["ai_summary"] is None

    @pytest.mark.asyncio
    async def test_prompt_includes_entity_metadata(self, service):
        """Prompt sent to Ollama contains entity_name, entity_type, source_text."""
        mock_response = _mock_ollama_response("Summary.")

        with patch("server.tools.ldm.services.ai_summary_service.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_response
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            await service.generate_summary("STR_001", "Elder Varon", "character", "He is old.")

            # Inspect the prompt sent
            call_args = client_instance.post.call_args
            payload = call_args[1] if "json" in call_args[1] else call_args[1]
            prompt = payload["json"]["prompt"]
            assert "Elder Varon" in prompt
            assert "character" in prompt
            assert "He is old." in prompt


# =============================================================================
# Cache Management Tests
# =============================================================================


class TestCacheManagement:
    """Test cache clear and status methods."""

    @pytest.mark.asyncio
    async def test_clear_cache(self, service):
        """After generate + clear_cache, next call hits Ollama again."""
        mock_response = _mock_ollama_response("Summary text.")

        with patch("server.tools.ldm.services.ai_summary_service.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_response
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            # Generate and cache
            await service.generate_summary("STR_001", "Varon", "character", "text")
            assert service.get_status()["cache_size"] == 1

            # Clear cache
            service.clear_cache()
            assert service.get_status()["cache_size"] == 0

            # Next call should hit Ollama again (not cached)
            result = await service.generate_summary("STR_001", "Varon", "character", "text")
            assert result["ai_status"] == "generated"
            assert client_instance.post.call_count == 2

    def test_get_status(self, service):
        """get_status returns dict with available, cache_size, model keys."""
        status = service.get_status()
        assert "available" in status
        assert "cache_size" in status
        assert "model" in status
        assert status["cache_size"] == 0
        assert status["model"] == "qwen3:8b"


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingleton:
    """Test get_ai_summary_service() returns singleton."""

    def test_returns_same_instance(self):
        import server.tools.ldm.services.ai_summary_service as mod
        mod._service_instance = None
        svc1 = get_ai_summary_service()
        svc2 = get_ai_summary_service()
        assert svc1 is svc2
        mod._service_instance = None  # Cleanup
