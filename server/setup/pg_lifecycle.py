"""PostgreSQL lifecycle management — find binaries, start, stop, check status, run SQL."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

_EXT = ".exe" if os.name == "nt" else ""

_REQUIRED_BINARIES = ("initdb", "pg_ctl", "psql", "pg_isready")


@dataclass
class PgPaths:
    """Paths to PostgreSQL binaries and directories."""

    bin_dir: Path
    initdb: Path
    pg_ctl: Path
    psql: Path
    pg_isready: Path
    data_dir: Path
    log_file: Path


def find_pg_binaries(resources_path: str) -> Optional[PgPaths]:
    """Find bundled PostgreSQL binaries.

    Returns PgPaths if all required binaries found, None otherwise.
    Layout: resources_path/bin/postgresql/bin/{initdb,pg_ctl,psql,pg_isready}[.exe]
    data_dir: resources_path/bin/postgresql/data
    log_file: resources_path/bin/postgresql/pg.log
    """
    root = Path(resources_path)
    bin_dir = root / "bin" / "postgresql" / "bin"

    if not bin_dir.is_dir():
        logger.debug("PG bin dir not found: {}", bin_dir)
        return None

    paths: dict[str, Path] = {}
    for name in _REQUIRED_BINARIES:
        p = bin_dir / f"{name}{_EXT}"
        if not p.exists():
            logger.debug("PG binary not found: {}", p)
            return None
        paths[name] = p

    pg_dir = root / "bin" / "postgresql"
    return PgPaths(
        bin_dir=bin_dir,
        initdb=paths["initdb"],
        pg_ctl=paths["pg_ctl"],
        psql=paths["psql"],
        pg_isready=paths["pg_isready"],
        data_dir=pg_dir / "data",
        log_file=pg_dir / "pg.log",
    )


def _make_env(bin_dir: Path) -> dict:
    """Create environment with PG bin + lib on PATH for DLL resolution."""
    env = os.environ.copy()
    lib_dir = bin_dir.parent / "lib"
    old_path = env.get("PATH", "")
    env["PATH"] = f"{bin_dir}{os.pathsep}{lib_dir}{os.pathsep}{old_path}"
    return env


def is_pg_running(pg_isready: Path, port: int = 5432) -> bool:
    """Check if PG is running using pg_isready. Returns True/False."""
    try:
        result = subprocess.run(
            [str(pg_isready), "-p", str(port)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("pg_isready check failed: {}", exc)
        return False


def start_pg(
    pg_ctl: Path,
    data_dir: Path,
    log_file: Path,
    timeout: int = 30,
) -> tuple[bool, str]:
    """Start PG with pg_ctl start -D data_dir -l log_file -w.

    Returns (success, message).
    """
    env = _make_env(pg_ctl.parent)
    cmd = [
        str(pg_ctl),
        "start",
        "-D", str(data_dir),
        "-l", str(log_file),
        "-w",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, f"pg_ctl start timed out after {timeout}s"
    except OSError as exc:
        return False, f"Failed to start PG: {exc}"


def stop_pg(
    pg_ctl: Path,
    data_dir: Path,
    timeout: int = 10,
) -> tuple[bool, str]:
    """Stop PG with pg_ctl stop -D data_dir -m fast.

    Returns (success, message).
    """
    env = _make_env(pg_ctl.parent)
    cmd = [
        str(pg_ctl),
        "stop",
        "-D", str(data_dir),
        "-m", "fast",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, f"pg_ctl stop timed out after {timeout}s"
    except OSError as exc:
        return False, f"Failed to stop PG: {exc}"


def run_sql(
    psql: Path,
    sql: str,
    user: str = "postgres",
    db: str = "postgres",
    password: str | None = None,
    host: str = "127.0.0.1",
    port: int = 5432,
    timeout: int = 10,
) -> tuple[bool, str]:
    """Run SQL via psql. Password via PGPASSWORD env var (NEVER as CLI arg).

    Windows has no Unix domain sockets — -h and -p are REQUIRED for TCP connection.
    Returns (success, stdout).
    """
    env = _make_env(psql.parent)
    if password is not None:
        env["PGPASSWORD"] = password

    cmd = [
        str(psql),
        "-h", host,       # REQUIRED on Windows (no Unix sockets)
        "-p", str(port),  # explicit port
        "-U", user,
        "-d", db,
        "-t",       # tuples only (no headers)
        "-A",       # unaligned output
        "-c", sql,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, f"psql timed out after {timeout}s"
    except OSError as exc:
        return False, f"Failed to run SQL: {exc}"
