# PG Startup Architecture Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix backend timeout crash on PG builds by replacing the fixed 90-second healthcheck with JSONL-aware progress tracking, add PG performance tuning for 200+ connections, enhance DB monitoring dashboard, and harden CI validation.

**Architecture:** The JSONL progress system (splash.js + jsonl.py + handleSetupMessage) already exists and works. The bug is a single `waitForServer()` call with a hard 90-second timeout that races against PG setup. Fix: replace the fixed timeout with a Promise that resolves on the `server_ready` JSONL message, with silence-based fallback. Then: add PG tuning step, fix logging visibility, enhance dashboard, add CI checks.

**Tech Stack:** Electron (main process JS), Python/FastAPI (server), PostgreSQL (bundled), Svelte (admin dashboard), GitHub Actions CI

**Spec:** `docs/superpowers/specs/2026-04-02-pg-startup-architecture-redesign.md`

---

## File Structure

### Files to Modify

| File | Lines | Responsibility |
|------|-------|----------------|
| `locaNext/electron/main.js` | 1485 | Backend startup, JSONL parsing, waitForServer replacement |
| `locaNext/electron/splash.js` | ~500 | Splash UI enhancements (detail log panel, elapsed timer, enriched steps) |
| `server/main.py` | 939 | __main__ JSONL emissions, lifespan server_ready emission |
| `server/setup/jsonl.py` | 85 | New message types (boot_started, setup_substep, setup_error) |
| `server/setup/runner.py` | 212 | STEP_FUNCTIONS registry update, loguru migration |
| `server/setup/steps.py` | 648 | New tune_performance step, loguru migration, JSONL substeps |
| `server/setup/pg_lifecycle.py` | 197 | Loguru migration, is_pg_running check before start |
| `server/setup/state.py` | 105 | STEP_NAMES update (add tune_performance), loguru migration |
| `server/setup/network.py` | 24 | Loguru migration |
| `server/config.py` | 639 | LAN server pool sizing (25/35) |
| `adminDashboard/src/routes/database/+page.svelte` | 451 | Connection monitor, cache stats, health panel |
| `.github/workflows/build-electron.yml` | 1731 | Package verification, PG binary check, flag file |

### Files to Create

| File | Responsibility |
|------|----------------|
| `server/setup/hardware_detect.py` | RAM/CPU/SSD detection using psutil |

---

## Task 1: Replace waitForServer with JSONL-Aware Startup (THE CORE FIX)

**Files:**
- Modify: `locaNext/electron/main.js:26-59` (handleSetupMessage), `locaNext/electron/main.js:210-243` (waitForServer), `locaNext/electron/main.js:338-348` (startBackendServer tail)

This is the single change that fixes the crash. Everything else is enhancement.

- [ ] **Step 1: Add serverReadyResolve callback to module scope**

In `locaNext/electron/main.js`, add after line 20 (after the splash imports):

```javascript
// Promise resolve/reject callbacks for JSONL-aware server startup
let _serverReadyResolve = null;
let _serverReadyReject = null;
let _lastJsonlTime = Date.now();
```

- [ ] **Step 2: Update handleSetupMessage to resolve the server_ready promise**

Replace lines 26-59 with:

```javascript
/**
 * Handle JSONL setup messages from Python backend stdout.
 * Routes messages to splash screen for visual feedback during first-launch setup.
 * Also tracks last JSONL time for silence-based timeout detection.
 */
function handleSetupMessage(msg) {
  _lastJsonlTime = Date.now(); // Any JSONL = backend is alive

  switch (msg.type) {
    case 'boot_started':
      logger.info('[Setup] Boot started', { version: msg.version, build_type: msg.build_type });
      splash.updateSplash('Initializing...', 5);
      break;

    case 'setup_started':
      splash.showSetupMode(msg.total_steps);
      break;

    case 'setup_step':
      splash.updateSetupStep(msg.index, msg.step, msg.status, msg.duration_ms, msg.error_detail);
      break;

    case 'setup_substep':
      logger.info('[Setup detail]', { step: msg.step, detail: msg.detail });
      break;

    case 'setup_complete':
      if (msg.success) {
        splash.showSetupComplete(msg.lan_ip);
      } else {
        splash.showSetupError(msg.failed_step, msg.error_code, msg.error_detail);
        if (_serverReadyReject) {
          _serverReadyReject(new Error(`Setup failed at ${msg.failed_step}: ${msg.error_detail}`));
        }
      }
      break;

    case 'setup_error':
      splash.showSetupError(msg.step, msg.error_code, msg.error_detail);
      if (_serverReadyReject) {
        _serverReadyReject(new Error(`Setup error: ${msg.error_code} — ${msg.error_detail}`));
      }
      break;

    case 'pg_starting':
      splash.updateSplash('Starting database...', 70);
      break;

    case 'pg_ready':
      splash.updateSplash('Starting server...', 85);
      break;

    case 'server_ready':
      splash.updateSplash('Ready!', 100);
      if (_serverReadyResolve) {
        _serverReadyResolve(true);
      }
      break;

    default:
      logger.info('[Setup message]', msg);
  }
}
```

- [ ] **Step 3: Create waitForServerJsonl function**

Add after the existing `waitForServer` function (after line 243):

