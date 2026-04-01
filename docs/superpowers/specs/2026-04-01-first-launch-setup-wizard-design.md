# First-Launch Setup Wizard — Design Spec

**Date:** 2026-04-01
**Status:** Draft
**Scope:** Full Build first-launch PostgreSQL setup with step-by-step progress

---

## 1. Problem

The Full Build bundles PostgreSQL portable so the admin PC becomes a LAN server. Currently, the entire PG setup (initdb, start, create user, create DB, SSL, LAN config) runs as one synchronous blob in `server/main.py` before FastAPI starts. No progress feedback, no error handling between steps, no verification. Electron's 30-second health check times out. The app crashes on first launch.

## 2. User Experience

### First launch (admin PC, Full Build)

1. Double-click LocaNext.exe
2. Splash screen appears: **"Setting up server..."**
3. Each step displays in real time:
   ```
   ✓ Checking system requirements...      1s
   ✓ Initializing database...             4s
   ✓ Configuring network access...        1s
   ✓ Starting PostgreSQL...               8s
   ✓ Creating service account...          2s
   ✓ Creating database...                 3s
   ⏳ Generating security certificates...
   ```
4. All done: splash shows **"Server ready! LAN IP: 192.168.1.100"** for 2 seconds
5. App opens. **No login screen.** Admin is identified by local token.
6. **Never runs again.** State file records completion.

### If a step fails

Splash shows the failed step with options:
```
✓ Initializing database...             4s
✓ Configuring network access...        1s
✗ Starting PostgreSQL... FAILED

  Error: Port 5432 already in use by another process.

  [Show Full Log]   [Retry]   [Start Offline]
```

- **Show Full Log:** Opens the setup log file in the default text editor.
- **Retry:** Re-runs from the failed step (not from the beginning).
- **Start Offline:** Starts in SQLite mode. Admin can retry later from the Admin Dashboard.

### Subsequent launches (admin PC)

1. Splash: **"Starting database..."** (pg_ctl start, ~5s)
2. Splash: **"Starting server..."** (FastAPI, ~3s)
3. App opens. No login.

### Team member's PC (Light Build)

1. Open LocaNext
2. Login screen: server IP + username/password (created by admin)
3. Connected. No PG setup, no wizard.

## 3. Architecture

### Module layout

```
server/setup/
  __init__.py          — exports run_setup(), StepResult, SetupResult, SetupConfig
  steps.py             — 7 step functions (pre-flight + 6 setup steps)
  runner.py            — sequential orchestrator with progress callback
  state.py             — setup_state.json read/write/resume
  pg_lifecycle.py      — pg_ctl start/stop/status helpers (used by setup AND normal launch)
  credential_store.py  — DPAPI encryption + NTFS ACL helpers
```

### Data flow — first launch

```
Electron main.js
  │
  ├─ spawns: python -m server
  │
  ├─ Python detects first-run (no setup_state.json with all steps done)
  │   ├─ Runs server/setup/runner.py → calls each step function
  │   ├─ Each step: PRE-CHECK → RUN → VERIFY → write state → emit JSONL
  │   ├─ Emits to stdout: {"type": "setup_step", "step": "init_database", ...}
  │   └─ On complete: {"type": "setup_complete", "success": true}
  │
  ├─ Electron reads stdout line-by-line
  │   ├─ Lines starting with { → parse as JSONL → update splash UI
  │   └─ Other lines → backend log output (ignore during setup)
  │
  ├─ After setup_complete → Python starts FastAPI (uvicorn)
  │   └─ Emits: {"type": "server_ready", "port": 8888}
  │
  └─ Electron sees server_ready → close splash → show main window
```

### Data flow — subsequent launch

```
Electron main.js
  │
  ├─ spawns: python -m server
  │
  ├─ Python reads setup_state.json → all steps done
  │   ├─ Calls pg_lifecycle.start() → starts PG
  │   ├─ Emits: {"type": "pg_starting"}
  │   ├─ Emits: {"type": "pg_ready"}
  │   └─ Starts FastAPI → {"type": "server_ready", "port": 8888}
  │
  └─ Electron shows splash "Starting database..." → "Starting server..." → app
```

### Data flow — retry from Admin Dashboard

