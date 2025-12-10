"""
Admin Database Statistics API

Provides database performance metrics for monitoring:
- Connection count and pool status
- Query performance stats
- Table sizes and row counts
- PostgreSQL configuration status
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime

from server.utils.dependencies import get_db
from server.utils.auth import require_admin

router = APIRouter(prefix="/api/v2/admin/db", tags=["Admin Database"])


@router.get("/stats", dependencies=[Depends(require_admin)])
async def get_db_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get database performance statistics.

    Returns connection pool status, query stats, and configuration.
    Requires admin authentication.
    """
    stats = {
        "timestamp": datetime.utcnow().isoformat(),
        "database_type": "unknown",
        "connection_pool": {},
        "performance": {},
        "tables": {},
        "configuration": {}
    }

    try:
        # Detect database type
        dialect = db.bind.dialect.name
        stats["database_type"] = dialect

        if dialect == "postgresql":
            stats.update(await _get_postgresql_stats(db))
        elif dialect == "sqlite":
            stats.update(_get_sqlite_stats(db))

    except Exception as e:
        logger.error(f"Error getting DB stats: {e}")
        stats["error"] = str(e)

    return stats


async def _get_postgresql_stats(db: Session) -> Dict[str, Any]:
    """Get PostgreSQL-specific statistics."""
    stats = {
        "connection_pool": {},
        "performance": {},
        "tables": {},
        "configuration": {}
    }

    try:
        # Connection stats
        result = db.execute(text("""
            SELECT
                numbackends as active_connections,
                xact_commit as commits,
                xact_rollback as rollbacks,
                blks_read as blocks_read,
                blks_hit as blocks_hit,
                tup_returned as rows_returned,
                tup_fetched as rows_fetched,
                tup_inserted as rows_inserted,
                tup_updated as rows_updated,
                tup_deleted as rows_deleted
            FROM pg_stat_database
            WHERE datname = current_database()
        """)).fetchone()

        if result:
            stats["connection_pool"] = {
                "active_connections": result.active_connections
            }

            # Calculate cache hit ratio
            total_blocks = (result.blocks_read or 0) + (result.blocks_hit or 0)
            cache_hit_ratio = 0
            if total_blocks > 0:
                cache_hit_ratio = round((result.blocks_hit / total_blocks) * 100, 2)

            stats["performance"] = {
                "commits": result.commits,
                "rollbacks": result.rollbacks,
                "cache_hit_ratio_percent": cache_hit_ratio,
                "rows_returned": result.rows_returned,
                "rows_fetched": result.rows_fetched,
                "rows_inserted": result.rows_inserted,
                "rows_updated": result.rows_updated,
                "rows_deleted": result.rows_deleted
            }

        # Max connections
        max_conn = db.execute(text("SHOW max_connections")).scalar()
        stats["connection_pool"]["max_connections"] = int(max_conn)

        # Key configuration values
        config_params = [
            "shared_buffers",
            "effective_cache_size",
            "work_mem",
            "maintenance_work_mem",
            "max_parallel_workers",
            "random_page_cost"
        ]

        for param in config_params:
            try:
                value = db.execute(text(f"SHOW {param}")).scalar()
                stats["configuration"][param] = value
            except:
                pass

        # Table sizes (main tables only)
        tables_result = db.execute(text("""
            SELECT
                relname as table_name,
                n_live_tup as row_count,
                pg_size_pretty(pg_total_relation_size(relid)) as total_size
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY n_live_tup DESC
            LIMIT 10
        """)).fetchall()

        stats["tables"] = {
            row.table_name: {
                "row_count": row.row_count,
                "total_size": row.total_size
            }
            for row in tables_result
        }

        # Slow query count (if pg_stat_statements available)
        try:
            slow_queries = db.execute(text("""
                SELECT COUNT(*) as count
                FROM pg_stat_statements
                WHERE mean_exec_time > 1000
            """)).scalar()
            stats["performance"]["slow_queries_count"] = slow_queries
        except:
            pass  # pg_stat_statements not installed

    except Exception as e:
        logger.error(f"Error getting PostgreSQL stats: {e}")
        stats["error"] = str(e)

    return stats


def _get_sqlite_stats(db: Session) -> Dict[str, Any]:
    """Get SQLite statistics (limited compared to PostgreSQL)."""
    stats = {
        "connection_pool": {
            "note": "SQLite uses file-based locking, not connection pooling"
        },
        "performance": {},
        "tables": {},
        "configuration": {
            "note": "SQLite - development mode only"
        }
    }

    try:
        # Get table row counts
        tables_result = db.execute(text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)).fetchall()

        for row in tables_result:
            table_name = row[0]
            count = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            stats["tables"][table_name] = {
                "row_count": count
            }

    except Exception as e:
        logger.error(f"Error getting SQLite stats: {e}")
        stats["error"] = str(e)

    return stats


@router.get("/health", dependencies=[Depends(require_admin)])
async def get_db_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Quick database health check with performance assessment.

    Returns:
    - status: healthy/warning/critical
    - issues: List of detected issues
    - recommendations: Suggested fixes
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "issues": [],
        "recommendations": []
    }

    try:
        dialect = db.bind.dialect.name

        if dialect != "postgresql":
            health["status"] = "warning"
            health["issues"].append("Using SQLite - not recommended for production")
            health["recommendations"].append("Migrate to PostgreSQL for 100+ users")
            return health

        # Check cache hit ratio
        result = db.execute(text("""
            SELECT blks_read, blks_hit
            FROM pg_stat_database
            WHERE datname = current_database()
        """)).fetchone()

        if result:
            total = (result.blks_read or 0) + (result.blks_hit or 0)
            if total > 0:
                cache_hit_ratio = (result.blks_hit / total) * 100
                if cache_hit_ratio < 90:
                    health["status"] = "warning"
                    health["issues"].append(f"Cache hit ratio is {cache_hit_ratio:.1f}% (should be >90%)")
                    health["recommendations"].append("Increase shared_buffers or add more RAM")

        # Check connection count
        active = db.execute(text("""
            SELECT numbackends FROM pg_stat_database WHERE datname = current_database()
        """)).scalar()
        max_conn = int(db.execute(text("SHOW max_connections")).scalar())

        connection_usage = (active / max_conn) * 100
        if connection_usage > 80:
            health["status"] = "warning"
            health["issues"].append(f"Connection usage at {connection_usage:.1f}% ({active}/{max_conn})")
            health["recommendations"].append("Consider using PgBouncer for connection pooling")

        # Check for bloated tables
        bloat_result = db.execute(text("""
            SELECT relname, n_dead_tup
            FROM pg_stat_user_tables
            WHERE n_dead_tup > 10000
            ORDER BY n_dead_tup DESC
            LIMIT 3
        """)).fetchall()

        for row in bloat_result:
            health["issues"].append(f"Table '{row.relname}' has {row.n_dead_tup} dead tuples")
            health["recommendations"].append(f"Run VACUUM ANALYZE on {row.relname}")

        if not health["issues"]:
            health["status"] = "healthy"
            health["message"] = "Database is performing well"

    except Exception as e:
        health["status"] = "critical"
        health["issues"].append(f"Health check failed: {str(e)}")

    return health
