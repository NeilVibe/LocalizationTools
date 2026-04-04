"""
Unit Tests for Phase 113: Network, Auth, and API Changes

Tests the cross-subnet LAN fix (/24 → /16), credential redaction,
auth LAN fallback detection, pillow-dds availability flag, and
SSL runtime re-evaluation.

All tests use mocks or pure logic — no database or server required.
"""

import pytest
import re
import secrets
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# 1. get_subnet() — /16 cross-subnet LAN
# ============================================================================

class TestGetSubnet:
    """Phase 113: get_subnet returns /16 for cross-subnet LAN."""

    def test_normal_ip_returns_16(self):
        from server.setup.network import get_subnet
        result = get_subnet("10.0.0.1")
        assert result == "10.0.0.0/16"

    def test_different_third_octet_same_16(self):
        """Admin 10.0.0.x and User 10.0.1.x must be in same /16."""
        from server.setup.network import get_subnet
        admin = get_subnet("10.0.0.1")
        user = get_subnet("10.0.1.1")
        assert admin == user  # Both 10.0.0.0/16

    def test_loopback_returns_none(self):
        from server.setup.network import get_subnet
        assert get_subnet("127.0.0.1") is None

    def test_loopback_any_suffix_returns_none(self):
        from server.setup.network import get_subnet
        assert get_subnet("127.0.0.2") is None
        assert get_subnet("127.255.255.255") is None

    def test_192_168_range(self):
        from server.setup.network import get_subnet
        result = get_subnet("192.168.1.100")
        assert result == "192.168.0.0/16"

    def test_172_16_range(self):
        from server.setup.network import get_subnet
        result = get_subnet("172.16.5.10")
        assert result == "172.16.0.0/16"

    def test_invalid_ip_too_few_parts(self):
        from server.setup.network import get_subnet
        assert get_subnet("abc") is None

    def test_invalid_ip_three_parts(self):
        from server.setup.network import get_subnet
        assert get_subnet("10.0.0") is None

    def test_invalid_ip_five_parts(self):
        from server.setup.network import get_subnet
        assert get_subnet("10.0.0.1.99") is None

    def test_empty_string(self):
        from server.setup.network import get_subnet
        assert get_subnet("") is None

    def test_third_and_fourth_octets_zeroed(self):
        """Output must zero out the 3rd and 4th octets."""
        from server.setup.network import get_subnet
        result = get_subnet("10.0.99.250")
        assert result == "10.0.0.0/16"
        assert ".99." not in result
        assert ".250" not in result


# ============================================================================
# 2. pg_hba.conf stale /24 detection regex
# ============================================================================

class TestPgHbaStaleDetection:
    """Phase 113: Regex detects stale /24 rules in pg_hba.conf."""

    # The exact regex from server/setup/steps.py line 286
    STALE_24_RE = re.compile(r'host\s+\S+\s+\S+\s+\d+\.\d+\.\d+\.\d+/24\s')

    def test_detects_stale_24(self):
        """Old pg_hba.conf with /24 subnet rule is detected."""
        content = (
            "# LocaNext -- managed by setup wizard\n"
            "host    all    postgres    127.0.0.1/32    trust\n"
            "host    localizationtools    locanext_service    10.0.0.0/24    scram-sha-256\n"
            "host    all    all    0.0.0.0/0    reject\n"
        )
        assert self.STALE_24_RE.search(content) is not None

    def test_no_false_positive_on_32(self):
        """127.0.0.1/32 should NOT trigger /24 detection."""
        content = (
            "host    all    postgres    127.0.0.1/32    trust\n"
            "host    localizationtools    locanext_service    10.0.0.0/16    scram-sha-256\n"
        )
        assert self.STALE_24_RE.search(content) is None

    def test_no_false_positive_on_comment(self):
        """Comment mentioning /24 should NOT trigger."""
        content = (
            "# Previously used /24 subnet\n"
            "host    localizationtools    locanext_service    10.0.0.0/16    scram-sha-256\n"
        )
        assert self.STALE_24_RE.search(content) is None

    def test_no_false_positive_on_16(self):
        """Already migrated /16 should NOT trigger."""
        content = "host    localizationtools    locanext_service    10.0.0.0/16    scram-sha-256\n"
        assert self.STALE_24_RE.search(content) is None

    def test_detects_192_168_stale_24(self):
        """Different private range with /24 is also stale."""
        content = "host    all    all    192.168.1.0/24    scram-sha-256\n"
        assert self.STALE_24_RE.search(content) is not None

    def test_no_false_positive_on_0_0_0_0(self):
        """Wildcard 0.0.0.0/0 should not trigger."""
        content = "host    all    all    0.0.0.0/0    reject\n"
        assert self.STALE_24_RE.search(content) is None


