-- ============================================
-- LocalizationTools Database Schema
-- PostgreSQL 15+
-- ============================================

-- Enable UUID extension for generating unique IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLE: users
-- Purpose: Store user authentication and profile data
-- ============================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt hashed
    display_name VARCHAR(100),
    department VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user',  -- 'user', 'admin', 'viewer'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    last_ip_address INET,
    preferences JSONB,  -- Store user preferences as JSON
    INDEX idx_users_username (username),
    INDEX idx_users_email (email),
    INDEX idx_users_active (is_active)
);

-- ============================================
-- TABLE: sessions
-- Purpose: Track active user sessions
-- ============================================
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    app_version VARCHAR(20),
    os_info VARCHAR(100),  -- Windows 10, macOS 13, etc.
    machine_id VARCHAR(255),  -- Unique machine identifier
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    ip_address INET,
    INDEX idx_sessions_user (user_id),
    INDEX idx_sessions_active (is_active),
    INDEX idx_sessions_started (started_at)
);

-- ============================================
-- TABLE: log_entries
-- Purpose: Main usage logs - every tool/function execution
-- ============================================
CREATE TABLE log_entries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,

    -- Tool & Function Info
    tool_name VARCHAR(100) NOT NULL,  -- 'XLSTransfer', 'TFMFull', etc.
    function_name VARCHAR(100) NOT NULL,  -- 'create_dictionary', 'translate_excel', etc.

    -- Timing
    timestamp_start TIMESTAMP NOT NULL,
    timestamp_end TIMESTAMP,
    duration_seconds FLOAT,

    -- File/Processing Info
    file_name VARCHAR(500),
    file_size_mb FLOAT,
    rows_processed INTEGER,
    sheets_processed INTEGER,

    -- Results
    status VARCHAR(20) NOT NULL,  -- 'success', 'error', 'cancelled'
    error_message TEXT,
    error_type VARCHAR(100),

    -- Performance Metrics
    cpu_percent FLOAT,
    memory_mb FLOAT,

    -- Additional Data (flexible JSON field)
    metadata JSONB,  -- Any extra tool-specific data

    INDEX idx_logs_user (user_id),
    INDEX idx_logs_session (session_id),
    INDEX idx_logs_tool (tool_name),
    INDEX idx_logs_function (function_name),
    INDEX idx_logs_timestamp (timestamp_start),
    INDEX idx_logs_status (status)
);

-- ============================================
-- TABLE: tool_usage_stats
-- Purpose: Aggregated statistics per tool (for faster queries)
-- Updated daily by cron job
-- ============================================
CREATE TABLE tool_usage_stats (
    id SERIAL PRIMARY KEY,
    tool_name VARCHAR(100) NOT NULL,
    date DATE NOT NULL,

    -- Usage Counts
    total_uses INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    successful_uses INTEGER DEFAULT 0,
    failed_uses INTEGER DEFAULT 0,

    -- Performance Averages
    avg_duration_seconds FLOAT,
    avg_file_size_mb FLOAT,
    avg_rows_processed FLOAT,

    -- Totals
    total_rows_processed BIGINT DEFAULT 0,
    total_files_processed INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (tool_name, date),
    INDEX idx_tool_stats_date (date),
    INDEX idx_tool_stats_tool (tool_name)
);

-- ============================================
-- TABLE: function_usage_stats
-- Purpose: Function-level statistics (detailed breakdown)
-- ============================================
CREATE TABLE function_usage_stats (
    id SERIAL PRIMARY KEY,
    tool_name VARCHAR(100) NOT NULL,
    function_name VARCHAR(100) NOT NULL,
    date DATE NOT NULL,

    -- Usage Counts
    total_uses INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    successful_uses INTEGER DEFAULT 0,
    failed_uses INTEGER DEFAULT 0,

    -- Performance
    avg_duration_seconds FLOAT,
    min_duration_seconds FLOAT,
    max_duration_seconds FLOAT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (tool_name, function_name, date),
    INDEX idx_func_stats_date (date),
    INDEX idx_func_stats_tool_func (tool_name, function_name)
);

