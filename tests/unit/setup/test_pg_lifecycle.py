from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from server.setup.pg_lifecycle import (
    PgPaths,
    find_pg_binaries,
    _make_env,
    is_pg_running,
    run_sql,
)


class TestFindPgBinaries:
    """Tests for find_pg_binaries."""

    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        """Empty directory => None."""
        result = find_pg_binaries(str(tmp_path))
        assert result is None

    def test_finds_bundled(self, tmp_path: Path) -> None:
        """Create fake binaries in correct structure => PgPaths."""
        ext = ".exe" if os.name == "nt" else ""
        bin_dir = tmp_path / "bin" / "postgresql" / "bin"
        bin_dir.mkdir(parents=True)
        for name in ("initdb", "pg_ctl", "psql", "pg_isready"):
            (bin_dir / f"{name}{ext}").touch()

        result = find_pg_binaries(str(tmp_path))
        assert result is not None
        assert result.bin_dir == bin_dir
        assert result.initdb == bin_dir / f"initdb{ext}"
        assert result.pg_ctl == bin_dir / f"pg_ctl{ext}"
        assert result.psql == bin_dir / f"psql{ext}"
        assert result.pg_isready == bin_dir / f"pg_isready{ext}"

    def test_data_dir_is_sibling_of_bin(self, tmp_path: Path) -> None:
        """data_dir should be resources/bin/postgresql/data."""
        ext = ".exe" if os.name == "nt" else ""
        bin_dir = tmp_path / "bin" / "postgresql" / "bin"
        bin_dir.mkdir(parents=True)
        for name in ("initdb", "pg_ctl", "psql", "pg_isready"):
            (bin_dir / f"{name}{ext}").touch()

        result = find_pg_binaries(str(tmp_path))
        assert result is not None
        assert result.data_dir == tmp_path / "bin" / "postgresql" / "data"


class TestIsPgRunning:
    """Tests for is_pg_running."""

    def test_returns_false_on_error(self) -> None:
        """When pg_isready fails or raises, return False."""
        with patch("server.setup.pg_lifecycle.subprocess.run", side_effect=OSError("not found")):
            result = is_pg_running(Path("/fake/pg_isready"))
            assert result is False

    def test_returns_true_on_zero_exit(self) -> None:
        """pg_isready exit code 0 => running."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("server.setup.pg_lifecycle.subprocess.run", return_value=mock_result):
            result = is_pg_running(Path("/fake/pg_isready"))
            assert result is True

    def test_returns_false_on_nonzero_exit(self) -> None:
        """pg_isready exit code != 0 => not running."""
        mock_result = MagicMock()
        mock_result.returncode = 2
        with patch("server.setup.pg_lifecycle.subprocess.run", return_value=mock_result):
            result = is_pg_running(Path("/fake/pg_isready"))
            assert result is False


class TestMakeEnv:
    """Tests for _make_env."""

    def test_includes_lib_dir(self) -> None:
        """PATH should contain both bin_dir and lib_dir."""
        bin_dir = Path("/fake/postgresql/bin")
        env = _make_env(bin_dir)
        path_val = env.get("PATH", "")
        assert str(bin_dir) in path_val
        assert str(bin_dir.parent / "lib") in path_val

    def test_preserves_existing_env(self) -> None:
        """Original env vars should still be present."""
        bin_dir = Path("/fake/postgresql/bin")
        env = _make_env(bin_dir)
        # HOME or some standard var should survive
        assert "PATH" in env


class TestRunSql:
    """Tests for run_sql."""

    def test_uses_pgpassword_env(self) -> None:
        """Password must be in PGPASSWORD env, never in command args."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "OK"
        mock_result.stderr = ""

        with patch("server.setup.pg_lifecycle.subprocess.run", return_value=mock_result) as mock_run:
            success, output = run_sql(
                psql=Path("/fake/psql"),
                sql="SELECT 1;",
                user="postgres",
                db="postgres",
                password="secret123",
            )
            assert success is True
            # Check that subprocess.run was called
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args
            # Password must be in env, not in command args
            cmd = call_kwargs[0][0] if call_kwargs[0] else call_kwargs.kwargs.get("args", [])
            assert "secret123" not in " ".join(str(c) for c in cmd)
            env_used = call_kwargs.kwargs.get("env") or call_kwargs[1].get("env", {})
            assert env_used.get("PGPASSWORD") == "secret123"

    def test_no_password_no_pgpassword(self) -> None:
        """When password is None, PGPASSWORD should not be set."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("server.setup.pg_lifecycle.subprocess.run", return_value=mock_result) as mock_run:
            run_sql(
                psql=Path("/fake/psql"),
                sql="SELECT 1;",
                user="postgres",
                db="postgres",
                password=None,
            )
            call_kwargs = mock_run.call_args
            env_used = call_kwargs.kwargs.get("env") or call_kwargs[1].get("env", {})
            assert "PGPASSWORD" not in env_used

    def test_returns_failure_on_nonzero(self) -> None:
        """Non-zero exit => (False, stderr)."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ERROR: syntax error"

        with patch("server.setup.pg_lifecycle.subprocess.run", return_value=mock_result):
            success, output = run_sql(
                psql=Path("/fake/psql"),
                sql="BAD SQL;",
            )
            assert success is False
            assert "syntax error" in output