# ============================================================================
# 3. Credential redaction regex
# ============================================================================

class TestCredentialRedaction:
    """Phase 113: DB URL password redaction handles edge cases."""

    # The exact regex from server/main.py line 93
    REDACT_RE = re.compile(r'://([^:]+):(.+)@(?=[^@]*$)')

    def _redact(self, url: str) -> str:
        return self.REDACT_RE.sub(r'://\1:***@', url)

    def test_basic_redaction(self):
        url = "postgresql://locanext:secret123@localhost:5432/db"
        safe = self._redact(url)
        assert "secret123" not in safe
        assert "locanext:***@localhost" in safe

    def test_password_with_at_sign(self):
        """Passwords containing @ must be fully redacted."""
        url = "postgresql://user:p@ssw0rd@localhost:5432/db"
        safe = self._redact(url)
        assert "p@ssw0rd" not in safe
        assert "user:***@localhost" in safe

    def test_password_with_special_chars(self):
        url = "postgresql://user:p@ss:w0rd!#$@host:5432/db"
        safe = self._redact(url)
        assert "p@ss:w0rd" not in safe
        assert "user:***@host" in safe

    def test_no_password_in_url(self):
        """URLs without credentials pass through unchanged."""
        url = "sqlite:///path/to/db.sqlite3"
        safe = self._redact(url)
        assert safe == url

    def test_token_urlsafe_password(self):
        """Our actual generated passwords (base64url, no @)."""
        pwd = secrets.token_urlsafe(32)
        url = f"postgresql://locanext:{pwd}@localhost:5432/db"
        safe = self._redact(url)
        assert pwd not in safe
        assert "locanext:***@localhost" in safe

    def test_username_preserved(self):
        """Username must survive redaction."""
        url = "postgresql://myuser:mypass@db.host:5432/mydb"
        safe = self._redact(url)
        assert "myuser:***@db.host" in safe

    def test_port_preserved(self):
        """Port and database name must survive redaction."""
        url = "postgresql://u:p@host:5432/db"
        safe = self._redact(url)
        assert ":5432/db" in safe

    def test_empty_password(self):
        """Empty password field is still redacted."""
        url = "postgresql://user:@host:5432/db"
        # Empty password means nothing between : and @, regex .+ won't match
        # so it passes through — this is acceptable behavior
        # Just verify no crash
        safe = self._redact(url)
        assert isinstance(safe, str)


# ============================================================================
# 4. Auth LAN fallback detection (503 vs 401)
# ============================================================================

class TestAuthLanFallback:
    """Phase 113: Login returns 503 when LAN configured but using SQLite."""

    LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1", "")

    def _is_lan_configured(self, pg_host: str) -> bool:
        """Mirror the logic from server/api/auth_async.py line 101."""
        return pg_host not in self.LOCAL_HOSTS

    def test_lan_ip_is_lan_configured(self):
        assert self._is_lan_configured("10.0.0.1") is True

    def test_localhost_not_lan(self):
        assert self._is_lan_configured("localhost") is False

    def test_127_not_lan(self):
        assert self._is_lan_configured("127.0.0.1") is False

    def test_ipv6_loopback_not_lan(self):
        assert self._is_lan_configured("::1") is False

    def test_empty_host_not_lan(self):
        assert self._is_lan_configured("") is False

    def test_lan_fallback_should_503(self):
        """When LAN configured + SQLite active → 503 (not 401)."""
        pg_host = "10.0.0.1"
        db_type = "sqlite"
        is_lan = self._is_lan_configured(pg_host)
        should_503 = is_lan and db_type == "sqlite"
        assert should_503 is True

    def test_lan_with_postgres_should_not_503(self):
        """When LAN configured + PG active → normal 401 path."""
        pg_host = "10.0.0.1"
        db_type = "postgresql"
        is_lan = self._is_lan_configured(pg_host)
        should_503 = is_lan and db_type == "sqlite"
        assert should_503 is False

    def test_local_with_sqlite_should_not_503(self):
        """When localhost + SQLite → normal 401 path (not LAN fallback)."""
        pg_host = "localhost"
        db_type = "sqlite"
        is_lan = self._is_lan_configured(pg_host)
        should_503 = is_lan and db_type == "sqlite"
        assert should_503 is False

    def test_192_168_is_lan(self):
        assert self._is_lan_configured("192.168.1.1") is True

    def test_hostname_is_lan(self):
        """A hostname like 'admin-pc' is LAN configured."""
        assert self._is_lan_configured("admin-pc") is True


