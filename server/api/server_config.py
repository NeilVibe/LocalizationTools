"""
Server Connection Configuration API

Endpoints for managing server connection settings (LAN server mode).
Allows clients to configure PG connection, test connectivity, and view status.
All endpoints require authentication (JWT token).
"""

from __future__ import annotations

import socket

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from loguru import logger

from server import config
from server.utils.dependencies import get_current_active_user_async

router = APIRouter(prefix="/api/server-config", tags=["server-config"])


# ============================================================================
# Models
# ============================================================================

class ServerConnectionConfig(BaseModel):
    """Server connection configuration from client."""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "locanext_service"
    postgres_password: str = ""
    postgres_db: str = "localizationtools"
    database_mode: str = "auto"  # auto, postgresql, sqlite


class ServerConnectionStatus(BaseModel):
    """Current server connection status."""
    database_mode: str
    active_database: str
    postgres_host: str
    postgres_port: int
    postgres_db: str
    is_online: bool
    server_mode: str  # "standalone" or "lan_server"
    lan_ip: str | None = None


class ConnectionTestResult(BaseModel):
    """Result of a connection test."""
    success: bool
    message: str
    pg_version: str | None = None
    latency_ms: float | None = None


# ============================================================================
# Helpers
# ============================================================================

def _get_lan_ip() -> str | None:
    """Get LAN IP address without any internet access."""
    from server.setup.network import detect_lan_ip
    ip = detect_lan_ip()
    return ip if ip != "127.0.0.1" else None


