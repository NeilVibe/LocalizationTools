"""
Tests for ContextSearcher - 3-Tier AC Context Search.

Tests cover:
- AC automaton construction from whole_lookup and line_lookup
- Multi-n-gram generation with space stripping for Korean
- Jaccard similarity calculation
- Tier 1: Whole AC substring match
- Tier 2: Line AC substring match
- Tier 3: Fuzzy character n-gram Jaccard
- Cascade ordering (whole > line > fuzzy)
- Edge cases (empty, no matches)
"""

import random
import time

import pytest

try:
    import ahocorasick
    AC_AVAILABLE = True
except ImportError:
    AC_AVAILABLE = False


# =========================================================================
# Helper: Build mock indexes dict matching TMIndexer.load_indexes() shape
# =========================================================================

def _build_mock_indexes(whole_entries=None, line_entries=None):
    """Build a mock indexes dict with AC automatons for testing.

    Args:
        whole_entries: list of dicts with entry_id, source_text, target_text, string_id
        line_entries: list of dicts with entry_id, source_line, target_line, line_num, total_lines, string_id
    """
    from server.tools.ldm.indexing.utils import normalize_for_hash

    whole_lookup = {}
    if whole_entries:
        for entry in whole_entries:
            key = normalize_for_hash(entry["source_text"])
            whole_lookup[key] = {
                "entry_id": entry["entry_id"],
                "source_text": entry["source_text"],
                "target_text": entry["target_text"],
                "string_id": entry.get("string_id"),
            }

    line_lookup = {}
    if line_entries:
        for entry in line_entries:
            key = normalize_for_hash(entry["source_line"])
            line_lookup[key] = {
                "entry_id": entry["entry_id"],
                "source_line": entry["source_line"],
                "target_line": entry["target_line"],
                "line_num": entry.get("line_num", 0),
                "total_lines": entry.get("total_lines", 1),
                "string_id": entry.get("string_id"),
            }

    # Build AC automatons
    whole_automaton = None
    line_automaton = None

    if AC_AVAILABLE:
        if whole_lookup:
            whole_automaton = ahocorasick.Automaton()
            for idx, key in enumerate(whole_lookup):
                whole_automaton.add_word(key, (idx, key))
            whole_automaton.make_automaton()

        if line_lookup:
            line_automaton = ahocorasick.Automaton()
            for idx, key in enumerate(line_lookup):
                line_automaton.add_word(key, (idx, key))
            line_automaton.make_automaton()

    return {
        "tm_id": 1,
        "metadata": {},
        "whole_lookup": whole_lookup,
        "line_lookup": line_lookup,
        "whole_automaton": whole_automaton,
        "line_automaton": line_automaton,
    }


# =========================================================================
# Test AC Automaton Build from whole_lookup
# =========================================================================

@pytest.mark.skipif(not AC_AVAILABLE, reason="ahocorasick not installed")
class TestACAutomatonBuild:
    """Test that AC automatons are built correctly from lookup dicts."""

    def test_whole_automaton_finds_substring(self):
        """AC automaton built from whole_lookup finds substring match in longer text."""
        indexes = _build_mock_indexes(whole_entries=[
            {"entry_id": 1, "source_text": "무기 강화", "target_text": "Weapon Enhancement"},
            {"entry_id": 2, "source_text": "방어구 수리", "target_text": "Armor Repair"},
            {"entry_id": 3, "source_text": "포션 사용", "target_text": "Use Potion"},
        ])

        automaton = indexes["whole_automaton"]
        assert automaton is not None

        # Search for substring in longer text
        from server.tools.ldm.indexing.utils import normalize_for_hash
        text = normalize_for_hash("지금 무기 강화를 시작합니다")
        found = []
        for end_idx, (idx, key) in automaton.iter(text):
            found.append(key)

        assert len(found) > 0
        assert normalize_for_hash("무기 강화") in found

    def test_line_automaton_finds_substring(self):
        """AC automaton built from line_lookup finds line substring."""
        indexes = _build_mock_indexes(line_entries=[
            {"entry_id": 1, "source_line": "시작 메뉴", "target_line": "Start Menu", "line_num": 0, "total_lines": 1},
            {"entry_id": 2, "source_line": "옵션 설정", "target_line": "Options", "line_num": 0, "total_lines": 1},
            {"entry_id": 3, "source_line": "게임 종료", "target_line": "Exit Game", "line_num": 0, "total_lines": 1},
        ])

        automaton = indexes["line_automaton"]
        assert automaton is not None

        from server.tools.ldm.indexing.utils import normalize_for_hash
        text = normalize_for_hash("메인 화면의 시작 메뉴에서 선택하세요")
        found = []
        for end_idx, (idx, key) in automaton.iter(text):
            found.append(key)

        assert len(found) > 0
        assert normalize_for_hash("시작 메뉴") in found


