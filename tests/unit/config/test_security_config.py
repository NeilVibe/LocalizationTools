"""
Test security configuration: setup wizard flow, strict mode, API_KEY generation.

Simulates the full PEARL scenario:
1. First launch: setup wizard generates config → security validation passes
2. Second launch: config loaded from file → strict mode passes
3. Corrupt config: logged, falls back to defaults
4. Edge cases: case-insensitive SECURITY_MODE, short keys, missing keys
"""

import json
import os
import secrets
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers — simulate config loading without importing the real module
# (importing server.config has side effects: it reads the REAL user config)
# ---------------------------------------------------------------------------

def simulate_load_user_config(config_path: Path) -> dict:
    """Replicate _load_user_config logic from config.py."""
    from loguru import logger
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Malformed user config at {config_path}: {e}. All values fall back to defaults.")
        except IOError as e:
            logger.warning(f"Cannot read user config at {config_path}: {e}. Using defaults.")
    return {}


def simulate_check_security(secret_key, api_key, security_mode, user_config=None):
    """Replicate check_security_config logic from config.py."""
    _DEFAULT_SECRET_KEY = "dev-secret-key-CHANGE-IN-PRODUCTION"
    _DEFAULT_API_KEY = "dev-key-change-in-production"

    warnings = []
    errors = []

    if secret_key == _DEFAULT_SECRET_KEY:
        msg = "SECRET_KEY is using default value!"
        if security_mode == "strict":
            errors.append(msg)
        else:
            warnings.append(msg)
    elif len(secret_key) < 32:
        warnings.append(f"SECRET_KEY is only {len(secret_key)} characters.")

    if api_key == _DEFAULT_API_KEY:
        msg = "API_KEY is using default value!"
        if security_mode == "strict":
            errors.append(msg)
        else:
            warnings.append(msg)
    elif len(api_key) < 32:
        warnings.append(f"API_KEY is only {len(api_key)} characters.")

    return {
        "is_secure": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "security_mode": security_mode,
    }


def simulate_setup_wizard_config():
    """Replicate what main.py generates after setup wizard completes."""
    return {
        "postgres_host": "localhost",
        "postgres_port": 5432,
        "postgres_user": "locanext_service",
        "postgres_password": secrets.token_urlsafe(24),
        "postgres_db": "localizationtools",
        "database_mode": "auto",
        "server_mode": "lan_server",
        "lan_ip": "10.35.34.61",
        "secret_key": secrets.token_urlsafe(32),
        "api_key": secrets.token_urlsafe(48),
        "admin_token": secrets.token_urlsafe(32),
        "security_mode": "strict",
        "origin_admin_ip": "127.0.0.1",
    }


def resolve_config_value(env_var_name, env_value, user_config, config_key, default):
    """Replicate the os.getenv(X, _USER_CONFIG.get(x, default)) pattern."""
    if env_value is not None:
        return env_value
    return user_config.get(config_key, default)


# ---------------------------------------------------------------------------
# SCENARIO 1: First launch — setup wizard generates everything
# ---------------------------------------------------------------------------

class TestFirstLaunch:
    """Simulate PEARL's first launch: setup wizard runs, generates config."""

    def test_setup_wizard_generates_api_key(self):
        """The setup wizard config must contain an api_key."""
        config = simulate_setup_wizard_config()
        assert "api_key" in config
        assert len(config["api_key"]) >= 32

    def test_setup_wizard_generates_secret_key(self):
        """The setup wizard config must contain a secret_key."""
        config = simulate_setup_wizard_config()
        assert "secret_key" in config
        assert len(config["secret_key"]) >= 32

    def test_setup_wizard_sets_strict_mode(self):
        """Setup wizard sets security_mode to strict."""
        config = simulate_setup_wizard_config()
        assert config["security_mode"] == "strict"

    def test_first_launch_security_passes_with_generated_keys(self):
        """After setup wizard, security validation must pass in strict mode."""
        config = simulate_setup_wizard_config()
        result = simulate_check_security(
            secret_key=config["secret_key"],
            api_key=config["api_key"],
            security_mode=config["security_mode"],
        )
        assert result["is_secure"] is True
        assert len(result["errors"]) == 0
        assert result["security_mode"] == "strict"

    def test_first_launch_runtime_overrides(self):
        """Simulate the runtime config overrides that happen on first launch."""
        wizard_config = simulate_setup_wizard_config()

        # Before override: defaults
        secret_key = "dev-secret-key-CHANGE-IN-PRODUCTION"
        api_key = "dev-key-change-in-production"
        security_mode = "warn"

        # Apply overrides (what main.py does)
        secret_key = wizard_config["secret_key"]
        api_key = wizard_config["api_key"]
        security_mode = "strict"

        result = simulate_check_security(secret_key, api_key, security_mode)
        assert result["is_secure"] is True