def _test_pg_connection(host: str, port: int, user: str, password: str, db: str) -> ConnectionTestResult:
    """Test a PostgreSQL connection with timing."""
    import time

    # Validate port range
    if not (1 <= port <= 65535):
        return ConnectionTestResult(success=False, message="Invalid port number")

    # Step 1: Socket check (fast)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        if result != 0:
            return ConnectionTestResult(
                success=False,
                message=f"Cannot reach {host}:{port} — is PostgreSQL running?",
            )
    except Exception:
        return ConnectionTestResult(
            success=False,
            message=f"Cannot reach {host}:{port} — network error",
        )

    # Step 2: Full DB connection
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine import URL

        url = URL.create(
            "postgresql",
            username=user,
            password=password,
            host=host,
            port=port,
            database=db,
        )
        start = time.monotonic()
        engine = create_engine(url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version()")).fetchone()
            pg_version = row[0] if row else "unknown"
        engine.dispose()
        latency = (time.monotonic() - start) * 1000

        return ConnectionTestResult(
            success=True,
            message=f"Connected to PostgreSQL at {host}:{port}",
            pg_version=pg_version,
            latency_ms=round(latency, 1),
        )
    except Exception as e:
        # Log full error server-side only — never expose credentials to client
        logger.error(f"Connection test to {host}:{port} failed: {e}")
        return ConnectionTestResult(
            success=False,
            message="Connection failed — check credentials and server address",
        )


# ============================================================================
# Endpoints (all require authentication)
# ============================================================================

@router.get("/status", response_model=ServerConnectionStatus)
async def get_server_status(_user=Depends(get_current_active_user_async)):
    """Get current server connection status."""
    user_config = config.get_user_config()

    return ServerConnectionStatus(
        database_mode=config.DATABASE_MODE,
        active_database=config.ACTIVE_DATABASE_TYPE,
        postgres_host=config.POSTGRES_HOST,
        postgres_port=config.POSTGRES_PORT,
        postgres_db=config.POSTGRES_DB,
        is_online=config.is_online_mode(),
        server_mode=user_config.get("server_mode", "standalone"),
        lan_ip=_get_lan_ip(),
    )


@router.get("/config")
async def get_server_config(_user=Depends(get_current_active_user_async)):
    """Get current server connection configuration (passwords redacted)."""
    user_config = config.get_user_config()

    return {
        "postgres_host": config.POSTGRES_HOST,
        "postgres_port": config.POSTGRES_PORT,
        "postgres_user": config.POSTGRES_USER,
        "postgres_db": config.POSTGRES_DB,
        "database_mode": config.DATABASE_MODE,
        "server_mode": user_config.get("server_mode", "standalone"),
        "lan_ip": user_config.get("lan_ip"),
        "has_password": bool(config.POSTGRES_PASSWORD and config.POSTGRES_PASSWORD != "change_this_password"),
    }


@router.post("/config")
async def update_server_config(body: ServerConnectionConfig, _user=Depends(get_current_active_user_async)):
    """
    Update server connection configuration.

    Saves to server-config.json. Requires app restart to take effect.
    Does NOT save secret_key — that is only set by the setup script.
    """
    logger.info(f"Updating server config: host={body.postgres_host}:{body.postgres_port}")

    # Load existing config and merge — preserve secret_key if it exists
    existing = config.get_user_config()
    existing.update({
        "postgres_host": body.postgres_host,
        "postgres_port": body.postgres_port,
        "postgres_user": body.postgres_user,
        "postgres_db": body.postgres_db,
        "database_mode": body.database_mode,
    })
    if body.postgres_password:
        existing["postgres_password"] = body.postgres_password

    success = config.save_user_config(existing)

    if success:
        logger.info("Server config saved — restart required to apply")
        return {
            "success": True,
            "message": "Configuration saved. Restart the application to connect.",
            "action_required": "restart",
        }
    else:
        logger.error("Failed to save server config")
        return {
            "success": False,
            "message": "Failed to save configuration file.",
        }


@router.post("/test-connection", response_model=ConnectionTestResult)
async def test_connection(body: ServerConnectionConfig, _user=Depends(get_current_active_user_async)):
    """
    Test a PostgreSQL connection without saving it.

    Use this to verify server address before saving.
    """
    logger.info(f"Testing connection to {body.postgres_host}:{body.postgres_port}")
    result = _test_pg_connection(
        host=body.postgres_host,
        port=body.postgres_port,
        user=body.postgres_user,
        password=body.postgres_password,
        db=body.postgres_db,
    )
    if result.success:
        logger.info(f"Connection test passed: {result.pg_version}")
    else:
        logger.warning(f"Connection test failed: {result.message}")
    return result


@router.post("/test-current", response_model=ConnectionTestResult)
async def test_current_connection(_user=Depends(get_current_active_user_async)):
    """Test the current active database connection."""
    if config.ACTIVE_DATABASE_TYPE == "sqlite":
        return ConnectionTestResult(
            success=True,
            message="Using local SQLite database (offline mode)",
        )

    return _test_pg_connection(
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        user=config.POSTGRES_USER,
        password=config.POSTGRES_PASSWORD,
        db=config.POSTGRES_DB,
    )


# ============================================================================
# Server Setup (runs PG initialization from within the app)
# ============================================================================

class SetupRequest(BaseModel):
    """Request to set up as LAN server."""
    pg_superuser: str = "postgres"
    pg_superuser_password: str = ""


class SetupStep(BaseModel):
    """A single setup step result."""
    step: str
    success: bool
    message: str


class SetupResult(BaseModel):
    """Full setup result."""
    success: bool
    steps: list[SetupStep]
    lan_ip: str | None = None
    admin_dashboard_url: str | None = None
    message: str


@router.post("/setup", response_model=SetupResult)
async def run_server_setup(body: SetupRequest, request: Request, _user=Depends(get_current_active_user_async)):
    """
    Run full LAN server setup from within the app.

    This replaces the manual setup_pg_server.py script.
    Only works from localhost (the admin machine).

    Steps:
    1. Verify PostgreSQL is running
    2. Create service account + database
    3. Initialize LocaNext schema
    4. Generate SSL certificates (if openssl available)
    5. Configure pg_hba.conf for LAN access
    6. Generate server-config.json
    7. Set this machine as Origin Admin
    """
    import re
    import secrets
    import subprocess
    import os as _os
    from pathlib import Path

    # Security: only allow setup from localhost
    from starlette.responses import JSONResponse
    client_ip = request.client.host if request.client else "unknown"
    if client_ip not in ("127.0.0.1", "::1"):
        logger.warning(f"Setup rejected for non-localhost IP: {client_ip}")
        return JSONResponse(
            {"success": False, "steps": [], "message": f"Setup only available from localhost. Your IP: {client_ip}"},
            status_code=403,
        )

    # Validate pg_superuser (prevent injection via username)
    _SAFE_PG_ID = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,62}$')
    if not _SAFE_PG_ID.match(body.pg_superuser):
        return SetupResult(
            success=False, steps=[],
            message="Invalid PostgreSQL username format",
        )

    steps = []
    lan_ip = _get_lan_ip()

    # Find PostgreSQL binaries — check bundled location first, then system PATH
    def _find_pg_bin() -> str | None:
        """Find psql binary — bundled or system."""
        # Check bundled PG (Electron: resources/bin/postgresql/bin/)
        resources = _os.environ.get("LOCANEXT_RESOURCES_PATH", "")
        if resources:
            bundled = Path(resources) / "bin" / "postgresql" / "bin" / "psql.exe"
            if bundled.exists():
                return str(bundled.parent)
        # Check project-level (dev)
        project_pg = Path(__file__).parent.parent.parent / "bin" / "postgresql" / "bin"
        if (project_pg / "psql.exe").exists() or (project_pg / "psql").exists():
            return str(project_pg)
        return None  # Fall back to system PATH

    pg_bin_dir = _find_pg_bin()

    def _pg_cmd(cmd: str) -> str:
        """Get full path to a PG command."""
        if pg_bin_dir:
            candidate = Path(pg_bin_dir) / cmd
            if candidate.exists():
                return str(candidate)
            candidate = Path(pg_bin_dir) / f"{cmd}.exe"
            if candidate.exists():
                return str(candidate)
        return cmd  # Fall back to system PATH

    def run_psql(sql: str, user: str = "postgres", db: str = "postgres") -> tuple[bool, str]:
        """Run a psql command."""
        env = _os.environ.copy()
        if body.pg_superuser_password:
            env["PGPASSWORD"] = body.pg_superuser_password
        # Add bundled PG lib to PATH for DLL resolution
        if pg_bin_dir:
            lib_dir = str(Path(pg_bin_dir).parent / "lib")
            env["PATH"] = pg_bin_dir + _os.pathsep + lib_dir + _os.pathsep + env.get("PATH", "")
        try:
            result = subprocess.run(
                [_pg_cmd("psql"), "-U", user, "-d", db, "-t", "-c", sql],
                capture_output=True, text=True, timeout=10, env=env,
            )
            return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
        except FileNotFoundError:
            return False, "psql not found — is PostgreSQL installed or bundled?"
        except subprocess.TimeoutExpired:
            return False, "Command timed out"

    # Step 0: If bundled PG, initialize data dir and start server
    if pg_bin_dir:
        data_dir = Path(pg_bin_dir).parent / "data"
        if not data_dir.exists():
            steps.append(SetupStep(step="Init bundled PG", success=True, message="Initializing data directory..."))
            try:
                env = _os.environ.copy()
                env["PATH"] = pg_bin_dir + _os.pathsep + env.get("PATH", "")
                init_result = subprocess.run(
                    [_pg_cmd("initdb"), "-D", str(data_dir), "-U", "postgres", "-E", "UTF8", "--locale=C"],
                    capture_output=True, text=True, timeout=30, env=env,
                )
                if init_result.returncode != 0:
                    steps[-1] = SetupStep(step="Init bundled PG", success=False, message=init_result.stderr[:200])
                else:
                    steps[-1] = SetupStep(step="Init bundled PG", success=True, message="Data directory initialized")
            except Exception as e:
                steps.append(SetupStep(step="Init bundled PG", success=False, message=str(e)[:200]))

        # Start PG if not running
        ok_check, _ = run_psql("SELECT 1;")
        if not ok_check and data_dir.exists():
            try:
                env = _os.environ.copy()
                env["PATH"] = pg_bin_dir + _os.pathsep + env.get("PATH", "")
                log_file = data_dir / "postgresql.log"
                # Use run with -w (wait) so we know when it's done
                start_result = subprocess.run(
                    [_pg_cmd("pg_ctl"), "start", "-D", str(data_dir), "-l", str(log_file), "-w"],
                    capture_output=True, text=True, timeout=30, env=env,
                )
                # Verify PG actually responds
                ok_verify, _ = run_psql("SELECT 1;")
                if ok_verify:
                    steps.append(SetupStep(step="Start bundled PG", success=True, message="PostgreSQL started"))
                else:
                    steps.append(SetupStep(step="Start bundled PG", success=False, message="pg_ctl ran but PostgreSQL not responding"))
            except Exception as e:
                steps.append(SetupStep(step="Start bundled PG", success=False, message=str(e)[:200]))

    # Step 1: Check PostgreSQL
    ok, msg = run_psql("SELECT version();")
    steps.append(SetupStep(step="Check PostgreSQL", success=ok, message=msg[:200] if ok else msg))
    if not ok:
        return SetupResult(
            success=False, steps=steps, lan_ip=lan_ip,
            message="PostgreSQL not reachable. Make sure it's installed and running, or check that the bundled PostgreSQL started correctly.",
        )

    # Step 2: Create service account (CRITICAL — abort on failure)
    db_password = secrets.token_urlsafe(24)
    ok, msg = run_psql(f"SELECT 1 FROM pg_roles WHERE rolname = 'locanext_service';")
    if "1" in msg:
        ok2, msg2 = run_psql(f"ALTER USER locanext_service WITH PASSWORD '{db_password}';")
        steps.append(SetupStep(step="Update service account", success=ok2, message="Password updated" if ok2 else msg2))
    else:
        ok2, msg2 = run_psql(
            f"CREATE USER locanext_service WITH PASSWORD '{db_password}' NOSUPERUSER NOCREATEDB NOCREATEROLE;"
        )
        steps.append(SetupStep(step="Create service account", success=ok2, message="Created" if ok2 else msg2))
    if not ok2:
        return SetupResult(success=False, steps=steps, lan_ip=lan_ip, message="Failed to create service account — check PostgreSQL permissions.")

    # Step 3: Create database (CRITICAL — abort on failure)
    ok, msg = run_psql(f"SELECT 1 FROM pg_database WHERE datname = 'localizationtools';")
    if "1" in msg:
        steps.append(SetupStep(step="Create database", success=True, message="Database already exists"))
    else:
        ok3, msg3 = run_psql("CREATE DATABASE localizationtools OWNER locanext_service;")
        steps.append(SetupStep(step="Create database", success=ok3, message="Created" if ok3 else msg3))
        if not ok3:
            return SetupResult(success=False, steps=steps, lan_ip=lan_ip, message="Failed to create database.")

    # Grant permissions (tracked)
    ok_g1, msg_g1 = run_psql("GRANT ALL PRIVILEGES ON DATABASE localizationtools TO locanext_service;")
    ok_g2, msg_g2 = run_psql("GRANT ALL ON SCHEMA public TO locanext_service;", db="localizationtools")
    if not ok_g1 or not ok_g2:
        steps.append(SetupStep(step="Grant permissions", success=False, message=msg_g1 or msg_g2))
        return SetupResult(success=False, steps=steps, lan_ip=lan_ip, message="Failed to grant permissions.")
    steps.append(SetupStep(step="Grant permissions", success=True, message="Granted"))

    # Step 4: Initialize schema (uses LocaNext's own setup)
    # Temporarily set env vars, clean up in finally block
    _env_keys = ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "DATABASE_MODE"]
    _env_backup = {k: _os.environ.get(k) for k in _env_keys}
    try:
        _os.environ["POSTGRES_HOST"] = "localhost"
        _os.environ["POSTGRES_PORT"] = "5432"
        _os.environ["POSTGRES_USER"] = "locanext_service"
        _os.environ["POSTGRES_PASSWORD"] = db_password
        _os.environ["POSTGRES_DB"] = "localizationtools"
        _os.environ["DATABASE_MODE"] = "postgresql"

        from server.database.db_setup import setup_database
        engine, _ = setup_database(force_mode="postgresql")
        engine.dispose()
        steps.append(SetupStep(step="Initialize schema", success=True, message="All tables created"))
    except Exception as e:
        logger.error(f"Schema init failed: {e}")
        steps.append(SetupStep(step="Initialize schema", success=False, message=str(e)[:200]))
    finally:
        # Restore original env vars
        for k, v in _env_backup.items():
            if v is None:
                _os.environ.pop(k, None)
            else:
                _os.environ[k] = v

    # Step 5: SSL certificates (optional — depends on openssl)
    # Initialize data_dir for Steps 5+6
    data_dir = None
    try:
        ok_dd, dd_msg = run_psql("SHOW data_directory;")
        if ok_dd and dd_msg.strip():
            data_dir = dd_msg.strip()

        if data_dir and Path(data_dir).exists() and (Path(data_dir) / "postgresql.conf").exists():
            cert_path = Path(data_dir) / "server.crt"
            key_path = Path(data_dir) / "server.key"
            if not cert_path.exists():
                ssl_result = subprocess.run([
                    "openssl", "req", "-new", "-x509", "-days", "3650",
                    "-nodes",
                    "-out", str(cert_path), "-keyout", str(key_path),
                    "-subj", "/CN=LocaNext-PG-Server/O=LocaNext/C=KR",
                ], capture_output=True, text=True, timeout=10)
                if ssl_result.returncode == 0:
                    try:
                        _os.chmod(str(key_path), 0o600)
                    except OSError:
                        pass
                    steps.append(SetupStep(step="SSL certificates", success=True, message="Generated"))
                else:
                    steps.append(SetupStep(step="SSL certificates", success=False, message="OpenSSL not available — skipped"))
            else:
                steps.append(SetupStep(step="SSL certificates", success=True, message="Already exist"))
        else:
            steps.append(SetupStep(step="SSL certificates", success=False, message="Could not find PG data directory"))
    except Exception as e:
        steps.append(SetupStep(step="SSL certificates", success=False, message=f"Skipped: {e}"))

    # Step 6: Configure pg_hba.conf for LAN
    if data_dir:
        try:
            subnet = f"{'.'.join((lan_ip or '192.168.1.1').split('.')[:3])}.0/24"
            pg_hba_path = Path(data_dir) / "pg_hba.conf"
            if pg_hba_path.exists():
                content = pg_hba_path.read_text()
                marker = "# LocaNext LAN access"
                if marker not in content:
                    lan_rule = f"\n{marker}\nhostssl    localizationtools    locanext_service    {subnet}    scram-sha-256\nhostnossl  localizationtools    locanext_service    {subnet}    reject\n"
                    with open(pg_hba_path, "a") as f:
                        f.write(lan_rule)
                    # Reload PG config
                    run_psql("SELECT pg_reload_conf();")
                    steps.append(SetupStep(step="LAN access", success=True, message=f"Configured for {subnet}"))
                else:
                    steps.append(SetupStep(step="LAN access", success=True, message="Already configured"))
            else:
                steps.append(SetupStep(step="LAN access", success=False, message="pg_hba.conf not found"))
        except Exception as e:
            steps.append(SetupStep(step="LAN access", success=False, message=str(e)[:200]))

    # Step 7: Save server config
    secret_key = secrets.token_urlsafe(32)
    server_config = {
        "postgres_host": "localhost",
        "postgres_port": 5432,
        "postgres_user": "locanext_service",
        "postgres_password": db_password,
        "postgres_db": "localizationtools",
        "database_mode": "auto",
        "server_mode": "lan_server",
        "lan_ip": lan_ip,
        "secret_key": secret_key,
        "origin_admin_ip": "127.0.0.1",
    }
    saved = config.save_user_config(server_config)
    # Set file permissions
    try:
        _os.chmod(str(config.USER_CONFIG_PATH), 0o600)
    except OSError:
        pass
    steps.append(SetupStep(
        step="Save configuration",
        success=saved,
        message="Config saved — restart app to apply" if saved else "Failed to save config",
    ))

    all_ok = all(s.success for s in steps if s.step not in ("SSL certificates",))  # SSL is optional
    return SetupResult(
        success=all_ok,
        steps=steps,
        lan_ip=lan_ip,
        admin_dashboard_url="http://localhost:5174" if all_ok else None,
        message="Server setup complete! Restart LocaNext to apply." if all_ok else "Setup completed with errors — check steps above.",
    )


