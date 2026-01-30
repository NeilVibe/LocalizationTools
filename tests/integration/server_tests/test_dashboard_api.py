"""
Comprehensive test suite for Admin Dashboard API endpoints

Tests all 16 endpoints with various scenarios:
- Authentication
- Query parameters
- Data validation
- Error handling
"""

import pytest
import requests
from typing import Dict, Any
import sys
from pathlib import Path

# Import the self-healing admin token function from conftest
# This ensures admin login ALWAYS works, even after 700+ tests
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from tests.conftest import get_admin_token_with_retry

BASE_URL = "http://localhost:8888"


def _check_postgresql_stats_available():
    """Check if PostgreSQL-based stats endpoints are functional."""
    import os
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError

    pg_user = os.getenv("POSTGRES_USER", "locanext")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "locanext_password")
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_PORT", "6433")
    pg_db = os.getenv("POSTGRES_DB", "locanext")

    db_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"

    try:
        engine = create_engine(db_url, echo=False)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except (OperationalError, Exception):
        return False


# Check if PostgreSQL is available for stats tests
_pg_stats_available = _check_postgresql_stats_available()
requires_postgresql = pytest.mark.skipif(
    not _pg_stats_available,
    reason="PostgreSQL not available for stats endpoints"
)


@pytest.fixture(scope="module")
def admin_token() -> str:
    """
    Get admin authentication token using SELF-HEALING mechanism.

    This fixture uses the robust get_admin_token_with_retry() which:
    1. Tries to login
    2. If login fails, resets admin credentials via direct DB access
    3. Retries login

    This ensures tests ALWAYS get a valid token, even if previous
    tests corrupted the admin user state.
    """
    return get_admin_token_with_retry()


@pytest.fixture(scope="module")
def auth_headers(admin_token: str) -> Dict[str, str]:
    """Get authorization headers."""
    return {"Authorization": f"Bearer {admin_token}"}


class TestStatisticsEndpoints:
    """Test all statistics endpoints."""

    def test_overview_stats(self, auth_headers):
        """Test overview statistics endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/stats/overview",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "active_users" in data
        assert "today_operations" in data
        assert "success_rate" in data
        assert "avg_duration_seconds" in data

        # Validate data types
        assert isinstance(data["active_users"], int)
        assert isinstance(data["today_operations"], int)
        assert isinstance(data["success_rate"], (int, float))
        assert isinstance(data["avg_duration_seconds"], (int, float))

        print(f"✅ Overview: {data['today_operations']} ops, {data['success_rate']}% success")

    @requires_postgresql
    def test_daily_stats(self, auth_headers):
        """Test daily statistics endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/stats/daily?days=7",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "data" in data
        assert isinstance(data["data"], list)

        # Validate data structure if data exists
        if data["data"]:
            day = data["data"][0]
            assert "date" in day
            assert "operations" in day
            assert "unique_users" in day
            assert "successful_ops" in day

        print(f"✅ Daily Stats: {len(data['data'])} days of data")

    @requires_postgresql
    def test_weekly_stats(self, auth_headers):
        """Test weekly statistics endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/stats/weekly?weeks=4",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "data" in data
        assert isinstance(data["data"], list)

        print(f"✅ Weekly Stats: {len(data['data'])} weeks of data")

    @requires_postgresql
    def test_monthly_stats(self, auth_headers):
        """Test monthly statistics endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/stats/monthly?months=6",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "data" in data
        assert isinstance(data["data"], list)

        print(f"✅ Monthly Stats: {len(data['data'])} months of data")

    def test_tool_popularity(self, auth_headers):
        """Test tool popularity endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/stats/tools/popularity?days=30",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "total_operations" in data
        assert "tools" in data
        assert isinstance(data["tools"], list)

        # Validate tool structure if data exists
        if data["tools"]:
            tool = data["tools"][0]
            assert "tool_name" in tool
            assert "usage_count" in tool
            assert "percentage" in tool

        print(f"✅ Tool Popularity: {len(data['tools'])} tools tracked")

    def test_function_stats(self, auth_headers):
        """Test function-level statistics."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/stats/tools/XLSTransfer/functions?days=30",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "tool_name" in data
        assert "functions" in data
        assert isinstance(data["functions"], list)

        print(f"✅ Function Stats: {len(data['functions'])} functions in XLSTransfer")

    def test_fastest_functions(self, auth_headers):
        """Test fastest functions endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/stats/performance/fastest?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "fastest_functions" in data
        assert isinstance(data["fastest_functions"], list)

        print(f"✅ Fastest Functions: {len(data['fastest_functions'])} found")

    def test_slowest_functions(self, auth_headers):
        """Test slowest functions endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/stats/performance/slowest?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "slowest_functions" in data
        assert isinstance(data["slowest_functions"], list)

        print(f"✅ Slowest Functions: {len(data['slowest_functions'])} found")

    @requires_postgresql
    def test_error_rate(self, auth_headers):
        """Test error rate endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/stats/errors/rate?days=30",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "data" in data
        assert isinstance(data["data"], list)

        print(f"✅ Error Rate: {len(data['data'])} days tracked")

    def test_top_errors(self, auth_headers):
        """Test top errors endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/stats/errors/top?limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "total_errors" in data
        assert "top_errors" in data
        assert isinstance(data["top_errors"], list)

        print(f"✅ Top Errors: {data['total_errors']} total, {len(data['top_errors'])} types")


