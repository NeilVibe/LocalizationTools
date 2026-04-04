# PG Startup Architecture Redesign — MEGA Spec

**Date:** 2026-04-02
**Status:** Draft
**Scope:** 7 subsystems, ~15 files, ~1500-2000 lines
**Priority:** CRITICAL — demo-blocking bug (backend timeout on PEARL)

---

## Problem Statement

The "Full Admin with PG" build bundles PostgreSQL. On first launch, the Python backend runs a 7-step setup wizard **synchronously in `__main__`** before calling `uvicorn.run()`. This blocks the main thread for up to 110 seconds. Electron's healthcheck times out at 90 seconds (90 retries x 1s). The backend never crashes — it's alive and working — but Electron gives up and shows "Backend server failed to start."

**Root cause:** Dumb fixed timeout + silent backend (setup uses stdlib `logging`, invisible to Electron).

**Secondary issues:**
- PG is not tuned for high concurrency (default settings, pool_size=5)
- DB monitoring dashboard exists but is incomplete (read-only stats, no live connections)
- Setup logging is invisible (stdlib logging, not loguru)
- CI installs 6 packages without verifying them

---

## Target Environment

- **PEARL PC:** Intel i7-12700 (12C/20T), 64GB RAM, SSD, Windows, offline
- **Use case:** LAN server hosting 10+ simultaneous users
- **PG target:** 200+ concurrent connections (10 users = ultra fast)
- **Build type:** Full Admin with PG (GitHub Actions)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ ELECTRON (main.js)                                              │
│                                                                 │
│  1. Spawn Python backend                                        │
│  2. Show Splash Window (pure HTML, no backend dependency)       │
│  3. Parse JSONL from backend stdout                             │
│  4. Update splash UI with step progress                         │
│  5. Progress-aware timeout (60s silence = error, NO fixed cap)  │
│  6. On "server_ready" → close splash, open main window          │
│                                                                 │
│  ┌─ splash.html ──────────────────────────────────────────────┐ │
│  │  Progress bar + percentage                                 │ │
│  │  Step list (✅ done / 🔄 running / ⏳ pending)             │ │
│  │  Detail log panel (scrollable)                             │ │
│  │  Error state: failed step + pg.log + [Retry] [Exit]       │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         │ stdout (JSONL)
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ PYTHON BACKEND (server/main.py __main__)                        │
│                                                                 │
│  1. Emit boot_started                                           │
│  2. find_pg_binaries() + read pg_setup_mode.flag                │
│  3. read_state() → is_setup_complete()?                         │
│     ├─ NO  → run_setup() (7+1 steps, emitting JSONL per step)  │
│     └─ YES → start_pg() (emit progress, 3-5s)                  │
│  4. Emit setup_complete                                         │
│  5. uvicorn.run() → lifespan startup                            │
│  6. Emit server_ready                                           │
│                                                                 │
│  Setup Steps (sequential, blocking — this is FINE now):         │
│  ┌─ Step 1: preflight_checks (port, disk, binaries)            │
│  ├─ Step 2: init_database (initdb, create cluster)             │
│  ├─ Step 3: configure_access (pg_hba.conf, postgresql.conf)    │
│  ├─ Step 4: generate_certificates (TLS self-signed)            │
│  ├─ Step 5: start_database (pg_ctl start)                      │
│  ├─ Step 6: tune_performance (NEW — hardware detect + config)  │
│  ├─ Step 7: create_account (CREATE USER)                       │
│  └─ Step 8: create_database (CREATE DATABASE + GRANT)          │
│                                                                 │
│  All steps emit JSONL progress via stdout                       │
│  All steps use loguru (visible in Electron log capture)         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Section 1: JSONL Progress Protocol

### Message Types

All messages are single-line JSON objects on stdout, prefixed with `JSONL:` to distinguish from regular output.

```
JSONL:{"type":"boot_started","version":"26.x","timestamp":"2026-04-02T10:06:10Z"}
```

#### boot_started
Emitted immediately when `__main__` begins.
```json
{
  "type": "boot_started",
  "version": "26.402.xxxx",
  "build_type": "full_admin_pg",
  "timestamp": "ISO8601"
}
```

#### setup_started
Emitted when setup wizard begins (first launch only).
```json
{
  "type": "setup_started",
  "run_id": "abc123",
  "total_steps": 8,
  "resumed_from": null,
  "timestamp": "ISO8601"
}
```

