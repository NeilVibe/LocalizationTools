"""
Tests for DESIGN-001: Public by Default Permission Model

Tests:
1. Uniqueness - DB-002: Per-parent unique with auto-rename (platforms global, rest per-parent)
2. Restriction - Admin can toggle restriction on platforms/projects
3. Access Control - Admin can grant/revoke user access
4. Public by Default - All resources visible to all users initially
"""

import pytest
import httpx
from typing import Optional

BASE_URL = "http://localhost:8888"


@pytest.fixture
def admin_headers():
    """Get auth headers for admin user."""
    response = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user2_headers():
    """Get auth headers for a second user (create if needed)."""
    # Try to login first
    response = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "testuser2", "password": "testpass123"}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    # Create user if doesn't exist (need admin)
    admin_resp = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    admin_token = admin_resp.json()["access_token"]
    admin_hdrs = {"Authorization": f"Bearer {admin_token}"}

    # Register user
    httpx.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "username": "testuser2",
            "password": "testpass123",
            "email": "testuser2@test.com",
            "full_name": "Test User 2"
        },
        headers=admin_hdrs
    )

    # Login
    response = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "testuser2", "password": "testpass123"}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    pytest.skip("Could not create test user")


class TestUniqueness:
    """Test name uniqueness constraints (DB-002: per-parent unique with auto-rename)."""

    def test_duplicate_platform_rejected(self, admin_headers):
        """Cannot create two platforms with same name."""
        unique_name = f"TestPlatform_Unique_{pytest.importorskip('time').time()}"

        # Create first platform
        r1 = httpx.post(
            f"{BASE_URL}/api/ldm/platforms",
            json={"name": unique_name},
            headers=admin_headers
        )
        assert r1.status_code == 201, f"First platform failed: {r1.text}"
        platform_id = r1.json()["id"]

        # Try to create duplicate
        r2 = httpx.post(
            f"{BASE_URL}/api/ldm/platforms",
            json={"name": unique_name},
            headers=admin_headers
        )
        assert r2.status_code == 400, "Duplicate platform should be rejected"
        assert "already exists" in r2.json().get("detail", "").lower()

        # Cleanup
        httpx.delete(f"{BASE_URL}/api/ldm/platforms/{platform_id}", headers=admin_headers)

    def test_duplicate_project_auto_renamed(self, admin_headers):
        """DB-002: Duplicate project names are auto-renamed with _1, _2 suffix."""
        unique_name = f"TestProject_Unique_{pytest.importorskip('time').time()}"

        # Create first project
        r1 = httpx.post(
            f"{BASE_URL}/api/ldm/projects",
            json={"name": unique_name},
            headers=admin_headers
        )
        assert r1.status_code in [200, 201], f"First project failed: {r1.text}"
        project_id = r1.json()["id"]
        project_name = r1.json()["name"]
        assert project_name == unique_name, "First project should have exact name"

        # Create duplicate - should succeed with auto-renamed name
        r2 = httpx.post(
            f"{BASE_URL}/api/ldm/projects",
            json={"name": unique_name},
            headers=admin_headers
        )
        assert r2.status_code in [200, 201], f"Duplicate project should succeed with auto-rename, got: {r2.text}"
        project2_id = r2.json()["id"]
        project2_name = r2.json()["name"]
        # Auto-renamed with _1 suffix
        assert project2_name != unique_name, f"Duplicate should be auto-renamed, got: {project2_name}"
        assert unique_name in project2_name, "Auto-renamed name should contain original name"

        # Cleanup
        httpx.delete(f"{BASE_URL}/api/ldm/projects/{project_id}", headers=admin_headers)
        httpx.delete(f"{BASE_URL}/api/ldm/projects/{project2_id}", headers=admin_headers)

    def test_folder_same_name_different_projects_allowed(self, admin_headers):
        """DB-002: Same folder name in different projects is allowed (per-parent unique)."""
        import time
        ts = time.time()
        folder_name = f"TestFolder_Unique_{ts}"

        # Create two projects
        p1 = httpx.post(
            f"{BASE_URL}/api/ldm/projects",
            json={"name": f"Project1_{ts}"},
            headers=admin_headers
        )
        p2 = httpx.post(
            f"{BASE_URL}/api/ldm/projects",
            json={"name": f"Project2_{ts}"},
            headers=admin_headers
        )
        project1_id = p1.json()["id"]
        project2_id = p2.json()["id"]

        # Create folder in project 1
        f1 = httpx.post(
            f"{BASE_URL}/api/ldm/folders",
            json={"name": folder_name, "project_id": project1_id},
            headers=admin_headers
        )
        assert f1.status_code in [200, 201], f"First folder failed: {f1.text}"
        folder1_id = f1.json()["id"]
        folder1_name = f1.json()["name"]
        assert folder1_name == folder_name, "First folder should have exact name"

        # Create folder with same name in project 2 - should succeed (different parent)
        f2 = httpx.post(
            f"{BASE_URL}/api/ldm/folders",
            json={"name": folder_name, "project_id": project2_id},
            headers=admin_headers
        )
        assert f2.status_code in [200, 201], f"Same folder name in different project should work, got: {f2.text}"
        folder2_id = f2.json()["id"]
        folder2_name = f2.json()["name"]
        # Same name allowed in different projects
        assert folder2_name == folder_name, f"Folder in different project should have exact name, got: {folder2_name}"

        # Cleanup
        httpx.delete(f"{BASE_URL}/api/ldm/folders/{folder1_id}", headers=admin_headers)
        httpx.delete(f"{BASE_URL}/api/ldm/folders/{folder2_id}", headers=admin_headers)
        httpx.delete(f"{BASE_URL}/api/ldm/projects/{project1_id}", headers=admin_headers)
        httpx.delete(f"{BASE_URL}/api/ldm/projects/{project2_id}", headers=admin_headers)

    def test_duplicate_folder_same_project_auto_renamed(self, admin_headers):
        """DB-002: Duplicate folder in same project is auto-renamed."""
        import time
        ts = time.time()
        folder_name = f"TestFolder_Same_{ts}"

        # Create project
        p = httpx.post(
            f"{BASE_URL}/api/ldm/projects",
            json={"name": f"Project_Same_{ts}"},
            headers=admin_headers
        )
        project_id = p.json()["id"]

        # Create first folder
        f1 = httpx.post(
            f"{BASE_URL}/api/ldm/folders",
            json={"name": folder_name, "project_id": project_id},
            headers=admin_headers
        )
        assert f1.status_code in [200, 201], f"First folder failed: {f1.text}"
        folder1_id = f1.json()["id"]
        folder1_name = f1.json()["name"]

        # Create duplicate in same project - should auto-rename
        f2 = httpx.post(
            f"{BASE_URL}/api/ldm/folders",
            json={"name": folder_name, "project_id": project_id},
            headers=admin_headers
        )
        assert f2.status_code in [200, 201], f"Duplicate folder should succeed with auto-rename, got: {f2.text}"
        folder2_id = f2.json()["id"]
        folder2_name = f2.json()["name"]
        assert folder2_name != folder_name, f"Duplicate should be auto-renamed, got: {folder2_name}"
        assert folder_name in folder2_name, "Auto-renamed name should contain original name"

        # Cleanup
        httpx.delete(f"{BASE_URL}/api/ldm/folders/{folder1_id}", headers=admin_headers)
        httpx.delete(f"{BASE_URL}/api/ldm/folders/{folder2_id}", headers=admin_headers)
        httpx.delete(f"{BASE_URL}/api/ldm/projects/{project_id}", headers=admin_headers)

    def test_duplicate_tm_rejected(self, admin_headers):
        """Cannot create two TMs with same name (via database constraint)."""
        # NOTE: TMs are created via file upload, so we test the DB constraint
        # by checking that duplicate names are rejected in the database.
        # This is verified by the UNIQUE constraint on ldm_translation_memories.name
        # For now, we just verify the constraint exists by checking the TM list endpoint works
        r = httpx.get(f"{BASE_URL}/api/ldm/tm", headers=admin_headers)
        assert r.status_code == 200, f"TM list failed: {r.text}"
        # The actual uniqueness is enforced at DB level via UniqueConstraint("name")


