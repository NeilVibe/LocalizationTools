"""7 idempotent setup steps: PRE-CHECK -> RUN -> VERIFY -> CLEANUP."""
from __future__ import annotations

import os
import secrets
import shutil
import socket
import subprocess
import time
from pathlib import Path

from server.setup import SetupConfig, StepResult
from server.setup.network import detect_lan_ip, get_subnet
from server.setup.pg_lifecycle import PgPaths, _make_env, is_pg_running, run_sql

from loguru import logger

_EXT = ".exe" if os.name == "nt" else ""

_MIN_DISK_MB = 500


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_paths(config: SetupConfig) -> PgPaths | None:
    """Build PgPaths from config, or None if bin_dir missing."""
    if not config.pg_bin_dir:
        return None
    bin_dir = Path(config.pg_bin_dir)
    pg_dir = bin_dir.parent  # e.g. …/postgresql
    data_dir = Path(config.data_dir) if config.data_dir else pg_dir / "data"
    return PgPaths(
        bin_dir=bin_dir,
        initdb=bin_dir / f"initdb{_EXT}",
        pg_ctl=bin_dir / f"pg_ctl{_EXT}",
        psql=bin_dir / f"psql{_EXT}",
        pg_isready=bin_dir / f"pg_isready{_EXT}",
        data_dir=data_dir,
        log_file=pg_dir / "pg.log",
    )


def _ms_since(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


# ---------------------------------------------------------------------------
# Step 0 — Preflight checks
# ---------------------------------------------------------------------------


def step_preflight_checks(config: SetupConfig) -> StepResult:
    """Check disk space (>500 MB), port free, binaries exist."""
    t0 = time.monotonic()
    step = "preflight_checks"

    # --- Binaries ---
    paths = _resolve_paths(config)
    if paths is None:
        return StepResult(
            step=step,
            status="failed",
            duration_ms=_ms_since(t0),
            message="pg_bin_dir not configured",
            error_code="MISSING_BINARIES",
        )
    for name in ("initdb", "pg_ctl", "psql", "pg_isready"):
        p = getattr(paths, name)
        if not p.exists():
            return StepResult(
                step=step,
                status="failed",
                duration_ms=_ms_since(t0),
                message=f"Binary not found: {p}",
                error_code="MISSING_BINARIES",
            )

    # --- Disk space ---
    try:
        usage = shutil.disk_usage(str(paths.data_dir.parent))
        free_mb = usage.free / (1024 * 1024)
        if free_mb < _MIN_DISK_MB:
            return StepResult(
                step=step,
                status="failed",
                duration_ms=_ms_since(t0),
                message=f"Only {free_mb:.0f} MB free, need {_MIN_DISK_MB} MB",
                error_code="LOW_DISK",
            )
    except OSError as exc:
        return StepResult(
            step=step,
            status="failed",
            duration_ms=_ms_since(t0),
            message=f"Cannot check disk: {exc}",
            error_code="DISK_CHECK_FAILED",
        )

    # --- Port ---
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", config.pg_port))
    except OSError:
        return StepResult(
            step=step,
            status="failed",
            duration_ms=_ms_since(t0),
            message=f"Port {config.pg_port} already in use",
            error_code="PORT_CONFLICT",
        )

    # --- Windows firewall (best effort) ---
    if os.name == "nt":
        try:
            subprocess.run(
                [
                    "netsh", "advfirewall", "firewall", "add", "rule",
                    f"name=LocaNext PG {config.pg_port}",
                    "dir=in", "action=allow", "protocol=TCP",
                    f"localport={config.pg_port}",
                ],
                capture_output=True,
                timeout=10,
            )
        except Exception as exc:
            logger.warning("Firewall rule creation failed (LAN connections may be blocked): {}", exc)

    return StepResult(
        step=step,
        status="done",
        duration_ms=_ms_since(t0),
        message="All preflight checks passed",
    )


# ---------------------------------------------------------------------------
# Step 1 — Init database
# ---------------------------------------------------------------------------


def step_init_database(config: SetupConfig) -> StepResult:
    """Run initdb. Skip if PG_VERSION already present."""
    t0 = time.monotonic()
    step = "init_database"
    paths = _resolve_paths(config)
    if paths is None:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="pg_bin_dir not configured", error_code="MISSING_BINARIES",
        )

    pg_version = paths.data_dir / "PG_VERSION"
    pg_conf = paths.data_dir / "postgresql.conf"
    # Validate BOTH PG_VERSION and postgresql.conf exist — a partial/corrupted
    # data dir from a previous failed install must be wiped and re-created.
    if pg_version.exists() and pg_conf.exists() and pg_version.read_text().strip():
        return StepResult(
            step=step, status="skipped", duration_ms=_ms_since(t0),
            message="Database already initialized (PG_VERSION exists)",
        )
    # Corrupted/partial data dir — wipe it so initdb can start fresh
    if paths.data_dir.exists() and not pg_conf.exists():
        logger.warning("Partial data_dir detected (PG_VERSION but no postgresql.conf) — wiping for fresh init")
        shutil.rmtree(paths.data_dir, ignore_errors=True)

    # Ensure parent exists
    paths.data_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(paths.initdb),
        "-D", str(paths.data_dir),
        "-U", config.pg_superuser,
        "-E", "UTF8",
        "--locale=C",
    ]
    env = _make_env(paths.bin_dir)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, env=env,
        )
    except subprocess.TimeoutExpired:
        # Cleanup partial data_dir
        shutil.rmtree(paths.data_dir, ignore_errors=True)
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="initdb timed out after 60s", error_code="INITDB_TIMEOUT",
        )
    except OSError as exc:
        shutil.rmtree(paths.data_dir, ignore_errors=True)
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message=f"initdb failed: {exc}", error_code="INITDB_FAILED",
        )

    if result.returncode != 0:
        shutil.rmtree(paths.data_dir, ignore_errors=True)
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="initdb failed", error_code="INITDB_FAILED",
            stderr=result.stderr.strip(),
        )

    # Verify
    if not pg_version.exists():
        shutil.rmtree(paths.data_dir, ignore_errors=True)
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="PG_VERSION not created after initdb",
            error_code="INITDB_VERIFY_FAILED",
        )

    return StepResult(
        step=step, status="done", duration_ms=_ms_since(t0),
        message="Database cluster initialized",
    )


