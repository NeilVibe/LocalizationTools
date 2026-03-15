"""Endpoint paths, response field sets, and test data constants.

Centralises all URL strings and expected schema shapes so that test
files never hard-code them.  Any endpoint path change only needs to be
updated here.
"""
from __future__ import annotations


# ======================================================================
# Auth endpoints  (prefix: /api/v2/auth)
# ======================================================================

AUTH_LOGIN = "/api/v2/auth/login"
AUTH_REGISTER = "/api/v2/auth/register"
AUTH_ME = "/api/v2/auth/me"
AUTH_USERS = "/api/v2/auth/users"
AUTH_USER = "/api/v2/auth/users/{user_id}"
AUTH_ACTIVATE = "/api/v2/auth/users/{user_id}/activate"
AUTH_DEACTIVATE = "/api/v2/auth/users/{user_id}/deactivate"
AUTH_CHANGE_PASSWORD = "/api/v2/auth/me/password"
AUTH_ADMIN_USERS = "/api/v2/auth/admin/users"
AUTH_ADMIN_USER = "/api/v2/auth/admin/users/{user_id}"
AUTH_ADMIN_RESET_PASSWORD = "/api/v2/auth/admin/users/{user_id}/reset-password"
AUTH_ADMIN_DELETE_USER = "/api/v2/auth/admin/users/{user_id}"

# ======================================================================
# Project endpoints  (prefix: /api/ldm)
# ======================================================================

PROJECTS_LIST = "/api/ldm/projects"
PROJECTS_CREATE = "/api/ldm/projects"
PROJECT_GET = "/api/ldm/projects/{project_id}"
PROJECT_RENAME = "/api/ldm/projects/{project_id}/rename"
PROJECT_DELETE = "/api/ldm/projects/{project_id}"
PROJECT_RESTRICTION = "/api/ldm/projects/{project_id}/restriction"
PROJECT_ACCESS = "/api/ldm/projects/{project_id}/access"
PROJECT_ACCESS_REVOKE = "/api/ldm/projects/{project_id}/access/{user_id}"
PROJECT_TREE = "/api/ldm/projects/{project_id}/tree"

# ======================================================================
# Folder endpoints
# ======================================================================

FOLDERS_LIST = "/api/ldm/projects/{project_id}/folders"
FOLDERS_CREATE = "/api/ldm/folders"
FOLDER_GET = "/api/ldm/folders/{folder_id}"
FOLDER_RENAME = "/api/ldm/folders/{folder_id}/rename"
FOLDER_MOVE = "/api/ldm/folders/{folder_id}/move"
FOLDER_DELETE = "/api/ldm/folders/{folder_id}"

# ======================================================================
# File endpoints
# ======================================================================

FILES_UPLOAD = "/api/ldm/files/upload"
FILES_LIST = "/api/ldm/files"
FILE_GET = "/api/ldm/files/{file_id}"
FILE_DOWNLOAD = "/api/ldm/files/{file_id}/download"
FILE_DELETE = "/api/ldm/files/{file_id}"
FILE_MOVE = "/api/ldm/files/{file_id}/move"
FILE_RENAME = "/api/ldm/files/{file_id}/rename"
FILE_TO_TM = "/api/ldm/files/{file_id}/to-tm"

# ======================================================================
# Row endpoints
# ======================================================================

ROWS_LIST = "/api/ldm/files/{file_id}/rows"
ROW_UPDATE = "/api/ldm/rows/{row_id}"

# ======================================================================
# TM CRUD endpoints
# ======================================================================

TM_UPLOAD = "/api/ldm/tm/upload"
TM_LIST = "/api/ldm/tm"
TM_GET = "/api/ldm/tm/{tm_id}"
TM_DELETE = "/api/ldm/tm/{tm_id}"
TM_EXPORT = "/api/ldm/tm/{tm_id}/export"

# ======================================================================
# TM Entries endpoints
# ======================================================================

TM_ENTRIES = "/api/ldm/tm/{tm_id}/entries"
TM_ENTRY = "/api/ldm/tm/{tm_id}/entries/{entry_id}"
TM_ENTRY_CONFIRM = "/api/ldm/tm/{tm_id}/entries/{entry_id}/confirm"
TM_ENTRIES_BULK_CONFIRM = "/api/ldm/tm/{tm_id}/entries/bulk-confirm"

# ======================================================================
# TM Search endpoints
# ======================================================================