@router.post("/setup/retry")
async def retry_server_setup(request: Request, _user=Depends(get_current_active_user_async)):
    """Retry server setup from Admin Dashboard."""
    from server.utils.auth import validate_admin_token
    if not validate_admin_token(request):
        from starlette.responses import JSONResponse
        return JSONResponse({"error": "Admin token required"}, status_code=403)

    import os as _os
    from pathlib import Path
    from server.setup import SetupConfig
    from server.setup.runner import run_setup
    from server.setup.pg_lifecycle import find_pg_binaries

    resources_path = _os.environ.get("LOCANEXT_RESOURCES_PATH", "")
    pg = find_pg_binaries(resources_path)
    if not pg:
        from starlette.responses import JSONResponse
        return JSONResponse({"error": "No bundled PostgreSQL found"}, status_code=400)

    if _os.name == "nt":
        state_dir = Path(_os.environ.get("APPDATA", "")) / "LocaNext"
    else:
        state_dir = Path.home() / ".config" / "locanext"

    setup_config = SetupConfig(pg_bin_dir=str(pg.bin_dir), data_dir=str(pg.data_dir))
    result = run_setup(setup_config, state_path=state_dir / "setup_state.json")

    return {
        "success": result.success,
        "steps": [{"step": s.step, "status": s.status, "message": s.message,
                    "duration_ms": s.duration_ms} for s in result.steps],
        "lan_ip": result.lan_ip,
        "message": "Restart app to apply" if result.success else "Setup failed",
    }
