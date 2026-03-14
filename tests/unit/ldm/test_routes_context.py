"""
Tests for Context API routes -- entity context endpoints.

Phase 5.1: Contextual Intelligence & QA Engine (Plan 03)
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from server.tools.ldm.services.context_service import (
    CharacterContext,
    LocationContext,
    EntityContext,
)
from server.tools.ldm.services.glossary_service import (
    DetectedEntity,
    EntityInfo,
)
from server.tools.ldm.services.mapdata_service import ImageContext, AudioContext
from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async

# Get FastAPI app from Socket.IO wrapper
fastapi_app = wrapped_app.other_asgi_app


# =============================================================================
# Fixtures
# =============================================================================


CHAR_ENTITY = EntityInfo(
    type="character", name="Varon", strkey="STR_CHAR_VARON",
    knowledge_key="KNOW_CHAR_VARON", source_file="char.xml",
)

SAMPLE_IMAGE = ImageContext(
    texture_name="tex_varon", dds_path="/img/varon.dds",
    thumbnail_url="/thumb/varon.png", has_image=True,
)

SAMPLE_AUDIO = AudioContext(
    event_name="vo_varon", wem_path="/audio/varon.wem",
    script_kr="안녕", script_eng="Hello", duration_seconds=1.5,
)

SAMPLE_ENTITY_CONTEXT = EntityContext(
    entities=[
        CharacterContext(
            name="Varon", entity_type="character", strkey="STR_CHAR_VARON",
            knowledge_key="KNOW_CHAR_VARON", source_file="char.xml",
            image=SAMPLE_IMAGE, audio=SAMPLE_AUDIO,
        )
    ],
    detected_in_text=[
        DetectedEntity(term="Varon", start=0, end=5, entity=CHAR_ENTITY)
    ],
    string_id_context={"image": SAMPLE_IMAGE.to_dict(), "audio": SAMPLE_AUDIO.to_dict()},
)

EMPTY_ENTITY_CONTEXT = EntityContext()


def override_get_user():
    return {"id": 1, "username": "admin", "is_active": True}


@pytest.fixture
def client():
    """TestClient with auth override and mocked context service."""
    fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()


# =============================================================================
# GET /context/{string_id}
# =============================================================================


class TestGetContextByStringId:
    """Test GET /api/ldm/context/{string_id} endpoint."""

    def test_returns_entity_context_with_media(self, client):
        mock_svc = MagicMock()
        mock_svc.resolve_context_for_row.return_value = SAMPLE_ENTITY_CONTEXT

        with patch("server.tools.ldm.routes.context.get_context_service", return_value=mock_svc):
            resp = client.get("/api/ldm/context/STR_001", params={"source_text": "Varon speaks"})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entities"]) == 1
        assert data["entities"][0]["name"] == "Varon"
        assert data["string_id_context"]["image"] is not None

    def test_returns_empty_when_service_not_loaded(self, client):
        mock_svc = MagicMock()
        mock_svc.resolve_context_for_row.return_value = EMPTY_ENTITY_CONTEXT

        with patch("server.tools.ldm.routes.context.get_context_service", return_value=mock_svc):
            resp = client.get("/api/ldm/context/UNKNOWN_ID")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entities"]) == 0


# =============================================================================
# POST /context/detect
# =============================================================================


class TestPostContextDetect:
    """Test POST /api/ldm/context/detect endpoint."""

    def test_returns_detected_entities_from_text(self, client):
        mock_svc = MagicMock()
        mock_svc.resolve_context.return_value = SAMPLE_ENTITY_CONTEXT

        with patch("server.tools.ldm.routes.context.get_context_service", return_value=mock_svc):
            resp = client.post("/api/ldm/context/detect", json={"text": "Varon enters the castle"})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entities"]) == 1
        assert data["detected_in_text"][0]["term"] == "Varon"


# =============================================================================
# GET /context/status
# =============================================================================


class TestGetContextStatus:
    """Test GET /api/ldm/context/status endpoint."""

    def test_returns_combined_service_status(self, client):
        mock_svc = MagicMock()
        mock_svc.get_status.return_value = {
            "glossary": {"loaded": True, "entity_count": 50},
            "mapdata": {"loaded": True, "image_count": 100},
        }

        with patch("server.tools.ldm.routes.context.get_context_service", return_value=mock_svc):
            resp = client.get("/api/ldm/context/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["glossary"]["loaded"] is True
        assert data["mapdata"]["loaded"] is True
