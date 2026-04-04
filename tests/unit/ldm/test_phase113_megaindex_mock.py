"""
Phase 113 MegaIndex Mock Tests

Verifies MegaIndex build pipeline with realistic mock game data:
1. Full build with mock data succeeds
2. None/missing folders handled gracefully (no crash)
3. D13 language translations indexed correctly
4. Script text lookup (C4/C5) works for different languages
5. Partial audio folders (only EN, no KR/ZH) works
6. DDS texture scanning
7. _path_or_none guard behavior

Uses tmp_path fixture to create a mini game data structure.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
from loguru import logger

from server.tools.ldm.services.mega_index import MegaIndex


# =============================================================================
# XML Templates (matching real game data format)
# =============================================================================

KNOWLEDGE_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<KnowledgeInfoList>
  <KnowledgeInfo StrKey="knowledge_test_01" UITextureName="test_image" KnowledgeGroupKey="group_animals">
    <Name>
      <LocStr StringID="100001" KR="테스트 지식 1" />
    </Name>
    <Desc>
      <LocStr StringID="100002" KR="테스트 설명 1" />
    </Desc>
  </KnowledgeInfo>
  <KnowledgeInfo StrKey="knowledge_test_02" UITextureName="test_image_2">
    <Name>
      <LocStr StringID="100003" KR="테스트 지식 2" />
    </Name>
    <Desc>
      <LocStr StringID="100004" KR="테스트 설명 2" />
    </Desc>
  </KnowledgeInfo>
  <KnowledgeInfo StrKey="knowledge_test_03" UITextureName="">
    <Name>
      <LocStr StringID="100005" KR="테스트 지식 3" />
    </Name>
  </KnowledgeInfo>
</KnowledgeInfoList>
"""

LANGUAGEDATA_KOR_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <LocStr StringID="100001" StrOrigin="테스트 지식 1" />
  <LocStr StringID="100002" StrOrigin="테스트 설명 1" />
  <LocStr StringID="100003" StrOrigin="테스트 지식 2" />
  <LocStr StringID="100004" StrOrigin="테스트 설명 2" />
  <LocStr StringID="100005" StrOrigin="테스트 지식 3" />
</LanguageData>
"""

LANGUAGEDATA_ENG_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <LocStr StringID="100001" Str="Test Knowledge 1" />
  <LocStr StringID="100002" Str="Test Description 1" />
  <LocStr StringID="100003" Str="Test Knowledge 2" />
  <LocStr StringID="100004" Str="Test Description 2" />
  <LocStr StringID="100005" Str="Test Knowledge 3" />
</LanguageData>
"""

LANGUAGEDATA_JPN_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <LocStr StringID="100001" Str="テスト知識1" />
  <LocStr StringID="100002" Str="テスト説明1" />
  <LocStr StringID="100003" Str="テスト知識2" />
</LanguageData>
"""

EXPORT_EVENT_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<ExportList>
  <Export>
    <LocStr StringID="100001" SoundEventName="vo_test_event_01" />
  </Export>
  <Export>
    <LocStr StringID="100003" SoundEventName="vo_test_event_02" />
  </Export>
  <Export>
    <LocStr StringID="100005" SoundEventName="vo_test_event_03" />
  </Export>
</ExportList>
"""

EXPORT_LOC_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<ExportList>
  <Export>
    <LocStr StringID="100001" SoundEventName="vo_test_event_01" />
  </Export>
  <Export>
    <LocStr StringID="100003" SoundEventName="vo_test_event_02" />
  </Export>
