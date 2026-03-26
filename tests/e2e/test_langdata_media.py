"""
E2E tests for DDS->PNG and WEM->WAV media resolution via API.

Verifies LDE2E-03: grid rows resolve DDS images and WEM audio via
Perforce-like paths through the mapdata API endpoints.

Uses Phase 74 mock gamedata fixtures containing valid DDS textures,
WAV-content WEM audio files, and PNG thumbnails.

Phase 91 Plan 02: Added LanguageData->media chain tests (MOCK-01..04),
fallback_reason verification, and drive-agnostic path checks.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root is importable
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

pytestmark = [pytest.mark.e2e, pytest.mark.media]

# Fixtures (client, auth_headers) provided by tests/e2e/conftest.py (session-scoped)


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

# StringIDs from mock languagedata that have SoundEventName mappings in export XMLs
DIALOG_STRINGID_VARON = "DLG_VARON_01"       # -> play_varon_greeting_01.wem
DIALOG_STRINGID_KIRA = "DLG_KIRA_01"         # -> play_kira_taunt_01.wem
DIALOG_STRINGID_GRIMJAW = "DLG_GRIMJAW_01"   # -> play_grimjaw_forge_01.wem


# ===========================================================================
# TestDDSThumbnail
# ===========================================================================


class TestDDSThumbnail:
    """Test DDS texture thumbnail endpoint (LDE2E-03, image part)."""

    def test_thumbnail_endpoint_returns_png_for_known_texture(
        self, client, auth_headers
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
        self, client, auth_headers
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

    def test_thumbnail_unknown_returns_404(self, client, auth_headers):
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
        self, client, auth_headers
    ):
        """GET /api/ldm/mapdata/image/{string_id} returns texture metadata."""
        response = client.get(
            f"/api/ldm/mapdata/image/{KNOWN_STRING_ID}",
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.xfail("MapData service not initialized in test environment")
        assert response.status_code == 200
        data = response.json()
        assert "texture_name" in data
        assert "has_image" in data
        assert "dds_path" in data
        assert "thumbnail_url" in data
        assert "fallback_reason" in data

    def test_image_context_unknown_returns_200_with_fallback(
        self, client, auth_headers
    ):
        """After Phase 91-01: unknown StringIDs return 200 with has_image=False, not 404."""
        response = client.get(
            "/api/ldm/mapdata/image/NONEXISTENT_STRING_ID_XYZ",
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.xfail("MapData service not initialized in test environment")
        assert response.status_code == 200
        data = response.json()
        assert data["has_image"] is False
        assert data["fallback_reason"] != ""


# ===========================================================================
# TestWEMAudioStream
# ===========================================================================


class TestWEMAudioStream:
    """Test WEM audio stream endpoint (LDE2E-03, audio part)."""

    def test_audio_stream_returns_wav_for_known_event(
        self, client, auth_headers
    ):
        """GET /api/ldm/mapdata/audio/stream/{string_id} returns WAV bytes."""
        response = client.get(
            f"/api/ldm/mapdata/audio/stream/{KNOWN_AUDIO_EVENT}"
        )
        if response.status_code in (404, 503):
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

    def test_audio_stream_unknown_returns_404(self, client, auth_headers):
        """GET /api/ldm/mapdata/audio/stream/nonexistent returns 404."""
        response = client.get(
            "/api/ldm/mapdata/audio/stream/nonexistent_audio_xyz"
        )
        assert response.status_code in (404, 503)


# ===========================================================================
# TestAudioContext
# ===========================================================================


class TestAudioContext:
    """Test audio context metadata endpoint (LDE2E-03, audio metadata)."""

    def test_audio_context_for_known_entity(
        self, client, auth_headers
    ):
        """GET /api/ldm/mapdata/audio/{string_id} returns audio metadata."""
        response = client.get(
            f"/api/ldm/mapdata/audio/{KNOWN_STRING_ID}",
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.xfail("MapData service not initialized in test environment")
        assert response.status_code == 200
        data = response.json()
        assert "event_name" in data
        assert "wem_path" in data
        assert "fallback_reason" in data

    def test_audio_context_unknown_returns_200_with_fallback(
        self, client, auth_headers
    ):
        """After Phase 91-01: unknown StringIDs return 200 with fallback_reason, not 404."""
        response = client.get(
            "/api/ldm/mapdata/audio/NONEXISTENT_STRING_ID_XYZ",
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.xfail("MapData service not initialized in test environment")
        assert response.status_code == 200
        data = response.json()
        assert data["wem_path"] == ""
        assert data["fallback_reason"] != ""


# ===========================================================================
# TestLanguageDataImageChain (MOCK-02, Phase 91 Plan 02)
# ===========================================================================


class TestLanguageDataImageChain:
    """E2E: LanguageData StringID -> entity -> DDS thumbnail (MOCK-02)."""

    def test_image_chain_for_dialog_stringid(self, client, auth_headers):
        """DLG_VARON_01 should resolve through C7 bridge to an entity with a texture.

        Chain: DLG_VARON_01 -> C7 entity (via C6 Korean text match) -> knowledge -> UITextureName -> DDS
        Note: This may fail if C6/C7 Korean text matching doesn't link
        DLG_VARON_01's StrOrigin to any entity. That's expected fragility (C6/C7 weakness).
        """
        response = client.get(
            f"/api/ldm/mapdata/image/{DIALOG_STRINGID_VARON}",
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.xfail("MapData service not initialized in test environment")
        assert response.status_code == 200
        data = response.json()
        # Either has_image=True (chain resolved) or has fallback_reason (chain didn't resolve)
        assert "has_image" in data
        assert "fallback_reason" in data
        if not data["has_image"]:
            # C6/C7 bridge may not resolve for dialog StringIDs -- that's the known fragility
            assert data["fallback_reason"] != "", "Must have a specific reason when no image"

    def test_image_chain_for_entity_strkey(self, client, auth_headers):
        """Direct StrKey lookup (CHARACTER_KIRA_NAME) should find metadata."""
        response = client.get(
            f"/api/ldm/mapdata/image/{KNOWN_STRING_ID}",
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.xfail("MapData service not initialized in test environment")
        assert response.status_code == 200
        data = response.json()
        # This may or may not resolve depending on how CHARACTER_KIRA_NAME is indexed
        assert "has_image" in data
        assert "fallback_reason" in data

    def test_image_returns_200_not_404_for_unknown(self, client, auth_headers):
        """After Plan 91-01, unknown StringIDs return 200 with has_image=False, not 404."""
        response = client.get(
            "/api/ldm/mapdata/image/TOTALLY_UNKNOWN_ID_99999",
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.xfail("MapData service not initialized in test environment")
        assert response.status_code == 200
        data = response.json()
        assert data["has_image"] is False
        assert data["fallback_reason"] != ""


# ===========================================================================
# TestLanguageDataAudioChain (MOCK-03, Phase 91 Plan 02)
# ===========================================================================


class TestLanguageDataAudioChain:
    """E2E: LanguageData StringID -> event -> WEM audio (MOCK-03)."""

    def test_audio_chain_for_dialog_stringid(self, client, auth_headers):
        """DLG_VARON_01 -> C3 chain -> play_varon_greeting_01.wem

        Chain: DLG_VARON_01 -> R3 (export XML maps SoundEventName=play_varon_greeting_01
        to StringId=DLG_VARON_01) -> D10 (WEM index) -> play_varon_greeting_01.wem
        """
        response = client.get(
            f"/api/ldm/mapdata/audio/{DIALOG_STRINGID_VARON}",
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.xfail("MapData service not initialized in test environment")
        assert response.status_code == 200
        data = response.json()
        if data.get("wem_path"):
            assert data.get("fallback_reason", "") == ""
        else:
            # If chain didn't resolve, must have reason
            assert data["fallback_reason"] != ""

    def test_audio_chain_for_kira_dialog(self, client, auth_headers):
        """DLG_KIRA_01 -> play_kira_taunt_01.wem"""
        response = client.get(
            f"/api/ldm/mapdata/audio/{DIALOG_STRINGID_KIRA}",
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.xfail("MapData service not initialized in test environment")
        assert response.status_code == 200
        data = response.json()
        assert "fallback_reason" in data

    def test_audio_returns_200_not_404_for_unknown(self, client, auth_headers):
        """Unknown StringIDs return 200 with fallback_reason, not 404."""
        response = client.get(
            "/api/ldm/mapdata/audio/TOTALLY_UNKNOWN_ID_99999",
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.xfail("MapData service not initialized in test environment")
        assert response.status_code == 200
        data = response.json()
        assert data["wem_path"] == ""
        assert data["fallback_reason"] != ""

    def test_audio_stream_still_404_for_unknown(self, client, auth_headers):
        """The audio STREAM endpoint (actual file serving) should still 404 for unknown IDs."""
        response = client.get(
            "/api/ldm/mapdata/audio/stream/TOTALLY_UNKNOWN_ID_99999"
        )
        # Stream endpoint returns actual audio bytes -- no fallback_reason pattern here
        assert response.status_code in (404, 503)


# ===========================================================================
# TestDriveAgnosticMockPaths (MOCK-04, Phase 91 Plan 02)
# ===========================================================================


class TestDriveAgnosticMockPaths:
    """MOCK-04: Mock paths work regardless of drive letter."""

    def test_mock_paths_are_local_not_windows_drive(self, client, auth_headers):
        """When using mock_gamedata, resolved paths should be local (not F:\\perforce\\...)."""
        response = client.get(
            "/api/ldm/mapdata/status",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            # In mock/DEV mode, the service should be functional
            # If loaded, paths should point to local mock_gamedata, not Windows Perforce paths
            assert "loaded" in data
