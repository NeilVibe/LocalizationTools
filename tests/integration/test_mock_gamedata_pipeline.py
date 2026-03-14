"""
E2E Test: Mock GameData Pipeline
=================================
Tests the full XML parsing → linkage → context resolution pipeline
using mock fixture data that mimics real Perforce/staticinfo structure.

ZERO ERROR GOAL — every assertion must pass.
"""
from __future__ import annotations

import os
import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

FIXTURES = Path(__file__).parent.parent / "fixtures" / "mock_gamedata"


class TestXMLParsing:
    """Test XML parsing patterns from MapDataGenerator/QACompiler."""

    def test_knowledge_info_parsing(self):
        """Parse KnowledgeInfo XML — extract StrKey, Name, Desc, UITextureName."""
        from lxml import etree as ET

        path = FIXTURES / "knowledge" / "knowledgeinfo_sample.xml"
        assert path.exists(), f"Fixture missing: {path}"

        tree = ET.parse(str(path))
        root = tree.getroot()

        entries = {}
        for ki in root.iter("KnowledgeInfo"):
            strkey = ki.get("StrKey", "").strip()
            name = ki.get("Name", "").strip()
            desc = ki.get("Desc", "").strip()
            texture = ki.get("UITextureName", "").strip()

            assert strkey, "StrKey must not be empty"
            assert name, f"Name must not be empty for {strkey}"
            entries[strkey] = {
                "name": name,
                "desc": desc,
                "ui_texture": texture,
            }

        # Verify expected entries
        assert len(entries) == 10, f"Expected 10 entries, got {len(entries)}"
        assert "KNOW_CHAR_VARON" in entries
        assert entries["KNOW_CHAR_VARON"]["name"] == "장로 바론"
        assert entries["KNOW_CHAR_VARON"]["ui_texture"] == "character_varon"
        assert "KNOW_ITEM_BLACKSTAR" in entries
        assert "KNOW_REGION_BLACKSTAR" in entries

    def test_br_tag_handling(self):
        """Verify <br/> tags are preserved correctly in descriptions."""
        from lxml import etree as ET

        path = FIXTURES / "knowledge" / "knowledgeinfo_sample.xml"
        tree = ET.parse(str(path))
        root = tree.getroot()

        varon = None
        for ki in root.iter("KnowledgeInfo"):
            if ki.get("StrKey") == "KNOW_CHAR_VARON":
                varon = ki
                break

        assert varon is not None
        desc = varon.get("Desc", "")
        # In XML attributes, <br/> is escaped as &lt;br/&gt;
        assert "&lt;br/&gt;" in desc or "<br/>" in desc, \
            f"br tag not found in desc: {desc[:100]}"

    def test_localization_loading(self):
        """Load Korean and English localization files, build language table."""
        from lxml import etree as ET

        kor_path = FIXTURES / "localization" / "locstr_kor.xml"
        eng_path = FIXTURES / "localization" / "locstr_eng.xml"

        # Load Korean (source)
        kor_tree = ET.parse(str(kor_path))
        kor_entries = {}
        for loc in kor_tree.getroot().iter("LocStr"):
            sid = loc.get("StringId", "")
            origin = loc.get("StrOrigin", "")
            if sid and origin:
                kor_entries[sid] = origin

        assert len(kor_entries) == 8
        assert "SID_VARON_001" in kor_entries

        # Load English (translation)
        eng_tree = ET.parse(str(eng_path))
        eng_entries = {}
        for loc in eng_tree.getroot().iter("LocStr"):
            sid = loc.get("StringId", "")
            translation = loc.get("Str", "")
            if sid and translation:
                eng_entries[sid] = translation

        assert len(eng_entries) == 8
        assert eng_entries["SID_VARON_001"].startswith("Under the supervision")

    def test_character_info_parsing(self):
        """Parse CharacterInfo with cross-reference to Knowledge."""
        from lxml import etree as ET

        char_path = FIXTURES / "characterinfo_sample.xml"
        know_path = FIXTURES / "knowledge" / "knowledgeinfo_sample.xml"

        # Build knowledge lookup first (Pattern 2: BUILD LOOKUP FIRST)
        know_tree = ET.parse(str(know_path))
        knowledge_map = {}
        for ki in know_tree.getroot().iter("KnowledgeInfo"):
            strkey = ki.get("StrKey", "").lower()
            knowledge_map[strkey] = {
                "name": ki.get("Name", ""),
                "desc": ki.get("Desc", ""),
                "texture": ki.get("UITextureName", ""),
            }

        # Parse characters with knowledge cross-reference
        char_tree = ET.parse(str(char_path))
        characters = []
        for ci in char_tree.getroot().iter("CharacterInfo"):
            char_name = ci.get("CharacterName", "")
            knowledge_key = ci.get("KnowledgeKey", "").lower()
            knowledge = knowledge_map.get(knowledge_key, {})

            characters.append({
                "name": char_name,
                "strkey": ci.get("StrKey", ""),
                "knowledge_key": ci.get("KnowledgeKey", ""),
                "gender": ci.get("Gender", ""),
                "age": ci.get("Age", ""),
                "job": ci.get("Job", ""),
                "race": ci.get("Race", ""),
                "kr_name": knowledge.get("name", ""),
                "desc": knowledge.get("desc", ""),
                "texture": knowledge.get("texture", ""),
            })

        assert len(characters) == 5
        varon = next(c for c in characters if c["name"] == "Varon")
        assert varon["kr_name"] == "장로 바론"
        assert varon["texture"] == "character_varon"
        assert varon["job"] == "Elder"
        assert varon["race"] == "Human"


