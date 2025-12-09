#!/usr/bin/env python3
"""
Benchmark: TM Import Performance

Tests bulk insert speed for large Translation Memories.
Run: python3 scripts/benchmark_tm_import.py --count 10000
"""

import argparse
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.database.models import Base, User, LDMTranslationMemory, LDMTMEntry
from server.database.db_utils import bulk_insert_tm_entries


def generate_test_entries(count: int) -> list:
    """Generate test TM entries."""
    print(f"Generating {count:,} test entries...")
    entries = []

    # Sample Korean-English pairs (realistic data)
    samples = [
        ("게임을 시작합니다", "Starting the game"),
        ("설정을 저장했습니다", "Settings saved"),
        ("레벨업을 축하합니다", "Congratulations on leveling up"),
        ("아이템을 획득했습니다", "Item acquired"),
        ("퀘스트를 완료했습니다", "Quest completed"),
        ("연결이 끊어졌습니다", "Connection lost"),
        ("서버에 접속 중입니다", "Connecting to server"),
        ("캐릭터를 선택하세요", "Select your character"),
        ("인벤토리가 가득 찼습니다", "Inventory is full"),
        ("스킬을 사용할 수 없습니다", "Cannot use skill"),
    ]

    for i in range(count):
        base = samples[i % len(samples)]
        entries.append({
            "source_text": f"{base[0]} #{i}",
            "target_text": f"{base[1]} #{i}",
        })

    return entries


def run_benchmark(count: int, use_postgres: bool = False):
    """Run the import benchmark."""

    # Create database
    if use_postgres:
        pg_user = os.getenv("POSTGRES_USER", "localization_admin")
        pg_pass = os.getenv("POSTGRES_PASSWORD", "locanext_dev_2025")
        pg_host = os.getenv("POSTGRES_HOST", "localhost")
        pg_port = os.getenv("POSTGRES_PORT", "5432")
        pg_db = os.getenv("POSTGRES_DB", "localizationtools")
        db_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
        print(f"Using PostgreSQL: {pg_host}:{pg_port}/{pg_db}")
    else:
        db_url = "sqlite:///:memory:"
        print("Using SQLite (in-memory)")

    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Create test user
        user = User(username="benchmark_user", password_hash="test", email="bench@test.com")
        db.add(user)
        db.commit()

        # Create test TM
        tm = LDMTranslationMemory(
            name="Benchmark TM",
            owner_id=user.user_id,
            source_lang="ko",
            target_lang="en"
        )
        db.add(tm)
        db.commit()

        # Generate entries
        entries = generate_test_entries(count)

        # Benchmark bulk insert
        print(f"\nInserting {count:,} entries...")
        print("=" * 60)

        start_time = time.time()

        def progress(inserted, total):
            pct = 100 * inserted / total
            rate = inserted / (time.time() - start_time) if time.time() > start_time else 0
            print(f"\r  Progress: {inserted:,}/{total:,} ({pct:.1f}%) - {rate:,.0f} entries/sec", end="", flush=True)

        inserted = bulk_insert_tm_entries(
            db,
            tm.id,
            entries,
            batch_size=5000,
            progress_callback=progress
        )

        elapsed = time.time() - start_time
        rate = count / elapsed

        print(f"\n\n{'=' * 60}")
        print(f"RESULTS:")
        print(f"  Entries inserted: {inserted:,}")
        print(f"  Time elapsed:     {elapsed:.2f} seconds")
        print(f"  Rate:             {rate:,.0f} entries/second")
        print(f"  Estimated 700k:   {700000/rate:.1f} seconds ({700000/rate/60:.1f} min)")
        print(f"{'=' * 60}")

        # Test search speed
        print(f"\nTesting search speed...")

        # Hash lookup (simulated)
        start = time.time()
        result = db.query(LDMTMEntry).filter(
            LDMTMEntry.tm_id == tm.id,
            LDMTMEntry.source_hash != None
        ).first()
        hash_time = (time.time() - start) * 1000
        print(f"  Hash lookup:      {hash_time:.2f}ms")

        # Count query
        start = time.time()
        count_result = db.query(LDMTMEntry).filter(LDMTMEntry.tm_id == tm.id).count()
        count_time = (time.time() - start) * 1000
        print(f"  Count query:      {count_time:.2f}ms ({count_result:,} entries)")

    finally:
        db.close()
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Benchmark TM import performance")
    parser.add_argument("--count", type=int, default=10000, help="Number of entries to import")
    parser.add_argument("--postgres", action="store_true", help="Use PostgreSQL instead of SQLite")
    args = parser.parse_args()

    print("=" * 60)
    print("TM IMPORT BENCHMARK")
    print("=" * 60)

    run_benchmark(args.count, args.postgres)


if __name__ == "__main__":
    main()