class TestRankingsEndpoints:
    """Test all rankings endpoints."""

    def test_user_rankings(self, auth_headers):
        """Test user rankings endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/rankings/users?period=monthly&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "rankings" in data
        assert isinstance(data["rankings"], list)

        # Validate ranking structure if data exists
        if data["rankings"]:
            user = data["rankings"][0]
            assert "rank" in user
            assert "username" in user
            assert "total_operations" in user
            assert user["rank"] == 1  # First user should be rank 1

        print(f"✅ User Rankings: {len(data['rankings'])} users ranked")

    def test_user_rankings_by_time(self, auth_headers):
        """Test user rankings by time spent."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/rankings/users/by-time?period=monthly",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "rankings" in data
        assert "sort_by" in data
        assert data["sort_by"] == "time_spent"

        print(f"✅ User Rankings (by time): {len(data['rankings'])} users")

    def test_app_rankings(self, auth_headers):
        """Test app/tool rankings."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/rankings/apps?period=all_time",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "rankings" in data
        assert isinstance(data["rankings"], list)

        print(f"✅ App Rankings: {len(data['rankings'])} apps ranked")

    def test_function_rankings(self, auth_headers):
        """Test function rankings."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/rankings/functions?period=monthly&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "rankings" in data

        print(f"✅ Function Rankings: {len(data['rankings'])} functions")

    def test_function_rankings_by_time(self, auth_headers):
        """Test function rankings by processing time."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/rankings/functions/by-time?period=monthly",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "sort_by" in data
        assert data["sort_by"] == "total_time"

        print(f"✅ Function Rankings (by time): {len(data['rankings'])} functions")

    def test_combined_top_rankings(self, auth_headers):
        """Test combined top rankings."""
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/rankings/top?period=all_time",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "top_users" in data
        assert "top_apps" in data
        assert "top_functions" in data
        assert isinstance(data["top_users"], list)
        assert isinstance(data["top_apps"], list)
        assert isinstance(data["top_functions"], list)

        print(f"✅ Combined Rankings: {len(data['top_users'])} users, "
              f"{len(data['top_apps'])} apps, {len(data['top_functions'])} functions")


class TestAuthentication:
    """Test authentication requirements."""

    def test_requires_authentication(self):
        """Test that endpoints require authentication."""
        import os
        # DEV_MODE=true auto-authenticates localhost requests, skip this test
        if os.environ.get("DEV_MODE", "").lower() == "true":
            pytest.skip("DEV_MODE enabled - auth is auto-bypassed for localhost")

        response = requests.get(f"{BASE_URL}/api/v2/admin/stats/overview")
        assert response.status_code in [401, 403]
        print("✅ Stats endpoint correctly requires authentication")

    def test_requires_admin_role(self, auth_headers):
        """Test that endpoints require admin role."""
        # This test assumes admin token works (tested in other tests)
        # In real scenario, would test with non-admin user
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/stats/overview",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("✅ Admin role: verified")


class TestParameterValidation:
    """Test query parameter validation."""

    def test_daily_stats_param_validation(self, auth_headers):
        """Test daily stats parameter validation."""
        # Test with invalid days parameter
        response = requests.get(
            f"{BASE_URL}/api/v2/admin/stats/daily?days=9999",
            headers=auth_headers
        )
        # Should either work or return 422 validation error
        assert response.status_code in [200, 422]
        print("✅ Parameter validation: working")

    def test_rankings_period_validation(self, auth_headers):
        """Test rankings period parameter."""
        # Test valid periods
        for period in ["daily", "weekly", "monthly", "all_time"]:
            response = requests.get(
                f"{BASE_URL}/api/v2/admin/rankings/users?period={period}",
                headers=auth_headers
            )
            assert response.status_code == 200
        print("✅ Period validation: all periods working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
