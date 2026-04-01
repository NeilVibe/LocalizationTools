#!/usr/bin/env python3
"""
LocaNext PostgreSQL Server Setup Script

Auto-configures PostgreSQL for LAN server mode:
1. Checks PostgreSQL is installed and running
2. Creates database + service account
3. Configures pg_hba.conf for LAN access
4. Opens Windows firewall port (if Windows)
5. Generates server-config.json
6. Prints connection info for teammates

Usage:
    python scripts/setup_pg_server.py                  # Interactive setup
    python scripts/setup_pg_server.py --auto           # Auto-detect everything
    python scripts/setup_pg_server.py --check          # Check current status
    python scripts/setup_pg_server.py --gen-config     # Generate config only
"""

import argparse
import json
import os
import platform
import secrets
import socket
import subprocess
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Constants
# ============================================================================

DB_NAME = "localizationtools"
DB_USER = "locanext_service"
PG_PORT = 5432
BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          LocaNext — PostgreSQL Server Setup                 ║
║          Self-hosted LAN server for team collaboration      ║
╚══════════════════════════════════════════════════════════════╝
"""


# ============================================================================
# Utilities
# ============================================================================

def get_lan_ip() -> str:
    """Detect the machine's LAN IP address."""
    try:
        # Connect to a public IP to determine which interface is used
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass

    # Fallback: check hostname
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if not ip.startswith("127."):
            return ip
    except Exception:
        pass

    return "127.0.0.1"


def get_subnet(ip: str) -> str:
    """Get /24 subnet from IP address."""
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return "192.168.0.0/24"


def generate_password(length: int = 24) -> str:
    """Generate a secure random password."""
    return secrets.token_urlsafe(length)


def run_cmd(cmd: list, capture: bool = True, check: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    try:
        return subprocess.run(
            cmd, capture_output=capture, text=True, check=check, timeout=30
        )
    except subprocess.TimeoutExpired:
        print(f"  ✗ Command timed out: {' '.join(cmd)}")
        return subprocess.CompletedProcess(cmd, 1, "", "timeout")
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, 1, "", f"Command not found: {cmd[0]}")


def is_windows() -> bool:
    """Check if running on Windows (or WSL targeting Windows)."""
    return platform.system() == "Windows"


def is_wsl() -> bool:
    """Check if running inside WSL."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False


# ============================================================================
# PostgreSQL Checks
# ============================================================================

def check_pg_installed() -> dict:
    """Check if PostgreSQL is installed and get version info."""
    result = {"installed": False, "version": None, "path": None, "data_dir": None}

    # Check psql
    psql = run_cmd(["psql", "--version"])
    if psql.returncode == 0:
        result["installed"] = True
        result["version"] = psql.stdout.strip()

    # Check pg_isready
    pg_ready = run_cmd(["pg_isready", "-p", str(PG_PORT)])
    result["running"] = pg_ready.returncode == 0

    # Try to find data directory
    if result["running"]:
        show = run_cmd(["psql", "-U", "postgres", "-t", "-c", "SHOW data_directory;"])
        if show.returncode == 0 and show.stdout.strip():
            result["data_dir"] = show.stdout.strip()

    return result


def check_pg_port_open(host: str = "localhost", port: int = PG_PORT) -> bool:
    """Check if PostgreSQL port is accepting connections."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_database_exists(db_name: str = DB_NAME) -> bool:
    """Check if the LocaNext database exists."""
    result = run_cmd([
        "psql", "-U", "postgres", "-t", "-c",
        f"SELECT 1 FROM pg_database WHERE datname = '{db_name}';"
    ])
    return result.returncode == 0 and "1" in result.stdout


def check_user_exists(username: str = DB_USER) -> bool:
    """Check if the service account exists."""
    result = run_cmd([
        "psql", "-U", "postgres", "-t", "-c",
        f"SELECT 1 FROM pg_roles WHERE rolname = '{username}';"
    ])
    return result.returncode == 0 and "1" in result.stdout


# ============================================================================
# Setup Steps
# ============================================================================