```
Admin Dashboard → POST /api/server/setup/retry
  │
  ├─ Server reads setup_state.json → finds first incomplete step
  ├─ Runs remaining steps via same runner.py
  ├─ Returns SetupResult with per-step status
  └─ Admin sees result, restarts app to apply PG mode
```

### Single source of truth

The setup logic exists in ONE place: `server/setup/steps.py`. Three consumers:

| Consumer | Entry point | Progress mechanism |
|----------|------------|-------------------|
| First launch | `server/__main__.py` → `run_setup()` | JSONL on stdout |
| Admin retry | `POST /api/server/setup/retry` | HTTP response (SSE for live progress) |
| Tests | `pytest` → individual step functions | Return values |

The duplicate setup code in `server/main.py` (lines 830-950) and `server/api/server_config.py` (lines 278-566) will be **deleted** and replaced with calls to the shared module.

## 4. Setup Steps

### Step order (revised from audit)

Configuration steps happen BEFORE pg_ctl start, so PG reads the correct config on startup.

| # | Step name | What it does | Timeout | Fatal? |
|---|-----------|-------------|---------|--------|
| 0 | `preflight_checks` | Disk space (>500MB), port 5432 free, permissions | 5s | Yes |
| 1 | `init_database` | `initdb -D <data_dir> -U postgres -E UTF8 --locale=C` | 60s | Yes |
| 2 | `configure_access` | Write `pg_hba.conf` + `postgresql.conf` (listen_addresses, ports) | 5s | Yes |
| 3 | `start_database` | `pg_ctl start -D <data_dir> -l <logfile> -w` + verify with `pg_isready` | 30s | Yes |
| 4 | `create_account` | Create `locanext_service` role with random password | 10s | Yes |
| 5 | `create_database` | Create `localizationtools` DB + schema + grants | 15s | Yes |
| 6 | `generate_certificates` | Self-signed TLS cert via Python `cryptography` lib | 10s | No (optional) |

### Step function contract

```python
@dataclass
class StepResult:
    step: str                          # "init_database"
    status: Literal["done", "skipped", "failed"]
    duration_ms: int
    message: str                       # Human-readable summary
    error_code: str | None = None      # "PORT_CONFLICT", "DISK_FULL", etc.
    error_detail: str | None = None    # Full error text
    stderr: str | None = None          # Raw subprocess stderr

def step_init_database(config: SetupConfig) -> StepResult:
    """
    PRE-CHECK:  Skip if pg_data/PG_VERSION exists AND is valid (check content, not just existence)
    RUN:        subprocess.run([initdb, ...], timeout=60)
    VERIFY:     pg_data/PG_VERSION exists and contains "15"
    CLEANUP:    On failure, delete partial pg_data/ directory
    """
```

### Pre-flight checks (Step 0)

```python
def step_preflight_checks(config: SetupConfig) -> StepResult:
    """
    1. Disk space: shutil.disk_usage() — require 500MB free
    2. Port 5432: socket.connect() — must be free
    3. PG binaries: verify initdb.exe, pg_ctl.exe, psql.exe exist and are executable
    4. Write permissions: try creating a temp file in the data dir parent
    5. Windows Firewall: attempt netsh advfirewall rule for postgres.exe
       - If fails (not admin): log warning, continue (firewall popup will appear later)
    """
```

### Idempotency

Every step checks its own precondition before running. Safe to re-run after crash:

| Step | Pre-check (skip if true) |
|------|-------------------------|
| preflight | Always runs |
| init_database | `pg_data/PG_VERSION` exists with valid content |
| configure_access | `pg_hba.conf` contains `# LocaNext` marker |
| start_database | `pg_isready` returns 0 |
| create_account | `SELECT 1 FROM pg_roles WHERE rolname = 'locanext_service'` |
| create_database | `SELECT 1 FROM pg_database WHERE datname = 'localizationtools'` |
| generate_certificates | `server.crt` and `server.key` exist in pg_data |

### Cleanup on failure

| Step | Cleanup action |
|------|---------------|
| init_database | Delete partial `pg_data/` directory |
| configure_access | Restore `pg_hba.conf` from backup (copied before edit) |
| start_database | `pg_ctl stop` (in case PG is in a broken state) |
| create_account | No cleanup needed (PG is transactional) |
| create_database | `DROP DATABASE IF EXISTS localizationtools` |
| generate_certificates | Delete partial cert files |

