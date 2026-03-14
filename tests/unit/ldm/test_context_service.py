"""
Tests for ContextService -- Entity context resolution combining glossary detection + mapdata lookups.

Phase 5.1: Contextual Intelligence & QA Engine (Plan 03)
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from server.tools.ldm.services.glossary_service import (
    DetectedEntity,
    EntityInfo,
)
from server.tools.ldm.services.mapdata_service import (
    ImageContext,
    AudioContext,
)
from server.tools.ldm.services.context_service import (
    ContextService,
    get_context_service,
    CharacterContext,
    LocationContext,
    EntityContext,
)


# =============================================================================
# Fixtures
# =============================================================================

CHAR_ENTITY = EntityInfo(
    type="character",
    name="Varon",
    strkey="STR_CHAR_VARON",
    knowledge_key="KNOW_CHAR_VARON",
    source_file="characterinfo_sample.xml",
)

LOCATION_ENTITY = EntityInfo(
    type="region",
    name="Stormhold Castle",
    strkey="STR_LOC_STORMHOLD",
    knowledge_key="KNOW_REGION_STORMHOLD",
    source_file="regioninfo_sample.xml",
)

SAMPLE_IMAGE = ImageContext(
    texture_name="tex_stormhold",
    dds_path="/images/stormhold.dds",
    thumbnail_url="/thumb/stormhold.png",
    has_image=True,
)

SAMPLE_AUDIO = AudioContext(
    event_name="vo_varon_greet",
    wem_path="/audio/varon_greet.wem",
    script_kr="안녕하세요",
    script_eng="Hello",
    duration_seconds=2.5,
)


# =============================================================================
# resolve_context() Tests
# =============================================================================


class TestResolveContext:
    """Test resolve_context() combines glossary detection with media lookups."""

    @pytest.fixture
    def mock_glossary(self):
        svc = MagicMock()
        svc.detect_entities.return_value = [
            DetectedEntity(
                term="Varon",
                start=18,
                end=23,
                entity=CHAR_ENTITY,
            )
        ]
        svc.get_status.return_value = {"loaded": True, "entity_count": 10}
        return svc

    @pytest.fixture
    def mock_mapdata(self):
        svc = MagicMock()
        svc.get_image_context.return_value = None
        svc.get_audio_context.return_value = None
        return svc

    def test_character_entity_returns_character_context(self, mock_glossary, mock_mapdata):
        """Character detected in text -> CharacterContext with metadata."""
        ctx_svc = ContextService()
        with patch("server.tools.ldm.services.context_service.get_glossary_service", return_value=mock_glossary), \
             patch("server.tools.ldm.services.context_service.get_mapdata_service", return_value=mock_mapdata):
            result = ctx_svc.resolve_context("The warrior named Varon enters.")

        assert len(result.entities) == 1
        char_ctx = result.entities[0]
        assert isinstance(char_ctx, CharacterContext)
        assert char_ctx.name == "Varon"
        assert char_ctx.entity_type == "character"
        assert char_ctx.strkey == "STR_CHAR_VARON"
        assert char_ctx.knowledge_key == "KNOW_CHAR_VARON"

    def test_location_entity_returns_location_context_with_image(self, mock_mapdata):
        """Location detected -> LocationContext with image from MapData."""
        mock_glossary = MagicMock()
        mock_glossary.detect_entities.return_value = [
            DetectedEntity(term="Stormhold Castle", start=0, end=16, entity=LOCATION_ENTITY)
        ]
        # Direct StrKey lookup returns image
        mock_mapdata.get_image_context.side_effect = lambda key: SAMPLE_IMAGE if key == "STR_LOC_STORMHOLD" else None

        ctx_svc = ContextService()
        with patch("server.tools.ldm.services.context_service.get_glossary_service", return_value=mock_glossary), \
             patch("server.tools.ldm.services.context_service.get_mapdata_service", return_value=mock_mapdata):
            result = ctx_svc.resolve_context("Stormhold Castle is beautiful.")

        loc_ctx = result.entities[0]
        assert isinstance(loc_ctx, LocationContext)
        assert loc_ctx.name == "Stormhold Castle"
        assert loc_ctx.image is not None
        assert loc_ctx.image.texture_name == "tex_stormhold"

    def test_character_entity_returns_audio_context(self, mock_glossary):
        """Character detected -> audio from direct StrKey lookup."""
        mock_mapdata = MagicMock()
        mock_mapdata.get_image_context.return_value = None
        mock_mapdata.get_audio_context.side_effect = lambda key: SAMPLE_AUDIO if key == "STR_CHAR_VARON" else None

        ctx_svc = ContextService()
        with patch("server.tools.ldm.services.context_service.get_glossary_service", return_value=mock_glossary), \
             patch("server.tools.ldm.services.context_service.get_mapdata_service", return_value=mock_mapdata):
            result = ctx_svc.resolve_context("The warrior named Varon enters.")

        char_ctx = result.entities[0]
        assert isinstance(char_ctx, CharacterContext)
        assert char_ctx.audio is not None
        assert char_ctx.audio.event_name == "vo_varon_greet"

    def test_indirect_image_lookup_via_knowledge_key(self, mock_glossary):
        """CTX-04: When direct StrKey returns None, try KnowledgeKey for image."""
        mock_mapdata = MagicMock()
        # Direct StrKey returns None, KnowledgeKey returns image
        mock_mapdata.get_image_context.side_effect = lambda key: (
            SAMPLE_IMAGE if key == "KNOW_CHAR_VARON" else None
        )
        mock_mapdata.get_audio_context.return_value = None

        ctx_svc = ContextService()
        with patch("server.tools.ldm.services.context_service.get_glossary_service", return_value=mock_glossary), \
             patch("server.tools.ldm.services.context_service.get_mapdata_service", return_value=mock_mapdata):
            result = ctx_svc.resolve_context("The warrior named Varon enters.")

        char_ctx = result.entities[0]
        assert char_ctx.image is not None
        assert char_ctx.image.texture_name == "tex_stormhold"

    def test_returns_empty_when_glossary_not_loaded(self):
        """Empty EntityContext when glossary service has no entities."""
        mock_glossary = MagicMock()
        mock_glossary.detect_entities.return_value = []
        mock_mapdata = MagicMock()

        ctx_svc = ContextService()
        with patch("server.tools.ldm.services.context_service.get_glossary_service", return_value=mock_glossary), \
             patch("server.tools.ldm.services.context_service.get_mapdata_service", return_value=mock_mapdata):
            result = ctx_svc.resolve_context("No entities here.")

        assert len(result.entities) == 0
        assert len(result.detected_in_text) == 0


# =============================================================================
# resolve_context_for_row() Tests
# =============================================================================


class TestResolveContextForRow:
    """Test resolve_context_for_row() combines StringID-direct + text detection."""

    def test_combines_string_id_direct_with_text_detection(self):
        """Row context = direct StringID media + entity detection from text."""
        mock_glossary = MagicMock()
        mock_glossary.detect_entities.return_value = [
            DetectedEntity(term="Varon", start=0, end=5, entity=CHAR_ENTITY)
        ]
        mock_mapdata = MagicMock()
        # Direct StringID lookup returns image+audio
        mock_mapdata.get_image_context.side_effect = lambda key: (
            SAMPLE_IMAGE if key == "ROW_STR_001" else None
        )
        mock_mapdata.get_audio_context.side_effect = lambda key: (
            SAMPLE_AUDIO if key == "ROW_STR_001" else None
        )

        ctx_svc = ContextService()
        with patch("server.tools.ldm.services.context_service.get_glossary_service", return_value=mock_glossary), \
             patch("server.tools.ldm.services.context_service.get_mapdata_service", return_value=mock_mapdata):
            result = ctx_svc.resolve_context_for_row("ROW_STR_001", "Varon speaks.")

        # Should have entity context from text detection
        assert len(result.entities) >= 1
        # Should have direct StringID context
        assert result.string_id_context.get("image") is not None
        assert result.string_id_context.get("audio") is not None


# =============================================================================
# get_status() Tests
# =============================================================================


class TestContextServiceStatus:
    """Test get_status() returns service health info."""

    def test_status_includes_service_info(self):
        mock_glossary = MagicMock()
        mock_glossary.get_status.return_value = {"loaded": True, "entity_count": 50}
        mock_mapdata = MagicMock()
        mock_mapdata.get_status.return_value = {"loaded": True, "image_count": 100}

        ctx_svc = ContextService()
        with patch("server.tools.ldm.services.context_service.get_glossary_service", return_value=mock_glossary), \
             patch("server.tools.ldm.services.context_service.get_mapdata_service", return_value=mock_mapdata):
            status = ctx_svc.get_status()

        assert "glossary" in status
        assert "mapdata" in status
        assert status["glossary"]["loaded"] is True
        assert status["mapdata"]["loaded"] is True


# =============================================================================
# Singleton Tests
# =============================================================================


class TestContextServiceSingleton:
    """Test get_context_service() returns singleton."""

    def test_returns_same_instance(self):
        import server.tools.ldm.services.context_service as mod
        mod._service_instance = None
        svc1 = get_context_service()
        svc2 = get_context_service()
        assert svc1 is svc2
        mod._service_instance = None  # Cleanup