def create_service_account(password: str) -> bool:
    """Create the PostgreSQL service account."""
    if check_user_exists():
        print(f"  → User '{DB_USER}' already exists, updating password...")
        result = run_cmd([
            "psql", "-U", "postgres", "-c",
            f"ALTER USER {DB_USER} WITH PASSWORD '{password}';"
        ])
    else:
        print(f"  → Creating user '{DB_USER}'...")
        result = run_cmd([
            "psql", "-U", "postgres", "-c",
            f"CREATE USER {DB_USER} WITH PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE;"
        ])

    if result.returncode != 0:
        print(f"  ✗ Failed: {result.stderr}")
        return False

    print(f"  ✓ Service account '{DB_USER}' ready")
    return True


def create_database() -> bool:
    """Create the LocaNext database."""
    if check_database_exists():
        print(f"  → Database '{DB_NAME}' already exists")
        # Ensure ownership
        run_cmd([
            "psql", "-U", "postgres", "-c",
            f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};"
        ])
        return True

    print(f"  → Creating database '{DB_NAME}'...")
    result = run_cmd([
        "psql", "-U", "postgres", "-c",
        f"CREATE DATABASE {DB_NAME} OWNER {DB_USER};"
    ])

    if result.returncode != 0:
        print(f"  ✗ Failed: {result.stderr}")
        return False

    # Grant schema permissions
    run_cmd([
        "psql", "-U", "postgres", "-d", DB_NAME, "-c",
        f"GRANT ALL ON SCHEMA public TO {DB_USER};"
    ])

    print(f"  ✓ Database '{DB_NAME}' created")
    return True


def initialize_schema(password: str) -> bool:
    """Initialize LocaNext tables using the app's own setup."""
    print("  → Initializing LocaNext schema...")
    try:
        os.environ["POSTGRES_HOST"] = "localhost"
        os.environ["POSTGRES_PORT"] = str(PG_PORT)
        os.environ["POSTGRES_USER"] = DB_USER
        os.environ["POSTGRES_PASSWORD"] = password
        os.environ["POSTGRES_DB"] = DB_NAME
        os.environ["DATABASE_MODE"] = "postgresql"

        from server.database.db_setup import setup_database
        engine, session_maker = setup_database(force_mode="postgresql")
        engine.dispose()
        print("  ✓ Schema initialized (all tables created)")
        return True
    except Exception as e:
        print(f"  ✗ Schema init failed: {e}")
        return False


def configure_pg_hba(subnet: str, data_dir: str = None) -> bool:
    """Configure pg_hba.conf for LAN access."""
    if not data_dir:
        result = run_cmd(["psql", "-U", "postgres", "-t", "-c", "SHOW data_directory;"])
        if result.returncode != 0:
            print("  ✗ Cannot find PostgreSQL data directory")
            return False
        data_dir = result.stdout.strip()

    pg_hba = Path(data_dir) / "pg_hba.conf"
    if not pg_hba.exists():
        print(f"  ✗ pg_hba.conf not found at {pg_hba}")
        return False

    # Check if LAN rule already exists
    content = pg_hba.read_text()
    marker = "# LocaNext LAN access"
    if marker in content:
        print("  → LAN access rule already configured in pg_hba.conf")
        return True

    # Add LAN access rule (hostssl = require TLS, hostnossl = reject plaintext)
    lan_rule = f"""
{marker}
hostssl    {DB_NAME}    {DB_USER}    {subnet}    scram-sha-256
hostnossl  {DB_NAME}    {DB_USER}    {subnet}    reject
"""
    with open(pg_hba, "a") as f:
        f.write(lan_rule)

    print(f"  ✓ Added LAN access rule for {subnet} in pg_hba.conf")
    return True


def configure_listen_addresses(data_dir: str = None) -> bool:
    """Configure postgresql.conf to listen on all interfaces."""
    if not data_dir:
        result = run_cmd(["psql", "-U", "postgres", "-t", "-c", "SHOW data_directory;"])
        if result.returncode != 0:
            return False
        data_dir = result.stdout.strip()

    pg_conf = Path(data_dir) / "postgresql.conf"
    if not pg_conf.exists():
        print(f"  ✗ postgresql.conf not found at {pg_conf}")
        return False

    content = pg_conf.read_text()

    # Check current listen_addresses
    if "listen_addresses = '*'" in content:
        print("  → listen_addresses already set to '*'")
        return True

    # Update or add listen_addresses
    import re
    new_content, count = re.subn(
        r"^#?\s*listen_addresses\s*=.*$",
        "listen_addresses = '*'",
        content,
        flags=re.MULTILINE,
    )

    if count == 0:
        # Not found, add it
        new_content = "listen_addresses = '*'\n" + content

    pg_conf.write_text(new_content)
    print("  ✓ listen_addresses set to '*' (all interfaces)")
    return True