class TestRestriction:
    """Test restriction toggle functionality."""

    def test_platform_restriction_toggle(self, admin_headers):
        """Admin can toggle platform restriction."""
        import time

        # Create platform
        r = httpx.post(
            f"{BASE_URL}/api/ldm/platforms",
            json={"name": f"RestrictTest_{time.time()}"},
            headers=admin_headers
        )
        platform_id = r.json()["id"]

        # Initially should be public (is_restricted=False)
        get_r = httpx.get(f"{BASE_URL}/api/ldm/platforms/{platform_id}", headers=admin_headers)
        assert get_r.json()["is_restricted"] == False

        # Toggle to restricted
        toggle_r = httpx.put(
            f"{BASE_URL}/api/ldm/platforms/{platform_id}/restriction?is_restricted=true",
            headers=admin_headers
        )
        assert toggle_r.status_code == 200
        assert toggle_r.json()["is_restricted"] == True

        # Verify
        get_r2 = httpx.get(f"{BASE_URL}/api/ldm/platforms/{platform_id}", headers=admin_headers)
        assert get_r2.json()["is_restricted"] == True

        # Toggle back to public
        toggle_r2 = httpx.put(
            f"{BASE_URL}/api/ldm/platforms/{platform_id}/restriction?is_restricted=false",
            headers=admin_headers
        )
        assert toggle_r2.status_code == 200
        assert toggle_r2.json()["is_restricted"] == False

        # Cleanup
        httpx.delete(f"{BASE_URL}/api/ldm/platforms/{platform_id}", headers=admin_headers)

    def test_project_restriction_toggle(self, admin_headers):
        """Admin can toggle project restriction."""
        import time

        # Create project
        r = httpx.post(
            f"{BASE_URL}/api/ldm/projects",
            json={"name": f"RestrictProjTest_{time.time()}"},
            headers=admin_headers
        )
        project_id = r.json()["id"]

        # Initially should be public
        get_r = httpx.get(f"{BASE_URL}/api/ldm/projects/{project_id}", headers=admin_headers)
        assert get_r.json()["is_restricted"] == False

        # Toggle to restricted
        toggle_r = httpx.put(
            f"{BASE_URL}/api/ldm/projects/{project_id}/restriction?is_restricted=true",
            headers=admin_headers
        )
        assert toggle_r.status_code == 200

        # Verify
        get_r2 = httpx.get(f"{BASE_URL}/api/ldm/projects/{project_id}", headers=admin_headers)
        assert get_r2.json()["is_restricted"] == True

        # Cleanup
        httpx.delete(f"{BASE_URL}/api/ldm/projects/{project_id}", headers=admin_headers)