TM_SUGGEST = "/api/ldm/tm/suggest"
TM_SEARCH = "/api/ldm/tm/{tm_id}/search"
TM_SEARCH_EXACT = "/api/ldm/tm/{tm_id}/search/exact"

# ======================================================================
# TM Index endpoints
# ======================================================================

TM_BUILD_INDEXES = "/api/ldm/tm/{tm_id}/build-indexes"
TM_INDEX_STATUS = "/api/ldm/tm/{tm_id}/indexes"
TM_SYNC_STATUS = "/api/ldm/tm/{tm_id}/sync-status"
TM_SYNC = "/api/ldm/tm/{tm_id}/sync"

# ======================================================================
# TM Linking endpoints
# ======================================================================

TM_LINK = "/api/ldm/projects/{project_id}/link-tm"
TM_UNLINK = "/api/ldm/projects/{project_id}/link-tm/{tm_id}"
TM_LINKED = "/api/ldm/projects/{project_id}/linked-tms"

# ======================================================================
# TM Assignment endpoints
# ======================================================================

TM_ASSIGNMENT = "/api/ldm/tm/{tm_id}/assignment"
TM_ASSIGN = "/api/ldm/tm/{tm_id}/assign"
TM_ACTIVATE = "/api/ldm/tm/{tm_id}/activate"
TM_ACTIVE_FOR_FILE = "/api/ldm/files/{file_id}/active-tms"
TM_TREE = "/api/ldm/tm-tree"

# ======================================================================
# TM Leverage endpoints
# ======================================================================

FILE_LEVERAGE = "/api/ldm/files/{file_id}/leverage"

# ======================================================================
# Pretranslate endpoints
# ======================================================================

PRETRANSLATE = "/api/ldm/pretranslate"

# ======================================================================
# Merge endpoints
# ======================================================================

FILE_MERGE = "/api/ldm/files/{file_id}/merge"
FILE_GAMEDEV_MERGE = "/api/ldm/files/{file_id}/gamedev-merge"

# ======================================================================
# GameData endpoints
# ======================================================================

GAMEDATA_BROWSE = "/api/ldm/gamedata/browse"
GAMEDATA_COLUMNS = "/api/ldm/gamedata/columns"
GAMEDATA_SAVE = "/api/ldm/gamedata/save"

# ======================================================================
# Codex endpoints
# ======================================================================

CODEX_SEARCH = "/api/ldm/codex/search"
CODEX_ENTITY = "/api/ldm/codex/entity/{entity_type}/{strkey}"
CODEX_LIST = "/api/ldm/codex/list/{entity_type}"
CODEX_TYPES = "/api/ldm/codex/types"

# ======================================================================
# WorldMap endpoints
# ======================================================================

WORLDMAP_DATA = "/api/ldm/worldmap/data"

# ======================================================================
# AI Suggestions endpoints
# ======================================================================

AI_SUGGESTIONS_STATUS = "/api/ldm/ai-suggestions/status"
AI_SUGGESTIONS = "/api/ldm/ai-suggestions/{string_id}"

# ======================================================================
# Naming endpoints
# ======================================================================

NAMING_SIMILAR = "/api/ldm/naming/similar/{entity_type}"
NAMING_SUGGEST = "/api/ldm/naming/suggest/{entity_type}"
NAMING_STATUS = "/api/ldm/naming/status"

# ======================================================================
# Search endpoints
# ======================================================================

SEARCH_EXPLORER = "/api/ldm/search"
SEARCH_SEMANTIC = "/api/ldm/semantic-search"

# ======================================================================
# QA endpoints
# ======================================================================

QA_CHECK_ROW = "/api/ldm/rows/{row_id}/check-qa"
QA_ROW_RESULTS = "/api/ldm/rows/{row_id}/qa-results"
QA_CHECK_FILE = "/api/ldm/files/{file_id}/check-qa"
QA_FILE_RESULTS = "/api/ldm/files/{file_id}/qa-results"
QA_FILE_SUMMARY = "/api/ldm/files/{file_id}/qa-summary"
QA_RESOLVE = "/api/ldm/qa-results/{result_id}/resolve"

# ======================================================================
# Grammar endpoints
# ======================================================================

GRAMMAR_STATUS = "/api/ldm/grammar/status"
GRAMMAR_CHECK_FILE = "/api/ldm/files/{file_id}/check-grammar"
GRAMMAR_CHECK_ROW = "/api/ldm/rows/{row_id}/check-grammar"

# ======================================================================
# Context endpoints
# ======================================================================

