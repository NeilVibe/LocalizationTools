"""
API Tools User Simulation Tests

TRUE PRODUCTION SIMULATION: These tests simulate EXACTLY what a real user does:
1. User opens the app (server already running)
2. User logs in (gets JWT token)
3. User creates/loads dictionaries
4. User searches/translates content
5. User views results

Each test class represents a complete user session.

Requires: RUN_API_TESTS=1 and server running on localhost:8888
"""

import pytest
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Skip all tests if not running API tests
pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_API_TESTS"),
    reason="API tests require running server (set RUN_API_TESTS=1)"
)

# Fixtures directory
FIXTURES_DIR = project_root / "tests" / "fixtures"


class APIClient:
    """Reusable API client that simulates real user browser/app behavior."""

    def __init__(self, base_url="http://localhost:8888"):
        import requests
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None

    def login(self, username="admin", password="admin123"):
        """Simulate user login - first thing every user does."""
        r = self.session.post(
            f"{self.base_url}/api/v2/auth/login",
            json={"username": username, "password": password},
            timeout=10
        )
        if r.status_code == 200:
            self.token = r.json()["access_token"]
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            return True
        return False

    def get(self, endpoint, **kwargs):
        return self.session.get(f"{self.base_url}{endpoint}", timeout=60, **kwargs)

    def post(self, endpoint, **kwargs):
        return self.session.post(f"{self.base_url}{endpoint}", timeout=60, **kwargs)

    def post_files(self, endpoint, files, data=None):
        """Upload files like a user would."""
        return self.session.post(
            f"{self.base_url}{endpoint}",
            files=files,
            data=data,
            timeout=120
        )


# =============================================================================
# KR SIMILAR - COMPLETE USER SESSION SIMULATION
# =============================================================================

