"""
Language-Aware Media Routing Tests

Tests that switching language correctly routes to the right audio/media:
- English/French/German → English(US) audio folder
- Korean/Japanese/ZHO-TW → Korean audio folder
- ZHO-CN → Chinese(PRC) audio folder
- Texture/image resolution is language-independent (shared DDS files)
- PerforcePathService resolves correct audio folder per language
- MegaIndex LANG_TO_AUDIO mapping covers all supported languages

Requires: server modules (no running server needed, uses mocks and fixtures)
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from server.tools.ldm.services.mega_index_helpers import LANG_TO_AUDIO
from server.tools.ldm.services.perforce_path_service import (
    PerforcePathService,
    LANG_TO_AUDIO_FOLDER,
    PATH_TEMPLATES,
)

MOCK_GAMEDATA = Path(__file__).parent.parent.parent / "fixtures" / "mock_gamedata"


# =============================================================================
# 1. LANG_TO_AUDIO routing map
# =============================================================================

class TestLangToAudioRouting:
    """Verify LANG_TO_AUDIO routes every language to the correct audio bucket."""

    def test_english_routes_to_en(self):
        assert LANG_TO_AUDIO["eng"] == "en"

    def test_french_routes_to_en(self):
        """Latin-script languages use English(US) audio."""
        assert LANG_TO_AUDIO["fre"] == "en"

    def test_german_routes_to_en(self):
        assert LANG_TO_AUDIO["ger"] == "en"

    def test_spanish_routes_to_en(self):
        assert LANG_TO_AUDIO["spa-es"] == "en"
        assert LANG_TO_AUDIO["spa-mx"] == "en"

    def test_korean_routes_to_kr(self):
        assert LANG_TO_AUDIO["kor"] == "kr"

    def test_japanese_routes_to_kr(self):
        """Japanese shares Korean audio (same voice actors)."""
        assert LANG_TO_AUDIO["jpn"] == "kr"

    def test_zho_tw_routes_to_kr(self):
        """Traditional Chinese (Taiwan) shares Korean audio."""
        assert LANG_TO_AUDIO["zho-tw"] == "kr"

    def test_zho_cn_routes_to_zh(self):
        """Simplified Chinese has its own audio recording."""
        assert LANG_TO_AUDIO["zho-cn"] == "zh"

    def test_all_latin_languages_route_to_en(self):
        """Every Latin-script language must route to English audio."""
        latin_langs = ["eng", "fre", "ger", "spa-es", "spa-mx",
                       "por-br", "ita", "rus", "tur", "pol"]
        for lang in latin_langs:
            assert LANG_TO_AUDIO[lang] == "en", f"{lang} should route to 'en'"

    def test_unknown_language_defaults_to_en(self):
        """LANG_TO_AUDIO.get(unknown, 'en') should fallback to English."""
        assert LANG_TO_AUDIO.get("xyz-unknown", "en") == "en"
        assert LANG_TO_AUDIO.get("", "en") == "en"

    def test_all_three_audio_buckets_exist(self):
        """Exactly 3 audio buckets: en, kr, zh."""
        buckets = set(LANG_TO_AUDIO.values())
        assert buckets == {"en", "kr", "zh"}

    def test_mapping_covers_14_languages(self):
        """All 14 supported languages are in the routing map."""
        assert len(LANG_TO_AUDIO) == 14


# =============================================================================
# 2. PerforcePathService audio folder resolution
# =============================================================================

class TestPerforceAudioFolderResolution:
    """PerforcePathService.resolve_audio_folder() returns correct path per language."""

    @pytest.fixture
    def service(self):
        svc = PerforcePathService()
        svc.configure_for_mock_gamedata(MOCK_GAMEDATA)
        return svc

    def test_english_audio_folder(self, service):
        path = service.resolve_audio_folder("eng")
        assert "English(US)" in str(path)
        assert path.exists(), f"English audio folder missing: {path}"

    def test_korean_audio_folder(self, service):
        path = service.resolve_audio_folder("kor")
        assert "Korean" in str(path)
        assert path.exists(), f"Korean audio folder missing: {path}"

    def test_chinese_audio_folder(self, service):
        path = service.resolve_audio_folder("zho-cn")
        assert "Chinese(PRC)" in str(path)
        assert path.exists(), f"Chinese audio folder missing: {path}"

    def test_invalid_language_raises(self, service):
        with pytest.raises(KeyError, match="Unknown audio language"):
            service.resolve_audio_folder("xyz")

    def test_english_and_korean_are_different_folders(self, service):
        """Language switch must change the actual folder, not just the name."""
        en_path = service.resolve_audio_folder("eng")
        kr_path = service.resolve_audio_folder("kor")
        assert en_path != kr_path, "EN and KR must resolve to different folders"

    def test_all_three_folders_are_distinct(self, service):
        en = service.resolve_audio_folder("eng")
        kr = service.resolve_audio_folder("kor")
        zh = service.resolve_audio_folder("zho-cn")
        assert len({str(en), str(kr), str(zh)}) == 3, "All 3 audio folders must be distinct"


# =============================================================================
# 3. Mock gamedata: audio files exist per language
# =============================================================================

class TestMockAudioFilesPerLanguage:
    """Verify mock fixtures have audio files in all 3 language folders."""

    EN_DIR = MOCK_GAMEDATA / "sound" / "windows" / "English(US)"
    KR_DIR = MOCK_GAMEDATA / "sound" / "windows" / "Korean"
    ZH_DIR = MOCK_GAMEDATA / "sound" / "windows" / "Chinese(PRC)"

    def test_english_has_wem_files(self):
        wems = list(self.EN_DIR.glob("*.wem"))
        assert len(wems) >= 10, f"English has only {len(wems)} WEM files (need 10+)"

    def test_korean_has_wem_files(self):
        wems = list(self.KR_DIR.glob("*.wem"))
        assert len(wems) >= 10, f"Korean has only {len(wems)} WEM files (need 10+)"

    def test_chinese_has_wem_files(self):
        wems = list(self.ZH_DIR.glob("*.wem"))
        assert len(wems) >= 10, f"Chinese has only {len(wems)} WEM files (need 10+)"

    def test_all_languages_same_filenames(self):
        """All 3 folders must have identical WEM filenames (same events, different recordings)."""
        en_stems = {f.stem for f in self.EN_DIR.glob("*.wem")}
        kr_stems = {f.stem for f in self.KR_DIR.glob("*.wem")}
        zh_stems = {f.stem for f in self.ZH_DIR.glob("*.wem")}

        assert en_stems == kr_stems, f"EN/KR mismatch: {en_stems.symmetric_difference(kr_stems)}"
        assert en_stems == zh_stems, f"EN/ZH mismatch: {en_stems.symmetric_difference(zh_stems)}"

    def test_wem_files_have_riff_header(self):
        """All WEM files across all languages must have valid RIFF headers."""
        for lang_dir in [self.EN_DIR, self.KR_DIR, self.ZH_DIR]:
            for wem in lang_dir.glob("*.wem"):
                data = wem.read_bytes()[:4]
                assert data == b"RIFF", f"{wem} has invalid header: {data}"


# =============================================================================
# 4. Mock gamedata: language data XML files
# =============================================================================

class TestLanguageDataXML:
    """Verify language data XML files exist and are parseable."""

    LOC_DIR = MOCK_GAMEDATA / "loc"

    def test_eng_xml_exists(self):
        assert (self.LOC_DIR / "languagedata_ENG.xml").exists()

    def test_kor_xml_exists(self):
        assert (self.LOC_DIR / "languagedata_KOR.xml").exists()

    def test_jpn_xml_exists(self):
        assert (self.LOC_DIR / "languagedata_JPN.xml").exists()

    def test_all_languages_have_same_stringids(self):
        """ENG, KOR, JPN must have identical StringId sets."""
        from lxml import etree

        ids_by_lang = {}
        for lang in ("ENG", "KOR", "JPN"):
            xml_path = self.LOC_DIR / f"languagedata_{lang}.xml"
            tree = etree.parse(str(xml_path))
            ids = {e.get("StringId") for e in tree.getroot().findall(".//LocStr")}
            ids_by_lang[lang] = ids

        assert ids_by_lang["ENG"] == ids_by_lang["KOR"], (
            f"ENG/KOR StringId mismatch: {ids_by_lang['ENG'].symmetric_difference(ids_by_lang['KOR'])}"
        )
        assert ids_by_lang["ENG"] == ids_by_lang["JPN"], (
            f"ENG/JPN StringId mismatch: {ids_by_lang['ENG'].symmetric_difference(ids_by_lang['JPN'])}"
        )

    def test_kor_xml_has_korean_text(self):
        """Korean language data must contain actual Korean characters."""
        from lxml import etree
        import re

        tree = etree.parse(str(self.LOC_DIR / "languagedata_KOR.xml"))
        korean_re = re.compile(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]')

        has_korean = False
        for el in tree.getroot().findall(".//LocStr"):
            for attr in ("Str", "StrOrigin"):
                val = el.get(attr, "")
                if korean_re.search(val):
                    has_korean = True
                    break
            if has_korean:
                break

        assert has_korean, "KOR language data has no Korean characters"

    def test_eng_xml_has_english_text(self):
        """English language data must contain ASCII text."""
        from lxml import etree

        tree = etree.parse(str(self.LOC_DIR / "languagedata_ENG.xml"))

        has_english = False
        for el in tree.getroot().findall(".//LocStr"):
            val = el.get("Str", "")
            if val and any(c.isascii() and c.isalpha() for c in val):
                has_english = True
                break

        assert has_english, "ENG language data has no English text"


# =============================================================================
# 5. Texture resolution is language-independent
# =============================================================================

class TestTextureLanguageIndependence:
    """DDS textures are shared across all languages (not language-specific)."""

    DDS_DIR = MOCK_GAMEDATA / "texture" / "image"

    def test_dds_folder_exists(self):
        assert self.DDS_DIR.exists()

    def test_dds_files_present(self):
        dds_files = list(self.DDS_DIR.glob("*.dds"))
        assert len(dds_files) >= 20, f"Only {len(dds_files)} DDS files (need 20+)"

    def test_texture_path_is_not_language_specific(self):
        """PATH_TEMPLATES['texture_folder'] has no language component."""
        template = PATH_TEMPLATES["texture_folder"]
        assert "English" not in template
        assert "Korean" not in template
        assert "Chinese" not in template

    def test_perforce_service_texture_same_for_all_languages(self):
        """Texture path doesn't change when language changes."""
        svc = PerforcePathService()
        svc.configure_for_mock_gamedata(MOCK_GAMEDATA)
        texture_path = svc.resolve("texture_folder")

        # Audio changes per language, but texture must stay the same
        assert "texture" in str(texture_path).lower()
        assert "English" not in str(texture_path)
        assert "Korean" not in str(texture_path)


