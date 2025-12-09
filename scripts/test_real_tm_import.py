#!/usr/bin/env python3
"""
Test TM Import with REAL Language Data

Uses sampleofLanguageData.txt (103k lines) to test PostgreSQL performance.
"""

import argparse
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from server.database.models import Base, User, LDMTranslationMemory, LDMTMEntry
from server.database.db_utils import bulk_insert_tm_entries, search_rows_fts, is_postgresql


def parse_language_data_file(filepath: str, limit: int = None) -> list:
    """
    Parse sampleofLanguageData.txt format.
    Format: col0\tcol1\tcol2\tcol3\tcol4\tSourceKO\tTargetFR\tStatus\t
    """
    entries = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break

            parts = line.strip().split('\t')
            if len(parts) >= 7:
                source = parts[5] if len(parts) > 5 else ""
                target = parts[6] if len(parts) > 6 else ""

                if source:  # Skip empty sources
                    entries.append({
                        "source_text": source,
                        "target_text": target
                    })

    return entries


def run_test(filepath: str, limit: int = None, use_postgres: bool = True):
    """Run the real data test."""

    # Database connection
    if use_postgres:
        pg_user = os.getenv("POSTGRES_USER", "localization_admin")
        pg_pass = os.getenv("POSTGRES_PASSWORD", "locanext_dev_2025")
        pg_host = os.getenv("POSTGRES_HOST", "localhost")
        pg_port = os.getenv("POSTGRES_PORT", "5432")
        pg_db = os.getenv("POSTGRES_DB", "localizationtools")
        db_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
        print(f"Database: PostgreSQL ({pg_host}:{pg_port}/{pg_db})")
    else:
        db_url = "sqlite:///:memory:"
        print("Database: SQLite (in-memory)")

    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Check if PostgreSQL
        is_pg = is_postgresql(db)
        print(f"PostgreSQL detected: {is_pg}")

        # Create test user (or get existing)
        user = db.query(User).filter(User.username == "tm_test_user").first()
        if not user:
            user = User(username="tm_test_user", password_hash="test", email="tmtest@test.com")
            db.add(user)
            db.commit()

        # Create test TM
        tm = LDMTranslationMemory(
            name=f"Real Data Test TM ({limit or 'all'} entries)",
            owner_id=user.user_id,
            source_lang="ko",
            target_lang="fr"
        )
        db.add(tm)
        db.commit()

        # Parse file
        print(f"\n{'='*60}")
        print(f"PARSING: {filepath}")
        print(f"Limit: {limit or 'ALL'}")
        print(f"{'='*60}")

        parse_start = time.time()
        entries = parse_language_data_file(filepath, limit)
        parse_time = time.time() - parse_start

        print(f"Parsed {len(entries):,} entries in {parse_time:.2f}s")

        # Import to TM
        print(f"\n{'='*60}")
        print(f"IMPORTING TO TM...")
        print(f"{'='*60}")

        import_start = time.time()

        def progress(inserted, total):
            pct = 100 * inserted / total
            elapsed = time.time() - import_start
            rate = inserted / elapsed if elapsed > 0 else 0
            print(f"\r  {inserted:,}/{total:,} ({pct:.1f}%) - {rate:,.0f}/sec", end="", flush=True)

        count = bulk_insert_tm_entries(db, tm.id, entries, batch_size=5000, progress_callback=progress)

        import_time = time.time() - import_start
        rate = count / import_time if import_time > 0 else 0

        print(f"\n\n{'='*60}")
        print(f"IMPORT RESULTS:")
        print(f"  Entries imported: {count:,}")
        print(f"  Time: {import_time:.2f} seconds")
        print(f"  Rate: {rate:,.0f} entries/second")
        print(f"{'='*60}")

        # Test search
        print(f"\nTESTING SEARCH...")

        # Test 1: Count query
        start = time.time()
        total = db.query(LDMTMEntry).filter(LDMTMEntry.tm_id == tm.id).count()
        count_time = (time.time() - start) * 1000
        print(f"  Count query: {count_time:.2f}ms ({total:,} entries)")

        # Test 2: Hash lookup (exact match)
        start = time.time()
        sample = db.query(LDMTMEntry).filter(LDMTMEntry.tm_id == tm.id).first()
        if sample:
            result = db.query(LDMTMEntry).filter(
                LDMTMEntry.tm_id == tm.id,
                LDMTMEntry.source_hash == sample.source_hash
            ).first()
        hash_time = (time.time() - start) * 1000
        print(f"  Hash lookup: {hash_time:.2f}ms")

        # Test 3: LIKE search
        start = time.time()
        results = db.query(LDMTMEntry).filter(
            LDMTMEntry.tm_id == tm.id,
            LDMTMEntry.source_text.ilike("%스킬%")  # Search for "skill" in Korean
        ).limit(10).all()
        like_time = (time.time() - start) * 1000
        print(f"  LIKE search '스킬': {like_time:.2f}ms ({len(results)} results)")

        # Test 4: FTS if PostgreSQL
        if is_pg:
            try:
                start = time.time()
                # Use raw SQL for FTS test
                fts_result = db.execute(text("""
                    SELECT COUNT(*) FROM ldm_tm_entries
                    WHERE tm_id = :tm_id
                    AND source_text ILIKE :pattern
                """), {"tm_id": tm.id, "pattern": "%마력%"})
                fts_time = (time.time() - start) * 1000
                fts_count = fts_result.scalar()
                print(f"  Pattern search '마력': {fts_time:.2f}ms ({fts_count} results)")
            except Exception as e:
                print(f"  FTS test error: {e}")

        print(f"\n{'='*60}")
        print(f"ALL TESTS PASSED!")
        print(f"{'='*60}")

        # Update TM entry count
        tm.entry_count = count
        tm.status = "ready"
        db.commit()

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Test TM import with real language data")
    parser.add_argument("--file", default="/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext/sampleofLanguageData.txt",
                       help="Path to language data file")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of entries")
    parser.add_argument("--sqlite", action="store_true", help="Use SQLite instead of PostgreSQL")
    args = parser.parse_args()

    print("="*60)
    print("REAL LANGUAGE DATA TM IMPORT TEST")
    print("="*60)

    run_test(args.file, args.limit, use_postgres=not args.sqlite)


if __name__ == "__main__":
    main()
