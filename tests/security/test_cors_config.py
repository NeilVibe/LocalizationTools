"""
Security Tests: CORS Configuration

Tests for CORS (Cross-Origin Resource Sharing) configuration.
Verifies that CORS settings work correctly in both development and production modes.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCORSConfiguration:
    """Tests for CORS configuration in server/config.py"""

    def test_01_default_development_mode(self):
        """Test that default config (no env vars) enables CORS_ALLOW_ALL.

        SECURITY: In development (no CORS_ORIGINS set), we allow all origins
        for convenience during local testing.
        """
        # Clear any existing CORS env vars
        with patch.dict(os.environ, {}, clear=True):
            # Force reload of config module
            if 'server.config' in sys.modules:
                del sys.modules['server.config']
            if 'server' in sys.modules:
                del sys.modules['server']

            from server import config

            # In development mode, CORS_ALLOW_ALL should be True
            assert config.CORS_ALLOW_ALL == True, "Development mode should allow all origins"
            assert len(config.CORS_ORIGINS) > 0, "Should have default localhost origins"

            # Verify localhost origins are present
            localhost_origins = [o for o in config.CORS_ORIGINS if 'localhost' in o or '127.0.0.1' in o]
            assert len(localhost_origins) > 0, "Should include localhost origins"

            print(f"Development mode: CORS_ALLOW_ALL={config.CORS_ALLOW_ALL}")
            print(f"Default origins: {len(config.CORS_ORIGINS)} localhost variants")

    def test_02_production_mode_with_cors_origins(self):
        """Test that setting CORS_ORIGINS disables CORS_ALLOW_ALL.

        SECURITY: When CORS_ORIGINS is set, only those specific origins
        are allowed - this is the production configuration.
        """
        production_origins = "http://192.168.11.100:5173,http://192.168.11.100:5175"

        with patch.dict(os.environ, {'CORS_ORIGINS': production_origins}, clear=True):
            # Force reload
            if 'server.config' in sys.modules:
                del sys.modules['server.config']
            if 'server' in sys.modules:
                del sys.modules['server']

            from server import config

            assert config.CORS_ALLOW_ALL == False, "Production mode should NOT allow all origins"
            assert len(config.CORS_ORIGINS) == 2, "Should have exactly 2 origins"
            assert "http://192.168.11.100:5173" in config.CORS_ORIGINS
            assert "http://192.168.11.100:5175" in config.CORS_ORIGINS

            print(f"Production mode: CORS_ALLOW_ALL={config.CORS_ALLOW_ALL}")
            print(f"Whitelisted origins: {config.CORS_ORIGINS}")

    def test_03_production_origin_legacy_support(self):
        """Test that PRODUCTION_ORIGIN env var still works (backward compatibility).

        SECURITY: Legacy support for older deployments using PRODUCTION_ORIGIN.
        """
        with patch.dict(os.environ, {'PRODUCTION_ORIGIN': 'https://locanext.company.com'}, clear=True):
            if 'server.config' in sys.modules:
                del sys.modules['server.config']
            if 'server' in sys.modules:
                del sys.modules['server']

            from server import config

            assert config.CORS_ALLOW_ALL == False, "Setting PRODUCTION_ORIGIN should disable CORS_ALLOW_ALL"
            assert 'https://locanext.company.com' in config.CORS_ORIGINS

            print(f"Legacy PRODUCTION_ORIGIN support works")

    def test_04_cors_credentials_default(self):
        """Test that CORS_ALLOW_CREDENTIALS defaults to True.

        SECURITY: Credentials (cookies, auth headers) should be allowed
        for authenticated API access.
        """
        with patch.dict(os.environ, {}, clear=True):
            if 'server.config' in sys.modules:
                del sys.modules['server.config']
            if 'server' in sys.modules:
                del sys.modules['server']

            from server import config

            assert config.CORS_ALLOW_CREDENTIALS == True, "Should allow credentials by default"
            print("CORS_ALLOW_CREDENTIALS defaults to True")

    def test_05_cors_credentials_can_be_disabled(self):
        """Test that CORS_ALLOW_CREDENTIALS can be disabled via env var."""
        with patch.dict(os.environ, {'CORS_ALLOW_CREDENTIALS': 'false'}, clear=True):
            if 'server.config' in sys.modules:
                del sys.modules['server.config']
            if 'server' in sys.modules:
                del sys.modules['server']

            from server import config

            assert config.CORS_ALLOW_CREDENTIALS == False, "Should be disabled when set to false"
            print("CORS_ALLOW_CREDENTIALS can be disabled")

    def test_06_cors_methods_default(self):
        """Test that default CORS methods include standard HTTP methods."""
        with patch.dict(os.environ, {}, clear=True):
            if 'server.config' in sys.modules:
                del sys.modules['server.config']
            if 'server' in sys.modules:
                del sys.modules['server']

            from server import config

            required_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
            for method in required_methods:
                assert method in config.CORS_ALLOW_METHODS, f"Should allow {method}"

            print(f"Default CORS methods: {config.CORS_ALLOW_METHODS}")

    def test_07_cors_headers_include_authorization(self):
        """Test that CORS headers include Authorization for JWT tokens.

        SECURITY: Authorization header must be allowed for JWT-based auth.
        """
        with patch.dict(os.environ, {}, clear=True):
            if 'server.config' in sys.modules:
                del sys.modules['server.config']
            if 'server' in sys.modules:
                del sys.modules['server']

            from server import config

            assert 'Authorization' in config.CORS_ALLOW_HEADERS, "Must allow Authorization header"
            assert 'Content-Type' in config.CORS_ALLOW_HEADERS, "Must allow Content-Type header"

            print(f"Default CORS headers: {config.CORS_ALLOW_HEADERS}")

    def test_08_empty_cors_origins_falls_back_to_development(self):
        """Test that empty CORS_ORIGINS falls back to development mode."""
        with patch.dict(os.environ, {'CORS_ORIGINS': ''}, clear=True):
            if 'server.config' in sys.modules:
                del sys.modules['server.config']
            if 'server' in sys.modules:
                del sys.modules['server']

            from server import config

            # Empty string should fall back to development mode
            assert config.CORS_ALLOW_ALL == True, "Empty CORS_ORIGINS should fall back to dev mode"
            print("Empty CORS_ORIGINS correctly falls back to development mode")

    def test_09_whitespace_handling_in_origins(self):
        """Test that whitespace around origins is handled correctly."""
        # Origins with extra whitespace
        origins_with_spaces = " http://192.168.1.1:5173 , http://192.168.1.2:5173 "

        with patch.dict(os.environ, {'CORS_ORIGINS': origins_with_spaces}, clear=True):
            if 'server.config' in sys.modules:
                del sys.modules['server.config']
            if 'server' in sys.modules:
                del sys.modules['server']

            from server import config

            # Should strip whitespace
            assert "http://192.168.1.1:5173" in config.CORS_ORIGINS
            assert "http://192.168.1.2:5173" in config.CORS_ORIGINS

            # Should not have leading/trailing spaces
            for origin in config.CORS_ORIGINS:
                assert origin == origin.strip(), f"Origin '{origin}' has whitespace"

            print("Whitespace in CORS_ORIGINS handled correctly")


class TestCORSSecurityValidation:
    """Security validation tests for CORS configuration"""

    def test_10_no_wildcard_in_production(self):
        """Verify that production mode never allows wildcard origin.

        SECURITY CRITICAL: Wildcard (*) origin should NEVER be used
        when CORS_ORIGINS is explicitly set.
        """
        production_origins = "http://192.168.11.100:5173"

        with patch.dict(os.environ, {'CORS_ORIGINS': production_origins}, clear=True):
            if 'server.config' in sys.modules:
                del sys.modules['server.config']
            if 'server' in sys.modules:
                del sys.modules['server']

            from server import config

            assert '*' not in config.CORS_ORIGINS, "Wildcard should never be in explicit origins"
            assert config.CORS_ALLOW_ALL == False, "CORS_ALLOW_ALL must be False in production"

            print("SECURITY: No wildcard in production mode - VERIFIED")

    def test_11_backward_compatibility_alias(self):
        """Test that ALLOWED_ORIGINS alias works for backward compatibility."""
        with patch.dict(os.environ, {}, clear=True):
            if 'server.config' in sys.modules:
                del sys.modules['server.config']
            if 'server' in sys.modules:
                del sys.modules['server']

            from server import config

            # ALLOWED_ORIGINS should be an alias for CORS_ORIGINS
            assert config.ALLOWED_ORIGINS == config.CORS_ORIGINS, "ALLOWED_ORIGINS should alias CORS_ORIGINS"

            print("Backward compatibility: ALLOWED_ORIGINS alias works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