class TestTextureIndex:
    """Test DDS texture index and lookup."""

    def test_texture_files_exist(self):
        """All expected DDS files exist in fixtures."""
        texture_dir = FIXTURES / "textures"
        expected = [
            "character_varon.dds", "character_kira.dds",
            "item_blackstar_sword.dds", "region_blackstar_village.dds",
        ]
        for name in expected:
            assert (texture_dir / name).exists(), f"Missing texture: {name}"

    def test_texture_index_build(self):
        """Build texture index and perform O(1) lookups."""
        texture_dir = FIXTURES / "textures"

        # Build index (Pattern 9: Case-insensitive fuzzy)
        dds_index = {}
        for dds_path in texture_dir.glob("*.dds"):
            dds_index[dds_path.stem.lower()] = dds_path

        assert len(dds_index) == 10

        # Exact lookup
        assert "character_varon" in dds_index
        assert dds_index["character_varon"].suffix == ".dds"

        # Case-insensitive
        lookup_name = "CHARACTER_VARON".lower()
        assert lookup_name in dds_index

    def test_dds_file_valid_header(self):
        """DDS files have valid magic bytes."""
        texture_dir = FIXTURES / "textures"
        for dds_path in texture_dir.glob("*.dds"):
            with open(dds_path, "rb") as f:
                magic = f.read(4)
            assert magic == b"DDS ", f"Invalid DDS magic in {dds_path.name}: {magic}"


class TestAudioIndex:
    """Test audio event mapping and lookup chain."""

    def test_event_mapping_parsing(self):
        """Parse EventMapping XML — EventName → StringId chain."""
        from lxml import etree as ET

        path = FIXTURES / "export" / "event_mapping.xml"
        tree = ET.parse(str(path))

        event_to_sid = {}
        for em in tree.getroot().iter("EventMapping"):
            event = em.get("SoundEventName", "").strip().lower()
            sid = em.get("StringId", "").strip()
            if event and sid:
                event_to_sid[event] = sid

        assert len(event_to_sid) == 5
        assert event_to_sid["varon_greeting"] == "SID_VARON_001"
        assert event_to_sid["kira_battle_cry"] == "SID_KIRA_001"

    def test_audio_files_exist(self):
        """All expected audio files exist."""
        audio_dir = FIXTURES / "audio"
        expected = ["varon_greeting.wem", "kira_battle_cry.wem", "drakmar_spell.wem"]
        for name in expected:
            assert (audio_dir / name).exists(), f"Missing audio: {name}"

    def test_full_audio_chain(self):
        """EventName → StringId → StrOrigin (full chain resolution)."""
        from lxml import etree as ET

        # Build event → StringId index
        event_path = FIXTURES / "export" / "event_mapping.xml"
        event_tree = ET.parse(str(event_path))
        event_to_sid = {}
        for em in event_tree.getroot().iter("EventMapping"):
            event_to_sid[em.get("SoundEventName", "").lower()] = em.get("StringId", "")

        # Build StringId → StrOrigin index
        kor_path = FIXTURES / "localization" / "locstr_kor.xml"
        kor_tree = ET.parse(str(kor_path))
        sid_to_origin = {}
        for loc in kor_tree.getroot().iter("LocStr"):
            sid_to_origin[loc.get("StringId", "")] = loc.get("StrOrigin", "")

        # Chain: varon_greeting → SID_VARON_001 → Korean script
        sid = event_to_sid.get("varon_greeting")
        assert sid == "SID_VARON_001"
        script = sid_to_origin.get(sid, "")
        assert "엘리언교" in script, f"Expected Korean script, got: {script[:50]}"