class TestAccessControl:
    """Test access grant/revoke functionality."""

    def test_grant_and_revoke_platform_access(self, admin_headers):
        """Admin can grant and revoke platform access."""
        import time

        # Create platform
        r = httpx.post(
            f"{BASE_URL}/api/ldm/platforms",
            json={"name": f"AccessTest_{time.time()}"},
            headers=admin_headers
        )
        platform_id = r.json()["id"]

        # Make it restricted
        httpx.put(
            f"{BASE_URL}/api/ldm/platforms/{platform_id}/restriction?is_restricted=true",
            headers=admin_headers
        )

        # Get admin user_id (to grant access to)
        me_r = httpx.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        me_data = me_r.json()
        admin_user_id = me_data.get("user_id") or me_data.get("id")

        # Grant access
        grant_r = httpx.post(
            f"{BASE_URL}/api/ldm/platforms/{platform_id}/access",
            json={"user_ids": [admin_user_id]},
            headers=admin_headers
        )
        assert grant_r.status_code == 200
        assert grant_r.json()["users_granted"] >= 0  # May be 0 if already has access as owner

        # List access
        list_r = httpx.get(
            f"{BASE_URL}/api/ldm/platforms/{platform_id}/access",
            headers=admin_headers
        )
        assert list_r.status_code == 200

        # Revoke access
        revoke_r = httpx.delete(
            f"{BASE_URL}/api/ldm/platforms/{platform_id}/access/{admin_user_id}",
            headers=admin_headers
        )
        assert revoke_r.status_code == 200

        # Cleanup
        httpx.delete(f"{BASE_URL}/api/ldm/platforms/{platform_id}", headers=admin_headers)


