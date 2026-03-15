"""
Tests for AI Suggestions REST endpoint.

Phase 17: AI Translation Suggestions (Plan 01)
Requirements: AISUG-01, AISUG-02, AISUG-04, AISUG-05
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient

from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async

# Get the original FastAPI app for dependency_overrides
fastapi_app = wrapped_app.other_asgi_app

MOCK_USER = {
    "user_id": 1,
    "username": "testuser",
    "role": "user",
    "is_active": True,
    "dev_mode": False,
}


@pytest.fixture
def mock_auth():
    """Mock auth for route tests."""
    async def override_get_user():
        return MOCK_USER

    fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
    yield
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def mock_service():
    """Mock AISuggestionService."""
    service = MagicMock()
    service.generate_suggestions = AsyncMock(return_value={
        "suggestions": [
            {"text": "번역 1", "confidence": 0.85, "reasoning": "Best match"},
            {"text": "번역 2", "confidence": 0.72, "reasoning": "Alternative"},
            {"text": "번역 3", "confidence": 0.60, "reasoning": "Literal"},
        ],
        "status": "generated",
    })
    service.get_status.return_value = {
        "available": True,
        "cache_size": 5,
        "model": "qwen3:4b",
    }
    return service


class TestAISuggestionsEndpoint:
    """Test GET /api/ldm/ai-suggestions/{string_id}."""

    def test_returns_suggestions(self, mock_auth, mock_service):
        """AISUG-01: Returns 200 with suggestions array."""
        with patch(
            "server.tools.ldm.routes.ai_suggestions.get_ai_suggestion_service",
            return_value=mock_service,
        ):
            client = TestClient(wrapped_app)
            response = client.get(
                "/api/ldm/ai-suggestions/SID_ITEM_001_NAME",
                params={"source_text": "Sword of Dawn", "target_lang": "KR"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) == 3
        assert data["status"] == "generated"

    def test_missing_source_text_returns_422(self, mock_auth, mock_service):
        """Missing required source_text query param returns 422."""
        with patch(
            "server.tools.ldm.routes.ai_suggestions.get_ai_suggestion_service",
            return_value=mock_service,
        ):
            client = TestClient(wrapped_app)
            response = client.get("/api/ldm/ai-suggestions/SID_001")

        assert response.status_code == 422

    def test_ollama_unavailable_returns_200(self, mock_auth):
        """AISUG-05: Ollama unavailable returns 200 with status=unavailable."""
        unavailable_service = MagicMock()
        unavailable_service.generate_suggestions = AsyncMock(return_value={
            "suggestions": [],
            "status": "unavailable",
        })

        with patch(
            "server.tools.ldm.routes.ai_suggestions.get_ai_suggestion_service",
            return_value=unavailable_service,
        ):
            client = TestClient(wrapped_app)
            response = client.get(
                "/api/ldm/ai-suggestions/SID_001",
                params={"source_text": "test"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "unavailable"

    def test_status_endpoint(self, mock_auth, mock_service):
        """GET /ai-suggestions/status returns service health."""
        with patch(
            "server.tools.ldm.routes.ai_suggestions.get_ai_suggestion_service",
            return_value=mock_service,
        ):
            client = TestClient(wrapped_app)
            response = client.get("/api/ldm/ai-suggestions/status")

        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        assert "cache_size" in data
        assert "model" in data

    def test_context_passed_to_service(self, mock_auth, mock_service):
        """AISUG-04: context_before/after params are passed through to service."""
        import json

        context_before = json.dumps([{"source": "Shield", "target": "방패"}])

        with patch(
            "server.tools.ldm.routes.ai_suggestions.get_ai_suggestion_service",
            return_value=mock_service,
        ):
            client = TestClient(wrapped_app)
            response = client.get(
                "/api/ldm/ai-suggestions/SID_ITEM_001_NAME",
                params={
                    "source_text": "Sword",
                    "target_lang": "KR",
                    "context_before": context_before,
                },
            )

        assert response.status_code == 200
        # Verify service was called with surrounding_context
        call_kwargs = mock_service.generate_suggestions.call_args
        surrounding = call_kwargs[1].get("surrounding_context") or call_kwargs[0][4]
        assert len(surrounding) >= 1