## 5. Setup State File

Location: `<APPDATA>/LocaNext/setup_state.json`

```json
{
  "version": 1,
  "pg_major_version": 15,
  "run_id": "a1b2c3d4",
  "started_at": "2026-04-01T16:27:22Z",
  "completed_at": "2026-04-01T16:28:05Z",
  "steps": {
    "preflight_checks": {"status": "done", "at": "2026-04-01T16:27:23Z"},
    "init_database": {"status": "done", "at": "2026-04-01T16:27:27Z"},
    "configure_access": {"status": "done", "at": "2026-04-01T16:27:28Z"},
    "start_database": {"status": "done", "at": "2026-04-01T16:27:36Z"},
    "create_account": {"status": "done", "at": "2026-04-01T16:27:38Z"},
    "create_database": {"status": "done", "at": "2026-04-01T16:27:41Z"},
    "generate_certificates": {"status": "done", "at": "2026-04-01T16:27:42Z"}
  },
  "config": {
    "pg_port": 5432,
    "lan_ip": "192.168.1.100",
    "lan_subnet": "192.168.1.0/24"
  }
}
```

**Resume logic:** On launch, read state file. Find the first step that is NOT `"done"`. Run from there.

**PG version tracking:** Records `pg_major_version: 15`. If a future build bundles PG 16, the setup detects the mismatch and shows: "Database upgrade required (PG 15 -> 16)."

## 6. JSONL Protocol

Python writes JSON lines to stdout. Electron parses them. Non-JSON lines (uvicorn logs, warnings) are forwarded to Electron's log file.

### Messages

```jsonc
// Setup session started
{"type": "setup_started", "run_id": "a1b2c3d4", "total_steps": 7, "protocol_version": 1}

// Step progress
{"type": "setup_step", "run_id": "a1b2c3d4", "step": "init_database", "index": 1, "total": 7, "status": "running"}
{"type": "setup_step", "run_id": "a1b2c3d4", "step": "init_database", "index": 1, "total": 7, "status": "done", "duration_ms": 3200, "message": "Database initialized"}
{"type": "setup_step", "run_id": "a1b2c3d4", "step": "init_database", "index": 1, "total": 7, "status": "skipped", "message": "Already initialized"}
{"type": "setup_step", "run_id": "a1b2c3d4", "step": "start_database", "index": 3, "total": 7, "status": "failed", "error_code": "PORT_CONFLICT", "error_detail": "Port 5432 in use", "stderr": "..."}

// Setup complete (terminal — always sent, success or failure)
{"type": "setup_complete", "run_id": "a1b2c3d4", "success": true, "lan_ip": "192.168.1.100"}
{"type": "setup_complete", "run_id": "a1b2c3d4", "success": false, "failed_step": "start_database", "error_code": "PORT_CONFLICT", "error_detail": "..."}

// Server lifecycle (separate from setup)
{"type": "pg_starting"}
{"type": "pg_ready"}
{"type": "server_ready", "port": 8888}
```

### Parsing rules for Electron

```javascript
// main.js — stdout line parsing
backendProcess.stdout.on('data', (chunk) => {
  for (const line of chunk.toString().split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith('{')) {
      try {
        const msg = JSON.parse(trimmed);
        handleSetupMessage(msg);  // update splash UI
      } catch {
        logToFile(trimmed);       // malformed JSON, log it
      }
    } else {
      logToFile(trimmed);         // regular backend log output
    }
  }
});
```

## 7. Electron Integration

### Splash screen changes

The existing `splash.js` gets a setup mode. Same window, different content based on context.

**Normal launch mode (existing):**
```
LocaNext
Starting server...
[progress bar]
```

**Setup mode (new):**
```
LocaNext — Server Setup

  [checkmark]  Checking system requirements      1s
  [checkmark]  Initializing database             4s
  [checkmark]  Configuring network access        1s
  [spinner]    Starting PostgreSQL...
  [circle]     Creating service account
  [circle]     Creating database
  [circle]     Generating certificates

  [progress bar] Step 4 of 7
```

