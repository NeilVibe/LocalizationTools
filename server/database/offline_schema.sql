-- =============================================================================
-- P3 Offline/Online Mode - SQLite Schema for Local Storage
-- =============================================================================
-- This schema mirrors the PostgreSQL structure but optimized for SQLite.
-- Includes sync metadata for tracking downloaded content and local changes.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Sync Metadata
-- -----------------------------------------------------------------------------

-- Track sync status and connection info
CREATE TABLE IF NOT EXISTS sync_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Default sync metadata
INSERT OR IGNORE INTO sync_meta (key, value) VALUES
    ('last_sync', ''),
    ('server_url', ''),
    ('user_id', ''),
    ('username', '');

-- -----------------------------------------------------------------------------
-- Platforms (mirrors ldm_platforms)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS offline_platforms (
    id INTEGER PRIMARY KEY,           -- Same as server ID
    server_id INTEGER NOT NULL,       -- Server's platform ID
    name TEXT NOT NULL,
    description TEXT,
    owner_id INTEGER,
    is_restricted INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT,
    downloaded_at TEXT DEFAULT (datetime('now')),
    sync_status TEXT DEFAULT 'synced'  -- synced, modified, new
);

CREATE INDEX IF NOT EXISTS idx_offline_platforms_server_id ON offline_platforms(server_id);

