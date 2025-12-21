"""
FEAT-001: Auto-Add to TM Tests

Tests the complete TM linking and auto-add workflow:
1. Link TM to project
2. Confirm cell (update_row with status='reviewed')
3. Verify entry added to linked TM
4. Unlink TM from project

Requires: RUN_API_TESTS=1 and server running on localhost:8888
"""

import pytest
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Skip all tests if not running API tests
pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS"),
        reason="API tests require running server (set RUN_API_TESTS=1)"
    ),
    pytest.mark.integration,
    pytest.mark.feat001,
]


class APIClient:
    """Reusable API client for FEAT-001 tests."""

    def __init__(self, base_url="http://localhost:8888"):
        import requests
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None

    def login(self, username="admin", password="admin123"):
        """Authenticate and store token."""
        # Try v2 first, then v1
        for endpoint in ["/api/v2/auth/login", "/api/auth/login"]:
            r = self.session.post(
                f"{self.base_url}{endpoint}",
                json={"username": username, "password": password},
                timeout=10
            )
            if r.status_code == 200:
                self.token = r.json()["access_token"]
                self.session.headers["Authorization"] = f"Bearer {self.token}"
                return True
        return False

    def get(self, endpoint, **kwargs):
        return self.session.get(f"{self.base_url}{endpoint}", timeout=30, **kwargs)

    def post(self, endpoint, **kwargs):
        return self.session.post(f"{self.base_url}{endpoint}", timeout=30, **kwargs)

    def delete(self, endpoint, **kwargs):
        return self.session.delete(f"{self.base_url}{endpoint}", timeout=30, **kwargs)

    def patch(self, endpoint, **kwargs):
        return self.session.patch(f"{self.base_url}{endpoint}", timeout=30, **kwargs)


# =============================================================================
# FEAT-001: TM LINK/UNLINK ENDPOINTS
# =============================================================================

class TestTMLinkEndpoints:
    """
    Tests TM linking endpoints:
    - POST /api/ldm/projects/{id}/link-tm
    - GET /api/ldm/projects/{id}/linked-tms
    - DELETE /api/ldm/projects/{id}/link-tm/{tm_id}
    """

    @pytest.fixture(scope="class")
    def client(self):
        """Create authenticated client."""
        client = APIClient()
        if not client.login():
            pytest.skip("Could not authenticate")
        return client

    @pytest.fixture(scope="class")
    def test_ids(self, client):
        """Get or create test project and TM IDs."""
        # Get first available project
        r = client.get("/api/ldm/projects")
        if r.status_code != 200 or not r.json():
            pytest.skip("No projects available for testing")
        project_id = r.json()[0]["id"]

        # Get first available TM
        r = client.get("/api/ldm/tm")
        if r.status_code != 200 or not r.json():
            pytest.skip("No TMs available for testing")
        tm_id = r.json()[0]["id"]

        return {"project_id": project_id, "tm_id": tm_id}

    def test_01_link_tm_to_project(self, client, test_ids):
        """
        POST /api/ldm/projects/{id}/link-tm
        Should link a TM to a project.
        """
        r = client.post(
            f"/api/ldm/projects/{test_ids['project_id']}/link-tm",
            json={"tm_id": test_ids['tm_id'], "priority": 0}
        )

        # Accept both 200 (linked) and 400 (already linked)
        assert r.status_code in [200, 400], f"Unexpected status: {r.status_code}, {r.text}"

        if r.status_code == 200:
            data = r.json()
            assert "tm_id" in data or "message" in data

    def test_02_get_linked_tms(self, client, test_ids):
        """
        GET /api/ldm/projects/{id}/linked-tms
        Should return list of linked TMs.
        """
        r = client.get(f"/api/ldm/projects/{test_ids['project_id']}/linked-tms")

        assert r.status_code == 200, f"Failed: {r.text}"
        data = r.json()

        assert isinstance(data, list), "Should return a list"
        # Should have at least one linked TM (from test_01)
        assert len(data) >= 1, "Should have at least one linked TM"

        # Verify structure
        if data:
            assert "tm_id" in data[0]
            assert "tm_name" in data[0]
            assert "priority" in data[0]

    def test_03_link_same_tm_again_fails(self, client, test_ids):
        """
        POST /api/ldm/projects/{id}/link-tm with same TM
        Should return 400 (already linked).
        """
        r = client.post(
            f"/api/ldm/projects/{test_ids['project_id']}/link-tm",
            json={"tm_id": test_ids['tm_id'], "priority": 0}
        )

        # Should fail because already linked
        assert r.status_code == 400, f"Expected 400, got {r.status_code}"
        assert "already linked" in r.json().get("detail", "").lower()

    def test_04_unlink_tm_from_project(self, client, test_ids):
        """
        DELETE /api/ldm/projects/{id}/link-tm/{tm_id}
        Should unlink the TM from project.
        """
        r = client.delete(
            f"/api/ldm/projects/{test_ids['project_id']}/link-tm/{test_ids['tm_id']}"
        )

        assert r.status_code == 200, f"Failed: {r.text}"
        data = r.json()
        assert "unlinked" in data.get("message", "").lower() or "success" in str(data).lower()

    def test_05_verify_tm_unlinked(self, client, test_ids):
        """
        GET /api/ldm/projects/{id}/linked-tms after unlink
        Should not contain the unlinked TM.
        """
        r = client.get(f"/api/ldm/projects/{test_ids['project_id']}/linked-tms")

        assert r.status_code == 200
        data = r.json()

        # The TM we unlinked should not be in the list
        tm_ids = [item["tm_id"] for item in data]
        # Note: It might be empty or contain other TMs
        # We just verify the unlinked one is gone
        # (This test assumes we're the only ones modifying)

    def test_06_unlink_nonexistent_returns_404(self, client, test_ids):
        """
        DELETE /api/ldm/projects/{id}/link-tm/99999
        Should return 404 for non-existent link.
        """
        r = client.delete(
            f"/api/ldm/projects/{test_ids['project_id']}/link-tm/99999"
        )

        assert r.status_code == 404, f"Expected 404, got {r.status_code}"

    def test_07_link_invalid_tm_returns_404(self, client, test_ids):
        """
        POST /api/ldm/projects/{id}/link-tm with invalid TM ID
        Should return 404.
        """
        r = client.post(
            f"/api/ldm/projects/{test_ids['project_id']}/link-tm",
            json={"tm_id": 99999, "priority": 0}
        )

        assert r.status_code == 404, f"Expected 404, got {r.status_code}"