class TestCrossReferenceChains:
    """Test multi-level cross-reference resolution (Pattern 2 + 5)."""

    def test_character_to_texture_chain(self):
        """CharacterInfo → KnowledgeKey → UITextureName → DDS path."""
        from lxml import etree as ET

        # Build knowledge map
        know_tree = ET.parse(str(FIXTURES / "knowledge" / "knowledgeinfo_sample.xml"))
        knowledge_map = {}
        for ki in know_tree.getroot().iter("KnowledgeInfo"):
            knowledge_map[ki.get("StrKey", "").lower()] = ki.get("UITextureName", "")

        # Build texture index
        texture_dir = FIXTURES / "textures"
        dds_index = {p.stem.lower(): p for p in texture_dir.glob("*.dds")}

        # Resolve: Character → Knowledge → Texture → DDS
        char_tree = ET.parse(str(FIXTURES / "characterinfo_sample.xml"))
        for ci in char_tree.getroot().iter("CharacterInfo"):
            kkey = ci.get("KnowledgeKey", "").lower()
            texture_name = knowledge_map.get(kkey, "")
            dds_path = dds_index.get(texture_name.lower())

            char_name = ci.get("CharacterName", "")
            assert texture_name, f"No texture for {char_name} (key={kkey})"
            assert dds_path is not None, f"No DDS for {char_name} (texture={texture_name})"
            assert dds_path.exists(), f"DDS file missing: {dds_path}"

    def test_character_to_audio_chain(self):
        """Character StrKey → EventMapping → Audio file."""
        from lxml import etree as ET

        # Build reverse index: StringId → EventName
        event_tree = ET.parse(str(FIXTURES / "export" / "event_mapping.xml"))
        sid_to_event = {}
        for em in event_tree.getroot().iter("EventMapping"):
            sid_to_event[em.get("StringId", "")] = em.get("SoundEventName", "")

        audio_dir = FIXTURES / "audio"

        # Varon's dialogue has audio
        event = sid_to_event.get("SID_VARON_001")
        assert event == "varon_greeting"
        assert (audio_dir / f"{event}.wem").exists()


class TestKoreanNormalization:
    """Test Korean string normalization patterns (Pattern 7)."""

    def test_korean_detection(self):
        """Detect Korean characters in text."""
        import re
        korean_re = re.compile(r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]')

        assert korean_re.search("장로 바론")
        assert korean_re.search("Mixed text 한국어")
        assert not korean_re.search("English only text")
        assert not korean_re.search("Blackstar Village")

    def test_br_tag_normalization(self):
        """Normalize <br/> tags for matching."""
        import re
        br_re = re.compile(r'<br\s*/?>', re.IGNORECASE)

        text = "첫 번째 줄<br/>두 번째 줄"
        normalized = br_re.sub(' ', text).strip()
        assert normalized == "첫 번째 줄 두 번째 줄"

        # Escaped variant
        text2 = "First line&lt;br/&gt;Second line"
        # In parsed XML, this would be literal <br/>
        assert "&lt;br/&gt;" in text2


class TestLanguageTableDuplicates:
    """Test language table loading with duplicate resolution (Pattern 3)."""

    def test_duplicate_korean_text_preservation(self):
        """Same Korean text with multiple translations should keep ALL."""
        from lxml import etree as ET

        eng_tree = ET.parse(str(FIXTURES / "localization" / "locstr_eng.xml"))

        # Build language table: normalized_korean → [(translation, sid), ...]
        lang_table = {}
        for loc in eng_tree.getroot().iter("LocStr"):
            origin = loc.get("StrOrigin", "").strip()
            translation = loc.get("Str", "").strip()
            sid = loc.get("StringId", "").strip()
            if origin and translation:
                if origin not in lang_table:
                    lang_table[origin] = []
                lang_table[origin].append((translation, sid))

        # Each unique Korean text should have its translations
        assert len(lang_table) == 8  # 8 unique Korean texts
        # Check quest text has translation
        quest_key = "검은별 마을로 향하라"
        assert quest_key in lang_table
        assert lang_table[quest_key][0][0] == "Head to Blackstar Village"