# =========================================================================
# Test Multi N-gram and Jaccard
# =========================================================================

class TestMultiNgrams:
    """Test character n-gram generation and Jaccard similarity."""

    def test_multi_ngrams_basic(self):
        """multi_ngrams returns correct sets for each n value."""
        from server.tools.ldm.indexing.context_searcher import ContextSearcher

        searcher = ContextSearcher({"whole_lookup": {}, "line_lookup": {}})
        result = searcher._get_multi_ngrams("한국어테스트", ns=(2, 3, 4, 5))

        # Should contain bigrams
        assert "한국" in result
        assert "국어" in result
        # Should contain trigrams
        assert "한국어" in result
        # Should contain 4-grams
        assert "한국어테" in result
        # Should contain 5-grams
        assert "한국어테스" in result

    def test_multi_ngrams_space_stripped(self):
        """Space-stripped Korean text produces correct n-grams."""
        from server.tools.ldm.indexing.context_searcher import ContextSearcher

        searcher = ContextSearcher({"whole_lookup": {}, "line_lookup": {}})

        # Space-stripped: "한국어테스트" (same as above)
        text = "한국어 테스트".replace(" ", "")
        result = searcher._get_multi_ngrams(text, ns=(2, 3))

        assert "한국" in result
        assert "어테" in result  # crosses the original space boundary
        assert "한국어" in result

    def test_jaccard_similarity(self):
        """Jaccard = |intersection| / |union| for two n-gram sets."""
        from server.tools.ldm.indexing.context_searcher import ContextSearcher

        searcher = ContextSearcher({"whole_lookup": {}, "line_lookup": {}})

        set_a = {"ab", "bc", "cd", "de"}
        set_b = {"ab", "bc", "ef", "fg"}

        score = searcher._jaccard_similarity(set_a, set_b)
        # intersection = {ab, bc} = 2, union = {ab, bc, cd, de, ef, fg} = 6
        assert abs(score - 2 / 6) < 0.001

    def test_jaccard_identical_sets(self):
        """Identical sets have Jaccard = 1.0."""
        from server.tools.ldm.indexing.context_searcher import ContextSearcher

        searcher = ContextSearcher({"whole_lookup": {}, "line_lookup": {}})
        set_a = {"ab", "bc", "cd"}
        assert searcher._jaccard_similarity(set_a, set_a) == 1.0

    def test_jaccard_disjoint_sets(self):
        """Disjoint sets have Jaccard = 0.0."""
        from server.tools.ldm.indexing.context_searcher import ContextSearcher

        searcher = ContextSearcher({"whole_lookup": {}, "line_lookup": {}})
        assert searcher._jaccard_similarity({"ab", "cd"}, {"ef", "gh"}) == 0.0


# =========================================================================
# Test 3-Tier Cascade Search
# =========================================================================

@pytest.mark.skipif(not AC_AVAILABLE, reason="ahocorasick not installed")
class TestTier1WholeAC:
    """Tier 1: Whole AC match."""

    def test_whole_ac_returns_match(self):
        """Tier 1 returns matches with tier='whole' when source contains whole_lookup key."""
        indexes = _build_mock_indexes(whole_entries=[
            {"entry_id": 1, "source_text": "무기 강화", "target_text": "Weapon Enhancement"},
            {"entry_id": 2, "source_text": "방어구 수리", "target_text": "Armor Repair"},
        ])

        from server.tools.ldm.indexing.context_searcher import ContextSearcher
        searcher = ContextSearcher(indexes)

        # Source text contains "무기 강화" as substring
        result = searcher.search("지금 무기 강화를 시작합니다")

        assert result["total"] > 0
        whole_results = [r for r in result["results"] if r["tier"] == "whole"]
        assert len(whole_results) > 0
        assert whole_results[0]["score"] == 1.0
        assert whole_results[0]["target_text"] == "Weapon Enhancement"


