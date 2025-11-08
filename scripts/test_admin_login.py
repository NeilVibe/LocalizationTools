#!/usr/bin/env python3
"""
Test Admin Login

Test the admin login flow via API to verify authentication works.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from server.database.db_setup import get_session_maker, create_database_engine
from server.database.models import User
from server.utils.auth import verify_password, create_access_token, verify_token
from server import config


def test_admin_login():
    """Test admin login functionality."""
    logger.info("=" * 70)
    logger.info("TESTING ADMIN LOGIN")
    logger.info("=" * 70)

    # Setup database
    use_postgres = config.DATABASE_TYPE == "postgresql"
    engine = create_database_engine(use_postgres=use_postgres, echo=False)
    session_maker = get_session_maker(engine)
    db = session_maker()

    try:
        # Step 1: Find admin user
        logger.info("\n1. Finding admin user in database...")
        admin = db.query(User).filter(User.username == config.DEFAULT_ADMIN_USERNAME).first()

        if not admin:
            logger.error(f"❌ Admin user '{config.DEFAULT_ADMIN_USERNAME}' not found!")
            logger.error("Run: python3 scripts/create_admin.py")
            return False

        logger.success(f"✓ Admin user found: {admin.username} (ID: {admin.user_id}, Role: {admin.role})")

        # Step 2: Verify password
        logger.info("\n2. Testing password verification...")
        password_correct = verify_password(config.DEFAULT_ADMIN_PASSWORD, admin.password_hash)

        if not password_correct:
            logger.error("❌ Password verification FAILED!")
            return False

        logger.success("✓ Password verification PASSED")

        # Step 3: Create JWT token
        logger.info("\n3. Creating JWT access token...")
        token_data = {
            "user_id": admin.user_id,
            "username": admin.username,
            "role": admin.role
        }
        access_token = create_access_token(token_data)

        logger.success(f"✓ JWT token created (length: {len(access_token)} chars)")
        logger.info(f"Token preview: {access_token[:50]}...")

        # Step 4: Verify JWT token
        logger.info("\n4. Verifying JWT token...")
        decoded_token = verify_token(access_token)

        if not decoded_token:
            logger.error("❌ Token verification FAILED!")
            return False

        logger.success("✓ Token verification PASSED")
        logger.info(f"Decoded token data: user_id={decoded_token.get('user_id')}, username={decoded_token.get('username')}, role={decoded_token.get('role')}")

        # Step 5: Simulate login flow
        logger.info("\n5. Simulating complete login flow...")

        # Check user active status
        if not admin.is_active:
            logger.error("❌ User account is inactive!")
            return False

        logger.success("✓ User is active")
        logger.success("✓ Login flow simulation PASSED")

        # Summary
        logger.info("\n" + "=" * 70)
        logger.success("✅ ALL TESTS PASSED")
        logger.info("=" * 70)

        logger.info("\nAdmin credentials are working correctly:")
        logger.info(f"  Username: {config.DEFAULT_ADMIN_USERNAME}")
        logger.info(f"  Password: {config.DEFAULT_ADMIN_PASSWORD}")
        logger.info(f"  Role: {admin.role}")
        logger.info(f"  User ID: {admin.user_id}")

        logger.info("\nYou can now:")
        logger.info("1. Start the server: python3 server/main.py")
        logger.info("2. Login via API: POST /api/auth/login")
        logger.info("3. Access admin dashboard: python3 run_admin_dashboard.py")

        return True

    except Exception as e:
        logger.exception(f"Test failed: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_admin_login()
    sys.exit(0 if success else 1)