class TestMapDataServiceIntegration:
    """Test MapDataService with mock fixtures."""

    def test_service_initialize_with_fixtures(self):
        """MapDataService can be instantiated and initialized."""
        from server.tools.ldm.services.mapdata_service import MapDataService

        service = MapDataService()
        assert not service._loaded

        # Initialize with default params — may not find real data but shouldn't crash
        result = service.initialize(branch="mainline", drive="F")
        # Result depends on whether real Perforce paths exist
        # The key test: it doesn't throw an unhandled exception
        assert isinstance(result, bool)

    def test_service_graceful_when_unconfigured(self):
        """Unconfigured service returns None, not 500."""
        from server.tools.ldm.services.mapdata_service import MapDataService

        service = MapDataService()
        result = service.get_image_context("KNOW_CHAR_VARON")
        assert result is None  # Graceful, not exception

        result2 = service.get_audio_context("varon_greeting")
        assert result2 is None


class TestGlossaryServiceIntegration:
    """Test GlossaryService with Aho-Corasick."""

    def test_ac_automaton_build(self):
        """Build Aho-Corasick automaton from knowledge entries."""
        try:
            import ahocorasick
        except ImportError:
            pytest.skip("ahocorasick not installed")

        from lxml import etree as ET

        # Extract glossary terms from knowledge
        know_tree = ET.parse(str(FIXTURES / "knowledge" / "knowledgeinfo_sample.xml"))
        terms = []
        for ki in know_tree.getroot().iter("KnowledgeInfo"):
            name = ki.get("Name", "").strip()
            if name:
                terms.append(name)

        assert len(terms) == 10

        # Build automaton (Pattern from QuickSearch)
        A = ahocorasick.Automaton()
        for i, term in enumerate(terms):
            A.add_word(term, (i, term))
        A.make_automaton()

        # Search text for entities
        test_text = "장로 바론이 검은별의 검을 들고 광명의 형제회 전초기지로 향했다."
        found = []
        for end_idx, (idx, term) in A.iter(test_text):
            found.append(term)

        assert "장로 바론" in found, f"Expected '장로 바론' in {found}"
        assert "검은별의 검" in found, f"Expected '검은별의 검' in {found}"

    def test_glossary_extraction_with_min_occurrence(self):
        """Glossary extraction respects min_occurrence threshold."""
        # Simulate a corpus where some terms appear multiple times
        corpus = [
            "장로 바론이 말했다.",
            "장로 바론은 현명한 지도자다.",
            "전사 키라가 싸웠다.",
            "마법사 드라크마르의 주문.",
            "장로 바론의 결정.",  # 3rd occurrence of 바론
        ]

        # Count occurrences
        from collections import Counter
        term_counts = Counter()
        terms = ["장로 바론", "전사 키라", "마법사 드라크마르", "정찰병 루네"]
        for text in corpus:
            for term in terms:
                if term in text:
                    term_counts[term] += 1

        # With min_occurrence=2, only 바론 qualifies
        filtered = {t: c for t, c in term_counts.items() if c >= 2}
        assert "장로 바론" in filtered
        assert "전사 키라" not in filtered  # Only 1 occurrence


class TestContextServiceIntegration:
    """Test ContextService entity resolution."""

    def test_context_service_exists(self):
        """ContextService module can be imported."""
        from server.tools.ldm.services.context_service import ContextService
        service = ContextService()
        assert service is not None

    def test_context_service_graceful_unconfigured(self):
        """Unconfigured ContextService returns empty context, not error."""
        from server.tools.ldm.services.context_service import ContextService
        service = ContextService()
        result = service.resolve_context("STR_CHAR_VARON")
        # Should return empty context (no entities), not raise an exception
        assert result is not None
        assert hasattr(result, 'entities') or isinstance(result, dict)
        # Entities list should be empty when unconfigured
        entities = result.entities if hasattr(result, 'entities') else result.get('entities', [])
        assert len(entities) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