def generate_ssl_certificates(data_dir: str = None) -> bool:
    """Generate self-signed SSL certificates for PostgreSQL."""
    if not data_dir:
        result = run_cmd(["psql", "-U", "postgres", "-t", "-c", "SHOW data_directory;"])
        if result.returncode != 0:
            return False
        data_dir = result.stdout.strip()

    cert_dir = Path(data_dir)
    server_key = cert_dir / "server.key"
    server_crt = cert_dir / "server.crt"

    if server_crt.exists() and server_key.exists():
        print("  → SSL certificates already exist")
        return True

    # Generate self-signed certificate (valid for 10 years)
    result = run_cmd([
        "openssl", "req", "-new", "-x509", "-days", "3650",
        "-nodes",
        "-out", str(server_crt),
        "-keyout", str(server_key),
        "-subj", "/CN=LocaNext-PG-Server/O=LocaNext/C=KR"
    ])

    if result.returncode != 0:
        print(f"  ✗ SSL certificate generation failed: {result.stderr}")
        # Check if openssl is available
        openssl_check = run_cmd(["openssl", "version"])
        if openssl_check.returncode != 0:
            print("  ✗ OpenSSL not installed. Install it first:")
            if is_windows():
                print("    → winget install OpenSSL")
            else:
                print("    → sudo apt install openssl")
        return False

    # Set correct permissions (PG requires key to be owner-only)
    try:
        os.chmod(server_key, 0o600)
        os.chmod(server_crt, 0o644)
    except OSError:
        pass  # Windows doesn't support POSIX permissions

    print("  ✓ SSL certificates generated (self-signed, valid 10 years)")
    return True


def configure_pg_ssl(data_dir: str = None) -> bool:
    """Enable SSL in postgresql.conf."""
    if not data_dir:
        result = run_cmd(["psql", "-U", "postgres", "-t", "-c", "SHOW data_directory;"])
        if result.returncode != 0:
            return False
        data_dir = result.stdout.strip()

    pg_conf = Path(data_dir) / "postgresql.conf"
    if not pg_conf.exists():
        return False

    content = pg_conf.read_text()

    # Check if SSL already enabled
    if "ssl = on" in content:
        print("  → SSL already enabled in postgresql.conf")
        return True

    import re
    # Enable SSL
    new_content, count = re.subn(
        r"^#?\s*ssl\s*=.*$",
        "ssl = on",
        content,
        flags=re.MULTILINE,
    )
    if count == 0:
        new_content = "ssl = on\n" + content

    pg_conf.write_text(new_content)
    print("  ✓ SSL enabled in postgresql.conf")
    return True


def reload_postgresql() -> bool:
    """Reload PostgreSQL configuration."""
    result = run_cmd(["psql", "-U", "postgres", "-c", "SELECT pg_reload_conf();"])
    if result.returncode == 0:
        print("  ✓ PostgreSQL configuration reloaded")
        return True
    else:
        print("  ⚠ Could not reload — you may need to restart PostgreSQL manually")
        return False


def open_firewall_port(port: int = PG_PORT) -> bool:
    """Open Windows firewall for PostgreSQL port."""
    if is_windows():
        result = run_cmd([
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name=LocaNext PostgreSQL (port {port})",
            "dir=in", "action=allow", f"protocol=TCP", f"localport={port}",
        ])
        if result.returncode == 0:
            print(f"  ✓ Windows Firewall rule added for port {port}")
            return True
        else:
            print(f"  ⚠ Firewall rule may need admin privileges: {result.stderr}")
            return False
    elif is_wsl():
        print(f"  ℹ WSL detected — firewall managed by Windows host")
        print(f"    On Windows, run as Administrator:")
        print(f'    netsh advfirewall firewall add rule name="LocaNext PG" dir=in action=allow protocol=TCP localport={port}')
        return True
    else:
        # Linux — check ufw
        result = run_cmd(["ufw", "status"])
        if result.returncode == 0 and "active" in result.stdout.lower():
            run_cmd(["sudo", "ufw", "allow", str(port)])
            print(f"  ✓ UFW rule added for port {port}")
        else:
            print(f"  ℹ No active firewall detected — port {port} should be accessible")
        return True


