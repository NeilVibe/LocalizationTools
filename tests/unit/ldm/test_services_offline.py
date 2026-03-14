"""
Validation: Phase 5/5.1 in-memory services degrade gracefully when not configured.

In offline demo mode, Perforce paths don't exist and services are never configure()'d.
This test proves they return empty data (not errors) -- so the UI shows no error popups.

Also validates offline_qa_results schema has check_type column.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from server.tools.ldm.services.mapdata_service import MapDataService
from server.tools.ldm.services.glossary_service import GlossaryService
from server.tools.ldm.services.context_service import ContextService, EntityContext
from server.tools.ldm.services.category_mapper import TwoTierCategoryMapper


# =============================================================================
# MapDataService: not configured
# =============================================================================


class TestMapDataServiceNotConfigured:
    """MapDataService returns None/empty when never initialized."""

    def test_not_loaded_on_init(self):
        svc = MapDataService()
        status = svc.get_status()
        assert status["loaded"] is False
        assert status["image_count"] == 0
        assert status["audio_count"] == 0

    def test_get_image_context_returns_none(self):
        svc = MapDataService()
        result = svc.get_image_context("ANY_STRING_ID")
        assert result is None

    def test_get_audio_context_returns_none(self):
        svc = MapDataService()
        result = svc.get_audio_context("ANY_STRING_ID")
        assert result is None


# =============================================================================
# GlossaryService: not configured
# =============================================================================


class TestGlossaryServiceNotConfigured:
    """GlossaryService returns empty when AC automaton never built."""

    def test_not_loaded_on_init(self):
        svc = GlossaryService()
        assert svc._loaded is False
        assert svc._automaton is None

    def test_detect_entities_returns_empty(self):
        svc = GlossaryService()
        result = svc.detect_entities("The warrior enters Stormhold Castle")
        assert result == []

    def test_get_status_shows_unloaded(self):
        svc = GlossaryService()
        status = svc.get_status()
        assert status["loaded"] is False
        assert status["entity_count"] == 0

    def test_get_glossary_terms_returns_empty(self):
        svc = GlossaryService()
        terms = svc.get_glossary_terms()
        assert terms == []


# =============================================================================
# ContextService: not configured (both sub-services unconfigured)
# =============================================================================


class TestContextServiceNotConfigured:
    """ContextService returns empty EntityContext when glossary+mapdata not loaded."""

    def test_resolve_context_returns_empty(self):
        """Fresh ContextService with unconfigured sub-services returns empty context."""
        svc = ContextService()
        # Patch sub-services to fresh (unconfigured) instances
        svc._glossary = GlossaryService()
        svc._mapdata = MapDataService()

        result = svc.resolve_context("The warrior enters Stormhold Castle")
        assert isinstance(result, EntityContext)
        assert result.entities == []
        assert result.detected_in_text == []

    def test_resolve_context_for_row_returns_empty(self):
        """resolve_context_for_row returns empty when nothing configured."""
        svc = ContextService()
        svc._glossary = GlossaryService()
        svc._mapdata = MapDataService()

        result = svc.resolve_context_for_row("SOME_STRING_ID", "Some text")
        assert isinstance(result, EntityContext)
        assert result.entities == []
        assert result.detected_in_text == []

    def test_get_status_shows_unloaded(self):
        """Status reflects unconfigured state for both sub-services."""
        svc = ContextService()
        svc._glossary = GlossaryService()
        svc._mapdata = MapDataService()

        status = svc.get_status()
        assert status["glossary"]["loaded"] is False
        assert status["mapdata"]["loaded"] is False


# =============================================================================
# CategoryMapper: works without configuration (stateless)
# =============================================================================


class TestCategoryMapperDefault:
    """CategoryMapper is stateless -- returns valid categories always."""

    def test_unknown_path_returns_other(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("some/unknown/path.xml")
        assert result == "Other"

    def test_dialog_path_returns_dialog(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("game/dialog/npc_quest.xml")
        assert result == "Dialog"

    def test_empty_path_returns_other(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("")
        assert result == "Other"


# =============================================================================
# Schema Validation: offline_qa_results has check_type column
# =============================================================================


class TestOfflineSchemaCheckType:
    """Verify offline_schema.sql defines check_type in offline_qa_results."""

    def test_check_type_in_offline_schema(self):
        """Parse offline_schema.sql and confirm check_type TEXT NOT NULL exists."""
        schema_path = (
            Path(__file__).parent.parent.parent.parent
            / "server" / "database" / "offline_schema.sql"
        )
        assert schema_path.exists(), f"offline_schema.sql not found at {schema_path}"

        schema_sql = schema_path.read_text(encoding="utf-8")

        # Find the offline_qa_results CREATE TABLE block
        assert "offline_qa_results" in schema_sql, "offline_qa_results table missing from schema"

        # Extract the CREATE TABLE block for offline_qa_results
        start = schema_sql.index("CREATE TABLE IF NOT EXISTS offline_qa_results")
        end = schema_sql.index(");", start) + 2
        create_block = schema_sql[start:end]

        assert "check_type TEXT NOT NULL" in create_block, (
            "check_type column missing or not NOT NULL in offline_qa_results. "
            "Block:\n" + create_block
        )

    def test_check_type_indexes_exist(self):
        """Verify indexes on check_type exist in offline schema."""
        schema_path = (
            Path(__file__).parent.parent.parent.parent
            / "server" / "database" / "offline_schema.sql"
        )
        schema_sql = schema_path.read_text(encoding="utf-8")

        assert "idx_offline_qa_results_type" in schema_sql, (
            "Missing index on offline_qa_results(check_type)"
        )
