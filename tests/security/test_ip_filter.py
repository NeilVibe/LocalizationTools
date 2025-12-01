"""
IP Filter Middleware Tests

Tests for the IP range filtering middleware that restricts
access to specific IP ranges for internal enterprise deployment.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.middleware.ip_filter import (
    IPFilterMiddleware,
    parse_ip_ranges,
    get_ip_filter_status,
)


class TestParseIPRanges:
    """Tests for IP range parsing."""

    def test_parse_single_range(self):
        """Test parsing a single CIDR range."""
        result = parse_ip_ranges("192.168.11.0/24")
        assert result == ["192.168.11.0/24"]

    def test_parse_multiple_ranges(self):
        """Test parsing multiple comma-separated ranges."""
        result = parse_ip_ranges("192.168.11.0/24,192.168.12.0/24,10.0.0.0/8")
        assert result == ["192.168.11.0/24", "192.168.12.0/24", "10.0.0.0/8"]

    def test_parse_with_spaces(self):
        """Test parsing handles whitespace correctly."""
        result = parse_ip_ranges("192.168.11.0/24, 192.168.12.0/24 , 10.0.0.0/8")
        assert result == ["192.168.11.0/24", "192.168.12.0/24", "10.0.0.0/8"]

    def test_parse_empty_string(self):
        """Test parsing empty string returns empty list."""
        result = parse_ip_ranges("")
        assert result == []

    def test_parse_none(self):
        """Test parsing None returns empty list."""
        result = parse_ip_ranges(None)
        assert result == []

    def test_parse_single_ip(self):
        """Test parsing single IP (no CIDR notation)."""
        result = parse_ip_ranges("192.168.11.50")
        assert result == ["192.168.11.50"]


class TestIPFilterMiddleware:
    """Tests for IP filter middleware behavior."""

    def create_app_with_filter(self, allowed_ranges=None, allow_localhost=True):
        """Helper to create a test app with IP filter."""
        app = FastAPI()

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        @app.get("/health")
        def health_endpoint():
            return {"health": "ok"}

        if allowed_ranges is not None:
            app.add_middleware(
                IPFilterMiddleware,
                allowed_ranges=allowed_ranges,
                allow_localhost=allow_localhost,
                log_blocked=False,  # Disable logging in tests
            )

        return app

    def test_no_filter_allows_all(self):
        """Test that no filter configuration allows all IPs."""
        app = self.create_app_with_filter(allowed_ranges=None)
        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200

    def test_empty_ranges_allows_all(self):
        """Test that empty ranges list allows all IPs."""
        app = self.create_app_with_filter(allowed_ranges=[])
        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200

    def test_localhost_always_allowed_by_default(self):
        """Test that localhost is allowed even with IP filter enabled."""
        # Test the middleware logic directly (TestClient uses 'testclient' as host)
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["10.0.0.0/8"],  # Different range
            allow_localhost=True,
        )

        # Localhost should be allowed even though not in 10.0.0.0/8 range
        assert middleware._is_allowed("127.0.0.1") is True
        assert middleware._is_allowed("::1") is True

        # But other IPs outside the range should be blocked
        assert middleware._is_allowed("192.168.1.1") is False

    def test_filter_blocks_outside_range(self):
        """Test that IPs outside the range are blocked."""
        app = self.create_app_with_filter(
            allowed_ranges=["192.168.11.0/24"],
            allow_localhost=False,
        )

        # Create middleware instance directly for testing
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["192.168.11.0/24"],
            allow_localhost=False,
        )

        # Test allowed IP
        assert middleware._is_allowed("192.168.11.50") is True
        assert middleware._is_allowed("192.168.11.1") is True
        assert middleware._is_allowed("192.168.11.254") is True

        # Test blocked IP
        assert middleware._is_allowed("192.168.12.50") is False
        assert middleware._is_allowed("10.0.0.1") is False
        assert middleware._is_allowed("8.8.8.8") is False

    def test_filter_allows_within_range(self):
        """Test that IPs within the range are allowed."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["192.168.11.0/24"],
            allow_localhost=False,
        )

        # All IPs in 192.168.11.x should be allowed
        assert middleware._is_allowed("192.168.11.0") is True
        assert middleware._is_allowed("192.168.11.100") is True
        assert middleware._is_allowed("192.168.11.255") is True

    def test_multiple_ranges(self):
        """Test filtering with multiple allowed ranges."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["192.168.11.0/24", "10.10.0.0/16"],
            allow_localhost=False,
        )

        # IPs in first range
        assert middleware._is_allowed("192.168.11.50") is True

        # IPs in second range
        assert middleware._is_allowed("10.10.5.100") is True
        assert middleware._is_allowed("10.10.255.255") is True

        # IPs outside both ranges
        assert middleware._is_allowed("192.168.12.50") is False
        assert middleware._is_allowed("10.11.0.1") is False

    def test_single_ip_range(self):
        """Test /32 single IP restriction."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["192.168.11.50/32"],
            allow_localhost=False,
        )

        # Only this exact IP should be allowed
        assert middleware._is_allowed("192.168.11.50") is True
        assert middleware._is_allowed("192.168.11.49") is False
        assert middleware._is_allowed("192.168.11.51") is False

    def test_localhost_bypass(self):
        """Test localhost bypass option."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["192.168.11.0/24"],
            allow_localhost=True,
        )

        # Localhost should be allowed even though not in range
        assert middleware._is_localhost("127.0.0.1") is True
        assert middleware._is_localhost("::1") is True
        assert middleware._is_localhost("localhost") is True

        # With bypass enabled, these should all be allowed
        assert middleware._is_allowed("127.0.0.1") is True

    def test_localhost_bypass_disabled(self):
        """Test localhost bypass can be disabled."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["192.168.11.0/24"],
            allow_localhost=False,
        )

        # Localhost should be blocked when bypass is disabled
        assert middleware._is_allowed("127.0.0.1") is False

    def test_invalid_ip_blocked(self):
        """Test that invalid IP formats are blocked."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["192.168.11.0/24"],
            allow_localhost=False,
        )

        assert middleware._is_allowed("invalid") is False
        assert middleware._is_allowed("999.999.999.999") is False
        assert middleware._is_allowed("") is False

    def test_x_forwarded_for_header(self):
        """Test that X-Forwarded-For header is respected."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["192.168.11.0/24"],
            allow_localhost=False,
        )

        # Create mock request with X-Forwarded-For header
        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.11.50, 10.0.0.1"}
        mock_request.client = MagicMock()
        mock_request.client.host = "10.0.0.1"

        # Should use the first IP from X-Forwarded-For
        client_ip = middleware._get_client_ip(mock_request)
        assert client_ip == "192.168.11.50"

    def test_x_real_ip_header(self):
        """Test that X-Real-IP header is respected."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["192.168.11.0/24"],
            allow_localhost=False,
        )

        # Create mock request with X-Real-IP header
        mock_request = MagicMock()
        mock_request.headers = {"X-Real-IP": "192.168.11.100"}
        mock_request.client = MagicMock()
        mock_request.client.host = "10.0.0.1"

        # Should use X-Real-IP
        client_ip = middleware._get_client_ip(mock_request)
        assert client_ip == "192.168.11.100"


class TestGetIPFilterStatus:
    """Tests for IP filter status reporting."""

    def test_status_when_enabled(self):
        """Test status reporting when filter is enabled."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["192.168.11.0/24", "10.0.0.0/8"],
            allow_localhost=True,
            log_blocked=True,
        )

        status = get_ip_filter_status(middleware)

        assert status["enabled"] is True
        assert status["allow_localhost"] is True
        assert status["log_blocked"] is True
        assert status["range_count"] == 2
        assert "192.168.11.0/24" in status["allowed_ranges"]

    def test_status_when_disabled(self):
        """Test status reporting when filter is disabled."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=[],
            allow_localhost=True,
        )

        status = get_ip_filter_status(middleware)

        assert status["enabled"] is False
        assert status["range_count"] == 0


class TestCIDRNotation:
    """Tests for various CIDR notation formats."""

    def test_class_c_network(self):
        """Test /24 (Class C) network."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["192.168.1.0/24"],
            allow_localhost=False,
        )

        # 256 addresses (192.168.1.0 - 192.168.1.255)
        assert middleware._is_allowed("192.168.1.0") is True
        assert middleware._is_allowed("192.168.1.128") is True
        assert middleware._is_allowed("192.168.1.255") is True
        assert middleware._is_allowed("192.168.2.0") is False

    def test_class_b_network(self):
        """Test /16 (Class B) network."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["172.16.0.0/16"],
            allow_localhost=False,
        )

        # 65536 addresses (172.16.0.0 - 172.16.255.255)
        assert middleware._is_allowed("172.16.0.1") is True
        assert middleware._is_allowed("172.16.128.128") is True
        assert middleware._is_allowed("172.16.255.255") is True
        assert middleware._is_allowed("172.17.0.0") is False

    def test_class_a_network(self):
        """Test /8 (Class A) network."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["10.0.0.0/8"],
            allow_localhost=False,
        )

        # 16 million+ addresses (10.0.0.0 - 10.255.255.255)
        assert middleware._is_allowed("10.0.0.1") is True
        assert middleware._is_allowed("10.128.128.128") is True
        assert middleware._is_allowed("10.255.255.255") is True
        assert middleware._is_allowed("11.0.0.0") is False

    def test_small_subnet(self):
        """Test /28 (16 addresses) network."""
        middleware = IPFilterMiddleware(
            app=MagicMock(),
            allowed_ranges=["192.168.11.0/28"],
            allow_localhost=False,
        )

        # 16 addresses (192.168.11.0 - 192.168.11.15)
        assert middleware._is_allowed("192.168.11.0") is True
        assert middleware._is_allowed("192.168.11.15") is True
        assert middleware._is_allowed("192.168.11.16") is False
