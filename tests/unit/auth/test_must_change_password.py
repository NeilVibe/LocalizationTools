"""Tests for must_change_password flow."""
import pytest


def test_token_schema_includes_must_change_password():
    """Token response schema must include must_change_password field."""
    from server.api.schemas import Token
    token = Token(
        access_token="test",
        token_type="bearer",
        user_id=1,
        username="admin",
        role="admin",
        must_change_password=True,
    )
    assert token.must_change_password is True


def test_token_schema_defaults_false():
    """must_change_password must default to False for backward compat."""
    from server.api.schemas import Token
    token = Token(
        access_token="test",
        token_type="bearer",
        user_id=1,
        username="admin",
        role="admin",
    )
    assert token.must_change_password is False
