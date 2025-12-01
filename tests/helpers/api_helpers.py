"""
API Test Helpers

Functions for making authenticated API requests and handling auth tokens.
"""

import os
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

import jwt


# Get secret from environment or use default for testing
TEST_SECRET_KEY = os.getenv("SECRET_KEY", "test_secret_key_for_testing_only")


def create_test_token(
    user_id: int,
    username: str,
    role: str = "user",
    expires_delta: timedelta = None,
) -> str:
    """
    Create a JWT token for testing.

    Args:
        user_id: User ID
        username: Username
        role: User role
        expires_delta: Token expiry time delta

    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=1)

    payload = {
        "sub": username,
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + expires_delta,
        "iat": datetime.utcnow(),
    }

    return jwt.encode(payload, TEST_SECRET_KEY, algorithm="HS256")


def get_auth_headers(
    user_id: int = 1,
    username: str = "test_user",
    role: str = "user",
    token: str = None,
) -> Dict[str, str]:
    """
    Get authorization headers for API requests.

    Args:
        user_id: User ID
        username: Username
        role: User role
        token: Pre-generated token (optional)

    Returns:
        Dict with Authorization header
    """
    if token is None:
        token = create_test_token(user_id, username, role)

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_admin_headers(user_id: int = 1, username: str = "admin") -> Dict[str, str]:
    """
    Get admin authorization headers.

    Args:
        user_id: Admin user ID
        username: Admin username

    Returns:
        Dict with Authorization header for admin user
    """
    return get_auth_headers(user_id, username, role="admin")


def make_authenticated_request(
    client,
    method: str,
    url: str,
    user_id: int = 1,
    username: str = "test_user",
    role: str = "user",
    **kwargs,
) -> Any:
    """
    Make an authenticated request using test client.

    Args:
        client: Test client (httpx or similar)
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        user_id: User ID for auth
        username: Username for auth
        role: User role
        **kwargs: Additional request arguments

    Returns:
        Response object
    """
    headers = get_auth_headers(user_id, username, role)

    # Merge with existing headers if provided
    if "headers" in kwargs:
        kwargs["headers"].update(headers)
    else:
        kwargs["headers"] = headers

    method_func = getattr(client, method.lower())
    return method_func(url, **kwargs)


def parse_api_error(response) -> Dict[str, Any]:
    """
    Parse error response from API.

    Args:
        response: API response object

    Returns:
        Dict with error details
    """
    try:
        data = response.json()
        return {
            "status_code": response.status_code,
            "detail": data.get("detail", "Unknown error"),
            "raw": data,
        }
    except Exception:
        return {
            "status_code": response.status_code,
            "detail": response.text,
            "raw": None,
        }


def assert_api_success(response, expected_status: int = 200) -> Dict[str, Any]:
    """
    Assert API response is successful and return JSON data.

    Args:
        response: API response object
        expected_status: Expected HTTP status code

    Returns:
        Response JSON data

    Raises:
        AssertionError: If status code doesn't match
    """
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text}"
    )
    return response.json()


def assert_api_error(response, expected_status: int = 400) -> Dict[str, Any]:
    """
    Assert API response is an error and return error details.

    Args:
        response: API response object
        expected_status: Expected HTTP status code

    Returns:
        Error details dict

    Raises:
        AssertionError: If status code doesn't match
    """
    assert response.status_code == expected_status, (
        f"Expected error status {expected_status}, got {response.status_code}. "
        f"Response: {response.text}"
    )
    return parse_api_error(response)
