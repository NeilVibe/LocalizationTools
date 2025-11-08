#!/usr/bin/env python3
"""
Create Default Admin User

Initialize the database with a default administrator account.
This script should be run once during initial setup.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from loguru import logger

from server.database.db_setup import setup_database
from server.database.models import User, AppVersion
from server.utils.auth import hash_password
from server import config


def create_default_admin(db):
    """
    Create the default admin user.

    Args:
        db: Database session.

    Returns:
        User object if created, None if already exists.
    """
    # Check if admin already exists
    existing_admin = db.query(User).filter(
        User.username == config.DEFAULT_ADMIN_USERNAME
    ).first()

    if existing_admin:
        logger.info(f"Admin user '{config.DEFAULT_ADMIN_USERNAME}' already exists")
        return None

    # Create admin user
    admin = User(
        username=config.DEFAULT_ADMIN_USERNAME,
        password_hash=hash_password(config.DEFAULT_ADMIN_PASSWORD),
        email=config.DEFAULT_ADMIN_EMAIL,
        full_name="System Administrator",
        department="IT",
        role="superadmin",
        is_active=True,
        created_at=datetime.utcnow()
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    logger.success(f"✓ Admin user created: {admin.username} (ID: {admin.user_id})")
    return admin


def create_initial_app_version(db):
    """
    Create initial app version record.

    Args:
        db: Database session.

    Returns:
        AppVersion object if created, None if already exists.
    """
    # Check if version already exists
    existing_version = db.query(AppVersion).filter(
        AppVersion.version_number == config.APP_VERSION
    ).first()

    if existing_version:
        logger.info(f"App version '{config.APP_VERSION}' already exists")
        return None

    # Create version record
    version = AppVersion(
        version_number=config.APP_VERSION,
        release_date=datetime.utcnow(),
        is_latest=True,
        is_required=False,
        release_notes="Initial release - MVP with XLSTransfer, logging, and admin dashboard",
        download_url=f"{config.UPDATE_DOWNLOAD_URL_BASE}/LocalizationTools-{config.APP_VERSION}.exe"
    )

    db.add(version)
    db.commit()
    db.refresh(version)

    logger.success(f"✓ App version created: {version.version_number}")
    return version


def main():
    """Main initialization script."""
    logger.info("=" * 70)
    logger.info("LOCALIZATIONTOOLS - INITIAL SETUP")
    logger.info("=" * 70)

    # Setup database
    logger.info("Setting up database...")
    use_postgres = config.DATABASE_TYPE == "postgresql"
    engine, session_maker = setup_database(use_postgres=use_postgres, drop_existing=False)

    # Create database session
    db = session_maker()

    try:
        # Create default admin
        logger.info("\nCreating default admin user...")
        admin = create_default_admin(db)

        if admin:
            logger.info("\n" + "=" * 70)
            logger.info("DEFAULT ADMIN CREDENTIALS")
            logger.info("=" * 70)
            logger.warning(f"Username: {config.DEFAULT_ADMIN_USERNAME}")
            logger.warning(f"Password: {config.DEFAULT_ADMIN_PASSWORD}")
            logger.warning("⚠️  CHANGE THIS PASSWORD IMMEDIATELY IN PRODUCTION!")
            logger.info("=" * 70)

        # Create initial app version
        logger.info("\nCreating initial app version...")
        create_initial_app_version(db)

        # Summary
        logger.info("\n" + "=" * 70)
        logger.success("✓ SETUP COMPLETE")
        logger.info("=" * 70)

        # Count records
        total_users = db.query(User).count()
        total_versions = db.query(AppVersion).count()

        logger.info(f"Total users: {total_users}")
        logger.info(f"Total app versions: {total_versions}")

        logger.info("\nNext steps:")
        logger.info("1. Start the server: python3 server/main.py")
        logger.info("2. Start the admin dashboard: python3 run_admin_dashboard.py")
        logger.info("3. Login with admin credentials")
        logger.info("4. Create additional users via admin dashboard")

    except Exception as e:
        logger.exception(f"Setup failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
