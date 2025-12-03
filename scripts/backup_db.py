#!/usr/bin/env python3
"""
Database Backup Script for LocaNext

Usage:
    python3 scripts/backup_db.py              # Create backup
    python3 scripts/backup_db.py --list       # List backups
    python3 scripts/backup_db.py --status     # Check backup status
    python3 scripts/backup_db.py --cleanup    # Remove old backups (keep 7)

Backups are stored in: server/data/backups/
Format: localizationtools_YYYYMMDD_HHMM.db
"""

import os
import sys
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Paths
DB_PATH = PROJECT_ROOT / "server" / "data" / "localizationtools.db"
BACKUP_DIR = PROJECT_ROOT / "server" / "data" / "backups"
MAX_BACKUPS = 7


def ensure_backup_dir():
    """Create backup directory if it doesn't exist."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def get_backup_filename():
    """Generate backup filename with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"localizationtools_{timestamp}.db"


def list_backups():
    """List all existing backups sorted by date."""
    ensure_backup_dir()
    backups = sorted(BACKUP_DIR.glob("localizationtools_*.db"), reverse=True)
    return backups


def create_backup():
    """Create a new database backup."""
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return False

    ensure_backup_dir()
    backup_file = BACKUP_DIR / get_backup_filename()

    # Check if backup already exists (same minute)
    if backup_file.exists():
        print(f"Backup already exists: {backup_file.name}")
        return True

    try:
        shutil.copy2(DB_PATH, backup_file)
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        print(f"Backup created: {backup_file.name} ({size_mb:.2f} MB)")
        return True
    except Exception as e:
        print(f"ERROR: Failed to create backup: {e}")
        return False


def cleanup_old_backups():
    """Remove old backups, keeping only the most recent MAX_BACKUPS."""
    backups = list_backups()

    if len(backups) <= MAX_BACKUPS:
        print(f"No cleanup needed ({len(backups)} backups, max {MAX_BACKUPS})")
        return 0

    to_delete = backups[MAX_BACKUPS:]
    for backup in to_delete:
        try:
            backup.unlink()
            print(f"Deleted: {backup.name}")
        except Exception as e:
            print(f"ERROR deleting {backup.name}: {e}")

    print(f"Cleanup complete: {len(to_delete)} old backups removed")
    return len(to_delete)


def show_status():
    """Show backup status summary."""
    backups = list_backups()

    print("=" * 50)
    print("DATABASE BACKUP STATUS")
    print("=" * 50)

    # Database info
    if DB_PATH.exists():
        db_size = DB_PATH.stat().st_size / (1024 * 1024)
        db_modified = datetime.fromtimestamp(DB_PATH.stat().st_mtime)
        print(f"Database: {DB_PATH.name}")
        print(f"Size: {db_size:.2f} MB")
        print(f"Last modified: {db_modified.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("Database: NOT FOUND")

    print("-" * 50)

    # Backup info
    print(f"Backups: {len(backups)} (max {MAX_BACKUPS})")
    print(f"Location: {BACKUP_DIR}")

    if backups:
        latest = backups[0]
        latest_time = datetime.fromtimestamp(latest.stat().st_mtime)
        days_ago = (datetime.now() - latest_time).days

        print("-" * 50)
        print(f"Latest backup: {latest.name}")
        print(f"Created: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if days_ago == 0:
            print("Age: Today")
        elif days_ago == 1:
            print("Age: Yesterday")
        else:
            print(f"Age: {days_ago} days ago")
            if days_ago >= 3:
                print("RECOMMENDATION: Consider creating a new backup")
    else:
        print("-" * 50)
        print("No backups found!")
        print("RECOMMENDATION: Create a backup now")

    print("=" * 50)


def show_list():
    """Show list of all backups with details."""
    backups = list_backups()

    if not backups:
        print("No backups found.")
        return

    print(f"{'Filename':<35} {'Size':>10} {'Created':>20}")
    print("-" * 67)

    for backup in backups:
        size_mb = backup.stat().st_size / (1024 * 1024)
        created = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"{backup.name:<35} {size_mb:>8.2f}MB {created.strftime('%Y-%m-%d %H:%M'):>20}")


def main():
    parser = argparse.ArgumentParser(
        description="Database backup utility for LocaNext",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 scripts/backup_db.py              # Create new backup
    python3 scripts/backup_db.py --status     # Check backup status
    python3 scripts/backup_db.py --list       # List all backups
    python3 scripts/backup_db.py --cleanup    # Remove old backups
        """
    )

    parser.add_argument("--list", action="store_true", help="List all backups")
    parser.add_argument("--status", action="store_true", help="Show backup status")
    parser.add_argument("--cleanup", action="store_true", help="Remove old backups (keep 7)")

    args = parser.parse_args()

    if args.list:
        show_list()
    elif args.status:
        show_status()
    elif args.cleanup:
        cleanup_old_backups()
    else:
        # Default: create backup
        if create_backup():
            cleanup_old_backups()
            print("\nBackup complete!")
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
