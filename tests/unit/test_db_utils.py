"""
Tests for Database Utilities (db_utils.py)

Tests bulk insert, FTS search, and query helpers.
Uses PostgreSQL in CI, SQLite locally.
"""

import os
import pytest
import hashlib
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from server.database.models import Base, LDMTMEntry, LDMRow, LDMFile, LDMProject, LDMTranslationMemory, User
from server.database.db_utils import (
    bulk_insert,
    bulk_insert_tm_entries,
    bulk_insert_rows,
    normalize_text_for_hash,
    search_rows_fts,
    is_postgresql,
    chunked_query,
)


def get_test_database_url():
    """Get database URL - PostgreSQL in CI, SQLite locally."""
    # CI environment has POSTGRES_* env vars
    pg_user = os.getenv("POSTGRES_USER")
    pg_pass = os.getenv("POSTGRES_PASSWORD")
    pg_db = os.getenv("POSTGRES_DB")
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_PORT", "5432")

    if pg_user and pg_pass and pg_db:
        return f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
    return "sqlite:///:memory:"


# =============================================================================
# Fixtures - Fresh database per test
# =============================================================================

@pytest.fixture
def test_session():
    """Create a fresh test database - PostgreSQL in CI, SQLite locally."""
    db_url = get_test_database_url()
    engine = create_engine(db_url, echo=False)

    if "postgresql" in db_url:
        # PostgreSQL: Create all tables (supports JSONB)
        Base.metadata.create_all(engine)
    else:
        # SQLite: Only create tables without JSONB columns
        tables_to_create = [
            User.__table__,
            LDMProject.__table__,
            LDMFile.__table__,
            LDMRow.__table__,
            LDMTranslationMemory.__table__,
            LDMTMEntry.__table__,
        ]
        Base.metadata.create_all(engine, tables=tables_to_create)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session

    session.close()

    if "postgresql" in db_url:
        # PostgreSQL: Clean up tables after test
        Base.metadata.drop_all(engine)

    engine.dispose()


@pytest.fixture
def test_user(test_session):
    """Create a test user with unique ID."""
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        username=f"test_user_{unique_id}",
        password_hash="test_hash",
        email=f"test_{unique_id}@example.com",
        role="user"
    )
    test_session.add(user)
    test_session.commit()
    return user


@pytest.fixture
def test_project(test_session, test_user):
    """Create a test LDM project."""
    project = LDMProject(
        name="Test Project",
        owner_id=test_user.user_id,
        description="Test project for unit tests"
    )
    test_session.add(project)
    test_session.commit()
    return project


@pytest.fixture
def test_file(test_session, test_project, test_user):
    """Create a test LDM file."""
    file = LDMFile(
        project_id=test_project.id,
        name="test_file.txt",
        original_filename="test_file.txt",
        format="txt",
        row_count=0,
        created_by=test_user.user_id
    )
    test_session.add(file)
    test_session.commit()
    return file


@pytest.fixture
def test_tm(test_session, test_user):
    """Create a test Translation Memory."""
    tm = LDMTranslationMemory(
        name="Test TM",
        owner_id=test_user.user_id,
        source_lang="ko",
        target_lang="en"
    )
    test_session.add(tm)
    test_session.commit()
    return tm


# =============================================================================
# Test: Text Normalization
# =============================================================================

class TestNormalizeTextForHash:
    """Test text normalization for consistent hashing."""

    def test_empty_string(self):
        """Empty string returns empty."""
        assert normalize_text_for_hash("") == ""
        assert normalize_text_for_hash(None) == ""

    def test_whitespace_strip(self):
        """Leading/trailing whitespace is stripped."""
        assert normalize_text_for_hash("  hello  ") == "hello"
        assert normalize_text_for_hash("\n\nhello\n\n") == "hello"

    def test_newline_normalization(self):
        """Different newline styles normalized to \n."""
        assert normalize_text_for_hash("a\r\nb") == "a\nb"
        assert normalize_text_for_hash("a\rb") == "a\nb"
        assert normalize_text_for_hash("a\nb") == "a\nb"

    def test_unicode_preserved(self):
        """Korean and other unicode preserved."""
        korean = "안녕하세요"
        assert normalize_text_for_hash(korean) == korean

    def test_consistent_hash(self):
        """Same text produces same hash."""
        text1 = "Hello World"
        text2 = "  Hello World  "  # With whitespace

        norm1 = normalize_text_for_hash(text1)
        norm2 = normalize_text_for_hash(text2)

        hash1 = hashlib.sha256(norm1.encode()).hexdigest()
        hash2 = hashlib.sha256(norm2.encode()).hexdigest()

        assert hash1 == hash2


