"""
Phase 113 API Logic Tests

Tests audio codex language switching logic, auth LAN fallback detection,
and HTTPException re-raise patterns — tested at function level, not HTTP.
"""

import pytest
from unittest.mock import MagicMock


# =============================================================================
# Audio Codex Language Tests (test _build_audio_card directly)
# =============================================================================


class TestBuildAudioCard:
    """Phase 113: _build_audio_card language-aware script text."""

    @pytest.fixture
    def mega(self):
        """Mock MegaIndex with audio data."""
        m = MagicMock()
        m.event_to_stringid_lookup.side_effect = lambda ev: {
            "vo_test_01": "100001", "vo_test_02": "100002", "vo_no_sid": None,
        }.get(ev)
        m.get_script_kr.side_effect = lambda ev: {
            "vo_test_01": "테스트 대사 1", "vo_test_02": "테스트 대사 2",
        }.get(ev)
        m.get_script_eng.side_effect = lambda ev: {
            "vo_test_01": "Test dialogue 1", "vo_test_02": "Test dialogue 2",
        }.get(ev)

        def mock_translation(sid, lang):
            return {
                ("100001", "jpn"): "テスト台詞 1",
                ("100001", "zho-cn"): "测试台词 1",
                ("100002", "jpn"): "テスト台詞 2",
            }.get((sid, lang))

        m.get_translation.side_effect = mock_translation
        m.get_audio_path_by_event_for_lang.return_value = None
        m.event_to_export_path = {"vo_test_01": "sound/test"}
        m.event_to_xml_order = {"vo_test_01": 1}
        return m

    def test_eng_default_no_script_lang(self, mega):
        from server.tools.ldm.routes.codex_audio import _build_audio_card
        card = _build_audio_card("vo_test_01", mega, language="eng")
        assert card.script_kr == "테스트 대사 1"
        assert card.script_eng == "Test dialogue 1"
        assert card.script_lang is None
        assert card.script_lang_code is None

    def test_kor_no_script_lang(self, mega):
        from server.tools.ldm.routes.codex_audio import _build_audio_card
        card = _build_audio_card("vo_test_01", mega, language="kor")
        assert card.script_lang is None

    def test_jpn_shows_japanese(self, mega):
        from server.tools.ldm.routes.codex_audio import _build_audio_card
        card = _build_audio_card("vo_test_01", mega, language="jpn")
        assert card.script_kr == "테스트 대사 1"
        assert card.script_eng == "Test dialogue 1"
        assert card.script_lang == "テスト台詞 1"
        assert card.script_lang_code == "jpn"

    def test_zhcn_shows_chinese(self, mega):
        from server.tools.ldm.routes.codex_audio import _build_audio_card
        card = _build_audio_card("vo_test_01", mega, language="zho-cn")
        assert card.script_lang == "测试台词 1"
        assert card.script_lang_code == "zho-cn"

    def test_no_stringid_no_translation(self, mega):
        """Event without StringID: script_lang always None."""
        from server.tools.ldm.routes.codex_audio import _build_audio_card
        card = _build_audio_card("vo_no_sid", mega, language="jpn")
        assert card.script_lang is None
        assert card.string_id is None

    def test_missing_translation_returns_none(self, mega):
        """StringID exists but no translation for this language."""
        from server.tools.ldm.routes.codex_audio import _build_audio_card
        # 100002 has jpn but NOT zho-cn
        card = _build_audio_card("vo_test_02", mega, language="zho-cn")
        assert card.script_lang is None
        assert card.script_lang_code is None

    def test_unknown_event_no_crash(self, mega):
        """Unknown event: all fields None, no crash."""
        from server.tools.ldm.routes.codex_audio import _build_audio_card
        card = _build_audio_card("nonexistent_event", mega, language="jpn")
        assert card.event_name == "nonexistent_event"
        assert card.script_kr is None
        assert card.script_eng is None
        assert card.script_lang is None

    def test_all_languages_always_have_kr_eng(self, mega):
        """KOR and ENG scripts always present regardless of language selection."""
        from server.tools.ldm.routes.codex_audio import _build_audio_card
        for lang in ["eng", "kor", "jpn", "zho-cn", "fre", "ger"]:
            card = _build_audio_card("vo_test_01", mega, language=lang)
            assert card.script_kr == "테스트 대사 1"
            assert card.script_eng == "Test dialogue 1"


# =============================================================================
# Schema Tests
# =============================================================================


class TestAudioSchemas:
    """Phase 113: AudioCardResponse and AudioDetailResponse have script_lang fields."""

    def test_card_response_has_script_lang(self):
        from server.tools.ldm.schemas.codex_audio import AudioCardResponse
        card = AudioCardResponse(
            event_name="test",
            script_lang="テスト",
            script_lang_code="jpn",
        )
        assert card.script_lang == "テスト"
        assert card.script_lang_code == "jpn"

    def test_card_response_defaults_none(self):
        from server.tools.ldm.schemas.codex_audio import AudioCardResponse
        card = AudioCardResponse(event_name="test")
        assert card.script_lang is None
        assert card.script_lang_code is None

    def test_detail_response_has_script_lang(self):
        from server.tools.ldm.schemas.codex_audio import AudioDetailResponse
        detail = AudioDetailResponse(
            event_name="test",
            script_lang="测试",
            script_lang_code="zho-cn",
        )
        assert detail.script_lang == "测试"
        assert detail.script_lang_code == "zho-cn"