# ---------------------------------------------------------------------------
# Step 2 — Configure access (pg_hba.conf + postgresql.conf)
# ---------------------------------------------------------------------------

_HBA_MARKER = "# LocaNext"

_HBA_TEMPLATE = """\
# LocaNext — managed by setup wizard. Do not edit above this line.
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             {superuser}                             trust
host    all             {superuser}     127.0.0.1/32            scram-sha-256
host    all             {superuser}     ::1/128                 scram-sha-256
host    all             {service_user}  127.0.0.1/32            scram-sha-256
host    all             {service_user}  ::1/128                 scram-sha-256
hostssl {service_db}    {service_user}  {subnet}                scram-sha-256
# Reject everything else
host    all             all             0.0.0.0/0               reject
host    all             all             ::0/0                   reject
"""

_CONF_SETTINGS = """\
# LocaNext — managed by setup wizard
listen_addresses = '*'
port = {port}
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
"""


def step_configure_access(config: SetupConfig) -> StepResult:
    """Write pg_hba.conf + postgresql.conf. Skip if marker exists."""
    t0 = time.monotonic()
    step = "configure_access"
    paths = _resolve_paths(config)
    if paths is None:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="pg_bin_dir not configured", error_code="MISSING_BINARIES",
        )

    hba_path = paths.data_dir / "pg_hba.conf"
    conf_path = paths.data_dir / "postgresql.conf"

    # Pre-check: skip if marker exists
    if hba_path.exists():
        content = hba_path.read_text(encoding="utf-8")
        if _HBA_MARKER in content:
            return StepResult(
                step=step, status="skipped", duration_ms=_ms_since(t0),
                message="pg_hba.conf already configured (marker found)",
            )

    # Backup originals
    hba_backup = hba_path.with_suffix(".conf.bak") if hba_path.exists() else None
    conf_backup = conf_path.with_suffix(".conf.bak") if conf_path.exists() else None
    if hba_backup and hba_path.exists():
        shutil.copy2(hba_path, hba_backup)
    if conf_backup and conf_path.exists():
        shutil.copy2(conf_path, conf_backup)

    try:
        lan_ip = detect_lan_ip()
        subnet = get_subnet(lan_ip)

        hba_content = _HBA_TEMPLATE.format(
            superuser=config.pg_superuser,
            service_user=config.service_user,
            service_db=config.service_db,
            subnet=subnet,
        )
        hba_path.write_text(hba_content, encoding="utf-8")

        # Append LocaNext settings to postgresql.conf (preserve existing content)
        conf_extra = _CONF_SETTINGS.format(port=config.pg_port)
        if conf_path.exists():
            existing = conf_path.read_text(encoding="utf-8")
            if _HBA_MARKER not in existing:
                conf_path.write_text(
                    existing.rstrip() + "\n\n" + conf_extra, encoding="utf-8",
                )
        else:
            conf_path.write_text(conf_extra, encoding="utf-8")

    except Exception as exc:
        # Restore backups
        if hba_backup and hba_backup.exists():
            shutil.copy2(hba_backup, hba_path)
        if conf_backup and conf_backup.exists():
            shutil.copy2(conf_backup, conf_path)
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message=f"Configuration failed: {exc}",
            error_code="CONFIGURE_FAILED",
        )

    # Verify
    if not hba_path.exists() or _HBA_MARKER not in hba_path.read_text(encoding="utf-8"):
        if hba_backup and hba_backup.exists():
            shutil.copy2(hba_backup, hba_path)
        if conf_backup and conf_backup.exists():
            shutil.copy2(conf_backup, conf_path)
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="Verification failed: marker not found after write",
            error_code="CONFIGURE_VERIFY_FAILED",
        )

    return StepResult(
        step=step, status="done", duration_ms=_ms_since(t0),
        message="pg_hba.conf and postgresql.conf configured",
    )


