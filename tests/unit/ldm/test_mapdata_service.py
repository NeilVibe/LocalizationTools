"""
Unit tests for MapDataService - StrKey-to-image/audio context lookups.

Tests use mock data (no actual file access). Pre-populates indexes
manually then tests get_image_context / get_audio_context lookups.

Updated for MegaIndex-based MapDataService (Phase 45+).
Covers C7 bridge: StringID -> entity StrKey -> C1 image path (Phase 50).
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from server.tools.ldm.services.mapdata_service import (
    MapDataService,
    ImageContext,
    AudioContext,
    KnowledgeLookup,
)
from server.tools.ldm.services.mega_index_schemas import KnowledgeEntry


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def service():
    """Create a MapDataService with manually populated indexes."""
    svc = MapDataService()

    # Manually populate image index (simulates C1 strkey_to_image_path)
    img = ImageContext(
        texture_name="UI_Icon_Sword_01",
        dds_path=r"F:\perforce\common\mainline\commonresource\ui\texture\image\UI_Icon_Sword_01.dds",
        thumbnail_url="/api/ldm/mapdata/thumbnail/UI_Icon_Sword_01",
        has_image=True,
    )
    svc._strkey_to_image["item_sword_01"] = img
    svc._strkey_to_image["STR_ITEM_SWORD_01"] = img  # StringID alias
    svc._strkey_to_image["knowledge_sword_01"] = img  # KnowledgeKey alias

    # Manually populate audio index
    audio = AudioContext(
        event_name="VO_NPC_Greeting_01",
        wem_path=r"F:\perforce\cd\mainline\resource\sound\windows\English(US)\VO_NPC_Greeting_01.wem",
        script_kr="안녕하세요, 여행자여.",
        script_eng="Hello, traveler.",
        duration_seconds=2.5,
    )
    svc._strkey_to_audio["npc_greeting_01"] = audio
    svc._strkey_to_audio["STR_NPC_GREETING_01"] = audio  # StringID alias

    svc._loaded = True
    svc._branch = "mainline"
    svc._drive = "F"

    return svc


@pytest.fixture
def mock_mega_index():
    """Create a mock MegaIndex with C7 bridge data."""
    mega = MagicMock()

    # C7: StringID -> (entity_type, strkey)
    mega.stringid_to_entity = {
        "CHAR_VARON_NAME": ("character", "CharInfo_Varon"),
    }

    # D1: knowledge_by_strkey
    mega.knowledge_by_strkey = {
        "CharInfo_Varon": KnowledgeEntry(
            strkey="CharInfo_Varon",
            name="바론",
            desc="전사",
            ui_texture_name="char_varon",
            group_key="character_group",
            source_file="KnowledgeInfo_Character.xml",
        ),
        "Knowledge_Region_Calpheon": KnowledgeEntry(
            strkey="Knowledge_Region_Calpheon",
            name="칼페온",
            desc="서쪽 도시",
            ui_texture_name="region_calpheon",
            group_key="region_group",
            source_file="KnowledgeInfo_Region.xml",
        ),
    }

    # C1: strkey_to_image_path
    mega.strkey_to_image_path = {
        "CharInfo_Varon": Path("/mock/textures/char_varon.dds"),
        "Knowledge_Region_Calpheon": Path("/mock/textures/region_calpheon.dds"),
    }

    # C3: stringid_to_audio_path (legacy)
    mega.stringid_to_audio_path = {
        "NPC_GREETING_01_NAME": Path("/mock/audio/VO_NPC_Greeting_01.wem"),
    }
    # C3 language-aware (new)
    mega.get_audio_path_by_stringid_for_lang.side_effect = lambda sid, lang="eng": (
        mega.stringid_to_audio_path.get(sid)
    )

    # R3: stringid_to_event
    mega.stringid_to_event = {
        "NPC_GREETING_01_NAME": "VO_NPC_Greeting_01",
    }

    # C4/C5: event_to_script
    mega.event_to_script_kr = {
        "vo_npc_greeting_01": "안녕하세요, 여행자여.",
    }
    mega.event_to_script_eng = {
        "vo_npc_greeting_01": "Hello, traveler.",
    }

    # C2: strkey_to_audio_path
    mega.strkey_to_audio_path = {}

    mega._built = True
    return mega


# =============================================================================
# Image Context Tests
# =============================================================================

class TestGetImageContext:
    def test_returns_image_context_for_known_strkey(self, service):
        result = service.get_image_context("item_sword_01")
        assert result is not None
        assert result.texture_name == "UI_Icon_Sword_01"
        assert result.has_image is True
        assert "UI_Icon_Sword_01.dds" in result.dds_path

    def test_returns_fallback_for_unknown_strkey(self, service):
        result = service.get_image_context("unknown_key_xyz")
        assert result is not None
        assert result.has_image is False
        assert result.fallback_reason != ""
        assert "Entity not found" in result.fallback_reason

    def test_multi_key_lookup_stringid(self, service):
        """StringID alias resolves to same ImageContext as StrKey."""
        result_strkey = service.get_image_context("item_sword_01")
        result_stringid = service.get_image_context("STR_ITEM_SWORD_01")
        assert result_strkey is not None
        assert result_stringid is not None
        assert result_strkey.texture_name == result_stringid.texture_name

    def test_multi_key_lookup_knowledge_key(self, service):
        """KnowledgeKey alias resolves to same ImageContext."""
        result = service.get_image_context("knowledge_sword_01")
        assert result is not None
        assert result.texture_name == "UI_Icon_Sword_01"


# =============================================================================
# C7 Bridge Tests (Phase 50 - StringID -> Entity -> Image)
# =============================================================================

class TestGetImageContextC7Bridge:
    """Test C7 bridge: StringID -> entity StrKey -> C1 image path."""

    def test_get_image_context_via_stringid(self, mock_mega_index):
        """CHAR_VARON_NAME -> C7 -> CharInfo_Varon -> C1 -> image."""
        svc = MapDataService()
        svc._loaded = True

        with patch(
            "server.tools.ldm.services.mega_index.get_mega_index",
            return_value=mock_mega_index,
        ):
            result = svc.get_image_context("CHAR_VARON_NAME")

        assert result is not None
        assert result.has_image is True
        assert result.dds_path == "/mock/textures/char_varon.dds"
        assert result.texture_name == "char_varon"

    def test_get_image_context_unknown_stringid(self, mock_mega_index):
        """UNKNOWN_SID returns fallback ImageContext with reason when no C7 mapping."""
        svc = MapDataService()
        svc._loaded = True

        with patch(
            "server.tools.ldm.services.mega_index.get_mega_index",
            return_value=mock_mega_index,
        ):
            result = svc.get_image_context("UNKNOWN_SID")

        assert result is not None
        assert result.has_image is False
        assert result.fallback_reason != ""
        assert "Entity not found" in result.fallback_reason

    def test_get_image_context_direct_strkey_still_works(self, mock_mega_index):
        """Knowledge_Region_Calpheon via direct StrKey match (existing behavior)."""
        svc = MapDataService()
        svc._loaded = True
        # Pre-populate the strkey_to_image cache (as initialize() would)
        svc._strkey_to_image["Knowledge_Region_Calpheon"] = ImageContext(
            texture_name="region_calpheon",
            dds_path="/mock/textures/region_calpheon.dds",
            thumbnail_url="/api/ldm/mapdata/thumbnail/region_calpheon",
            has_image=True,
        )

        result = svc.get_image_context("Knowledge_Region_Calpheon")
        assert result is not None
        assert result.texture_name == "region_calpheon"
        assert result.has_image is True

    def test_c7_bridge_caches_result(self, mock_mega_index):
        """C7 lookup result is cached for future O(1) access."""
        svc = MapDataService()
        svc._loaded = True

        with patch(
            "server.tools.ldm.services.mega_index.get_mega_index",
            return_value=mock_mega_index,
        ):
            result1 = svc.get_image_context("CHAR_VARON_NAME")

        # Second lookup should be from cache (no mock needed)
        result2 = svc.get_image_context("CHAR_VARON_NAME")
        assert result1 is not None
        assert result2 is not None
        assert result1.dds_path == result2.dds_path


# =============================================================================
# Audio Context Tests
# =============================================================================

class TestGetAudioContext:
    def test_returns_audio_context_for_known_strkey(self, service):
        result = service.get_audio_context("npc_greeting_01")
        assert result is not None
        assert result.event_name == "VO_NPC_Greeting_01"
        assert result.script_kr == "안녕하세요, 여행자여."
        assert result.script_eng == "Hello, traveler."
        assert result.duration_seconds == 2.5

    def test_returns_fallback_for_unknown_strkey(self, service):
        result = service.get_audio_context("unknown_audio_xyz")
        assert result is not None
        assert result.wem_path == ""
        assert result.fallback_reason != ""
        assert "No audio event" in result.fallback_reason

    def test_multi_key_lookup_stringid(self, service):
        """StringID alias resolves to same AudioContext."""
        result_strkey = service.get_audio_context("npc_greeting_01")
        result_stringid = service.get_audio_context("STR_NPC_GREETING_01")
        assert result_strkey is not None
        assert result_stringid is not None
        assert result_strkey.event_name == result_stringid.event_name

    def test_get_audio_context_via_mega_c3(self, mock_mega_index):
        """NPC_GREETING_01_NAME -> C3 -> WEM path, R3 -> event, C4/C5 -> scripts."""
        svc = MapDataService()
        svc._loaded = True

        with patch(
            "server.tools.ldm.services.mega_index.get_mega_index",
            return_value=mock_mega_index,
        ):
            result = svc.get_audio_context("NPC_GREETING_01_NAME")

        assert result is not None
        assert result.event_name == "VO_NPC_Greeting_01"
        assert result.wem_path == "/mock/audio/VO_NPC_Greeting_01.wem"
        assert result.script_kr == "안녕하세요, 여행자여."
        assert result.script_eng == "Hello, traveler."


# =============================================================================
# Service Status Tests
# =============================================================================

# =============================================================================
# Fallback Reason Tests (Phase 91, Plan 02 - MOCK-01..04)
# =============================================================================


class TestImageFallbackReason:
    """Test fallback_reason behavior for image context lookups."""

    def test_unknown_stringid_returns_fallback_reason(self, mock_mega_index):
        """When StringID has no matching image, returns ImageContext with has_image=False and fallback_reason."""
        svc = MapDataService()
        svc._loaded = True

        with patch(
            "server.tools.ldm.services.mega_index.get_mega_index",
            return_value=mock_mega_index,
        ):
            result = svc.get_image_context("UNKNOWN_STRING_ID_12345")

        assert result is not None, "Should return ImageContext, not None, when service is loaded"
        assert result.has_image is False
        assert result.fallback_reason != ""
        assert "not found" in result.fallback_reason.lower() or "no" in result.fallback_reason.lower()

    def test_known_strkey_has_no_fallback_reason(self, service):
        """Existing lookup by StrKey still returns has_image=True with no fallback_reason."""
        result = service.get_image_context("item_sword_01")
        assert result is not None
        assert result.has_image is True
        assert result.fallback_reason == ""

    def test_not_loaded_returns_none_not_fallback(self):
        """When service is not loaded, returns None (not an ImageContext with fallback)."""
        svc = MapDataService()
        svc._loaded = False
        result = svc.get_image_context("anything")
        assert result is None

    def test_entity_without_texture_gives_specific_reason(self, mock_mega_index):
        """When entity exists but has no UITextureName, fallback_reason is specific."""
        # Add an entity with no texture to the mock
        mock_mega_index.stringid_to_entity["NO_TEXTURE_SID"] = ("item", "Item_NoTexture")
        mock_mega_index.knowledge_by_strkey["Item_NoTexture"] = KnowledgeEntry(
            strkey="Item_NoTexture",
            name="텍스처없음",
            desc="설명",
            ui_texture_name="",  # Empty texture name
            group_key="item_group",
            source_file="test.xml",
        )

        svc = MapDataService()
        svc._loaded = True

        with patch(
            "server.tools.ldm.services.mega_index.get_mega_index",
            return_value=mock_mega_index,
        ):
            result = svc.get_image_context("NO_TEXTURE_SID")

        assert result is not None
        assert result.has_image is False
        assert "UITextureName" in result.fallback_reason or "texture" in result.fallback_reason.lower()


class TestAudioFallbackReason:
    """Test fallback_reason behavior for audio context lookups."""

    def test_unknown_stringid_returns_fallback_reason(self, mock_mega_index):
        """When StringID has no matching audio, returns AudioContext with fallback_reason."""
        svc = MapDataService()
        svc._loaded = True

        with patch(
            "server.tools.ldm.services.mega_index.get_mega_index",
            return_value=mock_mega_index,
        ):
            result = svc.get_audio_context("UNKNOWN_STRING_ID_12345")

        assert result is not None, "Should return AudioContext, not None, when service is loaded"
        assert result.wem_path == ""
        assert result.fallback_reason != ""

    def test_known_strkey_has_no_fallback_reason(self, service):
        """Existing lookup by StrKey still returns audio with no fallback_reason."""
        result = service.get_audio_context("npc_greeting_01")
        assert result is not None
        assert result.wem_path != ""
        assert result.fallback_reason == ""

    def test_not_loaded_returns_none_not_fallback(self):
        """When service is not loaded, returns None (not AudioContext with fallback)."""
        svc = MapDataService()
        svc._loaded = False
        result = svc.get_audio_context("anything")
        assert result is None


class TestDriveAgnosticPaths:
    """MOCK-04: Mock paths work regardless of drive letter."""

    def test_mock_paths_no_drive_letter_hardcoded(self, mock_mega_index):
        """Test assertions in mock_mega_index use local paths, not Windows drive letters."""
        # Verify the mock_mega_index paths are local (Path objects), not F:\perforce\...
        for key, path in mock_mega_index.strkey_to_image_path.items():
            path_str = str(path)
            assert not (len(path_str) >= 2 and path_str[1] == ":"), (
                f"Mock path for '{key}' uses Windows drive letter: {path_str}"
            )

        for key, path in mock_mega_index.stringid_to_audio_path.items():
            path_str = str(path)
            assert not (len(path_str) >= 2 and path_str[1] == ":"), (
                f"Mock audio path for '{key}' uses Windows drive letter: {path_str}"
            )


class TestServiceStatus:
    def test_unloaded_service_returns_none(self):
        svc = MapDataService()
        assert svc.get_image_context("anything") is None
        assert svc.get_audio_context("anything") is None

    def test_loaded_service_status(self, service):
        status = service.get_status()
        assert status["loaded"] is True
        assert status["branch"] == "mainline"
        assert status["drive"] == "F"
        assert status["image_count"] > 0
        assert status["audio_count"] > 0

    def test_unloaded_service_status(self):
        svc = MapDataService()
        status = svc.get_status()
        assert status["loaded"] is False