-- -----------------------------------------------------------------------------
-- Projects (mirrors ldm_projects)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS offline_projects (
    id INTEGER PRIMARY KEY,
    server_id INTEGER NOT NULL,       -- Server's project ID
    name TEXT NOT NULL,
    description TEXT,
    platform_id INTEGER,              -- Local platform ID
    server_platform_id INTEGER,       -- Server's platform ID
    owner_id INTEGER,
    is_restricted INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT,
    downloaded_at TEXT DEFAULT (datetime('now')),
    sync_status TEXT DEFAULT 'synced',
    FOREIGN KEY (platform_id) REFERENCES offline_platforms(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_offline_projects_server_id ON offline_projects(server_id);
CREATE INDEX IF NOT EXISTS idx_offline_projects_platform ON offline_projects(platform_id);

-- -----------------------------------------------------------------------------
-- Folders (mirrors ldm_folders)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS offline_folders (
    id INTEGER PRIMARY KEY,
    server_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    server_project_id INTEGER NOT NULL,
    parent_id INTEGER,                -- Local parent folder ID
    server_parent_id INTEGER,         -- Server's parent folder ID
    created_at TEXT,
    downloaded_at TEXT DEFAULT (datetime('now')),
    sync_status TEXT DEFAULT 'synced',
    FOREIGN KEY (project_id) REFERENCES offline_projects(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES offline_folders(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_offline_folders_server_id ON offline_folders(server_id);
CREATE INDEX IF NOT EXISTS idx_offline_folders_project ON offline_folders(project_id);

-- -----------------------------------------------------------------------------
-- Files (mirrors ldm_files)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS offline_files (
    id INTEGER PRIMARY KEY,
    server_id INTEGER NOT NULL,       -- Server's file ID
    name TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    format TEXT NOT NULL,             -- txt, xml, xlsx
    row_count INTEGER DEFAULT 0,
    source_language TEXT DEFAULT 'ko',
    target_language TEXT,
    project_id INTEGER NOT NULL,
    server_project_id INTEGER NOT NULL,
    folder_id INTEGER,
    server_folder_id INTEGER,
    extra_data TEXT,                  -- JSON metadata
    created_at TEXT,
    updated_at TEXT,
    downloaded_at TEXT DEFAULT (datetime('now')),
    sync_status TEXT DEFAULT 'synced',  -- 'synced', 'modified', 'new', 'local', 'orphaned'
                                        -- 'local' = created in Offline Storage, never synced
                                        -- 'orphaned' = was synced but lost server link
    error_message TEXT,                 -- P3-PHASE5: Reason for orphan/error status
    FOREIGN KEY (project_id) REFERENCES offline_projects(id) ON DELETE CASCADE,
    FOREIGN KEY (folder_id) REFERENCES offline_folders(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_offline_files_server_id ON offline_files(server_id);
CREATE INDEX IF NOT EXISTS idx_offline_files_project ON offline_files(project_id);
CREATE INDEX IF NOT EXISTS idx_offline_files_folder ON offline_files(folder_id);
CREATE INDEX IF NOT EXISTS idx_offline_files_sync_status ON offline_files(sync_status);  -- P3-PHASE5

-- -----------------------------------------------------------------------------
-- Rows (mirrors ldm_rows)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS offline_rows (
    id INTEGER PRIMARY KEY,
    server_id INTEGER NOT NULL,       -- Server's row ID
    file_id INTEGER NOT NULL,
    server_file_id INTEGER NOT NULL,
    row_num INTEGER NOT NULL,
    string_id TEXT,
    source TEXT,                      -- StrOrigin (read-only)
    target TEXT,                      -- Str (editable)
    memo TEXT,
    status TEXT DEFAULT 'normal',     -- normal, reviewed, approved
    extra_data TEXT,                  -- JSON for additional columns
    created_at TEXT,
    updated_at TEXT,
    downloaded_at TEXT DEFAULT (datetime('now')),
    sync_status TEXT DEFAULT 'synced',
    FOREIGN KEY (file_id) REFERENCES offline_files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_offline_rows_server_id ON offline_rows(server_id);
CREATE INDEX IF NOT EXISTS idx_offline_rows_file ON offline_rows(file_id);
CREATE INDEX IF NOT EXISTS idx_offline_rows_string_id ON offline_rows(string_id);

-- -----------------------------------------------------------------------------
-- Translation Memories (mirrors ldm_translation_memories)
-- SYNC-008: TM offline sync support
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS offline_tms (
    id INTEGER PRIMARY KEY,
    server_id INTEGER NOT NULL,       -- Server's TM ID
    name TEXT NOT NULL,
    description TEXT,
    source_lang TEXT DEFAULT 'ko',
    target_lang TEXT DEFAULT 'en',
    entry_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ready',      -- pending, indexing, ready, error
    mode TEXT DEFAULT 'standard',     -- standard, stringid
    owner_id INTEGER,
    created_at TEXT,
    updated_at TEXT,
    indexed_at TEXT,
    downloaded_at TEXT DEFAULT (datetime('now')),
    sync_status TEXT DEFAULT 'synced'
);

CREATE INDEX IF NOT EXISTS idx_offline_tms_server_id ON offline_tms(server_id);

-- -----------------------------------------------------------------------------
-- TM Entries (mirrors ldm_tm_entries)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS offline_tm_entries (
    id INTEGER PRIMARY KEY,
    server_id INTEGER NOT NULL,       -- Server's entry ID
    tm_id INTEGER NOT NULL,           -- Local TM ID
    server_tm_id INTEGER NOT NULL,    -- Server's TM ID
    source_text TEXT NOT NULL,
    target_text TEXT,
    source_hash TEXT NOT NULL,        -- SHA256 for O(1) lookup
    string_id TEXT,                   -- For stringid mode
    created_by TEXT,
    change_date TEXT,
    updated_at TEXT,
    updated_by TEXT,
    is_confirmed INTEGER DEFAULT 0,
    confirmed_by TEXT,
    confirmed_at TEXT,
    downloaded_at TEXT DEFAULT (datetime('now')),
    sync_status TEXT DEFAULT 'synced',
    FOREIGN KEY (tm_id) REFERENCES offline_tms(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_offline_tm_entries_server_id ON offline_tm_entries(server_id);
CREATE INDEX IF NOT EXISTS idx_offline_tm_entries_tm ON offline_tm_entries(tm_id);
CREATE INDEX IF NOT EXISTS idx_offline_tm_entries_hash ON offline_tm_entries(source_hash);
CREATE INDEX IF NOT EXISTS idx_offline_tm_entries_string_id ON offline_tm_entries(string_id);

-- -----------------------------------------------------------------------------
-- TM Assignments (mirrors ldm_tm_assignments)
-- Links TMs to Platform/Project/Folder scope
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS offline_tm_assignments (
    id INTEGER PRIMARY KEY,
    server_id INTEGER NOT NULL,
    tm_id INTEGER NOT NULL,
    server_tm_id INTEGER NOT NULL,
    platform_id INTEGER,
    project_id INTEGER,
    folder_id INTEGER,
    is_active INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 0,
    assigned_by INTEGER,
    assigned_at TEXT,
    activated_at TEXT,
    downloaded_at TEXT DEFAULT (datetime('now')),
    sync_status TEXT DEFAULT 'synced',
    FOREIGN KEY (tm_id) REFERENCES offline_tms(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_offline_tm_assignments_tm ON offline_tm_assignments(tm_id);
CREATE INDEX IF NOT EXISTS idx_offline_tm_assignments_scope ON offline_tm_assignments(platform_id, project_id, folder_id);

-- -----------------------------------------------------------------------------
-- Local Changes (for tracking edits to sync back)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS local_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,        -- platform, project, folder, file, row, tm, tm_entry
    entity_id INTEGER NOT NULL,       -- Local entity ID
    server_id INTEGER,                -- Server entity ID (null for new)
    change_type TEXT NOT NULL,        -- add, edit, delete
    field_name TEXT,                  -- Which field changed (for edits)
    old_value TEXT,                   -- Previous value
    new_value TEXT,                   -- New value
    changed_at TEXT DEFAULT (datetime('now')),
    synced_at TEXT,                   -- When synced to server (null = pending)
    sync_status TEXT DEFAULT 'pending' -- pending, synced, conflict, error
);

CREATE INDEX IF NOT EXISTS idx_local_changes_entity ON local_changes(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_local_changes_status ON local_changes(sync_status);
CREATE INDEX IF NOT EXISTS idx_local_changes_pending ON local_changes(sync_status) WHERE sync_status = 'pending';

-- -----------------------------------------------------------------------------
-- Sync Subscriptions (what's enabled for offline sync)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sync_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,        -- platform, project, folder, file, tm
    entity_id INTEGER NOT NULL,
    entity_name TEXT NOT NULL,        -- For display in dashboard
    server_id INTEGER NOT NULL,       -- Server's entity ID
    enabled INTEGER DEFAULT 1,        -- 1 = active, 0 = paused
    auto_subscribed INTEGER DEFAULT 0, -- 1 = auto (file opened), 0 = manual
    created_at TEXT DEFAULT (datetime('now')),
    last_sync_at TEXT,
    sync_status TEXT DEFAULT 'pending', -- pending, syncing, synced, error
    error_message TEXT,
    UNIQUE(entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_sync_subscriptions_type ON sync_subscriptions(entity_type);
CREATE INDEX IF NOT EXISTS idx_sync_subscriptions_enabled ON sync_subscriptions(enabled);

-- -----------------------------------------------------------------------------
-- Download Queue (for batch downloads)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS download_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,        -- file, folder, project
    server_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'pending',    -- pending, downloading, completed, error
    error_message TEXT,
    queued_at TEXT DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_download_queue_status ON download_queue(status);

-- -----------------------------------------------------------------------------
-- Views for easy querying
-- -----------------------------------------------------------------------------

-- Files with pending changes
CREATE VIEW IF NOT EXISTS v_pending_files AS
SELECT DISTINCT f.*
FROM offline_files f
INNER JOIN offline_rows r ON r.file_id = f.id
WHERE r.sync_status IN ('modified', 'new');

-- Count of pending changes by file
CREATE VIEW IF NOT EXISTS v_pending_counts AS
SELECT
    f.id as file_id,
    f.name as file_name,
    COUNT(CASE WHEN r.sync_status = 'modified' THEN 1 END) as modified_count,
    COUNT(CASE WHEN r.sync_status = 'new' THEN 1 END) as new_count
FROM offline_files f
LEFT JOIN offline_rows r ON r.file_id = f.id
GROUP BY f.id, f.name;

-- -----------------------------------------------------------------------------
-- Schema version for migrations
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO schema_version (version) VALUES (2);  -- SYNC-008: Added TM tables