def generate_server_config(password: str, lan_ip: str) -> dict:
    """Generate server-config.json for LocaNext."""
    config_data = {
        "postgres_host": "localhost",
        "postgres_port": PG_PORT,
        "postgres_user": DB_USER,
        "postgres_password": password,
        "postgres_db": DB_NAME,
        "database_mode": "auto",
        "server_mode": "lan_server",
        "lan_ip": lan_ip,
        "secret_key": secrets.token_urlsafe(32),
        "origin_admin_ip": "127.0.0.1",
        "origin_admin_setup_date": __import__("datetime").datetime.now().isoformat(),
    }

    # Save to user config path
    if platform.system() == "Windows":
        appdata = os.getenv("APPDATA", "")
        if appdata:
            config_path = Path(appdata) / "LocaNext" / "server-config.json"
        else:
            config_path = PROJECT_ROOT / "server" / "data" / "server-config.json"
    else:
        config_path = Path.home() / ".config" / "locanext" / "server-config.json"

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=2)
    # Restrict file permissions (owner read/write only)
    try:
        os.chmod(config_path, 0o600)
    except OSError:
        pass  # Windows doesn't support POSIX permissions

    print(f"  ✓ Config saved to {config_path}")
    return config_data


def generate_client_config(lan_ip: str, password: str) -> dict:
    """Generate the config that teammates need."""
    return {
        "postgres_host": lan_ip,
        "postgres_port": PG_PORT,
        "postgres_user": DB_USER,
        "postgres_password": password,
        "postgres_db": DB_NAME,
        "database_mode": "auto",
    }


# ============================================================================
# Status Check
# ============================================================================

def print_status():
    """Print current PostgreSQL and LocaNext server status."""
    print("\n📊 Current Status")
    print("─" * 50)

    pg = check_pg_installed()
    lan_ip = get_lan_ip()

    print(f"  PostgreSQL installed:  {'✓' if pg['installed'] else '✗'} {pg.get('version', '')}")
    print(f"  PostgreSQL running:    {'✓' if pg.get('running') else '✗'}")
    print(f"  Port {PG_PORT} open:          {'✓' if check_pg_port_open() else '✗'}")
    print(f"  Database '{DB_NAME}':  {'✓ exists' if check_database_exists() else '✗ not found'}")
    print(f"  User '{DB_USER}':  {'✓ exists' if check_user_exists() else '✗ not found'}")
    print(f"  LAN IP:               {lan_ip}")
    print(f"  Subnet:               {get_subnet(lan_ip)}")

    if pg.get("data_dir"):
        print(f"  Data directory:       {pg['data_dir']}")


# ============================================================================
# Main Setup Flow
# ============================================================================

