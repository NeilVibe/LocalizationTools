"""Tests for server.setup.steps — 7 idempotent step functions."""
from __future__ import annotations

import socket
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from server.setup import SetupConfig, StepResult
from server.setup.steps import (
    step_configure_access,
    step_generate_certificates,
    step_init_database,
    step_preflight_checks,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path, port: int = 5432) -> SetupConfig:
    """Create a SetupConfig pointing at a temp directory with fake binaries."""
    bin_dir = tmp_path / "bin" / "postgresql" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    data_dir = tmp_path / "bin" / "postgresql" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    ext = ".exe" if __import__("os").name == "nt" else ""
    for name in ("initdb", "pg_ctl", "psql", "pg_isready"):
        (bin_dir / f"{name}{ext}").touch()

    return SetupConfig(
        pg_bin_dir=str(bin_dir),
        data_dir=str(data_dir),
        pg_port=port,
    )


# ---------------------------------------------------------------------------
# Step 0 — Preflight
# ---------------------------------------------------------------------------


class TestPreflightChecks:
    def test_detects_port_conflict(self, tmp_path: Path) -> None:
        """Bind the port first, then preflight should detect conflict."""
        config = _make_config(tmp_path)

        # Bind the port so preflight sees it occupied
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", config.pg_port))
        try:
            result = step_preflight_checks(config)
            assert result.status == "failed"
            assert result.error_code == "PORT_CONFLICT"
        finally:
            blocker.close()

    def test_detects_missing_binaries(self, tmp_path: Path) -> None:
        """Point at a dir with no binaries."""
        config = SetupConfig(
            pg_bin_dir=str(tmp_path / "nonexistent"),
            data_dir=str(tmp_path / "data"),
        )
        result = step_preflight_checks(config)
        assert result.status == "failed"
        assert result.error_code == "MISSING_BINARIES"


# ---------------------------------------------------------------------------
# Step 1 — Init database
# ---------------------------------------------------------------------------


class TestInitDatabase:
    def test_skips_if_already_initialized(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        pg_version = Path(config.data_dir) / "PG_VERSION"
        pg_version.write_text("16\n")

        result = step_init_database(config)
        assert result.status == "skipped"

    def test_cleans_up_on_failure(self, tmp_path: Path) -> None:
        """Mock subprocess to fail, verify data_dir is cleaned up."""
        config = _make_config(tmp_path)
        data_dir = Path(config.data_dir)

        # Remove data_dir so step creates it fresh
        import shutil
        shutil.rmtree(data_dir, ignore_errors=True)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "fake initdb error"
        mock_result.stdout = ""

        with patch("server.setup.steps.subprocess.run", return_value=mock_result):
            result = step_init_database(config)

        assert result.status == "failed"
        assert result.error_code == "INITDB_FAILED"
        # data_dir should be cleaned up
        assert not data_dir.exists()


# ---------------------------------------------------------------------------
# Step 2 — Configure access
# ---------------------------------------------------------------------------


class TestConfigureAccess:
    def test_skips_if_marker_exists(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        hba_path = Path(config.data_dir) / "pg_hba.conf"
        hba_path.write_text("# LocaNext — already configured\n", encoding="utf-8")

        result = step_configure_access(config)
        assert result.status == "skipped"


# ---------------------------------------------------------------------------
# Step 6 — Generate certificates
# ---------------------------------------------------------------------------


class TestGenerateCertificates:
    def test_skips_if_exist(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        (Path(config.data_dir) / "server.crt").write_bytes(b"fake cert")
        (Path(config.data_dir) / "server.key").write_bytes(b"fake key")

        result = step_generate_certificates(config)
        assert result.status == "skipped"

    def test_returns_failed_if_no_cryptography(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)

        # Mock ImportError for cryptography
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "cryptography" or name.startswith("cryptography."):
                raise ImportError("No module named 'cryptography'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = step_generate_certificates(config)

        assert result.status == "failed"
        assert result.error_code == "MISSING_CRYPTOGRAPHY"