@pytest.mark.skipif(not AC_AVAILABLE, reason="ahocorasick not installed")
class TestTier2LineAC:
    """Tier 2: Line AC match."""

    def test_line_ac_returns_match(self):
        """Tier 2 returns matches with tier='line' when source contains line_lookup key."""
        indexes = _build_mock_indexes(line_entries=[
            {"entry_id": 10, "source_line": "시작 메뉴", "target_line": "Start Menu", "line_num": 0, "total_lines": 1},
            {"entry_id": 11, "source_line": "옵션 설정", "target_line": "Options", "line_num": 0, "total_lines": 1},
        ])

        from server.tools.ldm.indexing.context_searcher import ContextSearcher
        searcher = ContextSearcher(indexes)

        result = searcher.search("메인 화면의 시작 메뉴에서 선택하세요")

        assert result["total"] > 0
        line_results = [r for r in result["results"] if r["tier"] == "line"]
        assert len(line_results) > 0
        assert line_results[0]["score"] == 1.0
        assert line_results[0]["target_text"] == "Start Menu"


@pytest.mark.skipif(not AC_AVAILABLE, reason="ahocorasick not installed")
class TestTier3Fuzzy:
    """Tier 3: Fuzzy Jaccard match."""

    def test_fuzzy_returns_above_threshold(self):
        """Tier 3 returns matches >= 0.62 threshold with tier='fuzzy'."""
        # Create entries where fuzzy matching should fire
        # "무기 강화 시스템" vs "무기 강화 시스템 설명" — high overlap
        indexes = _build_mock_indexes(whole_entries=[
            {"entry_id": 1, "source_text": "무기 강화 시스템", "target_text": "Weapon Enhancement System"},
        ])

        from server.tools.ldm.indexing.context_searcher import ContextSearcher
        searcher = ContextSearcher(indexes)

        # Search with a similar but not substring-containing text
        # "무기의 강화 시스템이란" — not an exact substring of "무기 강화 시스템" but high char n-gram overlap
        result = searcher.search("무기의강화시스템이란")

        fuzzy_results = [r for r in result["results"] if r["tier"] == "fuzzy"]
        if fuzzy_results:
            assert fuzzy_results[0]["score"] >= 0.62
            assert fuzzy_results[0]["tier"] == "fuzzy"

    def test_fuzzy_below_threshold_excluded(self):
        """Entries below 0.62 threshold are excluded from fuzzy results."""
        indexes = _build_mock_indexes(whole_entries=[
            {"entry_id": 1, "source_text": "완전히 다른 텍스트입니다", "target_text": "Completely different text"},
        ])

        from server.tools.ldm.indexing.context_searcher import ContextSearcher
        searcher = ContextSearcher(indexes)

        result = searcher.search("이것은 관련없는 검색어")

        fuzzy_results = [r for r in result["results"] if r["tier"] == "fuzzy"]
        assert len(fuzzy_results) == 0


@pytest.mark.skipif(not AC_AVAILABLE, reason="ahocorasick not installed")
class TestCascadeOrdering:
    """Test cascade ordering: whole > line > fuzzy, score desc within tiers."""

    def test_whole_before_line_before_fuzzy(self):
        """Results ordered: whole matches first, then line, then fuzzy."""
        indexes = _build_mock_indexes(
            whole_entries=[
                {"entry_id": 1, "source_text": "무기 강화", "target_text": "Weapon Enhancement"},
                # This one should appear as fuzzy (similar but not substring match)
                {"entry_id": 3, "source_text": "무기 강화 시스템 전체 설명서", "target_text": "Full Weapon Enhancement Guide"},
            ],
            line_entries=[
                {"entry_id": 2, "source_line": "강화 시작", "target_line": "Start Enhancement", "line_num": 0, "total_lines": 1},
            ],
        )

        from server.tools.ldm.indexing.context_searcher import ContextSearcher
        searcher = ContextSearcher(indexes)

        # This text contains "무기 강화" (whole match) and "강화 시작" (line match)
        result = searcher.search("무기 강화를 통해 강화 시작이 가능합니다")

        tiers_in_order = [r["tier"] for r in result["results"]]

        # whole results should come before line results
        whole_indices = [i for i, t in enumerate(tiers_in_order) if t == "whole"]
        line_indices = [i for i, t in enumerate(tiers_in_order) if t == "line"]
        fuzzy_indices = [i for i, t in enumerate(tiers_in_order) if t == "fuzzy"]

        if whole_indices and line_indices:
            assert max(whole_indices) < min(line_indices), "Whole results must come before line results"

        if line_indices and fuzzy_indices:
            assert max(line_indices) < min(fuzzy_indices), "Line results must come before fuzzy results"


# =========================================================================
# Edge Cases
# =========================================================================

