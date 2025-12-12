"""
Server Configuration

This module contains all configuration settings for the LocalizationTools central server.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Load environment variables from .env file (if exists)
# override=True ensures .env values take precedence over system env vars
try:
    from dotenv import load_dotenv
    # Load from project root .env file
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
except ImportError:
    pass  # python-dotenv not installed, use system env vars only

# Add parent directory to path for version import
sys.path.insert(0, str(Path(__file__).parent.parent))
from version import VERSION, SEMANTIC_VERSION, VERSION_FOOTER

# ============================================
# Application Info
# ============================================

APP_NAME = "LocalizationTools Server"
APP_VERSION = SEMANTIC_VERSION  # Uses semantic version (e.g., "1.0.0")
VERSION = VERSION  # DateTime version (e.g., "2511221939")
API_VERSION = "v1"
APP_DESCRIPTION = "Central logging and analytics server for LocalizationTools"

# ============================================
# Paths
# ============================================

# Base directory
BASE_DIR = Path(__file__).parent.absolute()
ROOT_DIR = BASE_DIR.parent

# Data directory
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Logs directory
LOGS_DIR = DATA_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# Server Settings
# ============================================

# Host and port
# Default to 127.0.0.1 (localhost) to avoid Windows firewall popup
# For network access, set SERVER_HOST=0.0.0.0 in environment
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8888"))

# Admin dashboard
ADMIN_DASHBOARD_PORT = int(os.getenv("ADMIN_DASHBOARD_PORT", "8885"))

# ============================================
# Central Server Settings (Telemetry)
# ============================================

# Central Server URL for telemetry/remote logging
# Desktop apps send logs to this server
# Example: CENTRAL_SERVER_URL=http://192.168.11.100:9999
CENTRAL_SERVER_URL = os.getenv("CENTRAL_SERVER_URL", "")

# Enable telemetry sending (Desktop app setting)
TELEMETRY_ENABLED = os.getenv("TELEMETRY_ENABLED", "true").lower() == "true"

# Telemetry heartbeat interval in seconds
TELEMETRY_HEARTBEAT_INTERVAL = int(os.getenv("TELEMETRY_HEARTBEAT_INTERVAL", "300"))  # 5 min

# Offline queue: retry sending logs when central unavailable
TELEMETRY_RETRY_INTERVAL = int(os.getenv("TELEMETRY_RETRY_INTERVAL", "60"))  # 1 min
TELEMETRY_MAX_QUEUE_SIZE = int(os.getenv("TELEMETRY_MAX_QUEUE_SIZE", "1000"))  # max logs to queue

# CORS settings
# In development: allow all origins ("*")
# In production: set CORS_ORIGINS env var to whitelist specific origins
# Example: CORS_ORIGINS=http://192.168.11.100:5173,http://192.168.11.100:5175
_cors_origins_env = os.getenv("CORS_ORIGINS", "")

if _cors_origins_env:
    # Production: use explicit whitelist
    CORS_ORIGINS = [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
    CORS_ALLOW_ALL = False
else:
    # Development: allow common localhost origins
    CORS_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:7860",
        "http://127.0.0.1:7860",
        "http://localhost:8885",
        "http://127.0.0.1:8885",
    ]
    CORS_ALLOW_ALL = True  # Allow all in development for convenience

# Add production origins if specified (legacy support)
PRODUCTION_ORIGIN = os.getenv("PRODUCTION_ORIGIN")
if PRODUCTION_ORIGIN:
    CORS_ORIGINS.append(PRODUCTION_ORIGIN)
    CORS_ALLOW_ALL = False

# Additional CORS settings from environment
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
CORS_ALLOW_METHODS = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
CORS_ALLOW_HEADERS = os.getenv("CORS_ALLOW_HEADERS", "Content-Type,Authorization,X-Request-ID").split(",")

# Backward compatibility alias
ALLOWED_ORIGINS = CORS_ORIGINS

# ============================================
# Database Settings
# ============================================

# Database type - PostgreSQL is REQUIRED (no SQLite)
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "postgresql")

# PostgreSQL settings (same for dev and production)
POSTGRES_USER = os.getenv("POSTGRES_USER", "localization_admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "change_this_password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "localizationtools")
POSTGRES_DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Current database URL (PostgreSQL only)
DATABASE_URL = POSTGRES_DATABASE_URL

# Database pool settings
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# Query settings
DB_ECHO = os.getenv("DB_ECHO", "False").lower() == "true"  # Log all SQL queries

# ============================================
# Security Settings
# ============================================

# IP Range Filtering (Internal Enterprise Security)
# Set ALLOWED_IP_RANGE to restrict access to specific IP ranges
# Example: ALLOWED_IP_RANGE=192.168.11.0/24
# Example: ALLOWED_IP_RANGE=192.168.11.0/24,192.168.12.0/24,10.0.0.0/8
# If not set, all IPs are allowed (development mode)
ALLOWED_IP_RANGE = os.getenv("ALLOWED_IP_RANGE", "")
IP_FILTER_ALLOW_LOCALHOST = os.getenv("IP_FILTER_ALLOW_LOCALHOST", "true").lower() == "true"
IP_FILTER_LOG_BLOCKED = os.getenv("IP_FILTER_LOG_BLOCKED", "true").lower() == "true"

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-CHANGE-IN-PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# Default/insecure values (used for validation)
_DEFAULT_SECRET_KEY = "dev-secret-key-CHANGE-IN-PRODUCTION"
_DEFAULT_API_KEY = "dev-key-change-in-production"
_DEFAULT_ADMIN_PASSWORD = "admin123"

# Security mode: "strict" will fail on insecure defaults, "warn" will only log warnings
SECURITY_MODE = os.getenv("SECURITY_MODE", "warn")  # "strict" or "warn"

# DEV_MODE: Enables localhost-only auto-authentication for autonomous testing
# SECURITY: Only works when request comes from localhost (127.0.0.1 or ::1)
# Set DEV_MODE=true to enable. NEVER enable in production builds.
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
PRODUCTION = os.getenv("PRODUCTION", "false").lower() == "true"

# DEV_MODE is blocked if PRODUCTION is set
if DEV_MODE and PRODUCTION:
    import warnings
    warnings.warn("DEV_MODE disabled: Cannot use DEV_MODE with PRODUCTION=true")
    DEV_MODE = False

# API Key for client-server communication
API_KEY = os.getenv("API_KEY", "dev-key-change-in-production")

# Password hashing
BCRYPT_ROUNDS = 12  # Higher = more secure but slower

# Rate limiting
RATE_LIMIT_ENABLED = True
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

# ============================================
# Logging Settings
# ============================================

# Log file
LOG_FILE = LOGS_DIR / "server.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
LOG_ROTATION = "50 MB"
LOG_RETENTION = "3 months"

# Access logs
ENABLE_ACCESS_LOGS = True
ACCESS_LOG_FILE = LOGS_DIR / "access.log"

# Error logs
ERROR_LOG_FILE = LOGS_DIR / "error.log"

# ============================================
# Analytics Settings
# ============================================

# Statistics aggregation
AGGREGATE_STATS_DAILY = True
AGGREGATION_SCHEDULE = "0 2 * * *"  # Run at 2 AM daily (cron format)

# Data retention
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "90"))  # 3 months
SESSION_RETENTION_DAYS = int(os.getenv("SESSION_RETENTION_DAYS", "30"))
ERROR_LOG_RETENTION_DAYS = int(os.getenv("ERROR_LOG_RETENTION_DAYS", "180"))  # 6 months

# Performance metrics
COLLECT_PERFORMANCE_METRICS = True
PERFORMANCE_METRICS_SAMPLE_RATE = 1.0  # 100% sampling

# ============================================
# Update System
# ============================================

# Update file storage
UPDATES_DIR = DATA_DIR / "updates"
UPDATES_DIR.mkdir(parents=True, exist_ok=True)

# Update settings
UPDATE_CHECK_ENABLED = True
UPDATE_DOWNLOAD_URL_BASE = os.getenv(
    "UPDATE_DOWNLOAD_URL_BASE", "https://your-server.com/downloads"
)

# ============================================
# Notifications Settings
# ============================================

# Announcements
ANNOUNCEMENTS_ENABLED = True
MAX_ACTIVE_ANNOUNCEMENTS = 5

# Email notifications (future feature)
ENABLE_EMAIL_NOTIFICATIONS = False
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# ============================================
# Admin Settings
# ============================================

# Default admin user
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@company.com"
DEFAULT_ADMIN_PASSWORD = "admin123"  # CHANGE THIS!

# Admin dashboard
ADMIN_DASHBOARD_ENABLED = True
ADMIN_DASHBOARD_REFRESH_INTERVAL = 30  # seconds

# ============================================
# API Settings
# ============================================

# API documentation
ENABLE_DOCS = True  # Set to False in production for security
DOCS_URL = "/docs"
REDOC_URL = "/redoc"

# Request validation
MAX_REQUEST_SIZE = 100 * 1024 * 1024  # 100 MB
REQUEST_TIMEOUT = 300  # 5 minutes

# Pagination
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 1000

# ============================================
# Development Settings
# ============================================

# Debug mode
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Reload on code changes (development only)
RELOAD = os.getenv("RELOAD", "False").lower() == "true"

# Test mode
TEST_MODE = False

# Mock data (for development)
USE_MOCK_DATA = False

# ============================================
# Feature Flags
# ============================================

# Enable/disable features
FEATURE_USER_REGISTRATION = False  # Only admin can register users
FEATURE_USER_FEEDBACK = True
FEATURE_ANNOUNCEMENTS = True
FEATURE_AUTO_AGGREGATION = True

# Experimental features
EXPERIMENTAL_FEATURES = False

# ============================================
# Monitoring & Error Tracking
# ============================================

# Sentry (error tracking - future)
SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
SENTRY_ENABLED = SENTRY_DSN is not None

# Health check
HEALTH_CHECK_ENDPOINT = "/health"

# ============================================
# Backup Settings
# ============================================

# Database backups
ENABLE_AUTO_BACKUP = True
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_SCHEDULE = "0 3 * * *"  # Run at 3 AM daily
BACKUP_RETENTION_DAYS = 30

# ============================================
# Helper Functions
# ============================================


def get_config_summary() -> dict:
    """Get a summary of current configuration."""
    return {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "database_type": DATABASE_TYPE,
        "debug_mode": DEBUG,
        "server_host": SERVER_HOST,
        "server_port": SERVER_PORT,
        "admin_dashboard_port": ADMIN_DASHBOARD_PORT,
        "api_docs_enabled": ENABLE_DOCS,
    }


def is_production() -> bool:
    """Check if running in production mode."""
    return not DEBUG and DATABASE_TYPE == "postgresql"


def get_database_url() -> str:
    """Get the appropriate database URL."""
    return DATABASE_URL


# ============================================
# Security Validation Functions
# ============================================


def check_security_config() -> dict:
    """
    Check security configuration and return status.

    Returns dict with:
        - is_secure: bool - True if all security checks pass
        - warnings: list - Warning messages for insecure settings
        - errors: list - Error messages (only in strict mode)
    """
    warnings = []
    errors = []

    # Check SECRET_KEY
    if SECRET_KEY == _DEFAULT_SECRET_KEY:
        msg = "SECRET_KEY is using default value! Generate a secure key with: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
        if SECURITY_MODE == "strict":
            errors.append(msg)
        else:
            warnings.append(msg)
    elif len(SECRET_KEY) < 32:
        warnings.append(f"SECRET_KEY is only {len(SECRET_KEY)} characters. Recommend at least 32 characters.")

    # Check API_KEY
    if API_KEY == _DEFAULT_API_KEY:
        msg = "API_KEY is using default value! Generate a secure key with: python3 -c \"import secrets; print(secrets.token_urlsafe(48))\""
        if SECURITY_MODE == "strict":
            errors.append(msg)
        else:
            warnings.append(msg)

    # Check admin password
    if DEFAULT_ADMIN_PASSWORD == _DEFAULT_ADMIN_PASSWORD:
        warnings.append("Default admin password 'admin123' should be changed after first login!")

    # Check IP filter
    if not ALLOWED_IP_RANGE:
        warnings.append("ALLOWED_IP_RANGE not set - server accepts connections from any IP")

    # Check CORS
    if CORS_ALLOW_ALL:
        warnings.append("CORS allows all origins - set CORS_ORIGINS for production")

    return {
        "is_secure": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "security_mode": SECURITY_MODE,
    }


def validate_security_on_startup(logger=None) -> bool:
    """
    Validate security configuration on server startup.

    In 'strict' mode: raises exception if critical security issues found
    In 'warn' mode: logs warnings but continues

    Args:
        logger: Optional logger instance (uses print if not provided)

    Returns:
        True if startup should continue, False if should abort
    """
    result = check_security_config()

    def log_warning(msg):
        if logger:
            logger.warning(f"SECURITY: {msg}")
        else:
            print(f"[WARNING] SECURITY: {msg}")

    def log_error(msg):
        if logger:
            logger.error(f"SECURITY: {msg}")
        else:
            print(f"[ERROR] SECURITY: {msg}")

    def log_info(msg):
        if logger:
            logger.info(f"SECURITY: {msg}")
        else:
            print(f"[INFO] SECURITY: {msg}")

    # Log warnings
    for warning in result["warnings"]:
        log_warning(warning)

    # Log errors
    for error in result["errors"]:
        log_error(error)

    # In strict mode, fail if there are errors
    if result["errors"]:
        log_error("Security validation FAILED. Set SECURITY_MODE=warn to bypass (not recommended).")
        return False

    # Log success
    if not result["warnings"]:
        log_info("Security configuration validated - all checks passed!")
    else:
        log_warning(f"Security configuration has {len(result['warnings'])} warning(s) - review before production deployment")

    return True


def get_security_status() -> dict:
    """Get security configuration status for API/dashboard display."""
    result = check_security_config()
    return {
        "is_secure": result["is_secure"],
        "warning_count": len(result["warnings"]),
        "error_count": len(result["errors"]),
        "security_mode": SECURITY_MODE,
        "ip_filter_enabled": bool(ALLOWED_IP_RANGE),
        "cors_restricted": not CORS_ALLOW_ALL,
        "using_default_secret": SECRET_KEY == _DEFAULT_SECRET_KEY,
        "using_default_api_key": API_KEY == _DEFAULT_API_KEY,
    }


if __name__ == "__main__":
    # Print configuration summary for debugging
    import json

    print("LocalizationTools Server Configuration")
    print("=" * 50)
    print(json.dumps(get_config_summary(), indent=2))
    print(f"\nDatabase URL: {DATABASE_URL}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Logs directory: {LOGS_DIR}")
    print(f"Is Production: {is_production()}")