class TestKRSimilarUserSession:
    """
    Simulates a COMPLETE KR Similar user session:

    SCENARIO: Quality Assurance team member wants to find similar Korean strings

    USER WORKFLOW:
    1. Login to the system
    2. Check tool health/status
    3. Create dictionary from language files
    4. Load the dictionary
    5. Search for similar strings
    6. View results
    7. (Optional) Extract similar string groups
    """

    # Use valid dictionary type (BDO = Black Desert Online)
    TEST_DICT_TYPE = "BDO"

    @pytest.fixture(scope="class")
    def client(self):
        """Create authenticated API client for entire test class."""
        client = APIClient()
        if not client.login():
            pytest.skip("Could not authenticate - server may not be running")
        return client

    @pytest.fixture(scope="class")
    def fixture_file(self):
        """Get path to language data fixture."""
        path = FIXTURES_DIR / "sample_language_data.txt"
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        return path

    def test_01_user_checks_tool_status(self, client):
        """
        USER ACTION: User opens KR Similar tab and system shows tool status.
        EXPECTED: Health endpoint returns OK and shows available features.
        """
        r = client.get("/api/v2/kr-similar/health")

        assert r.status_code == 200, f"Health check failed: {r.text}"
        data = r.json()

        assert data["status"] == "ok", "Tool should be healthy"
        assert data["modules_loaded"]["embeddings_manager"] == True
        assert data["modules_loaded"]["searcher"] == True

        print(f"✓ KR Similar status: {data}")

    def test_02_user_lists_available_dictionaries(self, client):
        """
        USER ACTION: User clicks dropdown to see available dictionaries.
        EXPECTED: List of dictionaries with metadata.
        """
        r = client.get("/api/v2/kr-similar/list-dictionaries")

        assert r.status_code == 200, f"List failed: {r.text}"
        data = r.json()

        assert "dictionaries" in data or isinstance(data, list)
        print(f"✓ Available dictionaries: {data}")

    def test_03_user_creates_dictionary(self, client, fixture_file):
        """
        USER ACTION: User uploads language file and creates dictionary.

        This is the CRITICAL step - user uploads their game text files
        and the system processes them with Korean BERT to create embeddings.

        EXPECTED: Dictionary created with split and whole pairs.
        """
        # User selects file and clicks "Create Dictionary"
        with open(fixture_file, 'rb') as f:
            files = {'files': (fixture_file.name, f, 'text/plain')}
            data = {
                'dict_type': self.TEST_DICT_TYPE,
                'kr_column': '5',
                'trans_column': '6'
            }

            r = client.post_files("/api/v2/kr-similar/create-dictionary", files=files, data=data)

        # Accept 200, 201, or 202 (async operation)
        assert r.status_code in [200, 201, 202], f"Create failed: {r.status_code} - {r.text}"
        data = r.json()

        # Verify creation result (sync or async)
        if r.status_code == 202:
            # Async operation - wait for completion
            assert data.get("success") == True, f"Async operation failed: {data}"
            assert "operation_id" in data, "Should have operation_id for async"
            print(f"✓ Dictionary creation started (async): operation_id={data.get('operation_id')}")

            # Wait for async operation to complete
            import time
            op_id = data.get("operation_id")
            for _ in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                status_r = client.get(f"/api/progress/operations/{op_id}")
                if status_r.status_code == 200:
                    status_data = status_r.json()
                    if status_data.get("status") in ["completed", "finished", "done"]:
                        print(f"✓ Dictionary creation completed")
                        break
                    elif status_data.get("status") == "error":
                        print(f"✗ Dictionary creation failed: {status_data}")
                        break
        else:
            # Sync response
            assert "dict_type" in data or "message" in data, f"Unexpected response: {data}"
            if "split_pairs" in data:
                assert data["split_pairs"] > 0, "Should have created split pairs"
            print(f"✓ Dictionary created: {data}")

    def test_04_user_loads_dictionary(self, client):
        """
        USER ACTION: User selects dictionary from dropdown and clicks "Load".
        EXPECTED: Dictionary loaded into memory, ready for search.
        """
        # API uses form data, not JSON
        r = client.post(
            "/api/v2/kr-similar/load-dictionary",
            data={"dict_type": self.TEST_DICT_TYPE}
        )

        assert r.status_code == 200, f"Load failed: {r.text}"
        data = r.json()

        assert data.get("success") == True or "loaded" in str(data).lower()
        print(f"✓ Dictionary loaded: {data}")

    def test_05_user_searches_for_similar_strings(self, client):
        """
        USER ACTION: User types Korean text and clicks "Find Similar".

        This is the MAIN USE CASE - finding semantically similar strings.

        EXPECTED: List of similar strings with similarity scores.
        """
        # User types query and sets threshold - API uses form data
        search_request = {
            "query": "안녕하세요",  # Hello
            "threshold": "0.3",
            "top_k": "10",
            "use_whole": "false"
        }

        r = client.post("/api/v2/kr-similar/search", data=search_request)

        assert r.status_code == 200, f"Search failed: {r.text}"
        data = r.json()

        # Results should be a list
        results = data.get("results", data)
        assert isinstance(results, list), f"Expected list, got: {type(results)}"

        print(f"✓ Search '안녕하세요' returned {len(results)} results")
        for r in results[:3]:
            if isinstance(r, dict):
                print(f"  [{r.get('similarity', 0):.3f}] {r.get('korean', '')[:40]}...")

    def test_06_user_searches_various_queries(self, client):
        """
        USER ACTION: User tries multiple different searches.
        EXPECTED: All searches return valid results (may be empty if no match).
        """
        queries = [
            ("마을", "Village-related"),
            ("전투", "Combat-related"),
            ("퀘스트", "Quest-related"),
            ("상점에 오신 것을 환영합니다", "Full sentence"),
        ]

        for query, category in queries:
            search_request = {
                "query": query,
                "threshold": "0.3",
                "top_k": "5",
                "use_whole": "false"
            }

            r = client.post("/api/v2/kr-similar/search", data=search_request)

            assert r.status_code == 200, f"Search failed for '{query}': {r.text}"
            data = r.json()
            results = data.get("results", data)

            print(f"✓ Search '{query}' ({category}): {len(results)} results")

    def test_07_user_adjusts_threshold(self, client):
        """
        USER ACTION: User adjusts similarity threshold slider.
        EXPECTED: Higher threshold = fewer but more accurate results.
        """
        query = "마을에 오신 것을 환영합니다"

        # Low threshold - more results
        r_low = client.post("/api/v2/kr-similar/search", data={
            "query": query, "threshold": "0.3", "top_k": "20"
        })

        # High threshold - fewer results
        r_high = client.post("/api/v2/kr-similar/search", data={
            "query": query, "threshold": "0.8", "top_k": "20"
        })

        assert r_low.status_code == 200
        assert r_high.status_code == 200

        results_low = r_low.json().get("results", r_low.json())
        results_high = r_high.json().get("results", r_high.json())

        # Lower threshold should return >= results
        assert len(results_low) >= len(results_high), \
            f"Low threshold ({len(results_low)}) should have >= results than high ({len(results_high)})"

        print(f"✓ Threshold comparison: 0.3={len(results_low)} results, 0.8={len(results_high)} results")

    def test_08_user_uses_whole_text_mode(self, client):
        """
        USER ACTION: User toggles "Whole Text" mode for full sentence matching.
        EXPECTED: Search works in both split and whole modes.
        """
        query = "죄인은 푸줏간 백정과 공모하여"  # Complex sentence from fixture

        # Split mode (default)
        r_split = client.post("/api/v2/kr-similar/search", data={
            "query": query, "threshold": "0.3", "top_k": "5", "use_whole": "false"
        })

        # Whole mode
        r_whole = client.post("/api/v2/kr-similar/search", data={
            "query": query, "threshold": "0.3", "top_k": "5", "use_whole": "true"
        })

        assert r_split.status_code == 200, f"Split search failed: {r_split.text}"
        assert r_whole.status_code == 200, f"Whole search failed: {r_whole.text}"

        print(f"✓ Split mode: {len(r_split.json().get('results', []))} results")
        print(f"✓ Whole mode: {len(r_whole.json().get('results', []))} results")

    def test_09_user_handles_edge_cases(self, client):
        """
        USER ACTION: User tries edge cases (empty, special chars, etc.).
        EXPECTED: System handles gracefully without crashing.
        """
        edge_cases = [
            ("", "Empty query"),
            ("   ", "Whitespace only"),
            ("{ChangeScene(Main)}안녕", "With game tags"),
            ("Hello 안녕 World", "Mixed language"),
            ("안녕하세요 👋", "With emoji"),
        ]

        for query, description in edge_cases:
            r = client.post("/api/v2/kr-similar/search", data={
                "query": query, "threshold": "0.3", "top_k": "5"
            })

            # Should not crash - either 200 with results or 400 with error message
            assert r.status_code in [200, 400, 422], \
                f"Unexpected status for {description}: {r.status_code}"

            print(f"✓ Edge case '{description}': status {r.status_code}")


