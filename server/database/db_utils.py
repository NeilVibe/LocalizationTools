"""
Database Utilities - High-Performance Operations

Optimized database operations for LocaNext:
- COPY TEXT bulk inserts (3-5x faster than INSERT) - PostgreSQL
- INSERT fallback for SQLite
- Full-Text Search (FTS) using PostgreSQL tsvector / SQLite LIKE
- Query optimization helpers

P21 Database Powerhouse - COPY TEXT Implementation
- Uses COPY FROM STDIN (psycopg2.copy_from) on PostgreSQL
- Falls back to batch INSERT on SQLite

P33 Offline Mode - SQLite Support
- Automatic detection of database type
- SQLite-compatible fallbacks for all operations
"""

import hashlib
from io import StringIO
from typing import Any, Callable, Generator, List, Optional, Tuple, Type, TypeVar

from sqlalchemy import insert, text, func
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta
from loguru import logger

from server.database.models import Base, LDMTMEntry, LDMRow
from server import config

# Type variable for generic model operations
T = TypeVar('T', bound=Base)


# =============================================================================
# Database Detection
# =============================================================================

def is_postgresql(session_or_engine=None) -> bool:
    """
    Check if database is PostgreSQL.

    Uses config.ACTIVE_DATABASE_TYPE set during database setup.

    Args:
        session_or_engine: SQLAlchemy session or engine (ignored, kept for compatibility)

    Returns:
        True if PostgreSQL, False if SQLite
    """
    return config.ACTIVE_DATABASE_TYPE == "postgresql"


def is_sqlite(session_or_engine=None) -> bool:
    """
    Check if database is SQLite.

    Uses config.ACTIVE_DATABASE_TYPE set during database setup.

    Args:
        session_or_engine: SQLAlchemy session or engine (ignored, kept for compatibility)

    Returns:
        True if SQLite, False if PostgreSQL
    """
    return config.ACTIVE_DATABASE_TYPE == "sqlite"


# =============================================================================
# COPY TEXT - High-Performance Bulk Insert (PostgreSQL)
# =============================================================================

def escape_for_copy(value: Any) -> str:
    """
    Escape a value for PostgreSQL COPY TEXT format.

    Handles:
    - NULL values → \\N
    - Tabs → space (COPY uses tabs as delimiter)
    - Newlines → \\n (escaped newline)
    - Backslashes → \\\\ (escaped backslash)

    Args:
        value: Any value to escape

    Returns:
        Escaped string safe for COPY TEXT format
    """
    if value is None:
        return '\\N'

    s = str(value)

    # Escape in order: backslash first, then other special chars
    s = s.replace('\\', '\\\\')  # Backslash → \\
    s = s.replace('\t', ' ')      # Tab → space (delimiter conflict)
    s = s.replace('\n', '\\n')    # Newline → \n
    s = s.replace('\r', '\\r')    # Carriage return → \r

    return s