# =============================================================================
# Test: Bulk Insert
# =============================================================================

class TestBulkInsert:
    """Test bulk insert operations."""

    def test_bulk_insert_empty_list(self, test_session, test_tm):
        """Empty list returns 0."""
        count = bulk_insert(test_session, LDMTMEntry, [])
        assert count == 0

    def test_bulk_insert_single_record(self, test_session, test_tm):
        """Single record inserts correctly."""
        records = [{
            "tm_id": test_tm.id,
            "source_text": "Hello",
            "target_text": "안녕",
            "source_hash": "abc123"
        }]

        count = bulk_insert(test_session, LDMTMEntry, records)
        assert count == 1

        # Verify in database
        entry = test_session.query(LDMTMEntry).first()
        assert entry.source_text == "Hello"
        assert entry.target_text == "안녕"

    def test_bulk_insert_many_records(self, test_session, test_tm):
        """Many records insert efficiently."""
        records = [
            {
                "tm_id": test_tm.id,
                "source_text": f"Source {i}",
                "target_text": f"Target {i}",
                "source_hash": f"hash_{i:08d}"
            }
            for i in range(1000)
        ]

        count = bulk_insert(test_session, LDMTMEntry, records, batch_size=100)
        assert count == 1000

        # Verify count in database
        db_count = test_session.query(LDMTMEntry).count()
        assert db_count == 1000

    def test_bulk_insert_with_progress_callback(self, test_session, test_tm):
        """Progress callback is called."""
        progress_calls = []

        def callback(inserted, total):
            progress_calls.append((inserted, total))

        records = [
            {
                "tm_id": test_tm.id,
                "source_text": f"Source {i}",
                "target_text": f"Target {i}",
                "source_hash": f"hash_{i:08d}"
            }
            for i in range(250)
        ]

        bulk_insert(test_session, LDMTMEntry, records, batch_size=100, progress_callback=callback)

        # Should have 3 progress calls (100, 200, 250)
        assert len(progress_calls) == 3
        assert progress_calls[-1] == (250, 250)


# =============================================================================
# Test: Bulk Insert TM Entries (with auto hash)
# =============================================================================

class TestBulkInsertTMEntries:
    """Test TM-specific bulk insert with auto hash generation."""

    def test_auto_generates_hash(self, test_session, test_tm):
        """Source hash is auto-generated."""
        entries = [
            {"source_text": "Hello", "target_text": "안녕"},
            {"source_text": "World", "target_text": "세계"},
        ]

        count = bulk_insert_tm_entries(test_session, test_tm.id, entries)
        assert count == 2

        # Verify hashes were generated
        db_entries = test_session.query(LDMTMEntry).all()
        for entry in db_entries:
            assert entry.source_hash is not None
            assert len(entry.source_hash) == 64  # SHA256 hex

    def test_consistent_hash_generation(self, test_session, test_tm):
        """Same source text produces same hash."""
        entries = [
            {"source_text": "Test", "target_text": "A"},
            {"source_text": "Test", "target_text": "B"},  # Same source
        ]

        bulk_insert_tm_entries(test_session, test_tm.id, entries)

        db_entries = test_session.query(LDMTMEntry).all()
        assert db_entries[0].source_hash == db_entries[1].source_hash

    def test_preserves_metadata(self, test_session, test_tm):
        """Optional metadata is preserved."""
        entries = [
            {
                "source_text": "Hello",
                "target_text": "안녕",
                "created_by": "translator_01",
                "change_date": datetime(2025, 1, 1)
            }
        ]

        bulk_insert_tm_entries(test_session, test_tm.id, entries)

        entry = test_session.query(LDMTMEntry).first()
        assert entry.created_by == "translator_01"


# =============================================================================
# Test: Bulk Insert Rows
# =============================================================================

class TestBulkInsertRows:
    """Test LDM row bulk insert."""

    def test_bulk_insert_rows(self, test_session, test_file):
        """Rows insert correctly."""
        rows = [
            {"row_num": 1, "string_id": "menu_01", "source": "게임 시작", "target": "Start Game"},
            {"row_num": 2, "string_id": "menu_02", "source": "설정", "target": "Settings"},
            {"row_num": 3, "string_id": "menu_03", "source": "종료", "target": None},
        ]

        count = bulk_insert_rows(test_session, test_file.id, rows)
        assert count == 3

        # Verify in database
        db_rows = test_session.query(LDMRow).order_by(LDMRow.row_num).all()
        assert len(db_rows) == 3
        assert db_rows[0].source == "게임 시작"
        assert db_rows[2].target is None
        assert db_rows[0].status == "pending"  # Default status