</ExportList>
"""


# =============================================================================
# Helper: Create minimal DDS file (128-byte header + 64 bytes pixel data)
# =============================================================================

def _make_minimal_dds(path: Path) -> None:
    """Create a minimal 4x4 RGBA DDS file (128-byte header + 64 bytes)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    header = bytearray(128)

    # DDS magic
    header[0:4] = b"DDS "
    # Header size = 124
    struct.pack_into("<I", header, 4, 124)
    # Flags: CAPS | HEIGHT | WIDTH | PIXELFORMAT (0x1 | 0x2 | 0x4 | 0x1000)
    struct.pack_into("<I", header, 8, 0x1007)
    # Height = 4
    struct.pack_into("<I", header, 12, 4)
    # Width = 4
    struct.pack_into("<I", header, 16, 4)
    # Pitch or linear size
    struct.pack_into("<I", header, 20, 64)
    # Mip map count = 1
    struct.pack_into("<I", header, 28, 1)
    # Pixel format size = 32
    struct.pack_into("<I", header, 76, 32)
    # Pixel format flags: RGBA (0x41 = ALPHAPIXELS | RGB)
    struct.pack_into("<I", header, 80, 0x41)
    # RGB bit count = 32
    struct.pack_into("<I", header, 88, 32)
    # R mask
    struct.pack_into("<I", header, 92, 0x00FF0000)
    # G mask
    struct.pack_into("<I", header, 96, 0x0000FF00)
    # B mask
    struct.pack_into("<I", header, 100, 0x000000FF)
    # A mask
    struct.pack_into("<I", header, 104, 0xFF000000)
    # Caps: TEXTURE (0x1000)
    struct.pack_into("<I", header, 108, 0x1000)

    # 4x4 pixels, 4 bytes each = 64 bytes of pixel data
    pixel_data = bytes(64)

    with open(path, "wb") as f:
        f.write(bytes(header))
        f.write(pixel_data)


# =============================================================================
# Fixture: Create mock game data directory tree
# =============================================================================

@pytest.fixture
def mock_game_data(tmp_path: Path) -> Dict[str, Path]:
    """Create a realistic mini game data structure and return path dict."""
    # -- Knowledge folder --
    knowledge_dir = tmp_path / "GameData" / "StaticInfo" / "knowledgeinfo"
    knowledge_dir.mkdir(parents=True)
    (knowledge_dir / "knowledge.xml").write_text(KNOWLEDGE_XML, encoding="utf-8")

    # -- Loc folder (strorigin + translations) --
    loc_dir = tmp_path / "GameData" / "stringtable" / "loc"
    loc_dir.mkdir(parents=True)
    (loc_dir / "languagedata_KOR.xml").write_text(LANGUAGEDATA_KOR_XML, encoding="utf-8")
    (loc_dir / "languagedata_ENG.xml").write_text(LANGUAGEDATA_ENG_XML, encoding="utf-8")
    (loc_dir / "languagedata_JPN.xml").write_text(LANGUAGEDATA_JPN_XML, encoding="utf-8")

    # -- Export folder (event -> stringid mapping) --
    export_dir = tmp_path / "GameData" / "stringtable" / "export__"
    export_dir.mkdir(parents=True)
    (export_dir / "export_event.xml").write_text(EXPORT_EVENT_XML, encoding="utf-8")
    (export_dir / "export_event.loc.xml").write_text(EXPORT_LOC_XML, encoding="utf-8")

    # -- Texture folder (DDS files) --
    texture_dir = tmp_path / "commonresource" / "ui" / "texture" / "image"
    _make_minimal_dds(texture_dir / "test_image.dds")
    _make_minimal_dds(texture_dir / "test_image_2.dds")

    # -- Audio folders --
    audio_en_dir = tmp_path / "GameData" / "sound" / "windows" / "English(US)"
    audio_en_dir.mkdir(parents=True)
    for name in ["vo_test_event_01.wem", "vo_test_event_02.wem", "vo_test_event_03.wem"]:
        (audio_en_dir / name).write_bytes(b"\x00" * 16)

    audio_kr_dir = tmp_path / "GameData" / "sound" / "windows" / "Korean"
    audio_kr_dir.mkdir(parents=True)
    for name in ["vo_test_event_01.wem", "vo_test_event_02.wem"]:
        (audio_kr_dir / name).write_bytes(b"\x00" * 16)

    audio_zh_dir = tmp_path / "GameData" / "sound" / "windows" / "Chinese(PRC)"
    audio_zh_dir.mkdir(parents=True)
    # Empty -- tests partial audio (no WEM files)

    return {
        "knowledge_folder": knowledge_dir,
        "character_folder": None,
        "faction_folder": None,
        "texture_folder": texture_dir,
        "audio_folder": audio_en_dir,
        "audio_folder_kr": audio_kr_dir,
        "audio_folder_zh": audio_zh_dir,
        "export_folder": export_dir,
        "loc_folder": loc_dir,
    }