```javascript
/**
 * Wait for backend using JSONL progress tracking.
 * Resolves when 'server_ready' JSONL message arrives.
 * Rejects if 60 seconds pass with NO JSONL messages (backend stuck).
 * Falls back to HTTP healthcheck if JSONL never arrives.
 *
 * @param {string} url - Backend URL for fallback healthcheck
 * @param {number} silenceTimeoutMs - Max silence before assuming stuck (default: 60000)
 * @returns {Promise<boolean>}
 */
function waitForServerJsonl(url, silenceTimeoutMs = 60000) {
  return new Promise((resolve, reject) => {
    _serverReadyResolve = resolve;
    _serverReadyReject = reject;
    _lastJsonlTime = Date.now();

    const silenceCheck = setInterval(() => {
      const silenceMs = Date.now() - _lastJsonlTime;

      // If server_ready already resolved, clean up
      if (_serverReadyResolve === null) {
        clearInterval(silenceCheck);
        return;
      }

      // Check silence timeout
      if (silenceMs > silenceTimeoutMs) {
        clearInterval(silenceCheck);
        logger.error('Backend silent for ' + (silenceMs / 1000) + 's — may be stuck');

        // Last resort: try HTTP healthcheck once
        http.get(`${url}/health`, (res) => {
          if (res.statusCode === 200) {
            logger.info('Backend responding to HTTP despite JSONL silence');
            _serverReadyResolve = null;
            resolve(true);
          } else {
            _serverReadyResolve = null;
            reject(new Error(`Backend silent for ${silenceTimeoutMs / 1000}s and HTTP check failed`));
          }
        }).on('error', () => {
          _serverReadyResolve = null;
          reject(new Error(`Backend silent for ${silenceTimeoutMs / 1000}s — server not responding`));
        });
        return;
      }
    }, 2000); // Check every 2 seconds

    // Safety: also listen for backend process exit
    if (backendProcess) {
      backendProcess.once('exit', (code) => {
        clearInterval(silenceCheck);
        if (_serverReadyResolve) {
          _serverReadyResolve = null;
          reject(new Error(`Backend process exited with code ${code} before server was ready`));
        }
      });
    }
  });
}
```

- [ ] **Step 4: Replace waitForServer call in startBackendServer**

Replace lines 339-347 in `startBackendServer()`:

```javascript
  // Wait for server to be ready via JSONL progress tracking
  // No fixed timeout — waits as long as backend sends progress updates
  // Only times out after 60s of complete silence
  try {
    await waitForServerJsonl('http://127.0.0.1:8888', 60000);
    return true;
  } catch (error) {
    logger.error('Backend server failed to start', { error: error.message });
    return false;
  }
```

- [ ] **Step 5: Also update stderr handler to reset silence timer**

Replace line 326-328:

```javascript
  backendProcess.stderr.on('data', (data) => {
    _lastJsonlTime = Date.now(); // Any output = backend alive
    const output = data.toString().trim();
    if (output) {
      logger.warning('[Backend stderr]', { output });
    }
  });
```

- [ ] **Step 6: Verify the fix compiles — check main.js imports**

Verify `http` is already imported in main.js (it should be, used by existing waitForServer):

```bash
cd /home/neil1988/LocalizationTools && grep -n "import.*http" locaNext/electron/main.js | head -5
```

Expected: `http` or `net` import exists.

- [ ] **Step 7: Commit**

```bash
git add locaNext/electron/main.js
git commit -m "fix: replace fixed 90s backend timeout with JSONL-aware progress tracking

The PG setup wizard blocks the backend for up to 110s before uvicorn starts.
The old waitForServer() had a hard 90-retry limit (90s) causing timeout.
New waitForServerJsonl() resolves on 'server_ready' JSONL message with
silence-based fallback (60s of no output = stuck). Existing JSONL+splash
system already handles progress display."
```

---

## Task 2: Emit server_ready from Backend Lifespan

**Files:**
- Modify: `server/main.py:108-210` (lifespan function), `server/main.py:829-939` (__main__ block)

The backend must emit `server_ready` JSONL when uvicorn is actually listening. Currently `emit_server_ready` exists in `jsonl.py` but is never called.

- [ ] **Step 1: Add server_ready emission at end of lifespan startup**

In `server/main.py`, find the end of the lifespan startup section (around line 200, before the `yield`). Add:

```python
    # Signal to Electron that server is ready to accept connections
    try:
        from server.setup.jsonl import emit_server_ready
        emit_server_ready(config.SERVER_PORT)
        logger.success("Server startup complete")
    except Exception:
        logger.success("Server startup complete")
```

This goes right before the existing `logger.success("Server startup complete")` line — replace that line with this block.

- [ ] **Step 2: Add boot_started emission at top of __main__**

In `server/main.py`, at the beginning of the `__main__` block (after `import uvicorn` on line 830), add:

```python
    # Emit boot_started so Electron knows the backend process is alive
    try:
        import json as _json
        import sys as _sys
        _boot_msg = _json.dumps({
            "type": "boot_started",
            "version": getattr(config, "VERSION", "unknown"),
        })
        _sys.stdout.write(_boot_msg + "\n")
        _sys.stdout.flush()
    except Exception:
        pass
```

- [ ] **Step 3: Add is_pg_running check before start_pg on subsequent launches**

In `server/main.py`, around line 920 (the `else` branch for subsequent launches), replace:

