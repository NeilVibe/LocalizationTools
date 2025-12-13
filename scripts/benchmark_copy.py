#!/usr/bin/env python3
"""
Benchmark: COPY TEXT vs INSERT for bulk operations

Tests both methods and compares performance.
Run with PostgreSQL to see the real speedup (3-5x faster).

Usage:
    python3 scripts/benchmark_copy.py [--rows 100000]
"""

import sys
import os
import time
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from sqlalchemy import text

from server.database.db_setup import setup_database
from server.database.db_utils import (
    is_postgresql,
    bulk_insert,
    bulk_insert_tm_entries,
    bulk_copy,
    bulk_copy_tm_entries,
    normalize_text_for_hash,
)
from server.database.models import Base, LDMTranslationMemory, LDMTMEntry


def generate_test_entries(count: int) -> list:
    """Generate test TM entries with various content."""
    entries = []

    # Mix of content types for realistic testing
    templates = [
        # Normal text
        ("Hello World {n}", "안녕하세요 세계 {n}"),
        ("Game Start", "게임 시작"),
        ("Options Menu", "옵션 메뉴"),
        # With newlines
        ("Line 1\nLine 2\nLine 3", "첫번째 줄\n두번째 줄\n세번째 줄"),
        # With tabs (should be converted to spaces)
        ("Tab\there\ttest", "탭\t여기\t테스트"),
        # With backslashes
        ("Path\\to\\file", "경로\\파일\\위치"),
        # With special characters
        ("Special: <>&\"'", "특수: <>&\"'"),
        # Unicode
        ("日本語テスト {n}", "Japanese test {n}"),
        # Long text
        ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. {n}",
         "로렘 입숨 텍스트 테스트입니다. 긴 문장을 테스트하기 위한 예시 문장입니다. {n}"),
    ]

    for i in range(count):
        template_idx = i % len(templates)
        source, target = templates[template_idx]
        entries.append({
            "source_text": source.format(n=i),
            "target_text": target.format(n=i),
        })

    return entries


def cleanup_test_data(session):
    """Clean up test TM data."""
    try:
        session.execute(text("DELETE FROM ldm_tm_entries WHERE tm_id IN (SELECT id FROM ldm_translation_memories WHERE name LIKE 'BENCHMARK_TEST_%')"))
        session.execute(text("DELETE FROM ldm_translation_memories WHERE name LIKE 'BENCHMARK_TEST_%'"))
        session.commit()
        logger.info("Cleaned up test data")
    except Exception as e:
        session.rollback()
        logger.warning(f"Cleanup warning: {e}")


def benchmark_insert(session, entries: list, tm_name: str) -> dict:
    """Benchmark INSERT method."""
    # Create TM
    tm = LDMTranslationMemory(
        name=tm_name,
        description="Benchmark test TM (INSERT)",
        owner_id=1,
        source_lang="en",
        target_lang="ko",
        entry_count=0,
        status="indexing"
    )
    session.add(tm)
    session.commit()

    # Benchmark INSERT
    start_time = time.time()
    count = bulk_insert_tm_entries(session, tm.id, entries, batch_size=5000)
    elapsed = time.time() - start_time

    # Update TM
    tm.entry_count = count
    tm.status = "ready"
    session.commit()

    rate = count / elapsed if elapsed > 0 else 0

    return {
        "method": "INSERT (batch)",
        "entries": count,
        "time_seconds": round(elapsed, 3),
        "rate_per_second": round(rate),
        "tm_id": tm.id,
    }


def benchmark_copy(session, entries: list, tm_name: str) -> dict:
    """Benchmark COPY TEXT method."""
    # Create TM
    tm = LDMTranslationMemory(
        name=tm_name,
        description="Benchmark test TM (COPY TEXT)",
        owner_id=1,
        source_lang="en",
        target_lang="ko",
        entry_count=0,
        status="indexing"
    )
    session.add(tm)
    session.commit()

    # Benchmark COPY TEXT
    start_time = time.time()
    count = bulk_copy_tm_entries(session, tm.id, entries)
    elapsed = time.time() - start_time

    # Update TM
    tm.entry_count = count
    tm.status = "ready"
    session.commit()

    rate = count / elapsed if elapsed > 0 else 0

    return {
        "method": "COPY TEXT",
        "entries": count,
        "time_seconds": round(elapsed, 3),
        "rate_per_second": round(rate),
        "tm_id": tm.id,
    }


