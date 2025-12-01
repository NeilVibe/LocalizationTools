"""
JWT Security Tests

Tests for JWT token security, SECRET_KEY validation,
and security configuration checks.
"""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestSecurityConfigCheck:
    """Tests for security configuration validation."""

    def test_check_security_config_with_defaults(self):
        """Test that default values trigger warnings."""
        # Import fresh to get default values
        from server import config

        result = config.check_security_config()

        # Should have warnings for default values
        assert len(result["warnings"]) > 0
        assert result["is_secure"] is True  # warn mode doesn't set errors
        assert "SECRET_KEY" in str(result["warnings"])

    def test_check_security_config_detects_default_secret_key(self):
        """Test detection of default SECRET_KEY."""
        from server import config

        # Check if using default
        is_default = config.SECRET_KEY == config._DEFAULT_SECRET_KEY

        if is_default:
            result = config.check_security_config()
            warning_text = " ".join(result["warnings"])
            assert "SECRET_KEY" in warning_text

    def test_check_security_config_detects_default_api_key(self):
        """Test detection of default API_KEY."""
        from server import config

        is_default = config.API_KEY == config._DEFAULT_API_KEY

        if is_default:
            result = config.check_security_config()
            warning_text = " ".join(result["warnings"])
            assert "API_KEY" in warning_text

    def test_check_security_config_detects_default_admin_password(self):
        """Test detection of default admin password."""
        from server import config

        result = config.check_security_config()
        warning_text = " ".join(result["warnings"])
        assert "admin123" in warning_text or "admin password" in warning_text.lower()

    def test_check_security_config_detects_missing_ip_filter(self):
        """Test detection of missing IP range filter."""
        from server import config

        if not config.ALLOWED_IP_RANGE:
            result = config.check_security_config()
            warning_text = " ".join(result["warnings"])
            assert "ALLOWED_IP_RANGE" in warning_text or "any IP" in warning_text

    def test_check_security_config_detects_open_cors(self):
        """Test detection of CORS allowing all origins."""
        from server import config

        if config.CORS_ALLOW_ALL:
            result = config.check_security_config()
            warning_text = " ".join(result["warnings"])
            assert "CORS" in warning_text


class TestSecurityConfigWithEnvVars:
    """Tests for security config with custom environment variables."""

    def test_secure_secret_key_no_warning(self):
        """Test that a secure SECRET_KEY doesn't trigger warning."""
        with patch.dict(os.environ, {"SECRET_KEY": "a-very-secure-secret-key-that-is-long-enough-12345"}):
            # Need to reload config to pick up new env var
            import importlib
            from server import config
            importlib.reload(config)

            result = config.check_security_config()
            warning_text = " ".join(result["warnings"])

            # Should not warn about SECRET_KEY being default
            assert "SECRET_KEY is using default" not in warning_text

            # Reload with defaults for other tests
            with patch.dict(os.environ, {}, clear=True):
                importlib.reload(config)

    def test_short_secret_key_warning(self):
        """Test that a short SECRET_KEY triggers warning."""
        with patch.dict(os.environ, {"SECRET_KEY": "short"}):
            import importlib
            from server import config
            importlib.reload(config)

            result = config.check_security_config()
            warning_text = " ".join(result["warnings"])

            # Should warn about short key
            assert "characters" in warning_text.lower() or "short" in warning_text.lower()

            # Reload with defaults
            with patch.dict(os.environ, {}, clear=True):
                importlib.reload(config)

    def test_strict_mode_creates_errors(self):
        """Test that strict mode converts warnings to errors for critical issues."""
        with patch.dict(os.environ, {"SECURITY_MODE": "strict"}):
            import importlib
            from server import config
            importlib.reload(config)

            result = config.check_security_config()

            # In strict mode with defaults, should have errors
            assert len(result["errors"]) > 0
            assert result["is_secure"] is False

            # Reload with defaults
            with patch.dict(os.environ, {}, clear=True):
                importlib.reload(config)


