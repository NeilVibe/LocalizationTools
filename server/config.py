"""
Server Configuration

This module contains all configuration settings for the LocalizationTools central server.
"""

import os
import sys
from pathlib import Path
from typing import Optional

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
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8888"))

# Admin dashboard
ADMIN_DASHBOARD_PORT = int(os.getenv("ADMIN_DASHBOARD_PORT", "8885"))

# CORS settings
ALLOWED_ORIGINS = [
    "http://localhost:7860",
    "http://127.0.0.1:7860",
    "http://localhost:8885",
    "http://127.0.0.1:8885",
]

# Add production origins if specified
PRODUCTION_ORIGIN = os.getenv("PRODUCTION_ORIGIN")
if PRODUCTION_ORIGIN:
    ALLOWED_ORIGINS.append(PRODUCTION_ORIGIN)

# ============================================
# Database Settings
# ============================================

# Database type
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite")  # "sqlite" or "postgresql"

# SQLite settings (development)
SQLITE_DATABASE_PATH = DATA_DIR / "localizationtools.db"
SQLITE_DATABASE_URL = f"sqlite:///{SQLITE_DATABASE_PATH}"

# PostgreSQL settings (production)
POSTGRES_USER = os.getenv("POSTGRES_USER", "localization_admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "change_this_password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "localizationtools")
POSTGRES_DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Current database URL (based on DATABASE_TYPE)
DATABASE_URL = (
    POSTGRES_DATABASE_URL if DATABASE_TYPE == "postgresql" else SQLITE_DATABASE_URL
)

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

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-CHANGE-IN-PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

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