```python
            else:
                # Subsequent launch — just start PG
                emit_pg_starting()
                ok, msg = start_pg(pg.pg_ctl, pg.data_dir, pg.log_file)
                if ok:
                    emit_pg_ready()
                    logger.info("PostgreSQL started for existing setup")
                else:
                    logger.warning(f"PostgreSQL start failed: {msg}")
```

With:

```python
            else:
                # Subsequent launch — check if PG is already running, then start if needed
                from server.setup.pg_lifecycle import is_pg_running
                if is_pg_running(pg.pg_isready, getattr(config, 'POSTGRES_PORT', 5432)):
                    emit_pg_ready()
                    logger.info("PostgreSQL already running — skipping start")
                else:
                    emit_pg_starting()
                    ok, msg = start_pg(pg.pg_ctl, pg.data_dir, pg.log_file)
                    if ok:
                        emit_pg_ready()
                        logger.info("PostgreSQL started for existing setup")
                    else:
                        logger.warning(f"PostgreSQL start failed: {msg}")
```

- [ ] **Step 4: Commit**

```bash
git add server/main.py
git commit -m "feat: emit server_ready JSONL from lifespan + boot_started from __main__

Electron's new waitForServerJsonl resolves on server_ready.
Also adds is_pg_running check to skip redundant pg_ctl start on
subsequent launches (saves 3-5s when PG survives between sessions)."
```

---

## Task 3: Logging Overhaul — stdlib to loguru

**Files:**
- Modify: `server/setup/runner.py`, `server/setup/steps.py`, `server/setup/pg_lifecycle.py`, `server/setup/state.py`, `server/setup/network.py`

All 5 files use `import logging; logger = logging.getLogger(__name__)` which is invisible to Electron. Switch to loguru (same API, goes to stderr which Electron captures).

- [ ] **Step 1: Migrate runner.py**

In `server/setup/runner.py`, replace line 4:

```python
import logging
```

with:

```python
from loguru import logger
```

And delete line 30:

```python
logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Migrate steps.py**

In `server/setup/steps.py`, replace line 4:

```python
import logging
```

with:

```python
from loguru import logger
```

And delete line 17:

```python
logger = logging.getLogger(__name__)
```

- [ ] **Step 3: Migrate pg_lifecycle.py**

In `server/setup/pg_lifecycle.py`, replace line 3:

```python
import logging
```

with:

```python
from loguru import logger
```

And delete line 11:

```python
logger = logging.getLogger(__name__)
```

- [ ] **Step 4: Migrate state.py**

In `server/setup/state.py`, replace line 3:

```python
import logging
```

with:

```python
from loguru import logger
```

And delete line 16:

```python
logger = logging.getLogger(__name__)
```

- [ ] **Step 5: Migrate network.py — no logging to add**

`server/setup/network.py` doesn't use logging at all (just bare `except: pass`). No change needed.

- [ ] **Step 6: Verify no stdlib logging imports remain in setup/**

```bash
cd /home/neil1988/LocalizationTools && grep -rn "import logging" server/setup/ && grep -rn "getLogger" server/setup/
```

Expected: no matches.

- [ ] **Step 7: Commit**

```bash
git add server/setup/runner.py server/setup/steps.py server/setup/pg_lifecycle.py server/setup/state.py
git commit -m "fix: migrate setup wizard logging from stdlib to loguru

Setup modules used stdlib logging which was invisible to Electron's
stderr capture. Loguru goes to stderr and is captured in the log.
API is identical (logger.info/warning/error/exception)."
```

---

## Task 4: Hardware Detection Module

**Files:**
- Create: `server/setup/hardware_detect.py`

- [ ] **Step 1: Create hardware_detect.py**

```python
"""Hardware detection for PostgreSQL performance tuning.

Uses psutil to detect RAM, CPU cores, and storage type.
All detection is local-only, no network calls.
"""
from __future__ import annotations

from dataclasses import dataclass

from loguru import logger


@dataclass
class HardwareInfo:
    """Detected hardware specifications."""
    ram_gb: int           # Total RAM in GB (rounded down)
    physical_cores: int   # Physical CPU cores (not hyperthreaded)
    logical_cores: int    # Logical CPU cores (with hyperthreading)
    is_ssd: bool          # Best-effort SSD detection
    os_name: str          # 'nt' or 'posix'


def detect_hardware(data_dir: str = "") -> HardwareInfo:
    """Detect hardware specs using psutil.

    Falls back to conservative defaults if detection fails.
    SSD detection uses heuristic: Windows WMI query or assume SSD
    for modern systems (conservative default: True).
    """
    import os
    import psutil

    # RAM
    try:
        ram_bytes = psutil.virtual_memory().total
        ram_gb = int(ram_bytes / (1024 ** 3))
    except Exception as e:
        logger.warning("RAM detection failed, defaulting to 8GB: {}", e)
        ram_gb = 8

    # CPU cores
    try:
        physical_cores = psutil.cpu_count(logical=False) or 4
        logical_cores = psutil.cpu_count(logical=True) or physical_cores
    except Exception as e:
        logger.warning("CPU detection failed, defaulting to 4 cores: {}", e)
        physical_cores = 4
        logical_cores = 4

    # SSD detection (best-effort)
    is_ssd = True  # Default: assume SSD (modern systems)
    if os.name == "nt" and data_dir:
        try:
            import subprocess
            # Use PowerShell to query disk type
            drive_letter = os.path.splitdrive(data_dir)[0]
            if drive_letter:
                result = subprocess.run(
                    ["powershell", "-Command",
                     f"(Get-PhysicalDisk | Where-Object {{ $_.DeviceId -eq "
                     f"(Get-Partition -DriveLetter '{drive_letter[0]}').DiskNumber }}).MediaType"],
                    capture_output=True, text=True, timeout=5,
                )
                if "HDD" in result.stdout:
                    is_ssd = False
                    logger.info("Detected HDD storage")
                else:
                    logger.info("Detected SSD storage")
        except Exception:
            logger.debug("SSD detection failed, assuming SSD")

    info = HardwareInfo(
        ram_gb=ram_gb,
        physical_cores=physical_cores,
        logical_cores=logical_cores,
        is_ssd=is_ssd,
        os_name=os.name,
    )
    logger.info(
        "Hardware detected: {}GB RAM, {} physical / {} logical cores, SSD={}",
        info.ram_gb, info.physical_cores, info.logical_cores, info.is_ssd,
    )
    return info