-- ============================================
-- TABLE: error_logs
-- Purpose: Detailed error tracking and debugging
-- ============================================
CREATE TABLE error_logs (
    id SERIAL PRIMARY KEY,
    log_entry_id INTEGER REFERENCES log_entries(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,

    -- Error Details
    error_type VARCHAR(100),  -- 'FileNotFound', 'MemoryError', etc.
    error_message TEXT,
    stack_trace TEXT,

    -- Context
    tool_name VARCHAR(100),
    function_name VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Environment
    app_version VARCHAR(20),
    os_info VARCHAR(100),
    python_version VARCHAR(20),

    -- Additional Info
    metadata JSONB,

    INDEX idx_errors_timestamp (timestamp),
    INDEX idx_errors_type (error_type),
    INDEX idx_errors_tool (tool_name)
);

-- ============================================
-- TABLE: app_versions
-- Purpose: Track application versions and updates
-- ============================================
CREATE TABLE app_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) UNIQUE NOT NULL,  -- '1.0.0', '1.1.0', etc.
    release_date TIMESTAMP NOT NULL,
    is_latest BOOLEAN DEFAULT FALSE,
    is_mandatory BOOLEAN DEFAULT FALSE,  -- Force update?

    -- Release Info
    changelog TEXT,
    download_url VARCHAR(500),
    file_size_mb FLOAT,

    -- Deployment Stats
    total_downloads INTEGER DEFAULT 0,
    active_installations INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_versions_latest (is_latest),
    INDEX idx_versions_release_date (release_date)
);

-- ============================================
-- TABLE: update_history
-- Purpose: Track when users update their app
-- ============================================
CREATE TABLE update_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(session_id) ON DELETE SET NULL,

    from_version VARCHAR(20),
    to_version VARCHAR(20),

    update_started_at TIMESTAMP,
    update_completed_at TIMESTAMP,
    status VARCHAR(20),  -- 'completed', 'failed', 'in_progress'

    INDEX idx_updates_user (user_id),
    INDEX idx_updates_version (to_version)
);

-- ============================================
-- TABLE: performance_metrics
-- Purpose: Detailed performance tracking over time
-- ============================================
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    log_entry_id INTEGER REFERENCES log_entries(id) ON DELETE CASCADE,

    -- System Metrics
    cpu_percent FLOAT,
    memory_mb FLOAT,
    disk_io_mb FLOAT,

    -- Processing Metrics
    embedding_time_seconds FLOAT,  -- For ML operations
    file_read_time_seconds FLOAT,
    file_write_time_seconds FLOAT,

    -- Model-specific
    model_load_time_seconds FLOAT,
    inference_time_seconds FLOAT,

    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_perf_log_entry (log_entry_id)
);

-- ============================================
-- TABLE: user_activity_summary
-- Purpose: Daily active user tracking
-- ============================================
CREATE TABLE user_activity_summary (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,

    -- Activity Metrics
    total_operations INTEGER DEFAULT 0,
    total_duration_seconds FLOAT DEFAULT 0,
    tools_used VARCHAR(255)[],  -- Array of tool names used

    -- Session Info
    total_sessions INTEGER DEFAULT 0,
    total_session_time_seconds FLOAT DEFAULT 0,

    first_activity_time TIMESTAMP,
    last_activity_time TIMESTAMP,

    UNIQUE (user_id, date),
    INDEX idx_activity_date (date),
    INDEX idx_activity_user (user_id)
);

-- ============================================
-- TABLE: announcements
-- Purpose: Push notifications/announcements to users
-- ============================================
CREATE TABLE announcements (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'info',  -- 'info', 'warning', 'update', 'maintenance'

    -- Targeting
    target_users INTEGER[],  -- Specific user IDs, NULL = all users
    min_version VARCHAR(20),  -- Only show to users on version X+

    -- Display Rules
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,  -- Higher = more important

    -- Timing
    display_from TIMESTAMP,
    display_until TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),

    INDEX idx_announcements_active (is_active),
    INDEX idx_announcements_dates (display_from, display_until)
);