**Error mode (new):**
```
LocaNext — Server Setup

  [checkmark]  Checking system requirements      1s
  [checkmark]  Initializing database             4s
  [X]          Starting PostgreSQL — FAILED

  Port 5432 is already in use.
  Another PostgreSQL installation may be running.

  [Show Full Log]   [Retry]   [Start Offline]
```

### Splash API additions

```javascript
// splash.js — new exports
function showSetupMode(totalSteps) { ... }
function updateSetupStep(index, name, status, duration, error) { ... }
function showSetupError(step, errorCode, errorDetail, canRetry) { ... }
function showSetupComplete(lanIp) { ... }
```

### pg_ctl stop on app exit

```javascript
// main.js — stopBackendServer() addition
function stopBackendServer() {
  // Stop PostgreSQL FIRST (it's a separate process)
  const pgCtl = path.join(paths.projectRoot, 'resources', 'bin', 'postgresql', 'bin', 'pg_ctl.exe');
  const pgData = path.join(paths.projectRoot, 'resources', 'bin', 'postgresql', 'data');
  if (fs.existsSync(pgCtl) && fs.existsSync(pgData)) {
    try {
      child_process.execFileSync(pgCtl, ['stop', '-D', pgData, '-m', 'fast'], { timeout: 10000 });
      logger.info('PostgreSQL stopped');
    } catch (e) {
      logger.warn('PostgreSQL stop failed', { error: e.message });
    }
  }

  // Then stop Python backend (existing code)
  if (backendProcess) { ... }
}
```

### Single instance guard

Verify `app.requestSingleInstanceLock()` is used. Prevents two instances fighting over PG data.

## 8. Failure Handling

### Three tiers

| Tier | Steps | On failure |
|------|-------|-----------|
| **Fatal** | preflight, init_database, configure_access, start_database | Show error + retry/offline buttons. Cannot continue without these. |
| **Recoverable** | create_account, create_database | Auto-retry once. If still fails, treat as fatal. |
| **Optional** | generate_certificates | Skip with warning. Log the issue. App works without TLS on localhost. |

### SQLite fallback mode

If setup fails and user clicks "Start Offline":
- FastAPI starts in SQLite mode (existing behavior)
- App shows a persistent banner: **"Running in offline mode. Server setup incomplete. [Retry Setup]"**
- **Data entry is allowed** in SQLite mode (existing feature)
- If admin later completes setup, they must use Admin Dashboard's "Import from SQLite" to migrate any data created in offline mode

### Retry semantics

- Retry re-validates ALL prerequisites, not just the failed step
- If PG crashed during step 5, retry checks "is PG running?" before attempting step 5 again
- If PG is not running, it starts PG first (re-running step 3)
- The runner always reads `setup_state.json` and resumes from the first non-done step

## 9. Security

### Admin authentication

**Replace pure IP-based auth with local admin token:**

1. During first setup, generate a 32-byte token: `secrets.token_urlsafe(32)`
2. Store in `server-config.json` alongside PG credentials
3. Electron main process reads the token from config file
4. Electron injects token into renderer via `preload.js` (not accessible to external processes)
5. All admin API calls include `Authorization: Bearer <admin_token>` header
6. Backend validates: request from 127.0.0.1 AND valid admin token = admin access

**Why both IP AND token:** IP alone is vulnerable (any local process). Token alone requires login flow. Together: only the Electron app running on the server machine gets admin access.

### Credential storage (Windows)

```python
# server/setup/credential_store.py

def save_credentials(config: dict) -> None:
    """Save server config with encrypted sensitive fields."""
    # Sensitive fields: postgres_password, secret_key, admin_token
    if sys.platform == 'win32':
        try:
            import win32crypt
            for key in ('postgres_password', 'secret_key', 'admin_token'):
                if key in config:
                    encrypted = win32crypt.CryptProtectData(
                        config[key].encode(), None, None, None, None, 0
                    )
                    config[key] = base64.b64encode(encrypted).decode()
                    config[f'{key}_encrypted'] = True
        except ImportError:
            # Fallback: NTFS ACLs via icacls
            pass

    path = get_config_path()
    path.write_text(json.dumps(config, indent=2))

    # Set NTFS permissions (Windows)
    if sys.platform == 'win32':
        subprocess.run(
            ['icacls', str(path), '/inheritance:r', '/grant:r',
             f'{os.getlogin()}:F'],
            capture_output=True
        )
```

### PG password handling

