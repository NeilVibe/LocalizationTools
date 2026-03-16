"""
Tests for GlossaryService -- Aho-Corasick entity detection + glossary extraction.

Phase 5.1: Contextual Intelligence & QA Engine (Plan 01)
"""

from __future__ import annotations

import pytest
from pathlib import Path

from server.tools.ldm.services.glossary_service import (
    GlossaryService,
    get_glossary_service,
    DetectedEntity,
    EntityInfo,
    GlossaryEntry,
)

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "mock_gamedata"


# =============================================================================
# AC Automaton Tests
# =============================================================================


class TestBuildFromEntityNames:
    """Test build_from_entity_names() creates working AC automaton."""

    def test_builds_automaton_from_entity_list(self):
        svc = GlossaryService()
        entities = [
            ("Varon", EntityInfo(type="character", name="Varon", strkey="STR_CHAR_VARON", knowledge_key="KNOW_CHAR_VARON", source_file="characterinfo_sample.xml")),
            ("Stormhold Castle", EntityInfo(type="region", name="Stormhold Castle", strkey="", knowledge_key="KNOW_REGION_STORMHOLD", source_file="regioninfo_sample.xml")),
        ]
        svc.build_from_entity_names(entities)
        assert svc._loaded is True
        assert svc._automaton is not None

    def test_empty_entity_list_still_loads(self):
        svc = GlossaryService()
        svc.build_from_entity_names([])
        assert svc._loaded is True


# =============================================================================
# Entity Detection Tests
# =============================================================================


class TestDetectEntities:
    """Test detect_entities() scans text with AC automaton."""

    @pytest.fixture
    def loaded_service(self):
        svc = GlossaryService()
        entities = [
            ("Varon", EntityInfo(type="character", name="Varon", strkey="STR_CHAR_VARON", knowledge_key="KNOW_CHAR_VARON", source_file="char.xml")),
            ("Stormhold Castle", EntityInfo(type="region", name="Stormhold Castle", strkey="", knowledge_key="KNOW_REGION_STORMHOLD", source_file="region.xml")),
            ("Iron Sword", EntityInfo(type="item", name="Iron Sword", strkey="STR_ITEM_IRON_SWORD", knowledge_key="", source_file="item.xml")),
        ]
        svc.build_from_entity_names(entities)
        return svc

    def test_detects_single_entity(self, loaded_service):
        results = loaded_service.detect_entities("The elder Varon spoke wisely.")
        names = [r.term for r in results]
        assert "Varon" in names

    def test_detects_multiple_entities(self, loaded_service):
        results = loaded_service.detect_entities("Varon entered Stormhold Castle with an Iron Sword.")
        names = [r.term for r in results]
        assert "Varon" in names
        assert "Stormhold Castle" in names
        assert "Iron Sword" in names

    def test_returns_detected_entity_with_positions(self, loaded_service):
        results = loaded_service.detect_entities("The elder Varon spoke.")
        varon = [r for r in results if r.term == "Varon"][0]
        assert varon.start == 10
        assert varon.end == 15
        assert varon.entity.type == "character"

    def test_korean_word_boundary_prevents_false_match(self):
        """Korean compound words should not produce false matches."""
        svc = GlossaryService()
        entities = [
            ("검", EntityInfo(type="item", name="검", strkey="STR_SWORD", knowledge_key="", source_file="item.xml")),
        ]
        svc.build_from_entity_names(entities)
        # "검" embedded in compound word "검사" should NOT match (not isolated)
        results = svc.detect_entities("그 검사는 강하다")
        assert len(results) == 0

    def test_korean_isolated_match_succeeds(self):
        """Korean entity surrounded by spaces should match."""
        svc = GlossaryService()
        entities = [
            ("검", EntityInfo(type="item", name="검", strkey="STR_SWORD", knowledge_key="", source_file="item.xml")),
        ]
        svc.build_from_entity_names(entities)
        # "검" isolated by spaces should match
        results = svc.detect_entities("그 검 은 강하다")
        assert len(results) == 1
        assert results[0].term == "검"

    def test_returns_empty_when_not_loaded(self):
        svc = GlossaryService()
        results = svc.detect_entities("Varon entered Stormhold Castle.")
        assert results == []


# =============================================================================
# XML Extraction Tests
# =============================================================================


