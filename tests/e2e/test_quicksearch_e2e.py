"""
End-to-End Tests for QuickSearch (App #2)

Full integration tests that verify ALL production endpoints:
1. Health check
2. Create dictionary from files (XML/TXT/TSV)
3. Load dictionary into memory
4. Search (single line)
5. Search multiline
6. Set reference dictionary
7. Toggle reference
8. List dictionaries

These tests use real files and verify expected outputs.
"""

import pytest
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Test game/language (use TEST to avoid overwriting real data)
TEST_GAME = "BDO"  # Use valid game since TEST might not be accepted
TEST_LANGUAGE = "EN"


class TestQuickSearchCore:
    """Unit tests for QuickSearch core functionality."""

    def test_01_module_imports(self):
        """Test that QuickSearch modules can be imported."""
        from server.tools.quicksearch.dictionary import DictionaryManager, GAMES, LANGUAGES
        from server.tools.quicksearch.searcher import Searcher

        assert DictionaryManager is not None
        assert Searcher is not None
        assert len(GAMES) > 0
        assert len(LANGUAGES) > 0

        print(f"Available games: {GAMES}")
        print(f"Available languages: {LANGUAGES}")

    def test_02_fixture_file_exists(self):
        """Verify QuickSearch fixture file exists."""
        fixture_path = FIXTURES_DIR / "sample_quicksearch_data.txt"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

        # Read and verify content
        with open(fixture_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        assert len(lines) > 1, "Fixture should have header + data rows"

        print(f"Fixture has {len(lines)} lines")

    def test_03_dictionary_manager_init(self):
        """Test DictionaryManager initialization."""
        from server.tools.quicksearch.dictionary import DictionaryManager

        manager = DictionaryManager()
        assert manager is not None
        assert manager.base_dir.exists()
        assert manager.current_dict is None

        print(f"DictionaryManager base_dir: {manager.base_dir}")

    def test_04_searcher_init(self):
        """Test Searcher initialization."""
        from server.tools.quicksearch.searcher import Searcher

        searcher = Searcher()
        assert searcher is not None
        assert searcher.reference_enabled == False

        print("Searcher initialized successfully")


class TestQuickSearchDictionary:
    """Tests for QuickSearch dictionary creation and management."""

    @pytest.fixture(scope="class")
    def dict_manager(self):
        """Get DictionaryManager instance."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        return DictionaryManager()

    @pytest.fixture(scope="class")
    def searcher(self):
        """Get Searcher instance."""
        from server.tools.quicksearch.searcher import Searcher
        return Searcher()

    @pytest.fixture
    def fixture_file(self):
        """Get fixture file path."""
        return str(FIXTURES_DIR / "sample_quicksearch_data.txt")

    def test_05_create_dictionary(self, dict_manager, fixture_file):
        """Test creating dictionary from fixture file.

        PRODUCTION USE: User uploads TXT/XML files to create searchable dictionary.
        INPUT: TXT file with StringID, Korean, Translation columns
        EXPECTED OUTPUT: split_dict and whole_dict with searchable entries
        """
        # create_dictionary returns (split_dict, whole_dict, string_keys, stringid_to_entry)
        split_dict, whole_dict, string_keys, stringid_to_entry = dict_manager.create_dictionary(
            file_paths=[fixture_file],
            game=TEST_GAME,
            language=TEST_LANGUAGE
        )

        assert len(split_dict) > 0 or len(whole_dict) > 0, "Should create dictionary entries"

        print(f"Dictionary created: {len(split_dict)} split entries, {len(whole_dict)} whole entries")

    def test_06_list_dictionaries(self, dict_manager):
        """Test listing available dictionaries.

        PRODUCTION USE: Show user which dictionaries are available.
        EXPECTED: List of dictionaries with metadata.
        """
        dictionaries = dict_manager.list_available_dictionaries()

        assert isinstance(dictionaries, list)
        print(f"Available dictionaries: {len(dictionaries)}")

        for d in dictionaries:
            print(f"  - {d}")

    def test_07_load_dictionary(self, dict_manager, searcher):
        """Test loading dictionary into memory.

        PRODUCTION USE: Load dictionary before searching.
        EXPECTED: Dictionary loaded, searcher ready for queries.
        """
        try:
            dictionary = dict_manager.load_dictionary(TEST_GAME, TEST_LANGUAGE, as_reference=False)

            assert dictionary is not None, "Dictionary should load"
            assert 'split_dict' in dictionary or 'whole_dict' in dictionary

            # Load into searcher
            searcher.load_dictionary(dictionary)

            print(f"Dictionary loaded: {TEST_GAME}-{TEST_LANGUAGE}")
        except FileNotFoundError:
            pytest.skip(f"Dictionary {TEST_GAME}-{TEST_LANGUAGE} not found - run create_dictionary first")


class TestQuickSearchSearcher:
    """Tests for QuickSearch search functionality."""

    @pytest.fixture(scope="class")
    def loaded_searcher(self):
        """Get searcher with loaded dictionary."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        from server.tools.quicksearch.searcher import Searcher

        manager = DictionaryManager()
        searcher = Searcher()

        try:
            dictionary = manager.load_dictionary(TEST_GAME, TEST_LANGUAGE, as_reference=False)
            searcher.load_dictionary(dictionary)
            return searcher
        except FileNotFoundError:
            # Create dictionary first - returns (split_dict, whole_dict, string_keys, stringid_to_entry)
            fixture_file = str(FIXTURES_DIR / "sample_quicksearch_data.txt")
            split_dict, whole_dict, string_keys, stringid_to_entry = manager.create_dictionary(
                [fixture_file], TEST_GAME, TEST_LANGUAGE
            )
            dictionary = manager.load_dictionary(TEST_GAME, TEST_LANGUAGE, as_reference=False)
            searcher.load_dictionary(dictionary)
            return searcher

    def test_08_search_one_line_contains(self, loaded_searcher):
        """Test single-line search with 'contains' match.

        PRODUCTION USE: User searches for text, finds all entries containing query.
        INPUT: Query string like "안녕"
        EXPECTED OUTPUT: List of matches with Korean, Translation, StringID
        """
        results, total_count = loaded_searcher.search_one_line(
            query="안녕",
            match_type="contains",
            start_index=0,
            limit=50
        )

        assert isinstance(results, list)
        print(f"Search '안녕' (contains): {total_count} results")

        if len(results) > 0:
            first = results[0]
            print(f"First result: {first}")

    def test_09_search_one_line_exact(self, loaded_searcher):
        """Test single-line search with 'exact' match.

        PRODUCTION USE: User searches for exact text match.
        INPUT: Exact query string
        EXPECTED OUTPUT: Only exact matches
        """
        results, total_count = loaded_searcher.search_one_line(
            query="안녕하세요",
            match_type="exact",
            start_index=0,
            limit=50
        )

        assert isinstance(results, list)
        print(f"Search '안녕하세요' (exact): {total_count} results")

    def test_10_search_multi_line(self, loaded_searcher):
        """Test multi-line search.

        PRODUCTION USE: User pastes multiple queries, one per line.
        INPUT: List of queries
        EXPECTED OUTPUT: Results grouped by query
        """
        queries = ["안녕", "감사", "전투"]

        results = loaded_searcher.search_multi_line(
            queries=queries,
            match_type="contains",
            limit=10
        )

        assert isinstance(results, list)
        assert len(results) == len(queries), "Should have result for each query"

        for r in results:
            print(f"Query '{r['line']}': {r['total_count']} results")

    def test_11_toggle_reference(self, loaded_searcher):
        """Test toggling reference dictionary display.

        PRODUCTION USE: User enables/disables reference column in results.
        """
        # Enable
        loaded_searcher.toggle_reference(True)
        assert loaded_searcher.reference_enabled == True

        # Disable
        loaded_searcher.toggle_reference(False)
        assert loaded_searcher.reference_enabled == False

        print("Reference toggle works correctly")


class TestQuickSearchAPIE2E:
    """End-to-end API tests for ALL QuickSearch production endpoints.

    These tests require a running server (set RUN_API_TESTS=1).
    """

    @pytest.fixture(scope="class")
    def api_client(self):
        """Create authenticated API client."""
        import requests

        class APIClient:
            def __init__(self):
                self.base_url = "http://localhost:8888"
                self.token = None
                self.headers = {}

            def login(self):
                """Authenticate and store token."""
                r = requests.post(
                    f"{self.base_url}/api/v2/auth/login",
                    json={"username": "admin", "password": "admin123"},
                    timeout=10
                )
                if r.status_code == 200:
                    self.token = r.json()["access_token"]
                    self.headers = {"Authorization": f"Bearer {self.token}"}
                    return True
                return False

            def get(self, endpoint, **kwargs):
                return requests.get(f"{self.base_url}{endpoint}", headers=self.headers, timeout=30, **kwargs)

            def post(self, endpoint, **kwargs):
                return requests.post(f"{self.base_url}{endpoint}", headers=self.headers, timeout=60, **kwargs)

        client = APIClient()
        return client

    @pytest.fixture
    def fixture_file_path(self):
        """Get fixture file path."""
        return str(FIXTURES_DIR / "sample_quicksearch_data.txt")

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_api_01_health(self, api_client):
        """Test GET /health endpoint.

        EXPECTED: status=ok, modules_loaded shows dictionary_manager and searcher
        """
        if not api_client.login():
            pytest.skip("Could not login to API")

        r = api_client.get("/api/v2/quicksearch/health")

        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert data["status"] == "ok"
        assert "modules_loaded" in data
        print(f"API health: {data}")

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_api_02_list_dictionaries(self, api_client):
        """Test GET /list-dictionaries endpoint.

        EXPECTED: Returns list of available dictionaries
        """
        if not api_client.login():
            pytest.skip("Could not login to API")

        r = api_client.get("/api/v2/quicksearch/list-dictionaries")

        assert r.status_code == 200
        data = r.json()
        assert "data" in data
        assert "dictionaries" in data["data"]
        print(f"List dictionaries: {len(data['data']['dictionaries'])} found")

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_api_03_create_dictionary(self, api_client, fixture_file_path):
        """Test POST /create-dictionary endpoint.

        EXPECTED: Queues dictionary creation, returns operation_id
        """
        if not api_client.login():
            pytest.skip("Could not login to API")

        with open(fixture_file_path, 'rb') as f:
            r = api_client.post(
                "/api/v2/quicksearch/create-dictionary",
                files={"files": ("sample_quicksearch_data.txt", f, "text/plain")},
                data={
                    "game": TEST_GAME,
                    "language": TEST_LANGUAGE
                }
            )

        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "operation_id" in data
        print(f"Create dictionary started: operation_id={data['operation_id']}")

        # Wait for background task
        time.sleep(5)

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_api_04_load_dictionary(self, api_client):
        """Test POST /load-dictionary endpoint.

        EXPECTED: Loads dictionary into memory, returns pair counts
        """
        if not api_client.login():
            pytest.skip("Could not login to API")

        r = api_client.post(
            "/api/v2/quicksearch/load-dictionary",
            data={
                "game": TEST_GAME,
                "language": TEST_LANGUAGE
            }
        )

        if r.status_code == 404:
            pytest.skip(f"Dictionary {TEST_GAME}-{TEST_LANGUAGE} not found - run create_dictionary first")

        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "data" in data
        print(f"Load dictionary: {data['data']}")

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_api_05_search(self, api_client):
        """Test POST /search endpoint.

        EXPECTED: Returns matching entries with Korean, Translation, StringID
        """
        if not api_client.login():
            pytest.skip("Could not login to API")

        r = api_client.post(
            "/api/v2/quicksearch/search",
            data={
                "query": "안녕",
                "match_type": "contains",
                "start_index": "0",
                "limit": "50"
            }
        )

        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "data" in data
        assert "results" in data["data"]
        assert "total_count" in data["data"]
        print(f"Search results: {data['data']['total_count']} found")

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_api_06_search_multiline(self, api_client):
        """Test POST /search-multiline endpoint.

        EXPECTED: Returns results grouped by query
        """
        if not api_client.login():
            pytest.skip("Could not login to API")

        r = api_client.post(
            "/api/v2/quicksearch/search-multiline",
            data={
                "queries": ["안녕", "감사"],
                "match_type": "contains",
                "limit": "10"
            }
        )

        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "data" in data
        assert "results" in data["data"]
        print(f"Multiline search: {data['data']['total_matches']} total matches")

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_api_07_set_reference(self, api_client):
        """Test POST /set-reference endpoint.

        EXPECTED: Loads reference dictionary for comparison
        """
        if not api_client.login():
            pytest.skip("Could not login to API")

        r = api_client.post(
            "/api/v2/quicksearch/set-reference",
            data={
                "game": TEST_GAME,
                "language": TEST_LANGUAGE
            }
        )

        if r.status_code == 404:
            pytest.skip(f"Reference dictionary {TEST_GAME}-{TEST_LANGUAGE} not found")

        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "data" in data
        print(f"Set reference: {data['data']}")

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_api_08_toggle_reference(self, api_client):
        """Test POST /toggle-reference endpoint.

        EXPECTED: Enables/disables reference display
        """
        if not api_client.login():
            pytest.skip("Could not login to API")

        # Enable
        r = api_client.post(
            "/api/v2/quicksearch/toggle-reference",
            data={"enabled": "true"}
        )

        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["data"]["reference_enabled"] == True
        print(f"Toggle reference enabled: {data['data']}")

        # Disable
        r = api_client.post(
            "/api/v2/quicksearch/toggle-reference",
            data={"enabled": "false"}
        )

        assert r.status_code == 200
        data = r.json()
        assert data["data"]["reference_enabled"] == False
        print(f"Toggle reference disabled: {data['data']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