def bulk_copy(
    db: Session,
    table_name: str,
    columns: List[str],
    rows: List[Tuple],
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> int:
    """
    High-performance bulk insert.

    - PostgreSQL: Uses COPY FROM STDIN (3-5x faster than INSERT)
    - SQLite: Falls back to batch INSERT

    Args:
        db: SQLAlchemy database session
        table_name: Target table name (e.g., 'tm_entries')
        columns: List of column names in order
        rows: List of tuples, each tuple is one row
        progress_callback: Optional callback(inserted, total) for progress

    Returns:
        Number of rows inserted

    Example:
        >>> rows = [
        >>>     (1, 'Hello', 'World'),
        >>>     (2, 'Foo', 'Bar'),
        >>> ]
        >>> count = bulk_copy(db, 'my_table', ['id', 'col1', 'col2'], rows)
    """
    if not rows:
        return 0

    total = len(rows)

    # Use INSERT fallback for SQLite
    if is_sqlite():
        return _bulk_copy_sqlite(db, table_name, columns, rows, progress_callback)

    # PostgreSQL: Use COPY TEXT
    logger.info(f"COPY TEXT: Inserting {total:,} rows into {table_name}")

    try:
        # Build tab-separated text buffer
        buffer = StringIO()
        for row in rows:
            line = '\t'.join(escape_for_copy(v) for v in row)
            buffer.write(line + '\n')

        buffer.seek(0)

        # Get raw psycopg2 connection from SQLAlchemy
        raw_conn = db.connection().connection
        cursor = raw_conn.cursor()

        # Execute COPY
        cursor.copy_from(
            buffer,
            table_name,
            columns=columns,
            null='\\N'
        )

        # Commit
        db.commit()

        # Progress callback - report 100% at end
        if progress_callback:
            progress_callback(total, total)

        logger.success(f"COPY TEXT complete: {total:,} rows into {table_name}")
        return total

    except Exception as e:
        db.rollback()
        logger.error(f"COPY TEXT failed for {table_name}: {e}")
        raise


def _bulk_copy_sqlite(
    db: Session,
    table_name: str,
    columns: List[str],
    rows: List[Tuple],
    progress_callback: Optional[Callable[[int, int], None]] = None,
    batch_size: int = 1000
) -> int:
    """
    SQLite fallback for bulk_copy using batch INSERT.

    Args:
        db: SQLAlchemy database session
        table_name: Target table name
        columns: List of column names
        rows: List of tuples
        progress_callback: Optional callback for progress
        batch_size: Number of rows per batch

    Returns:
        Number of rows inserted
    """
    total = len(rows)
    inserted = 0

    logger.info(f"SQLite INSERT: Inserting {total:,} rows into {table_name}")

    try:
        # Build column string with named parameters
        cols_str = ', '.join(f'"{c}"' for c in columns)
        placeholders = ', '.join(f':{c}' for c in columns)
        stmt = text(f'INSERT INTO "{table_name}" ({cols_str}) VALUES ({placeholders})')

        for i in range(0, total, batch_size):
            batch = rows[i:i + batch_size]

            # Execute batch insert
            for row in batch:
                params = {columns[j]: row[j] for j in range(len(columns))}
                db.execute(stmt, params)

            inserted += len(batch)

            if progress_callback:
                progress_callback(inserted, total)

        db.commit()
        logger.success(f"SQLite INSERT complete: {inserted:,} rows into {table_name}")
        return inserted

    except Exception as e:
        db.rollback()
        logger.error(f"SQLite INSERT failed for {table_name}: {e}")
        raise


# =============================================================================
# Batch Insert Operations
# =============================================================================

def bulk_insert(
    db: Session,
    model: Type[T],
    records: List[dict],
    batch_size: int = 5000,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> int:
    """
    Bulk insert records into database using SQLAlchemy Core insert.

    10x+ faster than individual ORM inserts for large datasets.
    Uses batched commits to balance memory and performance.

    Args:
        db: Database session
        model: SQLAlchemy model class (e.g., LDMTMEntry)
        records: List of dictionaries with column values
        batch_size: Number of records per batch (default 5000)
        progress_callback: Optional callback(inserted, total) for progress updates

    Returns:
        Total number of records inserted

    Example:
        >>> entries = [
        >>>     {"tm_id": 1, "source_text": "Hello", "target_text": "안녕", "source_hash": "abc123..."},
        >>>     {"tm_id": 1, "source_text": "World", "target_text": "세계", "source_hash": "def456..."},
        >>> ]
        >>> count = bulk_insert(db, LDMTMEntry, entries)
        >>> print(f"Inserted {count} entries")
    """
    if not records:
        return 0

    total = len(records)
    inserted = 0

    logger.info(f"Bulk inserting {total} records into {model.__tablename__} (batch_size={batch_size})")

    try:
        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]

            # Use SQLAlchemy Core insert for speed
            stmt = insert(model)
            db.execute(stmt, batch)

            inserted += len(batch)

            # Progress callback
            if progress_callback:
                progress_callback(inserted, total)

            # Log progress every 10 batches
            if (i // batch_size) % 10 == 0:
                logger.debug(f"Progress: {inserted}/{total} ({100 * inserted / total:.1f}%)")

        # Commit all batches
        db.commit()
        logger.success(f"Bulk insert complete: {inserted} records into {model.__tablename__}")

        return inserted

    except Exception as e:
        db.rollback()
        logger.error(f"Bulk insert failed: {e}")
        raise


def bulk_insert_tm_entries(
    db: Session,
    tm_id: int,
    entries: List[dict],
    batch_size: int = 5000,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> int:
    """
    Optimized bulk insert for TM entries with auto hash generation.

    Args:
        db: Database session
        tm_id: Translation Memory ID
        entries: List of dicts with 'source_text' and 'target_text'
        batch_size: Records per batch
        progress_callback: Optional callback for progress

    Returns:
        Number of entries inserted

    Example:
        >>> entries = [
        >>>     {"source_text": "Hello", "target_text": "안녕"},
        >>>     {"source_text": "World", "target_text": "세계"},
        >>> ]
        >>> count = bulk_insert_tm_entries(db, tm_id=1, entries=entries)
    """
    # Prepare records with hashes
    prepared = []
    for entry in entries:
        source = entry.get('source_text', '')
        target = entry.get('target_text', '')

        # Generate SHA256 hash of normalized source text
        normalized_source = normalize_text_for_hash(source)
        source_hash = hashlib.sha256(normalized_source.encode('utf-8')).hexdigest()

        prepared.append({
            'tm_id': tm_id,
            'source_text': source,
            'target_text': target,
            'source_hash': source_hash,
            'created_by': entry.get('created_by'),
            'change_date': entry.get('change_date'),
        })

    return bulk_insert(db, LDMTMEntry, prepared, batch_size, progress_callback)


def bulk_insert_rows(
    db: Session,
    file_id: int,
    rows: List[dict],
    batch_size: int = 5000,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> int:
    """
    Optimized bulk insert for LDM rows (from file upload).

    Args:
        db: Database session
        file_id: LDM File ID
        rows: List of dicts with 'row_num', 'string_id', 'source', 'target'
        batch_size: Records per batch
        progress_callback: Optional callback for progress

    Returns:
        Number of rows inserted
    """
    # Prepare records
    prepared = []
    for row in rows:
        prepared.append({
            'file_id': file_id,
            'row_num': row.get('row_num', 0),
            'string_id': row.get('string_id'),
            'source': row.get('source'),
            'target': row.get('target'),
            'status': row.get('status', 'pending'),
        })

    return bulk_insert(db, LDMRow, prepared, batch_size, progress_callback)


# =============================================================================
# COPY TEXT Wrapper Functions (3-5x faster)
# =============================================================================

def bulk_copy_tm_entries(
    db: Session,
    tm_id: int,
    entries: List[dict],
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> int:
    """
    COPY TEXT bulk insert for TM entries (3-5x faster than INSERT).

    Uses PostgreSQL COPY FROM STDIN for maximum performance.

    Args:
        db: Database session
        tm_id: Translation Memory ID
        entries: List of dicts with 'source_text' and 'target_text'
        progress_callback: Optional callback for progress

    Returns:
        Number of entries inserted

    Example:
        >>> entries = [
        >>>     {"source_text": "Hello", "target_text": "안녕"},
        >>>     {"source_text": "World", "target_text": "세계"},
        >>> ]
        >>> count = bulk_copy_tm_entries(db, tm_id=1, entries=entries)
    """
    if not entries:
        return 0

    # Prepare rows as tuples with hashes
    rows = []
    for entry in entries:
        source = entry.get('source_text', '')
        target = entry.get('target_text', '')

        # Generate SHA256 hash of normalized source text
        normalized_source = normalize_text_for_hash(source)
        source_hash = hashlib.sha256(normalized_source.encode('utf-8')).hexdigest()

        rows.append((
            tm_id,
            source,
            target,
            source_hash,
            entry.get('created_by'),
            entry.get('change_date'),
        ))

    columns = ['tm_id', 'source_text', 'target_text', 'source_hash', 'created_by', 'change_date']

    return bulk_copy(db, 'ldm_tm_entries', columns, rows, progress_callback)


def bulk_copy_rows(
    db: Session,
    file_id: int,
    rows: List[dict],
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> int:
    """
    COPY TEXT bulk insert for LDM rows (3-5x faster than INSERT).

    Uses PostgreSQL COPY FROM STDIN for maximum performance.

    Args:
        db: Database session
        file_id: LDM File ID
        rows: List of dicts with 'row_num', 'string_id', 'source', 'target'
        progress_callback: Optional callback for progress

    Returns:
        Number of rows inserted

    Example:
        >>> rows = [
        >>>     {"row_num": 0, "string_id": "menu_01", "source": "게임", "target": "Game"},
        >>>     {"row_num": 1, "string_id": "menu_02", "source": "설정", "target": "Settings"},
        >>> ]
        >>> count = bulk_copy_rows(db, file_id=1, rows=rows)
    """
    if not rows:
        return 0

    # Prepare rows as tuples
    prepared = []
    for row in rows:
        prepared.append((
            file_id,
            row.get('row_num', 0),
            row.get('string_id'),
            row.get('source'),
            row.get('target'),
            row.get('status', 'pending'),
        ))

    columns = ['file_id', 'row_num', 'string_id', 'source', 'target', 'status']

    return bulk_copy(db, 'ldm_rows', columns, prepared, progress_callback)


# =============================================================================
# Text Normalization
# =============================================================================

def normalize_text_for_hash(text: str) -> str:
    """
    Normalize text for hash generation.

    - Strip leading/trailing whitespace
    - Normalize newlines to \\n
    - Remove excessive whitespace

    Args:
        text: Input text

    Returns:
        Normalized text for consistent hashing
    """
    if not text:
        return ''

    # Normalize newlines
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')

    # Strip whitespace
    normalized = normalized.strip()

    return normalized


# =============================================================================
# Full-Text Search (PostgreSQL)
# =============================================================================

def search_rows_fts(
    db: Session,
    file_id: int,
    query: str,
    limit: int = 50,
    search_source: bool = True,
    search_target: bool = True
) -> List[LDMRow]:
    """
    Full-text search on LDM rows using PostgreSQL tsvector.

    Falls back to LIKE search if FTS columns don't exist.

    Args:
        db: Database session
        file_id: File ID to search within
        query: Search query string
        limit: Maximum results to return
        search_source: Search in source column
        search_target: Search in target column

    Returns:
        List of matching LDMRow objects
    """
    from server.database.models import LDMRow

    try:
        # Try FTS search first
        return _search_rows_fts_postgres(db, file_id, query, limit, search_source, search_target)
    except Exception as e:
        logger.debug(f"FTS search not available, falling back to LIKE: {e}")
        # Fallback to LIKE search
        return _search_rows_like(db, file_id, query, limit, search_source, search_target)


def _search_rows_fts_postgres(
    db: Session,
    file_id: int,
    query: str,
    limit: int,
    search_source: bool,
    search_target: bool
) -> List[LDMRow]:
    """PostgreSQL full-text search using tsvector."""
    from server.database.models import LDMRow

    ts_query = func.plainto_tsquery('simple', query)

    conditions = [LDMRow.file_id == file_id]

    fts_conditions = []
    if search_source:
        fts_conditions.append(LDMRow.source_tsv.op('@@')(ts_query))
    if search_target:
        fts_conditions.append(LDMRow.target_tsv.op('@@')(ts_query))

    if fts_conditions:
        from sqlalchemy import or_
        conditions.append(or_(*fts_conditions))

    return db.query(LDMRow).filter(*conditions).limit(limit).all()


def _search_rows_like(
    db: Session,
    file_id: int,
    query: str,
    limit: int,
    search_source: bool,
    search_target: bool
) -> List[LDMRow]:
    """Fallback LIKE search when FTS not available."""
    from server.database.models import LDMRow
    from sqlalchemy import or_

    conditions = [LDMRow.file_id == file_id]

    like_conditions = []
    search_pattern = f"%{query}%"

    if search_source:
        like_conditions.append(LDMRow.source.ilike(search_pattern))
    if search_target:
        like_conditions.append(LDMRow.target.ilike(search_pattern))

    if like_conditions:
        conditions.append(or_(*like_conditions))

    return db.query(LDMRow).filter(*conditions).limit(limit).all()


# =============================================================================
# FTS Index Migration (PostgreSQL)
# =============================================================================

def add_fts_indexes(db: Session) -> bool:
    """
    Add Full-Text Search columns and indexes to ldm_rows table.

    - PostgreSQL: Creates tsvector columns and GIN indexes
    - SQLite: Skips (uses LIKE search fallback)

    Safe to call multiple times (uses IF NOT EXISTS).

    Args:
        db: Database session

    Returns:
        True if indexes added/exist (always True for SQLite)
    """
    if is_sqlite():
        logger.info("SQLite: Skipping FTS indexes (using LIKE search)")
        return True

    try:
        logger.info("Adding FTS columns to ldm_rows...")

        # Add tsvector columns (generated from source/target)
        db.execute(text("""
            ALTER TABLE ldm_rows
            ADD COLUMN IF NOT EXISTS source_tsv tsvector
            GENERATED ALWAYS AS (to_tsvector('simple', coalesce(source, ''))) STORED
        """))

        db.execute(text("""
            ALTER TABLE ldm_rows
            ADD COLUMN IF NOT EXISTS target_tsv tsvector
            GENERATED ALWAYS AS (to_tsvector('simple', coalesce(target, ''))) STORED
        """))

        # Create GIN indexes for fast FTS
        logger.info("Creating GIN indexes...")

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ldm_rows_source_fts
            ON ldm_rows USING GIN (source_tsv)
        """))

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ldm_rows_target_fts
            ON ldm_rows USING GIN (target_tsv)
        """))

        db.commit()
        logger.success("FTS indexes added successfully")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add FTS indexes: {e}")
        raise


def add_trigram_index(db: Session, table: str, column: str) -> bool:
    """
    Add trigram GIN index for similarity search.

    - PostgreSQL: Creates pg_trgm GIN index
    - SQLite: Skips (not supported)

    Requires pg_trgm extension (created if not exists).

    Args:
        db: Database session
        table: Table name
        column: Column name

    Returns:
        True if index added (always True for SQLite)
    """
    if is_sqlite():
        logger.info(f"SQLite: Skipping trigram index for {table}.{column}")
        return True

    try:
        # Enable pg_trgm extension
        db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

        # Create GIN trigram index
        index_name = f"idx_{table}_{column}_trgm"
        db.execute(text(f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table} USING GIN ({column} gin_trgm_ops)
        """))

        db.commit()
        logger.success(f"Trigram index created: {index_name}")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create trigram index: {e}")
        raise


# =============================================================================
# Query Helpers
# =============================================================================

def chunked_query(
    db: Session,
    model: Type[T],
    filters: list,
    chunk_size: int = 1000,
    order_by=None
) -> Generator[List[T], None, None]:
    """
    Yield query results in chunks to avoid memory issues with large datasets.

    Args:
        db: Database session
        model: SQLAlchemy model class
        filters: List of filter conditions
        chunk_size: Number of records per chunk
        order_by: Column to order by (defaults to primary key for consistent pagination)

    Yields:
        Lists of model instances

    Example:
        >>> for chunk in chunked_query(db, LDMRow, [LDMRow.file_id == 1], chunk_size=1000):
        >>>     for row in chunk:
        >>>         process(row)
    """
    query = db.query(model).filter(*filters)

    # Default to primary key if no order_by specified (required for consistent OFFSET/LIMIT)
    if order_by is not None:
        query = query.order_by(order_by)
    else:
        # Get primary key column(s) from model
        pk_columns = [c for c in model.__table__.columns if c.primary_key]
        if pk_columns:
            query = query.order_by(*pk_columns)

    offset = 0
    while True:
        chunk = query.offset(offset).limit(chunk_size).all()
        if not chunk:
            break
        yield chunk
        offset += chunk_size


def upsert_batch(
    db: Session,
    model: Type[T],
    records: List[dict],
    unique_key: str,
    batch_size: int = 1000
) -> dict:
    """
    Upsert records (insert or update if exists).

    - PostgreSQL: Uses ON CONFLICT DO UPDATE
    - SQLite: Uses INSERT OR REPLACE

    Args:
        db: Database session
        model: SQLAlchemy model class
        records: List of dictionaries with column values
        unique_key: Column name for conflict detection
        batch_size: Records per batch

    Returns:
        Dict with 'total' count (inserted + updated combined)
    """
    if not records:
        return {'total': 0}

    if is_sqlite():
        return _upsert_batch_sqlite(db, model, records, unique_key, batch_size)

    # PostgreSQL: Use ON CONFLICT
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    total = 0

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]

        # Get all column names except primary key
        columns = [c.name for c in model.__table__.columns if c.name != 'id']
        update_dict = {c: getattr(pg_insert(model).excluded, c) for c in columns if c != unique_key}

        stmt = pg_insert(model).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=[unique_key],
            set_=update_dict
        )

        db.execute(stmt)
        total += len(batch)

    db.commit()
    return {'total': total}


def _upsert_batch_sqlite(
    db: Session,
    model: Type[T],
    records: List[dict],
    unique_key: str,
    batch_size: int = 1000
) -> dict:
    """
    SQLite fallback for upsert using INSERT OR REPLACE.

    Args:
        db: Database session
        model: SQLAlchemy model class
        records: List of dictionaries
        unique_key: Column for conflict detection
        batch_size: Records per batch

    Returns:
        Dict with 'total' count
    """
    total = 0
    table_name = model.__tablename__

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]

        for record in batch:
            columns = list(record.keys())
            cols_str = ', '.join(f'"{c}"' for c in columns)
            placeholders = ', '.join(f':{c}' for c in columns)

            # SQLite INSERT OR REPLACE
            stmt = text(f'INSERT OR REPLACE INTO "{table_name}" ({cols_str}) VALUES ({placeholders})')
            db.execute(stmt, record)
            total += 1

    db.commit()
    return {'total': total}


# =============================================================================
# Export utilities
# =============================================================================

__all__ = [
    # Database detection
    'is_postgresql',
    'is_sqlite',

    # COPY TEXT (P21 - 3-5x faster on PostgreSQL, INSERT fallback on SQLite)
    'bulk_copy',
    'bulk_copy_tm_entries',
    'bulk_copy_rows',
    'escape_for_copy',

    # Batch operations
    'bulk_insert',
    'bulk_insert_tm_entries',
    'bulk_insert_rows',

    # Text utilities
    'normalize_text_for_hash',

    # FTS (PostgreSQL tsvector / SQLite LIKE)
    'search_rows_fts',
    'add_fts_indexes',
    'add_trigram_index',

    # Query helpers
    'chunked_query',
    'upsert_batch',
]