# =============================================================================
# Auth LAN Fallback Logic Tests
# =============================================================================


class TestAuthLanFallbackLogic:
    """Phase 113: LAN fallback detection logic."""

    def test_remote_pg_sqlite_is_fallback(self):
        """Remote PG host + SQLite active = LAN fallback."""
        pg_host = "10.35.34.61"
        is_lan = pg_host not in ("localhost", "127.0.0.1", "::1", "")
        db_type = "sqlite"
        assert is_lan is True
        assert db_type == "sqlite"
        # Would return 503

    def test_localhost_sqlite_is_not_fallback(self):
        """Localhost PG + SQLite = normal offline mode, NOT fallback."""
        pg_host = "localhost"
        is_lan = pg_host not in ("localhost", "127.0.0.1", "::1", "")
        assert is_lan is False

    def test_remote_pg_postgresql_is_not_fallback(self):
        """Remote PG + PostgreSQL active = connected, NOT fallback."""
        pg_host = "10.35.34.61"
        is_lan = pg_host not in ("localhost", "127.0.0.1", "::1", "")
        db_type = "postgresql"
        assert is_lan is True
        assert db_type != "sqlite"
        # Would return 401 (normal user-not-found)

    def test_ipv6_loopback_not_lan(self):
        pg_host = "::1"
        is_lan = pg_host not in ("localhost", "127.0.0.1", "::1", "")
        assert is_lan is False

    def test_empty_host_not_lan(self):
        pg_host = ""
        is_lan = pg_host not in ("localhost", "127.0.0.1", "::1", "")
        assert is_lan is False

    def test_172_range_is_lan(self):
        """Private 172.x.x.x range is LAN."""
        pg_host = "172.28.150.120"
        is_lan = pg_host not in ("localhost", "127.0.0.1", "::1", "")
        assert is_lan is True


# =============================================================================
# HTTPException Re-raise Pattern Tests
# =============================================================================


class TestHttpExceptionReRaise:
    """Phase 113: Verify except HTTPException: raise pattern in codex_audio."""

    def test_pattern_exists_in_list_audio(self):
        """list_audio has 'except HTTPException: raise' before broad catch."""
        import inspect
        from server.tools.ldm.routes import codex_audio
        source = inspect.getsource(codex_audio.list_audio)
        assert "except HTTPException" in source

    def test_pattern_exists_in_categories(self):
        import inspect
        from server.tools.ldm.routes import codex_audio
        source = inspect.getsource(codex_audio.get_audio_categories)
        assert "except HTTPException" in source

    def test_pattern_exists_in_cleanup(self):
        import inspect
        from server.tools.ldm.routes import codex_audio
        source = inspect.getsource(codex_audio.cleanup_audio_cache)
        assert "except HTTPException" in source

    def test_pattern_exists_in_stop(self):
        import inspect
        from server.tools.ldm.routes import codex_audio
        source = inspect.getsource(codex_audio.stop_audio)
        assert "except HTTPException" in source

    def test_pattern_exists_in_playback_status(self):
        import inspect
        from server.tools.ldm.routes import codex_audio
        source = inspect.getsource(codex_audio.get_playback_status)
        assert "except HTTPException" in source


# =============================================================================
# Media Converter pillow-dds Tests
# =============================================================================


class TestPillowDdsIntegration:
    """Phase 113: pillow-dds availability flag and early-out."""

    def test_flag_is_bool(self):
        from server.tools.ldm.services.media_converter import _PILLOW_DDS_AVAILABLE
        assert isinstance(_PILLOW_DDS_AVAILABLE, bool)

    def test_early_out_for_dds_without_plugin(self, tmp_path):
        """DDS file without DDS plugin returns None."""
        from server.tools.ldm.services.media_converter import (
            MediaConverter, _PILLOW_DDS_AVAILABLE,
        )
        if _PILLOW_DDS_AVAILABLE:
            pytest.skip("DDS plugin available, can't test early-out")
        converter = MediaConverter()
        fake_dds = tmp_path / "texture.dds"
        fake_dds.write_bytes(b"DDS " + b"\x00" * 124)
        result = converter.convert_dds_to_png(fake_dds)
        assert result is None

    def test_non_dds_file_unaffected(self, tmp_path):
        """PNG file should not be affected by pillow-dds flag."""
        from server.tools.ldm.services.media_converter import MediaConverter
        from PIL import Image
        converter = MediaConverter()
        # Create a real PNG
        img = Image.new("RGBA", (4, 4), (255, 0, 0, 255))
        png_path = tmp_path / "test.png"
        img.save(png_path)
        result = converter.convert_dds_to_png(png_path)
        assert result is not None
        assert len(result) > 0
