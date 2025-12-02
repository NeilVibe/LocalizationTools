"""
Client Application Configuration

This module contains all configuration settings for the LocalizationTools client application.
"""

import os
from pathlib import Path

# ============================================
# Application Info
# ============================================

APP_NAME = "LocalizationTools"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Neil"
APP_DESCRIPTION = "Unified Localization & Translation Tools Suite"

# ============================================
# Paths
# ============================================

# Base directory (where this config file is located)
BASE_DIR = Path(__file__).parent.absolute()
ROOT_DIR = BASE_DIR.parent

# Models directory
MODELS_DIR = BASE_DIR / "models"
KOREAN_BERT_MODEL_PATH = MODELS_DIR / "KRTransformer"

# Assets directory
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"
ICON_PATH = ASSETS_DIR / "icon.ico"

# Data directories (ALL inside program folder under server/data/)
# This keeps everything in one clean tree for easy backup and management
SERVER_DATA_DIR = ROOT_DIR / "server" / "data"
USER_DATA_DIR = SERVER_DATA_DIR / "cache"  # Client data/machine ID
CACHE_DIR = SERVER_DATA_DIR / "cache"
LOGS_DIR = SERVER_DATA_DIR / "logs"
TEMP_DIR = SERVER_DATA_DIR / "cache" / "temp"

# Create directories if they don't exist
for directory in [USER_DATA_DIR, CACHE_DIR, LOGS_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================
# Server Connection
# ============================================

# Server endpoints
SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8888"))
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

# API Endpoints
API_BASE_URL = f"{SERVER_URL}/api"
API_AUTH_LOGIN = f"{API_BASE_URL}/auth/login"
API_AUTH_REGISTER = f"{API_BASE_URL}/auth/register"
API_LOGS = f"{API_BASE_URL}/logs"
API_SESSION_START = f"{API_BASE_URL}/sessions/start"
API_SESSION_END = f"{API_BASE_URL}/sessions/end"
API_VERSION_CHECK = f"{API_BASE_URL}/version/latest"
API_ANNOUNCEMENTS = f"{API_BASE_URL}/announcements"

# Connection settings
API_TIMEOUT = 30  # seconds
API_RETRY_COUNT = 3
API_RETRY_DELAY = 2  # seconds

# API Key (for client-server communication)
API_KEY = os.getenv("API_KEY", "dev-key-change-in-production")

# ============================================
# UI Settings
# ============================================

# Gradio settings
GRADIO_SERVER_NAME = "127.0.0.1"  # localhost only
GRADIO_SERVER_PORT = 7860
GRADIO_SHARE = False  # Never share publicly
GRADIO_INBROWSER = True  # Auto-open browser

# Theme settings
UI_THEME = "soft"  # Options: "default", "soft", "monochrome", "glass"
UI_DARK_MODE = False

# Window settings (for desktop mode)
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}"

# ============================================
# Tool Settings
# ============================================

# XLSTransfer settings
XLSTRANSFER_FAISS_THRESHOLD = 0.99  # Default similarity threshold
XLSTRANSFER_BATCH_SIZE = 100  # Embedding batch size
XLSTRANSFER_MAX_FILE_SIZE_MB = 100  # Max upload file size

# General tool settings
MAX_CONCURRENT_OPERATIONS = 1  # Process one tool at a time
SHOW_PROGRESS = True
ENABLE_NOTIFICATIONS = True

# ============================================
# Logging Settings
# ============================================

# Local logging
LOG_FILE = LOGS_DIR / f"{APP_NAME}.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
LOG_ROTATION = "10 MB"  # Rotate when log file reaches 10MB
LOG_RETENTION = "1 month"  # Keep logs for 1 month

# Server logging (send to central server)
ENABLE_SERVER_LOGGING = True
LOG_QUEUE_MAX_SIZE = 100  # Queue logs locally if server unavailable
LOG_BATCH_SIZE = 10  # Send logs in batches

# Privacy settings
LOG_FILE_NAMES = False  # Don't log actual file names (privacy)
LOG_FILE_CONTENT = False  # Never log file content
LOG_USER_DATA = False  # Don't log user-specific data

# ============================================
# Performance Settings
# ============================================

# Model loading
LAZY_LOAD_MODELS = True  # Load models only when needed
MODEL_CACHE_SIZE = 1  # Number of models to keep in memory

# Processing
USE_MULTIPROCESSING = False  # Not recommended for Gradio
MAX_WORKERS = 4  # Thread pool size
CHUNK_SIZE = 1000  # For processing large files

# ============================================
# Update Settings
# ============================================

CHECK_UPDATES_ON_STARTUP = True
UPDATE_CHECK_INTERVAL = 86400  # 24 hours in seconds
AUTO_DOWNLOAD_UPDATES = False  # Prompt user instead
MANDATORY_UPDATE_FORCE = True  # Force install mandatory updates

# ============================================
# Session Settings
# ============================================

# Session management
SESSION_TIMEOUT = 3600  # 1 hour in seconds
REMEMBER_LOGIN = True
AUTO_LOGOUT_INACTIVE = True
INACTIVE_TIMEOUT = 1800  # 30 minutes

# Machine ID (unique identifier for this installation)
import uuid
import platform

MACHINE_ID = os.getenv("MACHINE_ID")
if not MACHINE_ID:
    # Generate and save machine ID
    machine_id_file = USER_DATA_DIR / "machine_id"
    if machine_id_file.exists():
        MACHINE_ID = machine_id_file.read_text().strip()
    else:
        MACHINE_ID = str(uuid.uuid4())
        machine_id_file.write_text(MACHINE_ID)

# System info
OS_INFO = f"{platform.system()} {platform.release()}"
PYTHON_VERSION = platform.python_version()

# ============================================
# Development Settings
# ============================================

# Debug mode
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "False").lower() == "true"

# Test mode
TEST_MODE = False  # Set to True for automated testing

# Mock server (for development without server running)
MOCK_SERVER = os.getenv("MOCK_SERVER", "False").lower() == "true"

# ============================================
# Feature Flags
# ============================================

# Enable/disable features
FEATURE_AUTO_UPDATES = True
FEATURE_ANNOUNCEMENTS = True
FEATURE_USER_FEEDBACK = True
FEATURE_PERFORMANCE_METRICS = True
FEATURE_ERROR_REPORTING = True

# Experimental features
EXPERIMENTAL_FEATURES = False

# ============================================
# Helper Functions
# ============================================

def get_config_summary() -> dict:
    """Get a summary of current configuration."""
    return {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "server_url": SERVER_URL,
        "debug_mode": DEBUG,
        "offline_mode": OFFLINE_MODE,
        "machine_id": MACHINE_ID,
        "os_info": OS_INFO,
    }


def is_server_available() -> bool:
    """Check if server is reachable (implemented in utils)."""
    # Will be implemented in client/utils/logger.py
    pass


if __name__ == "__main__":
    # Print configuration summary for debugging
    import json
    print("LocalizationTools Client Configuration")
    print("=" * 50)
    print(json.dumps(get_config_summary(), indent=2))
    print(f"\nLogs directory: {LOGS_DIR}")
    print(f"Cache directory: {CACHE_DIR}")
    print(f"Models directory: {MODELS_DIR}")
