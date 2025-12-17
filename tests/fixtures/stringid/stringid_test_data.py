"""
StringID Test Data for E2E Testing

This module contains all test data for StringID mode testing.
Data is organized by pattern type and can be combined as needed.

Test Data Structure:
- Each entry has: string_id, source, target
- Duplicate sources with different string_ids test the core StringID feature
"""

# =============================================================================
# BASIC STRINGID TEST DATA (Core feature test)
# Same source text with different StringIDs -> different translations
# =============================================================================

BASIC_STRINGID_DATA = [
    # "저장" (Save) - 3 variations
    {"string_id": "UI_BUTTON_SAVE", "source": "저장", "target": "Save"},
    {"string_id": "UI_MENU_SAVE", "source": "저장", "target": "Save Game"},
    {"string_id": "TECH_STORAGE", "source": "저장", "target": "Storage"},

    # "설정" (Settings) - 2 variations
    {"string_id": "UI_MENU_SETTINGS", "source": "설정", "target": "Settings"},
    {"string_id": "TECH_CONFIG", "source": "설정", "target": "Configuration"},

    # "확인" (Confirm/OK) - 2 variations
    {"string_id": "UI_BUTTON_OK", "source": "확인", "target": "OK"},
    {"string_id": "UI_BUTTON_CONFIRM", "source": "확인", "target": "Confirm"},

    # "열기" (Open) - 2 variations
    {"string_id": "UI_BUTTON_OPEN", "source": "열기", "target": "Open"},
    {"string_id": "UI_MENU_OPEN_FILE", "source": "열기", "target": "Open File"},

    # "취소" (Cancel) - single entry (no variations)
    {"string_id": "UI_BUTTON_CANCEL", "source": "취소", "target": "Cancel"},
]

# =============================================================================
# COLOR CODE TEST DATA
# Tests color code preservation with StringID
# =============================================================================

COLOR_CODE_TEST_DATA = [
    # Same source with color codes, different translations
    {
        "string_id": "ITEM_DESC_001",
        "source": "<PAColor0xffe9bd23>아이템 설명</PAOldColor>",
        "target": "<PAColor0xffe9bd23>Item Description</PAOldColor>"
    },
    {
        "string_id": "ITEM_DESC_002",
        "source": "<PAColor0xffe9bd23>아이템 설명</PAOldColor>",
        "target": "<PAColor0xffe9bd23>Item Info</PAOldColor>"
    },
    # Warning with color
    {
        "string_id": "NPC_DIALOGUE_001",
        "source": "<PAColor0xff0000>경고!</PAOldColor> 위험합니다",
        "target": "<PAColor0xff0000>Warning!</PAOldColor> Danger ahead"
    },
    # Multiple colors in same string
    {
        "string_id": "MULTI_COLOR_001",
        "source": "<PAColor0xff0000>빨강</PAOldColor> <PAColor0x00ff00>초록</PAOldColor>",
        "target": "<PAColor0xff0000>Red</PAOldColor> <PAColor0x00ff00>Green</PAOldColor>"
    },
]

# =============================================================================
# TEXTBIND TEST DATA
# Tests TextBind placeholder preservation with StringID
# =============================================================================

TEXTBIND_TEST_DATA = [
    # Same source with TextBind, different translations
    {
        "string_id": "KEYBIND_RMB",
        "source": "{TextBind:CLICK_ON_RMB_ONLY}를 눌러 공격",
        "target": "Press {TextBind:CLICK_ON_RMB_ONLY} to attack"
    },
    {
        "string_id": "KEYBIND_RMB_ALT",
        "source": "{TextBind:CLICK_ON_RMB_ONLY}를 눌러 공격",
        "target": "{TextBind:CLICK_ON_RMB_ONLY} for attack"
    },
    # Different keybind
    {
        "string_id": "KEYBIND_INTERACT",
        "source": "{TextBind:INTERACT}로 상호작용",
        "target": "{TextBind:INTERACT} to interact"
    },
    # Multiple bindings
    {
        "string_id": "MULTI_BIND_001",
        "source": "{TextBind:ATTACK} 공격, {TextBind:DEFEND} 방어",
        "target": "{TextBind:ATTACK} attack, {TextBind:DEFEND} defend"
    },
]