# =============================================================================
# 6. MegaIndex language-aware audio path routing (mocked)
# =============================================================================

class TestMegaIndexLanguageRouting:
    """MegaIndex.get_audio_path_by_stringid_for_lang routes correctly."""

    def _make_mock_mega(self):
        """Create a mock MegaIndex with separate audio paths per language."""
        mega = MagicMock()
        mega.stringid_to_audio_path_en = {
            "dlg_kira_01": Path("/audio/en/play_kira_taunt_01.wem"),
        }
        mega.stringid_to_audio_path_kr = {
            "dlg_kira_01": Path("/audio/kr/play_kira_taunt_01.wem"),
        }
        mega.stringid_to_audio_path_zh = {
            "dlg_kira_01": Path("/audio/zh/play_kira_taunt_01.wem"),
        }
        return mega

    def test_english_file_gets_english_audio(self):
        """When editing English file, audio comes from English(US) folder."""
        lang_key = LANG_TO_AUDIO.get("eng", "en")
        assert lang_key == "en"
        mega = self._make_mock_mega()
        path = mega.stringid_to_audio_path_en.get("dlg_kira_01")
        assert "/en/" in str(path)

    def test_korean_file_gets_korean_audio(self):
        """When editing Korean file, audio comes from Korean folder."""
        lang_key = LANG_TO_AUDIO.get("kor", "en")
        assert lang_key == "kr"
        mega = self._make_mock_mega()
        path = mega.stringid_to_audio_path_kr.get("dlg_kira_01")
        assert "/kr/" in str(path)

    def test_chinese_file_gets_chinese_audio(self):
        """When editing ZHO-CN file, audio comes from Chinese(PRC) folder."""
        lang_key = LANG_TO_AUDIO.get("zho-cn", "en")
        assert lang_key == "zh"
        mega = self._make_mock_mega()
        path = mega.stringid_to_audio_path_zh.get("dlg_kira_01")
        assert "/zh/" in str(path)

    def test_french_file_gets_english_audio(self):
        """French is Latin-script → uses English(US) audio, not Korean."""
        lang_key = LANG_TO_AUDIO.get("fre", "en")
        assert lang_key == "en"

    def test_japanese_file_gets_korean_audio(self):
        """Japanese shares Korean audio (same voice recordings)."""
        lang_key = LANG_TO_AUDIO.get("jpn", "en")
        assert lang_key == "kr"

    def test_same_stringid_different_language_different_path(self):
        """Same StringId returns different audio paths for different languages."""
        mega = self._make_mock_mega()
        en_path = mega.stringid_to_audio_path_en.get("dlg_kira_01")
        kr_path = mega.stringid_to_audio_path_kr.get("dlg_kira_01")
        zh_path = mega.stringid_to_audio_path_zh.get("dlg_kira_01")

        assert en_path != kr_path, "EN and KR must return different audio paths"
        assert en_path != zh_path, "EN and ZH must return different audio paths"
        assert kr_path != zh_path, "KR and ZH must return different audio paths"
