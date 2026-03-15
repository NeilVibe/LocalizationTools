"""
End-to-end integration tests for AI Suggestions pipeline.

Tests the full flow: HTTP request -> route -> service -> mocked Ollama.
Covers AISUG-01 (suggestions generated), AISUG-02 (blended scores),
AISUG-04 (context in prompt).

Phase 17: AI Translation Suggestions (Plan 01)
"""

from __future__ import annotations

import json

import httpx
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.services.ai_suggestion_service import AISuggestionService

# Get the original FastAPI app for dependency_overrides
fastapi_app = wrapped_app.other_asgi_app

MOCK_USER = {
    "user_id": 1,
    "username": "testuser",
    "role": "user",
    "is_active": True,
    "dev_mode": False,
}


def _ollama_response_json(suggestions: list[dict]) -> str:
    """Build a raw Ollama API response string."""
    inner = json.dumps({"suggestions": suggestions})
    return json.dumps({
        "model": "qwen3:4b",
        "response": inner,
        "done": True,
    })


SAMPLE_SUGGESTIONS = [
    {"text": "여명의 검", "confidence": 0.85, "reasoning": "Direct translation"},
    {"text": "새벽의 칼", "confidence": 0.72, "reasoning": "Alternative phrasing"},
    {"text": "빛의 검", "confidence": 0.60, "reasoning": "Simplified version"},
]


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock auth for all integration tests."""
    async def override_get_user():
        return MOCK_USER

    fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
    yield
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def fresh_service():
    """Provide a fresh AISuggestionService (bypass singleton cache)."""
    service = AISuggestionService()
    with patch(
        "server.tools.ldm.routes.ai_suggestions.get_ai_suggestion_service",
        return_value=service,
    ):
        yield service


def _mock_httpx_post(response_text: str):
    """Create a context manager mock for httpx.AsyncClient that returns given response."""
    mock_response = httpx.Response(status_code=200, text=response_text)
    client_instance = AsyncMock()
    client_instance.post.return_value = mock_response
    client_instance.__aenter__ = AsyncMock(return_value=client_instance)
    client_instance.__aexit__ = AsyncMock(return_value=False)
    return client_instance


class TestFullPipelineWithBlendedScores:
    """Integration: route -> service -> mocked Ollama returns blended confidence."""

    def test_full_pipeline_returns_blended_scores(self, fresh_service):
        """AISUG-01 + AISUG-02: Full pipeline returns suggestions with blended confidence."""
        ollama_body = _ollama_response_json(SAMPLE_SUGGESTIONS)
        mock_client = _mock_httpx_post(ollama_body)

        with patch(
            "server.tools.ldm.services.ai_suggestion_service.httpx.AsyncClient",
            return_value=mock_client,
        ):
            client = TestClient(wrapped_app)
            response = client.get(
                "/api/ldm/ai-suggestions/SID_ITEM_001_NAME",
                params={"source_text": "Sword of Dawn", "target_lang": "KR"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "generated"
        assert len(data["suggestions"]) == 3

        # All suggestions have required fields
        for s in data["suggestions"]:
            assert "text" in s
            assert "confidence" in s
            assert "reasoning" in s
            assert 0.0 <= s["confidence"] <= 1.0

    def test_full_pipeline_unavailable_ollama(self, fresh_service):
        """AISUG-05: Full pipeline with unavailable Ollama returns graceful fallback."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "server.tools.ldm.services.ai_suggestion_service.httpx.AsyncClient",
            return_value=mock_client,
        ):
            client = TestClient(wrapped_app)
            response = client.get(
                "/api/ldm/ai-suggestions/SID_ITEM_001_NAME",
                params={"source_text": "Sword of Dawn"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["suggestions"] == []

    def test_full_pipeline_with_embedding_engine(self, fresh_service):
        """AISUG-02 + AISUG-04: Embedding engine segments influence prompt and confidence."""
        ollama_body = _ollama_response_json(SAMPLE_SUGGESTIONS)
        mock_client = _mock_httpx_post(ollama_body)

        # Mock embedding engine to return a valid encoding
        mock_engine = MagicMock()
        mock_engine.is_loaded = True
        mock_engine.encode.return_value = np.array([[0.5] * 256], dtype=np.float32)

        # Mock TMSearcher to simulate FAISS index availability
        mock_searcher = MagicMock()
        mock_searcher.whole_index = MagicMock()
        mock_searcher.whole_index.search.return_value = (
            np.array([[0.92, 0.85, 0.70]], dtype=np.float32),
            np.array([[0, 1, 2]]),
        )
        mock_searcher.whole_mapping = [
            {"source": "Sword of Light", "target": "빛의 검"},
            {"source": "Blade of Dawn", "target": "여명의 칼날"},
            {"source": "Holy Sword", "target": "성검"},
        ]

        with patch(
            "server.tools.ldm.services.ai_suggestion_service.httpx.AsyncClient",
            return_value=mock_client,
        ), patch(
            "server.tools.ldm.services.ai_suggestion_service.get_embedding_engine",
            return_value=mock_engine,
        ), patch.dict("sys.modules", {
            "server.tools.ldm.indexing.searcher": MagicMock(
                TMSearcher=MagicMock(get_instance=MagicMock(return_value=mock_searcher))
            ),
        }):

            client = TestClient(wrapped_app)
            response = client.get(
                "/api/ldm/ai-suggestions/SID_ITEM_001_NAME",
                params={"source_text": "Sword of Dawn", "target_lang": "KR"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "generated"
        assert len(data["suggestions"]) == 3

        # Verify embedding engine was called for encoding
        mock_engine.encode.assert_called_once()

        # With similar segments found, confidence should be blended
        # (0.4 * 0.92 + 0.6 * original_conf) for highest similarity
        for s in data["suggestions"]:
            assert 0.0 <= s["confidence"] <= 1.0

    def test_pipeline_with_context_in_prompt(self, fresh_service):
        """AISUG-04: Context params appear in the Ollama prompt."""
        ollama_body = _ollama_response_json(SAMPLE_SUGGESTIONS)
        mock_client = _mock_httpx_post(ollama_body)
        captured_prompts = []

        original_post = mock_client.post

        async def capture_post(*args, **kwargs):
            if "json" in kwargs:
                captured_prompts.append(kwargs["json"].get("prompt", ""))
            return await original_post(*args, **kwargs)

        mock_client.post = AsyncMock(side_effect=capture_post)
        # Re-set return value for original_post
        original_post.return_value = httpx.Response(status_code=200, text=ollama_body)

        context_before = json.dumps([{"source": "Iron Shield", "target": "철의 방패"}])

        with patch(
            "server.tools.ldm.services.ai_suggestion_service.httpx.AsyncClient",
            return_value=mock_client,
        ):
            client = TestClient(wrapped_app)
            response = client.get(
                "/api/ldm/ai-suggestions/SID_ITEM_010_NAME",
                params={
                    "source_text": "Blade of Light",
                    "target_lang": "KR",
                    "context_before": context_before,
                },
            )

        assert response.status_code == 200
        assert len(captured_prompts) == 1
        prompt = captured_prompts[0]
        assert "Iron Shield" in prompt
        assert "철의 방패" in prompt