# =============================================================================
# NEWLINE TEST DATA
# Tests multi-line text with StringID
# =============================================================================

NEWLINE_TEST_DATA = [
    # Same multi-line source, different translations
    {
        "string_id": "MULTILINE_001",
        "source": "첫 번째 줄\n두 번째 줄",
        "target": "First line\nSecond line"
    },
    {
        "string_id": "MULTILINE_002",
        "source": "첫 번째 줄\n두 번째 줄",
        "target": "Line 1\nLine 2"
    },
    # Complex multi-line
    {
        "string_id": "MULTILINE_COMPLEX",
        "source": "제목\n\n본문 내용\n끝",
        "target": "Title\n\nBody content\nEnd"
    },
]

# =============================================================================
# COMPLEX MIXED PATTERNS
# Tests combinations of color codes, TextBind, and newlines
# =============================================================================

COMPLEX_TEST_DATA = [
    # Color + TextBind + Newline
    {
        "string_id": "COMPLEX_001",
        "source": "<PAColor0xffe9bd23>{TextBind:INTERACT}</PAOldColor>를 눌러\n상호작용",
        "target": "Press <PAColor0xffe9bd23>{TextBind:INTERACT}</PAOldColor>\nto interact"
    },
    # Scale + Color + TextBind + Newline
    {
        "string_id": "COMPLEX_002",
        "source": "<Scale:1.2><PAColor0xff0000>경고</PAOldColor></Scale>\n{TextBind:ESCAPE}로 취소",
        "target": "<Scale:1.2><PAColor0xff0000>Warning</PAOldColor></Scale>\n{TextBind:ESCAPE} to cancel"
    },
]

# =============================================================================
# KR SIMILAR TEST DATA (Triangle markers)
# Triangle markers (▶) for KR Similar mode
# NOTE: sampleofLanguageData.txt doesn't contain these - manually created
# =============================================================================

KR_SIMILAR_TEST_DATA = [
    # Same triangle-prefixed source, different translations
    {
        "string_id": "KRSIM_001",
        "source": "▶첫 번째 줄\n▶두 번째 줄",
        "target": "▶First line\n▶Second line"
    },
    {
        "string_id": "KRSIM_002",
        "source": "▶첫 번째 줄\n▶두 번째 줄",
        "target": "▶Line one\n▶Line two"
    },
    # Triangle with Scale tag
    {
        "string_id": "KRSIM_SCALE",
        "source": "▶<Scale:1.2>큰 텍스트</Scale>",
        "target": "▶<Scale:1.2>Large text</Scale>"
    },
    # Triangle with color
    {
        "string_id": "KRSIM_COLOR",
        "source": "▶<PAColor0xff0000>빨간 텍스트</PAOldColor>",
        "target": "▶<PAColor0xff0000>Red text</PAOldColor>"
    },
]

# =============================================================================
# XLS TRANSFER TEST DATA
# Code preservation patterns for XLS Transfer engine
# =============================================================================

XLS_TRANSFER_TEST_DATA = [
    # Code at start
    {
        "string_id": "XLS_CODE_START",
        "source": "<PAColor0xff0000>아이템</PAOldColor> 획득",
        "target": "<PAColor0xff0000>Item</PAOldColor> obtained"
    },
    # Code in middle
    {
        "string_id": "XLS_CODE_MIDDLE",
        "source": "당신은 <PAColor0xff0000>영웅</PAOldColor>입니다",
        "target": "You are a <PAColor0xff0000>hero</PAOldColor>"
    },
    # Multiple codes
    {
        "string_id": "XLS_MULTI_CODE",
        "source": "<PAColor0xff0000>빨강</PAOldColor>과 <PAColor0x00ff00>초록</PAOldColor>",
        "target": "<PAColor0xff0000>Red</PAOldColor> and <PAColor0x00ff00>Green</PAOldColor>"
    },
    # _x000D_ removal (Excel artifact)
    {
        "string_id": "XLS_X000D",
        "source": "첫줄_x000D_\n둘째줄",
        "target": "First_x000D_\nSecond"
    },
]