# ---------------------------------------------------------------------------
# Step 4 — Start database
# ---------------------------------------------------------------------------


def step_start_database(config: SetupConfig) -> StepResult:
    """Start PG with pg_ctl. Skip if already running."""
    t0 = time.monotonic()
    step = "start_database"
    paths = _resolve_paths(config)
    if paths is None:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="pg_bin_dir not configured", error_code="MISSING_BINARIES",
        )

    # Pre-check
    if is_pg_running(paths.pg_isready, config.pg_port):
        return StepResult(
            step=step, status="skipped", duration_ms=_ms_since(t0),
            message="PostgreSQL already running",
        )

    env = _make_env(paths.bin_dir)
    cmd = [
        str(paths.pg_ctl), "start",
        "-D", str(paths.data_dir),
        "-l", str(paths.log_file),
        "-w",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, env=env,
        )
    except subprocess.TimeoutExpired:
        # Cleanup: try to stop
        try:
            subprocess.run(
                [str(paths.pg_ctl), "stop", "-D", str(paths.data_dir), "-m", "fast"],
                capture_output=True, timeout=10, env=env,
            )
        except Exception:
            pass
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="pg_ctl start timed out", error_code="START_TIMEOUT",
        )
    except OSError as exc:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message=f"pg_ctl start failed: {exc}", error_code="START_FAILED",
        )

    if result.returncode != 0:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="pg_ctl start failed", error_code="START_FAILED",
            stderr=result.stderr.strip(),
        )

    # Verify
    if not is_pg_running(paths.pg_isready, config.pg_port):
        # Cleanup
        try:
            subprocess.run(
                [str(paths.pg_ctl), "stop", "-D", str(paths.data_dir), "-m", "fast"],
                capture_output=True, timeout=10, env=env,
            )
        except Exception:
            pass
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="pg_isready check failed after start",
            error_code="START_VERIFY_FAILED",
        )

    return StepResult(
        step=step, status="done", duration_ms=_ms_since(t0),
        message="PostgreSQL started",
    )


# ---------------------------------------------------------------------------
# Step 5 — Create account
# ---------------------------------------------------------------------------


def step_create_account(config: SetupConfig) -> StepResult:
    """Create service user role. Skip if exists. Returns password in message."""
    t0 = time.monotonic()
    step = "create_account"
    paths = _resolve_paths(config)
    if paths is None:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="pg_bin_dir not configured", error_code="MISSING_BINARIES",
        )

    # Pre-check: role exists?
    ok, out = run_sql(
        paths.psql,
        f"SELECT 1 FROM pg_roles WHERE rolname = '{config.service_user}'",
        user=config.pg_superuser,
    )
    if ok and out.strip() == "1":
        # Role exists — ensure password is current (ALTER)
        password = secrets.token_urlsafe(24)
        run_sql(
            paths.psql,
            f"ALTER USER {config.service_user} WITH PASSWORD '{password}'",
            user=config.pg_superuser,
        )
        return StepResult(
            step=step, status="skipped", duration_ms=_ms_since(t0),
            message=password,  # Caller stores this
        )

    password = secrets.token_urlsafe(24)
    ok, out = run_sql(
        paths.psql,
        f"CREATE USER {config.service_user} WITH PASSWORD '{password}'",
        user=config.pg_superuser,
    )
    if not ok:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message=f"CREATE USER failed: {out}", error_code="CREATE_USER_FAILED",
            stderr=out,
        )

    return StepResult(
        step=step, status="done", duration_ms=_ms_since(t0),
        message=password,  # Caller stores this
    )


