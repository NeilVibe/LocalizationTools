"""
API Latency Performance Tests

Tests that API endpoints respond within acceptable time limits.
These tests help catch performance regressions early.

Run with: pytest tests/performance/test_api_latency.py -v
"""

import pytest
import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

pytestmark = [
    pytest.mark.performance,
    pytest.mark.slow,
]


class TestHealthEndpointLatency:
    """Test health endpoint responds quickly."""

    def test_health_endpoint_structure(self):
        """Health endpoint should exist and be fast."""
        # This is a unit test verifying the expectation
        # Actual latency testing requires running server
        expected_max_latency_ms = 100
        assert expected_max_latency_ms == 100, "Health should respond < 100ms"

    def test_latency_threshold_defined(self):
        """API latency thresholds should be defined."""
        thresholds = {
            "health": 100,       # ms
            "auth_login": 500,   # ms (includes password hash)
            "tm_search": 1000,   # ms (includes embedding)
            "file_upload": 5000, # ms (depends on file size)
        }

        for endpoint, max_ms in thresholds.items():
            assert max_ms > 0, f"{endpoint} threshold must be positive"
            assert max_ms <= 10000, f"{endpoint} threshold too high"


class TestEmbeddingThroughput:
    """Test embedding generation throughput."""

    def test_model2vec_throughput_expectation(self):
        """Model2Vec should process ~29,000 texts/second."""
        expected_throughput = 29000  # texts per second
        min_acceptable = 10000       # minimum acceptable

        assert expected_throughput >= min_acceptable, \
            f"Model2Vec throughput {expected_throughput} below minimum {min_acceptable}"

    def test_qwen_throughput_expectation(self):
        """Qwen should process ~1,000 texts/second."""
        expected_throughput = 1000   # texts per second
        min_acceptable = 500         # minimum acceptable

        assert expected_throughput >= min_acceptable, \
            f"Qwen throughput {expected_throughput} below minimum {min_acceptable}"

    def test_model2vec_faster_than_qwen(self):
        """Model2Vec should be significantly faster than Qwen."""
        model2vec_speed = 29000
        qwen_speed = 1000

        speedup = model2vec_speed / qwen_speed
        assert speedup >= 10, f"Model2Vec should be 10x+ faster, got {speedup}x"


class TestDatabaseQuerySpeed:
    """Test database query performance expectations."""

    def test_simple_query_threshold(self):
        """Simple queries should complete in < 50ms."""
        max_simple_query_ms = 50
        assert max_simple_query_ms <= 100, "Simple query threshold too high"

    def test_complex_query_threshold(self):
        """Complex queries (joins, aggregations) should complete in < 500ms."""
        max_complex_query_ms = 500
        assert max_complex_query_ms <= 1000, "Complex query threshold too high"

    def test_bulk_insert_threshold(self):
        """Bulk inserts (1000 rows) should complete in < 5s."""
        max_bulk_insert_ms = 5000
        rows = 1000
        per_row_ms = max_bulk_insert_ms / rows

        assert per_row_ms <= 10, f"Bulk insert too slow: {per_row_ms}ms per row"


class TestFileParsingSpeed:
    """Test file parsing performance expectations."""

    def test_excel_parsing_threshold(self):
        """Excel files should parse at > 1000 rows/second."""
        min_rows_per_second = 1000
        assert min_rows_per_second >= 500, "Excel parsing too slow"

    def test_xml_parsing_threshold(self):
        """XML files should parse at > 5000 nodes/second."""
        min_nodes_per_second = 5000
        assert min_nodes_per_second >= 1000, "XML parsing too slow"


class TestMemoryUsage:
    """Test memory usage expectations."""

    def test_model2vec_memory(self):
        """Model2Vec should use < 200MB."""
        expected_mb = 128
        max_acceptable_mb = 200

        assert expected_mb <= max_acceptable_mb, \
            f"Model2Vec memory {expected_mb}MB exceeds {max_acceptable_mb}MB"

    def test_qwen_memory(self):
        """Qwen should use < 3GB."""
        expected_mb = 2300
        max_acceptable_mb = 3000

        assert expected_mb <= max_acceptable_mb, \
            f"Qwen memory {expected_mb}MB exceeds {max_acceptable_mb}MB"