class TestValidateSecurityOnStartup:
    """Tests for startup security validation."""

    def test_validate_returns_true_in_warn_mode(self):
        """Test that validation returns True in warn mode (default)."""
        from server import config

        # In warn mode, should return True even with warnings
        result = config.validate_security_on_startup(logger=None)
        assert result is True

    def test_validate_logs_warnings(self):
        """Test that validation logs warnings."""
        from server import config

        mock_logger = MagicMock()
        config.validate_security_on_startup(logger=mock_logger)

        # Should have called warning at least once (for default values)
        assert mock_logger.warning.called

    def test_validate_returns_false_in_strict_mode_with_defaults(self):
        """Test that strict mode fails with default values."""
        with patch.dict(os.environ, {"SECURITY_MODE": "strict"}):
            import importlib
            from server import config
            importlib.reload(config)

            result = config.validate_security_on_startup(logger=None)
            assert result is False

            # Reload with defaults
            with patch.dict(os.environ, {}, clear=True):
                importlib.reload(config)

    def test_validate_passes_strict_mode_with_secure_config(self):
        """Test that strict mode passes with secure configuration."""
        secure_env = {
            "SECURITY_MODE": "strict",
            "SECRET_KEY": "a-very-secure-secret-key-that-is-long-enough-12345",
            "API_KEY": "another-very-secure-api-key-that-is-also-long-enough",
            "ALLOWED_IP_RANGE": "192.168.1.0/24",
            "CORS_ORIGINS": "http://localhost:5173",
        }

        with patch.dict(os.environ, secure_env):
            import importlib
            from server import config
            importlib.reload(config)

            result = config.validate_security_on_startup(logger=None)
            assert result is True

            # Reload with defaults
            with patch.dict(os.environ, {}, clear=True):
                importlib.reload(config)


class TestGetSecurityStatus:
    """Tests for security status reporting."""

    def test_get_security_status_returns_dict(self):
        """Test that get_security_status returns proper structure."""
        from server import config

        status = config.get_security_status()

        assert isinstance(status, dict)
        assert "is_secure" in status
        assert "warning_count" in status
        assert "error_count" in status
        assert "security_mode" in status
        assert "ip_filter_enabled" in status
        assert "cors_restricted" in status
        assert "using_default_secret" in status
        assert "using_default_api_key" in status

    def test_get_security_status_detects_defaults(self):
        """Test that status correctly detects default values."""
        from server import config

        status = config.get_security_status()

        # With default config, should detect default values
        if config.SECRET_KEY == config._DEFAULT_SECRET_KEY:
            assert status["using_default_secret"] is True

        if config.API_KEY == config._DEFAULT_API_KEY:
            assert status["using_default_api_key"] is True

    def test_get_security_status_ip_filter(self):
        """Test that status correctly reports IP filter status."""
        from server import config

        status = config.get_security_status()

        expected = bool(config.ALLOWED_IP_RANGE)
        assert status["ip_filter_enabled"] == expected

    def test_get_security_status_cors(self):
        """Test that status correctly reports CORS status."""
        from server import config

        status = config.get_security_status()

        expected = not config.CORS_ALLOW_ALL
        assert status["cors_restricted"] == expected


class TestSecurityModeConfiguration:
    """Tests for SECURITY_MODE configuration."""

    def test_default_security_mode_is_warn(self):
        """Test that default security mode is 'warn'."""
        from server import config

        # Default should be warn
        assert config.SECURITY_MODE == "warn"

    def test_security_mode_can_be_set_to_strict(self):
        """Test that security mode can be set to strict via env var."""
        with patch.dict(os.environ, {"SECURITY_MODE": "strict"}):
            import importlib
            from server import config
            importlib.reload(config)

            assert config.SECURITY_MODE == "strict"

            # Reload with defaults
            with patch.dict(os.environ, {}, clear=True):
                importlib.reload(config)


class TestDefaultValues:
    """Tests for security-related default values."""

    def test_default_secret_key_is_identifiable(self):
        """Test that default SECRET_KEY is clearly identifiable."""
        from server import config

        # Default should contain "dev" or "CHANGE" to indicate it's not for production
        default = config._DEFAULT_SECRET_KEY
        assert "dev" in default.lower() or "change" in default.lower()

    def test_default_api_key_is_identifiable(self):
        """Test that default API_KEY is clearly identifiable."""
        from server import config

        default = config._DEFAULT_API_KEY
        assert "dev" in default.lower() or "change" in default.lower()

    def test_default_admin_password_is_identifiable(self):
        """Test that default admin password is simple/identifiable."""
        from server import config

        # Default admin password should be simple enough to recognize
        default = config._DEFAULT_ADMIN_PASSWORD
        assert default == "admin123"