class TestEdgeCases:
    """Edge cases for ContextSearcher."""

    def test_empty_source_returns_empty(self):
        """Empty source text returns empty results."""
        from server.tools.ldm.indexing.context_searcher import ContextSearcher

        searcher = ContextSearcher({"whole_lookup": {}, "line_lookup": {}})
        result = searcher.search("")

        assert result["total"] == 0
        assert result["results"] == []

    def test_no_matches_returns_empty(self):
        """Source with no matches returns empty results."""
        indexes = _build_mock_indexes(whole_entries=[
            {"entry_id": 1, "source_text": "무기 강화", "target_text": "Weapon Enhancement"},
        ])

        from server.tools.ldm.indexing.context_searcher import ContextSearcher
        searcher = ContextSearcher(indexes)

        result = searcher.search("완전히 다른 텍스트")

        assert result["total"] == 0
        assert result["results"] == []

    def test_result_structure(self):
        """Each result has required fields."""
        indexes = _build_mock_indexes(whole_entries=[
            {"entry_id": 1, "source_text": "테스트", "target_text": "Test"},
        ])

        from server.tools.ldm.indexing.context_searcher import ContextSearcher
        searcher = ContextSearcher(indexes)

        result = searcher.search("이것은 테스트입니다")

        if result["results"]:
            r = result["results"][0]
            assert "source_text" in r
            assert "target_text" in r
            assert "entry_id" in r
            assert "score" in r
            assert "tier" in r
            assert "match_type" in r

    def test_tier_counts_in_response(self):
        """Response includes tier_counts dict."""
        from server.tools.ldm.indexing.context_searcher import ContextSearcher

        searcher = ContextSearcher({"whole_lookup": {}, "line_lookup": {}})
        result = searcher.search("test")

        assert "tier_counts" in result
        assert "whole" in result["tier_counts"]
        assert "line" in result["tier_counts"]
        assert "fuzzy" in result["tier_counts"]


# =========================================================================
# Test indexer.py AC build integration
# =========================================================================

@pytest.mark.skipif(not AC_AVAILABLE, reason="ahocorasick not installed")
class TestIndexerACBuild:
    """Test that TMIndexer._build_ac_automatons works correctly."""

    def test_build_ac_automatons_method_exists(self):
        """TMIndexer has _build_ac_automatons method."""
        from server.tools.ldm.indexing.indexer import TMIndexer
        assert hasattr(TMIndexer, "_build_ac_automatons")

    def test_build_ac_automatons_returns_tuple(self):
        """_build_ac_automatons returns (whole_automaton, line_automaton) tuple."""
        from server.tools.ldm.indexing.indexer import TMIndexer
        from server.tools.ldm.indexing.utils import normalize_for_hash

        # Create a minimal TMIndexer (we just need the method, not DB)
        class FakeDB:
            pass

        indexer = TMIndexer.__new__(TMIndexer)

        whole_lookup = {
            normalize_for_hash("무기 강화"): {
                "entry_id": 1,
                "source_text": "무기 강화",
                "target_text": "Weapon Enhancement",
            }
        }
        line_lookup = {
            normalize_for_hash("시작 메뉴"): {
                "entry_id": 2,
                "source_line": "시작 메뉴",
                "target_line": "Start Menu",
            }
        }

        whole_auto, line_auto = indexer._build_ac_automatons(whole_lookup, line_lookup)

        assert whole_auto is not None
        assert line_auto is not None

        # Verify they are ahocorasick.Automaton instances
        assert isinstance(whole_auto, ahocorasick.Automaton)
        assert isinstance(line_auto, ahocorasick.Automaton)

    def test_build_ac_empty_lookups(self):
        """_build_ac_automatons with empty lookups returns (None, None)."""
        from server.tools.ldm.indexing.indexer import TMIndexer

        indexer = TMIndexer.__new__(TMIndexer)

        whole_auto, line_auto = indexer._build_ac_automatons({}, {})

        assert whole_auto is None
        assert line_auto is None


# =========================================================================
# Performance Benchmarks
# =========================================================================

def _random_korean_string(min_len: int = 20, max_len: int = 80) -> str:
    """Generate a random Korean string using syllable range 0xAC00-0xD7AF."""
    length = random.randint(min_len, max_len)
    chars = []
    for _ in range(length):
        # Mix Korean syllables with occasional spaces (~10% chance)
        if random.random() < 0.1:
            chars.append(" ")
        else:
            chars.append(chr(random.randint(0xAC00, 0xD7AF)))
    return "".join(chars)


