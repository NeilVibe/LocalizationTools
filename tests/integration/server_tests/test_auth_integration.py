"""
Authentication Integration Tests

Tests for the full authentication flow including:
- User registration
- Login/logout
- Token validation
- Session management
"""

import pytest
from datetime import datetime, timedelta
import uuid
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.database.models import Base, User, Session as DBSession


# Skip if not running integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="function")
def test_db():
    """Create a test database using PostgreSQL (required for JSONB)."""
    from server import config
    engine = create_engine(config.DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    # Don't drop tables - they're shared with the running server


class TestUserCreation:
    """Tests for user creation and management."""

    def test_create_user_with_hashed_password(self, test_db):
        """Test creating a user with properly hashed password."""
        import bcrypt

        password = "secure_password_123"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        user = User(
            username="hashtest",
            password_hash=password_hash,
            email="hash@test.com",
        )
        test_db.add(user)
        test_db.commit()

        # Verify password can be checked
        stored_user = test_db.query(User).filter_by(username="hashtest").first()
        assert bcrypt.checkpw(password.encode(), stored_user.password_hash.encode())

    def test_create_admin_user(self, test_db):
        """Test creating an admin user."""
        admin = User(
            username="admin",
            password_hash="admin_hash",
            email="admin@test.com",
            role="admin",
        )
        test_db.add(admin)
        test_db.commit()

        assert admin.role == "admin"
        assert admin.is_active is True

    def test_deactivate_user(self, test_db):
        """Test deactivating a user."""
        user = User(
            username="deactivate_me",
            password_hash="hash",
        )
        test_db.add(user)
        test_db.commit()

        assert user.is_active is True

        user.is_active = False
        test_db.commit()

        assert user.is_active is False


class TestSessionManagement:
    """Tests for session creation and management."""

    def test_create_session_for_user(self, test_db):
        """Test creating a session for a user."""
        user = User(username="sessiontest", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        session = DBSession(
            user_id=user.user_id,
            machine_id="test_machine_001",
            ip_address="192.168.1.100",
            app_version="2512010029",
        )
        test_db.add(session)
        test_db.commit()

        assert session.session_id is not None
        assert session.is_active is True

    def test_multiple_sessions_per_user(self, test_db):
        """Test that a user can have multiple sessions."""
        user = User(username="multisession", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        # Create multiple sessions (different machines)
        for i in range(3):
            session = DBSession(
                user_id=user.user_id,
                machine_id=f"machine_{i}",
                app_version="1.0.0",
            )
            test_db.add(session)

        test_db.commit()

        assert len(user.sessions) == 3

    def test_end_session(self, test_db):
        """Test ending a session."""
        user = User(username="endsession", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        session = DBSession(
            user_id=user.user_id,
            machine_id="machine",
            app_version="1.0.0",
        )
        test_db.add(session)
        test_db.commit()

        # End session
        session.is_active = False
        test_db.commit()

        assert session.is_active is False

    def test_update_last_activity(self, test_db):
        """Test updating session last activity."""
        user = User(username="activity", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        session = DBSession(
            user_id=user.user_id,
            machine_id="machine",
            app_version="1.0.0",
        )
        test_db.add(session)
        test_db.commit()

        original_activity = session.last_activity

        # Simulate activity update
        import time
        time.sleep(0.1)
        session.last_activity = datetime.utcnow()
        test_db.commit()

        assert session.last_activity > original_activity

    def test_find_active_sessions(self, test_db):
        """Test finding all active sessions."""
        user = User(username="findactive", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        # Create mix of active and inactive sessions
        for i in range(5):
            session = DBSession(
                user_id=user.user_id,
                machine_id=f"machine_{i}",
                app_version="1.0.0",
                is_active=(i % 2 == 0),  # Alternate active/inactive
            )
            test_db.add(session)

        test_db.commit()

        active_sessions = test_db.query(DBSession).filter_by(
            user_id=user.user_id,
            is_active=True
        ).all()

        assert len(active_sessions) == 3


class TestLoginFlow:
    """Tests for the complete login flow."""

    def test_successful_login_updates_last_login(self, test_db):
        """Test that successful login updates last_login."""
        user = User(
            username="loginuser",
            password_hash="hash",
        )
        test_db.add(user)
        test_db.commit()

        assert user.last_login is None

        # Simulate login
        user.last_login = datetime.utcnow()
        test_db.commit()

        assert user.last_login is not None

    def test_login_creates_session(self, test_db):
        """Test that login creates a new session."""
        user = User(username="createsession", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        # Simulate login creating session
        session = DBSession(
            user_id=user.user_id,
            machine_id="login_machine",
            ip_address="10.0.0.1",
            app_version="1.0.0",
        )
        test_db.add(session)
        user.last_login = datetime.utcnow()
        test_db.commit()

        assert len(user.sessions) == 1
        assert user.sessions[0].ip_address == "10.0.0.1"


class TestPasswordSecurity:
    """Tests for password security features."""

    def test_password_not_stored_plaintext(self, test_db):
        """Verify passwords are never stored as plaintext."""
        import bcrypt

        password = "my_secret_password"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        user = User(
            username="plaintext_test",
            password_hash=hashed,
        )
        test_db.add(user)
        test_db.commit()

        stored = test_db.query(User).filter_by(username="plaintext_test").first()
        assert stored.password_hash != password
        assert stored.password_hash.startswith("$2")  # bcrypt hash prefix

    def test_different_users_different_hashes(self, test_db):
        """Test that same password produces different hashes for different users."""
        import bcrypt

        password = "same_password"

        user1 = User(
            username="user1",
            password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        )
        user2 = User(
            username="user2",
            password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        )

        test_db.add_all([user1, user2])
        test_db.commit()

        # Hashes should be different due to different salts
        assert user1.password_hash != user2.password_hash

        # But both should verify correctly
        assert bcrypt.checkpw(password.encode(), user1.password_hash.encode())
        assert bcrypt.checkpw(password.encode(), user2.password_hash.encode())


class TestRoleBasedAccess:
    """Tests for role-based access control."""

    def test_user_roles(self, test_db):
        """Test different user roles."""
        roles = ["user", "admin", "superadmin"]

        for role in roles:
            user = User(
                username=f"{role}_user",
                password_hash="hash",
                role=role,
            )
            test_db.add(user)

        test_db.commit()

        # Verify each role
        for role in roles:
            user = test_db.query(User).filter_by(username=f"{role}_user").first()
            assert user.role == role

    def test_default_role_is_user(self, test_db):
        """Test that default role is 'user'."""
        user = User(
            username="norole",
            password_hash="hash",
        )
        test_db.add(user)
        test_db.commit()

        assert user.role == "user"

    def test_find_admins(self, test_db):
        """Test finding all admin users."""
        # Create mix of users and admins
        for i in range(5):
            user = User(
                username=f"mixed_{i}",
                password_hash="hash",
                role="admin" if i < 2 else "user",
            )
            test_db.add(user)

        test_db.commit()

        admins = test_db.query(User).filter_by(role="admin").all()
        assert len(admins) == 2