# =============================================================================
# Test: Search (FTS with fallback to LIKE)
# =============================================================================

class TestSearchRowsFTS:
    """Test full-text search (uses LIKE on SQLite)."""

    def test_search_empty_query(self, test_session, test_file):
        """Empty query returns empty results."""
        results = search_rows_fts(test_session, test_file.id, "")
        assert results == []

    def test_search_source_column(self, test_session, test_file):
        """Search finds matches in source column."""
        # Insert test data
        rows = [
            {"row_num": 1, "string_id": "a", "source": "Hello World", "target": "안녕 세계"},
            {"row_num": 2, "string_id": "b", "source": "Goodbye", "target": "안녕"},
        ]
        bulk_insert_rows(test_session, test_file.id, rows)

        # Search for "Hello"
        results = search_rows_fts(test_session, test_file.id, "Hello", search_source=True, search_target=False)
        assert len(results) == 1
        assert results[0].source == "Hello World"

    def test_search_target_column(self, test_session, test_file):
        """Search finds matches in target column."""
        rows = [
            {"row_num": 1, "string_id": "a", "source": "Source", "target": "Target Match"},
            {"row_num": 2, "string_id": "b", "source": "Source2", "target": "No"},
        ]
        bulk_insert_rows(test_session, test_file.id, rows)

        results = search_rows_fts(test_session, test_file.id, "Match", search_source=False, search_target=True)
        assert len(results) == 1

    def test_search_both_columns(self, test_session, test_file):
        """Search finds matches in both columns."""
        rows = [
            {"row_num": 1, "string_id": "a", "source": "Apple", "target": "사과"},
            {"row_num": 2, "string_id": "b", "source": "Orange", "target": "Apple Pie"},
        ]
        bulk_insert_rows(test_session, test_file.id, rows)

        results = search_rows_fts(test_session, test_file.id, "Apple")
        assert len(results) == 2  # Found in source AND target

    def test_search_korean(self, test_session, test_file):
        """Search works with Korean text."""
        rows = [
            {"row_num": 1, "string_id": "a", "source": "안녕하세요", "target": "Hello"},
            {"row_num": 2, "string_id": "b", "source": "감사합니다", "target": "Thank you"},
        ]
        bulk_insert_rows(test_session, test_file.id, rows)

        results = search_rows_fts(test_session, test_file.id, "안녕")
        assert len(results) == 1

    def test_search_limit(self, test_session, test_file):
        """Search respects limit parameter."""
        rows = [{"row_num": i, "string_id": f"id_{i}", "source": "Match", "target": f"T{i}"} for i in range(100)]
        bulk_insert_rows(test_session, test_file.id, rows)

        results = search_rows_fts(test_session, test_file.id, "Match", limit=10)
        assert len(results) == 10


# =============================================================================
# Test: Database Detection
# =============================================================================

class TestIsPostgreSQL:
    """Test PostgreSQL detection."""

    def test_always_returns_true(self, test_session):
        """PostgreSQL-only mode always returns True."""
        assert is_postgresql(test_session) == True


# =============================================================================
# Test: Chunked Query
# =============================================================================

class TestChunkedQuery:
    """Test memory-safe chunked queries."""

    def test_chunked_query_empty(self, test_session, test_file):
        """Empty table yields no chunks."""
        chunks = list(chunked_query(test_session, LDMRow, [LDMRow.file_id == test_file.id]))
        assert len(chunks) == 0

    def test_chunked_query_small_dataset(self, test_session, test_file):
        """Small dataset returns single chunk."""
        rows = [{"row_num": i, "string_id": f"id_{i}", "source": f"S{i}", "target": f"T{i}"} for i in range(50)]
        bulk_insert_rows(test_session, test_file.id, rows)

        chunks = list(chunked_query(
            test_session, LDMRow,
            [LDMRow.file_id == test_file.id],
            chunk_size=100,
            order_by=LDMRow.row_num
        ))

        assert len(chunks) == 1
        assert len(chunks[0]) == 50

    def test_chunked_query_multiple_chunks(self, test_session, test_file):
        """Large dataset splits into chunks."""
        rows = [{"row_num": i, "string_id": f"id_{i}", "source": f"S{i}", "target": f"T{i}"} for i in range(250)]
        bulk_insert_rows(test_session, test_file.id, rows)

        chunks = list(chunked_query(
            test_session, LDMRow,
            [LDMRow.file_id == test_file.id],
            chunk_size=100,
            order_by=LDMRow.row_num
        ))

        assert len(chunks) == 3  # 100 + 100 + 50
        assert len(chunks[0]) == 100
        assert len(chunks[1]) == 100
        assert len(chunks[2]) == 50