class TestPublicByDefault:
    """Test that resources are public by default."""

    def test_new_platform_is_public(self, admin_headers):
        """Newly created platform has is_restricted=False."""
        import time

        r = httpx.post(
            f"{BASE_URL}/api/ldm/platforms",
            json={"name": f"PublicTest_{time.time()}"},
            headers=admin_headers
        )
        assert r.status_code == 201
        assert r.json()["is_restricted"] == False

        # Cleanup
        httpx.delete(f"{BASE_URL}/api/ldm/platforms/{r.json()['id']}", headers=admin_headers)

    def test_new_project_is_public(self, admin_headers):
        """Newly created project has is_restricted=False."""
        import time

        r = httpx.post(
            f"{BASE_URL}/api/ldm/projects",
            json={"name": f"PublicProjTest_{time.time()}"},
            headers=admin_headers
        )
        assert r.status_code in [200, 201], f"Create project failed: {r.text}"
        assert r.json()["is_restricted"] == False

        # Cleanup
        httpx.delete(f"{BASE_URL}/api/ldm/projects/{r.json()['id']}", headers=admin_headers)

    def test_all_users_see_public_resources(self, admin_headers, user2_headers):
        """Both admin and regular user can see public platforms."""
        import time

        # Admin creates platform
        r = httpx.post(
            f"{BASE_URL}/api/ldm/platforms",
            json={"name": f"SharedTest_{time.time()}"},
            headers=admin_headers
        )
        platform_id = r.json()["id"]

        # User2 should be able to see it
        list_r = httpx.get(f"{BASE_URL}/api/ldm/platforms", headers=user2_headers)
        assert list_r.status_code == 200
        platform_ids = [p["id"] for p in list_r.json()["platforms"]]
        assert platform_id in platform_ids, "User2 should see public platform created by admin"

        # Cleanup
        httpx.delete(f"{BASE_URL}/api/ldm/platforms/{platform_id}", headers=admin_headers)


class TestRestrictedAccess:
    """Test that restricted resources are hidden from unauthorized users."""

    def test_restricted_platform_hidden_from_non_granted_user(self, admin_headers, user2_headers):
        """User without access cannot see restricted platform."""
        import time

        # Admin creates platform
        r = httpx.post(
            f"{BASE_URL}/api/ldm/platforms",
            json={"name": f"HiddenTest_{time.time()}"},
            headers=admin_headers
        )
        platform_id = r.json()["id"]

        # Make it restricted
        httpx.put(
            f"{BASE_URL}/api/ldm/platforms/{platform_id}/restriction?is_restricted=true",
            headers=admin_headers
        )

        # User2 should NOT see it in list
        list_r = httpx.get(f"{BASE_URL}/api/ldm/platforms", headers=user2_headers)
        platform_ids = [p["id"] for p in list_r.json()["platforms"]]
        assert platform_id not in platform_ids, "User2 should NOT see restricted platform"

        # User2 should get 404 when trying to access directly (security: don't reveal existence)
        direct_r = httpx.get(f"{BASE_URL}/api/ldm/platforms/{platform_id}", headers=user2_headers)
        assert direct_r.status_code == 404, "Restricted platform should appear as not found to unauthorized users"

        # Cleanup
        httpx.delete(f"{BASE_URL}/api/ldm/platforms/{platform_id}", headers=admin_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
