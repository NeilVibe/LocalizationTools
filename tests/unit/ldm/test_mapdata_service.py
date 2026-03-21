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

    # C3: stringid_to_audio_path
    mega.stringid_to_audio_path = {
        "NPC_GREETING_01_NAME": Path("/mock/audio/VO_NPC_Greeting_01.wem"),
    }

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

    def test_returns_none_for_unknown_strkey(self, service):
        result = service.get_image_context("unknown_key_xyz")
        assert result is None

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
            "server.tools.ldm.services.mapdata_service.get_mega_index",
            return_value=mock_mega_index,
        ):
            result = svc.get_image_context("CHAR_VARON_NAME")

        assert result is not None
        assert result.has_image is True
        assert result.dds_path == "/mock/textures/char_varon.dds"
        assert result.texture_name == "char_varon"

    def test_get_image_context_unknown_stringid(self, mock_mega_index):
        """UNKNOWN_SID returns None when no C7 mapping and no StrKey match."""
        svc = MapDataService()
        svc._loaded = True

        with patch(
            "server.tools.ldm.services.mapdata_service.get_mega_index",
            return_value=mock_mega_index,
        ):
            result = svc.get_image_context("UNKNOWN_SID")

        assert result is None

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
            "server.tools.ldm.services.mapdata_service.get_mega_index",
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

    def test_returns_none_for_unknown_strkey(self, service):
        result = service.get_audio_context("unknown_audio_xyz")
        assert result is None

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
            "server.tools.ldm.services.mapdata_service.get_mega_index",
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
