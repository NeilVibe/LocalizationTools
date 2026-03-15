"""
Tests for MapData thumbnail and audio stream API routes.

Phase 11: Image/Audio Pipeline (Plan 02)
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from fastapi.testclient import TestClient

from server.tools.ldm.services.mapdata_service import AudioContext
from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async

# Get FastAPI app from Socket.IO wrapper
fastapi_app = wrapped_app.other_asgi_app


def override_get_user():
    return {"id": 1, "username": "admin", "is_active": True}


@pytest.fixture
def client():
    """TestClient with auth override."""
    fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()


# =============================================================================
# GET /mapdata/thumbnail/{texture_name}
# =============================================================================


class TestThumbnailEndpoint:
    """Test GET /api/ldm/mapdata/thumbnail/{texture_name} endpoint."""

    def test_thumbnail_200(self, client):
        """Valid texture returns 200 with image/png content type."""
        mock_service = MagicMock()
        mock_service._dds_index = {"sword_icon": Path("/mnt/f/textures/sword_icon.dds")}

        mock_converter = MagicMock()
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        mock_converter.convert_dds_to_png.return_value = fake_png

        with (
            patch("server.tools.ldm.routes.mapdata.get_mapdata_service", return_value=mock_service),
            patch("server.tools.ldm.routes.mapdata.get_media_converter", return_value=mock_converter),
        ):
            resp = client.get("/api/ldm/mapdata/thumbnail/sword_icon")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert resp.content == fake_png

    def test_thumbnail_404(self, client):
        """Unknown texture returns 404 with descriptive message."""
        mock_service = MagicMock()
        mock_service._dds_index = {}

        with patch("server.tools.ldm.routes.mapdata.get_mapdata_service", return_value=mock_service):
            resp = client.get("/api/ldm/mapdata/thumbnail/nonexistent_texture")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_thumbnail_500(self, client):
        """Conversion failure returns 500."""
        mock_service = MagicMock()
        mock_service._dds_index = {"broken": Path("/mnt/f/textures/broken.dds")}

        mock_converter = MagicMock()
        mock_converter.convert_dds_to_png.return_value = None

        with (
            patch("server.tools.ldm.routes.mapdata.get_mapdata_service", return_value=mock_service),
            patch("server.tools.ldm.routes.mapdata.get_media_converter", return_value=mock_converter),
        ):
            resp = client.get("/api/ldm/mapdata/thumbnail/broken")

        assert resp.status_code == 500
        assert "failed" in resp.json()["detail"].lower() or "convert" in resp.json()["detail"].lower()

    def test_thumbnail_cache_header(self, client):
        """Response includes Cache-Control header with max-age."""
        mock_service = MagicMock()
        mock_service._dds_index = {"icon": Path("/mnt/f/textures/icon.dds")}

        mock_converter = MagicMock()
        mock_converter.convert_dds_to_png.return_value = b"\x89PNG\r\n\x1a\n"

        with (
            patch("server.tools.ldm.routes.mapdata.get_mapdata_service", return_value=mock_service),
            patch("server.tools.ldm.routes.mapdata.get_media_converter", return_value=mock_converter),
        ):
            resp = client.get("/api/ldm/mapdata/thumbnail/icon")

        assert resp.status_code == 200
        assert "max-age" in resp.headers.get("cache-control", "")

    def test_thumbnail_case_insensitive(self, client):
        """Texture name lookup is case-insensitive."""
        mock_service = MagicMock()
        mock_service._dds_index = {"sword_icon": Path("/mnt/f/textures/sword_icon.dds")}

        mock_converter = MagicMock()
        mock_converter.convert_dds_to_png.return_value = b"\x89PNG\r\n\x1a\n"

        with (
            patch("server.tools.ldm.routes.mapdata.get_mapdata_service", return_value=mock_service),
            patch("server.tools.ldm.routes.mapdata.get_media_converter", return_value=mock_converter),
        ):
            resp = client.get("/api/ldm/mapdata/thumbnail/Sword_Icon")

        assert resp.status_code == 200


# =============================================================================
# GET /mapdata/audio/stream/{string_id}
# =============================================================================


class TestAudioStreamEndpoint:
    """Test GET /api/ldm/mapdata/audio/stream/{string_id} endpoint."""

    def test_audio_stream_200(self, client, tmp_path):
        """Valid audio returns 200 with audio/wav content type."""
        # Create a real WAV file for FileResponse
        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"RIFF" + b"\x00" * 100)

        mock_service = MagicMock()
        mock_service.get_audio_context.return_value = AudioContext(
            event_name="vo_test", wem_path=r"F:\audio\test.wem",
            script_kr="", script_eng="", duration_seconds=1.0,
        )

        mock_converter = MagicMock()
        mock_converter.convert_wem_to_wav.return_value = wav_file

        with (
            patch("server.tools.ldm.routes.mapdata.get_mapdata_service", return_value=mock_service),
            patch("server.tools.ldm.routes.mapdata.get_media_converter", return_value=mock_converter),
        ):
            resp = client.get("/api/ldm/mapdata/audio/stream/STR_001")

        assert resp.status_code == 200
        assert "audio/wav" in resp.headers["content-type"]

    def test_audio_stream_404(self, client):
        """Unknown string_id returns 404."""
        mock_service = MagicMock()
        mock_service.get_audio_context.return_value = None

        with patch("server.tools.ldm.routes.mapdata.get_mapdata_service", return_value=mock_service):
            resp = client.get("/api/ldm/mapdata/audio/stream/UNKNOWN_ID")

        assert resp.status_code == 404
        assert "no audio" in resp.json()["detail"].lower()

    def test_audio_stream_500(self, client):
        """Conversion failure returns 500."""
        mock_service = MagicMock()
        mock_service.get_audio_context.return_value = AudioContext(
            event_name="vo_broken", wem_path=r"F:\audio\broken.wem",
            script_kr="", script_eng="", duration_seconds=None,
        )

        mock_converter = MagicMock()
        mock_converter.convert_wem_to_wav.return_value = None

        with (
            patch("server.tools.ldm.routes.mapdata.get_mapdata_service", return_value=mock_service),
            patch("server.tools.ldm.routes.mapdata.get_media_converter", return_value=mock_converter),
        ):
            resp = client.get("/api/ldm/mapdata/audio/stream/STR_BROKEN")

        assert resp.status_code == 500
        assert "failed" in resp.json()["detail"].lower() or "conversion" in resp.json()["detail"].lower()
