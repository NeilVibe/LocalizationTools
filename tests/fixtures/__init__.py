"""
Test Fixtures - COMPLETE UNIVERSE of Test Cases for LocaNext Apps

Provides COMPREHENSIVE mock data covering ALL POSSIBLE production patterns.
See TESTING_PROTOCOL.md section "Test Data Design Philosophy" for details.

=== DATA FORMAT (Tab-Separated) ===

Column 0: Category ID (e.g., 39, 18, 25)
Column 1: File ID (e.g., 7924197, 8504)
Column 2: String ID (e.g., 1001, 2001)
Column 3: Unknown (typically 0)
Column 4: Sequence number (1, 2, 3...)
Column 5: Korean text (source) - may contain tags and \\n
Column 6: Translation (target) - French, English, etc.
Column 7+: Additional metadata (notes, category, etc.)

=== COMPLETE UNIVERSE OF TEST CASES ===

sample_language_data.txt contains 48 rows covering:

CATEGORY A: TAG PATTERNS (Rows 1-14, 26-37)
├── A1. Multiple tags at start          Row 1, 2: {ChangeScene(X)}{AudioVoice(Y)}Text
├── A2. Tags after newline              Row 2, 4: Text\\n{Tag}More
├── A3. Multiple blocks per cell        Row 2, 4, 22: {T1}L1\\n{T2}L2\\n{T3}L3
├── A4. Complex asset names             Row 22: NPC_VCE_NEW_8504_26_10_DuckGoo
├── A5. HTML-like color tags            Row 11: <color=red>text</color>
├── A6. Scale/formatting tags           Row 12: {Scale(1.2)}text{/Scale}
├── A7. PAColor tags                    Row 43: {PAColor(#FF0000)}text{PAOldColor}
├── A8. Only tags no text               Row 26: {AudioVoice(NPC_001)}
├── A9. Malformed tag (no close)        Row 27: {incomplete tag without closing
├── A10. Orphan closing brace           Row 28: text with } orphan
├── A11. Double braces                  Row 29: {{DoubleOpen}}text{{DoubleClose}}
├── A12. Many tags at start (5+)        Row 35: {Tag1}{Tag2}{Tag3}{Tag4}{Tag5}text
├── A13. Tags in middle of text         Row 36: text\\n{Mid1}middle\\n{Mid2}more
├── A14. Nested tags                    Row 37: {Outer{Inner}Nested}text
└── A15. 10 blocks complex              Row 48: 5 scene + 5 voice alternating

CATEGORY B: CONTENT PATTERNS (Rows 5-6, 10-11, 19-21, 24-25, 30-34, 44-47)
├── B1. Korean standard                 All rows: 안녕하세요
├── B2. Korean punctuation              Row 2: !, !!, ?, ...
├── B3. Korean dialect                  Row 4, 21: 싶어유!, 있잖아유?
├── B4. Special chars ▶【】             Row 5, 10: menu markers
├── B5. Numbers in text                 Row 11: HP: 100, MP: 50
├── B6. Long text 100+ chars            Row 23: continuous text test
├── B7. Emoji                           Row 24: 👋 🎉 🎮
├── B8. HTML entities                   Row 25: &nbsp; &amp; &lt; &gt;
├── B9. Pure numbers only               Row 30: 12345
├── B10. Korean + Japanese mix          Row 33: 한국어と日本語
├── B11. Multi-script (4 scripts)       Row 34: Привет 안녕 你好 مرحبا
├── B12. Symbol heavy                   Row 44: ★★★ ☆☆ ♥♡
├── B13. Zero-width character           Row 45: hidden unicode
├── B14. Very long word (no spaces)     Row 46: 아주아주아주...긴단어
└── B15. Single character               Row 47: .

CATEGORY C: EDGE CASES (Rows 31-32, 38-42)
├── C1. Empty Korean (blank source)     Row 31: [empty]→"Empty Translation"
├── C2. Empty translation               Row 32: "빈 번역 테스트"→[empty]
├── C3. Multiple consecutive newlines   Row 38: \\n\\n\\n text \\n\\n\\n
├── C4. Embedded tabs                   Row 39: tab-separated content
├── C5. Quotes (single, double, nested) Row 40: "text 'nested' \"double\""
├── C6. Backslash escapes               Row 41: text\\\\double\\\\\\\\
└── C7. XSS pattern                     Row 42: <script>alert('xss')</script>

CATEGORY D: STRUCTURE PATTERNS
├── D1. Single line                     Row 9, 16, 19
├── D2. Multi-line (\\n)                Row 2, 4, 5, 7
├── D3. Empty trailing columns          Row 9, 19
├── D4. Variable column counts          7-9 columns throughout
└── D5. 5+ newlines in cell             Row 2, 22, 48

=== FIXTURE FILES ===

sample_language_data.txt (48 rows)
    - COMPLETE UNIVERSE: All tag patterns, content patterns, edge cases
    - Used by: KR Similar, XLSTransfer
    - Tests: String reconstruction, tag extraction, similarity search

sample_quicksearch_data.txt (36 rows)
    - Simpler format: Korean-English pairs (tags already stripped)
    - Used by: QuickSearch dictionary search
    - Focus: Content search, not tag processing

sample_dictionary.xlsx
    - Excel format for XLSTransfer tests

sample_to_translate.txt
    - Input file for translation tests

=== REAL DATA REFERENCE ===

Production data format from:
RessourcesForCodingTheProject/datausedfortesting/langsampleallweneed.txt

Voice naming: NPC_VCE_NEW_[ID]_[SEQ]_[Name]
Scene naming: MorningMain_XX_XXX, MorningLand_NPC_XXXXX
"""

import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent


def get_fixture_path(filename: str) -> str:
    """Get full path to a fixture file."""
    return str(FIXTURES_DIR / filename)


def get_sample_language_data() -> str:
    """
    Get path to comprehensive language data file.

    Contains 24 rows with full complexity:
    - Multiple tag blocks per cell
    - Complex voice asset naming
    - French translations
    - Multi-line content (\\n)
    - Edge cases (emoji, long text, dialect)
    """
    return get_fixture_path("sample_language_data.txt")


def get_sample_quicksearch_data() -> str:
    """
    Get path to quicksearch dictionary data.

    Contains 36 rows of Korean-English pairs:
    - Simple lookups (yes/no, confirm/cancel)
    - Special characters (▶, 【】)
    - Numbers (HP: 100)
    - Long text
    """
    return get_fixture_path("sample_quicksearch_data.txt")


def get_sample_excel() -> str:
    """Get path to sample Excel file for XLSTransfer tests."""
    return get_fixture_path("sample_dictionary.xlsx")


def get_sample_to_translate() -> str:
    """Get path to sample translation input file."""
    return get_fixture_path("sample_to_translate.txt")


# Pattern checklist for test validation
REQUIRED_PATTERNS = {
    "basic_single_tag": "{Tag}Text",
    "multiple_tags_start": "{Tag1}{Tag2}Text",
    "tags_after_newline": "Text\\n{Tag}More",
    "multiple_blocks": "{T1}L1\\n{T2}L2",
    "complex_tag_names": "NPC_VCE_NEW_",
    "scene_references": "MorningMain_",
    "empty_columns": True,
    "korean_punctuation": ["!", "?", "...", "~"],
    "special_chars": ["▶", "【", "】"],
    "numbers_in_text": ["HP:", "MP:", "레벨"],
    "long_text": 100,  # chars
}