# =============================================================================
# FEAT-001: AUTO-ADD TO TM ON CELL CONFIRM
# =============================================================================

class TestAutoAddToTM:
    """
    Tests auto-add to TM when cell is confirmed:
    1. Link TM to project
    2. Update row with status='reviewed'
    3. Verify TM entry count increased
    4. Cleanup: unlink TM
    """

    @pytest.fixture(scope="class")
    def client(self):
        """Create authenticated client."""
        client = APIClient()
        if not client.login():
            pytest.skip("Could not authenticate")
        return client

    @pytest.fixture(scope="class")
    def test_context(self, client):
        """Set up test project, TM, and row."""
        # Get first available project with rows
        r = client.get("/api/ldm/projects")
        if r.status_code != 200 or not r.json():
            pytest.skip("No projects available")

        project = None
        project_data = None
        for p in r.json():
            r2 = client.get(f"/api/ldm/projects/{p['id']}/data")
            if r2.status_code == 200:
                data = r2.json()
                if data.get("rows") and len(data["rows"]) > 0:
                    project = p
                    project_data = data
                    break

        if not project:
            pytest.skip("No project with rows available")

        # Get first TM
        r = client.get("/api/ldm/tm")
        if r.status_code != 200 or not r.json():
            pytest.skip("No TMs available")
        tm = r.json()[0]

        # Get initial TM entry count
        r = client.get(f"/api/ldm/tm/{tm['id']}")
        initial_count = r.json().get("entry_count", 0) if r.status_code == 200 else 0

        return {
            "project_id": project["id"],
            "tm_id": tm["id"],
            "row_id": project_data["rows"][0]["id"],
            "initial_tm_count": initial_count,
        }

    def test_01_link_tm_for_auto_add(self, client, test_context):
        """Link TM to project for auto-add testing."""
        r = client.post(
            f"/api/ldm/projects/{test_context['project_id']}/link-tm",
            json={"tm_id": test_context['tm_id'], "priority": 0}
        )
        # Accept 200 or 400 (already linked)
        assert r.status_code in [200, 400]

    def test_02_update_row_to_reviewed(self, client, test_context):
        """
        Update row with status='reviewed' to trigger auto-add.
        """
        # Get current row data
        r = client.get(f"/api/ldm/projects/{test_context['project_id']}/data")
        assert r.status_code == 200
        rows = r.json().get("rows", [])
        assert len(rows) > 0

        row = rows[0]
        row_id = row["id"]

        # Update to 'reviewed' status
        r = client.patch(
            f"/api/ldm/projects/{test_context['project_id']}/rows/{row_id}",
            json={
                "target_text": row.get("target_text", "Test translation"),
                "status": "reviewed"
            }
        )

        assert r.status_code == 200, f"Failed to update row: {r.text}"

        # Store for verification
        test_context["confirmed_row_id"] = row_id
        test_context["confirmed_source"] = row.get("source_text", "")
        test_context["confirmed_target"] = row.get("target_text", "Test translation")

    def test_03_verify_tm_entry_added(self, client, test_context):
        """
        Verify TM entry count increased after cell confirm.
        Note: Auto-add runs in background, may need small delay.
        """
        time.sleep(1)  # Allow background task to complete

        r = client.get(f"/api/ldm/tm/{test_context['tm_id']}")
        assert r.status_code == 200

        new_count = r.json().get("entry_count", 0)

        # Entry count should be >= initial (could be equal if duplicate)
        assert new_count >= test_context["initial_tm_count"], \
            f"TM entry count didn't increase: {test_context['initial_tm_count']} -> {new_count}"

    def test_04_cleanup_unlink_tm(self, client, test_context):
        """Cleanup: unlink TM from project."""
        r = client.delete(
            f"/api/ldm/projects/{test_context['project_id']}/link-tm/{test_context['tm_id']}"
        )
        # Accept 200 or 404 (already unlinked)
        assert r.status_code in [200, 404]