-- ============================================
-- TABLE: user_feedback
-- Purpose: Collect user feedback and feature requests
-- ============================================
CREATE TABLE user_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,

    feedback_type VARCHAR(50),  -- 'bug', 'feature_request', 'improvement', 'other'
    title VARCHAR(200),
    description TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),

    -- Context
    tool_name VARCHAR(100),
    function_name VARCHAR(100),
    app_version VARCHAR(20),

    -- Status
    status VARCHAR(50) DEFAULT 'open',  -- 'open', 'in_progress', 'resolved', 'closed'
    admin_response TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,

    INDEX idx_feedback_user (user_id),
    INDEX idx_feedback_type (feedback_type),
    INDEX idx_feedback_status (status)
);

-- ============================================
-- VIEWS: Pre-computed queries for dashboard
-- ============================================

-- Real-time active users
CREATE OR REPLACE VIEW active_users_now AS
SELECT
    COUNT(DISTINCT user_id) as active_users,
    COUNT(DISTINCT session_id) as active_sessions
FROM sessions
WHERE is_active = TRUE
AND started_at >= NOW() - INTERVAL '30 minutes';

-- Today's statistics
CREATE OR REPLACE VIEW today_stats AS
SELECT
    COUNT(*) as total_operations,
    COUNT(DISTINCT user_id) as unique_users,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_operations,
    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed_operations,
    AVG(duration_seconds) as avg_duration,
    SUM(rows_processed) as total_rows_processed
FROM log_entries
WHERE DATE(timestamp_start) = CURRENT_DATE;

-- Most used tools (last 7 days)
CREATE OR REPLACE VIEW popular_tools_week AS
SELECT
    tool_name,
    COUNT(*) as usage_count,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(duration_seconds) as avg_duration
FROM log_entries
WHERE timestamp_start >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY tool_name
ORDER BY usage_count DESC;

-- Most used functions (last 7 days)
CREATE OR REPLACE VIEW popular_functions_week AS
SELECT
    tool_name,
    function_name,
    COUNT(*) as usage_count,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(duration_seconds) as avg_duration
FROM log_entries
WHERE timestamp_start >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY tool_name, function_name
ORDER BY usage_count DESC;

-- User leaderboard (most active users this month)
CREATE OR REPLACE VIEW user_leaderboard_month AS
SELECT
    u.username,
    u.display_name,
    u.department,
    COUNT(l.id) as total_operations,
    SUM(l.duration_seconds) as total_time_seconds,
    COUNT(DISTINCT DATE(l.timestamp_start)) as active_days
FROM users u
JOIN log_entries l ON u.id = l.user_id
WHERE l.timestamp_start >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY u.id, u.username, u.display_name, u.department
ORDER BY total_operations DESC
LIMIT 20;

-- Error rate by tool
CREATE OR REPLACE VIEW error_rate_by_tool AS
SELECT
    tool_name,
    COUNT(*) as total_executions,
    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
    ROUND(100.0 * SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) / COUNT(*), 2) as error_rate_percent
FROM log_entries
WHERE timestamp_start >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY tool_name
ORDER BY error_rate_percent DESC;

-- ============================================
-- FUNCTIONS: Utility functions
-- ============================================