def verify_data_integrity(session, tm_id: int, sample_size: int = 10) -> bool:
    """Verify inserted data looks correct."""
    result = session.execute(
        text(f"SELECT source_text, target_text FROM ldm_tm_entries WHERE tm_id = {tm_id} LIMIT {sample_size}")
    )
    rows = result.fetchall()

    for source, target in rows:
        if not source or not target:
            logger.error(f"Empty data found: source={source!r}, target={target!r}")
            return False

    logger.info(f"Data integrity check passed ({len(rows)} samples)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Benchmark COPY TEXT vs INSERT")
    parser.add_argument("--rows", type=int, default=100000, help="Number of rows to test")
    parser.add_argument("--postgres", action="store_true", help="Use PostgreSQL instead of SQLite")
    args = parser.parse_args()

    row_count = args.rows

    print("\n" + "=" * 70)
    print("P21 DATABASE POWERHOUSE - BENCHMARK")
    print("COPY TEXT vs INSERT Performance Test")
    print("=" * 70 + "\n")

    # Setup database (PostgreSQL ONLY)
    logger.info("Setting up database connection...")
    engine, SessionMaker = setup_database()

    with SessionMaker() as session:
        # Check database type
        is_pg = is_postgresql(session)
        db_type = "PostgreSQL" if is_pg else "SQLite"
        print(f"Database: {db_type}")
        print(f"Test size: {row_count:,} entries\n")

        if not is_pg:
            print("WARNING: SQLite detected - COPY TEXT will fall back to INSERT")
            print("Run with PostgreSQL to see the real speedup.\n")

        # Cleanup previous test data
        cleanup_test_data(session)

        # Generate test data
        logger.info(f"Generating {row_count:,} test entries...")
        start = time.time()
        entries = generate_test_entries(row_count)
        gen_time = time.time() - start
        print(f"Generated {len(entries):,} entries in {gen_time:.2f}s\n")

        # Run benchmarks
        print("-" * 70)
        print("BENCHMARK RESULTS")
        print("-" * 70)

        # Test INSERT first
        timestamp = datetime.now().strftime("%H%M%S")
        logger.info("Running INSERT benchmark...")
        insert_result = benchmark_insert(session, entries, f"BENCHMARK_TEST_INSERT_{timestamp}")

        print(f"\n{'Method':<20} {'Entries':<12} {'Time (s)':<12} {'Rate (/s)':<12}")
        print("-" * 56)
        print(f"{insert_result['method']:<20} {insert_result['entries']:<12,} {insert_result['time_seconds']:<12.3f} {insert_result['rate_per_second']:<12,}")

        # Verify INSERT data
        verify_data_integrity(session, insert_result["tm_id"])

        # Test COPY TEXT
        logger.info("Running COPY TEXT benchmark...")
        copy_result = benchmark_copy(session, entries, f"BENCHMARK_TEST_COPY_{timestamp}")

        print(f"{copy_result['method']:<20} {copy_result['entries']:<12,} {copy_result['time_seconds']:<12.3f} {copy_result['rate_per_second']:<12,}")

        # Verify COPY data
        verify_data_integrity(session, copy_result["tm_id"])

        # Calculate speedup
        print("-" * 56)
        if insert_result['time_seconds'] > 0:
            speedup = insert_result['time_seconds'] / copy_result['time_seconds']
            print(f"\nSPEEDUP: {speedup:.2f}x faster with COPY TEXT")

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        if is_pg:
            print(f"PostgreSQL COPY TEXT is {speedup:.1f}x faster than batch INSERT")
            print(f"INSERT:    {insert_result['rate_per_second']:,} entries/sec")
            print(f"COPY TEXT: {copy_result['rate_per_second']:,} entries/sec")

            # Estimate time for 1M rows
            insert_1m = 1000000 / insert_result['rate_per_second']
            copy_1m = 1000000 / copy_result['rate_per_second']
            print(f"\nEstimate for 1M rows:")
            print(f"  INSERT:    {insert_1m:.1f} seconds ({insert_1m/60:.1f} minutes)")
            print(f"  COPY TEXT: {copy_1m:.1f} seconds ({copy_1m/60:.1f} minutes)")
        else:
            print("SQLite doesn't support COPY - both methods use INSERT")
            print("Run with PostgreSQL for true COPY TEXT performance.")

        # Cleanup
        print("\nCleaning up test data...")
        cleanup_test_data(session)

        print("\nBenchmark complete!")


if __name__ == "__main__":
    main()