class TestExtractGlossaryFromXML:
    """Test XML extraction methods."""

    def test_extract_character_glossary(self):
        svc = GlossaryService()
        entries = svc.extract_character_glossary(FIXTURES_DIR)
        names = [name for name, info in entries]
        assert "Varon" in names
        assert "Kira" in names
        assert "Drakmar" in names
        assert len(entries) >= 5  # expanded mock data has 43+ characters

    def test_character_entries_have_strkey_and_knowledge_key(self):
        svc = GlossaryService()
        entries = svc.extract_character_glossary(FIXTURES_DIR)
        varon = [(n, i) for n, i in entries if n == "Varon"][0]
        assert varon[1].strkey == "STR_CHAR_VARON"
        assert varon[1].knowledge_key == "KNOW_CHAR_VARON"
        assert varon[1].type == "character"

    def test_extract_item_glossary(self):
        svc = GlossaryService()
        entries = svc.extract_item_glossary(FIXTURES_DIR)
        names = [name for name, info in entries]
        assert "Iron Sword" in names
        assert "Health Potion" in names
        assert len(entries) >= 5  # expanded mock data has 130+ items

    def test_item_entries_have_strkey(self):
        svc = GlossaryService()
        entries = svc.extract_item_glossary(FIXTURES_DIR)
        sword = [(n, i) for n, i in entries if n == "Iron Sword"][0]
        assert sword[1].strkey == "STR_ITEM_IRON_SWORD"
        assert sword[1].type == "item"

    def test_extract_region_glossary(self):
        svc = GlossaryService()
        entries = svc.extract_region_glossary(FIXTURES_DIR)
        names = [name for name, info in entries]
        assert "Stormhold Castle" in names
        assert "Ashenvale Forest" in names
        assert len(entries) == 3

    def test_region_entries_have_knowledge_key(self):
        svc = GlossaryService()
        entries = svc.extract_region_glossary(FIXTURES_DIR)
        storm = [(n, i) for n, i in entries if n == "Stormhold Castle"][0]
        assert storm[1].knowledge_key == "KNOW_REGION_STORMHOLD"
        assert storm[1].type == "region"


# =============================================================================
# Glossary Filter Tests
# =============================================================================


class TestGlossaryFilter:
    """Test glossary_filter() removes noise."""

    def test_filters_long_terms(self):
        svc = GlossaryService()
        entities = [
            ("Short", EntityInfo(type="item", name="Short", strkey="S", knowledge_key="", source_file="x.xml")),
            ("A" * 30, EntityInfo(type="item", name="A" * 30, strkey="L", knowledge_key="", source_file="x.xml")),
        ]
        filtered = svc.glossary_filter(entities, max_term_length=25, min_occurrence=1)
        names = [n for n, _ in filtered]
        assert "Short" in names
        assert ("A" * 30) not in names

    def test_filters_sentences(self):
        svc = GlossaryService()
        entities = [
            ("Iron Sword", EntityInfo(type="item", name="Iron Sword", strkey="S1", knowledge_key="", source_file="x.xml")),
            ("This is a sentence.", EntityInfo(type="item", name="This is a sentence.", strkey="S2", knowledge_key="", source_file="x.xml")),
        ]
        filtered = svc.glossary_filter(entities, min_occurrence=1)
        names = [n for n, _ in filtered]
        assert "Iron Sword" in names
        assert "This is a sentence." not in names

    def test_filters_punctuation(self):
        svc = GlossaryService()
        entities = [
            ("Clean", EntityInfo(type="item", name="Clean", strkey="S1", knowledge_key="", source_file="x.xml")),
            ("Not,Clean", EntityInfo(type="item", name="Not,Clean", strkey="S2", knowledge_key="", source_file="x.xml")),
        ]
        filtered = svc.glossary_filter(entities, min_occurrence=1)
        names = [n for n, _ in filtered]
        assert "Clean" in names
        assert "Not,Clean" not in names

    def test_filters_min_occurrence(self):
        svc = GlossaryService()
        entities = [
            ("Varon", EntityInfo(type="character", name="Varon", strkey="S1", knowledge_key="", source_file="x.xml")),
            ("Varon", EntityInfo(type="character", name="Varon", strkey="S2", knowledge_key="", source_file="y.xml")),
            ("Unique", EntityInfo(type="character", name="Unique", strkey="S3", knowledge_key="", source_file="z.xml")),
        ]
        filtered = svc.glossary_filter(entities, min_occurrence=2)
        names = [n for n, _ in filtered]
        assert "Varon" in names
        assert "Unique" not in names