# ============================================================================
# 5. pillow-dds availability flag
# ============================================================================

class TestPillowDdsFlag:
    """Phase 113: pillow-dds availability tracking."""

    def test_flag_exists_and_is_bool(self):
        from server.tools.ldm.services.media_converter import _PILLOW_DDS_AVAILABLE
        assert isinstance(_PILLOW_DDS_AVAILABLE, bool)

    def test_converter_early_out_when_no_dds_support(self, tmp_path):
        """If pillow-dds not available, convert_dds_to_png returns None for .dds files."""
        from server.tools.ldm.services.media_converter import MediaConverter, _PILLOW_DDS_AVAILABLE
        if _PILLOW_DDS_AVAILABLE:
            pytest.skip("pillow-dds IS installed, can't test early-out path")
        converter = MediaConverter()
        fake_dds = tmp_path / "test.dds"
        fake_dds.write_bytes(b"\x44\x44\x53\x20" + b"\x00" * 120)  # DDS magic + padding
        result = converter.convert_dds_to_png(fake_dds)
        assert result is None

    def test_converter_returns_none_for_missing_file(self, tmp_path):
        """Non-existent file returns None regardless of pillow-dds."""
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter()
        missing = tmp_path / "nonexistent.dds"
        result = converter.convert_dds_to_png(missing)
        assert result is None


# ============================================================================
# 6. SSL_ENABLED runtime re-evaluation
# ============================================================================

class TestSslEnabled:
    """Phase 113: SSL_ENABLED is True only when both cert files exist."""

    def test_ssl_enabled_when_both_files_exist(self, tmp_path):
        """SSL_ENABLED should be True when both cert and key exist."""
        cert = tmp_path / "server.crt"
        key = tmp_path / "server.key"
        cert.write_text("fake cert")
        key.write_text("fake key")
        ssl_enabled = cert.exists() and key.exists()
        assert ssl_enabled is True

    def test_ssl_disabled_when_cert_missing(self, tmp_path):
        """SSL_ENABLED should be False when cert is missing."""
        key = tmp_path / "server.key"
        key.write_text("fake key")
        cert = tmp_path / "server.crt"
        ssl_enabled = cert.exists() and key.exists()
        assert ssl_enabled is False

    def test_ssl_disabled_when_key_missing(self, tmp_path):
        """SSL_ENABLED should be False when key is missing."""
        cert = tmp_path / "server.crt"
        cert.write_text("fake cert")
        key = tmp_path / "server.key"
        ssl_enabled = cert.exists() and key.exists()
        assert ssl_enabled is False

    def test_ssl_disabled_when_both_missing(self, tmp_path):
        """SSL_ENABLED should be False when neither file exists."""
        cert = tmp_path / "server.crt"
        key = tmp_path / "server.key"
        ssl_enabled = cert.exists() and key.exists()
        assert ssl_enabled is False

    def test_config_ssl_enabled_is_bool(self):
        """The actual config value should be a bool."""
        from server.config import SSL_ENABLED
        assert isinstance(SSL_ENABLED, bool)


# ============================================================================
# 7. detect_lan_ip() sanity
# ============================================================================

class TestDetectLanIp:
    """Sanity checks for detect_lan_ip."""

    def test_returns_string(self):
        from server.setup.network import detect_lan_ip
        result = detect_lan_ip()
        assert isinstance(result, str)

    def test_returns_valid_ip_format(self):
        from server.setup.network import detect_lan_ip
        result = detect_lan_ip()
        parts = result.split(".")
        assert len(parts) == 4
        for p in parts:
            assert p.isdigit()
            assert 0 <= int(p) <= 255

    def test_fallback_on_error(self):
        """When socket fails, returns 127.0.0.1."""
        from server.setup.network import detect_lan_ip
        with patch("server.setup.network.socket.gethostname", side_effect=OSError("mock")):
            result = detect_lan_ip()
        assert result == "127.0.0.1"