```

- [ ] **Step 2: Commit**

```bash
git add server/setup/hardware_detect.py
git commit -m "feat: add hardware detection module for PG performance tuning

Uses psutil (already bundled) to detect RAM, CPU cores, and SSD.
Falls back to conservative defaults if detection fails.
SSD detection via PowerShell on Windows."
```

---

## Task 5: New Setup Step — tune_performance

**Files:**
- Modify: `server/setup/state.py:18-26` (STEP_NAMES)
- Modify: `server/setup/runner.py:36-44` (STEP_FUNCTIONS), `server/setup/runner.py:47-53` (FATAL_STEPS)
- Modify: `server/setup/steps.py` (add step_tune_performance function)
- Modify: `locaNext/electron/splash.js:22-30` (SETUP_STEP_LABELS)

- [ ] **Step 1: Add tune_performance to STEP_NAMES in state.py**

In `server/setup/state.py`, replace lines 18-26:

```python
STEP_NAMES: list[str] = [
    "preflight_checks",
    "init_database",
    "configure_access",
    "generate_certificates",
    "start_database",
    "tune_performance",
    "create_account",
    "create_database",
]
```

- [ ] **Step 2: Add step_tune_performance to steps.py**

At the end of `server/setup/steps.py` (after `step_generate_certificates`), add:

```python
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
            message="pg_bin_dir not configured", error_code="MISSING_BINARIES",
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
    max_connections = 250  # 200 target + 50 buffer
    shared_buffers_gb = max(1, hw.ram_gb // 4)
    effective_cache_size_gb = max(2, hw.ram_gb * 3 // 4)
    # work_mem: safe for high concurrency (connections * 2 ops * work_mem < RAM)
    work_mem_mb = max(16, min(128, hw.ram_gb * 1024 // (max_connections * 2)))
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

    # Write tuning to postgresql.conf
    try:
        existing = conf_path.read_text(encoding="utf-8")
        marker = "# LocaNext Performance Tuning"
        if marker in existing:
            # Remove old tuning block
            before = existing[:existing.index(marker)]
            existing = before.rstrip() + "\n"
        conf_path.write_text(existing + "\n" + tuning_block, encoding="utf-8")
    except Exception as exc:
        return StepResult(
            step=step, status="failed", duration_ms=_ms_since(t0),
            message=f"Failed to write postgresql.conf: {exc}",
            error_code="TUNE_FAILED",
        )

    # Reload PG config (no restart needed)
    env = _make_env(paths.bin_dir)
    try:
        result = subprocess.run(
            [str(paths.pg_ctl), "reload", "-D", str(paths.data_dir)],
            capture_output=True, text=True, timeout=10, env=env,
        )
        if result.returncode != 0:
            logger.warning("pg_ctl reload failed (settings will apply on next restart): {}", result.stderr)
    except Exception as exc:
        logger.warning("pg_ctl reload failed: {} (settings will apply on next restart)", exc)

    logger.info(
        "PG tuned: max_connections={}, shared_buffers={}GB, work_mem={}MB, "
        "parallel_workers={}, SSD={}",
        max_connections, shared_buffers_gb, work_mem_mb, max_parallel_workers, hw.is_ssd,
    )

    return StepResult(
        step=step, status="done", duration_ms=_ms_since(t0),
        message=f"Tuned for {hw.ram_gb}GB RAM, {hw.physical_cores} cores, {max_connections} connections",
    )
```

- [ ] **Step 3: Register tune_performance in runner.py**

In `server/setup/runner.py`, add the import (line 28):

```python
from server.setup.steps import (
    step_configure_access,
    step_create_account,
    step_create_database,
    step_generate_certificates,
    step_init_database,
    step_preflight_checks,
    step_start_database,
    step_tune_performance,
)
```

Update STEP_FUNCTIONS (line 36-44):

```python
STEP_FUNCTIONS: dict[str, Callable[[SetupConfig], StepResult]] = {
    "preflight_checks": step_preflight_checks,
    "init_database": step_init_database,
    "configure_access": step_configure_access,
    "generate_certificates": step_generate_certificates,
    "start_database": step_start_database,
    "tune_performance": step_tune_performance,
    "create_account": step_create_account,
    "create_database": step_create_database,
}
```

Add to FATAL_STEPS (line 47-53) — tune_performance is NOT fatal (PG works with defaults):

```python
FATAL_STEPS: set[str] = {
    "preflight_checks",
    "init_database",
    "configure_access",
    "generate_certificates",
    "start_database",
}
RECOVERABLE_STEPS: set[str] = {"create_account", "create_database"}
OPTIONAL_STEPS: set[str] = {"tune_performance"}  # PG works with defaults
```

- [ ] **Step 4: Update splash.js SETUP_STEP_LABELS**

In `locaNext/electron/splash.js`, replace lines 22-30:

```javascript
const SETUP_STEP_LABELS = [
  'Checking system requirements',
  'Initializing database',
  'Configuring network access',
  'Generating certificates',
  'Starting PostgreSQL',
  'Tuning performance',
  'Creating service account',
  'Creating database',
];
```

- [ ] **Step 5: Commit**

```bash
git add server/setup/state.py server/setup/steps.py server/setup/runner.py server/setup/hardware_detect.py locaNext/electron/splash.js
git commit -m "feat: add tune_performance setup step with hardware auto-detection

New step detects RAM/CPU/SSD via psutil and writes optimized postgresql.conf:
- max_connections=250, shared_buffers=25% RAM, work_mem safe for concurrency
- SSD detection for random_page_cost and io_concurrency
- pg_ctl reload applies settings without restart
- Classified as OPTIONAL (PG works with defaults if tuning fails)"
```

---

## Task 6: SQLAlchemy Connection Pool Tuning

**Files:**
- Modify: `server/config.py:185-199` (_apply_lan_server_overrides), `server/config.py:234-238` (pool defaults)

- [ ] **Step 1: Update LAN server pool settings**

In `server/config.py`, find the `_apply_lan_server_overrides` function (around line 185-199). Replace the pool settings within it:

```python
        # Connection pool tuned for LAN server with 200+ concurrent connections
        # 25 base + 35 overflow = 60 max connections from this backend instance
        cls.DB_POOL_SIZE = 25
        cls.DB_MAX_OVERFLOW = 35
        cls.DB_POOL_TIMEOUT = 20    # Fail fast if pool exhausted
        cls.DB_POOL_RECYCLE = 1800  # Recycle every 30 min
```

- [ ] **Step 2: Commit**

```bash
git add server/config.py
git commit -m "feat: tune SQLAlchemy connection pool for 200+ concurrent users

LAN server mode: pool_size=25, max_overflow=35 (total 60).
Previous values (3/5) were inadequate for 10+ simultaneous users.
Pool timeout reduced to 20s for faster failure detection."
```

---

## Task 7: Enhanced JSONL Protocol (Enriched Messages)

**Files:**
- Modify: `server/setup/jsonl.py`

- [ ] **Step 1: Add new message types to jsonl.py**

In `server/setup/jsonl.py`, add after the existing `emit_server_ready` function (line 86):

```python
def emit_boot_started(version: str, build_type: str = "unknown") -> None:
    """Emit when __main__ block begins execution."""
    emit_jsonl({
        "type": "boot_started",
        "version": version,
        "build_type": build_type,
    })


def emit_setup_substep(step: str, detail: str) -> None:
    """Emit a sub-step detail message for enriched progress display."""
    emit_jsonl({
        "type": "setup_substep",
        "step": step,
        "detail": detail,
    })


def emit_setup_error(
    step: str,
    error_code: str,
    error_detail: str,
    pg_log_tail: str = "",
    suggestion: str = "",
) -> None:
    """Emit a setup error with full diagnostic info."""
    emit_jsonl({
        "type": "setup_error",
        "step": step,
        "error_code": error_code,
        "error_detail": error_detail,
        "pg_log_tail": pg_log_tail,
        "suggestion": suggestion,
    })


# Error code → user-friendly suggestion mapping
SUGGESTIONS: dict[str, str] = {
    "PORT_CONFLICT": "Port 5432 is already in use. Close any other PostgreSQL instances.",
    "LOW_DISK": "Less than 500MB free disk space. Free up space and retry.",
    "MISSING_BINARIES": "PostgreSQL binaries not found. The installation may be corrupted.",
    "INITDB_TIMEOUT": "Database initialization timed out. Check antivirus isn't blocking.",
    "INITDB_FAILED": "Database initialization failed. Check disk permissions.",
    "START_TIMEOUT": "PostgreSQL failed to start. Check resources/bin/postgresql/pg.log",
    "START_FAILED": "PostgreSQL failed to start. Check if port 5432 is available.",
    "CERT_GENERATION_FAILED": "TLS certificate generation failed. Check disk space.",
    "CREATE_USER_FAILED": "Could not create database user. Check PostgreSQL logs.",
    "CREATE_DB_FAILED": "Could not create database. Check PostgreSQL logs.",
    "TUNE_FAILED": "Performance tuning failed. PG will work with default settings.",
}


def get_suggestion(error_code: str) -> str:
    """Get a user-friendly suggestion for an error code."""
    return SUGGESTIONS.get(error_code, "Check the application logs for details.")
```

- [ ] **Step 2: Commit**

```bash
git add server/setup/jsonl.py
git commit -m "feat: add enriched JSONL message types for setup progress

New: boot_started, setup_substep, setup_error with diagnostics.
Includes error code → suggestion mapping for user-friendly messages."
```

---

## Task 8: Enhanced DB Monitoring Dashboard

**Files:**
- Modify: `adminDashboard/src/routes/database/+page.svelte`

- [ ] **Step 1: Add API calls for connection and health data**

In the `<script>` section of `adminDashboard/src/routes/database/+page.svelte`, add after the existing `loadDatabaseStats` function:

```javascript
  let dbHealth = null;
  let dbPoolStats = null;
  let refreshInterval = null;

  async function loadDbHealth() {
    try {
      dbHealth = await adminAPI.request('/admin/db/health');
    } catch (e) {
      console.warn('DB health check failed:', e);
    }
  }

  async function loadDbPoolStats() {
    try {
      dbPoolStats = await adminAPI.request('/admin/db/stats');
    } catch (e) {
      console.warn('DB pool stats failed:', e);
    }
  }

  async function loadAll() {
    await Promise.all([loadDatabaseStats(), loadDbHealth(), loadDbPoolStats()]);
  }
```

Update the `onMount` to call `loadAll()` and set up auto-refresh:

```javascript
  onMount(async () => {
    await loadAll();
    refreshInterval = setInterval(loadAll, 5000); // Refresh every 5s
    return () => {
      if (refreshInterval) clearInterval(refreshInterval);
    };
  });
```

- [ ] **Step 2: Add Connection Monitor section to template**

Before the existing table tree section in the template, add:

```svelte
<!-- Connection Monitor -->
{#if dbPoolStats?.connection_pool}
  {@const pool = dbPoolStats.connection_pool}
  {@const maxConn = pool.max_connections || 250}
  {@const activeConn = pool.active_connections || 0}
  {@const idleConn = pool.idle_connections || 0}
  {@const pct = Math.round((activeConn / maxConn) * 100)}
  <div class="monitor-card">
    <h3>Connections</h3>
    <div class="stat-row">
      <span class="stat-label">Active: {activeConn} / {maxConn}</span>
      <span class="stat-value {pct > 80 ? 'warning' : pct > 50 ? 'caution' : 'good'}">{pct}%</span>
    </div>
    <div class="progress-bar-container">
      <div class="progress-bar {pct > 80 ? 'warning' : 'good'}" style="width: {pct}%"></div>
    </div>
    <div class="stat-details">
      Active: {activeConn} | Idle: {idleConn} | Waiting: {pool.waiting_connections || 0}
    </div>
  </div>
{/if}

<!-- Cache Performance -->
{#if dbPoolStats?.performance}
  {@const perf = dbPoolStats.performance}
  {@const hitRatio = perf.cache_hit_ratio || 0}
  {@const hitColor = hitRatio > 99 ? 'good' : hitRatio > 95 ? 'caution' : 'warning'}
  <div class="monitor-card">
    <h3>Cache Performance</h3>
    <div class="stat-row">
      <span class="stat-label">Hit Ratio</span>
      <span class="stat-value {hitColor}">{hitRatio.toFixed(1)}%</span>
    </div>
    <div class="progress-bar-container">
      <div class="progress-bar {hitColor}" style="width: {hitRatio}%"></div>
    </div>
  </div>
{/if}

<!-- Health Recommendations -->
{#if dbHealth?.issues?.length > 0}
  <div class="monitor-card">
    <h3>Health Check</h3>
    {#each dbHealth.issues as issue}
      <div class="health-issue {issue.severity || 'info'}">
        <span class="issue-icon">{issue.severity === 'warning' ? '⚠️' : 'ℹ️'}</span>
        <span>{issue.message}</span>
      </div>
    {/each}
    {#if dbHealth.recommendations?.length > 0}
      {#each dbHealth.recommendations as rec}
        <div class="health-rec">💡 {rec}</div>
      {/each}
    {/if}
  </div>
{/if}
```

- [ ] **Step 3: Add CSS for monitoring panels**

Add to the `<style>` section:

```css
  .monitor-card {
    background: var(--cds-layer-01, #262626);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
  }
  .monitor-card h3 {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 12px;
    color: var(--cds-text-primary, #f4f4f4);
  }
  .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  .stat-label { color: var(--cds-text-secondary, #c6c6c6); font-size: 13px; }
  .stat-value { font-size: 18px; font-weight: 600; }
  .stat-value.good { color: #42be65; }
  .stat-value.caution { color: #f1c21b; }
  .stat-value.warning { color: #da1e28; }
  .stat-details { font-size: 12px; color: var(--cds-text-secondary, #c6c6c6); margin-top: 8px; }
  .progress-bar-container {
    background: var(--cds-layer-02, #393939);
    border-radius: 4px;
    height: 8px;
    overflow: hidden;
  }
  .progress-bar {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
  }
  .progress-bar.good { background: linear-gradient(90deg, #42be65, #24a148); }
  .progress-bar.caution { background: linear-gradient(90deg, #f1c21b, #d2a106); }
  .progress-bar.warning { background: linear-gradient(90deg, #da1e28, #ba1b23); }
  .health-issue {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    font-size: 13px;
    border-radius: 4px;
    margin-bottom: 4px;
  }
  .health-issue.warning { background: rgba(241, 194, 27, 0.1); color: #f1c21b; }
  .health-issue.info { background: rgba(66, 190, 101, 0.1); color: #42be65; }
  .health-rec { font-size: 12px; color: var(--cds-text-secondary, #c6c6c6); padding: 4px 8px; }
```

- [ ] **Step 4: Commit**

```bash
git add adminDashboard/src/routes/database/+page.svelte
git commit -m "feat: add live connection monitor, cache stats, health panel to DB dashboard

Wires existing /admin/db/stats and /admin/db/health endpoints to UI.
Auto-refreshes every 5s. Shows connection usage %, cache hit ratio,
and health recommendations with color-coded severity."
```

---

## Task 9: CI/CD Validation Enhancements

**Files:**
- Modify: `.github/workflows/build-electron.yml`

- [ ] **Step 1: Add missing package verification checks**

After the existing verification block (around line 730), add:

```powershell
        # Verify packages that were installed but never checked
        Write-Host "=== Verifying additional packages ==="
        & "tools\python\python.exe" -c "from cryptography import x509; print('[OK] cryptography')"
        if ($LASTEXITCODE -ne 0) { Write-Error "cryptography verification failed"; exit 1 }
        & "tools\python\python.exe" -c "from PIL import Image; print('[OK] Pillow')"
        if ($LASTEXITCODE -ne 0) { Write-Error "Pillow verification failed"; exit 1 }
        & "tools\python\python.exe" -c "import psutil; print('[OK] psutil')"
        if ($LASTEXITCODE -ne 0) { Write-Error "psutil verification failed"; exit 1 }
        & "tools\python\python.exe" -c "from sse_starlette.sse import EventSourceResponse; print('[OK] sse-starlette')"
        if ($LASTEXITCODE -ne 0) { Write-Error "sse-starlette verification failed"; exit 1 }
        & "tools\python\python.exe" -c "import xlsxwriter; print('[OK] xlsxwriter')"
        if ($LASTEXITCODE -ne 0) { Write-Error "xlsxwriter verification failed"; exit 1 }
```

- [ ] **Step 2: Add PG binary validation (Full Admin builds only)**

After the PG download/extract section (around line 960), add:

```powershell
        # Verify PG binaries are complete
        Write-Host "=== Verifying PostgreSQL binaries ==="
        $pgBinDir = "resources\bin\postgresql\bin"
        if (Test-Path $pgBinDir) {
          $required = @("initdb.exe", "pg_ctl.exe", "psql.exe", "pg_isready.exe")
          foreach ($bin in $required) {
            $binPath = Join-Path $pgBinDir $bin
            if (-not (Test-Path $binPath)) {
              Write-Error "MISSING PG BINARY: $binPath"
              exit 1
            }
            Write-Host "[OK] PG binary: $bin"
          }
          # Write pg_setup_mode flag
          "auto" | Out-File -FilePath "resources\pg_setup_mode.flag" -Encoding ascii -NoNewline
          Write-Host "[OK] pg_setup_mode.flag written (auto)"
        } else {
          Write-Host "[INFO] No PG binaries bundled (Build Light)"
        }
```

- [ ] **Step 3: Add setup module import test**

After the package verification, add:

```powershell
        # Verify setup module imports cleanly
        Write-Host "=== Verifying setup module ==="
        & "tools\python\python.exe" -c @"
from server.setup import SetupConfig, SetupResult, StepResult
from server.setup.runner import run_setup, STEP_FUNCTIONS
from server.setup.state import read_state, is_setup_complete, STEP_NAMES
from server.setup.pg_lifecycle import find_pg_binaries, start_pg, is_pg_running
from server.setup.hardware_detect import detect_hardware
from server.setup.jsonl import emit_jsonl, emit_setup_started, emit_server_ready
print(f'[OK] Setup module: {len(STEP_NAMES)} steps ({", ".join(STEP_NAMES)})')
print(f'[OK] Step functions: {len(STEP_FUNCTIONS)} registered')
"@
        if ($LASTEXITCODE -ne 0) { Write-Error "Setup module import failed"; exit 1 }
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/build-electron.yml
git commit -m "ci: add package verification for 6 unchecked deps + PG binary validation

Adds import checks for: cryptography, Pillow, psutil, sse-starlette, xlsxwriter.
Validates all 4 PG binaries exist (initdb, pg_ctl, psql, pg_isready).
Writes pg_setup_mode.flag for Full Admin builds.
Tests setup module imports cleanly."
```

---

## Task 10: Splash Screen Enrichment

**Files:**
- Modify: `locaNext/electron/splash.js`

- [ ] **Step 1: Add elapsed timer to setup mode**

In `locaNext/electron/splash.js`, in the `getSetupHTML` function (line 452), add an elapsed timer element after the progress bar in the HTML template. Add to the setup-container div:

```html
    <div class="elapsed" id="elapsed-timer">Elapsed: 0.0s</div>
```

And add the JavaScript timer at the bottom of the `<body>`:

```html
    <script>
      var startTime = Date.now();
      setInterval(function() {
        var el = document.getElementById('elapsed-timer');
        if (el) el.textContent = 'Elapsed: ' + ((Date.now() - startTime) / 1000).toFixed(1) + 's';
      }, 100);
    </script>
```

Add CSS for the elapsed timer:

```css
    .elapsed {
      text-align: center;
      font-size: 12px;
      color: rgba(255,255,255,0.4);
      margin-top: 16px;
    }
```

- [ ] **Step 2: Enlarge setup window for more detail**

In `showSetupMode` (line 219), increase the window size to accommodate 8 steps + elapsed timer:

```javascript
  splashWindow.setSize(500, 500);
```

- [ ] **Step 3: Commit**

```bash
git add locaNext/electron/splash.js
git commit -m "feat: add elapsed timer and enlarge setup splash for 8 steps

Shows running elapsed time during setup wizard.
Window enlarged to 500x500 to fit tune_performance step."
```

---

## Task 11: Update Spec with Corrected Understanding

**Files:**
- Modify: `docs/superpowers/specs/2026-04-02-pg-startup-architecture-redesign.md`

- [ ] **Step 1: Add discovery note to spec**

Add at the top of the spec, after the date/status header:

```markdown
**KEY DISCOVERY:** 60% of the infrastructure already existed:
- `splash.js` — full setup mode UI with step-by-step progress, error panel, retry/offline buttons
- `jsonl.py` — all emit functions for setup events
- `main.js:26-59` — JSONL parsing + routing to splash
- The ENTIRE bug was ONE LINE: `waitForServer('http://127.0.0.1:8888', 90, 1000)` — a dumb fixed timeout
- Fix: `waitForServerJsonl()` — resolves on `server_ready` JSONL, silence-based fallback
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-04-02-pg-startup-architecture-redesign.md
git commit -m "docs: update spec with corrected scope (60% already existed)"
```

---

## Task 12: Final Integration Verification

- [ ] **Step 1: Verify all setup module imports work**

```bash
cd /home/neil1988/LocalizationTools && python3 -c "
from server.setup import SetupConfig, SetupResult, StepResult
from server.setup.runner import run_setup, STEP_FUNCTIONS
from server.setup.state import read_state, is_setup_complete, STEP_NAMES
from server.setup.pg_lifecycle import find_pg_binaries, start_pg, is_pg_running
from server.setup.hardware_detect import detect_hardware
from server.setup.jsonl import emit_jsonl, emit_setup_started, emit_server_ready, emit_setup_substep, emit_setup_error, get_suggestion, emit_boot_started
print(f'Steps: {len(STEP_NAMES)} = {STEP_NAMES}')
print(f'Functions: {len(STEP_FUNCTIONS)} = {list(STEP_FUNCTIONS.keys())}')
assert len(STEP_NAMES) == 8, f'Expected 8 steps, got {len(STEP_NAMES)}'
assert 'tune_performance' in STEP_NAMES, 'tune_performance not in STEP_NAMES'
assert 'tune_performance' in STEP_FUNCTIONS, 'tune_performance not in STEP_FUNCTIONS'
print('ALL ASSERTIONS PASSED')
"
```

Expected: ALL ASSERTIONS PASSED

- [ ] **Step 2: Verify hardware detection works on WSL**

```bash
python3 -c "
from server.setup.hardware_detect import detect_hardware
hw = detect_hardware()
print(f'RAM: {hw.ram_gb}GB, Cores: {hw.physical_cores}/{hw.logical_cores}, SSD: {hw.is_ssd}')
assert hw.ram_gb > 0, 'RAM detection failed'
assert hw.physical_cores > 0, 'CPU detection failed'
print('HARDWARE DETECTION OK')
"
```

- [ ] **Step 3: Verify loguru migration is complete**

```bash
cd /home/neil1988/LocalizationTools && grep -rn "import logging" server/setup/ && echo "FAIL: stdlib logging still present" || echo "OK: no stdlib logging in setup/"
grep -rn "getLogger" server/setup/ && echo "FAIL: getLogger still present" || echo "OK: no getLogger in setup/"
```

Expected: Both OK messages.

- [ ] **Step 4: Verify JSONL protocol functions exist**

```bash
python3 -c "
from server.setup.jsonl import (
    emit_jsonl, emit_setup_started, emit_setup_step, emit_setup_complete,
    emit_pg_starting, emit_pg_ready, emit_server_ready,
    emit_boot_started, emit_setup_substep, emit_setup_error, get_suggestion,
)
print('ALL JSONL FUNCTIONS IMPORTABLE')
"
```

- [ ] **Step 5: Commit verification results**

```bash
git add -A
git commit -m "chore: final verification — all modules import, hardware detect works, logging migrated"
```

---

## Execution Summary

| Task | Description | Files | Estimated Lines |
|------|-------------|-------|-----------------|
| 1 | **Replace waitForServer (CORE FIX)** | main.js | ~80 |
| 2 | Emit server_ready from backend | main.py | ~30 |
| 3 | Logging: stdlib → loguru | 4 setup files | ~20 |
| 4 | Hardware detection module | hardware_detect.py (NEW) | ~80 |
| 5 | tune_performance step | state.py, steps.py, runner.py, splash.js | ~120 |
| 6 | SQLAlchemy pool tuning | config.py | ~10 |
| 7 | Enriched JSONL messages | jsonl.py | ~70 |
| 8 | DB monitoring dashboard | database/+page.svelte | ~120 |
| 9 | CI/CD validation | build-electron.yml | ~50 |
| 10 | Splash screen enrichment | splash.js | ~20 |
| 11 | Spec update | spec doc | ~10 |
| 12 | Integration verification | (tests) | ~20 |

**Total: ~630 lines across 13 files (1 new, 12 modified)**

**Critical path:** Tasks 1 → 2 → 3 (fixes the crash). All other tasks are independent enhancements.

**Parallelizable:** Tasks 4+5 (PG tuning), Task 6 (pool config), Task 7 (JSONL), Task 8 (dashboard), Task 9 (CI) can all run in parallel after Task 3.