# =============================================================================
# Entity Index Tests
# =============================================================================


class TestEntityIndex:
    """Test entity_index maps terms to datapoint info."""

    def test_entity_index_populated(self):
        svc = GlossaryService()
        entities = [
            ("Varon", EntityInfo(type="character", name="Varon", strkey="STR_CHAR_VARON", knowledge_key="KNOW_CHAR_VARON", source_file="char.xml")),
        ]
        svc.build_from_entity_names(entities)
        assert "Varon" in svc._entity_index
        info = svc._entity_index["Varon"]
        assert info.strkey == "STR_CHAR_VARON"
        assert info.knowledge_key == "KNOW_CHAR_VARON"
        assert info.type == "character"
        assert info.source_file == "char.xml"


# =============================================================================
# Status Tests
# =============================================================================


class TestGetStatus:
    """Test get_status() reports service state."""

    def test_status_when_not_loaded(self):
        svc = GlossaryService()
        status = svc.get_status()
        assert status["loaded"] is False
        assert status["entity_count"] == 0

    def test_status_when_loaded(self):
        svc = GlossaryService()
        entities = [
            ("Varon", EntityInfo(type="character", name="Varon", strkey="S1", knowledge_key="K1", source_file="c.xml")),
            ("Iron Sword", EntityInfo(type="item", name="Iron Sword", strkey="S2", knowledge_key="", source_file="i.xml")),
        ]
        svc.build_from_entity_names(entities)
        status = svc.get_status()
        assert status["loaded"] is True
        assert status["entity_count"] == 2
        assert status["counts_by_type"]["character"] == 1
        assert status["counts_by_type"]["item"] == 1


# =============================================================================
# Singleton Tests
# =============================================================================


# =============================================================================
# XMLParsingEngine Delegation Tests
# =============================================================================


class TestParseXmlDelegation:
    """Test _parse_xml() delegates to XMLParsingEngine."""

    def test_parse_xml_uses_xml_parsing_engine(self, tmp_path):
        """_parse_xml delegates to XMLParsingEngine.parse_file."""
        xml_file = tmp_path / "test_char.xml"
        xml_file.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<Root><CharacterInfo CharacterName="Test" StrKey="S1" KnowledgeKey="K1" /></Root>',
            encoding="utf-8",
        )
        svc = GlossaryService()
        root = svc._parse_xml(xml_file)
        assert root is not None
        assert root.tag == "Root"

    def test_parse_xml_handles_malformed(self, tmp_path):
        """_parse_xml handles malformed XML via engine recovery."""
        xml_file = tmp_path / "bad.xml"
        xml_file.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<Root><Item Name="Broken & Unescaped" /></Root>',
            encoding="utf-8",
        )
        svc = GlossaryService()
        root = svc._parse_xml(xml_file)
        # Engine sanitizer fixes bare ampersand, recovery mode parses
        assert root is not None

    def test_initialize_converts_wsl_paths(self, tmp_path):
        """initialize() converts Windows paths to WSL paths."""
        # Create character folder with a fixture
        char_dir = tmp_path / "characters"
        char_dir.mkdir()
        (char_dir / "characterinfo_test.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<Root><CharacterInfo CharacterName="Hero" StrKey="S1" KnowledgeKey="K1" />'
            '<CharacterInfo CharacterName="Hero" StrKey="S2" KnowledgeKey="K2" />'
            '</Root>',
            encoding="utf-8",
        )

        svc = GlossaryService()
        # Pass already-unix path (should pass through unchanged)
        paths = {"character_folder": str(char_dir)}
        result = svc.initialize(paths)
        assert result is True


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingleton:
    """Test get_glossary_service() returns singleton."""

    def test_returns_same_instance(self):
        # Reset singleton for test isolation
        import server.tools.ldm.services.glossary_service as mod
        mod._service_instance = None
        svc1 = get_glossary_service()
        svc2 = get_glossary_service()
        assert svc1 is svc2
        mod._service_instance = None  # Cleanup