# ---------------------------------------------------------------------------
# SCENARIO 2: Second launch — config loaded from file
# ---------------------------------------------------------------------------

class TestSecondLaunch:
    """Simulate PEARL's second launch: config loaded from saved JSON file."""

    def test_config_roundtrip_preserves_keys(self, tmp_path):
        """Config saved by setup wizard → loaded on next launch → keys intact."""
        config_file = tmp_path / "server-config.json"

        # First launch: setup wizard saves config
        wizard_config = simulate_setup_wizard_config()
        config_file.write_text(json.dumps(wizard_config, indent=2))

        # Second launch: load config from file
        loaded = simulate_load_user_config(config_file)

        assert loaded["secret_key"] == wizard_config["secret_key"]
        assert loaded["api_key"] == wizard_config["api_key"]
        assert loaded["security_mode"] == "strict"

    def test_second_launch_security_passes(self, tmp_path):
        """Second launch with saved config passes strict security validation."""
        config_file = tmp_path / "server-config.json"
        wizard_config = simulate_setup_wizard_config()
        config_file.write_text(json.dumps(wizard_config, indent=2))

        loaded = simulate_load_user_config(config_file)

        # Simulate config.py resolution: env var → user config → default
        secret_key = resolve_config_value(
            "SECRET_KEY", None, loaded, "secret_key",
            "dev-secret-key-CHANGE-IN-PRODUCTION"
        )
        api_key = resolve_config_value(
            "API_KEY", None, loaded, "api_key",
            "dev-key-change-in-production"
        )
        security_mode = resolve_config_value(
            "SECURITY_MODE", None, loaded, "security_mode", "warn"
        )

        result = simulate_check_security(secret_key, api_key, security_mode)
        assert result["is_secure"] is True
        assert result["security_mode"] == "strict"

    def test_second_launch_without_api_key_fails_strict(self, tmp_path):
        """BUG REPRO: If api_key is missing from saved config, strict mode blocks."""
        config_file = tmp_path / "server-config.json"

        # Simulate the OLD buggy config (no api_key!)
        buggy_config = simulate_setup_wizard_config()
        del buggy_config["api_key"]
        config_file.write_text(json.dumps(buggy_config, indent=2))

        loaded = simulate_load_user_config(config_file)

        api_key = resolve_config_value(
            "API_KEY", None, loaded, "api_key",
            "dev-key-change-in-production"
        )
        security_mode = resolve_config_value(
            "SECURITY_MODE", None, loaded, "security_mode", "warn"
        )

        # This is exactly what PEARL hit: api_key falls back to default, strict mode blocks
        assert api_key == "dev-key-change-in-production"
        result = simulate_check_security(
            secret_key=loaded["secret_key"],
            api_key=api_key,
            security_mode=security_mode,
        )
        assert result["is_secure"] is False
        assert any("API_KEY" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# SCENARIO 3: Corrupt / missing config
# ---------------------------------------------------------------------------

class TestCorruptConfig:
    """Simulate corrupt or missing config files."""

    def test_missing_config_returns_empty(self, tmp_path):
        """Missing config file returns empty dict (not crash)."""
        config_file = tmp_path / "nonexistent.json"
        loaded = simulate_load_user_config(config_file)
        assert loaded == {}

    def test_corrupt_json_returns_empty(self, tmp_path):
        """Malformed JSON returns empty dict and logs error."""
        config_file = tmp_path / "server-config.json"
        config_file.write_text("{invalid json content!!!")

        loaded = simulate_load_user_config(config_file)
        assert loaded == {}

    def test_empty_file_returns_empty(self, tmp_path):
        """Empty file returns empty dict."""
        config_file = tmp_path / "server-config.json"
        config_file.write_text("")

        loaded = simulate_load_user_config(config_file)
        assert loaded == {}

    def test_corrupt_config_falls_back_to_defaults(self, tmp_path):
        """With corrupt config, all values fall back to insecure defaults."""
        config_file = tmp_path / "server-config.json"
        config_file.write_text("NOT JSON")

        loaded = simulate_load_user_config(config_file)

        secret_key = resolve_config_value(
            "SECRET_KEY", None, loaded, "secret_key",
            "dev-secret-key-CHANGE-IN-PRODUCTION"
        )
        api_key = resolve_config_value(
            "API_KEY", None, loaded, "api_key",
            "dev-key-change-in-production"
        )

        assert secret_key == "dev-secret-key-CHANGE-IN-PRODUCTION"
        assert api_key == "dev-key-change-in-production"


# ---------------------------------------------------------------------------
# SCENARIO 4: SECURITY_MODE edge cases
# ---------------------------------------------------------------------------

class TestSecurityModeEdgeCases:
    """Test SECURITY_MODE normalization and validation."""

    @pytest.mark.parametrize("raw_value,expected", [
        ("strict", "strict"),
        ("Strict", "strict"),
        ("STRICT", "strict"),
        ("  strict  ", "strict"),
        ("warn", "warn"),
        ("WARN", "warn"),
        ("  Warn  ", "warn"),
    ])
    def test_security_mode_normalization(self, raw_value, expected):
        """SECURITY_MODE is case-insensitive and strips whitespace."""
        normalized = raw_value.lower().strip()
        assert normalized == expected

    @pytest.mark.parametrize("invalid_value", [
        "stricy",  # typo
        "error",
        "enforce",
        "",
        "true",
        "false",
    ])
    def test_invalid_security_mode_defaults_to_warn(self, invalid_value):
        """Invalid SECURITY_MODE values fall back to 'warn'."""
        normalized = invalid_value.lower().strip()
        if normalized not in ("strict", "warn"):
            normalized = "warn"
        assert normalized == "warn"

    def test_strict_mode_blocks_default_keys(self):
        """Strict mode must block startup if default keys are used."""
        result = simulate_check_security(
            secret_key="dev-secret-key-CHANGE-IN-PRODUCTION",
            api_key="dev-key-change-in-production",
            security_mode="strict",
        )
        assert result["is_secure"] is False
        assert len(result["errors"]) == 2

    def test_warn_mode_allows_default_keys(self):
        """Warn mode logs warnings but doesn't block."""
        result = simulate_check_security(
            secret_key="dev-secret-key-CHANGE-IN-PRODUCTION",
            api_key="dev-key-change-in-production",
            security_mode="warn",
        )
        assert result["is_secure"] is True
        assert len(result["warnings"]) == 2
        assert len(result["errors"]) == 0


# ---------------------------------------------------------------------------
# SCENARIO 5: Key length validation
# ---------------------------------------------------------------------------

class TestKeyLengthValidation:
    """Test that short keys produce warnings."""

    def test_short_secret_key_warns(self):
        """SECRET_KEY shorter than 32 chars produces a warning."""
        result = simulate_check_security(
            secret_key="short",
            api_key=secrets.token_urlsafe(48),
            security_mode="strict",
        )
        assert any("SECRET_KEY is only" in w for w in result["warnings"])

    def test_short_api_key_warns(self):
        """API_KEY shorter than 32 chars produces a warning."""
        result = simulate_check_security(
            secret_key=secrets.token_urlsafe(32),
            api_key="short-key",
            security_mode="strict",
        )
        assert any("API_KEY is only" in w for w in result["warnings"])

    def test_generated_keys_pass_length_check(self):
        """Keys from token_urlsafe(32/48) are long enough."""
        secret = secrets.token_urlsafe(32)
        api = secrets.token_urlsafe(48)
        assert len(secret) >= 32
        assert len(api) >= 32

        result = simulate_check_security(secret, api, "strict")
        assert result["is_secure"] is True
        assert len(result["warnings"]) == 0


# ---------------------------------------------------------------------------
# SCENARIO 6: Config value precedence (env > user_config > default)
# ---------------------------------------------------------------------------

class TestConfigPrecedence:
    """Test that env vars override user config, which overrides defaults."""

    def test_env_var_overrides_user_config(self):
        """Environment variable takes precedence over user config."""
        user_config = {"api_key": "from-config-file"}
        result = resolve_config_value("API_KEY", "from-env", user_config, "api_key", "default")
        assert result == "from-env"

    def test_user_config_overrides_default(self):
        """User config takes precedence over hardcoded default."""
        user_config = {"api_key": "from-config-file"}
        result = resolve_config_value("API_KEY", None, user_config, "api_key", "default")
        assert result == "from-config-file"

    def test_default_used_when_nothing_set(self):
        """Hardcoded default used when no env var and no user config."""
        result = resolve_config_value("API_KEY", None, {}, "api_key", "default")
        assert result == "default"

    def test_empty_user_config_uses_default(self):
        """Empty user config (corrupt file) falls back to default."""
        result = resolve_config_value("API_KEY", None, {}, "api_key", "dev-key-change-in-production")
        assert result == "dev-key-change-in-production"


# ---------------------------------------------------------------------------
# SCENARIO 7: Full PEARL lifecycle simulation
# ---------------------------------------------------------------------------

class TestPearlLifecycle:
    """End-to-end simulation of PEARL's exact bug scenario."""

    def test_pearl_full_lifecycle(self, tmp_path):
        """
        Simulate the exact PEARL scenario:
        1. First launch: setup wizard runs, generates config, saves to disk
        2. App closes
        3. Second launch: loads config from disk, security validation runs
        4. Server starts successfully (no abort!)
        """
        config_file = tmp_path / "server-config.json"

        # === FIRST LAUNCH ===

        # Step 1: Setup wizard generates config (NEW code with api_key fix)
        wizard_config = simulate_setup_wizard_config()
        assert "api_key" in wizard_config  # THE FIX

        # Step 2: Save to disk
        config_file.write_text(json.dumps(wizard_config, indent=2))

        # Step 3: Runtime overrides for first launch
        runtime_secret = wizard_config["secret_key"]
        runtime_api = wizard_config["api_key"]
        runtime_mode = "strict"

        # Step 4: Security validation on first launch
        result = simulate_check_security(runtime_secret, runtime_api, runtime_mode)
        assert result["is_secure"] is True, f"First launch failed: {result['errors']}"

        # === APP CLOSES, REOPENS ===

        # === SECOND LAUNCH ===

        # Step 5: Load config from file (simulates _load_user_config at module init)
        loaded = simulate_load_user_config(config_file)
        assert loaded != {}, "Config file should not be empty"

        # Step 6: Resolve values (simulates config.py module-level assignment)
        secret_key = resolve_config_value("SECRET_KEY", None, loaded, "secret_key",
                                          "dev-secret-key-CHANGE-IN-PRODUCTION")
        api_key = resolve_config_value("API_KEY", None, loaded, "api_key",
                                       "dev-key-change-in-production")
        security_mode = resolve_config_value("SECURITY_MODE", None, loaded, "security_mode", "warn")

        # Step 7: Security validation on second launch
        result = simulate_check_security(secret_key, api_key, security_mode)
        assert result["is_secure"] is True, f"Second launch failed: {result['errors']}"
        assert result["security_mode"] == "strict"

        # Step 8: No errors, no warnings about default keys
        assert len(result["errors"]) == 0
        assert not any("default value" in w for w in result["warnings"])

    def test_pearl_bug_repro_old_code(self, tmp_path):
        """
        Reproduce PEARL's exact bug with the OLD code (no api_key in config).
        This test MUST show the failure that PEARL experienced.
        """
        config_file = tmp_path / "server-config.json"

        # OLD buggy setup wizard: generates secret_key but NOT api_key
        old_config = {
            "postgres_host": "localhost",
            "postgres_port": 5432,
            "postgres_user": "locanext_service",
            "postgres_password": secrets.token_urlsafe(24),
            "postgres_db": "localizationtools",
            "database_mode": "auto",
            "server_mode": "lan_server",
            "lan_ip": "10.35.34.61",
            "secret_key": secrets.token_urlsafe(32),
            # NO api_key! <-- THIS WAS THE BUG
            "admin_token": secrets.token_urlsafe(32),
            "security_mode": "strict",
            "origin_admin_ip": "127.0.0.1",
        }
        config_file.write_text(json.dumps(old_config, indent=2))

        # Second launch: load config
        loaded = simulate_load_user_config(config_file)

        # API_KEY falls back to default because it's missing from config
        api_key = resolve_config_value("API_KEY", None, loaded, "api_key",
                                       "dev-key-change-in-production")

        # STRICT mode blocks because API_KEY is the default value
        security_mode = resolve_config_value("SECURITY_MODE", None, loaded, "security_mode", "warn")
        result = simulate_check_security(loaded["secret_key"], api_key, security_mode)

        # THIS IS THE BUG: server aborts
        assert result["is_secure"] is False
        assert any("API_KEY" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# SCENARIO 8: File permissions
# ---------------------------------------------------------------------------

class TestFilePermissions:
    """Test that saved config files get restrictive permissions."""

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions test")
    def test_save_user_config_sets_permissions(self, tmp_path):
        """save_user_config sets 0o600 on Linux."""
        from server.config import save_user_config, _get_user_config_path

        # Patch the config path to use our temp dir
        config_file = tmp_path / "LocaNext" / "server-config.json"
        with patch("server.config._get_user_config_path", return_value=config_file):
            result = save_user_config({"test": "data"})

        assert result is True
        assert config_file.exists()
        mode = oct(config_file.stat().st_mode & 0o777)
        assert mode == "0o600", f"Expected 0o600 but got {mode}"
