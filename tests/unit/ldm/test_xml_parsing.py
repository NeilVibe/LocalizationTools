"""
Tests for XMLParsingEngine service.

Covers: sanitizer, parser, language tables, StringIdConsumer, attribute constants.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from server.tools.ldm.services.xml_parsing import (
    XMLParsingEngine,
    StringIdConsumer,
    get_xml_parsing_engine,
    get_attr,
    iter_locstr_elements,
    STRINGID_ATTRS,
    STRORIGIN_ATTRS,
    STR_ATTRS,
    DESC_ATTRS,
    DESCORIGIN_ATTRS,
    LOCSTR_TAGS,
)


FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "xml"


@pytest.fixture
def engine() -> XMLParsingEngine:
    return XMLParsingEngine()


# =========================================================================
# Sanitizer Tests
# =========================================================================


class TestSanitizer:
    def test_sanitizer_removes_control_chars(self, engine: XMLParsingEngine):
        raw = 'Hello\x00World\x08End'
        result = engine.sanitize(raw)
        assert '\x00' not in result
        assert '\x08' not in result
        assert 'Hello' in result
        assert 'World' in result

    def test_sanitizer_fixes_bad_entities(self, engine: XMLParsingEngine):
        raw = '<Root><LocStr Str="Rock & Roll" /></Root>'
        result = engine.sanitize(raw)
        # After sanitizing, bare & should become &amp;
        assert '& ' not in result or '&amp;' in result

    def test_sanitizer_preserves_valid_entities(self, engine: XMLParsingEngine):
        raw = '<Root><LocStr Str="a &lt; b &amp; c" /></Root>'
        result = engine.sanitize(raw)
        assert '&lt;' in result
        assert '&amp;' in result

    def test_sanitizer_fixes_unescaped_lt_in_attrs(self, engine: XMLParsingEngine):
        raw = '<Root><LocStr Str="a<b" /></Root>'
        result = engine.sanitize(raw)
        # Should fix unescaped < inside attribute values
        assert 'a&lt;b' in result or 'a<b' not in result.split('Str="')[1].split('"')[0] if 'Str="' in result else True


# =========================================================================
# Parser Tests
# =========================================================================


class TestParser:
    def test_parse_file_strict_success(self, engine: XMLParsingEngine):
        valid_xml = FIXTURES / "locstr_sample.xml"
        root = engine.parse_file(valid_xml)
        assert root is not None
        assert root.tag == "GameData"

    def test_parse_file_recovery_fallback(self, engine: XMLParsingEngine):
        malformed = FIXTURES / "malformed_sample.xml"
        root = engine.parse_file(malformed)
        # Recovery mode should return a root, not None
        assert root is not None

    def test_parse_file_returns_none_on_total_failure(self, engine: XMLParsingEngine, tmp_path: Path):
        garbage = tmp_path / "garbage.xml"
        garbage.write_bytes(b'\x89PNG\r\n\x1a\n' + bytes(range(256)))
        root = engine.parse_file(garbage)
        assert root is None

    def test_parse_bytes_returns_root_and_encoding(self, engine: XMLParsingEngine):
        content = b'<?xml version="1.0" encoding="utf-8"?>\n<Root><LocStr StringId="1" Str="hello" /></Root>'
        root, encoding = engine.parse_bytes(content, "test.xml")
        assert root is not None
        assert encoding is not None
        assert root.tag == "Root"


# =========================================================================
# Language Table Tests
# =========================================================================


class TestLanguageTables:
    def test_language_table_parsing(self, engine: XMLParsingEngine):
        lang_file = FIXTURES / "languagedata_eng.xml"
        lookup = engine.build_translation_lookup(lang_file)
        assert "LANG_001" in lookup
        assert lookup["LANG_001"]["Str"] == "English text 1"
        assert lookup["LANG_001"]["StrOrigin"] == "Original text 1"
        assert lookup["LANG_001"]["Desc"] == "Eng desc 1"
        assert lookup["LANG_001"]["DescOrigin"] == "Original desc 1"
        # Entry without Desc
        assert "LANG_003" in lookup
        assert lookup["LANG_003"]["Str"] == "English text 3"

    def test_language_table_discovers_files(self, engine: XMLParsingEngine):
        discovered = engine.discover_language_files(FIXTURES)
        assert "eng" in discovered
        assert "kor" in discovered
        assert discovered["eng"].name == "languagedata_eng.xml"
        assert discovered["kor"].name == "languagedata_kor.xml"


# =========================================================================
# StringIdConsumer Tests
# =========================================================================


class TestStringIdConsumer:
    def test_stringid_consumer_basic(self):
        index = {
            "export_key_1": {
                "normalized_text_a": ["SID_001", "SID_002"],
                "normalized_text_b": ["SID_003"],
            }
        }
        consumer = StringIdConsumer(index)
        assert consumer.consume("normalized_text_a", "export_key_1") == "SID_001"
        assert consumer.consume("normalized_text_b", "export_key_1") == "SID_003"

    def test_stringid_consumer_dedup(self):
        index = {
            "key": {
                "same_text": ["SID_A", "SID_B", "SID_C"],
            }
        }
        consumer = StringIdConsumer(index)
        assert consumer.consume("same_text", "key") == "SID_A"
        assert consumer.consume("same_text", "key") == "SID_B"
        assert consumer.consume("same_text", "key") == "SID_C"

    def test_stringid_consumer_exhausted(self):
        index = {
            "key": {
                "text": ["SID_ONLY"],
            }
        }
        consumer = StringIdConsumer(index)
        assert consumer.consume("text", "key") == "SID_ONLY"
        assert consumer.consume("text", "key") is None

    def test_stringid_consumer_fresh_per_language(self):
        index = {
            "key": {
                "text": ["SID_1", "SID_2"],
            }
        }
        consumer1 = StringIdConsumer(index)
        consumer2 = StringIdConsumer(index)
        assert consumer1.consume("text", "key") == "SID_1"
        assert consumer2.consume("text", "key") == "SID_1"  # Independent pointer


# =========================================================================
# Constants & Helpers Tests
# =========================================================================


class TestConstantsAndHelpers:
    def test_attribute_constants(self):
        assert 'StringId' in STRINGID_ATTRS
        assert 'StringID' in STRINGID_ATTRS
        assert 'stringid' in STRINGID_ATTRS
        assert 'STRINGID' in STRINGID_ATTRS
        assert 'Stringid' in STRINGID_ATTRS
        assert 'stringId' in STRINGID_ATTRS

    def test_locstr_tags(self):
        assert 'LocStr' in LOCSTR_TAGS
        assert 'locstr' in LOCSTR_TAGS
        assert 'LOCSTR' in LOCSTR_TAGS
        assert 'LOCStr' in LOCSTR_TAGS
        assert 'Locstr' in LOCSTR_TAGS

    def test_get_attr_helper(self):
        from lxml import etree
        elem = etree.Element("LocStr")
        elem.set("StringID", "TEST_123")
        result = get_attr(elem, STRINGID_ATTRS)
        assert result == "TEST_123"

    def test_get_attr_returns_none_for_missing(self):
        from lxml import etree
        elem = etree.Element("LocStr")
        result = get_attr(elem, STRINGID_ATTRS)
        assert result is None

    def test_iter_locstr_elements(self, engine: XMLParsingEngine):
        root = engine.parse_file(FIXTURES / "locstr_sample.xml")
        assert root is not None
        elements = list(iter_locstr_elements(root))
        # Should find all 5 LocStr variants (LocStr, LocStr, locstr, LOCSTR, Locstr)
        assert len(elements) == 5

    def test_get_xml_parsing_engine_singleton(self):
        e1 = get_xml_parsing_engine()
        e2 = get_xml_parsing_engine()
        assert e1 is e2


# =========================================================================
# Cross-Reference Chain Tests (XML-05)
# =========================================================================


class TestCrossReferenceChain:
    """Test building knowledge tables across multiple XML files."""

    def test_cross_reference_across_files(self, engine: XMLParsingEngine, tmp_path: Path):
        """Two XML files with different KnowledgeInfo -> all entries resolve."""
        from server.tools.ldm.services.mapdata_service import build_knowledge_table

        xml1 = tmp_path / "knowledge_a.xml"
        xml1.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<KnowledgeInfoList>\n'
            '  <KnowledgeInfo StrKey="str_npc_001" UITextureName="tex_npc_001" '
            'Name="Guard" Desc="Guard desc" GroupKey="g1" />\n'
            '</KnowledgeInfoList>\n',
            encoding="utf-8",
        )

        xml2 = tmp_path / "knowledge_b.xml"
        xml2.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<KnowledgeInfoList>\n'
            '  <KnowledgeInfo StrKey="str_item_bow" UITextureName="tex_bow_001" '
            'Name="Longbow" Desc="Ranged weapon" GroupKey="g2" />\n'
            '  <KnowledgeInfo StrKey="str_region_forest" UITextureName="tex_forest" '
            'Name="Dark Forest" Desc="Dangerous area" GroupKey="g3" />\n'
            '</KnowledgeInfoList>\n',
            encoding="utf-8",
        )

        table = build_knowledge_table(tmp_path, engine)
        assert "str_npc_001" in table
        assert "str_item_bow" in table
        assert "str_region_forest" in table
        assert table["str_npc_001"].name == "Guard"
        assert table["str_item_bow"].ui_texture_name == "tex_bow_001"
        assert table["str_region_forest"].source_file == "knowledge_b.xml"