# ---------------------------------------------------------------------------
# Step 6 — Create database
# ---------------------------------------------------------------------------


def step_create_database(config: SetupConfig) -> StepResult:
    """Create service database + GRANT ALL. Skip if exists."""
    t0 = time.monotonic()
    step = "create_database"
    paths = _resolve_paths(config)
    if paths is None:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="pg_bin_dir not configured", error_code="MISSING_BINARIES",
        )

    # Pre-check
    ok, out = run_sql(
        paths.psql,
        f"SELECT 1 FROM pg_database WHERE datname = '{config.service_db}'",
        user=config.pg_superuser,
    )
    if ok and out.strip() == "1":
        return StepResult(
            step=step, status="skipped", duration_ms=_ms_since(t0),
            message=f"Database '{config.service_db}' already exists",
        )

    # Create
    ok, out = run_sql(
        paths.psql,
        f"CREATE DATABASE {config.service_db} OWNER {config.service_user}",
        user=config.pg_superuser,
    )
    if not ok:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message=f"CREATE DATABASE failed: {out}",
            error_code="CREATE_DB_FAILED", stderr=out,
        )

    # Grant
    ok2, out2 = run_sql(
        paths.psql,
        f"GRANT ALL PRIVILEGES ON DATABASE {config.service_db} TO {config.service_user}",
        user=config.pg_superuser,
    )
    if not ok2:
        # Cleanup: drop the database we just created
        run_sql(
            paths.psql,
            f"DROP DATABASE IF EXISTS {config.service_db}",
            user=config.pg_superuser,
        )
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message=f"GRANT failed: {out2}", error_code="GRANT_FAILED",
            stderr=out2,
        )

    return StepResult(
        step=step, status="done", duration_ms=_ms_since(t0),
        message=f"Database '{config.service_db}' created with grants",
    )


# ---------------------------------------------------------------------------
# Step 3 — Generate TLS certificates
# ---------------------------------------------------------------------------


def step_generate_certificates(config: SetupConfig) -> StepResult:
    """Generate self-signed RSA 2048 cert (10 years). Uses Python cryptography lib."""
    t0 = time.monotonic()
    step = "generate_certificates"
    paths = _resolve_paths(config)
    if paths is None:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="pg_bin_dir not configured", error_code="MISSING_BINARIES",
        )

    cert_path = paths.data_dir / "server.crt"
    key_path = paths.data_dir / "server.key"

    # Pre-check
    if cert_path.exists() and key_path.exists():
        return StepResult(
            step=step, status="skipped", duration_ms=_ms_since(t0),
            message="Certificates already exist",
        )

    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="Python 'cryptography' package not installed",
            error_code="MISSING_CRYPTOGRAPHY",
        )

    import datetime

    try:
        # Generate key
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        lan_ip = detect_lan_ip()
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"LocaNext-{lan_ip}"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "LocaNext"),
        ])

        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.IPAddress(
                        __import__("ipaddress").ip_address(lan_ip),
                    ),
                ]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        # Write key (restricted permissions)
        key_bytes = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path.write_bytes(key_bytes)
        if os.name == "nt":
            # Restrict key file to current user only (PG requires this for ssl=on)
            try:
                subprocess.run(
                    ["icacls", str(key_path), "/inheritance:r",
                     "/grant:r", f"{os.environ.get('USERNAME', 'SYSTEM')}:(R)"],
                    capture_output=True, text=True, timeout=10,
                )
                logger.info("SSL key permissions restricted via icacls")
            except Exception as exc:
                logger.warning("Could not restrict SSL key permissions: {}", exc)
        else:
            key_path.chmod(0o600)

        # Write cert
        cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
        cert_path.write_bytes(cert_bytes)

    except Exception as exc:
        # Cleanup partial files
        for p in (cert_path, key_path):
            if p.exists():
                p.unlink()
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message=f"Certificate generation failed: {exc}",
            error_code="CERT_GENERATION_FAILED",
        )

    # Verify
    if not cert_path.exists() or not key_path.exists():
        for p in (cert_path, key_path):
            if p.exists():
                p.unlink()
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="Certificate files not found after generation",
            error_code="CERT_VERIFY_FAILED",
        )

    return StepResult(
        step=step, status="done", duration_ms=_ms_since(t0),
        message=f"Self-signed certificate generated (LAN IP: {lan_ip})",
    )


# ---------------------------------------------------------------------------
# Step 5b — Tune performance (after PG is running)
# ---------------------------------------------------------------------------