- Generated via `secrets.token_urlsafe(24)`
- Passed to `psql` via `PGPASSWORD` environment variable (NOT command-line argument)
- Never logged, never printed, never in JSONL messages
- Stored encrypted in `server-config.json` (DPAPI on Windows)

### pg_hba.conf rules (restrictive)

```
# TYPE  DATABASE        USER               ADDRESS              METHOD

# Local (admin PC)
host    localizationtools  locanext_service  127.0.0.1/32        scram-sha-256

# LAN (team PCs — TLS required)
hostssl localizationtools  locanext_service  192.168.1.0/24      scram-sha-256

# Reject everything else
host    all                all               0.0.0.0/0           reject
```

### SSL certificates

Generated via Python `cryptography` library (not openssl CLI, which may not exist on Windows):

```python
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate key pair
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Generate self-signed cert
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, "LocaNext-PG-Server"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "LocaNext"),
])
cert = (x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.utcnow())
    .not_valid_after(datetime.utcnow() + timedelta(days=3650))
    .sign(key, hashes.SHA256()))
```

### Windows Firewall

During preflight, attempt to add a firewall rule:

```python
# Uses list-form subprocess (no shell injection risk)
subprocess.run([
    'netsh', 'advfirewall', 'firewall', 'add', 'rule',
    'name=LocaNext PostgreSQL',
    'dir=in', 'action=allow',
    f'program={pg_bin_dir / "postgres.exe"}',
    'protocol=tcp', f'localport={pg_port}',
], capture_output=True)
```

If this fails (not running as admin), log a warning. The Windows Firewall popup will appear when PG starts — the splash screen should NOT be `alwaysOnTop` during the `start_database` step so the popup is visible.

## 10. LAN IP Detection (NO INTERNET REQUIRED)

**CRITICAL: Setup must NEVER call the internet.** This runs on a corporate LAN that may have no internet access. The old code connected to `8.8.8.8:80` to detect LAN IP — this is removed.

```python
def detect_lan_ip() -> str:
    """Detect LAN IP without ANY internet access."""
    import socket

    # Method 1: Enumerate interfaces (no network needed)
    try:
        hostname = socket.gethostname()
        ips = socket.getaddrinfo(hostname, None, socket.AF_INET)
        for _, _, _, _, (ip, _) in ips:
            if not ip.startswith('127.'):
                return ip
    except Exception:
        pass

    # Method 2: UDP socket to broadcast (local network only, no packet sent)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(('255.255.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith('127.'):
            return ip
    except Exception:
        pass

    # Method 3: Fallback — admin sets it manually in Admin Dashboard
    return "127.0.0.1"
```

**No DNS resolution, no external connections, no internet dependency.** All detection is local.

The detected IP is shown in the setup complete message and saved in state. Admin can change it later in the Admin Dashboard.

## 11. REST Retry Endpoint

For when setup failed and admin wants to retry from the running app:

```
POST /api/server/setup/retry
Authorization: Bearer <admin_token>

Response (SSE stream):
event: step
data: {"step": "start_database", "index": 3, "total": 7, "status": "running"}

event: step
data: {"step": "start_database", "index": 3, "total": 7, "status": "done", "duration_ms": 8100}

event: complete
data: {"success": true, "lan_ip": "192.168.1.100", "message": "Restart app to switch to PostgreSQL mode"}
```

**Concurrency guard:** A mutex prevents concurrent setup calls. Returns `409 Conflict` if setup is already running.

**After successful retry:** Admin must restart the app. The backend started in SQLite mode and cannot hot-swap to PG mid-session. On restart, Python reads `setup_state.json`, sees all steps done, starts PG, and launches in online mode.

## 12. Testing Strategy

### Unit tests (per step)

```python
def test_step_init_database_creates_data_dir(tmp_path, pg_bin):
    config = SetupConfig(pg_bin_dir=pg_bin, data_dir=tmp_path / "data")
    result = step_init_database(config)
    assert result.status == "done"
    assert (tmp_path / "data" / "PG_VERSION").exists()

def test_step_init_database_skips_if_exists(tmp_path, pg_bin):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "PG_VERSION").write_text("15")
    result = step_init_database(SetupConfig(pg_bin_dir=pg_bin, data_dir=tmp_path / "data"))
    assert result.status == "skipped"

def test_step_preflight_detects_port_conflict():
    # Bind port 5432, then run preflight
    ...
```