#### setup_step
Emitted at start and end of each step.
```json
{
  "type": "setup_step",
  "step": "init_database",
  "index": 2,
  "total": 8,
  "status": "running|done|skipped|failed",
  "message": "Creating PostgreSQL cluster...",
  "progress_pct": 25,
  "duration_ms": null,
  "timestamp": "ISO8601"
}
```

Progress percentages per step (first launch, 8 steps):
| Step | Start % | Done % |
|------|---------|--------|
| preflight_checks | 5 | 10 |
| init_database | 10 | 25 |
| configure_access | 25 | 30 |
| generate_certificates | 30 | 38 |
| start_database | 38 | 55 |
| tune_performance | 55 | 68 |
| create_account | 68 | 78 |
| create_database | 78 | 88 |
| (uvicorn startup) | 88 | 100 |

#### setup_substep
Emitted for detailed progress within a step.
```json
{
  "type": "setup_substep",
  "step": "tune_performance",
  "detail": "Detected 64GB RAM, SSD, 12 cores",
  "timestamp": "ISO8601"
}
```

#### setup_complete
Emitted when wizard finishes (success or failure).
```json
{
  "type": "setup_complete",
  "success": true,
  "total_ms": 45000,
  "lan_ip": "192.168.1.50",
  "failed_step": null,
  "error_code": null,
  "error_detail": null,
  "timestamp": "ISO8601"
}
```

#### pg_starting / pg_ready
Emitted on subsequent launches (PG already set up).
```json
{"type": "pg_starting", "timestamp": "ISO8601"}
{"type": "pg_ready", "duration_ms": 3100, "timestamp": "ISO8601"}
```

#### server_ready
Emitted from lifespan startup after uvicorn is listening.
```json
{
  "type": "server_ready",
  "port": 8888,
  "database": "postgresql",
  "host": "0.0.0.0",
  "timestamp": "ISO8601"
}
```

#### setup_error
Emitted on fatal failure with full diagnostic info.
```json
{
  "type": "setup_error",
  "step": "start_database",
  "error_code": "START_TIMEOUT",
  "error_detail": "pg_ctl start timed out after 30s",
  "pg_log_tail": "last 20 lines of pg.log",
  "suggestion": "Check if another PostgreSQL instance is running on port 5432",
  "timestamp": "ISO8601"
}
```

### Electron Parsing Rules

1. Read backend stdout line by line
2. Lines starting with `JSONL:` → parse JSON, update splash UI
3. All other lines → append to log buffer (displayed in splash detail panel)
4. **Timeout:** If no `JSONL:` message for 60 seconds → show error state
5. **Success:** On `server_ready` message → close splash, open main window
6. **Failure:** On `setup_error` or `setup_complete` with `success:false` → show error state with retry/exit buttons

---

## Section 2: Splash Screen UI

### File: `locaNext/electron/splash.html`

Single HTML file with embedded CSS/JS. No framework, no build step. Loaded by Electron BrowserWindow.

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    LocaNext                                  │
│              Starting up... v26.402.xxxx                     │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ██████████████████████░░░░░░░░░░░  60%                │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                             │
│  ✅ Step 1/8  Preflight checks              0.3s           │
│  ✅ Step 2/8  Initialize database           4.2s           │
│  ✅ Step 3/8  Configure access              0.1s           │
│  ✅ Step 4/8  Generate certificates         0.5s           │
│  🔄 Step 5/8  Starting PostgreSQL...                       │
│  ⏳ Step 6/8  Tune performance                             │
│  ⏳ Step 7/8  Create service account                       │
│  ⏳ Step 8/8  Create database                              │
│                                                             │
│  ┌─ Detail Log ──────────────────────────────────────────┐  │
│  │ 10:06:15  Running initdb with UTF8 encoding...        │  │
│  │ 10:06:19  Cluster created successfully                │  │
│  │ 10:06:19  Writing pg_hba.conf (LAN: 192.168.1.0/24)  │  │
│  │ 10:06:20  Generating RSA 2048 TLS certificate...      │  │
│  │ 10:06:20  Starting pg_ctl on port 5432...             │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  Elapsed: 12.3s                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Subsequent Launch (Fast Path)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    LocaNext                                  │
│              Starting up... v26.402.xxxx                     │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ██████████████████████████████████████████████  100%   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                             │
│  ✅ PostgreSQL started                          3.1s       │
│  ✅ Server ready on port 8888                   1.2s       │
│                                                             │
│  Elapsed: 4.3s                                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Minimum display time: 1.5 seconds (polish feel). Fades out to main window.

