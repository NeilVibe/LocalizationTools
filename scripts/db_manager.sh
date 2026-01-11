#!/bin/bash
#
# DB Manager Shell Wrapper
# ========================
# Comprehensive database management for LocaNext
# Supports both SQLite (offline) and PostgreSQL (online)
#
# Usage: ./scripts/db_manager.sh <command> [options]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVER_DATA="$PROJECT_ROOT/server/data"
BACKUP_DIR="$SERVER_DATA/backups"
SQLITE_HOME="$HOME/.local/share/locanext"
SQLITE_DB="$SQLITE_HOME/offline.db"
SQLITE_SERVER="$SERVER_DATA/offline.db"

# PostgreSQL settings (from config)
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_DB="${PG_DB:-localizationtools}"
PG_USER="${PG_USER:-localization_admin}"
PG_PASSWORD="${PG_PASSWORD:-locanext_dev_2025}"

# ============================================
# Helper Functions
# ============================================

print_header() {
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}  LocaNext DB Manager${NC}"
    echo -e "${CYAN}============================================${NC}"
    echo ""
}

print_section() {
    echo -e "\n${BLUE}[$1]${NC}"
}

ok() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

err() {
    echo -e "${RED}[ERROR]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

confirm() {
    read -p "$1 [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

get_timestamp() {
    date +"%Y%m%d_%H%M%S"
}

ensure_backup_dir() {
    mkdir -p "$BACKUP_DIR"
}

# ============================================
# SQLite Operations
# ============================================

sqlite_status() {
    print_section "SQLite Status"

    echo "Home DB: $SQLITE_HOME/offline.db"
    if [[ -f "$SQLITE_DB" ]]; then
        local size=$(du -h "$SQLITE_DB" 2>/dev/null | cut -f1)
        local tables=$(python3 -c "import sqlite3; c=sqlite3.connect('$SQLITE_DB'); print(len(c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()))" 2>/dev/null || echo "0")
        ok "Exists | Size: $size | Tables: $tables"

        # Show table counts
        if [[ "$1" == "-v" ]]; then
            echo ""
            python3 -c "
import sqlite3
conn = sqlite3.connect('$SQLITE_DB')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name\").fetchall()
for (table,) in tables:
    try:
        count = conn.execute(f'SELECT COUNT(*) FROM \"{table}\"').fetchone()[0]
        print(f'  {table:35} {count} rows')
    except:
        print(f'  {table:35} ? rows')
conn.close()
" 2>/dev/null
        fi
    else
        warn "Not found"
    fi

    echo ""
    echo "Server DB: $SQLITE_SERVER"
    if [[ -f "$SQLITE_SERVER" ]]; then
        local size=$(du -h "$SQLITE_SERVER" 2>/dev/null | cut -f1)
        local tables=$(python3 -c "import sqlite3; c=sqlite3.connect('$SQLITE_SERVER'); print(len(c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()))" 2>/dev/null || echo "0")
        ok "Exists | Size: $size | Tables: $tables"
    else
        warn "Not found"
    fi
}

sqlite_backup() {
    print_section "SQLite Backup"
    ensure_backup_dir

    local timestamp=$(get_timestamp)
    local backup_subdir="$BACKUP_DIR/sqlite_$timestamp"
    mkdir -p "$backup_subdir"

    if [[ -f "$SQLITE_DB" ]]; then
        cp "$SQLITE_DB" "$backup_subdir/offline_home.db"
        ok "Home DB backed up to $backup_subdir/offline_home.db"
    else
        warn "Home DB not found, skipping"
    fi

    if [[ -f "$SQLITE_SERVER" ]]; then
        cp "$SQLITE_SERVER" "$backup_subdir/offline_server.db"
        ok "Server DB backed up to $backup_subdir/offline_server.db"
    else
        warn "Server DB not found, skipping"
    fi

    echo ""
    ok "Backup complete: $backup_subdir"
}

sqlite_reset() {
    print_section "SQLite Reset"

    if ! confirm "This will DELETE all SQLite offline databases. Continue?"; then
        warn "Aborted"
        return 1
    fi

    # Backup first
    sqlite_backup

    # Remove databases
    if [[ -f "$SQLITE_DB" ]]; then
        rm -f "$SQLITE_DB"
        ok "Removed: $SQLITE_DB"
    fi

    if [[ -f "$SQLITE_SERVER" ]]; then
        rm -f "$SQLITE_SERVER"
        ok "Removed: $SQLITE_SERVER"
    fi

    echo ""
    info "Databases will be recreated on next access"
    info "Run: python3 -c \"from server.database.offline import get_offline_db; get_offline_db()\""
}

sqlite_reinit() {
    print_section "SQLite Re-initialize"

    info "Force re-initializing SQLite databases..."

    python3 -c "
from server.database.offline import get_offline_db
from server.database import offline
import os

# Reset singleton
offline._offline_db = None

# Remove existing files
home_db = '$SQLITE_DB'
server_db = '$SQLITE_SERVER'

if os.path.exists(home_db):
    os.remove(home_db)
    print(f'Removed: {home_db}')

if os.path.exists(server_db):
    os.remove(server_db)
    print(f'Removed: {server_db}')

# Re-create
db = get_offline_db()
print(f'Created: {db.db_path}')
print(f'Size: {os.path.getsize(db.db_path)} bytes')

# Verify tables
import sqlite3
conn = sqlite3.connect(db.db_path)
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print(f'Tables: {len(tables)}')
for t in sorted(tables):
    print(f'  - {t[0]}')
conn.close()
"

    ok "SQLite databases re-initialized"
}

sqlite_analyze() {
    print_section "SQLite Analysis"

    local db_path="${1:-$SQLITE_DB}"

    if [[ ! -f "$db_path" ]]; then
        err "Database not found: $db_path"
        return 1
    fi

    echo "Database: $db_path"
    echo "Size: $(du -h "$db_path" | cut -f1)"
    echo ""

    python3 -c "
import sqlite3
conn = sqlite3.connect('$db_path')
conn.row_factory = sqlite3.Row

print('Tables:')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name\").fetchall()
for (table,) in tables:
    try:
        count = conn.execute(f'SELECT COUNT(*) FROM \"{table}\"').fetchone()[0]
        print(f'  {table:35} {count} rows')
    except Exception as e:
        print(f'  {table:35} error: {e}')

print()
print('Offline Storage Platform/Project:')
try:
    platform = conn.execute('SELECT id, name FROM offline_platforms WHERE id = -1').fetchone()
    if platform:
        print(f'  Platform: id={platform[0]}, name={platform[1]}')
    project = conn.execute('SELECT id, name FROM offline_projects WHERE id = -1').fetchone()
    if project:
        print(f'  Project: id={project[0]}, name={project[1]}')
except:
    print('  (not initialized)')

print()
print('Sync Subscriptions:')
try:
    subs = conn.execute('SELECT entity_type, entity_name, sync_status FROM sync_subscriptions LIMIT 10').fetchall()
    if subs:
        for s in subs:
            print(f'  {s[0]:10} {s[1]:30} {s[2]}')
    else:
        print('  (none)')
except:
    print('  (table not found)')

print()
print('Local Files:')
try:
    files = conn.execute('SELECT id, name, format FROM offline_files LIMIT 10').fetchall()
    if files:
        for f in files:
            print(f'  {f[0]:5} {f[1]:35} {f[2]}')
    else:
        print('  (none)')
except:
    print('  (table not found)')

print()
print('Local Folders:')
try:
    folders = conn.execute('SELECT id, name, parent_id FROM offline_folders LIMIT 10').fetchall()
    if folders:
        for f in folders:
            print(f'  {f[0]:5} {f[1]:35} parent={f[2]}')
    else:
        print('  (none)')
except:
    print('  (table not found)')

conn.close()
"
}

sqlite_query() {
    local db_path="${1:-$SQLITE_DB}"
    local query="$2"

    # If only one arg, it's the query, use default db
    if [[ -z "$query" ]]; then
        query="$db_path"
        db_path="$SQLITE_DB"
    fi

    if [[ -z "$query" ]]; then
        err "Usage: db_manager.sh sqlite-query \"SQL query\""
        err "       db_manager.sh sqlite-query /path/to/db.db \"SQL query\""
        return 1
    fi

    if [[ ! -f "$db_path" ]]; then
        err "Database not found: $db_path"
        return 1
    fi

    python3 -c "
import sqlite3
conn = sqlite3.connect('$db_path')
conn.row_factory = sqlite3.Row
try:
    cursor = conn.execute('''$query''')
    rows = cursor.fetchall()
    if rows:
        # Print header
        cols = [d[0] for d in cursor.description]
        print(' | '.join(cols))
        print('-' * (len(' | '.join(cols)) + 5))
        # Print rows
        for row in rows:
            print(' | '.join(str(v) for v in row))
        print(f'\\n({len(rows)} rows)')
    else:
        print('(0 rows)')
except Exception as e:
    print(f'Error: {e}')
conn.close()
"
}

# ============================================
# PostgreSQL Operations
# ============================================

pg_status() {
    print_section "PostgreSQL Status"

    echo "Connection: $PG_USER@$PG_HOST:$PG_PORT/$PG_DB"

    if pg_isready -h "$PG_HOST" -p "$PG_PORT" > /dev/null 2>&1; then
        ok "PostgreSQL is running"

        # Get database info
        PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -c "
            SELECT 'Size: ' || pg_size_pretty(pg_database_size('$PG_DB'));
        " 2>/dev/null | head -1

        if [[ "$1" == "-v" ]]; then
            echo ""
            echo "Tables:"
            PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -c "
                SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
            " 2>/dev/null | while read table; do
                if [[ -n "$table" ]]; then
                    count=$(PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -c "SELECT COUNT(*) FROM \"$table\";" 2>/dev/null | tr -d ' ')
                    printf "  %-35s %s rows\n" "$table" "$count"
                fi
            done
        fi
    else
        err "PostgreSQL is not running"
    fi
}

pg_backup() {
    print_section "PostgreSQL Backup"
    ensure_backup_dir

    local timestamp=$(get_timestamp)
    local backup_file="$BACKUP_DIR/pg_backup_$timestamp.sql"

    info "Creating backup: $backup_file"

    PGPASSWORD="$PG_PASSWORD" pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" "$PG_DB" > "$backup_file"

    local size=$(du -h "$backup_file" | cut -f1)
    ok "Backup complete: $backup_file ($size)"
}

pg_analyze() {
    print_section "PostgreSQL Analysis"

    if ! pg_isready -h "$PG_HOST" -p "$PG_PORT" > /dev/null 2>&1; then
        err "PostgreSQL is not running"
        return 1
    fi

    echo "Database: $PG_DB"

    PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -c "
        SELECT 'Size: ' || pg_size_pretty(pg_database_size('$PG_DB')) as info;
    " 2>/dev/null

    echo ""
    echo "Table Row Counts:"
    PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -c "
        SELECT
            schemaname || '.' || relname as table_name,
            n_live_tup as row_count
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        ORDER BY n_live_tup DESC
        LIMIT 20;
    " 2>/dev/null

    echo ""
    echo "LDM Statistics:"
    PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -c "
        SELECT 'Platforms' as entity, COUNT(*) as count FROM ldm_platforms
        UNION ALL
        SELECT 'Projects', COUNT(*) FROM ldm_projects
        UNION ALL
        SELECT 'Folders', COUNT(*) FROM ldm_folders
        UNION ALL
        SELECT 'Files', COUNT(*) FROM ldm_files
        UNION ALL
        SELECT 'Rows', COUNT(*) FROM ldm_rows
        UNION ALL
        SELECT 'TMs', COUNT(*) FROM ldm_translation_memories
        UNION ALL
        SELECT 'TM Entries', COUNT(*) FROM ldm_tm_entries
        UNION ALL
        SELECT 'Users', COUNT(*) FROM users;
    " 2>/dev/null
}

pg_query() {
    local query="$1"

    if [[ -z "$query" ]]; then
        err "Usage: db_manager.sh pg-query \"SQL query\""
        return 1
    fi

    PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -c "$query"
}

pg_reset_ldm() {
    print_section "PostgreSQL LDM Reset"

    warn "This will DELETE all LDM data (platforms, projects, files, TMs)"
    warn "Users and sessions will be preserved"

    if ! confirm "Are you absolutely sure?"; then
        warn "Aborted"
        return 1
    fi

    # Backup first
    pg_backup

    info "Truncating LDM tables..."

    PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -c "
        TRUNCATE TABLE
            ldm_tm_assignments,
            ldm_active_tms,
            ldm_tm_entries,
            ldm_tm_indexes,
            ldm_translation_memories,
            ldm_qa_results,
            ldm_edit_history,
            ldm_rows,
            ldm_files,
            ldm_folders,
            ldm_projects,
            ldm_platforms,
            ldm_trash,
            ldm_backups
        CASCADE;
    " 2>/dev/null

    ok "LDM tables truncated"
}

# ============================================
# Combined Operations
# ============================================

full_status() {
    print_header
    sqlite_status "$1"
    echo ""
    pg_status "$1"
}

full_backup() {
    print_header
    sqlite_backup
    echo ""
    pg_backup
}

full_reset() {
    print_header

    warn "This will reset BOTH SQLite and PostgreSQL LDM data!"

    if ! confirm "Are you absolutely sure?"; then
        warn "Aborted"
        return 1
    fi

    sqlite_reset
    echo ""
    pg_reset_ldm

    echo ""
    ok "Full reset complete"
}

# ============================================
# List Backups
# ============================================

list_backups() {
    print_section "Available Backups"

    if [[ ! -d "$BACKUP_DIR" ]]; then
        warn "No backups directory found"
        return
    fi

    echo "Location: $BACKUP_DIR"
    echo ""

    # SQLite backups
    echo "SQLite Backups:"
    ls -lt "$BACKUP_DIR"/sqlite_* 2>/dev/null | head -10 || echo "  (none)"

    echo ""

    # PostgreSQL backups
    echo "PostgreSQL Backups:"
    ls -lh "$BACKUP_DIR"/pg_backup_*.sql 2>/dev/null | head -10 || echo "  (none)"
}

# ============================================
# Help
# ============================================

show_help() {
    print_header
    echo "Usage: ./scripts/db_manager.sh <command> [options]"
    echo ""
    echo -e "${CYAN}General Commands:${NC}"
    echo "  status [-v]        Show status of all databases"
    echo "  backup             Backup all databases"
    echo "  list-backups       List available backups"
    echo ""
    echo -e "${CYAN}SQLite Commands:${NC}"
    echo "  sqlite-status [-v] Show SQLite database status"
    echo "  sqlite-backup      Backup SQLite databases"
    echo "  sqlite-reset       Delete and reset SQLite databases"
    echo "  sqlite-reinit      Force re-initialize SQLite (fresh)"
    echo "  sqlite-analyze     Analyze SQLite database contents"
    echo "  sqlite-query       Run SQL query on SQLite"
    echo ""
    echo -e "${CYAN}PostgreSQL Commands:${NC}"
    echo "  pg-status [-v]     Show PostgreSQL status"
    echo "  pg-backup          Backup PostgreSQL database"
    echo "  pg-analyze         Analyze PostgreSQL database"
    echo "  pg-query \"SQL\"     Run SQL query on PostgreSQL"
    echo "  pg-reset-ldm       Reset LDM tables (keeps users)"
    echo ""
    echo -e "${CYAN}Combined Commands:${NC}"
    echo "  full-reset         Reset both SQLite and PostgreSQL LDM data"
    echo ""
    echo -e "${CYAN}Examples:${NC}"
    echo "  ./scripts/db_manager.sh status -v"
    echo "  ./scripts/db_manager.sh sqlite-reinit"
    echo "  ./scripts/db_manager.sh sqlite-query \"SELECT * FROM offline_files\""
    echo "  ./scripts/db_manager.sh pg-analyze"
    echo ""
}

# ============================================
# Main
# ============================================

case "${1:-}" in
    # General
    status)
        full_status "$2"
        ;;
    backup)
        full_backup
        ;;
    list-backups)
        list_backups
        ;;
    full-reset)
        full_reset
        ;;

    # SQLite
    sqlite-status)
        sqlite_status "$2"
        ;;
    sqlite-backup)
        sqlite_backup
        ;;
    sqlite-reset)
        sqlite_reset
        ;;
    sqlite-reinit)
        sqlite_reinit
        ;;
    sqlite-analyze)
        sqlite_analyze "$2"
        ;;
    sqlite-query)
        sqlite_query "$2" "$3"
        ;;

    # PostgreSQL
    pg-status)
        pg_status "$2"
        ;;
    pg-backup)
        pg_backup
        ;;
    pg-analyze)
        pg_analyze
        ;;
    pg-query)
        pg_query "$2"
        ;;
    pg-reset-ldm)
        pg_reset_ldm
        ;;

    # Help
    help|--help|-h|"")
        show_help
        ;;

    *)
        err "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