CONTEXT_STATUS = "/api/ldm/context/status"
CONTEXT_BY_STRING_ID = "/api/ldm/context/{string_id}"
CONTEXT_DETECT = "/api/ldm/context/detect"

# ======================================================================
# MapData endpoints
# ======================================================================

MAPDATA_STATUS = "/api/ldm/mapdata/status"
MAPDATA_CONFIGURE = "/api/ldm/mapdata/configure"
MAPDATA_IMAGE = "/api/ldm/mapdata/image/{string_id}"
MAPDATA_AUDIO = "/api/ldm/mapdata/audio/{string_id}"
MAPDATA_COMBINED = "/api/ldm/mapdata/context/{string_id}"
MAPDATA_THUMBNAIL = "/api/ldm/mapdata/thumbnail/{texture_name}"
MAPDATA_AUDIO_STREAM = "/api/ldm/mapdata/audio/stream/{string_id}"

# ======================================================================
# Trash endpoints
# ======================================================================

TRASH_LIST = "/api/ldm/trash"
TRASH_RESTORE = "/api/ldm/trash/{trash_id}/restore"
TRASH_PERMANENT_DELETE = "/api/ldm/trash/{trash_id}"
TRASH_EMPTY = "/api/ldm/trash/empty"

# ======================================================================
# Platform endpoints
# ======================================================================

PLATFORMS_LIST = "/api/ldm/platforms"
PLATFORMS_CREATE = "/api/ldm/platforms"
PLATFORM_GET = "/api/ldm/platforms/{platform_id}"
PLATFORM_UPDATE = "/api/ldm/platforms/{platform_id}"
PLATFORM_DELETE = "/api/ldm/platforms/{platform_id}"
PROJECT_ASSIGN_PLATFORM = "/api/ldm/projects/{project_id}/platform"
PLATFORM_RESTRICTION = "/api/ldm/platforms/{platform_id}/restriction"
PLATFORM_ACCESS = "/api/ldm/platforms/{platform_id}/access"
PLATFORM_ACCESS_REVOKE = "/api/ldm/platforms/{platform_id}/access/{user_id}"

# ======================================================================
# Capabilities (admin) endpoints
# ======================================================================

CAPABILITIES_AVAILABLE = "/api/ldm/admin/capabilities/available"
CAPABILITIES_GRANT = "/api/ldm/admin/capabilities"
CAPABILITIES_REVOKE = "/api/ldm/admin/capabilities/{capability_id}"
CAPABILITIES_LIST_ALL = "/api/ldm/admin/capabilities"
CAPABILITIES_USER = "/api/ldm/admin/capabilities/user/{user_id}"

# ======================================================================
# Settings endpoints
# ======================================================================

SETTINGS_EMBEDDING_ENGINES = "/api/ldm/settings/embedding-engines"
SETTINGS_EMBEDDING_ENGINE = "/api/ldm/settings/embedding-engine"

# ======================================================================
# Maintenance endpoints
# ======================================================================

MAINTENANCE_CHECK_STALE = "/api/ldm/maintenance/check-stale"
MAINTENANCE_STALE_TMS = "/api/ldm/maintenance/stale-tms"
MAINTENANCE_SYNC = "/api/ldm/maintenance/sync/{tm_id}"
MAINTENANCE_STATUS = "/api/ldm/maintenance/sync-status"

# ======================================================================
# Health endpoints
# ======================================================================

LDM_HEALTH = "/api/ldm/health"
APP_HEALTH = "/health"

# ======================================================================
# Offline / Sync endpoints  (prefix: /api/ldm/offline)
# ======================================================================

