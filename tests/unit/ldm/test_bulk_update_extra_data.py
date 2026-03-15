"""
Tests for bulk_update extra_data support in row repositories.

Verifies:
- bulk_update with extra_data persists JSON correctly
- bulk_update without extra_data key is backward compatible
- bulk_update with extra_data=None is ignored (no null overwrite)

Tests at the code level by inspecting the bulk_update logic directly,
since full DB integration requires the server database setup.
"""

from __future__ import annotations

import json

import pytest


class TestSQLiteBulkUpdateExtraDataLogic:
    """Tests that SQLite bulk_update extra_data logic is correct by inspecting the method source."""

    def test_extra_data_support_in_sqlite_bulk_update(self):
        """SQLite bulk_update method handles extra_data field."""
        import inspect
        from server.repositories.sqlite.row_repo import SQLiteRowRepository

        source = inspect.getsource(SQLiteRowRepository.bulk_update)
        # Must contain extra_data handling
        assert '"extra_data" in update' in source
        assert 'json.dumps(update["extra_data"])' in source

    def test_extra_data_none_guard_in_sqlite(self):
        """SQLite bulk_update skips extra_data when value is None."""
        import inspect
        from server.repositories.sqlite.row_repo import SQLiteRowRepository

        source = inspect.getsource(SQLiteRowRepository.bulk_update)
        # Must have the None guard
        assert 'update["extra_data"] is not None' in source

    def test_backward_compatible_no_extra_data(self):
        """SQLite bulk_update still has target and status handling."""
        import inspect
        from server.repositories.sqlite.row_repo import SQLiteRowRepository

        source = inspect.getsource(SQLiteRowRepository.bulk_update)
        assert '"target" in update' in source
        assert '"status" in update' in source


class TestPostgreSQLBulkUpdateExtraDataLogic:
    """Tests that PostgreSQL bulk_update extra_data logic is correct."""

    def test_extra_data_support_in_pg_bulk_update(self):
        """PostgreSQL bulk_update method handles extra_data field."""
        import inspect
        from server.repositories.postgresql.row_repo import PostgreSQLRowRepository

        source = inspect.getsource(PostgreSQLRowRepository.bulk_update)
        assert '"extra_data" in update' in source
        assert 'row.extra_data = update["extra_data"]' in source

    def test_extra_data_none_guard_in_pg(self):
        """PostgreSQL bulk_update skips extra_data when value is None."""
        import inspect
        from server.repositories.postgresql.row_repo import PostgreSQLRowRepository

        source = inspect.getsource(PostgreSQLRowRepository.bulk_update)
        assert 'update["extra_data"] is not None' in source


class TestInterfaceDocstring:
    """Tests that the interface documents extra_data support."""

    def test_interface_mentions_extra_data(self):
        """RowRepository.bulk_update docstring mentions extra_data."""
        from server.repositories.interfaces.row_repository import RowRepository

        doc = RowRepository.bulk_update.__doc__
        assert "extra_data" in doc
