"""Unit tests for AIImageService -- Gemini image generation + disk cache.

Phase 31: Codex AI Image Generation (Plan 01, Task 1)
Tests service layer: prompt templates, cache, sanitization, Gemini wrapping.
All Gemini API calls are mocked -- NEVER hits real API.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_entity():
    """Build a sample CodexEntity with full attributes for testing."""
    from server.tools.ldm.schemas.codex import CodexEntity

    return CodexEntity(
        entity_type="character",
        strkey="Warrior_001",
        name="Aelric the Bold",
        description="A legendary warrior from the Northern Kingdoms.",
        knowledge_key="KnowledgeWarrior001",
        image_texture="warrior_tex",
        audio_key="Warrior_001",
        source_file="/some/path.xml",
        attributes={
            "Race": "Human",
            "Job": "Knight",
            "Grade": "Epic",
            "Level": "50",
        },
        related_entities=["item/Sword_001"],
    )


@pytest.fixture()
def item_entity():
    from server.tools.ldm.schemas.codex import CodexEntity

    return CodexEntity(
        entity_type="item",
        strkey="Sword_002",
        name="Blade of Dawn",
        description="A radiant sword forged in ancient fire.",
        source_file="/items.xml",
        attributes={"ItemType": "Weapon", "Grade": "Rare"},
    )


@pytest.fixture()
def region_entity():
    from server.tools.ldm.schemas.codex import CodexEntity

    return CodexEntity(
        entity_type="region",
        strkey="Region_Frost",
        name="Frostpeak Mountains",
        description="Jagged peaks eternally cloaked in snow.",
        source_file="/regions.xml",
        attributes={},
    )


@pytest.fixture()
def skill_entity():
    from server.tools.ldm.schemas.codex import CodexEntity

    return CodexEntity(
        entity_type="skill",
        strkey="Skill_Fireball",
        name="Fireball",
        description="Hurls a ball of fire.",
        source_file="/skills.xml",
        attributes={},
    )


@pytest.fixture()
def gimmick_entity():
    from server.tools.ldm.schemas.codex import CodexEntity

    return CodexEntity(
        entity_type="gimmick",
        strkey="Seal_Dark",
        name="Dark Seal",
        description="Binds dark energy.",
        source_file="/gimmicks.xml",
        attributes={},
    )


@pytest.fixture()
def minimal_entity():
    """Entity with no description or attributes -- tests graceful degradation."""
    from server.tools.ldm.schemas.codex import CodexEntity

    return CodexEntity(
        entity_type="knowledge",
        strkey="Know_001",
        name="Ancient Lore",
        source_file="/knowledge.xml",
    )


@pytest.fixture()
def _mock_genai():
    """Mock google.genai so AIImageService can be imported without real SDK."""
    mock_genai = MagicMock()
    mock_types = MagicMock()
    mock_genai.Client = MagicMock
    mock_types.GenerateContentConfig = MagicMock
    mock_types.ImageConfig = MagicMock
    sys.modules["google"] = MagicMock()
    sys.modules["google.genai"] = mock_genai
    sys.modules["google.genai.types"] = mock_types
    yield mock_genai, mock_types
    # Cleanup
    for mod in ["google", "google.genai", "google.genai.types"]:
        sys.modules.pop(mod, None)


@pytest.fixture()
def service_available(tmp_path, _mock_genai):
    """AIImageService with GEMINI_API_KEY set (available)."""
    # Need to reimport after mocking
    if "server.tools.ldm.services.ai_image_service" in sys.modules:
        del sys.modules["server.tools.ldm.services.ai_image_service"]

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123"}):
        from server.tools.ldm.services.ai_image_service import AIImageService

        svc = AIImageService()
        svc.CACHE_DIR = tmp_path / "cache" / "ai_images" / "by_strkey"
        svc.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        yield svc


@pytest.fixture()
def service_unavailable(tmp_path, _mock_genai):
    """AIImageService with no GEMINI_API_KEY (unavailable)."""
    if "server.tools.ldm.services.ai_image_service" in sys.modules:
        del sys.modules["server.tools.ldm.services.ai_image_service"]

    env = os.environ.copy()
    env.pop("GEMINI_API_KEY", None)
    with patch.dict(os.environ, env, clear=True):
        from server.tools.ldm.services.ai_image_service import AIImageService

        svc = AIImageService()
        svc.CACHE_DIR = tmp_path / "cache" / "ai_images" / "by_strkey"
        svc.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        yield svc


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestInit:
    def test_no_api_key_sets_unavailable(self, service_unavailable):
        assert service_unavailable.available is False

    def test_with_api_key_sets_available(self, service_available):
        assert service_available.available is True

    def test_with_api_key_creates_client(self, service_available):
        assert service_available._client is not None


# ---------------------------------------------------------------------------
# Tests: Cache operations
# ---------------------------------------------------------------------------


class TestCache:
    def test_get_cached_path_returns_none_when_missing(self, service_available):
        result = service_available.get_cached_image_path("NonExistent_Key")
        assert result is None

    def test_get_cached_path_returns_path_when_exists(self, service_available, tmp_path):
        strkey = "Warrior_001"
        img_dir = service_available.CACHE_DIR / strkey
        img_dir.mkdir(parents=True, exist_ok=True)
        (img_dir / "generated.png").write_bytes(b"\x89PNG_FAKE")

        result = service_available.get_cached_image_path(strkey)
        assert result is not None
        assert result.name == "generated.png"

    def test_save_to_cache_writes_png_and_metadata(self, service_available):
        strkey = "Test_Entity"
        png_bytes = b"\x89PNG_TEST_DATA"
        prompt = "A test prompt"

        saved_path = service_available.save_to_cache(strkey, png_bytes, prompt)

        assert saved_path.exists()
        assert saved_path.read_bytes() == png_bytes

        meta_path = saved_path.parent / "metadata.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["prompt"] == prompt
        assert "generated_at" in meta
        assert "model" in meta


# ---------------------------------------------------------------------------
# Tests: Prompt building
# ---------------------------------------------------------------------------


class TestPromptBuilding:
    def test_character_prompt_includes_race_job(self, service_available, sample_entity):
        prompt = service_available.build_prompt(sample_entity)
        assert "Aelric the Bold" in prompt
        assert "Human" in prompt
        assert "Knight" in prompt

    def test_item_prompt_includes_item_type(self, service_available, item_entity):
        prompt = service_available.build_prompt(item_entity)
        assert "Blade of Dawn" in prompt
        assert "Weapon" in prompt

    def test_region_prompt_includes_landscape(self, service_available, region_entity):
        prompt = service_available.build_prompt(region_entity)
        assert "Frostpeak Mountains" in prompt
        assert "landscape" in prompt.lower()

    def test_skill_prompt_includes_skill_icon(self, service_available, skill_entity):
        prompt = service_available.build_prompt(skill_entity)
        assert "Fireball" in prompt
        assert "skill" in prompt.lower()

    def test_gimmick_prompt_includes_sigil(self, service_available, gimmick_entity):
        prompt = service_available.build_prompt(gimmick_entity)
        assert "Dark Seal" in prompt
        assert "sigil" in prompt.lower()

    def test_graceful_degradation_missing_attrs(self, service_available, minimal_entity):
        prompt = service_available.build_prompt(minimal_entity)
        assert "Ancient Lore" in prompt
        # Should use fallback template, not crash
        assert "fantasy" in prompt.lower() or "knowledge" in prompt.lower()


# ---------------------------------------------------------------------------
# Tests: Aspect ratio
# ---------------------------------------------------------------------------


class TestAspectRatio:
    def test_character_portrait(self, service_available):
        assert service_available._get_aspect_ratio("character") == "3:4"

    def test_item_square(self, service_available):
        assert service_available._get_aspect_ratio("item") == "1:1"

    def test_skill_square(self, service_available):
        assert service_available._get_aspect_ratio("skill") == "1:1"

    def test_gimmick_square(self, service_available):
        assert service_available._get_aspect_ratio("gimmick") == "1:1"

    def test_region_landscape(self, service_available):
        assert service_available._get_aspect_ratio("region") == "16:9"

    def test_unknown_defaults_to_square(self, service_available):
        assert service_available._get_aspect_ratio("unknown_type") == "1:1"


# ---------------------------------------------------------------------------
# Tests: Generate image
# ---------------------------------------------------------------------------


class TestGenerateImage:
    def test_generate_calls_gemini_client(self, service_available, sample_entity):
        mock_part = MagicMock()
        mock_part.inline_data.data = b"\x89PNG_GENERATED"
        mock_response = MagicMock()
        mock_response.parts = [mock_part]

        service_available._client.models.generate_content = MagicMock(
            return_value=mock_response
        )

        result = service_available.generate_image(sample_entity)
        assert result == b"\x89PNG_GENERATED"
        service_available._client.models.generate_content.assert_called_once()

    def test_generate_raises_when_no_image(self, service_available, sample_entity):
        mock_part = MagicMock()
        mock_part.inline_data = None
        mock_response = MagicMock()
        mock_response.parts = [mock_part]

        service_available._client.models.generate_content = MagicMock(
            return_value=mock_response
        )

        with pytest.raises(ValueError, match="No image"):
            service_available.generate_image(sample_entity)


# ---------------------------------------------------------------------------
# Tests: StrKey sanitization
# ---------------------------------------------------------------------------


class TestSanitization:
    def test_strips_path_traversal(self, service_available):
        sanitized = service_available._sanitize_strkey("../../../etc/passwd")
        assert ".." not in sanitized
        assert "/" not in sanitized

    def test_strips_backslashes(self, service_available):
        sanitized = service_available._sanitize_strkey("key\\with\\backslash")
        assert "\\" not in sanitized

    def test_strips_null_bytes(self, service_available):
        sanitized = service_available._sanitize_strkey("key\x00null")
        assert "\x00" not in sanitized


# ---------------------------------------------------------------------------
# Tests: Schema extension
# ---------------------------------------------------------------------------


class TestSchemaExtension:
    def test_codex_entity_has_ai_image_url(self):
        from server.tools.ldm.schemas.codex import CodexEntity

        e = CodexEntity(
            entity_type="item",
            strkey="test",
            name="Test",
            source_file="f.xml",
        )
        assert hasattr(e, "ai_image_url")
        assert e.ai_image_url is None

    def test_codex_entity_ai_image_url_settable(self):
        from server.tools.ldm.schemas.codex import CodexEntity

        e = CodexEntity(
            entity_type="item",
            strkey="test",
            name="Test",
            source_file="f.xml",
            ai_image_url="/api/ldm/codex/image/test",
        )
        assert e.ai_image_url == "/api/ldm/codex/image/test"