-- Function to update aggregated statistics (run daily via cron)
CREATE OR REPLACE FUNCTION update_daily_stats()
RETURNS void AS $$
BEGIN
    -- Update tool usage stats
    INSERT INTO tool_usage_stats (
        tool_name, date, total_uses, unique_users,
        successful_uses, failed_uses, avg_duration_seconds,
        avg_file_size_mb, avg_rows_processed,
        total_rows_processed, total_files_processed
    )
    SELECT
        tool_name,
        DATE(timestamp_start) as date,
        COUNT(*) as total_uses,
        COUNT(DISTINCT user_id) as unique_users,
        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_uses,
        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed_uses,
        AVG(duration_seconds) as avg_duration_seconds,
        AVG(file_size_mb) as avg_file_size_mb,
        AVG(rows_processed) as avg_rows_processed,
        SUM(rows_processed) as total_rows_processed,
        COUNT(DISTINCT file_name) as total_files_processed
    FROM log_entries
    WHERE DATE(timestamp_start) = CURRENT_DATE - INTERVAL '1 day'
    GROUP BY tool_name, DATE(timestamp_start)
    ON CONFLICT (tool_name, date) DO UPDATE SET
        total_uses = EXCLUDED.total_uses,
        unique_users = EXCLUDED.unique_users,
        successful_uses = EXCLUDED.successful_uses,
        failed_uses = EXCLUDED.failed_uses,
        avg_duration_seconds = EXCLUDED.avg_duration_seconds,
        avg_file_size_mb = EXCLUDED.avg_file_size_mb,
        avg_rows_processed = EXCLUDED.avg_rows_processed,
        total_rows_processed = EXCLUDED.total_rows_processed,
        total_files_processed = EXCLUDED.total_files_processed;

    -- Update function usage stats
    INSERT INTO function_usage_stats (
        tool_name, function_name, date, total_uses, unique_users,
        successful_uses, failed_uses, avg_duration_seconds,
        min_duration_seconds, max_duration_seconds
    )
    SELECT
        tool_name,
        function_name,
        DATE(timestamp_start) as date,
        COUNT(*) as total_uses,
        COUNT(DISTINCT user_id) as unique_users,
        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_uses,
        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed_uses,
        AVG(duration_seconds) as avg_duration_seconds,
        MIN(duration_seconds) as min_duration_seconds,
        MAX(duration_seconds) as max_duration_seconds
    FROM log_entries
    WHERE DATE(timestamp_start) = CURRENT_DATE - INTERVAL '1 day'
    GROUP BY tool_name, function_name, DATE(timestamp_start)
    ON CONFLICT (tool_name, function_name, date) DO UPDATE SET
        total_uses = EXCLUDED.total_uses,
        unique_users = EXCLUDED.unique_users,
        successful_uses = EXCLUDED.successful_uses,
        failed_uses = EXCLUDED.failed_uses,
        avg_duration_seconds = EXCLUDED.avg_duration_seconds,
        min_duration_seconds = EXCLUDED.min_duration_seconds,
        max_duration_seconds = EXCLUDED.max_duration_seconds;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- INDEXES: Additional composite indexes for common queries
-- ============================================

CREATE INDEX idx_logs_user_tool_date ON log_entries(user_id, tool_name, DATE(timestamp_start));
CREATE INDEX idx_logs_tool_status_date ON log_entries(tool_name, status, DATE(timestamp_start));
CREATE INDEX idx_sessions_user_active ON sessions(user_id, is_active);

-- ============================================
-- INITIAL DATA: Create default admin user
-- ============================================

-- Default admin user (password: 'admin123' - CHANGE THIS!)
-- Password hash generated with bcrypt
INSERT INTO users (username, email, password_hash, display_name, role, is_active)
VALUES (
    'admin',
    'admin@company.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYT5Z8K0u',  -- 'admin123'
    'System Administrator',
    'admin',
    TRUE
);

-- Insert initial app version
INSERT INTO app_versions (version, release_date, is_latest, changelog, download_url)
VALUES (
    '1.0.0',
    CURRENT_TIMESTAMP,
    TRUE,
    'Initial release',
    'https://your-server.com/downloads/LocalizationTools-1.0.0.exe'
);

-- ============================================
-- COMMENTS: Document the schema
-- ============================================

COMMENT ON TABLE users IS 'User accounts and authentication';
COMMENT ON TABLE sessions IS 'Active and historical user sessions';
COMMENT ON TABLE log_entries IS 'Main usage log - every tool execution is recorded here';
COMMENT ON TABLE tool_usage_stats IS 'Aggregated statistics per tool (daily)';
COMMENT ON TABLE function_usage_stats IS 'Aggregated statistics per function (daily)';
COMMENT ON TABLE error_logs IS 'Detailed error tracking for debugging';
COMMENT ON TABLE app_versions IS 'Application version management';
COMMENT ON TABLE update_history IS 'Track user update history';
COMMENT ON TABLE performance_metrics IS 'Detailed performance metrics for optimization';
COMMENT ON TABLE user_activity_summary IS 'Daily user activity summary';
COMMENT ON TABLE announcements IS 'Push notifications to users';
COMMENT ON TABLE user_feedback IS 'User feedback and feature requests';

-- ============================================
-- PERMISSIONS: Set up roles (optional)
-- ============================================

-- Create read-only role for dashboard viewers
-- CREATE ROLE dashboard_viewer WITH LOGIN PASSWORD 'viewer_password';
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO dashboard_viewer;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO dashboard_viewer;

-- Create app role for the application
-- CREATE ROLE app_user WITH LOGIN PASSWORD 'app_password';
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