# =============================================================================
# EDGE CASE TEST DATA
# =============================================================================

EDGE_CASE_TEST_DATA = [
    # Unicode StringID
    {
        "string_id": "한글ID_001",
        "source": "테스트",
        "target": "Test"
    },
    # Empty target (valid case)
    {
        "string_id": "EMPTY_TARGET",
        "source": "빈 타겟",
        "target": ""
    },
    # Very short source
    {
        "string_id": "SHORT_001",
        "source": "예",
        "target": "Yes"
    },
    # Long source
    {
        "string_id": "LONG_001",
        "source": "이것은 매우 긴 소스 텍스트입니다. 여러 문장이 포함되어 있습니다. 테스트를 위한 긴 텍스트입니다.",
        "target": "This is a very long source text. It contains multiple sentences. Long text for testing."
    },
]

# =============================================================================
# COMBINED TEST DATA SETS
# =============================================================================

# All StringID test data combined
ALL_STRINGID_TEST_DATA = (
    BASIC_STRINGID_DATA +
    COLOR_CODE_TEST_DATA +
    TEXTBIND_TEST_DATA +
    NEWLINE_TEST_DATA +
    COMPLEX_TEST_DATA +
    KR_SIMILAR_TEST_DATA +
    XLS_TRANSFER_TEST_DATA +
    EDGE_CASE_TEST_DATA
)

# Standard TM data (no duplicates - for backward compat testing)
STANDARD_TM_DATA = [
    {"string_id": None, "source": "저장", "target": "Save"},
    {"string_id": None, "source": "설정", "target": "Settings"},
    {"string_id": None, "source": "확인", "target": "OK"},
    {"string_id": None, "source": "열기", "target": "Open"},
    {"string_id": None, "source": "취소", "target": "Cancel"},
]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_duplicate_sources():
    """Get list of sources that have multiple StringID variations."""
    sources = {}
    for entry in BASIC_STRINGID_DATA:
        src = entry["source"]
        if src not in sources:
            sources[src] = []
        sources[src].append(entry)
    return {k: v for k, v in sources.items() if len(v) > 1}


def get_test_data_by_source(source: str):
    """Get all entries with a specific source text."""
    return [e for e in ALL_STRINGID_TEST_DATA if e["source"] == source]


def get_test_data_by_stringid(string_id: str):
    """Get entry with a specific StringID."""
    for e in ALL_STRINGID_TEST_DATA:
        if e["string_id"] == string_id:
            return e
    return None


def count_variations():
    """Count sources with multiple variations."""
    sources = {}
    for entry in ALL_STRINGID_TEST_DATA:
        src = entry["source"]
        if src not in sources:
            sources[src] = 0
        sources[src] += 1
    return {k: v for k, v in sources.items() if v > 1}


# =============================================================================
# TEST DATA STATISTICS
# =============================================================================

if __name__ == "__main__":
    print(f"Total test entries: {len(ALL_STRINGID_TEST_DATA)}")
    print(f"Basic StringID entries: {len(BASIC_STRINGID_DATA)}")
    print(f"Color code entries: {len(COLOR_CODE_TEST_DATA)}")
    print(f"TextBind entries: {len(TEXTBIND_TEST_DATA)}")
    print(f"Newline entries: {len(NEWLINE_TEST_DATA)}")
    print(f"Complex entries: {len(COMPLEX_TEST_DATA)}")
    print(f"KR Similar entries: {len(KR_SIMILAR_TEST_DATA)}")
    print(f"XLS Transfer entries: {len(XLS_TRANSFER_TEST_DATA)}")
    print(f"Edge case entries: {len(EDGE_CASE_TEST_DATA)}")
    print()
    print("Sources with multiple variations:")
    for src, count in count_variations().items():
        print(f"  '{src}': {count} variations")
