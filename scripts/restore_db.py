#!/usr/bin/env python3
"""
Database Restore Script for LocaNext

Usage:
    python3 scripts/restore_db.py                     # Interactive restore (list + select)
    python3 scripts/restore_db.py --latest            # Restore latest backup
    python3 scripts/restore_db.py --file <filename>   # Restore specific backup

Backups are stored in: server/data/backups/
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


def list_backups():
    """List all existing backups sorted by date."""
    if not BACKUP_DIR.exists():
        return []
    return sorted(BACKUP_DIR.glob("localizationtools_*.db"), reverse=True)


def show_backups():
    """Display available backups."""
    backups = list_backups()

    if not backups:
        print("No backups available.")
        return []

    print("\nAvailable backups:")
    print("-" * 70)
    print(f"{'#':<4} {'Filename':<35} {'Size':>10} {'Created':>18}")
    print("-" * 70)

    for i, backup in enumerate(backups, 1):
        size_mb = backup.stat().st_size / (1024 * 1024)
        created = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"{i:<4} {backup.name:<35} {size_mb:>8.2f}MB {created.strftime('%Y-%m-%d %H:%M'):>18}")

    print("-" * 70)
    return backups


def restore_backup(backup_path: Path, force: bool = False):
    """Restore database from backup."""
    if not backup_path.exists():
        print(f"ERROR: Backup not found: {backup_path}")
        return False

    # Safety check
    if DB_PATH.exists() and not force:
        db_size = DB_PATH.stat().st_size / (1024 * 1024)
        backup_size = backup_path.stat().st_size / (1024 * 1024)

        print(f"\nWARNING: This will OVERWRITE the current database!")
        print(f"  Current DB: {db_size:.2f} MB")
        print(f"  Backup: {backup_size:.2f} MB ({backup_path.name})")
        print()

        confirm = input("Type 'yes' to confirm restore: ").strip().lower()
        if confirm != 'yes':
            print("Restore cancelled.")
            return False

    try:
        # Create pre-restore backup
        if DB_PATH.exists():
            pre_restore = DB_PATH.with_suffix('.db.pre_restore')
            shutil.copy2(DB_PATH, pre_restore)
            print(f"Pre-restore backup: {pre_restore.name}")

        # Restore
        shutil.copy2(backup_path, DB_PATH)
        print(f"\nDatabase restored from: {backup_path.name}")
        print("Restart the server to use restored database.")
        return True

    except Exception as e:
        print(f"ERROR: Failed to restore: {e}")
        return False


def interactive_restore():
    """Interactive backup selection and restore."""
    backups = show_backups()

    if not backups:
        return False

    print("\nEnter backup number to restore (or 'q' to quit):")
    choice = input("> ").strip()

    if choice.lower() == 'q':
        print("Cancelled.")
        return False

    try:
        index = int(choice) - 1
        if 0 <= index < len(backups):
            return restore_backup(backups[index])
        else:
            print("Invalid selection.")
            return False
    except ValueError:
        print("Invalid input. Enter a number.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Database restore utility for LocaNext",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 scripts/restore_db.py                              # Interactive
    python3 scripts/restore_db.py --latest                     # Restore latest
    python3 scripts/restore_db.py --file localizationtools_20251203_1430.db
    python3 scripts/restore_db.py --latest --force             # No confirmation
        """
    )

    parser.add_argument("--latest", action="store_true", help="Restore the latest backup")
    parser.add_argument("--file", type=str, help="Restore specific backup file")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--list", action="store_true", help="List available backups")

    args = parser.parse_args()

    if args.list:
        show_backups()
        return

    if args.latest:
        backups = list_backups()
        if not backups:
            print("No backups available.")
            sys.exit(1)
        success = restore_backup(backups[0], force=args.force)
        sys.exit(0 if success else 1)

    if args.file:
        backup_path = BACKUP_DIR / args.file
        if not backup_path.exists():
            # Try exact path
            backup_path = Path(args.file)
        success = restore_backup(backup_path, force=args.force)
        sys.exit(0 if success else 1)

    # Default: interactive
    success = interactive_restore()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
