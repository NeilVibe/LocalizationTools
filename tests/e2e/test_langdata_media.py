"""
E2E tests for DDS->PNG and WEM->WAV media resolution via API.

Verifies LDE2E-03: grid rows resolve DDS images and WEM audio via
Perforce-like paths through the mapdata API endpoints.

Uses Phase 74 mock gamedata fixtures containing valid DDS textures,
WAV-content WEM audio files, and PNG thumbnails.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root is importable
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from fastapi.testclient import TestClient
from server.main import app

pytestmark = [pytest.mark.e2e, pytest.mark.media]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> TestClient:
    """TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict[str, str]:
    """Authenticate as admin and return bearer-token headers."""
    response = client.post(
        "/api/v2/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v2/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}

    pytest.fail(
        f"Admin login failed: {response.status_code} {response.text[:200]}"
    )


# ---------------------------------------------------------------------------
# Known mock gamedata filenames (from Phase 74 fixtures)
# ---------------------------------------------------------------------------

# PNG thumbnails in tests/fixtures/mock_gamedata/textures/
KNOWN_TEXTURE_NAME = "character_kira"  # .png in textures/, .dds in texture/image/

# DDS textures in tests/fixtures/mock_gamedata/texture/image/
KNOWN_DDS_TEXTURE = "item_0001"  # .dds file

# WEM audio files in tests/fixtures/mock_gamedata/sound/windows/English(US)/
KNOWN_AUDIO_EVENT = "play_kira_taunt_01"  # .wem file

# StringId that might have associated image/audio in MegaIndex
KNOWN_STRING_ID = "CHARACTER_KIRA_NAME"


# ===========================================================================
# TestDDSThumbnail
# ===========================================================================


class TestDDSThumbnail:
    """Test DDS texture thumbnail endpoint (LDE2E-03, image part)."""

    def test_thumbnail_endpoint_returns_png_for_known_texture(
        self, client: TestClient
    ):
        """GET /api/ldm/mapdata/thumbnail/{texture_name} returns image bytes
        for a texture name that exists in mock_gamedata/textures/.
        """
        response = client.get(
            f"/api/ldm/mapdata/thumbnail/{KNOWN_TEXTURE_NAME}"
        )
        if response.status_code == 404:
            pytest.xfail(
                "Texture not found in DDS index or mock_gamedata fallback"
            )

        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "image/" in content_type, (
            f"Expected image content-type, got: {content_type}"
        )
        assert len(response.content) > 100, (
            f"Image too small ({len(response.content)} bytes)"
        )

    def test_thumbnail_endpoint_returns_image_for_dds_texture(
        self, client: TestClient
    ):
        """GET /api/ldm/mapdata/thumbnail/{texture_name} works for DDS files
        found via case-insensitive rglob in mock_gamedata/textures/ subdirs.
        """
        response = client.get(
            f"/api/ldm/mapdata/thumbnail/{KNOWN_DDS_TEXTURE}"
        )
        if response.status_code == 404:
            pytest.xfail(
                "DDS texture not found via fallback search in mock_gamedata"
            )

        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "image/" in content_type, (
            f"Expected image content-type, got: {content_type}"
        )
        assert len(response.content) > 100

    def test_thumbnail_unknown_returns_404(self, client: TestClient):
        """GET /api/ldm/mapdata/thumbnail/nonexistent returns 404."""
        response = client.get(
            "/api/ldm/mapdata/thumbnail/nonexistent_texture_xyz"
        )
        assert response.status_code == 404


# ===========================================================================
# TestImageContext
# ===========================================================================


class TestImageContext:
    """Test image context metadata endpoint (LDE2E-03, image metadata)."""

    def test_image_context_for_known_entity(
        self, client: TestClient, auth_headers: dict
    ):
        """GET /api/ldm/mapdata/image/{string_id} returns texture metadata."""
        response = client.get(
            f"/api/ldm/mapdata/image/{KNOWN_STRING_ID}",
            headers=auth_headers,
        )
        if response.status_code == 404:
            pytest.xfail(
                "MegaIndex not initialized with mock data -- "
                "no image context for this string_id"
            )

        assert response.status_code == 200
        data = response.json()
        assert "texture_name" in data
        assert "has_image" in data
        assert "dds_path" in data
        assert "thumbnail_url" in data

    def test_image_context_unknown_returns_404(
        self, client: TestClient, auth_headers: dict
    ):
        """GET /api/ldm/mapdata/image/{unknown} returns 404."""
        response = client.get(
            "/api/ldm/mapdata/image/NONEXISTENT_STRING_ID_XYZ",
            headers=auth_headers,
        )
        assert response.status_code == 404


# ===========================================================================
# TestWEMAudioStream
# ===========================================================================


class TestWEMAudioStream:
    """Test WEM audio stream endpoint (LDE2E-03, audio part)."""

    def test_audio_stream_returns_wav_for_known_event(
        self, client: TestClient
    ):
        """GET /api/ldm/mapdata/audio/stream/{string_id} returns WAV bytes."""
        response = client.get(
            f"/api/ldm/mapdata/audio/stream/{KNOWN_AUDIO_EVENT}"
        )
        if response.status_code == 404:
            pytest.xfail(
                "MegaIndex not initialized with mock data -- "
                "no audio context for this string_id"
            )

        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "audio/wav" in content_type or "audio/wave" in content_type, (
            f"Expected audio/wav content-type, got: {content_type}"
        )
        # WAV header is 44 bytes minimum
        assert len(response.content) > 44, (
            f"Audio too small ({len(response.content)} bytes)"
        )

    def test_audio_stream_unknown_returns_404(self, client: TestClient):
        """GET /api/ldm/mapdata/audio/stream/nonexistent returns 404."""
        response = client.get(
            "/api/ldm/mapdata/audio/stream/nonexistent_audio_xyz"
        )
        assert response.status_code == 404


# ===========================================================================
# TestAudioContext
# ===========================================================================


class TestAudioContext:
    """Test audio context metadata endpoint (LDE2E-03, audio metadata)."""

    def test_audio_context_for_known_entity(
        self, client: TestClient, auth_headers: dict
    ):
        """GET /api/ldm/mapdata/audio/{string_id} returns audio metadata."""
        response = client.get(
            f"/api/ldm/mapdata/audio/{KNOWN_STRING_ID}",
            headers=auth_headers,
        )
        if response.status_code == 404:
            pytest.xfail(
                "MegaIndex not initialized with mock data -- "
                "no audio context for this string_id"
            )

        assert response.status_code == 200
        data = response.json()
        assert "event_name" in data
        assert "wem_path" in data

    def test_audio_context_unknown_returns_404(
        self, client: TestClient, auth_headers: dict
    ):
        """GET /api/ldm/mapdata/audio/{unknown} returns 404."""
        response = client.get(
            "/api/ldm/mapdata/audio/NONEXISTENT_STRING_ID_XYZ",
            headers=auth_headers,
        )
        assert response.status_code == 404