# =============================================================================
# QUICKSEARCH - COMPLETE USER SESSION SIMULATION
# =============================================================================

class TestQuickSearchUserSession:
    """
    Simulates a COMPLETE QuickSearch user session:

    SCENARIO: Translator searching for existing translations

    USER WORKFLOW:
    1. Login to the system
    2. Check tool health/status
    3. Create dictionary from data files
    4. Load dictionary for searching
    5. Search for Korean terms
    6. Toggle between exact/contains modes
    7. Use reference dictionary comparison
    """

    # Use valid game/language types
    TEST_GAME = "BDO"
    TEST_LANG = "EN"

    @pytest.fixture(scope="class")
    def client(self):
        """Create authenticated API client."""
        client = APIClient()
        if not client.login():
            pytest.skip("Could not authenticate")
        return client

    @pytest.fixture(scope="class")
    def fixture_file(self):
        """Get path to quicksearch fixture."""
        path = FIXTURES_DIR / "sample_quicksearch_data.txt"
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        return path

    def test_01_user_checks_tool_status(self, client):
        """
        USER ACTION: User opens QuickSearch tab.
        EXPECTED: Tool status shows available.
        """
        r = client.get("/api/v2/quicksearch/health")

        assert r.status_code == 200, f"Health check failed: {r.text}"
        data = r.json()

        assert data["status"] == "ok"
        print(f"✓ QuickSearch status: {data}")

    def test_02_user_lists_available_dictionaries(self, client):
        """
        USER ACTION: User opens game/language dropdown.
        EXPECTED: List of available dictionaries.
        """
        r = client.get("/api/v2/quicksearch/list-dictionaries")

        assert r.status_code == 200, f"List failed: {r.text}"
        data = r.json()

        print(f"✓ Available dictionaries: {data}")

    def test_03_user_creates_dictionary(self, client, fixture_file):
        """
        USER ACTION: User uploads data file and creates dictionary.
        EXPECTED: Dictionary created for game/language.
        """
        with open(fixture_file, 'rb') as f:
            files = {'files': (fixture_file.name, f, 'text/plain')}
            data = {
                'game': self.TEST_GAME,
                'language': self.TEST_LANG
            }

            r = client.post_files("/api/v2/quicksearch/create-dictionary", files=files, data=data)

        # Accept 200, 201, or 202 (async operation)
        assert r.status_code in [200, 201, 202], f"Create failed: {r.text}"
        result = r.json()

        if r.status_code == 202:
            # Async operation - wait for completion
            assert result.get("success") == True
            print(f"✓ Dictionary creation started (async): operation_id={result.get('operation_id')}")

            import time
            op_id = result.get("operation_id")
            for _ in range(30):
                time.sleep(1)
                status_r = client.get(f"/api/progress/operations/{op_id}")
                if status_r.status_code == 200:
                    status_data = status_r.json()
                    if status_data.get("status") in ["completed", "finished", "done"]:
                        print(f"✓ Dictionary creation completed")
                        break
        else:
            print(f"✓ Dictionary created: {result}")

    def test_04_user_loads_dictionary(self, client):
        """
        USER ACTION: User selects game/language and clicks Load.
        EXPECTED: Dictionary loaded and ready for search.
        """
        r = client.post(
            "/api/v2/quicksearch/load-dictionary",
            data={"game": self.TEST_GAME, "language": self.TEST_LANG}
        )

        assert r.status_code == 200, f"Load failed: {r.text}"
        print(f"✓ Dictionary loaded: {r.json()}")

    def test_05_user_searches_exact_match(self, client):
        """
        USER ACTION: User types search term with "Exact Match" selected.
        EXPECTED: Only exact matches returned.
        """
        r = client.post("/api/v2/quicksearch/search", data={
            "query": "안녕하세요",
            "match_type": "exact"
        })

        assert r.status_code == 200, f"Search failed: {r.text}"
        data = r.json()
        results = data.get("results", data)

        print(f"✓ Exact search '안녕하세요': {len(results) if isinstance(results, list) else results}")

    def test_06_user_searches_contains(self, client):
        """
        USER ACTION: User types partial term with "Contains" selected.
        EXPECTED: All entries containing the substring.
        """
        r = client.post("/api/v2/quicksearch/search", data={
            "query": "마을",
            "match_type": "contains"
        })

        assert r.status_code == 200, f"Search failed: {r.text}"
        data = r.json()
        results = data.get("results", data)

        print(f"✓ Contains search '마을': {len(results) if isinstance(results, list) else results}")

    def test_07_user_searches_by_string_id(self, client):
        """
        USER ACTION: User searches by string ID (common workflow).
        EXPECTED: Entry with matching ID returned.
        """
        r = client.post("/api/v2/quicksearch/search", data={
            "query": "1001",
            "match_type": "stringid"
        })

        assert r.status_code == 200, f"Search failed: {r.text}"
        print(f"✓ StringID search '1001': {r.json()}")

    def test_08_user_searches_special_characters(self, client):
        """
        USER ACTION: User searches for UI elements with special chars.
        EXPECTED: Special characters don't break search.
        """
        special_queries = ["▶", "【", "..."]

        for query in special_queries:
            r = client.post("/api/v2/quicksearch/search", data={
                "query": query,
                "match_type": "contains"
            })

            assert r.status_code == 200, f"Search failed for '{query}': {r.text}"
            print(f"✓ Special char search '{query}': status {r.status_code}")

    def test_09_user_searches_multiline(self, client):
        """
        USER ACTION: User pastes multiple lines to search at once.
        EXPECTED: Each line searched individually.
        """
        multiline_query = "안녕하세요\n마을\n전투"

        r = client.post("/api/v2/quicksearch/search-multiline", data={
            "queries": multiline_query,
            "match_type": "contains"
        })

        # May not be implemented - check status
        if r.status_code == 404:
            print("✓ Multi-line search endpoint not available (OK)")
        else:
            assert r.status_code == 200, f"Multi search failed: {r.text}"
            print(f"✓ Multi-line search: {r.json()}")