def step_tune_performance(config: SetupConfig) -> StepResult:
    """Detect hardware and write optimized postgresql.conf settings.

    Tunes for 200+ concurrent connections based on detected RAM, CPU, SSD.
    Applies settings via pg_ctl reload (no restart needed).
    """
    t0 = time.monotonic()
    step = "tune_performance"
    paths = _resolve_paths(config)
    if paths is None:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="pg_bin_dir not configured", error_code="TUNE_FAILED",
        )

    conf_path = paths.data_dir / "postgresql.conf"
    if not conf_path.exists():
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message="postgresql.conf not found", error_code="TUNE_FAILED",
        )

    # Detect hardware
    try:
        from server.setup.hardware_detect import detect_hardware
        hw = detect_hardware(str(paths.data_dir))
    except Exception as exc:
        logger.warning("Hardware detection failed, using defaults: {}", exc)
        from server.setup.hardware_detect import HardwareInfo
        hw = HardwareInfo(ram_gb=8, physical_cores=4, logical_cores=8, is_ssd=True, os_name=os.name)

    # Calculate optimal settings
    max_connections = 250
    shared_buffers_gb = max(1, hw.ram_gb // 4)
    effective_cache_size_gb = max(2, hw.ram_gb * 3 // 4)
    work_mem_mb = max(4, min(64, hw.ram_gb * 1024 // (max_connections * 4)))
    maintenance_work_mem_gb = max(1, min(4, hw.ram_gb // 16))
    max_parallel_workers = min(8, hw.physical_cores)
    max_parallel_per_gather = min(4, hw.physical_cores // 3) if hw.physical_cores >= 3 else 1
    random_page_cost = "1.1" if hw.is_ssd else "4.0"
    effective_io_concurrency = 200 if hw.is_ssd else 2

    tuning_block = f"""
# LocaNext Performance Tuning (auto-generated)
# Hardware: {hw.ram_gb}GB RAM, {hw.physical_cores} cores, SSD={hw.is_ssd}
max_connections = {max_connections}
shared_buffers = {shared_buffers_gb}GB
effective_cache_size = {effective_cache_size_gb}GB
work_mem = {work_mem_mb}MB
maintenance_work_mem = {maintenance_work_mem_gb}GB
wal_buffers = 64MB
max_wal_size = 4GB
min_wal_size = 1GB
checkpoint_completion_target = 0.9
random_page_cost = {random_page_cost}
effective_io_concurrency = {effective_io_concurrency}
max_parallel_workers_per_gather = {max_parallel_per_gather}
max_parallel_workers = {max_parallel_workers}
max_parallel_maintenance_workers = {max_parallel_per_gather}
default_statistics_target = 200
"""

    end_marker = "# End LocaNext Performance Tuning"
    try:
        existing = conf_path.read_text(encoding="utf-8")
        marker = "# LocaNext Performance Tuning"
        if marker in existing:
            before = existing[:existing.index(marker)]
            after_part = ""
            if end_marker in existing:
                after_idx = existing.index(end_marker) + len(end_marker)
                after_part = existing[after_idx:]
            existing = before.rstrip() + "\n" + after_part
        conf_path.write_text(existing + "\n" + tuning_block + end_marker + "\n", encoding="utf-8")
    except Exception as exc:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message=f"Failed to write postgresql.conf: {exc}",
            error_code="TUNE_FAILED",
        )

    # shared_buffers and max_connections require restart, not reload
    env = _make_env(paths.bin_dir)
    try:
        result = subprocess.run(
            [str(paths.pg_ctl), "restart", "-D", str(paths.data_dir),
             "-l", str(paths.log_file), "-w"],
            capture_output=True, text=True, timeout=30, env=env,
        )
        if result.returncode != 0:
            logger.warning("pg_ctl restart failed (settings apply on next manual restart): {}", result.stderr)
    except subprocess.TimeoutExpired:
        logger.warning("pg_ctl restart timed out — settings may apply on next launch")
    except Exception as exc:
        logger.warning("pg_ctl restart failed: {} (settings apply on next launch)", exc)

    logger.info(
        "PG tuned: max_connections={}, shared_buffers={}GB, work_mem={}MB, parallel_workers={}, SSD={}",
        max_connections, shared_buffers_gb, work_mem_mb, max_parallel_workers, hw.is_ssd,
    )

    return StepResult(
        step=step, status="done", duration_ms=_ms_since(t0),
        message=f"Tuned for {hw.ram_gb}GB RAM, {hw.physical_cores} cores, {max_connections} connections",
    )