def _build_mega_with_paths(paths: Dict[str, Any]) -> MegaIndex:
    """Build a MegaIndex by mocking the perforce path service to return given paths."""
    mock_path_svc = MagicMock()
    mock_path_svc.get_all_resolved.return_value = {
        k: str(v) if v is not None else None
        for k, v in paths.items()
    }
    mock_path_svc.get_status.return_value = {"drive": "T", "branch": "test"}

    with patch(
        "server.tools.ldm.services.mega_index.get_perforce_path_service",
        return_value=mock_path_svc,
    ):
        mega = MegaIndex()
        mega.build(preload_langs=["eng", "jpn"])
    return mega


@pytest.fixture
def mega_with_mock_data(mock_game_data: Dict[str, Path]) -> MegaIndex:
    """Build MegaIndex from mock game data."""
    return _build_mega_with_paths(mock_game_data)


# =============================================================================
# Tests
# =============================================================================


class TestMegaIndexPhase113:
    """Phase 113: MegaIndex with None guards and language translations."""

    # ----- Build success -----

    def test_full_build_with_mock_data(self, mega_with_mock_data: MegaIndex):
        """MegaIndex builds successfully with realistic mock data."""
        mega = mega_with_mock_data
        assert mega._built is True
        assert mega._build_time > 0
        assert len(mega.knowledge_by_strkey) == 3
        assert len(mega.dds_by_stem) >= 2  # At least 2 stems (dual-key may add more)
        assert len(mega.wem_by_event_en) == 3

    def test_build_populates_stats(self, mega_with_mock_data: MegaIndex):
        """stats() returns valid build statistics after build."""
        stats = mega_with_mock_data.stats()
        assert stats["built"] is True
        assert stats["build_time"] > 0
        assert stats["entity_counts"]["knowledge"] == 3
        assert stats["dict_sizes"]["D9_dds"] >= 2
        assert stats["dict_sizes"]["D10_wem_en"] == 3

    # ----- None folder guards -----

    def test_none_folders_no_crash(self):
        """MegaIndex handles ALL folders = None without crashing."""
        all_none = {
            "knowledge_folder": None,
            "character_folder": None,
            "faction_folder": None,
            "texture_folder": None,
            "audio_folder": None,
            "audio_folder_kr": None,
            "audio_folder_zh": None,
            "export_folder": None,
            "loc_folder": None,
        }
        mega = _build_mega_with_paths(all_none)
        assert mega._built is True
        # All dicts should be empty but not None
        assert len(mega.knowledge_by_strkey) == 0
        assert len(mega.dds_by_stem) == 0
        assert len(mega.wem_by_event_en) == 0
        assert len(mega.wem_by_event_kr) == 0
        assert len(mega.wem_by_event_zh) == 0
        assert len(mega.stringid_to_strorigin) == 0
        assert len(mega.stringid_to_translations) == 0
        assert len(mega.event_to_stringid) == 0

    def test_nonexistent_path_no_crash(self, tmp_path: Path):
        """Paths that point to nonexistent directories don't crash."""
        bogus = {
            "knowledge_folder": str(tmp_path / "does_not_exist" / "knowledge"),
            "texture_folder": str(tmp_path / "does_not_exist" / "textures"),
            "audio_folder": str(tmp_path / "does_not_exist" / "audio"),
            "audio_folder_kr": None,
            "audio_folder_zh": None,
            "export_folder": None,
            "loc_folder": None,
            "character_folder": None,
            "faction_folder": None,
        }
        mega = _build_mega_with_paths(bogus)
        assert mega._built is True
        assert len(mega.knowledge_by_strkey) == 0

    def test_partial_none_folders(self, mock_game_data: Dict[str, Path]):
        """Some folders None, others valid -- builds with available data."""
        paths = dict(mock_game_data)
        paths["texture_folder"] = None
        paths["audio_folder_kr"] = None
        paths["audio_folder_zh"] = None
        mega = _build_mega_with_paths(paths)
        assert mega._built is True
        # Knowledge still parsed
        assert len(mega.knowledge_by_strkey) == 3
        # Textures skipped
        assert len(mega.dds_by_stem) == 0
        # EN audio still works
        assert len(mega.wem_by_event_en) == 3
        # KR and ZH empty
        assert len(mega.wem_by_event_kr) == 0
        assert len(mega.wem_by_event_zh) == 0

    # ----- Audio partial folders -----

    def test_partial_audio_folders(self, mega_with_mock_data: MegaIndex):
        """EN audio exists (3 files), KR has 2, ZH folder is empty -- no crash."""
        mega = mega_with_mock_data
        assert len(mega.wem_by_event_en) == 3
        assert len(mega.wem_by_event_kr) == 2
        assert len(mega.wem_by_event_zh) == 0

    def test_audio_backward_compat_alias(self, mega_with_mock_data: MegaIndex):
        """wem_by_event is aliased to wem_by_event_en for backward compat."""
        mega = mega_with_mock_data
        assert mega.wem_by_event is mega.wem_by_event_en

    # ----- Translation D13 -----

    def test_translation_d13_eng_indexed(self, mega_with_mock_data: MegaIndex):
        """D13 ENG translations indexed correctly."""
        mega = mega_with_mock_data
        eng = mega.get_translation("100001", "eng")
        assert eng is not None
        assert eng == "Test Knowledge 1"

    def test_translation_d13_jpn_indexed(self, mega_with_mock_data: MegaIndex):
        """D13 JPN translations indexed correctly."""
        mega = mega_with_mock_data
        jpn = mega.get_translation("100001", "jpn")
        assert jpn is not None
        assert jpn == "テスト知識1"

    def test_translation_d13_partial_jpn(self, mega_with_mock_data: MegaIndex):
        """JPN has only 3 entries (not 5) -- missing ones return None."""
        mega = mega_with_mock_data
        # 100004 is NOT in JPN XML
        assert mega.get_translation("100004", "jpn") is None
        # But ENG has it
        assert mega.get_translation("100004", "eng") == "Test Description 2"

    def test_translation_kor_skipped(self, mega_with_mock_data: MegaIndex):
        """Korean is StrOrigin, not D13 translation -- get_translation returns None."""
        mega = mega_with_mock_data
        kor = mega.get_translation("100001", "kor")
        assert kor is None

    def test_translation_nonexistent_lang(self, mega_with_mock_data: MegaIndex):
        """Requesting a language not preloaded returns None."""
        mega = mega_with_mock_data
        assert mega.get_translation("100001", "fre") is None
        assert mega.get_translation("100001", "ger") is None

    def test_translation_nonexistent_stringid(self, mega_with_mock_data: MegaIndex):
        """Requesting a StringID that doesn't exist returns None."""
        mega = mega_with_mock_data
        assert mega.get_translation("999999", "eng") is None

    # ----- StrOrigin D12 -----

    def test_strorigin_indexed(self, mega_with_mock_data: MegaIndex):
        """D12 Korean StrOrigin text indexed from languagedata_KOR."""
        mega = mega_with_mock_data
        origin = mega.get_strorigin("100001")
        assert origin is not None
        assert origin == "테스트 지식 1"

    def test_strorigin_all_entries(self, mega_with_mock_data: MegaIndex):
        """All 5 KOR StrOrigin entries are indexed."""
        mega = mega_with_mock_data
        assert len(mega.stringid_to_strorigin) == 5

    # ----- Script text C4/C5 -----

    def test_script_kr_from_c4(self, mega_with_mock_data: MegaIndex):
        """C4: event -> stringid -> strorigin = Korean script text."""
        mega = mega_with_mock_data
        script = mega.get_script_kr("vo_test_event_01")
        assert script is not None
        assert script == "테스트 지식 1"

    def test_script_eng_from_c5(self, mega_with_mock_data: MegaIndex):
        """C5: event -> stringid -> translation(eng) = English script text."""
        mega = mega_with_mock_data
        script = mega.get_script_eng("vo_test_event_01")
        assert script is not None
        assert script == "Test Knowledge 1"

    def test_script_kr_nonexistent_event(self, mega_with_mock_data: MegaIndex):
        """Nonexistent event returns None for script text."""
        mega = mega_with_mock_data
        assert mega.get_script_kr("vo_nonexistent") is None
        assert mega.get_script_eng("vo_nonexistent") is None

    # ----- DDS textures D9 -----

    def test_dds_scan_with_mock_image(self, mega_with_mock_data: MegaIndex):
        """DDS textures scanned and indexed by stem (lowercase)."""
        mega = mega_with_mock_data
        assert "test_image" in mega.dds_by_stem
        assert "test_image_2" in mega.dds_by_stem
        # Dual-key: full filename also indexed
        assert "test_image.dds" in mega.dds_by_stem

    def test_dds_path_is_valid(self, mega_with_mock_data: MegaIndex):
        """DDS path points to a real file."""
        mega = mega_with_mock_data
        dds_path = mega.get_dds_path("test_image")
        assert dds_path is not None
        assert dds_path.exists()
        assert dds_path.suffix == ".dds"

    # ----- Event -> StringID D11 -----

    def test_event_to_stringid_indexed(self, mega_with_mock_data: MegaIndex):
        """D11: Event names mapped to StringIDs."""
        mega = mega_with_mock_data
        sid = mega.event_to_stringid_lookup("vo_test_event_01")
        assert sid == "100001"
        sid2 = mega.event_to_stringid_lookup("vo_test_event_02")
        assert sid2 == "100003"

    # ----- Reverse lookups -----

    def test_stringid_to_event_reverse(self, mega_with_mock_data: MegaIndex):
        """R3: StringID -> event name reverse lookup."""
        mega = mega_with_mock_data
        event = mega.stringid_to_event_lookup("100001")
        assert event == "vo_test_event_01"

    def test_strorigin_to_stringids_reverse(self, mega_with_mock_data: MegaIndex):
        """R6: Korean text -> StringID reverse lookup."""
        mega = mega_with_mock_data
        sids = mega.find_stringids_by_korean("테스트 지식 1")
        assert "100001" in sids

    # ----- Knowledge entity lookup -----

    def test_knowledge_lookup(self, mega_with_mock_data: MegaIndex):
        """Knowledge entity accessible by strkey."""
        mega = mega_with_mock_data
        entry = mega.get_knowledge("knowledge_test_01")
        assert entry is not None
        assert entry.strkey == "knowledge_test_01"
        assert entry.ui_texture_name == "test_image"

    def test_knowledge_case_insensitive(self, mega_with_mock_data: MegaIndex):
        """Knowledge lookup is case-insensitive."""
        mega = mega_with_mock_data
        entry = mega.get_knowledge("KNOWLEDGE_TEST_01")
        assert entry is not None

    # ----- Image path C1 -----

    def test_strkey_to_image_path(self, mega_with_mock_data: MegaIndex):
        """C1: StrKey -> image path through UITextureName -> DDS."""
        mega = mega_with_mock_data
        img = mega.get_image_path("knowledge_test_01")
        assert img is not None
        assert "test_image" in img.stem.lower()

    # ----- Audio path by StringID C3 -----

    def test_audio_path_by_stringid(self, mega_with_mock_data: MegaIndex):
        """C3: StringID -> audio path (through event -> WEM)."""
        mega = mega_with_mock_data
        audio = mega.get_audio_path_by_stringid("100001")
        assert audio is not None
        assert audio.suffix == ".wem"

    def test_audio_path_by_stringid_for_lang_en(self, mega_with_mock_data: MegaIndex):
        """C3 lang-aware: English file language routes to EN audio."""
        mega = mega_with_mock_data
        audio = mega.get_audio_path_by_stringid_for_lang("100001", "eng")
        assert audio is not None
        assert "English(US)" in str(audio) or "english" in str(audio).lower()

    def test_audio_path_by_stringid_for_lang_kr(self, mega_with_mock_data: MegaIndex):
        """C3 lang-aware: Korean file language routes to KR audio."""
        mega = mega_with_mock_data
        audio = mega.get_audio_path_by_stringid_for_lang("100001", "kor")
        # KR audio exists for event_01
        assert audio is not None
        assert "Korean" in str(audio) or "korean" in str(audio).lower()

    def test_audio_path_by_stringid_for_lang_zh_empty(self, mega_with_mock_data: MegaIndex):
        """C3 lang-aware: Chinese folder was empty, so ZH audio returns None."""
        mega = mega_with_mock_data
        audio = mega.get_audio_path_by_stringid_for_lang("100001", "zho-cn")
        assert audio is None

    # ----- _path_or_none guards -----

    def test_path_or_none_with_none_value(self):
        """_path_or_none returns None for missing keys in paths dict."""
        mega = _build_mega_with_paths({"knowledge_folder": None})
        # Build completes, knowledge empty
        assert mega._built is True
        assert len(mega.knowledge_by_strkey) == 0

    def test_path_or_none_with_invalid_type(self):
        """_path_or_none returns None for non-string/non-Path values."""
        paths = {
            "knowledge_folder": 12345,  # Invalid type
            "texture_folder": None,
            "audio_folder": None,
            "audio_folder_kr": None,
            "audio_folder_zh": None,
            "export_folder": None,
            "loc_folder": None,
            "character_folder": None,
            "faction_folder": None,
        }
        mock_path_svc = MagicMock()
        mock_path_svc.get_all_resolved.return_value = paths
        mock_path_svc.get_status.return_value = {"drive": "T", "branch": "test"}

        with patch(
            "server.tools.ldm.services.mega_index.get_perforce_path_service",
            return_value=mock_path_svc,
        ):
            mega = MegaIndex()
            mega.build(preload_langs=["eng"])

        assert mega._built is True
        # Invalid type should be logged and treated as None
        assert len(mega.knowledge_by_strkey) == 0

    # ----- Entity counts -----

    def test_entity_counts(self, mega_with_mock_data: MegaIndex):
        """entity_counts() returns correct numbers."""
        counts = mega_with_mock_data.entity_counts()
        assert counts["knowledge"] == 3
        # No character/item/faction/etc. in mock data
        assert counts["character"] == 0
        assert counts["item"] == 0
        assert counts["faction"] == 0
        assert counts["skill"] == 0

    # ----- Rebuild cleans state -----

    def test_rebuild_clears_previous_data(self, mock_game_data: Dict[str, Path]):
        """Rebuilding clears data from previous build."""
        mega = _build_mega_with_paths(mock_game_data)
        assert len(mega.knowledge_by_strkey) == 3

        # Rebuild with all-None paths
        all_none = {k: None for k in mock_game_data}
        mock_path_svc = MagicMock()
        mock_path_svc.get_all_resolved.return_value = all_none
        mock_path_svc.get_status.return_value = {"drive": "T", "branch": "test2"}

        with patch(
            "server.tools.ldm.services.mega_index.get_perforce_path_service",
            return_value=mock_path_svc,
        ):
            mega.build(preload_langs=["eng"])

        # Previous data should be gone
        assert len(mega.knowledge_by_strkey) == 0
        assert len(mega.dds_by_stem) == 0
        assert len(mega.wem_by_event_en) == 0