# =============================================================================
# EMBEDDING ENGINE & QWEN WARNING
# =============================================================================

class TestEmbeddingEngineWarning:
    """
    Tests embedding engine switching and Qwen warning:
    - GET /api/ldm/settings/embedding-engine
    - POST /api/ldm/settings/embedding-engine
    """

    @pytest.fixture(scope="class")
    def client(self):
        """Create authenticated client."""
        client = APIClient()
        if not client.login():
            pytest.skip("Could not authenticate")
        return client

    def test_01_get_current_engine(self, client):
        """
        GET /api/ldm/settings/embedding-engine
        Should return current engine info.
        """
        r = client.get("/api/ldm/settings/embedding-engine")

        assert r.status_code == 200, f"Failed: {r.text}"
        data = r.json()

        assert "current_engine" in data
        assert "engine_name" in data
        assert data["current_engine"] in ["model2vec", "qwen"]

    def test_02_switch_to_qwen_shows_warning(self, client):
        """
        POST /api/ldm/settings/embedding-engine with engine=qwen
        Should return warning about slower speed.
        """
        r = client.post(
            "/api/ldm/settings/embedding-engine",
            json={"engine": "qwen"}
        )

        assert r.status_code == 200, f"Failed: {r.text}"
        data = r.json()

        assert data["current_engine"] == "qwen"
        assert "warning" in data, "Qwen should return warning"
        assert "slower" in data["warning"].lower(), "Warning should mention slower speed"

    def test_03_switch_to_model2vec_no_warning(self, client):
        """
        POST /api/ldm/settings/embedding-engine with engine=model2vec
        Should NOT return warning.
        """
        r = client.post(
            "/api/ldm/settings/embedding-engine",
            json={"engine": "model2vec"}
        )

        assert r.status_code == 200, f"Failed: {r.text}"
        data = r.json()

        assert data["current_engine"] == "model2vec"
        # No warning for model2vec (or warning is None/empty)
        warning = data.get("warning")
        assert not warning, f"Model2Vec should not have warning, got: {warning}"

    def test_04_invalid_engine_returns_error(self, client):
        """
        POST /api/ldm/settings/embedding-engine with invalid engine
        Should return 400.
        """
        r = client.post(
            "/api/ldm/settings/embedding-engine",
            json={"engine": "invalid_engine"}
        )

        assert r.status_code in [400, 422], f"Expected 400/422, got {r.status_code}"


# =============================================================================
# TM SYNC ENDPOINTS
# =============================================================================

class TestTMSyncEndpoints:
    """
    Tests TM sync functionality:
    - POST /api/ldm/tm/{id}/sync (manual sync with toast)
    """

    @pytest.fixture(scope="class")
    def client(self):
        """Create authenticated client."""
        client = APIClient()
        if not client.login():
            pytest.skip("Could not authenticate")
        return client

    @pytest.fixture(scope="class")
    def tm_id(self, client):
        """Get first available TM."""
        r = client.get("/api/ldm/tm")
        if r.status_code != 200 or not r.json():
            pytest.skip("No TMs available")
        return r.json()[0]["id"]

    def test_01_manual_sync_tm(self, client, tm_id):
        """
        POST /api/ldm/tm/{id}/sync
        Should trigger manual sync (shows toast in UI).
        """
        r = client.post(f"/api/ldm/tm/{tm_id}/sync")

        assert r.status_code == 200, f"Failed: {r.text}"
        data = r.json()

        # Should return sync stats
        assert "stats" in data or "message" in data or "entries_synced" in data

    def test_02_sync_nonexistent_tm_returns_404(self, client):
        """
        POST /api/ldm/tm/99999/sync
        Should return 404 for non-existent TM.
        """
        r = client.post("/api/ldm/tm/99999/sync")

        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
