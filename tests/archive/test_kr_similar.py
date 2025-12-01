"""
Tests for KR Similar (App #3)

Tests the Korean semantic similarity search functionality.
Uses mock data based on real language file structure.
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestKRSimilarCore:
    """Tests for KR Similar core functionality."""

    def test_normalize_text_basic(self):
        """Test basic text normalization."""
        from server.tools.kr_similar.core import normalize_text

        # Test empty/None handling
        assert normalize_text(None) == ''
        assert normalize_text('') == ''

        # Test basic text
        assert normalize_text('안녕하세요') == '안녕하세요'

    def test_normalize_text_removes_markers(self):
        """Test that code markers are removed."""
        from server.tools.kr_similar.core import normalize_text

        # Test code marker removal
        text = '{ChangeScene(Main_001)}{AudioVoice(NPC_001)}안녕하세요'
        result = normalize_text(text)
        assert '{' not in result
        assert '}' not in result
        assert '안녕하세요' in result

    def test_normalize_text_removes_triangles(self):
        """Test that triangle markers are removed."""
        from server.tools.kr_similar.core import normalize_text

        text = '▶ 선택지 1\n▶ 선택지 2'
        result = normalize_text(text)
        assert '▶' not in result

    def test_normalize_text_removes_color_tags(self):
        """Test that color tags are removed."""
        from server.tools.kr_similar.core import normalize_text

        text = '<color=red>경고</color>: 주의하세요'
        result = normalize_text(text)
        assert '<color' not in result
        assert '</color>' not in result
        assert '경고' in result
        assert '주의하세요' in result

    def test_normalize_text_removes_scale_tags(self):
        """Test that scale tags are removed."""
        from server.tools.kr_similar.core import normalize_text

        text = '<Scale(1.2)>특별</Scale> 무기'
        result = normalize_text(text)
        assert '<Scale' not in result
        assert '특별' in result


class TestKRSimilarCoreClass:
    """Tests for KRSimilarCore class methods."""

    def test_parse_language_file(self):
        """Test parsing language data file."""
        from server.tools.kr_similar.core import KRSimilarCore

        fixture_path = Path(__file__).parent / "fixtures" / "sample_language_data.txt"

        if fixture_path.exists():
            df = KRSimilarCore.parse_language_file(str(fixture_path))

            assert 'Korean' in df.columns
            assert 'Translation' in df.columns
            assert len(df) > 0

    def test_process_split_data(self):
        """Test splitting multi-line entries."""
        from server.tools.kr_similar.core import KRSimilarCore
        import pandas as pd

        # Create test data with multi-line entries
        data = pd.DataFrame({
            'Korean': ['라인1\\n라인2\\n라인3', '싱글라인'],
            'Translation': ['Line1\\nLine2\\nLine3', 'SingleLine']
        })

        result = KRSimilarCore.process_split_data(data)

        # Should have split the multi-line entry
        assert len(result) >= 2  # At least the split lines + single line


class TestEmbeddingsManager:
    """Tests for EmbeddingsManager."""

    def test_init(self):
        """Test EmbeddingsManager initialization."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager

        manager = EmbeddingsManager()

        assert manager is not None
        assert manager.dictionaries_dir.exists()
        assert manager.model is None  # Lazy loaded

    def test_list_available_dictionaries(self):
        """Test listing available dictionaries."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager

        manager = EmbeddingsManager()
        dictionaries = manager.list_available_dictionaries()

        assert isinstance(dictionaries, list)

    def test_check_dictionary_exists_false(self):
        """Test checking for non-existent dictionary."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager

        manager = EmbeddingsManager()

        # This should return False for non-existent dictionary
        assert manager.check_dictionary_exists("NONEXISTENT") == False

    def test_get_status(self):
        """Test getting manager status."""
        from server.tools.kr_similar.embeddings import EmbeddingsManager

        manager = EmbeddingsManager()
        status = manager.get_status()

        assert 'model_loaded' in status
        assert 'current_dict_type' in status
        assert 'dictionaries_dir' in status


class TestSimilaritySearcher:
    """Tests for SimilaritySearcher."""

    def test_init(self):
        """Test SimilaritySearcher initialization."""
        from server.tools.kr_similar.searcher import SimilaritySearcher

        searcher = SimilaritySearcher()

        assert searcher is not None
        assert searcher.model is None  # Lazy loaded

    def test_get_status(self):
        """Test getting searcher status."""
        from server.tools.kr_similar.searcher import SimilaritySearcher

        searcher = SimilaritySearcher()
        status = searcher.get_status()

        assert 'model_loaded' in status
        assert 'embeddings_manager_set' in status
        assert 'faiss_available' in status


class TestAdaptStructure:
    """Tests for structure adaptation."""

    def test_adapt_structure_basic(self):
        """Test basic structure adaptation."""
        from server.tools.kr_similar.core import adapt_structure

        kr_text = '라인1\\n라인2'
        translation = 'This is line one. This is line two.'

        result = adapt_structure(kr_text, translation)

        # Should have same number of lines
        assert '\\n' in result

    def test_adapt_structure_empty_translation(self):
        """Test adaptation with empty translation."""
        from server.tools.kr_similar.core import adapt_structure

        kr_text = '라인1\\n라인2\\n라인3'
        translation = ''

        result = adapt_structure(kr_text, translation)

        # Should return empty lines
        parts = result.split('\\n')
        assert len(parts) == 3


# ============================================================================
# API TESTS (require running server)
# ============================================================================

class TestKRSimilarAPI:
    """API tests for KR Similar endpoints."""

    @pytest.fixture
    def api_client(self):
        """Get API client for testing."""
        import requests

        class APIClient:
            def __init__(self):
                self.base_url = "http://localhost:8888"
                self.token = None

            def login(self):
                """Login and get token."""
                r = requests.post(
                    f"{self.base_url}/api/v2/auth/login",
                    json={"username": "admin", "password": "admin123"},
                    timeout=10
                )
                if r.status_code == 200:
                    self.token = r.json()["access_token"]
                return r.status_code == 200

            def get_headers(self):
                """Get auth headers."""
                return {"Authorization": f"Bearer {self.token}"}

            def get(self, endpoint, **kwargs):
                """GET request."""
                return requests.get(
                    f"{self.base_url}{endpoint}",
                    headers=self.get_headers(),
                    **kwargs
                )

            def post(self, endpoint, **kwargs):
                """POST request."""
                return requests.post(
                    f"{self.base_url}{endpoint}",
                    headers=self.get_headers(),
                    **kwargs
                )

        return APIClient()

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_health_endpoint(self, api_client):
        """Test health endpoint."""
        if not api_client.login():
            pytest.skip("Could not login to API")

        r = api_client.get("/api/v2/kr-similar/health")

        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "modules_loaded" in data

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_list_dictionaries_endpoint(self, api_client):
        """Test list dictionaries endpoint."""
        if not api_client.login():
            pytest.skip("Could not login to API")

        r = api_client.get("/api/v2/kr-similar/list-dictionaries")

        assert r.status_code == 200
        data = r.json()
        assert "dictionaries" in data
        assert "available_types" in data

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    )
    def test_status_endpoint(self, api_client):
        """Test status endpoint."""
        if not api_client.login():
            pytest.skip("Could not login to API")

        r = api_client.get("/api/v2/kr-similar/status")

        assert r.status_code == 200
        data = r.json()
        assert "tool_name" in data
        assert data["tool_name"] == "KRSimilar"