### Integration test (runner)

```python
def test_full_setup_run(tmp_path, pg_bin):
    config = SetupConfig(pg_bin_dir=pg_bin, data_dir=tmp_path / "data")
    progress = []
    result = run_setup(config, on_progress=progress.append)
    assert result.success
    assert len(progress) == 7  # All steps reported
    assert all(s.status in ("done", "skipped") for s in progress)
```

### Resume test

```python
def test_resume_after_partial_failure(tmp_path, pg_bin):
    # Create state file with steps 0-2 done, step 3 failed
    state = {"steps": {"preflight_checks": {"status": "done"}, ...}}
    write_state(tmp_path / "setup_state.json", state)

    # Resume should start from step 3
    result = run_setup(config, on_progress=progress.append)
    assert progress[0].step == "start_database"  # Resumed here
```

### JSONL protocol test

```python
def test_jsonl_output(tmp_path, pg_bin, capsys):
    run_setup(config, on_progress=emit_jsonl)
    lines = capsys.readouterr().out.strip().split('\n')
    msgs = [json.loads(l) for l in lines]
    assert msgs[0]["type"] == "setup_started"
    assert msgs[-1]["type"] == "setup_complete"
```

## 13. Files to Create/Modify

### New files

| File | Purpose |
|------|---------|
| `server/setup/__init__.py` | Module exports |
| `server/setup/steps.py` | 7 step functions (preflight + 6 setup) |
| `server/setup/runner.py` | Sequential orchestrator with progress callback |
| `server/setup/state.py` | setup_state.json read/write/resume |
| `server/setup/pg_lifecycle.py` | pg_ctl start/stop/status (shared by setup AND normal launch) |
| `server/setup/credential_store.py` | DPAPI encryption + NTFS ACL helpers |

### Modified files

| File | Change |
|------|--------|
| `server/main.py` | **Delete** lines 830-950 (old setup blob). Replace with: read state, if not complete call `run_setup()` with JSONL emitter, then start FastAPI. On exit: call `pg_lifecycle.stop()`. |
| `server/api/server_config.py` | **Delete** setup endpoint body (lines 278-566). Replace with call to `run_setup()` from shared module. Add SSE streaming for progress. |
| `locaNext/electron/main.js` | Parse JSONL from Python stdout. Route setup messages to splash. Add `pg_ctl stop` to `stopBackendServer()`. Increase timeout to 120s. |
| `locaNext/electron/splash.js` | Add setup mode UI: step list, progress, error panel with retry/offline buttons. |
| `server/config.py` | Read admin_token from config. Add token validation helper. |
| `server/utils/auth.py` | Admin check: IP 127.0.0.1 AND valid admin_token (not just IP). |
| `.github/workflows/build-electron.yml` | Add `cryptography` to pip install list (for SSL cert generation). |

### Deleted code

| Location | What | Why |
|----------|------|-----|
| `server/main.py:830-950` | Auto-setup blob | Replaced by `server/setup/` module |
| `server/api/server_config.py:278-566` | Duplicate setup endpoint | Replaced by call to shared module |

## 14. Build Pipeline Changes

### `cryptography` package

Add to the pip install step in `build-electron.yml`:

```yaml
pip install cryptography
```

This replaces the dependency on `openssl` CLI. The `cryptography` package includes compiled C extensions but is well-supported on Windows.

### No other build changes needed

PostgreSQL bundling, Light Mode flag, and Python embedded setup remain unchanged.

## 15. Migration from Current Code

The transition is clean because the current auto-setup has only been in one build (which broke). No users have successfully completed the old setup flow, so there's no state to migrate.

1. Delete old auto-setup blob from `main.py`
2. Delete old setup endpoint body from `server_config.py`
3. Create `server/setup/` module
4. Wire up `main.py` to call `run_setup()` + JSONL
5. Wire up `server_config.py` to call `run_setup()` + SSE
6. Update Electron splash + stdout parsing + pg_ctl stop
7. Test full flow on Windows

---

*Spec written: 2026-04-01. Tribunal-audited. Addresses all CRITICAL and HIGH findings from 3-expert audit (Electron, Security, API Design).*