OFFLINE_STATUS = "/api/ldm/offline/status"
OFFLINE_FILES = "/api/ldm/offline/files"
OFFLINE_SUBSCRIPTIONS = "/api/ldm/offline/subscriptions"
OFFLINE_SUBSCRIBE = "/api/ldm/offline/subscribe"
OFFLINE_UNSUBSCRIBE = "/api/ldm/offline/subscribe/{entity_type}/{entity_id}"
OFFLINE_PUSH_PREVIEW = "/api/ldm/offline/push-preview/{file_id}"
OFFLINE_PUSH_CHANGES = "/api/ldm/offline/push-changes"
OFFLINE_SYNC_SUBSCRIPTION = "/api/ldm/offline/sync-subscription"
OFFLINE_LOCAL_FILES = "/api/ldm/offline/local-files"
OFFLINE_LOCAL_FILE_COUNT = "/api/ldm/offline/local-file-count"
OFFLINE_STORAGE_FILE = "/api/ldm/offline/storage/files/{file_id}"
OFFLINE_STORAGE_FILE_RENAME = "/api/ldm/offline/storage/files/{file_id}/rename"
OFFLINE_STORAGE_FILE_ROWS = "/api/ldm/offline/storage/files/{file_id}/rows"
OFFLINE_STORAGE_FOLDERS = "/api/ldm/offline/storage/folders"
OFFLINE_STORAGE_FOLDER = "/api/ldm/offline/storage/folders/{folder_id}"
OFFLINE_STORAGE_FOLDER_RENAME = "/api/ldm/offline/storage/folders/{folder_id}/rename"
OFFLINE_STORAGE_FILE_MOVE = "/api/ldm/offline/storage/files/{file_id}/move"
OFFLINE_STORAGE_FOLDER_MOVE = "/api/ldm/offline/storage/folders/{folder_id}/move"
OFFLINE_TRASH = "/api/ldm/offline/trash"
OFFLINE_TRASH_RESTORE = "/api/ldm/offline/trash/{trash_id}/restore"
OFFLINE_TRASH_DELETE = "/api/ldm/offline/trash/{trash_id}"
OFFLINE_DOWNLOAD = "/api/ldm/files/{file_id}/download-for-offline"
SYNC_TO_CENTRAL = "/api/ldm/sync-to-central"
SYNC_TM_TO_CENTRAL = "/api/ldm/tm/sync-to-central"

# ======================================================================
# Expected response field sets
# ======================================================================

PROJECT_FIELDS = ["id", "name", "owner_id", "is_restricted"]
PROJECT_FIELDS_FULL = ["id", "name", "description", "owner_id", "platform_id", "created_at", "updated_at", "is_restricted"]

FILE_FIELDS = ["id", "name", "original_filename", "format", "row_count"]
FILE_FIELDS_FULL = ["id", "project_id", "folder_id", "name", "original_filename", "format", "file_type", "row_count", "source_language", "target_language"]

ROW_FIELDS = ["id", "file_id", "row_num", "status"]
ROW_FIELDS_FULL = ["id", "file_id", "row_num", "string_id", "source", "target", "status", "qa_flag_count", "category"]

TM_FIELDS = ["id", "name", "source_lang", "target_lang", "entry_count", "status"]
TM_FIELDS_FULL = ["id", "name", "description", "source_lang", "target_lang", "entry_count", "status", "created_at"]

TM_UPLOAD_FIELDS = ["tm_id", "name", "entry_count", "status", "time_seconds", "rate_per_second"]

CODEX_ENTITY_FIELDS = ["entity_type", "strkey", "name", "source_file"]
CODEX_ENTITY_FIELDS_FULL = ["entity_type", "strkey", "name", "description", "knowledge_key", "image_texture", "audio_key", "source_file", "attributes", "related_entities"]

CODEX_SEARCH_FIELDS = ["results", "count", "search_time_ms"]

WORLDMAP_FIELDS = ["nodes", "routes", "bounds"]

QA_ISSUE_FIELDS = ["id", "check_type", "severity", "message"]
QA_SUMMARY_FIELDS = ["file_id", "line", "term", "pattern", "character", "grammar", "total"]

PAGINATION_FIELDS = ["rows", "total", "page", "limit", "total_pages"]

FOLDER_FIELDS = ["id", "name", "project_id"]

# ======================================================================
# Test credentials
# ======================================================================

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_EMAIL = "admin@locanext.local"

# ======================================================================
# Test data constants
# ======================================================================

KOREAN_TEXT_SAMPLES = [
    "안녕하세요",
    "감사합니다",
    "검은 칼날의 전사",
    "마법<br/>스킬",
    "지역 이름: 봄의 숲",
]

BRTAG_SAMPLES = [
    "첫 줄<br/>둘째 줄",
    "A<br/>B<br/>C",
    "한 줄만",  # no br-tags (control)
]

VALID_ROW_STATUSES = ["pending", "translated", "reviewed", "approved"]

VALID_QA_CHECK_TYPES = ["line", "pattern", "term", "character", "grammar"]

VALID_SEARCH_MODES = ["contain", "exact", "not_contain", "fuzzy"]

VALID_FILE_FORMATS = ["xml", "xlsx", "txt", "tsv"]

VALID_TM_MODES = ["standard", "stringid"]

VALID_EXPORT_FORMATS = ["text", "excel", "tmx"]

ENTITY_TYPES = ["item", "character", "region", "skill", "gimmick", "knowledge", "quest"]