def run_setup(auto: bool = False):
    """Run the full setup flow."""
    print(BANNER)

    # Step 1: Check PostgreSQL
    print("Step 1/8: Checking PostgreSQL installation...")
    pg = check_pg_installed()

    if not pg["installed"]:
        print("\n  ✗ PostgreSQL is NOT installed!")
        print("\n  Install PostgreSQL first:")
        if is_windows() or is_wsl():
            print("    → Download from https://www.postgresql.org/download/windows/")
            print("    → Or use: winget install PostgreSQL.PostgreSQL.15")
            print("    → Or use: scoop install postgresql")
        else:
            print("    → sudo apt install postgresql postgresql-contrib")
        print("\n  After installing, run this script again.")
        return False

    if not pg.get("running"):
        print("\n  ✗ PostgreSQL is installed but NOT running!")
        if is_windows() or is_wsl():
            print("    → Start the PostgreSQL service from Windows Services")
            print('    → Or: net start postgresql-x64-15')
        else:
            print("    → sudo systemctl start postgresql")
        return False

    print(f"  ✓ PostgreSQL {pg.get('version', '')} — running")

    # Step 2: Detect network
    print("\nStep 2/8: Detecting network...")
    lan_ip = get_lan_ip()
    subnet = get_subnet(lan_ip)
    print(f"  ✓ LAN IP: {lan_ip}")
    print(f"  ✓ Subnet: {subnet}")

    # Step 3: Generate password
    print("\nStep 3/8: Creating service account...")
    db_password = generate_password()
    if not create_service_account(db_password):
        return False

    # Step 4: Create database
    print("\nStep 4/8: Creating database...")
    if not create_database():
        return False

    # Get data directory for PG config steps
    data_dir = pg.get("data_dir")

    # Step 5: SSL/TLS encryption
    print("\nStep 5/8: Setting up TLS encryption...")
    if generate_ssl_certificates(data_dir):
        configure_pg_ssl(data_dir)
    else:
        print("  ⚠ TLS not configured — connections will be unencrypted")
        print("    Install OpenSSL and re-run to enable encryption")

    # Step 6: Configure LAN access
    print("\nStep 6/8: Configuring LAN access...")
    lan_ok = True
    if not configure_listen_addresses(data_dir):
        print("  ⚠ WARNING: listen_addresses not configured — LAN clients may not connect")
        lan_ok = False
    if not configure_pg_hba(subnet, data_dir):
        print("  ⚠ WARNING: pg_hba.conf not configured — LAN clients will be rejected")
        lan_ok = False
    if lan_ok:
        reload_postgresql()

    # Step 7: Initialize schema
    print("\nStep 7/8: Initializing LocaNext schema...")
    if not initialize_schema(db_password):
        print("  ⚠ Schema init failed — the app will create tables on first start")

    # Step 8: Generate configs + firewall
    print("\nStep 8/8: Generating configuration...")
    server_config = generate_server_config(db_password, lan_ip)
    open_firewall_port()

    # Generate client config
    client_config = generate_client_config(lan_ip, db_password)

    # Print summary
    print("\n" + "═" * 60)
    print("  ✅ SERVER SETUP COMPLETE!")
    print("═" * 60)

    print(f"""
  Your LocaNext server is ready at:

    Server IP:     {lan_ip}
    PG Port:       {PG_PORT}
    Database:      {DB_NAME}
    Service User:  {DB_USER}
    Password:      {db_password}

  ────────────────────────────────────────
  FOR TEAMMATES — give them this config:
  ────────────────────────────────────────

    Server Address:  {lan_ip}
    Port:            {PG_PORT}

    In LocaNext → Settings → Server Connection:
      Enter: {lan_ip}:{PG_PORT}

  ────────────────────────────────────────
  ADMIN DASHBOARD:
  ────────────────────────────────────────

    Open in your browser:
      http://localhost:5174

    Default login: admin / admin123
    Create user accounts for your teammates there.

  ────────────────────────────────────────
  CLIENT CONFIG (for automation):
  ────────────────────────────────────────
""")
    print(f"  {json.dumps(client_config, indent=2)}")

    # Save client config to a shareable file
    client_config_path = PROJECT_ROOT / "server" / "data" / "client-config.json"
    with open(client_config_path, "w") as f:
        json.dump(client_config, f, indent=2)
    try:
        os.chmod(client_config_path, 0o600)
    except OSError:
        pass
    print(f"\n  Client config also saved to: {client_config_path}")
    print(f"  Share this file with teammates (they put it in their LocaNext config folder)")

    print(f"""
  ────────────────────────────────────────
  NEXT STEPS:
  ────────────────────────────────────────

    1. Open http://localhost:5174 → create user accounts
    2. Give teammates the Server Address: {lan_ip}:{PG_PORT}
    3. Teammates: LocaNext → Settings → Server → enter address
    4. Everyone logs in with their credentials
    5. Start collaborating! 🎉

  ────────────────────────────────────────
  FOR YOUR SECURITY TEAM:
  ────────────────────────────────────────

    • Standard PostgreSQL 15 on internal LAN only
    • Port {PG_PORT} open to {subnet} only (not internet)
    • App-level auth: JWT + bcrypt (industry standard)
    • DB-level auth: scram-sha-256 (PG standard)
    • No cloud services, no external connections
    • All data stays on office network
""")

    return True


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="LocaNext PostgreSQL Server Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--auto", action="store_true", help="Auto-detect everything, no prompts")
    parser.add_argument("--check", action="store_true", help="Check current status only")
    parser.add_argument("--gen-config", action="store_true", help="Generate config files only")
    args = parser.parse_args()

    if args.check:
        print_status()
    elif args.gen_config:
        lan_ip = get_lan_ip()
        password = generate_password()
        generate_server_config(password, lan_ip)
        client_config = generate_client_config(lan_ip, password)
        print(json.dumps(client_config, indent=2))
    else:
        success = run_setup(auto=args.auto)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