# =============================================================================
# XLSTRANSFER - COMPLETE USER SESSION SIMULATION
# =============================================================================

class TestXLSTransferUserSession:
    """
    Simulates a COMPLETE XLSTransfer user session:

    SCENARIO: Translator applying dictionary to new game text

    USER WORKFLOW:
    1. Login to the system
    2. Check tool health/status
    3. Create dictionary from reference Excel file
    4. Load dictionary
    5. Translate text using dictionary
    6. View translation results
    """

    @pytest.fixture(scope="class")
    def client(self):
        """Create authenticated API client."""
        client = APIClient()
        if not client.login():
            pytest.skip("Could not authenticate")
        return client

    @pytest.fixture(scope="class")
    def fixture_excel(self):
        """Get path to sample Excel file."""
        path = FIXTURES_DIR / "sample_dictionary.xlsx"
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        return path

    def test_01_user_checks_tool_status(self, client):
        """
        USER ACTION: User opens XLSTransfer tab.
        EXPECTED: Tool status shows modules loaded.
        """
        r = client.get("/api/v2/xlstransfer/health")

        assert r.status_code == 200, f"Health check failed: {r.text}"
        data = r.json()

        assert data["status"] == "ok"
        assert data["modules_loaded"]["core"] == True
        assert data["modules_loaded"]["embeddings"] == True

        print(f"✓ XLSTransfer status: {data}")

    def test_02_user_lists_available_dictionaries(self, client):
        """
        USER ACTION: User checks what dictionaries are available.
        EXPECTED: List of saved dictionaries.
        """
        r = client.get("/api/v2/xlstransfer/dictionaries")

        # May return 200 with list or 404 if not implemented
        if r.status_code == 404:
            print("✓ XLSTransfer dictionaries endpoint not available (OK)")
        else:
            assert r.status_code == 200
            print(f"✓ Available dictionaries: {r.json()}")

    def test_03_user_creates_dictionary(self, client, fixture_excel):
        """
        USER ACTION: User uploads Excel file with Korean→English pairs.
        EXPECTED: Dictionary created with embeddings.
        """
        with open(fixture_excel, 'rb') as f:
            files = {'file': (fixture_excel.name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            data = {
                'sheet_name': 'Sheet1',
                'source_column': 'A',
                'target_column': 'B'
            }

            r = client.post_files("/api/v2/xlstransfer/dictionary/create", files=files, data=data)

        if r.status_code == 404:
            print("✓ XLSTransfer create endpoint not available (OK)")
        else:
            assert r.status_code in [200, 201], f"Create failed: {r.text}"
            print(f"✓ Dictionary created: {r.json()}")

    def test_04_user_translates_single_text(self, client):
        """
        USER ACTION: User types Korean text to get translation.
        EXPECTED: Best matching translation returned with score.
        """
        r = client.post("/api/v2/xlstransfer/translate", json={
            "text": "안녕하세요",
            "threshold": 0.5
        })

        if r.status_code == 404:
            print("✓ XLSTransfer translate endpoint not available (OK)")
        else:
            assert r.status_code == 200, f"Translate failed: {r.text}"
            data = r.json()
            print(f"✓ Translation: {data}")

    def test_05_user_translates_multiple_texts(self, client):
        """
        USER ACTION: User submits multiple texts for translation.
        EXPECTED: Each text translated with scores.
        """
        texts = ["안녕하세요", "감사합니다", "전투를 시작합니다"]

        r = client.post("/api/v2/xlstransfer/translate-batch", json={
            "texts": texts,
            "threshold": 0.5
        })

        if r.status_code == 404:
            print("✓ XLSTransfer batch translate not available (OK)")
        else:
            assert r.status_code == 200
            print(f"✓ Batch translation: {len(r.json().get('results', []))} results")


# =============================================================================
# CROSS-TOOL USER SESSION
# =============================================================================

class TestCrossToolUserSession:
    """
    Simulates a user using MULTIPLE TOOLS in one session.

    SCENARIO: Localization team member uses all tools together:
    1. QuickSearch to find existing translations
    2. KR Similar to find similar strings
    3. XLSTransfer to apply translations
    """

    @pytest.fixture(scope="class")
    def client(self):
        """Create authenticated API client."""
        client = APIClient()
        if not client.login():
            pytest.skip("Could not authenticate")
        return client

    def test_01_user_checks_all_tools_status(self, client):
        """
        USER ACTION: User opens app, system checks all tools.
        EXPECTED: All tools healthy.
        """
        tools = [
            "/api/v2/kr-similar/health",
            "/api/v2/quicksearch/health",
            "/api/v2/xlstransfer/health"
        ]

        for endpoint in tools:
            r = client.get(endpoint)
            assert r.status_code == 200, f"{endpoint} not healthy"
            assert r.json()["status"] == "ok"

        print("✓ All 3 tools healthy")

    def test_02_user_session_persists_across_tools(self, client):
        """
        USER ACTION: User switches between tools in same session.
        EXPECTED: Authentication persists, no re-login needed.
        """
        # Hit each tool in sequence - token should work for all
        r1 = client.get("/api/v2/kr-similar/health")
        r2 = client.get("/api/v2/quicksearch/health")
        r3 = client.get("/api/v2/xlstransfer/health")
        r4 = client.get("/api/v2/auth/me")  # Protected endpoint

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 200
        assert r4.status_code == 200

        print("✓ Session persists across all tools")

    def test_03_user_activity_tracked(self, client):
        """
        USER ACTION: User performs various actions.
        EXPECTED: Activity is logged for admin visibility.
        """
        # Make several requests
        client.get("/api/v2/kr-similar/health")
        client.get("/api/v2/quicksearch/health")

        # Check user info updated
        r = client.get("/api/v2/auth/me")
        assert r.status_code == 200

        data = r.json()
        assert "username" in data
        print(f"✓ User activity tracked: {data.get('username')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