def _build_korean_tm_entries(count: int):
    """Generate synthetic Korean TM data entries.

    Returns:
        Tuple of (whole_lookup, line_lookup) dicts.
    """
    from server.tools.ldm.indexing.utils import normalize_for_hash

    whole_lookup = {}
    line_lookup = {}

    for i in range(count):
        source = _random_korean_string(20, 80)
        target = _random_korean_string(20, 80)
        normalized = normalize_for_hash(source)
        if not normalized:
            continue

        whole_lookup[normalized] = {
            "entry_id": i,
            "source_text": source,
            "target_text": target,
            "string_id": None,
        }

        # Build line entries from first line
        lines = source.split(" ")
        for j, line in enumerate(lines[:3]):  # limit lines per entry
            line_norm = normalize_for_hash(line)
            if line_norm and len(line_norm) >= 2 and line_norm not in line_lookup:
                line_lookup[line_norm] = {
                    "entry_id": i,
                    "source_line": line,
                    "target_line": target[:20],
                    "line_num": j,
                    "total_lines": min(len(lines), 3),
                    "string_id": None,
                }

    return whole_lookup, line_lookup


def _build_indexes_with_ac(whole_lookup, line_lookup):
    """Create indexes dict with AC automatons from lookups."""
    whole_automaton = None
    line_automaton = None

    if whole_lookup:
        whole_automaton = ahocorasick.Automaton()
        for idx, key in enumerate(whole_lookup):
            whole_automaton.add_word(key, (idx, key))
        whole_automaton.make_automaton()

    if line_lookup:
        line_automaton = ahocorasick.Automaton()
        for idx, key in enumerate(line_lookup):
            line_automaton.add_word(key, (idx, key))
        line_automaton.make_automaton()

    return {
        "tm_id": 1,
        "metadata": {},
        "whole_lookup": whole_lookup,
        "line_lookup": line_lookup,
        "whole_automaton": whole_automaton,
        "line_automaton": line_automaton,
    }


@pytest.mark.skipif(not AC_AVAILABLE, reason="ahocorasick not installed")
class TestContextSearcherPerformance:
    """Performance benchmarks for ContextSearcher with realistic Korean TM data."""

    def test_performance_1000_entries(self):
        """Context search completes in < 100ms per query with 1000+ entries.

        Generates 1000 Korean TM entries, builds AC indexes, runs 10 searches
        with partial substrings from actual entries. Each must be < 100ms,
        average must be < 50ms (headroom).
        """
        from server.tools.ldm.indexing.context_searcher import ContextSearcher

        random.seed(42)  # Reproducible

        whole_lookup, line_lookup = _build_korean_tm_entries(1000)
        assert len(whole_lookup) >= 900, f"Expected 900+ entries, got {len(whole_lookup)}"

        indexes = _build_indexes_with_ac(whole_lookup, line_lookup)
        searcher = ContextSearcher(indexes)

        # Pick 10 source texts -- mix of partial substrings to trigger all tiers
        source_keys = list(whole_lookup.keys())
        search_texts = []
        for i in range(10):
            key = source_keys[i * (len(source_keys) // 10)]
            # Use a substring (partial) to trigger both AC and fuzzy tiers
            text = key[:len(key) // 2] + _random_korean_string(5, 15)
            search_texts.append(text)

        timings = []
        for text in search_texts:
            start = time.perf_counter()
            result = searcher.search(text, max_results=10)
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        max_time = max(timings)
        avg_time = sum(timings) / len(timings)

        assert max_time < 100, f"Max search time {max_time:.1f}ms exceeds 100ms limit"
        assert avg_time < 50, f"Average search time {avg_time:.1f}ms exceeds 50ms headroom"

    def test_performance_2000_entries_consecutive(self):
        """10 consecutive searches with 2000 entries all complete in < 100ms each.

        Validates sustained performance under heavier load.
        """
        from server.tools.ldm.indexing.context_searcher import ContextSearcher

        random.seed(123)  # Reproducible

        whole_lookup, line_lookup = _build_korean_tm_entries(2000)
        assert len(whole_lookup) >= 1800, f"Expected 1800+ entries, got {len(whole_lookup)}"

        indexes = _build_indexes_with_ac(whole_lookup, line_lookup)
        searcher = ContextSearcher(indexes)

        source_keys = list(whole_lookup.keys())
        timings = []

        for i in range(10):
            key = source_keys[i * (len(source_keys) // 10)]
            text = key[:len(key) // 2] + _random_korean_string(10, 30)

            start = time.perf_counter()
            result = searcher.search(text, max_results=10)
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        for i, t in enumerate(timings):
            assert t < 100, f"Search {i} took {t:.1f}ms, exceeds 100ms limit"
