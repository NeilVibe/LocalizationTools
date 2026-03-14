"""
Unit tests for MapDataService - StrKey-to-image/audio context lookups.

Tests use mock data (no actual file access). Pre-populates indexes
manually then tests get_image_context / get_audio_context lookups.
"""

from __future__ import annotations

import pytest

from server.tools.ldm.services.mapdata_service import (
    MapDataService,
    ImageContext,
    AudioContext,
    convert_to_wsl_path,
    generate_paths,
    KNOWN_BRANCHES,
    PATH_TEMPLATES,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def service():
    """Create a MapDataService with manually populated indexes."""
    svc = MapDataService()

    # Manually populate image index
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


# =============================================================================
# WSL Path Conversion Tests
# =============================================================================

class TestWslPathConversion:
    def test_converts_windows_path_to_wsl(self):
        win_path = r"F:\perforce\cd\mainline\resource\sound\file.wem"
        wsl_path = convert_to_wsl_path(win_path)
        assert wsl_path == "/mnt/f/perforce/cd/mainline/resource/sound/file.wem"

    def test_handles_lowercase_drive(self):
        win_path = r"d:\some\path\file.txt"
        wsl_path = convert_to_wsl_path(win_path)
        assert wsl_path == "/mnt/d/some/path/file.txt"

    def test_passes_through_unix_path(self):
        unix_path = "/mnt/f/already/unix/path.txt"
        result = convert_to_wsl_path(unix_path)
        assert result == unix_path

    def test_handles_empty_string(self):
        assert convert_to_wsl_path("") == ""


# =============================================================================
# Path Generation Tests
# =============================================================================

class TestGeneratePaths:
    def test_default_branch_drive(self):
        paths = generate_paths("F", "mainline")
        assert "texture_folder" in paths
        assert "audio_folder" in paths
        assert r"F:\perforce" in paths["texture_folder"] or "F:" in paths["texture_folder"]
        assert "mainline" in paths["texture_folder"]

    def test_custom_branch(self):
        paths = generate_paths("F", "cd_beta")
        assert "cd_beta" in paths["texture_folder"]
        assert "mainline" not in paths["texture_folder"]

    def test_custom_drive(self):
        paths = generate_paths("D", "mainline")
        assert paths["texture_folder"].startswith("D:")
        assert not paths["texture_folder"].startswith("F:")

    def test_all_template_keys_present(self):
        paths = generate_paths("F", "mainline")
        for key in PATH_TEMPLATES:
            assert key in paths, f"Missing key: {key}"


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


# =============================================================================
# Known Branches
# =============================================================================

class TestKnownBranches:
    def test_known_branches_list(self):
        assert "mainline" in KNOWN_BRANCHES
        assert "cd_beta" in KNOWN_BRANCHES
        assert "cd_alpha" in KNOWN_BRANCHES
        assert "cd_lambda" in KNOWN_BRANCHES