### Error State

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    LocaNext                                  │
│              ⚠ Setup failed at Step 5                       │
│                                                             │
│  ✅ Step 1/8  Preflight checks              0.3s           │
│  ✅ Step 2/8  Initialize database           4.2s           │
│  ✅ Step 3/8  Configure access              0.1s           │
│  ✅ Step 4/8  Generate certificates         0.5s           │
│  ❌ Step 5/8  Start database — FAILED                      │
│                                                             │
│  Error: pg_ctl start timed out after 30s                    │
│  Suggestion: Check if another PostgreSQL instance           │
│              is running on port 5432                        │
│                                                             │
│  ┌─ Full Log (scrollable) ───────────────────────────────┐  │
│  │ [detailed log output including pg.log tail]           │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│           [ Copy Log ]    [ Retry ]    [ Exit ]             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Visual Design

- Window: 600x520px, no frame, centered, always on top
- Background: dark (#1a1a2e) with subtle gradient
- Progress bar: blue-to-green gradient (#4361ee → #2ecc71)
- Step icons: ✅ green, 🔄 blue pulse animation, ⏳ gray, ❌ red
- Detail log: monospace font, dark panel, auto-scroll to bottom
- Typography: system font, 14px body, 24px title
- Minimum 1.5s display before fade-out transition

### Electron Integration

```javascript
// In main.js — createSplashWindow()
const splash = new BrowserWindow({
  width: 600, height: 520,
  frame: false, transparent: false,
  backgroundColor: '#1a1a2e',
  resizable: false, center: true,
  alwaysOnTop: true,
  webPreferences: { nodeIntegration: false, contextIsolation: true, preload: splashPreload }
});
splash.loadFile(path.join(__dirname, 'splash.html'));
```

Communication: main process sends IPC messages to splash window based on parsed JSONL from backend stdout.

---

## Section 3: Electron main.js Rewrite (Backend Startup)

### Replace: Blind Healthcheck Loop

**Remove:** The current `waitForBackend()` function (90 retries x 1s polling http://127.0.0.1:8888).

**Replace with:** JSONL-aware startup coordinator.

```javascript
async function startBackendWithProgress(splashWindow) {
  const SILENCE_TIMEOUT_MS = 60000;  // 60s of no JSONL = stuck
  let lastJsonlTime = Date.now();
  let serverReady = false;
  let setupFailed = false;
  let failureInfo = null;

  // Spawn Python backend (same as current)
  backendProcess = spawn(pythonExe, [serverScript], { ... });

  // Parse stdout for JSONL messages
  backendProcess.stdout.on('data', (data) => {
    const lines = data.toString().split('\n');
    for (const line of lines) {
      if (line.startsWith('JSONL:')) {
        lastJsonlTime = Date.now();
        const msg = JSON.parse(line.slice(6));
        handleJsonlMessage(msg, splashWindow);

        if (msg.type === 'server_ready') serverReady = true;
        if (msg.type === 'setup_error') { setupFailed = true; failureInfo = msg; }
        if (msg.type === 'setup_complete' && !msg.success) { setupFailed = true; failureInfo = msg; }
      } else if (line.trim()) {
        // Regular log line — send to splash detail panel
        splashWindow.webContents.send('log-line', line.trim());
      }
    }
  });

  // Also capture stderr (loguru output)
  backendProcess.stderr.on('data', (data) => {
    const lines = data.toString().split('\n');
    for (const line of lines) {
      if (line.trim()) {
        lastJsonlTime = Date.now();  // Any output = backend alive
        splashWindow.webContents.send('log-line', line.trim());
      }
    }
  });

  // Wait for server_ready OR failure OR silence timeout
  return new Promise((resolve, reject) => {
    const checkInterval = setInterval(() => {
      if (serverReady) {
        clearInterval(checkInterval);
        resolve();
      } else if (setupFailed) {
        clearInterval(checkInterval);
        reject(new Error(JSON.stringify(failureInfo)));
      } else if (Date.now() - lastJsonlTime > SILENCE_TIMEOUT_MS) {
        clearInterval(checkInterval);
        reject(new Error('Backend silent for 60s — may be stuck'));
      }
    }, 500);
  });
}
```

### IPC Message Handler

```javascript
function handleJsonlMessage(msg, splashWindow) {
  switch (msg.type) {
    case 'boot_started':
      splashWindow.webContents.send('boot-started', msg);
      break;
    case 'setup_started':
      splashWindow.webContents.send('setup-started', msg);
      break;
    case 'setup_step':
      splashWindow.webContents.send('setup-step', msg);
      break;
    case 'setup_substep':
      splashWindow.webContents.send('setup-substep', msg);
      break;
    case 'setup_complete':
      splashWindow.webContents.send('setup-complete', msg);
      break;
    case 'pg_starting':
    case 'pg_ready':
      splashWindow.webContents.send('pg-status', msg);
      break;
    case 'server_ready':
      splashWindow.webContents.send('server-ready', msg);
      break;
    case 'setup_error':
      splashWindow.webContents.send('setup-error', msg);
      break;
  }
}
```

### Startup Flow (main.js)

```javascript
app.whenReady().then(async () => {
  const splash = createSplashWindow();

  try {
    await startBackendWithProgress(splash);

    // Minimum display time for polish
    await new Promise(r => setTimeout(r, 1500));

    // Fade out splash, open main window
    splash.webContents.send('fade-out');
    await new Promise(r => setTimeout(r, 300));
    splash.close();

    createMainWindow();
  } catch (error) {
    // Show error state in splash (don't close it)
    splash.webContents.send('setup-error', {
      error_detail: error.message,
      suggestion: 'Try restarting the application or check the logs.'
    });

    // Retry button handler
    ipcMain.once('retry-setup', async () => {
      splash.close();
      // Kill backend, restart everything
      if (backendProcess) backendProcess.kill();
      app.relaunch();
      app.exit(0);
    });
  }
});
```

---

## Section 4: Backend Startup Redesign (server/main.py)

### __main__ Block Rewrite

```python
if __name__ == "__main__":
    import uvicorn
    import os as _os
    import json as _json
    import sys
    from pathlib import Path
    from datetime import datetime, timezone

    def _emit_jsonl(msg: dict):
        """Emit a JSONL message to stdout for Electron to parse."""
        msg.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        sys.stdout.write(f"JSONL:{_json.dumps(msg)}\n")
        sys.stdout.flush()

    # ---- Phase 1: Boot Started ----
    _emit_jsonl({
        "type": "boot_started",
        "version": getattr(config, "VERSION", "unknown"),
        "build_type": "full_admin_pg" if Path(
            _os.environ.get("LOCANEXT_RESOURCES_PATH", "")
        ).joinpath("pg_setup_mode.flag").exists() else "light",
    })

    # ---- Phase 2: PG Setup (if needed) ----
    try:
        from server.setup.pg_lifecycle import find_pg_binaries, start_pg, is_pg_running
        from server.setup.state import read_state, is_setup_complete
        from server.setup.jsonl import (
            emit_setup_started, emit_setup_step, emit_setup_complete,
            emit_pg_starting, emit_pg_ready, emit_setup_substep,
        )

        resources_path = _os.environ.get("LOCANEXT_RESOURCES_PATH", "")

        # Check pg_setup_mode.flag
        flag_path = Path(resources_path) / "pg_setup_mode.flag"
        setup_mode = "absent"
        if flag_path.exists():
            setup_mode = flag_path.read_text().strip().lower()

        pg = find_pg_binaries(resources_path) if setup_mode != "absent" else None

        if _os.name == "nt":
            state_dir = Path(_os.environ.get("APPDATA", "")) / "LocaNext"
        else:
            state_dir = Path.home() / ".config" / "locanext"
        state_path = state_dir / "setup_state.json"

        if pg and setup_mode == "auto":
            state = read_state(state_path)

            if not is_setup_complete(state):
                # --- First launch: full setup wizard ---
                import secrets
                from server.setup import SetupConfig
                from server.setup.runner import run_setup
                from server.setup.network import detect_lan_ip
                from server.setup.credential_store import save_config

                setup_config = SetupConfig(
                    pg_bin_dir=str(pg.bin_dir),
                    data_dir=str(pg.data_dir),
                )

                run_id = state.run_id or secrets.token_urlsafe(8)
                _emit_jsonl({"type": "setup_started", "run_id": run_id, "total_steps": 8})

                def _on_progress(result):
                    # Emit JSONL for each step completion
                    _emit_jsonl({
                        "type": "setup_step",
                        "step": result.step,
                        "index": STEP_NAMES.index(result.step) + 1 if result.step in STEP_NAMES else 0,
                        "total": 8,
                        "status": result.status,
                        "message": result.message,
                        "duration_ms": result.duration_ms,
                    })

                setup_result = run_setup(
                    setup_config, state_path=state_path, on_progress=_on_progress
                )

                _emit_jsonl({
                    "type": "setup_complete",
                    "success": setup_result.success,
                    "total_ms": sum(s.duration_ms for s in setup_result.steps),
                    "lan_ip": setup_result.lan_ip,
                    "failed_step": setup_result.failed_step,
                    "error_code": setup_result.error_code,
                    "error_detail": setup_result.error_detail,
                })

                if setup_result.success:
                    # Configure for PG mode
                    lan_ip = detect_lan_ip()
                    db_password = secrets.token_urlsafe(24)
                    # ... (existing credential save code) ...
                    logger.success(f"=== SETUP COMPLETE: LAN server ready at {lan_ip} ===")
                else:
                    # Setup failed — emit error with diagnostics
                    pg_log = ""
                    try:
                        pg_log_path = pg.log_file
                        if pg_log_path.exists():
                            pg_log = pg_log_path.read_text()[-2000:]  # last 2KB
                    except Exception:
                        pass
                    _emit_jsonl({
                        "type": "setup_error",
                        "step": setup_result.failed_step,
                        "error_code": setup_result.error_code,
                        "error_detail": setup_result.error_detail,
                        "pg_log_tail": pg_log,
                        "suggestion": _get_suggestion(setup_result.error_code),
                    })
                    # Don't start server — let Electron handle the error
                    sys.exit(1)
            else:
                # --- Subsequent launch: just start PG ---
                # Fast check: is PG already running?
                if is_pg_running(pg.pg_isready, config.POSTGRES_PORT):
                    _emit_jsonl({"type": "pg_ready", "duration_ms": 0, "message": "Already running"})
                else:
                    _emit_jsonl({"type": "pg_starting"})
                    ok, msg = start_pg(pg.pg_ctl, pg.data_dir, pg.log_file)
                    if ok:
                        _emit_jsonl({"type": "pg_ready", "duration_ms": 0, "message": msg})
                    else:
                        _emit_jsonl({
                            "type": "setup_error",
                            "step": "start_database",
                            "error_code": "START_FAILED",
                            "error_detail": msg,
                        })
                        sys.exit(1)
        else:
            _emit_jsonl({"type": "setup_substep", "step": "boot", "detail": "No PG bundled or dormant — SQLite mode"})

    except Exception as e:
        logger.warning(f"Setup phase skipped or failed: {e}")
        _emit_jsonl({"type": "setup_substep", "step": "boot", "detail": f"Setup skipped: {e}"})

    # ---- Phase 3: Start Server ----
    logger.info(f"Starting server on {config.SERVER_HOST}:{config.SERVER_PORT}")
    _emit_jsonl({"type": "setup_substep", "step": "uvicorn", "detail": "Starting web server..."})

    uvicorn.run(
        app,
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        reload=False,
        log_level=config.LOG_LEVEL.lower(),
    )
```

### Lifespan Startup — Emit server_ready

Add to the end of the `lifespan()` function's startup section:

```python
# At the end of lifespan startup (after all init is done):
import sys, json
sys.stdout.write(f'JSONL:{json.dumps({"type":"server_ready","port":config.SERVER_PORT,"database":"postgresql" if not is_sqlite() else "sqlite"})}\n')
sys.stdout.flush()
```

---

## Section 5: New Setup Step — tune_performance

### File: `server/setup/steps.py` — New function

```python
def step_tune_performance(config: SetupConfig) -> StepResult:
    """Detect hardware and write optimized postgresql.conf settings."""
```

### Hardware Detection (new file: `server/setup/hardware_detect.py`)

Uses `psutil` (already bundled) to detect:
- **RAM:** `psutil.virtual_memory().total` → bytes → GB
- **CPU cores:** `psutil.cpu_count(logical=False)` (physical cores)
- **SSD detection:** `psutil.disk_usage(data_dir)` + Windows WMI query or heuristic (assume SSD if < 1ms seek on small read)

### PG Tuning Calculation (for 200+ connections)

Based on detected hardware, writes optimized settings to postgresql.conf:

```
# Performance tuning (auto-generated by LocaNext)
max_connections = 250
shared_buffers = {ram_gb // 4}GB          # 25% of RAM (16GB for 64GB)
effective_cache_size = {ram_gb * 3 // 4}GB # 75% of RAM (48GB for 64GB)
work_mem = {max(16, ram_gb * 1024 // (max_connections * 2))}MB  # Safe for concurrency
maintenance_work_mem = {min(4, ram_gb // 16)}GB
wal_buffers = 64MB
max_wal_size = 4GB
min_wal_size = 1GB
checkpoint_completion_target = 0.9
random_page_cost = 1.1                    # SSD
effective_io_concurrency = 200            # SSD
max_parallel_workers_per_gather = {min(4, physical_cores // 3)}
max_parallel_workers = {min(8, physical_cores)}
max_parallel_maintenance_workers = {min(4, physical_cores // 3)}
default_statistics_target = 200
```

For PEARL (64GB, 12 cores):
- `shared_buffers = 16GB`
- `effective_cache_size = 48GB`
- `work_mem = 64MB` (64*1024 / 500 ≈ 131, clamped to 64 for safety)
- `max_parallel_workers = 8`

### Step Sequence Update

Insert `tune_performance` after `start_database` (PG must be running to reload config):

```python
STEP_NAMES = [
    "preflight_checks",     # Step 1
    "init_database",        # Step 2
    "configure_access",     # Step 3
    "generate_certificates",# Step 4
    "start_database",       # Step 5
    "tune_performance",     # Step 6 (NEW)
    "create_account",       # Step 7
    "create_database",      # Step 8
]
```

After writing config, the step calls `pg_ctl reload` to apply settings without restart:
```python
subprocess.run([str(pg_ctl), "reload", "-D", str(data_dir)], timeout=10)
```

### STEP_FUNCTIONS Update

```python
STEP_FUNCTIONS["tune_performance"] = step_tune_performance
```

Classification: `tune_performance` is a **FATAL** step (misconfigured PG is dangerous for data integrity).

---

## Section 6: SQLAlchemy Connection Pool Tuning

### File: `server/config.py`

Update LAN server mode pool defaults:

```python
# Current (inadequate):
if server_mode == "lan_server":
    DB_POOL_SIZE = 3
    DB_MAX_OVERFLOW = 5

# New (tuned for 200+ connections):
if server_mode == "lan_server":
    DB_POOL_SIZE = 25       # Base persistent connections
    DB_MAX_OVERFLOW = 35    # Spike headroom (total max: 60)
    DB_POOL_TIMEOUT = 20    # Fail fast if pool exhausted
    DB_POOL_RECYCLE = 1800  # Recycle every 30 min
```

### Connection Pool Logging

Add pool event listeners to log connection checkout/checkin/overflow:

```python
from sqlalchemy import event

@event.listens_for(engine, "checkout")
def log_checkout(dbapi_conn, connection_record, connection_proxy):
    logger.debug("[POOL] Connection checked out (pool_size={})", engine.pool.size())

@event.listens_for(engine, "overflow")
def log_overflow(dbapi_conn, connection_record):
    logger.warning("[POOL] Connection overflow — consider increasing pool_size")
```

---

## Section 7: Logging Overhaul

### Files to Migrate (stdlib logging → loguru)

All files in `server/setup/`:

| File | Current | Change |
|------|---------|--------|
| `runner.py` | `logging.getLogger(__name__)` | `from loguru import logger` |
| `steps.py` | `logging.getLogger(__name__)` | `from loguru import logger` |
| `pg_lifecycle.py` | `logging.getLogger(__name__)` | `from loguru import logger` |
| `state.py` | `logging.getLogger(__name__)` | `from loguru import logger` |
| `network.py` | No logging | Add loguru for LAN IP detection |

### Migration Pattern

```python
# BEFORE (invisible to Electron):
import logging
logger = logging.getLogger(__name__)
logger.info("Starting PG...")

# AFTER (visible in Electron stderr capture):
from loguru import logger
logger.info("Starting PG...")
```

No other code changes needed — loguru's API is identical to stdlib for `.info()`, `.warning()`, `.error()`, `.exception()`.

### JSONL Emission Points

Every subprocess call in `pg_lifecycle.py` emits a JSONL substep:

```python
def start_pg(pg_ctl, data_dir, log_file, timeout=30):
    _emit_jsonl({"type": "setup_substep", "step": "start_database",
                 "detail": f"Running pg_ctl start -D {data_dir} -w (timeout {timeout}s)"})
    result = subprocess.run(cmd, ...)
    _emit_jsonl({"type": "setup_substep", "step": "start_database",
                 "detail": f"pg_ctl returned code {result.returncode} in {duration}ms"})
```

---

## Section 8: Enhanced DB Monitoring Dashboard

### File: `adminDashboard/src/routes/database/+page.svelte`

### New Sections (above existing table tree)

#### 1. PG Status Banner
```
┌────────────────────────────────────────────────────┐
│ 🟢 PostgreSQL 16.x  |  Uptime: 2d 14h  |  Port: 5432  │
│ Mode: LAN Server  |  Max Connections: 250              │
└────────────────────────────────────────────────────┘
```

#### 2. Connection Monitor
```
Active Connections: 12 / 250
┌──────────────────────────────────────────┐
│ ██████░░░░░░░░░░░░░░░░░░░░░░░░░░  4.8%  │
└──────────────────────────────────────────┘
Active: 8  |  Idle: 4  |  Waiting: 0
```

#### 3. Cache Performance
```
Cache Hit Ratio: 99.7%  🟢
┌──────────────────────────────────────────┐
│ █████████████████████████████████████ 99.7%│
└──────────────────────────────────────────┘
Heap reads: 145,231  |  Heap hits: 48,392,105
```

#### 4. Health Recommendations
```
┌─ Health Check ─────────────────────────────────┐
│ ✅ Cache hit ratio optimal (>99%)              │
│ ✅ Connection usage low (4.8%)                 │
│ ⚠️ Table "file_metadata": 1,204 dead tuples   │
│    Recommendation: Run VACUUM ANALYZE          │
└────────────────────────────────────────────────┘
```

### Backend API

Already exists at `GET /api/v2/admin/db/stats` and `GET /api/v2/admin/db/health`. Just need to wire to UI.

Response includes: `max_connections`, `active_connections`, `idle_connections`, `cache_hit_ratio`, `database_size`, `table_stats`, `health_issues`, `recommendations`.

### Auto-Refresh

Poll every 5 seconds for live connection monitoring. Use `setInterval` with cleanup on page leave.

---

## Section 9: CI/CD Validation

### File: `.github/workflows/build-electron.yml`

### New Validations (after package install)

```powershell
# ---- Verify ALL installed packages ----
Write-Host "=== Verifying package installations ==="
& "tools\python\python.exe" -c "from cryptography import x509; print('[OK] cryptography')"
& "tools\python\python.exe" -c "from PIL import Image; print('[OK] Pillow')"
& "tools\python\python.exe" -c "import psutil; print('[OK] psutil')"
& "tools\python\python.exe" -c "import multipart; print('[OK] python-multipart')"
& "tools\python\python.exe" -c "from sse_starlette.sse import EventSourceResponse; print('[OK] sse-starlette')"
& "tools\python\python.exe" -c "import xlsxwriter; print('[OK] xlsxwriter')"
```

### PG Binary Validation (Full Admin builds only)

```powershell
# ---- Verify PG binaries ----
if (Test-Path "resources\bin\postgresql\bin") {
    $required = @("initdb.exe", "pg_ctl.exe", "psql.exe", "pg_isready.exe")
    foreach ($bin in $required) {
        $p = "resources\bin\postgresql\bin\$bin"
        if (-not (Test-Path $p)) {
            Write-Error "MISSING PG BINARY: $p"
            exit 1
        }
        Write-Host "[OK] PG binary: $bin"
    }
}
```

### pg_setup_mode.flag Creation

```powershell
# ---- Write PG setup mode flag ----
if (Test-Path "resources\bin\postgresql\bin") {
    "auto" | Out-File -FilePath "resources\pg_setup_mode.flag" -Encoding ascii -NoNewline
    Write-Host "[OK] pg_setup_mode.flag written (auto)"
}
```

### Setup Module Import Test

```powershell
# ---- Verify setup module imports cleanly ----
& "tools\python\python.exe" -c "
from server.setup import SetupConfig, SetupResult, StepResult
from server.setup.runner import run_setup
from server.setup.state import read_state, is_setup_complete, STEP_NAMES
from server.setup.pg_lifecycle import find_pg_binaries, start_pg, is_pg_running
from server.setup.steps import step_preflight_checks, step_tune_performance
from server.setup.hardware_detect import detect_hardware
from server.setup.network import detect_lan_ip
print('[OK] All setup modules import successfully')
print(f'[OK] Steps: {len(STEP_NAMES)} ({", ".join(STEP_NAMES)})')
"
```

---

## Section 10: Resilience & Recovery

### State Recovery

The existing `setup_state.json` tracks per-step completion. Resume logic already works in `runner.py`. Enhancements:

1. **Corrupted state detection:** If state file exists but JSON is invalid, wipe it and start fresh (already implemented in `read_state`).
2. **Stale state from old version:** If `pg_major_version` in state doesn't match bundled PG version, wipe state and re-run setup (new check).
3. **Partial data dir:** If `PG_VERSION` exists but `postgresql.conf` is missing, wipe `data_dir` and re-init (already implemented in `step_init_database`).

### Retry from Splash Screen

The "Retry" button in the error state:
1. Kills the backend process
2. Relaunches the entire Electron app (`app.relaunch(); app.exit(0);`)
3. The setup wizard resumes from the last successful step (state file preserved)

### Error → Suggestion Mapping

```python
SUGGESTIONS = {
    "PORT_CONFLICT": "Port 5432 is already in use. Close any other PostgreSQL instances.",
    "LOW_DISK": "Less than 500MB free disk space. Free up space and retry.",
    "MISSING_BINARIES": "PostgreSQL binaries not found. The installation may be corrupted. Re-download.",
    "INITDB_TIMEOUT": "Database initialization timed out. Check antivirus isn't blocking pg processes.",
    "INITDB_FAILED": "Database initialization failed. Check disk permissions.",
    "START_TIMEOUT": "PostgreSQL failed to start within 30s. Check resources/bin/postgresql/pg.log.",
    "START_FAILED": "PostgreSQL failed to start. Check if port 5432 is available.",
    "CERT_GENERATION_FAILED": "TLS certificate generation failed. Check disk space and permissions.",
    "CREATE_USER_FAILED": "Could not create database user. PostgreSQL may need manual intervention.",
    "CREATE_DB_FAILED": "Could not create database. Check PostgreSQL logs.",
    "TUNE_FAILED": "Performance tuning failed (non-critical). PG will work with defaults.",
}
```

### Startup Telemetry

Log to `startup_telemetry.json` in the LocaNext data dir:

```json
{
  "launches": [
    {
      "timestamp": "ISO8601",
      "version": "26.x",
      "total_startup_ms": 4300,
      "pg_start_ms": 3100,
      "steps": {"preflight_checks": 300, "start_database": 3100},
      "hardware": {"ram_gb": 64, "cores": 12, "ssd": true},
      "result": "success"
    }
  ]
}
```

---

## File Changes Summary

| File | Type | Lines | Description |
|------|------|-------|-------------|
| `locaNext/electron/main.js` | Modify | ~200 | JSONL parsing, splash window, progress-aware timeout |
| `locaNext/electron/splash.html` | **New** | ~350 | Rich progress splash screen (HTML/CSS/JS) |
| `locaNext/electron/splash-preload.js` | **New** | ~30 | IPC bridge for splash window |
| `server/main.py` | Modify | ~100 | __main__ JSONL emissions, server_ready in lifespan |
| `server/setup/runner.py` | Modify | ~30 | Loguru migration, richer progress callbacks |
| `server/setup/steps.py` | Modify | ~120 | Loguru, new tune_performance step, JSONL substeps |
| `server/setup/pg_lifecycle.py` | Modify | ~40 | Loguru, is_pg_running check before start, JSONL |
| `server/setup/state.py` | Modify | ~10 | Loguru migration, add tune_performance to STEP_NAMES |
| `server/setup/network.py` | Modify | ~5 | Loguru migration |
| `server/setup/hardware_detect.py` | **New** | ~80 | RAM/CPU/SSD detection using psutil |
| `server/setup/jsonl.py` | Modify | ~60 | New message types, _emit_jsonl helper |
| `server/config.py` | Modify | ~15 | LAN pool sizing (25/35), pool logging |
| `adminDashboard/.../database/+page.svelte` | Modify | ~200 | Connection monitor, cache stats, health panel |
| `.github/workflows/build-electron.yml` | Modify | ~40 | Package verification, PG binary check, flag file |

**Total: ~14 files, ~1280 lines of changes**

---

## Implementation Order

1. **JSONL protocol + splash screen** (Sections 1-3) — fixes the crash
2. **Backend startup rewrite** (Section 4) — emits JSONL messages
3. **Logging overhaul** (Section 7) — makes everything visible
4. **tune_performance step** (Section 5) — PG optimization
5. **Connection pool tuning** (Section 6) — SQLAlchemy pool
6. **DB monitoring dashboard** (Section 8) — enhanced UI
7. **CI/CD validation** (Section 9) — package + binary checks
8. **Resilience & recovery** (Section 10) — error handling polish

---

## Success Criteria

1. **PEARL first launch:** Splash screen shows all 8 steps with progress → PG fully configured → app opens → NEVER times out
2. **PEARL subsequent launch:** Splash shows "Starting PostgreSQL..." for 3-5s → app opens
3. **10 concurrent users:** PG handles with 4.8% connection usage (12/250), cache hit >99%
4. **Setup failure:** Clear error in splash with step, message, pg.log, retry button
5. **Dashboard:** Live connection count, cache ratio, health recommendations
6. **CI:** All packages verified, PG binaries checked, setup module imports tested
